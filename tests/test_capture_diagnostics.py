import json
import queue
import threading
from contextlib import nullcontext
from unittest.mock import Mock
import pytest
from jtranslate_app import capture_diagnostics as diagnostics,translation
from jtranslate_app.capture_errors import CaptureFailure,MESSAGES
from jtranslate_app.browser_clipboard import ClipboardCapture
from jtranslate_app.translate_app import TranslationApp

def entries():
    path=diagnostics.data_dir()/'selection-diagnostics.log'
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]

def test_diagnostics_drop_text_credentials_urls_and_exception_messages():
    private='PRIVATE_SOURCE_TEXT_DO_NOT_LOG'
    diagnostics.record('capture_failed',code='clipboard_busy',text=private,token=private,
        url=private,error_message=private,status=private)
    raw=(diagnostics.data_dir()/'selection-diagnostics.log').read_text(encoding='utf-8')
    assert private not in raw
    assert entries()[0]['code']=='clipboard_busy'
    assert set(entries()[0])=={'time','event','code'}

def test_startup_has_loaded_code_fingerprint_and_revision():
    diagnostics.startup()
    row=entries()[0]
    assert row['revision']==4 and len(row['signature'])==12
    assert row['event']=='startup'

def test_diagnostics_are_bounded():
    path=diagnostics.data_dir()/'selection-diagnostics.log'
    path.parent.mkdir(parents=True)
    path.write_text((json.dumps({'event':'uia','status':'empty'})+'\n')*3000,encoding='utf-8')
    diagnostics.record('uia',status='selected')
    assert path.stat().st_size<65536
    assert entries()[-1]['status']=='selected'

def test_capture_error_is_specific_and_never_reads_credentials(monkeypatch):
    from jtranslate_app import translate_app
    app=TranslationApp.__new__(TranslationApp)
    app.events=queue.Queue();app.busy=threading.Lock();app.busy.acquire()
    monkeypatch.setattr(translate_app,'capture_selected',Mock(side_effect=CaptureFailure('clipboard_preserve')))
    credentials=Mock(side_effect=AssertionError('must not read credentials'))
    monkeypatch.setattr(translate_app,'get_api_key',credentials)
    app.worker(1)
    assert app.events.get_nowait()==('message',1,MESSAGES['clipboard_preserve'])
    assert entries()[-1]['code']=='clipboard_preserve'
    assert not app.busy.locked()
    credentials.assert_not_called()

def test_waits_for_m_as_well_as_control_release(monkeypatch):
    states=iter([{'ctrl_down':True,'m_down':True},
                 {'ctrl_down':False,'m_down':True},
                 {'ctrl_down':False,'m_down':False}])
    monkeypatch.setattr(diagnostics,'hotkey_state',lambda:next(states))
    sleep=Mock();monkeypatch.setattr(translation.time,'sleep',sleep)
    translation._wait_for_hotkey_release()
    assert sleep.call_count==2
    assert entries()[-1]['m_down'] is False

def test_stuck_m_key_aborts_before_copy(monkeypatch):
    monkeypatch.setattr(diagnostics,'hotkey_state',lambda:{'ctrl_down':False,'m_down':True})
    with pytest.raises(CaptureFailure) as failure:translation._wait_for_hotkey_release(timeout=0)
    assert failure.value.code=='hotkey_not_released'

def test_uia_timeout_gets_its_own_safe_category(monkeypatch):
    monkeypatch.setattr(translation.subprocess,'run',Mock(side_effect=translation.subprocess.TimeoutExpired('test',10)))
    with pytest.raises(CaptureFailure) as failure:translation.read_uia_selection()
    assert failure.value.code=='uia_timeout'

def test_missing_clipboard_owner_is_distinct_from_foreign_copy():
    capture=ClipboardCapture.__new__(ClipboardCapture)
    capture.sequence=10;capture.window=42;capture.opened=lambda:nullcontext()
    capture.user=Mock();capture.user.GetClipboardSequenceNumber.return_value=11
    capture.user.GetClipboardOwner.return_value=None
    with pytest.raises(CaptureFailure) as failure:capture.fresh_text(123)
    assert failure.value.code=='copy_owner_missing'
    assert entries()[-1]['owner']=='missing'
    capture.user.GetClipboardData.assert_not_called()


def test_loaded_signature_is_stable_across_processes():
    import subprocess,sys
    result=subprocess.check_output([sys.executable,'-c',
        'from jtranslate_app.capture_diagnostics import loaded_signature; print(loaded_signature())'],text=True)
    assert result.strip()==diagnostics.loaded_signature()
