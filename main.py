import logging
import time

from AppKit import NSWorkspace

# Dependencies:
# - pyobjc-core
# - pyobjc-framework-quartz?
# - pyobjc-framework-cocoa?

"""
## Stackoverflow thread with hints
 - https://stackoverflow.com/questions/373020/finding-the-current-active-window-in-mac-os-x-using-python

## Apple Docs references
 - NSWorkspace:         https://developer.apple.com/library/mac/documentation/Cocoa/Reference/ApplicationKit/Classes/NSWorkspace_Class/index.html
 - RunningApplication:  https://developer.apple.com/library/mac/documentation/AppKit/Reference/NSRunningApplication_Class/index.html
"""


def run():
    logging.warning("OS X Window-watcher not implemented")
    print(get_running_apps())
    while True:
        time.sleep(3)
        print_app(get_active_app())

def print_app(app):
    print(app)
    print(app_to_dict(app))

def app_to_dict(app):
    return {
            "name": app.localizedName(),
            "bundleIdentifier": app.bundleIdentifier(),
            "bundleURL": app.bundleURL(),
            "executableURL": app.executableURL(),
            "launchDate": app.launchDate()
    }


def get_active_app():
    """Returns a dict containing some things like exec location, program name, but not window title."""
    # FIXME: Doesn't return the active app, constantly returns iTerm for me when testing despite changing window.
    #        Same behavior with frontmostApplication and menuBarOwningApplication.
    #        activeApplication works, but is deprecated in 10.11 and gives data in a different format.
    #        The same issue applies for get_running_apps()
    #        Docs give a hint at why:
    #
    #          "Similar to the NSRunningApplication class’s properties, this property will
    #           only change when the main run loop is run in a common mode.
    #           Instead of polling, use key-value observing to be notified of changes to this array property."
    #
    #          "Properties that vary over time are inherently race-prone. For example, a hidden app
    #           may unhide itself at any time. To ameliorate this, properties persist until the next
    #           turn of the main run loop in a common mode. For example, if you repeatedly poll an
    #           unhidden app for its hidden property without allowing the run loop to run, it will
    #           continue to return NO, even if the app hides, until the next turn of the run loop."
    #
    # Deprecated: return NSWorkspace.sharedWorkspace().activeApplication()
    return NSWorkspace.sharedWorkspace().frontmostApplication()
    #return NSWorkspace.sharedWorkspace().menuBarOwningApplication()
    #return NSWorkspace.sharedWorkspace().activeApplication()

def get_running_apps():
    return NSWorkspace.sharedWorkspace().runningApplications()

if __name__ == "__main__":
    run()
