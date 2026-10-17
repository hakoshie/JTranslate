"""Reproduce cross-thread owner notification blocking without any clipboard API."""
import ctypes,threading,time,json
from ctypes import wintypes
from jtranslate_app.browser_clipboard import _pump_window_messages
u=ctypes.WinDLL('user32',use_last_error=True)
u.CreateWindowExW.restype=wintypes.HWND
u.SendMessageTimeoutW.argtypes=(wintypes.HWND,wintypes.UINT,wintypes.WPARAM,wintypes.LPARAM,
                               wintypes.UINT,wintypes.UINT,ctypes.POINTER(ctypes.c_size_t))
u.PeekMessageW.argtypes=(ctypes.POINTER(wintypes.MSG),wintypes.HWND,wintypes.UINT,wintypes.UINT,wintypes.UINT)
window=u.CreateWindowExW(0,'STATIC','Synthetic clipboard owner message test',0,0,0,0,0,None,None,None,None)
assert window
answers=[]
def send(timeout):
    result=ctypes.c_size_t()
    answers.append(bool(u.SendMessageTimeoutW(window,0x0307,0,0,2,timeout,ctypes.byref(result))))
try:
    sender=threading.Thread(target=send,args=(150,));sender.start();sender.join()
    assert answers==[False],'owner without pump should block synchronous notification'
    sender=threading.Thread(target=send,args=(1000,));sender.start()
    msg=wintypes.MSG();deadline=time.monotonic()+2
    while sender.is_alive() and time.monotonic()<deadline:
        _pump_window_messages(u,window)
        time.sleep(.005)
    sender.join(.1)
    assert answers==[False,True]
    print(json.dumps({'without_message_pump':'timed_out','with_message_pump':'completed',
                      'message':'WM_DESTROYCLIPBOARD','clipboard_api_called':False}))
finally:u.DestroyWindow(ctypes.c_void_p(window))
