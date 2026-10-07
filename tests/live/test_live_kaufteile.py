"""Live-Tests der Kaufteil-Aufnahme am Muster-Getriebemotor (Spec 3c §6, §11): Import, Diagnose, Bau und Prüfung,
Negativfälle Gegenprobe und Körperzahl. SolidWorks muss laufen; gespeichert wird nur im Arbeitsordner."""

import shutil
from pathlib import Path

import pytest

from swki.aenderungen import sha256_datei
from swki.compiler import sw
from swki.compiler.topologie import koerper
from swki.kaufteile import aufnahme, sw_kaufteil
from swki.konfig import PROJEKT, lade_rechner
from swki.verbindung import verbinde
from tests.kaufteile.beispiel import kopie

pytestmark = pytest.mark.sw
STEP = PROJEKT / "tests" / "referenz" / "motorhalter" / "muster" / "gm42-10.step"
AUFTRAG = "LIVE-KAUFTEIL"


@pytest.fixture
def ordner():
    pfad = lade_rechner().arbeitsordner / AUFTRAG
    yield pfad
    shutil.rmtree(pfad, ignore_errors=True)


def _eintrag(volumen: float | None = None) -> dict:
    spec = kopie()
    spec["original"]["sha256"] = sha256_datei(STEP)
    if volumen is None:
        del spec["pruefung"]["volumen"]
    else:
        spec["pruefung"]["volumen"]["soll"] = volumen
    return spec


def test_import_ohne_interconnect_und_optionen_zurueck():
    app = verbinde(lade_rechner().sw_jahr)
    vorher = sw_kaufteil.optionen(app)
    model = sw_kaufteil.importiere(app, STEP)
    try:
        assert len(koerper(model)) == 2 and sw_kaufteil.flaechenkoerper(model) == 0
        assert sw_kaufteil.interconnect_features(model) == []
        assert all(n == 0 for n in sw_kaufteil.koerperfehler(model).values())
    finally:
        sw.schliesse(app, model)
    assert sw_kaufteil.optionen(app) == vorher


def test_untersuche_muster(ordner):
    d = aufnahme.untersuche(STEP, ordner / "untersuchung")
    assert (d["koerper"], d["flaechenkoerper"], d["interconnect"]) == (2, 0, [])
    assert {10.0, 40.0, 56.0, 4.2} <= {z["durchmesser"] for z in d["zylinder"]}
    box = d["huellquader"]
    assert [round(box[i + 3] - box[i], 3) for i in range(3)] == [60.0, 107.0, 60.0]
    assert d["volumen"] > 0 and all(Path(p).stat().st_size > 0 for p in d["bilder"].values())


def test_baue_und_pruefe_muster(ordner):
    volumen = aufnahme.untersuche(STEP, ordner / "untersuchung")["volumen"]
    e = aufnahme.baue_und_pruefe(_eintrag(volumen), STEP, ordner / "lauf", mit_bildern=True)
    assert e["fehler"] is None and e["maengel"] == [], e["maengel"]
    assert e["gewinde_modell"] == {"flansch": {"modell": "kernloch", "durchmesser": 4.2}} and Path(e["teil"]).is_file()
    assert all(Path(p).stat().st_size > 0 for p in e["bilder"].values())


@pytest.mark.parametrize(("aenderung", "erwartet"), [
    ("durchmesser", {"einbau:EINBAU_ACHSE"}),
    ("koerper", {"koerper"}),
])
def test_negativfaelle(ordner, aenderung, erwartet):
    spec = _eintrag()
    if aenderung == "durchmesser":
        spec["einbau"]["EINBAU_ACHSE"]["zylinder"]["durchmesser"] = 12
    else:
        spec["koerper"] = 1
    e = aufnahme.baue_und_pruefe(spec, STEP, ordner / "lauf")
    assert {m["pruefung"] for m in e["maengel"]} == erwartet, e["maengel"]
