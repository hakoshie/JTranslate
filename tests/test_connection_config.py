import json
from unittest.mock import Mock
from jtranslate_app import config,chatgpt_auth

def test_other_apps_settings_are_never_used(tmp_path,monkeypatch):
    legacy=tmp_path/'JHenkan';legacy.mkdir()
    original=json.dumps({'provider':'chatgpt','chatgpt_account':'other-app-account','chatgpt_model':'other-model'})
    (legacy/'settings.json').write_text(original,encoding='utf-8')
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path/'JTranslate')
    s=config.Settings.load()
    assert s.chatgpt_account=='' and s.model=='gpt-6-luna' and s.reasoning_effort=='none'
    assert (legacy/'settings.json').read_text(encoding='utf-8')==original
    assert not (tmp_path/'JTranslate').exists()

def test_old_sharing_override_does_not_select_foreign_credentials(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path)
    (tmp_path/'settings.json').write_text(json.dumps({'connection_source':'jhenkan','chatgpt_account':'other-app-account'}))
    assert config.Settings.load().chatgpt_account==''

def test_only_own_authentication_is_called(monkeypatch):
    access=Mock(return_value='fake-test-token')
    monkeypatch.setattr(chatgpt_auth,'access_token',access)
    assert config.get_api_key('chatgpt','own-test-account')=='fake-test-token'
    access.assert_called_once_with('own-test-account')

def test_new_install_does_not_register_or_save_automatically(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path/'JTranslate')
    signin=Mock();monkeypatch.setattr(chatgpt_auth,'sign_in',signin)
    assert config.Settings.load().chatgpt_account==''
    signin.assert_not_called()
    assert not (tmp_path/'JTranslate').exists()
