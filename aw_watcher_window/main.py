import logging
import traceback
import sys
from time import sleep
from datetime import datetime

import pytz

from aw_core.models import Event
from aw_client import ActivityWatchClient

from . import xprop
from . import __desc__

logger = logging.getLogger("aw.watcher.window")


def get_current_window_linux():
    active_window_id = xprop.get_active_window_id()
    if active_window_id == "0x0":
        print("Failed to find active window, id found was 0x0")
        return None
    return xprop.get_windows([active_window_id], active_window_id)[0]


def get_current_window_macos():
    raise NotImplementedError


def get_current_window_windows():
    raise NotImplementedError


def get_current_window():
    # TODO: Implement with_title kwarg as option
    if sys.platform.startwith("linux"):
        return get_current_window_linux()
    elif sys.platform == "darwin":
        return get_current_window_macos()
    elif sys.platform == "win32":
        return get_current_window_windows()
    else:
        raise Exception("Unknown platform: {}".format(sys.platform))


def main():
    import argparse

    poll_time = 1.0

    parser = argparse.ArgumentParser("A cross platform window watcher for Linux, macOS and Windows.")
    parser.add_argument("--testing", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.testing else logging.INFO)
    client = ActivityWatchClient("windowwatcher", testing=args.testing)

    bucketname = "{}_{}".format(client.client_name, client.client_hostname)
    eventtype = "currentwindow"
    client.create_bucket(bucketname, eventtype)

    last_window = []
    while True:
        try:
            current_window = get_current_window()

            if last_window != current_window:
                last_window = current_window
                print("Window changed")
                labels = ["title:" + current_window["name"]]
                labels.extend(["class:" + cls for cls in set(current_window["class"])])
                client.send_event(bucketname,
                                  Event(label=labels, timestamp=datetime.now(pytz.utc)))
                print(current_window)
        except Exception as e:
            logger.error("Exception thrown while trying to get active window: {}".format(e))
            traceback.print_exc(e)
        sleep(poll_time)
