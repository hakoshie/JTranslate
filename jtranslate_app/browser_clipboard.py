"""Fresh-copy fallback for browser document selections, with conditional restore."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from pathlib import PureWindowsPath
import threading
import time
import uuid
import keyboard
from .capture_errors import CaptureFailure
from . import capture_diagnostics as diagnostics

_capture_lock=threading.Lock()
_recovery_pending=threading.Event()
_BROWSERS={'chrome.exe','msedge.exe','firefox.exe','brave.exe','vivaldi.exe','opera.exe'}

def _pump_window_messages(user,window):
    """Clipboard writers synchronously notify the old owner while holding the lock."""
    if not window:return
    user.PeekMessageW.argtypes=(ctypes.POINTER(wintypes.MSG),wintypes.HWND,
                               wintypes.UINT,wintypes.UINT,wintypes.UINT)
    message=wintypes.MSG()
    for _ in range(16):
        # PeekMessage also dispatches cross-thread sent messages, even if it returns 0.
        if not user.PeekMessageW(ctypes.byref(message),window,0,0,1):break
        user.TranslateMessage(ctypes.byref(message))
        user.DispatchMessageW(ctypes.byref(message))

def browser_process(window):
    user=ctypes.WinDLL('user32',use_last_error=True)
    name=ctypes.create_unicode_buffer(128)
    user.GetClassNameW(ctypes.c_void_p(window),name,128)
    if name.value not in ('Chrome_WidgetWin_1','MozillaWindowClass'):return None
    pid=wintypes.DWORD()
    user.GetWindowThreadProcessId(ctypes.c_void_p(window),ctypes.byref(pid))
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.restype=wintypes.HANDLE
    handle=kernel.OpenProcess(0x1000,False,pid.value)
    if not handle:return None
    try:
        buffer=ctypes.create_unicode_buffer(4096);length=wintypes.DWORD(len(buffer))
        kernel.QueryFullProcessImageNameW.argtypes=(wintypes.HANDLE,wintypes.DWORD,wintypes.LPWSTR,ctypes.POINTER(wintypes.DWORD))
        if not kernel.QueryFullProcessImageNameW(handle,0,buffer,ctypes.byref(length)):return None
        return pid.value if PureWindowsPath(buffer.value).name.lower() in _BROWSERS else None
    finally:
        kernel.CloseHandle.argtypes=(wintypes.HANDLE,);kernel.CloseHandle(handle)

def _decode_unicode(raw):
    end=next((i for i in range(0,len(raw)-1,2) if raw[i:i+2]==b'\0\0'),None)
    if end is None:raise ValueError('Clipboard Unicode text is not terminated')
    return raw[:end].decode('utf-16-le')

class ClipboardCapture:
    """Duplicate all preservable formats before any write; do not overwrite a rival copy.

    Delayed/owner-display/metafile formats that cannot be duplicated abort safely.
    Text is never accepted merely because it was on the clipboard before Ctrl+C.
    """
    def __init__(self):
        self.user=ctypes.WinDLL('user32',use_last_error=True)
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.ole=ctypes.WinDLL('ole32',use_last_error=True)
        self.user.CreateWindowExW.restype=wintypes.HWND
        self.user.GetClipboardData.restype=wintypes.HANDLE
        self.user.GetClipboardOwner.restype=wintypes.HWND
        self.user.SetClipboardData.argtypes=(wintypes.UINT,wintypes.HANDLE)
        self.user.SetClipboardData.restype=wintypes.HANDLE
        self.kernel.GlobalAlloc.argtypes=(wintypes.UINT,ctypes.c_size_t)
        self.kernel.GlobalAlloc.restype=wintypes.HANDLE
        self.kernel.GlobalLock.argtypes=(wintypes.HANDLE,)
        self.kernel.GlobalLock.restype=ctypes.c_void_p
        self.kernel.GlobalUnlock.argtypes=(wintypes.HANDLE,)
        self.kernel.GlobalSize.argtypes=(wintypes.HANDLE,)
        self.kernel.GlobalSize.restype=ctypes.c_size_t
        self.kernel.GlobalFree.argtypes=(wintypes.HANDLE,)
        self.ole.OleDuplicateData.restype=wintypes.HANDLE
        self.ole.OleDuplicateData.argtypes=(wintypes.HANDLE,ctypes.c_ushort,ctypes.c_uint)
        self.window=None;self.handles=[];self.sequence=None;self.restored=False
        self.deferred=False;self._old_owner=None
        self.marker='JTranslate-selection-'+uuid.uuid4().hex

    def pump_messages(self):
        _pump_window_messages(self.user,self.window)

    @contextmanager
    def opened(self):
        deadline=time.monotonic()+1
        self.pump_messages()
        while not self.user.OpenClipboard(ctypes.c_void_p(self.window)):
            self.pump_messages()
            if time.monotonic()>=deadline:raise CaptureFailure('clipboard_busy')
            time.sleep(.01)
        try:yield
        finally:self.user.CloseClipboard()

    def put(self,fmt,data):
        handle=self.kernel.GlobalAlloc(0x42,len(data))
        if not handle:raise CaptureFailure('clipboard_access')
        pointer=self.kernel.GlobalLock(handle)
        if not pointer:
            self.kernel.GlobalFree(handle);raise CaptureFailure('clipboard_access')
        ctypes.memmove(pointer,data,len(data));self.kernel.GlobalUnlock(handle)
        if not self.user.SetClipboardData(fmt,handle):
            self.kernel.GlobalFree(handle);raise CaptureFailure('clipboard_access')

    def __enter__(self):
        self.window=self.user.CreateWindowExW(0,'STATIC','JTranslate selection capture',0,0,0,0,0,None,None,None,None)
        if not self.window:raise CaptureFailure('clipboard_access')
        try:
            with self.opened():
                fmt=0
                while True:
                    ctypes.set_last_error(0)
                    fmt=self.user.EnumClipboardFormats(fmt)
                    if not fmt:
                        if ctypes.get_last_error():raise CaptureFailure('clipboard_preserve')
                        break
                    if fmt in (3,14) or 0x80<=fmt<=0x8f or 0x200<=fmt<=0x2ff:
                        raise CaptureFailure('clipboard_preserve')
                    original=self.user.GetClipboardData(fmt)
                    duplicate=self.ole.OleDuplicateData(original,fmt,0) if original else None
                    if not duplicate:raise CaptureFailure('clipboard_preserve')
                    self.handles.append((fmt,duplicate))
                diagnostics.record('snapshot',formats=len(self.handles))
                if not self.user.EmptyClipboard():raise CaptureFailure('clipboard_access')
                self.put(13,(self.marker+'\0').encode('utf-16-le'))
                # Exclude the temporary sentinel from Windows clipboard history/cloud sync.
                for flag in ('CanIncludeInClipboardHistory','CanUploadToCloudClipboard'):
                    self.put(self.user.RegisterClipboardFormatW(flag),b'\0'*4)
            self.sequence=self.user.GetClipboardSequenceNumber()
        except Exception:
            # If a write has begun, restore our snapshot while it is still ours.
            if self.user.GetClipboardOwner()==self.window:
                self.sequence=self.user.GetClipboardSequenceNumber()
                self.__exit__(None,None,None)
            else:self.cleanup()
            raise
        return self

    def fresh_text(self,browser_pid):
        sequence=self.user.GetClipboardSequenceNumber()
        if sequence==self.sequence:return None
        with self.opened():
            owner=self.user.GetClipboardOwner();pid=wintypes.DWORD()
            if owner:self.user.GetWindowThreadProcessId(ctypes.c_void_p(owner),ctypes.byref(pid))
            diagnostics.record('copy_wait',owner=('our_marker' if owner==self.window else
                'missing' if not owner else 'same_browser' if pid.value==browser_pid else 'other'))
            if owner==self.window:
                self.sequence=self.user.GetClipboardSequenceNumber()
                return None
            if not owner:raise CaptureFailure('copy_owner_missing')
            if pid.value!=browser_pid:raise CaptureFailure('clipboard_changed')
            self.sequence=self.user.GetClipboardSequenceNumber()
            text=self.read_unicode_locked()
            if text is None:return None
            self.sequence=self.user.GetClipboardSequenceNumber()
            if text==self.marker:return None
            self.restore_locked()
            return text

    def read_unicode_locked(self):
        handle=self.user.GetClipboardData(13)
        if not handle:return None
        size=self.kernel.GlobalSize(handle)
        if size>2_000_002:raise CaptureFailure('selection_too_large')
        pointer=self.kernel.GlobalLock(handle)
        if not pointer:raise CaptureFailure('clipboard_access')
        try:return _decode_unicode(ctypes.string_at(pointer,size))
        finally:self.kernel.GlobalUnlock(handle)

    def cleanup(self):
        for fmt,handle in self.handles:
            if fmt in (2,9):ctypes.windll.gdi32.DeleteObject(ctypes.c_void_p(handle))
            else:self.kernel.GlobalFree(handle)
        self.handles.clear()
        if self.window:self.user.DestroyWindow(ctypes.c_void_p(self.window));self.window=None

    def restore_locked(self):
        if not self.user.EmptyClipboard():raise CaptureFailure('clipboard_restore')
        while self.handles:
            fmt,handle=self.handles[0]
            if not self.user.SetClipboardData(fmt,handle):raise CaptureFailure('clipboard_restore')
            self.handles.pop(0)
        self.restored=True

    def try_pending_restore(self):
        with self.opened():
            owner=self.user.GetClipboardOwner()
            if owner and owner not in (self.window,self._old_owner):return 'superseded'
            try:text=self.read_unicode_locked()
            except ValueError:return 'superseded'
            # Only our exact temporary marker permits a delayed restore.
            if text!=self.marker:return 'superseded'
            self.restore_locked()
            return 'restored'

    def defer_restore(self):
        # Retain the duplicated original in RAM, rather than free it on a busy lock.
        self.deferred=True
        _recovery_pending.set()
        self._old_owner=self.window
        self.user.DestroyWindow(ctypes.c_void_p(self.window))
        self.window=None
        diagnostics.record('restore_wait')
        def recover():
            try:
                while not self.window:
                    self.window=self.user.CreateWindowExW(0,'STATIC','JTranslate pending restore',0,
                                                         0,0,0,0,None,None,None,None)
                    if not self.window:time.sleep(.1)
                while True:
                    try:
                        status=self.try_pending_restore()
                        diagnostics.record('restore_done',status=status)
                        break
                    except (CaptureFailure,OSError):
                        time.sleep(.1)
            finally:
                self.cleanup()
                _recovery_pending.clear()
        threading.Thread(target=recover,daemon=True,name='JTranslate clipboard restore').start()

    def __exit__(self,*args):
        try:
            if not self.restored:
                try:
                    with self.opened():
                        # A newer user/application copy wins over our saved snapshot.
                        if self.sequence is not None and (self.user.GetClipboardSequenceNumber()==self.sequence
                                or self.user.GetClipboardOwner()==self.window):
                            self.restore_locked()
                except CaptureFailure as error:
                    if error.code=='clipboard_busy' and self.user.GetClipboardOwner()==self.window:
                        self.defer_restore()
                        raise CaptureFailure('clipboard_restore_pending') from None
                    raise
        finally:
            if not self.deferred:self.cleanup()


def copy_browser_selection(window=None,foreground=None,send=None,timeout=1.5):
    if foreground is None:
        from .selection import foreground_window
        foreground=foreground_window
    if window is None:window=foreground()
    pid=browser_process(window)
    diagnostics.record('browser_gate',supported=bool(pid),foreground_matches=foreground()==window)
    if not pid or foreground()!=window:return None
    if _recovery_pending.is_set():raise CaptureFailure('clipboard_restore_pending')
    if not _capture_lock.acquire(False):return None
    try:
        with ClipboardCapture() as capture:
            if foreground()!=window:return None
            diagnostics.record('copy_sent',pump_active=True)
            (send or (lambda:keyboard.send('ctrl+c')))()
            deadline=time.monotonic()+timeout
            while time.monotonic()<deadline:
                capture.pump_messages()
                if foreground()!=window:return None
                text=capture.fresh_text(pid)
                if text is not None:return text
                time.sleep(.015)
            capture.pump_messages()
            if foreground()==window:
                text=capture.fresh_text(pid)
                if text is not None:return text
            diagnostics.record('capture_failed',code='copy_timeout')
            raise CaptureFailure('copy_timeout')
    finally:_capture_lock.release()
