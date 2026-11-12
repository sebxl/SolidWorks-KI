"""swki aenderungen über den Baum (Spec Bestandsdateien §8.5, §8.6): Features, Material und Eigenschaften neben den Maßen; ein Lauf
mit Bestandsaufnahme wird nicht in SolidWorks geöffnet."""

import copy
import json
import os

import pytest

from swki import aenderungen
from swki.aenderungen import MANUELL_GEAENDERT, AenderungFehler, pruefe_unveraendert, soll_teile
from swki.auftrag import lauf_datei
from swki.baugruppe.freigabe import freigeben_baugruppe, freigegebene_teile
from swki.baugruppe.laden import lade_baugruppe
from swki.konfig import lade_standard
from swki.spec.freigabe import freigeben, freigegebene_spec
from tests.baugruppe.beispiel import schreibe
from tests.bestand.test_abgleich import PROTOKOLL_TEIL, SPEC_TEIL, _f, _ist_teil
from tests.spec.beispiel import GUELTIG
from tests.test_aenderungen import _lauf, umgebung  # noqa: F401  (Fixture)


def _herkunft(r, auftrag="B", nummer=1, lauf=1, spec="platte.yaml"):
    """Eine Bestandsaufnahme, deren Original aus Lauf `lauf` des Auftrags A stammt (`herkunft.json`, Plan Task 1)."""
    pfad = r.arbeitsordner / auftrag / f"bestand-{nummer}" / "herkunft.json"
    pfad.parent.mkdir(parents=True)
    pfad.write_text(json.dumps({"auftrag": "A", "lauf": lauf, "spec": spec}), encoding="utf-8")


def _aufbau(umgebung, monkeypatch, ist, geaendert=True):
    """Lauf 1 mit einem Teil, dessen Protokoll dem von test_abgleich entspricht; alles Maßliche ist gleich. Rückgabe: (Teil, Aufrufe
    von oeffne, Aufrufe von lies_bestand)."""
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    if geaendert:
        datei.write_bytes(b"von Hand geaendert")
    masse = [m for k in PROTOKOLL_TEIL["knoten"] for m in k["masse"]]
    oeffnen, lesen = [], []
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: "app")
    monkeypatch.setattr(aenderungen, "oeffne_lauf", lambda app, pfad, ordner: oeffnen.append((pfad, ordner)) or "modell")
    monkeypatch.setattr(aenderungen.sw, "schliesse", lambda app, model: None)
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {datei.name: {"L": 100}})
    monkeypatch.setattr(aenderungen, "soll_masse", lambda *a: {datei.name: masse})
    monkeypatch.setattr(aenderungen, "soll_teile", lambda *a: {datei.name: (PROTOKOLL_TEIL, SPEC_TEIL)})
    monkeypatch.setattr(aenderungen, "lies_masse", lambda model, m: {x["name"]: x["wert"] for x in m})
    monkeypatch.setattr("swki.bestand.sw_bestand.lies_bestand", lambda app, model: lesen.append((app, model)) or ist)
    return datei, oeffnen, lesen


def _momentaufnahme(ordner):
    return {str(p.relative_to(ordner)): (p.is_file(), p.stat().st_size, p.stat().st_mtime_ns) for p in sorted(ordner.rglob("*"))}


def test_aenderungen_oeffnet_nur_lesend(umgebung, monkeypatch):
    """Über den Pfadschutz im Lauf-Ordner (Bestandsdateien Korrektur 2), unsichtbar und schreibgeschützt."""
    datei, oeffnen, lesen = _aufbau(umgebung, monkeypatch, _ist_teil())
    aenderungen.aenderungen(umgebung[1])
    assert oeffnen == [(datei.parent / datei.name, datei.parent)]
    assert lesen == [("app", "modell")]


def test_oeffne_lauf_geht_ueber_den_pfadschutz(monkeypatch, tmp_path):
    from swki.bestand import pfade

    aufrufe = []
    monkeypatch.setattr(pfade, "oeffne_in", lambda app, pfad, wurzel, **k: aufrufe.append((pfad, wurzel, k)) or "modell")
    assert aenderungen.oeffne_lauf("app", tmp_path / "A.sldprt", tmp_path) == "modell"
    assert aufrufe == [(tmp_path / "A.sldprt", tmp_path, {"sichtbar": False, "nur_lesen": True})]


def test_aenderungen_nennt_den_baum_und_schweigt_dann_ueber_gleiche_masse(umgebung, monkeypatch):
    """Ein neues Feature erklärt die Änderung: kein „Datei geändert, Maße gleich“."""
    ist = _ist_teil()
    ist["features"].append(_f("Verrundung1", "Fillet", eltern=["f1"]))
    _aufbau(umgebung, monkeypatch, ist)
    [eintrag] = aenderungen.aenderungen(umgebung[1])["geaendert"]
    assert [f["name"] for f in eintrag["baum"]["features_neu"]] == ["Verrundung1"]
    assert eintrag["masse"] == [] and "hinweis" not in eintrag and "nicht_erklaert" not in eintrag


def test_aenderungen_hinweis_nur_wenn_der_baum_nichts_erklaert(umgebung, monkeypatch):
    _aufbau(umgebung, monkeypatch, _ist_teil())
    [eintrag] = aenderungen.aenderungen(umgebung[1])["geaendert"]
    assert eintrag["baum"]["nicht_erklaert"] is True and eintrag["nicht_erklaert"] is True
    assert "Datei geändert, Maße gleich" in eintrag["hinweis"] and "nicht erklärt" in eintrag["hinweis"]


def test_aenderungen_material_und_eigenschaft_erklaeren_die_aenderung(umgebung, monkeypatch):
    ist = _ist_teil()
    ist["material"] = "Aluminium 6061"
    _aufbau(umgebung, monkeypatch, ist)
    [eintrag] = aenderungen.aenderungen(umgebung[1])["geaendert"]
    assert eintrag["baum"]["material"] == {"soll": "1.0038", "ist": "Aluminium 6061"} and "hinweis" not in eintrag


def test_aenderungen_baum_nicht_lesbar_sagt_nie_unveraendert(umgebung, monkeypatch):
    _aufbau(umgebung, monkeypatch, _ist_teil())

    def kaputt(app, model):
        raise RuntimeError("COM weg")

    monkeypatch.setattr("swki.bestand.sw_bestand.lies_bestand", kaputt)
    [eintrag] = aenderungen.aenderungen(umgebung[1])["geaendert"]
    assert eintrag["baum"]["nicht_erklaert"] is True and eintrag["baum"]["vollstaendig"] is False
    assert "RuntimeError: COM weg" in eintrag["baum"]["luecken"][0] and eintrag["nicht_erklaert"] is True


def test_aenderungen_teil_ohne_soll_im_protokoll_sagt_nie_unveraendert(umgebung, monkeypatch):
    _aufbau(umgebung, monkeypatch, _ist_teil())
    monkeypatch.setattr(aenderungen, "soll_teile", lambda *a: {})
    [eintrag] = aenderungen.aenderungen(umgebung[1])["geaendert"]
    assert eintrag["baum"]["nicht_erklaert"] is True and "kein Soll" in eintrag["baum"]["luecken"][0]


def test_aenderungen_alter_lauf_ohne_massprotokoll_bleibt_unerklaert(umgebung, monkeypatch):
    """Der Lauf kennt kein Maßprotokoll: der Weg über globale Variablen bleibt, der Baum nennt die Lücke."""
    ist = _ist_teil()
    datei, _, _ = _aufbau(umgebung, monkeypatch, ist)
    alt = copy.deepcopy(PROTOKOLL_TEIL)
    for k in alt["knoten"]:
        del k["masse"]
    monkeypatch.setattr(aenderungen, "soll_masse", lambda *a: {})
    monkeypatch.setattr(aenderungen, "soll_teile", lambda *a: {datei.name: (alt, SPEC_TEIL)})
    monkeypatch.setattr(aenderungen, "lies_globale_variablen", lambda m: {"L": 100})
    [eintrag] = aenderungen.aenderungen(umgebung[1])["geaendert"]
    assert eintrag["baum"]["masse_geprueft"] is False and eintrag["nicht_erklaert"] is True
    assert "Parameter gleich" in eintrag["hinweis"]


def test_aenderungen_nennt_neue_dateien_im_lauf_ordner(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    (datei.parent / "Neu.SLDPRT").write_bytes(b"neu")
    (datei.parent / "bilder").mkdir()
    (datei.parent / "bilder" / "iso.png").write_bytes(b"png")
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: pytest.fail("ohne geänderte Datei kein SolidWorks"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert ergebnis["geaendert"] == [] and [n["datei"] for n in ergebnis["neu"]] == ["Neu.SLDPRT"]


# --- Lauf mit Bestandsaufnahme --------------------------------------------------------------------------------------

def test_aenderungen_oeffnet_lauf_mit_aufnahme_nicht(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    soll_sha = aenderungen.sha256_datei(datei)
    datei.write_bytes(b"von Hand geaendert")
    _herkunft(r)
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: pytest.fail("Lauf mit Aufnahme nicht in SolidWorks öffnen"))
    monkeypatch.setattr(aenderungen, "oeffne_lauf", lambda *a, **k: pytest.fail("Lauf mit Aufnahme nicht öffnen"))
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: pytest.fail("keine Freigabe nötig"))
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert ergebnis["aufnahmen"] == [{"auftrag": "B", "aufnahme": 1}]
    assert ergebnis["abgleich"] == f"swki bestand abgleich B --spec {spec_pfad.resolve()}"
    [eintrag] = ergebnis["geaendert"]
    assert eintrag["datei"] == datei.name and eintrag["sha256"] == {"soll": soll_sha, "ist": aenderungen.sha256_datei(datei)}
    assert "swki bestand abgleich" in eintrag["hinweis"] and ergebnis["fehlend"] == []


def test_aenderungen_lauf_mit_aufnahme_ohne_aenderung_bleibt_wie_bisher(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    _lauf(r, spec_pfad, 1)
    _herkunft(r)
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    ergebnis = aenderungen.aenderungen(spec_pfad)
    assert (ergebnis["lauf"], ergebnis["geaendert"], ergebnis["fehlend"]) == (1, [], [])


def test_aenderungen_aufnahme_eines_anderen_laufs_gilt_nicht(umgebung, monkeypatch):
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    datei.write_bytes(b"von Hand geaendert")
    _herkunft(r, lauf=7)
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    monkeypatch.setattr(aenderungen, "verbinde", lambda jahr: "app")
    oeffnen = []
    monkeypatch.setattr(aenderungen, "oeffne_lauf", lambda app, pfad, ordner, **kw: oeffnen.append(pfad) or "modell")
    monkeypatch.setattr(aenderungen.sw, "schliesse", lambda app, model: None)
    monkeypatch.setattr(aenderungen, "soll_parameter", lambda *a: {datei.name: {"L": 100}})
    monkeypatch.setattr(aenderungen, "soll_masse", lambda *a: {})
    monkeypatch.setattr(aenderungen, "soll_teile", lambda *a: {})
    monkeypatch.setattr(aenderungen, "lies_globale_variablen", lambda m: {"L": 100})
    monkeypatch.setattr("swki.bestand.sw_bestand.lies_bestand", lambda app, model: _ist_teil())
    aenderungen.aenderungen(spec_pfad)
    assert len(oeffnen) == 1


def test_manuell_geaendert_nennt_die_aufnahme(umgebung):
    r, spec_pfad = umgebung
    _lauf(r, spec_pfad, 1).write_bytes(b"von Hand geaendert")
    _herkunft(r)
    with pytest.raises(AenderungFehler) as e:
        pruefe_unveraendert(r, "A", spec_pfad)
    assert e.value.daten["code"] == MANUELL_GEAENDERT
    assert e.value.daten["aufnahmen"] == [{"auftrag": "B", "aufnahme": 1}]
    text = str(e.value)
    assert "swki bestand abgleich B --spec" in text and "swki aenderungen" not in text and "--verwerfen" in text


def test_manuell_geaendert_ohne_aufnahme_nennt_den_dritten_weg(umgebung):
    r, spec_pfad = umgebung
    _lauf(r, spec_pfad, 1).write_bytes(b"von Hand geaendert")
    with pytest.raises(AenderungFehler) as e:
        pruefe_unveraendert(r, "A", spec_pfad)
    assert e.value.daten["aufnahmen"] == []
    text = str(e.value)
    assert "swki aenderungen" in text and "swki bestand aufnehmen" in text and "neuen Auftrag" in text
    assert "swki bestand abgleich" not in text


def test_uebernahme_ohne_neue_freigabe_nennt_die_aufnahme_ebenfalls(umgebung):
    r, spec_pfad = umgebung
    freigeben(spec_pfad, GUELTIG, zeitpunkt="2026-10-03T09:00:00")
    datei = _lauf(r, spec_pfad, 1, gestartet="2026-10-03T10:00:00")
    datei.write_bytes(b"von Hand geaendert")
    _herkunft(r)
    with pytest.raises(AenderungFehler) as e:
        pruefe_unveraendert(r, "A", spec_pfad, uebernommen=True)
    assert e.value.daten["aufnahmen"] == [{"auftrag": "B", "aufnahme": 1}]


def test_fremder_lauf_wird_nicht_beschrieben(umgebung, monkeypatch):
    """Weder `aenderungen` noch die Sperre schreiben in den Lauf-Ordner: Inhalt, Größe und Änderungszeit bleiben gleich."""
    r, spec_pfad = umgebung
    datei = _lauf(r, spec_pfad, 1)
    datei.write_bytes(b"von Hand geaendert")
    (datei.parent / "neu.sldprt").write_bytes(b"neu")
    _herkunft(r)
    monkeypatch.setattr(aenderungen, "lade_rechner", lambda: r)
    vorher = _momentaufnahme(datei.parent)
    aenderungen.aenderungen(spec_pfad)
    with pytest.raises(AenderungFehler):
        pruefe_unveraendert(r, "A", spec_pfad)
    assert _momentaufnahme(datei.parent) == vorher
    assert not any(p.name == "herkunft.json" for p in datei.parent.rglob("*"))


# --- soll_teile -----------------------------------------------------------------------------------------------------

def test_soll_teile_eines_teils(umgebung):
    r, spec_pfad = umgebung
    freigeben(spec_pfad, GUELTIG)
    protokoll = {"status": "ok", "knoten": [{"id": "f1", "sw_name": "f1"}]}
    soll = soll_teile(protokoll, spec_pfad, "A", lade_standard())
    assert list(soll) == ["A_Platte_1.sldprt"]
    assert soll["A_Platte_1.sldprt"][0] is protokoll and soll["A_Platte_1.sldprt"][1] == freigegebene_spec(spec_pfad)


def test_soll_teile_einer_baugruppe(tmp_path):
    pfad = schreibe(tmp_path / "A")
    bg = lade_baugruppe(pfad)
    freigeben_baugruppe(bg)
    teile = {datei: {"knoten": [{"id": "f1", "sw_name": datei}]} for datei in bg.teile}
    soll = soll_teile({"knoten": [], "teile": teile}, pfad, "A", lade_standard())
    assert len(soll) == len(teile) and all(n.endswith(".sldprt") for n in soll)
    [(protokoll_teil, spec_teil)] = [v for v in soll.values() if v[0] is teile["platte.yaml"]]
    assert spec_teil == freigegebene_teile(bg)["platte.yaml"]
