import os
import subprocess
from subprocess import PIPE
from typing import Dict
from Foundation import NSAppleScript

# the applescript version of the macos strategy is kept here until the jxa
# approach is proven out in production environments
# https://github.com/ActivityWatch/aw-watcher-window/pull/52

source = """
global frontApp, frontAppName, windowTitle

set windowTitle to ""
tell application "System Events"
    set frontApp to first application process whose frontmost is true
    set frontAppName to name of frontApp
    tell process frontAppName
        try
            tell (1st window whose value of attribute "AXMain" is true)
                set windowTitle to value of attribute "AXTitle"
            end tell
        end try
    end tell
end tell

return frontAppName & "
" & windowTitle
"""

script = None


def getInfo() -> Dict[str, str]:
    # Cache compiled script
    global script
    if script is None:
        script = NSAppleScript.alloc().initWithSource_(source)

    # Call script
    result, errorinfo = script.executeAndReturnError_(None)
    if errorinfo:
        raise Exception(errorinfo)
    output = result.stringValue()

    # Ensure there's no extra newlines in the output
    assert len(output.split("\n")) == 2

    app = getApp(output)
    title = getTitle(output)

    return {"app": app, "title": title}


def getApp(info: str) -> str:
    return info.split('\n')[0]


def getTitle(info: str) -> str:
    return info.split('\n')[1]


if __name__ == "__main__":
    info = getInfo()
    print(info)
