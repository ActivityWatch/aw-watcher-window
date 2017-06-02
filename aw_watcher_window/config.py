from configparser import ConfigParser

from aw_core.config import load_config as _load_config


def load_config():
    default_client_config = ConfigParser()
    default_client_config["aw-watcher-window"] = {
        "poll_time": "1.0",
        "update_time": "15.0",
    }

    return _load_config("aw-watcher-window", default_client_config)
