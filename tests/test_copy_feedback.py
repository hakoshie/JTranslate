from unittest.mock import Mock,patch
import pyperclip
from jtranslate_app.translate_app import TranslationApp

def make_app():
    app=TranslationApp.__new__(TranslationApp)
    app.result='Full original translation\n'+'Long line '*100
    app.root=Mock();app.root.winfo_viewable.return_value=True
    app.copy_feedback=Mock();app.text=Mock();app.fit_height=Mock()
    app._copy_feedback_timer=None;app.closed=False;app.generation=1;app.resizing=None
    app.root.after.return_value='feedback-timer'
    return app

def test_copy_reports_success_only_after_complete_original_result_copied():
    app=make_app()
    with patch('jtranslate_app.translate_app.pyperclip.copy') as copy:
        assert app.copy_result() is True
        copy.assert_called_once_with(app.result)
    assert app.copy_feedback.configure.call_args.kwargs['text']=='コピーしました'
    assert app.root.after.call_args.args[0]==1800

def test_copy_failure_reports_failure_without_exception_or_success_text():
    app=make_app()
    with patch('jtranslate_app.translate_app.pyperclip.copy',side_effect=pyperclip.PyperclipException('PRIVATE')):
        assert app.copy_result() is False
    text=app.copy_feedback.configure.call_args.kwargs['text']
    assert 'コピーできませんでした' in text and 'PRIVATE' not in text and 'コピーしました' not in text

def test_empty_result_never_claims_success_or_touches_clipboard():
    app=make_app();app.result=''
    with patch('jtranslate_app.translate_app.pyperclip.copy') as copy:
        assert app.copy_result() is False
        copy.assert_not_called()
    app.copy_feedback.configure.assert_not_called()

def test_repeated_copy_replaces_old_feedback_timer():
    app=make_app()
    with patch('jtranslate_app.translate_app.pyperclip.copy'):
        app.copy_result();app.copy_result()
    app.root.after_cancel.assert_called_once_with('feedback-timer')

def test_hide_cancels_feedback_without_reopening_or_refitting():
    app=make_app();app._copy_feedback_timer='feedback-timer'
    app.hide()
    app.root.after_cancel.assert_called_once_with('feedback-timer')
    app.copy_feedback.pack_forget.assert_called_once()
    app.fit_height.assert_not_called()
    app.root.withdraw.assert_called_once()


def test_reentrant_failure_keeps_its_own_message_and_expiry():
    app=make_app();nested=[False]
    def fit():
        if not nested[0]:
            nested[0]=True
            app.show_copy_feedback('コピーできませんでした',False)
    app.fit_height.side_effect=fit
    app.show_copy_feedback('コピーしました',True)
    assert app.copy_feedback.configure.call_args.kwargs['text']=='コピーできませんでした'
    app.root.after.assert_called_once()
    assert app.root.after.call_args.args[0]==4000

def test_obsolete_expiry_cannot_clear_new_feedback():
    app=make_app()
    app.show_copy_feedback('old',True)
    expire=app.root.after.call_args.args[1]
    app.show_copy_feedback('new',True)
    app.copy_feedback.pack_forget.reset_mock()
    expire()
    app.copy_feedback.pack_forget.assert_not_called()
