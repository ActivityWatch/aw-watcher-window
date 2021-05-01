import subprocess
import os
import json
import logging

logger = logging.getLogger(__name__)

def getInfo() -> str:
    cmd = [os.path.join(os.path.dirname(os.path.realpath(__file__)), "printAppStatus.jxa")]
    p = subprocess.run(cmd, stdout=subprocess.PIPE)
    result = str(p.stdout, "utf8").strip()

    try:
        return json.loads(result)
    except json.JSONDecodeError as e:
        logger.warn(f"invalid JSON encountered {result}")
        return {}

def background_ensure_permissions() -> None:
    from multiprocessing import Process
    permission_process = Process(target=ensure_permissions, args=(()))
    permission_process.start()
    return


def ensure_permissions() -> None:
    from ApplicationServices import AXIsProcessTrusted
    from AppKit import NSAlert, NSAlertFirstButtonReturn, NSWorkspace, NSURL
    accessibility_permissions = AXIsProcessTrusted()
    if not accessibility_permissions:
        title = "Missing accessibility permissions"
        info = "To let ActivityWatch capture window titles grant it accessibility permissions. \n If you've already given ActivityWatch accessibility permissions and are still seeing this dialog, try removing and re-adding them."

        alert = NSAlert.new()
        alert.setMessageText_(title)
        alert.setInformativeText_(info)

        ok_button = alert.addButtonWithTitle_("Open accessibility settings")

        alert.addButtonWithTitle_("Close")
        choice = alert.runModal()
        print(choice)
        if choice == NSAlertFirstButtonReturn:
            NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"))
