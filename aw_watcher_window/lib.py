import sys
from typing import Callable, Dict, Optional


def get_current_window_linux() -> Dict[str, str]:
    from . import xlib
    window = xlib.get_current_window()

    if window is None:
        cls = "unknown"
        name = "unknown"
    else:
        cls = xlib.get_window_class(window)
        name = xlib.get_window_name(window)

    return {"appname": cls, "title": name}


def initialize_get_macos_window() -> Callable[[], Dict[str, str]]:
    from . import macos
    def get_current_window_macos() -> Dict[str, str]:
        app = macos.get_current_app()
        print ("appname" + macos.get_app_name(app) + ", title" + macos.get_app_title(app))
        return {"appname": macos.get_app_name(app), "title": macos.get_app_title(app)}
    return get_current_window_macos

def get_current_window_windows() -> Dict[str, str]:
    from . import windows
    window_handle = windows.get_active_window_handle()
    app = windows.get_app_name(window_handle)
    title = windows.get_window_title(window_handle)

    if app is None:
        app = "unknown"
    if title is None:
        title = "unknown"

    return {"appname": app, "title": title}


def get_current_window() -> Optional[Callable[[], Dict[str, str]]]:
    if sys.platform.startswith("linux"):
        return get_current_window_linux
    elif sys.platform == "darwin":
        return initialize_get_macos_window()
    elif sys.platform in ["win32", "cygwin"]:
        return get_current_window_windows
    else:
        raise Exception("Unknown platform: {}".format(sys.platform))
