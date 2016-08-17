import subprocess
from subprocess import PIPE
from time import sleep
import logging
import re
import sys
from datetime import datetime
import pytz

from aw_core.models import Event
from aw_client import ActivityWatchClient

logger = logging.getLogger("aw-watcher-macos")

# req_version is 3.5 due to usage of subprocess.run
# It would be nice to be able to use 3.4 as well since it's still common as of May 2016
req_version = (3,5)
cur_version = sys.version_info

if not cur_version >= req_version:
    logger.error("Your Python version is too old, 3.5 or higher is required.")
    exit(1)

def getInfo() -> str:
    cmd = ["osascript", "printAppTitle.scpt"]
    p = subprocess.run(cmd, stdout=PIPE)
    return str(p.stdout, "utf8").strip()

def getApp(info) -> str:
    return info.split('","')[0][1:]

def getTitle(info) -> str:
    return info.split('","')[1][:-1]


def main():
    import argparse

    parser = argparse.ArgumentParser("A watcher for applications with activationPolicy=regular")
    parser.add_argument("--testing", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.testing else logging.INFO)
    client = ActivityWatchClient("macoswatcher", testing=args.testing)

    last_app = "";
    last_title = "";
    info = getInfo()
    active_app = getApp(info)
    active_title = getTitle(info)
    if(active_title == ""):
        logger.error("Title of active window not found. Does the terminal have access to accessibility API? See README for how to give access!")

    while True:
        try:
            info = getInfo()
            active_app = getApp(info)
            active_title = getTitle(info)

            if(last_app != active_app or last_title != active_title):
                last_app = active_app
                last_title = active_title
                client.send_event(Event(label=[active_app,active_title], timestamp=datetime.now(pytz.utc)))
                print(active_app + ", " + active_title)
        except Exception as e:
            logger.error("Exception thrown while trying to get active applications {}".format(e))
        sleep(0.5)

if __name__ == "__main__":
    main()
