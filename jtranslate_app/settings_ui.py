"""Explicit user-driven Sign in with ChatGPT for JTranslate's own storage."""
import queue
import threading
import tkinter as tk
from tkinter import ttk
from . import chatgpt_auth
from .config import Settings


def open_settings(parent):
    settings=Settings.load()
    window=tk.Toplevel(parent)
    window.title('JTranslate 設定・ChatGPT接続')
    window.resizable(False,False)
    frame=ttk.Frame(window,padding=18)
    frame.pack(fill='both',expand=True)
    source=tk.StringVar(value=settings.connection_source)
    ttk.Label(frame,text='翻訳に使う接続').pack(anchor='w')
    ttk.Radiobutton(frame,text='JTranslate専用のChatGPT接続',variable=source,value='jtranslate').pack(anchor='w')
    ttk.Radiobutton(frame,text='このPCのJHenkan接続を共有（コピーしない）',variable=source,value='jhenkan').pack(anchor='w')
    ttk.Label(frame,text='JTranslate専用アカウント').pack(anchor='w',pady=(12,0))
    account=tk.StringVar()
    account_box=ttk.Combobox(frame,textvariable=account,state='readonly',width=48)
    account_box.pack(fill='x',pady=4)
    accounts={}
    selected=[settings.chatgpt_account if settings.connection_source=='jtranslate' else '']
    model=tk.StringVar(value=settings.model)
    ttk.Label(frame,text='モデル').pack(anchor='w',pady=(8,0))
    model_box=ttk.Combobox(frame,textvariable=model,values=[settings.model,'gpt-6-luna'],width=48)
    model_box.pack(fill='x',pady=4)
    ttk.Label(frame,text='新規ログインはブラウザーで本人確認・利用枠の許可を行います。\n'
        '認証はJTranslate専用に保存し、JHenkanの接続は変更しません。',wraplength=430).pack(anchor='w',pady=8)
    status=ttk.Label(frame,text='現在の接続: '+('JHenkan共有' if settings.connection_source=='jhenkan' else 'JTranslate専用'))
    status.pack(anchor='w')
    results=queue.Queue()
    cancel=threading.Event()
    busy=[False]

    def refresh():
        accounts.clear()
        for item in chatgpt_auth.accounts():
            label=item.get('email','account')+' ['+item['client_id'][-8:]+']'
            accounts[label]=item['client_id']
        accounts['新しいアカウントを追加']=''
        account_box.configure(values=list(accounts))
        account.set(next((label for label,cid in accounts.items() if cid==selected[0]),'新しいアカウントを追加'))

    def changed(_event=None):
        selected[0]=accounts.get(account.get(),'')
    account_box.bind('<<ComboboxSelected>>',changed)

    def start(action):
        if busy[0]: return
        busy[0]=True
        status.configure(text='ブラウザーで確認してください…' if action=='signin' else 'モデルを確認中…')
        signin.configure(state='disabled')
        def worker():
            try:
                result=chatgpt_auth.sign_in(selected[0],cancel) if action=='signin' else chatgpt_auth.list_models(selected[0])
                results.put((action,result,None))
            except Exception:
                results.put((action,None,True))
        threading.Thread(target=worker,daemon=True).start()

    signin=ttk.Button(frame,text='Continue with ChatGPT',command=lambda:start('signin'))
    signin.pack(fill='x',pady=(10,4))
    ttk.Button(frame,text='専用接続のモデル一覧を読み込む',command=lambda:start('models')).pack(fill='x')

    def close():
        cancel.set()
        window.destroy()
    window.protocol('WM_DELETE_WINDOW',close)

    def save():
        if busy[0]:
            status.configure(text='接続処理の完了を待つかキャンセルしてください。')
            return
        if source.get()=='jtranslate':
            if not selected[0] or not chatgpt_auth.connected(selected[0]):
                status.configure(text='Continue with ChatGPTから接続してください。')
                return
            settings.chatgpt_account=selected[0]
        else:
            # Resolve the shared account from its own settings without copying credentials.
            from .config import legacy_data_dir
            import json
            try:
                legacy=json.loads((legacy_data_dir()/'settings.json').read_text(encoding='utf-8'))
                if legacy.get('provider')!='chatgpt' or not legacy.get('chatgpt_account'):
                    raise ValueError()
                settings.chatgpt_account=legacy['chatgpt_account']
            except (OSError,ValueError):
                status.configure(text='共有できるJHenkanのChatGPT設定がありません。')
                return
        settings.connection_source=source.get()
        settings.chatgpt_model=model.get().strip() or 'gpt-6-luna'
        settings.save()
        close()

    buttons=ttk.Frame(frame)
    buttons.pack(fill='x',pady=(12,0))
    ttk.Button(buttons,text='保存',command=save).pack(side='right')
    ttk.Button(buttons,text='キャンセル',command=close).pack(side='right',padx=6)

    def poll():
        if not window.winfo_exists(): return
        try: action,value,error=results.get_nowait()
        except queue.Empty: pass
        else:
            busy[0]=False
            signin.configure(state='normal')
            if error:
                status.configure(text='接続できませんでした。通信とブラウザーの許可を確認してください。')
            elif action=='signin':
                selected[0]=value
                source.set('jtranslate')
                refresh()
                status.configure(text='JTranslate専用の接続が完了しました。「保存」で利用を切り替えます。')
            else:
                model_box.configure(values=[item['slug'] for item in value])
                status.configure(text='専用アカウントで使えるモデルを選択してください。')
        parent.after(100,poll)
    refresh()
    poll()
    window.lift()
    return window
