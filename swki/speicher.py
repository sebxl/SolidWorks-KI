"""Private Bytes eines Prozesses (Windows, ctypes): SolidWorks-Speicher für die Speichergrenze der Bewegungsprüfung
(Spec 4a §8.4) und die Speicherspitze beim Import eines Kaufteils (Spec 3c §5.1). Gemessen wird PrivateUsage aus
PROCESS_MEMORY_COUNTERS_EX, nicht das Working Set."""

import ctypes
import threading
from ctypes import wintypes

_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class _Speicher(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t), ("PrivateUsage", ctypes.c_size_t)]


def privat_mb(pid: int) -> float:
    """Private Bytes des Prozesses pid in MB."""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    k32.K32GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(_Speicher), wintypes.DWORD)
    k32.K32GetProcessMemoryInfo.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    h = k32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        z = _Speicher()
        z.cb = ctypes.sizeof(z)
        if not k32.K32GetProcessMemoryInfo(h, ctypes.byref(z), z.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return round(z.PrivateUsage / 2 ** 20, 1)
    finally:
        k32.CloseHandle(h)


class Spitzenmessung:
    """Kontext: Private Bytes vor, höchstens alle `takt_s` Sekunden während und nach dem Block (MB); danach stehen
    .vorher, .spitze und .nachher fest. `messen` ist austauschbar (Tests)."""

    def __init__(self, pid: int, takt_s: float = 0.5, messen=privat_mb):
        self.pid, self.takt_s, self.messen = pid, takt_s, messen
        self.vorher = self.spitze = self.nachher = 0.0
        self._halt = threading.Event()
        self._faden: threading.Thread | None = None

    def _laufe(self) -> None:
        while not self._halt.wait(self.takt_s):
            self.spitze = max(self.spitze, self.messen(self.pid))

    def __enter__(self):
        self.vorher = self.spitze = self.messen(self.pid)
        self._faden = threading.Thread(target=self._laufe, daemon=True)
        self._faden.start()
        return self

    def __exit__(self, *_):
        self._halt.set()
        self._faden.join()
        self.nachher = self.messen(self.pid)
        self.spitze = max(self.spitze, self.nachher)
        return False

    def als_dict(self) -> dict:
        return {"vorher": self.vorher, "spitze": self.spitze, "nachher": self.nachher}
