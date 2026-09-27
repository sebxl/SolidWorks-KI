from dataclasses import dataclass, field

import pytest

from swki.compiler.ablauf import baue_features
from swki.compiler.fehler import REBUILD_FEHLER, UNBEKANNTER_TYP, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.protokoll import Protokoll


@dataclass
class _Feature:
    Name: str


@dataclass
class _Ctx:
    spec: dict
    ergebnisse: dict = field(default_factory=dict)


def _ok(ctx, f):
    return FeatureErgebnis([_Feature(f["id"])])


def _kaputt(ctx, f):
    raise BauFehler("REFERENZ_NICHT_GEFUNDEN", "keine Fläche +y", schritt="flaeche")


def _spec(*typen):
    return {"features": [{"id": f"f{i}", "typ": t} for i, t in enumerate(typen, start=1)]}


def _protokoll():
    return Protokoll("A", "a.yaml", 1, 2025)


def test_alle_knoten_ok():
    ctx, p, geprueft = _Ctx(_spec("extrusion", "fase")), _protokoll(), []
    fehler = baue_features(ctx, p, {"extrusion": _ok, "fase": _ok}, lambda c: geprueft.append(len(c.ergebnisse)))
    assert fehler is None
    assert [(k.id, k.status, k.sw_name) for k in p.knoten] == [("f1", "ok", "f1"), ("f2", "ok", "f2")]
    assert geprueft == [1, 2]  # nach jedem Knoten geprüft
    assert set(ctx.ergebnisse) == {"f1", "f2"}


def test_erster_fehler_stoppt_und_ueberspringt_rest():
    ctx, p = _Ctx(_spec("extrusion", "bohrung", "fase")), _protokoll()
    fehler = baue_features(ctx, p, {"extrusion": _ok, "bohrung": _kaputt, "fase": _ok}, lambda c: None)
    assert isinstance(fehler, BauFehler) and fehler.code == "REFERENZ_NICHT_GEFUNDEN"
    assert [k.status for k in p.knoten] == ["ok", "fehler", "uebersprungen"]
    assert p.knoten[1].fehler["schritt"] == "flaeche"


def test_unbekannter_typ():
    p = _protokoll()
    fehler = baue_features(_Ctx(_spec("gewinde")), p, {}, lambda c: None)
    assert fehler.code == UNBEKANNTER_TYP and p.knoten[0].status == "fehler"


def test_rebuildfehler_nach_knoten():
    def rebuild(ctx):
        raise BauFehler(REBUILD_FEHLER, "f1: Code 71", schritt="rebuild")

    p = _protokoll()
    fehler = baue_features(_Ctx(_spec("schnitt", "fase")), p, {"schnitt": _ok, "fase": _ok}, rebuild)
    assert fehler.code == REBUILD_FEHLER
    assert [k.status for k in p.knoten] == ["fehler", "uebersprungen"]


def test_com_fehler_wird_protokolliert():
    def com(ctx, f):
        raise OSError("Mitglied nicht gefunden")

    p = _protokoll()
    fehler = baue_features(_Ctx(_spec("extrusion")), p, {"extrusion": com}, lambda c: None)
    assert isinstance(fehler, OSError)
    assert p.knoten[0].fehler["code"] == "OSError"


@pytest.mark.parametrize("namen", [["f1"], ["f1", "f1_senkung"]])
def test_sw_name_mehrerer_features(namen):
    assert FeatureErgebnis([_Feature(n) for n in namen]).sw_name == ", ".join(namen)
