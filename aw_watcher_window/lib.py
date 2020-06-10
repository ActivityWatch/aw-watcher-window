import sys
import json
from typing import Optional


class Linux:
    def __init__(self):
        try:
            import pydbus
            self.bus = pydbus.SessionBus()
        except ModuleNotFoundError:
            self.bus = False
            self.gnome_shell = None
        
        if self.bus:
            import gi.repository.GLib
            try:
                self.gnome_shell = self.bus.get("org.gnome.Shell")
                self._setup_gnome()
            except gi.repository.GLib.Error:
                self.gnome_shell = None

    def get_current_window(self) -> dict:
        if self.gnome_shell:
            return self.get_current_window_gnome_shell()
        
        return self.get_current_window_x11()
    
    def _setup_gnome(self) -> None:
        js_code = """
        global._aw_current_window = () => {
            var window_list = global.get_window_actors();
            var active_window_actor = window_list.find(window => window.meta_window.has_focus());
            var active_window = active_window_actor.get_meta_window()
            var vm_class = active_window.get_wm_class();
            var title = active_window.get_title()
            var result = {"title": title, "appname": vm_class};
            return result    
        }
        """
        ok, result = self.gnome_shell.Eval(js_code)
        if not ok:
            raise Error("failed seting up gnome-shell function: " + result)

    def get_current_window_gnome_shell(self) -> dict:
        """get current app from GNOME Shell via dbus"""

        ok, result = self.gnome_shell.Eval("global._aw_current_window()")
        if ok:
            result_data = json.loads(result)
            return result_data
        
        return {"appname": "unknown", "title": "unknown"}

    def get_current_window_x11(self) -> dict:
        from . import xlib
        window = xlib.get_current_window()

        if window is None:
            cls = "unknown"
            name = "unknown"
        else:
            cls = xlib.get_window_class(window)
            name = xlib.get_window_name(window)

        return {"appname": cls, "title": name}


if sys.platform.startswith("linux"):
    linux = Linux()


def get_current_window_macos() -> Optional[dict]:
    from . import macos
    info = macos.getInfo()
    app = macos.getApp(info)
    title = macos.getTitle(info)

    return {"title": title, "appname": app}


def get_current_window_windows() -> Optional[dict]:
    from . import windows
    window_handle = windows.get_active_window_handle()
    app = windows.get_app_name(window_handle)
    title = windows.get_window_title(window_handle)

    if app is None:
        app = "unknown"
    if title is None:
        title = "unknown"

    return {"appname": app, "title": title}


def get_current_window() -> Optional[dict]:
    if sys.platform.startswith("linux"):
        return linux.get_current_window()
    elif sys.platform == "darwin":
        return get_current_window_macos()
    elif sys.platform in ["win32", "cygwin"]:
        return get_current_window_windows()
    else:
        raise Exception("Unknown platform: {}".format(sys.platform))
