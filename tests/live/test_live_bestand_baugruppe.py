"""Live-Tests der Bestandsdateien an der Musterbaugruppe (Spec Bestandsdateien §8, §12; Plan Etappe 2 Task 13): Aufnahme und die Negativfälle
der Plan-Tabelle. Die ganze Revision steht in `tests/referenz/test_bestand.py`. SolidWorks muss laufen, jeder Test auf frischem SolidWorks:

    .venv\\Scripts\\python.exe -m werkzeuge.live_frisch tests/live/test_live_bestand_baugruppe.py tests/referenz/test_bestand.py --zeit 1500

Vorher einmal `-m werkzeuge.bestand_muster hubeinheit`. Das Muster wird nur kopiert: Als Original dient `kollege/` im Testauftrag, dort
geöffnet und gespeichert, damit die gespeicherten Pfade wirklich dorthin zeigen (S18g). Geöffnet und gespeichert wird sonst nur im Lauf."""

import json
import shutil
import stat
from pathlib import Path

import pytest
import yaml

from swki.aenderungen import sha256_datei
from swki.auftrag import lauf_datei, lauf_ordner
from swki.baugruppe import sw_baugruppe
from swki.bestand import ausgabe, bau, bau_baugruppe, befehle
from swki.bestand.ablage import bestand_ordner, lade_aufnahme
from swki.bestand.fehler import (BESTAND_ORIGINAL_GEAENDERT, BESTAND_PFAD_FREMD, BESTAND_REFERENZ_EXTERN, VERKNUEPFUNGEN_FEHLEN)
from swki.bestand.pfade import oeffne_in
from swki.bestand.pruefen import pruefen
from swki.bestand.spec import freigeben, validieren
from swki.bestand.sw_bestand import eigenschaften_von, whats_wrong
from swki.compiler import sw
from swki.compiler.bauen import BauAbbruch
from swki.konfig import PROJEKT, lade_rechner
from swki.pruefung.messen import oeffne
from swki.spec.laden import SpecFehler
from swki.verbindung import byref_long, mm, r8_array, verbinde
from werkzeuge.bestand_muster import (HUB_DATEIEN, HUB_KOMPONENTEN, HUB_LAGE, HUB_STATUS, HUB_VERKNUEPFUNGEN, HUBEINHEIT, KONFIG_OHNE, SW_MASS,
                                      TEILE_HUB, hubeinheit_ordner)

pytestmark = pytest.mark.sw
AUFTRAG = "LIVE-BESTAND-BG"
REFERENZ = PROJEKT / "tests" / "referenz" / "bestand"
SPEC = REFERENZ / "hubeinheit_rev.yaml"
KLEMMSCHRAUBE = ("p3", "v1", "v2")  # Punkte der Referenz
SW_WARNUNG_NEUAUFBAU = 32  # swFileLoadWarning_NeedsRegen: Teil neben alter Baugruppe (S18g)
SW_OEFFNEN_STILL_VOLL = 1 | 64  # swOpenDocOptions_e: Silent, OverrideDefaultLoadLightweight
SW_DOC_BAUGRUPPE = 2


def _sichere(app, model) -> None:
    fehler, warnungen = byref_long(), byref_long()
    assert model.Save3(sw.SW_SAVEAS_SILENT, fehler, warnungen) and not fehler.value, fehler.value


def _kollege(r, auftrag: str) -> Path:
    """Die Dateien des Kollegen: Kopie des Musters, erst die Unterbaugruppe, dann die Hauptbaugruppe hier gespeichert."""
    ordner = r.arbeitsordner / auftrag / "kollege"
    quelle = hubeinheit_ordner(r)
    for rel in HUB_DATEIEN:
        (ordner / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle / rel, ordner / rel)
        (ordner / rel).chmod(stat.S_IWRITE)
    app = verbinde(r.sw_jahr)
    for name in ("Muster.SLDASM", HUBEINHEIT):
        model = oeffne(app, ordner / name, voll=True)
        try:
            _sichere(app, model)
        finally:
            sw.schliesse(app, model)
    return ordner


def _spec_daten(punkte: list[dict], a: dict, bereiche=(), kollision_erlaubt=()) -> dict:
    spec = {"art": "aenderung", "name": "Hubeinheit_Fall", "bestand": {"datei": a["datei"]["name"], "sha256": a["datei"]["sha256"], "aufnahme": 1},
            "punkte": punkte, "bereiche": list(bereiche)}
    return spec | ({"kollision_erlaubt": list(kollision_erlaubt)} if kollision_erlaubt else {})


def _schreibe(tmp_path, auftrag: str, spec: dict, name: str = "fall") -> Path:
    ordner = tmp_path / auftrag
    ordner.mkdir(exist_ok=True)
    shutil.copy2(REFERENZ / "anschlag_neu.yaml", ordner)
    pfad = ordner / f"{name}.yaml"
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def _freigegeben(tmp_path, auftrag: str, spec: dict, name: str = "fall") -> Path:
    """Spec im Auftragsordner, validiert und für diesen Test freigegeben."""
    pfad = _schreibe(tmp_path, auftrag, spec, name)
    validieren(pfad)
    freigeben(pfad)
    return pfad


def _eigenschaft(a: dict) -> dict:
    """Ein Punkt, der nur die Hauptbaugruppe speichert: Der Lauf entsteht, alles Weitere geschieht von Hand danach."""
    return _spec_daten([{"id": "p1", "typ": "eigenschaft", "name": "Revision", "neu": "B"}], a)


def _aufgenommen(r, auftrag: str) -> tuple[Path, dict]:
    kollege = _kollege(r, auftrag)
    befehle.aufnehmen(kollege / HUBEINHEIT, auftrag)
    return kollege, lade_aufnahme(r, auftrag, 1)


def _referenz_punkte(*ids: str) -> list[dict]:
    punkte = yaml.safe_load(SPEC.read_text(encoding="utf-8"))["punkte"]
    return [p for p in punkte if p["id"] in ids]


@pytest.fixture
def r():
    return lade_rechner()


def _im_lauf(r, spec: Path, nummer: int, rel: str, aendern) -> None:
    """Eine Handänderung im Lauf, nach dem Bau: Der Bericht soll sie finden."""
    ordner = lauf_ordner(r, spec.parent.name, nummer)
    app = verbinde(r.sw_jahr)
    model = oeffne_in(app, ordner / rel, ordner, sichtbar=True, nur_lesen=False)
    try:
        aendern(app, model)
        _sichere(app, model)
    finally:
        sw.schliesse(app, model)


def _maengel(b: dict) -> list[str]:
    return [m["pruefung"] for m in b["maengel"]]


def _geprueft_abgenommen(spec: Path) -> int:
    """Lauf bauen und prüfen, ohne Mangel; das Urteil des Prüfers steht hier als Datei da."""
    nummer = bau.bauen(spec)["lauf"]
    b = pruefen(spec)
    assert b["bestanden"] is True and b["maengel"] == [], b["maengel"]
    lauf_datei(spec, nummer, "pruefer").write_text(json.dumps({"bestanden": True, "maengel": []}), encoding="utf-8")
    return nummer


# ---------------------------------------------------------------------------------------------------------------------- Aufnahme

def test_aufnahme_der_musterbaugruppe(auftrag, r):
    kollege = _kollege(r, auftrag)
    original = {rel: sha256_datei(kollege / rel) for rel in HUB_DATEIEN}
    aus = befehle.aufnehmen(kollege / HUBEINHEIT, auftrag)
    a = lade_aufnahme(r, auftrag, 1)
    assert {rel: sha256_datei(kollege / rel) for rel in HUB_DATEIEN} == original
    assert {rel: sha256_datei(bestand_ordner(r, auftrag, 1) / rel) for rel in HUB_DATEIEN} == original
    assert a["art"] == "baugruppe" and set(a["konfigurationen"]) == {"Standard", KONFIG_OHNE} and a["aktiv"] == "Standard"
    assert set(a["dateien"]) == set(HUB_DATEIEN) - {HUBEINHEIT} and a["dateien"][TEILE_HUB[0]]["art"] == "teil"
    assert a["dateien"]["Muster.SLDASM"]["art"] == "baugruppe"
    assert set(HUB_KOMPONENTEN) <= set(a["komponenten"]) and set(HUB_VERKNUEPFUNGEN) == set(a["verknuepfungen"])
    for name, lage in HUB_LAGE.items():
        t = a["komponenten"][name]["transform"]["Standard"]
        assert [round(x * 1000, 3) for x in t[9:12]] == pytest.approx(list(lage), abs=0.01), name
        assert a["komponenten"][name]["status"]["Standard"] == HUB_STATUS[name], name
    assert a["komponenten"]["Anschlag-1"]["datei"] == a["komponenten"]["Anschlag-2"]["datei"] == TEILE_HUB[2]
    assert a["komponenten"]["Muster-1"]["unterdrueckt"] == {"Standard": False, KONFIG_OHNE: True}
    assert a["komponenten"]["Muster-1"]["transform"][KONFIG_OHNE] is None
    hub = a["verknuepfungen"]["Hub"]
    assert (hub["grenze"], hub["min"], hub["max"]) == (True, 0.0, 25.0) and hub["partner"] == ["Schlitten-1", "Grundplatte-1"]
    assert a["verknuepfungen"]["Schlitten Seite"]["grenze"] is False and a["verknuepfungen"]["Schlitten Seite"]["wert"] == pytest.approx(15)
    assert None in a["verknuepfungen"]["Antrieb vorne"]["partner"]  # Ebene der Hauptbaugruppe
    assert any("/" in p for p in a["verknuepfungen"]["Antrieb Abstand"]["partner"])  # Partner in der Unterbaugruppe
    assert a["bewegungen"]["Hub"]["gefahren"] is True and a["bewegungen"]["Hub"]["bewegt"] == ["Schlitten-1"]
    assert a["kollisionen"] == [] and a["neuaufbau"] == []
    assert [w for w in a["warnungen"] if w["code"] == "VERKNUEPFUNG_UNERREICHT"] == []
    assert aus["zaehler"]["grenzen"] == 1 and verbinde(r.sw_jahr).GetDocuments in (None, ())
    assert befehle.aufnehmen(kollege / HUBEINHEIT, auftrag)["neu"] is False


def test_bestand_gegen_bestand_ohne_punkt_ist_unveraendert(auftrag, tmp_path, r):
    """Eine unveränderte Baugruppe muss sich selbst beweisen, ohne `ok: None`: Sonst verdeckt ein Fehlalarm jeden echten Befund (Task 7)."""
    _, a = _aufgenommen(r, auftrag)
    spec = _freigegeben(tmp_path, auftrag, _eigenschaft(a))
    bau.bauen(spec)
    b = pruefen(spec)
    assert b["bestanden"] is True and b["maengel"] == [], b["maengel"]
    assert all(e["ok"] is True for e in b["pruefungen"]), [e for e in b["pruefungen"] if e["ok"] is not True]
    assert set(b["dateien"]["geaendert"]) == {HUBEINHEIT}


# ------------------------------------------------------------------------------------------------------------------- Negativfälle

def test_datei_fehlt_im_lauf_laedt_nicht_vom_original(auftrag, tmp_path, r, monkeypatch):
    """Plan Review Focus 3: Original liegt am gespeicherten Pfad, die Datei fehlt im Lauf. Sperre 1 greift, geöffnet wird nichts."""
    kollege, a = _aufgenommen(r, auftrag)
    original = sha256_datei(kollege / TEILE_HUB[1])
    spec = _freigegeben(tmp_path, auftrag, _eigenschaft(a))
    echte = bau_baugruppe.lauf_kopie_alle

    def ohne_schlitten(quelle, dateien, lauf):
        pfad = echte(quelle, dateien, lauf)
        (lauf / TEILE_HUB[1]).unlink()
        return pfad

    monkeypatch.setattr(bau_baugruppe, "lauf_kopie_alle", ohne_schlitten)
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(spec)
    assert e.value.daten["fehler"]["code"] == BESTAND_PFAD_FREMD, e.value.daten
    ordner = Path(e.value.daten["ordner"])
    assert sha256_datei(ordner / HUBEINHEIT) == a["datei"]["sha256"]  # nichts gespeichert
    assert sha256_datei(kollege / TEILE_HUB[1]) == original and verbinde(r.sw_jahr).GetDocuments in (None, ())


def test_von_hand_verschobene_komponente(auftrag, tmp_path, r):
    """Verschiebbar ist nur, was keine Verknüpfung hält: Der Schlitten ist voll bestimmt, `Hub` stellt ihn beim Neuaufbau auf
    seinen Wert 0 zurück, auch innerhalb 0…25 (Task 13 live). Die fixierte Grundplatte nimmt eine neue Lage an, alles auf ihr
    wandert mit."""
    _, a = _aufgenommen(r, auftrag)
    spec = _freigegeben(tmp_path, auftrag, _eigenschaft(a))
    nummer = bau.bauen(spec)["lauf"]
    z = {}

    def hebe(app, asm):
        k = next(x for x in asm.GetComponents(True) if x.Name2 == "Grundplatte-1")
        t = list(k.Transform2.ArrayData)
        t[11] += mm(10)
        k.Transform2 = sw.mathutil(app).CreateTransform(r8_array(t))
        assert asm.EditRebuild3
        z.update({x.Name2: x.Transform2.ArrayData[11] for x in asm.GetComponents(True)})

    _im_lauf(r, spec, nummer, HUBEINHEIT, hebe)
    assert (z["Grundplatte-1"], z["Schlitten-1"]) == pytest.approx((mm(10), mm(25))), z  # die Handänderung ist wirklich geschehen
    b = pruefen(spec)
    assert b["bestanden"] is False and "lage" in _maengel(b), b["maengel"]
    lage = next(e for e in b["pruefungen"] if e["id"] == "lage")
    assert {"Grundplatte-1", "Schlitten-1"} <= {q["komponente"] for q in lage["ist"]}, lage


def test_von_hand_geloeschte_verknuepfung(auftrag, tmp_path, r):
    _, a = _aufgenommen(r, auftrag)
    spec = _freigegeben(tmp_path, auftrag, _eigenschaft(a))
    nummer = bau.bauen(spec)["lauf"]

    def loesche(app, asm):
        sw_baugruppe.loesche(asm, next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "Hub"))

    _im_lauf(r, spec, nummer, HUBEINHEIT, loesche)
    b = pruefen(spec)
    assert {"verknuepfungen", "bewegung:Hub"} <= set(_maengel(b)), b["maengel"]


def test_neue_schraube_kollidiert_ohne_erlaubnis(auftrag, tmp_path, r):
    _, a = _aufgenommen(r, auftrag)
    spec = _freigegeben(tmp_path, auftrag, _spec_daten(_referenz_punkte(*KLEMMSCHRAUBE), a))
    bau.bauen(spec)
    b = pruefen(spec)
    assert "kollision" in _maengel(b), b["maengel"]


def test_neue_schraube_mit_erlaubnis_besteht(auftrag, tmp_path, r):
    """Gegenprobe zum Fall davor: Nur das genannte Paar ist frei."""
    _, a = _aufgenommen(r, auftrag)
    erlaubt = [{"paar": ["p3", "Schlitten-1"], "grund": "Schraube im Kernloch"}]
    spec = _freigegeben(tmp_path, auftrag, _spec_daten(_referenz_punkte(*KLEMMSCHRAUBE), a, kollision_erlaubt=erlaubt))
    bau.bauen(spec)
    b = pruefen(spec)
    assert b["bestanden"] is True, b["maengel"]
    assert next(e for e in b["pruefungen"] if e["id"] == "bewegung:Hub")["ok"] is True  # die Schraube darf mitfahren


def test_neue_komponente_blockiert_die_grenze(auftrag, tmp_path, r):
    """Ein weiterer Anschlag im Weg des Schlittens: bei x = -20 steht er still daneben, ab 10 mm Hub trifft ihn der Schlitten.
    Der Abstand zählt in Richtung der Flächennormalen (Task 13 live: 80 mm von der linken Stirn der Grundplatte lagen bei
    x = -180, neben der Platte), darum 40 mm von der linken Stirn von Anschlag-1 (x = 20). Die Lage wird nachgemessen, sonst
    bestünde der Test mit einem Anschlag außerhalb des Wegs."""
    _, a = _aufgenommen(r, auftrag)
    k = "k1"
    punkte = [{"id": k, "typ": "komponente_neu", "wie": "Anschlag-1"},
              {"id": "b1", "typ": "verknuepfung_neu", "art": "deckungsgleich", "a": {"komponente": k, "ebene": "vorne"},
               "b": {"komponente": "Grundplatte-1", "feature": "Aufsatz-Linear austragen1", "flaeche": "+z"}},
              {"id": "b2", "typ": "verknuepfung_neu", "art": "deckungsgleich", "a": {"komponente": k, "ebene": "oben"},
               "b": {"komponente": "Grundplatte-1", "ebene": "oben"}},
              {"id": "b3", "typ": "verknuepfung_neu", "art": "abstand", "wert": 40, "a": {"komponente": k, "ebene": "rechts"},
               "b": {"komponente": "Anschlag-1", "nahe": [-10, 0, 15]}}]
    spec = _freigegeben(tmp_path, auftrag, _spec_daten(punkte, a))
    erg = bau.bauen(spec)
    name = next(x["sw_name"] for x in erg["knoten"] if x["id"] == k)
    ordner = lauf_ordner(r, auftrag, erg["lauf"])
    app = verbinde(r.sw_jahr)
    asm = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=False, nur_lesen=True)
    try:
        lage = next(x for x in asm.GetComponents(True) if x.Name2 == name).Transform2.ArrayData[9:12]
    finally:
        sw.schliesse(app, asm)
    assert [round(c * 1000, 3) for c in lage] == pytest.approx([-20, 0, 15], abs=0.01), lage
    b = pruefen(spec)
    assert {"bewegung_kollision:Hub", "bewegung:Hub"} & set(_maengel(b)), b["maengel"]


def test_unbeteiligtes_teil_gespeichert(auftrag, tmp_path, r):
    _, a = _aufgenommen(r, auftrag)
    spec = _freigegeben(tmp_path, auftrag, _eigenschaft(a))
    nummer = bau.bauen(spec)["lauf"]

    def eigenschaft(app, model):
        model.Extension.CustomPropertyManager("").Add3("Notiz", 30, "von Hand", 2)

    _im_lauf(r, spec, nummer, TEILE_HUB[2], eigenschaft)
    b = pruefen(spec)
    assert "dateien" in _maengel(b), b["maengel"]
    e = next(x for x in b["pruefungen"] if x["id"] == "dateien")
    assert TEILE_HUB[2] in e["geaendert"]


def test_entfernen_ohne_alle_verknuepfungen(auftrag, tmp_path, r):
    _, a = _aufgenommen(r, auftrag)
    punkte = [{"id": "p1", "typ": "komponente_entfernen", "komponente": "Anschlag-2", "verknuepfungen": ["Anschlag2 Auflage", "Anschlag2 Mitte"]}]
    with pytest.raises(SpecFehler) as e:
        validieren(_schreibe(tmp_path, auftrag, _spec_daten(punkte, a)))
    assert VERKNUEPFUNGEN_FEHLEN in [b.get("code") for b in e.value.daten["befunde"]]


def _abgeleitetes_teil(r, kollege: Path) -> str:
    """Ein abgeleitetes Teil (IPartDoc.InsertPart3) in der Baugruppe des Kollegen: `InsertPart3` schreibt die Referenz aufs Anschlag-Teil."""
    app = verbinde(r.sw_jahr)
    rel = "teile/Abgeleitet.SLDPRT"
    neu = app.NewDocument(str(r.vorlage_teil), 0, 0, 0)
    assert neu.InsertPart3(str(kollege / TEILE_HUB[2]), 1, "") is not None
    sw.speichere(neu, kollege / rel)
    asm = oeffne(app, kollege / HUBEINHEIT, voll=True)
    try:
        assert asm.AddComponent5(str(kollege / rel), 0, "", False, "", 0.0, mm(-100), mm(50)) is not None
        _sichere(app, asm)
    finally:
        sw.schliesse(app, asm)
        sw.schliesse(app, neu)
    return rel


def test_punkt_auf_teil_mit_referenz(auftrag, tmp_path, r):
    kollege = _kollege(r, auftrag)
    rel = _abgeleitetes_teil(r, kollege)
    befehle.aufnehmen(kollege / HUBEINHEIT, auftrag)
    a = lade_aufnahme(r, auftrag, 1)
    assert a["dateien"][rel]["referenzen"] == [TEILE_HUB[2]]
    punkte = [{"id": "p1", "typ": "eigenschaft", "in_datei": rel, "name": "Revision", "neu": "B"}]
    with pytest.raises(SpecFehler) as e:
        validieren(_schreibe(tmp_path, auftrag, _spec_daten(punkte, a)))
    assert BESTAND_REFERENZ_EXTERN in [b.get("code") for b in e.value.daten["befunde"]]


def _teil_und_haupt(a: dict) -> dict:
    """Eine Teil-Änderung und ein Haupt-Punkt: Beide Dateien gehen in die Ausgabe."""
    p = _referenz_punkte("p2")
    return _spec_daten([*p, {"id": "p9", "typ": "eigenschaft", "name": "Revision", "neu": "B"}], a,
                       bereiche=[{"punkte": ["p2"], "in_datei": TEILE_HUB[1], "box": {"min": [30, -25, 0], "max": [40, 25, 20]}}]) | {"parameter": {"L_NEU": 70}}


def test_original_nach_der_aufnahme_geaendert(auftrag, tmp_path, r):
    kollege, a = _aufgenommen(r, auftrag)
    spec = _freigegeben(tmp_path, auftrag, _teil_und_haupt(a))
    _geprueft_abgenommen(spec)
    assert BESTAND_ORIGINAL_GEAENDERT not in [w["code"] for w in ausgabe.ausgabe(spec)["warnungen"]]
    (kollege / TEILE_HUB[1]).write_bytes((kollege / TEILE_HUB[1]).read_bytes() + b"Kollege")
    warnungen = ausgabe.ausgabe(spec)["warnungen"]
    assert [w.get("datei") for w in warnungen if w["code"] == BESTAND_ORIGINAL_GEAENDERT] == [TEILE_HUB[1]]


def test_rueckweg_neben_kopie_der_originale(auftrag, tmp_path, r):
    """Spec §8.3: Eine geänderte Hauptbaugruppe trägt Lauf-Pfade. Neben eine Kopie der Originale gelegt, lädt sie von dort; nur Warnung 32."""
    kollege, a = _aufgenommen(r, auftrag)
    spec = _freigegeben(tmp_path, auftrag, _teil_und_haupt(a))
    _geprueft_abgenommen(spec)
    erg = ausgabe.ausgabe(spec)
    assert {d["datei"] for d in erg["dateien"]} == {HUBEINHEIT, TEILE_HUB[1]}
    ziel = r.arbeitsordner / auftrag / "zurueck"
    shutil.copytree(kollege, ziel)
    for d in erg["dateien"]:
        shutil.copy2(d["ausgabe"], ziel / d["datei"])
    app = verbinde(r.sw_jahr)
    fehler, warnungen = byref_long(), byref_long()
    asm = app.OpenDoc6(str(ziel / HUBEINHEIT), SW_DOC_BAUGRUPPE, SW_OEFFNEN_STILL_VOLL, "", fehler, warnungen)
    assert asm is not None, fehler.value
    try:
        assert warnungen.value & ~SW_WARNUNG_NEUAUFBAU == 0, warnungen.value
        for k in asm.GetComponents(False):
            assert Path(k.GetPathName).resolve().is_relative_to(ziel.resolve()), k.GetPathName
        assert asm.ForceRebuild3(False) and whats_wrong(asm) == []
        assert eigenschaften_von(asm, "")["Revision"] == "B"
        schlitten = next(k for k in asm.GetComponents(True) if k.Name2 == "Schlitten-1")
        assert schlitten.GetModelDoc2.Parameter("D1@Skizze1").SystemValue == pytest.approx(mm(70))
    finally:
        sw.schliesse(app, asm)


def test_grenze_nur_in_einer_konfiguration_wird_abgewiesen(auftrag, tmp_path, r):
    """Spec §8.2 (S19e T9.27): `ModifyDefinition` setzt eine Grenze in allen Konfigurationen, also weist `validieren` einen
    Grenz-Punkt mit `konfigurationen` ungleich `alle` ab; je Konfiguration nur über `skript`. Ohne `konfigurationen` ist derselbe
    Punkt gültig."""
    _, a = _aufgenommen(r, auftrag)
    punkt = {"id": "p1", "typ": "verknuepfung_wert", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30}
    with pytest.raises(SpecFehler) as e:
        validieren(_schreibe(tmp_path, auftrag, _spec_daten([punkt | {"konfigurationen": ["Standard"]}], a)))
    assert [b["pfad"] for b in e.value.daten["befunde"]] == ["punkte[0].konfigurationen"], e.value.daten["befunde"]
    assert validieren(_schreibe(tmp_path, auftrag, _spec_daten([punkt], a)))["gueltig"] is True


def test_abstand_ueber_d1_in_allen_konfigurationen(auftrag, tmp_path, r):
    _, a = _aufgenommen(r, auftrag)
    punkte = [{"id": "p1", "typ": "verknuepfung_wert", "verknuepfung": "Schlitten Seite", "alt": 15, "neu": 16, "lage_folgen": ["Schlitten-1"]}]
    spec = _freigegeben(tmp_path, auftrag, _spec_daten(punkte, a))
    nummer = bau.bauen(spec)["lauf"]
    b = pruefen(spec)
    assert b["bestanden"] is True, b["maengel"]
    app = verbinde(r.sw_jahr)
    asm = oeffne_in(app, lauf_ordner(r, auftrag, nummer) / HUBEINHEIT, lauf_ordner(r, auftrag, nummer), sichtbar=False, nur_lesen=True)
    try:
        mate = next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "Schlitten Seite")
        assert mate.Parameter(SW_MASS).SystemValue == pytest.approx(mm(16))
    finally:
        sw.schliesse(app, asm)
