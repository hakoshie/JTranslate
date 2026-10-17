from types import SimpleNamespace
from unittest.mock import patch
import pytest
from jtranslate_app import config
from jtranslate_app.converter import JapaneseConverter
from jtranslate_app.reasoning import supported_efforts, ReasoningConfigurationError


def test_luna_responses_options_match_documented_capability():
    assert supported_efforts('gpt-6-luna') == ('none','low','medium','high','xhigh','max')
    assert supported_efforts('unknown-model') == ()


@pytest.mark.parametrize('effort',['none','low','medium','high','xhigh','max'])
def test_chatgpt_sends_exact_selected_effort(effort):
    events=[SimpleNamespace(type='response.output_text.delta',delta='翻訳'),SimpleNamespace(type='response.completed')]
    with patch('jtranslate_app.converter.OpenAI') as api:
        request=api.return_value.responses.create
        request.return_value.__enter__.return_value=iter(events)
        c=JapaneseConverter('fake','gpt-6-luna',provider='chatgpt',reasoning_effort=effort)
        assert c.convert('test')=='翻訳'
        assert request.call_args.kwargs['reasoning']=={'effort':effort}


def test_unsupported_effort_never_silently_changes_or_calls_api():
    with patch('jtranslate_app.converter.OpenAI') as api:
        with pytest.raises(ReasoningConfigurationError):
            JapaneseConverter('fake','gpt-6-luna',reasoning_effort='ultra')
        api.assert_not_called()


def test_unknown_model_requires_explicit_catalog_capabilities():
    assert supported_efforts('another-model',['low','high'])==('low','high')
    with pytest.raises(ReasoningConfigurationError):
        JapaneseConverter('fake','another-model',reasoning_effort='none',supported_reasoning_efforts=['low','high'])


def test_effort_survives_save_and_fresh_load(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path)
    s=config.Settings(reasoning_effort='high',reasoning_options={'another-model':['low','high']})
    s.save()
    loaded=config.Settings.load()
    assert loaded.reasoning_effort=='high'
    assert loaded.reasoning_options=={'another-model':['low','high']}


def test_default_is_still_none(tmp_path,monkeypatch):
    monkeypatch.setattr(config,'data_dir',lambda:tmp_path/'new')
    assert config.Settings.load().reasoning_effort=='none'
