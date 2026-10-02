import re
from types import SimpleNamespace

import pytest

import aw_watcher_window.main as main_module
from aw_watcher_window.macos_cli import build_swift_command


def test_research_mode_passes_map_to_macos_swift_strategy(monkeypatch):
    commands = []

    class FakeProcess:
        pid = 123

        def wait(self):
            return None

    class FakeClient:
        client_name = "aw-watcher-window"
        client_hostname = "host.localdomain"
        server_address = "http://localhost:5600"

        def __init__(self, *args, **kwargs):
            pass

        def create_bucket(self, *args, **kwargs):
            pass

        def wait_for_start(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main_module.sys, "platform", "darwin")
    monkeypatch.setattr(main_module, "background_ensure_permissions", lambda: None)
    monkeypatch.setattr(main_module, "setup_logging", lambda **kwargs: None)
    monkeypatch.setattr(main_module, "ActivityWatchClient", FakeClient)
    monkeypatch.setattr(main_module.signal, "signal", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        main_module.subprocess,
        "Popen",
        lambda command: commands.append(command) or FakeProcess(),
    )
    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            testing=True,
            verbose=False,
            host=None,
            port=None,
            strategy="swift",
            exclude_title=False,
            exclude_titles=[],
            research_enabled=True,
            research_category_map={"youtube": "Youtube"},
            research_app_category_map={},
        ),
    )

    main_module.main()

    assert commands[0][-4:] == [
        "--research",
        "--research-category",
        "youtube",
        "Youtube",
    ]


def test_build_swift_command_omits_optional_filters():
    command = build_swift_command(
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
    )

    assert command == [
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
    ]


def test_build_swift_command_passes_title_filters():
    command = build_swift_command(
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
        exclude_title=True,
        exclude_titles=["Zoom", "Slack.*huddle"],
    )

    assert command == [
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
        "--exclude-title",
        "--exclude-titles",
        "Zoom",
        "--exclude-titles",
        "Slack.*huddle",
    ]


def test_build_swift_command_passes_empty_research_map():
    command = build_swift_command(
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
        research_category_map={},
    )

    assert command == [
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
        "--research",
    ]


def test_build_swift_command_passes_research_categories():
    command = build_swift_command(
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
        research_category_map={"youtube": "Youtube", "gmail": "Email"},
    )

    assert command == [
        "/tmp/aw-watcher-window-macos",
        "http://localhost:5600",
        "bucket",
        "host.localdomain",
        "aw-watcher-window",
        "--research",
        "--research-category",
        "youtube",
        "Youtube",
        "--research-category",
        "gmail",
        "Email",
    ]


def test_research_transform_takes_precedence_over_exclude_titles():
    window = {
        "app": "Chrome",
        "title": "YouTube - Google Chrome",
        "url": "https://youtube.com/watch?v=abc",
    }

    transformed = main_module.transform_window(
        window,
        exclude_titles=[re.compile("youtube", re.IGNORECASE)],
        research_category_map={"youtube": "Youtube"},
    )

    assert transformed == {"app": "Chrome", "title": "Youtube"}


def test_research_transform_takes_precedence_over_exclude_title():
    window = {
        "app": "Chrome",
        "title": "YouTube - Google Chrome",
        "url": "https://youtube.com/watch?v=abc",
    }

    transformed = main_module.transform_window(
        window,
        exclude_title=True,
        research_category_map={"youtube": "Youtube"},
    )

    assert transformed == {"app": "Chrome", "title": "Youtube"}


def test_legacy_exclude_titles_still_apply_without_research_mode():
    window = {"app": "Chrome", "title": "YouTube - Google Chrome"}

    transformed = main_module.transform_window(
        window,
        exclude_titles=[re.compile("youtube", re.IGNORECASE)],
    )

    assert transformed == {"app": "Chrome", "title": "excluded"}


@pytest.mark.parametrize(
    "poll_time,expected_pulsetime",
    [
        (1.0, 2.0),
        (2.0, 3.0),
        (5.0, 7.5),
        (10.0, 15.0),
    ],
)
def test_pulsetime_scales_with_poll_time(poll_time: float, expected_pulsetime: float):
    assert main_module.compute_pulsetime(poll_time) == expected_pulsetime


@pytest.mark.parametrize(
    "returncode,expected",
    [
        (None, 0),
        (0, 0),
        (1, 1),
        (-6, 134),  # SIGABRT
        (-11, 139),  # SIGSEGV
        (134, 134),
    ],
)
def test_swift_helper_exit_status(returncode, expected):
    assert main_module.swift_helper_exit_status(returncode) == expected


def test_swift_strategy_propagates_helper_crash(monkeypatch):
    class FakeProcess:
        pid = 123

        def wait(self):
            return -6  # SIGABRT from an uncaught NSException

    class FakeClient:
        client_name = "aw-watcher-window"
        client_hostname = "host.localdomain"
        server_address = "http://localhost:5600"

        def __init__(self, *args, **kwargs):
            pass

        def create_bucket(self, *args, **kwargs):
            pass

        def wait_for_start(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(main_module.sys, "platform", "darwin")
    monkeypatch.setattr(main_module, "background_ensure_permissions", lambda: None)
    monkeypatch.setattr(main_module, "setup_logging", lambda **kwargs: None)
    monkeypatch.setattr(main_module, "ActivityWatchClient", FakeClient)
    monkeypatch.setattr(main_module.signal, "signal", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module.subprocess, "Popen", lambda command: FakeProcess())
    monkeypatch.setattr(
        main_module,
        "parse_args",
        lambda: SimpleNamespace(
            testing=True,
            verbose=False,
            host=None,
            port=None,
            strategy="swift",
            exclude_title=False,
            exclude_titles=[],
            research_enabled=False,
            research_category_map={},
            research_app_category_map={},
        ),
    )

    with pytest.raises(SystemExit) as exc:
        main_module.main()
    assert exc.value.code == 134


# --- Wayland / X-auth diagnostic tests ---


def test_warn_wayland_once_logs_on_wayland_display(monkeypatch, caplog):
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.delenv("XDG_SESSION_TYPE", raising=False)
    import logging

    with caplog.at_level(logging.WARNING, logger="aw_watcher_window.main"):
        main_module._warn_wayland_once()

    assert any("Wayland" in r.message for r in caplog.records)
    assert any("aw-watcher-window-wayland" in r.message for r in caplog.records)


def test_warn_wayland_once_logs_on_xdg_session_type(monkeypatch, caplog):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    import logging

    with caplog.at_level(logging.WARNING, logger="aw_watcher_window.main"):
        main_module._warn_wayland_once()

    assert any("Wayland" in r.message for r in caplog.records)


def test_warn_wayland_once_silent_on_x11(monkeypatch, caplog):
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    import logging

    with caplog.at_level(logging.WARNING, logger="aw_watcher_window.main"):
        main_module._warn_wayland_once()

    assert not caplog.records


def test_heartbeat_loop_xconn_error_logs_once_and_backs_off(monkeypatch, caplog):
    """DisplayConnectionError must log exactly once and apply exponential backoff."""
    import logging

    # Minimal fake DisplayConnectionError that _is_xconn_error will recognise.
    # Skip only when python-xlib is unavailable; a construction error below must
    # fail the test rather than masquerade as a missing dependency (#155 CodeQL
    # flagged `Xlib` as possibly uninitialised after the try/except import).
    Xlib_error = pytest.importorskip("Xlib.error")

    fake_exc = Xlib_error.DisplayConnectionError(":0", b"Authorization required")

    call_count = [0]
    sleep_calls = []

    def fake_get_window(_strategy):
        call_count[0] += 1
        if call_count[0] <= 3:
            raise fake_exc
        # After 3 auth errors, raise FatalError to exit the loop cleanly.
        raise main_module.FatalError()

    class FakeClient:
        def heartbeat(self, *args, **kwargs):
            pass

    monkeypatch.setattr(main_module, "get_current_window", fake_get_window)
    monkeypatch.setattr(main_module, "sleep", lambda s: sleep_calls.append(s))
    monkeypatch.setattr(main_module.os, "getppid", lambda: 999)
    monkeypatch.setattr(main_module.sys, "platform", "linux")

    with caplog.at_level(logging.ERROR, logger="aw_watcher_window.main"):
        main_module.heartbeat_loop(
            FakeClient(),
            "bucket",
            poll_time=1.0,
            strategy="xlib",
        )

    error_records = [
        r for r in caplog.records if "Cannot connect to X display" in r.message
    ]
    assert len(error_records) == 1, "Should log the auth error exactly once"

    # Backoff sleeps should grow: 1s, 2s (poll_time doubles each time)
    assert sleep_calls[0] == 1.0
    assert sleep_calls[1] == 2.0


def test_heartbeat_loop_repeated_exception_logs_once_and_backs_off(monkeypatch, caplog):
    """An identical poll error must not write a traceback per poll (#78)."""
    import logging

    n_errors = 250
    calls = [0]
    sleep_calls = []

    def fake_get_window(_strategy):
        calls[0] += 1
        if calls[0] <= n_errors:
            raise RuntimeError("X connection is dead")
        raise main_module.FatalError()

    class FakeClient:
        def heartbeat(self, *args, **kwargs):
            pass

    monkeypatch.setattr(main_module, "get_current_window", fake_get_window)
    monkeypatch.setattr(main_module, "sleep", lambda s: sleep_calls.append(s))
    monkeypatch.setattr(main_module.os, "getppid", lambda: 999)

    with caplog.at_level(logging.ERROR, logger="aw_watcher_window.main"):
        main_module.heartbeat_loop(
            FakeClient(), "bucket", poll_time=1.0, strategy="xlib"
        )

    tracebacks = [
        r for r in caplog.records if r.exc_info and "Exception thrown" in r.message
    ]
    summaries = [r for r in caplog.records if "Still failing" in r.message]
    assert len(tracebacks) == 1
    assert len(summaries) == 2  # at 100 and 200 repeats
    # Total interval is capped at 60s: extra sleep (on top of the 1s poll_time)
    # grows to at most 59s.
    assert max(sleep_calls) == 59.0
    assert sum(sleep_calls) < n_errors * 60.0  # each poll: poll_time(1s) + extra(≤59s)


def test_heartbeat_loop_alternating_exceptions_backs_off(monkeypatch, caplog):
    """Alternating poll errors must still accumulate backoff and cap tracebacks at one per distinct error."""
    import logging

    n_errors = 20
    calls = [0]
    sleep_calls = []
    # Two distinct RuntimeErrors that alternate each poll.
    error_msgs = ["Error type A", "Error type B"]

    def fake_get_window(_strategy):
        calls[0] += 1
        if calls[0] <= n_errors:
            raise RuntimeError(error_msgs[calls[0] % 2])
        raise main_module.FatalError()

    class FakeClient:
        def heartbeat(self, *args, **kwargs):
            pass

    monkeypatch.setattr(main_module, "get_current_window", fake_get_window)
    monkeypatch.setattr(main_module, "sleep", lambda s: sleep_calls.append(s))
    monkeypatch.setattr(main_module.os, "getppid", lambda: 999)

    with caplog.at_level(logging.ERROR, logger="aw_watcher_window.main"):
        main_module.heartbeat_loop(
            FakeClient(), "bucket", poll_time=1.0, strategy="xlib"
        )

    tracebacks = [
        r for r in caplog.records if r.exc_info and "Exception thrown" in r.message
    ]
    # Exactly one traceback per distinct error signature (2 here), not one per poll.
    assert len(tracebacks) == 2

    # Backoff must grow: with 20 alternating errors the extra sleep must exceed
    # poll_time (1.0) before the loop ends.
    backoff_sleeps = [s for s in sleep_calls if s > 1.0]
    assert len(backoff_sleeps) > 0, "Expected growing backoff on alternating errors"


def test_heartbeat_loop_long_poll_time_no_negative_sleep(monkeypatch):
    """poll_time > 60s must never produce a negative sleep duration."""
    calls = [0]
    sleep_calls = []

    def fake_get_window(_strategy):
        calls[0] += 1
        if calls[0] <= 3:
            raise RuntimeError("some transient error")
        raise main_module.FatalError()

    class FakeClient:
        def heartbeat(self, *args, **kwargs):
            pass

    monkeypatch.setattr(main_module, "get_current_window", fake_get_window)
    monkeypatch.setattr(main_module, "sleep", lambda s: sleep_calls.append(s))
    monkeypatch.setattr(main_module.os, "getppid", lambda: 999)

    main_module.heartbeat_loop(FakeClient(), "bucket", poll_time=120.0, strategy="xlib")

    assert all(s >= 0.0 for s in sleep_calls), f"Negative sleep found: {sleep_calls}"
    # poll_time already exceeds the 60s cap, so no extra backoff is added: the
    # retry interval stays at poll_time rather than being stretched to 180s.
    extra_sleeps = [s for s in sleep_calls if s != 120.0]
    assert extra_sleeps == [], (
        f"Unexpected extra backoff for poll_time=120: {sleep_calls}"
    )
