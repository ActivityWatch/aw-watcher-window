from threading import Thread
from _thread import interrupt_main
from typing import Dict, Tuple, Callable
from time import sleep
from queue import Queue
from datetime import datetime, timezone
import logging

from ApplicationServices import AXIsProcessTrusted
from AppKit import NSObject, NSNotification, NSWorkspace, NSRunningApplication, NSWorkspaceDidActivateApplicationNotification, NSWorkspaceDidDeactivateApplicationNotification
from AppKit import NSAlert, NSAlertFirstButtonReturn, NSURL
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)
from PyObjCTools import AppHelper

logger = logging.getLogger(__name__)

watcher: 'Watcher'


def init(callback: Callable) -> None:
    print("Initializing...")
    background_ensure_permissions()

    global watcher
    watcher = Watcher()

    hand_over_main(watcher, callback)  # will take control of the main thread and spawn a second one for pushing heartbeats


def get_current_window() -> Dict[str, str]:
    return watcher.get_next_event()


class Observer(NSObject):
    queue: "Queue[Tuple[float, Dict[str, str]]]" = Queue()

    def handle_(self, noti: NSNotification) -> None:
        # called by the main event loop
        print(f"Event received {noti}")
        self._set_front_app()

    def _set_front_app(self) -> None:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        self.queue.put((
            datetime.now(tz=timezone.utc).timestamp(),
            {"app": get_app_name(app), "title": get_app_title(app)}
        ))


class Watcher:
    def __init__(self):
        self.observer = Observer.new()

    def run_loop(self):
        """Runs the main event loop, needs to run in the main thread."""
        # NOTE: This event doesn't trigger for window changes nor for application deactivations.
        nc = NSWorkspace.sharedWorkspace().notificationCenter()
        nc.addObserver_selector_name_object_(
            self.observer,
            "handle:",
            NSWorkspaceDidActivateApplicationNotification,
            None)
        # Redundant, they fire at the same time.
        # nc.addObserver_selector_name_object_(
        #     self.observer,
        #     "handle:",
        #     NSWorkspaceDidDeactivateApplicationNotification,
        #     None)
        try:
            AppHelper.runConsoleEventLoop()
        except KeyboardInterrupt:
            print("Main thread was asked to stop, quitting.")

    def stop(self):
        AppHelper.stopEventLoop()

    def get_next_event(self) -> Dict[str, str]:
        return self.observer.queue.get()


def get_app_name(app: NSRunningApplication) -> str:
    return app.localizedName()


def get_app_title(app: NSRunningApplication) -> str:
    pid = app.processIdentifier()
    options = kCGWindowListOptionOnScreenOnly
    windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID)

    for window in windowList:
        lookupPid = window['kCGWindowOwnerPID']
        if (lookupPid == pid):
            print(AXIsProcessTrusted())
            print(window)
            title = window.get('kCGWindowName', None)
            if title:
                return title
            else:
                # This has a risk of spamming the user
                logger.warning("Couldn't get window title, check accessibility permissions")
                return ''

    logger.warning("Couldn't find title by PID")
    return ''


def hand_over_main(watcher, callback):
    """Initializes the main thread and calls back"""
    Thread(target=callback, daemon=True).start()
    watcher.run_loop()


def background_ensure_permissions() -> None:
    # For some reason I get a SIGSEGV when trying to fork here.
    # Python mailinglists indicate that macOS APIs don't like fork(), and that one should use 'forkserver' instead.
    # However, the Python docs also state that 'spawn' and 'forkserver' cannot be used with 'frozen' executables (as produced by PyInstaller).
    # I guess we'll see...
    from multiprocessing import Process, set_start_method
    set_start_method('spawn')  # should be the default in Python 3.8

    print("Checking if we have accessibility permissions... ", end='')
    accessibility_permissions = AXIsProcessTrusted()
    if accessibility_permissions:
        print("We do!")
    else:
        print("We don't, showing dialog.")
        Process(target=show_screencapture_permissions_dialog, args=(())).start()

    # Needed on macOS 10.15+
    # TODO: Add macOS version check to ensure it doesn't break on lower versions
    # This would have been nice, but can't seem to call it through pyobjc... ('unknown location')
    # from Quartz.CoreGraphics import CGRequestScreenCaptureAccess
    # screencapture_permissions = CGRequestScreenCaptureAccess()
    Process(target=show_screencapture_permissions_dialog, args=(())).start()


def show_accessibility_permissions_dialog() -> None:
    title = "Missing accessibility permissions"
    info = ("To let ActivityWatch capture window titles grant it accessibility permissions."
            + "\n\nIf you've already given ActivityWatch accessibility permissions and are still seeing this dialog, try removing and re-adding them (not just checking/unchecking the box).")

    alert = NSAlert.new()
    alert.setMessageText_(title)
    alert.setInformativeText_(info)

    ok_button = alert.addButtonWithTitle_("Open accessibility settings")

    alert.addButtonWithTitle_("Close")
    choice = alert.runModal()
    if choice == NSAlertFirstButtonReturn:
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"))


def show_screencapture_permissions_dialog() -> None:
    # FIXME: When settings are opened, there's no way to add the application.
    #        Probably need to trigger the permission somehow.
    title = "Missing screen capture permissions"
    info = ("To let ActivityWatch capture window titles it needs screen capture permissions (since macOS 10.15+)."
            + "\n\nIf you've already given ActivityWatch screen capture permissions and are still seeing this dialog, try removing and re-adding them (not just checking/unchecking the box).")

    alert = NSAlert.new()
    alert.setMessageText_(title)
    alert.setInformativeText_(info)

    ok_button = alert.addButtonWithTitle_("Open screen capture settings")

    alert.addButtonWithTitle_("Close")
    choice = alert.runModal()
    if choice == NSAlertFirstButtonReturn:
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"))


def test_secondthread():
    print("In second thread")
    print("Listening for events...")

    while True:
        event = watcher.get_next_event()
        print(event)

    print("Exiting")
    watcher.stop()
    #interrupt_main()

def test():
    # Used in debugging

    init(test_secondthread)


if __name__ == "__main__":
    test()
