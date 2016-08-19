import subprocess
from subprocess import PIPE
import os


def getInfo() -> str:
    cmd = ["osascript", os.path.join(os.path.dirname(os.path.realpath(__file__)), "printAppTitle.scpt")]
    p = subprocess.run(cmd, stdout=PIPE)
    return str(p.stdout, "utf8").strip()


def getApp(info) -> str:
    return info.split('","')[0][1:]


def getTitle(info) -> str:
    return info.split('","')[1][:-1]
