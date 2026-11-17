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
    rolle: str                      # haupt | seite | drauf | seite_rechts | unter
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


def drehachse(f: dict, parameter: dict) -> str:
    """Lage der Drehachse in der Skizze eines Rotationsprofils: "v" (Mittellinie senkrecht) oder "u"."""
    achse = "v"
    for e in f.get("skizze", {}).get("elemente", []):
        if "mittellinie" in e:
            von, bis = e["mittellinie"]["von"], e["mittellinie"]["bis"]
            du = abs((_wert(bis[0], parameter) or 0) - (_wert(von[0], parameter) or 0))
            dv = abs((_wert(bis[1], parameter) or 0) - (_wert(von[1], parameter) or 0))
            achse = "v" if dv > du else "u"
    return achse


def profilpunkte(f: dict, parameter: dict, achse: str) -> list[tuple[float, float]]:
    """(Radius, Lage auf der Achse) je Polygonpunkt; Achse durch 0 (Mittellinie)."""
    ir, ia = (0, 1) if achse == "v" else (1, 0)
    punkte = []
    for e in f.get("skizze", {}).get("elemente", []):
        for p in e.get("polygon", {}).get("punkte", []):
            r, a = _wert(p[ir], parameter), _wert(p[ia], parameter)
            if r is not None and a is not None:
                punkte.append((abs(r), a))
    return punkte


def _radien(f: dict, parameter: dict, achse: str) -> list[float]:
    """Abstände der Profilpunkte zur Drehachse: Achse entlang v → |u|, entlang u → |v| (Review I2; Achse durch 0)."""
    i = 0 if achse == "v" else 1
    werte = []
    for e in f.get("skizze", {}).get("elemente", []):
        for p in e.get("polygon", {}).get("punkte", []):
            r = _wert(p[i], parameter)
            if r is not None:
                werte.append(abs(r))
    return werte


def _drehteil(spec: dict) -> list[Ansicht]:
    parameter = spec.get("parameter", {})
    rotationen = [f for f in spec["features"] if f.get("typ") == "rotation"]
    erste = rotationen[0] if rotationen else spec["features"][0]
    ebene = erste.get("skizze", {}).get("ebene")
    modellansicht = EBENE_ANSICHT.get(ebene, "*Vorderseite") if isinstance(ebene, str) else "*Vorderseite"
    achse = drehachse(erste, parameter)
    winkel = 90 if achse == "v" else 0  # Achse liegend darstellen (R-Kap. 3: Fertigungslage)
    r_erstes = _radien(erste, parameter, achse)
    hohl = bool(r_erstes) and min(r_erstes) > _NULL
    bohrt_achse = any(f.get("typ") == "rotation" and f.get("schnitt") and _radien(f, parameter, achse)
                      and min(_radien(f, parameter, achse)) <= _NULL for f in rotationen[1:])
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


def hauptrichtung(spec: dict) -> str:
    """Flächenrichtung mit den meisten Features (Frästeil-Hauptansicht schaut darauf); ohne Anker +y."""
    richtungen = [r for f in spec.get("features", [])[1:] if (r := _richtung(f))]
    zaehl = {r: richtungen.count(r) for r in richtungen}
    return max(zaehl, key=lambda r: (zaehl[r], r == "+y")) if zaehl else "+y"


def vorzugsansichten(spec: dict, plan: list) -> dict[str, str]:
    """Maße, die in die Hauptansicht gehören, solange dort Platz ist: Grundkörper und Merkmale auf der Fläche, auf die
    die Hauptansicht schaut (Live Z1.3 Stufe 2)."""
    if ist_drehteil(spec) and _hat_rotation(spec):
        return {}
    haupt = hauptrichtung(spec)
    features = spec.get("features", [])
    basis = features[0]["id"] if features else None
    richtung = {f["id"]: _richtung(f) for f in features}
    for f in features:  # Muster und Spiegeln erben die Richtung ihrer Quellen
        if f.get("typ") in ("muster_linear", "muster_kreis", "spiegeln") and richtung.get(f["id"]) is None:
            richtung[f["id"]] = next((richtung.get(q) for q in f.get("features", []) if richtung.get(q)), None)
    return {m.id: "haupt" for m in plan if m.merkmal == basis or richtung.get(m.merkmal) == haupt}


def _fraesteil(spec: dict) -> list[Ansicht]:
    haupt = hauptrichtung(spec)
    achse = haupt[1]
    nicht_haupt = [f for f in spec.get("features", [])[1:] if (r := _richtung(f)) and r != haupt]
    blind = any(f.get("typ") in (*_BOHRUNGEN, "schnitt") and "durch" not in f
                and f.get("ende", {}).get("typ") != "durch_alles" for f in nicht_haupt)  # Review I4b: auch Gegenseite
    # Grundsatz drei Ansichten (Nutzer 17.11.2026: meist 3–4); Ansichten ohne Maß entfallen in `zeichnen`
    return [Ansicht("haupt", MODELLANSICHT[haupt]), Ansicht("drauf", None, schnitt=blind), Ansicht("seite", None)]


def _hat_rotation(spec: dict) -> bool:
    return any(f.get("typ") == "rotation" for f in spec.get("features", []))


def hinweise(spec: dict) -> list[str]:
    """Wo die Ansichtswahl rät (Repo-Regel: nie still weglassen)."""
    aus = []
    if ist_drehteil(spec) and not _hat_rotation(spec):
        aus.append("ANSICHT_GERATEN: Drehteil ohne Rotation-Feature – Ansichten wie ein Frästeil gewählt (Review I3)")
    if not ist_drehteil(spec) and not any(_richtung(f) for f in spec.get("features", [])[1:]):
        aus.append("ANSICHT_GERATEN: keine Flächenanker – Hauptansicht von oben angenommen")
    return aus


# Modellrichtung der Skizzenachsen u/v je Standardebene (vorne: X/Y; oben: X/−Z wie Spannplatte-Kommentar;
# rechts: −Z/Y – ungeprüft, Ledger)
_SKIZZENACHSEN = {"vorne": {"u": (1, 0, 0), "v": (0, 1, 0)}, "oben": {"u": (1, 0, 0), "v": (0, 0, -1)},
                  "rechts": {"u": (0, 0, -1), "v": (0, 1, 0)}}


def achsvektor(spec: dict) -> tuple:
    """Richtung der Drehachse in Modellkoordinaten (Einheitsvektor); Frästeil: (0, 1, 0)."""
    rotationen = [f for f in spec.get("features", []) if f.get("typ") == "rotation"]
    if not rotationen:
        return (0, 1, 0)
    ebene = rotationen[0].get("skizze", {}).get("ebene")
    achse = drehachse(rotationen[0], spec.get("parameter", {}))
    return _SKIZZENACHSEN.get(ebene if isinstance(ebene, str) else "vorne", _SKIZZENACHSEN["vorne"])[achse]


def weitere_rollen(spec: dict) -> list[str]:
    """Zusätzliche Projektionen, wenn Maße keinen Platz finden (Design §6.1): von rechts (links der Hauptansicht),
    von unten (über ihr). Drehteile haben in Stufe 2 keine weiteren (Einzelheit folgt)."""
    return [] if ist_drehteil(spec) and _hat_rotation(spec) else ["seite_rechts", "unter"]


def waehle_ansichten(spec: dict) -> list[Ansicht]:
    """Hauptansicht und benötigte Projektionen. Drehteil: Achse liegend, Stirnansicht bei Bohrungen; bei Innenkontur
    Stirnansicht als Modellansicht und Längsschnitt A-A daraus als Hauptansicht (Vollschnitt). Frästeil: Hauptansicht von der Seite mit den meisten Features, Draufsicht für die Dicke, Seitenansicht
    bei Features quer dazu; Schnitt, wenn ein Feature quer blind endet."""
    return _drehteil(spec) if ist_drehteil(spec) and _hat_rotation(spec) else _fraesteil(spec)
