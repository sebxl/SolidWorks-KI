"""Bauprotokoll (protokoll.json): Status und Dauer je Knoten, Phasenzeiten."""

import json
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from swki.compiler.fehler import fehler_dict


@dataclass
class Knoten:
    id: str
    typ: str
    status: str = "offen"  # offen | ok | fehler | uebersprungen
    dauer_s: float = 0.0
    sw_name: str | None = None
    fehler: dict | None = None
    punkte: list | None = None  # Bohrungsinstanzen: Achspunkte (mm), für die Prüfung


@dataclass
class Protokoll:
    auftrag: str
    spec: str
    lauf: int
    sw_jahr: int
    status: str = "laeuft"  # laeuft | ok | fehler
    gestartet: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    dauer_s: float = 0.0
    phasen: dict[str, float] = field(default_factory=dict)
    knoten: list[Knoten] = field(default_factory=list)
    dateien: dict[str, str] = field(default_factory=dict)
    fehler: dict | None = None
    sha256: dict[str, str] = field(default_factory=dict)  # gespeicherte Dateien (relativ zum Lauf-Ordner) → SHA-256
    verworfen: dict | None = None  # Befund der Änderungserkennung, den swki bauen --verwerfen übergangen hat
    teile: dict[str, dict] = field(default_factory=dict)  # Baugruppe: Teil-Spec → Protokoll des Teil-Baus
    komponenten: list[dict] = field(default_factory=list)  # Baugruppe: [{"id", "sw_name", "datei"}]
    normteile: dict[str, dict] = field(default_factory=dict)  # Baugruppe: Schlüssel → {"bibliothek", "gebaut", "pruefsumme"}

    @contextmanager
    def phase(self, name: str):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            self.phasen[name] = round(self.phasen.get(name, 0.0) + time.perf_counter() - t0, 3)

    @contextmanager
    def knoten_lauf(self, kid: str, typ: str):
        """Misst einen Knoten; Ausnahmen werden als Fehler vermerkt und weitergereicht."""
        k = Knoten(kid, typ)
        self.knoten.append(k)
        t0 = time.perf_counter()
        try:
            yield k
            k.status = "ok"
        except Exception as e:
            k.status = "fehler"
            k.fehler = fehler_dict(e)
            raise
        finally:
            k.dauer_s = round(time.perf_counter() - t0, 3)

    def uebersprungen(self, kid: str, typ: str) -> None:
        self.knoten.append(Knoten(kid, typ, status="uebersprungen"))

    def als_dict(self) -> dict:
        return asdict(self)

    def schreibe(self, pfad: Path) -> None:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(json.dumps(self.als_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
