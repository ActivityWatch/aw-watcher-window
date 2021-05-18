from configparser import ConfigParser
import argparse

from aw_core.config import load_config as _load_config

def load_config():
    default_client_config = ConfigParser()
    default_client_config["aw-watcher-window"] = default_client_config["aw-watcher-window-testing"] = {
        "exclude_title": False,
        "poll_time": "1.0",
        "macos_strategy": "jxa"
    }

    # TODO: Handle so aw-watcher-window testing gets loaded instead of testing is on
    return _load_config("aw-watcher-window", default_client_config)["aw-watcher-window"]

def parse_args():
    config = load_config()

    default_poll_time = config.getfloat("poll_time")
    default_exclude_title = config.getboolean("exclude_title")
    default_macos_strategy = config.get("macos_strategy")

    parser = argparse.ArgumentParser("A cross platform window watcher for Activitywatch.\nSupported on: Linux (X11), macOS and Windows.")
    parser.add_argument("--testing", dest="testing", action="store_true")
    parser.add_argument("--exclude-title", dest="exclude_title", action="store_true", default=default_exclude_title)
    parser.add_argument("--verbose", dest="verbose", action="store_true")
    parser.add_argument("--poll-time", dest="poll_time", type=float, default=default_poll_time)
    parser.add_argument("--macos-strategy", dest="macos_strategy", default=default_macos_strategy, choices=["jxa", "applescript"])
    return parser.parse_args()
