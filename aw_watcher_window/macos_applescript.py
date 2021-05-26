import os
import subprocess
from subprocess import PIPE
from typing import Dict


# the applescript version of the macos strategy is kept here until the jxa
# approach is proven out in production environments
# https://github.com/ActivityWatch/aw-watcher-window/pull/52


def getInfo() -> Dict[str, str]:
    cmd = [
        "osascript",
        os.path.join(os.path.dirname(os.path.realpath(__file__)), "printAppTitle.scpt"),
    ]
    p = subprocess.run(cmd, stdout=PIPE)
    info = str(p.stdout, "utf8").strip()

    app = getApp(info)
    title = getTitle(info)

    return {"app": app, "title": title}


def getApp(info: str) -> str:
    return info.split('","')[0][1:]


def getTitle(info: str) -> str:
    return info.split('","')[1][:-1]
