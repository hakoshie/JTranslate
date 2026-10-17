"""Bounded metadata-only diagnostics. No text, clipboard data, URLs or tokens."""
import hashlib,json,os,re,threading,time,types
from .config import data_dir
from .capture_errors import MESSAGES

REVISION=3
_lock=threading.Lock()
_EVENTS={'startup','request','wait_release','native','uia','browser_gate','snapshot','copy_sent',
         'copy_wait','capture_done','capture_failed','provider_failed'}
_BOOLEANS={'ctrl_down','m_down','can_copy','supported','foreground_matches'}
_NUMBERS={'elapsed_ms','formats','pid','revision'}
_ENUMS={'status':{'selected','blocked','unsupported','empty','text','not_native','other'},
        'owner':{'same_browser','our_marker','missing','other'},
        'error_type':{'OSError','RuntimeError','TimeoutExpired','JSONDecodeError','CaptureFailure','ValueError','UnicodeDecodeError','PermissionError','FileNotFoundError','AttributeError','TypeError','NameError','IndexError','other'}}

def record(event,**details):
    if event not in _EVENTS:return
    item={'time':round(time.time(),3),'event':event}
    for key,value in details.items():
        if key in _BOOLEANS and isinstance(value,bool):item[key]=value
        elif key in _NUMBERS and isinstance(value,int) and 0<=value<100_000_000:item[key]=value
        elif key in _ENUMS and isinstance(value,str) and value in _ENUMS[key]:item[key]=value
        elif key=='code' and isinstance(value,str) and value in MESSAGES:item[key]=value
        elif key=='signature' and isinstance(value,str) and re.fullmatch('[0-9a-f]{12}',value):item[key]=value
    try:
        with _lock:
            folder=data_dir();folder.mkdir(parents=True,exist_ok=True)
            path=folder/'selection-diagnostics.log'
            if path.exists() and path.stat().st_size>65536:
                tail=path.read_text(encoding='utf-8').splitlines()[-100:]
                path.write_text('\n'.join(tail)+'\n',encoding='utf-8')
            with path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(item)+'\n')
    except (OSError,ValueError):pass

def loaded_signature():
    from .translation import capture_selected,read_selection
    from .browser_clipboard import ClipboardCapture
    from .translate_app import TranslationApp
    def freeze(value):
        if isinstance(value,types.CodeType):
            return {'bytecode':value.co_code.hex(),'names':value.co_names,
                    'constants':[freeze(item) for item in value.co_consts]}
        if isinstance(value,bytes):return {'bytes':value.hex()}
        if isinstance(value,tuple):return [freeze(item) for item in value]
        if isinstance(value,frozenset):return sorted(freeze(item) for item in value)
        if value is None or isinstance(value,(str,int,float,bool)):return value
        return type(value).__name__
    data=[freeze(fn.__code__) for fn in
          (capture_selected,read_selection,ClipboardCapture.fresh_text,TranslationApp.display)]
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()[:12]

def startup():
    record('startup',revision=REVISION,pid=os.getpid(),signature=loaded_signature())


def hotkey_state():
    import ctypes
    user=ctypes.windll.user32
    return {'ctrl_down':bool(user.GetAsyncKeyState(0x11)&0x8000),
            'm_down':bool(user.GetAsyncKeyState(0x4d)&0x8000)}
