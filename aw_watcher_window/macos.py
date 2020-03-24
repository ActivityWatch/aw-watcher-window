from typing import Dict, Optional
from AppKit import NSObject, NSWorkspace, NSRunningApplication, NSWorkspaceDidActivateApplicationNotification
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)
from PyObjCTools import AppHelper


class Observer(NSObject):
    app = NSWorkspace.sharedWorkspace().frontmostApplication()

    def get_front_app(self) -> NSRunningApplication:
        return self.app
    def set_front_app_(self) -> NSRunningApplication:
        self.app = NSWorkspace.sharedWorkspace().frontmostApplication()

observer = Observer.new()
NSWorkspace.sharedWorkspace().notificationCenter().addObserver_selector_name_object_(
        observer,
        "set_front_app:",
        NSWorkspaceDidActivateApplicationNotification,
        None)

AppHelper.runConsoleEventLoop()

def get_current_app() -> NSRunningApplication:
    return observer.get_front_app()


def get_app_name(app: NSRunningApplication) -> str:
    return app.localizedName()


def get_app_title(app: NSRunningApplication) -> str:
    pid = app.processIdentifier()
    options = kCGWindowListOptionOnScreenOnly
    windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID)

    for window in windowList:
        lookupPid = window['kCGWindowOwnerPID']
        if (lookupPid == pid):
            print(window)
            return window.get('kCGWindowName', 'Non-detected window title')

    return "Couldn't find title by pid"

