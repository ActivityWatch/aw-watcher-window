import os
import json
import logging
from typing import Dict

logger = logging.getLogger(__name__)
script = None


def compileScript():
    # https://stackoverflow.com/questions/44209057/how-can-i-run-jxa-from-swift
    # https://stackoverflow.com/questions/16065162/calling-applescript-from-python-without-using-osascript-or-appscript
    from OSAKit import OSAScript, OSALanguage

    scriptPath = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "printAppStatus.jxa"
    )
    scriptContents = open(scriptPath, mode="r").read()
    javascriptLanguage = OSALanguage.languageForName_("JavaScript")

    script = OSAScript.alloc().initWithSource_language_(
        scriptContents, javascriptLanguage
    )
    (success, err) = script.compileAndReturnError_(None)

    # should only occur if jxa was modified incorrectly
    if not success:
        raise Exception("error compiling jxa script")

    return script


def getInfo() -> Dict[str, str]:
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


if __name__ == "__main__":
    print(getInfo())
    print("Waiting 5 seconds...")
    import time

    time.sleep(5)
    print(getInfo())
