import argparse

from aw_core.config import load_config_toml

default_config = """
[aw-watcher-virtualdesktop]
exclude_title = false
exclude_titles = []
poll_time = 1.0
""".strip()


def load_config():
    return load_config_toml("aw-watcher-virtualdesktop", default_config)["aw-watcher-virtualdesktop"]


def parse_args():
    config = load_config()

    default_poll_time = config["poll_time"]
    default_exclude_title = config["exclude_title"]
    default_exclude_titles = config["exclude_titles"]

    parser = argparse.ArgumentParser(
        description="A cross platform window watcher for ActivityWatch.\nSupported on: Linux (X11) and Windows."
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
    parser.add_argument("--oneshot", dest="oneshot", action="store_true")
    parser.add_argument(
        "--poll-time", dest="poll_time", type=float, default=default_poll_time
    )
    parsed_args = parser.parse_args()
    return parsed_args
