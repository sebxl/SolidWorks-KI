"""Baukontext: laufendes Dokument, Spezifikation und Ergebnisse der bereits gebauten Features."""

from dataclasses import dataclass, field
from pathlib import Path

from swki.compiler.anker import Vektor
from swki.compiler.fehler import GLEICHUNG_FEHLER, BauFehler
from swki.spec.ausdruck import auswerten, ist_ausdruck, sw_ausdruck
from swki.verbindung import grad, mm


@dataclass
class FeatureErgebnis:
    features: list  # erzeugte IFeature, das erste ist das Hauptfeature
    richtung: Vektor | None = None  # Extrusions-/Bohr-/Achsrichtung im Modell (für senkrechte_kanten)
    punkte: list[Vektor] = field(default_factory=list)  # Bohrungsinstanzen: Punkt auf der Achse (mm)

    @property
    def sw_name(self) -> str:
        return ", ".join(f.Name for f in self.features)


@dataclass
class Kontext:
    app: object
    model: object
    spec: dict
    spec_pfad: Path
    tol_mm: float
    ergebnisse: dict[str, FeatureErgebnis] = field(default_factory=dict)
    achsen: dict[str, tuple] = field(default_factory=dict)  # Referenzachsen je Teil (swki.compiler.handler.muster)

    def wert(self, x) -> float:
        """Zahl oder "=Ausdruck" → mm bzw. Grad."""
        return auswerten(x, self.spec.get("parameter", {}))

    def m(self, x) -> float:
        """Länge aus der Spezifikation (mm) → Meter für die API."""
        return mm(self.wert(x))

    def rad(self, x) -> float:
        return grad(self.wert(x))

    def ergebnis(self, fid: str) -> FeatureErgebnis:
        return self.ergebnisse[fid]

    def verknuepfe(self, masname: str, roh, vorzeichen: int = 1) -> None:
        """Maß per SW-Gleichung an Parameter binden, wenn roh ein Ausdruck ist (z. B. "=L").

        vorzeichen -1: das Maß (immer ein Betrag) entspricht dem negierten Ausdruck, z. B. Lage u = "=-L/2".
        """
        if not ist_ausdruck(roh):
            return
        rechts = sw_ausdruck(roh) if vorzeichen > 0 else f"-({sw_ausdruck(roh)})"
        if self.model.GetEquationMgr.Add2(-1, f'"{masname}" = {rechts}', True) < 0:
            raise BauFehler(GLEICHUNG_FEHLER, f"Gleichung für {masname} = {roh} abgelehnt", schritt="gleichung")
