import logging
import json
import os
import re
import sys
from datetime import datetime, timezone
from time import sleep

from aw_client import ActivityWatchClient
from aw_core.log import setup_logging
from aw_core.models import Event

from .config import parse_args
from .exceptions import FatalError
from .lib import get_current_window
from .platform import get_virtual_desktop

logger = logging.getLogger(__name__)

# run with LOG_LEVEL=DEBUG
log_level = os.environ.get("LOG_LEVEL")
if log_level:
    logger.setLevel(logging.__getattribute__(log_level.upper()))
def try_compile_title_regex(title):
    try:
        return re.compile(title, re.IGNORECASE)
    except re.error:
        logger.error(f"Invalid regex pattern: {title}")
        exit(1)


def main():
    args = parse_args()

    if sys.platform.startswith("linux") and (
        "DISPLAY" not in os.environ or not os.environ["DISPLAY"]
    ):
        raise Exception("DISPLAY environment variable not set")

    if args.oneshot:
        data = get_current_window()
        if data is not None and "virtual_desktop" not in data:
            data["virtual_desktop"] = get_virtual_desktop()

        for pattern in [try_compile_title_regex(t) for t in args.exclude_titles]:
            if data and "title" in data and pattern.search(data["title"]):
                data.pop("title", None)

        if args.exclude_title and data is not None:
            data.pop("title", None)

        print(json.dumps(data))
        return

    setup_logging(
        name="aw-watcher-virtualdesktop",
        testing=args.testing,
        verbose=args.verbose,
        log_stderr=True,
        log_file=True,
    )

    client = ActivityWatchClient(
        "aw-watcher-virtualdesktop", host=args.host, port=args.port, testing=args.testing
    )

    bucket_id = f"{client.client_name}_{client.client_hostname}"
    event_type = "currentwindow"

    client.create_bucket(bucket_id, event_type, queued=True)

    logger.info("aw-watcher-virtualdesktop started")
    client.wait_for_start()

    with client:
        heartbeat_loop(
            client,
            bucket_id,
            poll_time=args.poll_time,
            # strategy=args.strategy,

            exclude_title=args.exclude_title,
            exclude_titles=[
                try_compile_title_regex(title)
                for title in args.exclude_titles
                if title is not None
            ],
        )


def heartbeat_loop(
    client, bucket_id, poll_time, exclude_title=False, exclude_titles=[]
):
    while True:
        if os.getppid() == 1:
            logger.info("window-watcher stopped because parent process died")
            break

        current_window = None
        try:
            current_window = get_current_window()
            logger.debug(current_window)
        except (FatalError, OSError):
            # Fatal exceptions should quit the program
            try:
                logger.exception("Fatal error, stopping")
            except OSError:
                pass
            break
        except Exception:
            # Non-fatal exceptions should be logged
            try:
                # If stdout has been closed, this exception-print can cause (I think)
                #   OSError: [Errno 5] Input/output error
                # See: https://github.com/ActivityWatch/activitywatch/issues/756#issue-1296352264
                #
                # However, I'm unable to reproduce the OSError in a test (where I close stdout before logging),
                # so I'm in uncharted waters here... but this solution should work.
                logger.exception("Exception thrown while trying to get active window")
            except OSError:
                break

        if current_window is None:
            logger.debug("Unable to fetch window, trying again on next poll")
        else:
            for pattern in exclude_titles:
                if "title" in current_window and pattern.search(current_window["title"]):
                    current_window.pop("title", None)
                    break

            if exclude_title and "title" in current_window:
                current_window.pop("title", None)

            if "virtual_desktop" not in current_window:
                current_window["virtual_desktop"] = get_virtual_desktop()

            now = datetime.now(timezone.utc)
            current_window_event = Event(timestamp=now, data=current_window)

            # Set pulsetime to 1 second more than the poll_time
            # This since the loop takes more time than poll_time
            # due to sleep(poll_time).
            client.heartbeat(
                bucket_id, current_window_event, pulsetime=poll_time + 1.0, queued=True
            )

        sleep(poll_time)
