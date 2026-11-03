"""Fail-closed private Windows clipboard test environment; no interactive desktop access."""
def station(name, create):
    import ctypes
    from ctypes import wintypes as w
    u = ctypes.WinDLL('user32', use_last_error=True)
    u.CreateWindowStationW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p]
    u.CreateWindowStationW.restype = w.HANDLE
    u.OpenWindowStationW.argtypes = [w.LPCWSTR, w.BOOL, w.DWORD]
    u.OpenWindowStationW.restype = w.HANDLE
    u.SetProcessWindowStation.argtypes = [w.HANDLE]; u.SetProcessWindowStation.restype = w.BOOL
    u.CreateDesktopW.argtypes = [w.LPCWSTR, w.LPCWSTR, ctypes.c_void_p, w.DWORD, w.DWORD, ctypes.c_void_p]
    u.CreateDesktopW.restype = w.HANDLE
    u.OpenDesktopW.argtypes = [w.LPCWSTR, w.DWORD, w.BOOL, w.DWORD]; u.OpenDesktopW.restype = w.HANDLE
    u.SetThreadDesktop.argtypes = [w.HANDLE]; u.SetThreadDesktop.restype = w.BOOL
    handle = u.CreateWindowStationW(name, 1, 0xF037F, None) if create else u.OpenWindowStationW(name, False, 0xF037F)
    if not handle or not u.SetProcessWindowStation(handle):
        raise ctypes.WinError(ctypes.get_last_error())
    desktop = u.CreateDesktopW('Default', None, None, 0, 0xF01FF, None) if create else u.OpenDesktopW('Default', 0, False, 0xF01FF)
    if not desktop or not u.SetThreadDesktop(desktop):
        raise ctypes.WinError(ctypes.get_last_error())
    # This child process exits after tests, releasing the station and desktop handles.

