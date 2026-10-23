from pathlib import Path
from types import SimpleNamespace

import pytest

from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import Kontext


class _Gleichungen:
    def __init__(self, rueckgabe: int = 0):
        self.texte, self.rueckgabe = [], rueckgabe

    def Add2(self, index, text, loesen):
        self.texte.append(text)
        return self.rueckgabe


def _ctx(rueckgabe: int = 0, gleichungen: bool = True) -> Kontext:
    model = SimpleNamespace(GetEquationMgr=_Gleichungen(rueckgabe))
    return Kontext(None, model, {"parameter": {"L": 100}}, Path("x.yaml"), 0.1, gleichungen=gleichungen)


def test_feste_zahl_wird_nicht_gebunden():
    ctx = _ctx()
    ctx.mass("D1@f1", 20, "features[0].ende.tiefe", "tiefe")
    assert ctx.model.GetEquationMgr.texte == []


def test_ausdruck_wird_als_gleichung_gebunden():
    ctx = _ctx()
    ctx.mass("D1@f1", "=L", "features[0].ende.tiefe", "tiefe")
    assert ctx.model.GetEquationMgr.texte == ['"D1@f1" = "L"']


def test_vorzeichen_negiert_den_ausdruck():
    ctx = _ctx()
    ctx.mass("D2@f1_skizze", "=L/2-20", "features[0].skizze.elemente[0].rechteck.mitte[0]", "lage", -1)
    assert ctx.model.GetEquationMgr.texte == ['"D2@f1_skizze" = -(("L" / 2) - 20)']


def test_abgelehnte_gleichung_ist_baufehler():
    with pytest.raises(BauFehler) as e:
        _ctx(rueckgabe=-1).mass("D1@f1", "=L", "features[0].ende.tiefe", "tiefe")
    assert "D1@f1" in str(e.value)


def test_mass_ohne_gleichungen_legt_nichts_an():
    ctx = _ctx(gleichungen=False)
    ctx.mass("D1@f1", "=L", "features[0].ende.tiefe", "tiefe")
    ctx.mass("D2@f1_skizze", "=L/2-20", "features[0].skizze.elemente[0].rechteck.mitte[0]", "lage", -1)
    assert ctx.model.GetEquationMgr.texte == []


def _ctx_mit_spec(**kw) -> Kontext:
    ctx = _ctx(**kw)
    ctx.spec = {"parameter": {"T": 8, "L": 100}, "features": [{"id": "f1"}, {"id": "f2"}]}
    return ctx


def test_mass_traegt_ein_ohne_gleichung():
    ctx = _ctx_mit_spec(gleichungen=False)
    ctx.knoten = "f2"
    ctx.mass("D1@f2", "=T", "features[1].ende.tiefe", "tiefe")
    assert ctx.masse["f2"] == [{"name": "D1@f2", "pfad": "features[1].ende.tiefe", "art": "tiefe", "bezug": None,
                                "roh": "=T", "vorzeichen": 1, "wert": 8.0}]
    assert ctx.model.GetEquationMgr.texte == []


def test_mass_traegt_feste_zahl_und_betrag_ein():
    ctx = _ctx_mit_spec()
    ctx.knoten = "f1"
    ctx.mass("D2@f1_skizze", "=-L/2", "features[0].skizze.elemente[0].kreis.mitte[0]", "lage", -1)
    ctx.mass("D3@f1_skizze", 12, "features[0].skizze.elemente[0].kreis.durchmesser", "groesse")
    assert [(m["roh"], m["vorzeichen"], m["wert"]) for m in ctx.masse["f1"]] == [("=-L/2", -1, 50.0), (12, 1, 12.0)]


def test_mass_sammelt_je_knoten():
    ctx = _ctx_mit_spec(gleichungen=False)
    ctx.knoten = "f1"
    ctx.mass("D1@f1", 5, "features[0].ende.tiefe", "tiefe")
    ctx.knoten = "f2"
    ctx.mass("D1@f2", 6, "features[1].radius", "radius")
    assert {k: [m["name"] for m in v] for k, v in ctx.masse.items()} == {"f1": ["D1@f1"], "f2": ["D1@f2"]}


def test_mass_mit_gleichungen_bindet_ausdruck():
    ctx = _ctx_mit_spec(gleichungen=True)
    ctx.knoten = "f1"
    ctx.mass("D1@f1", "=L", "features[0].ende.tiefe", "tiefe")
    ctx.mass("D2@f1_skizze", "=L/2-20", "features[0].skizze.elemente[0].rechteck.mitte[0]", "lage", -1)
    assert ctx.model.GetEquationMgr.texte == ['"D1@f1" = "L"', '"D2@f1_skizze" = -(("L" / 2) - 20)']
    assert len(ctx.masse["f1"]) == 2


@pytest.mark.parametrize("bezug", ["ursprung", None, "mitte"])
def test_mass_mit_bezug_ursprung_bindet(bezug):
    # mitte: Lage zum Ursprung oder Paarabstand (2 × Koordinate) lassen sich aus der Spec ausdrücken (Ruling 7)
    ctx = _ctx_mit_spec(gleichungen=True)
    ctx.knoten = "f1"
    ctx.mass("D1@f1", "=L", "features[0].ende.tiefe", "lage", bezug=bezug)
    assert ctx.model.GetEquationMgr.texte == ['"D1@f1" = "L"']


@pytest.mark.parametrize("bezug", ["-rand", "+rand", {"flaeche": {"feature": "f1", "flaeche": "+x"}}])
def test_mass_mit_bezug_rand_bindet_nie(bezug):
    ctx = _ctx_mit_spec(gleichungen=True)
    ctx.knoten = "f1"
    ctx.mass("D1@f1", "=L", "features[0].ende.tiefe", "lage", bezug=bezug)
    assert ctx.model.GetEquationMgr.texte == []
    assert ctx.masse["f1"][0]["bezug"] == bezug


def test_mass_mit_eigenem_wert_traegt_ihn_ein_und_bindet_nie():
    # Rand-/Paarmaß oder Rechteckseite: roh ist die Spec-Koordinate, der Maßwert ein anderer Betrag
    ctx = _ctx_mit_spec(gleichungen=True)
    ctx.knoten = "f1"
    ctx.mass("D1@f1_skizze", "=L/2-10", "features[0].skizze.elemente[0].rechteck.mitte[0]", "lage", bezug="ursprung",
             wert=35.0)
    assert ctx.model.GetEquationMgr.texte == []
    assert (ctx.masse["f1"][0]["roh"], ctx.masse["f1"][0]["wert"]) == ("=L/2-10", 35.0)


def test_pfad_ist_position_im_feature_baum():
    ctx = _ctx_mit_spec()
    assert (ctx.pfad("f1"), ctx.pfad("f2")) == ("features[0]", "features[1]")
    with pytest.raises(KeyError):
        ctx.pfad("f9")
