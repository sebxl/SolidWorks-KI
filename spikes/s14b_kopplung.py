"""S14b (Stufe 4b, Etappe 2): Zahnrad- und Zahnstangenverknüpfung an der Getriebeprobe (tests/live/getriebeprobe/).

6 CreateMate mit IRackPinionMateFeatureData (Vorauswahl Marke 64/128) und IGearMateFeatureData (EntitiesToMate):
  Rückgabe, IMate2.Type, Fehlercode, Rücklesen über IFeature.GetDefinition (DiameterVal/-Type, Zähler/Nenner, Reverse);
  Drehsinn bei Reverse = False (Ritzel um +z, wenn die Zahnstange nach +x fährt; Antriebswelle gegensinnig).
7 Zahnphase: Phasenfehler vor/nach SetTransformAndSolve2 mit kopplung.drehe (Seite a um ihre Achse).
8 GetConstrainedStatus mit Kopplungen: Grenze unterdrückt ohne Antrieb, mit Antrieb auf 0.
9 Kollision je Stellung (9 Stellungen 0 … HUB) in Phase: Paare und Volumen; Zeit und Private Bytes je Schritt; danach
  k2 gelöscht, Antriebswelle um eine halbe Teilung gedreht: wird Zahn auf Zahn als Kollision erkannt?
10 Grenze wirkt durch die Kette: Schritt auf HUB + 3,75.
11 Aufsummierte Drehung der Wellen um z aus Transform2 gegen die Übersetzung.
12 Bild entlang der Radachse (Ansicht vorne, Zoom auf die Auswahl).
13 Speichern, Schließen, Öffnen: Kopplungen vorhanden, Antrieb auf 30 dreht die Ritzelwelle um 30/20 rad.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s14b_kopplung

Nachtrag Zeile 13 (nur messen): .venv\\Scripts\\python.exe -m spikes.s14b_kopplung neuoeffnen
  Öffnet die gespeicherte S14B\\Getriebeprobe.sldasm wie `swki pruefen` (Teile der Grenze mit Kontext aus der Datei, dann
  die Baugruppe, aufloesen), treibt g1 über sw_baugruppe.treibe/stelle auf 0, 30, 60 (Lage und aufsummierte Drehung je
  Stellung), löscht die treibende Verknüpfung, liest Status und k1/k2 zurück und schließt ohne Speichern.
  Ergebnis: docs/stufe0/ergebnisse/s14b_kopplung_neuoeffnen.json (setzt einen früheren Lauf des Spikes voraus).
"""

import math
import shutil
import sys
import time
from pathlib import Path

from spikes._gemeinsam import lauf
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import basis, instanzen, verknuepfungen
from swki.baugruppe.kopplung import KOPPLUNGEN, drehe, in_baugruppe, phasenfehler, phasenwinkel, verzahnung_der_seite
from swki.baugruppe.modell import Quelle
from swki.baugruppe.referenzen import loese_im_teil
from swki.compiler import sw
from swki.compiler.bauen import baue_teil_dokument
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.fehler import BauFehler
from swki.compiler.protokoll import Protokoll
from swki.compiler.topologie import flaechen
from swki.konfig import PROJEKT, lade_rechner, lade_standard
from swki.pruefung.bilder import ANSICHTEN, SW_TIFF_SCREEN_OR_PRINT_CAPTURE
from swki.pruefung.messen import kontext_aus_datei, oeffne
from swki.spec.laden import lade_spec, lade_yaml
from swki.speicher import privat_mb
from swki.verbindung import dispatch_array, in_mm, mm, r8_array, verbinde

AUFTRAG = "S14B"
TYP = {"zahnrad": 10, "zahnstange": 13}  # swMateType_e swMateGEAR / swMateRACKPINION
PROBE = PROJEKT / "tests" / "live" / "getriebeprobe"
REFERENZ = PROJEKT / "tests" / "referenz" / "zahnstangentrieb"


def _rebuild(asm) -> str:
    try:
        sw.rebuild(asm)
        return "ok"
    except BauFehler as e:
        return str(e)


def _drehwinkel_z(t0, t1) -> float:
    """Drehung um +z (Grad, −180 … 180) aus dem Bild der Teil-x-Achse."""
    d = math.degrees(math.atan2(t1[1], t1[0]) - math.atan2(t0[1], t0[0]))
    return (d + 180) % 360 - 180


class _Probe:
    """Baugruppe der Probe ohne lade_baugruppe (Schema und Plausibilität der Kopplungen kommen mit Task 9)."""

    def __init__(self, ordner: Path):
        self.spec = lade_yaml(ordner / "getriebeprobe.yaml")
        self.teile = {k["quelle"]["teil"]: lade_spec(ordner / k["quelle"]["teil"]) for k in self.spec["komponenten"]}
        self.quellen = {k["id"]: Quelle("teil", self.teile[k["quelle"]["teil"]], datei=k["quelle"]["teil"])
                        for k in self.spec["komponenten"]}


def _teile(app, r, standard, bg, ordner) -> dict:
    kontexte = {}
    for datei, spec in bg.teile.items():
        model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, ordner / datei, AUFTRAG,
                                                Protokoll(AUFTRAG, datei, 0, r.sw_jahr))
        if fehler is not None:
            raise fehler
        sw.speichere(model, ordner / f"{spec['name']}.sldprt")
        kontexte[datei] = ctx
    return kontexte


def _kopple(asm, v, a, b, wert_a, wert_b) -> tuple[object, dict]:
    """Kopplung direkt über CreateMate (der Handler kommt mit Task 11)."""
    e = {}
    vorher = len(sw_baugruppe.verknuepfungen(asm))
    sw.auswahl_leeren(asm)
    daten = asm.CreateMateData(TYP[v.typ])
    e["mate_data"] = daten is not None
    if v.typ == "zahnrad":
        daten.EntitiesToMate = dispatch_array([a[0], b[0]])
        daten.GearRatioNumerator = mm(wert_a)
        daten.GearRatioDenominator = mm(wert_b)
    else:
        daten_b = asm.SelectionManager.CreateSelectData
        daten_b.Mark = 64
        b[0].Select4(False, daten_b)
        daten_a = asm.SelectionManager.CreateSelectData
        daten_a.Mark = 128
        a[0].Select4(True, daten_a)
        daten.DiameterType = 0
        daten.DiameterVal = mm(wert_a)
    daten.Reverse = False
    mate = asm.CreateMate(daten)
    sw.auswahl_leeren(asm)
    alle = sw_baugruppe.verknuepfungen(asm)
    neu = alle[-1] if mate is not None and len(alle) > vorher else None
    e["angelegt"] = neu is not None
    if neu is not None:
        neu.Name = v.id
        e["rebuild"] = _rebuild(asm)
        e["fehlercode"] = sw_baugruppe.fehlercode(neu)
        e["typ"] = int(neu.GetSpecificFeature2.Type)
        try:
            d = neu.GetDefinition
            e["gelesen"] = ({"zaehler": in_mm(d.GearRatioNumerator), "nenner": in_mm(d.GearRatioDenominator),
                             "reverse": bool(d.Reverse)} if v.typ == "zahnrad"
                            else {"durchmesser": in_mm(d.DiameterVal), "art": d.DiameterType, "reverse": bool(d.Reverse)})
        except Exception as ex:  # Spike: festhalten
            e["gelesen"] = repr(ex)
    return neu, e


def _phase(app, asm, bg, komponenten, v) -> dict:
    def lagen():
        return [in_baugruppe(verzahnung_der_seite(bg.quellen, s), sw_baugruppe.transform(komponenten[s["komponente"]]))
                for s in (v.a, v.b)]

    a, b = lagen()
    e = {"fehler_vorher": round(phasenfehler(a, b), 6), "winkel": round(phasenwinkel(a, b), 6)}
    komp = komponenten[v.a["komponente"]]
    t = drehe(sw_baugruppe.transform(komp), a.punkt, a.achse, phasenwinkel(a, b))
    e["set_transform"] = bool(komp.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(t))))
    e["rebuild"] = _rebuild(asm)
    a, b = lagen()
    e["fehler_nachher"] = round(phasenfehler(a, b), 9)
    return e


def _status(komponenten) -> dict:
    return {k: sw_baugruppe.status(x) for k, x in komponenten.items()}


def _untersuche() -> dict:
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    ordner = r.arbeitsordner / AUFTRAG
    shutil.rmtree(ordner, ignore_errors=True)
    ordner.mkdir(parents=True)
    for quelle in [*PROBE.glob("*.yaml"), *(REFERENZ / n for n in ("zahnstange.yaml", "lagerbock.yaml", "ritzelwelle.yaml",
                                                                    "antriebswelle.yaml"))]:
        shutil.copy2(quelle, ordner / quelle.name)
    bg = _Probe(ordner)
    ergebnis = {"privat_mb_start": privat_mb(int(app.GetProcessID))}
    kontexte = _teile(app, r, standard, bg, ordner)
    asm = None
    try:
        asm = sw_baugruppe.neue_baugruppe(app, r.vorlage_baugruppe)
        globale_variablen(asm, bg.spec.get("parameter", {}))  # Spike-Korrektur: Gleichung v5 = ZL braucht die globale Variable
        komponenten = {}
        for i in instanzen(bg.spec, bg.quellen):
            model = kontexte[bg.quellen[i.komponente].datei].model
            komponenten[i.id] = sw_baugruppe.fuege_ein(app, asm, Path(model.GetPathName), sw.teilebox_mm(model))
        sw_baugruppe.fixiere(asm, komponenten["platte"])

        def ent(seite):
            ctx = kontexte[bg.quellen[basis(seite["komponente"])].datei]
            ref = loese_im_teil(ctx, {k: w for k, w in seite.items() if k != "komponente"})
            return sw_baugruppe.in_baugruppe(komponenten[seite["komponente"]], ref)

        def ent_kopplung(seite):
            ctx = kontexte[bg.quellen[basis(seite["komponente"])].datei]
            f = next(x for x in ctx.spec["features"] if x["id"] == seite["feature"])
            if f["art"] == "stirnrad":
                return ent({"komponente": seite["komponente"], "feature": seite["feature"], "instanz": 1, "achse": True})
            for kopf in flaechen(ctx.ergebnis(seite["feature"]).features[0]):  # gerade Kante einer Kopffläche entlang x
                if kopf.art == "ebene" and kopf.normale[1] > 1 - 1e-6:
                    for kante in kopf.objekt.GetEdges or ():
                        c = kante.GetCurve
                        if c.IsLine and abs(c.LineParams[3]) > 1 - 1e-6:
                            return sw_baugruppe.in_baugruppe(komponenten[seite["komponente"]],
                                                             type("Ref", (), {"objekt": kante, "ist_feature": False})())
            raise RuntimeError("keine Kante der Zahnstange")

        gesetzt: dict[str, int] = {}
        p = bg.spec.get("parameter", {})
        for v in verknuepfungen(bg.spec, bg.quellen):
            if v.typ in KOPPLUNGEN:
                ergebnis[f"7_phase_{v.id}"] = _phase(app, asm, bg, komponenten, v)
                a, b = (verzahnung_der_seite(bg.quellen, s).geo for s in (v.a, v.b))
                werte = (a.m * a.z, b.m * b.z) if v.typ == "zahnrad" else (a.m * a.z, 0.0)
                _, ergebnis[f"6_kopplung_{v.id}"] = _kopple(asm, v, ent_kopplung(v.a), ent_kopplung(v.b), *werte)
            else:
                sw_baugruppe.verknuepfe(asm, v, ent(v.a), ent(v.b), p, gesetzt)
        g1 = next(v for v in verknuepfungen(bg.spec, bg.quellen) if v.id == "g1")
        grenze = next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "g1")
        sw_baugruppe.unterdruecke(asm, grenze, True)
        ergebnis["8_status_ohne_antrieb"] = _status(komponenten)
        antrieb = sw_baugruppe.treibe(asm, g1, ent(g1.a), ent(g1.b), 0.0)
        ergebnis["8_status_mit_antrieb"] = _status(komponenten)
        sw_baugruppe.unterdruecke(asm, grenze, False)

        hub = p["HUB"]
        start = {k: sw_baugruppe.transform(komponenten[k]) for k in ("ritzelwelle", "antriebswelle")}
        vorige = dict(start)
        summe = {k: 0.0 for k in start}
        schritte = []
        pid = int(app.GetProcessID)
        for i in range(9):
            wert = hub * i / 8
            t = time.perf_counter()
            meldung = sw_baugruppe.stelle(asm, antrieb, "abstand", wert)
            stellen = time.perf_counter() - t
            t = time.perf_counter()
            paare = sw_baugruppe.interferenzen(asm)
            kollision = time.perf_counter() - t
            for k in summe:
                jetzt = sw_baugruppe.transform(komponenten[k])
                summe[k] += _drehwinkel_z(vorige[k], jetzt)
                vorige[k] = jetzt
            schritte.append({"wert": wert, "meldung": meldung, "paare": [[sorted(n), round(vol, 4)] for n, vol in paare],
                             "s_stellen": round(stellen, 3), "s_kollision": round(kollision, 3),
                             "drehung_z": {k: round(w, 4) for k, w in summe.items()}, "privat_mb": privat_mb(pid)})
        ergebnis["9_11_schritte"] = schritte
        ergebnis["11_soll"] = {"ritzelwelle": round(math.degrees(hub / 20), 4),
                               "antriebswelle": round(-math.degrees(hub / 20) * 25 / 50, 4)}
        ergebnis["10_grenze"] = {"meldung": sw_baugruppe.stelle(asm, antrieb, "abstand", hub + 3.75),
                                 "x_zahnstange_mm": round(in_mm(sw_baugruppe.transform(komponenten["zahnstange"])[9]), 4)}
        ergebnis["10_zurueck"] = sw_baugruppe.stelle(asm, antrieb, "abstand", 0.0)

        model = asm
        model._FlagAsMethod("ViewZoomToSelection")
        with sw.einstellung_int(app, SW_TIFF_SCREEN_OR_PRINT_CAPTURE, 0):
            model.ShowNamedView2("", ANSICHTEN["vorne"])
            sw.auswahl_leeren(model)
            for k in ("antriebswelle", "ritzelwelle"):
                komponenten[k].Select4(True, model.SelectionManager.CreateSelectData, False)
            model.ViewZoomToSelection()
            sw.auswahl_leeren(model)
            (ordner / "bilder").mkdir(exist_ok=True)
            sw.speichere(model, ordner / "bilder" / "k2-eingriff.png", kopie=True)
        ergebnis["12_bild_bytes"] = (ordner / "bilder" / "k2-eingriff.png").stat().st_size

        sw_baugruppe.loesche(asm, antrieb)
        sw.speichere(asm, ordner / "Getriebeprobe.sldasm")

        k2 = next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "k2")
        sw_baugruppe.loesche(asm, k2)
        komp = komponenten["antriebswelle"]
        a = in_baugruppe(verzahnung_der_seite(bg.quellen, {"komponente": "antriebswelle", "feature": "z1"}),
                         sw_baugruppe.transform(komp))
        t = drehe(sw_baugruppe.transform(komp), a.punkt, a.achse, 180 / 50)
        komp.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(t)))
        _rebuild(asm)
        ergebnis["9_halbe_teilung_paare"] = [[sorted(n), round(vol, 4)] for n, vol in sw_baugruppe.interferenzen(asm)]
    finally:
        if asm is not None:
            sw.schliesse(app, asm)
    asm = oeffne(app, ordner / "Getriebeprobe.sldasm")
    try:
        sw_baugruppe.aufloesen(asm)
        namen = [f.Name for f in sw_baugruppe.verknuepfungen(asm)]
        ergebnis["13_verknuepfungen"] = namen
        komps = {k.Name2.split("-")[0]: k for k in sw_baugruppe.komponenten(asm)}
        ergebnis["13_komponenten"] = sorted(komps)
        ritzel = next(k for n, k in komps.items() if "Ritzelwelle" in n)
        t0 = sw_baugruppe.transform(ritzel)
        grenze = next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "g1")
        stange = next(k for n, k in komps.items() if "Zahnstange" in n)
        dx = sw_baugruppe.transform(stange)[9]
        # Lage der Zahnstange über SetTransformAndSolve2 um 30 mm in +x verschieben (ohne Antrieb, nur Neuöffnen prüfen)
        t = sw_baugruppe.transform(stange)
        t[9] = dx + mm(30)
        stange.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(t)))
        ergebnis["13_rebuild"] = _rebuild(asm)
        ergebnis["13_ritzel_drehung_z"] = round(_drehwinkel_z(t0, sw_baugruppe.transform(ritzel)), 4)
        ergebnis["13_soll"] = round(math.degrees(30 / 20), 4)
        ergebnis["13_grenze_fehlercode"] = sw_baugruppe.fehlercode(grenze)
    finally:
        sw.schliesse(app, asm)
    for ctx in reversed(list(kontexte.values())):
        sw.schliesse(app, ctx.model)
    ergebnis["privat_mb_ende"] = privat_mb(int(app.GetProcessID))
    return ergebnis


def _lesen(f) -> dict:
    """Typ, Fehlercode und GetDefinition einer Kopplung (wie im Lauf, Zeile 6)."""
    d = f.GetDefinition
    typ = int(f.GetSpecificFeature2.Type)
    e = {"typ": typ, "fehlercode": sw_baugruppe.fehlercode(f), "reverse": bool(d.Reverse)}
    if typ == TYP["zahnrad"]:
        e.update(zaehler=in_mm(d.GearRatioNumerator), nenner=in_mm(d.GearRatioDenominator))
    else:
        e.update(durchmesser=in_mm(d.DiameterVal), art=d.DiameterType)
    return e


def _neuoeffnen() -> dict:
    """Nachtrag Zeile 13: den Antriebsweg von `swki pruefen` an der gespeicherten Getriebeprobe messen."""
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    ordner = r.arbeitsordner / AUFTRAG
    bg = _Probe(ordner)
    pid = int(app.GetProcessID)
    ergebnis = {"privat_mb_vorher": privat_mb(pid)}
    tol = standard["toleranzen"]["anker_mm"]
    offen, kontexte, asm = [], {}, None
    try:
        for datei in ("platte.yaml", "zahnstange.yaml"):  # die Dokumente der Grenze g1 (wie pruefen: offen_halten)
            spec = bg.teile[datei]
            model = oeffne(app, ordner / f"{spec['name']}.sldprt")
            offen.append(model)
            kontexte[datei] = kontext_aus_datei(app, model, spec, ordner / datei, tol, {"knoten": []})
        asm = oeffne(app, ordner / "Getriebeprobe.sldasm")
        sw_baugruppe.aufloesen(asm)
        namen = {bg.teile[k["quelle"]["teil"]]["name"]: k["id"] for k in bg.spec["komponenten"]}
        komponenten = {namen[k.Name2.rsplit("-", 1)[0]]: k for k in sw_baugruppe.komponenten(asm)}
        ergebnis["komponenten"] = sorted(komponenten)

        def ent(seite):
            ctx = kontexte[bg.quellen[basis(seite["komponente"])].datei]
            ref = loese_im_teil(ctx, {k: w for k, w in seite.items() if k != "komponente"})
            return sw_baugruppe.in_baugruppe(komponenten[seite["komponente"]], ref)

        ergebnis["verknuepfungen"] = [f.Name for f in sw_baugruppe.verknuepfungen(asm)]
        ergebnis["status_beim_oeffnen"] = _status(komponenten)
        g1 = next(v for v in verknuepfungen(bg.spec, bg.quellen) if v.id == "g1")
        grenze = next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == "g1")
        sw_baugruppe.unterdruecke(asm, grenze, True)
        ergebnis["status_grenze_unterdrueckt"] = _status(komponenten)
        antrieb = sw_baugruppe.treibe(asm, g1, ent(g1.a), ent(g1.b), 0.0)
        ergebnis["status_mit_antrieb"] = _status(komponenten)
        wellen = ("ritzelwelle", "antriebswelle")
        lagen, summe = {}, {k: 0.0 for k in wellen}
        stellungen = []
        for wert in (0.0, 30.0, 60.0):
            t0 = time.perf_counter()
            meldung = sw_baugruppe.stelle(asm, antrieb, "abstand", wert)
            dauer = time.perf_counter() - t0
            jetzt = {k: sw_baugruppe.transform(komponenten[k]) for k in ("zahnstange", *wellen)}
            if not lagen:
                x0 = in_mm(jetzt["zahnstange"][9])
            else:
                for k in wellen:
                    summe[k] += _drehwinkel_z(lagen[k], jetzt[k])
            lagen = jetzt
            stellungen.append({
                "wert": wert, "meldung": meldung, "s": round(dauer, 3), "privat_mb": privat_mb(pid),
                "x_zahnstange_mm": round(in_mm(jetzt["zahnstange"][9]), 4),
                "verschiebung_zahnstange_mm": round(in_mm(jetzt["zahnstange"][9]) - x0, 4),
                "drehung_z_aufsummiert": {k: round(w, 4) for k, w in summe.items()},
                "lage_transform2": {k: [round(v, 6) for v in t] for k, t in jetzt.items()}})
        ergebnis["stellungen"] = stellungen
        ergebnis["soll"] = {"zahnstange_mm": [30, 60], "ritzelwelle_grad": [85.9437, 171.8873],
                            "antriebswelle_grad": [-42.9718, -85.9437]}
        sw_baugruppe.loesche(asm, antrieb)
        sw_baugruppe.unterdruecke(asm, grenze, False)
        ergebnis["status_danach"] = _status(komponenten)
        ergebnis["verknuepfungen_danach"] = [f.Name for f in sw_baugruppe.verknuepfungen(asm)]
        ergebnis["ruecklesen"] = {n: _lesen(next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == n))
                                  for n in ("k1", "k2")}
    finally:
        if asm is not None:
            sw.schliesse(app, asm)  # ohne Speichern (wie swki pruefen)
        for model in reversed(offen):
            sw.schliesse(app, model)
    ergebnis["privat_mb_nachher"] = privat_mb(pid)
    return ergebnis


if __name__ == "__main__":
    if sys.argv[1:] == ["neuoeffnen"]:
        lauf("s14b_kopplung_neuoeffnen", _neuoeffnen)
    else:
        lauf("s14b_kopplung", _untersuche)