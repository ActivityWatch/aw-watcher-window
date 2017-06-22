import argparse
import logging
import traceback
import sys
import os
from time import sleep
from datetime import datetime, timezone

from aw_core.util import assert_version
from aw_core.models import Event
from aw_core.log import setup_logging
from aw_client import ActivityWatchClient

from .lib import get_current_window
from .config import load_config

logger = logging.getLogger(__name__)


def main():
    # Verify python version is >=3.5
    #   req_version is 3.5 due to usage of subprocess.run
    assert_version((3, 5))

    # Read settings from config
    config = load_config()

    # Parse arguments
    parser = argparse.ArgumentParser("A cross platform window watcher for Linux, macOS and Windows.")
    parser.add_argument("--testing", dest="testing", action="store_true")
    parser.add_argument("--exclude-title", dest="exclude_title", action="store_true")
    parser.add_argument("--verbose", dest="verbose", action="store_true")
    parser.add_argument("--poll-time", type=float, default=config.getfloat("poll_time"))
    args = parser.parse_args()

    setup_logging(name="aw-watcher-window", testing=args.testing, verbose=args.verbose,
                  log_stderr=True, log_file=True)

    logging.info("Running watcher with poll time {} seconds".format(args.poll_time))

    if sys.platform.startswith("linux") and ("DISPLAY" not in os.environ or not os.environ["DISPLAY"]):
        raise Exception("DISPLAY environment variable not set")

    client = ActivityWatchClient("aw-watcher-window", testing=args.testing)

    bucketname = "{}_{}".format(client.client_name, client.client_hostname)
    eventtype = "currentwindow"
    client.setup_bucket(bucketname, eventtype)
    client.connect()

    logger.info("aw-watcher-window has started")
    while True:
        try:
            current_window = get_current_window()
            logger.debug(current_window)
        except Exception as e:
            logger.error("Exception thrown while trying to get active window: {}".format(e))
            traceback.print_exc(e)
            continue

        now = datetime.now(timezone.utc)
        if current_window is None:
            logger.debug('Unable to fetch window, trying again on next poll')
        else:
            # Create current_window event
            data = {
                "app": current_window["appname"],
                "title": current_window["title"] if not args.exclude_title else "title:excluded"
            }
            current_window_event = Event(timestamp=now, data=data)

            # Set pulsetime to 1 second more than the poll_time
            # This since the loop takes more time than poll_time
            # due to sleep(poll_time).
            client.heartbeat(bucketname, current_window_event,
                             pulsetime=args.poll_time + 1.0, queued=True)

        sleep(args.poll_time)
