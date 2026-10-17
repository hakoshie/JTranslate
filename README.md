# JTranslate

Windowsで文章を選択し、**Ctrl+M** で日本語訳する独立したタスクトレイ常駐アプリです。
他のアプリの設定・ログイン・APIキーは使用しません。
JHenkan由来のMITライセンスのコードを利用しています。[PROVENANCE.md](PROVENANCE.md)

## セットアップと起動

WindowsとPython 3.10以降が必要です。任意のフォルダーへcloneしてください。

```powershell
git clone https://github.com/hakoshie/JTranslate.git
cd JTranslate
.\setup.ps1
```

`setup.ps1`は、このフォルダー専用の`.venv`へ依存ライブラリを導入し、起動用ショートカットを作ります。
自動起動登録・認証・他アプリの設定変更は行いません。
以後は **JTranslate.lnk** をダブルクリックします。代替は **JTranslate.cmd** です。
常駐は1インスタンスで、コンソールを表示しません。終了はトレイの「訳 → 終了」。

## Sign in with ChatGPT

未ログインで起動すると設定画面を表示します。**Continue with ChatGPT** を押し、
自分のアカウントでブラウザーから本人確認と利用枠の許可を行ってください。
自動で認証や新規登録を開始することはありません。

JTranslateというアプリ名で、公式のオープンソースアプリ向け登録手順を使用します。
他アプリやCodexのclient ID・トークンを流用しません。
既存の専用アカウントの選択、別アカウント追加、再認証、モデル一覧取得に対応します。

設定は通常の利用者設定として `%LOCALAPPDATA%\JTranslate\settings.json`、
認証は同フォルダーの `chatgpt-auth.bin`（Windows DPAPI暗号化）へ保存します。
リポジトリへ設定・認証・ログを含めません。他アプリの保存先を探したり移植したりしません。

公式資料：

- [登録・認証](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [モデル一覧とResponses API](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)

## Thinking level

トレイの **設定・ChatGPTログイン → Thinking level** で選び、「保存」を押します。
再起動後も保存した値を使い、Responses APIの`reasoning.effort`へその値を明示送信します。
初期モデルは`gpt-6-luna`、初期値は速度優先の **none** です。サーバー既定値任せにはしません。

Lunaは`none / low / medium / high / xhigh / max`を選択できます。
他モデルはアカウントのモデル一覧から確認した対応値だけを表示します。
モデル変更後に現在値が未対応なら、分かるエラーを表示し、勝手に別の値へ変更しません。
高い設定では応答時間や利用枠が増える場合があります。
[Lunaの公式仕様](https://developers.openai.com/api/docs/models/gpt-6-luna)

## 操作

- 文章を選択して **Ctrl+M**。元の入力欄は書き換えません。
- ポップアップ上部をドラッグして移動。
- 端・四隅を両矢印カーソルでリサイズ。最小320×100、モニター作業領域内に制限。
- 手動サイズをプロセス内で維持。本文は幅に合わせて折り返し、長文は縦スクロール。
- 右クリックの「翻訳結果をコピー」で全文コピー。
- 外クリック・Esc・×で閉じます。リサイズ・ドラッグ・メニュー内操作では閉じません。
- トレイから設定・一時停止・終了。

枠なしの軽い表示で、元アプリのフォーカスを奪いません。閉じた後に古い結果を再表示しません。
翻訳中の連打は無視します。最大100,000文字を約3,000文字ずつ順番に翻訳します。
長文は時間と利用枠を使い、分割境界の文脈には限界があります。

## 改行とプライバシー

明確な文中の行末折返しだけを保守的に整理し、空行・文末・見出し・箇条書き・
インデント・コードを維持します。UIの折返しでコピー本文に改行文字は追加しません。

選択取得はWindows標準選択API／UI Automationです。クリップボードの既存本文を送信せず、
Ctrl+Cも送信しません。空選択・非対応欄・パスワード欄・取得中の別ウィンドウへの移動では
送信しません。画面全体の取得・画像・OCRは使用しません。
一部PDF描画領域や管理者アプリなど、選択取得できないアプリがあります。
本文や認証情報はログへ記録しません。コピー操作時だけクリップボードを変更します。

## アイコン

承認済みの水色の「訳」を使用します。MSゴシックの輪郭を高解像度で描き、
16／20／24／32px等を個別にアンチエイリアス付きで生成した多サイズICOです。
大きい1枚をWindows側で無理に縮小する方式を避けています。
ランタイムは同梱のPNG／ICOだけを使用し、フォントファイルを再配布しません。
再生成する場合はWindows上の`tools/render_icons.py --output <出力先>`を使用します。

## 開発・テスト

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe tests\windows_resize_smoke.py
.\.venv\Scripts\python.exe tests\windows_translation_smoke.py
```

Windows実動テストは合成文だけを使い、翻訳応答・認証はテスト用データに置き換えます。
設定保存テストも一時フォルダーだけを使います。実ユーザーの認証は行いません。
