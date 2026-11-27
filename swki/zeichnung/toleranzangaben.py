"""Zeichnungsableitung Z1.3 Stufe 4: Texte und Werte der Anforderungen (Toleranzen, Rauheit, Form/Lage, Behandlung,
Halbzeug, Sammelangaben), ohne SolidWorks."""

from dataclasses import dataclass

from swki.spec.ausdruck import AusdruckFehler, auswerten, namen
from swki.zeichnung.angaben import zahl

SAMMEL_RAUHEIT = "Ra 3,2"
_ALLGEMEINTOLERANZ = "Allgemeintoleranzen ISO 2768-1:1989 – m"
_TOLERIERUNG = "Tolerierung ISO 8015:2011"
_KANTEN = "Kanten ISO 13715 −0,1 … −0,3"
_MASSGEBEND = "Maßgebend ist die Zeichnung"

# Codes aus der Symboldatei `lang/german/gtol97.sym`, Abschnitt #GTOL (Task 5, 27.11.: „<IGTOL-PARALLEL>“ erschien
# im Rahmen nicht; die Datei kennt PARA, POSI, SYMMETRY, SRUN „Lauf“, TRUN „Gesamtlauf“)
GTOL_SYMBOL = {
    "ebenheit": "<IGTOL-FLAT>", "rechtwinkligkeit": "<IGTOL-PERP>", "parallelitaet": "<IGTOL-PARA>",
    "rundheit": "<IGTOL-CIRC>", "zylindrizitaet": "<IGTOL-CYL>", "position": "<IGTOL-POSI>",
    "koaxialitaet": "<IGTOL-CONC>", "symmetrie": "<IGTOL-SYMMETRY>", "rundlauf": "<IGTOL-SRUN>",
    "gesamtlauf": "<IGTOL-TRUN>", "neigung": "<IGTOL-ANGULAR>", "geradheit": "<IGTOL-STRAIGHT>",
    "linienprofil": "<IGTOL-LPROF>", "flaechenprofil": "<IGTOL-SPROF>",
}

_ART_WORT = {
    "haerten": "gehärtet", "haerten_anlassen": "gehärtet und angelassen", "vergueten": "vergütet",
    "einsatzhaerten": "einsatzgehärtet und angelassen", "randschichthaerten": "randschichtgehärtet",
    "nitrieren": "nitriert", "nitrocarburieren": "nitrocarburiert", "gluehen": "geglüht", "eloxieren": "eloxiert",
    "hartanodisieren": "hartanodisiert", "verzinken": "verzinkt", "bruenieren": "brüniert", "beschichten": "beschichtet",
}


@dataclass(frozen=True)
class Toleranz:
    passung: str | None
    oben: float | None
    unten: float | None
    huelle: bool


@dataclass(frozen=True)
class FormLage:
    merkmal: str
    art: str
    symbol: str
    wert: str
    bezug: tuple[str, ...]
    mmr: bool


def toleranz_aus(passung: str | None, toleranz: dict | None, huelle: bool,
                 parameter: dict | None = None) -> Toleranz | None:
    """Toleranz eines Features; None, wenn weder Passung noch Abmaße vorliegen."""
    if passung is None and not toleranz:
        return None
    if passung is not None:
        return Toleranz(passung, None, None, bool(huelle))
    return Toleranz(None, auswerten(toleranz["oben"], parameter or {}), auswerten(toleranz["unten"], parameter or {}),
                     bool(huelle))


def parameter_toleranzen(spec: dict) -> dict[str, Toleranz]:
    """Toleranz je Parameter aus `toleranzen` der Spec (Reihenfolge wie in der Spec). Eine Passung ist ein Passmaß und
    trägt Ⓔ (Nutzer 16.11.2026), reine Abmaße nicht."""
    parameter = spec.get("parameter", {})
    aus = {}
    for name, t in (spec.get("toleranzen") or {}).items():
        passung = t.get("passung")
        toleranz = toleranz_aus(passung, None if passung else t, passung is not None, parameter)
        if toleranz is not None:
            aus[name] = toleranz
    return aus


def treibende_parameter(roh, toleranzen: dict[str, Toleranz]) -> list[str]:
    """Alle Parameter aus `toleranzen`, deren Name im Ausdruck `roh` ("=A/2") vorkommt (ganze Namen), in der
    Reihenfolge von `toleranzen`."""
    if not isinstance(roh, str) or not roh.startswith("="):
        return []
    try:
        vorhanden = namen(roh)
    except AusdruckFehler:
        return []
    return [p for p in toleranzen if p in vorhanden]


def treibender_parameter(roh, toleranzen: dict[str, Toleranz]) -> str | None:
    """Erster Parameter aus `treibende_parameter`; sonst None."""
    return next(iter(treibende_parameter(roh, toleranzen)), None)


def _vorzeichen(x: float) -> str:
    if x == 0:
        return "0"
    return ("+" if x > 0 else "−") + zahl(abs(x))


def toleranztext(t: Toleranz) -> str:
    """„H7“ bzw. „±0,02“ bzw. „+0,1/−0,05“, mit „ Ⓔ“ bei Hülle."""
    if t.passung is not None:
        text = t.passung
    elif abs(t.oben + t.unten) < 1e-9:
        text = "±" + zahl(t.oben)
    else:
        text = f"{_vorzeichen(t.oben)}/{_vorzeichen(t.unten)}"
    return text + " Ⓔ" if t.huelle else text


def rauheitstext(rauheit: dict) -> str:
    kenngroesse, wert = next(iter(rauheit.items()))
    return f"{kenngroesse} {zahl(wert)}"


def form_lage_angaben(merkmal: str, eintraege: list[dict]) -> tuple[list[FormLage], list[str]]:
    """Form-/Lagetoleranzen eines Merkmals; Einträge mit IT-Grad statt Wert ergeben eine Meldung (keine Tabelle)."""
    angaben, meldungen = [], []
    for e in eintraege:
        if "wert" not in e:
            meldungen.append(f"FORM_LAGE_IT_OHNE_TABELLE: {merkmal} {e['art']} IT{e.get('it')} – keine ISO-286-Tabelle")
            continue
        angaben.append(FormLage(merkmal, e["art"], GTOL_SYMBOL[e["art"]], zahl(e["wert"]),
                                tuple(e.get("bezug", ())), bool(e.get("mmr", False))))
    return angaben, meldungen


def _abmass(w: float, plus: float | None, minus: float | None) -> str:
    """„w +p/−m“ (Nullseite als „0“); „w“ ohne Abmaße."""
    if plus is None and minus is None:
        return zahl(w)
    p, m = plus or 0, minus or 0
    return f"{zahl(w)} {_vorzeichen(p)}/{'0' if m == 0 else '−' + zahl(m)}"


def _haerte(h: dict) -> str:
    v = h["verfahren"]
    plus, minus = h.get("plus"), h.get("minus")
    if plus is None and minus is None:
        return f"≥ {zahl(h['wert'])} {v}"
    if (plus or 0) == (minus or 0):
        return f"({zahl(h['wert'])} ± {zahl(plus or 0)}) {v}"
    return f"({_abmass(h['wert'], plus, minus)}) {v}"


def behandlungstext(b: dict) -> str:
    """Behandlungsangabe nach DIN ISO 15787 (docs/zeichnungsableitung/haerteangabe.md)."""
    text = _ART_WORT[b["art"]]
    if "haerte" in b:
        text += " " + _haerte(b["haerte"])
    if "kernhaerte" in b:
        text += ", Kern " + _haerte(b["kernhaerte"])
    if "tiefe" in b:
        t = b["tiefe"]
        mass = zahl(t["wert"]) if "plus" not in t and "minus" not in t else f"({_abmass(t['wert'], t.get('plus'), t.get('minus'))})"
        text += f", {t['art']} = {mass} mm"
        if "grenzhaerte" in t:
            text += f" ({t['grenzhaerte']})"
    if b.get("zustand") == "vor_schleifen":
        text += " (vor dem Schleifen)"
    if "schicht" in b:
        text += f", {b['schicht']['norm']} {b['schicht']['bezeichnung']}"
    return text


def halbzeugtext(h: dict) -> str:
    text = f"Halbzeug: {h['art'].capitalize()} {h['norm']} – {h['masse'].replace(' x ', ' × ')}"
    for feld in ("toleranz", "zustand"):
        if feld in h:
            text += f", {h[feld]}"
    return text


def sammelangaben(spec: dict) -> list[str]:
    """Zeilen der Sammelangabe in fester Reihenfolge: Allgemeintoleranz, Tolerierung, Kanten, Maßgebend, Behandlungen,
    Halbzeug."""
    zeilen = [_ALLGEMEINTOLERANZ, _TOLERIERUNG, _KANTEN, _MASSGEBEND]
    zeilen += [behandlungstext(b) for b in spec.get("behandlung", [])]
    if "halbzeug" in spec:
        zeilen.append(halbzeugtext(spec["halbzeug"]))
    return zeilen
