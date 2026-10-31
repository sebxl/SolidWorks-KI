"""Live-Tests der Bestandsaufnahme am Musterteil (Spec Bestandsdateien §5, §12). SolidWorks muss laufen; das Muster dient als
Original und wird nur gelesen, geöffnet und gespeichert wird nur unter dem Arbeitsordner."""

import json
import math
import shutil
import stat
from pathlib import Path

import pytest
import yaml

from swki.aenderungen import pruefe_unveraendert, sha256_datei
from swki.auftrag import lauf_datei
from swki.bestand import ausgabe, bau, befehle
from swki.bestand.ablage import bestand_ordner, lade_aufnahme
from swki.bestand.fehler import BESTAND_ALTWERT, BESTAND_ORIGINAL_GEAENDERT, BESTAND_REFERENZ_EXTERN, MASS_GESTEUERT, BestandFehler
from swki.bestand.pruefen import pruefen
from swki.bestand.spec import freigeben, validieren
from swki.bestand.sw_bestand import _geometrie, bstr_array, lies_bestand, whats_wrong
from swki.compiler import sw
from swki.compiler.bauen import BauAbbruch
from swki.konfig import PROJEKT, lade_rechner
from swki.pruefung.messen import oeffne
from swki.spec.laden import SpecFehler
from swki.verbindung import byref_long, verbinde

pytestmark = pytest.mark.sw
REFERENZ = PROJEKT / "tests" / "referenz" / "bestand"
MUSTER = REFERENZ / "muster" / "Lagerdeckel.SLDPRT"
AUFTRAG = "LIVE-BESTAND"
SW_UNTERDRUECKEN, SW_BENANNT = 0, 3  # swFeatureSuppressionAction_e, swInConfigurationOpts_e
SW_DOC_BAUGRUPPE = 2  # swDocumentTypes_e
SW_OEFFNEN_STILL_VOLL = 1 | 64  # swOpenDocOptions_Silent | OverrideDefaultLoadLightweight (S18g: sonst GetModelDoc2 = None)
SW_WARNUNG_ID, SW_WARNUNG_REFERENZ_FEHLT = 1, 1048576  # swFileLoadWarning_e: IdMismatch, MissingExternalReferences
SW_KOMPONENTE_ID_FALSCH = 5  # swComponentSuppressionState_e.swComponentInternalIdMismatch


def test_aufnahme_musterteil(auftrag):
    r = lade_rechner()
    sha = sha256_datei(MUSTER)
    aus = befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(r, auftrag, 1)
    assert sha256_datei(MUSTER) == sha == a["datei"]["sha256"]
    assert a["datei"]["version_aelter"] is False and a["sw_jahr"] == r.sw_jahr
    assert (a["konfigurationen"], a["aktiv"]) == (["Standard", "Variante B"], "Standard") and a["tabelle"] is False
    assert a["einheitensystem"] == 5 and a["material"].startswith("1.0038") and a["externe_referenzen"] == []
    assert a["eigenschaften"]["datei"]["Benennung"] == "Lagerdeckel" and a["eigenschaften"]["konfiguration"]["Variante B"]

    assert a["variablen"] == {"L": 100.0}
    assert {g["links"]: g["global"] for g in a["gleichungen"]} == {"L": True, "D1@Skizze1": False}

    masse = {m["name"]: m for m in a["masse"]}
    assert len(masse) == len(a["masse"])  # Dubletten aus Skizze und Feature zusammengelegt
    m = masse["D1@Skizze1"]
    assert (m["zustand"], m["quelle"], m["werte"]) == ("gesteuert", {"art": "variable", "name": "L"},
                                                       {"Standard": 100.0, "Variante B": 100.0})
    assert masse["D5@Skizze2"]["zustand"] == "getrieben"
    assert masse["D2@Skizze3"]["zustand"] == "treibend" and len(masse["D2@Skizze3"]["punkte"]) == 2
    assert {masse["Bohrung_D@Skizze3"]["gruppe"], masse["Bohrung_D@Skizze4"]["gruppe"]} == {"Bohrung_D"}
    assert masse["Bohrung_D@Skizze3"]["zustand"] == "treibend" and masse["Bohrung_D@Skizze4"]["werte"]["Standard"] == 8.0
    assert masse["D2@Fase1"]["einheit"] == "Grad" and masse["D2@Fase1"]["werte"]["Standard"] == 45.0

    # Abweichung vom Brief nach S18b: Maße unterdrückter Features sind lesbar, `werte` bleibt eine Zahl
    features = {f["name"]: f for f in a["features"]}
    assert features["Fase1"]["unterdrueckt"] == {"Standard": False, "Variante B": True}
    assert masse["D1@Fase1"]["werte"] == {"Standard": 2.0, "Variante B": 2.0}
    assert features["Skizze1"]["kinder"] == ["Aufsatz-Linear austragen1"] and "Skizze1" in features["Aufsatz-Linear austragen1"]["eltern"]
    assert not any(f["typ"].endswith("Folder") for f in a["features"])
    assert a["reihenfolge"]["Standard"] == a["reihenfolge"]["Variante B"] == [f["name"] for f in a["features"]]

    assert a["skizzen"]["Skizze5"] == 2 and a["skizzen"]["Skizze1"] == 3 and aus["skizzen_offen"] == {"Skizze5": 2}
    assert a["neuaufbau"] == []
    assert a["geometrie"]["Standard"]["volumen"] == pytest.approx(106239.381, abs=0.01)
    assert a["geometrie"]["Variante B"]["volumen"] == pytest.approx(106439.381, abs=0.01)
    assert a["geometrie"]["Standard"]["koerper"] == 1 and a["geometrie"]["Standard"]["box"][3] == pytest.approx(50.0)

    ordner = bestand_ordner(r, auftrag, 1)
    kopie = ordner / MUSTER.name
    assert sha256_datei(kopie) == sha and not kopie.stat().st_mode & stat.S_IWRITE
    assert {p.name for p in (ordner / "bilder").iterdir()} == {"iso.png", "vorne.png", "oben.png", "rechts.png"}

    z = befehle.zeige(auftrag, "D2@Skizze3", None)
    assert Path(z["bild"]).stat().st_size > 0
    f = befehle.zeige(auftrag, None, "Schnitt-Linear austragen2")
    assert Path(f["bild"]).stat().st_size > 0
    assert sha256_datei(kopie) == sha

    assert befehle.aufnehmen(MUSTER, auftrag)["neu"] is False


def test_verknuepfte_gleichungen_lehnt_aufnehmen_ab(auftrag):
    """Spec §3: Eine Kopie des Musters wird mit einer Gleichungsdatei verknüpft (`LinkToFile` wirkt erst nach `FilePath`, laut Index). Die
    Aufnahme lehnt sie ab und nennt die Datei."""
    r = lade_rechner()
    ordner = r.arbeitsordner / auftrag / "verknuepft"
    ordner.mkdir(parents=True)
    kollege = ordner / MUSTER.name
    shutil.copy2(MUSTER, kollege)
    datei = ordner / "gleichungen.txt"
    datei.write_text('"L"= 100\n"D1@Skizze1" = "L"\n', encoding="utf-8")
    app = verbinde(r.sw_jahr)
    model = oeffne(app, kollege, sichtbar=False)
    try:
        gleichungen = model.GetEquationMgr
        gleichungen.FilePath = str(datei)
        gleichungen.LinkToFile = True
        fehler, warnungen = byref_long(), byref_long()
        assert model.Save3(sw.SW_SAVEAS_SILENT, fehler, warnungen) and not fehler.value, fehler.value
    finally:
        sw.schliesse(app, model)
    with pytest.raises(BestandFehler) as e:
        befehle.aufnehmen(kollege, auftrag)
    assert e.value.daten["code"] == BESTAND_REFERENZ_EXTERN
    assert [Path(p).name for p in e.value.daten["referenzen"]] == [datei.name], e.value.daten


TASCHE = "D1@Schnitt-Linear austragen1"
NORMBOHRUNG = {"typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [45, 0, 20]},
               "positionen": [["=-50+RA", 24], ["=-50+RA", -24]], "bezug": {"u": "-rand", "v": "mitte"}, "tiefe": 10, "gewindetiefe": 8}


def _schreibe_spec(tmp_path, auftrag: str, a: dict, punkte: list[dict], name="aenderung", box=([-60, -40, -1], [70, 40, 30]),
                   pruefung=None, features=None) -> Path:
    pfad = tmp_path / auftrag / f"{name}.yaml"
    pfad.parent.mkdir(exist_ok=True)
    spec = {"art": "aenderung", "name": "Lagerdeckel_Rev",
            "bestand": {"datei": a["datei"]["name"], "sha256": a["datei"]["sha256"], "aufnahme": 1}, "parameter": {"RA": 12},
            "punkte": punkte, "bereiche": [{"punkte": [p["id"] for p in punkte], "box": {"min": box[0], "max": box[1]}}]}
    if pruefung:
        spec["pruefung"] = pruefung
    if features:
        spec["bereiche"] = [{"punkte": [p["id"] for p in punkte], "features": features}]
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


def _aenderung(tmp_path, auftrag: str, a: dict, punkte: list[dict], **optionen) -> Path:
    """Spec im Auftragsordner, validiert und für diesen Test freigegeben."""
    pfad = _schreibe_spec(tmp_path, auftrag, a, punkte, **optionen)
    validieren(pfad)
    freigeben(pfad)
    return pfad


def _lies_lauf(datei: Path) -> dict:
    app = verbinde(lade_rechner().sw_jahr)
    model = oeffne(app, datei, sichtbar=False, nur_lesen=True)
    try:
        return lies_bestand(app, model)
    finally:
        sw.schliesse(app, model)


def test_bau_mass_und_normbohrung(auftrag, tmp_path):
    """Brief Step 8: alle Punktarten, die den Kern tragen; die Lauf-Datei wird neu geöffnet und gelesen."""
    r = lade_rechner()
    sha = sha256_datei(MUSTER)
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(r, auftrag, 1)
    kopie = bestand_ordner(r, auftrag, 1) / MUSTER.name
    punkte = [{"id": "p1", "typ": "mass", "was": "Tasche tiefer", "mass": TASCHE, "alt": 8, "neu": 9},
              {"id": "p2", "typ": "gleichung", "was": "Länge", "variable": "L", "alt": 100, "neu": 110, "folgen": ["D1@Skizze1"]},
              {"id": "p3", "typ": "mass", "was": "Beide Bohrungen", "mass": "Bohrung_D@Skizze3", "alt": 8, "neu": 9,
               "folgen": ["Bohrung_D@Skizze4"]},
              {"id": "p4", "typ": "unterdruecken", "was": "Fase weg", "feature": "Fase1", "konfigurationen": ["Standard"]},
              {"id": "p5", "typ": "feature", "was": "Gewinde", "name": "Gewinde M6 Deckel", "feature": NORMBOHRUNG,
               "nach": "Schnitt-Linear austragen3"},
              {"id": "p6", "typ": "material", "neu": "1.4301"},
              {"id": "p7", "typ": "eigenschaft", "name": "Revision", "neu": "B"},
              {"id": "p8", "typ": "skript", "datei": "skripte/p8.py", "luecke": "Skizze bemaßen (Review: ctx.pfad)"}]
    skript = tmp_path / auftrag / "skripte" / "p8.py"
    skript.parent.mkdir(parents=True)
    skript.write_text('def bauen(ctx):\n    ctx.skizze({"nahe": [45, 0, 20]}, [{"kreis": {"mitte": [45, 10], "durchmesser": 3}}])\n',
                      encoding="utf-8")
    aus = bau.bauen(_aenderung(tmp_path, auftrag, a, punkte))

    datei = Path(aus["dateien"]["teil"])
    assert aus["status"] == "ok" and datei.name == MUSTER.name  # Teil heißt wie das Original
    assert sha256_datei(MUSTER) == sha and sha256_datei(kopie) == sha and sha256_datei(datei) != sha
    n = _lies_lauf(datei)
    assert n["aktiv"] == "Standard" and n["neuaufbau"] == [] and n["variablen"] == {"L": 110.0}
    assert len(n["gleichungen"]) == len(a["gleichungen"])  # keine neuen Gleichungen
    masse = {m["name"]: m["werte"] for m in n["masse"]}
    assert masse[TASCHE] == {"Standard": 9.0, "Variante B": 9.0}
    assert masse["D1@Skizze1"] == {"Standard": 110.0, "Variante B": 110.0}
    assert masse["Bohrung_D@Skizze4"] == {"Standard": 9.0, "Variante B": 9.0}
    features = {f["name"]: f for f in n["features"]}
    assert features["Fase1"]["unterdrueckt"] == {"Standard": True, "Variante B": True}
    neu = features["Gewinde M6 Deckel"]
    assert neu["unterdrueckt"] == {"Standard": False, "Variante B": False} and "Gewinde M6 Deckel Skizze" in features
    for k in n["konfigurationen"]:
        reihe = n["reihenfolge"][k]
        assert reihe.index("Gewinde M6 Deckel") == reihe.index("Schnitt-Linear austragen3") + 1, k
    assert set(n["materialien"].values()) == {"1.4301 (X5CrNi18-10)"}
    assert n["eigenschaften"]["datei"]["Revision"] == "B"
    # Fase in beiden Konfigurationen weg: gleiche Geometrie, in beiden die neuen Bohrungen
    assert n["geometrie"]["Standard"]["volumen"] == pytest.approx(n["geometrie"]["Variante B"]["volumen"], abs=0.01)

    protokoll = json.loads((datei.parent / "protokoll.json").read_text(encoding="utf-8"))
    assert protokoll["sha256"] == {MUSTER.name: sha256_datei(datei)}
    assert protokoll["lizenz"]["sitzung"]["name"].startswith("swLicenseType_")
    knoten = {k["id"]: k for k in protokoll["knoten"]}
    assert len(knoten["p5"]["punkte"]) == 2 and knoten["p1"]["masse"][0]["wert"] == 9
    assert all(m["name"].endswith("@Gewinde M6 Deckel Skizze") for m in knoten["p5"]["masse"] if m["art"] == "lage")
    assert {m["pfad"] for m in knoten["p8"]["masse"]} == {"punkte[p8]"} and "p8_skizze" in features


def test_bau_mit_variante_b_aktiv(auftrag, tmp_path):
    """Plan Review Focus 4 und S18c: Ein Feature aus Variante B wäre in Standard unterdrückt, gespeichert wird Variante B."""
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    quelle = r.arbeitsordner / auftrag / "quelle" / MUSTER.name
    quelle.parent.mkdir(parents=True)
    shutil.copy2(MUSTER, quelle)
    model = oeffne(app, quelle, sichtbar=False)
    try:
        model.ShowConfiguration2("Variante B")
        assert model.Save3(sw.SW_SAVEAS_SILENT, byref_long(), byref_long())
    finally:
        sw.schliesse(app, model)
    befehle.aufnehmen(quelle, auftrag)
    a = lade_aufnahme(r, auftrag, 1)
    assert a["aktiv"] == "Variante B"
    punkte = [{"id": "p1", "typ": "feature", "name": "Gewinde M6", "feature": NORMBOHRUNG}]
    aus = bau.bauen(_aenderung(tmp_path, auftrag, a, punkte))
    n = _lies_lauf(Path(aus["dateien"]["teil"]))
    assert n["aktiv"] == "Variante B" and n["neuaufbau"] == []
    assert {f["name"]: f for f in n["features"]}["Gewinde M6"]["unterdrueckt"] == {"Variante B": False, "Standard": False}
    for k in n["konfigurationen"]:  # beide Konfigurationen haben die Bohrungen wirklich
        assert n["geometrie"][k]["volumen"] < a["geometrie"][k]["volumen"] - 100, k


def test_unmoeglicher_zug_speichert_nicht(auftrag, tmp_path):
    """S18c3: Vor die Grundplatte lässt sich die Bohrung nicht ziehen. Die Datei im Lauf bleibt die unveränderte Kopie."""
    sha = sha256_datei(MUSTER)
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(lade_rechner(), auftrag, 1)
    punkte = [{"id": "p1", "typ": "feature", "name": "Gewinde M6", "feature": NORMBOHRUNG, "nach": "Skizze1"},
              {"id": "p2", "typ": "unterdruecken", "feature": "Fase1"}]
    with pytest.raises(BauAbbruch) as e:
        bau.bauen(_aenderung(tmp_path, auftrag, a, punkte))
    d = e.value.daten
    assert d["fehler"]["punkt"] == "p1" and d["dateien"] == {}
    assert [k["status"] for k in d["knoten"]] == ["fehler", "uebersprungen"]
    assert sha256_datei(Path(d["ordner"]) / MUSTER.name) == sha


def test_pruefen_besteht_und_zu_enger_bereich(auftrag, tmp_path):
    """Brief Step 8. Bestand und Lauf heißen gleich (Plan Review Focus 1), die Fase verschwindet nur in Standard. Der Skript-Punkt gibt
    seine Skizze zurück: Sie ist ein neues Feature, das nur das Protokoll erklärt."""
    r = lade_rechner()
    sha = sha256_datei(MUSTER)
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(r, auftrag, 1)
    kopie = bestand_ordner(r, auftrag, 1) / MUSTER.name
    punkte = [{"id": "p1", "typ": "mass", "was": "Tasche tiefer", "mass": TASCHE, "alt": 8, "neu": 9},
              {"id": "p2", "typ": "gleichung", "was": "Länge", "variable": "L", "alt": 100, "neu": 110, "folgen": ["D1@Skizze1"]},
              {"id": "p3", "typ": "unterdruecken", "was": "Fase weg", "feature": "Fase1", "konfigurationen": ["Standard"]},
              {"id": "p4", "typ": "feature", "was": "Gewinde", "name": "Gewinde M6 Deckel", "feature": NORMBOHRUNG},
              {"id": "p5", "typ": "eigenschaft", "name": "Revision", "neu": "B"},
              {"id": "p6", "typ": "skript", "datei": "skripte/p6.py", "luecke": "Hilfsskizze"}]
    skript = tmp_path / auftrag / "skripte" / "p6.py"
    skript.parent.mkdir(parents=True)
    skript.write_text('def bauen(ctx):\n    return ctx.skizze({"nahe": [45, 0, 20]}, [{"kreis": {"mitte": [45, 10], "durchmesser": 3}}])[0]\n',
                      encoding="utf-8")
    pruefung = {"masse_pruefen": [
        {"was": "Randabstand", "von": {"flaeche": {"nahe": [-50, 0, 10], "normale": [-1, 0, 0]}}, "zu": {"punkt": ["=-50+RA", 24, 20]},
         "soll": "=RA"},
        {"was": "Dicke", "von": {"feature": "Aufsatz-Linear austragen1", "flaeche": "+z"}, "zu": {"punkt": [0, 0, 0]}, "soll": 20}]}
    spec = _aenderung(tmp_path, auftrag, a, punkte, pruefung=pruefung)
    datei = Path(bau.bauen(spec)["dateien"]["teil"])
    sha_lauf = sha256_datei(datei)

    b = pruefen(spec)
    assert b["maengel"] == [] and b["bestanden"] is True, b["maengel"]
    assert all(e["ok"] is True for e in b["pruefungen"])
    assert next(e for e in b["pruefungen"] if e["id"] == "punkt:p6")["hinweis"].startswith("Notausgang")
    assert len({e["id"] for e in b["pruefungen"] if e["id"].startswith("punkt:")}) == 6
    vorher = datei.parent / "vergleich" / f"vorher_{MUSTER.name}"
    assert b["vorher"] == str(vorher) and sha256_datei(vorher) == sha and sha256_datei(datei) == sha_lauf
    assert sha256_datei(kopie) == sha and sha256_datei(MUSTER) == sha and pruefe_unveraendert(r, auftrag, spec) is None
    assert verbinde(r.sw_jahr).GetDocuments in (None, ())
    assert {Path(p).name for p in b["bilder"].values()} == {"iso.png", "vorne.png", "oben.png", "rechts.png"}
    assert all(Path(p).stat().st_size for p in [*b["bilder"].values(), *b["bilder_vorher"].values()])
    masse = {e["id"]: e for e in b["pruefungen"] if e["id"].startswith("mass:")}
    assert masse["mass:Randabstand"]["ist"] == pytest.approx(12) and masse["mass:Dicke"]["ist"] == pytest.approx(20)
    assert masse["mass:Dicke"]["konfiguration"] == "Standard"

    # Volumen unabhängig von den Differenzkörpern: Die Aufnahmen beider Stände müssen zur Differenz passen
    n = _lies_lauf(datei)
    for k in a["konfigurationen"]:
        d = sum(x["volumen"] * (1 if x["art"] == "hinzu" else -1) for x in b["differenzen"][k])
        assert d == pytest.approx(n["geometrie"][k]["volumen"] - a["geometrie"][k]["volumen"], abs=0.1), k
    assert all(x["bereich"] == 0 for k in a["konfigurationen"] for x in b["differenzen"][k])
    assert len(b["differenzen"]["Standard"]) >= 2  # Fase und Tasche liegen getrennt

    eng = _aenderung(tmp_path, auftrag, a, punkte, name="eng", box=([-60, -40, -1], [0, 40, 30]))  # die rechte Seite fehlt
    bau.bauen(eng)
    b = pruefen(eng)
    assert b["bestanden"] is False
    m = [x for x in b["maengel"] if x["pruefung"] == "bereich"]
    assert len(m) == 2 and "mm³" in m[0]["beschreibung"] and "x " in m[0]["beschreibung"]
    assert {x["pruefung"] for x in b["maengel"]} == {"bereich"}


def test_verschobene_flaeche_5_um_liegt_unter_der_toleranz(auftrag, tmp_path):
    """S18d an `swki pruefen`: Der Körper ist exakt da, zählt aber nicht; `punkt` meldet, dass im Bereich nichts geschah."""
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(lade_rechner(), auftrag, 1)
    punkte = [{"id": "p1", "typ": "gleichung", "was": "Länge", "variable": "L", "alt": 100, "neu": 100.005, "folgen": ["D1@Skizze1"]}]
    spec = _aenderung(tmp_path, auftrag, a, punkte, box=([-60, -40, -1], [-40, 40, 30]))
    bau.bauen(spec)
    b = pruefen(spec)
    d = b["differenzen"]["Standard"]
    assert len(d) == 1 and d[0]["art"] == "hinzu" and d[0]["volumen"] == pytest.approx(5.99, abs=0.01)
    assert d[0]["unter_toleranz"] is True and d[0]["dicke"] == pytest.approx(0.005, abs=1e-5) and d[0]["bereich"] is None
    assert [e["ok"] for e in b["pruefungen"] if e["id"] == "bereich"] == [True, True]
    assert [m["pruefung"] for m in b["maengel"]] == ["punkt:p1"]


@pytest.mark.parametrize("neu, ok", [(40.02, False), (40.004, None)])
def test_sichel_einer_versetzten_bohrung(auftrag, tmp_path, neu, ok):
    """S18d an `swki pruefen`, die Fläche live: Je Richtung eine Sichel, 4 mm breit, Dicke `2·2V/A`. 20 µm sind ein Mangel, 4 µm lassen sich
    über die Kante nicht beweisen und bleiben offen."""
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(lade_rechner(), auftrag, 1)
    punkte = [{"id": "p1", "typ": "mass", "was": "Bohrung versetzt", "mass": "D2@Skizze3", "alt": 40, "neu": neu}]
    spec = _aenderung(tmp_path, auftrag, a, punkte, box=([40, -40, -1], [60, 40, 30]))  # neben der Bohrung
    bau.bauen(spec)
    b = pruefen(spec)
    versatz, d = neu - 40, b["differenzen"]["Standard"]
    assert sorted(x["art"] for x in d) == ["entfernt", "hinzu"]
    for x in d:
        assert x["volumen"] == pytest.approx(8 * versatz * 20, rel=0.01)
        assert x["flaeche"] == pytest.approx(math.pi * 8 * 20, abs=1)  # zwei Halbzylinder und zwei Sicheln als Stirnflächen
        assert x["dicke"] == pytest.approx(4 * versatz / math.pi, rel=0.02)
        assert min(x["box"][i + 3] - x["box"][i] for i in range(3)) > 3
    assert [e["ok"] for e in b["pruefungen"] if e["id"] == "bereich"] == [ok, ok]


def test_feature_bereich_aus_den_flaechen_vorher(auftrag, tmp_path):
    """Die Fase hat nachher keine Flächen mehr, ihr Bereich kommt aus dem Vorher-Dokument; Variante B ändert sich nicht."""
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(lade_rechner(), auftrag, 1)
    punkte = [{"id": "p1", "typ": "unterdruecken", "was": "Fase weg", "feature": "Fase1"}]
    spec = _aenderung(tmp_path, auftrag, a, punkte, features=["Fase1"])
    bau.bauen(spec)
    b = pruefen(spec)
    assert b["maengel"] == [] and b["bestanden"] is True, b["maengel"]
    [d] = b["differenzen"]["Standard"]
    assert d["art"] == "hinzu" and d["bereich"] == 0 and d["volumen"] == pytest.approx(200, abs=0.01)
    assert b["differenzen"]["Variante B"] == []


def test_aktive_konfiguration_bleibt_unterdrueckte_skizze_stoert_nicht(auftrag):
    """Plan Review Focus 4 und 5: Variante B aktiv, Fase dort unterdrückt, dazu ein Schnitt samt Skizze im aktiven Stand."""
    app = verbinde(lade_rechner().sw_jahr)
    ordner = lade_rechner().arbeitsordner / auftrag
    ordner.mkdir(parents=True)
    kopie = shutil.copy2(MUSTER, ordner / MUSTER.name)
    model = oeffne(app, Path(kopie), sichtbar=False, nur_lesen=True)
    try:
        assert model.IsOpenedReadOnly
        model.ShowConfiguration2("Variante B")
        schnitt = "Schnitt-Linear austragen2"
        assert model.FeatureByName(schnitt).SetSuppression2(SW_UNTERDRUECKEN, SW_BENANNT, bstr_array(["Variante B"]))
        model.EditRebuild3
        d = lies_bestand(app, model)
        assert model.ConfigurationManager.ActiveConfiguration.Name == "Variante B" and d["aktiv"] == "Variante B"
        assert d["konfigurationen"] == ["Variante B", "Standard"]
        features = {f["name"]: f for f in d["features"]}
        assert features[schnitt]["unterdrueckt"] == {"Variante B": True, "Standard": False}
        assert d["geometrie"]["Variante B"]["volumen"] > d["geometrie"]["Standard"]["volumen"]
    finally:
        sw.schliesse(app, model)
    assert sha256_datei(Path(kopie)) == sha256_datei(MUSTER)


# ------------------------------------------------------------------------------------------------------ Negativfälle, S18a

def _geprueft_abgenommen(spec: Path) -> None:
    """Lauf bauen und prüfen, ohne Mangel; das Urteil des Prüfers steht hier als Datei da."""
    nummer = bau.bauen(spec)["lauf"]
    b = pruefen(spec)
    assert b["maengel"] == [] and b["bestanden"] is True, b["maengel"]
    lauf_datei(spec, nummer, "pruefer").write_text(json.dumps({"bestanden": True, "maengel": []}), encoding="utf-8")


def test_versetzte_gewindebohrung_ist_ein_mangel(auftrag, tmp_path):
    """Die Messung sieht die Achse, nicht das Protokoll: Ein Skript schiebt die fertige Bohrung, der Handler hatte sie richtig gesetzt."""
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(lade_rechner(), auftrag, 1)
    skript = tmp_path / auftrag / "skripte" / "p2.py"
    skript.parent.mkdir(parents=True)
    skript.write_text('def bauen(ctx):\n    mass = ctx.model.Parameter("D1@Gewinde M6 Deckel Skizze")\n'
                      '    mass.SetSystemValue3(mass.SystemValue + 0.001, 2, None)\n', encoding="utf-8")
    punkte = [{"id": "p1", "typ": "feature", "was": "Gewinde", "name": "Gewinde M6 Deckel", "feature": NORMBOHRUNG},
              {"id": "p2", "typ": "skript", "datei": "skripte/p2.py", "luecke": "Testfall: Bohrung versetzen"}]
    spec = _aenderung(tmp_path, auftrag, a, punkte)
    bau.bauen(spec)
    b = pruefen(spec)
    e = next(x for x in b["pruefungen"] if x["id"] == "punkt:p1")
    assert e["ok"] is False and "Standard: Position" in e["hinweis"] and "Variante B: Position" in e["hinweis"], e
    assert (e["ist"]["Standard"]["groesse"], e["ist"]["Standard"]["gewindetiefe"]) == ("M6", 8)  # Größe und Tiefe stimmen, nur die Lage nicht


def test_formschraege_und_verzahnung_werden_gemessen(auftrag, tmp_path):
    """Dieselben Bausteine wie beim Teil, je Konfiguration. Das Rad steht abseits, ein eigener Körper: Hier zählt nur die Messung."""
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(lade_rechner(), auftrag, 1)
    schraeg = {"typ": "schnitt", "skizze": {"ebene": {"feature": "Aufsatz-Linear austragen1", "flaeche": "+z"},
                                            "elemente": [{"kreis": {"mitte": [38, 12], "durchmesser": 8}}]},
               "ende": {"typ": "blind", "tiefe": 5, "formschraege": {"winkel": 5, "querschnitt": "kleiner"}}}
    rad = {"typ": "verzahnung", "art": "stirnrad", "ebene": "vorne", "mitte": [200, 0], "modul": 2, "zaehne": 20, "breite": 10,
           "zahndickenabmass": -0.05}
    punkte = [{"id": "p1", "typ": "feature", "was": "Schräge Tasche", "name": "Tasche schräg", "feature": schraeg},
              {"id": "p2", "typ": "feature", "was": "Rad", "name": "Rad", "feature": rad}]
    spec = _aenderung(tmp_path, auftrag, a, punkte, box=([-60, -40, -1], [260, 60, 30]))
    bau.bauen(spec)
    b = pruefen(spec)
    e = {x["id"]: x for x in b["pruefungen"]}
    assert e["punkt:p1"]["ok"] is True, e["punkt:p1"]
    assert e["punkt:p1"]["ist"] == {"Standard": [5.0], "Variante B": [5.0]} and e["punkt:p1"]["soll"] == {"winkel": 5, "querschnitt": "kleiner"}
    assert e["punkt:p2"]["ok"] is True, e["punkt:p2"]
    assert e["punkt:p2"]["ist"]["Variante B"]["zaehne"] == 20 and e["punkt:p2"]["ist"]["Standard"]["kopfkreis"] == pytest.approx(44, abs=0.2)


def test_validieren_weist_altwert_und_gesteuertes_mass_ab(auftrag, tmp_path):
    """Spec §12, gegen die echte Aufnahme des Musters."""
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(lade_rechner(), auftrag, 1)
    faelle = {"altwert": ({"mass": "D2@Skizze4", "alt": 41, "neu": 45}, BESTAND_ALTWERT),
              "gesteuert": ({"mass": "D1@Skizze1", "alt": 100, "neu": 110}, MASS_GESTEUERT)}
    for name, (mass, code) in faelle.items():
        pfad = _schreibe_spec(tmp_path, auftrag, a, [{"id": "p1", "typ": "mass", "was": name, **mass}], name=name)
        with pytest.raises(SpecFehler) as e:
            validieren(pfad)
        assert [b.get("code") for b in e.value.daten["befunde"]] == [code], name


def test_aenderung_in_allen_statt_in_einer_konfiguration(auftrag, tmp_path):
    """Spec §12: Der Punkt nennt nur Standard, ein Skript zieht Variante B mit. Herbeigeführt über den Notausgang, denn `mass` selbst
    trifft richtig. Baum, Bereich und Punkt stimmen, nur `masse` sieht es."""
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(lade_rechner(), auftrag, 1)
    skript = tmp_path / auftrag / "skripte" / "p2.py"
    skript.parent.mkdir(parents=True)
    skript.write_text(f'def bauen(ctx):\n    ctx.model.Parameter("{TASCHE}").SetSystemValue3(0.009, 2, None)\n', encoding="utf-8")
    punkte = [{"id": "p1", "typ": "mass", "was": "Tasche tiefer, nur Standard", "mass": TASCHE, "alt": 8, "neu": 9,
               "konfigurationen": ["Standard"]},
              {"id": "p2", "typ": "skript", "datei": "skripte/p2.py", "luecke": "Testfall: alle Konfigurationen"}]
    spec = _aenderung(tmp_path, auftrag, a, punkte)
    bau.bauen(spec)
    b = pruefen(spec)
    assert b["bestanden"] is False and [m["pruefung"] for m in b["maengel"]] == ["masse"], b["maengel"]
    assert TASCHE in b["maengel"][0]["beschreibung"] and "Variante B: 8 → 9" in b["maengel"][0]["beschreibung"]


def test_original_geaendert_warnt_bei_der_ausgabe(auftrag, tmp_path):
    """Spec §12, §9: Das Original gilt als Datei des Kollegen, hier eine Kopie im Testordner. Ändert es sich nach der Aufnahme, wird trotzdem
    ausgegeben, aber gewarnt; zuvor bleibt die Warnung aus."""
    original = tmp_path / MUSTER.name
    shutil.copy2(MUSTER, original)
    befehle.aufnehmen(original, auftrag)
    a = lade_aufnahme(lade_rechner(), auftrag, 1)
    spec = _aenderung(tmp_path, auftrag, a, [{"id": "p1", "typ": "eigenschaft", "name": "Revision", "neu": "B"}])
    _geprueft_abgenommen(spec)
    assert BESTAND_ORIGINAL_GEAENDERT not in [w["code"] for w in ausgabe.ausgabe(spec)["warnungen"]]
    original.write_bytes(original.read_bytes() + b"Kollege")
    erg = ausgabe.ausgabe(spec)
    assert BESTAND_ORIGINAL_GEAENDERT in [w["code"] for w in erg["warnungen"]]
    assert sha256_datei(Path(erg["dateien"][0]["ausgabe"])) == erg["dateien"][0]["sha256"] != sha256_datei(original)


def test_datei_id_bleibt(auftrag, tmp_path):
    """S18a am Ergebnis: Die Ausgabe-Datei liegt neben einer Kopie der Musterbaugruppe. Sie öffnet ohne ID-Warnung und ohne Neuaufbau-
    Fehler, die Komponente lädt aus dieser Kopie und trägt die Änderung."""
    r = lade_rechner()
    befehle.aufnehmen(MUSTER, auftrag)
    a = lade_aufnahme(r, auftrag, 1)
    punkte = [{"id": "p1", "typ": "mass", "was": "Tasche tiefer", "mass": TASCHE, "alt": 8, "neu": 9}]
    spec = _aenderung(tmp_path, auftrag, a, punkte)
    _geprueft_abgenommen(spec)
    [datei] = ausgabe.ausgabe(spec)["dateien"]

    ordner = r.arbeitsordner / auftrag / "baugruppe"
    ordner.mkdir()
    for name in ("Muster.SLDASM", "gm42-10.SLDPRT"):
        shutil.copy2(MUSTER.parent / name, ordner)
    shutil.copy2(datei["ausgabe"], ordner / MUSTER.name)

    app = verbinde(r.sw_jahr)
    fehler, warnungen = byref_long(), byref_long()
    asm = app.OpenDoc6(str(ordner / "Muster.SLDASM"), SW_DOC_BAUGRUPPE, SW_OEFFNEN_STILL_VOLL, "", fehler, warnungen)
    assert asm is not None, fehler.value
    try:
        assert warnungen.value & (SW_WARNUNG_ID | SW_WARNUNG_REFERENZ_FEHLT) == 0, warnungen.value
        komponenten = {k.Name2: k for k in asm.GetComponents(True)}
        for k in komponenten.values():
            assert Path(k.GetPathName).parent == ordner and k.GetSuppression2 != SW_KOMPONENTE_ID_FALSCH, k.Name2
        assert asm.EditRebuild3 and whats_wrong(asm) == []
        volumen = _geometrie(komponenten["Lagerdeckel-1"].GetModelDoc2)["volumen"]
        # Tasche 1 mm tiefer: 50 × 30 × 1 weniger, die Rippe wächst 3 × 30 × 1 mit
        assert volumen == pytest.approx(a["geometrie"]["Standard"]["volumen"] - 1500 + 90, abs=0.1)
    finally:
        sw.schliesse(app, asm)
    assert sha256_datei(MUSTER) == a["datei"]["sha256"]
