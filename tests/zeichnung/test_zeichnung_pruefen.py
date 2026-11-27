"""`swki zeichnung pruefen` ohne Rückleser (Plan Z1.4 Task 4a): Kopfprüfung, Orchestrierung mit Fake-Leser, CLI."""

import hashlib
import json
from types import SimpleNamespace

import pytest
import yaml

from swki.auftrag import dateiname, lauf_datei, lauf_nummern_dateien
from swki.cli import main
from swki.konfig import lade_standard
from swki.pruefung.schleife import lies_laeufe
from swki.zeichnung import zeichnung_pruefen as zp
from swki.zeichnung.massplan import massplan
from swki.zeichnung.zeichnen import ZeichnungFehler, schreibe_uebergabe, uebergabe, zeichnungsname
from tests.zeichnung.ist_bau import ideal_ist
from tests.zeichnung.test_massplan import _lade_ref, _spannplatte_protokoll


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _code(fehler) -> str:
    return fehler.value.daten["code"]


# --- kopf_pruefung ---------------------------------------------------------------------------------------------------

def test_kopf_sha_gleich():
    assert zp.kopf_pruefung("abc", {"sha256_slddrw": "abc"}) == []


def test_kopf_sha_abweichend_meldet_geaendert():
    meldungen = zp.kopf_pruefung("abc", {"sha256_slddrw": "xyz"})
    assert len(meldungen) == 1 and meldungen[0].startswith("ZEICHNUNG_GEAENDERT:")
    assert "swki aenderungen" in meldungen[0]


def test_kopf_ohne_uebergabe_bricht_ab():
    with pytest.raises(ZeichnungFehler) as e:
        zp.kopf_pruefung("abc", None)
    assert _code(e) == "ZEICHNUNG_UEBERGABE_FEHLT"


# --- Orchestrierung --------------------------------------------------------------------------------------------------

@pytest.fixture
def auftrag(tmp_path, monkeypatch):
    spec = _lade_ref("zeichnung/spannplatte_z.yaml")
    protokoll = _spannplatte_protokoll()
    spec_dir = tmp_path / "auftraege" / "T-AUF"
    (spec_dir / "protokolle").mkdir(parents=True)
    spec_pfad = spec_dir / "spannplatte_z.yaml"
    text = yaml.safe_dump(spec, allow_unicode=True)
    spec_pfad.write_text(text, encoding="utf-8")
    spec_pfad.with_name("spannplatte_z.freigegeben.yaml").write_text(text, encoding="utf-8")
    arbeits = tmp_path / "arbeit"
    ordner = arbeits / "T-AUF" / "lauf-1"
    (ordner / "zeichnung").mkdir(parents=True)
    lauf_datei(spec_pfad, 1, "protokoll").write_text(json.dumps(protokoll), encoding="utf-8")
    teil = ordner / f"{dateiname(spec, 'T-AUF', lade_standard())}.sldprt"
    teil.write_bytes(b"teil")
    drw = ordner / "zeichnung" / f"{zeichnungsname(spec)}.slddrw"
    drw.write_bytes(b"zeichnung")
    plan = massplan(spec, protokoll)
    schreibe_uebergabe(ordner / "zeichnung" / "zeichnung.json",
                       uebergabe(plan, {}, _sha(b"zeichnung"), ["VORMELDUNG"], "A3quer", (1, 1), 1,
                                 {"haupt": "Zeichnungsansicht1"}))
    monkeypatch.setattr(zp, "lade_rechner", lambda: SimpleNamespace(arbeitsordner=arbeits, sw_jahr=2025))
    monkeypatch.setattr(zp, "waehle_lauf", lambda p, lauf: (lauf or 1, []))
    return SimpleNamespace(spec_pfad=spec_pfad, spec=spec, plan=plan, teil=teil, drw=drw, ordner=ordner)


def _ideal_leser(a, gesehen=None):
    def leser(slddrw, rollen):
        if gesehen is not None:
            gesehen.append((slddrw, dict(rollen)))
        return ideal_ist(a.plan, spec=a.spec)
    return leser


def test_pruefung_mit_fake_leser_bestanden(auftrag):
    gesehen = []
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag, gesehen))
    assert bericht["bestanden"] is True, bericht["maengel"]
    assert gesehen == [(auftrag.drw, {"haupt": "Zeichnungsansicht1"})]
    assert "VORMELDUNG" in bericht["meldungen"]
    assert bericht["zeichnung"] == str(auftrag.drw)
    assert bericht["pdf"] is None or bericht["pdf"].endswith(".pdf")
    assert set(bericht) >= {"ist", "pdf", "png", "zeichnung", "pruefungen", "maengel", "lauf"}
    assert bericht["ist"]["format_"] == "A3quer"
    assert bericht["ist"]["sha256_slddrw"] == _sha(b"zeichnung")
    ziel = lauf_datei(auftrag.spec_pfad, 1, "zeichnung.pruefbericht")
    assert ziel.name == "spannplatte_z.lauf-1.zeichnung.pruefbericht.json"
    assert json.loads(ziel.read_text(encoding="utf-8"))["bestanden"] is True


def test_bericht_zaehlt_nicht_als_teilpruefbericht(auftrag):
    zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    lauf_datei(auftrag.spec_pfad, 1, "protokoll").write_text('{"status": "ok", "dauer_s": 1}', encoding="utf-8")
    assert lauf_datei(auftrag.spec_pfad, 1, "zeichnung.pruefbericht").exists()
    assert lauf_nummern_dateien(auftrag.spec_pfad) == [1]  # nur das Protokoll zählt
    (eintrag,) = lies_laeufe(auftrag.spec_pfad)
    assert eintrag["code_maengel"] is None and eintrag["bestanden"] is False


def test_handaenderung_wird_gemeldet_nicht_abgebrochen(auftrag):
    auftrag.drw.write_bytes(b"von hand geaendert")
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert any(m.startswith("ZEICHNUNG_GEAENDERT:") for m in bericht["meldungen"])
    assert bericht["ist"]["sha256_slddrw"] == _sha(b"von hand geaendert")


def test_plan_veraltet_wird_gemeldet(auftrag):
    pfad = auftrag.ordner / "zeichnung" / "zeichnung.json"
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    daten["plan"][0]["wert"] += 7.0
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert any(m.startswith("ZEICHNUNG_PLAN_VERALTET") for m in bericht["meldungen"])


def test_plan_gleich_keine_veraltet_meldung(auftrag):
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert not any("PLAN_VERALTET" in m for m in bericht["meldungen"])


def test_plan_namen_zaehlen_nicht(auftrag):
    """Nach Wirkung: andere Ids und Maßnamen sind kein veralteter Plan."""
    pfad = auftrag.ordner / "zeichnung" / "zeichnung.json"
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    for i, m in enumerate(daten["plan"]):
        m["id"], m["name"] = f"x{i}", None if m["name"] is None else m["name"] + "_x"
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert not any("PLAN_VERALTET" in m for m in bericht["meldungen"])


def test_leser_aendert_zeichnung(auftrag):
    def leser(slddrw, rollen):
        slddrw.write_bytes(b"veraendert")
        return ideal_ist(auftrag.plan, spec=auftrag.spec)

    with pytest.raises(ZeichnungFehler) as e:
        zp.zeichnung_pruefen(auftrag.spec_pfad, leser=leser)
    assert _code(e) == "ZEICHNUNG_PRUEFUNG_AENDERT"


def test_leser_aendert_teil(auftrag):
    def leser(slddrw, rollen):
        auftrag.teil.write_bytes(b"veraendert")
        return ideal_ist(auftrag.plan, spec=auftrag.spec)

    with pytest.raises(ZeichnungFehler) as e:
        zp.zeichnung_pruefen(auftrag.spec_pfad, leser=leser)
    assert _code(e) == "ZEICHNUNG_PRUEFUNG_AENDERT"
    assert not lauf_datei(auftrag.spec_pfad, 1, "zeichnung.pruefbericht").exists()


def test_fehlende_uebergabe(auftrag):
    (auftrag.ordner / "zeichnung" / "zeichnung.json").unlink()
    with pytest.raises(ZeichnungFehler) as e:
        zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert _code(e) == "ZEICHNUNG_UEBERGABE_FEHLT"


def test_fehlende_zeichnung(auftrag):
    auftrag.drw.unlink()
    with pytest.raises(ZeichnungFehler) as e:
        zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert _code(e) == "ZEICHNUNG_FEHLT"


def test_standardleser_ohne_rueckleser_klare_meldung(auftrag, monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "swki.zeichnung.rueckleser", None)  # Import schlägt fehl wie bei fehlendem Modul
    with pytest.raises(ZeichnungFehler, match="Rückleser fehlt") as e:
        zp.zeichnung_pruefen(auftrag.spec_pfad)
    assert _code(e) == "ZEICHNUNG_RUECKLESER_FEHLT"


def test_lauf_meldung_aus_waehle_lauf(auftrag, monkeypatch):
    monkeypatch.setattr(zp, "waehle_lauf", lambda p, lauf: (1, ["LAUF_NICHT_BESTANDEN: nur Ansicht"]))
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert "LAUF_NICHT_BESTANDEN: nur Ansicht" in bericht["meldungen"]


# --- CLI -------------------------------------------------------------------------------------------------------------

def test_cli_kennt_zeichnung_pruefen(capsys):
    assert main(["zeichnung", "pruefen", "--help"]) == 0
    assert "--lauf" in capsys.readouterr().out
