"""Exercise real Tk right-click bindings with synthetic text, without moving the pointer."""
import json,sys,uuid,ctypes
from pathlib import Path
from unittest.mock import patch
import pyperclip
from windows_clipboard_test_support import ClipboardSnapshot
from jtranslate_app.translate_app import TranslationApp

app=TranslationApp()
snapshot=ClipboardSnapshot();snapshot.__enter__()
checks=[]
result=('Synthetic full translation '+uuid.uuid4().hex+' \u65e5\u672c\u8a9e\U0001f30f\n')*1000
pyperclip.paste()  # Resolve pyperclip lazy backend before wrapping its copy function.
copy=pyperclip.copy
try:
    # Use a visible native window so Windows delivers pointer events normally.
    app.root.geometry('540x200+100+100')
    app.root.deiconify();app.root.update()
    app.result=result
    app.text.configure(state='normal');app.text.insert('1.0',result);app.text.configure(state='disabled')
    app.root.update()
    with patch('jtranslate_app.translate_app.pyperclip.copy',wraps=copy) as copied:
        app.text.event_generate('<Button-3>',x=20,y=20,time=ctypes.windll.kernel32.GetTickCount())
        app.text.event_generate('<ButtonRelease-3>',x=20,y=20,time=ctypes.windll.kernel32.GetTickCount());app.root.update()
        assert copied.call_count==1
        assert pyperclip.paste()==result
        checks.extend(['one text right-click dispatches one copy','entire Unicode result copied'])
        assert app.root.winfo_viewable()
        checks.append('right-click keeps popup open')
        app.text.yview_moveto(1);app.root.update()
        app.text.event_generate('<Button-3>',x=20,y=20,time=ctypes.windll.kernel32.GetTickCount())
        app.text.event_generate('<ButtonRelease-3>',x=20,y=20,time=ctypes.windll.kernel32.GetTickCount());app.root.update()
        assert copied.call_count==2 and pyperclip.paste()==result
        checks.append('scrolled result still copies entire text')
        app.root.event_generate('<Button-3>',x=10,y=10,time=ctypes.windll.kernel32.GetTickCount())
        app.root.event_generate('<ButtonRelease-3>',x=10,y=10,time=ctypes.windll.kernel32.GetTickCount());app.root.update()
        assert copied.call_count==3
        checks.append('one background right-click copies once')
        app.result=''
        app.text.event_generate('<Button-3>',x=20,y=20,time=ctypes.windll.kernel32.GetTickCount())
        app.text.event_generate('<ButtonRelease-3>',x=20,y=20,time=ctypes.windll.kernel32.GetTickCount());app.root.update()
        assert copied.call_count==3
        checks.append('empty/loading result does not copy')
    app.hide();assert not app.root.winfo_viewable()
    checks.append('hide still closes popup')
finally:
    # Restore only our synthetic clipboard result; a newer user copy wins.
    if pyperclip.paste()==result:snapshot.__exit__(None,None,None)
    else:snapshot.cleanup()
    app.quit()
report={'passed':len(checks),'checks':checks,'os_pointer_moved':False,'browser_operated':False}
Path('RIGHTCLICK-TEST-RESULTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
