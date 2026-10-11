"""STEP-Datei (ISO 10303-21) eines gebauten Teils lesen: exakte Flächen mit Typ, Parametern, Orientierung und Randpunkten.

Grundlage des Merkmalsberichts (swki/pruefung/merkmale.py). `swki bauen` speichert die STEP schon je Lauf
(`<name>.step` im Laufordner, SolidWorks-Standardeinstellungen); hier kommt kein SolidWorks-Aufruf dazu. Reines Python
ohne CAD-Bibliothek: gelesen werden nur die Einträge, die eine B-Rep beschreibt (Körper, Flächen, Kanten, Punkte,
Einheiten). Alle Längen in mm, Winkel in rad, Koordinaten wie im Modell.

Orientierung: In einem geschlossenen Körper zeigt die Flächennormale ins Freie. Bei ADVANCED_FACE mit same_sense .F.
ist sie der Normalen der Trägerfläche entgegengesetzt (Ebene: Achse der Platzierung; Zylinder, Kegel, Torus, Kugel:
von der Achse weg).
"""

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

_TOKEN = re.compile(
    r"\s*(?:(?P<ref>#\d+)|(?P<str>'(?:[^']|'')*')|(?P<enum>\.[A-Z_][A-Z_0-9]*\.)"
    r"|(?P<num>[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)|(?P<kw>[A-Z_][A-Z_0-9]*)|(?P<sym>[(),$*=]))"
)
_PREFIX_MM = {None: 1000.0, "MILLI": 1.0, "CENTI": 10.0, "DECI": 100.0, "MICRO": 1e-3, "KILO": 1e6}
_BOGEN_SCHRITT = math.pi / 12   # Stützpunkte auf Kreisbögen alle 15°


class StepFehler(Exception):
    pass


@dataclass(frozen=True)
class Ref:
    nr: int


@dataclass(frozen=True)
class Typisiert:
    """Typisierter Wert wie LENGTH_MEASURE(1.0E-05)."""
    name: str
    args: tuple


@dataclass
class Flaeche:
    nr: int
    typ: str                    # ebene | zylinder | kegel | torus | kugel | sonstige:<STEP-Name>
    ursprung: np.ndarray        # Platzierung der Trägerfläche (mm)
    achse: np.ndarray           # Ebene: Normale der Trägerfläche; sonst Rotationsachse
    gleichsinnig: bool          # same_sense der ADVANCED_FACE
    koerper: int
    radius: float | None = None     # Zylinder, Kegel (an der Platzierung), Kugel; Torus: großer Radius
    radius2: float | None = None    # Torus: kleiner Radius
    halbwinkel: float | None = None  # Kegel (rad)
    punkte: np.ndarray = field(default_factory=lambda: np.zeros((0, 3)))  # Randpunkte (Ecken + Bogenstützpunkte)
    kanten: frozenset = frozenset()

    @property
    def normale(self) -> np.ndarray:
        """Nur Ebene: Normale ins Freie."""
        return self.achse if self.gleichsinnig else -self.achse


@dataclass
class Modell:
    flaechen: list[Flaeche]
    koerper: int
    einheit_mm: float


# --- Datei lesen --------------------------------------------------------------------------------------------------


def _anweisungen(text: str):
    """Einzelne Anweisungen des DATA-Abschnitts (Semikolon außerhalb von Zeichenketten)."""
    beginn = text.find("DATA;")
    if beginn < 0:
        raise StepFehler("kein DATA-Abschnitt")
    i, n, start, in_str = beginn + 5, len(text), beginn + 5, False
    while i < n:
        c = text[i]
        if c == "'":
            in_str = not in_str
        elif c == ";" and not in_str:
            teil = text[start:i].strip()
            if teil.startswith("ENDSEC"):
                return
            if teil:
                yield teil
            start = i + 1
        i += 1


def _tokens(anweisung: str) -> list[tuple[str, str]]:
    erg, pos = [], 0
    while pos < len(anweisung):
        m = _TOKEN.match(anweisung, pos)
        if not m or m.end() == pos:
            if anweisung[pos:].strip() == "":
                break
            raise StepFehler(f"nicht lesbar: {anweisung[pos:pos + 40]!r}")
        art = m.lastgroup
        erg.append((art, m.group(art)))
        pos = m.end()
    return erg


class _Leser:
    def __init__(self, tokens):
        self.t, self.i = tokens, 0

    def naechstes(self):
        tok = self.t[self.i]
        self.i += 1
        return tok

    def sieht(self, wert) -> bool:
        return self.i < len(self.t) and self.t[self.i][1] == wert

    def liste(self) -> tuple:
        art, wert = self.naechstes()
        if wert != "(":
            raise StepFehler("( erwartet")
        werte = []
        while not self.sieht(")"):
            werte.append(self.wert())
            if self.sieht(","):
                self.i += 1
        self.i += 1
        return tuple(werte)

    def wert(self):
        art, wert = self.t[self.i]
        if wert == "(":
            return self.liste()
        self.i += 1
        if art == "ref":
            return Ref(int(wert[1:]))
        if art == "num":
            return float(wert)
        if art == "str":
            return wert[1:-1].replace("''", "'")
        if art == "enum":
            return wert[1:-1]
        if art == "kw":
            return Typisiert(wert, self.liste())
        return None  # $ und *


def lies_eintraege(text: str) -> dict[int, tuple[str, object]]:
    """#nr → (NAME, args) für einfache Einträge, ("", {NAME: args}) für zusammengesetzte."""
    eintraege = {}
    for anweisung in _anweisungen(text):
        if not anweisung.startswith("#"):
            continue
        tokens = _tokens(anweisung)
        nr, leser = int(tokens[0][1][1:]), _Leser(tokens[2:])   # #nr =
        if leser.sieht("("):
            leser.i += 1
            teile = {}
            while not leser.sieht(")"):
                _, name = leser.naechstes()
                teile[name] = leser.liste()
            eintraege[nr] = ("", teile)
        else:
            _, name = leser.naechstes()
            eintraege[nr] = (name, leser.liste())
    return eintraege


# --- Geometrie ----------------------------------------------------------------------------------------------------


class _Geometrie:
    def __init__(self, eintraege: dict):
        self.e = eintraege
        self.mm = self._laengeneinheit()
        self.rad = self._winkeleinheit()

    def name(self, ref: Ref) -> str:
        return self.e[ref.nr][0]

    def args(self, ref: Ref):
        return self.e[ref.nr][1]

    def _einheit(self, art: str):
        for name, args in self.e.values():
            if name == "" and art in args:
                return args
        return None

    def _laengeneinheit(self) -> float:
        teile = self._einheit("LENGTH_UNIT")
        if teile is None:
            return 1.0
        if "SI_UNIT" in teile:
            return _PREFIX_MM.get(teile["SI_UNIT"][0], 1.0)
        if "CONVERSION_BASED_UNIT" in teile and str(teile["CONVERSION_BASED_UNIT"][0]).upper().startswith("INCH"):
            return 25.4
        return 1.0

    def _winkeleinheit(self) -> float:
        teile = self._einheit("PLANE_ANGLE_UNIT")
        if teile and "CONVERSION_BASED_UNIT" in teile and "DEG" in str(teile["CONVERSION_BASED_UNIT"][0]).upper():
            return math.pi / 180
        return 1.0

    def punkt(self, ref: Ref) -> np.ndarray:
        name, args = self.e[ref.nr]
        if name == "VERTEX_POINT":
            return self.punkt(args[1])
        return np.array(args[1], dtype=float) * self.mm

    def richtung(self, ref, standard=(0.0, 0.0, 1.0)) -> np.ndarray:
        v = np.array(standard if ref is None else self.args(ref)[1], dtype=float)
        return v / np.linalg.norm(v)

    def platzierung(self, ref: Ref) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Ursprung, Achse (z) und Bezugsrichtung (x, senkrecht zu z) eines AXIS2_PLACEMENT_3D."""
        args = self.args(ref)
        o, z = self.punkt(args[1]), self.richtung(args[2])
        x = self.richtung(args[3], (1.0, 0.0, 0.0) if abs(z[0]) < 0.9 else (0.0, 1.0, 0.0))
        x = x - z * float(x @ z)
        return o, z, x / np.linalg.norm(x)

    def kurvenpunkte(self, kurve: Ref, p1: np.ndarray, p2: np.ndarray, gleichsinnig: bool) -> list[np.ndarray]:
        """Stützpunkte einer Kante von p1 nach p2 (Kreis und Ellipse als Bogen, sonst Endpunkte bzw. Kontrollpunkte)."""
        name, args = self.e[kurve.nr]
        if name in ("SURFACE_CURVE", "SEAM_CURVE", "INTERSECTION_CURVE"):
            return self.kurvenpunkte(args[1], p1, p2, gleichsinnig)
        if name in ("CIRCLE", "ELLIPSE"):
            o, z, x = self.platzierung(args[1])
            y = np.cross(z, x)
            a = args[2] * self.mm
            b = (args[3] if name == "ELLIPSE" else args[2]) * self.mm

            def winkel(p):
                d = p - o
                return math.atan2(float(d @ y) / b, float(d @ x) / a)

            t1, t2 = (winkel(p1), winkel(p2)) if gleichsinnig else (winkel(p2), winkel(p1))
            sweep = (t2 - t1) % (2 * math.pi)
            if sweep < 1e-9:
                sweep = 2 * math.pi
            n = max(2, math.ceil(sweep / _BOGEN_SCHRITT))
            return [o + x * a * math.cos(t1 + sweep * k / n) + y * b * math.sin(t1 + sweep * k / n)
                    for k in range(n + 1)]
        if name.startswith("B_SPLINE_CURVE") or (name == "" and "B_SPLINE_CURVE" in args):
            pts = args[2] if name else args["B_SPLINE_CURVE"][1]
            return [p1, p2] + [self.punkt(r) for r in pts]
        return [p1, p2]

    def flaeche(self, nr: int, koerper: int) -> Flaeche:
        _, args = self.e[nr]
        grenzen, traeger, gleichsinnig = args[1], args[2], args[3] == "T"
        name, targs = self.e[traeger.nr]
        o, z, _ = self.platzierung(targs[1]) if name in (
            "PLANE", "CYLINDRICAL_SURFACE", "CONICAL_SURFACE", "TOROIDAL_SURFACE", "SPHERICAL_SURFACE") \
            else (np.zeros(3), np.array([0.0, 0.0, 1.0]), None)
        f = Flaeche(nr, "sonstige:" + (name or "zusammengesetzt"), o, z, gleichsinnig, koerper)
        if name == "PLANE":
            f.typ = "ebene"
        elif name == "CYLINDRICAL_SURFACE":
            f.typ, f.radius = "zylinder", targs[2] * self.mm
        elif name == "CONICAL_SURFACE":
            f.typ, f.radius, f.halbwinkel = "kegel", targs[2] * self.mm, targs[3] * self.rad
        elif name == "TOROIDAL_SURFACE":
            f.typ, f.radius, f.radius2 = "torus", targs[2] * self.mm, targs[3] * self.mm
        elif name == "SPHERICAL_SURFACE":
            f.typ, f.radius = "kugel", targs[2] * self.mm
        punkte, kanten = [], set()
        for grenze in grenzen:
            schleife = self.args(grenze)[1]
            if self.name(schleife) == "VERTEX_LOOP":
                punkte.append(self.punkt(self.args(schleife)[1]))
                continue
            for oe in self.args(schleife)[1]:
                kante = self.args(oe)[3]
                kanten.add(kante.nr)
                _, kargs = self.e[kante.nr]
                p1, p2 = self.punkt(kargs[1]), self.punkt(kargs[2])
                punkte += self.kurvenpunkte(kargs[3], p1, p2, kargs[4] == "T")
        if punkte:
            f.punkte = np.array(punkte)
        f.kanten = frozenset(kanten)
        return f


def _koerper(e: dict) -> list[list[int]]:
    """Flächen je Volumenkörper (MANIFOLD_SOLID_BREP, BREP_WITH_VOIDS)."""
    koerper = []
    for name, args in e.values():
        if name in ("MANIFOLD_SOLID_BREP", "BREP_WITH_VOIDS"):
            schalen = [args[1]] + (list(args[2]) if name == "BREP_WITH_VOIDS" else [])
            koerper.append([f.nr for s in schalen for f in e[s.nr][1][1]])
    return koerper


def lies_modell(text: str) -> Modell:
    e = lies_eintraege(text)
    g = _Geometrie(e)
    koerper = _koerper(e)
    if not koerper:   # Flächenmodell ohne Körper: alle Flächen als ein Körper
        koerper = [[nr for nr, (name, _) in e.items() if name == "ADVANCED_FACE"]]
    flaechen = [g.flaeche(nr, k) for k, nrn in enumerate(koerper) for nr in nrn if e[nr][0] == "ADVANCED_FACE"]
    return Modell(flaechen, len(koerper), g.mm)


def lies_step(pfad: Path) -> Modell:
    return lies_modell(Path(pfad).read_text(encoding="utf-8", errors="replace"))
