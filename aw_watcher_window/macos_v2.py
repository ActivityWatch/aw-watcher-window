#!/usr/bin/python3
# This code was rewritten from:
#   http://stackoverflow.com/a/37368813/965332
# Selfspy does this and a lot more here:
#   https://github.com/gurgeh/selfspy/blob/master/selfspy/sniff_cocoa.py

import logging
from typing import Tuple, Optional

# import applescript
from AppKit import NSWorkspace
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID

logger = logging.getLogger("aw.watcher.window.macos")


def get_active_window_title(event_window_num: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
    # Doesn't return any window title for Chrome, possibly due to unicode
    # formatted window title's handled differently as in X11.
    try:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        active_app_name = app.localizedName()

        options = kCGWindowListOptionOnScreenOnly
        window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
        window_title = None
        for window in window_list:
            window_number = window['kCGWindowNumber']
            owner_name = window['kCGWindowOwnerName']
            window_title = window.get('kCGWindowName', 'unknown')
            if window_title \
               and event_window_num == window_number or owner_name == active_app_name:
                logger.debug('owner={}, title={}'.format(owner_name, window_title))
                break
        return active_app_name, window_title
    except Exception:
        logger.error('Exception was raised while trying to get active window', exc_info=True)
    return None, None


if __name__ == "__main__":
    from time import sleep
    app, title = get_active_window_title()
    while True:
        print(app)
        print(title)
        sleep(1)
