import json
from pathlib import Path

import pytest

from swki.aenderungen import sha256_datei
from swki.cli import main
from swki.kaufteile import befehle, cache, katalog as kat
from swki.kaufteile.fehler import KaufteilFehler
from swki.konfig import Rechner
from swki.spec.freigabe import FreigabeFehler, pruefsumme
from tests.kaufteile.beispiel import kopie, schreibe

SCHLUESSEL = "SWKI-MUSTER GM42-10"


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    r = Rechner(2025, Path("C:/SW"), Path("C:/t.prtdot"), None, None, tmp_path / "arbeit", None, tmp_path / "kauf")
    monkeypatch.setattr(befehle, "lade_rechner", lambda: r)
    step = tmp_path / "download" / "GM42-10.STEP"
    step.parent.mkdir()
    step.write_bytes(b"ISO-10303-21;\nHEADER;\n")
    blatt = tmp_path / "download" / "datenblatt.md"
    blatt.write_text("# Datenblatt GM42\n", encoding="utf-8")
    return r, tmp_path / "katalog", step, blatt


@pytest.fixture
def sw(monkeypatch):
    aufrufe = []

    def untersuche(original, ordner):
        aufrufe.append(("untersuche", original.name))
        return {"koerper": 2, "volumen": 220123.456, "flaechen": 40}

    def baue_und_pruefe(spec, original, ordner, mit_bildern=False):
        aufrufe.append(("bau", mit_bildern))
        ordner.mkdir(parents=True, exist_ok=True)
        teil = ordner / "SWKI-MUSTER_GM42-10.sldprt"
        teil.write_bytes(b"teil")
        return {"bestanden": True, "pruefungen": [{"id": "rebuild", "ok": True}], "maengel": [], "teil": str(teil),
                "bilder": {"iso": "iso.png"} if mit_bildern else {}, "fehler": None,
                "gewinde_modell": {"flansch": "kernloch"}, "kennzahlen": {"flaechen": 40}}

    monkeypatch.setattr(befehle.aufnahme, "untersuche", untersuche)
    monkeypatch.setattr(befehle.aufnahme, "baue_und_pruefe", baue_und_pruefe)
    return aufrufe


def _eintrag(katalog, step) -> Path:
    spec = kopie()
    spec["original"] = {"datei": "gm42-10.step", "sha256": sha256_datei(step), "bezug": {"art": "nutzer", "datum": "2026-10-07"}}
    return schreibe(katalog, spec)


def _urteil(pfad, tmp_path, katalog, bestanden=True):
    datei = tmp_path / "urteil.json"
    datei.write_text(json.dumps({"bestanden": bestanden, "maengel": []}), encoding="utf-8")
    spec = befehle.lade_eintrag(pfad)
    return befehle.urteil(SCHLUESSEL, datei, pruefsumme(spec), katalog)


def test_nur_step(umgebung):
    with pytest.raises(KaufteilFehler) as e:
        befehle.untersuchen(Path("motor.igs"), "SWKI-MUSTER", "GM42-10")
    assert e.value.daten["code"] == "KAUFTEIL_FORMAT"


def test_untersuchen_kopiert_und_liefert_geruest(umgebung, sw):
    r, katalog, step, blatt = umgebung
    erg = befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", blatt, katalog=katalog)
    kopie_step = r.kaufteilbibliothek / "quellen" / "swki-muster" / "gm42-10.step"
    assert erg["original"] == {"datei": "gm42-10.step", "pfad": str(kopie_step), "sha256": sha256_datei(step), "kopiert": True}
    assert kopie_step.read_bytes() == step.read_bytes() and (kopie_step.parent / "datenblatt.md").is_file()
    assert erg["geruest"]["original"]["sha256"] == sha256_datei(step) and erg["geruest"]["koerper"] == 2
    assert erg["geruest"]["pruefung"]["volumen"] == {"soll": 220123.456, "toleranz_prozent": 0.01}
    assert erg["geruest"]["datenblatt"] == {"datei": "datenblatt.md"} and erg["eintrag_vorhanden"] is False
    assert json.loads((Path(erg["lauf"]) / "diagnose.json").read_text(encoding="utf-8"))["flaechen"] == 40
    assert sw == [("untersuche", "gm42-10.step")]
    assert befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)["original"]["kopiert"] is False
    assert Path(befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)["lauf"]).name == "lauf-3"


def test_anderer_inhalt_ueberschreibt_nie(umgebung, sw):
    _, katalog, step, _ = umgebung
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    step.write_bytes(b"ISO-10303-21;\nANDERS;\n")
    with pytest.raises(KaufteilFehler) as e:
        befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    assert e.value.daten["code"] == "KAUFTEIL_QUELLE_ABWEICHEND"


def test_eintrag_mit_anderem_original_und_neue_version(umgebung, sw):
    r, katalog, step, _ = umgebung
    _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    alt = r.kaufteilbibliothek / "quellen" / "swki-muster" / "gm42-10.step"
    step.write_bytes(b"ISO-10303-21;\nNEU;\n")
    with pytest.raises(KaufteilFehler) as e:
        befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    assert e.value.daten["code"] == "KAUFTEIL_QUELLE_ABWEICHEND"
    neu = befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", neue_version=True, katalog=katalog)["original"]
    assert neu["datei"] == f"gm42-10.{sha256_datei(step)[:8]}.step" and alt.is_file()


def test_stellt_original_eines_eintrags_wieder_her(umgebung, sw):
    r, katalog, step, _ = umgebung
    _eintrag(katalog, step)
    erg = befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    assert erg["eintrag_vorhanden"] is True and erg["original"]["kopiert"] is True


def test_hole_braucht_quelle_freigabe_und_urteil(umgebung, sw, tmp_path):
    r, katalog, step, _ = umgebung
    pfad = _eintrag(katalog, step)
    with pytest.raises(FreigabeFehler):
        befehle.hole(SCHLUESSEL, katalog)
    main(["freigeben", str(pfad)])
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_UNGEPRUEFT"
    _urteil(pfad, tmp_path, katalog)
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_QUELLE_FEHLT"
    assert sw == []


def test_hole_legt_ab_und_trifft_den_cache(umgebung, sw, tmp_path):
    r, katalog, step, _ = umgebung
    pfad = _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    main(["freigeben", str(pfad)])
    _urteil(pfad, tmp_path, katalog)
    erst = befehle.hole(SCHLUESSEL, katalog)
    ziel = r.kaufteilbibliothek / "2025" / "SWKI-MUSTER_GM42-10.sldprt"
    assert erst["gebaut"] is True and Path(erst["pfad"]) == ziel and erst["gewinde_modell"] == {"flansch": "kernloch"}
    eintrag = json.loads(ziel.with_suffix(".json").read_text(encoding="utf-8"))
    assert eintrag["sldprt_sha256"] == sha256_datei(ziel) and eintrag["pruefsumme"] == erst["pruefsumme"]
    zweit = befehle.hole(SCHLUESSEL, katalog)
    assert zweit["gebaut"] is False and zweit["gewinde_modell"] == {"flansch": "kernloch"}
    ziel.write_bytes(b"von Hand geaendert")
    assert befehle.hole(SCHLUESSEL, katalog)["gebaut"] is True
    assert [a for a in sw if a[0] == "bau"] == [("bau", False), ("bau", False)]
    kat.urteil_pfad(pfad).unlink()  # ohne Prüfer-Urteil kein Cache-Treffer (Spec 3c §5.3 Schritt 1)
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_UNGEPRUEFT"


def test_hole_pruefung_oder_import_scheitert(umgebung, sw, tmp_path, monkeypatch):
    r, katalog, step, _ = umgebung
    pfad = _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    main(["freigeben", str(pfad)])
    _urteil(pfad, tmp_path, katalog)
    mangel = {"bestanden": False, "pruefungen": [], "maengel": [{"pruefung": "koerper", "knoten": [], "beschreibung": "x"}],
              "teil": None, "bilder": {}, "fehler": None, "gewinde_modell": {}, "kennzahlen": {}}
    monkeypatch.setattr(befehle.aufnahme, "baue_und_pruefe", lambda *a, **k: mangel)
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_PRUEFUNG" and e.value.daten["maengel"][0]["pruefung"] == "koerper"
    fehler = {**mangel, "fehler": {"code": "KAUFTEIL_IMPORT", "schritt": "import", "meldung": "Import gescheitert"}}
    monkeypatch.setattr(befehle.aufnahme, "baue_und_pruefe", lambda *a, **k: fehler)
    with pytest.raises(KaufteilFehler) as e:
        befehle.hole(SCHLUESSEL, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_IMPORT"
    assert not (r.kaufteilbibliothek / "2025").exists()


def test_urteil_zur_alten_freigabe_und_muster(umgebung, sw, tmp_path):
    r, katalog, step, blatt = umgebung
    pfad = _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", blatt, katalog=katalog)
    main(["freigeben", str(pfad)])
    datei = tmp_path / "u.json"
    datei.write_text(json.dumps({"bestanden": True, "maengel": []}), encoding="utf-8")
    with pytest.raises(KaufteilFehler) as e:
        befehle.urteil(SCHLUESSEL, datei, "0" * 64, katalog)
    assert e.value.daten["code"] == "KAUFTEIL_UNGEPRUEFT"
    m = befehle.muster(SCHLUESSEL, katalog)
    assert m["bestanden"] is True and m["bilder"] == {"iso": "iso.png"} and m["eintrag"].endswith("gm42-10.freigegeben.yaml")
    assert m["datenblatt"] == str(r.kaufteilbibliothek / "quellen" / "swki-muster" / "datenblatt.md")
    assert ("bau", True) in sw and not (r.kaufteilbibliothek / "2025").exists()


def test_liste_markiert_veralteten_cache(umgebung, sw, tmp_path, monkeypatch, capsys):
    r, katalog, step, _ = umgebung
    pfad = _eintrag(katalog, step)
    befehle.untersuchen(step, "SWKI-MUSTER", "GM42-10", katalog=katalog)
    main(["freigeben", str(pfad)])
    _urteil(pfad, tmp_path, katalog)
    befehle.hole(SCHLUESSEL, katalog)
    [t] = befehle.liste(katalog=katalog)["teile"]
    assert t == {"schluessel": SCHLUESSEL, "gueltig": True, "freigegeben": True, "geprueft": True, "cache": True}
    assert befehle.liste(nur_veraltet=True, katalog=katalog)["teile"] == []
    monkeypatch.setattr(cache, "IMPORTWEG_VERSION", cache.IMPORTWEG_VERSION + 1)
    assert befehle.liste(nur_veraltet=True, katalog=katalog)["teile"][0]["cache"] is False
    monkeypatch.setattr(kat, "ORDNER", katalog)
    capsys.readouterr()
    assert main(["kaufteil", "liste"]) == 0 and json.loads(capsys.readouterr().out)["teile"][0]["cache"] is False
