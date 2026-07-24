import argparse

from aw_core.config import load_config_toml

default_config = """
[aw-watcher-window]
exclude_title = false
exclude_titles = []
poll_time = 1.0
strategy_macos = "swift"
host = ""
port = ""
auth_user = ""
auth_password = ""
""".strip()


def load_config():
    return load_config_toml("aw-watcher-window", default_config)["aw-watcher-window"]


def parse_args():
    config = load_config()

    default_poll_time = config["poll_time"]
    default_exclude_title = config["exclude_title"]
    default_exclude_titles = config["exclude_titles"]
    default_strategy_macos = config["strategy_macos"]
    default_host = config["host"] or None
    default_port = config["port"] or None
    default_auth_user = config["auth_user"]
    default_auth_password = config["auth_password"]

    parser = argparse.ArgumentParser(
        description="A cross platform window watcher for Activitywatch.\nSupported on: Linux (X11), macOS and Windows."
    )
    parser.add_argument("--host", dest="host", default=default_host)
    parser.add_argument("--port", dest="port", default=default_port)
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
        "--auth-user",
        dest="auth_user",
        default=default_auth_user,
        help="Username for HTTP Basic Auth (for nginx-proxied servers)",
    )
    parser.add_argument(
        "--auth-password",
        dest="auth_password",
        default=default_auth_password,
        help="Password for HTTP Basic Auth (for nginx-proxied servers)",
    )
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
