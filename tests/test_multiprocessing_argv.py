"""The entry point must not feed multiprocessing's own argv into argparse.

In a frozen (PyInstaller) build Python's multiprocessing re-executes the same
binary for helper processes, so the watcher's ``parse_args()`` sees flags like
``--multiprocessing-fork`` and exits the child. See
ActivityWatch/aw-watcher-window#133.
"""

import pytest

import aw_watcher_window.main as main_module

FORK_ARGV = [
    "aw-watcher-window",
    "--multiprocessing-fork",
    "tracker_fd=7",
    "pipe_handle=9",
]
RESOURCE_TRACKER_ARGV = [
    "aw-watcher-window",
    "-B",
    "-S",
    "-I",
    "-c",
    "from multiprocessing.resource_tracker import main;main(6)",
]


@pytest.mark.parametrize("argv", [FORK_ARGV, RESOURCE_TRACKER_ARGV])
def test_is_multiprocessing_child_detects_helper_argv(argv):
    assert main_module.is_multiprocessing_child(argv)


@pytest.mark.parametrize(
    "argv",
    [
        ["aw-watcher-window"],
        ["aw-watcher-window", "--testing"],
        ["aw-watcher-window", "--strategy", "jxa"],
    ],
)
def test_is_multiprocessing_child_ignores_normal_argv(argv):
    assert not main_module.is_multiprocessing_child(argv)


@pytest.mark.parametrize("argv", [FORK_ARGV, RESOURCE_TRACKER_ARGV])
def test_main_skips_argparse_for_multiprocessing_argv(argv, monkeypatch):
    monkeypatch.setattr(main_module.sys, "argv", argv)
    monkeypatch.setattr(main_module.multiprocessing, "freeze_support", lambda: None)

    def _fail():
        raise AssertionError("parse_args must not run for a multiprocessing child")

    monkeypatch.setattr(main_module, "parse_args", _fail)
    main_module.main()  # must return without touching parse_args


def test_main_calls_freeze_support_first(monkeypatch):
    monkeypatch.setattr(main_module.sys, "argv", FORK_ARGV)
    calls = []
    monkeypatch.setattr(
        main_module.multiprocessing,
        "freeze_support",
        lambda: calls.append("freeze_support"),
    )
    monkeypatch.setattr(main_module, "parse_args", lambda: calls.append("parse_args"))

    main_module.main()

    assert calls == ["freeze_support"]
