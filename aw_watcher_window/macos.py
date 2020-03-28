from ApplicationServices import AXIsProcessTrusted
from AppKit import NSAlert, NSAlertFirstButtonReturn, NSButton, NSWorkspace, NSURL
import subprocess
from subprocess import PIPE
import os
import time


def getInfo() -> str:
    #accessibility_permissions = AXIsProcessTrusted()
    accessibility_permissions = False
    if not accessibility_permissions:
        title = "Missing accessibility permissions"
        info = "To let ActivityWatch capture window titles grant it accessibility permissions"

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
        #while True:
        #    time.sleep(1)
    cmd = ["osascript", os.path.join(os.path.dirname(os.path.realpath(__file__)), "printAppTitle.scpt")]
    p = subprocess.run(cmd, stdout=PIPE)
    return str(p.stdout, "utf8").strip()


def getApp(info) -> str:
    return info.split('","')[0][1:]


def getTitle(info) -> str:
    return info.split('","')[1][:-1]
