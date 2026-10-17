"""Safe, fixed capture error categories; never include source/clipboard content."""
MESSAGES={
    'hotkey_not_released':'Ctrl+M のキーが押されたままです。キーを離してからもう一度お試しください。',
    'uia_failed':'Windowsから選択範囲を取得できませんでした。本文を選択してもう一度お試しください。',
    'uia_timeout':'選択範囲の確認に時間がかかりました。少し待ってからもう一度お試しください。',
    'native_timeout':'選択元の入力欄が応答しなかったため取得を中止しました。',
    'clipboard_busy':'他のアプリがクリップボードを使用中のため取得できませんでした。少し待ってからお試しください。',
    'clipboard_preserve':'現在のクリップボードを安全に保持できない形式のため、選択取得を中止しました。現在の内容は変更していません。',
    'clipboard_access':'クリップボードへのアクセスに失敗したため選択取得を中止しました。',
    'clipboard_changed':'取得中に別のアプリがクリップボードを更新したため中止しました。新しい内容は上書きしていません。',
    'copy_owner_missing':'コピー元を確認できなかったため取得を中止しました。別のアプリの内容は翻訳していません。',
    'copy_timeout':'ブラウザから選択文のコピーを確認できませんでした。本文を選択し、Ctrl+M のキーを離してからお待ちください。',
    'clipboard_restore_pending':'元のクリップボードはアプリ内に保持し、復元を待っています。翻訳は中止しました。JTranslateを終了せずにお待ちください。',
    'clipboard_restore':'元のクリップボードの復元を完了できなかったため翻訳を中止しました。',
    'selection_too_large':'選択文が大きすぎるため取得を中止しました。短い範囲に分けてお試しください。',
}

class CaptureFailure(OSError):
    def __init__(self,code):
        if code not in MESSAGES:raise ValueError('Unknown capture error category')
        self.code=code
        super().__init__(code)

    @property
    def user_message(self):
        return MESSAGES[self.code]
