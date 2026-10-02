from pathlib import Path

import pytest

from swki import konfig
from swki.konfig import KonfigFehler, Rechner, lade_rechner, lade_standard, rechner_als_dict, schreibe_rechner


def _rechner(tmp_path):
    return Rechner(
        sw_jahr=2025,
        installationsordner=Path(r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS"),
        vorlage_teil=Path(r"C:\ProgramData\SolidWorks\SOLIDWORKS 2025\templates\Teil.prtdot"),
        vorlage_baugruppe=None,
        materialdatenbank=None,
        arbeitsordner=tmp_path / "arbeit",
    )


def test_rechner_fehlt_nennt_befehl(tmp_path):
    with pytest.raises(KonfigFehler, match="rechner init"):
        lade_rechner(tmp_path / "rechner.yaml")


def test_rechner_rundreise(tmp_path):
    pfad = tmp_path / "rechner.yaml"
    r = _rechner(tmp_path)
    schreibe_rechner(r, pfad)
    assert lade_rechner(pfad) == r


def test_rechner_als_dict_hat_strings(tmp_path):
    d = rechner_als_dict(_rechner(tmp_path))
    assert d["sw_jahr"] == 2025
    assert isinstance(d["vorlage_teil"], str)
    assert d["vorlage_baugruppe"] is None


def test_standard_projektdatei():
    daten = lade_standard()
    assert daten["max_nachbesserungen"] == 3
    assert daten["api"]["max_jahr_compiler"] == 2025
    assert daten["bohrungsnorm"] == "ISO"


def test_swki_home_aus_umgebung(swki_home):
    assert konfig.swki_home() == swki_home


def test_normteilbibliothek_optional(tmp_path):
    pfad = tmp_path / "rechner.yaml"
    grund = "sw_jahr: 2025\ninstallationsordner: C:/SW\nvorlage_teil: C:/t.prtdot\narbeitsordner: C:/arbeit\n"
    pfad.write_text(grund, encoding="utf-8")
    assert lade_rechner(pfad).normteilbibliothek is None
    pfad.write_text(grund + "normteilbibliothek: C:/bib\n", encoding="utf-8")
    assert lade_rechner(pfad).normteilbibliothek == Path("C:/bib")
