import logging
import sys
from typing import Optional


if sys.platform.startswith("linux"):
    from . import xprop
elif sys.platform == "darwin":
    from . import macos
elif sys.platform in ["win32", "cygwin"]:
    from . import windows

logger = logging.getLogger(__name__)


def get_current_window_linux() -> Optional[dict]:
    active_window_id = xprop.get_active_window_id()
    if active_window_id == "0x0":
        logger.warning("Failed to find active window, id found was 0x0")
        return None
    w = xprop.get_windows([active_window_id], active_window_id)[0]
    window = {"appname": w["class"][1], "title": w["name"]}
    return window


def get_current_window_macos() -> Optional[dict]:
    info = macos.getInfo()
    app = macos.getApp(info)
    title = macos.getTitle(info)
    return {"title": title, "appname": app}


def get_current_window_windows() -> Optional[dict]:
    window_handle = windows.get_active_window_handle()
    app = windows.get_app_name(window_handle)
    title = windows.get_window_title(window_handle)

    if app is None or title is None:
        return None

    return {"appname": app, "title": title}


def get_current_window() -> Optional[dict]:
    # TODO: Implement with_title kwarg as option
    if sys.platform.startswith("linux"):
        return get_current_window_linux()
    elif sys.platform == "darwin":
        return get_current_window_macos()
    elif sys.platform in ["win32", "cygwin"]:
        return get_current_window_windows()
    else:
        raise Exception("Unknown platform: {}".format(sys.platform))

