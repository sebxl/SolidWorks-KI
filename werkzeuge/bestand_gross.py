"""Größe messen (Spec Bestandsdateien §8.7, Plan Etappe 2 Task 14): Eine erzeugte große Baugruppe läuft durch `aufnehmen`, einen
Bau mit einem Teil-Punkt und `pruefen`, je Schritt und Phase Zeit und Private Bytes, dazu die Teil-Differenz bei rund 2000 Flächen.

`erzeugen` baut über die rohe API (Bausteine aus `bestand_muster`) nach <arbeitsordner>/BESTAND-GROSS/<jahr>/orig/: 40 Teile, 200
Komponenten, davon ein Teil mit rund 2000 Flächen (Bohrbild), alle fixiert bis auf den Schieber auf einer Grenzverknüpfung.
`messen` läuft in einem eigenen Testauftrag `LIVE-GROSS-*`, freigegeben ohne Rückfrage wie die Live-Tests: Die Dateien sind selbst
erzeugt, nichts davon ist ein Original eines Kollegen. Ergebnis nach docs/bestandsdateien/gross_<modus>.json, die Tabelle kommt
von Hand in ergebnisse.md.

Modus `unsichtbar` ist der Regelfall. `sichtbar` öffnet jedes `oeffne_in` mit Fenster, damit der Abstand zu sehen ist; das geht
nur hier über den Austausch von `pfade.oeffne`, der Code von swki bleibt unverändert. Liegt eine Phase über `speicher_grenze_mb`
oder braucht die Aufnahme mehr als zehn Minuten, steht das in `bewertung`, abgeschaltet wird nichts.

Bohrbild: Platte 10 mm dick, je Bohrung Ø4 eine Zylinderfläche, Skizze mit allen Kreisen ohne Maße, eine Fläche je Bohrung ist
Annahme, die Ausgabe nennt die gemessene Zahl.

API (swki api methode, Parameterzahl laut Index):
  ISldWorks.NewDocument(4), .OpenDoc6(6), .CloseDoc(1), .DocumentVisible(2), .GetProcessID(0)
  IAssemblyDoc.AddComponent5(8), .FixComponent(0), .GetComponents(1); IComponent2.Select4(3); ISketchManager.CreateCircleByRadius(4)
  IBody2.GetFaceCount(0); IModelDoc2.Save3(3), .GetTitle(0); IModelDocExtension.GetWhatsWrongCount(0)

Aufruf (SolidWorks frisch, frei):
  .venv\\Scripts\\python.exe -m werkzeuge.bestand_gross erzeugen
  .venv\\Scripts\\python.exe -m werkzeuge.bestand_gross messen --modus unsichtbar
  .venv\\Scripts\\python.exe -m werkzeuge.bestand_gross messen --modus sichtbar
"""

import argparse
import json
import math
import shutil
import stat
import time
from contextlib import contextmanager
from pathlib import Path

import yaml

from swki.auftrag import lauf_datei
from swki.bestand import bau, befehle, pfade
from swki.bestand.ablage import lade_aufnahme
from swki.bestand.pruefen import pruefen
from swki.bestand.spec import freigeben, validieren
from swki.konfig import PROJEKT, lade_rechner, lade_standard
from swki.speicher import Spitzenmessung
from swki.verbindung import byref_long, mm, verbinde, wert
from werkzeuge.bestand_muster import (SW_DOC_PART, SW_INPUT_DIM_VAL_ON_CREATE, SW_OPEN_SILENT, SW_SAVEAS_SILENT, abstand_mit_lage,
                                      baue_block,
                                      ebene_von, ebenen, lege, mates, schnitt, skizze_auf_flaeche, speichere)

ERGEBNIS = PROJEKT / "docs" / "bestandsdateien"
HAUPT = "Gross.SLDASM"
BOHRBILD = "teile/Bohrbild.SLDPRT"
TEILE, KOMPONENTEN, BOHRUNGEN = 40, 200, 2000
TEILUNG, BOHRUNG_D, DICKE = 10.0, 4.0, 10.0  # mm
DICKE_NEU = 12.0
BLOCK_MAX, RASTER, HOEHE = 40.0, 60.0, 100.0  # größte Seite eines Blocks, Abstand im Raster, Unterkante über der Platte (mm)
HUB = 25.0
SCHIEBER = "Block_00-1"
SCHIEBER_LAGE = (0.0, 480.0, HOEHE)  # außerhalb des Rasters, mm
AUFTRAEGE = {"unsichtbar": "LIVE-GROSS-UNSICHTBAR", "sichtbar": "LIVE-GROSS-SICHTBAR"}
ZEHN_MINUTEN = 600.0
SCHRITTE = ("aufnahme", "bauen", "pruefen")
AUFSATZ = "Aufsatz-Linear austragen1"


def bohrbild(anzahl: int) -> list[tuple[float, float]]:
    """Die ersten `anzahl` Punkte eines quadratischen Rasters um den Ursprung, Zeile für Zeile."""
    seite = math.ceil(math.sqrt(anzahl))
    start = -(seite - 1) * TEILUNG / 2
    return [(start + s * TEILUNG, start + z * TEILUNG) for z in range(seite) for s in range(seite)][:anzahl]


def plattenseite(punkte: list[tuple[float, float]]) -> float:
    """Halbe Seite der Platte: eine Teilung Rand um das Bohrbild."""
    return max(abs(c) for p in punkte for c in p) + TEILUNG


def _blockdatei(i: int) -> str:
    return f"teile/Block_{i:02d}.SLDPRT"


def _block_mass(i: int) -> tuple[float, float]:
    """Halbe Seite und Höhe des Blocks `i`: Die Dateien unterscheiden sich, sonst hülfe SolidWorks ein gemeinsamer Cache."""
    return (10 + (i % 3) * 5, 20 + (i % 4) * 5)


def plan_komponenten() -> list[dict]:
    """Eine Komponente je Eintrag: das Bohrbild, der Schieber abseits des Rasters, dann die Blöcke reihum im Raster oberhalb der Platte."""
    plan = [{"datei": BOHRBILD, "name": "Bohrbild-1", "x": 0.0, "y": 0.0, "z": DICKE / 2},
            {"datei": _blockdatei(0), "name": SCHIEBER, "x": SCHIEBER_LAGE[0], "y": SCHIEBER_LAGE[1], "z": HOEHE}]
    spalten = math.ceil(math.sqrt(KOMPONENTEN))
    for i in range(KOMPONENTEN - len(plan)):
        zeile, spalte = divmod(i, spalten)
        plan.append({"datei": _blockdatei((i + 1) % (TEILE - 1)), "name": None, "x": (spalte - spalten / 2) * RASTER,
                     "y": (zeile - spalten / 2) * RASTER, "z": HOEHE})
    return plan


def bohrungen(app, punkte: list):
    """`danach` für `baue_block`: alle Kreise in einer Skizze auf der Oberseite, ein Schnitt durch alles."""
    def ergaenze(model, _) -> dict:
        rand = plattenseite(punkte) - TEILUNG / 2
        s = skizze_auf_flaeche(app, model, rand, rand, DICKE)
        for x, y in punkte:
            s.sm.CreateCircleByRadius(*s.uv(x, y, DICKE), 0.0, mm(BOHRUNG_D / 2))
        schnitt(model, s.ende(), 1)
        return {"flaechen": wert(model.GetBodies2(0, False)[0].GetFaceCount)}  # late-bound eine Methode (Lauf 12.11.2026)

    return ergaenze


def erzeuge(app, r, ordner: Path) -> dict:
    (ordner / "teile").mkdir(parents=True)
    punkte = bohrbild(BOHRUNGEN)
    seite = plattenseite(punkte)
    d: dict = {"bohrbild": baue_block(app, r, ordner / BOHRBILD, (-seite, -seite, seite, seite), DICKE, "Bohrbild", bohrungen(app,
                                                                                                                              punkte))}
    for i in range(TEILE - 1):
        halb, hoehe = _block_mass(i)
        baue_block(app, r, ordner / _blockdatei(i), (-halb, -halb, halb, halb), hoehe, f"Block {i}")
    d["baugruppe"] = baue_baugruppe(app, r, ordner)
    return d


def baue_baugruppe(app, r, ordner: Path) -> dict:
    plan = plan_komponenten()
    offen, dateien = [], sorted({k["datei"] for k in plan})
    app.DocumentVisible(False, SW_DOC_PART)
    try:
        for rel in dateien:
            e, w = byref_long(), byref_long()
            offen.append(app.OpenDoc6(str(ordner / rel), SW_DOC_PART, SW_OPEN_SILENT, "", e, w))
    finally:
        app.DocumentVisible(True, SW_DOC_PART)
    asm = app.NewDocument(str(r.vorlage_baugruppe), 0, 0, 0)
    komponenten = [asm.AddComponent5(str(ordner / k["datei"]), 0, "", False, "", mm(k["x"]), mm(k["y"]), mm(k["z"]))
                   for k in plan]
    if None in komponenten:
        raise RuntimeError("AddComponent5 fehlgeschlagen")
    platte, schieber = komponenten[0], komponenten[1]
    lege(app, schieber, *SCHIEBER_LAGE)
    asm.ClearSelection2(True)
    for i, k in enumerate(k for k in komponenten if k is not schieber):
        k.Select4(i > 0, asm.SelectionManager.CreateSelectData, False)
    asm._FlagAsMethod("FixComponent")
    asm.FixComponent()
    asm.ClearSelection2(True)
    d = {"speichern": speichere(asm, ordner / HAUPT)}
    vorne, oben, rechts = (schieber.FeatureByName(e.Name) for e in ebenen(schieber.GetModelDoc2))
    p_vorne, p_oben, p_rechts = (platte.FeatureByName(e.Name) for e in ebenen(platte.GetModelDoc2))
    abstand_mit_lage(asm, "Schieber Hoehe", schieber, SCHIEBER_LAGE, ebene_von(vorne), ebene_von(p_vorne), SCHIEBER_LAGE[2])
    abstand_mit_lage(asm, "Schieber Seite", schieber, SCHIEBER_LAGE, ebene_von(oben), ebene_von(p_oben), SCHIEBER_LAGE[1])
    abstand_mit_lage(asm, "Hub", schieber, SCHIEBER_LAGE, ebene_von(rechts), ebene_von(p_rechts), 0.0, grenzen=(0.0, HUB))
    d |= {"komponenten": len(asm.GetComponents(True)), "dateien": len(dateien), "verknuepfungen": [f.Name for f in mates(asm)],
          "whats_wrong": asm.Extension.GetWhatsWrongCount}
    s, w = byref_long(), byref_long()
    d["speichern2"] = asm.Save3(SW_SAVEAS_SILENT, s, w), s.value, w.value
    app.CloseDoc(asm.GetTitle)
    for t in offen:
        try:
            app.CloseDoc(t.GetTitle)
        except AttributeError:  # SolidWorks hat es mit der Baugruppe geschlossen
            pass
    return d


def erzeugen() -> None:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    ordner = r.arbeitsordner / "BESTAND-GROSS" / str(r.sw_jahr) / "orig"
    if ordner.exists():
        shutil.rmtree(ordner)
    alt = app.GetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE)
    app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, False)
    t0 = time.monotonic()
    try:
        d = erzeuge(app, r, ordner)
    finally:
        app.SetUserPreferenceToggle(SW_INPUT_DIM_VAL_ON_CREATE, alt)
    d["sekunden"] = round(time.monotonic() - t0, 1)
    print(json.dumps(d, indent=1, ensure_ascii=False, default=str))


def haupt_pfad(r) -> Path:
    pfad = r.arbeitsordner / "BESTAND-GROSS" / str(r.sw_jahr) / "orig" / HAUPT
    if not pfad.is_file():
        raise SystemExit(f"{pfad} fehlt: zuerst -m werkzeuge.bestand_gross erzeugen")
    return pfad


def schreibe_spec(pfad: Path, a: dict) -> Path:
    """Ein Teil-Punkt auf dem Bohrbild: Die neue Dicke trifft jede Bohrung, die Differenz sieht alle 2000 Flächen."""
    seite = plattenseite(bohrbild(BOHRUNGEN))
    spec = {"art": "aenderung", "name": "Gross_Rev", "bestand": {"datei": a["datei"]["name"], "sha256": a["datei"]["sha256"],
                                                                 "aufnahme": 1},
            "parameter": {"DICKE_NEU": DICKE_NEU},
            "punkte": [{"id": "p1", "was": "Bohrbild dicker", "typ": "mass", "in_datei": BOHRBILD, "mass": f"D1@{AUFSATZ}",
                        "alt": DICKE, "neu": "=DICKE_NEU"}],
            "bereiche": [{"punkte": ["p1"], "in_datei": BOHRBILD, "box": {"min": [-seite, -seite, DICKE], "max": [seite, seite,
                                                                                                                  DICKE_NEU]}}]}
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pfad


@contextmanager
def modus(art: str):
    """`sichtbar`: Jedes `oeffne_in` öffnet mit Fenster, sonst bleibt alles, wie swki es tut."""
    if art not in AUFTRAEGE:
        raise ValueError(f"Modus {art!r}: {', '.join(AUFTRAEGE)}")
    if art == "unsichtbar":
        yield
        return
    echte = pfade.oeffne

    def mit_fenster(app, pfad, sichtbar=True, nur_lesen=False, voll=False):
        return echte(app, pfad, sichtbar=True, nur_lesen=nur_lesen, voll=voll)

    pfade.oeffne = mit_fenster
    try:
        yield
    finally:
        pfade.oeffne = echte


def gemessen(pid: int, lauf) -> tuple[object, dict]:
    """Ergebnis von `lauf()`, Zeit und Spitze der Private Bytes im Takt von `Spitzenmessung`; `messung` der Phasen sieht nur Punkte."""
    t0 = time.perf_counter()
    with Spitzenmessung(pid) as s:
        ergebnis = lauf()
    return ergebnis, {"s": round(time.perf_counter() - t0, 1), "spitze_mb": s.spitze}


def bewertung(b: dict, grenze_mb: float) -> list[str]:
    """Plan Task 14 Step 3: was dem Nutzer vorzulegen ist. Nicht gelesener Speicher ist kein Befund."""
    aus = []
    for schritt in SCHRITTE:
        spitze = b[schritt]["spitze_mb"]
        if spitze is not None and spitze > grenze_mb:
            aus.append(f"{schritt}: Spitze {spitze:.0f} MB über speicher_grenze_mb {grenze_mb:.0f}")
        aus += [f"{schritt}/{name}: {p['mb']:.0f} MB über speicher_grenze_mb {grenze_mb:.0f}" for name,
                p in (b[schritt]["phasen"] or {}).items()
                if p.get("mb") is not None and p["mb"] > grenze_mb]
    if b["aufnahme"]["s"] > ZEHN_MINUTEN:
        aus.append(f"Aufnahme dauert {b['aufnahme']['s']:.0f} s, mehr als zehn Minuten")
    return aus


def _zeile(schritt: str, phase: str, s, mb) -> str:
    return f"| {schritt} | {phase} | {s:.1f} | {'–' if mb is None else f'{mb:.0f}'} |"


def tabelle(b: dict) -> str:
    """Je Phase Zeit und Private Bytes, je Schritt die Summe mit der Spitze; für `ergebnisse.md`."""
    zeilen = ["| Schritt | Phase | s | MB |", "|---|---|---|---|"]
    for schritt in SCHRITTE:
        zeilen += [_zeile(schritt, name, p["s"], p.get("mb")) for name, p in (b[schritt]["phasen"] or {}).items()]
        zeilen.append(_zeile(schritt, "gesamt", b[schritt]["s"], b[schritt]["spitze_mb"]))
    return "\n".join(zeilen)


def leere(ordner: Path) -> None:
    for p in ordner.rglob("*"):
        if p.is_file():
            p.chmod(stat.S_IWRITE)  # Bestandskopien sind schreibgeschützt
    shutil.rmtree(ordner, ignore_errors=True)


def messen(art: str) -> None:
    r, standard = lade_rechner(), lade_standard()
    haupt, auftrag = haupt_pfad(r), AUFTRAEGE[art]
    leere(r.arbeitsordner / auftrag)
    jahr = r.arbeitsordner / "BESTAND-GROSS" / str(r.sw_jahr)
    leere(jahr / "spec" / auftrag)
    pid = int(verbinde(r.sw_jahr).GetProcessID)
    with modus(art):
        _, aufnahme = gemessen(pid, lambda: befehle.aufnehmen(haupt, auftrag))
        a = lade_aufnahme(r, auftrag, 1)
        spec = schreibe_spec(jahr / "spec" / auftrag / "aenderung.yaml", a)
        validieren(spec)
        freigeben(spec)
        gebaut, bauen = gemessen(pid, lambda: bau.bauen(spec))
        bericht, pruefung = gemessen(pid, lambda: pruefen(spec))
    protokoll = json.loads(lauf_datei(spec, gebaut["lauf"], "protokoll").read_text(encoding="utf-8"))
    b = {"modus": art, "aufnahme": aufnahme | {"phasen": a["messung"]}, "bauen": bauen | {"phasen": protokoll.get("messung")},
         "pruefen": pruefung | {"phasen": bericht["messung"]},
         "zaehler": {"komponenten": len(a["komponenten"]), "dateien": len(a["dateien"]) + 1,
                     "verknuepfungen": len(a["verknuepfungen"])},
         "bestanden": bericht["bestanden"], "maengel": bericht["maengel"],
         "differenzen": {rel: {k: len(d) for k, d in je.items()} for rel, je in bericht["differenzen"].items()}}
    b["bewertung"] = bewertung(b, standard["speicher_grenze_mb"])
    ERGEBNIS.mkdir(parents=True, exist_ok=True)
    (ERGEBNIS / f"gross_{art}.json").write_text(json.dumps(b, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(tabelle(b))
    print(json.dumps({"bewertung": b["bewertung"], "bestanden": b["bestanden"], "maengel": b["maengel"]}, indent=1,
                     ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Bestandsdateien an einer erzeugten großen Baugruppe messen")
    unter = parser.add_subparsers(dest="was", required=True)
    unter.add_parser("erzeugen", help="Teile und Baugruppe im Arbeitsordner erzeugen")
    m = unter.add_parser("messen", help="aufnehmen, bauen, pruefen in einem Testauftrag")
    m.add_argument("--modus", choices=sorted(AUFTRAEGE), default="unsichtbar")
    args = parser.parse_args()
    if args.was == "erzeugen":
        erzeugen()
    else:
        messen(args.modus)


if __name__ == "__main__":
    main()
