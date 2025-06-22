import sys
import subprocess
import re
import logging
from subprocess import PIPE
from typing import List

logger = logging.getLogger(__name__)

# req_version is 3.5 due to usage of subprocess.run
# It would be nice to be able to use 3.4 as well since it's still common as of May 2016
req_version = (3, 5)
cur_version = sys.version_info

if not cur_version >= req_version:
    logger.error("Your Python version is too old, 3.5 or higher is required.")
    exit(1)


def xprop_id(window_id) -> str:
    cmd = ["xprop"]
    cmd.append("-id")
    cmd.append(window_id)
    p = subprocess.run(cmd, stdout=PIPE)
    return str(p.stdout, "utf8")


def xprop_root() -> str:
    cmd = ["xprop"]
    cmd.append("-root")
    p = subprocess.run(cmd, stdout=PIPE)
    return str(p.stdout, "utf8")


def get_active_window_id():
    lines = xprop_root().split("\n")
    match="_NET_ACTIVE_WINDOW(WINDOW)"
    result = None
    for line in lines:
        if match in line:
            result = line
            break
    wid = "0x0"
    if result:
        wids = re.findall("0x[0-9a-f]*", result)
        if len(wids) > 0:
            wid = wids[0]
    return wid


def get_window_ids():
    lines = xprop_root().split("\n")
    client_list = next(filter(lambda x: "_NET_CLIENT_LIST(" in x, lines))
    window_ids = re.findall("0x[0-9a-f]*", client_list)
    return window_ids


def _extract_xprop_field(line):
    return "".join(line.split("=")[1:]).strip(" \n")


def get_xprop_field(fieldname, xprop_output):
    return list(map(_extract_xprop_field, re.findall(fieldname + ".*\n", xprop_output)))


def get_xprop_field_str(fieldname, xprop_output) -> str:
    field = None
    try:
        field = get_xprop_field(fieldname, xprop_output)[0].strip('"')
    except IndexError:
        pass
    if not field:
        field = "unknown"
    return field


def get_xprop_field_strlist(fieldname, xprop_output) -> List[str]:
    return [s.strip('"') for s in get_xprop_field(fieldname, xprop_output)]


def get_xprop_field_int(fieldname, xprop_output) -> int:
    field = None
    try:
        field = int(get_xprop_field(fieldname, xprop_output)[0])
    except IndexError:
        pass
    if not field:
        field = -1
    return field


def get_xprop_field_class(xprop_output) -> List[str]:
    classname: List[str] = []
    try:
        classname = [c.strip('", ') for c in get_xprop_field("WM_CLASS", xprop_output)[0].split(',')]
    except IndexError:
        pass
    if not classname:
        classname = ["unknown"]
    return classname


def get_window(wid, active_window=False):
    s = xprop_id(wid)
    window = {
        "id": wid,
        "active": active_window,
        "name": get_xprop_field_str("WM_NAME", s),
        "class": get_xprop_field_class(s),
        "desktop": get_xprop_field_int("WM_DESKTOP", s),
        "command": get_xprop_field("WM_COMMAND", s),
        "role": get_xprop_field_strlist("WM_WINDOW_ROLE", s),
        "pid": get_xprop_field_int("WM_PID", s),
    }

    return window


def get_windows(wids, active_window_id=None):
    return [get_window(wid, active_window=(wid == active_window_id)) for wid in wids]


if __name__ == "__main__":
    from time import sleep
    logging.basicConfig(level=logging.INFO)
    while True:
        sleep(1)
        print("Active window id: " + str(get_active_window_id()))
