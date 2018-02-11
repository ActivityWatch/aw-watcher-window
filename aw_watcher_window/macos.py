from typing import Optional
from AppKit import NSWorkspace
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)

def getInfo() -> Optional[dict]:
    app_name = ''
    title = ''

    app = NSWorkspace.sharedWorkspace().activeApplication()

    if app:
        pid = app['NSApplicationProcessIdentifier']

        options = kCGWindowListOptionOnScreenOnly
        window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
        for window in window_list:
            if pid == window['kCGWindowOwnerPID']:
                # We could use app['NSApplicationName'], but this value is more
                # accurate and matches other methods (like applescript)
                app_name = window['kCGWindowOwnerName']
                title = window.get('kCGWindowName', u'')
                break

    return {"appname": app_name, "title": title}
