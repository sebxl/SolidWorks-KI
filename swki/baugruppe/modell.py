"""Datenmodell einer geladenen Baugruppe (Spec 3b §4): Quellen der Komponenten und Dateinamen im Lauf."""

from dataclasses import dataclass, field
from pathlib import Path

from swki.auftrag import dateiname


@dataclass
class Quelle:
    art: str                       # "teil" | "normteil"
    spec: dict                     # Teil-Spezifikation bzw. aus der Bauvorlage erzeugte Normteil-Spezifikation
    datei: str | None = None       # teil: Dateiname der Teil-Spec im Auftragsordner
    norm: str | None = None        # normteil: Norm wie in der Tabelle, z. B. "ISO 4762"
    groesse: str | None = None     # normteil: Tabellenschlüssel, z. B. "M8" oder "8"
    laenge: float | None = None    # normteil: mm; None bei Teilen ohne Länge
    variante: str | None = None
    schluessel: str | None = None  # normteil: Bibliotheksschlüssel, z. B. "ISO4762_M8x30_8_8"
    masse: dict = field(default_factory=dict)  # normteil: Normmaße der Größe

    @property
    def referenzen(self) -> set[str]:
        """IDs der referenz-Features (bei Normteilen die Einbaureferenzen EINBAU_*)."""
        return {f["id"] for f in self.spec["features"] if f["typ"] == "referenz"}

    @property
    def schluessel_dokument(self) -> str:
        """Schlüssel des Quelldokuments: Dateiname der Teil-Spec bzw. Bibliotheksschlüssel."""
        return self.datei if self.art == "teil" else self.schluessel

    @property
    def hole_groesse(self) -> str:
        """Größe für swki normteil hole: "M8x30", "M8", "8x30"."""
        return self.groesse if self.laenge is None else f"{self.groesse}x{self.laenge:g}"


@dataclass
class Baugruppe:
    pfad: Path                     # Baugruppen-Spezifikation
    spec: dict
    quellen: dict[str, Quelle]     # Komponenten-ID → Quelle
    teile: dict[str, dict]         # Dateiname → Teil-Spezifikation, in Reihenfolge der ersten Verwendung

    def komponente_von(self, datei: str) -> str:
        """Erste Komponente mit der Teil-Spec `datei` (Präfix der Teilprüfung, Knoten bei TEIL_BAU)."""
        return next(k for k, q in self.quellen.items() if q.datei == datei)


def dokument_name(q: Quelle, auftrag: str, standard: dict) -> str:
    """Dateiname im Lauf-Ordner: <auftrag>_<name>.sldprt (Eigenteil) bzw. <schluessel>.sldprt (Normteil-Kopie)."""
    return f"{dateiname(q.spec, auftrag, standard)}.sldprt" if q.art == "teil" else f"{q.schluessel}.sldprt"
