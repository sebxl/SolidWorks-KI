"""Zeichnungsableitung Z1.3 Stufe 3: Angabetexte (Bohrungsangaben) und Bohrbilder aus der Spec, ohne SolidWorks."""

import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from swki.spec.ausdruck import auswerten
from swki.zeichnung.lesbarkeit import _schneidet, _ueberlappt

FASE_SUFFIX = " × 45°"
_NORMEN = Path(__file__).parents[1] / "wissen" / "bohrungsnormen.yaml"


@dataclass(frozen=True)
class Bohrbild:
    merkmal: str
    anzahl: int
    teilkreis: float | None
    teilung: float | None
    reihe: str | None
    reihe_anzahl: int | None = None


def zahl(x: float) -> str:
    """Dezimalkomma, ohne nachgestellte Nullen."""
    text = f"{round(float(x), 4):.4f}".rstrip("0").rstrip(".")
    return (text or "0").replace(".", ",")


@lru_cache(maxsize=1)
def _normen() -> dict:
    return yaml.safe_load(_NORMEN.read_text(encoding="utf-8"))["normen"]["ISO"]


def _enthalten(spec: dict, fid: str) -> list[dict]:
    """Alle muster_*/spiegeln, die das Feature direkt oder über ein anderes Muster enthalten (innen nach außen)."""
    gefunden: list[dict] = []
    ids = {fid}
    neu = True
    while neu:
        neu = False
        for f in spec.get("features", []):
            if f.get("typ") in ("muster_linear", "muster_kreis", "spiegeln") and f not in gefunden \
                    and ids & set(f.get("features", [])):
                gefunden.append(f)
                ids.add(f["id"])
                neu = True
    return gefunden


def bohrbilder(spec: dict) -> dict[str, Bohrbild]:
    param = spec.get("parameter", {})
    bilder = {}
    for f in spec.get("features", []):
        if f.get("typ") not in ("bohrung", "normbohrung"):
            continue
        positionen = f.get("positionen") or [[0, 0]]
        anzahl, teilkreis, teilung, reihe, reihe_n = len(positionen), None, None, None, None
        for m in _enthalten(spec, f["id"]):
            if m["typ"] == "spiegeln":
                anzahl *= 2
            elif m["typ"] == "muster_kreis":
                anzahl *= int(auswerten(m["anzahl"], param))
                if teilkreis is None and f.get("positionen"):
                    try:
                        u, v = (auswerten(c, param) for c in positionen[0][:2])
                        teilkreis = round(2 * math.hypot(u, v), 6)
                    except (ValueError, TypeError, KeyError):
                        teilkreis = None
            else:
                r1, r2 = m["richtung1"], m.get("richtung2")
                anzahl *= int(auswerten(r1["anzahl"], param)) * (int(auswerten(r2["anzahl"], param)) if r2 else 1)
                if r2 is None and teilung is None and len(positionen) == 1:
                    teilung, reihe = float(auswerten(r1["abstand"], param)), m["id"]
                    reihe_n = int(auswerten(r1["anzahl"], param))
        bilder[f["id"]] = Bohrbild(f["id"], anzahl, teilkreis, teilung, reihe, reihe_n)
    return bilder


def reihenzusatz(bild: Bohrbild) -> tuple[str, str]:
    """Präfix und Suffix für das Teilungsmaß einer Reihe, z. B. ("4 × ", " (= 120)")."""
    n = (bild.reihe_anzahl or bild.anzahl) - 1
    return f"{n} × ", f" (= {zahl(abs(n * (bild.teilung or 0)))})"


def _gewindekopf(groesse: str) -> str:
    """Gewindegröße nach ISO: „M12x1.5“ wird „M12 × 1,5“ (Dezimalkomma), „M6“ bleibt."""
    m = re.fullmatch(r"M(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)", groesse)
    return f"M{zahl(float(m.group(1)))} × {zahl(float(m.group(2)))}" if m else groesse


def _nenn(groesse: str) -> str:
    m = re.match(r"M(\d+(?:\.\d+)?)", groesse)
    return zahl(float(m.group(1))) if m else groesse


def bohrungsangabe(feature: dict, spec: dict, bild: Bohrbild) -> tuple[str, list[str]]:
    """(Text mit Zeilenumbrüchen, Meldungen) der Bohrungsangabe."""
    param = spec.get("parameter", {})
    meld: list[str] = []
    fid, art, groesse = feature["id"], feature.get("art"), str(feature.get("groesse", ""))
    zeilen: list[str] = []
    if feature["typ"] == "normbohrung":
        tab = _normen().get(art, {}).get(groesse)
        if tab is None:
            meld.append(f"ANGABE_UNBEKANNT: {fid} {art} {groesse} nicht in bohrungsnormen.yaml")
        if art == "gewinde":
            kopf = _gewindekopf(groesse)
            tiefe = feature.get("gewindetiefe", feature.get("tiefe"))
        elif art == "stift":
            kopf = f"Ø{zahl(float(groesse))}" if re.fullmatch(r"[\d.]+", groesse) else groesse
            tiefe = feature.get("tiefe")
        else:
            kopf = f"Ø{zahl(tab['durchgang'])}" if tab else groesse
            tiefe = feature.get("tiefe")
            if tab and art == "zylinderschraube":
                zeilen.append(f"Senkung Ø{zahl(tab['senkung_d'])} × {zahl(tab['senkung_t'])} tief")
            elif tab and art == "senkschraube":
                zeilen.append(f"Senkung Ø{zahl(tab['senkung_d'])} × {zahl(tab.get('senkwinkel', 90))}°")
    else:
        kopf, tiefe = f"Ø{zahl(auswerten(feature['durchmesser'], param))}", feature.get("tiefe")
        if senkung := feature.get("senkung"):
            zeilen.append(f"Senkung Ø{zahl(auswerten(senkung['durchmesser'], param))} × "
                          f"{zahl(auswerten(senkung['tiefe'], param))} tief")
    if feature.get("durch"):
        tief = "durch"
    elif tiefe is not None:
        tief = f"{zahl(auswerten(tiefe, param))} tief"
    else:
        tief = ""
        meld.append(f"ANGABE_UNVOLLSTAENDIG: {fid} Tiefe fehlt (weder durch noch tiefe/gewindetiefe)")
    kopfzeile = (f"{bild.anzahl} × " if bild.anzahl > 1 else "") + kopf + (f" – {tief}" if tief else "")
    fase = feature.get("fase")
    if fase == "nenn" and art == "gewinde":
        zeilen.append(f"Senkung Ø{_nenn(groesse)} × 90°")
    elif fase == "nenn":
        meld.append(f"ANGABE_UNVOLLSTAENDIG: {fid} fase nenn bei Art {art} nicht ausgegeben")
    elif fase is not None:
        zeilen.append(f"Fase {zahl(auswerten(fase, param))}{FASE_SUFFIX}")
    if bild.teilkreis is not None:
        zeilen.append(f"TK Ø{zahl(bild.teilkreis)}")
        try:
            u, v = (auswerten(c, param) for c in (feature.get("positionen") or [[0, 0]])[0][:2])
            if abs(u) > 1e-9 and abs(v) > 1e-9:
                meld.append(f"ANGABE_UNVOLLSTAENDIG: {fid} Winkellage der Bohrung im Lochkreis nicht angegeben "
                            f"(Position mit zwei Komponenten ungleich 0)")
        except (ValueError, TypeError, KeyError):
            pass
    elif any(m["typ"] == "muster_kreis" for m in _enthalten(spec, fid)):
        meld.append(f"ANGABE_UNVOLLSTAENDIG: {fid} Teilkreis nicht bestimmbar (Position fehlt oder unlesbar)")
    return "\n".join([kopfzeile, *zeilen]), meld


# --- Lage des Hinweistexts in der Zeichnung (Task 4) -----------------------------------------------------------------

HINWEIS_RICHTUNGEN_GRAD = (45, 135, 315, 225)
HINWEIS_ABSTAENDE_MM = (12.0, 18.0, 25.0, 35.0)


def hinweis_lagen(kreis: tuple[tuple[float, float], float], umriss: tuple[float, float, float, float],
                  hindernisse: list[tuple], groesse: tuple[float, float]) -> list[tuple[float, float]]:
    """Alle Lagen des Hinweistexts, beste zuerst (`hinweis_lagen_bewertet` ohne Bewertung)."""
    return [lage for _, lage in hinweis_lagen_bewertet(kreis, umriss, hindernisse, groesse)]


def hinweis_lagen_bewertet(kreis: tuple[tuple[float, float], float], umriss: tuple[float, float, float, float],
                           hindernisse: list[tuple], groesse: tuple[float, float]) -> list[tuple[tuple, tuple]]:
    """Alle Lagen des Hinweistexts einer Bohrungsangabe (Blatt-mm, Mitte des Texts), beste zuerst.

    Die Hinweislinie endet in Richtung 45°/135°/315°/225° im Abstand 12/18/25/35 mm von der Kreismitte; dort beginnt
    der Text (rechts davon bei 45°/315°, links bei 135°/225°), mittig in der Höhe. „Von der Ansichtsmitte weg zuerst“
    gilt in der Höhe: liegt die Bohrung über der Mitte des Umrisses, kommen 45°/135° vor 315°/225°, sonst umgekehrt;
    innerhalb eines Paars rechts vor links (Lesefluss; Plan Task 4 Step 1: Bohrung links oben → Text rechts oben).
    Reihenfolge: Abstand vor Richtung; zuerst Lagen, deren Textrechteck keine Strecke aus `hindernisse` kreuzt und
    außerhalb des Umrisses liegt, dann die ohne Kreuzung im Umriss, zuletzt die übrigen. Bewertung je Lage:
    (kreuzt, im Umriss, Rang) – kleiner ist besser (Wahl unter mehreren Bohrungen eines Bohrbilds)."""
    (mx, my), _ = kreis
    breite, hoehe = groesse
    oben = my >= (umriss[1] + umriss[3]) / 2
    paare = [(45, 135), (315, 225)] if oben else [(315, 225), (45, 135)]
    richtungen = [w for paar in paare for w in paar]
    lagen = []
    for i, (d, w) in enumerate((d, w) for d in HINWEIS_ABSTAENDE_MM for w in richtungen):
        ex, ey = mx + d * math.cos(math.radians(w)), my + d * math.sin(math.radians(w))
        cx = ex + breite / 2 if math.cos(math.radians(w)) > 0 else ex - breite / 2
        r = (cx - breite / 2, ey - hoehe / 2, cx + breite / 2, ey + hoehe / 2)
        kreuzt = any(_schneidet(a, b, r) for a, b in hindernisse)
        lagen.append(((kreuzt, _ueberlappt(r, umriss), i), (round(cx, 3), round(ey, 3))))
    return sorted(lagen)


def hinweis_lage(kreis: tuple[tuple[float, float], float], umriss: tuple[float, float, float, float],
                 hindernisse: list[tuple], groesse: tuple[float, float]) -> tuple[float, float]:
    """Beste Lage aus `hinweis_lagen`."""
    return hinweis_lagen(kreis, umriss, hindernisse, groesse)[0]
