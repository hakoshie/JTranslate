import pytest
from jtranslate_app import capture_diagnostics

@pytest.fixture(autouse=True)
def isolate_capture_diagnostics(monkeypatch,tmp_path):
    monkeypatch.setattr(capture_diagnostics,'data_dir',lambda:tmp_path/'diagnostics')
    monkeypatch.setattr(capture_diagnostics,'hotkey_state',lambda:{'ctrl_down':False,'m_down':False})
