"""Bewegungsprüfung ohne SolidWorks (Spec 4a §8.2): Bewegungen aus der Spezifikation, Lagevergleich aus
Transformationen, überstrichene Räume, Paare, Endlagen und die Bewertung zu Prüfungen und Mängeln.

Transformationen wie IComponent2.Transform2.ArrayData: [0:9] Drehung in Zeilenvektor-Konvention (Zeile i = Bild der
Teilachse i, wie swki.baugruppe.geometrie.transformiere), [9:12] Verschiebung in m. Drehungen rechnet dieses Modul in
Spaltenform (C · p = Bild von p). Hüllquader [xmin, ymin, zmin, xmax, ymax, zmax] in mm."""

import math
from dataclasses import dataclass, field

from swki.baugruppe.bewertung import STATUS_TEXT, UNTERBESTIMMT, VOLL_BESTIMMT
from swki.baugruppe.geometrie import drehmatrix
from swki.pruefung.bewertung import _beschreibung, _pruefung
from swki.spec.ausdruck import auswerten
from swki.verbindung import in_mm

TOL_BEWEGT_MM = 1e-3      # Präzisierung 7
TOL_BEWEGT_DREHUNG = 1e-6
TOL_WINKEL_GRAD = 0.01    # Präzisierung 6
TOL_RAUM_MM = 1e-3        # Präzisierung 7


@dataclass(frozen=True)
class Bewegung:
    name: str
    grenze: str          # ID der Grenzverknüpfung
    art: str             # "abstand" | "winkel"
    komponente: str      # bewegte Komponente (Seite a der Grenze)
    min: float           # mm bzw. Grad
    max: float
    schritte: int

    @property
    def schrittweite(self) -> float:
        return (self.max - self.min) / self.schritte

    def stellungen(self) -> list[float]:
        return [self.min + i * self.schrittweite for i in range(self.schritte)] + [self.max]


def bewegungen(spec: dict, standard: dict) -> list[Bewegung]:
    """Bewegungen der Spezifikation mit ausgewerteten Grenzen (setzt eine plausible Spezifikation voraus)."""
    p = spec.get("parameter", {})
    grenzen = {v["id"]: v for v in spec.get("verknuepfungen", [])}
    ergebnis = []
    for b in spec.get("bewegungen", []):
        v = grenzen[b["grenze"]]
        ergebnis.append(Bewegung(b["name"], b["grenze"], "abstand" if v["typ"] == "grenze_abstand" else "winkel",
                                 v["a"]["komponente"], auswerten(v["min"], p), auswerten(v["max"], p),
                                 b.get("schritte", standard["bewegung_schritte"])))
    return ergebnis


def _drehung(t) -> list[list[float]]:
    """Spaltenform C aus der Zeilenvektor-Konvention: C[i][j] = t[3j + i]."""
    return [[t[3 * j + i] for j in range(3)] for i in range(3)]


def _mal(a, b) -> list[list[float]]:
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _transponiert(a) -> list[list[float]]:
    return [[a[j][i] for j in range(3)] for i in range(3)]


def verschiebung_mm(t0, t1) -> tuple[float, float, float]:
    """Verschiebung des Komponentenursprungs von t0 nach t1 in Baugruppenkoordinaten (mm)."""
    return tuple(in_mm(t1[9 + i] - t0[9 + i]) for i in range(3))


def relative_drehung(t0, t1) -> list[list[float]]:
    """Drehung der Komponente von Lage t0 nach t1 in Baugruppenkoordinaten (Spaltenform): C1 · C0ᵀ."""
    return _mal(_drehung(t1), _transponiert(_drehung(t0)))


def winkel_grad(q) -> float:
    """Drehwinkel einer Drehmatrix in Grad (0 … 180)."""
    return math.degrees(math.acos(max(-1.0, min(1.0, (q[0][0] + q[1][1] + q[2][2] - 1) / 2))))


def achse_winkel(q) -> tuple[tuple[float, float, float] | None, float]:
    """Drehachse (Einheitsvektor, Rechte-Hand-Regel) und Winkel in Grad; bei 0° und 180° ohne Achse."""
    w = winkel_grad(q)
    v = (q[2][1] - q[1][2], q[0][2] - q[2][0], q[1][0] - q[0][1])
    n = math.sqrt(sum(c * c for c in v))
    if n < 1e-12:
        return None, w
    return tuple(c / n for c in v), w


def ist_bewegt(t0, t1) -> bool:
    return (any(abs(c) > TOL_BEWEGT_MM for c in verschiebung_mm(t0, t1))
            or any(abs(t1[i] - t0[i]) > TOL_BEWEGT_DREHUNG for i in range(9)))


def weg(b: Bewegung, t0, t1) -> float:
    """Zurückgelegter Weg der bewegten Komponente: Betrag der Verschiebung (mm) bzw. Drehwinkel (Grad)."""
    if b.art == "abstand":
        return math.sqrt(sum(c * c for c in verschiebung_mm(t0, t1)))
    return winkel_grad(relative_drehung(t0, t1))


def soll_weg(b: Bewegung, wert: float) -> float:
    """Soll zu weg(): |wert − min|; beim Winkel auf [0, 180] gefaltet wie der Drehwinkel aus der Matrix."""
    d = abs(wert - b.min)
    if b.art == "winkel":
        d %= 360
        d = min(d, 360 - d)
    return d


def vereinige(a: list[float] | None, b: list[float]) -> list[float]:
    if a is None:
        return list(b)
    return [min(a[i], b[i]) for i in range(3)] + [max(a[i], b[i]) for i in range(3, 6)]


def schnitt(a: list[float], b: list[float]) -> list[float] | None:
    """Schnitt zweier Hüllquader oder None, wenn sie sich in einer Achse nur berühren oder gar nicht überdecken."""
    unten = [max(a[i], b[i]) for i in range(3)]
    oben = [min(a[i + 3], b[i + 3]) for i in range(3)]
    return unten + oben if all(oben[i] - unten[i] > TOL_RAUM_MM for i in range(3)) else None


@dataclass
class Lauf:
    """Ein Durchlauf einer Bewegung von min bis max (Grundstellungslauf: gegen = {}; Paarlauf: {andere: "max"})."""
    bewegung: str
    gegen: dict[str, str] = field(default_factory=dict)
    stellungen: list[float] = field(default_factory=list)            # angefahrene Stellungen
    lagen: list[dict[str, list[float]]] = field(default_factory=list)  # Grundstellungslauf: je Stellung Instanz → Transform
    bewegt: list[str] = field(default_factory=list)
    raum: list[float] | None = None
    kollisionen: list[dict] = field(default_factory=list)  # {"paar", "volumen", "stellung", "gegen", "bild"}
    fehler: dict | None = None                              # {"stellung", "meldung"}: Lauf vorzeitig beendet
    grenze: dict = field(default_factory=dict)              # {"oben": bool, "unten": bool | None}; True = ging durch
    bilder: dict[str, str] = field(default_factory=dict)    # "min" | "mitte" | "max" → Pfad
    dauer_s: float = 0.0


@dataclass
class BewegungsMesswerte:
    status_frei: dict[str, int]      # Instanz-ID → GetConstrainedStatus, Grenzen der Bewegungen unterdrückt, ohne Antrieb
    status_gehalten: dict[str, int]  # Instanz-ID → GetConstrainedStatus, Grenzen unterdrückt, alle Bewegungen auf min festgehalten
    laeufe: list[Lauf]
    paare: list[dict]                # {"bewegungen": [b1, b2], "schnitt": [...]}


def paare(bws: list[Bewegung], grund: dict[str, Lauf]) -> list[tuple[Bewegung, Bewegung, list[float]]]:
    """Paare von Bewegungen, deren überstrichene Räume sich schneiden (Spec 4a §8.2.6), in Spec-Reihenfolge."""
    ergebnis = []
    for i, b1 in enumerate(bws):
        for b2 in bws[i + 1:]:
            r1, r2 = grund[b1.name].raum, grund[b2.name].raum
            if r1 is not None and r2 is not None and (s := schnitt(r1, r2)) is not None:
                ergebnis.append((b1, b2, s))
    return ergebnis


def _freiheitsgrad(b: Bewegung, frei: dict[str, int], gehalten: dict[str, int]) -> dict:
    """Freiheitsgrad belegt: mit unterdrückten Grenzen ohne Antrieb unterbestimmt, mit Antrieb auf min voll bestimmt
    (die aktive Grenze zählt für GetConstrainedStatus schon als Bindung, Spike S13/S13b)."""
    vorher = frei.get(b.komponente)
    nachher = gehalten.get(b.komponente)
    gruende = []
    if vorher != UNTERBESTIMMT:
        gruende.append(f"ohne Antrieb (Grenze unterdrückt) {STATUS_TEXT.get(vorher, vorher)} statt unterbestimmt "
                       "(nicht beweglich)")
    if nachher != VOLL_BESTIMMT:
        gruende.append(f"mit Antrieb {STATUS_TEXT.get(nachher, nachher)} statt voll bestimmt"
                       + (" (mehr als ein Freiheitsgrad offen)" if nachher == UNTERBESTIMMT else ""))
    return _pruefung(f"freiheitsgrad:{b.komponente}", not gruende,
                     ist={"ohne_antrieb": vorher, "mit_antrieb": nachher}, knoten=[b.komponente],
                     **({"hinweis": "; ".join(gruende)} if gruende else {}))


def _grenze(b: Bewegung, grund: Lauf | None) -> dict:
    pid = f"grenze:{b.name}"
    if grund is None or grund.fehler is not None:
        return _pruefung(pid, None, hinweis="Lauf abgebrochen – Grenze nicht geprüft", knoten=[b.komponente])
    durch = [s for s in ("oben", "unten") if grund.grenze.get(s)]
    if durch:
        return _pruefung(pid, False, ist=grund.grenze, knoten=[b.komponente],
                         hinweis=f"Schritt {' und '.join(durch)} über die Grenze ging durch – die Grenze im Modell wirkt "
                                 "nicht wie freigegeben")
    return _pruefung(pid, True, ist=grund.grenze, knoten=[])


def _endlage(b: Bewegung, e: dict, grund: Lauf | None, p: dict, tol_mm: float) -> dict:
    kid = e["komponente"]
    pid = f"endlage:{b.name}:{kid}"
    if grund is None or grund.fehler is not None or not grund.lagen:
        return _pruefung(pid, False, hinweis="Lauf abgebrochen – Endlage nicht messbar", knoten=[kid])
    erste, letzte = grund.lagen[0].get(kid), grund.lagen[-1].get(kid)
    if erste is None or letzte is None:
        return _pruefung(pid, False, hinweis=f"Komponente {kid} fehlt in der Baugruppe", knoten=[kid])
    if "verschiebung" in e:
        soll = [auswerten(w, p) for w in e["verschiebung"]]
        ist = [round(c, 4) for c in verschiebung_mm(erste, letzte)]
        return _pruefung(pid, all(abs(i - s) <= tol_mm for i, s in zip(ist, soll)), ist=ist, soll=soll, tol=tol_mm,
                         knoten=[kid])
    achse = [auswerten(w, p) for w in e["drehung"]["achse"]]
    winkel = auswerten(e["drehung"]["winkel"], p)
    q = relative_drehung(erste, letzte)
    abweichung = winkel_grad(_mal(q, _transponiert(drehmatrix(achse, winkel))))
    ist_achse, ist_winkel = achse_winkel(q)
    return _pruefung(pid, abweichung <= TOL_WINKEL_GRAD,
                     ist={"achse": [round(c, 6) for c in ist_achse] if ist_achse else None, "winkel": round(ist_winkel, 4)},
                     soll={"achse": achse, "winkel": winkel}, abweichung_grad=round(abweichung, 4), knoten=[kid])


def _lauf_bericht(lauf: Lauf) -> dict:
    return {"bewegung": lauf.bewegung, "gegen": lauf.gegen, "stellungen": len(lauf.stellungen), "bewegt": lauf.bewegt,
            "raum": [round(v, 3) for v in lauf.raum] if lauf.raum else None, "kollisionen": len(lauf.kollisionen),
            "grenze": lauf.grenze, "fehler": lauf.fehler, "dauer_s": lauf.dauer_s}


def bewerte_bewegungen(spec: dict, bws: list[Bewegung], m: BewegungsMesswerte, tol_mm: float) -> tuple[list[dict], dict]:
    """Prüfungen je Bewegung (Spec 4a §8.2): freiheitsgrad, bewegung, bewegung_kollision, grenze, endlage; dazu der
    Bewegungsteil des Prüfberichts (Spec 4a §8.5). Der Freiheitsgrad kommt aus den Messwerten (status_frei,
    status_gehalten), nicht aus der statischen Prüfung."""
    p = spec.get("parameter", {})
    erwartet = {b["name"]: b.get("erwartet", {}) for b in spec.get("bewegungen", [])}
    pruefungen = []
    for b in bws:
        laeufe = [lauf for lauf in m.laeufe if lauf.bewegung == b.name]
        grund = next((lauf for lauf in laeufe if not lauf.gegen), None)
        pruefungen.append(_freiheitsgrad(b, m.status_frei, m.status_gehalten))
        fehler = [{"gegen": lauf.gegen, **lauf.fehler} for lauf in laeufe if lauf.fehler]
        pruefungen.append(_pruefung(f"bewegung:{b.name}", not fehler, ist=fehler, knoten=[b.komponente] if fehler else []))
        kollisionen = [k for lauf in laeufe for k in lauf.kollisionen]
        pruefungen.append(_pruefung(f"bewegung_kollision:{b.name}", not kollisionen, ist=kollisionen,
                                    knoten=sorted({x for k in kollisionen for x in k["paar"]})))
        pruefungen.append(_grenze(b, grund))
        pruefungen += [_endlage(b, e, grund, p, tol_mm) for e in erwartet.get(b.name, {}).get("endlagen", [])]
    return pruefungen, {"laeufe": [_lauf_bericht(lauf) for lauf in m.laeufe], "paare": m.paare}


def ersatz_pruefungen(bws: list[Bewegung], hinweis: str, fehlerhaft: dict[str, str] | None = None) -> tuple[list[dict], dict]:
    """Ersatz für bewerte_bewegungen, wenn die Bewegungsprüfung nicht (vollständig) lief (Spec 4a §8.2.3): je Bewegung
    die Prüfung bewegung:<name>. Bewegungen in fehlerhaft (Name → Meldung) sind ein Mangel (ok=False, Knoten = bewegte
    Komponente); alle übrigen sind nicht geprüft (ok=None, hinweis). Der Bewegungsbericht ist leer."""
    fehlerhaft = fehlerhaft or {}
    pruefungen = [_pruefung(f"bewegung:{b.name}", False, ist=[{"gegen": {}, "meldung": fehlerhaft[b.name]}],
                            hinweis=fehlerhaft[b.name], knoten=[b.komponente]) if b.name in fehlerhaft
                  else _pruefung(f"bewegung:{b.name}", None, hinweis=hinweis, knoten=[])
                  for b in bws]
    return pruefungen, {"laeufe": [], "paare": []}


def ergaenze_bericht(bericht: dict, pruefungen: list[dict], bewegungsbericht: dict, bilder: dict[str, str]) -> dict:
    """Prüfbericht der Statik um die Bewegungsprüfung ergänzen (neues Dict; Mängel, bestanden, Bilder)."""
    neu = [{"pruefung": e["id"], "knoten": e["knoten"], "beschreibung": _beschreibung(e)}
           for e in pruefungen if e["ok"] is False]
    return {**bericht, "pruefungen": bericht["pruefungen"] + pruefungen, "maengel": bericht["maengel"] + neu,
            "bestanden": bericht["bestanden"] and not neu, "bewegungen": bewegungsbericht,
            "bilder": {**bericht.get("bilder", {}), **bilder}}
