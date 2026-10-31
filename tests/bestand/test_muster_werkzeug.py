"""Muster je SolidWorks-Jahr (`werkzeuge.bestand_muster`): SolidWorks öffnet keine neueren Dateien und stuft ältere hoch, die Dateien im
Git gelten also nur für ihr Jahr."""

import json
from pathlib import Path

import pytest

from swki.konfig import PROJEKT, Rechner
from werkzeuge.bestand_muster import DATEIEN, MusterFehlt, abweichungen, muster_ordner

REFERENZ = PROJEKT / "tests" / "referenz" / "bestand"
JAHR_IM_GIT = json.loads((REFERENZ / "bestand.json").read_text(encoding="utf-8"))["sw_jahr"]


def rechner(tmp_path, jahr: int) -> Rechner:
    return Rechner(jahr, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path)


def gut() -> dict:
    return {"Standard": {"neuaufbau": True, "whats_wrong": 0, "volumen": 106239.38},
            "Variante B": {"neuaufbau": True, "whats_wrong": 0, "volumen": 106439.38},
            "oeffnen_baugruppe": {"fehler": 0, "warnungen": 0},
            "baugruppe": {"neuaufbau": True, "whats_wrong": 0, "komponenten": [("Lagerdeckel-1", "a"), ("gm42-10-1", "b")]}}


def test_jahr_der_dateien_im_git_nimmt_das_repo(tmp_path):
    assert muster_ordner(rechner(tmp_path, JAHR_IM_GIT)) == REFERENZ / "muster"


@pytest.mark.parametrize("jahr", [JAHR_IM_GIT - 1, JAHR_IM_GIT + 1])
def test_anderes_jahr_ohne_erzeugte_dateien_nennt_das_werkzeug(tmp_path, jahr):
    with pytest.raises(MusterFehlt, match="werkzeuge.bestand_muster"):
        muster_ordner(rechner(tmp_path, jahr))


def test_anderes_jahr_nimmt_die_erzeugten_dateien(tmp_path):
    jahr = JAHR_IM_GIT + 1
    ordner = tmp_path / "BESTAND-MUSTER" / str(jahr)
    ordner.mkdir(parents=True)
    for name in DATEIEN:
        (ordner / name).write_bytes(b"x")
    assert muster_ordner(rechner(tmp_path, jahr)) == ordner


def test_unvollstaendig_erzeugt_zaehlt_als_fehlend(tmp_path):
    jahr = JAHR_IM_GIT + 1
    ordner = tmp_path / "BESTAND-MUSTER" / str(jahr)
    ordner.mkdir(parents=True)
    (ordner / DATEIEN[0]).write_bytes(b"x")
    with pytest.raises(MusterFehlt, match=DATEIEN[1]):
        muster_ordner(rechner(tmp_path, jahr))


def test_ein_gutes_muster_hat_keine_abweichung():
    assert abweichungen(gut()) == []


@pytest.mark.parametrize("schluessel, wert, nennt", [
    ("Standard", {"neuaufbau": True, "whats_wrong": 0, "volumen": 106239.5}, "Standard"),
    ("Variante B", {"neuaufbau": False, "whats_wrong": 0, "volumen": 106439.38}, "Variante B"),
    ("Standard", {"neuaufbau": True, "whats_wrong": 1, "volumen": 106239.38}, "Standard"),
    ("oeffnen_baugruppe", {"fehler": 1, "warnungen": 0}, "Baugruppe"),
    ("baugruppe", {"neuaufbau": True, "whats_wrong": 0, "komponenten": [("Lagerdeckel-1", "a")]}, "Baugruppe"),
])
def test_abweichungen_werden_benannt(schluessel, wert, nennt):
    n = gut()
    n[schluessel] = wert
    assert any(nennt in a for a in abweichungen(n))


def test_fehlende_konfiguration_ist_eine_abweichung():
    """Eine Vorlage mit anderem Konfigurationsnamen ergäbe keine `Standard`; die Soll-Volumina prüfen dann nichts."""
    n = gut()
    del n["Standard"]
    assert any("Standard" in a for a in abweichungen(n))
