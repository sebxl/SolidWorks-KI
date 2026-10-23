"""Maßprotokoll (Bemaßungsbezug, Task 5): jedes Maß landet mit Spec-Pfad im Bauprotokoll (Knoten.masse) – ohne SolidWorks."""

import json
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.compiler import skizze as modul
from swki.compiler.ablauf import baue_features
from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import FeatureErgebnis, Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.skizze import Skizzenebene, Skizzierer, _Mass

P = "features[0].skizze.elemente[0]"
URSPRUNG_UV = {0: "ursprung", 1: "ursprung"}


def _kontext(**kw) -> Kontext:
    spec = {"parameter": {"T": 8, "B": 40}, "features": [{"id": "f1"}, {"id": "f2"}]}
    return Kontext(None, SimpleNamespace(), spec, Path("t.yaml"), 0.1, **kw)


# --- Bauprotokoll -------------------------------------------------------------------------------------------------------


@dataclass
class _Feature:
    Name: str


@dataclass
class _Ctx:
    spec: dict
    ergebnisse: dict = field(default_factory=dict)
    knoten: str | None = None
    masse: dict = field(default_factory=dict)


def _protokoll() -> Protokoll:
    return Protokoll("A", "a.yaml", 1, 2025)


def _eintrag(name: str) -> dict:
    return {"name": name, "pfad": "features[0].ende.tiefe", "art": "tiefe", "bezug": None, "roh": 5, "vorzeichen": 1,
            "wert": 5.0}


def test_baue_features_schreibt_masse_in_knoten():
    ctx = _Ctx({"features": [{"id": "f1", "typ": "a"}, {"id": "f2", "typ": "b"}]})
    gesehen = []

    def mit_masse(ctx, f):
        gesehen.append(ctx.knoten)
        ctx.masse.setdefault(ctx.knoten, []).append(_eintrag("D1@f1"))
        return FeatureErgebnis([_Feature(f["id"])])

    def ohne_masse(ctx, f):
        gesehen.append(ctx.knoten)
        return FeatureErgebnis([_Feature(f["id"])])

    p = _protokoll()
    assert baue_features(ctx, p, {"a": mit_masse, "b": ohne_masse}, lambda c: None) is None
    assert gesehen == ["f1", "f2"]  # ctx.knoten steht vor jedem Handler
    assert p.knoten[0].masse == [_eintrag("D1@f1")]
    assert p.knoten[1].masse is None
    assert ctx.masse == {}  # abgeholt


def test_masse_bleiben_auch_beim_fehler_im_knoten():
    ctx = _Ctx({"features": [{"id": "f1", "typ": "a"}]})

    def kaputt(ctx, f):
        ctx.masse.setdefault(ctx.knoten, []).append(_eintrag("D1@f1"))
        raise BauFehler("FEATURE_NICHT_ERZEUGT", "nicht erzeugt", schritt="feature")

    p = _protokoll()
    assert isinstance(baue_features(ctx, p, {"a": kaputt}, lambda c: None), BauFehler)
    assert p.knoten[0].status == "fehler" and p.knoten[0].masse == [_eintrag("D1@f1")]


def test_protokoll_json_enthaelt_masse(tmp_path):
    p = _protokoll()
    with p.knoten_lauf("f1", "extrusion") as k:
        k.masse = [_eintrag("D1@f1")]
    p.uebersprungen("f2", "fase")
    ziel = tmp_path / "protokoll.json"
    p.schreibe(ziel)
    knoten = json.loads(ziel.read_text(encoding="utf-8"))["knoten"]
    assert knoten[0]["masse"] == [_eintrag("D1@f1")]
    assert knoten[1]["masse"] is None


# --- Skizzierer: Pfade der Maße -----------------------------------------------------------------------------------------


class _Punkt:
    def __init__(self, x, y):
        self.X, self.Y, self.GetID = x, y, (1, id(self))


class _Segment:
    def __init__(self, a, b):
        self.a, self.b = a, b

    @property
    def GetStartPoint2(self):
        return _Punkt(*self.a)

    @property
    def GetEndPoint2(self):
        return _Punkt(*self.b)


class _Skizzenmanager:
    def __getattr__(self, name):
        if name.startswith("Create"):
            return lambda *args: object()
        raise AttributeError(name)


class _Modell:
    def SketchAddConstraints(self, art):  # noqa: N802 – Name der SolidWorks-API
        pass


class _Aufzeichner(Skizzierer):
    """Skizzierer ohne SolidWorks: Größenmaße, vorgemerkte Lagen und Radien werden nur mit ihren Pfaden aufgezeichnet."""

    def __init__(self, ctx):
        self.ctx, self.model, self.sm, self.masse = ctx, _Modell(), _Skizzenmanager(), []
        self.gleichsinnig, self.hilfslinien = True, True
        self._kennpunkte, self._ziele, self._verrundungen = [], [], []
        self.aufrufe = []

    def zu_skizze(self, u, v):
        return u / 1000, v / 1000

    def _linienzug(self, punkte):
        return [_Segment(a, b) for a, b in zip(punkte, punkte[1:] + punkte[:1])]

    def groesse(self, segment, text_uv, roh, pfad=None, art="groesse"):
        self.aufrufe.append(("groesse", roh, pfad, art))

    def kennpunkt(self, punkt_uv, roh_uv, bezug, pfad, gruppe, achsen=(0, 1), ziel=None):
        self.aufrufe.append(("lage", list(roh_uv), pfad, tuple(achsen)))

    def _diagonale(self, seg):
        return object()

    def verrunde(self, linien, ecke_uv, roh_radius, pfad=None):
        self.aufrufe.append(("radius", roh_radius, pfad))


@pytest.fixture(autouse=True)
def _ohne_sw(monkeypatch):
    monkeypatch.setattr(modul.sw, "auswahl_leeren", lambda model: None)
    monkeypatch.setattr(modul.sw, "waehle", lambda *args, **kwargs: None)


def _aufrufe(element: dict, pfad=P) -> list:
    sk = _Aufzeichner(_kontext())
    sk.element(element, pfad)
    sk.lagen_festlegen()  # legt die vorgemerkten Verrundungen an
    return sk.aufrufe


def test_rechteck_pfade():
    r = {"mitte": [5, "=B"], "breite": "=B", "hoehe": 20, "radius": 3}
    aufrufe = _aufrufe({"rechteck": r})
    assert aufrufe[0] == ("groesse", "=B", f"{P}.rechteck.breite", "groesse")
    assert aufrufe[1] == ("groesse", 20, f"{P}.rechteck.hoehe", "groesse")
    # Seiten u = −15, v = 30 sind dem Ursprung am nächsten: ein Kennpunkt (Ecke) für beide Achsen, Pfad der Mitte,
    # roh die Seite als Ausdruck von Mitte und Größe (für Gleichungen, Ruling 7)
    assert aufrufe[2] == ("lage", ["=5 - (B) / 2", "=(B) - 20 / 2"], f"{P}.rechteck.mitte", (0, 1))
    assert aufrufe[3:] == [("radius", 3, f"{P}.rechteck.radius")] * 4


def test_kreis_pfade():
    aufrufe = _aufrufe({"kreis": {"mitte": [1, 2], "durchmesser": "=T"}})
    assert aufrufe == [("groesse", "=T", f"{P}.kreis.durchmesser", "groesse"),
                       ("lage", [1, 2], f"{P}.kreis.mitte", (0, 1))]


def test_pfade_als_dict_fuer_bohrungen():
    # Bohrung: die Lage steht in positionen[k], der Durchmesser am Feature
    pfad = {"mitte": "features[0].positionen[2]", "durchmesser": "features[0].senkung.durchmesser"}
    aufrufe = _aufrufe({"kreis": {"mitte": [1, 2], "durchmesser": 9}}, pfad)
    assert aufrufe == [("groesse", 9, "features[0].senkung.durchmesser", "groesse"),
                       ("lage", [1, 2], "features[0].positionen[2]", (0, 1))]


def test_polygon_pfade_radien_liste_und_skalar():
    punkte = [[0, 0], [10, 0], [10, 5]]
    liste = _aufrufe({"polygon": {"punkte": punkte, "radien": [0, 2, "=T"]}})
    assert [a[2] for a in liste if a[0] == "lage"] == [f"{P}.polygon.punkte[{k}]" for k in range(3)]
    assert [a[1:] for a in liste if a[0] == "radius"] == [(0, f"{P}.polygon.radien[0]"), (2, f"{P}.polygon.radien[1]"),
                                                           ("=T", f"{P}.polygon.radien[2]")]
    skalar = _aufrufe({"polygon": {"punkte": punkte, "radien": 2}})
    assert {a[2] for a in skalar if a[0] == "radius"} == {f"{P}.polygon.radien"}


def test_mittellinie_pfade():
    aufrufe = _aufrufe({"mittellinie": {"von": [0, 0], "bis": [0, 30]}})
    assert [(a[0], a[2]) for a in aufrufe] == [("lage", f"{P}.mittellinie.von"), ("lage", f"{P}.mittellinie.bis")]


def test_kontur_pfade():
    kontur = {"start": [0, 0], "segmente": [{"linie": [20, 0]}, {"bogen": [20, 10], "mitte": [20, 5]}, {"linie": [0, 0]}]}
    aufrufe = _aufrufe({"kontur": kontur})
    assert [a[2] for a in aufrufe] == [
        f"{P}.kontur.segmente[0].linie", f"{P}.kontur.segmente[1].mitte", f"{P}.kontur.segmente[1].bogen",
        f"{P}.kontur.segmente[2].linie",
    ]


def test_ohne_pfad_laeuft_alles_ueber_das_skriptfeature():
    # Notausgang-Skripte kennen keinen Spec-Pfad der Elemente: Maße tragen den Pfad des Features, art "skript"
    sk = _Aufzeichner(_kontext())
    sk.ctx.knoten = "f2"
    assert modul.feld_pfad(None, "kreis", "durchmesser") is None
    assert sk._eintrag("D1", 5, 1, None, "groesse") == _Mass("D1", 5, 1, "features[1]", "skript")
    assert sk._eintrag("D1", 5, 1, "a.b", "groesse") == _Mass("D1", 5, 1, "a.b", "groesse")


# --- Skizzierer.lagen_festlegen: Pfad je Koordinate -------------------------------------------------------------------


class _Anzeige:
    def __init__(self, name):
        self.name = name

    def GetDimension2(self, i):  # noqa: N802 – Name der SolidWorks-API
        return SimpleNamespace(Name=self.name)


class _LageModell(_Modell):
    def __init__(self):
        self.namen = iter(["D1", "D2"])

    def AddHorizontalDimension2(self, *text):  # noqa: N802 – Name der SolidWorks-API
        return _Anzeige(next(self.namen))

    AddVerticalDimension2 = AddHorizontalDimension2


def _lage_skizzierer(punkte: list[tuple[float, float]], bindbar: bool = True) -> Skizzierer:
    """Skizzen-x folgt u, Skizzen-y läuft gegen v (y = −v)."""
    sk = Skizzierer.__new__(Skizzierer)
    sk.ctx, sk.masse, sk.model, sk.ursprung = _kontext(), [], _LageModell(), object()
    sk.lage_bindbar, sk.x_von, sk.y_von, sk.hilfslinien = bindbar, (0, 1), (1, -1), True
    sk._kennpunkte, sk._ziele, sk._belegt, sk._verrundungen = [], [], set(), []
    sk.skizze = SimpleNamespace(GetSketchPoints2=[_Punkt(*p) for p in punkte])
    sk.zu_skizze = lambda u, v: (u / 1000, -v / 1000)
    sk._text = lambda u, v: (u, v, 0.0)
    return sk


def test_lage_traegt_pfad_mit_koordinatenindex_ein():
    sk = _lage_skizzierer([(0.04, -0.012)])
    sk.kennpunkt((40, 12), ["=B", 12], URSPRUNG_UV, f"{P}.kreis.mitte", "")
    sk.lagen_festlegen()
    assert sk.masse == [
        _Mass("D1", "=B", 1, f"{P}.kreis.mitte[0]", "lage", "ursprung"),
        _Mass("D2", 12, 1, f"{P}.kreis.mitte[1]", "lage", "ursprung"),
    ]


def test_lage_nur_eine_koordinate_und_ohne_pfad():
    sk = _lage_skizzierer([(0.03, -0.012)])
    sk.kennpunkt((30, 12), [30, 12], URSPRUNG_UV, f"{P}.polygon.punkte[1]", "", achsen=(1,))
    sk.lagen_festlegen()
    assert [(m.pfad, m.art) for m in sk.masse] == [(f"{P}.polygon.punkte[1][1]", "lage")]
    sk = _lage_skizzierer([(0.03, -0.012)])
    sk.ctx.knoten = "f1"
    sk.kennpunkt((30, 12), [30, 12], URSPRUNG_UV, None, "", achsen=(0,))
    sk.lagen_festlegen()
    assert [(m.pfad, m.art) for m in sk.masse] == [("features[0]", "skript")]


def test_lage_ohne_deckung_von_skizzen_und_modellursprung_traegt_millimeter_ein():
    sk = _lage_skizzierer([(0.04, -0.008)], bindbar=False)
    sk.kennpunkt((40, 8), ["=B", "=T"], URSPRUNG_UV, f"{P}.kreis.mitte", "")
    sk.lagen_festlegen()
    # Der Maßwert ist der Abstand in der Skizze (hier in mm), nicht der Spec-Ausdruck; vorzeichen gehört zu dieser
    # Skizzenkoordinate (y = −8), nicht zu v
    assert [(m.roh, m.vorzeichen) for m in sk.masse] == [(pytest.approx(40.0), 1), (pytest.approx(-8.0), -1)]


# --- skizziere und positionen_festlegen -----------------------------------------------------------------------------------


class _Skizzenfeature:
    Name = ""


def _skizziere_ohne_sw(monkeypatch, ctx, erzeugt: list):
    class _Skizzierer:
        def __init__(self, ctx_, se, skizze, hilfslinien=True):
            self.masse = [_Mass("D1", "=B", 1, f"{P}.kreis.durchmesser", "groesse"),
                          _Mass("D2", 5, -1, f"{P}.kreis.mitte[0]", "lage")]

        def element(self, element, pfad=None):
            erzeugt.append((element, pfad))

        def kennpunkt(self, punkt_uv, roh_uv, bezug, pfad, gruppe, achsen=(0, 1), ziel=None):
            erzeugt.append((list(roh_uv), pfad))

        def lagen_festlegen(self):
            pass

        def zu_skizze(self, u, v):
            return u, v

    skizze = SimpleNamespace(GetConstrainedStatus=modul.sw.SW_FULLY_CONSTRAINED)
    manager = SimpleNamespace(InsertSketch=lambda neu: None, ActiveSketch=skizze, CreatePoint=lambda x, y, z: object())
    ctx.model = SimpleNamespace(SketchManager=manager)
    ctx.app = object()
    ebenen = []
    monkeypatch.setattr(modul, "Skizzierer", _Skizzierer)
    monkeypatch.setattr(modul, "ebene_aufloesen",
                        lambda ctx_, ebene, pfad=None: ebenen.append(pfad) or Skizzenebene(object(), "vorne", 0.0, (0, 0, 1)))
    monkeypatch.setattr(modul.sw, "letztes_feature", lambda model: _Skizzenfeature())
    monkeypatch.setattr(modul.sw, "einstellung", contextmanager(lambda *a: (yield)))
    monkeypatch.setattr(modul.sw, "ohne_inferenz", contextmanager(lambda *a: (yield)))
    return ebenen


def test_skizziere_reicht_pfade_durch_und_protokolliert_die_masse(monkeypatch):
    ctx, erzeugt = _kontext(), []
    ctx.knoten = "f1"
    ebenen = _skizziere_ohne_sw(monkeypatch, ctx, erzeugt)
    elemente = [{"kreis": {}}, {"rechteck": {}}]
    pfade = ["features[0].skizze.elemente[0]", "features[0].skizze.elemente[1]"]
    feature, _ = modul.skizziere(ctx, "vorne", elemente, "f1_skizze", pfade, "features[0].skizze.ebene")
    assert feature.Name == "f1_skizze"
    assert erzeugt == list(zip(elemente, pfade))
    assert ebenen == ["features[0].skizze.ebene"]
    assert ctx.masse["f1"] == [
        {"name": "D1@f1_skizze", "pfad": f"{P}.kreis.durchmesser", "art": "groesse", "bezug": None, "roh": "=B",
         "vorzeichen": 1, "wert": 40.0},
        {"name": "D2@f1_skizze", "pfad": f"{P}.kreis.mitte[0]", "art": "lage", "bezug": None, "roh": 5, "vorzeichen": -1,
         "wert": 5.0},
    ]


def test_skizziere_ohne_pfade_fuer_skripte(monkeypatch):
    ctx, erzeugt = _kontext(), []
    ctx.knoten = "f2"
    _skizziere_ohne_sw(monkeypatch, ctx, erzeugt)
    modul.skizziere(ctx, "vorne", [{"kreis": {}}], "f2_skizze", None)
    assert erzeugt == [({"kreis": {}}, None)]


def test_positionen_festlegen_gibt_jedem_punkt_seinen_pfad(monkeypatch):
    ctx, erzeugt = _kontext(), []
    ctx.knoten = "f2"
    _skizziere_ohne_sw(monkeypatch, ctx, erzeugt)
    skizze = _Skizzenfeature()
    skizze.Select2 = lambda anhaengen, marke: None
    monkeypatch.setattr(modul, "positionsskizze", lambda feature: skizze)
    modul.positionen_festlegen(ctx, object(), Skizzenebene(object(), "vorne", 0.0, (0, 0, 1)), [[1, 2], ["=B", 4]],
                               "f2_positionen", None, "features[1].positionen")
    assert [pfad for _, pfad in erzeugt] == ["features[1].positionen[0]", "features[1].positionen[1]"]
    assert [m["name"] for m in ctx.masse["f2"]] == ["D1@f2_positionen", "D2@f2_positionen"]
    assert skizze.Name == "f2_positionen"


# --- versetzte Skizzenebene ----------------------------------------------------------------------------------------------


def test_versetzte_ebene_protokolliert_versatz(monkeypatch):
    neue = SimpleNamespace(Name="Ebene1")
    ctx = _kontext()
    ctx.knoten = "f1"
    ctx.model = SimpleNamespace(FeatureManager=SimpleNamespace(InsertRefPlane=lambda *args: neue))
    monkeypatch.setattr(modul.sw, "standardebenen", lambda model: ["vorne", "oben", "rechts"])
    se = modul.ebene_aufloesen(ctx, {"versatz": {"ebene": "oben", "abstand": "=-T"}}, "features[0].skizze.ebene")
    assert se.lage == -8
    assert ctx.masse["f1"] == [{"name": "D1@Ebene1", "pfad": "features[0].skizze.ebene.versatz.abstand", "art": "versatz",
                                "bezug": None, "roh": "=-T", "vorzeichen": -1, "wert": 8.0}]


# --- Handler: Pfade der Feature-Maße ------------------------------------------------------------------------------------


class _Sammler:
    """Ersatz für skizziere: merkt sich die Aufrufe und liefert Skizze und Ebene."""

    def __init__(self):
        self.aufrufe = []

    def __call__(self, ctx, ebene, elemente, name, pfade=None, ebene_pfad=None, hilfslinien=True):
        self.aufrufe.append((name, pfade, ebene_pfad) + (() if hilfslinien else ("ohne hilfslinien",)))
        return SimpleNamespace(Select2=lambda anhaengen, marke: None), Skizzenebene(object(), "oben", 0.0, (0, 1, 0))


def _handler_kontext(features: list[dict], **fm) -> Kontext:
    model = SimpleNamespace(FeatureManager=SimpleNamespace(**fm))
    return Kontext(None, model, {"parameter": {"T": 8, "W": 5}, "features": features}, Path("t.yaml"), 0.1)


def _namen(ctx, fid: str) -> list[tuple]:
    return [(m["name"], m["pfad"], m["art"]) for m in ctx.masse[fid]]


def test_extrusion_traegt_tiefe_und_winkel_mit_pfad_ein(monkeypatch):
    from swki.compiler.handler import extrusion as h

    sammler = _Sammler()
    monkeypatch.setattr(h, "skizziere", sammler)
    feature = SimpleNamespace(Name="")
    f0 = {"id": "f0", "typ": "extrusion"}
    f1 = {"id": "f1", "typ": "extrusion",
          "skizze": {"ebene": "oben", "elemente": [{"kreis": {}}, {"kreis": {}}]},
          "ende": {"typ": "blind", "tiefe": "=T", "formschraege": {"winkel": "=W", "querschnitt": "kleiner"}}}
    ctx = _handler_kontext([f0, f1], FeatureExtrusion3=lambda *args: feature)
    ctx.knoten = "f1"
    h.extrusion(ctx, f1)
    assert sammler.aufrufe == [("f1_skizze", ["features[1].skizze.elemente[0]", "features[1].skizze.elemente[1]"],
                                "features[1].skizze.ebene")]
    assert _namen(ctx, "f1") == [("D1@f1", "features[1].ende.tiefe", "tiefe"),
                                 ("D3@f1", "features[1].ende.formschraege.winkel", "winkel")]


def test_extrusion_traegt_versatz_von_flaeche_als_abstand_ein(monkeypatch):
    from swki.compiler.handler import extrusion as h

    monkeypatch.setattr(h, "skizziere", _Sammler())
    monkeypatch.setattr(h, "loese_flaeche", lambda ctx, anker: SimpleNamespace(objekt=object()))
    f = {"id": "f1", "typ": "schnitt", "skizze": {"ebene": "oben", "elemente": []},
         "ende": {"typ": "versatz_von_flaeche", "flaeche": {"feature": "f0", "flaeche": "+y"}, "abstand": "=T"}}
    ctx = _handler_kontext([f], FeatureCut4=lambda *args: SimpleNamespace(Name=""))
    ctx.knoten = "f1"
    h.extrusion(ctx, f)
    assert _namen(ctx, "f1") == [("D1@f1", "features[0].ende.abstand", "abstand")]


def test_bohrung_ordnet_lage_und_durchmesser_ihre_pfade_zu(monkeypatch):
    from swki.compiler.handler import bohrung as h

    sammler = _Sammler()
    monkeypatch.setattr(h, "skizziere", sammler)
    monkeypatch.setattr(h, "loese_flaeche", lambda ctx, anker: None)
    monkeypatch.setattr(h, "ebene_aus_flaeche", lambda flaeche: Skizzenebene(object(), "oben", 0.0, (0, 1, 0)))
    monkeypatch.setattr(h, "schnitt", lambda *args: SimpleNamespace(Name=""))
    f = {"id": "f2", "typ": "bohrung", "flaeche": {}, "durchmesser": 6, "tiefe": "=T", "positionen": [[1, 2], [3, 4]],
         "senkung": {"durchmesser": 10, "tiefe": 2}}
    ctx = _handler_kontext([{"id": "f1"}, f], FeatureManager=None)
    ctx.knoten = "f2"
    h.bohrung(ctx, f)
    bohr, senk = [a[1] for a in sammler.aufrufe]
    assert bohr == [{"mitte": f"features[1].positionen[{k}]", "durchmesser": "features[1].durchmesser"} for k in range(2)]
    assert senk == [{"mitte": f"features[1].positionen[{k}]", "durchmesser": "features[1].senkung.durchmesser"}
                    for k in range(2)]
    assert _namen(ctx, "f2") == [("D1@f2", "features[1].tiefe", "tiefe"),
                                 ("D1@f2_senkung", "features[1].senkung.tiefe", "tiefe")]


def test_kanten_pfade(monkeypatch):
    from swki.compiler.handler import kanten as h

    monkeypatch.setattr(h, "_waehle_kanten", lambda ctx, f: None)
    ctx = _handler_kontext(
        [{"id": "f1"}, {"id": "f2"}],
        CreateDefinition=lambda art: SimpleNamespace(Initialize=lambda t: None),
        CreateFeature=lambda daten: SimpleNamespace(Name=""),
        InsertFeatureChamfer=lambda *args: SimpleNamespace(Name="", GetFaces=[object()]),
    )
    ctx.knoten = "f1"
    h.verrundung(ctx, {"id": "f1", "radius": "=T"})
    ctx.knoten = "f2"
    h.fase(ctx, {"id": "f2", "abstand": 1, "winkel": "=W"})
    assert _namen(ctx, "f1") == [("D1@f1", "features[0].radius", "radius")]
    assert _namen(ctx, "f2") == [("D1@f2", "features[1].abstand", "abstand"), ("D2@f2", "features[1].winkel", "winkel")]


def test_rotation_pfade(monkeypatch):
    from swki.compiler.handler import rotation as h

    sammler = _Sammler()
    monkeypatch.setattr(h, "skizziere", sammler)
    monkeypatch.setattr(h, "rotiere", lambda model, schnitt, winkel: SimpleNamespace(Name=""))
    f = {"id": "f1", "typ": "rotation", "winkel": "=W",
         "skizze": {"ebene": "vorne", "elemente": [{"mittellinie": {"von": [0, 0], "bis": [0, 10]}}]}}
    ctx = _handler_kontext([f])
    ctx.knoten = "f1"
    h.rotation(ctx, f)
    # Rotationsskizze: ihre Mittellinie wird Achse, der Skizzierer legt keine weiteren Konstruktionslinien an
    assert sammler.aufrufe == [("f1_skizze", ["features[0].skizze.elemente[0]"], "features[0].skizze.ebene",
                                "ohne hilfslinien")]
    assert _namen(ctx, "f1") == [("D1@f1", "features[0].winkel", "winkel")]
