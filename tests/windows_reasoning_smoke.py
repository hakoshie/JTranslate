"""Real settings UI, temporary preferences, mocked authentication, fresh-process load."""
import json,os,subprocess,sys,uuid
from pathlib import Path
from unittest.mock import patch
from jtranslate_app import config
from jtranslate_app.translate_app import TranslationApp
from jtranslate_app.settings_ui import open_settings

def descendants(widget):
    yield widget
    for child in widget.winfo_children(): yield from descendants(child)

def field(window,name):
    return next(w for w in descendants(window) if w.winfo_name()==name)

def save_button(window):
    return next(w for w in descendants(window) if 'text' in w.keys() and w.cget('text')=='保存')

root=Path.cwd()/'.pytest-scratch-thinking-ui'/uuid.uuid4().hex
store=root/'JTranslate'
checks=[]
app=TranslationApp()
try:
    with patch.object(config,'data_dir',lambda:store), \
         patch('jtranslate_app.chatgpt_auth.accounts',return_value=[{'client_id':'fake-own-account','email':'test@example.invalid'}]), \
         patch('jtranslate_app.chatgpt_auth.connected',return_value=True), \
         patch('jtranslate_app.chatgpt_auth.sign_in') as signin:
        config.Settings(chatgpt_account='fake-own-account').save()
        window=open_settings(app.root);app.root.update()
        box=field(window,'reasoning_effort')
        assert tuple(box.cget('values'))==('none','low','medium','high','xhigh','max')
        assert box.get()=='none'
        checks.append('UI shows supported options and preserves none default')
        box.set('high');save_button(window).invoke();app.root.update()
        assert config.Settings.load().reasoning_effort=='high'
        checks.append('UI save stores selected high')
        env=dict(os.environ,LOCALAPPDATA=str(root))
        result=subprocess.check_output([sys.executable,'-c','from jtranslate_app.config import Settings; print(Settings.load().reasoning_effort)'],env=env,text=True)
        assert result.strip()=='high'
        checks.append('fresh process retains selected effort')
        window=open_settings(app.root);app.root.update()
        assert field(window,'reasoning_effort').get()=='high'
        checks.append('reopened UI retains selected effort')
        field(window,'reasoning_effort').set('ultra');save_button(window).invoke();app.root.update()
        assert window.winfo_exists() and config.Settings.load().reasoning_effort=='high'
        checks.append('unsupported effort cannot save and does not silently fallback')
        field(window,'model').set('unverified-model');app.root.update()
        assert str(field(window,'reasoning_effort').cget('state'))=='disabled'
        save_button(window).invoke()
        assert window.winfo_exists()
        checks.append('unknown model requires verified catalog choices')
        signin.assert_not_called();window.destroy()
finally: app.root.destroy()

# First launch without preferences or credentials explicitly opens sign-in,
# without opening a browser, generating a grant or reading another application's data.
empty=root/'new-user'/'JTranslate'
app=TranslationApp();errors=[]
with patch.object(config,'data_dir',lambda:empty), \
     patch('jtranslate_app.chatgpt_auth.connected',return_value=False), \
     patch('jtranslate_app.chatgpt_auth.accounts',return_value=[]), \
     patch('jtranslate_app.chatgpt_auth.sign_in') as signin, \
     patch('jtranslate_app.chatgpt_auth.access_token') as access, \
     patch.object(app.icon,'run_detached'),patch.object(app.icon,'stop'), \
     patch.object(app.hotkey,'start'),patch.object(app.hotkey,'stop'):
    def inspect_startup():
        try:
            window=app.settings_window
            assert window.winfo_exists()
            assert any('text' in w.keys() and w.cget('text')=='Continue with ChatGPT' for w in descendants(window))
            signin.assert_not_called();access.assert_not_called()
            assert not empty.exists()
            checks.append('new-user startup explicitly shows sign-in without automatic auth or stored settings')
        except Exception as exc: errors.append(str(exc))
        finally: app.quit()
    app.root.after(800,inspect_startup)
    app.run()
assert not errors,errors
report={'passed':len(checks),'checks':checks,'new_grants_created':False}
Path('THINKING-TEST-RESULTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
