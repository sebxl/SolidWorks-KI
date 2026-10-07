"""Durchmesserprüfung (pruefung.durchmesser_pruefen) ohne SolidWorks: die Zylinderfläche wird über alle Features eines
Spezifikationsschritts gesucht, auch über die Senkung einer Bohrung (`<id>_senkung`, zweites Feature)."""

from types import SimpleNamespace

from swki.compiler.anker import Flaeche
from swki.compiler.kontext import FeatureErgebnis
from swki.pruefung import messen


def _zyl(radius):
    return Flaeche("zylinder", (0, 50, 0), achse=(1, 0, 0), radius=radius)


class _Ctx:
    tol_mm = 0.01

    def __init__(self, ergebnis):
        self.ergebnisse = {"f3": ergebnis}
        self.spec = {"pruefung": {"durchmesser_pruefen": [
            {"was": "Zentrierbohrung", "feature": "f3", "nahe": [7.5, 70, 0], "soll": 40}]}}

    def ergebnis(self, fid):
        return self.ergebnisse[fid]

    def wert(self, v):
        return v


def _messe(monkeypatch, nahe):
    bohrung, senkung = object(), object()
    monkeypatch.setattr(messen, "flaechen", lambda f: [_zyl(10)] if f is bohrung else [_zyl(20)])
    ctx = _Ctx(FeatureErgebnis([bohrung, senkung]))
    ctx.spec["pruefung"]["durchmesser_pruefen"][0]["nahe"] = nahe
    return messen.durchmesser(ctx, ctx.spec)["Zentrierbohrung"]


def test_punkt_auf_der_senkung_zweites_feature(monkeypatch):
    assert _messe(monkeypatch, [7.5, 70, 0])["durchmesser"] == 40.0


def test_punkt_auf_der_bohrung_erstes_feature(monkeypatch):
    assert _messe(monkeypatch, [7.5, 60, 0])["durchmesser"] == 20.0


class _Modell:
    def __init__(self, namen):
        self.namen = {n: SimpleNamespace(Name=n) for n in namen}

    def FeatureByName(self, name):  # noqa: N802 – COM-Name
        return self.namen.get(name)


def test_kontext_aus_datei_nimmt_die_senkung_der_bohrung_mit():
    spec = {"features": [
        {"id": "f2", "typ": "extrusion"},
        {"id": "f3", "typ": "bohrung", "senkung": {"durchmesser": 40, "tiefe": 5}},
        {"id": "f4", "typ": "bohrung"}]}
    ctx = messen.kontext_aus_datei(None, _Modell(["f2", "f3", "f3_senkung", "f4"]), spec, None, 0.01, {"knoten": []})
    assert [f.Name for f in ctx.ergebnis("f3").features] == ["f3", "f3_senkung"]
    assert [f.Name for f in ctx.ergebnis("f2").features] == ["f2"]
    assert [f.Name for f in ctx.ergebnis("f4").features] == ["f4"]
