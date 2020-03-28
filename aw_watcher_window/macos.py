from ApplicationServices import AXIsProcessTrusted
from AppKit import NSAlert
import subprocess
from subprocess import PIPE
import os


def getInfo() -> str:
    accessibility_permissions = AXIsProcessTrusted()
    #accessibility_permissions = False
    if not accessibility_permissions:
        title = "Missing accessibility permissions"
        message = "To let ActivityWatch capture window titles grant it accessibility permissions"
        ok = False
        cancel = False
        alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(title, ok, 'Cancel' if cancel else None, None, message)
        alert.runModal()
    cmd = ["osascript", os.path.join(os.path.dirname(os.path.realpath(__file__)), "printAppTitle.scpt")]
    p = subprocess.run(cmd, stdout=PIPE)
    return str(p.stdout, "utf8").strip()


def getApp(info) -> str:
    return info.split('","')[0][1:]


def getTitle(info) -> str:
    return info.split('","')[1][:-1]
