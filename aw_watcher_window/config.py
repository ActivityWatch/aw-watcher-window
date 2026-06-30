import argparse

from aw_core.config import load_config_toml

default_config = """
[aw-watcher-window]
exclude_title = false
exclude_titles = []
poll_time = 1.0
strategy_macos = "swift"

# Title cleaning rules - apply regex replacements to window titles for specific apps
# [[title_cleaning_rules.rules]]
# app = "firefox"
# pattern = "( - Mozilla Firefox)$"
# replacement = ""
""".strip()


def load_config():
    return load_config_toml("aw-watcher-window", default_config)


def get_title_cleaning_rules():
    """Load title cleaning rules from configuration"""
    config = load_config_toml("aw-watcher-window", default_config)
    rules = []
    
    # Check if title_cleaning_rules section exists
    if "title_cleaning_rules" in config and "rules" in config["title_cleaning_rules"]:
        for rule in config["title_cleaning_rules"]["rules"]:
            if "app" in rule and "pattern" in rule:
                rules.append({
                    "app": rule["app"],
                    "pattern": rule["pattern"],
                    "replacement": rule.get("replacement", "")
                })
    
    return rules


def parse_args():
    config = load_config()["aw-watcher-window"]

    default_poll_time = config["poll_time"]
    default_exclude_title = config["exclude_title"]
    default_exclude_titles = config["exclude_titles"]
    default_strategy_macos = config["strategy_macos"]

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
    parsed_args = parser.parse_args()
    return parsed_args
