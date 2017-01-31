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
    poll_time = 1.0
    update_time = 15.0

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

    last_window = None
    last_window_start = datetime.now(timezone.utc)
    last_event_time = datetime.now(timezone.utc)
    while True:
        try:
            current_window = get_current_window()

            now = datetime.now(timezone.utc)
            if current_window is None:
                logger.debug('Unable to fetch window, trying again on next poll')

            # If windows are not the same, insert it as a new event
            elif last_window != current_window:
                if last_window is not None:
                    # Create last_window event
                    duration = now - last_window_start
                    labels = ["title:" + last_window["title"]]
                    labels.append("appname:" + last_window["appname"])
                    last_window_event = Event(label=labels, timestamp=last_window_start, duration=duration)
                    # Send last_window event
                    client.replace_last_event(bucketname, last_window_event)
                    # Log
                    logger.debug("Window is no longer active: " + str(last_window))
                    logger.debug("Duration: {}s".format(str(duration.total_seconds())))

                # Create current_window event
                duration = timedelta()
                labels = ["title:" + current_window["title"]]
                labels.append("appname:" + current_window["appname"])
                current_window_event = Event(label=labels, timestamp=now, duration=duration)
                # Send events
                client.send_event(bucketname, current_window_event)
                last_event_time = now

                # Log
                logger.info("Window became active: " + str(current_window))
                # Store current window
                last_window = current_window
                last_window_start = now

            # If windows are the same and update_time has passed (default 15sec), replace last event with this event for updated duration
            elif now - timedelta(seconds=update_time) > last_event_time:
                # Create current_window event
                duration = now - last_window_start
                labels = ["title:" + current_window["title"]]
                labels.append("appname:" + current_window["appname"])
                current_window_event = Event(label=labels, timestamp=last_window_start, duration=duration)

                # Send current_window event
                client.replace_last_event(bucketname, current_window_event)
                last_event_time = now

        except Exception as e:
            logger.error("Exception thrown while trying to get active window: {}".format(e))
            traceback.print_exc(e)
        sleep(poll_time)
