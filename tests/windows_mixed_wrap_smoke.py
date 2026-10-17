"""Synthetic text and native Tk layout only; never touches clipboard or provider."""
import json
from pathlib import Path
from unittest.mock import patch
import tkinter.font as tkfont
from jtranslate_app.translate_app import TranslationApp

app=TranslationApp();checks=[];fonts=[]
sample='ChatGPT Spaceとは何か。それが今回のテーマです。実際に開発チームが取り組んでいるので、思わず微笑んでしまうような不器用さがときどきあります。次は何を見てみたいですか？'
def check(name,value):
    assert value,name
    checks.append(name)
def fits():
    app.root.update()
    return app.text.yview()[1]==1 and app.text.bbox('end-2c') is not None
try:
    with patch.object(app,'work_area',return_value=(0,0,1200,1000)):
        for dpi in (96,144,192):
            app.root.tk.call('tk','scaling',dpi/72)
            font=tkfont.Font(root=app.root,family='Yu Gothic UI',size=12);fonts.append(font)
            app.text.configure(font=font)
            for width in (320,540,800):
                app.user_size=(width,100);app.result=sample;app.display(sample);app.root.update()
                rendered=app.text.get('1.0','end-1c')
                check(f'{dpi} DPI {width}px mixed words stay on first line',rendered.splitlines()[0].startswith('ChatGPT Space'))
                check(f'{dpi} DPI {width}px measured height fits rendering',fits())
                check(f'{dpi} DPI {width}px copy source remains unchanged',app.result==sample)
                content_width=app.text.winfo_width()-2*sum(int(app.text.cget(k)) for k in ('padx','borderwidth','highlightthickness'))
                check(f'{dpi} DPI {width}px no horizontal overflow',all(font.measure(line)<=content_width for line in rendered.split('\n')))
        app.root.tk.call('tk','scaling',96/72)
        font=tkfont.Font(root=app.root,family='Yu Gothic UI',size=12);fonts.append(font);app.text.configure(font=font)
        structured='見出し\n\n- ChatGPT Spaceの説明\n  code = "English words"\n```\nprint("hello")\n```'
        app.user_size=(540,100);app.display(structured);app.root.update()
        check('short structured source keeps intentional formatting',app.text.get('1.0','end-1c')==structured)
        for source in ['日本語 translation example 日本語 '*6,'Supercalifragilisticexpialidocious'*8,'https://example.com/'+'long/path/'*40]:
            app.user_size=(320,100);app.display(source);app.root.update()
            text=app.text.get('1.0','end-1c')
            check('long mixed token wraps without clipping '+str(len(checks)),fits())
            if 'translation' in source:check('ordinary English words never split','translation' in text and 'example' in text)
            else:check('long word or URL original characters preserved',''.join(text.splitlines())==source)
        app.display((sample+'\n')*100);app.root.update()
        check('overflow still scrolls',app.scroll.winfo_ismapped() and app.text.yview()[1]<1)
        app.text.yview_moveto(1);app.root.update()
        check('overflow reaches final character',app.text.bbox('end-2c') is not None)
        app.user_size=(540,100);app.display(sample);app.root.update()
        with patch('jtranslate_app.translate_app.pyperclip.copy') as copy:
            app.result=sample
            app.copy_on_right_click(None)
            copy.assert_called_once_with(sample)
        check('right-click copies original source without visual breaks',True)
        from PIL import ImageGrab
        x,y=app.root.winfo_rootx(),app.root.winfo_rooty()
        ImageGrab.grab(bbox=(x,y,x+app.root.winfo_width(),y+app.root.winfo_height()),all_screens=True).save('translation-mixed-wrap.png')
        app.root.tk.call('tk','scaling',192/72)
        font=tkfont.Font(root=app.root,family='Yu Gothic UI',size=12);fonts.append(font)
        app.text.configure(font=font)
        app.fit_height();app.root.update()
        rendered=app.text.get('1.0','end-1c')
        content_width=app.text.winfo_width()-2*sum(int(app.text.cget(k)) for k in ('padx','borderwidth','highlightthickness'))
        check('font DPI change reflows existing content without new result',all(font.measure(line)<=content_width for line in rendered.split('\n')) and fits())
finally:app.quit()
report={'passed':len(checks),'checks':checks,'clipboard_touched':False,'provider_called':False}
Path('MIXED-WRAP-TEST-RESULTS.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
