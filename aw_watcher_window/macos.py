from typing import Dict, Optional
from AppKit import NSWorkspace
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)

def getInfo() -> Optional[Dict[str, str]]:
    app = NSWorkspace.sharedWorkspace().frontmostApplication()
    if app:
        app_name = app.localizedName()
        title = getTitle(app.processIdentifier())

        print("appname: " + app_name + ", title: "+ title)
        return {"appname": app_name, "title": title}

    else:
        return None

def getTitle(pid: int) -> str:
    options = kCGWindowListOptionOnScreenOnly
    windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID)

    for window in windowList:
        lookupPid = window['kCGWindowOwnerPID']
        if (pid == lookupPid):
            return str(window.get('kCGWindowName', 'Non-detected window title'))
    return ""

