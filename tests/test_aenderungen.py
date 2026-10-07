import json
from pathlib import Path

import pytest
import yaml

from swki import aenderungen
from swki.aenderungen import (
    MANUELL_GEAENDERT, UEBERNAHME_OHNE_NEUE_FREIGABE, AenderungFehler, abweichungen, letzter_gebauter_lauf,
    parameter_differenz, pruefe_unveraendert, pruefsummen, sha256_datei, vermerke_befund,
)
from swki.auftrag import lauf_datei, lauf_ordner
from swki.cli import SwkiFehler
from swki.compiler.protokoll import Protokoll
from swki.konfig import Rechner
from swki.spec.freigabe import freigeben
from tests.spec.beispiel import GUELTIG


@pytest.fixture
def umgebung(tmp_path):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit")
    spec_pfad = tmp_path / "auftraege" / "A" / "platte.yaml"
    spec_pfad.parent.mkdir(parents=True)
    spec_pfad.write_text(yaml.safe_dump(GUELTIG, allow_unicode=True), encoding="utf-8")
    return r, spec_pfad


def _lauf(r, spec_pfad, n: int, status: str = "ok", inhalt: bytes | None = b"teil", mit_summen: bool = True,
          gestartet: str | None = None) -> Path:
    ordner = lauf_ordner(r, "A", n)
    ordner.mkdir(parents=True)
    datei = ordner / "A_Platte_1.sldprt"
    summen = {}
    if inhalt is not None:
        datei.write_bytes(inhalt)
        summen = pruefsummen(ordner, [datei])
    protokoll = {"status": status, **({"sha256": summen} if mit_summen else {}),
                 **({"gestartet": gestartet} if gestartet else {})}
    ziel = lauf_datei(spec_pfad, n, "protokoll")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps(protokoll), encoding="utf-8")
    return datei


def test_sha256_datei(tmp_path):
    (tmp_path / "x").write_bytes(b"abc")
    assert sha256_datei(tmp_path / "x") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_pruefsummen_relativ(tmp_path):
    (tmp_path / "bilder").mkdir()
    (tmp_path / "bilder" / "iso.png").write_bytes(b"1")
    (tmp_path / "a.sldprt").write_bytes(b"2")
    summen = pruefsummen(tmp_path, [tmp_path / "a.sldprt", tmp_path / "bilder" / "iso.png", tmp_path / "fehlt.step"])
    assert set(summen) == {"a.sldprt", "bilder/iso.png"}


def test_letzter_gebauter_lauf(umgebung):
    r, spec_pfad = umgebung
    _lauf(r, spec_pfad, 1)
    _lauf(r, spec_pfad, 2, status="fehler")
    assert letzter_gebauter_lauf(spec_pfad)[0] == 1
    _lauf(r, spec_pfad, 3, mit_summen=False)          # vor Stufe 3b gebaut
    assert letzter_gebauter_lauf(spec_pfad) is None


def test_abweichungen(tmp_path):
    (tmp_path / "a").write_bytes(b"1")
    (tmp_path / "b").write_bytes(b"2")
    soll = pruefsummen(tmp_path, [tmp_path / "a", tmp_path / "b"])
    (tmp_path / "a").write_bytes(b"geaendert")
    (tmp_path / "b").unlink()
    assert abweichungen(tmp_path, soll) == {"geaendert": ["a"], "fehlend": ["b"]}


def test_geaenderter_lauf_wird_verweigert(umgebung):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    assert pruefe_unveraendert(r, "A", spec_pfad) is None
    datei.write_bytes(b"von Hand geaendert")
    with pytest.raises(AenderungFehler) as e:
        pruefe_unveraendert(r, "A", spec_pfad)
    assert e.value.daten["code"] == MANUELL_GEAENDERT and e.value.daten["lauf"] == 1
    assert e.value.daten["geaendert"] == ["A_Platte_1.sldprt"] and "--verwerfen" in str(e.value)
    assert pruefe_unveraendert(r, "A", spec_pfad, verwerfen=True)["geaendert"] == ["A_Platte_1.sldprt"]


def _geaenderter_lauf(umgebung, freigabe: str, gestartet: str | None = "2026-10-03T10:00:00") -> Path:
    r, spec_pfad = umgebung
    freigeben(spec_pfad, GUELTIG, zeitpunkt=freigabe)
    datei = _lauf(r, spec_pfad, 1, gestartet=gestartet)
    datei.write_bytes(b"von Hand geaendert")
    return datei


def test_uebernommen_mit_neuerer_freigabe_baut_trotz_aenderung(umgebung):
    r, spec_pfad = umgebung
    _geaenderter_lauf(umgebung, freigabe="2026-10-03T12:00:00")
    b = pruefe_unveraendert(r, "A", spec_pfad, uebernommen=True)
    assert b["lauf"] == 1 and b["geaendert"] == ["A_Platte_1.sldprt"] and b["fehlend"] == []
    protokoll = Protokoll("A", spec_pfad.name, 2, 2025)
    vermerke_befund(protokoll, b, verwerfen=False)
    assert protokoll.uebernommen == b and protokoll.verworfen is None
    vermerke_befund(protokoll, b, verwerfen=True)
    assert protokoll.verworfen == b and protokoll.uebernommen is None


def test_uebernommen_mit_fehlender_datei_und_neuerer_freigabe(umgebung):
    r, spec_pfad = umgebung
    _geaenderter_lauf(umgebung, freigabe="2026-10-03T12:00:00").unlink()
    assert pruefe_unveraendert(r, "A", spec_pfad, uebernommen=True)["fehlend"] == ["A_Platte_1.sldprt"]


def test_uebernommen_mit_aelterer_freigabe_wird_verweigert(umgebung):
    r, spec_pfad = umgebung
    _geaenderter_lauf(umgebung, freigabe="2026-10-03T09:00:00")
    with pytest.raises(AenderungFehler) as e:
        pruefe_unveraendert(r, "A", spec_pfad, uebernommen=True)
    assert e.value.daten["code"] == UEBERNAHME_OHNE_NEUE_FREIGABE and e.value.daten["lauf"] == 1
    assert e.value.daten["geaendert"] == ["A_Platte_1.sldprt"]
    assert "Freigabe ist nicht neuer als Lauf 1" in str(e.value) and "swki freigeben" in str(e.value)


def test_uebernommen_mit_gleichzeitiger_freigabe_wird_verweigert(umgebung):
    """Nur eine Freigabe NACH dem Lauf zählt (strikt neuer)."""
    r, spec_pfad = umgebung
    _geaenderter_lauf(umgebung, freigabe="2026-10-03T10:00:00")
    with pytest.raises(AenderungFehler) as e:
        pruefe_unveraendert(r, "A", spec_pfad, uebernommen=True)
    assert e.value.daten["code"] == UEBERNAHME_OHNE_NEUE_FREIGABE


def test_uebernommen_ohne_zeitstempel_im_protokoll_nutzt_aenderungszeit(umgebung):
    r, spec_pfad = umgebung
    _geaenderter_lauf(umgebung, freigabe="2000-01-01T00:00:00", gestartet=None)   # Protokolldatei ist jünger
    with pytest.raises(AenderungFehler) as e:
        pruefe_unveraendert(r, "A", spec_pfad, uebernommen=True)
    assert e.value.daten["code"] == UEBERNAHME_OHNE_NEUE_FREIGABE
    freigeben(spec_pfad, GUELTIG, zeitpunkt="2999-01-01T00:00:00")
    assert pruefe_unveraendert(r, "A", spec_pfad, uebernommen=True)["lauf"] == 1


def test_verwerfen_und_uebernommen_zugleich_ist_fehler(umgebung):
    r, spec_pfad = umgebung
    _geaenderter_lauf(umgebung, freigabe="2026-10-03T12:00:00")
    with pytest.raises(SwkiFehler, match="--verwerfen und --uebernommen"):
        pruefe_unveraendert(r, "A", spec_pfad, verwerfen=True, uebernommen=True)


def test_uebernommen_ohne_abweichung_ist_wirkungslos(umgebung):
    """Kein Befund: weder eine Freigabe wird gelesen noch ein Vermerk gemacht."""
    r, spec_pfad = umgebung
    _lauf(r, spec_pfad, 1, gestartet="2026-10-03T10:00:00")      # unverändert, es gibt nicht einmal eine Freigabe
    assert pruefe_unveraendert(r, "A", spec_pfad, uebernommen=True) is None
    protokoll = Protokoll("A", spec_pfad.name, 2, 2025)
    vermerke_befund(protokoll, None, verwerfen=False)
    assert protokoll.uebernommen is None and protokoll.verworfen is None


def test_aufgeraeumter_lauf_wird_nicht_verweigert(umgebung):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    for p in datei.parent.iterdir():
        p.unlink()
    datei.parent.rmdir()
    assert pruefe_unveraendert(r, "A", spec_pfad) is None


def test_parameter_differenz():
    assert parameter_differenz({"L": 100, "B": 60, "H": 20}, {"L": 120.0, "B": 60.0, "T": 5.0}) == [
        {"name": "H", "soll": 20, "ist": None}, {"name": "L", "soll": 100, "ist": 120.0},
        {"name": "T", "soll": None, "ist": 5.0}]


def test_aenderungen_ohne_geaenderte_datei(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    freigeben(spec_pfad, GUELTIG)
    _lauf(r, spec_pfad, 1)
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: pytest.fail("ohne Änderung kein SolidWorks"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert (ergebnis["lauf"], ergebnis["geaendert"], ergebnis["fehlend"]) == (1, [], [])


def test_aenderungen_bei_aufgeraeumtem_lauf_ordner(umgebung, monkeypatch):
    import shutil

    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    shutil.rmtree(datei.parent)
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: pytest.fail("ohne Lauf-Ordner nichts vergleichen"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert (ergebnis["lauf"], ergebnis["geaendert"], ergebnis["fehlend"]) == (1, [], [])
    assert "Lauf-Ordner" in ergebnis["text"]


def test_aenderungen_ohne_aenderung_braucht_keine_freigabe(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    _lauf(r, spec_pfad, 1)  # keine Freigabe abgelegt
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: pytest.fail("ohne Änderung kein SolidWorks"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert (ergebnis["lauf"], ergebnis["geaendert"], ergebnis["fehlend"]) == (1, [], [])


def test_aenderungen_oeffnet_normteil_kopie_nicht(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    kopie = datei.parent / "ISO4762_M8x30_8_8.sldprt"
    kopie.write_bytes(b"normteil")
    protokoll_pfad = lauf_datei(spec_pfad, 1, "protokoll")
    protokoll = json.loads(protokoll_pfad.read_text(encoding="utf-8"))
    protokoll["sha256"] |= pruefsummen(datei.parent, [kopie])
    protokoll_pfad.write_text(json.dumps(protokoll), encoding="utf-8")
    kopie.write_bytes(b"von Hand geaendert")
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {datei.name: {"L": 100}})
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: pytest.fail("Normteil-Kopie ohne Soll nicht öffnen"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert ergebnis["geaendert"] == [{"datei": "ISO4762_M8x30_8_8.sldprt", "parameter": [],
                                      "hinweis": "keine Spezifikation zu dieser Datei (Normteil- oder Kaufteil-Kopie)"}]
