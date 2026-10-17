from unittest.mock import Mock
from jtranslate_app import translation
from jtranslate_app.translate_app import TranslationApp

def test_browser_empty_uia_can_use_fresh_copy(monkeypatch):
    monkeypatch.setattr(translation,'read_native_edit',lambda:None)
    monkeypatch.setattr(translation,'read_uia_selection',lambda:{'status':'selected','text':'','copy_safe':True})
    copy=Mock(return_value='public browser selection')
    monkeypatch.setattr(translation,'copy_browser_selection',copy)
    assert translation.read_selection()=='public browser selection'
    copy.assert_called_once()

def test_password_never_uses_browser_copy(monkeypatch):
    monkeypatch.setattr(translation,'read_native_edit',lambda:None)
    monkeypatch.setattr(translation,'read_uia_selection',lambda:{'status':'blocked','text':''})
    copy=Mock(side_effect=AssertionError('must not copy'))
    monkeypatch.setattr(translation,'copy_browser_selection',copy)
    assert translation.read_selection()==''

def test_right_click_directly_copies_full_result():
    app=TranslationApp.__new__(TranslationApp)
    app.result="complete result"
    app.copy_result=Mock()
    app.menu=Mock()
    assert app.copy_on_right_click(Mock())=='break'
    app.copy_result.assert_called_once_with()
    app.menu.tk_popup.assert_not_called()


def test_editable_empty_uia_never_falls_back_to_copy(monkeypatch):
    monkeypatch.setattr(translation,'read_native_edit',lambda:None)
    monkeypatch.setattr(translation,'read_uia_selection',lambda:{'status':'selected','text':'','copy_safe':False})
    copy=Mock(side_effect=AssertionError('must not copy an unselected editor line'))
    monkeypatch.setattr(translation,'copy_browser_selection',copy)
    assert translation.read_selection()==''


def test_existing_uia_selection_never_touches_clipboard(monkeypatch):
    monkeypatch.setattr(translation,'read_native_edit',lambda:None)
    monkeypatch.setattr(translation,'read_uia_selection',lambda:{'status':'selected','text':'Selected Unicode \u65e5\u672c\u8a9e','copy_safe':True})
    monkeypatch.setattr(translation,'copy_browser_selection',Mock(side_effect=AssertionError('must not copy')))
    assert translation.read_selection()=='Selected Unicode \u65e5\u672c\u8a9e'


def test_hotkey_records_original_window(monkeypatch):
    import queue,threading
    from jtranslate_app import translate_app
    app=TranslationApp.__new__(TranslationApp)
    app.closed=app.paused=False
    app.busy=threading.Lock()
    app.events=queue.Queue()
    monkeypatch.setattr(translate_app,'foreground_window',lambda:42)
    app.request()
    assert app.events.get_nowait()==('begin',42)


def test_changed_window_before_worker_never_reads_selection(monkeypatch):
    monkeypatch.setattr(translation,'foreground_window',lambda:99)
    monkeypatch.setattr(translation,'_wait_for_hotkey_release',lambda:None)
    read=Mock(side_effect=AssertionError('must not read another window'))
    assert translation.capture_selected(read=read,expected_window=42) is None


def test_right_click_copies_entire_long_result(monkeypatch):
    from jtranslate_app import translate_app
    app=TranslationApp.__new__(TranslationApp)
    app.result=('Full Unicode result \u65e5\u672c\u8a9e\U0001f30f\n'*3000)
    copy=Mock()
    monkeypatch.setattr(translate_app.pyperclip,'copy',copy)
    assert app.copy_on_right_click(Mock())=='break'
    copy.assert_called_once_with(app.result)


def test_right_click_on_loading_or_error_never_copies(monkeypatch):
    from jtranslate_app import translate_app
    app=TranslationApp.__new__(TranslationApp)
    app.result=''
    copy=Mock()
    monkeypatch.setattr(translate_app.pyperclip,'copy',copy)
    app.copy_on_right_click(Mock())
    copy.assert_not_called()


def test_temporary_marker_restores_even_if_windows_updates_sequence():
    from contextlib import nullcontext
    from jtranslate_app.browser_clipboard import ClipboardCapture
    capture=ClipboardCapture.__new__(ClipboardCapture)
    capture.restored=False
    capture.deferred=False
    capture.sequence=10
    capture.window=42
    capture.opened=lambda:nullcontext()
    capture.user=Mock()
    capture.user.GetClipboardSequenceNumber.return_value=11
    capture.user.GetClipboardOwner.return_value=42
    capture.restore_locked=Mock()
    capture.cleanup=Mock()
    capture.__exit__(None,None,None)
    capture.restore_locked.assert_called_once_with()


def test_new_foreign_clipboard_is_never_overwritten_by_snapshot():
    from contextlib import nullcontext
    from jtranslate_app.browser_clipboard import ClipboardCapture
    capture=ClipboardCapture.__new__(ClipboardCapture)
    capture.restored=False
    capture.deferred=False
    capture.sequence=10
    capture.window=42
    capture.opened=lambda:nullcontext()
    capture.user=Mock()
    capture.user.GetClipboardSequenceNumber.return_value=11
    capture.user.GetClipboardOwner.return_value=99
    capture.restore_locked=Mock()
    capture.cleanup=Mock()
    capture.__exit__(None,None,None)
    capture.restore_locked.assert_not_called()


def test_atomic_restore_does_not_reopen_clipboard_later():
    from jtranslate_app.browser_clipboard import ClipboardCapture
    capture=ClipboardCapture.__new__(ClipboardCapture)
    capture.restored=True
    capture.deferred=False
    capture.opened=Mock(side_effect=AssertionError('do not overwrite a subsequent user copy'))
    capture.cleanup=Mock()
    capture.__exit__(None,None,None)
    capture.cleanup.assert_called_once_with()


def test_clipboard_unicode_ignores_padding_after_aligned_terminator():
    from jtranslate_app.browser_clipboard import _decode_unicode
    value='Selected \u65e5\u672c\u8a9e\U0001f30f'
    assert _decode_unicode((value+'\0').encode('utf-16-le')+b'\x00\xd8')==value


def test_clipboard_unicode_does_not_split_on_unaligned_zero_bytes():
    from jtranslate_app.browser_clipboard import _decode_unicode
    assert _decode_unicode('abc\0'.encode('utf-16-le'))=='abc'


def test_malformed_clipboard_text_is_rejected():
    import pytest
    from jtranslate_app.browser_clipboard import _decode_unicode
    with pytest.raises(ValueError):_decode_unicode('no terminator'.encode('utf-16-le'))
