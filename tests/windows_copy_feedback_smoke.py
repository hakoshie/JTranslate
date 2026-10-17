"""Own synthetic popup; clipboard copy is mocked for every interaction."""
import ctypes,json
from pathlib import Path
from unittest.mock import patch
import tkinter.font as tkfont
import pyperclip
from jtranslate_app.translate_app import TranslationApp

app=TranslationApp();checks=[];fonts=[]
source='Synthetic translation 日本語。\n'+'Long translated paragraph. '*200
def check(name,condition):
    assert condition,name
    checks.append(name)
def show(text=source):
    app.result=text;app.display(text);app.root.update()
def inside(widget):
    x,y=widget.winfo_rootx(),widget.winfo_rooty()
    return widget.winfo_ismapped() and app.contains_point(x,y) and app.contains_point(x+widget.winfo_width()-1,y+widget.winfo_height()-1)
try:
    with patch.object(app,'work_area',return_value=(0,0,1100,900)):
        app.user_size=(540,100);show()
        with patch('jtranslate_app.translate_app.pyperclip.copy') as copy:
            app.copy_button.invoke();app.root.update()
            copy.assert_called_once_with(source)
        check('button copies entire unwrapped result once',True)
        check('successful button copy shows inline confirmation',app.copy_toast.winfo_ismapped() and app.copy_toast_label.cget('text')=='✓ コピーしました')
        check('long text still scrolls with feedback',app.scroll.winfo_ismapped() and app.text.yview()[1]<1)
        app.text.yview_moveto(1);app.root.update()
        check('feedback leaves final text reachable',app.text.bbox('end-2c') is not None)
        with patch('jtranslate_app.translate_app.pyperclip.copy') as copy:
            app.text.event_generate('<Button-3>',x=20,y=20);app.root.update()
            copy.assert_called_once_with(source)
        check('single right click shares copy and success feedback',app.copy_toast_label.cget('text')=='✓ コピーしました')
        x,y=app.copy_button.winfo_rootx()+3,app.copy_button.winfo_rooty()+3
        app.mouse_down=False
        with patch.object(app.root,'winfo_pointerxy',return_value=(x,y)),patch.object(ctypes.windll.user32,'GetAsyncKeyState',side_effect=lambda key:0x8000 if key==1 else 0):
            app.dismiss_outside()
        check('copy button click is inside popup and stays open',app.root.winfo_viewable())
        with patch('jtranslate_app.translate_app.pyperclip.copy',side_effect=pyperclip.PyperclipException('PRIVATE')):
            app.copy_button.invoke();app.root.update()
        check('failure is visible without false success or raw exception','コピーできませんでした' in app.copy_feedback.cget('text') and 'PRIVATE' not in app.copy_feedback.cget('text'))
        for dpi in (96,192):
            app.root.tk.call('tk','scaling',dpi/72)
            font=tkfont.Font(root=app.root,family='Yu Gothic UI',size=12);fonts.append(font);app.text.configure(font=font)
            app.user_size=(320,100);show('Short synthetic result')
            check(str(dpi)+' DPI narrow copy and close controls visible',inside(app.copy_button) and inside(app.close_button))
            with patch('jtranslate_app.translate_app.pyperclip.copy',side_effect=OSError('PRIVATE')):
                app.copy_button.invoke();app.root.update()
            check(str(dpi)+' DPI failure feedback fits narrow popup',app.copy_feedback.winfo_ismapped() and app.text.yview()[1]==1 and app.root.winfo_height()<=900)
        default_font=tkfont.nametofont('TkDefaultFont')
        default_font.configure(size=9)
        app.user_size=(320,100);show('Short synthetic result')
        check('scaled header retains copy control in narrow popup',inside(app.copy_button) and inside(app.close_button))
        app.user_size=(540,100);show('Short synthetic result')
        with patch('jtranslate_app.translate_app.pyperclip.copy',side_effect=OSError('PRIVATE')):
            app.copy_button.invoke();app.root.update()
        from types import SimpleNamespace
        handle=app.resize_handles['e']
        start=SimpleNamespace(widget=handle,x_root=app.root.winfo_rootx()+540,y_root=app.root.winfo_rooty()+30)
        app.resize_start(start,'e')
        app.resize_end(SimpleNamespace(widget=handle,x_root=start.x_root-220,y_root=start.y_root));app.root.update()
        check('active failure feedback rewraps and height fits after resize',app.text.yview()[1]==1 and app.copy_feedback.winfo_height()>=app.copy_feedback.winfo_reqheight())
        show('Short synthetic result')
        with patch('jtranslate_app.translate_app.pyperclip.copy'):
            app.copy_button.invoke()
        app.root.after(1950,app.root.quit);app.root.mainloop()
        check('success feedback expires automatically',not app.copy_feedback.winfo_ismapped() and not app.copy_toast.winfo_ismapped() and app._copy_feedback_timer is None)
        app.events.put(('loading',app.generation));app.poll();app.root.update()
        check('loading explanation uses one Esc explanation line',app._display_source.count('\n')==1 and 'Esc：' in app._display_source and '進行中の通信' in app._display_source)
        check('loading copy button disabled',app.copy_button.instate(['disabled']))
        app.root.tk.call('tk','scaling',96/72);default_font.configure(size=9)
        font=tkfont.Font(root=app.root,family='Yu Gothic UI',size=12);fonts.append(font);app.text.configure(font=font)
        app.user_size=(540,100)
        show('コピーした翻訳結果は、ここに表示されます。ChatGPT Spaceも自然に折り返します。')
        with patch('jtranslate_app.translate_app.pyperclip.copy'):app.copy_button.invoke()
        app.root.geometry(f'540x{app.root.winfo_height()}+100+100');app.root.update()
        start=SimpleNamespace(x_root=app.title.winfo_rootx()+4,y_root=app.title.winfo_rooty()+4)
        app.drag_start(start)
        app.drag_move(SimpleNamespace(x_root=start.x_root+30,y_root=start.y_root+20));app.root.update()
        check('header drag preserves inline feedback and controls',app.root.winfo_x()==130 and app.root.winfo_y()==120 and app.copy_toast.winfo_ismapped() and inside(app.copy_button))
        check('feedback layout keeps wrapped final character visible',app.text.yview()[1]==1 and app.text.bbox('end-2c') is not None)
        ctypes.windll.dwmapi.DwmFlush()
        from PIL import ImageGrab
        x,y=app.root.winfo_rootx(),app.root.winfo_rooty()
        ImageGrab.grab(bbox=(x,y,x+app.root.winfo_width(),y+app.root.winfo_height()),all_screens=True).save('translation-copy-feedback.png')
        app.hide();app.root.update()
        check('hide cancels feedback without reopening',not app.root.winfo_viewable() and app._copy_feedback_timer is None)
finally:app.quit()
report={'passed':len(checks),'checks':checks,'clipboard_touched':False,'provider_called':False}
Path('COPY-FEEDBACK-TEST-RESULTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
