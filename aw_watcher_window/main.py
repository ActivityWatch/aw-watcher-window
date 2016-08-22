import logging
import traceback
import sys
from time import sleep
from datetime import datetime, timezone

import pytz

from aw_core.models import Event
from aw_client import ActivityWatchClient

if sys.platform.startswith("linux"):
    from . import xprop
elif sys.platform == "darwin":
    from . import macos
elif sys.platform == "win32":
    # from . import windows
    pass

logger = logging.getLogger("aw.watcher.window")


def get_current_window_linux() -> dict:
    active_window_id = xprop.get_active_window_id()
    if active_window_id == "0x0":
        print("Failed to find active window, id found was 0x0")
        return None
    w = xprop.get_windows([active_window_id], active_window_id)[0]
    window = {"appname": w["class"][1], "title": w["name"]}
    return window


def get_current_window_macos() -> dict:
    info = macos.getInfo()
    app = macos.getApp(info)
    title = macos.getTitle(info)
    return {"title": title, "appname": app}


def get_current_window_windows() -> dict:
    raise NotImplementedError


def get_current_window() -> dict:
    # TODO: Implement with_title kwarg as option
    if sys.platform.startswith("linux"):
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

    # req_version is 3.5 due to usage of subprocess.run
    # It would be nice to be able to use 3.4 as well since it's still common as of May 2016
    req_version = (3, 5)
    cur_version = sys.version_info
    if not cur_version >= req_version:
        logger.error("Your Python version is too old, 3.5 or higher is required")
        exit(1)

    parser = argparse.ArgumentParser("A cross platform window watcher for Linux, macOS and Windows.")
    parser.add_argument("--testing", action="store_true")
    parser.add_argument("--poll-time", type=float, default=1.0)

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.testing else logging.INFO)
    client = ActivityWatchClient("aw-watcher-window", testing=args.testing)

    bucketname = "{}_{}".format(client.client_name, client.client_hostname)
    eventtype = "currentwindow"
    client.create_bucket(bucketname, eventtype)

    last_window = None
    last_window_start = datetime.now(timezone.utc)
    while True:
        try:
            current_window = get_current_window()

            if last_window != current_window:
                finished_window = last_window
                now = datetime.now(timezone.utc)

                # Send away finished window
                if last_window is not None:
                    labels = ["title:" + finished_window["title"]]
                    labels.append("appname:" + finished_window["appname"])
                    duration = now - last_window_start
                    logger.debug("Window is no longer active: " + str(finished_window))
                    logger.debug("Duration: " + str(duration.total_seconds()) + "s")
                    event = Event(label=labels, timestamp=now, duration=duration)
                    client.send_event(bucketname, event)

                # Store current window
                last_window = current_window
                last_window_start = now
                logger.info("Window became active: " + str(last_window))
        except Exception as e:
            logger.error("Exception thrown while trying to get active window: {}".format(e))
            traceback.print_exc(e)
        sleep(poll_time)
