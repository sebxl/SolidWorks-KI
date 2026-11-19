"""Ansichtswahl aus der Spec (Z1.3 Stufe 1; Design §6.1, Recherche Kap. 3).

Die Hauptansicht ist eine Modellansicht; Seiten- und Draufsicht werden in SolidWorks aus ihr projiziert
(Projektionsmethode 1 des Blatts): `seite` rechts daneben, `drauf` darunter. Achsen wie beim Prüfer: vorne → +Z,
oben → +Y, rechts → +X. Modellansichten heißen in der deutschen Oberfläche „*Vorderseite“, „*Oben“ … (Spike Z1.0).
"""

from dataclasses import dataclass

from swki.spec.ausdruck import AusdruckFehler, auswerten
from swki.spec.konturen import kontur_punkte

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
    durch: tuple[str, ...] = ()     # Frästeil-Schnitt: Merkmale, durch deren Mitte die Schnittlinie läuft


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


def elementpunkte(e: dict, parameter: dict) -> list[tuple[float, float]] | None:
    """Eckpunkte (u, v) eines Profilelements: polygon, rechteck, kontur (Review Stufe 2 C1); None = nicht unterstützt
    (Mittellinie liefert []). Ausdrucksfehler → None."""
    try:
        if "polygon" in e:
            return [(auswerten(p[0], parameter), auswerten(p[1], parameter)) for p in e["polygon"]["punkte"]]
        if "rechteck" in e:
            r = e["rechteck"]
            mu, mv = (auswerten(x, parameter) for x in r["mitte"])
            b, h = auswerten(r["breite"], parameter) / 2, auswerten(r["hoehe"], parameter) / 2
            return [(mu - b, mv - h), (mu + b, mv - h), (mu + b, mv + h), (mu - b, mv + h)]
        if "kontur" in e:
            return kontur_punkte(e["kontur"], parameter)
    except AusdruckFehler:
        return None
    return [] if "mittellinie" in e else None


def profilpunkte(f: dict, parameter: dict, achse: str) -> list[tuple[float, float]]:
    """(Radius, Lage auf der Achse) je Eckpunkt des Profils; Achse durch 0 (Mittellinie)."""
    ir, ia = (0, 1) if achse == "v" else (1, 0)
    punkte = []
    for e in f.get("skizze", {}).get("elemente", []):
        for p in elementpunkte(e, parameter) or []:
            punkte.append((abs(p[ir]), p[ia]))
    return punkte


def _radien(f: dict, parameter: dict, achse: str) -> list[float]:
    """Abstände der Profilpunkte zur Drehachse: Achse entlang v → |u|, entlang u → |v| (Review I2; Achse durch 0)."""
    return [r for r, _ in profilpunkte(f, parameter, achse)]


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
    for f in features:  # Muster/Spiegeln erben von ihren Quellen, Verrundung/Fase vom Kanten-Feature (Review I4)
        if richtung.get(f["id"]) is not None:
            continue
        quellen = f.get("features", []) if f.get("typ") in ("muster_linear", "muster_kreis", "spiegeln") else \
            [k.get("feature") for k in f.get("kanten", []) if isinstance(k, dict)]
        richtung[f["id"]] = next((richtung.get(q) for q in quellen if richtung.get(q)), None)
    return {m.id: "haupt" for m in plan if m.merkmal == basis or richtung.get(m.merkmal) == haupt}


def _fraesteil(spec: dict) -> list[Ansicht]:
    haupt = hauptrichtung(spec)
    achse = haupt[1]
    nicht_haupt = [f for f in spec.get("features", [])[1:] if (r := _richtung(f)) and r != haupt]
    blind = any(f.get("typ") in (*_BOHRUNGEN, "schnitt") and "durch" not in f
                and f.get("ende", {}).get("typ") != "durch_alles" for f in nicht_haupt)  # Review I4b: auch Gegenseite
    # Nutzer 19.11.2026: Tiefe einer Tasche in der Hauptfläche ist in keiner Projektion sichtbar → untere Ansicht als
    # Schnitt durch die Taschen (blinde Bohrungen nicht: ihre Tiefe steht in der Bohrungsangabe)
    taschen = tuple(f["id"] for f in spec.get("features", [])[1:]
                    if f.get("typ") == "schnitt" and _richtung(f) == haupt and _blind(f))
    # Grundsatz drei Ansichten (Nutzer 17.11.2026: meist 3–4); Ansichten ohne Maß entfallen in `zeichnen`
    return [Ansicht("haupt", MODELLANSICHT[haupt]), Ansicht("drauf", None, schnitt=blind or bool(taschen), durch=taschen),
            Ansicht("seite", None)]


def _blind(f: dict) -> bool:
    ende = f.get("ende") or {}
    return ende.get("typ") == "blind" or ("tiefe" in ende and ende.get("typ") not in ("durch", "durch_alles"))


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


# Blickachse, Rechts- und Hochachse des Bildes je Modellansicht (0 = x, 1 = y, 2 = z; Vorzeichen spielen keine Rolle)
_BILDACHSEN = {"*Oben": (1, 0, 2), "*Unten": (1, 0, 2), "*Vorderseite": (2, 0, 1), "*Rückseite": (2, 0, 1),
               "*Rechts": (0, 2, 1), "*Links": (0, 2, 1)}


def blickachsen(ansichten: list[Ansicht], weitere: list[str]) -> dict[str, int]:
    """Blickachse je Rolle (Nutzer 18.11.2026: Maße nur in Ansichten, in denen ihr Merkmal in wahrer Größe liegt).
    Projektionen nach Methode 1: Seitenansichten blicken entlang der Rechtsachse der Hauptansicht, Drauf-/Unteransicht
    entlang ihrer Hochachse; ein um 90° gedrehtes Bild tauscht beide. Der Längsschnitt aus der Stirnansicht blickt
    entlang deren Rechtsachse (Schnittlinie senkrecht)."""
    basis = next(a for a in ansichten if a.modellansicht)
    n, r, u = _BILDACHSEN.get(basis.modellansicht, (2, 0, 1))
    if round(basis.winkel_grad) % 180 == 90:
        r, u = u, r
    aus = {basis.rolle: n}
    if basis.rolle != "haupt":
        aus["haupt"] = r
        n, r = r, n
    for rolle in [a.rolle for a in ansichten] + list(weitere):
        if rolle in ("seite", "seite_rechts"):
            aus.setdefault(rolle, r)
        elif rolle in ("drauf", "unter"):
            aus.setdefault(rolle, u)
    return aus


def weitere_rollen(spec: dict) -> list[str]:
    """Zusätzliche Projektionen, wenn Maße keinen Platz finden (Design §6.1): von rechts (links der Hauptansicht),
    von unten (über ihr). Drehteile haben in Stufe 2 keine weiteren (Einzelheit folgt)."""
    return [] if ist_drehteil(spec) and _hat_rotation(spec) else ["seite_rechts", "unter"]


def waehle_ansichten(spec: dict) -> list[Ansicht]:
    """Hauptansicht und benötigte Projektionen. Drehteil: Achse liegend, Stirnansicht bei Bohrungen; bei Innenkontur
    Stirnansicht als Modellansicht und Längsschnitt A-A daraus als Hauptansicht (Vollschnitt). Frästeil: Hauptansicht von der Seite mit den meisten Features, Draufsicht für die Dicke, Seitenansicht
    bei Features quer dazu; Schnitt, wenn ein Feature quer blind endet."""
    return _drehteil(spec) if ist_drehteil(spec) and _hat_rotation(spec) else _fraesteil(spec)
