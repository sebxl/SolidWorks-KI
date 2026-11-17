"""Ansichtswahl aus der Spec (Z1.3 Stufe 1; Design §6.1, Recherche Kap. 3).

Die Hauptansicht ist eine Modellansicht; Seiten- und Draufsicht werden in SolidWorks aus ihr projiziert
(Projektionsmethode 1 des Blatts): `seite` rechts daneben, `drauf` darunter. Achsen wie beim Prüfer: vorne → +Z,
oben → +Y, rechts → +X. Modellansichten heißen in der deutschen Oberfläche „*Vorderseite“, „*Oben“ … (Spike Z1.0).
"""

from dataclasses import dataclass

from swki.spec.ausdruck import AusdruckFehler, auswerten

MODELLANSICHT = {"+y": "*Oben", "-y": "*Unten", "+z": "*Vorderseite", "-z": "*Rückseite", "+x": "*Rechts",
                 "-x": "*Links"}
EBENE_ANSICHT = {"vorne": "*Vorderseite", "oben": "*Oben", "rechts": "*Rechts"}
# Blick entlang der Drehachse je Skizzenebene und Achsrichtung in der Skizze (u/v): vorne X/Y, oben X/Z, rechts Z/Y
ACHSANSICHT = {("vorne", "v"): "*Oben", ("vorne", "u"): "*Rechts", ("oben", "u"): "*Rechts",
               ("oben", "v"): "*Vorderseite", ("rechts", "v"): "*Oben", ("rechts", "u"): "*Vorderseite"}
_BOHRUNGEN = ("bohrung", "normbohrung")
_NULL = 1e-6


@dataclass(frozen=True)
class Ansicht:
    rolle: str                      # haupt | seite | drauf
    modellansicht: str | None       # nur die Hauptansicht; Seite/Drauf werden projiziert
    schnitt: bool = False
    winkel_grad: float = 0


def ist_drehteil(spec: dict) -> bool:
    if "verfahren" in spec:
        return spec["verfahren"] == "drehen"
    features = spec.get("features", [])
    return bool(features) and features[0].get("typ") == "rotation"


def _wert(x, parameter: dict) -> float | None:
    try:
        return auswerten(x, parameter)
    except AusdruckFehler:
        return None


def _profil_u(f: dict, parameter: dict) -> list[float]:
    werte = []
    for e in f.get("skizze", {}).get("elemente", []):
        for p in e.get("polygon", {}).get("punkte", []):
            u = _wert(p[0], parameter)
            if u is not None:
                werte.append(abs(u))
    return werte


def _drehteil(spec: dict) -> list[Ansicht]:
    parameter = spec.get("parameter", {})
    rotationen = [f for f in spec["features"] if f.get("typ") == "rotation"]
    erste = rotationen[0] if rotationen else spec["features"][0]
    ebene = erste.get("skizze", {}).get("ebene")
    modellansicht = EBENE_ANSICHT.get(ebene, "*Vorderseite") if isinstance(ebene, str) else "*Vorderseite"
    achse = "v"
    for e in erste.get("skizze", {}).get("elemente", []):
        if "mittellinie" in e:
            von, bis = e["mittellinie"]["von"], e["mittellinie"]["bis"]
            du = abs((_wert(bis[0], parameter) or 0) - (_wert(von[0], parameter) or 0))
            dv = abs((_wert(bis[1], parameter) or 0) - (_wert(von[1], parameter) or 0))
            achse = "v" if dv > du else "u"
    winkel = 90 if achse == "v" else 0  # Achse liegend darstellen (R-Kap. 3: Fertigungslage)
    u_erstes = _profil_u(erste, parameter)
    hohl = bool(u_erstes) and min(u_erstes) > _NULL
    bohrt_achse = any(f.get("typ") == "rotation" and f.get("schnitt") and _profil_u(f, parameter)
                      and min(_profil_u(f, parameter)) <= _NULL for f in rotationen[1:])
    if hohl or bohrt_achse:
        # Längsschnitt A-A aus der Stirnansicht: Skizzen in gedrehten Ansichten landen nicht in Blattkoordinaten
        # (Live Z1.3 Stufe 1), die ungedrehte Stirnansicht trägt die Schnittlinie wie im Spike Z1.0.
        stirn = ACHSANSICHT.get((ebene, achse), "*Oben") if isinstance(ebene, str) else "*Oben"
        return [Ansicht("seite", stirn), Ansicht("haupt", None, schnitt=True)]
    ansichten = [Ansicht("haupt", modellansicht, winkel_grad=winkel)]
    if any(f.get("typ") in _BOHRUNGEN for f in spec["features"]):
        ansichten.append(Ansicht("seite", None))
    return ansichten


def _richtung(f: dict) -> str | None:
    for anker in (f.get("flaeche"), f.get("skizze", {}).get("ebene")):
        if isinstance(anker, dict) and isinstance(anker.get("flaeche"), str):
            return anker["flaeche"]
    return None


def _fraesteil(spec: dict) -> list[Ansicht]:
    richtungen = [r for f in spec["features"][1:] if (r := _richtung(f))]
    zaehl = {r: richtungen.count(r) for r in richtungen}
    haupt = max(zaehl, key=lambda r: (zaehl[r], r == "+y")) if zaehl else "+y"
    achse = haupt[1]
    quer = [f for f in spec["features"][1:] if (r := _richtung(f)) and r[1] != achse]
    blind_quer = any(f.get("typ") in (*_BOHRUNGEN, "schnitt") and "durch" not in f
                     and f.get("ende", {}).get("typ") != "durch_alles" for f in quer)
    ansichten = [Ansicht("haupt", MODELLANSICHT[haupt]), Ansicht("drauf", None, schnitt=blind_quer)]
    if quer:
        ansichten.append(Ansicht("seite", None))
    return ansichten


def waehle_ansichten(spec: dict) -> list[Ansicht]:
    """Hauptansicht und benötigte Projektionen. Drehteil: Achse liegend, Stirnansicht bei Bohrungen; bei Innenkontur
    Stirnansicht als Modellansicht und Längsschnitt A-A daraus als Hauptansicht (Vollschnitt). Frästeil: Hauptansicht von der Seite mit den meisten Features, Draufsicht für die Dicke, Seitenansicht
    bei Features quer dazu; Schnitt, wenn ein Feature quer blind endet."""
    return _drehteil(spec) if ist_drehteil(spec) else _fraesteil(spec)
