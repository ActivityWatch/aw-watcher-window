import argparse

import tomlkit

from aw_core.config import load_config_toml

# Only end-user options belong here. load_config_toml() writes this template into
# the user's config file on first run; it comments out keys but NOT table headers,
# so anything listed here is authored into every fresh install's config.
default_config = """
[aw-watcher-window]
exclude_title = false
exclude_titles = []
poll_time = 1.0
strategy_macos = "swift"
""".strip()

# Research Edition defaults, deliberately kept out of default_config: these are
# study/dev knobs, not end-user options, and should not be persisted into the
# config of users who are not part of a study. They are still read normally when
# a user does set them (see load_config), which is how the Research Edition build
# and study participants configure them.
#
# The Research Edition release build rewrites the flag below with
#   sed -i 's/^research_enabled = false$/research_enabled = true/'
# (ActivityWatch/activitywatch, .github/workflows/release.yml). Keep that line at
# column 0 and byte-identical.
research_defaults = """
research_enabled = false
""".strip()


def load_config():
    config = load_config_toml("aw-watcher-window", default_config)["aw-watcher-window"]
    # Research defaults fill in only what the user's config didn't set.
    for key, value in tomlkit.parse(research_defaults).items():
        config.setdefault(key, value)
    return config


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
    research_group = parser.add_mutually_exclusive_group()
    research_group.add_argument(
        "--research",
        dest="research_enabled",
        action="store_true",
        default=default_research_enabled,
        help="Enable Research Edition mode: browser titles are classified into study categories, non-browser titles are dropped. Category map must be set in the config file.",
    )
    research_group.add_argument(
        "--no-research",
        dest="research_enabled",
        action="store_false",
        help="Disable Research Edition mode, even when enabled in the config file.",
    )
    parsed_args = parser.parse_args()
    parsed_args.research_category_map = dict(config.get("research_category_map", {}))
    parsed_args.research_app_category_map = dict(config.get("research_app_category_map", {}))
    parsed_args.privacy_filter_rules = list(config.get("privacy_filter", []))
    return parsed_args
