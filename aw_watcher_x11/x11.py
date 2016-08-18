from time import sleep
import logging
from datetime import datetime
import traceback
from . import xprop

import pytz

from aw_core.models import Event
from aw_client import ActivityWatchClient

logger = logging.getLogger("aw_watcher_x11")


def main():
    import argparse

    poll_time = 1.0

    parser = argparse.ArgumentParser("A watcher for windows in X11")
    parser.add_argument("--testing", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.testing else logging.INFO)
    client = ActivityWatchClient("x11watcher", testing=args.testing)

    bucketname = "{}-{}".format(client.client_name, client.client_hostname)
    eventtype = "currentwindow"
    
    buckets = client.get_buckets()
    if bucketname not in buckets:
        client.create_bucket(bucketname, eventtype)

    

    # get_only_active = True

    last_window = []
    while True:
        try:
            # wids = xprop.get_window_ids()
            active_window_id = xprop.get_active_window_id()
            if active_window_id == "0x0":
                print("Failed to find active window, id found was 0x0")
                sleep(poll_time)
                continue

            # Always true, getting all windows currently not supported
            # if get_only_active:
            current_window = xprop.get_windows([active_window_id], active_window_id)[0]
            # else:
            #    current_windows = get_windows(wids, active_window_id)

            """
            if last_windows != current_windows:
                last_windows = current_windows
                print("Windows changed")
                client.send_event(Event(windows=last_windows, timestamp=datetime.now()))
                print(current_windows)
            """

            if last_window != current_window:
                last_window = current_window
                print("Window changed")
                labels = ["title:" + current_window["name"]]
                labels.extend(["class:" + cls for cls in set(current_window["class"])])
                client.send_event(bucketname, Event(label=labels,
                                        timestamp=datetime.now(pytz.utc),
                                        duration=()))
                print(current_window)
        except Exception as e:
            logger.error("Exception thrown while trying to get active window: {}".format(e))
            traceback.print_exc(e)
        sleep(poll_time)
