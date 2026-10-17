"""Preserve the clipboard around explicit Windows integration tests only."""
import ctypes
import time

class ClipboardSnapshot:
    """Duplicate clipboard formats before capture; restore actual data handles.

    Unsupported owner/display/metafile formats abort before any modification.
    Uses a hidden owner window, not an OLE object tied to a closed apartment.
    """
    def __enter__(self):
        self.user = ctypes.WinDLL('user32', use_last_error=True)
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.ole = ctypes.WinDLL('ole32', use_last_error=True)
        self.user.CreateWindowExW.restype = ctypes.c_void_p
        self.user.GetClipboardData.restype = ctypes.c_void_p
        self.user.SetClipboardData.restype = ctypes.c_void_p
        self.ole.OleDuplicateData.restype = ctypes.c_void_p
        self.ole.OleDuplicateData.argtypes = (ctypes.c_void_p, ctypes.c_ushort, ctypes.c_uint)
        self.window = self.user.CreateWindowExW(0, 'STATIC', 'JTranslate clipboard owner', 0,
                                                0, 0, 0, 0, None, None, None, None)
        if not self.window:
            raise OSError('Cannot create clipboard owner')
        self.handles = []
        try:
            self.open()
            try:
                fmt = 0
                while True:
                    fmt = self.user.EnumClipboardFormats(fmt)
                    if not fmt:
                        break
                    if fmt in (3, 14) or 0x80 <= fmt <= 0x8f or 0x200 <= fmt <= 0x2ff:
                        raise OSError('Unsupported clipboard format; clipboard left unchanged')
                    original = self.user.GetClipboardData(fmt)
                    duplicate = self.ole.OleDuplicateData(original, fmt, 0) if original else None
                    if not duplicate:
                        raise OSError('Clipboard cannot be preserved; capture cancelled')
                    self.handles.append((fmt, duplicate))
            finally:
                self.user.CloseClipboard()
        except Exception:
            self.cleanup()
            raise
        return self

    def open(self):
        for _ in range(50):
            if self.user.OpenClipboard(ctypes.c_void_p(self.window)):
                return
            time.sleep(.02)
        raise OSError('Clipboard is busy')

    def cleanup(self):
        for fmt, handle in self.handles:
            if fmt in (2, 9):
                ctypes.windll.gdi32.DeleteObject(ctypes.c_void_p(handle))
            else:
                self.kernel.GlobalFree(ctypes.c_void_p(handle))
        self.handles.clear()
        self.user.DestroyWindow(ctypes.c_void_p(self.window))

    def __exit__(self, *args):
        try:
            self.open()
            try:
                if not self.user.EmptyClipboard():
                    raise OSError('Cannot restore clipboard')
                while self.handles:
                    fmt, handle = self.handles[0]
                    if not self.user.SetClipboardData(fmt, ctypes.c_void_p(handle)):
                        raise OSError('Cannot restore clipboard format')
                    self.handles.pop(0)  # Windows owns the handle now.
            finally:
                self.user.CloseClipboard()
        finally:
            self.cleanup()


