import argparse

from aw_core.config import load_config_toml

default_config = """
[aw-watcher-window]
exclude_title = false
exclude_titles = []
poll_time = 1.0
strategy_macos = "swift"
research_enabled = false

[aw-watcher-window.research_category_map]
""".strip()


def load_config():
    return load_config_toml("aw-watcher-window", default_config)["aw-watcher-window"]


def parse_args():
    config = load_config()

    default_poll_time = config["poll_time"]
    default_exclude_title = config["exclude_title"]
    default_exclude_titles = config["exclude_titles"]
    default_strategy_macos = config["strategy_macos"]
    default_research_enabled = config.get("research_enabled", False)

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
        "--research",
        dest="research_enabled",
        action="store_true",
        default=default_research_enabled,
        help="Enable Research Edition mode: browser titles are classified into study categories, non-browser titles are dropped. Category map must be set in the config file. Not supported with --strategy swift on macOS.",
    )
    parsed_args = parser.parse_args()
    return parsed_args
