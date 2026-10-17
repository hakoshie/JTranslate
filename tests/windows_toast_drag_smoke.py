"""Own synthetic popup only; no clipboard access or translation requests."""
import ctypes,json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tkinter.font as tkfont
from jtranslate_app.translate_app import TranslationApp

app=TranslationApp();checks=[];fonts=[]
def check(name,value):
    assert value,name
    checks.append(name)
def drag_event(widget,kind,x,y):
    widget.event_generate(kind,x=4,y=4,rootx=x,rooty=y);app.root.update()
def position():return app.root.winfo_x(),app.root.winfo_y()
def show_loading():
    app.result='';app.display('Synthetic translation in progress…',kind='loading');app.root.update()
try:
    with patch.object(app,'work_area',return_value=(0,0,1100,900)):
        app.busy.acquire()
        show_loading();app.root.geometry('540x120+100+100');app.root.update()
        x,y=app.header.winfo_rootx()+4,app.header.winfo_rooty()+4
        drag_event(app.header,'<ButtonPress-1>',x,y)
        check('loading header captures drag while worker busy',app.busy.locked() and app.dragging and app.root.grab_current() is app.header)
        drag_event(app.header,'<B1-Motion>',x+50,y+30)
        check('loading header moves popup',position()==(150,130))
        app.mouse_down=False
        with patch.object(app.root,'winfo_pointerxy',return_value=(-10000,-10000)),patch.object(ctypes.windll.user32,'GetAsyncKeyState',side_effect=lambda key:0x8000 if key==1 else 0):app.dismiss_outside()
        check('fast drag outside initial bounds is not dismissed',app.root.winfo_viewable())
        app.result='Synthetic completed translation'
        app.display(app.result);app.root.update()
        check('result update preserves moved position and active capture',position()==(150,130) and app.dragging and app.root.grab_current() is app.header)
        drag_event(app.header,'<B1-Motion>',x+60,y+40)
        drag_event(app.header,'<ButtonRelease-1>',x+60,y+40)
        check('drag continues across completion and releases capture',position()==(160,140) and not app.dragging and app.root.grab_current() is None)
        show_loading()
        x,y=app.text.winfo_rootx()+8,app.text.winfo_rooty()+8
        before=position()
        drag_event(app.text,'<ButtonPress-1>',x,y)
        drag_event(app.text,'<B1-Motion>',x+20,y+20)
        drag_event(app.text,'<ButtonRelease-1>',x+20,y+20)
        check('loading message provides safe drag area',position()==(before[0]+20,before[1]+20) and not app.dragging)
        app.result='Result text stays selectable';app.display(app.result);app.root.update()
        before=position();width=app.root.winfo_width()
        handle=app.resize_handles['e']
        start=SimpleNamespace(widget=handle,x_root=app.root.winfo_rootx()+width,y_root=app.root.winfo_rooty()+20)
        app.resize_start(start,'e')
        app.resize_end(SimpleNamespace(widget=handle,x_root=start.x_root-80,y_root=start.y_root));app.root.update()
        check('resize after loading drag retains position and releases capture',position()==before and app.root.winfo_width()==width-80 and not app.dragging and app.root.grab_current() is None)

        x,y=app.text.winfo_rootx()+8,app.text.winfo_rooty()+8
        drag_event(app.text,'<ButtonPress-1>',x,y)
        check('completed text does not start window drag',not app.dragging)
        drag_event(app.text,'<ButtonRelease-1>',x,y)
        show_loading();x,y=app.header.winfo_rootx()+4,app.header.winfo_rooty()+4
        drag_event(app.header,'<ButtonPress-1>',x,y)
        with patch.object(ctypes.windll.user32,'GetAsyncKeyState',side_effect=lambda key:0x8000 if key==0x1b else 0):app.dismiss_outside()
        check('Esc during loading drag closes and releases mouse',not app.root.winfo_viewable() and not app.dragging and app.root.grab_current() is None)
        app.busy.release()
        app.result=('Synthetic long translation 日本語。\n'*100)
        app.display(app.result);app.root.update();app.text.yview_moveto(.5);app.root.update()
        old_height=app.root.winfo_height();old_scroll=app.text.yview()
        foreground=ctypes.windll.user32.GetForegroundWindow()
        with patch('jtranslate_app.translate_app.pyperclip.copy') as copy:
            app.copy_button.invoke();app.root.update();copy.assert_called_once_with(app.result)
        check('success shows green bordered check toast',app.copy_toast.winfo_ismapped() and app.copy_toast.cget('highlightbackground')=='#16a34a' and '✓' in app.copy_toast_label.cget('text'))
        check('toast stays in same nonactivating popup',app.copy_toast.winfo_toplevel() is app.root and ctypes.windll.user32.GetForegroundWindow()==foreground)
        check('toast does not resize or scroll translation',app.root.winfo_height()==old_height and app.text.yview()==old_scroll and not app.copy_feedback.winfo_ismapped())
        with patch('jtranslate_app.translate_app.pyperclip.copy') as copy:
            app.text.event_generate('<Button-3>',x=20,y=20);app.root.update();copy.assert_called_once_with(app.result)
        check('single right-click also shows success toast',app.copy_toast.winfo_ismapped())
        for dpi in (96,192):
            app.root.tk.call('tk','scaling',dpi/72)
            font=tkfont.Font(root=app.root,family='Yu Gothic UI',size=10,weight='bold');fonts.append(font)
            app.copy_toast_label.configure(font=font)
            app.user_size=(320,100);app.result='Short result';app.display(app.result);app.root.update()
            with patch('jtranslate_app.translate_app.pyperclip.copy'):app.copy_button.invoke()
            app.root.update()
            tx,ty=app.copy_toast.winfo_rootx(),app.copy_toast.winfo_rooty()
            check(str(dpi)+' DPI toast fits narrow popup',app.contains_point(tx,ty) and app.contains_point(tx+app.copy_toast.winfo_width()-1,ty+app.copy_toast.winfo_height()-1))
        app.root.after(1500,app.root.quit);app.root.mainloop()
        check('toast expires without closing translation',not app.copy_toast.winfo_ismapped() and app.root.winfo_viewable())
        with patch('jtranslate_app.translate_app.pyperclip.copy',side_effect=OSError('PRIVATE')):app.copy_button.invoke()
        app.root.update()
        check('failure shows error and never success toast',not app.copy_toast.winfo_ismapped() and app.copy_feedback.winfo_ismapped() and 'PRIVATE' not in app.copy_feedback.cget('text'))
        failure_height=app.root.winfo_height()
        with patch('jtranslate_app.translate_app.pyperclip.copy'):app.copy_button.invoke()
        app.root.update()
        check('successful retry removes failure row and refits immediately',not app.copy_feedback.winfo_ismapped() and app.copy_toast.winfo_ismapped() and app.root.winfo_height()<failure_height)
        show_loading();app.root.geometry('540x120+100+100');app.root.update()
        def intended_area(anchor=None):
            return (1200,0,2300,900) if anchor is not None and anchor[0]>=1200 else (0,0,1100,900)
        with patch.object(app,'work_area',side_effect=intended_area):
            start=SimpleNamespace(widget=app.header,x_root=app.header.winfo_rootx()+4,y_root=app.header.winfo_rooty()+4)
            app.drag_start(start)
            move=SimpleNamespace(widget=app.header,x_root=start.x_root+1200,y_root=start.y_root+20)
            app.drag_move(move)  # Deliberately leave native geometry unflushed.
            target=app._drag_position
            app.result='Synthetic result on intended second monitor'
            app.display(app.result);app.root.update()
            check('completion before native move flush retains intended monitor',position()==target and position()[0]>=1200)
            app.drag_end()
finally:app.quit()
report={'passed':len(checks),'checks':checks,'clipboard_touched':False,'provider_called':False}
Path('TOAST-DRAG-TEST-RESULTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
