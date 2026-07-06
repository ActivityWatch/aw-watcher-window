from types import SimpleNamespace

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
        ),
    )

    main_module.main()

    assert commands[0][-4:] == ["--research", "--research-category", "youtube", "Youtube"]


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
