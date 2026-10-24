"""Baukontext: laufendes Dokument, Spezifikation und Ergebnisse der bereits gebauten Features."""

from dataclasses import dataclass, field
from pathlib import Path

from swki.compiler.anker import Vektor
from swki.compiler.fehler import GLEICHUNG_FEHLER, BauFehler
from swki.spec.ausdruck import auswerten, ist_ausdruck, sw_ausdruck
from swki.verbindung import grad, mm


def einheit_der_art(art: str) -> str:
    """Einheit eines Maßes im Maßprotokoll: Winkel in Grad, alles andere in mm."""
    return "grad" if art == "winkel" else "mm"


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
    gleichungen: bool = False  # Maße per Gleichung an Parameter binden (gleichungen_an)
    knoten: str | None = None  # Feature-ID des Knotens, der gerade gebaut wird (setzt baue_features vor jedem Handler)
    masse: dict[str, list[dict]] = field(default_factory=dict)  # Maßprotokoll je Feature-ID, baue_features holt es ab

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

    def pfad(self, fid: str) -> str:
        """Spec-Pfad eines Features: Position im Feature-Baum, z. B. "features[1]"."""
        for index, f in enumerate(self.spec["features"]):
            if f["id"] == fid:
                return f"features[{index}]"
        raise KeyError(f"Feature {fid!r} steht nicht in der Spezifikation")

    def mass(self, masname: str, roh, pfad: str, art: str, vorzeichen: int = 1, bezug=None,
             wert: float | None = None, einheit: str | None = None) -> None:
        """Maß ins Maßprotokoll des laufenden Knotens eintragen (Knoten.masse im Bauprotokoll).

        pfad: Spec-Pfad des Werts (z. B. "features[1].ende.tiefe"), art: lage | paarabstand | groesse | radius |
        winkel | tiefe | abstand | versatz | konstruktion | skript, roh: Wert der Spezifikation (Zahl oder "=Ausdruck"),
        vorzeichen -1: das Maß (immer ein Betrag) entspricht dem negierten Wert, z. B. Lage u = "=-L/2". bezug:
        Spec-Wert des Bezugs ("-rand", {"flaeche": …} …) oder None. wert: Betrag des Maßes in mm bzw. Grad, wenn er
        nicht |roh| ist (Lage zum Rand, Abstand eines Paars, Rechteckseite statt Mitte) – roh ist dann nur die
        Spec-Koordinate. einheit: "grad" | "mm", Vorgabe aus art (winkel: Grad); ausdrücklich, wenn art die Einheit
        nicht mehr zeigt (Skriptmaß eines Winkels).

        Nur mit ctx.gleichungen und bei einem Ausdruck bindet die Methode das Maß per SW-Gleichung an den Parameter (Spec §4:
        auch Lage zum Ursprung und Abstand eines mitte-Paars); bei einem Rand- oder Flächenbezug oder einem eigenen wert nie
        (der Wert hängt dann an der Geometrie, nicht allein am Ausdruck).
        """
        self.masse.setdefault(self.knoten or "", []).append({
            "name": masname, "pfad": pfad, "art": art, "bezug": bezug, "roh": roh, "vorzeichen": vorzeichen,
            "wert": abs(self.wert(roh)) if wert is None else wert,
            "einheit": einheit or einheit_der_art(art),
        })
        zur_geometrie = isinstance(bezug, dict) or bezug in ("-rand", "+rand")
        if not self.gleichungen or not ist_ausdruck(roh) or zur_geometrie or wert is not None:
            return
        rechts = sw_ausdruck(roh) if vorzeichen > 0 else f"-({sw_ausdruck(roh)})"
        if self.model.GetEquationMgr.Add2(-1, f'"{masname}" = {rechts}', True) < 0:
            raise BauFehler(GLEICHUNG_FEHLER, f"Gleichung für {masname} = {roh} abgelehnt", schritt="gleichung")
