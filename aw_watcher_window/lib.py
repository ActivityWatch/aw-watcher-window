import sys
from typing import Callable, Dict, Optional, Any


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


def get_current_window_macos() -> Dict[str, str]:
    from . import macos
    # TODO: This should return the latest event, or block until there is one
    return macos.get_window_event()


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


def init(callback: Callable[[], Any]):
    """
    Initializes whatever is needed.
    Might block main thread, but will return control to `callback` on a new thread (or on the main thread, if not needed for something else).
    """
    if sys.platform == "darwin":
        from . import macos
        return macos.init(callback)
    else:
        callback()


def get_current_window() -> Dict[str, str]:
    if sys.platform.startswith("linux"):
        return get_current_window_linux()
    elif sys.platform == "darwin":
        return get_current_window_macos()
    elif sys.platform in ["win32", "cygwin"]:
        return get_current_window_windows()
    raise Exception("Unknown platform: {}".format(sys.platform))
