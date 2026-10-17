"""Responses reasoning options; other models require account-catalog metadata.

Luna source: https://developers.openai.com/api/docs/models/gpt-6-luna
"""
EFFORTS=('none','minimal','low','medium','high','xhigh','max')
LUNA_EFFORTS=('none','low','medium','high','xhigh','max')

class ReasoningConfigurationError(ValueError):
    pass

def supported_efforts(model,metadata=None):
    if model=='gpt-6-luna': return LUNA_EFFORTS
    if metadata is None: return ()
    return tuple(value for value in EFFORTS if value in metadata)

def validate_effort(model,effort,metadata=None):
    choices=supported_efforts(model,metadata)
    if not choices:
        raise ReasoningConfigurationError('このモデルのThinking levelは未確認です。設定でモデル一覧を読み込んでください。')
    if effort not in choices:
        raise ReasoningConfigurationError('このモデルに対応しないThinking levelです。設定画面で選び直してください。')
    return effort
