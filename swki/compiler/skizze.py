"""Skizzenebenen und voll bestimmte Skizzen aus der Spezifikation (verifiziert in Spike S9a, Bausteine 1–4).

2D-Koordinaten (u, v) einer Skizze folgen der Standardebene gleicher Orientierung:
vorne: X=u, Y=v · oben: X=u, Z=−v · rechts: Z=−u, Y=v. Die dritte Koordinate ist die Lage der Ebene.
Der Compiler rechnet (u, v) in einen Modellpunkt und von dort über ModelToSketchTransform in die Skizze um,
damit Skizzen auf Flächen und versetzten Ebenen genauso funktionieren.
"""

from dataclasses import dataclass

from swki.compiler import sw
from swki.compiler.anker import Flaeche, Vektor
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, SKIZZE_NICHT_BESTIMMT, SKIZZE_UNGUELTIG, BauFehler
from swki.compiler.topologie import loese_flaeche
from swki.spec.ausdruck import ist_ausdruck
from swki.verbindung import mm

STANDARD = {"vorne": 0, "oben": 1, "rechts": 2}  # Index in sw.standardebenen()
NORMALE = {"vorne": (0.0, 0.0, 1.0), "oben": (0.0, 1.0, 0.0), "rechts": (1.0, 0.0, 0.0)}
_ACHSE_ZU_ORIENTIERUNG = {0: "rechts", 1: "oben", 2: "vorne"}
_ORIENTIERUNG_ZU_ACHSE = {o: i for i, o in _ACHSE_ZU_ORIENTIERUNG.items()}
REF_PLANE_ABSTAND = 8  # swRefPlaneReferenceConstraint_Distance
REF_PLANE_UMKEHREN = 256  # swRefPlaneReferenceConstraint_OptionFlip
_MASS_ABSTAND_MM = 8.0  # Abstand der Maßtexte von der Geometrie


@dataclass
class Skizzenebene:
    objekt: object  # IFeature (Ebene) oder IFace2
    orientierung: str  # "vorne" | "oben" | "rechts"
    lage: float  # mm, Koordinate der Ebene auf ihrer Normalenachse
    normale: Vektor  # Richtung, in die ein Aufsatz standardmäßig wächst


def modellpunkt(orientierung: str, u: float, v: float, lage: float) -> Vektor:
    if orientierung == "vorne":
        return (u, v, lage)
    if orientierung == "oben":
        return (u, lage, -v)
    return (lage, v, -u)


def orientierung_der_normale(normale: Vektor) -> str:
    for i, c in enumerate(normale):
        if abs(c) > 1 - 1e-6:
            return _ACHSE_ZU_ORIENTIERUNG[i]
    raise BauFehler(SKIZZE_UNGUELTIG, f"Skizzenfläche ist nicht achsparallel (Normale {normale})", schritt="ebene")


def ebene_aus_flaeche(flaeche: Flaeche) -> Skizzenebene:
    if flaeche.art != "ebene":
        raise BauFehler(SKIZZE_UNGUELTIG, "Skizzen nur auf ebenen Flächen", schritt="ebene")
    orientierung = orientierung_der_normale(flaeche.normale)
    lage = flaeche.punkt[_ORIENTIERUNG_ZU_ACHSE[orientierung]]
    return Skizzenebene(flaeche.objekt, orientierung, lage, flaeche.normale)


def ebene_aufloesen(ctx, ebene) -> Skizzenebene:
    if isinstance(ebene, Skizzenebene):
        return ebene
    ebenen = sw.standardebenen(ctx.model)
    if isinstance(ebene, str):
        return Skizzenebene(ebenen[STANDARD[ebene]], ebene, 0.0, NORMALE[ebene])
    if "versatz" in ebene:
        basis = ebene["versatz"]["ebene"]
        abstand = ctx.wert(ebene["versatz"]["abstand"])
        sw.auswahl_leeren(ctx.model)
        sw.waehle(ctx.model, ebenen[STANDARD[basis]], 0)
        art = REF_PLANE_ABSTAND | (REF_PLANE_UMKEHREN if abstand < 0 else 0)
        neu = ctx.model.FeatureManager.InsertRefPlane(art, mm(abs(abstand)), 0, 0.0, 0, 0.0)
        if neu is None:
            raise BauFehler(FEATURE_NICHT_ERZEUGT, f"Versetzte Ebene {basis} {abstand:g} mm", schritt="ebene")
        return Skizzenebene(neu, basis, abstand, NORMALE[basis])
    return ebene_aus_flaeche(loese_flaeche(ctx, ebene))


def _position_mm(se: Skizzenebene, u: float, v: float) -> Vektor:
    return modellpunkt(se.orientierung, u, v, se.lage)


def _halb_weg(mitte, groesse):
    """Wert "mitte - groesse/2" als Zahl oder Ausdruck (damit die Ecke eines Rechtecks an Parametern hängt)."""
    if not ist_ausdruck(mitte) and not ist_ausdruck(groesse):
        return mitte - groesse / 2

    def teil(x):
        return f"({x[1:]})" if ist_ausdruck(x) else repr(x)
    return f"={teil(mitte)} - {teil(groesse)} / 2"


def _vorzeichen(x: float) -> int:
    return -1 if x < 0 else 1


@dataclass
class _Mass:
    name: str  # z. B. "D3" (vor dem Umbenennen der Skizze)
    roh: object  # Zahl oder Ausdruck aus der Spezifikation
    vorzeichen: int = 1  # Maße sind Beträge: -1, wenn der Maßwert dem negierten Ausdruck entspricht


class Skizzierer:
    """Legt Skizzenelemente an und bestimmt sie voll: eigene Maße für Größen und für die Lage jedes Kennpunkts
    zum Ursprung (bei 0 eine Ausrichtungsbeziehung). Erzeugt mit AddToDB=True, damit keine automatischen
    Beziehungen entstehen, die eigene Maße überbestimmen würden (live geprüft beim Schreiben von Plan 2a)."""

    def __init__(self, ctx, se: Skizzenebene, skizze):
        self.ctx, self.se, self.model, self.skizze = ctx, se, ctx.model, skizze
        self.sm = ctx.model.SketchManager
        self.mu = sw.mathutil(ctx.app)
        self.ursprung = sw.ursprung(ctx.model)
        self.masse: list[_Mass] = []
        x0, y0 = self.zu_skizze(0, 0)
        # Skizzenursprung = Projektion des Modellursprungs? Nur dann entsprechen Lagemaße den (u, v)-Werten.
        self.lage_bindbar = abs(x0) < 1e-9 and abs(y0) < 1e-9
        xu, yu = self.zu_skizze(1, 0)
        xv, yv = self.zu_skizze(0, 1)
        # Welche Spezifikationskoordinate (0 = u, 1 = v) mit welchem Vorzeichen auf Skizzen-x bzw. -y liegt
        self.x_von = (0, _vorzeichen(xu - x0)) if abs(xu - x0) > 1e-6 else (1, _vorzeichen(xv - x0))
        self.y_von = (0, _vorzeichen(yu - y0)) if abs(yu - y0) > 1e-6 else (1, _vorzeichen(yv - y0))

    def zu_skizze(self, u: float, v: float) -> tuple[float, float]:
        return sw.modell_zu_skizze(self.mu, self.skizze, _position_mm(self.se, u, v))

    def _text(self, u: float, v: float) -> tuple[float, float, float]:
        return tuple(mm(c) for c in _position_mm(self.se, u, v))

    def _merke(self, anzeige, roh, vorzeichen: int = 1) -> None:
        if anzeige is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "Maß konnte nicht angelegt werden", schritt="skizze")
        self.masse.append(_Mass(anzeige.GetDimension2(0).Name, roh, vorzeichen))

    def groesse(self, segment, text_uv: tuple[float, float], roh) -> None:
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, segment, 0)
        self._merke(self.model.AddDimension2(*self._text(*text_uv)), roh)
        sw.auswahl_leeren(self.model)

    def hat_punkt(self, u, v) -> bool:
        x, y = self.zu_skizze(self.ctx.wert(u), self.ctx.wert(v))
        return any(abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8 for p in self.skizze.GetSketchPoints2 or ())

    def _punkt(self, x: float, y: float):
        for p in self.skizze.GetSketchPoints2 or ():
            if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8:
                return p
        raise BauFehler(SKIZZE_UNGUELTIG, f"Skizzenpunkt ({x}, {y}) nicht gefunden", schritt="skizze")

    def lage(self, roh_uv, text_uv: tuple[float, float]) -> None:
        """Kennpunkt (u, v) zum Ursprung festlegen: je Richtung Maß, bei 0 Ausrichtung, bei (0, 0) deckungsgleich."""
        uv = (self.ctx.wert(roh_uv[0]), self.ctx.wert(roh_uv[1]))
        x, y = self.zu_skizze(*uv)
        punkt = self._punkt(x, y)

        def auswahl():
            sw.auswahl_leeren(self.model)
            sw.waehle(self.model, punkt, 0)
            sw.waehle(self.model, self.ursprung, 0, anhaengen=True)

        if abs(x) < 1e-9 and abs(y) < 1e-9:
            auswahl()
            self.model.SketchAddConstraints("sgCOINCIDENT")
            sw.auswahl_leeren(self.model)
            return
        for wert, (index, richtung), waagrecht in ((x, self.x_von, True), (y, self.y_von, False)):
            auswahl()
            if abs(wert) < 1e-9:
                self.model.SketchAddConstraints("sgVERTICALPOINTS2D" if waagrecht else "sgHORIZONTALPOINTS2D")
                continue
            text = self._text(*text_uv)
            anzeige = self.model.AddHorizontalDimension2(*text) if waagrecht else self.model.AddVerticalDimension2(*text)
            roh = roh_uv[index] if self.lage_bindbar else wert
            self._merke(anzeige, roh, _vorzeichen(wert) * richtung)
        sw.auswahl_leeren(self.model)

    def element(self, element: dict) -> None:
        w = self.ctx.wert
        if "rechteck" in element:
            r = element["rechteck"]
            mu_, mv = w(r["mitte"][0]), w(r["mitte"][1])
            b, h = w(r["breite"]), w(r["hoehe"])
            x0, y0 = self.zu_skizze(mu_ - b / 2, mv - h / 2)
            x1, y1 = self.zu_skizze(mu_ + b / 2, mv + h / 2)
            # CreateCornerRectangle statt CreateCenterRectangle: der Mittelpunkt des Mittelpunktrechtecks wird je nach
            # SolidWorks-Zustand nicht angelegt (live beobachtet); die Ecke ist immer ein Skizzenpunkt.
            seg = self.sm.CreateCornerRectangle(x0, y0, 0.0, x1, y1, 0.0)
            if not seg:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCornerRectangle fehlgeschlagen", schritt="skizze")
            # seg[0], seg[1] sind benachbarte Seiten; Breite/Höhe über die Länge zuordnen (Skizzensystem kann gedreht sein)
            seite_b, seite_h = (seg[0], seg[1]) if abs(seg[0].GetLength - mm(b)) < 1e-9 else (seg[1], seg[0])
            self.groesse(seite_b, (mu_, mv - h / 2 - _MASS_ABSTAND_MM), r["breite"])
            self.groesse(seite_h, (mu_ - b / 2 - _MASS_ABSTAND_MM, mv), r["hoehe"])
            ecke = (_halb_weg(r["mitte"][0], r["breite"]), _halb_weg(r["mitte"][1], r["hoehe"]))
            self.lage(ecke, (mu_ - b / 2 - _MASS_ABSTAND_MM, mv - h / 2 - _MASS_ABSTAND_MM))
        elif "kreis" in element:
            k = element["kreis"]
            mu_, mv = w(k["mitte"][0]), w(k["mitte"][1])
            d = w(k["durchmesser"])
            x, y = self.zu_skizze(mu_, mv)
            seg = self.sm.CreateCircleByRadius(x, y, 0.0, mm(d / 2))
            if seg is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCircleByRadius fehlgeschlagen", schritt="skizze")
            self.groesse(seg, (mu_ + d / 2 + _MASS_ABSTAND_MM, mv + _MASS_ABSTAND_MM), k["durchmesser"])
            self.lage(k["mitte"], (mu_ - d / 2 - _MASS_ABSTAND_MM, mv - _MASS_ABSTAND_MM))
        elif "polygon" in element:
            roh = element["polygon"]["punkte"]
            punkte = [self.zu_skizze(w(p[0]), w(p[1])) for p in roh]
            for (xa, ya), (xb, yb) in zip(punkte, punkte[1:] + punkte[:1]):
                if self.sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0) is None:
                    raise BauFehler(SKIZZE_UNGUELTIG, "CreateLine fehlgeschlagen", schritt="skizze")
            for p in roh:
                self.lage(p, (w(p[0]) + _MASS_ABSTAND_MM, w(p[1]) + _MASS_ABSTAND_MM))
        else:
            m = element["mittellinie"]
            xa, ya = self.zu_skizze(w(m["von"][0]), w(m["von"][1]))
            xb, yb = self.zu_skizze(w(m["bis"][0]), w(m["bis"][1]))
            if self.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0) is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCenterLine fehlgeschlagen", schritt="skizze")
            for p in (m["von"], m["bis"]):
                self.lage(p, (w(p[0]) - _MASS_ABSTAND_MM, w(p[1]) + _MASS_ABSTAND_MM))


def skizziere(ctx, ebene, elemente: list[dict], name: str):
    """Erzeugt eine voll bestimmte Skizze und benennt sie. Rückgabe: (Skizzen-Feature, Skizzenebene).

    Alle Größen- und Lagemaße werden per Gleichung an Parameter gebunden, wenn der Wert ein Ausdruck ist.
    """
    se = ebene_aufloesen(ctx, ebene)
    model, sm = ctx.model, ctx.model.SketchManager
    sw.auswahl_leeren(model)
    sw.waehle(model, se.objekt, 0)
    sm.InsertSketch(True)
    status, masse = None, []
    try:
        skizzierer = Skizzierer(ctx, se, sm.ActiveSketch)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            for element in elemente:
                skizzierer.element(element)
        status, masse = sm.ActiveSketch.GetConstrainedStatus, skizzierer.masse
    finally:
        sm.InsertSketch(True)
    if status != sw.SW_FULLY_CONSTRAINED:
        raise BauFehler(SKIZZE_NICHT_BESTIMMT, f"Skizze {name}: Status {status} statt voll bestimmt", schritt="skizze")
    feature = sw.letztes_feature(model)
    feature.Name = name
    for m in masse:
        ctx.verknuepfe(f"{m.name}@{name}", m.roh, m.vorzeichen)
    return feature, se


def richtung(se: Skizzenebene, umkehren: bool) -> Vektor:
    return tuple(-c for c in se.normale) if umkehren else se.normale
