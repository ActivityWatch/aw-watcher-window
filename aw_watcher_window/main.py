import argparse
import logging
import traceback
import sys
from time import sleep
from datetime import datetime, timezone, timedelta

from aw_core.models import Event
from aw_core.log import setup_logging
from aw_client import ActivityWatchClient

from .lib import get_current_window

logger = logging.getLogger("aw.watchers.window")


def main():
    # req_version is 3.5 due to usage of subprocess.run
    # It would be nice to be able to use 3.4 as well since it's still common as of May 2016
    req_version = (3, 5)
    cur_version = sys.version_info
    if not cur_version >= req_version:
        logger.error("Your Python version is too old, 3.5 or higher is required")
        exit(1)

    parser = argparse.ArgumentParser("A cross platform window watcher for Linux, macOS and Windows.")
    parser.add_argument("--testing", dest="testing", action="store_true")
    parser.add_argument("--poll-time", type=float, default=1.0)

    args = parser.parse_args()

    setup_logging(name="aw-watcher-window", testing=args.testing,
                  log_stderr=True, log_file=True)

    client = ActivityWatchClient("aw-watcher-window", testing=args.testing)

    bucketname = "{}_{}".format(client.client_name, client.client_hostname)
    eventtype = "currentwindow"
    client.setup_bucket(bucketname, eventtype)
    client.connect()

    while True:
        try:
            current_window = get_current_window()
        except Exception as e:
            logger.error("Exception thrown while trying to get active window: {}".format(e))
            traceback.print_exc(e)
            continue

        now = datetime.now(timezone.utc)
        if current_window is None:
            logger.debug('Unable to fetch window, trying again on next poll')
        else:
            # Create current_window event
            labels = ["title:" + current_window["title"]]
            labels.append("appname:" + current_window["appname"])
            current_window_event = Event(label=labels, timestamp=now)

            client.heartbeat(bucketname, current_window_event, 2*args.poll_time)

        sleep(args.poll_time)
