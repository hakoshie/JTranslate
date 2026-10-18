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
from .display_wrap import wrap_display_text
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
        self.dragging = False
        self._drag_position = None
        self._drag_anchor = None
        self._display_kind = None
        self.user_size = None
        self.popup_minimum = (320,100)
        content = ttk.Frame(self.root)
        content.pack(fill='both',expand=True,padx=5,pady=5)
        header = self.header = ttk.Frame(content,padding=8,cursor='fleur')
        header.pack(fill='x')
        self.title = ttk.Label(header, text='⠿ 日本語訳')
        self.title.configure(cursor='fleur')
        for target in (header,self.title):
            target.bind('<ButtonPress-1>',self.drag_start)
            target.bind('<B1-Motion>',self.drag_move)
            target.bind('<ButtonRelease-1>',self.drag_end)
        self.close_button = ttk.Button(header,text='×',width=3,command=self.hide)
        self.close_button.pack(side='right')
        self.copy_button = ttk.Button(header,text='コピー',width=6,command=self.copy_result,state='disabled')
        self.copy_button.pack(side='right',padx=(4,6))
        self.title.pack(side='left',fill='x',expand=True)
        self.copy_feedback = ttk.Label(content,text='',padding=(0,2))
        self._copy_feedback_timer = None
        self._copy_feedback_revision = 0
        self.copy_toast = tk.Frame(self.root,bg='#f0fdf4',highlightbackground='#16a34a',
                                   highlightthickness=2,bd=0,takefocus=0)
        self.copy_toast_label = tk.Label(self.copy_toast,text='',bg='#f0fdf4',fg='#166534',
            font=('Yu Gothic UI',10,'bold'),padx=10,pady=6,takefocus=0)
        self.copy_toast_label.pack(fill='both',expand=True)
        self.text = tk.Text(content, wrap='none', font=('Yu Gothic UI', 12),
                            relief='flat', padx=12, pady=8, state='disabled')
        self.scroll = ttk.Scrollbar(content, command=self.text.yview)
        self.text.configure(yscrollcommand=self.scroll.set)
        self.text.pack(fill='both', expand=True)
        self.base_title = self.title.cget('text')
        self._layout_active = False
        self._layout_dirty = False
        self._display_source = ''
        self._wrap_key = None
        self._layout_revision = 0
        self._layout_request = 0
        self._layout_timer = None
        self._layout_key = None
        self.root.bind('<Configure>', self.layout_changed)
        self.text.bind('<Button-3>',self.copy_on_right_click)
        self.text.bind('<ButtonPress-1>',self.loading_drag_start)
        self.text.bind('<B1-Motion>',self.loading_drag_move)
        self.text.bind('<ButtonRelease-1>',self.drag_end)
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
        if self.resizing:
            return 'break'
        self.dragging = True
        self._drag_anchor = (event.x_root,event.y_root)
        self._drag_position = (self.root.winfo_x(),self.root.winfo_y())
        self.drag = (event.x_root-self._drag_position[0],event.y_root-self._drag_position[1])
        target = getattr(event,'widget',self.title)
        target.grab_set()
        return 'break'

    def loading_drag_start(self, event):
        if self._display_kind == 'loading':
            return self.drag_start(event)

    def loading_drag_move(self, event):
        if self.dragging:
            return self.drag_move(event)

    def drag_move(self, event):
        if not self.dragging:
            return
        self._drag_anchor = (event.x_root,event.y_root)
        x,y,w,h = constrain_rect((event.x_root-self.drag[0],event.y_root-self.drag[1],
                                 self.root.winfo_width(),self.root.winfo_height()),
                                 self.work_area((event.x_root,event.y_root)))
        self._drag_position = (x,y)
        self.root.geometry(f'{w}x{h}+{x}+{y}')
        return 'break'

    def drag_end(self, event=None):
        if not getattr(self,'dragging',False):
            return
        if event is not None:
            self.drag_move(event)
        grab = self.root.grab_current()
        if grab:
            grab.grab_release()
        self.dragging = False
        self.mouse_down = False
        return 'break'

    def popup_work_area(self):
        # The intended monitor is authoritative before Win32 applies a queued move.
        anchor = self._drag_anchor if self._drag_position is not None else None
        return self.work_area(anchor)

    def work_area(self, anchor=None):
        from ctypes import wintypes
        class MonitorInfo(ctypes.Structure):
            _fields_ = [('size',wintypes.DWORD),('monitor',wintypes.RECT),
                        ('work',wintypes.RECT),('flags',wintypes.DWORD)]
        user = ctypes.WinDLL('user32')
        user.MonitorFromWindow.restype = ctypes.c_void_p
        if anchor is None:
            monitor = user.MonitorFromWindow(ctypes.c_void_p(self.root.winfo_id()),2)
        else:
            user.MonitorFromPoint.restype = ctypes.c_void_p
            user.MonitorFromPoint.argtypes = (wintypes.POINT,wintypes.DWORD)
            monitor = user.MonitorFromPoint(wintypes.POINT(*anchor),2)
        info = MonitorInfo()
        info.size = ctypes.sizeof(info)
        if user.GetMonitorInfoW(ctypes.c_void_p(monitor),ctypes.byref(info)):
            r = info.work
            return r.left,r.top,r.right,r.bottom
        return 0,0,self.root.winfo_screenwidth(),self.root.winfo_screenheight()

    def resize_start(self,event,edge):
        self.drag_end()
        self.resizing = (edge,event.x_root,event.y_root,
            (self.root.winfo_x(),self.root.winfo_y(),self.root.winfo_width(),self.root.winfo_height()))
        event.widget.grab_set()
        return 'break'

    def resize_move(self,event):
        if self.resizing:
            edge,x,y,rect = self.resizing
            left,top,w,h = resize_rect(rect,edge,event.x_root-x,event.y_root-y,self.popup_work_area(),
                getattr(self,'popup_minimum',(320,100)))
            self.user_size = (w,h)
            if self._drag_position is not None:
                self._drag_position = (left,top)
            self.root.geometry(f'{w}x{h}+{left}+{top}')
        return 'break'

    def resize_end(self,event):
        self.resize_move(event)
        grab=self.root.grab_current()
        if grab:
            grab.grab_release()
        self.root.update_idletasks()
        self.resizing = None
        self.fit_height()
        return 'break'

    def hide(self):
        self.drag_end()
        self._drag_position = None
        self._drag_anchor = None
        self.clear_copy_feedback(refit=False)
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
            if down and not self.mouse_down and not self.resizing and not getattr(self,'dragging',False) and not self.contains_point(*self.root.winfo_pointerxy()):
                self.hide()
            elif escape and not self.escape_down:
                self.hide()
        self.mouse_down, self.escape_down = down, escape

    def layout_changed(self, event):
        if event.widget is self.root:
            self.position_copy_toast()
        if event.widget is not self.root or self.resizing:
            return
        if self._layout_active:
            self._layout_dirty = True
            return
        if self._layout_timer is None and self.root.winfo_viewable():
            self._layout_timer = self.root.after_idle(self.refit_if_changed)

    def refit_if_changed(self):
        self._layout_timer = None
        if self.closed or self.resizing or not self.root.winfo_viewable():
            return
        if self._layout_active:
            self._layout_dirty = True
            return
        if self._layout_dirty or self.layout_key() != self._layout_key:
            self.fit_height()

    def layout_key(self):
        return (self.root.winfo_width(),self.root.winfo_height(),
                self.popup_work_area(),self.root.winfo_fpixels('1i'))

    def reflow_text(self):
        self.copy_feedback.configure(wraplength=max(1,self.text.winfo_width()-24))
        self.root.update_idletasks()
        font = tkfont.Font(font=self.text.cget('font'))
        width = max(1,self.text.winfo_width()-2*sum(int(self.text.cget(option))
                    for option in ('padx','borderwidth','highlightthickness')))
        key = (self._layout_revision,width,tuple(sorted(font.actual().items())),
               font.metrics('linespace'),font.measure('M'))
        if key == self._wrap_key:
            return
        rendered = wrap_display_text(self._display_source,font.measure,width)
        position = self.text.yview()[0]
        self.text.configure(state='normal')
        self.text.delete('1.0','end')
        self.text.insert('1.0',rendered)
        self.text.configure(state='disabled')
        self.text.yview_moveto(position)
        self._wrap_key = key

    def fit_height(self, bounds=None):
        # Tk measures actual wrapped display lines, including Unicode and DPI.
        if self._layout_active:
            self._layout_request += 1
            self._layout_dirty = True
            return
        if not self.root.winfo_viewable():
            return
        self._layout_active = True
        self._layout_dirty = False
        content_revision,fit_request = self._layout_revision,self._layout_request
        try:
            bounds = bounds or self.popup_work_area()
            self.scroll.pack_forget()
            self.root.update()
            if self.closed or not self.root.winfo_viewable():
                return
            def required_height():
                self.reflow_text()
                pixels = self.text.count('1.0','end','update','ypixels')
                pixels = (pixels[0] if isinstance(pixels,tuple) else pixels) or 0
                chrome = self.root.winfo_height()-self.text.winfo_height()
                padding = 2*sum(int(self.text.cget(option)) for option in
                                ('pady','borderwidth','highlightthickness'))
                return max(self.popup_minimum[1],chrome+padding+pixels+4)
            measured_width = self.root.winfo_width()
            height = required_height()
            if height > bounds[3]-bounds[1]:
                self.scroll.pack(side='right',fill='y',before=self.text)
                self.root.update()
                if self.closed or not self.root.winfo_viewable():
                    return
                height = required_height()
            left,top = self._drag_position or (self.root.winfo_x(),self.root.winfo_y())
            x,y,w,h = constrain_rect((left,top,self.root.winfo_width(),height),bounds,self.popup_minimum)
            if self._drag_position is not None:
                self._drag_position = (x,y)
            measured = (measured_width,bounds,self.root.winfo_fpixels('1i'),
                        content_revision,fit_request)
            # An explicit plus also represents absolute negative monitor coordinates.
            self.root.geometry(f'{w}x{h}+{x}+{y}')
            self.root.update()
            if not self.closed:
                actual = (self.root.winfo_width(),self.popup_work_area(),self.root.winfo_fpixels('1i'),
                          self._layout_revision,self._layout_request)
                self._layout_dirty = actual != measured
                if not self._layout_dirty:
                    self._layout_key = self.layout_key()
        finally:
            self._layout_active = False
            if not self.closed and self._layout_dirty and self._layout_timer is None:
                self._layout_timer = self.root.after_idle(self.refit_if_changed)

    def display(self, text, kind='result'):
        self._display_kind = kind
        self.text.configure(cursor='fleur' if kind=='loading' else 'xterm')
        self.clear_copy_feedback(refit=False)
        self.copy_button.configure(state='normal' if kind=='result' and self.result else 'disabled')
        self._layout_revision += 1
        self._display_source = text
        self.title.configure(text=('翻訳中' if kind=='loading' else
            ('お知らせ' if kind=='message' else self.base_title)+'（Escで閉じる）'))
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', text)
        self.text.configure(state='disabled')
        visible = self.root.winfo_viewable()
        anchor = None if visible else self.root.winfo_pointerxy()
        bounds = self.popup_work_area() if visible else self.work_area(anchor)
        self.popup_minimum = (min(320,bounds[2]-bounds[0]),min(100,bounds[3]-bounds[1]))
        self.root.minsize(*self.popup_minimum)
        width = self.user_size[0] if self.user_size else 540
        x,y = (self._drag_position or (self.root.winfo_x(),self.root.winfo_y())) if visible else (anchor[0]+16,anchor[1]+16)
        x,y,width,height = constrain_rect((x,y,width,self.popup_minimum[1]),bounds,self.popup_minimum)
        layout_was_active = self._layout_active
        self._layout_active = True
        try:
            self.root.geometry(f'{width}x{height}+{x}+{y}')
            self.root.deiconify()
            self.root.lift()
            self.root.update_idletasks()
        finally:
            self._layout_active = layout_was_active
        self.fit_height(bounds)
        if not self.closed:
            self.text.yview_moveto(0)

    def display_message(self,text):
        self.display(text,kind='message')

    def copy_on_right_click(self, event):
        # A single right click copies the complete result, including off-screen text.
        self.copy_result()
        return 'break'

    def clear_copy_feedback(self, refit=True):
        if getattr(self,'copy_feedback',None) is None:
            return
        self._copy_feedback_revision = getattr(self,'_copy_feedback_revision',0)+1
        if self._copy_feedback_timer is not None:
            self.root.after_cancel(self._copy_feedback_timer)
            self._copy_feedback_timer = None
        self.copy_feedback.pack_forget()
        self.copy_toast.place_forget()
        if refit and not self.closed and self.root.winfo_viewable():
            self.fit_height()

    def position_copy_toast(self, show=False):
        if not show and self.copy_toast.winfo_manager() != 'place':
            return
        font = tkfont.Font(font=self.copy_toast_label.cget('font'))
        natural_width = font.measure(self.copy_toast_label.cget('text'))+24
        width = max(1,min(natural_width,self.root.winfo_width()-20))
        self.copy_toast_label.configure(wraplength=max(1,width-24))
        self.copy_toast.place(relx=.5,rely=1,anchor='s',y=-10,width=width)
        self.copy_toast.lift()

    def show_copy_feedback(self, text, success):
        had_error = self.copy_feedback.winfo_ismapped()
        self.clear_copy_feedback(refit=False)
        revision = self._copy_feedback_revision
        if success:
            if had_error:
                self.fit_height()
            if revision != self._copy_feedback_revision or self.closed:
                return
            self.copy_toast_label.configure(text='✓ '+text)
            self.root.update_idletasks()
            if revision != self._copy_feedback_revision or self.closed:
                return
            self.position_copy_toast(show=True)
        else:
            self.copy_feedback.configure(text=text,foreground='#b91c1c')
            self.copy_feedback.pack(fill='x',before=self.text,padx=12,pady=(0,4))
            self.fit_height()
        if revision == self._copy_feedback_revision and not self.closed and self.root.winfo_viewable():
            self._copy_feedback_timer = self.root.after(1300 if success else 4000,
                lambda: self.expire_copy_feedback(revision))

    def expire_copy_feedback(self, revision):
        if revision == self._copy_feedback_revision:
            self.clear_copy_feedback()

    def copy_result(self):
        if not self.result:
            return False
        try:
            pyperclip.copy(self.result)
        except (pyperclip.PyperclipException,OSError):
            self.show_copy_feedback('コピーできませんでした。もう一度お試しください。',False)
            return False
        self.show_copy_feedback('コピーしました',True)
        return True

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
                    self.display('日本語に翻訳中…\nEsc：結果表示を取り消す（進行中の通信は完了まで続きます）',kind='loading')
                elif kind == 'message':
                    self.display_message(event[2])
        self.root.after(30, self.poll)

    def quit(self):
        self.drag_end()
        self.closed = True
        self.clear_copy_feedback(refit=False)
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
