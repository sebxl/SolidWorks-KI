"""Spike S19 ohne SolidWorks: Das Skript läuft nur an Kopien unter `<arbeitsordner>/S19/`, nie unter `AP68-Pruefstation`, nur an einem
leeren SolidWorks, und jede Pflichtfrage aus den Berichten der Tasks 8 bis 11 steht in ihrer Zeile."""

import ast
import importlib
import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from spikes import s19_baugruppe as s19

QUELLE = Path(s19.__file__).read_text(encoding="utf-8")
ANZAHL = {"T8": 26, "T9": 31, "T10": 16, "T11": 14}  # Pflichtfragen je Bericht, T11 zusätzlich die vier aus der Korrekturrunde


def test_pfad_unter_s19_geht(tmp_path):
    ziel = tmp_path / "S19" / "c" / "kopie" / "Hubeinheit.SLDASM"
    assert s19.pruefe_pfad(ziel, tmp_path / "S19") == ziel.resolve()


@pytest.mark.parametrize("pfad", ["anders/Hubeinheit.SLDASM", "S19x/Hubeinheit.SLDASM", "S19/../anders/Hubeinheit.SLDASM"])
def test_pfad_ausserhalb_bricht_ab(tmp_path, pfad):
    with pytest.raises(s19.Sperre, match="S19"):
        s19.pruefe_pfad(tmp_path / pfad, tmp_path / "S19")


@pytest.mark.parametrize("name", ["AP68-Pruefstation", "ap68-pruefstation", "AP68-Pruefstation-Rev1"])
def test_ap68_bricht_ab_auch_unter_s19(tmp_path, name):
    with pytest.raises(s19.Sperre, match="AP68"):
        s19.pruefe_pfad(tmp_path / "S19" / name / "lauf-30" / "A.SLDASM", tmp_path / "S19")


@pytest.mark.parametrize("name", ["AP68-Pruefstation", "AP68-Pruefstation-Rev1"])
def test_quelle_aus_ap68_bricht_ab(tmp_path, name):
    with pytest.raises(s19.Sperre, match="AP68"):
        s19.pruefe_quelle(tmp_path / name / "lauf-30")


def test_andere_quelle_geht(tmp_path):
    assert s19.pruefe_quelle(tmp_path / "LIVE-S19-SCHLITTEN" / "lauf-1") == (tmp_path / "LIVE-S19-SCHLITTEN" / "lauf-1").resolve()


@pytest.mark.parametrize("name", ["S19x/A.SLDASM", "S19/AP68-Pruefstation/lauf-30/A.SLDASM"])
def test_oeffne_ruft_opendoc_nie_fuer_einen_gesperrten_pfad(tmp_path, monkeypatch, name):
    monkeypatch.setattr(s19, "s19_ordner", lambda: tmp_path / "S19")

    def nie(*_):
        raise AssertionError("OpenDoc6 gerufen")

    with pytest.raises(s19.Sperre):
        s19.oeffne(SimpleNamespace(OpenDoc6=nie, DocumentVisible=nie), tmp_path / name)


def test_es_gibt_genau_einen_opendoc():
    code = re.sub(r'""".*?"""', "", QUELLE, flags=re.S)
    assert code.count(".OpenDoc6(") == 1 and "def oeffne(" in code and "sw_neustart" not in code


def test_frisch_loescht_nur_unter_s19(tmp_path, monkeypatch):
    monkeypatch.setattr(s19, "s19_ordner", lambda: tmp_path / "S19")
    fremd = tmp_path / "fremd"
    fremd.mkdir()
    (fremd / "A.SLDPRT").write_bytes(b"x")
    with pytest.raises(s19.Sperre):
        s19.frisch("../fremd")
    assert (fremd / "A.SLDPRT").read_bytes() == b"x"
    assert s19.frisch("c/kopie").is_dir()


def test_kopie_nur_unter_s19_und_nie_aus_ap68(tmp_path, monkeypatch):
    monkeypatch.setattr(s19, "s19_ordner", lambda: tmp_path / "S19")
    with pytest.raises(s19.Sperre, match="S19"):
        s19.kopiere_stand(tmp_path / "muster", tmp_path / "anderswo")
    with pytest.raises(s19.Sperre, match="AP68"):
        s19.kopiere_stand(tmp_path / "AP68-Pruefstation" / "lauf-30", tmp_path / "S19" / "c")


class Dokument:
    def __init__(self, pfad: str):
        self.GetPathName, self.GetTitle = pfad, Path(pfad).name


@pytest.mark.parametrize("offen", [None, ()])
def test_leeres_solidworks_geht(offen):
    s19.pruefe_leer(SimpleNamespace(GetDocuments=offen))


def test_offenes_dokument_bricht_ab_und_nennt_es():
    app = SimpleNamespace(GetDocuments=(Dokument("D:/Kunde/lauf-30/A.SLDASM"),))
    with pytest.raises(s19.Sperre, match="A.SLDASM"):
        s19.pruefe_leer(app)


def test_jede_frage_gehoert_zu_einer_zeile():
    assert {z for z, _ in s19.FRAGEN.values()} == set("abcdef") | {"v"}
    for vorsilbe, anzahl in ANZAHL.items():
        for n in range(1, anzahl + 1):
            assert f"{vorsilbe}.{n}" in s19.FRAGEN, f"{vorsilbe}.{n}"
    assert all(f"T11.K{n}" in s19.FRAGEN for n in range(1, 5))


def _fragen_je_funktion() -> dict[str, set[str]]:
    """Top-Level-Funktion → Nummern ihrer `lauf.frage(...)`-Aufrufe."""
    gefunden: dict[str, set[str]] = {}
    for knoten in ast.parse(QUELLE).body:
        if isinstance(knoten, ast.FunctionDef):
            namen = {k.args[0].value for k in ast.walk(knoten)
                     if isinstance(k, ast.Call) and isinstance(k.func, ast.Attribute) and k.func.attr == "frage"
                     and k.args and isinstance(k.args[0], ast.Constant)}
            gefunden[knoten.name] = namen
    return gefunden


def test_jede_frage_wird_in_ihrer_zeile_gestellt():
    je_funktion = _fragen_je_funktion()
    for nummer, (zeile, _) in s19.FRAGEN.items():
        orte = [f for f, namen in je_funktion.items() if nummer in namen]
        assert orte, f"{nummer} wird nirgends gestellt"
        assert all(f == f"zeile_{zeile}" or f.startswith(f"{zeile}_") for f in orte), (nummer, zeile, orte)


def test_alle_gestellten_fragen_stehen_im_katalog():
    gestellt = set().union(*_fragen_je_funktion().values())
    assert gestellt <= set(s19.FRAGEN), gestellt - set(s19.FRAGEN)


def test_reihenfolge_nach_risiko():
    assert s19.REIHENFOLGE[:2] == ("c", "b") and set(s19.REIHENFOLGE) == set(s19.ZEILEN) and sorted(s19.ZEIT) == sorted(s19.ZEILEN)


def test_jede_zeile_prueft_vorher_ob_solidworks_leer_ist(monkeypatch, tmp_path):
    """`main` fragt vor der Zeile; ein offenes Dokument lässt die Zeile gar nicht erst laufen."""
    gelaufen = []
    app = SimpleNamespace(GetDocuments=(Dokument("C:/x/Fremd.SLDPRT"),))
    monkeypatch.setattr(s19, "verbinde", lambda jahr: app)
    monkeypatch.setattr(s19, "rechner", lambda: SimpleNamespace(sw_jahr=2025))
    monkeypatch.setitem(s19.ZEILEN, "c", lambda a: gelaufen.append(a))
    with pytest.raises(s19.Sperre):
        s19.main(["c"])
    assert gelaufen == []


def test_import_verbindet_nicht(monkeypatch):
    def nie(_):
        raise AssertionError("verbinde beim Import")

    monkeypatch.setattr("swki.verbindung.verbinde", nie)
    importlib.reload(s19)
    importlib.reload(s19)


def test_lauf_schreibt_nach_jedem_schritt_und_eine_kaputte_frage_stoppt_nichts(monkeypatch, tmp_path):
    monkeypatch.setattr(s19, "ERGEBNIS", tmp_path)
    monkeypatch.setattr(s19, "privat_mb", lambda pid: 123.0)
    lauf = s19.Lauf(SimpleNamespace(GetProcessID=7), "c")

    def kaputt():
        raise RuntimeError("gibt es nicht")

    lauf.frage("T8.9", kaputt)
    lauf.frage("T8.9", {"pfad": "x"}, fall="zweiter")
    lauf["schritt"] = {"wert": 1}
    lauf.halt("Auflösung weicht ab")
    d = json.loads((tmp_path / "s19_c.json").read_text(encoding="utf-8"))
    antworten = d["fragen"]["T8.9"]["antworten"]
    assert "RuntimeError: gibt es nicht" in antworten[0]["wert"]["fehler"] and antworten[1] == {"fall": "zweiter", "wert": {"pfad": "x"}}
    assert d["schritt"] == {"wert": 1} and d["halt"] == ["Auflösung weicht ab"]
    assert d["start_mb"] == d["ende_mb"] == 123 and "sekunden" in d


def test_unbeantwortete_fragen_stehen_im_ergebnis(monkeypatch, tmp_path):
    monkeypatch.setattr(s19, "ERGEBNIS", tmp_path)
    monkeypatch.setattr(s19, "privat_mb", lambda pid: 1.0)
    lauf = s19.Lauf(SimpleNamespace(GetProcessID=7), "b")
    lauf.frage("T8.6", "ja")
    lauf.schliesse()
    d = json.loads((tmp_path / "s19_b.json").read_text(encoding="utf-8"))
    assert "T8.6" not in d["unbeantwortet"] and "T8.7" in d["unbeantwortet"]


def test_warnungen_werden_benannt():
    assert s19.warnbits(1 | 32) == ["id_abweichung", "neuaufbau_noetig"]
    assert s19.warnbits(0) == []


def test_keine_jahreszahl_und_kein_kundenpfad_im_skript():
    code = re.sub(r'""".*?"""', "", QUELLE, flags=re.S)
    assert not re.search(r"20[12]\d", code)
    assert "Kunde" not in code
