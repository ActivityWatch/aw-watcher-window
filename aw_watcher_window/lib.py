import sys
import os
from typing import Optional
import psutil
from .nuke_utils import get_nuke_script_path
from .exceptions import FatalError
from .path_utils import normalize_project_path
from .houdini_utils import get_houdini_scene_path

def get_current_window_linux() -> Optional[dict]:
    from . import xlib

    window = xlib.get_current_window()

    if window is None:
        cls = "unknown"
        name = "unknown"
    else:
        cls = xlib.get_window_class(window)
        name = xlib.get_window_name(window)
        try:
            pid = xlib.get_window_pid(window)
        except Exception:
            pid = None

        if cls and "nuke" in cls.lower() and pid:
            full_path = get_nuke_script_path(pid, name)
            if full_path:
                name = full_path

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
        raise FatalError(f"invalid strategy '{strategy}'")


def get_current_window_windows() -> Optional[dict]:
    """
    Windows: возвращаем {"app": <каноническое имя>, "title": <нормализованный путь или 'unknown'/'excluded'>}
    - Для Nuke: пытаемся вытащить .nk через psutil (cmdline/open_files), иначе из title; нормализуем путь.
    - Для Houdini: сначала пробуем взять абсолютный .hip* из title; если нет — пробуем psutil; нормализуем.
    - Для прочих приложений оставляем исходные значения (далее heartbeat_loop решает, исключать ли title).
    """
    from . import windows

    hwnd = windows.get_active_window_handle()

    try:
        app = windows.get_app_name(hwnd)
    except Exception:
        app = windows.get_app_name_wmi(hwnd)

    title = windows.get_window_title(hwnd)

    if app is None:
        app = "unknown"
    if title is None:
        title = "unknown"

    pid = windows.get_window_pid(hwnd)

    lower_app = (app or "").lower()

    if "nuke" in lower_app and pid:
        canonical_app = "NukeX"
        try:
            nuke_path = get_nuke_script_path(pid, title)
            if nuke_path:
                title = normalize_project_path(nuke_path)
        except Exception:
            pre = title.split(" - ", 1)[0].strip()
            if pre.lower().endswith(".nk") and os.path.isabs(pre):
                title = normalize_project_path(pre)
        return {"app": canonical_app, "title": title}

    if "houdini" in lower_app and pid:
        canonical_app = "Houdini FX"

        pre = title.split(" - ", 1)[0].strip()
        if pre.lower().endswith((".hip", ".hiplc", ".hipnc")) and os.path.isabs(pre):
            title = normalize_project_path(pre)
            return {"app": canonical_app, "title": title}

        try:
            hip_path = get_houdini_scene_path(pid, title)
            if hip_path:
                title = normalize_project_path(hip_path)
        except Exception:
            pass

        return {"app": canonical_app, "title": title}

    return {"app": app, "title": title}


def get_current_window(strategy: Optional[str] = None) -> Optional[dict]:
    """
    :raises FatalError: if a fatal error occurs (e.g. unsupported platform, X server closed)
    """

    if sys.platform.startswith("linux"):
        return get_current_window_linux()
    elif sys.platform == "darwin":
        if strategy is None:
            raise FatalError("macOS strategy not specified")
        return get_current_window_macos(strategy)
    elif sys.platform in ["win32", "cygwin"]:
        return get_current_window_windows()
    else:
        raise FatalError(f"Unknown platform: {sys.platform}")
