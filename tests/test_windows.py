import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows-only")

HOST_PID = 100
FRAME = 1  # ApplicationFrameHost.exe frame window
TITLE_BAR = 2  # child owned by the frame host itself
APP_WINDOW = 3  # CoreWindow owned by the UWP app


@pytest.fixture
def windows():
    from aw_watcher_window import windows

    return windows


def _fake_windows(monkeypatch, windows, children, owners):
    """Fake the Win32 calls: `children` lists the frame's child windows,
    `owners` maps each window to the pid of its owning process."""
    monkeypatch.setattr(
        windows.win32process,
        "GetWindowThreadProcessId",
        lambda hwnd: (0, owners[hwnd]),
    )

    def enum_child_windows(hwnd, callback, extra):
        for child in children:
            callback(child, extra)

    monkeypatch.setattr(windows.win32gui, "EnumChildWindows", enum_child_windows)


def test_get_uwp_app_window_returns_child_owned_by_app(monkeypatch, windows):
    _fake_windows(
        monkeypatch,
        windows,
        children=[TITLE_BAR, APP_WINDOW],
        owners={FRAME: HOST_PID, TITLE_BAR: HOST_PID, APP_WINDOW: 200},
    )
    assert windows.get_uwp_app_window(FRAME) == APP_WINDOW


def test_get_uwp_app_window_none_before_app_window_attached(monkeypatch, windows):
    # For a moment after activation, the frame only has its own children
    _fake_windows(
        monkeypatch,
        windows,
        children=[TITLE_BAR],
        owners={FRAME: HOST_PID, TITLE_BAR: HOST_PID},
    )
    assert windows.get_uwp_app_window(FRAME) is None


def _fake_foreground(monkeypatch, windows, app_names, uwp_window):
    monkeypatch.setattr(windows, "get_active_window_handle", lambda: FRAME)
    monkeypatch.setattr(windows, "get_app_name", lambda hwnd: app_names[hwnd])
    monkeypatch.setattr(windows, "get_uwp_app_window", lambda hwnd: uwp_window)
    monkeypatch.setattr(windows, "get_window_title", lambda hwnd: "Calculator")


def test_current_window_reports_uwp_app_instead_of_frame_host(monkeypatch, windows):
    from aw_watcher_window.lib import get_current_window_windows

    _fake_foreground(
        monkeypatch,
        windows,
        app_names={FRAME: "ApplicationFrameHost.exe", APP_WINDOW: "CalculatorApp.exe"},
        uwp_window=APP_WINDOW,
    )
    assert get_current_window_windows() == {
        "app": "CalculatorApp.exe",
        "title": "Calculator",
    }


def test_current_window_keeps_frame_host_when_app_window_not_found(
    monkeypatch, windows
):
    from aw_watcher_window.lib import get_current_window_windows

    _fake_foreground(
        monkeypatch,
        windows,
        app_names={FRAME: "ApplicationFrameHost.exe"},
        uwp_window=None,
    )
    assert get_current_window_windows() == {
        "app": "ApplicationFrameHost.exe",
        "title": "Calculator",
    }


def test_current_window_ignores_non_uwp_apps(monkeypatch, windows):
    from aw_watcher_window.lib import get_current_window_windows

    def fail(hwnd):
        raise AssertionError("should not look for a UWP child")

    _fake_foreground(
        monkeypatch, windows, app_names={FRAME: "chrome.exe"}, uwp_window=None
    )
    monkeypatch.setattr(windows, "get_uwp_app_window", fail)
    assert get_current_window_windows()["app"] == "chrome.exe"


def test_current_window_keeps_frame_host_when_child_lookup_fails(monkeypatch, windows):
    from aw_watcher_window.lib import get_current_window_windows

    def fail(hwnd):
        raise OSError("access denied")

    _fake_foreground(
        monkeypatch,
        windows,
        app_names={FRAME: "ApplicationFrameHost.exe"},
        uwp_window=None,
    )
    monkeypatch.setattr(windows, "get_uwp_app_window", fail)
    assert get_current_window_windows()["app"] == "ApplicationFrameHost.exe"
