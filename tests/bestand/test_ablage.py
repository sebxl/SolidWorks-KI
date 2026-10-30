import hashlib
import os
import stat
from pathlib import Path

import pytest

from swki.bestand import ablage
from swki.bestand.ablage import (aufnahmen, bestand_ordner, kopiere_original, lade_aufnahme, lauf_kopie, pruefe_format,
                                 pruefe_kopie, schreibe_aufnahme)
from swki.bestand.fehler import (BESTAND_ABWEICHEND, BESTAND_ANDERE_DATEI, BESTAND_FORMAT, BESTAND_NICHT_LESBAR,
                                 BESTAND_UNBEKANNT, BestandFehler)
from swki.cli import SwkiFehler
from swki.konfig import Rechner


@pytest.fixture
def r(tmp_path):
    return Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")


def _datei(ordner: Path, name: str, inhalt: bytes) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    pfad = ordner / name
    pfad.write_bytes(inhalt)
    return pfad


def test_kopie_liest_original_nur_und_ist_schreibgeschuetzt(r, tmp_path):
    original = tmp_path / "Lager deckel.SLDPRT"
    original.write_bytes(b"abc")
    stempel = original.stat().st_mtime_ns
    k = kopiere_original(r, "a1", original)
    assert k["nummer"] == 1 and k["neu"] and k["pfad"].name == "Lager deckel.SLDPRT"
    assert k["pfad"].parent == bestand_ordner(r, "a1", 1)
    assert k["sha256"] == hashlib.sha256(b"abc").hexdigest()
    assert original.stat().st_mtime_ns == stempel and original.read_bytes() == b"abc"
    assert os.access(original, os.W_OK)
    assert not os.access(k["pfad"], os.W_OK)


def test_gleiche_datei_keine_neue_aufnahme(r, tmp_path):
    original = _datei(tmp_path / "kunde", "Deckel.SLDPRT", b"abc")
    erste = kopiere_original(r, "a1", original)
    zweite = kopiere_original(r, "a1", original)
    assert zweite["nummer"] == 1 and not zweite["neu"] and zweite["pfad"] == erste["pfad"]
    assert aufnahmen(r, "a1") == [1]


def test_gleiche_datei_andere_schreibweise_des_namens(r, tmp_path):
    erste = kopiere_original(r, "a1", _datei(tmp_path / "x", "Deckel.SLDPRT", b"abc"))
    zweite = kopiere_original(r, "a1", _datei(tmp_path / "y", "DECKEL.sldprt", b"abc"))
    assert zweite["nummer"] == 1 and not zweite["neu"] and zweite["pfad"] == erste["pfad"]


def test_geaenderte_datei_neue_aufnahme(r, tmp_path):
    original = _datei(tmp_path / "kunde", "Deckel.SLDPRT", b"abc")
    kopiere_original(r, "a1", original)
    original.write_bytes(b"abcd")
    k = kopiere_original(r, "a1", original)
    assert k["nummer"] == 2 and k["neu"] and k["sha256"] == hashlib.sha256(b"abcd").hexdigest()
    assert aufnahmen(r, "a1") == [1, 2]
    assert (bestand_ordner(r, "a1", 1) / "Deckel.SLDPRT").read_bytes() == b"abc"
    # wieder die alte Fassung: die jüngste Aufnahme gilt, also noch einmal neu
    original.write_bytes(b"abc")
    assert kopiere_original(r, "a1", original)["nummer"] == 3


def test_anderes_original_im_auftrag_wird_abgelehnt(r, tmp_path):
    kopiere_original(r, "a1", _datei(tmp_path, "Deckel.SLDPRT", b"abc"))
    with pytest.raises(BestandFehler) as e:
        kopiere_original(r, "a1", _datei(tmp_path, "Flansch.SLDPRT", b"abc"))
    assert e.value.daten["code"] == BESTAND_ANDERE_DATEI
    assert aufnahmen(r, "a1") == [1]


@pytest.mark.parametrize("name", ["Deckel.SLDPRT", "deckel.sldprt"])
def test_endung_grossgeschrieben_geht(r, tmp_path, name):
    assert kopiere_original(r, "a1", _datei(tmp_path, name, b"x"))["neu"]


@pytest.mark.parametrize("name", ["Deckel.step", "Baugruppe.sldasm", "Deckel"])
def test_endung_step_und_baugruppe_gehen_nicht(r, tmp_path, name):
    with pytest.raises(BestandFehler) as e:
        kopiere_original(r, "a1", _datei(tmp_path, name, b"x"))
    assert e.value.daten["code"] == BESTAND_FORMAT
    assert aufnahmen(r, "a1") == []
    with pytest.raises(BestandFehler):
        pruefe_format(Path(name))


def test_original_fehlt(r, tmp_path):
    with pytest.raises(BestandFehler) as e:
        kopiere_original(r, "a1", tmp_path / "weg.SLDPRT")
    assert e.value.daten["code"] == BESTAND_NICHT_LESBAR and isinstance(e.value, SwkiFehler)
    assert aufnahmen(r, "a1") == []


def test_original_gesperrt(r, tmp_path, monkeypatch):
    original = _datei(tmp_path, "Deckel.SLDPRT", b"abc")

    def gesperrt(pfad):
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(ablage, "sha256_datei", gesperrt)
    with pytest.raises(BestandFehler) as e:
        kopiere_original(r, "a1", original)
    assert e.value.daten["code"] == BESTAND_NICHT_LESBAR and e.value.daten["pfad"] == str(original)
    assert aufnahmen(r, "a1") == []


def test_lauf_kopie_hebt_schreibschutz_auf(r, tmp_path):
    k = kopiere_original(r, "a1", _datei(tmp_path, "Deckel.SLDPRT", b"abc"))
    ziel = lauf_kopie(k["pfad"], tmp_path / "arbeit" / "a1" / "lauf-1")
    assert ziel == tmp_path / "arbeit" / "a1" / "lauf-1" / "Deckel.SLDPRT" and ziel.read_bytes() == b"abc"
    assert os.access(ziel, os.W_OK)
    assert not os.access(k["pfad"], os.W_OK)     # die Bestandskopie bleibt geschützt
    ziel.write_bytes(b"geaendert")               # und die Lauf-Kopie lässt sich ändern
    assert k["pfad"].read_bytes() == b"abc"


def test_pruefe_kopie_erkennt_aenderung(r, tmp_path):
    k = kopiere_original(r, "a1", _datei(tmp_path, "Deckel.SLDPRT", b"abc"))
    aufnahme = {"datei": {"sha256": k["sha256"]}}
    pruefe_kopie(aufnahme, k["pfad"])
    os.chmod(k["pfad"], stat.S_IWRITE)
    k["pfad"].write_bytes(b"xyz")
    with pytest.raises(BestandFehler) as e:
        pruefe_kopie(aufnahme, k["pfad"])
    assert e.value.daten["code"] == BESTAND_ABWEICHEND
    assert e.value.daten["aufnahme"] == hashlib.sha256(b"abc").hexdigest()
    assert e.value.daten["vorhanden"] == hashlib.sha256(b"xyz").hexdigest()


def test_aufnahme_schreiben_und_laden(r):
    daten = {"version": 1, "datei": {"name": "Größe.SLDPRT", "sha256": "ab"}, "aktiv": "Standard"}
    pfad = schreibe_aufnahme(r, "a1", 1, daten)
    assert pfad == bestand_ordner(r, "a1", 1) / "bestand.json"
    assert lade_aufnahme(r, "a1", 1) == daten
    assert "Größe" in pfad.read_text(encoding="utf-8")


def test_unbekannte_aufnahme(r):
    with pytest.raises(BestandFehler) as e:
        lade_aufnahme(r, "a1", 3)
    assert e.value.daten["code"] == BESTAND_UNBEKANNT


def test_aufnahmen_ignoriert_fremde_ordner(r, tmp_path):
    for name in ("bestand-2", "bestand-10", "bestand-x", "lauf-1", "bestand-1"):
        (r.arbeitsordner / "a1" / name).mkdir(parents=True)
    (r.arbeitsordner / "a1" / "bestand-5").write_text("datei", encoding="utf-8")
    assert aufnahmen(r, "a1") == [1, 2, 10]
    assert aufnahmen(r, "gibt-es-nicht") == []
