"""Kaufteile ohne Volumenkörper (reine Flächenmodelle, z. B. Nanotec-STEP mit OPEN_SHELL): Attrappen statt SolidWorks.
SolidWorks liefert dann CreateMassProperty2 = None; Diagnose, Messung und Massenüberschreibung dürfen nicht abstürzen."""

from swki.kaufteile import sw_kaufteil
from swki.kaufteile.bewertung import bewerte_kaufteil
from tests.kaufteile.beispiel import EINTRAG, kopie

SW_SOLID_BODY, SW_SHEET_BODY = 0, 1


class _Fehlerliste:
    def __init__(self, n: int):
        self.Count = n


class _Koerper:
    def __init__(self, fehler: int = 0):
        self.Check3 = _Fehlerliste(fehler) if fehler else None

    def GetFaces(self):
        return ()


class _Extension:
    GetWhatsWrongCount = 0

    def __init__(self, mp=None):
        self.mp = mp

    @property
    def CreateMassProperty2(self):
        return self.mp


class _Flaechenmodell:
    """Teil mit nur Flächenkörpern: keine Volumenkörper, CreateMassProperty2 ist None."""

    def __init__(self, sheets: list[_Koerper]):
        self.sheets = sheets
        self.Extension = _Extension(None)
        self.ausgewaehlt = []
        self.FirstFeature = None
        self.EditRebuild3 = True

    def GetBodies2(self, art, sichtbar):
        return tuple(self.sheets) if art == SW_SHEET_BODY else ()

    def GetPartBox(self, genau):
        return (-0.02, -0.02, -0.015, 0.02, 0.036, 0.048)

    def ClearSelection2(self, alle):
        self.ausgewaehlt = []


def test_diagnose_flaechenmodell_ohne_absturz():
    model = _Flaechenmodell([_Koerper(), _Koerper(6)])
    d = sw_kaufteil.diagnose(model, [])
    assert d["koerper"] == 0 and d["flaechenkoerper"] == 2
    assert d["volumen"] is None and d["schwerpunkt"] is None
    assert d["huellquader"] == [-20.0, -20.0, -15.0, 20.0, 36.0, 48.0]
    assert d["koerperfehler"] == {"F1": 0, "F2": 6}


def test_koerperfehler_zaehlt_flaechenkoerper_mit():
    model = _Flaechenmodell([_Koerper(1)])
    assert sw_kaufteil.koerperfehler(model) == {"F1": 1}


def test_setze_masse_ohne_volumenkoerper_tut_nichts():
    model = _Flaechenmodell([_Koerper()])
    sw_kaufteil.setze_masse(model, 0.5)   # keine Ausnahme


def test_messe_flaechenmodell_liefert_werte_und_mangel_import(monkeypatch):
    monkeypatch.setattr(sw_kaufteil, "rebuild_fehler", lambda model: [])
    monkeypatch.setattr(sw_kaufteil, "lies_eigenschaften", lambda model: {})
    monkeypatch.setattr(sw_kaufteil, "byref_str", lambda: type("S", (), {"value": ""})())
    model = _Flaechenmodell([_Koerper(), _Koerper()])
    model.GetMaterialPropertyName2 = lambda *a: ""
    spec = kopie(EINTRAG)
    spec["pruefung"] = {}
    spec["einbau"] = {}
    spec.pop("gewinde", None)
    m = sw_kaufteil.messe(model, spec, [], {}, {}, 0.05)
    assert (m.koerper, m.flaechenkoerper, m.volumen, m.masse_kg, m.masse_ueberschrieben) == (0, 2, 0.0, 0.0, False)
    b = bewerte_kaufteil(spec, m)
    assert not b["bestanden"]
    importe = next(e for e in b["pruefungen"] if e["id"] == "import")
    assert importe["ok"] is False and importe["ist"]["flaechenkoerper"] == 2
    assert {"import", "koerper", "masse"} <= {x["pruefung"] for x in b["maengel"]}
