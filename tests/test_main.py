from types import SimpleNamespace

import pytest

import aw_watcher_window.main as main_module
from aw_watcher_window.exceptions import FatalError
from aw_watcher_window.macos_cli import build_swift_command


def test_research_mode_rejects_macos_swift_strategy(monkeypatch):
    monkeypatch.setattr(main_module.sys, "platform", "darwin")
    args = SimpleNamespace(research_enabled=True, strategy="swift")

    with pytest.raises(FatalError, match="not supported with the macOS swift strategy"):
        main_module.ensure_research_strategy_supported(args)


def test_research_mode_allows_macos_jxa_strategy(monkeypatch):
    monkeypatch.setattr(main_module.sys, "platform", "darwin")
    args = SimpleNamespace(research_enabled=True, strategy="jxa")

    main_module.ensure_research_strategy_supported(args)


def test_normal_mode_allows_macos_swift_strategy(monkeypatch):
    monkeypatch.setattr(main_module.sys, "platform", "darwin")
    args = SimpleNamespace(research_enabled=False, strategy="swift")

    main_module.ensure_research_strategy_supported(args)


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
