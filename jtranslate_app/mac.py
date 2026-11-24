"""macOS status item and selection-only hotkey; never simulates Copy."""
import AppKit as cocoa
import ApplicationServices as ax
import objc


class TrayAction(cocoa.NSObject):
    def invoke_(self, item):
        self.callback(str(item.representedObject()))


class MacTray:
    def __init__(self, callback, is_paused):
        self.callback = is_paused
        self.target = TrayAction.alloc().init()
        self.target.callback = callback

    def run_detached(self):
        self.bar = cocoa.NSStatusBar.systemStatusBar()
        self.item = self.bar.statusItemWithLength_(cocoa.NSVariableStatusItemLength)
        self.item.button().setTitle_("訳")
        menu = cocoa.NSMenu.alloc().init()
        for title, event in (
            ("翻訳結果を表示", "show"),
            ("一時停止", "pause"),
            ("設定・ChatGPTログイン", "settings"),
            ("終了", "quit"),
        ):
            item = cocoa.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, "invoke:", "")
            item.setTarget_(self.target)
            item.setRepresentedObject_(event)
            menu.addItem_(item)
            if event == "pause":
                self.pause = item
        self.item.setMenu_(menu)

    def update_menu(self):
        self.pause.setState_(int(self.callback()))

    def stop(self):
        self.bar.removeStatusItem_(self.item)


class MacHotkey:
    def __init__(self, callback):
        self.callback = callback
        self.monitor = None

    def start(self):
        if not ax.AXIsProcessTrustedWithOptions({ax.kAXTrustedCheckOptionPrompt: True}):
            # The status menu remains usable while the user grants permissions.
            return
        self.monitor = cocoa.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(
            cocoa.NSEventMaskKeyDown, self.handle
        )

    def handle(self, event):
        mods = event.modifierFlags() & (cocoa.NSEventModifierFlagControl |
            cocoa.NSEventModifierFlagOption | cocoa.NSEventModifierFlagCommand |
            cocoa.NSEventModifierFlagShift)
        if mods == cocoa.NSEventModifierFlagControl and event.keyCode() == 46 and not event.isARepeat():
            self.callback()

    def stop(self):
        if self.monitor is not None:
            cocoa.NSEvent.removeMonitor_(self.monitor)
            self.monitor = None


def foreground_pid():
    app = cocoa.NSWorkspace.sharedWorkspace().frontmostApplication()
    return int(app.processIdentifier()) if app else 0


def selected_text(expected_pid):
    with objc.autorelease_pool():
        if not expected_pid or foreground_pid() != expected_pid:
            return None
        app = ax.AXUIElementCreateApplication(expected_pid)
        err, element = ax.AXUIElementCopyAttributeValue(app, ax.kAXFocusedUIElementAttribute, None)
        if err or element is None:
            return None
        err, role = ax.AXUIElementCopyAttributeValue(element, ax.kAXRoleAttribute, None)
        if err or role not in ("AXTextArea", "AXTextField", "AXStaticText", "AXWebArea"):
            return None
        err, subrole = ax.AXUIElementCopyAttributeValue(element, ax.kAXSubroleAttribute, None)
        if err not in (0, ax.kAXErrorAttributeUnsupported, ax.kAXErrorNoValue) or subrole == "AXSecureTextField":
            return None
        err, text = ax.AXUIElementCopyAttributeValue(element, ax.kAXSelectedTextAttribute, None)
        if not err and isinstance(text, str) and foreground_pid() == expected_pid:
            return text
        return None
