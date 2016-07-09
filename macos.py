import subprocess
from subprocess import PIPE
from time import sleep
import logging
import re
import sys
from datetime import datetime

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

#Starts swiftbinary that asks osx what apps are running.
def getApps() -> str:
    cmd = ["./getRunningApplications"]
    p = subprocess.run(cmd, stdout=PIPE)
    return str(p.stdout, "utf8")

#just extracts the right content from the firstline produced by getApps()
def getActive(apps) -> str:
    return " ".join(apps.splitlines()[0].split(" ")[1:])

def main():
    import argparse

    parser = argparse.ArgumentParser("A watcher for applications with activationPolicy=regular")
    parser.add_argument("--testing", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.testing else logging.INFO)
    client = ActivityWatchClient("macoswatcher", testing=args.testing)

    last_active_app = "";
    while True:
        try:
            active_app = getActive(getApps())
            if(last_active_app != active_app):
                last_active_app = active_app
                print("Active application changed")
                client.send_event(Event(application=active_app, timestamp=datetime.now()))
                print(active_app)
        except Exception as e:
            logger.error("Exception thrown while trying to get active applications {}".format(e))
        sleep(1)

if __name__ == "__main__":
    main()
