import sys
from typing import Optional

from .platform import get_virtual_desktop

from .exceptions import FatalError


def get_current_window_linux() -> Optional[dict]:
    from . import xlib

    window = xlib.get_current_window()

    if window is None:
        cls = "unknown"
        name = "unknown"
    else:
        cls = xlib.get_window_class(window)
        name = xlib.get_window_name(window)

    return {"app": cls, "title": name, "virtual_desktop": get_virtual_desktop()}


# macOS support has been disabled. The function is kept for compatibility but
# always raises a FatalError to signal unsupported platform.
def get_current_window_macos(strategy: str) -> Optional[dict]:
    raise FatalError("macOS support has been disabled in this build")

def get_current_window_windows() -> Optional[dict]:
    from . import windows

    window_handle = windows.get_active_window_handle()
    app = None
    title = None
    # まず有効なハンドルかチェック
    if not window_handle or window_handle == 0:
        app = "unknown"
        title = "unknown"
    else:
        # app名取得
        try:
            app = windows.get_app_name(window_handle)
        except Exception:
            app = None
        if not app:
            try:
                app = windows.get_app_name_wmi(window_handle)
            except Exception:
                app = None
        # どちらも失敗した場合
        if not app:
            app = "unknown"
        # タイトル取得
        try:
            title = windows.get_window_title(window_handle)
        except Exception:
            title = None
        if not title:
            title = "unknown"
    return {"app": app, "title": title, "virtual_desktop": get_virtual_desktop()}


def get_current_window(strategy: Optional[str] = None) -> Optional[dict]:
    """
    :raises FatalError: if a fatal error occurs (e.g. unsupported platform, X server closed)
    """

    if sys.platform.startswith("linux"):
        return get_current_window_linux()

    elif sys.platform == "darwin":
        raise FatalError("macOS support disabled")

    elif sys.platform in ["win32", "cygwin"]:
        return get_current_window_windows()
    else:
        raise FatalError(f"Unknown platform: {sys.platform}")
