"""Window class lookup when the watcher's output has gone away.

aw-qt hands its stdio to the watcher, so closing the terminal aw-qt was started
from leaves stdout on a hung-up tty where every write raises EIO. heartbeat_loop
treats OSError as fatal, so nothing on the polling path may write to stdout.
"""

import errno
import importlib
import sys
from types import SimpleNamespace
from unittest import mock

import pytest

pytest.importorskip("Xlib", reason="python-xlib is a Linux-only dependency")

import Xlib.display
import Xlib.error

import aw_watcher_window
from aw_watcher_window import xauth


class HungUpStdout:
    def write(self, _text):
        raise OSError(errno.EIO, "Input/output error")


class FakeWindow:
    def __init__(self, wm_class=None, parent=None):
        self.wm_class = wm_class
        self.parent = parent

    def get_wm_class(self):
        return self.wm_class

    def query_tree(self):
        return SimpleNamespace(parent=self.parent)


class VanishedWindow(FakeWindow):
    """A window destroyed between being reported active and being queried."""

    def get_wm_class(self):
        raise Xlib.error.BadWindow.__new__(Xlib.error.BadWindow)

    def query_tree(self):
        raise Xlib.error.BadWindow.__new__(Xlib.error.BadWindow)


@pytest.fixture
def xlib(monkeypatch):
    # The module connects to the X server at import time.
    monkeypatch.setattr(xauth, "install", lambda: None)
    monkeypatch.setattr(Xlib.display, "Display", mock.MagicMock)
    monkeypatch.delitem(sys.modules, "aw_watcher_window.xlib", raising=False)
    yield importlib.import_module("aw_watcher_window.xlib")
    sys.modules.pop("aw_watcher_window.xlib", None)
    del aw_watcher_window.xlib


def test_window_class_falls_back_to_parent_with_hung_up_stdout(xlib, monkeypatch):
    monkeypatch.setattr(sys, "stdout", HungUpStdout())
    window = FakeWindow(parent=FakeWindow(wm_class=("navigator", "Firefox")))

    assert xlib.get_window_class(window) == "Firefox"


def test_vanished_window_is_unknown_with_hung_up_stdout(xlib, monkeypatch):
    monkeypatch.setattr(sys, "stdout", HungUpStdout())

    assert xlib.get_window_class(VanishedWindow()) == "unknown"
