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

    def InsertSketch(self, neu):  # noqa: N802
        pass


class _Anzeige:
    def __init__(self, name):
        self.name = name

    def GetDimension2(self, i):  # noqa: N802
        return SimpleNamespace(Name=self.name)


class _Feature:
    def __init__(self):
        self.Name = ""

    def Select2(self, anhaengen, marke):  # noqa: N802
        return True


class _Modell:
    def __init__(self):
        self.auswahl, self.aufrufe, self.nr = [], [], 0
        self.SketchManager = _Manager(self)
        self.feature = _Feature()

    def SketchAddConstraints(self, art):  # noqa: N802
        self.aufrufe.append(("beziehung", art, tuple(self.auswahl)))

    def _mass(self, art):
        self.nr += 1
        self.aufrufe.append((art, tuple(self.auswahl), f"D{self.nr}"))
        return _Anzeige(f"D{self.nr}")

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


def _kontext(modell, parameter=None) -> Kontext:
    spec = {"parameter": parameter or {}, "features": [{"id": "f1"}, {"id": "f2"}, {"id": "f3"}]}
    ctx = Kontext(None, modell, spec, Path("t.yaml"), 0.1)
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


def test_rechteck_um_ursprung_ueber_mitte(modell):
    ctx = _kontext(modell)
    modul.skizziere(ctx, STANDARD_OBEN, [{"rechteck": {"mitte": [0, 0], "breite": 100, "hoehe": 60}}], "f1_skizze",
                    [f"{P}[0]"])
    diagonale, = modell.mittellinien()
    # Diagonale von Ecke (−,−) nach (+,+), teilt die Ecken (Spike S17 Zeile 5)
    assert (diagonale.GetStartPoint2.X, diagonale.GetStartPoint2.Y) == (-0.05, -0.03)
    assert (diagonale.GetEndPoint2.X, diagonale.GetEndPoint2.Y) == (0.05, 0.03)
    assert modell.beziehungen("sgATMIDDLE") == [(URSPRUNG, diagonale)]
    assert modell.beziehungen("sgCOINCIDENT") == []
    assert [a for a, _ in modell.masse("horizontal", "vertikal", "frei")] == ["frei", "frei"]  # Breite und Höhe
    assert [m["art"] for m in ctx.masse["f2"]] == ["groesse", "groesse"]


def test_rechteck_ursprung_bemasst_die_naechste_seite_ueber_die_ecke(modell):
    ctx = _kontext(modell, {"A": 30})
    r = {"mitte": ["=A", 20], "breite": 20, "hoehe": 10}
    modul.skizziere(ctx, STANDARD_OBEN, [{"rechteck": r}], "f1_skizze", [f"{P}[0]"])
    assert modell.mittellinien() == []  # keine Diagonale, wenn keine Achse über die Mitte läuft
    ecke = _punkt(modell, 20, 15)  # dem Ursprung nächste Seiten: u = 20, v = 15
    assert modell.masse("horizontal", "vertikal") == [("horizontal", (ecke, URSPRUNG)), ("vertikal", (ecke, URSPRUNG))]
    # Pfad mitte[a]; Wert ist die Seite, roh der Spec-Wert der Mitte (keine Gleichung: roh ≠ Maßwert)
    assert [(m["pfad"], m["roh"], m["wert"], m["bezug"]) for m in _lagen(ctx)] == [
        (f"{P}[0].rechteck.mitte[0]", "=A", 20.0, "ursprung"), (f"{P}[0].rechteck.mitte[1]", 20, 15.0, "ursprung")]


def test_rechteck_seite_zum_rand_mit_linie_und_kante(modell):
    kanten = _block_kanten()
    ctx = _kontext(modell)
    r = {"mitte": [-35, 0], "breite": 20, "hoehe": 10, "bezug": {"u": "-rand", "v": "mitte"}}
    modul.skizziere(ctx, _auf_flaeche(kanten), [{"rechteck": r}], "f2_skizze", [f"{P}[0]"])
    links = next(a[1] for a in modell.aufrufe if a[0] == "linie" and a[1].GetStartPoint2.X == -0.045
                 and a[1].GetEndPoint2.X == -0.045)
    # u: linke Seite zur linken Kante (AddDimension2, Spike Zeile 3); v: Mitte auf 0 über die Diagonale
    assert ("frei", (links, kanten["links"])) in modell.masse("frei")
    diagonale, = modell.mittellinien()
    mitte, = [a[1] for a in modell.aufrufe if a[0] == "punkt"]
    assert modell.beziehungen("sgATMIDDLE") == [(mitte, diagonale)]
    assert modell.masse("horizontal", "vertikal") == []
    assert modell.beziehungen("sgHORIZONTALPOINTS2D") == [(mitte, URSPRUNG)]
    assert [(m["pfad"], m["bezug"], m["wert"], m["vorzeichen"]) for m in _lagen(ctx)] == [
        (f"{P}[0].rechteck.mitte[0]", "-rand", 5.0, 1)]


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
                                        "roh": -30, "vorzeichen": -1, "wert": 60.0}
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
    modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]", f"{P}[1]"])
    assert len(modell.mittellinien()) == 1
    assert modell.beziehungen("sgATMIDDLE") == []
    ecke = _punkt(modell, 0, -20)  # v: Mitte auf 0 → Seite in −v
    assert modell.beziehungen("sgVERTICALPOINTS2D")[0] == (ecke, URSPRUNG)  # linke Seite u = 0


def test_nicht_bindbare_lage_traegt_skizzenkoordinate_mit_ihrem_vorzeichen(modell, monkeypatch):
    """Skizzenursprung ≠ Projektion des Modellursprungs: roh ist die Skizzenkoordinate (mm), vorzeichen ihr Vorzeichen."""
    ctx = _kontext(modell)
    monkeypatch.setattr(modul.sw, "modell_zu_skizze", lambda mu, skizze, p: ((p[0] + 5) / 1000, (p[2] + 2) / 1000))
    elemente = [{"kreis": {"mitte": ["=1+29", 12], "durchmesser": 4}}]
    modul.skizziere(ctx, STANDARD_OBEN, elemente, "f1_skizze", [f"{P}[0]"])
    # u = 30 → x = 35 mm; v = 12 → Modell z = −12 → y = −10 mm
    assert [(m["roh"], m["vorzeichen"]) for m in _lagen(ctx)] == [(pytest.approx(35.0), 1), (pytest.approx(-10.0), -1)]
