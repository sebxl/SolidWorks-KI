"""S13c (Stufe 4a): Warum trägt die Winkelgrenze nach Speichern und Neuöffnen nur noch 0°?

Befund aus Task 7 (Diagnose Schwenk): In der Bau-Sitzung lässt die Winkelgrenze g2 (hebel +z / schieber +z, gleich,
0…90°) den Antrieb auf 22,5 / 45 / 90° zu; in der gespeicherten und neu geöffneten Baugruppe scheitert jeder Wert außer 0
mit Code 47 (auch negative Werte). MinimumVariation/MaximumVariation/Alignment/D1 sind in beiden Fällen gleich.
Hypothese: Die Grenze wird bei genau 0° zwischen parallelen Flächen gespeichert (Drehsinn aus 0° nicht bestimmbar).

Jede Variante: Probe wie S13 in derselben Sitzung aufbauen (Grenze g1 für den Hub, Grenze g2 für den Schwenk), speichern,
schließen, neu öffnen, Antriebe anlegen und stellen; Min/MaxVariation, Alignment und D1 vor dem Speichern und nach dem Öffnen.

E1 Reproduktion: g2 an hebel +z / schieber +z, gleich, 0…90, gespeichert bei 0 → nach dem Öffnen 22,5 / 45 / 90.
E2 Speicherwinkel: wie E1, vor dem Speichern per Antrieb auf 10° gestellt, Antrieb gelöscht → 0 / 22,5 / 45 / 90.
E3 Flip: wie E1, AddMate5 mit Flip = True → 22,5 / 45 / 90 und −22,5.
E4 nicht parallel in Grundstellung: g2 an hebel −x / schieber +z (Normalen senkrecht), 90…180, gespeichert bei 90 →
   112,5 / 135 / 170 (Drehsinn aus der Drehachse des Hebels).
E5 wie E1, nach dem Öffnen ForceRebuild3(False) vor dem Anlegen der Antriebe.
E6 wie `bauen`: vor dem Speichern Antrieb g1.antrieb und g2.antrieb bei min anlegen (Grundstellung) und beide wieder löschen
   (g2 zuerst) → nach dem Öffnen 22,5 / 45 / 90. (Nachgeschoben: E1 geht nach dem Neuöffnen, der Unterschied zur Pipeline ist
   die Grundstellung.)
E7 wie E6, aber nur g2.antrieb (ohne Hub-Antrieb).
In E6/E7 zusätzlich: Alignment und Flipped von g1/g2 (und der Antriebe) vor dem Anlegen, mit Antrieb, nach dem Löschen
(Verdacht: kippt das Anlegen von g2.antrieb die Grenze g2 still um, Spike S12 Zeile 5?).
E8 wie E6, aber g2.antrieb in der Grundstellung mit AddMate5 Flip = True.
E9 wie E6, aber g2.antrieb in der Grundstellung mit entgegengesetzter Ausrichtung.
E10 wie E6, aber nur g1.antrieb (Hub) in der Grundstellung (E6 scheitert, E7 mit nur g2.antrieb geht).
E11 wie E6, aber die Antriebe in Erstellungsreihenfolge gelöscht (g1 zuerst).
E12 wie E6, aber g2.antrieb zuerst angelegt, dann g1.antrieb (gelöscht in umgekehrter Reihenfolge: g1 zuerst).

Speicherregel: vor jeder Variante Private Bytes lesen; ab 4500 MB nicht fahren (blockiert_vor im Ergebnis); der Aufruf mit den
übrigen Varianten als Argumente (z. B. `-m spikes.s13c_winkelgrenze E3 E4 E5`) ergänzt das vorhandene Ergebnis.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s13c_winkelgrenze [E1 … E5]
"""

import json
import shutil
import sys
import traceback
from pathlib import Path

from spikes import s13_bewegung as s13
from spikes._gemeinsam import ERGEBNISSE, lauf
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.referenzen import loese_im_teil
from swki.compiler import sw
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.messen import oeffne
from swki.verbindung import byref_long, grad, mm, verbinde

NAME = "s13c_winkelgrenze"
AUFTRAG = "S13C"
SCHWELLE_MB = 4500
F1 = {"feature": "f1"}

VARIANTEN = {
    "E1": {"flaeche_a": "+z", "unten": 0, "oben": 90, "stellungen": [22.5, 45, 90]},
    "E2": {"flaeche_a": "+z", "unten": 0, "oben": 90, "vorwinkel": 10, "stellungen": [0, 22.5, 45, 90]},
    "E3": {"flaeche_a": "+z", "unten": 0, "oben": 90, "flip": True, "stellungen": [22.5, 45, 90, -22.5]},
    "E4": {"flaeche_a": "-x", "unten": 90, "oben": 180, "stellungen": [112.5, 135, 170]},
    "E5": {"flaeche_a": "+z", "unten": 0, "oben": 90, "neu_aufbauen": True, "stellungen": [22.5, 45, 90]},
    "E6": {"flaeche_a": "+z", "unten": 0, "oben": 90, "grundstellung": ["g1", "g2"], "stellungen": [22.5, 45, 90]},
    "E7": {"flaeche_a": "+z", "unten": 0, "oben": 90, "grundstellung": ["g2"], "stellungen": [22.5, 45, 90]},
    "E10": {"flaeche_a": "+z", "unten": 0, "oben": 90, "grundstellung": ["g1"], "stellungen": [22.5, 45, 90]},
    "E11": {"flaeche_a": "+z", "unten": 0, "oben": 90, "grundstellung": ["g1", "g2"], "loeschen_in_erstellung": True,
            "stellungen": [22.5, 45, 90]},
    "E12": {"flaeche_a": "+z", "unten": 0, "oben": 90, "grundstellung": ["g2", "g1"], "stellungen": [22.5, 45, 90]},
    "E8": {"flaeche_a": "+z", "unten": 0, "oben": 90, "grundstellung": ["g1", "g2"], "antrieb_flip": True,
           "stellungen": [22.5, 45, 90]},
    "E9": {"flaeche_a": "+z", "unten": 0, "oben": 90, "grundstellung": ["g1", "g2"],
           "antrieb_ausrichtung": "entgegengesetzt", "stellungen": [22.5, 45, 90]},
}


def _grenze_winkel(asm, name, a, b, ausrichtung, unten, oben, flip):
    """Winkelgrenze direkt über AddMate5 (wie s13._grenze, zusätzlich mit Flip)."""
    sw.auswahl_leeren(asm)
    sw_baugruppe.waehle(asm, a, False)
    sw_baugruppe.waehle(asm, b, True)
    status = byref_long()
    vorher = len(sw_baugruppe.verknuepfungen(asm))
    mate = asm.AddMate5(s13.TYP["winkel"], sw_baugruppe.AUSRICHTUNG[ausrichtung], flip, 0.0, 0.0, 0.0, 1, 1,
                        grad(unten), grad(oben), grad(unten), False, False, 0, status)
    sw.auswahl_leeren(asm)
    alle = sw_baugruppe.verknuepfungen(asm)
    neu = alle[-1] if mate is not None and len(alle) > vorher else None
    ergebnis = {"status": status.value, "mate": mate is not None, "neu": neu is not None, "flip": flip}
    if neu is not None:
        neu.Name = name
        ergebnis["rebuild"] = s13._rebuild(asm)
        ergebnis["fehlercode"] = sw_baugruppe.fehlercode(neu)
    return neu, ergebnis


def _lesen(asm, name):
    """Min/MaxVariation (mm bzw. Grad), Alignment, Flipped, D1 einer Verknüpfung."""
    import math
    f = {x.Name.lower(): x for x in sw_baugruppe.verknuepfungen(asm)}[name]
    spez = f.GetSpecificFeature2
    winkel = spez.Type == s13.TYP["winkel"]
    ergebnis = {}
    for attr in ("MinimumVariation", "MaximumVariation"):
        wert = getattr(spez, attr)
        ergebnis[attr] = round(math.degrees(wert) if winkel else wert * 1000, 4)
    for attr in ("Alignment", "Flipped"):
        try:
            ergebnis[attr] = getattr(spez, attr)
        except Exception as e:  # Spike: festhalten
            ergebnis[attr] = repr(e)
    d1 = f.Parameter("D1")
    ergebnis["D1"] = None if d1 is None else round(math.degrees(d1.SystemValue) if winkel else d1.SystemValue * 1000, 4)
    return ergebnis


def _antrieb_winkel(asm, name, a, b, ausrichtung, wert, flip):
    """Winkelantrieb direkt über AddMate5 (für E8/E9: Flip bzw. Ausrichtung vorgeben)."""
    sw.auswahl_leeren(asm)
    sw_baugruppe.waehle(asm, a, False)
    sw_baugruppe.waehle(asm, b, True)
    status = byref_long()
    vorher = len(sw_baugruppe.verknuepfungen(asm))
    mate = asm.AddMate5(s13.TYP["winkel"], sw_baugruppe.AUSRICHTUNG[ausrichtung], flip, 0.0, 0.0, 0.0, 1, 1,
                        grad(wert), grad(wert), grad(wert), False, False, 0, status)
    sw.auswahl_leeren(asm)
    alle = sw_baugruppe.verknuepfungen(asm)
    if mate is None or len(alle) <= vorher or status.value != 1:
        raise RuntimeError(f"Antrieb {name}: AddMate5 Status {status.value}")
    neu = alle[-1]
    neu.Name = name
    s13._rebuild(asm)
    return neu


def _zeige(asm, namen):
    return {n: _lesen(asm, n) for n in namen}


def _lage(k, t0):
    return s13._achse_winkel(t0, sw_baugruppe.transform(k["hebel"]))


def _variante(app, r, teile, ordner, name, cfg):
    e = {"konfiguration": cfg}
    pid = int(app.GetProcessID)
    e["privat_mb_vorher"] = s13._privat_mb(pid)
    asm, k, ent = s13._probe(app, r, teile)
    pfad = ordner / f"S13C_{name}.sldasm"
    try:
        g1, e["g1_anlegen"] = s13._grenze(asm, "g1", "abstand", ent("schieber", {**F1, "flaeche": "-x"}),
                                          ent("platte", {**F1, "flaeche": "-x"}), "gleich", 0, 100)
        t_hebel = sw_baugruppe.transform(k["hebel"])
        g2, e["g2_anlegen"] = _grenze_winkel(asm, "g2", ent("hebel", {**F1, "flaeche": cfg["flaeche_a"]}),
                                             ent("schieber", {**F1, "flaeche": "+z"}), "gleich", cfg["unten"],
                                             cfg["oben"], cfg.get("flip", False))
        if g2 is None:
            e["abbruch"] = "g2 nicht angelegt"
            return e
        e["vor_speichern"] = {"g1": _lesen(asm, "g1"), "g2": _lesen(asm, "g2"), "hebel_lage": _lage(k, t_hebel)}
        if "vorwinkel" in cfg:
            t_ref = sw_baugruppe.transform(k["hebel"])
            a2 = sw_baugruppe.verknuepfe(asm, s13._v("g2.antrieb", "winkel", "gleich", cfg["unten"]),
                                         ent("hebel", {**F1, "flaeche": cfg["flaeche_a"]}),
                                         ent("schieber", {**F1, "flaeche": "+z"}), {})
            e["vorwinkel_stellen"] = s13._stelle(asm, a2, "winkel", cfg["vorwinkel"], k["hebel"], t_ref)
            sw_baugruppe.loesche(asm, a2)
            e["vor_speichern"]["hebel_lage_nach_loeschen"] = _lage(k, t_ref)
        if cfg.get("grundstellung"):  # wie bauen._grundstellung: je Antrieb anlegen und auf min stellen, dann löschen
            antriebe = {}
            e["umkehr"] = {"vor_antrieb": _zeige(asm, ["g1", "g2"])}
            for gn in cfg["grundstellung"]:
                if gn == "g1":
                    a = sw_baugruppe.verknuepfe(asm, s13._v("g1.antrieb", "abstand", "gleich", 0),
                                                ent("schieber", {**F1, "flaeche": "-x"}),
                                                ent("platte", {**F1, "flaeche": "-x"}), {})
                    antriebe[gn] = (a, s13._stelle(asm, a, "abstand", 0, k["schieber"], sw_baugruppe.transform(k["schieber"])))
                elif "antrieb_flip" in cfg or "antrieb_ausrichtung" in cfg:
                    a = _antrieb_winkel(asm, "g2.antrieb", ent("hebel", {**F1, "flaeche": cfg["flaeche_a"]}),
                                        ent("schieber", {**F1, "flaeche": "+z"}), cfg.get("antrieb_ausrichtung", "gleich"),
                                        cfg["unten"], cfg.get("antrieb_flip", False))
                    antriebe[gn] = (a, s13._stelle(asm, a, "winkel", cfg["unten"], k["hebel"], t_hebel))
                else:
                    a = sw_baugruppe.verknuepfe(asm, s13._v("g2.antrieb", "winkel", "gleich", cfg["unten"]),
                                                ent("hebel", {**F1, "flaeche": cfg["flaeche_a"]}),
                                                ent("schieber", {**F1, "flaeche": "+z"}), {})
                    antriebe[gn] = (a, s13._stelle(asm, a, "winkel", cfg["unten"], k["hebel"], t_hebel))
            e["grundstellung_stellen"] = {gn: v[1] for gn, v in antriebe.items()}
            e["umkehr"]["mit_antrieb"] = _zeige(asm, ["g1", "g2", *(f"{gn}.antrieb" for gn in antriebe)])
            for gn in (cfg["grundstellung"] if cfg.get("loeschen_in_erstellung") else reversed(cfg["grundstellung"])):
                sw_baugruppe.loesche(asm, antriebe[gn][0])
            e["vor_speichern"]["g2_nach_grundstellung"] = _lesen(asm, "g2")
            e["umkehr"]["nach_loeschen"] = _zeige(asm, ["g1", "g2"])
            e["vor_speichern"]["hebel_lage_nach_loeschen"] = _lage(k, t_hebel)
        sw.speichere(asm, pfad)
        namen = {x.Name2: n for n, x in k.items()}  # vor dem Schließen lesen
    finally:
        sw.schliesse(app, asm)
    asm = oeffne(app, pfad)
    try:
        sw_baugruppe.aufloesen(asm)
        k2 = {namen.get(x.Name2, x.Name2): x for x in sw_baugruppe.komponenten(asm)}

        def ent2(n, seite):
            return sw_baugruppe.in_baugruppe(k2[n], loese_im_teil(teile[n][1], seite))

        e["nach_oeffnen"] = {"g1": _lesen(asm, "g1"), "g2": _lesen(asm, "g2")}
        if cfg.get("neu_aufbauen"):
            e["force_rebuild3"] = bool(asm.ForceRebuild3(False))
            e["nach_force_rebuild"] = {"g1": _lesen(asm, "g1"), "g2": _lesen(asm, "g2"), "rebuild": s13._rebuild(asm)}
        t_ref = sw_baugruppe.transform(k2["hebel"])
        e["hebel_lage_nach_oeffnen"] = _lage(k2, t_ref)
        sw_baugruppe.verknuepfe(asm, s13._v("g1.antrieb", "abstand", "gleich", 0),
                                ent2("schieber", {**F1, "flaeche": "-x"}), ent2("platte", {**F1, "flaeche": "-x"}), {})
        wert0 = cfg["unten"]
        a2 = sw_baugruppe.verknuepfe(asm, s13._v("g2.antrieb", "winkel", "gleich", wert0),
                                     ent2("hebel", {**F1, "flaeche": cfg["flaeche_a"]}),
                                     ent2("schieber", {**F1, "flaeche": "+z"}), {})
        e["antriebe_angelegt"] = True
        e["umkehr_nach_oeffnen_mit_antrieb"] = _zeige(asm, ["g1", "g2", "g1.antrieb", "g2.antrieb"])
        t_ref = sw_baugruppe.transform(k2["hebel"])
        e["hebel_lage_mit_antrieb"] = _lage(k2, t_ref)
        e["stellungen"] = [s13._stelle(asm, a2, "winkel", w, k2["hebel"], t_ref) for w in cfg["stellungen"]]
        e["nach_stellungen"] = {"g2": _lesen(asm, "g2")}
    finally:
        sw.schliesse(app, asm)
    e["privat_mb_nachher"] = s13._privat_mb(pid)
    return e


def _untersuche():
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    gewaehlt = [a for a in sys.argv[1:] if a in VARIANTEN] or list(VARIANTEN)
    datei = ERGEBNISSE / f"{NAME}.json"
    ergebnis = {}
    if sys.argv[1:] and datei.exists():
        ergebnis = {k: v for k, v in json.loads(datei.read_text(encoding="utf-8")).items() if k not in ("ok", "fehler", "trace")}
    ergebnis.setdefault("varianten", {})
    ergebnis.pop("blockiert_vor", None)
    ergebnis["privat_mb_start"] = s13._privat_mb(int(app.GetProcessID))
    s13.AUFTRAG = AUFTRAG
    ordner = r.arbeitsordner / AUFTRAG
    shutil.rmtree(ordner, ignore_errors=True)
    ordner.mkdir(parents=True)
    teile = s13._teile(app, r, standard, ordner)
    try:
        for name in gewaehlt:
            mb = s13._privat_mb(int(app.GetProcessID))
            if mb >= SCHWELLE_MB:
                ergebnis["blockiert_vor"] = {"variante": name, "privat_mb": mb}
                break
            try:
                ergebnis["varianten"][name] = _variante(app, r, teile, ordner, name, VARIANTEN[name])
            except Exception:  # Spike: bis dahin Gemessenes nicht verlieren
                ergebnis["varianten"][name] = {"abbruch": traceback.format_exc()}
            lauf_zwischen = {"ok": True, **ergebnis}
            ERGEBNISSE.mkdir(parents=True, exist_ok=True)
            datei.write_text(json.dumps(lauf_zwischen, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    finally:
        for model, _ in reversed(list(teile.values())):
            sw.schliesse(app, model)
        shutil.rmtree(ordner, ignore_errors=True)
    ergebnis["privat_mb_ende"] = s13._privat_mb(int(app.GetProcessID))
    return ergebnis


if __name__ == "__main__":
    lauf(NAME, _untersuche)
