from typing import Optional
import logging
from typing import Tuple

import Xlib
import Xlib.display
from Xlib.xobject.drawable import Window
from Xlib import X, Xatom

display = Xlib.display.Display()
screen = display.screen()


def get_current_window_id() -> Optional[int]:
    atom = display.get_atom("_NET_ACTIVE_WINDOW")
    window_prop = screen.root.get_full_property(atom, X.AnyPropertyType)

    if window_prop is None:
        logging.warning("window_prop was None")
        return None

    # window_prop may contain more than one value, but it seems that it's always the first we want.
    # The second has in my attempts always been 0 or rubbish.
    window_id = window_prop.value[0]
    return window_id if window_id != 0 else None


def get_window(window_id: int) -> Window:
    return display.create_resource_object('window', window_id)

# Things that can lead to unknown cls/name:
#  - (cls+name) Empty desktop in xfce (no window focused)
#  - (name) Chrome (fixed, didn't support when WM_NAME was UTF8_STRING)


def _get_window_name(window: Window) -> str:
    name = None

    try:
        # Doesn't seem to work for UTF8 titles:
        # name = window.get_wm_name()
        p_wm_name = window.get_full_property(Xatom.WM_NAME, 0)
        name = p_wm_name.value
    except Xlib.error.BadWindow:
        logging.warning("Unable to get window name, got a BadWindow exception.")

    if not name:
        name = "unknown"

    return name


def _get_window_class(window: Window) -> str:
    cls = None

    try:
        cls = window.get_wm_class()
        cls = cls[0].lower()
    except Xlib.error.BadWindow:
        logging.warning("Unable to get window class, got a BadWindow exception.")

    # TODO: Is this needed?
    if not cls:
        print("")
        logging.warning("Code made an unclear branch")
        window = window.query_tree().parent
        if window:
            return _get_window_class(window)
        else:
            return "unknown"
    return cls


def get_window_name(window: Window) -> Tuple[str, str]:
    return _get_window_name(window), _get_window_class(window)


def get_window_pid(window: Window) -> str:
    atom = display.get_atom("_NET_WM_PID")
    pid_property = window.get_full_property(atom, X.AnyPropertyType)
    if pid_property:
        pid = pid_property.value[-1]
        return pid
    else:
        # TODO: Needed?
        raise Exception("pid_property was None")

if __name__ == "__main__":
    from time import sleep

    while True:
        print("-" * 20)
        window_id = get_current_window_id()
        if window_id is None:
            print("unable to get window id")
            name, cls = "unknown", "unknown"
        else:
            print("wid:", window_id)
            window = get_window(window_id)
            cls = _get_window_name(window)
            name = _get_window_class(window)
        print("name:", name)
        print("class:", cls)

        sleep(1)
