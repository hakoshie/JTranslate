from contextlib import contextmanager,nullcontext
from unittest.mock import Mock
import pytest
from jtranslate_app import browser_clipboard as module
from jtranslate_app.capture_errors import CaptureFailure

def test_pump_runs_even_when_no_queued_message_exists():
    user=Mock();user.PeekMessageW.return_value=0
    module._pump_window_messages(user,42)
    user.PeekMessageW.assert_called_once()
    user.DispatchMessageW.assert_not_called()

def test_pump_is_bounded_for_posted_messages():
    user=Mock();user.PeekMessageW.return_value=1
    module._pump_window_messages(user,42)
    assert user.DispatchMessageW.call_count==16

def test_copy_wait_services_owner_notifications(monkeypatch):
    capture=Mock()
    capture.__enter__=Mock(return_value=capture)
    capture.__exit__=Mock(return_value=False)
    capture.fresh_text.side_effect=[None,'Synthetic selected text']
    monkeypatch.setattr(module,'ClipboardCapture',lambda:capture)
    monkeypatch.setattr(module,'browser_process',lambda window:123)
    monkeypatch.setattr(module.time,'sleep',lambda seconds:None)
    send=Mock()
    assert module.copy_browser_selection(window=42,foreground=lambda:42,send=send)=='Synthetic selected text'
    assert capture.pump_messages.call_count>=2
    send.assert_called_once_with()

def test_busy_restore_retains_original_handles_instead_of_freeing_them():
    capture=module.ClipboardCapture.__new__(module.ClipboardCapture)
    capture.restored=False;capture.deferred=False;capture.window=42;capture.sequence=10
    capture.handles=[(13,1234)]
    @contextmanager
    def busy():
        raise CaptureFailure('clipboard_busy')
        yield
    capture.opened=busy;capture.user=Mock();capture.user.GetClipboardOwner.return_value=42
    capture.defer_restore=Mock(side_effect=lambda:setattr(capture,'deferred',True))
    capture.cleanup=Mock()
    with pytest.raises(CaptureFailure) as failure:capture.__exit__(None,None,None)
    assert failure.value.code=='clipboard_restore_pending'
    assert capture.handles==[(13,1234)]
    capture.defer_restore.assert_called_once_with()
    capture.cleanup.assert_not_called()

def pending_capsule(owner,text):
    capture=module.ClipboardCapture.__new__(module.ClipboardCapture)
    capture.window=42;capture._old_owner=24;capture.marker='Unique synthetic marker'
    capture.opened=lambda:nullcontext()
    capture.user=Mock();capture.user.GetClipboardOwner.return_value=owner
    capture.read_unicode_locked=Mock(return_value=text)
    capture.restore_locked=Mock()
    return capture

def test_delayed_restore_only_accepts_its_exact_marker():
    capture=pending_capsule(None,'Unique synthetic marker')
    assert capture.try_pending_restore()=='restored'
    capture.restore_locked.assert_called_once_with()

def test_delayed_restore_does_not_read_or_overwrite_foreign_owner():
    capture=pending_capsule(99,'New user copy')
    assert capture.try_pending_restore()=='superseded'
    capture.read_unicode_locked.assert_not_called()
    capture.restore_locked.assert_not_called()

def test_delayed_restore_preserves_new_copy_with_no_owner_window():
    capture=pending_capsule(None,'New user copy')
    assert capture.try_pending_restore()=='superseded'
    capture.restore_locked.assert_not_called()

def test_pending_recovery_blocks_another_clipboard_capture(monkeypatch):
    monkeypatch.setattr(module,'browser_process',lambda window:123)
    constructor=Mock(side_effect=AssertionError('must not replace clipboard during recovery'))
    monkeypatch.setattr(module,'ClipboardCapture',constructor)
    module._recovery_pending.set()
    try:
        with pytest.raises(CaptureFailure) as failure:
            module.copy_browser_selection(window=42,foreground=lambda:42)
        assert failure.value.code=='clipboard_restore_pending'
    finally:module._recovery_pending.clear()
    constructor.assert_not_called()


def test_recovery_waits_for_a_valid_owner_window_before_clipboard_access(monkeypatch):
    capture=module.ClipboardCapture.__new__(module.ClipboardCapture)
    capture.window=24;capture.deferred=False
    capture.user=Mock();capture.user.CreateWindowExW.side_effect=[None,42]
    capture.try_pending_restore=Mock(return_value='restored')
    capture.cleanup=Mock()
    monkeypatch.setattr(module.time,'sleep',Mock())
    def thread_factory(*,target,**kwargs):
        thread=Mock();thread.start.side_effect=target;return thread
    monkeypatch.setattr(module.threading,'Thread',thread_factory)
    capture.defer_restore()
    assert capture.user.CreateWindowExW.call_count==2
    capture.try_pending_restore.assert_called_once_with()
    capture.cleanup.assert_called_once_with()
    assert not module._recovery_pending.is_set()
