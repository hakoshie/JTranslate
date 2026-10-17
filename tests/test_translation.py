from types import SimpleNamespace
from unittest.mock import Mock

from jtranslate_app.converter import JapaneseConverter, INSTRUCTIONS
from jtranslate_app import translation
from jtranslate_app.translate_app import TranslationApp
import queue
import threading


def test_translation_prompt_and_unicode():
    converter = translation.JapaneseTranslator('test', 'gpt-6-luna')
    converter.client = Mock()
    converter.client.responses.create.return_value = SimpleNamespace(output_text='こんにちは世界🌏')
    assert converter.convert('Hello world 🌏') == 'こんにちは世界🌏'
    request = converter.client.responses.create.call_args.kwargs
    assert request['instructions'] == translation.TRANSLATION_INSTRUCTIONS
    assert request['input'] == 'Hello world 🌏'
    assert JapaneseConverter('test', 'gpt-6-luna').instructions == INSTRUCTIONS


def test_empty_never_contacts_provider():
    converter = translation.JapaneseTranslator('test', 'gpt-6-luna')
    converter.client = Mock()
    assert converter.convert('  ') == '  '
    converter.client.responses.create.assert_not_called()


def test_capture_restores_on_success_and_failure():
    for text in ['Hello 🌏', None]:
        assert translation.capture_selected(read=lambda: text) == text


def test_capture_rejects_stale_clipboard():
    assert translation.capture_selected(read=lambda: None) is None


def test_repeat_requests_are_ignored_until_worker_finishes():
    app = TranslationApp.__new__(TranslationApp)
    app.closed = app.paused = False
    app.busy = threading.Lock()
    app.events = queue.Queue()
    for _ in range(20):
        app.request()
    assert app.events.qsize() == 1
    assert app.busy.locked()


def test_empty_selection_never_reads_credentials(monkeypatch):
    from jtranslate_app import translate_app
    app = TranslationApp.__new__(TranslationApp)
    app.events = queue.Queue()
    app.busy = threading.Lock()
    app.busy.acquire()
    monkeypatch.setattr(translate_app, 'capture_selected', lambda: None)
    credentials = Mock(side_effect=AssertionError('must not read auth'))
    monkeypatch.setattr(translate_app, 'get_api_key', credentials)
    app.worker(1)
    assert app.events.get_nowait()[0] == 'message'
    assert not app.busy.locked()
    credentials.assert_not_called()


def test_failure_is_safe_and_allows_retry(monkeypatch):
    from jtranslate_app import translate_app
    app = TranslationApp.__new__(TranslationApp)
    app.events = queue.Queue()
    app.busy = threading.Lock()
    app.busy.acquire()
    monkeypatch.setattr(translate_app, 'capture_selected', Mock(side_effect=RuntimeError('PRIVATE')))
    app.worker(1)
    event = app.events.get_nowait()
    assert 'PRIVATE' not in event[2]
    assert not app.busy.locked()


def test_close_invalidates_pending_result():
    app = TranslationApp.__new__(TranslationApp)
    app.generation = 3
    app.root = Mock()
    app.menu = Mock()
    app.hide()
    assert app.generation == 4
    app.root.withdraw.assert_called_once()


def test_long_text_translates_every_character_in_order(monkeypatch):
    calls = []
    def convert(self, text, previous=None):
        calls.append(text)
        return '訳' + text
    monkeypatch.setattr(JapaneseConverter, 'convert', convert)
    source = ('A long paragraph. 日本語🌏\n' * 1000)
    result = translation.JapaneseTranslator('test', 'gpt-6-luna').convert(source)
    assert ''.join(calls) == source
    assert len(calls) > 1
    assert result.count('訳') == len(calls)


def test_long_text_stops_after_cancellation(monkeypatch):
    calls = []
    def convert(self, text, previous=None):
        calls.append(text)
        return '訳'
    monkeypatch.setattr(JapaneseConverter, 'convert', convert)
    converter = translation.JapaneseTranslator('test', 'gpt-6-luna')
    import pytest
    with pytest.raises(InterruptedError):
        converter.convert('hello ' * 2000, cancelled=lambda: len(calls) == 1)
    assert len(calls) == 1


def test_outside_click_does_not_close_popup_or_menu():
    app = TranslationApp.__new__(TranslationApp)
    app.root = Mock()
    app.root.winfo_viewable.return_value = True
    app.root.winfo_rootx.return_value = 100
    app.root.winfo_rooty.return_value = 100
    app.root.winfo_width.return_value = 500
    app.root.winfo_height.return_value = 300
    app.menu = Mock()
    app.menu.winfo_ismapped.return_value = False
    assert app.contains_point(120, 120)
    assert not app.contains_point(20, 20)
    app.menu.winfo_ismapped.return_value = True
    app.menu.winfo_rootx.return_value = 600
    app.menu.winfo_rooty.return_value = 400
    app.menu.winfo_width.return_value = 150
    app.menu.winfo_height.return_value = 40
    assert app.contains_point(650, 410)


def test_dismissed_result_does_not_reopen_popup():
    app = TranslationApp.__new__(TranslationApp)
    app.events = queue.Queue()
    app.events.put(('result', 1, 'old result'))
    app.generation = 2
    app.root = Mock()
    app.display = Mock()
    app.dismiss_outside = Mock()
    app.poll()
    app.display.assert_not_called()


def test_focus_change_does_not_capture_unrelated_selection(monkeypatch):
    windows = iter([1, 2])
    monkeypatch.setattr(translation, 'foreground_window', lambda: next(windows))
    read = Mock(return_value='unrelated')
    assert translation.capture_selected(read=read) is None
    read.assert_not_called()


def test_incomplete_translation_is_not_shown_as_complete():
    import pytest
    converter = translation.JapaneseTranslator('test', 'gpt-6-luna')
    converter.client = Mock()
    converter.client.responses.create.return_value = SimpleNamespace(output_text='partial', status='incomplete')
    with pytest.raises(RuntimeError):
        converter.convert('Long text')
