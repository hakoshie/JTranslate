from __future__ import annotations

import ctypes
import queue
from pathlib import Path
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

import pyperclip
import pystray
from PIL import Image, ImageDraw

from .config import Settings, get_api_key
from .hotkey import GlobalHotkey
from .selection import foreground_window
from .tray import TrayIcon, set_app_identity
from .translation import JapaneseTranslator, capture_selected
from .popup_geometry import constrain_rect, resize_rect
from .reasoning import ReasoningConfigurationError, validate_effort
from . import chatgpt_auth
from .capture_errors import CaptureFailure
from . import capture_diagnostics as diagnostics


ICON_PATH = Path(__file__).resolve().parents[1] / 'assets' / 'jtranslate-d-yaku.ico'


class TranslationApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.overrideredirect(True)
        self.root.attributes('-toolwindow', True)
        self.root.title('JTranslate — 日本語訳')
        self.root.attributes('-topmost', True)
        self.root.geometry('540x300')
        self.root.minsize(320, 80)
        self.root.protocol('WM_DELETE_WINDOW', self.hide)
        self.root.bind('<Escape>', lambda _e: self.hide())
        self.events = queue.Queue()
        self.busy = threading.Lock()
        self.closed = False
        self.generation = 0
        self.result = ''
        self.paused = False
        self.mouse_down = False
        self.escape_down = False
        self.resizing = None
        self.user_size = None
        self.popup_minimum = (320,100)
        content = ttk.Frame(self.root)
        content.pack(fill='both',expand=True,padx=5,pady=5)
        header = ttk.Frame(content, padding=8)
        header.pack(fill='x')
        self.title = ttk.Label(header, text='⠿ 日本語訳')
        self.title.pack(side='left', fill='x', expand=True)
        self.title.bind('<ButtonPress-1>', self.drag_start)
        self.title.bind('<B1-Motion>', self.drag_move)
        ttk.Button(header, text='×', width=3, command=self.hide).pack(side='right')
        self.text = tk.Text(content, wrap='word', font=('Yu Gothic UI', 12),
                            relief='flat', padx=12, pady=8, state='disabled')
        scroll = ttk.Scrollbar(content, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.text.pack(fill='both', expand=True)
        self.text.bind('<Button-3>',self.copy_on_right_click)
        self.root.bind('<Button-3>',self.copy_on_right_click)
        self.resize_handles = {}
        for edge,cursor in {'n':'size_ns','s':'size_ns','e':'size_we','w':'size_we',
                            'nw':'size_nw_se','se':'size_nw_se','ne':'size_ne_sw','sw':'size_ne_sw'}.items():
            handle = tk.Frame(self.root,bg='#e5e7eb',cursor=cursor)
            if len(edge)==1 and edge in 'ns':
                handle.place(x=8,rely=1 if edge=='s' else 0,y=-5 if edge=='s' else 0,
                             relwidth=1,width=-16,height=5)
            elif len(edge)==1:
                handle.place(relx=1 if edge=='e' else 0,x=-5 if edge=='e' else 0,y=8,
                             relheight=1,height=-16,width=5)
            else:
                handle.place(relx=1 if 'e' in edge else 0,rely=1 if 's' in edge else 0,
                             x=-8 if 'e' in edge else 0,y=-8 if 's' in edge else 0,width=8,height=8)
            handle.bind('<ButtonPress-1>',lambda event,e=edge:self.resize_start(event,e))
            handle.bind('<B1-Motion>',self.resize_move)
            handle.bind('<ButtonRelease-1>',self.resize_end)
            self.resize_handles[edge] = handle
        with Image.open(ICON_PATH.with_suffix('.png')) as source_icon:
            image = source_icon.copy()
        self.icon = TrayIcon('JTranslate', image, 'JTranslate — Ctrl+Mで日本語訳',
            icon_file=ICON_PATH,
            menu=pystray.Menu(
                pystray.MenuItem('翻訳結果を表示', lambda *_: self.events.put(('show',))),
                pystray.MenuItem('一時停止', lambda *_: self.events.put(('pause',)),
                                 checked=lambda _: self.paused),
                pystray.MenuItem('設定・ChatGPTログイン', lambda *_: self.events.put(('settings',))),
                pystray.MenuItem('終了', lambda *_: self.events.put(('quit',)))))
        self.hotkey = GlobalHotkey(self.request, key='M')
        self.root.update_idletasks()
        user = ctypes.WinDLL('user32')
        user.GetParent.restype = ctypes.c_void_p
        hwnd = user.GetParent(ctypes.c_void_p(self.root.winfo_id()))
        get_style = user.GetWindowLongPtrW
        get_style.restype = ctypes.c_ssize_t
        get_style.argtypes = (ctypes.c_void_p, ctypes.c_int)
        user.SetWindowLongPtrW.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t)
        user.SetWindowLongPtrW(hwnd, -20, get_style(hwnd, -20) | 0x08000080)

    def drag_start(self, event):
        self.drag = (event.x_root - self.root.winfo_x(), event.y_root - self.root.winfo_y())

    def drag_move(self, event):
        x,y,w,h = constrain_rect((event.x_root-self.drag[0],event.y_root-self.drag[1],
                                 self.root.winfo_width(),self.root.winfo_height()),self.work_area())
        self.root.geometry(f'{w}x{h}{x:+d}{y:+d}')

    def work_area(self):
        from ctypes import wintypes
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('size',wintypes.DWORD),('monitor',wintypes.RECT),
                        ('work',wintypes.RECT),('flags',wintypes.DWORD)]
        user = ctypes.WinDLL('user32')
        user.MonitorFromWindow.restype = ctypes.c_void_p
        monitor = user.MonitorFromWindow(ctypes.c_void_p(self.root.winfo_id()),2)
        info = MonitorInfo()
        info.size = ctypes.sizeof(info)
        if user.GetMonitorInfoW(ctypes.c_void_p(monitor),ctypes.byref(info)):
            r = info.work
            return r.left,r.top,r.right,r.bottom
        return 0,0,self.root.winfo_screenwidth(),self.root.winfo_screenheight()

    def resize_start(self,event,edge):
        self.resizing = (edge,event.x_root,event.y_root,
            (self.root.winfo_x(),self.root.winfo_y(),self.root.winfo_width(),self.root.winfo_height()))
        event.widget.grab_set()
        return 'break'

    def resize_move(self,event):
        if self.resizing:
            edge,x,y,rect = self.resizing
            left,top,w,h = resize_rect(rect,edge,event.x_root-x,event.y_root-y,self.work_area(),
                getattr(self,'popup_minimum',(320,100)))
            self.user_size = (w,h)
            self.root.geometry(f'{w}x{h}{left:+d}{top:+d}')
        return 'break'

    def resize_end(self,event):
        self.resize_move(event)
        grab=self.root.grab_current()
        if grab:
            grab.grab_release()
        self.resizing = None
        return 'break'

    def hide(self):
        self.generation += 1
        if getattr(self,'resizing',None):
            grab=self.root.grab_current()
            if grab:
                grab.grab_release()
            self.resizing = None
        self.root.withdraw()

    def contains_point(self, x, y):
        left, top = self.root.winfo_rootx(), self.root.winfo_rooty()
        return left <= x < left+self.root.winfo_width() and top <= y < top+self.root.winfo_height()

    def dismiss_outside(self):
        user = ctypes.windll.user32
        down = bool(user.GetAsyncKeyState(1) & 0x8000 or user.GetAsyncKeyState(2) & 0x8000)
        escape = bool(user.GetAsyncKeyState(0x1b) & 0x8000)
        if self.root.winfo_viewable():
            if down and not self.mouse_down and not self.resizing and not self.contains_point(*self.root.winfo_pointerxy()):
                self.hide()
            elif escape and not self.escape_down:
                self.hide()
        self.mouse_down, self.escape_down = down, escape

    def display(self, text, kind='result'):
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', text)
        self.text.configure(state='disabled')
        self.text.yview_moveto(0)
        font = tkfont.Font(font=self.text.cget('font'))
        width = self.user_size[0] if self.user_size else 540
        available = max(1,width-40)
        lines = sum(max(1, (font.measure(line)+available-1)//available) for line in text.split('\n'))
        height = min(360, max(90, 48+lines*font.metrics('linespace')))
        if self.user_size:
            width,height = self.user_size
        bounds = self.work_area()
        if kind == 'message':
            scale=max(.75,self.root.winfo_fpixels('1i')/96)
            self.popup_minimum=(min(round(440*scale),bounds[2]-bounds[0]),
                                min(round(140*scale),bounds[3]-bounds[1]))
            width=min(bounds[2]-bounds[0],max(width,round(540*scale)))
            height=self.popup_minimum[1]
        else:
            self.popup_minimum=(320,100)
        self.root.minsize(*self.popup_minimum)
        x,y,width,height = constrain_rect((self.root.winfo_x(),self.root.winfo_y(),width,height),bounds,
                                          self.popup_minimum)
        if not self.root.winfo_viewable():
            x,y,width,height = constrain_rect((self.root.winfo_pointerx()+16,
                self.root.winfo_pointery()+16,width,height),bounds)
        self.root.geometry(f'{width}x{height}{x:+d}{y:+d}')
        self.root.deiconify()
        self.root.lift()
        if kind == 'message':
            # Measure Tk's actual wrapped display lines at the current font/DPI.
            self.root.update_idletasks()
            content_pixels=self.text.count('1.0','end-1c','ypixels')
            content_pixels=(content_pixels[0] if content_pixels else 0)+font.metrics('linespace')
            chrome=self.root.winfo_height()-self.text.winfo_height()
            padding=2*sum(int(self.text.cget(option)) for option in ('pady','borderwidth','highlightthickness'))
            height=min(bounds[3]-bounds[1],max(self.popup_minimum[1],chrome+padding+content_pixels+4))
            x,y,width,height=constrain_rect((x,y,width,height),bounds,self.popup_minimum)
            self.root.geometry(f'{width}x{height}{x:+d}{y:+d}')
            self.root.update_idletasks()
            self.text.yview_moveto(0)

    def display_message(self,text):
        self.display(text,kind='message')

    def copy_on_right_click(self, event):
        # A single right click copies the complete result, including off-screen text.
        self.copy_result()
        return 'break'

    def copy_result(self):
        if self.result:
            pyperclip.copy(self.result)

    def request(self):
        if self.closed or self.paused or not self.busy.acquire(False):
            return
        diagnostics.record('request',**diagnostics.hotkey_state())
        self.events.put(('begin', foreground_window()))

    def worker(self, generation, source_window=None):
        try:
            try:
                selected = (capture_selected(expected_window=source_window)
                            if source_window is not None else capture_selected())
            except CaptureFailure as exc:
                diagnostics.record('capture_failed',code=exc.code)
                self.events.put(('message',generation,exc.user_message))
                return
            except Exception as exc:
                diagnostics.record('capture_failed',error_type=type(exc).__name__)
                self.events.put(('message', generation,
                    'この入力欄から選択文を取得できませんでした。対応する本文・入力欄で文章を選択してお試しください。'))
                return
            if not selected:
                self.events.put(('message', generation, '文章を選択してから Ctrl+M を押してください。'))
                return
            if len(selected) > 100000:
                self.events.put(('message', generation, '選択文が長すぎます。100,000文字以内に分けてください。'))
                return
            self.events.put(('loading', generation))
            settings = Settings.load()
            validate_effort(settings.model,settings.reasoning_effort,settings.reasoning_options.get(settings.model))
            converter = JapaneseTranslator(
                get_api_key(settings.provider, settings.chatgpt_account), settings.model,
                settings.api_timeout_seconds, settings.provider,
                diagnostic_text_logging=False, reasoning_effort=settings.reasoning_effort,
                supported_reasoning_efforts=settings.reasoning_options.get(settings.model))
            result = converter.convert(selected, cancelled=lambda: self.closed or generation != self.generation)
            self.events.put(('result', generation, result))
        except ReasoningConfigurationError as exc:
            self.events.put(('message',generation,str(exc)))
        except Exception as exc:
            diagnostics.record('provider_failed',error_type=type(exc).__name__)
            # Never expose provider responses, credentials or source text in logs/UI.
            self.events.put(('message', generation,
                '翻訳できませんでした。トレイの「設定・ChatGPTログイン」と通信状態を確認し、もう一度お試しください。'))
        finally:
            self.busy.release()

    def poll(self):
        self.dismiss_outside()
        while not self.events.empty():
            event = self.events.get_nowait()
            kind = event[0]
            if kind == 'quit':
                self.quit()
                return
            if kind == 'pause':
                self.paused = not self.paused
                self.icon.update_menu()
            elif kind == 'show':
                (self.display(self.result) if self.result else
                 self.display_message('文章を選択してから Ctrl+M を押してください。'))
            elif kind == 'settings':
                from .settings_ui import open_settings
                self.hide()
                if not getattr(self,'settings_window',None) or not self.settings_window.winfo_exists():
                    self.settings_window=open_settings(self.root)
                else:
                    self.settings_window.lift()
            elif kind == 'begin':
                self.generation += 1
                self.result = ''
                threading.Thread(target=self.worker, args=(self.generation,event[1] if len(event)>1 else None), daemon=True).start()
            elif len(event) > 1 and event[1] == self.generation:
                if kind == 'result':
                    self.result = event[2]
                    self.display(self.result)
                elif kind == 'loading':
                    self.display_message('日本語に翻訳中…（Escで表示を閉じる）')
                elif kind == 'message':
                    self.display_message(event[2])
        self.root.after(30, self.poll)

    def quit(self):
        self.closed = True
        self.hotkey.stop()
        self.icon.stop()
        self.root.destroy()

    def run(self):
        diagnostics.startup()
        try:
            self.hotkey.start()
        except OSError:
            self.hotkey.stop()
            messagebox.showerror('JTranslate', 'Ctrl+Mを登録できません。他の常駐アプリとの競合を確認してください。', parent=self.root)
            self.root.destroy()
            return
        self.icon.run_detached()
        if not chatgpt_auth.connected(Settings.load().chatgpt_account):
            self.events.put(("settings",))
        self.root.after(30, self.poll)
        self.root.mainloop()


def main():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.restype = ctypes.c_void_p
    mutex = kernel.CreateMutexW(None, False, 'Local\\JTranslate-1f604a38')
    if not mutex or ctypes.get_last_error() == 183:
        if mutex:
            kernel.CloseHandle(ctypes.c_void_p(mutex))
        return
    try:
        set_app_identity("JTranslate", "JTranslate", ICON_PATH.with_suffix(".png"))
        TranslationApp().run()
    finally:
        kernel.CloseHandle(ctypes.c_void_p(mutex))
