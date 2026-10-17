from unittest.mock import Mock,patch
import ctypes
from jtranslate_app.translate_app import TranslationApp

def test_active_drag_is_not_dismissed_by_pointer_leaving_window():
    app=TranslationApp.__new__(TranslationApp)
    app.root=Mock();app.root.winfo_viewable.return_value=True
    app.root.winfo_pointerxy.return_value=(-10000,-10000)
    app.contains_point=Mock(return_value=False);app.hide=Mock()
    app.dragging=True;app.resizing=None;app.mouse_down=app.escape_down=False
    with patch.object(ctypes.windll.user32,'GetAsyncKeyState',side_effect=lambda key:0x8000 if key==1 else 0):
        app.dismiss_outside()
    app.hide.assert_not_called()

def test_escape_still_dismisses_active_drag():
    app=TranslationApp.__new__(TranslationApp)
    app.root=Mock();app.root.winfo_viewable.return_value=True
    app.contains_point=Mock(return_value=False);app.hide=Mock()
    app.dragging=True;app.resizing=None;app.mouse_down=app.escape_down=False
    with patch.object(ctypes.windll.user32,'GetAsyncKeyState',side_effect=lambda key:0x8000 if key==0x1b else 0):
        app.dismiss_outside()
    app.hide.assert_called_once()


def test_normal_outside_click_still_dismisses_after_drag_finished():
    app=TranslationApp.__new__(TranslationApp)
    app.root=Mock();app.root.winfo_viewable.return_value=True
    app.root.winfo_pointerxy.return_value=(-10000,-10000)
    app.contains_point=Mock(return_value=False);app.hide=Mock()
    app.dragging=False;app.resizing=None;app.mouse_down=app.escape_down=False
    with patch.object(ctypes.windll.user32,'GetAsyncKeyState',side_effect=lambda key:0x8000 if key==1 else 0):
        app.dismiss_outside()
    app.hide.assert_called_once()
