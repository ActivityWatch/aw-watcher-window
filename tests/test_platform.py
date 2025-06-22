import importlib
import sys
import ctypes
import pytest

import aw_watcher_virtualdesktop.platform as platform_mod


def reload_for_platform(monkeypatch, plat, mods=None):
    monkeypatch.setattr(sys, 'platform', plat, raising=False)
    if mods:
        for name, mod in mods.items():
            monkeypatch.setitem(sys.modules, name, mod)
    importlib.reload(platform_mod)


@pytest.mark.skipif(getattr(ctypes, 'WINFUNCTYPE', None) is None, reason='non-windows')
def test_get_virtual_desktop_windows(monkeypatch):
    # FakeGUIDクラスの実装
    class FakeGUID(ctypes.Structure):
        _fields_ = [("value", ctypes.c_char_p)]

        def __init__(self, *args, **kwargs):
            super().__init__()
            self.value = b'abc'

        def __str__(self):
            return 'abc'

    # FakeMgrクラスの実装
    class FakeMgr:
        def GetWindowDesktopId(self, hwnd):
            return FakeGUID()

    # モジュールのモック設定
    fake_mod = type('FakeComtypes', (), {
        'GUID': FakeGUID,
        'CoInitialize': lambda: None,
        'CoCreateInstance': lambda clsid, interface=None: FakeMgr(),
        'IUnknown': object,
        'COMMETHOD': lambda *a, **k: None,
        'HRESULT': int
    })

    # モックを適用
    reload_for_platform(monkeypatch, 'win32', {'comtypes': fake_mod})
    monkeypatch.setattr(platform_mod, 'IVirtualDesktopManager', FakeMgr, raising=False)
    monkeypatch.setattr(platform_mod, 'CLSID_VirtualDesktopManager', FakeGUID, raising=False)
    monkeypatch.setitem(sys.modules, 'aw_watcher_virtualdesktop.windows', 
                       type('M', (), {'get_active_window_handle': lambda: 1}))
    
    # テスト実行
    monkeypatch.setattr(platform_mod, '_lookup_desktop_name', lambda g: 'DeskName', raising=False)
    result = platform_mod.get_virtual_desktop()
    assert result == 'DeskName'


@pytest.mark.skipif(getattr(ctypes, 'WINFUNCTYPE', None) is None, reason='non-windows')
def test_print_virtual_desktop_info(monkeypatch):
    class FakeGUID(ctypes.Structure):
        _fields_ = [("value", ctypes.c_char_p)]

        def __init__(self, *args, **kwargs):
            super().__init__()
            self.value = b'abc'

        def __str__(self):
            return 'abc'

    class FakeMgr:
        def GetWindowDesktopId(self, hwnd):
            return FakeGUID()

    fake_mod = type('FakeComtypes', (), {
        'GUID': FakeGUID,
        'CoInitialize': lambda: None,
        'CoCreateInstance': lambda clsid, interface=None: FakeMgr(),
        'IUnknown': object,
        'COMMETHOD': lambda *a, **k: None,
        'HRESULT': int
    })

    reload_for_platform(monkeypatch, 'win32', {'comtypes': fake_mod})
    monkeypatch.setattr(platform_mod, 'IVirtualDesktopManager', FakeMgr, raising=False)
    monkeypatch.setattr(platform_mod, 'CLSID_VirtualDesktopManager', FakeGUID, raising=False)
    monkeypatch.setitem(sys.modules, 'aw_watcher_virtualdesktop.windows',
                       type('M', (), {'get_active_window_handle': lambda: 1}))
    monkeypatch.setattr(platform_mod, '_lookup_desktop_name', lambda g: 'DeskName', raising=False)

    name = platform_mod.get_virtual_desktop()
    guid = platform_mod._get_virtual_desktop_guid()
    print(f"Desktop Name: {name}")
    print(f"GUID: {guid}")
    # capsysによるキャプチャを削除
    assert name == 'DeskName'
    assert str(guid) == 'abc'


@pytest.mark.skipif(getattr(ctypes, 'WINFUNCTYPE', None) is None, reason='non-windows')
def test_get_virtual_desktop_windows_bad_comtypes(monkeypatch):
    class FakeGUID(ctypes.Structure):
        _fields_ = [("value", ctypes.c_char_p)]

    class FakeMgr:
        def GetWindowDesktopId(self, hwnd):
            return 0

    fake_mod = type('FakeComtypes', (), {
        'GUID': FakeGUID,
        'CoInitialize': lambda: None,
        'CoCreateInstance': lambda clsid, interface=None: FakeMgr(),
        'IUnknown': object,
        'COMMETHOD': lambda *a, **k: None,
        'HRESULT': int
    })

    reload_for_platform(monkeypatch, 'win32', {'comtypes': fake_mod})
    monkeypatch.setattr(platform_mod, 'IVirtualDesktopManager', FakeMgr, raising=False)
    monkeypatch.setattr(platform_mod, 'CLSID_VirtualDesktopManager', FakeGUID, raising=False)
    monkeypatch.setitem(sys.modules, 'aw_watcher_virtualdesktop.windows',
                       type('M', (), {'get_active_window_handle': lambda: 1}))

    assert platform_mod.get_virtual_desktop() is None


def test_get_virtual_desktop_x11(monkeypatch):
    reload_for_platform(monkeypatch, 'linux')
    monkeypatch.setenv('XDG_SESSION_TYPE', 'x11')
    monkeypatch.setattr(platform_mod, '_get_current_desktop_x11', lambda: 1, raising=False)
    assert platform_mod.get_virtual_desktop() == 1


def test_get_virtual_desktop_gnome(monkeypatch):
    reload_for_platform(monkeypatch, 'linux')
    monkeypatch.setenv('XDG_SESSION_TYPE', 'wayland')
    monkeypatch.setenv('XDG_CURRENT_DESKTOP', 'GNOME')
    monkeypatch.setattr(platform_mod, '_get_current_desktop_gnome', lambda: 3, raising=False)
    assert platform_mod.get_virtual_desktop() == 3


def test_print_real_virtual_desktop_info():
    import importlib
    import aw_watcher_virtualdesktop.platform as platform_mod
    importlib.reload(platform_mod)  # ここでリロード

    name = platform_mod.get_virtual_desktop()
    guid = None
    if hasattr(platform_mod, "_get_virtual_desktop_guid"):
        guid = platform_mod._get_virtual_desktop_guid()

    print(f"Real Desktop Name: {name}")
    print(f"Real GUID: {guid}")

    assert guid is not None, "GUIDが取得できませんでした"
    assert name is not None, "Desktop Nameが取得できませんでした"
