"""Portable per-user settings, independent of credentials belonging to other apps."""
import json
import os
import sys
from dataclasses import asdict,dataclass,field
from pathlib import Path

def data_dir():
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'JTranslate'
    return Path(os.getenv('LOCALAPPDATA',Path.home()/'AppData'/'Local'))/'JTranslate'

@dataclass
class Settings:
    provider: str = 'chatgpt'
    chatgpt_model: str = 'gpt-6-luna'
    chatgpt_account: str = ''
    reasoning_effort: str = 'none'
    reasoning_options: dict = field(default_factory=dict)
    api_timeout_seconds: float = 30.0

    @property
    def model(self): return self.chatgpt_model

    @classmethod
    def load(cls):
        try:
            raw=json.loads((data_dir()/'settings.json').read_text(encoding='utf-8'))
            if raw.get('connection_source')=='jhenkan': return cls()
            return cls(**{k:v for k,v in raw.items() if k in cls.__dataclass_fields__})
        except (OSError,ValueError,TypeError): return cls()

    def save(self):
        data_dir().mkdir(parents=True,exist_ok=True)
        (data_dir()/'settings.json').write_text(json.dumps(asdict(self),ensure_ascii=False,indent=2),encoding='utf-8')

def get_api_key(provider,account):
    if provider!='chatgpt': raise ValueError('JTranslate uses Sign in with ChatGPT')
    from . import chatgpt_auth
    return chatgpt_auth.access_token(account)
