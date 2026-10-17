"""Inspect the sign-in entry point without opening a browser or creating a grant."""
import json
from pathlib import Path
from unittest.mock import patch
from jtranslate_app.translate_app import TranslationApp
from jtranslate_app.settings_ui import open_settings
from jtranslate_app.config import data_dir, Settings

app=TranslationApp()
credential=data_dir()/'chatgpt-auth.bin'
existed=credential.exists()
try:
    with patch('jtranslate_app.chatgpt_auth.sign_in') as signin, \
            patch('jtranslate_app.chatgpt_auth.accounts',return_value=[]):
        window=open_settings(app.root)
        app.root.update()
        def texts(widget):
            value=[]
            if 'text' in widget.keys(): value.append(widget.cget('text'))
            for child in widget.winfo_children(): value.extend(texts(child))
            return value
        labels=texts(window)
        assert 'Continue with ChatGPT' in labels
        assert 'JTranslate専用のChatGPT接続' in labels
        assert any('JHenkan' in label for label in labels)
        signin.assert_not_called()
        assert credential.exists()==existed
        window.destroy()
finally:
    app.root.destroy()

result={'dedicated_signin_button':True,'shared_connection_choice':True,
        'no_browser_or_auth_grant_created':True,'credential_store_unchanged':True}
Path('SETTINGS-TEST-RESULTS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
