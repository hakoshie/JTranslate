"""Synthetic error layout only: no clipboard, hotkey input, browser, or provider calls."""
import json
from pathlib import Path
from unittest.mock import patch
import tkinter.font as tkfont
from jtranslate_app.translate_app import TranslationApp

app=TranslationApp()
app.dismiss_outside=lambda:None
checks=[]
message='Synthetic selection error. '+('\u9078\u629e\u6587\u3092\u53d6\u5f97\u3067\u304d\u307e\u305b\u3093\u3067\u3057\u305f\u3002\u672c\u6587\u3092\u9078\u629e\u3057\u3066\u3082\u3046\u4e00\u5ea6\u304a\u8a66\u3057\u304f\u3060\u3055\u3044\u3002')
fonts=[]
def show(text):
    app.events.put(('message',app.generation,text))
    app.poll();app.root.update()
try:
    app.user_size=(320,100)
    with patch.object(app,'work_area',return_value=(0,0,1000,800)):
        show(message)
        assert app.root.winfo_width()>=440,'error must expand small saved width'
        assert app.root.winfo_height()>100,'error must expand small saved height'
        assert app.text.yview()[1]==1.0,'short error must fit without scrolling'
        assert app.text.bbox('end-2c') is not None,'last error character must be visible'
        assert app.user_size==(320,100),'automatic error expansion must preserve translation preference'
        checks.extend(['small saved size expanded','short error fully visible','translation size preserved'])
        app.display('Synthetic translation')
        app.root.update()
        assert (app.root.winfo_width(),app.root.winfo_height())==(320,100)
        checks.append('translation returns to manual size')
    for dpi in (96,144,192):
        app.root.tk.call('tk','scaling',dpi/72)
        font=tkfont.Font(root=app.root,family='Yu Gothic UI',size=12)
        fonts.append(font);app.text.configure(font=font)
        with patch.object(app,'work_area',return_value=(0,0,1100,850)):
            show(message)
            assert app.text.yview()[1]==1.0,(dpi,'error clipped at DPI')
            box=app.text.bbox('end-2c');assert box is not None
            assert box[1]+box[3]<=app.text.winfo_height()
            checks.append(str(dpi)+' DPI measured wrapping fits')
    with patch.object(app,'work_area',return_value=(0,0,360,240)):
        show((message+'\n')*40)
        assert app.root.winfo_width()<=360 and app.root.winfo_height()<=240
        assert app.text.yview()[1]<1.0
        app.text.yview_moveto(1);app.root.update()
        assert app.text.bbox('end-2c') is not None
        checks.extend(['narrow work area bounded','long error scrolls to final character'])
finally:
    for timer in app.root.tk.call('after','info'):app.root.after_cancel(timer)
    app.quit()
report={'passed':len(checks),'checks':checks,'clipboard_touched':False,'browser_operated':False}
Path('ERROR-LAYOUT-TEST-RESULTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
