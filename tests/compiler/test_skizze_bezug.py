"""Skizzierer mit Bemaßungsbezug (Task 6): Lagen über bemassung.massplan zu Ursprung, Mitte, Rand und Fläche – ohne
SolidWorks. Die Attrappe zeichnet Beziehungen und Maße mit den gewählten Objekten auf; die Wege folgen Spike S17
(Zeile 1: Punkt + Kante achsparallel, Zeile 3: Rechteckseite + Kante mit AddDimension2, Zeile 4: Mittellinie mit Endpunkt
auf der Randkante bzw. Längenmaß, Zeile 5: Symmetrie + Abstand, Rechteck über Diagonale + sgATMIDDLE)."""

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.compiler import skizze as modul
from swki.compiler.anker import Flaeche, Kante
from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import Kontext
from swki.compiler.skizze import Skizzenebene

# --- Attrappe ----------------------------------------------------------------------------------------------------------


class _Punkt:
    def __init__(self, nr: int, x: float, y: float, name: str = ""):
        self.X, self.Y, self.GetID, self.name = x, y, (1, nr), name

    def __repr__(self):
        return self.name or f"P({self.X * 1000:g}, {self.Y * 1000:g})"


class _Linie:
    GetType = 0

    def __init__(self, nr: int, a: _Punkt, b: _Punkt, konstruktion: bool):
        self.GetStartPoint2, self.GetEndPoint2, self.ConstructionGeometry = a, b, konstruktion
        self.GetID = (2, nr)

    def __repr__(self):
        return f"{'M' if self.ConstructionGeometry else 'L'}({self.GetStartPoint2!r}–{self.GetEndPoint2!r})"


class _Kreis:
    GetType = 1

    def __init__(self, nr: int, mitte: _Punkt):
        self.mitte, self.GetID = mitte, (3, nr)

    def __repr__(self):
        return f"K({self.mitte!r})"


class _Skizze:
    GetConstrainedStatus = modul.sw.SW_FULLY_CONSTRAINED

    def __init__(self):
        self.punkte, self.segmente = [], []

    @property
    def GetSketchPoints2(self):  # noqa: N802 – Name der SolidWorks-API
        return list(self.punkte)

    @property
    def GetSketchSegments(self):  # noqa: N802 – Name der SolidWorks-API
        return list(self.segmente)


class _Manager:
    """Linien teilen Endpunkte an gleicher Stelle (AddToDB, Spike S17: die Diagonale teilt die Rechteckecken); Kreise und
    CreatePoint legen immer eigene Punkte an."""

    def __init__(self, modell):
        self.modell, self.ActiveSketch, self.nr = modell, _Skizze(), 0
        self.linienpunkte: list[_Punkt] = []

    def _neu(self, x, y) -> _Punkt:
        self.nr += 1
        p = _Punkt(self.nr, x, y)
        self.ActiveSketch.punkte.append(p)
        return p

    def _ende(self, x, y) -> _Punkt:
        for p in self.linienpunkte:
            if abs(p.X - x) < 1e-12 and abs(p.Y - y) < 1e-12:
                return p
        p = self._neu(x, y)
        self.linienpunkte.append(p)
        return p

    def _linie(self, xa, ya, xb, yb, konstruktion):
        self.nr += 1
        linie = _Linie(self.nr, self._ende(xa, ya), self._ende(xb, yb), konstruktion)
        self.ActiveSketch.segmente.append(linie)
        self.modell.aufrufe.append(("mittellinie" if konstruktion else "linie", linie))
        return linie

    def CreateLine(self, xa, ya, za, xb, yb, zb):  # noqa: N802
        return self._linie(xa, ya, xb, yb, False)

    def CreateCenterLine(self, xa, ya, za, xb, yb, zb):  # noqa: N802
        return self._linie(xa, ya, xb, yb, True)

    def CreateCircleByRadius(self, x, y, z, r):  # noqa: N802
        self.nr += 1
        kreis = _Kreis(self.nr, self._neu(x, y))
        self.ActiveSketch.segmente.append(kreis)
        return kreis

    def CreatePoint(self, x, y, z):  # noqa: N802
        p = self._neu(x, y)
        self.modell.aufrufe.append(("punkt", p))
        return p

    def CreateFillet(self, radius, art):  # noqa: N802
        self.modell.aufrufe.append(("verrundung", tuple(self.modell.auswahl)))
        self.modell.anzeigen.append(_Anzeige(f"R{len(self.modell.anzeigen) + 1}"))
        return object()

    def InsertSketch(self, neu):  # noqa: N802
        pass


class _Anzeige:
    def __init__(self, name):
        self.name = name

    def GetDimension2(self, i):  # noqa: N802
        return SimpleNamespace(Name=self.name)


class _Feature:
    def __init__(self, anzeigen=()):
        self.Name, self.anzeigen = "", anzeigen

    def Select2(self, anhaengen, marke):  # noqa: N802
        return True

    @property
    def GetFirstDisplayDimension(self):  # noqa: N802
        return self.anzeigen[0] if self.anzeigen else None

    def GetNextDisplayDimension(self, dd):  # noqa: N802
        i = self.anzeigen.index(dd) + 1
        return self.anzeigen[i] if i < len(self.anzeigen) else None


class _Gleichungen:
    def __init__(self):
        self.texte = []

    def Add2(self, index, text, loesen):  # noqa: N802
        self.texte.append(text)
        return 0


class _Modell:
    def __init__(self):
        self.auswahl, self.aufrufe, self.nr, self.anzeigen = [], [], 0, []
        self.SketchManager = _Manager(self)
        self.feature = _Feature(self.anzeigen)
        self.GetEquationMgr = _Gleichungen()

    def SketchAddConstraints(self, art):  # noqa: N802
        self.aufrufe.append(("beziehung", art, tuple(self.auswahl)))

    def _mass(self, art):
        self.nr += 1
        self.aufrufe.append((art, tuple(self.auswahl), f"D{self.nr}"))
        self.anzeigen.append(_Anzeige(f"D{self.nr}"))
        return self.anzeigen[-1]

    def AddHorizontalDimension2(self, x, y, z):  # noqa: N802
        return self._mass("horizontal")

    def AddVerticalDimension2(self, x, y, z):  # noqa: N802
        return self._mass("vertikal")

    def AddDimension2(self, x, y, z):  # noqa: N802
        return self._mass("frei")

    # Auswertung
    def beziehungen(self, art: str) -> list[tuple]:
        return [a[2] for a in self.aufrufe if a[0] == "beziehung" and a[1] == art]

    def masse(self, *arten: str) -> list[tuple]:
        return [(a[0], a[1]) for a in self.aufrufe if a[0] in arten]

    def mittellinien(self) -> list:
        return [a[1] for a in self.aufrufe if a[0] == "mittellinie"]

    def linien(self) -> list:
        return [a[1] for a in self.aufrufe if a[0] == "linie"]

    def neue_punkte(self) -> list:
        return [a[1] for a in self.aufrufe if a[0] == "punkt"]

    def zaehlprobe(self) -> tuple[int, int]:
        """(Freiheitsgrade, gesetzte Bedingungen) der Skizze: je Punkt 2, je Kreis 1 (Radius); Ursprung und Modellkanten
        stehen fest. Deckung Punkt–Punkt, Mittig und Symmetrie nehmen 2, Deckung Punkt–Kante und alles andere 1."""
        skizze = self.SketchManager.ActiveSketch
        frei = 2 * len(skizze.punkte) + sum(isinstance(s, _Kreis) for s in skizze.segmente)
        gesetzt = 0
        for a in self.aufrufe:
            if a[0] == "beziehung":
                zwei = a[1] in ("sgATMIDDLE", "sgSYMMETRIC") or (
                    a[1] == "sgCOINCIDENT" and all(isinstance(o, _Punkt) for o in a[2]))
                gesetzt += 2 if zwei else 1
            elif a[0] in ("horizontal", "vertikal", "frei"):
                gesetzt += 1
        return frei, gesetzt


URSPRUNG = _Punkt(0, 0.0, 0.0, "Ursprung")


def _uv(orientierung: str, p) -> tuple[float, float]:
    """Modellpunkt (mm) → (u, v); Umkehrung von skizze.modellpunkt."""
    if orientierung == "vorne":
        return p[0], p[1]
    if orientierung == "oben":
        return p[0], -p[2]
    return -p[2], p[1]


@pytest.fixture
def modell(monkeypatch):
    """Skizzen-x = u, Skizzen-y = v (wie auf der Deckfläche im Spike S17)."""
    m = _Modell()
    orientierung = {"wert": "oben"}

    def waehle(model, objekt, marke=0, anhaengen=False):
        model.auswahl = (model.auswahl if anhaengen else []) + [objekt]

    def leeren(model):
        model.auswahl = []

    monkeypatch.setattr(modul.sw, "waehle", waehle)
    monkeypatch.setattr(modul.sw, "auswahl_leeren", leeren)
    monkeypatch.setattr(modul.sw, "mathutil", lambda app: None)
    monkeypatch.setattr(modul.sw, "ursprung", lambda model: URSPRUNG)
    monkeypatch.setattr(modul.sw, "modell_zu_skizze",
                        lambda mu, skizze, p: tuple(c / 1000 for c in _uv(orientierung["wert"], p)))
    monkeypatch.setattr(modul.sw, "letztes_feature", lambda model: model.feature)
    monkeypatch.setattr(modul.sw, "einstellung", lambda *a: nullcontext())
    monkeypatch.setattr(modul.sw, "ohne_inferenz", lambda *a: nullcontext())
    monkeypatch.setattr(modul, "kante_aus", lambda e: e.kante)
    return m


def _kontext(modell, parameter=None, gleichungen=False) -> Kontext:
    spec = {"parameter": parameter or {}, "features": [{"id": "f1"}, {"id": "f2"}, {"id": "f3"}]}
    ctx = Kontext(None, modell, spec, Path("t.yaml"), 0.1, gleichungen=gleichungen)
    ctx.knoten = "f2"
    return ctx


class _Kante:
    def __init__(self, name, start, ende):
        d = tuple(b - a for a, b in zip(start, ende))
        n = sum(c * c for c in d) ** 0.5
        self.name = name
        self.kante = Kante("linie", start, ende, richtung=tuple(c / n for c in d), objekt=self)

    def __repr__(self):
        return self.name


def _block_kanten(y: float = 20.0) -> dict[str, _Kante]:
    """Deckfläche eines Blocks 100 × 60 (Ebene oben, y = 20): u = X, v = −Z."""
    return {"links": _Kante("links", (-50, y, 30), (-50, y, -30)), "rechts": _Kante("rechts", (50, y, -30), (50, y, 30)),
            "vorn": _Kante("vorn", (50, y, 30), (-50, y, 30)), "hinten": _Kante("hinten", (-50, y, -30), (50, y, -30))}


def _deckflaeche(kanten: dict) -> Flaeche:
    return Flaeche("ebene", (0.0, 20.0, 0.0), normale=(0.0, 1.0, 0.0),
                   objekt=SimpleNamespace(GetEdges=list(kanten.values())))


def _auf_flaeche(kanten: dict) -> Skizzenebene:
    return modul.ebene_aus_flaeche(_deckflaeche(kanten))


STANDARD_OBEN = Skizzenebene(object(), "oben", 0.0, (0.0, 1.0, 0.0))
P = "features[0].skizze.elemente"


def _punkt(modell, u, v) -> _Punkt:
    """Der Skizzenpunkt bei (u, v) – bei mehreren der zuerst angelegte."""
    return next(p for p in modell.SketchManager.ActiveSketch.punkte if abs(p.X - u / 1000) < 1e-12
                and abs(p.Y - v / 1000) < 1e-12)


def _lagen(ctx, fid="f2") -> list[dict]:
    return [m for m in ctx.masse[fid] if m["art"] == "lage"]


# --- Rechteck ----------------------------------------------------------------------------------------------------------


def _seiten(modell) -> list:
    """Die vier Seiten des (ersten) Rechtecks: unten (−v), rechts (+u), oben (+v), links (−u)."""
    return modell.linien()[:4]


def test_rechteck_um_ursprung_ueber_seitenmitten(modell):
    # Fall (c): Mitte (0, 0) – zwei Seitenmittelpunkte, keine Diagonale (Ruling 6)
    ctx = _kontext(modell)
    modul.skizziere(ctx, STANDARD_OBEN, [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}], "f1_skizze",
                    [f"{P}[0]"])
    unten, _, _, links = _seiten(modell)
    mitte_unten, mitte_links = modell.neue_punkte()
    assert ((mitte_unten.X, mitte_unten.Y), (mitte_links.X, mitte_links.Y)) == ((0.0, -0.03), (-0.05, 0.0))
    assert modell.beziehungen("sgATMIDDLE") == [(mitte_unten, unten), (mitte_links, links)]
    assert modell.beziehungen("sgVERTICALPOINTS2D") == [(mitte_unten, URSPRUNG)]  # u = 0
    assert modell.beziehungen("sgHORIZONTALPOINTS2D") == [(mitte_links, URSPRUNG)]  # v = 0
    assert modell.mittellinien() == []
    assert [a for a, _ in modell.masse("horizontal", "vertikal", "frei")] == ["frei", "frei"]  # Breite und Höhe
    assert [m["art"] for m in ctx.masse["f2"]] == ["groesse", "groesse"]
    assert modell.zaehlprobe() == (12, 12)


def test_rechteck_ursprung_bemasst_die_naechste_seite_ueber_die_ecke(modell):
    # Fall (a): beide Achsen Seite – die Ecke der zugewandten Seiten
    ctx = _kontext(modell, {"A": 30})
    r = {"mitte": ["=A", 20], "breite": 20, "hoehe": 10}
    modul.skizziere(ctx, STANDARD_OBEN, [{"rechteck": r}], "f1_skizze", [f"{P}[0]"])
    assert modell.mittellinien() == [] and modell.neue_punkte() == []
    ecke = _punkt(modell, 20, 15)  # dem Ursprung nächste Seiten: u = 20, v = 15
    assert modell.masse("horizontal", "vertikal") == [("horizontal", (ecke, URSPRUNG)), ("vertikal", (ecke, URSPRUNG))]
    # Pfad mitte[a]; roh ist die Seite als Ausdruck der Mitte (Ruling 7), der Wert die Seite
    assert [(m["pfad"], m["roh"], m["wert"], m["bezug"]) for m in _lagen(ctx)] == [
        (f"{P}[0].rechteck.mitte[0]", "=(A) - 20 / 2", 20.0, "ursprung"),
        (f"{P}[0].rechteck.mitte[1]", 15.0, 15.0, "ursprung")]
    assert modell.zaehlprobe() == (8, 8)


def test_rechteck_seite_zum_rand_und_mitte_ueber_den_seitenmittelpunkt(modell):
    # Fall (b): u zur linken Kante, v mitte (auf 0) – Mittelpunkt der linken Seite, beide Achsen
    kanten = _block_kanten()
    ctx = _kontext(modell)
    r = {"mitte": [-35, 0], "breite": 20, "hoehe": 10, "bezug": {"u": "-rand", "v": "mitte"}}
    modul.skizziere(ctx, _auf_flaeche(kanten), [{"rechteck": r}], "f2_skizze", [f"{P}[0]"])
    _, _, _, links = _seiten(modell)
    mitte, = modell.neue_punkte()
    assert (mitte.X, mitte.Y) == (-0.045, 0.0)
    assert modell.beziehungen("sgATMIDDLE") == [(mitte, links)]
    assert ("frei", (links, kanten["links"])) in modell.masse("frei")  # Seite + Kante (Spike S17 Zeile 3)
    assert modell.beziehungen("sgHORIZONTALPOINTS2D") == [(mitte, URSPRUNG)]
    assert modell.mittellinien() == [] and modell.masse("horizontal", "vertikal") == []
    assert [(m["pfad"], m["roh"], m["bezug"], m["wert"], m["vorzeichen"]) for m in _lagen(ctx)] == [
        (f"{P}[0].rechteck.mitte[0]", -45.0, "-rand", 5.0, 1)]
    assert modell.zaehlprobe() == (10, 10)


def test_zwei_taschen_mitte_und_rand_gepaart(modell):
    # Fall (b) paarfähig: {u: mitte, v: "-rand"} bei u = ±30 → Symmetrie, Abstand 60, ein Randmaß
    kanten = _block_kanten()
    ctx = _kontext(modell)
    elemente = [{"rechteck": {"mitte": [u, -20], "breite": 20, "hoehe": 10, "bezug": {"u": "mitte", "v": "-rand"}}}
                for u in (-30, 30)]
    modul.skizziere(ctx, _auf_flaeche(kanten), elemente, "f2_skizze", [f"{P}[0]", f"{P}[1]"])
    links, rechts = modell.neue_punkte()  # Mitten der unteren Seiten (v = −25)
    assert ((links.X, links.Y), (rechts.X, rechts.Y)) == ((-0.03, -0.025), (0.03, -0.025))
    mittellinie, = modell.mittellinien()
    assert modell.beziehungen("sgSYMMETRIC") == [(links, rechts, mittellinie)]
    assert modell.masse("horizontal") == [("horizontal", (links, rechts))]
    unten_links = modell.linien()[0]
    assert modell.masse("frei")[-1] == ("frei", (unten_links, kanten["vorn"]))  # nur der festlegende Punkt
    assert [(m["pfad"], m["bezug"], m["wert"]) for m in _lagen(ctx)] == [
        (f"{P}[0].rechteck.mitte[0]", "mitte", 60.0), (f"{P}[0].rechteck.mitte[1]", "-rand", 5.0)]
    assert modell.zaehlprobe() == (24, 24)


def test_zwei_rechtecke_mitte_gepaart_ueber_diagonalen(modell):
    # Fall (d): beide Achsen mitte-artig, Mitte ≠ (0, 0) – Mittelpunkt über die Diagonale, paarfähig
    ctx = _kontext(modell)
    elemente = [{"rechteck": {"mitte": [u, 0], "breite": 20, "hoehe": 10, "bezug": {"u": "mitte"}}} for u in (-30, 30)]
    modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]", f"{P}[1]"])
    diagonale_1, diagonale_2, mittellinie = modell.mittellinien()
    mitte_1, mitte_2 = modell.neue_punkte()
    assert ((mitte_1.X, mitte_1.Y), (mitte_2.X, mitte_2.Y)) == ((-0.03, 0.0), (0.03, 0.0))
    assert modell.beziehungen("sgATMIDDLE") == [(mitte_1, diagonale_1), (mitte_2, diagonale_2)]
    assert modell.beziehungen("sgSYMMETRIC") == [(mitte_1, mitte_2, mittellinie)]
    assert modell.beziehungen("sgHORIZONTALPOINTS2D") == [(mitte_1, URSPRUNG)]
    assert [(m["bezug"], m["wert"]) for m in _lagen(ctx)] == [("mitte", 60.0)]
    assert modell.zaehlprobe() == (24, 24)


def test_rechteck_versetzt_mit_mitte_ueber_diagonale(modell):
    # Fall (d) ungepaart: Mittelpunkt über die Diagonale, Maße zum Ursprung
    ctx = _kontext(modell)
    r = {"mitte": [12, 7], "breite": 20, "hoehe": 10, "bezug": {"u": "mitte", "v": "mitte"}}
    modul.skizziere(ctx, STANDARD_OBEN, [{"rechteck": r}], "f1_skizze", [f"{P}[0]"])
    diagonale, = modell.mittellinien()
    mitte, = modell.neue_punkte()
    assert modell.beziehungen("sgATMIDDLE") == [(mitte, diagonale)]
    assert modell.masse("horizontal", "vertikal") == [("horizontal", (mitte, URSPRUNG)), ("vertikal", (mitte, URSPRUNG))]
    assert [(m["roh"], m["wert"]) for m in _lagen(ctx)] == [(12, 12.0), (7, 7.0)]
    assert modell.zaehlprobe() == (10, 10)


def test_rechteck_zur_flaeche_loest_die_kante_einmal_auf(monkeypatch, modell):
    # Kennkoordinate (zugewandte Seite) und Maß nutzen dieselbe Kante (M1)
    kanten = _block_kanten()
    seite = Flaeche("ebene", (50.0, 10.0, 0.0), normale=(1.0, 0.0, 0.0))
    aufgeloest = []
    monkeypatch.setattr(modul, "loese_flaeche", lambda ctx, anker: aufgeloest.append(anker) or seite)
    ctx = _kontext(modell)
    bezug = {"flaeche": {"feature": "f1", "flaeche": "+x"}}
    r = {"mitte": [30, 0], "breite": 20, "hoehe": 10, "bezug": {"u": bezug}}
    modul.skizziere(ctx, _auf_flaeche(kanten), [{"rechteck": r}], "f2_skizze", [f"{P}[0]"])
    _, rechts, _, _ = _seiten(modell)
    mitte, = modell.neue_punkte()  # Fall (b): Mitte der rechten Seite (u = 40, v = 0)
    assert (mitte.X, mitte.Y) == (0.04, 0.0)
    assert modell.beziehungen("sgATMIDDLE") == [(mitte, rechts)]
    assert ("frei", (rechts, kanten["rechts"])) in modell.masse("frei")
    assert [(m["bezug"], m["wert"], m["vorzeichen"]) for m in _lagen(ctx)] == [(bezug, 10.0, -1)]
    assert len(aufgeloest) == 1


def test_rechteck_mit_radius_um_ursprung_verrundet_nach_den_lagen(modell):
    ctx = _kontext(modell)
    r = {"mitte": [0, 0], "breite": 40, "hoehe": 20, "radius": 5}
    modul.skizziere(ctx, STANDARD_OBEN, [{"rechteck": r}], "f1_skizze", [f"{P}[0]"])
    arten = [a[0] if a[0] != "beziehung" else a[1] for a in modell.aufrufe]
    verrundungen = [i for i, a in enumerate(arten) if a == "verrundung"]
    lagen = [i for i, a in enumerate(arten) if a in ("sgATMIDDLE", "sgVERTICALPOINTS2D", "sgHORIZONTALPOINTS2D")]
    assert len(verrundungen) == 4 and len(lagen) == 4 and max(lagen) < min(verrundungen)
    assert modell.mittellinien() == []
    assert [m["art"] for m in ctx.masse["f2"]] == ["groesse", "groesse"] + ["radius"] * 4


def test_rotation_rechteck_um_ursprung_ohne_konstruktionslinien(modell):
    # Fall (c) in der Rotationsskizze: nur die Achse ist Mittellinie
    ctx = _kontext(modell)
    elemente = [{"rechteck": {"mitte": [0, 0], "breite": 20, "hoehe": 40, "bezug": {"u": "mitte", "v": "mitte"}}},
                {"mittellinie": {"von": [0, -30], "bis": [0, 30]}}]
    modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]", f"{P}[1]"], hilfslinien=False)
    assert len(modell.mittellinien()) == 1
    assert len(modell.beziehungen("sgATMIDDLE")) == 2 and modell.beziehungen("sgSYMMETRIC") == []


def test_rotation_rechteck_versetzt_mit_mitte_ueber_seitenmitten(modell):
    # statt (d) ohne Hilfslinien: zwei Seitenmittelpunkte mit Maßen zum Ursprung, keine Diagonale
    ctx = _kontext(modell)
    elemente = [{"rechteck": {"mitte": [10, 5], "breite": 20, "hoehe": 40, "bezug": {"u": "mitte", "v": "mitte"}}},
                {"mittellinie": {"von": [0, -30], "bis": [0, 30]}}]
    modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]", f"{P}[1]"], hilfslinien=False)
    unten, _, _, links = _seiten(modell)
    mitte_unten, mitte_links = modell.neue_punkte()
    assert modell.beziehungen("sgATMIDDLE") == [(mitte_unten, unten), (mitte_links, links)]
    assert len(modell.mittellinien()) == 1
    assert ("horizontal", (mitte_unten, URSPRUNG)) in modell.masse("horizontal")
    assert ("vertikal", (mitte_links, URSPRUNG)) in modell.masse("vertikal")
    assert [(m["pfad"], m["wert"]) for m in _lagen(ctx)][:2] == [
        (f"{P}[0].rechteck.mitte[0]", 10.0), (f"{P}[0].rechteck.mitte[1]", 5.0)]


# --- Gleichungen an (Ruling 7) ----------------------------------------------------------------------------------------


def test_gleichung_der_rechteckseite(modell):
    ctx = _kontext(modell, {"A": 30}, gleichungen=True)
    modul.skizziere(ctx, STANDARD_OBEN, [{"rechteck": {"mitte": ["=A", 20], "breite": 20, "hoehe": 10}}], "f1_skizze",
                    [f"{P}[0]"])
    assert modell.GetEquationMgr.texte == ['"D3@f1_skizze" = "A" - (20 / 2)']


def test_gleichung_des_paarabstands(modell):
    ctx = _kontext(modell, {"ZG": 30}, gleichungen=True)
    elemente = [{"kreis": {"mitte": [u, 0], "durchmesser": 8, "bezug": {"u": "mitte"}}} for u in ("=-ZG", "=ZG")]
    modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]", f"{P}[1]"])
    abstand, = _lagen(ctx)
    assert (abstand["roh"], abstand["vorzeichen"], abstand["wert"]) == ("=2 * (-ZG)", -1, 60.0)
    assert modell.GetEquationMgr.texte == [f'"{abstand["name"]}" = -(2 * -"ZG")']


def test_gleichung_nie_zum_rand(modell):
    ctx = _kontext(modell, {"X": 40}, gleichungen=True)
    elemente = [{"kreis": {"mitte": ["=-X", 0], "durchmesser": 4, "bezug": {"u": "-rand"}}}]
    modul.skizziere(ctx, _auf_flaeche(_block_kanten()), elemente, "f2_skizze", [f"{P}[0]"])
    assert modell.GetEquationMgr.texte == []


# --- Kreise: mitte ----------------------------------------------------------------------------------------------------


def _zwei_kreise(bezug=None) -> list[dict]:
    return [{"kreis": {"mitte": [u, 0], "durchmesser": 8, **({"bezug": bezug} if bezug else {})}} for u in (-30, 30)]


def test_kreise_mitte_paar_ueber_elemente(modell):
    ctx = _kontext(modell)
    modul.skizziere(ctx, STANDARD_OBEN, _zwei_kreise({"u": "mitte"}), "f1_skizze", [f"{P}[0]", f"{P}[1]"])
    links, rechts = _punkt(modell, -30, 0), _punkt(modell, 30, 0)
    mittellinie, = modell.mittellinien()
    assert modell.beziehungen("sgSYMMETRIC") == [(links, rechts, mittellinie)]
    assert ("horizontal", (links, rechts)) in modell.masse("horizontal")
    abstand, = [m for m in _lagen(ctx) if m["bezug"] == "mitte"]
    assert abstand | {"name": None} == {"name": None, "pfad": f"{P}[0].kreis.mitte[0]", "art": "lage", "bezug": "mitte",
                                        "roh": -60, "vorzeichen": -1, "wert": 60.0}
    # Mittellinie entlang v durch den Ursprung; ohne Skizzenfläche mit Längenmaß (Ruling 4a)
    assert (mittellinie.GetStartPoint2.X, mittellinie.GetEndPoint2.X) == (0.0, 0.0)
    assert modell.beziehungen("sgCOINCIDENT") == [(mittellinie.GetStartPoint2, URSPRUNG)]
    assert modell.beziehungen("sgVERTICAL2D") == [(mittellinie,)]
    assert [m["art"] for m in ctx.masse["f2"]].count("konstruktion") == 1
    # v = 0: nur der festlegende Punkt bekommt die Ausrichtung, der Partner folgt aus der Symmetrie
    assert modell.beziehungen("sgHORIZONTALPOINTS2D") == [(links, URSPRUNG)]
    assert [m["art"] for m in ctx.masse["f2"]] == ["groesse", "groesse", "konstruktion", "lage"]


def test_mitte_auf_flaeche_mittellinie_endet_auf_der_randkante(modell):
    kanten = _block_kanten()
    ctx = _kontext(modell)
    modul.skizziere(ctx, _auf_flaeche(kanten), _zwei_kreise({"u": "mitte"}), "f2_skizze", [f"{P}[0]", f"{P}[1]"])
    mittellinie, = modell.mittellinien()
    # entlang v bis zur Randkante in −v (Kante "vorn", v = −30), Endpunkt deckungsgleich (Ruling 4, Spike Zeile 4)
    assert (mittellinie.GetEndPoint2.X, mittellinie.GetEndPoint2.Y) == (0.0, -0.03)
    assert modell.beziehungen("sgCOINCIDENT") == [(mittellinie.GetStartPoint2, URSPRUNG),
                                                  (mittellinie.GetEndPoint2, kanten["vorn"])]
    assert "konstruktion" not in [m["art"] for m in ctx.masse["f2"]]


def test_ungepaarte_mitte_und_ursprung_wie_bisher(modell):
    ctx = _kontext(modell)
    elemente = [{"kreis": {"mitte": [12, 7], "durchmesser": 8, "bezug": {"u": "mitte"}}}]
    modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]"])
    mitte = _punkt(modell, 12, 7)
    assert modell.mittellinien() == []
    assert modell.masse("horizontal", "vertikal") == [("horizontal", (mitte, URSPRUNG)), ("vertikal", (mitte, URSPRUNG))]
    assert [(m["pfad"], m["roh"], m["vorzeichen"], m["wert"], m["bezug"]) for m in _lagen(ctx)] == [
        (f"{P}[0].kreis.mitte[0]", 12, 1, 12.0, "mitte"), (f"{P}[0].kreis.mitte[1]", 7, 1, 7.0, "ursprung")]


def test_kreis_im_ursprung_deckungsgleich(modell):
    ctx = _kontext(modell)
    modul.skizziere(ctx, STANDARD_OBEN, [{"kreis": {"mitte": [0, 0], "durchmesser": 8}}], "f1_skizze", [f"{P}[0]"])
    assert modell.beziehungen("sgCOINCIDENT") == [(_punkt(modell, 0, 0), URSPRUNG)]
    assert _lagen(ctx) == []


# --- Bohrung: rand und Senkung ----------------------------------------------------------------------------------------


def _bohren(monkeypatch, modell, kanten, f: dict) -> Kontext:
    from swki.compiler.handler import bohrung as h

    monkeypatch.setattr(h, "loese_flaeche", lambda ctx, anker: _deckflaeche(kanten))
    monkeypatch.setattr(h, "schnitt", lambda *args: _Feature())
    ctx = _kontext(modell)
    h.bohrung(ctx, f)
    return ctx


def test_bohrung_rand_maß_zur_kante(monkeypatch, modell):
    kanten = _block_kanten()
    f = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "durchmesser": 8, "durch": True,
         "positionen": [[-40, 0]], "bezug": {"u": "-rand"}}
    ctx = _bohren(monkeypatch, modell, kanten, f)
    mitte = _punkt(modell, -40, 0)
    assert ("horizontal", (mitte, kanten["links"])) in modell.masse("horizontal")  # Spike S17 Zeile 1
    assert modell.beziehungen("sgHORIZONTALPOINTS2D") == [(mitte, URSPRUNG)]  # v = 0
    assert _lagen(ctx) == [{"name": "D2@f2_skizze", "pfad": "features[1].positionen[0][0]", "art": "lage",
                            "bezug": "-rand", "roh": -40, "vorzeichen": 1, "wert": 10.0}]


def test_bohrung_senkung_erbt_bezug(monkeypatch, modell):
    kanten = _block_kanten()
    f = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "durchmesser": 6, "tiefe": 10,
         "positionen": [[-40, 20], [-40, -20]], "bezug": {"u": "-rand", "v": "mitte"},
         "senkung": {"durchmesser": 11, "tiefe": 6}}
    ctx = _bohren(monkeypatch, modell, kanten, f)
    lagen = [(m["name"].split("@")[1], m["pfad"], m["bezug"], m["wert"]) for m in _lagen(ctx)]
    # je Skizze: Symmetrie zur Mittellinie entlang u, Abstand 40, Rand 10 – nur am festlegenden Punkt (positionen[0])
    for skizze in ("f2_skizze", "f2_senkung_skizze"):
        assert sorted(x[1:] for x in lagen if x[0] == skizze) == [
            ("features[1].positionen[0][0]", "-rand", 10.0), ("features[1].positionen[0][1]", "mitte", 40.0)]
    assert len(modell.beziehungen("sgSYMMETRIC")) == 2
    # Maße der Senkung stehen unter der Feature-ID der Bohrung
    assert set(ctx.masse) == {"f2"}


def test_flaechenbezug_bemasst_zur_kante_in_der_seitenflaeche(monkeypatch, modell):
    kanten = _block_kanten()
    seite = Flaeche("ebene", (50.0, 10.0, 0.0), normale=(1.0, 0.0, 0.0))
    monkeypatch.setattr(modul, "loese_flaeche", lambda ctx, anker: seite)
    ctx = _kontext(modell)
    bezug = {"flaeche": {"feature": "f1", "flaeche": "+x"}}
    elemente = [{"kreis": {"mitte": [42, 5], "durchmesser": 4, "bezug": {"u": bezug}}}]
    modul.skizziere(ctx, _auf_flaeche(kanten), elemente, "f2_skizze", [f"{P}[0]"])
    assert ("horizontal", (_punkt(modell, 42, 5), kanten["rechts"])) in modell.masse("horizontal")
    assert [(m["bezug"], m["wert"], m["vorzeichen"]) for m in _lagen(ctx)][0] == (bezug, 8.0, -1)


def test_flaechenbezug_ohne_kante_in_der_skizzenflaeche(monkeypatch, modell):
    seite = Flaeche("ebene", (80.0, 10.0, 0.0), normale=(1.0, 0.0, 0.0))  # berührt die Deckfläche nicht
    monkeypatch.setattr(modul, "loese_flaeche", lambda ctx, anker: seite)
    ctx = _kontext(modell)
    elemente = [{"kreis": {"mitte": [42, 5], "durchmesser": 4, "bezug": {"u": {"flaeche": {"nahe": [80, 10, 0]}}}}}]
    with pytest.raises(BauFehler) as e:
        modul.skizziere(ctx, _auf_flaeche(_block_kanten()), elemente, "f2_skizze", [f"{P}[0]"])
    assert e.value.code == "REFERENZ_NICHT_GEFUNDEN"


def test_rand_ohne_skizzenflaeche_ist_ein_baufehler(modell):
    ctx = _kontext(modell)
    elemente = [{"kreis": {"mitte": [42, 5], "durchmesser": 4, "bezug": {"u": "+rand"}}}]
    with pytest.raises(BauFehler) as e:
        modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]"])
    assert e.value.code == "REFERENZ_NICHT_GEFUNDEN"


# --- Normbohrung: Positionsskizze -------------------------------------------------------------------------------------


def test_positionen_festlegen_mit_bezug(monkeypatch, modell):
    kanten = _block_kanten()
    ctx = _kontext(modell)
    sm = modell.SketchManager
    sm._neu(-0.04, 0.02)  # erste Position steht schon (SelectByRay)
    skizze = _Feature()
    monkeypatch.setattr(modul, "positionsskizze", lambda feature: skizze)
    modul.positionen_festlegen(ctx, object(), _auf_flaeche(kanten), [[-40, 20], [-40, -20]], "f2_positionen",
                               {"u": "-rand", "v": "mitte"}, "features[1].positionen")
    erste, zweite = _punkt(modell, -40, 20), _punkt(modell, -40, -20)
    mittellinie, = modell.mittellinien()
    assert modell.beziehungen("sgSYMMETRIC") == [(erste, zweite, mittellinie)]
    assert ("horizontal", (erste, kanten["links"])) in modell.masse("horizontal")
    assert [(m["name"], m["pfad"], m["bezug"], m["wert"]) for m in _lagen(ctx)] == [
        ("D1@f2_positionen", "features[1].positionen[0][0]", "-rand", 10.0),
        ("D2@f2_positionen", "features[1].positionen[0][1]", "mitte", 40.0)]
    assert skizze.Name == "f2_positionen"


# --- Konturen, Rotation, Notausgang -----------------------------------------------------------------------------------


def test_kontur_bleibt_koordinatenmass(modell):
    ctx = _kontext(modell)
    punkte = [[0, 0], [40, 0], [40, 10], [-20, 10]]
    modul.skizziere(ctx, STANDARD_OBEN, [{"polygon": {"punkte": punkte}}], "f1_skizze", [f"{P}[0]"])
    assert modell.mittellinien() == []
    assert modell.beziehungen("sgCOINCIDENT") == [(_punkt(modell, 0, 0), URSPRUNG)]
    assert modell.beziehungen("sgVERTICALPOINTS2D") == []
    assert modell.beziehungen("sgHORIZONTALPOINTS2D") == [(_punkt(modell, 40, 0), URSPRUNG)]
    assert [(m["pfad"], m["bezug"], m["wert"]) for m in _lagen(ctx)] == [
        (f"{P}[0].polygon.punkte[1][0]", "ursprung", 40.0), (f"{P}[0].polygon.punkte[2][0]", "ursprung", 40.0),
        (f"{P}[0].polygon.punkte[2][1]", "ursprung", 10.0), (f"{P}[0].polygon.punkte[3][0]", "ursprung", 20.0),
        (f"{P}[0].polygon.punkte[3][1]", "ursprung", 10.0)]
    assert all(ziel is URSPRUNG for _, (_, ziel) in modell.masse("horizontal", "vertikal"))


def test_rotation_ohne_zusaetzliche_mittellinien(modell):
    # Die Mittellinie der Skizze wird Rotationsachse: keine Diagonale, keine Symmetrielinie (sonst zwei Mittellinien)
    ctx = _kontext(modell)
    elemente = [{"rechteck": {"mitte": [10, 0], "breite": 20, "hoehe": 40}},
                {"mittellinie": {"von": [0, -30], "bis": [0, 30]}}]
    modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]", f"{P}[1]"], hilfslinien=False)
    assert len(modell.mittellinien()) == 1
    _, _, _, links = _seiten(modell)
    mitte, = modell.neue_punkte()  # Fall (b): linke Seite u = 0, Mitte v = 0 → Mittelpunkt der linken Seite
    assert modell.beziehungen("sgATMIDDLE") == [(mitte, links)]
    assert modell.beziehungen("sgCOINCIDENT")[0] == (mitte, URSPRUNG)


def test_nicht_bindbare_lage_traegt_skizzenkoordinate_mit_ihrem_vorzeichen(modell, monkeypatch):
    """Skizzenursprung ≠ Projektion des Modellursprungs: roh ist die Skizzenkoordinate (mm), vorzeichen ihr Vorzeichen."""
    ctx = _kontext(modell)
    monkeypatch.setattr(modul.sw, "modell_zu_skizze", lambda mu, skizze, p: ((p[0] + 5) / 1000, (p[2] + 2) / 1000))
    elemente = [{"kreis": {"mitte": ["=1+29", 12], "durchmesser": 4}}]
    modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]"])
    # u = 30 → x = 35 mm; v = 12 → Modell z = −12 → y = −10 mm
    assert [(m["roh"], m["vorzeichen"]) for m in _lagen(ctx)] == [(pytest.approx(35.0), 1), (pytest.approx(-10.0), -1)]
