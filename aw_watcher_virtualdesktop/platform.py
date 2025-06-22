import os
import sys
import subprocess
from typing import Optional


if sys.platform.startswith("win"):
    import ctypes
    import winreg
    try:
        import comtypes
        from ctypes import wintypes
        from comtypes import GUID, COMMETHOD, HRESULT

        class IVirtualDesktopManager(comtypes.IUnknown):
            _iid_ = GUID("{A5CD92FF-29BE-454C-8D04-D82879FB3F1B}")
            _methods_ = [
                COMMETHOD([], HRESULT, "IsWindowOnCurrentVirtualDesktop",
                          (["in"], wintypes.HWND, "hwnd"),
                          (["out"], ctypes.POINTER(ctypes.c_bool), "onCurrentDesktop")),
                COMMETHOD([], HRESULT, "GetWindowDesktopId",
                          (["in"], wintypes.HWND, "hwnd"),
                          (["out"], ctypes.POINTER(comtypes.GUID), "desktopId")),
                COMMETHOD([], HRESULT, "MoveWindowToDesktop",
                          (["in"], wintypes.HWND, "hwnd"),
                          (["in"], ctypes.POINTER(comtypes.GUID), "desktopId")),
            ]

        CLSID_VirtualDesktopManager = GUID("{AA509086-5CA9-4C25-8F95-589D3C07B48A}")
    except Exception:  # pragma: no cover - used on non-windows platforms
        comtypes = None  # type: ignore
        IVirtualDesktopManager = object  # type: ignore
        CLSID_VirtualDesktopManager = None

    def _get_virtual_desktop_guid() -> Optional[str]:
        """Return the GUID of the current virtual desktop on Windows. 必ず取得できなければ詳細なエラーを出す"""

        from .windows import get_active_window_handle

        if comtypes is None:
            print("comtypes is None (not installed or import error)")
            return None

        # COM初期化（STA明示、既に初期化済みなら無視）
        # COM初期化は呼び出し側に任せる（ここでは呼ばない）
        # try:
        #     if hasattr(comtypes, 'CoInitializeEx'):
        #         try:
        #             comtypes.CoInitializeEx(0)  # 0 = COINIT_APARTMENTTHREADED
        #         except Exception as e:
        #             if getattr(e, 'hresult', None) != -2147417850:
        #                 print(f"COM initialization failed: {e}")
        #                 return None
        #     else:
        #         try:
        #             comtypes.CoInitialize()
        #         except Exception as e:
        #             if getattr(e, 'hresult', None) != -2147417850:
        #                 print(f"COM initialization failed: {e}")
        #                 return None
        # except Exception as e:
        #     print(f"COM initialization unexpected error: {e}")
        #     return None

        # インターフェース生成
        try:
            manager = comtypes.CoCreateInstance(
                CLSID_VirtualDesktopManager, interface=IVirtualDesktopManager
            )
            print(f"manager: {manager}, type: {type(manager)}")
        except Exception as e:
            print(f"CoCreateInstance failed: {e}")
            return None

        hwnd = get_active_window_handle()
        print(f"get_active_window_handle() returned: {hwnd}, type: {type(hwnd)}")
        if not hwnd or hwnd == 0:
            print(f"get_active_window_handle() failed: hwnd={hwnd}")
            return None
        try:
            hwnd_c = ctypes.wintypes.HWND(hwnd)
            print(f"hwnd_c: {hwnd_c}, type: {type(hwnd_c)}")
        except Exception as e:
            print(f"HWND cast failed: {e}")
            return None

        desktop_id = comtypes.GUID()
        print(f"desktop_id (before): {desktop_id}, type: {type(desktop_id)}")
        try:
            guid_out = manager.GetWindowDesktopId(hwnd_c)
            print(f"GetWindowDesktopId returned: {guid_out}, type: {type(guid_out)}")
            guid_str = str(guid_out)
        except Exception as e:
            print(f"GetWindowDesktopId error: {e}")
            import traceback; traceback.print_exc()
            return None
        if not guid_str or guid_str == "00000000-0000-0000-0000-000000000000":
            print(f"GetWindowDesktopId returned empty or default GUID: {guid_str}")
            return None
        return guid_str

    def _lookup_desktop_name(desktop_guid: str) -> Optional[str]:
        """Look up the configured name for a virtual desktop GUID."""
        path = rf"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\VirtualDesktops\Desktops\{desktop_guid.upper()}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                name, _ = winreg.QueryValueEx(key, "Name")
                return name
        except Exception:
            return None

    def get_virtual_desktop() -> Optional[str]:
        guid = _get_virtual_desktop_guid()
        if guid is None:
            return None
        name = _lookup_desktop_name(guid)
        if name is not None:
            return name
        return guid

elif sys.platform == "darwin":
    def get_virtual_desktop() -> Optional[int]:
        # macOS support removed
        return None


else:
    def _get_current_desktop_x11() -> Optional[int]:
        try:
            from Xlib import X, display as xdisplay
        except Exception:
            return None
        disp = xdisplay.Display()
        root = disp.screen().root
        NET_CURRENT_DESKTOP = disp.intern_atom("_NET_CURRENT_DESKTOP")
        prop = root.get_full_property(NET_CURRENT_DESKTOP, X.AnyPropertyType)
        if prop:
            return int(prop.value[0])
        return None

    def _get_current_desktop_gnome() -> Optional[int]:
        try:
            out = subprocess.check_output([
                "gdbus",
                "call",
                "--session",
                "--dest",
                "org.gnome.Shell",
                "--object-path",
                "/org/gnome/Shell",
                "--method",
                "org.gnome.Shell.Eval",
                "global.workspace_manager.get_active_workspace_index()",
            ], text=True)
            val = out.split()[0].strip("(),")
            return int(val)
        except Exception:
            return None

    def _get_current_desktop_kde() -> Optional[int]:
        try:
            out = subprocess.check_output([
                "qdbus",
                "org.kde.KWin",
                "/KWin",
                "currentDesktop",
            ], text=True)
            return int(out.strip())
        except Exception:
            return None

    def get_virtual_desktop() -> Optional[int]:
        """Return the current workspace index on Linux desktops."""
        if os.environ.get("XDG_SESSION_TYPE") == "x11":
            return _get_current_desktop_x11()
        session = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if session.startswith("gnome"):
            return _get_current_desktop_gnome()
        if session.startswith("kde"):
            return _get_current_desktop_kde()
        # fallback to x11 property
        return _get_current_desktop_x11()

__all__ = ["get_virtual_desktop"]
