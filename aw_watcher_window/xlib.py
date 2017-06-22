from typing import Optional
import logging

import Xlib
import Xlib.display
from Xlib.xobject.drawable import Window
from Xlib import X, Xatom

display = Xlib.display.Display()
screen = display.screen()

NET_WM_NAME = display.intern_atom("_NET_WM_NAME")
UTF8_STRING = display.intern_atom("UTF8_STRING")


def _get_current_window_id() -> Optional[int]:
    atom = display.get_atom("_NET_ACTIVE_WINDOW")
    window_prop = screen.root.get_full_property(atom, X.AnyPropertyType)

    if window_prop is None:
        logging.warning("window_prop was None")
        return None

    # window_prop may contain more than one value, but it seems that it's always the first we want.
    # The second has in my attempts always been 0 or rubbish.
    window_id = window_prop.value[0]
    return window_id if window_id != 0 else None


def _get_window(window_id: int) -> Window:
    return display.create_resource_object('window', window_id)


def get_current_window() -> Optional[Window]:
    window_id = _get_current_window_id()
    if window_id is None:
        return None
    else:
        return _get_window(window_id)

# Things that can lead to unknown cls/name:
#  - (cls+name) Empty desktop in xfce (no window focused)
#  - (name) Chrome (fixed, didn't support when WM_NAME was UTF8_STRING)


def get_window_name(window: Window) -> str:
    """ After some annoying debugging I resorted to pretty much copying selfspy.
        Source: https://github.com/gurgeh/selfspy/blob/8a34597f81000b3a1be12f8cde092a40604e49cf/selfspy/sniff_x.py#L165 """
    d = window.get_full_property(NET_WM_NAME, UTF8_STRING)
    if d is None or d.format != 8:
        # Fallback.
        r = window.get_wm_name()
        if type(r) == str:
            return r
        else:
            logging.warning("I don't think this case will ever happen, but not sure so leaving this message here just in case.")
            return r.decode('latin1')  # WM_NAME with type=STRING.
    else:
        # Fixing utf8 issue on Ubuntu (https://github.com/gurgeh/selfspy/issues/133)
        # Thanks to https://github.com/gurgeh/selfspy/issues/133#issuecomment-142943681
        try:
            return d.value.decode('utf8')
        except UnicodeError:
            return d.value.encode('utf8').decode('utf8')


def get_window_class(window: Window) -> str:
    cls = None

    try:
        cls = window.get_wm_class()
        cls = cls[1]
    except Xlib.error.BadWindow:
        logging.warning("Unable to get window class, got a BadWindow exception.")

    # TODO: Is this needed?
    if not cls:
        print("")
        logging.warning("Code made an unclear branch")
        window = window.query_tree().parent
        if window:
            return get_window_class(window)
        else:
            return "unknown"
    return cls


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
        window = get_current_window()
        if window is None:
            print("unable to get active window")
            name, cls = "unknown", "unknown"
        else:
            cls = get_window_class(window)
            name = get_window_name(window)
        print("name:", name)
        print("class:", cls)

        sleep(1)
