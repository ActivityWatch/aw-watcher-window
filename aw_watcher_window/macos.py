import subprocess
from subprocess import PIPE
import os


def getInfo() -> str:
    cmd = ["osascript", os.path.join(os.path.dirname(os.path.realpath(__file__)), "printAppTitle.scpt")]
    p = subprocess.run(cmd, stdout=PIPE)
    return str(p.stdout, "utf8").strip()


def getApp(info: str) -> str:
    return info.split('","')[0][1:]


def getTitle(info: str) -> str:
    return info.split('","')[1][:-1]


def background_ensure_permissions() -> None:
    import threading
    print("Starting permission check thread")
    permission_thread = threading.Thread(target=ensure_permissions, args=([]))
    permission_thread.start()
    return

def ensure_permissions() -> None:
    from ApplicationServices import AXIsProcessTrusted
    from AppKit import NSAlert, NSAlertFirstButtonReturn, NSWorkspace, NSURL
    #accessibility_permissions = AXIsProcessTrusted()
    accessibility_permissions = False
    if not accessibility_permissions:
        title = "Missing accessibility permissions"
        info = "To let ActivityWatch capture window titles grant it accessibility permissions. \n If you've already given ActivityWatch accessibility permissions and are still seeing this dialog, try removing and re-adding them."

        alert = NSAlert.new()
        alert.setMessageText_(title)
        alert.setInformativeText_(info)

        ok_button = alert.addButtonWithTitle_("Ok")

        accessibility_button = alert.addButtonWithTitle_("Turn on accessibility")
        accessibility_button.setTitle_("Open accessibility settings")
        accessibility_button.setAction_("")

        alert.addButtonWithTitle_("Cancel")
        choice = alert.runModal()
        print(choice)
        if choice == NSAlertFirstButtonReturn:
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"))
