import queue
from unittest.mock import Mock,patch
from jtranslate_app.translate_app import TranslationApp

def make_app():
    app=TranslationApp.__new__(TranslationApp)
    app.root=Mock();app.hotkey=Mock();app.icon=Mock();app.events=queue.Queue()
    return app

def test_startup_does_not_open_settings_or_read_or_refresh_authentication():
    app=make_app()
    with patch('jtranslate_app.translate_app.diagnostics.startup'),patch('jtranslate_app.translate_app.chatgpt_auth.connected',side_effect=AssertionError('startup must not inspect authentication')),patch('jtranslate_app.translate_app.Settings.load',side_effect=AssertionError('startup must not change settings')):
        app.run()
    app.hotkey.start.assert_called_once()
    app.icon.run_detached.assert_called_once()
    app.icon.notify.assert_not_called()
    assert app.events.empty()
    app.root.mainloop.assert_called_once()

def test_hotkey_registration_error_is_still_reported():
    app=make_app();app.hotkey.start.side_effect=OSError('synthetic hotkey collision')
    with patch('jtranslate_app.translate_app.diagnostics.startup'),patch('jtranslate_app.translate_app.messagebox.showerror') as error:
        app.run()
    error.assert_called_once()
    app.root.destroy.assert_called_once()
    app.icon.run_detached.assert_not_called()


def test_manual_mode_starts_without_hotkey_or_tray():
    app = make_app()
    app.resident = False
    with patch('jtranslate_app.translate_app.diagnostics.startup'):
        app.run()
    app.hotkey.start.assert_not_called()
    app.icon.run_detached.assert_not_called()
    app.root.mainloop.assert_called_once()
