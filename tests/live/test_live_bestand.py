"""Live-Tests der Bestandsaufnahme am Musterteil (Spec Bestandsdateien §5, §12). SolidWorks muss laufen; das Muster dient als
Original und wird nur gelesen, geöffnet und gespeichert wird nur unter dem Arbeitsordner."""

import shutil
import stat
from pathlib import Path

import pytest

from swki.aenderungen import sha256_datei
from swki.bestand import befehle
from swki.bestand.ablage import bestand_ordner, lade_aufnahme
from swki.bestand.sw_bestand import bstr_array, lies_bestand
from swki.compiler import sw
from swki.konfig import PROJEKT, lade_rechner
from swki.pruefung.messen import oeffne
from swki.verbindung import verbinde

pytestmark = pytest.mark.sw
MUSTER = PROJEKT / "tests" / "referenz" / "bestand" / "muster" / "Lagerdeckel.SLDPRT"
AUFTRAG = "LIVE-BESTAND"
SW_UNTERDRUECKEN, SW_BENANNT = 0, 3  # swFeatureSuppressionAction_e, swInConfigurationOpts_e


def _aufraeumen(pfad: Path) -> None:
    for p in pfad.rglob("*"):
        if p.is_file():
            p.chmod(stat.S_IWRITE)  # Bestandskopien sind schreibgeschützt
    shutil.rmtree(pfad, ignore_errors=True)


@pytest.fixture
def auftrag():
    pfad = lade_rechner().arbeitsordner / AUFTRAG
    _aufraeumen(pfad)
    yield AUFTRAG
    _aufraeumen(pfad)


def test_aufnahme_musterteil(auftrag):
    r = lade_rechner()
    sha = sha256_datei(MUSTER)
    aus = befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(r, auftrag, 1)
    assert sha256_datei(MUSTER) == sha == a["datei"]["sha256"]
    assert a["datei"]["version_aelter"] is False and a["sw_jahr"] == r.sw_jahr
    assert (a["konfigurationen"], a["aktiv"]) == (["Standard", "Variante B"], "Standard") and a["tabelle"] is False
    assert a["einheitensystem"] == 5 and a["material"].startswith("1.0038") and a["externe_referenzen"] == []
    assert a["eigenschaften"]["datei"]["Benennung"] == "Lagerdeckel" and a["eigenschaften"]["konfiguration"]["Variante B"]

    assert a["variablen"] == {"L": 100.0}
    assert {g["links"]: g["global"] for g in a["gleichungen"]} == {"L": True, "D1@Skizze1": False}

    masse = {m["name"]: m for m in a["masse"]}
    assert len(masse) == len(a["masse"])  # Dubletten aus Skizze und Feature zusammengelegt
    m = masse["D1@Skizze1"]
    assert (m["zustand"], m["quelle"], m["werte"]) == ("gesteuert", {"art": "variable", "name": "L"},
                                                       {"Standard": 100.0, "Variante B": 100.0})
    assert masse["D5@Skizze2"]["zustand"] == "getrieben"
    assert masse["D2@Skizze3"]["zustand"] == "treibend" and len(masse["D2@Skizze3"]["punkte"]) == 2
    assert {masse["Bohrung_D@Skizze3"]["gruppe"], masse["Bohrung_D@Skizze4"]["gruppe"]} == {"Bohrung_D"}
    assert masse["Bohrung_D@Skizze3"]["zustand"] == "treibend" and masse["Bohrung_D@Skizze4"]["werte"]["Standard"] == 8.0
    assert masse["D2@Fase1"]["einheit"] == "Grad" and masse["D2@Fase1"]["werte"]["Standard"] == 45.0

    # Abweichung vom Brief nach S18b: Maße unterdrückter Features sind lesbar, `werte` bleibt eine Zahl
    features = {f["name"]: f for f in a["features"]}
    assert features["Fase1"]["unterdrueckt"] == {"Standard": False, "Variante B": True}
    assert masse["D1@Fase1"]["werte"] == {"Standard": 2.0, "Variante B": 2.0}
    assert features["Skizze1"]["kinder"] == ["Aufsatz-Linear austragen1"] and "Skizze1" in features["Aufsatz-Linear austragen1"]["eltern"]
    assert not any(f["typ"].endswith("Folder") for f in a["features"])
    assert a["reihenfolge"]["Standard"] == a["reihenfolge"]["Variante B"] == [f["name"] for f in a["features"]]

    assert a["skizzen"]["Skizze5"] == 2 and a["skizzen"]["Skizze1"] == 3 and aus["skizzen_offen"] == {"Skizze5": 2}
    assert a["neuaufbau"] == []
    assert a["geometrie"]["Standard"]["volumen"] == pytest.approx(106239.381, abs=0.01)
    assert a["geometrie"]["Variante B"]["volumen"] == pytest.approx(106439.381, abs=0.01)
    assert a["geometrie"]["Standard"]["koerper"] == 1 and a["geometrie"]["Standard"]["box"][3] == pytest.approx(50.0)

    ordner = bestand_ordner(r, auftrag, 1)
    kopie = ordner / MUSTER.name
    assert sha256_datei(kopie) == sha and not kopie.stat().st_mode & stat.S_IWRITE
    assert {p.name for p in (ordner / "bilder").iterdir()} == {"iso.png", "vorne.png", "oben.png", "rechts.png"}

    z = befehle.zeige(auftrag, "D2@Skizze3", None)
    assert Path(z["bild"]).stat().st_size > 0
    f = befehle.zeige(auftrag, None, "Schnitt-Linear austragen2")
    assert Path(f["bild"]).stat().st_size > 0
    assert sha256_datei(kopie) == sha

    assert befehle.aufnehmen(MUSTER, auftrag)["neu"] is False


def test_aktive_konfiguration_bleibt_unterdrueckte_skizze_stoert_nicht(auftrag):
    """Plan Review Focus 4 und 5: Variante B aktiv, Fase dort unterdrückt, dazu ein Schnitt samt Skizze im aktiven Stand."""
    app = verbinde(lade_rechner().sw_jahr)
    ordner = lade_rechner().arbeitsordner / auftrag
    ordner.mkdir(parents=True)
    kopie = shutil.copy2(MUSTER, ordner / MUSTER.name)
    model = oeffne(app, Path(kopie), sichtbar=False, nur_lesen=True)
    try:
        assert model.IsOpenedReadOnly
        model.ShowConfiguration2("Variante B")
        schnitt = "Schnitt-Linear austragen2"
        assert model.FeatureByName(schnitt).SetSuppression2(SW_UNTERDRUECKEN, SW_BENANNT, bstr_array(["Variante B"]))
        model.EditRebuild3
        d = lies_bestand(app, model)
        assert model.ConfigurationManager.ActiveConfiguration.Name == "Variante B" and d["aktiv"] == "Variante B"
        assert d["konfigurationen"] == ["Variante B", "Standard"]
        features = {f["name"]: f for f in d["features"]}
        assert features[schnitt]["unterdrueckt"] == {"Variante B": True, "Standard": False}
        assert d["geometrie"]["Variante B"]["volumen"] > d["geometrie"]["Standard"]["volumen"]
    finally:
        sw.schliesse(app, model)
    assert sha256_datei(Path(kopie)) == sha256_datei(MUSTER)
