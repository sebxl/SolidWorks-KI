"""Lage, Körper und Gelenke der Referenz-Baugruppen ohne SolidWorks (Spec C1 §2, §4.1): gegen die eigenen
masse_pruefen und bewegungen.erwartet der Specs – die Werte, gegen die SolidWorks in der Live-Suite besteht."""

import math
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("build123d")

from swki.schnellbau.baugruppe import Baugruppe  # noqa: E402
from swki.schnellbau.teil import lade  # noqa: E402
from swki.spec.ausdruck import auswerten  # noqa: E402

REFERENZ = Path(__file__).parents[1] / "referenz"
BAUGRUPPEN = sorted(p for p in REFERENZ.glob("*/*.yaml") if lade(p).get("art") == "baugruppe")


@pytest.fixture(scope="module", params=BAUGRUPPEN, ids=lambda p: p.stem)
def bg(request):
    return Baugruppe(request.param)


def _eigen(bg, seite: dict) -> bool:
    return seite["komponente"] in bg.komp


def test_masse_pruefen_der_spec(bg):
    geprueft = 0
    for m in bg.spec.get("pruefung", {}).get("masse_pruefen", []):
        if "punkt" in m["von"] or "punkt" in m["zu"] or not (_eigen(bg, m["von"]) and _eigen(bg, m["zu"])):
            continue
        assert bg.abstand(m["von"], m["zu"]) == pytest.approx(auswerten(m["soll"], bg.p), abs=1e-6), m["was"]
        geprueft += 1
    if bg.spec["name"].lower() in ("linearschlitten", "zahnstangentrieb"):
        assert geprueft >= 1


def _kette(bg, kid: str) -> list:
    """Gelenke vom Körper der Komponente bis zur Welt."""
    gelenke = {g.komponente: g for g in bg.gelenke}
    out, koerper = [], bg.komp[kid].koerper
    while koerper is not None:
        g = gelenke[koerper]
        out.append(g)
        koerper = g.eltern
    return out


def test_endlagen_wie_bewegungen_erwartet(bg):
    for b in bg.spec.get("bewegungen", []):
        grenze = b["grenze"]
        for e in b["erwartet"]["endlagen"]:
            kette = _kette(bg, e["komponente"])
            if "verschiebung" in e:
                soll = np.array([auswerten(c, bg.p) for c in e["verschiebung"]])
                g = next(g for g in kette if g.id == grenze)
                assert g.typ == "schub"
                assert np.array(g.achse) * g.bereich[1] == pytest.approx(soll)
            else:
                d = e["drehung"]
                g = next(g for g in kette if g.typ == "dreh")
                achse = np.array([auswerten(c, bg.p) for c in d["achse"]], float)
                assert np.array(g.achse) == pytest.approx(achse / np.linalg.norm(achse))
                if g.bereich is not None and b["grenze"] == next((m["id"] for m in bg.spec["verknuepfungen"]
                                                                  if m["typ"] == "grenze_winkel"
                                                                  and m["a"]["komponente"] == g.komponente), None):
                    assert g.bereich[1] == pytest.approx(math.radians(auswerten(d["winkel"], bg.p)))


def test_linearschlitten_koerper():
    bg = Baugruppe(REFERENZ / "schlitten" / "linearschlitten.yaml")
    g = {x.id: x for x in bg.gelenke}
    assert (g["g1"].typ, g["g1"].komponente, g["g1"].eltern) == ("schub", "schlitten", None)
    assert (g["s1"].typ, g["s1"].komponente, g["s1"].eltern) == ("dreh", "hebel", "schlitten")
    assert bg.komp["leiste_links"].koerper is None and bg.komp["leiste_rechts"].koerper is None
    # die Drehachse liegt in der Bolzenbohrung des Schlittens
    bohrung = bg.welt(bg.seite({"komponente": "schlitten", "feature": "f2", "instanz": 1, "achse": True}))
    assert np.array(g["s1"].punkt)[[0, 2]] == pytest.approx(np.array(bohrung.punkt)[[0, 2]])


def test_zahnstangentrieb_kopplungen_gemeldet_zahnstange_am_schlitten():
    bg = Baugruppe(REFERENZ / "zahnstangentrieb" / "zahnstangentrieb.yaml")
    assert bg.komp["zahnstange"].koerper == "schlitten"
    assert {x.komponente for x in bg.gelenke if x.typ == "dreh"} == {"ritzelwelle", "antriebswelle"}
    assert any("k1" in m and "Kopplung" in m for m in bg.meldungen)
