# JTranslate

Windowsの文章を選択して **Ctrl+M** で日本語訳する、独立したタスクトレイ常駐アプリです。
JHenkanに由来するMITライセンスのソースを使用しています。由来は [PROVENANCE.md](PROVENANCE.md)。

## このPCの本体と起動

本体は **`C:\Users\hakos\Downloads\tools\JTranslate`** です。
同じフォルダーの **JTranslate.lnk** をダブルクリックすると、コンソールなしで起動します。
代替は **JTranslate.cmd**。二重起動はしません。Windowsログイン時の自動起動は設定しません。

このPCでは既存のPython仮想環境を読み取り利用できます。ソースの実行場所と設定・認証は
JTranslate専用です。Python依存環境も独立させたい場合は、後述の `setup.ps1` を実行します。

## 操作

- 文章を選択して **Ctrl+M**。入力欄は書き換えません。
- 上部の「⠿ 日本語訳」をドラッグして移動。
- 端や四隅の両矢印カーソルをドラッグしてサイズ変更。最小320×100、作業領域内に制限。
- 手動で変更したサイズは次の結果にも維持します（プロセス内）。本文は幅に合わせて折り返します。
- 長文は縦スクロール。右クリックの「翻訳結果をコピー」で全文コピー。
- 外クリック・Esc・右上の×で閉じます。ドラッグ、リサイズ、メニュー内操作では閉じません。
- トレイの **T → 設定・ChatGPTログイン／一時停止／終了**。

枠なしの軽い表示で、元アプリのフォーカスを奪いません。閉じた後の古い応答は再表示しません。
翻訳中の連打は無視します。最大100,000文字を約3,000文字ずつ翻訳します。
分割境界の文脈には限界があり、長文は時間と既存サービスの利用枠を使います。

## JTranslate自身のSign in with ChatGPT

トレイの **設定・ChatGPTログイン → Continue with ChatGPT** から、ブラウザーで本人が
ログインと利用枠の許可を行います。新規接続ではアプリ名 **JTranslate** で登録します。
既存アプリのclient IDやトークンをJTranslateの新規登録へ流用しません。

独立設定は `%LOCALAPPDATA%\JTranslate\settings.json`、認証は同フォルダーの
`chatgpt-auth.bin`（Windows DPAPI暗号化）です。別アカウントの追加・既存専用アカウントの
再認証・モデル一覧取得に対応します。ログイン後は「保存」で使用する接続を切り替えます。
コード作成中に新規ログイン・連携承認・実トークン生成は実行していません。
実際の新規接続はユーザーのブラウザー操作が必要です。

[公式のOSS向け登録・認証手順](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
に沿い、動的登録・PKCE・state/nonce検証・IDトークン署名検証・利用権限検証を使用します。
これは一般商用アプリ向けの固定client IDやCodexのclient IDを借用する方式ではありません。
利用可否はアカウント、サービスの提供条件・利用枠に従います。

このPCでは、専用設定がまだない間は既存JHenkanのChatGPT接続を互換利用できます。
設定画面で「このPCのJHenkan接続を共有」を選ぶ方式です。認証情報をコピーせず、
JHenkan側の既存登録・保存先で通常のトークン更新を行います。
JTranslate専用接続へ切り替えてもJHenkanのログインを解除しません。
現在確認済みの共有設定は **ChatGPT sign-in / gpt-6-luna / reasoning none** です。

## 改行とプライバシー

PDF等の文中の行末折返しは、明確な継続行だけを保守的に連結し、翻訳プロンプトでも
自然な段落へ整えるよう指示します。空行、文末、箇条書き、見出し、インデント、
フェンス付きコードは維持します。曖昧な改行は機械的には削除しません。
UIの折返しは表示だけで、コピーする本文に追加の改行は挿入しません。

選択取得はWindows標準選択API／UI Automationです。既存クリップボードの本文を送らず、
Ctrl+Cも送信しません。空選択・非対応欄・パスワード欄・取得中の別ウィンドウへの移動では
送信しません。画像・OCR・画面全体の取得は行いません。
UI Automation非対応アプリ、管理者アプリ、一部PDF描画領域では取得できない場合があります。
本文と認証情報はログに残しません。コピー操作時だけクリップボードが翻訳結果になります。

## 開発・テスト・依存環境

```powershell
# 初回に専用Python環境を作りたい場合（自動起動登録・ログインは行いません）
.\setup.ps1

# 仮想環境作成後
.\.venv\Scripts\python.exe -m pytest -q
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe tests\windows_resize_smoke.py
.\.venv\Scripts\python.exe tests\windows_translation_smoke.py
```

pytestは開発用です。必要な場合だけ `python -m pip install pytest` を追加してください。
Windows実動テストは合成入力欄へフォーカスを移します。API応答はテスト用に置換し、
クリップボードを保存・復元します。実APIは非機密の図書館の例文で別途確認しています。

ソースは `jtranslate_app/`、エントリーは `translate.pyw` です。
この本体フォルダー自体をGit管理します。秘密値、認証、個人設定、ログ、仮想環境、
このPC専用のショートカット・検証画像はGit対象外です。remote、push、PRは作成していません。
