"""JTranslate settings; compatibility reads never migrate JHenkan credentials."""
import importlib.util
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


def data_dir():
    return Path(os.getenv('LOCALAPPDATA',Path.home()/'AppData'/'Local'))/'JTranslate'


def legacy_data_dir():
    return data_dir().with_name('JHenkan')


def legacy_auth():
    name='jtranslate_app._legacy_auth'
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name('chatgpt_auth.py'))
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.data_dir=legacy_data_dir
        sys.modules[name]=module
    return sys.modules[name]


@dataclass
class Settings:
    provider: str = 'chatgpt'
    chatgpt_model: str = 'gpt-6-luna'
    chatgpt_account: str = ''
    connection_source: str = 'jtranslate'
    reasoning_effort: str = 'none'
    api_timeout_seconds: float = 30.0

    @property
    def model(self):
        return self.chatgpt_model

    @classmethod
    def load(cls):
        path=data_dir()/'settings.json'
        try:
            raw=json.loads(path.read_text(encoding='utf-8'))
            settings=cls(**{k:v for k,v in raw.items() if k in cls.__dataclass_fields__})
            if settings.connection_source not in ('jtranslate','jhenkan'):
                settings.connection_source='jtranslate'
            return settings
        except (OSError,ValueError,TypeError):
            pass
        try:
            raw=json.loads((legacy_data_dir()/'settings.json').read_text(encoding='utf-8'))
            if raw.get('provider')=='chatgpt' and raw.get('chatgpt_account'):
                return cls(chatgpt_account=raw['chatgpt_account'],chatgpt_model=raw.get('chatgpt_model','gpt-6-luna'),
                    reasoning_effort=raw.get('reasoning_effort','none'),connection_source='jhenkan')
        except (OSError,ValueError,TypeError):
            pass
        return cls()

    def save(self):
        data_dir().mkdir(parents=True,exist_ok=True)
        (data_dir()/'settings.json').write_text(json.dumps(asdict(self),ensure_ascii=False,indent=2),encoding='utf-8')


def get_api_key(provider,account,connection_source='jtranslate'):
    if provider!='chatgpt':
        raise ValueError('JTranslate uses Sign in with ChatGPT')
    if connection_source=='jhenkan':
        return legacy_auth().access_token(account)
    from . import chatgpt_auth
    return chatgpt_auth.access_token(account)
