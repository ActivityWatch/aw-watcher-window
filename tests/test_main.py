from aw_watcher_window.macos_cli import build_swift_command


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
