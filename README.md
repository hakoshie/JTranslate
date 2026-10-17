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
- 手動で変えた幅をプロセス中に維持。高さは本文の実際の折り返し量に合わせて伸縮します。
  モニターの作業領域いっぱいまで広げても収まらない長文だけ縦スクロールします。幅を変えた後も高さを測り直します。
- 訳文を右クリック1回で全文コピー。スクロールで見えていない部分も含みます。
- 外クリック・Esc・×で閉じます。リサイズ・ドラッグ・右クリックコピー中は閉じません。
- トレイから設定・一時停止・終了。

枠なしの軽い表示で、元アプリのフォーカスを奪いません。閉じた後に古い結果を再表示しません。
翻訳中のEsc・×・外クリックは表示とその結果の採用を取り消します。送信済みの通信は現在の区切りの完了まで続きます。
取り消し後は次の分割送信を行わず、戻った結果を破棄します。通信が終わるまで新しいCtrl+Mは無視します。
サーバー側の即時停止や利用枠の返却は保証しません。完了後のEscは表示を閉じます。
翻訳中の連打は無視します。最大100,000文字を約3,000文字ずつ順番に翻訳します。
長文は時間と利用枠を使い、分割境界の文脈には限界があります。

## 改行とプライバシー

明確な文中の行末折返しだけを保守的に整理し、空行・文末・見出し・箇条書き・
インデント・コードを維持します。UIの折返しでコピー本文に改行文字は追加しません。

選択取得はWindows標準選択API／UI Automationを優先します。ブラウザ本文で取得できない場合は、
Chrome／Edge／Firefoxなどのブラウザプロセスに限定してCtrl+Cを送り、新しくコピーされた選択文を取得します。
コピー前のクリップボード全形式を複製し、コピー後はロック中に元データを復元します。
保持できない形式がある場合、取得を中止してクリップボードを変更しません。
既存クリップボードの本文は翻訳対象に使いません。コピー完了の更新番号と所有プロセスを確認し、
空選択・パスワード欄・選択のない入力欄・取得中の別ウィンドウへの移動では送信しません。
他アプリが途中でコピーした新しい内容は上書きせず、その取得を中止します。
コピー待ち中も専用ウィンドウのWindows通知を処理し、ブラウザのコピーを待たせないようにします。
使用中で直ちに復元できない場合は、元データをディスクへ保存せずアプリのRAM内に保持します。
専用の一時マーカーが残る場合だけ後で復元し、新しいコピーがあれば上書きしません。
復元待ちの案内中はJTranslateを終了せずお待ちください。
画面全体の取得・画像・OCRは使いません。
一部PDF描画領域や管理者アプリなど、選択取得できないアプリがあります。
本文や認証情報はログへ記録しません。右クリックでコピーした結果は、そのままクリップボードに残します。

## エラー表示と診断

翻訳結果とエラー・案内文は同じ高さ調整を使います。以前の手動高さが小さくても、実際の折返しと文字の高さを測って広げます。
短文は縮み、手動の幅は保持します。モニターの作業領域に収まらない長文だけ縦スクロールで全文を読めます。

取得失敗はキー解放待ち、Windows選択API、クリップボード保持、コピー完了、コピー元確認、復元失敗を区別します。
`%LOCALAPPDATA%\JTranslate\selection-diagnostics.log`には、失敗分類・処理段階・キー状態・稼働コードの指紋だけを記録します。
本文、クリップボード内容、URL、ウィンドウ名、認証情報は記録しません。
ログは約64KiBを超えると直近100行へ縮小します。診断ログはリポジトリに含めません。

## アイコン

承認済みの水色の「訳」を使用します。MSゴシックの輪郭を高解像度で描き、
16／20／24／32px等を個別にアンチエイリアス付きで生成した多サイズICOです。
大きい1枚をWindows側で無理に縮小する方式を避けています。
ランタイムは同梱のPNG／ICOだけを使用し、フォントファイルを再配布しません。
再生成する場合はWindows上の`tools/render_icons.py --output <出力先>`を使用します。

Windows通知にも専用の32pxアイコンを明示し、通知元ウィンドウの大小アイコンと
アプリ識別子`JTranslate`を設定します。古い通知履歴やOS全体のキャッシュは変更しません。

## 開発・テスト

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe tests\windows_resize_smoke.py
.\.venv\Scripts\python.exe tests\windows_error_layout_smoke.py
.\.venv\Scripts\python.exe tests\windows_autoheight_smoke.py
.\.venv\Scripts\python.exe tests\windows_owner_message_smoke.py
.\.venv\Scripts\python.exe tests\windows_right_click_smoke.py
.\.venv\Scripts\python.exe tests\windows_translation_smoke.py
.\.venv\Scripts\python.exe -m pytest -q tests\windows_clipboard_smoke.py
.\.venv\Scripts\python.exe tests\windows_notification_smoke.py
```

Windows実動テストは常駐を終了した検証環境で手動実行してください。合成文だけを使い、翻訳応答・認証はテスト用データに置き換えます。
設定保存テストも一時フォルダーだけを使います。実ユーザーの認証は行いません。
