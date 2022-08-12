import sys
from typing import Optional


def get_current_window_linux() -> Optional[dict]:
    from . import xlib

    window = xlib.get_current_window()

    if window is None:
        cls = "unknown"
        name = "unknown"
    else:
        cls = xlib.get_window_class(window)
        name = xlib.get_window_name(window)

    return {"app": cls, "title": name}


def get_current_window_macos(strategy: str) -> Optional[dict]:
    # TODO should we use unknown when the title is blank like the other platforms?

    # `jxa` is the default & preferred strategy. It includes the url + incognito status
    if strategy == "jxa":
        from . import macos_jxa

        return macos_jxa.getInfo()
    elif strategy == "applescript":
        from . import macos_applescript

        return macos_applescript.getInfo()
    else:
        raise ValueError(f"invalid strategy '{strategy}'")


def get_current_window_windows() -> Optional[dict]:
    from . import windows

    window_handle = windows.get_active_window_handle()
    app = windows.get_app_name(window_handle)
    title = windows.get_window_title(window_handle)

    if app is None:
        app = "unknown"
    if title is None:
        title = "unknown"

    return {"app": app, "title": title}


def get_current_window(strategy: str = None) -> Optional[dict]:
    if sys.platform.startswith("linux"):
        return get_current_window_linux()
    elif sys.platform == "darwin":
        return get_current_window_macos(strategy)
    elif sys.platform in ["win32", "cygwin"]:
        return get_current_window_windows()
    else:
        raise Exception(f"Unknown platform: {sys.platform}")
