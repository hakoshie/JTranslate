import os
import ctypes
from contextlib import contextmanager
from unittest.mock import Mock
import pyperclip
import pytest
from jtranslate_app import browser_clipboard as module
from windows_clipboard_test_support import ClipboardSnapshot

@pytest.fixture
def saved_clipboard():
    snapshot=ClipboardSnapshot()
    try:snapshot.__enter__()
    except OSError:pytest.skip('Current clipboard cannot be safely preserved for this native test')
    try:yield
    finally:snapshot.__exit__(None,None,None)

@pytest.fixture
def browser_writer():
    helper=module.ClipboardCapture()
    helper.window=helper.user.CreateWindowExW(0,'STATIC','Synthetic browser owner',0,0,0,0,0,None,None,None,None)
    def write(text):
        with helper.opened():
            helper.user.EmptyClipboard()
            helper.put(13,(text+'\0').encode('utf-16-le'))
    try:yield write
    finally:helper.cleanup()

def prepare(monkeypatch):
    monkeypatch.setattr(module,'browser_process',lambda window:os.getpid())

def test_unchanged_clipboard_is_never_selected(monkeypatch,saved_clipboard):
    prepare(monkeypatch);pyperclip.copy('Unrelated synthetic clipboard')
    with pytest.raises(module.CaptureFailure) as failure:
        module.copy_browser_selection(window=42,foreground=lambda:42,send=lambda:None,timeout=.04)
    assert failure.value.code=='copy_timeout'
    assert pyperclip.paste()=='Unrelated synthetic clipboard'

def test_fresh_copy_can_equal_original_text(monkeypatch,saved_clipboard,browser_writer):
    prepare(monkeypatch);pyperclip.copy('Same synthetic selection')
    value=module.copy_browser_selection(window=42,foreground=lambda:42,
        send=lambda:browser_writer('Same synthetic selection'),timeout=.1)
    assert value=='Same synthetic selection'
    assert pyperclip.paste()=='Same synthetic selection'

def test_copy_restores_plain_text_and_html(monkeypatch,saved_clipboard,browser_writer):
    prepare(monkeypatch)
    helper=module.ClipboardCapture()
    helper.window=helper.user.CreateWindowExW(0,'STATIC','Synthetic test owner',0,0,0,0,0,None,None,None,None)
    html=helper.user.RegisterClipboardFormatW('HTML Format')
    try:
        with helper.opened():
            helper.user.EmptyClipboard()
            helper.put(13,'Original synthetic text\0'.encode('utf-16-le'))
            helper.put(html,b'<p>Synthetic HTML</p>\0')
        value=module.copy_browser_selection(window=42,foreground=lambda:42,
            send=lambda:browser_writer('Selected Unicode \u65e5\u672c\u8a9e \U0001f30f'),timeout=.1)
        assert value=='Selected Unicode \u65e5\u672c\u8a9e \U0001f30f'
        assert pyperclip.paste()=='Original synthetic text'
        with helper.opened():
            handle=helper.user.GetClipboardData(html)
            pointer=helper.kernel.GlobalLock(handle)
            try:assert ctypes.string_at(pointer)==b'<p>Synthetic HTML</p>'
            finally:helper.kernel.GlobalUnlock(handle)
    finally:helper.cleanup()

def test_foreign_copy_wins_without_translating_it(monkeypatch,saved_clipboard):
    monkeypatch.setattr(module,'browser_process',lambda window:os.getpid()+100000)
    pyperclip.copy('Original synthetic text')
    with pytest.raises(module.CaptureFailure,match='clipboard_changed'):
        module.copy_browser_selection(window=42,foreground=lambda:42,
            send=lambda:pyperclip.copy('Concurrent synthetic copy'),timeout=.1)
    assert pyperclip.paste()=='Concurrent synthetic copy'

def test_focus_change_aborts_and_restores(monkeypatch,saved_clipboard):
    prepare(monkeypatch);pyperclip.copy('Original synthetic text')
    current=[42]
    assert module.copy_browser_selection(window=42,foreground=lambda:current[0],
        send=lambda:current.__setitem__(0,99),timeout=.1) is None
    assert pyperclip.paste()=='Original synthetic text'

def test_non_browser_never_touches_clipboard(monkeypatch):
    monkeypatch.setattr(module,'browser_process',lambda window:None)
    snapshot=Mock(side_effect=AssertionError('must not touch clipboard'))
    monkeypatch.setattr(module,'ClipboardCapture',snapshot)
    assert module.copy_browser_selection(window=42,foreground=lambda:42) is None

def test_concurrent_capture_is_ignored(monkeypatch):
    prepare(monkeypatch)
    with module._capture_lock:
        assert module.copy_browser_selection(window=42,foreground=lambda:42) is None
