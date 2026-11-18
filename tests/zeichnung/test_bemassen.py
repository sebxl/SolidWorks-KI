"""Zeichnungsableitung Z1.3 Stufe 2 (Plan 2026-11-17 Stufe 2, Task 5): Bemaßungsablauf mit Fake-COM ohne SolidWorks –
einfügen, Kandidaten, Zuordnung, weitere Ansicht, Duplikate und Nicht-Plan-Maße löschen."""

from swki.zeichnung import bemassen as b
from swki.zeichnung.massplan import Mass


class _Dim:
    def __init__(self, name):
        self.FullName = f"{name}@Teil.Part"


class _Ann:
    def __init__(self, dd, drw):
        self.dd, self.drw = dd, drw

    def Select2(self, append, mark):
        self.drw.auswahl.append(self.dd)
        return True


class _DD:
    def __init__(self, name, view, drw):
        self.name, self.view, self.drw = name, view, drw

    def GetDimension2(self, i):
        return _Dim(self.name)

    def GetAnnotation(self):
        return _Ann(self, self.drw)


class _View:
    def __init__(self, name):
        self.GetName2, self.masse = name, []

    def GetDisplayDimensions(self):
        return tuple(self.masse)


class _Drw:
    """Fügt je Ansicht die Modellmaße ein, die `sichtbar[rolle]` nennt (wie SolidWorks: in jede passende Ansicht)."""

    def __init__(self, views: dict, sichtbar: dict):
        self.views, self.sichtbar, self.auswahl, self.geloescht = views, sichtbar, [], 0
        self.aktiv = None
        drw = self
        self.Extension = type("E", (), {"SelectByID2": lambda *a: True,
                                        "DeleteSelection2": lambda s, opt: drw.EditDelete()})()

    def ActivateView(self, name):
        self.aktiv = name
        return True

    def ClearSelection2(self, alle):
        self.auswahl = []

    def InsertModelAnnotations4(self, option, typen, alle, dup, versteckt, platz, a, r):
        ziele = self.views.items() if alle else [(k, v) for k, v in self.views.items() if v.GetName2 == self.aktiv]
        for rolle, v in ziele:
            for name in self.sichtbar.get(rolle, []):
                v.masse.append(_DD(name, v, self))
        return ()

    def EditDelete(self):
        for dd in self.auswahl:
            dd.view.masse.remove(dd)
            self.geloescht += 1
        self.auswahl = []


def _plan(*namen):
    return [Mass(n, "modell", "laenge", 1.0, "f1", name=n) for n in namen]


def test_kurzname():
    assert b.kurzname(_DD("D3@t1_skizze", None, None)) == "D3@t1_skizze"


def test_duplikate_und_fremde_masse_geloescht():
    views = {"haupt": _View("V1"), "drauf": _View("V2"), "seite": _View("V3")}
    drw = _Drw(views, {"haupt": ["A", "B", "X"], "drauf": ["A", "C"], "seite": ["C"]})
    erg = b.bemasse(drw, views, _plan("A", "B", "C"), ["haupt", "drauf", "seite"], max_je=12,
                    weitere=[], neue_ansicht=None)
    namen = {r: sorted(b.kurzname(d) for d in v.masse) for r, v in views.items()}
    assert sorted(sum(namen.values(), [])) == ["A", "B", "C"]  # je Plan-Maß genau eines, X gelöscht
    assert namen["haupt"][:2] == ["A", "B"] or "A" in namen["drauf"]
    assert erg.meldungen == [] and erg.gesetzt == 3


def test_volle_ansicht_fuehrt_zu_weiterer_ansicht():
    views = {"haupt": _View("V1")}
    sichtbar = {"haupt": ["A", "B", "C"], "unter": ["C"]}
    drw = _Drw(views, sichtbar)

    def neue_ansicht(rolle):
        views[rolle] = _View(f"N-{rolle}")
        return views[rolle]

    erg = b.bemasse(drw, views, _plan("A", "B", "C"), ["haupt"], max_je=2, weitere=["unter"], neue_ansicht=neue_ansicht)
    assert "unter" in views and [b.kurzname(d) for d in views["unter"].masse] == ["C"]
    assert len(views["haupt"].masse) == 2 and erg.meldungen == []


def test_mass_ohne_ansicht_gemeldet():
    views = {"haupt": _View("V1")}
    erg = b.bemasse(_Drw(views, {"haupt": ["A"]}), views, _plan("A", "Z"), ["haupt"], max_je=12, weitere=[],
                    neue_ansicht=None)
    assert any("Z" in m for m in erg.meldungen) and erg.gesetzt == 1


def test_neue_masse_gehen_in_die_hauptansicht():
    views = {"haupt": _View("V1"), "seite": _View("V2")}
    plan = [Mass("f1:d50", "neu", "durchmesser", 50.0, "f1", geometrie={"radius": 25})]
    erg = b.bemasse(_Drw(views, {}), views, plan, ["haupt", "seite"], max_je=12, weitere=[], neue_ansicht=None)
    assert erg.neu == {"haupt": ["f1:d50"]}


def test_neue_masse_ueber_obergrenze_gemeldet():
    """Review I2: neue Drehteil-Maße belegen die Hauptansicht vor; mehr als die Obergrenze wird gemeldet."""
    views = {"haupt": _View("V1"), "seite": _View("V2")}
    plan = [Mass(f"f1:a{i}", "neu", "laenge", float(i), "f1", geometrie={"von": 0, "bis": i}) for i in range(1, 4)]
    erg = b.bemasse(_Drw(views, {}), views, plan, ["haupt", "seite"], max_je=2, weitere=[], neue_ansicht=None)
    assert any(m.startswith("ANSICHT_VOLL") for m in erg.meldungen)


def test_kandidaten_nach_blickachse_gefiltert():
    """Ein Skizzenmaß (flach, Achse 1) nur in Ansichten mit Blickachse 1; ein Tiefenmaß (quer) nur in anderen."""
    views = {"haupt": _View("V1"), "drauf": _View("V2")}
    plan = [Mass("S", "modell", "lage", 1.0, "f1", name="S", achse=1, modus="flach"),
            Mass("T", "modell", "tiefe", 1.0, "f1", name="T", achse=1, modus="quer")]
    erg = b.bemasse(_Drw(views, {"haupt": ["S", "T"], "drauf": ["S", "T"]}), views, plan, ["haupt", "drauf"], max_je=12,
                    weitere=[], neue_ansicht=None, blickachsen={"haupt": 1, "drauf": 2})
    assert erg.je_ansicht == {"haupt": ["S"], "drauf": ["T"]}
