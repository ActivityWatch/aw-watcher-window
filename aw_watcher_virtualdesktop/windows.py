import os
import time
from typing import Optional

import win32api
import win32gui
import win32process
import wmi


def get_app_path(hwnd) -> Optional[str]:
    """Get application path given hwnd."""
    path = None
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            process = win32api.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION = 0x0400
        except Exception:
            return None
        try:
            path = win32process.GetModuleFileNameEx(process, 0)
        finally:
            win32api.CloseHandle(process)
    except Exception:
        return None
    return path


def get_app_name(hwnd) -> Optional[str]:
    """Get application filename given hwnd."""
    try:
        path = get_app_path(hwnd)
    except Exception:
        return None
    if path is None:
        return None
    return os.path.basename(path)


def get_window_title(hwnd):
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return None


def get_active_window_handle():
    try:
        hwnd = win32gui.GetForegroundWindow()
        return hwnd
    except Exception:
        return None

# WMI-version, used as fallback if win32gui/win32process/win32api fails (such as for "run as admin" processes)

c = wmi.WMI()

"""
Much of this derived from: http://stackoverflow.com/a/14973422/965332
"""

def get_app_name_wmi(hwnd) -> Optional[str]:
    """Get application filename given hwnd."""
    name = None
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            for p in c.query("SELECT Name FROM Win32_Process WHERE ProcessId = %s" % str(pid)):
                name = p.Name
                break
        except Exception:
            return None
    except Exception:
        return None
    return name

def get_app_path_wmi(hwnd) -> Optional[str]:
    """Get application path given hwnd."""
    path = None
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        for p in c.query(
            "SELECT ExecutablePath FROM Win32_Process WHERE ProcessId = %s" % str(pid)
        ):
            path = p.ExecutablePath
            break
    except Exception:
        return None
    return path

if __name__ == "__main__":
    while True:
        hwnd = get_active_window_handle()
        print("Title:", get_window_title(hwnd))
        print("App:        ", get_app_name(hwnd))
        print("App (wmi):  ", get_app_name_wmi(hwnd))
        print("Path:       ", get_app_path(hwnd))
        print("Path (wmi): ", get_app_path_wmi(hwnd))
        time.sleep(1.0)
