import os
import json
import logging

logger = logging.getLogger(__name__)
script = None

def compileScript():
    # https://stackoverflow.com/questions/44209057/how-can-i-run-jxa-from-swift
    # https://stackoverflow.com/questions/16065162/calling-applescript-from-python-without-using-osascript-or-appscript
    from OSAKit import OSAScript, OSALanguage

    scriptPath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "printAppStatus.jxa")
    scriptContents = open(scriptPath, mode="r").read()
    javascriptLanguage = OSALanguage.languageForName_("JavaScript")

    script = OSAScript.alloc().initWithSource_language_(scriptContents, javascriptLanguage)
    (success, err) = script.compileAndReturnError_(None)

    # should only occur if jxa was modified incorrectly
    if not success:
        raise Exception("error compiling jxa script")

    return script

def getInfo() -> str:
    # use a global variable to cache the compiled script for performance
    global script
    if not script:
        script = compileScript()

    (result, err) = script.executeAndReturnError_(None)

    if err:
        # error structure:
        # {
        #     NSLocalizedDescription = "Error: Error: Can't get object.";
        #     NSLocalizedFailureReason = "Error: Error: Can't get object.";
        #     OSAScriptErrorBriefMessageKey = "Error: Error: Can't get object.";
        #     OSAScriptErrorMessageKey = "Error: Error: Can't get object.";
        #     OSAScriptErrorNumberKey = "-1728";
        #     OSAScriptErrorRangeKey = "NSRange: {0, 0}";
        # }

        raise Exception("jxa error: {}".format(err["NSLocalizedDescription"]))

    return json.loads(result.stringValue())

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

if __name__ == "__main__":
    print(getInfo())
    print("Waiting 5 seconds...")
    import time
    time.sleep(5)
    print(getInfo())