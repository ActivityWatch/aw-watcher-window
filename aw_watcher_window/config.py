import argparse

from aw_core.config import load_config_toml

default_config = """
[aw-watcher-window]
exclude_title = false
exclude_titles = []
poll_time = 1.0
strategy_macos = "swift"
always_track_apps = "NukeX,Houdini FX"
""".strip()


def load_config():
    return load_config_toml("aw-watcher-window", default_config)["aw-watcher-window"]


def parse_args():
    config = load_config()

    default_poll_time = config["poll_time"]
    default_exclude_title = config["exclude_title"]
    default_exclude_titles = config["exclude_titles"]
    default_strategy_macos = config["strategy_macos"]
    default_always_track_apps = config.get("always_track_apps", [])  # Безопасно получаем значение

    parser = argparse.ArgumentParser(
        description="A cross platform window watcher for Activitywatch.\nSupported on: Linux (X11), macOS and Windows."
    )
    parser.add_argument("--host", dest="host")
    parser.add_argument("--port", dest="port")
    parser.add_argument("--testing", dest="testing", action="store_true")
    parser.add_argument(
        "--exclude-title",
        dest="exclude_title",
        action="store_true",
        default=default_exclude_title,
    )
    parser.add_argument(
        "--exclude-titles",
        dest="exclude_titles",
        nargs='+',
        default=default_exclude_titles,
        help="Exclude window titles by regular expression. Can specify multiple times."
    )
    parser.add_argument("--verbose", dest="verbose", action="store_true")
    parser.add_argument(
        "--poll-time", dest="poll_time", type=float, default=default_poll_time
    )
    parser.add_argument(
        "--strategy",
        dest="strategy",
        default=default_strategy_macos,
        choices=["jxa", "applescript", "swift"],
        help="(macOS only) strategy to use for retrieving the active window",
    )
    parser.add_argument(
        "--always-track-apps",
        dest="always_track_apps",
        nargs='+',
        default=default_always_track_apps,
        help="List of applications where window titles should always be tracked."
    )

    parsed_args = parser.parse_args()
    return parsed_args
