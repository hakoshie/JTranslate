"""Synthetic result/status layout only. Never reads or writes the clipboard."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tkinter.font as tkfont
from jtranslate_app.translate_app import TranslationApp

app=TranslationApp();checks=[];fonts=[]
paragraph='This synthetic paragraph wraps naturally at the selected width. '+('\u65e5\u672c\u8a9e\u306e\u8868\u793a\u3082\u78ba\u8a8d\u3057\u307e\u3059\u3002')
def rect():
    app.root.update_idletasks()
    return app.root.winfo_x(),app.root.winfo_y(),app.root.winfo_width(),app.root.winfo_height()
def full():
    app.root.update_idletasks()
    return app.text.yview()[1]==1.0 and app.text.bbox('end-2c') is not None
def check(name,value):
    assert value,name
    checks.append(name)
try:
    with patch.object(app,'work_area',return_value=(0,40,1000,900)):
        app.user_size=(540,100)
        app.display(paragraph*12);app.root.update()
        check('old small height does not clip result',rect()[3]>100 and full())
        check('manual width retained',rect()[2]==540)
        tall=rect()[3]
        app.user_size=(540,750)
        app.display('Short synthetic result');app.root.update()
        check('short result shrinks despite old tall height',rect()[3]<tall)
        check('short result hides scrollbar',not app.scroll.winfo_ismapped())
        app.user_size=(600,100);app.display(paragraph*10);app.root.update()
        wide_height=rect()[3]
        handle=app.resize_handles['e']
        event=SimpleNamespace(widget=handle,x_root=app.root.winfo_rootx()+600,y_root=app.root.winfo_rooty()+30)
        app.resize_start(event,'e')
        narrower=SimpleNamespace(widget=handle,x_root=event.x_root-180,y_root=event.y_root)
        app.resize_end(narrower);app.root.update()
        check('width resize remeasures height',rect()[2]==420 and rect()[3]>wide_height and full())
        app.display('Another short result');app.root.update()
        check('next result retains resized width only',rect()[2]==420 and rect()[3]<wide_height)
        app.hide()
        with patch.object(app.root,'winfo_pointerxy',return_value=(980,880)):
            app.display(paragraph*14);app.root.update()
        x,y,w,h=rect()
        check('bottom edge moves popup upward',y+h<=900 and y>=40 and full())
        app.display((paragraph+'\n')*100);app.root.update()
        check('oversize result uses complete work area',rect()[3]==860)
        check('only oversize result shows scrolling',app.scroll.winfo_ismapped() and app.text.yview()[1]<1)
        app.text.yview_moveto(1);app.root.update()
        check('overflow scroll reaches final character',app.text.bbox('end-2c') is not None)
        app.display_message(paragraph*12);app.root.update()
        check('status uses same measured-height rule',rect()[2]==420 and full())
    for dpi in (96,144,192):
        app.root.tk.call('tk','scaling',dpi/72)
        font=tkfont.Font(root=app.root,family='Yu Gothic UI',size=12);fonts.append(font);app.text.configure(font=font)
        app.user_size=(540,100)
        with patch.object(app,'work_area',return_value=(0,0,1100,1000)):
            app.display(paragraph*5);app.root.update()
            check(str(dpi)+' DPI result fits actual wrapping',rect()[2]==540 and full())
    with patch.object(app,'work_area',return_value=(-900,0,0,760)):
        app.hide();app.user_size=(420,100)
        with patch.object(app.root,'winfo_pointerxy',return_value=(-10,740)):
            app.display(paragraph*5);app.root.update()
        x,y,w,h=rect()
        check('left monitor negative coordinates retained',-900<=x and x+w<=0 and y>=0 and y+h<=760)
    with patch.object(app,'work_area',return_value=(1920,30,2640,700)):
        app.hide();app.user_size=(420,100)
        with patch.object(app.root,'winfo_pointerxy',return_value=(2630,690)):
            app.display(paragraph*5);app.root.update()
        x,y,w,h=rect()
        check('right monitor taskbar work area retained',1920<=x and x+w<=2640 and 30<=y and y+h<=700)
    app.display('Synthetic in-flight status',kind='loading');app.root.update()
    check('loading does not claim Esc stops communication',app.title.cget('text')=='翻訳中')
    app.display('Completed result');app.root.update()
    check('completed result labels Esc as close','Esc' in app.title.cget('text'))
    app.root.after_idle(app.refit_if_changed)
    generation=app.generation;app.hide();app.root.update()
    check('hide invalidates result and pending refit cannot reopen',
          app.generation==generation+1 and not app.root.winfo_viewable())
    app.root.tk.call('tk','scaling',96/72)
    font=tkfont.Font(root=app.root,family='Yu Gothic UI',size=12);fonts.append(font)
    app.text.configure(font=font)
    with patch.object(app,'work_area',return_value=(0,0,1000,900)):
        app.user_size=(600,100)
        actual_update=app.root.update
        update_calls=[0]
        def resize_during_flush():
            actual_update()
            update_calls[0]+=1
            if update_calls[0]==2:
                app.root.geometry('320x100+100+100');app.user_size=(320,100)
                actual_update()
                app.fit_height()
        with patch.object(app.root,'update',side_effect=resize_during_flush):
            app.display(paragraph*7)
        app.root.update()
        check('resize during layout is eventually remeasured',rect()[2]==320 and full())
        update_calls=[0]
        def display_during_flush():
            actual_update()
            update_calls[0]+=1
            if update_calls[0]==2:
                app.display('Synthetic replacement result')
                check('reentrant display preserves outer layout guard',app._layout_active)
        with patch.object(app.root,'update',side_effect=display_during_flush):
            app.display(paragraph*7)
        app.root.update()
        check('replacement result receives final measured height',full() and rect()[3]<200)
        update_calls=[0]
        def replace_overflow_during_flush():
            actual_update()
            update_calls[0]+=1
            if update_calls[0]==2:
                app.display('Short replacement during overflow layout')
        with patch.object(app.root,'update',side_effect=replace_overflow_during_flush):
            app.display((paragraph+'\n')*100)
        app.root.update()
        check('replacement during overflow removes unnecessary scrollbar',
              full() and not app.scroll.winfo_ismapped())
finally:
    for timer in app.root.tk.call('after','info'):app.root.after_cancel(timer)
    app.quit()
report={'passed':len(checks),'checks':checks,'clipboard_touched':False,'provider_called':False}
Path('AUTOHEIGHT-TEST-RESULTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
