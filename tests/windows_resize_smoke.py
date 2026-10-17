"""Exercise border widgets and real Tk layout with synthetic prose only."""
import ctypes
import json
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from jtranslate_app.translate_app import TranslationApp

sys.stdout.reconfigure(encoding='utf-8')
app = TranslationApp()
checks = []

def check(name, value):
    assert value, name
    checks.append(name)

def rect():
    app.root.update_idletasks()
    return app.root.winfo_x(),app.root.winfo_y(),app.root.winfo_width(),app.root.winfo_height()

def gesture(edge, dx,dy):
    handle=app.resize_handles[edge]
    x,y=handle.winfo_rootx()+2,handle.winfo_rooty()+2
    handle.event_generate('<ButtonPress-1>',x=2,y=2,rootx=x,rooty=y)
    check('resize gesture active '+edge, app.resizing is not None)
    original=app.root.winfo_pointerxy
    app.root.winfo_pointerxy=lambda:(-10000,-10000)
    with patch.object(ctypes.windll,'user32',Mock(GetAsyncKeyState=lambda key:0x8000 if key==1 else 0)):
        app.dismiss_outside()
    app.root.winfo_pointerxy=original
    check('outside pointer during resize stays open '+edge,app.root.winfo_viewable())
    handle.event_generate('<B1-Motion>',x=2+dx,y=2+dy,rootx=x+dx,rooty=y+dy)
    handle.event_generate('<ButtonRelease-1>',x=2+dx,y=2+dy,rootx=x+dx,rooty=y+dy)
    app.root.update()
    check('resize gesture ended '+edge,app.resizing is None)
    check('resize mouse capture released '+edge,app.root.grab_current() is None)

try:
    app.result=('This is a long synthetic paragraph that should wrap naturally at the current popup width. ' * 80)
    app.display(app.result)
    app.root.update()
    check('eight resize edges with Windows cursors',len(app.resize_handles)==8 and
        app.resize_handles['se'].cget('cursor')=='size_nw_se' and app.resize_handles['e'].cget('cursor')=='size_we')
    app.root.geometry('540x300+100+100')
    app.root.update()
    before=rect()
    gesture('se',150,100)
    after=rect()
    check('corner enlarges width with automatic content height',after[2]>before[2] and after[3]>=100)
    app.display('New result. '+app.result)
    app.root.update()
    check('new output retains manual width',rect()[2]==after[2])
    before_lines=int(app.text.count('1.0','end','displaylines')[0])
    gesture('e',-200,0)
    after_lines=int(app.text.count('1.0','end','displaylines')[0])
    check('narrower size reflows more display lines',after_lines>before_lines)
    check('long text scrolls after resize',app.text.yview()[1]<1)
    app.text.yview_moveto(1)
    app.root.update()
    check('resized scroll reaches final text',app.text.yview()[1]==1)
    gesture('nw',10000,10000)
    check('minimum width enforced with content height',rect()[2]==320 and rect()[3]>=100)
    gesture('se',10000,10000)
    left,top,right,bottom=app.work_area()
    x,y,w,h=rect()
    check('resized popup stays within work area',left<=x and top<=y and x+w<=right and y+h<=bottom)
    app.root.geometry('640x320+100+100')
    app.root.update()
    from PIL import ImageGrab
    x,y,w,h=rect()
    ImageGrab.grab(bbox=(x,y,x+w,y+h)).save('translation-resizable-popup.png')
finally:
    app.root.destroy()

result={'passed':len(checks),'checks':checks}
Path('RESIZE-TEST-RESULTS.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
