from typing import Dict, Optional
from AppKit import NSWorkspace, NSRunningApplication
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)

def get_current_app() -> Optional[NSRunningApplication]:
    return NSWorkspace.sharedWorkspace().frontmostApplication()


def get_app_name(app: NSRunningApplication) -> str:
    return app.localizedName()


def get_app_title(app: NSRunningApplication) -> str:
    pid = app.processIdentifier()
    options = kCGWindowListOptionOnScreenOnly
    windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID)

    for window in windowList:
        lookupPid = window['kCGWindowOwnerPID']
        if (lookupPid == pid):
            return window.get('kCGWindowName', 'Non-detected window title')
    return ""

