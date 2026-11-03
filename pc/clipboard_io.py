"""Use native Unicode clipboard on Windows, bypassing Tk's same-owner chunk bug."""
import sys
from decoder import MAX_TEXT_CHARS


_owner_window = None


class ClipboardError(RuntimeError):
    pass


def _api():
    import ctypes
    from ctypes import wintypes as w
    user = ctypes.WinDLL('user32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    user.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, ctypes.c_void_p]
    user.CreateWindowExW.restype = w.HWND
    user.IsWindow.argtypes = [w.HWND]; user.IsWindow.restype = w.BOOL
    user.OpenClipboard.argtypes = [w.HWND]; user.OpenClipboard.restype = w.BOOL
    user.CloseClipboard.argtypes = []; user.CloseClipboard.restype = w.BOOL
    user.EmptyClipboard.argtypes = []; user.EmptyClipboard.restype = w.BOOL
    user.GetClipboardData.argtypes = [w.UINT]; user.GetClipboardData.restype = w.HANDLE
    user.SetClipboardData.argtypes = [w.UINT, w.HANDLE]; user.SetClipboardData.restype = w.HANDLE
    kernel.GlobalAlloc.argtypes = [w.UINT, ctypes.c_size_t]; kernel.GlobalAlloc.restype = w.HGLOBAL
    kernel.GlobalLock.argtypes = [w.HGLOBAL]; kernel.GlobalLock.restype = ctypes.c_void_p
    kernel.GlobalUnlock.argtypes = [w.HGLOBAL]; kernel.GlobalUnlock.restype = w.BOOL
    kernel.GlobalSize.argtypes = [w.HGLOBAL]; kernel.GlobalSize.restype = ctypes.c_size_t
    kernel.GlobalFree.argtypes = [w.HGLOBAL]; kernel.GlobalFree.restype = w.HGLOBAL
    return ctypes, user, kernel


def read_text(widget):
    if sys.platform != 'win32':
        return widget.clipboard_get()
    ctypes, user, kernel = _api()
    if not user.OpenClipboard(widget.winfo_id()):
        raise ClipboardError('다른 프로그램이 클립보드를 사용 중입니다. 잠시 후 다시 붙여넣어 주세요.')
    try:
        handle = user.GetClipboardData(13)  # CF_UNICODETEXT
        if not handle:
            raise ClipboardError('클립보드에 Unicode 텍스트가 없습니다.')
        size = kernel.GlobalSize(handle)
        if not 2 <= size <= (MAX_TEXT_CHARS + 1) * 4 or size % 2:
            raise ClipboardError('클립보드 본문이 너무 크거나 올바른 형식이 아닙니다.')
        pointer = kernel.GlobalLock(handle)
        if not pointer:
            raise ClipboardError('클립보드 본문을 읽을 수 없습니다.')
        try:
            # Bound the memory read even if a foreign clipboard has no terminator.
            text = ctypes.wstring_at(pointer, size // 2)
            end = text.find('\0')
            if end < 0:
                raise ClipboardError('클립보드 텍스트의 끝을 확인할 수 없습니다.')
            text = text[:end]
            if len(text) > MAX_TEXT_CHARS:
                raise ClipboardError('클립보드 본문은 2,097,152자 이하여야 합니다.')
            return text
        finally:
            kernel.GlobalUnlock(handle)
    finally:
        user.CloseClipboard()


def write_text(widget, text):
    if len(text) > MAX_TEXT_CHARS or '\0' in text:
        raise ClipboardError('복사할 텍스트 크기 또는 형식이 올바르지 않습니다.')
    if sys.platform != 'win32':
        widget.clipboard_clear()
        widget.clipboard_append(text)
        widget.update_idletasks()
        return
    ctypes, user, kernel = _api()
    try:
        data = (text + '\0').encode('utf-16-le')
    except UnicodeError as exc:
        raise ClipboardError('복사할 Unicode 텍스트가 올바르지 않습니다.') from exc
    handle = kernel.GlobalAlloc(0x0002, len(data))  # GMEM_MOVEABLE
    if not handle:
        raise ClipboardError('클립보드 메모리를 준비할 수 없습니다.')
    try:
        pointer = kernel.GlobalLock(handle)
        if not pointer:
            raise ClipboardError('클립보드 메모리에 접근할 수 없습니다.')
        try:
            ctypes.memmove(pointer, data, len(data))
        finally:
            kernel.GlobalUnlock(handle)
        global _owner_window
        # A native message-only window owns eagerly materialized data. A Tk owner
        # can overwrite it with Tk's stale cache during WM_RENDERALLFORMATS at exit.
        if not _owner_window or not user.IsWindow(_owner_window):
            _owner_window = user.CreateWindowExW(0, 'STATIC', 'TextTransferClipboard',
                                                0, 0, 0, 0, 0, -3, None, None, None)
        if not _owner_window:
            raise ClipboardError('Windows 클립보드 창을 준비할 수 없습니다.')
        if not user.OpenClipboard(_owner_window):
            raise ClipboardError('다른 프로그램이 클립보드를 사용 중입니다. 잠시 후 다시 복사해주세요.')
        try:
            if not user.EmptyClipboard() or not user.SetClipboardData(13, handle):
                raise ClipboardError('Windows 클립보드에 기록하지 못했습니다.')
            handle = None  # Windows now owns the memory.
        finally:
            user.CloseClipboard()
    finally:
        if handle:
            kernel.GlobalFree(handle)
