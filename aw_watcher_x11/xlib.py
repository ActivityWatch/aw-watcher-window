"""
Highly WIP, copy-pasted from activitywatch-old.

Uses python-xlib.
"""

from typing import Optional
from time import sleep
from datetime import datetime, timedelta
import logging

import psutil

import Xlib
import Xlib.display
from Xlib.xobject.drawable import Window
from Xlib import X, Xatom


class Watcher:
    def __init__(self):
        self.display = Xlib.display.Display()
        self.screen = self.display.screen()

        self._last_window = None
        self._active_window = None

        self.window_name = None
        self.pid = None
        self.cls = None
        self.process = None
        self.selected_at = None

        self.last_name = None
        self.last_pid = None
        self.last_cls = None
        self.last_process = None
        self.last_selected_at = None

    def last_window(self) -> Window:
        return self._last_window

    def update_last_window(self):
        self._last_window = self.active_window
        self.last_selected_at = self.selected_at
        self.last_pid = self.pid
        self.last_cmd = self.cmd
        self.last_name, self.last_cls = self.window_name, self.cls
        self.last_process = self.process

    def active_window(self) -> Window:
        return self._active_window

    def get_current_window_id(self) -> Optional[int]:
        atom = self.display.get_atom("_NET_ACTIVE_WINDOW")
        window_prop = self.screen.root.get_full_property(atom, X.AnyPropertyType)
        if window_prop is None:
            logging.warning("window_prop was None")
            return None
        window_id = window_prop.value[-1] if window_prop.value[-1] != 0 else window_prop.value[0]
        return window_id

    def update_active_window(self) -> bool:
        """Updates the active window and stores its properties
        Returns True if changed, False if was unchanged"""
        window_id = self.get_current_window_id()
        if not window_id:
            return False
        window = self.get_window(window_id)

        if self.last_window is not None:
            # Was not the first window
            if self.last_window.id == window_id:
                # If window was same as last
                return False

        try:
            pid = self.get_window_pid(window)
        except Xlib.error.BadWindow as e:
            logging.error("Error while updating active window, trying again.")
            logging.error(e, exc_info=True)
            sleep(1)
            return False

        self.pid = pid
        self.window_name, self.cls = self.get_window_name(window)
        self.process = self.process_by_pid(self.pid)
        self.cmd = self.process.cmdline()
        self.selected_at = datetime.now()

        self._active_window = window

        return True

    def run(self):
        success = False
        while not success:
            success = self.update_active_window()

        logging.debug("First focus is '{}'".format(self.window_name))

        self.update_last_window()

        while True:
            # TODO: Make sleep interval a setting
            sleep(0.1)
            try:
                self.loop()
            except Exception as e:
                logging.error("Exception was thrown while running loop: '{}', trying again.".format(e))
                continue

    def loop(self):
        changed = self.update_active_window()
        if not changed:
            return

        # Creation of the activity that just ended
        event = Event(self.last_cls, self.last_selected_at, datetime.now(), cmd=self.last_cmd)

        logging.debug("Switched to '{}' with PID: {}".format(self.cls, self.pid))

        self.update_last_window()


    def get_window(self, window_id) -> Window:
        return self.display.create_resource_object('window', window_id)

    @staticmethod
    def get_window_name(window) -> (str, str):
        name, cls = None, None
        while window:
            cls = window.get_wm_class()
            name = window.get_wm_name()
            if not cls:
                window = window.query_tree().parent
            else:
                break
        return name, cls

    def get_window_pid(self, window: Window) -> str:
        atom = self.display.get_atom("_NET_WM_PID")
        pid_property = window.get_full_property(atom, X.AnyPropertyType)
        if pid_property:
            pid = pid_property.value[-1]
            return pid
        else:
            # TODO: Needed?
            raise Exception("pid_property was None")

    def get_current_pid(self):
        return self.get_window_pid(self.active_window)

    @staticmethod
    def process_by_pid(pid: str) -> psutil.Process:
        return psutil.Process(int(pid))

if __name__ == "__main__":
    w = Watcher()
    wid = w.get_current_window_id()
    window = w.get_window(wid)
    print(wid, window)
    print(w.get_window_name(window))
