"""`swki zeichnung pruefen` ohne Rückleser (Plan Z1.4 Task 4a): Kopfprüfung, Orchestrierung mit Fake-Leser, CLI."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from swki.auftrag import dateiname, lauf_datei, lauf_nummern_dateien
from swki.cli import main
from swki.konfig import lade_standard
from swki.pruefung.schleife import lies_laeufe
from swki.spec.freigabe import freigeben
from swki.zeichnung import zeichnung_pruefen as zp
from swki.zeichnung.massplan import Mass, massplan
from swki.zeichnung.zeichnen import ZeichnungFehler, schreibe_uebergabe, uebergabe, zeichnungsname
from tests.zeichnung.ist_bau import ideal_ist
from tests.zeichnung.test_massplan import _lade_ref, _spannplatte_protokoll


VORMELDUNG = "EINZELHEIT: t1 aus haupt ausgelagert (3 Maße)"  # Übergabe-Meldung „nur Bericht“ (Task 4b)


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
    freigeben(spec_pfad, spec)                     # Gesamtreview I1: `zeichnung pruefen` prüft die Freigabe
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
                       uebergabe(plan, {}, _sha(b"zeichnung"), [VORMELDUNG], "A3quer", (1, 1), 1,
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
    assert VORMELDUNG in bericht["meldungen"]
    assert bericht["zeichnung"] == str(auftrag.drw)
    assert bericht["pdf"] is None  # im Test liegt kein PDF
    assert bericht["kopf"] == {"ok": True, "meldungen": []}
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
    assert bericht["bestanden"] is False and bericht["kopf"]["ok"] is False
    assert any(m.startswith("ZEICHNUNG_GEAENDERT:") for m in bericht["kopf"]["meldungen"])
    assert len(bericht["pruefungen"]) == 9  # die Prüfungen laufen trotzdem
    assert bericht["ist"]["sha256_slddrw"] == _sha(b"von hand geaendert")


def test_plan_veraltet_wird_gemeldet(auftrag):
    pfad = auftrag.ordner / "zeichnung" / "zeichnung.json"
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    daten["plan"][0]["wert"] += 7.0
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert any(m.startswith("ZEICHNUNG_PLAN_VERALTET") for m in bericht["meldungen"])
    assert bericht["bestanden"] is False and bericht["kopf"]["ok"] is False
    assert any(m.startswith("ZEICHNUNG_PLAN_VERALTET") for m in bericht["kopf"]["meldungen"])
    assert len(bericht["pruefungen"]) == 9


def test_kopfmangel_verwirft_pdf(auftrag):
    auftrag.drw.with_suffix(".pdf").write_bytes(b"%PDF-kaputt")
    auftrag.drw.write_bytes(b"von hand geaendert")
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert bericht["pdf"] is None
    assert any(m.startswith("PDF_VERWORFEN") for m in bericht["meldungen"])


def test_wirkung_vergleicht_geometrie_gerundet():
    a = Mass("a", "neu", "durchmesser", 10.0, "f1", geometrie={"von": 0.0, "bis": 5.0})
    gleich = Mass("b", "neu", "durchmesser", 10.0, "f1", geometrie={"von": 0.0000001, "bis": 5.0})
    anders = Mass("c", "neu", "durchmesser", 10.0, "f1", geometrie={"von": 1.0, "bis": 5.0})
    assert zp._wirkung([a]) == zp._wirkung([gleich])
    assert zp._wirkung([a]) != zp._wirkung([anders])


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


def test_fehlendes_teil_bricht_vor_dem_leser_ab(auftrag):
    auftrag.teil.unlink()
    gesehen = []
    with pytest.raises(ZeichnungFehler) as e:
        zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag, gesehen))
    assert _code(e) == "ZEICHNUNG_TEIL_FEHLT" and gesehen == []


def test_alter_bericht_wird_bei_jedem_abbruch_geloescht(auftrag):
    ziel = lauf_datei(auftrag.spec_pfad, 1, "zeichnung.pruefbericht")
    uebergabe_pfad = auftrag.ordner / "zeichnung" / "zeichnung.json"
    uebergabe_text = uebergabe_pfad.read_bytes()

    def aendernder_leser(slddrw, rollen):
        auftrag.teil.write_bytes(b"veraendert")
        return ideal_ist(auftrag.plan, spec=auftrag.spec)

    faelle = [lambda: uebergabe_pfad.unlink(), lambda: auftrag.drw.unlink(), lambda: auftrag.teil.unlink(), None]
    for fall in faelle:
        uebergabe_pfad.write_bytes(uebergabe_text)
        auftrag.drw.write_bytes(b"zeichnung")
        auftrag.teil.write_bytes(b"teil")
        ziel.write_text("{}", encoding="utf-8")
        if fall:
            fall()
        with pytest.raises(ZeichnungFehler):
            zp.zeichnung_pruefen(auftrag.spec_pfad, leser=aendernder_leser if fall is None else _ideal_leser(auftrag))
        assert not ziel.exists()


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


def test_cli_reicht_lauf_durch(monkeypatch, capsys):
    aufrufe = []
    monkeypatch.setattr(zp, "zeichnung_pruefen", lambda spec, lauf=None, leser=None: aufrufe.append((spec, lauf)) or {"x": 1})
    assert main(["zeichnung", "pruefen", "a/spec.yaml", "--lauf", "3"]) == 0
    assert aufrufe == [(Path("a/spec.yaml"), 3)]


# --- Task 4b: Anbindung des Rücklesers ------------------------------------------------------------------------------

def _uebergabe_aendern(auftrag, **felder):
    pfad = auftrag.ordner / "zeichnung" / "zeichnung.json"
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    daten.update(felder)
    pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    sha = _sha(auftrag.drw.read_bytes())
    assert daten["sha256_slddrw"] == sha


def test_unbekannte_uebergabemeldung_ist_mangel(auftrag):
    _uebergabe_aendern(auftrag, meldungen=["NEU_ERFUNDEN: x"])
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert bericht["bestanden"] is False
    assert any("unbekannte Zeichnungsmeldung: NEU_ERFUNDEN" in m["text"] for m in bericht["maengel"])


def test_rauheit_nur_eine_instanz_aus_der_uebergabe(auftrag):
    meldung = "RAUHEIT_NUR_EINE_INSTANZ: t1 Ra 1,6 – Symbol an einer von 2 Instanzen"
    _uebergabe_aendern(auftrag, meldungen=[meldung])
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert bericht["bestanden"] is False
    assert [m["regel"] for m in bericht["maengel"] if m["text"] == meldung] == ["Z-TOL-4"]


def test_zeichnungsmasse_und_merkmale_nach_dem_lesen(auftrag):
    """Der Rückleser liefert Zeichnungsmaße unter `RD<n>@…` und Angaben nur mit den Features der Kante; die Prüfung
    ordnet über `zeichnungsmasse` und die `enthalten`-Logik zu."""
    from dataclasses import replace
    _uebergabe_aendern(auftrag, zeichnungsmasse={"D3@m1": "RD1@Zeichenansicht1"})
    features = {"t1": ("Schnitt1", "s1"), "st": ("st", "st_fase"), "f1": ("Schnitt1", "f1"), "g1": ("f1", "m1")}

    def leser(slddrw, rollen):
        ist = ideal_ist(auftrag.plan, spec=auftrag.spec)
        masse = tuple(replace(m, name="RD1@Zeichenansicht1") if m.name == "D3@m1" else m for m in ist.masse)
        angaben = tuple(replace(a, merkmal=None, features=features.get(a.merkmal, ())) for a in ist.angaben)
        return replace(ist, masse=masse, angaben=angaben)

    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=leser)
    assert bericht["bestanden"] is True, bericht["maengel"]
    assert any(m["name"] == "D3@m1" for m in bericht["ist"]["masse"])
    # st ohne Rauheit (Nutzer 28.11.2026); None: Symbol des Rauheitsfelds (ohne Kante, Sammelrauheit)
    assert {a["merkmal"] for a in bericht["ist"]["angaben"] if a["art"] == "rauheit"} == {"t1", None}


def test_meldungen_des_ruecklesers_im_bericht(auftrag):
    from dataclasses import replace
    meldung = "RUECKLESEN_UNVOLLSTAENDIG: Zeichenansicht1 – Maß RD3 ohne Wert"

    def leser(slddrw, rollen):
        return replace(ideal_ist(auftrag.plan, spec=auftrag.spec), meldungen=(meldung,))

    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=leser)
    assert bericht["bestanden"] is False and meldung in bericht["meldungen"]


def test_standardleser_ist_der_rueckleser():
    from swki.zeichnung import rueckleser
    assert zp._standardleser() is rueckleser.lies_zeichnung


# --- Gesamtreview: Spec und Freigabe (I1, C1) -------------------------------------------------------------------------

def _umbenannt(x, alt: str, neu: str):
    """Feature-ID überall ersetzen (nur ganze Werte, keine Teilwörter)."""
    if isinstance(x, dict):
        return {k: _umbenannt(v, alt, neu) for k, v in x.items()}
    if isinstance(x, list):
        return [_umbenannt(v, alt, neu) for v in x]
    return neu if x == alt else x


def test_bauweg_umbenennung_nach_der_freigabe_gilt(auftrag):
    """I1: Freigegeben wurde die Kabelnut als `kabelnut`, gebaut und gezeichnet aus der Arbeitsdatei mit `k1`
    (erlaubte Bauweg-Umbenennung, Prüfsumme gleich). Plan und Merkmale kommen aus der Arbeitsdatei – wie bei
    `swki zeichnen` – sonst wäre der Plan „veraltet“ und k1 fehlte."""
    kopie = _umbenannt(auftrag.spec, "k1", "kabelnut")
    text = auftrag.spec_pfad.read_text(encoding="utf-8")
    auftrag.spec_pfad.write_text(yaml.safe_dump(kopie, allow_unicode=True), encoding="utf-8")
    freigeben(auftrag.spec_pfad, kopie)
    auftrag.spec_pfad.write_text(text, encoding="utf-8")
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert bericht["bestanden"] is True, (bericht["kopf"], bericht["maengel"])


def test_freigabe_veraltet_bricht_ab(auftrag):
    """I1: `zeichnung pruefen` prüft die Freigabe wie `swki zeichnen` (Anforderung nach der Freigabe geändert)."""
    from swki.spec.freigabe import FreigabeFehler
    spec = {**auftrag.spec, "material": "1.0037"}
    auftrag.spec_pfad.write_text(yaml.safe_dump(spec, allow_unicode=True), encoding="utf-8")
    ziel = lauf_datei(auftrag.spec_pfad, 1, "zeichnung.pruefbericht")
    ziel.write_text("{}", encoding="utf-8")
    with pytest.raises(FreigabeFehler) as e:
        zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert _code(e) == "FREIGABE_VERALTET" and not ziel.exists()


def test_funktionen_veraltet_ist_kopfmangel(auftrag, monkeypatch):
    """C1: C-Wert der Stiftbohrung H7 → H8 nach der Freigabe – die Prüfsumme sieht es nicht, die Kopfprüfung schon."""
    from swki.spec import funktionen
    tabelle = {**funktionen.lade_funktionen(), "stiftbohrung": {**funktionen.lade_funktionen()["stiftbohrung"],
                                                               "passung": "H8"}}
    monkeypatch.setattr(funktionen, "lade_funktionen", lambda pfad=None: tabelle)
    bericht = zp.zeichnung_pruefen(auftrag.spec_pfad, leser=_ideal_leser(auftrag))
    assert bericht["bestanden"] is False and bericht["kopf"]["ok"] is False
    assert any(m.startswith("FUNKTIONEN_VERALTET:") for m in bericht["kopf"]["meldungen"])
    assert not any("unbekannte Zeichnungsmeldung" in m["text"] for m in bericht["maengel"])
