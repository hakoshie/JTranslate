"""Explicit Windows integration probe using only synthetic, non-sensitive text.

Run manually, outside pytest. Preserves the user's clipboard formats.
"""
import ctypes
import json
import time
import faulthandler
import sys
import threading
import tkinter as tk
from types import SimpleNamespace
from unittest.mock import patch

import keyboard
import pyperclip

from jtranslate_app.hotkey import GlobalHotkey
from windows_clipboard_test_support import ClipboardSnapshot
from jtranslate_app.translate_app import TranslationApp
from jtranslate_app.translation import capture_selected as real_capture
from jtranslate_app.selection import activate_window


checks = []
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
faulthandler.dump_traceback_later(100)

def debug_capture():
    import traceback
    try:
        if not activate_window(top):
            raise AssertionError('Cannot focus synthetic source')
        ready = threading.Event()
        app.root.after(0, lambda: (text.focus_force(), ready.set()))
        if not ready.wait(2):
            raise AssertionError('Cannot focus synthetic edit control')
        print('native selection at capture:', user.SendMessageW(edit, 0xb0, 0, 0), flush=True)
        info = ctypes.create_string_buffer(72)
        ctypes.c_uint32.from_buffer(info).value = 72
        user.GetGUIThreadInfo(0, info)
        focus = ctypes.c_void_p.from_buffer(info,16).value
        name = ctypes.create_unicode_buffer(128)
        user.GetClassNameW(ctypes.c_void_p(focus), name, 128)
        print('focus class:', name.value, 'test focused:', focus == edit, flush=True)
        result = real_capture()
        print('synthetic selection:', repr(result), flush=True)
        return result
    except Exception:
        traceback.print_exc()
        raise


def check(name, value):
    if not value:
        raise AssertionError(name)
    checks.append(name)
    print('PASS:', name, flush=True)


with ClipboardSnapshot():
    pyperclip.copy('Synthetic clipboard before capture 🌏')
    app = TranslationApp()
    source = tk.Tk()
    source.title('JTranslate synthetic test source')
    source.geometry('450x180+40+40')
    source.update()
    user = ctypes.WinDLL('user32')
    user.CreateWindowExW.restype = ctypes.c_void_p
    user.CreateWindowExW.argtypes = (ctypes.c_ulong, ctypes.c_wchar_p, ctypes.c_wchar_p,
        ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
    user.SendMessageW.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t)
    edit = user.CreateWindowExW(0, 'EDIT', 'Hello world 🌏\r\n日本語のテスト',
        0x50001004, 0, 0, 440, 170, source.winfo_id(), None, None, None)
    assert edit
    class NativeText:
        def focus_force(self):
            user.SetFocus(ctypes.c_void_p(edit))
        def tag_add(self, *args):
            user.SendMessageW(edit, 0xB1, 0, -1)
        def tag_remove(self, *args):
            user.SendMessageW(edit, 0xB1, 0, 0)
        def get(self, *args):
            buf = ctypes.create_unicode_buffer(256)
            user.SendMessageW(edit, 0xD, 256, ctypes.addressof(buf))
            return buf.value.replace('\r\n','\n')
    text = NativeText()
    user.GetAncestor.restype = ctypes.c_void_p
    top = user.GetAncestor(ctypes.c_void_p(source.winfo_id()), 2)
    count = []

    class FakeTranslator:
        def __init__(self, *args, **kwargs):
            pass

        def convert(self, selected, **kwargs):
            count.append(selected)
            time.sleep(.25)
            return 'こんにちは世界🌏\n日本語のテスト'

    error = []
    stage = [0]
    deadline = time.monotonic()+90

    def step():
        try:
            if time.monotonic() > deadline:
                raise AssertionError(f'timeout at stage {stage[0]}: busy={app.busy.locked()}, calls={count!r}, ui={app.text.get("1.0","end")!r}')
            if stage[0] == 0:
                source.deiconify()
                source.lift()
                source.focus_force()
                check('synthetic source can receive focus', activate_window(top))
                text.focus_force()
                text.tag_add('sel', '1.0', 'end-1c')
                stage[0] = 1
                app.root.after(200, step)
                return
            if stage[0] == 1:
                activate_window(top)
                text.focus_force()
                text.tag_add('sel', '1.0', 'end-1c')
                print('native selection before hotkey:', user.SendMessageW(edit, 0xb0, 0, 0), flush=True)
                keyboard.send('ctrl+m')
                stage[0] = 2
            elif stage[0] == 2 and app.result:
                print('synthetic captured:', repr(count), flush=True)
                check('hotkey translates exact Unicode selection', len(count) == 1 and count[0].replace('\r\n','\n') == 'Hello world 🌏\n日本語のテスト')
                check('clipboard restored after selection', pyperclip.paste() == 'Synthetic clipboard before capture 🌏')
                check('popup visible', app.root.winfo_viewable())
                popup = user.GetAncestor(ctypes.c_void_p(app.root.winfo_id()), 2)
                check('popup does not take foreground focus', user.GetForegroundWindow() != popup)
                check('source unchanged', text.get('1.0', 'end-1c') == count[0].replace('\r\n','\n'))
                app.root.update()
                start = app.root.winfo_x(), app.root.winfo_y()
                app.title.event_generate('<ButtonPress-1>', x=5, y=5, rootx=start[0]+5, rooty=start[1]+5)
                app.title.event_generate('<B1-Motion>', x=105, y=65, rootx=start[0]+105, rooty=start[1]+65)
                app.root.update()
                check('drag moves popup', app.root.winfo_x() == start[0]+100)
                app.menu.invoke(0)
                check('context menu copy Unicode', pyperclip.paste() == app.result)
                app.display(('Long Japanese paragraph 日本語🌏\n' * 300))
                app.root.update()
                check('long text scrolls', app.text.yview()[1] < 1)
                app.text.yview_moveto(1)
                app.root.update()
                check('scroll reaches long text end', app.text.yview()[1] == 1)
                check('scroll keeps popup visible', app.root.winfo_viewable())
                from PIL import ImageGrab
                x,y=app.root.winfo_rootx(),app.root.winfo_rooty()
                ImageGrab.grab(bbox=(x,y,x+app.root.winfo_width(),y+app.root.winfo_height())).save('translation-popup.png')
                point = ctypes.wintypes.POINT()
                user.GetCursorPos(ctypes.byref(point))
                user.SetCursorPos(60,60)
                user.mouse_event(2,0,0,0,0)
                app.dismiss_outside()
                user.mouse_event(4,0,0,0,0)
                user.SetCursorPos(point.x,point.y)
                check('outside click hides popup', not app.root.winfo_viewable())
                app.display(app.result)
                keyboard.press('esc')
                app.dismiss_outside()
                keyboard.release('esc')
                check('Escape hides popup', not app.root.winfo_viewable())
                app.display(app.result)
                app.root.protocol('WM_DELETE_WINDOW')
                app.hide()
                check('close hides popup', not app.root.winfo_viewable())
                text.tag_remove('sel', '1.0', 'end')
                source.focus_force()
                text.focus_force()
                stage[0] = 3
                app.root.after(200, step)
                return
            elif stage[0] == 3:
                keyboard.send('ctrl+m')
                stage[0] = 4
            elif stage[0] == 4 and not app.busy.locked():
                check('empty selection never translates stale clipboard', len(count) == 1)
                check('empty selection leaves clipboard unchanged', pyperclip.paste() == 'こんにちは世界🌏\n日本語のテスト')
                check('empty selection shows hint', '文章を選択' in app.text.get('1.0','end'))
                conflict = GlobalHotkey(lambda: None, key='M')
                try:
                    conflict.start()
                except OSError:
                    checks.append('hotkey conflict detected')
                else:
                    raise AssertionError('hotkey conflict not detected')
                finally:
                    conflict.stop()
                source.destroy()
                app.events.put(('quit',))
                return
            app.root.after(50, step)
        except Exception as exc:
            error.append(str(exc))
            source.destroy()
            app.quit()

    with patch('jtranslate_app.translate_app.JapaneseTranslator', FakeTranslator), \
         patch('jtranslate_app.translate_app.get_api_key', return_value='test-only'), \
         patch('jtranslate_app.translate_app.capture_selected', debug_capture):
        app.root.after(300, step)
        app.run()
    check('tray exit releases hotkey', app.closed)
    if error:
        raise AssertionError(error[0])

print(json.dumps({'checks': checks, 'passed': len(checks)}, ensure_ascii=False, indent=2))
