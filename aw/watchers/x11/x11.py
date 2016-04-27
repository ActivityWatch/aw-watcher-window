import subprocess
from subprocess import PIPE
from time import sleep
import logging
import re

from aw.client import ActivityWatchClient

logger = logging.getLogger("aw-watcher-x11")


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
    client_list = next(filter(lambda x: "_NET_ACTIVE_WINDOW(" in x, lines))
    wid = re.findall("0x[0-9a-f]*", client_list)[0]
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
    return get_xprop_field(fieldname, xprop_output)[0].strip('"')


def get_xprop_field_strlist(fieldname, xprop_output) -> str:
    return [s.strip('"') for s in get_xprop_field(fieldname, xprop_output)]


def get_xprop_field_class(xprop_output) -> str:
    return [c.strip('", ') for c in get_xprop_field("WM_CLASS", xprop_output)[0].split(',')]


def get_xprop_field_int(fieldname, xprop_output) -> int:
    return int(get_xprop_field(fieldname, xprop_output)[0])


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

def main():
    logging.basicConfig(level=logging.DEBUG)
    client = ActivityWatchClient("x11watcher")

    GET_ONLY_ACTIVE = True

    last_windows = []
    while True:
        try:
            wids = get_window_ids()
            active_window_id = get_active_window_id()
            if active_window_id == "0x0":
                print("Failed to find active window, id found was 0x0")
                sleep(1)
                continue

            if GET_ONLY_ACTIVE:
                current_windows = get_windows([active_window_id], active_window_id)
            else:
                current_windows = get_windows(wids, active_window_id)

            if last_windows != current_windows:
                last_windows = current_windows
                print("Windows changed")
                client.send_event(last_windows)
                print(current_windows)
        except Exception as e:
            logger.error("Exception thrown while trying to get active window: " + e)
        sleep(1)

