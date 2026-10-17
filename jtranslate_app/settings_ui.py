"""Explicit per-user ChatGPT sign-in and validated Responses thinking settings."""
import queue
import threading
import tkinter as tk
from tkinter import ttk
from . import chatgpt_auth
from .config import Settings
from .reasoning import supported_efforts, validate_effort, ReasoningConfigurationError


def open_settings(parent):
    settings=Settings.load()
    window=tk.Toplevel(parent)
    window.title('JTranslate 設定・ChatGPTログイン')
    window.resizable(False,False)
    frame=ttk.Frame(window,padding=18)
    frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='JTranslateにサインインするアカウント').pack(anchor='w')
    account=tk.StringVar()
    account_box=ttk.Combobox(frame,textvariable=account,state='readonly',width=49)
    account_box.pack(fill='x',pady=4)
    accounts={}
    selected=[settings.chatgpt_account]
    catalog=dict(settings.reasoning_options) if isinstance(settings.reasoning_options,dict) else {}
    model=tk.StringVar(value=settings.model)
    ttk.Label(frame,text='モデル').pack(anchor='w',pady=(8,0))
    model_box=ttk.Combobox(frame,name='model',textvariable=model,values=[settings.model],state='readonly',width=49)
    model_box.pack(fill='x',pady=4)
    effort=tk.StringVar(value=settings.reasoning_effort)
    ttk.Label(frame,text='Thinking level（推論の強さ）').pack(anchor='w',pady=(8,0))
    effort_box=ttk.Combobox(frame,name='reasoning_effort',textvariable=effort,state='readonly',width=49)
    effort_box.pack(fill='x',pady=4)
    ttk.Label(frame,text='none：推論オフ／速度優先。高い設定は応答時間や利用枠が増える場合があります。',wraplength=440).pack(anchor='w')
    ttk.Label(frame,text='未ログインなら Continue with ChatGPT からブラウザーで本人確認・利用許可を行ってください。\n'
        '他のアプリのログインや設定は使用しません。',wraplength=440).pack(anchor='w',pady=10)
    status=ttk.Label(frame,text='',wraplength=440)
    status.pack(anchor='w')
    results=queue.Queue()
    cancel=threading.Event()
    busy=[False]
    poll_timer=[None]

    def refresh_efforts(*_):
        choices=supported_efforts(model.get(),catalog.get(model.get()))
        effort_box.configure(values=choices,state='readonly' if choices else 'disabled')
        try: validate_effort(model.get(),effort.get(),catalog.get(model.get()))
        except ReasoningConfigurationError as exc: status.configure(text=str(exc))
        else: status.configure(text='選択したThinking levelをそのまま送信します。')

    def refresh_accounts():
        accounts.clear()
        for item in chatgpt_auth.accounts():
            label=item.get('email','account')+' ['+item['client_id'][-8:]+']'
            accounts[label]=item['client_id']
        accounts['新しいアカウントを追加']=''
        account_box.configure(values=list(accounts))
        account.set(next((label for label,cid in accounts.items() if cid==selected[0]),'新しいアカウントを追加'))

    def changed(_event=None):
        selected[0]=accounts.get(account.get(),'')
        catalog.clear()
        refresh_efforts()
    account_box.bind('<<ComboboxSelected>>',changed)
    model.trace_add('write',refresh_efforts)
    effort.trace_add('write',refresh_efforts)

    def start(action):
        if busy[0]: return
        if action=='models' and not selected[0]:
            status.configure(text='先にContinue with ChatGPTからサインインしてください。')
            return
        busy[0]=True
        cid=selected[0]
        status.configure(text='ブラウザーで確認してください…' if action=='signin' else 'モデルを確認中…')
        signin.configure(state='disabled')
        def worker():
            try:
                result=chatgpt_auth.sign_in(cid,cancel) if action=='signin' else chatgpt_auth.list_models(cid,include_capabilities=True)
                results.put((action,result,None))
            except Exception: results.put((action,None,True))
        threading.Thread(target=worker,daemon=True).start()

    signin=ttk.Button(frame,text='Continue with ChatGPT',command=lambda:start('signin'))
    signin.pack(fill='x',pady=(10,4))
    ttk.Button(frame,text='このアカウントのモデル一覧を読み込む',command=lambda:start('models')).pack(fill='x')

    def cleanup(event=None):
        if event is not None and event.widget is not window: return
        cancel.set()
        if poll_timer[0] is not None:
            try: parent.after_cancel(poll_timer[0])
            except tk.TclError: pass
            poll_timer[0]=None
    window.bind('<Destroy>',cleanup)

    def close():
        cleanup()
        window.destroy()
    window.protocol('WM_DELETE_WINDOW',close)

    def save():
        if busy[0]:
            status.configure(text='接続処理の完了を待つかキャンセルしてください。')
            return
        try: validate_effort(model.get(),effort.get(),catalog.get(model.get()))
        except ReasoningConfigurationError as exc:
            status.configure(text=str(exc));return
        if not selected[0] or not chatgpt_auth.connected(selected[0]):
            status.configure(text='Continue with ChatGPTからサインインしてください。');return
        settings.chatgpt_account=selected[0]
        settings.chatgpt_model=model.get()
        settings.reasoning_effort=effort.get()
        settings.reasoning_options=dict(catalog)
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
            if error: status.configure(text='接続できませんでした。通信とブラウザーの許可を確認してください。')
            elif action=='signin':
                selected[0]=value
                catalog.clear()
                refresh_accounts()
                start('models')
            else:
                catalog.clear()
                catalog.update({item['slug']:item.get('reasoning_efforts',[]) for item in value})
                model_box.configure(values=[item['slug'] for item in value])
                refresh_efforts()
        poll_timer[0]=parent.after(100,poll)
    refresh_accounts()
    refresh_efforts()
    poll()
    window.lift()
    return window
