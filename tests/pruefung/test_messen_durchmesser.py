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
