import json
from unittest.mock import Mock
from jtranslate_app import config, chatgpt_auth


def test_legacy_fallback_does_not_create_or_copy_credentials(tmp_path,monkeypatch):
    own=tmp_path/'JTranslate'
    legacy=tmp_path/'JHenkan'
    legacy.mkdir()
    (legacy/'settings.json').write_text(json.dumps({'provider':'chatgpt','chatgpt_account':'test-account',
        'chatgpt_model':'gpt-6-luna'}),encoding='utf-8')
    monkeypatch.setattr(config,'data_dir',lambda:own)
    result=config.Settings.load()
    assert result.connection_source=='jhenkan'
    assert result.model=='gpt-6-luna'
    assert not own.exists()


def test_dedicated_settings_are_separate_from_legacy(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path/'JTranslate')
    config.Settings(chatgpt_account='new-test-account').save()
    assert config.Settings.load().connection_source=='jtranslate'
    assert not (tmp_path/'JHenkan').exists()


def test_existing_connection_and_dedicated_auth_are_routed_separately(monkeypatch):
    legacy=Mock()
    legacy.access_token.return_value='test-shared'
    monkeypatch.setattr(config,'legacy_auth',lambda:legacy)
    own=Mock(return_value='test-own')
    monkeypatch.setattr(chatgpt_auth,'access_token',own)
    assert config.get_api_key('chatgpt','shared-account','jhenkan')=='test-shared'
    own.assert_not_called()
    assert config.get_api_key('chatgpt','own-account','jtranslate')=='test-own'
    own.assert_called_once_with('own-account')


def test_new_install_defaults_to_own_login_without_registering(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path/'JTranslate')
    signin=Mock()
    monkeypatch.setattr(chatgpt_auth,'sign_in',signin)
    assert config.Settings.load().connection_source=='jtranslate'
    signin.assert_not_called()
    assert not (tmp_path/'JTranslate').exists()
