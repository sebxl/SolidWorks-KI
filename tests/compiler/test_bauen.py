"""swki bauen ohne SolidWorks: Laufnummer und Sperre belegter Läufe (verbinde wird nie erreicht bzw. abgefangen)."""

import json
from pathlib import Path

import pytest

from swki.auftrag import lauf_datei, lauf_ordner
from swki.cli import SwkiFehler
from swki.compiler import bauen as bauen_modul
from swki.konfig import Rechner


class _KeinSolidWorks(Exception):
    pass


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    spec_pfad = tmp_path / "auftraege" / "A" / "platte.yaml"
    spec_pfad.parent.mkdir(parents=True)
    spec_pfad.write_text("name: platte\n", encoding="utf-8")
    aufrufe = {"verbinde": 0, "protokoll_lauf": None}

    def verbinde(jahr):
        aufrufe["verbinde"] += 1
        raise _KeinSolidWorks

    def protokoll(auftrag, spec_name, lauf, sw_jahr):
        aufrufe["protokoll_lauf"] = lauf
        return object()

    monkeypatch.setattr(bauen_modul, "lade_spec", lambda pfad: {"name": "platte"})
    monkeypatch.setattr(bauen_modul, "pruefe_freigabe", lambda pfad, spec: None)
    monkeypatch.setattr(bauen_modul, "lade_rechner", lambda: r)
    monkeypatch.setattr(bauen_modul, "lade_standard", lambda: {"namensschema": {"datei": "{auftrag}_{name}"}})
    monkeypatch.setattr(bauen_modul, "verbinde", verbinde)
    monkeypatch.setattr(bauen_modul, "Protokoll", protokoll)
    return r, spec_pfad, aufrufe


def test_belegter_lauf_wird_vor_solidworks_verweigert(umgebung):
    r, spec_pfad, aufrufe = umgebung
    lauf_ordner(r, "A", 2).mkdir(parents=True)
    with pytest.raises(SwkiFehler, match="Lauf 2 von A existiert schon"):
        bauen_modul.bauen(spec_pfad, lauf=2)
    assert aufrufe["verbinde"] == 0


def test_lauf_mit_nur_pruefdatei_ist_belegt(umgebung):
    r, spec_pfad, aufrufe = umgebung
    datei = lauf_datei(spec_pfad, 1, "pruefbericht")
    datei.parent.mkdir(parents=True)
    datei.write_text("{}", encoding="utf-8")
    with pytest.raises(SwkiFehler, match="Lauf 1 von A existiert schon"):
        bauen_modul.bauen(spec_pfad, lauf=1)
    assert aufrufe["verbinde"] == 0


def test_automatische_laufnummer_ueberspringt_alte_pruefdateien(umgebung):
    """Arbeitsordner aufgeräumt, aber Prüfdateien von Lauf 1 liegen noch im Auftragsordner: es wird Lauf 2 gebaut."""
    r, spec_pfad, aufrufe = umgebung
    for art in ("protokoll", "pruefbericht", "pruefer"):
        datei = lauf_datei(spec_pfad, 1, art)
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_text("{}", encoding="utf-8")
    with pytest.raises(_KeinSolidWorks):
        bauen_modul.bauen(spec_pfad)
    assert aufrufe["protokoll_lauf"] == 2


def _gebauter_lauf(r, spec_pfad, inhalt: bytes) -> Path:
    from swki.aenderungen import pruefsummen

    ordner = lauf_ordner(r, "A", 1)
    ordner.mkdir(parents=True)
    datei = ordner / "A_platte.sldprt"
    datei.write_bytes(b"gebaut")
    protokoll = lauf_datei(spec_pfad, 1, "protokoll")
    protokoll.parent.mkdir(parents=True, exist_ok=True)
    protokoll.write_text(json.dumps({"status": "ok", "sha256": pruefsummen(ordner, [datei])}), encoding="utf-8")
    datei.write_bytes(inhalt)
    return datei


def test_manuelle_aenderung_wird_vor_solidworks_verweigert(umgebung):
    r, spec_pfad, aufrufe = umgebung
    _gebauter_lauf(r, spec_pfad, b"von Hand geaendert")
    with pytest.raises(SwkiFehler) as e:
        bauen_modul.bauen(spec_pfad)
    assert e.value.daten["code"] == "MANUELL_GEAENDERT" and aufrufe["verbinde"] == 0


def test_verwerfen_baut_trotzdem(umgebung):
    r, spec_pfad, aufrufe = umgebung
    _gebauter_lauf(r, spec_pfad, b"von Hand geaendert")
    with pytest.raises(_KeinSolidWorks):
        bauen_modul.bauen(spec_pfad, verwerfen=True)
    assert aufrufe["protokoll_lauf"] == 2


def _freigabe_zeitpunkt(spec_pfad, zeitpunkt: str):
    from swki.spec.freigabe import freigabe_pfad

    freigabe_pfad(spec_pfad).write_text(
        json.dumps({spec_pfad.name: {"pruefsumme": "x", "freigegeben": zeitpunkt, "kopie_sha256": "x"}}), encoding="utf-8")


def _gebauter_lauf_von(r, spec_pfad, gestartet: str) -> None:
    _gebauter_lauf(r, spec_pfad, b"von Hand geaendert")
    protokoll = lauf_datei(spec_pfad, 1, "protokoll")
    daten = json.loads(protokoll.read_text(encoding="utf-8"))
    protokoll.write_text(json.dumps({**daten, "gestartet": gestartet}), encoding="utf-8")


def test_uebernommen_baut_nach_neuer_freigabe(umgebung):
    r, spec_pfad, aufrufe = umgebung
    _gebauter_lauf_von(r, spec_pfad, "2026-10-03T10:00:00")
    _freigabe_zeitpunkt(spec_pfad, "2026-10-03T12:00:00")
    with pytest.raises(_KeinSolidWorks):
        bauen_modul.bauen(spec_pfad, uebernommen=True)
    assert aufrufe["protokoll_lauf"] == 2


def test_uebernommen_ohne_neue_freigabe_wird_vor_solidworks_verweigert(umgebung):
    r, spec_pfad, aufrufe = umgebung
    _gebauter_lauf_von(r, spec_pfad, "2026-10-03T10:00:00")
    _freigabe_zeitpunkt(spec_pfad, "2026-10-03T09:00:00")
    with pytest.raises(SwkiFehler, match="Freigabe ist nicht neuer als Lauf 1") as e:
        bauen_modul.bauen(spec_pfad, uebernommen=True)
    assert e.value.daten["code"] == "UEBERNAHME_OHNE_NEUE_FREIGABE" and aufrufe["verbinde"] == 0


def test_cli_verwerfen_und_uebernommen_schliessen_sich_aus(umgebung, capsys):
    from swki.cli import main

    _, spec_pfad, aufrufe = umgebung
    assert main(["bauen", str(spec_pfad), "--verwerfen", "--uebernommen"]) == 1
    assert "not allowed with argument" in json.loads(capsys.readouterr().out)["fehler"]
    assert aufrufe["verbinde"] == 0
