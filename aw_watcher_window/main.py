import argparse
import logging
import traceback
import sys
import os
from time import sleep
from datetime import datetime, timezone

from aw_core.models import Event
from aw_core.log import setup_logging
from aw_client import ActivityWatchClient

from .lib import get_current_window
from .config import load_config

logger = logging.getLogger(__name__)


def main():
    # Read settings from config
    config = load_config()
    args = parse_args(
        default_poll_time=config.getfloat("poll_time"),
        default_exclude_title=config.getboolean("exclude_title"),
    )

    if sys.platform.startswith("linux") and ("DISPLAY" not in os.environ or not os.environ["DISPLAY"]):
        raise Exception("DISPLAY environment variable not set")

    setup_logging(name="aw-watcher-window", testing=args.testing, verbose=args.verbose,
                  log_stderr=True, log_file=True)

    if sys.platform == "darwin":
        from . import macos
        macos.background_ensure_permissions()

    client = ActivityWatchClient("aw-watcher-window", testing=args.testing)

    bucket_id = "{}_{}".format(client.client_name, client.client_hostname)
    event_type = "currentwindow"

    client.create_bucket(bucket_id, event_type, queued=True)

    logger.info("aw-watcher-window started")

    sleep(1)  # wait for server to start
    with client:
        heartbeat_loop(client, bucket_id, poll_time=args.poll_time, exclude_title=args.exclude_title)


def parse_args(default_poll_time: float, default_exclude_title: bool):
    """config contains defaults loaded from the config file"""
    parser = argparse.ArgumentParser("A cross platform window watcher for Activitywatch.\nSupported on: Linux (X11), macOS and Windows.")
    parser.add_argument("--testing", dest="testing", action="store_true")
    parser.add_argument("--exclude-title", dest="exclude_title", action="store_true", default=default_exclude_title)
    parser.add_argument("--verbose", dest="verbose", action="store_true")
    parser.add_argument("--poll-time", dest="poll_time", type=float, default=default_poll_time)
    return parser.parse_args()


def heartbeat_loop(client, bucket_id, poll_time, exclude_title=False):
    while True:
        if os.getppid() == 1:
            logger.info("window-watcher stopped because parent process died")
            break

        try:
            current_window = get_current_window()
            logger.debug(current_window)
        except Exception as e:
            logger.error("Exception thrown while trying to get active window: {}".format(e))
            traceback.print_exc()
            current_window = {"appname": "unknown", "title": "unknown"}

        now = datetime.now(timezone.utc)
        if current_window is None:
            logger.debug('Unable to fetch window, trying again on next poll')
        else:
            # Create current_window event
            data = {
                "app": current_window["appname"],
                "title": current_window["title"] if not exclude_title else "excluded"
            }
            current_window_event = Event(timestamp=now, data=data)

            # Set pulsetime to 1 second more than the poll_time
            # This since the loop takes more time than poll_time
            # due to sleep(poll_time).
            client.heartbeat(bucket_id, current_window_event,
                             pulsetime=poll_time + 1.0, queued=True)

        sleep(poll_time)
