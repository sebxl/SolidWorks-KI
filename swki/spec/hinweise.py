"""Hinweise zu einer gültigen Spezifikation, die nicht verhindern, dass sie gebaut wird (Spec 2c §6.2).

art "feste_zahl": feste Zahlen in maßtragenden Feldern der Features deckt die Freigabe-Prüfsumme nicht ab (sie gehören
zum Bauweg). Anforderungsmaße sollen deshalb als Parameter geführt werden ("=Name"); validieren meldet die übrigen.
art "zusammenfassen": Knoten, die sich nach den Modellierregeln (Skill konstruieren) für einen kompakteren
Feature-Baum zusammenfassen lassen.
"""

import json

from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck
from swki.spec.normen import lade_tabelle

MASS_FELDER = frozenset({
    "tiefe", "durchmesser", "radius", "abstand", "winkel", "breite", "hoehe", "mitte", "punkte", "positionen", "von", "bis",
    "gewindetiefe", "laenge", "radien", "start", "linie", "bogen",
})
_ANKER = frozenset({"nahe", "kanten", "flaeche"})  # Anker wählen Geometrie aus, sie sind keine Maße
_TOL_NORM_MM = 0.01


_KEINE_MASSE = _ANKER | {"mittellinie"}  # Rotationsachse: Konstruktionslinie, kein Anforderungsmaß
_SAMMELN = frozenset({"punkte", "kontur"})  # viele Koordinaten einer Kontur → ein Hinweis statt einer je Zahl


def _feste_zahlen(wert) -> int:
    if isinstance(wert, dict):
        return sum(_feste_zahlen(v) for v in wert.values())
    if isinstance(wert, list):
        return sum(_feste_zahlen(v) for v in wert)
    return int(isinstance(wert, (int, float)) and not isinstance(wert, bool) and wert != 0)


def _standardwert(feature_typ: str, schluessel: str, wert) -> bool:
    """Werte, die keine Anforderung tragen: Vollkreis 360° (Muster, Rotation), Fase 45°."""
    return schluessel == "winkel" and (wert == 360 or (feature_typ == "fase" and wert == 45))


def feste_masse(spec: dict) -> list[dict]:
    """Feste Zahlen ≠ 0 in maßtragenden Feldern der Features als [{"art", "pfad", "meldung"}] (0 = Lage auf Achse/Ebene).
    Konturen (polygon.punkte, kontur) ergeben je Element einen Sammelhinweis; Mittellinien, 360° und Fase 45° nie."""
    hinweise = []

    def melde(pfad: str, meldung: str) -> None:
        hinweise.append({"art": "feste_zahl", "pfad": pfad, "meldung": meldung})

    def gehe(wert, pfad: str, mass: bool, typ: str) -> None:
        if isinstance(wert, dict):
            for k, v in wert.items():
                if k in _KEINE_MASSE or _standardwert(typ, k, v):
                    continue
                if k in _SAMMELN:
                    if n := _feste_zahlen(v):
                        melde(f"{pfad}.{k}", f"{n} feste Zahlen in {k}: als Parameter führen, wenn die Kontur eine "
                                             "Anforderung ist, sonst deckt die Freigabe sie nicht ab")
                    continue
                gehe(v, f"{pfad}.{k}", mass or k in MASS_FELDER, typ)
        elif isinstance(wert, list):
            for i, v in enumerate(wert):
                gehe(v, f"{pfad}[{i}]", mass, typ)
        elif mass and isinstance(wert, (int, float)) and not isinstance(wert, bool) and wert != 0:
            melde(pfad, f"feste Zahl {wert:g}: als Parameter führen, sonst deckt die Freigabe dieses Maß nicht ab")

    for i, feature in enumerate(spec.get("features", [])):
        gehe(feature, f"features[{i}]", False, feature.get("typ", ""))
    return hinweise


def _gruppen(features: list[dict], typen: tuple[str, ...], ohne: str) -> list[list[tuple[int, dict]]]:
    """Knoten gleichen Typs, die sich nur in id und dem Feld `ohne` unterscheiden (Reihenfolge des ersten Auftretens)."""
    gruppen: dict[str, list] = {}
    for i, f in enumerate(features):
        if f["typ"] in typen:
            schluessel = json.dumps({k: v for k, v in f.items() if k not in ("id", ohne)}, sort_keys=True, ensure_ascii=False)
            gruppen.setdefault(schluessel, []).append((i, f))
    return [g for g in gruppen.values() if len(g) > 1]


def _hinweis(eintraege: list[tuple[int, dict]], meldung: str) -> dict:
    return {"art": "zusammenfassen", "pfad": ", ".join(f"features[{i}]" for i, _ in eintraege),
            "knoten": [f["id"] for _, f in eintraege], "meldung": meldung}


def _iso_4762(f: dict, parameter: dict) -> str | None:
    """Größe, deren ISO-4762-Senkung (Durchgang und Senkungs-Ø laut Maßtabelle) die Bohrung mit Senkung trifft."""
    try:
        d, ds = auswerten(f["durchmesser"], parameter), auswerten(f["senkung"]["durchmesser"], parameter)
    except AusdruckFehler:
        return None
    for groesse, m in lade_tabelle()["normen"].get("ISO", {}).get("zylinderschraube", {}).items():
        if abs(d - m["durchgang"]) <= _TOL_NORM_MM and abs(ds - m["senkung_d"]) <= _TOL_NORM_MM:
            return groesse
    return None


_REGEL_3 = {
    "muster_linear": "muster_linear mit festen Abständen: Positionen direkt angeben, außer Anzahl und Abstand sind "
                     "Anforderungen – dann den Abstand als Parameter (Regel 3)",
    "muster_kreis": "muster_kreis mit festem Winkel: Positionen direkt angeben, außer die Teilung ist eine Anforderung – "
                    "dann den Winkel als Parameter; die Anzahl ist immer eine Zahl (Regel 3)",
    "spiegeln": "spiegeln nur von Bohrungen: Positionen direkt angeben, außer die Symmetrie ist eine Anforderung "
                "(Regel 3)",
}


def zusammenfassen(spec: dict) -> list[dict]:
    """Spec 2c §6.2: gleiche Bohrungen (Regel 2), gleiche Kantenmaße (Regel 6), Muster/Spiegeln mit festen Zahlen
    (Regel 3), Bohrung mit ISO-4762-Senkung (→ normbohrung, Regel 2)."""
    features = spec.get("features", [])
    parameter = spec.get("parameter", {})
    ergebnis = [_hinweis(g, "gleiche Bohrungen auf derselben Fläche: in einen Knoten mit mehreren positionen "
                            "zusammenfassen (Regel 2)")
                for g in _gruppen(features, ("bohrung", "normbohrung"), "positionen")]
    ergebnis += [_hinweis(g, "gleiches Maß: Kanten in einem Knoten zusammenfassen, am Ende des Baums (Regel 6)")
                 for g in _gruppen(features, ("fase", "verrundung"), "kanten")]
    typ_von = {f["id"]: f["typ"] for f in features}
    for i, f in enumerate(features):
        if f["typ"] == "muster_linear":
            fest = all(not ist_ausdruck(f[r]["abstand"]) for r in ("richtung1", "richtung2") if r in f)
        elif f["typ"] == "muster_kreis":
            fest = not ist_ausdruck(f.get("winkel", 360))
        elif f["typ"] == "spiegeln":
            fest = all(typ_von.get(q) in ("bohrung", "normbohrung") for q in f["features"])
        else:
            continue
        if fest:
            ergebnis.append(_hinweis([(i, f)], _REGEL_3[f["typ"]]))
    for i, f in enumerate(features):
        if f["typ"] == "bohrung" and "senkung" in f and (groesse := _iso_4762(f, parameter)):
            ergebnis.append(_hinweis([(i, f)], f"Bohrung mit Senkung entspricht ISO 4762 {groesse}: als normbohrung "
                                               f"(art: zylinderschraube, groesse: {groesse}) führen (Regel 2)"))
    return ergebnis


def hinweise(spec: dict) -> list[dict]:
    """Alle Hinweise für swki validieren: erst feste Zahlen, dann Zusammenfassbares. Hinweise blockieren nie."""
    return feste_masse(spec) + zusammenfassen(spec)
