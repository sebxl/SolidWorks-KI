"""Merkmalsbericht aus der STEP eines gebauten Teils: Bohrungen (mit Senkung, Tiefe, durch/blind, Eintrittsseite),
Zapfen, Rundungen, ebene Flächen je Richtung und Höhe, schräge Flächen, Kegel, Hüllquader und Körperzahl.

Ersetzt für Agent und Prüfer den Blick auf die Screenshots: Lage, Seite und Maß jedes Merkmals stehen als Zahlen da.
Alle Längen in mm, Koordinaten wie im Modell; Winkel in Grad. Nur achsparallele Achsen und Normalen bekommen einen
Namen (X, Y, Z bzw. +X … −Z); andere werden als Richtungsvektor genannt.
"""

import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from swki.pruefung.step import Flaeche, Modell, lies_step

ACHSEN = "XYZ"
MAX_ZEILEN = 60
_TOL = 0.01          # mm: gleiche Lage, gleicher Radius, gleiche Höhe
_PARALLEL = 1 - 1e-6
_VOLL_GRAD = 340.0   # Abdeckung um die Achse, ab der ein Zylinder als voll gilt (Stützpunkte alle 15°: Lücke ≤ 15°)


# --- Grundlagen ---------------------------------------------------------------------------------------------------


def _achsname(a: np.ndarray) -> str | None:
    for i in range(3):
        if abs(a[i]) > _PARALLEL:
            return ACHSEN[i]
    return None


def _richtungsname(n: np.ndarray) -> str | None:
    for i in range(3):
        if abs(n[i]) > _PARALLEL:
            return ("+" if n[i] > 0 else "-") + ACHSEN[i]
    return None


def _kanonisch(a: np.ndarray) -> np.ndarray:
    """Achsrichtung ohne Vorzeichen: größte Komponente positiv."""
    return a if a[int(np.argmax(np.abs(a)))] > 0 else -a


def _abdeckung(punkte: np.ndarray, o: np.ndarray, a: np.ndarray) -> float:
    """Überstrichener Winkel (Grad) der Punkte um die Achse (o, a): 360 minus größte Lücke."""
    x = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    x = x - a * (x @ a)
    x /= np.linalg.norm(x)
    y = np.cross(a, x)
    d = punkte - o
    radial = d - np.outer(d @ a, a)
    gueltig = np.linalg.norm(radial, axis=1) > 1e-6
    if gueltig.sum() < 2:
        return 0.0
    w = np.sort(np.degrees(np.arctan2(radial[gueltig] @ y, radial[gueltig] @ x)) % 360)
    luecken = np.diff(np.concatenate([w, [w[0] + 360]]))
    return float(360 - luecken.max())


def _achslinie(o: np.ndarray, a: np.ndarray) -> np.ndarray:
    """Punkt der Achse, der dem Ursprung am nächsten liegt (Lage der Achslinie unabhängig vom Ursprung der Fläche)."""
    return o - a * (o @ a)


def _z(v: float) -> str:
    """0,01 mm, Dezimalkomma, ohne überflüssige Nullen."""
    t = f"{v:.2f}".rstrip("0").rstrip(".")
    return ("0" if t in ("-0", "") else t).replace(".", ",")


def _mitte_text(achse: str, mitte: dict) -> str:
    if "linie" in mitte:   # schräge Achse: Punkt der Achslinie
        return "(" + " | ".join(_z(v) for v in mitte["linie"]) + ")"
    return "(" + " | ".join(f"{k} {_z(v)}" for k, v in mitte.items()) + ")"


def _quer(achse: str) -> list[int]:
    return [i for i in range(3) if ACHSEN[i] != achse]


# --- Rotationsflächen gruppieren ----------------------------------------------------------------------------------


def _rotationsgruppen(flaechen: list[Flaeche], typ: str) -> list[dict]:
    """Flächen gleicher Art (Zylinder oder Kegel) auf derselben Achslinie mit gleichem Radius/Kegel und sich
    berührenden Bereichen entlang der Achse zu einem Element zusammenfassen (SolidWorks teilt volle Zylinder in zwei
    Hälften). Ergebnis je Element: achse (kanonisch), linie, innen, Bereich s0…s1 (Koordinate entlang der Achse),
    Radien an s0/s1, Abdeckung in Grad."""
    roh = []
    for f in flaechen:
        if f.typ != typ or len(f.punkte) == 0:
            continue
        a = _kanonisch(f.achse)
        s = f.punkte @ a
        s0, s1 = float(s.min()), float(s.max())
        if typ == "zylinder":
            r0 = r1 = f.radius
        else:   # Kegel: Radius wächst in Richtung der Platzierungsachse
            richtung = 1.0 if f.achse @ a > 0 else -1.0
            sp = float(f.ursprung @ a)
            r0 = f.radius + richtung * (s0 - sp) * math.tan(f.halbwinkel)
            r1 = f.radius + richtung * (s1 - sp) * math.tan(f.halbwinkel)
        roh.append({"flaechen": [f], "achse": a, "linie": _achslinie(f.ursprung, a), "innen": not f.gleichsinnig,
                    "s0": s0, "s1": s1, "r0": r0, "r1": r1, "halbwinkel": f.halbwinkel})
    gruppen: list[dict] = []
    for e in roh:
        for g in gruppen:
            if (g["innen"] == e["innen"] and np.allclose(g["achse"], e["achse"], atol=1e-6)
                    and np.linalg.norm(g["linie"] - e["linie"]) < _TOL
                    and e["s0"] <= g["s1"] + _TOL and g["s0"] <= e["s1"] + _TOL
                    and _radius_bei(g, e["s0"]) is not None and abs(_radius_bei(g, e["s0"]) - e["r0"]) < _TOL
                    and abs(_radius_bei(g, e["s1"]) - e["r1"]) < _TOL):
                g["flaechen"] += e["flaechen"]
                if e["s0"] < g["s0"]:
                    g["s0"], g["r0"] = e["s0"], e["r0"]
                if e["s1"] > g["s1"]:
                    g["s1"], g["r1"] = e["s1"], e["r1"]
                break
        else:
            gruppen.append(e)
    for g in gruppen:
        punkte = np.vstack([f.punkte for f in g["flaechen"]])
        g["abdeckung"] = _abdeckung(punkte, g["linie"], g["achse"])
    return gruppen


def _radius_bei(g: dict, s: float) -> float | None:
    if abs(g["s1"] - g["s0"]) < 1e-9:
        return g["r0"]
    return g["r0"] + (g["r1"] - g["r0"]) * (s - g["s0"]) / (g["s1"] - g["s0"])


# --- Bohrungen ----------------------------------------------------------------------------------------------------


def _boden(ebenen: list[Flaeche], a: np.ndarray, linie: np.ndarray, s: float, r: float) -> bool:
    """Liegt bei s eine ebene Fläche quer zur Achse, die ganz innerhalb des Radius r bleibt (Bohrungsgrund)?"""
    for f in ebenen:
        if abs(abs(f.achse @ a) - 1) > 1e-6 or abs(float(f.ursprung @ a) - s) > _TOL or len(f.punkte) == 0:
            continue
        d = f.punkte - linie
        radial = np.linalg.norm(d - np.outer(d @ a, a), axis=1)
        if radial.max() <= r + _TOL:
            return True
    return False


def _bohrungen(zylinder: list[dict], kegel: list[dict], ebenen: list[Flaeche]) -> list[dict]:
    """Innere volle Zylinder und Kegel auf einer Achslinie, die entlang der Achse aneinander anschließen, bilden einen
    Bohrungszug (Senkung, Bohrung, Bohrspitze). Enden: offen, Boden (ebener Grund) oder Spitze (Kegel bis r = 0)."""
    teile = [g for g in zylinder + kegel if g["innen"] and g["abdeckung"] >= _VOLL_GRAD]
    teile.sort(key=lambda g: g["s0"])
    zuege: list[list[dict]] = []
    for t in teile:
        for z in zuege:
            if (np.allclose(z[0]["achse"], t["achse"], atol=1e-6) and np.linalg.norm(z[0]["linie"] - t["linie"]) < _TOL
                    and t["s0"] <= max(x["s1"] for x in z) + _TOL):
                z.append(t)
                break
        else:
            zuege.append([t])
    erg = []
    for z in zuege:
        a, linie = z[0]["achse"], z[0]["linie"]
        s0, s1 = min(t["s0"] for t in z), max(t["s1"] for t in z)
        z.sort(key=lambda t: (t["s0"], t["s1"]))
        enden = {}
        for seite, s, rand in (("-", s0, z[0]), ("+", s1, max(z, key=lambda t: t["s1"]))):
            r = rand["r0"] if seite == "-" else rand["r1"]
            if r < _TOL:
                enden[seite] = "spitze"
            elif _boden(ebenen, a, linie, s, r):
                enden[seite] = "boden"
            else:
                enden[seite] = "offen"
        achse = _achsname(a)
        abschnitte = []
        for t in z:
            if t in zylinder:
                abschnitte.append({"art": "zylinder", "d": round(2 * t["r0"], 4), "s0": round(t["s0"], 4),
                                   "s1": round(t["s1"], 4)})
            else:
                abschnitte.append({"art": "kegel", "d0": round(2 * t["r0"], 4), "d1": round(2 * t["r1"], 4),
                                   "winkel": round(math.degrees(2 * t["halbwinkel"]), 3),
                                   "s0": round(t["s0"], 4), "s1": round(t["s1"], 4)})
        b = {"achse": achse or [round(float(c), 6) for c in a], "s0": round(s0, 4), "s1": round(s1, 4),
             "enden": enden, "abschnitte": abschnitte, "durch": enden["-"] == "offen" and enden["+"] == "offen"}
        if achse:
            b["mitte"] = {ACHSEN[i]: round(float(linie[i]), 4) for i in _quer(achse)}
        else:
            b["linie"] = [round(float(c), 4) for c in linie]
        erg.append(b)
    return erg


def bohrung_von(b: dict, eintritt: str) -> dict:
    """Sicht von der Eintrittsseite ('+' oder '-' entlang der Achse): Tiefe bis zum Ende der letzten Zylinderwand
    (ohne Bohrspitze), Zylinderabschnitte in Bohrrichtung mit Länge."""
    zyl = [t for t in b["abschnitte"] if t["art"] == "zylinder"]
    if eintritt == "+":
        zyl = sorted(zyl, key=lambda t: -t["s1"])
        start = b["s1"]
        tiefe = start - min(t["s0"] for t in zyl) if zyl else 0.0
    else:
        zyl = sorted(zyl, key=lambda t: t["s0"])
        start = b["s0"]
        tiefe = max(t["s1"] for t in zyl) - start if zyl else 0.0
    return {"tiefe": round(tiefe, 4), "zylinder": [{"d": t["d"], "laenge": round(t["s1"] - t["s0"], 4)} for t in zyl]}


# --- Bericht ------------------------------------------------------------------------------------------------------


def merkmale(modell: Modell) -> dict:
    fl = modell.flaechen
    alle = np.vstack([f.punkte for f in fl if len(f.punkte)]) if fl else np.zeros((1, 3))
    lo, hi = alle.min(axis=0), alle.max(axis=0)
    ebenen = [f for f in fl if f.typ == "ebene"]
    zylinder = _rotationsgruppen(fl, "zylinder")
    kegel = _rotationsgruppen(fl, "kegel")
    bohrungen = _bohrungen(zylinder, kegel, ebenen)
    in_bohrung = {id(f) for g in zylinder + kegel if g["innen"] and g["abdeckung"] >= _VOLL_GRAD
                  for f in g["flaechen"]}

    zapfen, rundungen = [], []
    for g in zylinder:
        achse = _achsname(g["achse"])
        lage = ({ACHSEN[i]: round(float(g["linie"][i]), 4) for i in _quer(achse)} if achse
                else {"linie": [round(float(c), 4) for c in g["linie"]]})
        if g["abdeckung"] >= _VOLL_GRAD:
            if not g["innen"]:
                zapfen.append({"achse": achse or [round(float(c), 6) for c in g["achse"]], "d": round(2 * g["r0"], 4),
                               "mitte": lage, "s0": round(g["s0"], 4), "s1": round(g["s1"], 4)})
        else:
            rundungen.append({"r": round(g["r0"], 4), "art": "konkav" if g["innen"] else "konvex",
                              "achse": achse or [round(float(c), 6) for c in g["achse"]], "mitte": lage,
                              "abdeckung": round(g["abdeckung"], 1), "s0": round(g["s0"], 4), "s1": round(g["s1"], 4)})
    for f in fl:
        if f.typ == "torus":
            rundungen.append({"r": round(f.radius2, 4), "art": "konkav" if not f.gleichsinnig else "konvex",
                              "torus": True, "achse": _achsname(_kanonisch(f.achse)) or
                              [round(float(c), 6) for c in f.achse]})

    kegel_frei = []
    for g in kegel:
        if any(id(f) in in_bohrung for f in g["flaechen"]):
            continue
        achse = _achsname(g["achse"])
        kegel_frei.append({"achse": achse or [round(float(c), 6) for c in g["achse"]],
                           "mitte": ({ACHSEN[i]: round(float(g["linie"][i]), 4) for i in _quer(achse)} if achse
                                     else {"linie": [round(float(c), 4) for c in g["linie"]]}),
                           "art": "innen" if g["innen"] else "aussen", "d0": round(2 * g["r0"], 4),
                           "d1": round(2 * g["r1"], 4), "winkel": round(math.degrees(2 * g["halbwinkel"]), 3),
                           "s0": round(g["s0"], 4), "s1": round(g["s1"], 4)})

    flaechen_je_richtung: dict = defaultdict(list)
    schraege: list[dict] = []
    for f in ebenen:
        if len(f.punkte) == 0:
            continue
        n = f.normale
        name = _richtungsname(n)
        if name is None:
            nah = int(np.argmax(np.abs(n)))
            schraege.append({"normale": [round(float(c), 4) for c in n],
                             "winkel_zu": ACHSEN[nah], "winkel": round(math.degrees(math.acos(min(1.0, abs(n[nah])))), 3),
                             "min": [round(float(c), 4) for c in f.punkte.min(axis=0)],
                             "max": [round(float(c), 4) for c in f.punkte.max(axis=0)]})
            continue
        i = ACHSEN.index(name[1])
        flaechen_je_richtung[name].append({"hoehe": round(float(f.ursprung[i]), 4),
                                           "min": f.punkte.min(axis=0), "max": f.punkte.max(axis=0)})
    ebene_flaechen = {}
    for name, liste in flaechen_je_richtung.items():
        i = ACHSEN.index(name[1])
        hoehen: dict = {}
        for e in liste:
            schluessel = next((h for h in hoehen if abs(h - e["hoehe"]) < _TOL), e["hoehe"])
            h = hoehen.setdefault(schluessel, {"hoehe": schluessel, "anzahl": 0, "min": e["min"], "max": e["max"]})
            h["anzahl"] += 1
            h["min"], h["max"] = np.minimum(h["min"], e["min"]), np.maximum(h["max"], e["max"])
        ebene_flaechen[name] = [
            {"hoehe": h["hoehe"], "anzahl": h["anzahl"],
             "bereich": {ACHSEN[k]: [round(float(h["min"][k]), 4), round(float(h["max"][k]), 4)] for k in range(3) if k != i}}
            for h in sorted(hoehen.values(), key=lambda h: -h["hoehe"] if name[0] == "+" else h["hoehe"])
        ]

    sonstige: dict = defaultdict(int)
    for f in fl:
        if f.typ.startswith("sonstige") or f.typ == "kugel":
            sonstige[f.typ.split(":")[-1]] += 1

    return {
        "huellquader": {"min": [round(float(c), 4) for c in lo], "max": [round(float(c), 4) for c in hi],
                        "kanten": [round(float(c), 4) for c in hi - lo]},
        "koerper": modell.koerper, "flaechen": len(fl),
        "bohrungen": bohrungen, "zapfen": zapfen, "rundungen": rundungen, "kegel": kegel_frei,
        "ebenen": {k: ebene_flaechen[k] for k in sorted(ebene_flaechen, key=lambda n: (n[1], n[0] == "-"))},
        "schraege": schraege, "sonstige": dict(sonstige),
    }


def merkmale_aus_datei(pfad: Path) -> dict:
    return merkmale(lies_step(pfad))


# --- Textform -----------------------------------------------------------------------------------------------------


def _bohrung_text(b: dict) -> str:
    achse = b["achse"] if isinstance(b["achse"], str) else "(" + ", ".join(_z(c) for c in b["achse"]) + ")"
    teile = []
    for t in b["abschnitte"]:
        if t["art"] == "zylinder":
            teile.append(f"Ø{_z(t['d'])} {achse} {_z(t['s0'])}…{_z(t['s1'])}")
        else:
            teile.append(f"Kegel {_z(t['winkel'])}° Ø{_z(t['d0'])}→{_z(t['d1'])} {achse} {_z(t['s0'])}…{_z(t['s1'])}")
    if b["durch"]:
        art = "durch"
    else:
        offen = [s for s, e in b["enden"].items() if e == "offen"]
        grund = [e for e in b["enden"].values() if e != "offen"]
        art = (f"blind von {offen[0]}{achse}, Grund {grund[0]}" if len(offen) == 1 else
               f"geschlossen ({b['enden']['-']}/{b['enden']['+']})")
        if len(offen) == 1:
            art += f", Tiefe {_z(bohrung_von(b, offen[0])['tiefe'])}"
    return f"{art}: " + " + ".join(teile)


def als_text(m: dict) -> str:
    h = m["huellquader"]
    zeilen = [
        "Hüllquader " + "  ".join(f"{a} {_z(h['min'][k])}…{_z(h['max'][k])}" for k, a in enumerate(ACHSEN))
        + f"  ({' × '.join(_z(v) for v in h['kanten'])})   Körper {m['koerper']}   Flächen {m['flaechen']}",
    ]
    gruppen: dict = defaultdict(list)
    for b in m["bohrungen"]:
        gruppen[_bohrung_text(b)].append(b)
    for text, liste in gruppen.items():
        lagen = " ".join(_mitte_text("", b["mitte"] if "mitte" in b else {"linie": b["linie"]}) for b in liste)
        zeilen.append(f"Bohrung {len(liste)}× {text}  bei {lagen}")
    for z in m["zapfen"]:
        achse = z["achse"] if isinstance(z["achse"], str) else str(z["achse"])
        zeilen.append(f"Zapfen Ø{_z(z['d'])} Achse {achse} {_z(z['s0'])}…{_z(z['s1'])} bei {_mitte_text(achse, z['mitte'])}")
    rund: dict = defaultdict(int)
    for r in m["rundungen"]:
        rund[(r["r"], r["art"], r["achse"] if isinstance(r["achse"], str) else "schräg", r.get("torus", False))] += 1
    for (r, art, achse, torus), n in sorted(rund.items(), key=lambda x: x[0][0]):
        zeilen.append(f"Rundung R{_z(r)} {art} {'Torus' if torus else 'Achse ' + achse} ×{n}")
    kegel: dict = defaultdict(list)
    for k in m["kegel"]:
        kegel[f"{k['art']} {_z(k['winkel'])}° Ø{_z(k['d0'])}→{_z(k['d1'])} Achse {k['achse']} "
              f"{_z(k['s0'])}…{_z(k['s1'])}"].append(k)
    for text, liste in kegel.items():
        lagen = " ".join(_mitte_text("", k["mitte"]) for k in liste)
        zeilen.append(f"Kegel {len(liste)}× {text}  bei {lagen}")
    for name, hoehen in m["ebenen"].items():
        teile = []
        for e in hoehen:
            b = e["bereich"]
            teile.append(f"{name[1]} {_z(e['hoehe'])} [" + " ".join(f"{a} {_z(v[0])}…{_z(v[1])}" for a, v in b.items())
                         + "]" + (f" ×{e['anzahl']}" if e["anzahl"] > 1 else ""))
        zeilen.append(f"Ebene {name}: " + "; ".join(teile))
    schraeg: dict = defaultdict(int)
    for s in m["schraege"]:
        schraeg[(s["winkel_zu"], s["winkel"])] += 1
    for (achse, w), n in sorted(schraeg.items()):
        zeilen.append(f"Schräge Ebene {_z(w)}° zu {achse} ×{n}")
    if m["sonstige"]:
        zeilen.append("Sonstige Flächen: " + ", ".join(f"{k} ×{v}" for k, v in m["sonstige"].items()))
    if len(zeilen) > MAX_ZEILEN:
        rest = len(zeilen) - MAX_ZEILEN + 1
        zeilen = zeilen[:MAX_ZEILEN - 1] + [f"… {rest} weitere Zeilen (siehe merkmale.json)"]
    return "\n".join(zeilen)
