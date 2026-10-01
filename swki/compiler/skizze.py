"""Skizzenebenen und voll bestimmte Skizzen aus der Spezifikation (verifiziert in Spike S9a, Bausteine 1–4).

2D-Koordinaten (u, v) einer Skizze folgen der Standardebene gleicher Orientierung:
vorne: X=u, Y=v · oben: X=u, Z=−v · rechts: Z=−u, Y=v. Die dritte Koordinate ist die Lage der Ebene.
Der Compiler rechnet (u, v) in einen Modellpunkt und von dort über ModelToSketchTransform in die Skizze um,
damit Skizzen auf Flächen und versetzten Ebenen genauso funktionieren.
"""

import math
from dataclasses import dataclass

from swki.compiler import sw
from swki.compiler.anker import Flaeche, Vektor
from swki.compiler.fehler import (
    FEATURE_NICHT_ERZEUGT, REFERENZ_NICHT_GEFUNDEN, SKIZZE_NICHT_BESTIMMT, SKIZZE_UNGUELTIG, BauFehler,
)
from swki.compiler.topologie import loese_flaeche
from swki.spec.ausdruck import ist_ausdruck
from swki.spec.konturen import bogenende_koordinate, kontur_punkte_roh
from swki.verbindung import mm

STANDARD = {"vorne": 0, "oben": 1, "rechts": 2}  # Index in sw.standardebenen()
NORMALE = {"vorne": (0.0, 0.0, 1.0), "oben": (0.0, 1.0, 0.0), "rechts": (1.0, 0.0, 0.0)}
_ACHSE_ZU_ORIENTIERUNG = {0: "rechts", 1: "oben", 2: "vorne"}
_ORIENTIERUNG_ZU_ACHSE = {o: i for i, o in _ACHSE_ZU_ORIENTIERUNG.items()}
REF_PLANE_ABSTAND = 8  # swRefPlaneReferenceConstraint_Distance
REF_PLANE_UMKEHREN = 256  # swRefPlaneReferenceConstraint_OptionFlip
_MASS_ABSTAND_MM = 8.0  # Abstand der Maßtexte von der Geometrie
SW_ECKE_BEHALTEN = 1  # swConstrainedCornerAction_e.swConstrainedCornerKeepGeometry (Spike S10 Frage 5)
SW_NUT_MITTELPUNKT = 1  # swSketchSlotCreationType_e.swSketchSlotCreationType_center_line (erster Punkt = Mitte)
SW_NUT_MITTE_MITTE = 0  # swSketchSlotLengthType_e.swSketchSlotLengthType_CenterCenter
SW_SKIZZE_LINIE = 0  # swSketchSegments_e.swSketchLINE
SW_GEGEN_UHRZEIGERSINN = 1  # CreateArc/CreateSketchSlot Direction: +1 = gegen den Uhrzeigersinn (Skizzensystem)


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
        # Das Maß ist der Betrag, die Richtung steckt im Umkehren-Flag (live belegt: D1@<Ebenenname>).
        # Wechselt der Parameter später das Vorzeichen, kippt die Ebene nicht mit – dann neu bauen.
        ctx.verknuepfe(f"D1@{neu.Name}", ebene["versatz"]["abstand"], -1 if abstand < 0 else 1)
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
        # Drehsinn: die Abbildung (u, v) → Skizze erhält ihn, wenn ihre Determinante positiv ist (Bögen, S10 Frage 5)
        self.gleichsinnig = (xu - x0) * (yv - y0) - (xv - x0) * (yu - y0) > 0

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

    def lage(self, roh_uv, text_uv: tuple[float, float], nur: int | None = None) -> None:
        """Kennpunkt (u, v) zum Ursprung festlegen: je Richtung Maß, bei 0 Ausrichtung, bei (0, 0) deckungsgleich.

        nur = 0 bzw. 1: nur die u- bzw. v-Lage (Endpunkt eines Bogens, dessen Radius schon feststeht; S10 Frage 5).
        """
        uv = (self.ctx.wert(roh_uv[0]), self.ctx.wert(roh_uv[1]))
        x, y = self.zu_skizze(*uv)
        punkt = self._punkt(x, y)

        def auswahl():
            sw.auswahl_leeren(self.model)
            sw.waehle(self.model, punkt, 0)
            sw.waehle(self.model, self.ursprung, 0, anhaengen=True)

        if nur is None and abs(x) < 1e-9 and abs(y) < 1e-9:
            auswahl()
            self.model.SketchAddConstraints("sgCOINCIDENT")
            sw.auswahl_leeren(self.model)
            return
        for wert, (index, richtung), waagrecht in ((x, self.x_von, True), (y, self.y_von, False)):
            if nur is not None and index != nur:
                continue
            auswahl()
            if abs(wert) < 1e-9:
                self.model.SketchAddConstraints("sgVERTICALPOINTS2D" if waagrecht else "sgHORIZONTALPOINTS2D")
                continue
            text = self._text(*text_uv)
            anzeige = self.model.AddHorizontalDimension2(*text) if waagrecht else self.model.AddVerticalDimension2(*text)
            roh = roh_uv[index] if self.lage_bindbar else wert
            self._merke(anzeige, roh, _vorzeichen(wert) * richtung)
        sw.auswahl_leeren(self.model)

    def _massnamen(self) -> list[str]:
        """Namen der Maße der (noch offenen) Skizze, über das letzte Feature des Baums (S10 Frage 5)."""
        feature = sw.letztes_feature(self.model)
        namen, dd = [], feature.GetFirstDisplayDimension
        while dd is not None:
            namen.append(dd.GetDimension2(0).Name)
            dd = feature.GetNextDisplayDimension(dd)
        return namen

    @staticmethod
    def _linien_an(linien: list, x: float, y: float) -> list:
        """Die Linien, die im Skizzenpunkt (x, y) beginnen oder enden."""
        return [s for s in linien for p in (s.GetStartPoint2, s.GetEndPoint2)
                if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8]

    def verrunde(self, linien: list, ecke_uv: tuple[float, float], roh_radius) -> None:
        """Ecke (u, v) mit Skizzenverrundung runden. Die beiden Linien der Ecke werden gewählt; Maße der Ecke bleiben
        am virtuellen Schnittpunkt (swConstrainedCornerKeepGeometry). CreateFillet legt selbst ein maßgebendes
        Radiusmaß an (S10 Frage 5): es wird über den Vergleich der Maßnamen vor/nach dem Aufruf gefunden und wie
        jedes Skizzenmaß vorgemerkt, damit es später an den Parameter gebunden wird."""
        if self.ctx.wert(roh_radius) == 0:
            return
        x, y = self.zu_skizze(*ecke_uv)
        paar = self._linien_an(linien, x, y)
        if len(paar) != 2:
            raise BauFehler(SKIZZE_UNGUELTIG, f"Ecke {ecke_uv}: {len(paar)} statt 2 Linien", schritt="skizze")
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, paar[0], 0)
        sw.waehle(self.model, paar[1], 0, anhaengen=True)
        vorher = self._massnamen()
        bogen = self.sm.CreateFillet(mm(self.ctx.wert(roh_radius)), SW_ECKE_BEHALTEN)
        sw.auswahl_leeren(self.model)
        if bogen is None:
            raise BauFehler(SKIZZE_UNGUELTIG, f"CreateFillet an Ecke {ecke_uv} fehlgeschlagen", schritt="skizze")
        neu = [n for n in self._massnamen() if n not in vorher]
        if len(neu) != 1:
            raise BauFehler(SKIZZE_UNGUELTIG, f"CreateFillet an Ecke {ecke_uv}: {len(neu)} neue Maße statt 1 ({neu})",
                            schritt="skizze")
        self.masse.append(_Mass(neu[0], roh_radius))

    def _richtung_zu_u(self, linie, mitte_uv: tuple[float, float], roh_winkel, mitte_punkt) -> None:
        """Richtung einer Linie zur u-Achse: 0°/90° über Beziehungen, sonst Winkelmaß zu einer u-parallelen
        Hilfslinie durch mitte_uv (Anfang per sgCOINCIDENT an mitte_punkt, den Slot-Mittelpunkt, gebunden, S10 Frage 5)."""
        winkel = self.ctx.wert(roh_winkel) % 180
        u_ist_x = self.x_von[0] == 0
        sw.auswahl_leeren(self.model)
        if abs(winkel) < 1e-9 or abs(winkel - 90) < 1e-9:
            parallel_u = abs(winkel) < 1e-9
            sw.waehle(self.model, linie, 0)
            self.model.SketchAddConstraints("sgHORIZONTAL2D" if parallel_u == u_ist_x else "sgVERTICAL2D")
            sw.auswahl_leeren(self.model)
            return
        mu_, mv = mitte_uv
        xa, ya = self.zu_skizze(mu_, mv)
        xb, yb = self.zu_skizze(mu_ + 2 * _MASS_ABSTAND_MM, mv)
        hilfe = self.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0)
        if hilfe is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "Hilfslinie für den Langlochwinkel nicht erzeugt", schritt="skizze")
        # Genau zwei Punkte verbinden: Anfang der Hilfslinie und Mittelpunkt des Langlochs. Weitere Punkte an derselben
        # Stelle (konzentrischer Kreis, Polygonecke …) haben eigene Lagemaße und bleiben unberührt.
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, mitte_punkt, 0)
        sw.waehle(self.model, hilfe.GetStartPoint2, 0, anhaengen=True)
        self.model.SketchAddConstraints("sgCOINCIDENT")
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, hilfe, 0)
        self.model.SketchAddConstraints("sgHORIZONTAL2D" if u_ist_x else "sgVERTICAL2D")
        sw.auswahl_leeren(self.model)
        self.groesse(hilfe, (mu_ + _MASS_ABSTAND_MM, mv - _MASS_ABSTAND_MM), 2 * _MASS_ABSTAND_MM)
        sw.waehle(self.model, linie, 0)
        sw.waehle(self.model, hilfe, 0, anhaengen=True)
        halb = math.radians(winkel) / 2
        text = (mu_ + 3 * _MASS_ABSTAND_MM * math.cos(halb), mv + 3 * _MASS_ABSTAND_MM * math.sin(halb))
        self._merke(self.model.AddDimension2(*self._text(*text)), roh_winkel)
        sw.auswahl_leeren(self.model)

    def _langloch(self, l: dict) -> None:
        """Langloch (CreateSketchSlot, Mittelpunkt-Typ, Länge Mitte–Mitte): Breite = Abstand der geraden Seiten,
        Länge = Mittellinie, Richtung zu u, Lage der Mitte (S10 Frage 5)."""
        w = self.ctx.wert
        mu_, mv = w(l["mitte"][0]), w(l["mitte"][1])
        laenge, breite = w(l["laenge"]), w(l["breite"])
        winkel = math.radians(w(l.get("winkel", 0)))
        xm, ym = self.zu_skizze(mu_, mv)
        xe, ye = self.zu_skizze(mu_ + laenge / 2 * math.cos(winkel), mv + laenge / 2 * math.sin(winkel))
        vorher = len(self.skizze.GetSketchSegments or ())
        nut = self.sm.CreateSketchSlot(SW_NUT_MITTELPUNKT, SW_NUT_MITTE_MITTE, mm(breite), xm, ym, 0.0, xe, ye, 0.0,
                                       0.0, 0.0, 0.0, SW_GEGEN_UHRZEIGERSINN, False)
        if nut is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "CreateSketchSlot fehlgeschlagen", schritt="skizze")
        neu = list(self.skizze.GetSketchSegments or ())[vorher:]
        seiten = [s for s in neu if s.GetType == SW_SKIZZE_LINIE and not s.ConstructionGeometry]
        achsen = [s for s in neu if s.GetType == SW_SKIZZE_LINIE and s.ConstructionGeometry]
        if len(seiten) != 2 or len(achsen) != 1:
            raise BauFehler(SKIZZE_UNGUELTIG, f"Langloch: {len(seiten)} Seiten, {len(achsen)} Mittellinien",
                            schritt="skizze")
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, seiten[0], 0)
        sw.waehle(self.model, seiten[1], 0, anhaengen=True)
        self._merke(self.model.AddDimension2(*self._text(mu_, mv + breite / 2 + _MASS_ABSTAND_MM)), l["breite"])
        sw.auswahl_leeren(self.model)
        self.groesse(achsen[0], (mu_, mv - breite / 2 - _MASS_ABSTAND_MM), l["laenge"])
        self._richtung_zu_u(achsen[0], (mu_, mv), l.get("winkel", 0), nut.GetCenterPointHandle)
        self.lage(l["mitte"], (mu_ - laenge / 2 - _MASS_ABSTAND_MM, mv - _MASS_ABSTAND_MM))

    def _kontur(self, k: dict) -> None:
        """Geschlossener Linienzug aus Linien und Bögen (Bögen gegen den Uhrzeigersinn in (u, v)). Bestimmung:
        Eckpunkte und Bogenmittelpunkte zum Ursprung; der Endpunkt eines Bogens nur in einer Koordinate
        (bogenende_koordinate), die andere folgt aus dem Radius (S10 Frage 5). Benachbarte Segmente teilen ihre
        Endpunkte schon, ein Verschmelzen ist nicht nötig."""
        w = self.ctx.wert
        roh = kontur_punkte_roh(k)
        uv = [(w(p[0]), w(p[1])) for p in roh]
        richtung = SW_GEGEN_UHRZEIGERSINN if self.gleichsinnig else -SW_GEGEN_UHRZEIGERSINN
        for i, s in enumerate(k["segmente"]):
            (xa, ya), (xb, yb) = self.zu_skizze(*uv[i]), self.zu_skizze(*uv[i + 1])
            if "linie" in s:
                seg = self.sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)
            else:
                xm, ym = self.zu_skizze(w(s["mitte"][0]), w(s["mitte"][1]))
                seg = self.sm.CreateArc(xm, ym, 0.0, xa, ya, 0.0, xb, yb, 0.0, richtung)
            if seg is None:
                raise BauFehler(SKIZZE_UNGUELTIG, f"Kontur: Segment {i + 1} nicht erzeugt", schritt="skizze")
        bemasst: set[tuple[float, float]] = set()

        def festlegen(p_roh, nur: int | None = None) -> None:
            q = (w(p_roh[0]), w(p_roh[1]))
            schluessel = (round(q[0], 6), round(q[1], 6))
            if schluessel in bemasst:
                return
            bemasst.add(schluessel)
            self.lage(p_roh, (q[0] + _MASS_ABSTAND_MM, q[1] + _MASS_ABSTAND_MM), nur)

        for i, s in enumerate(k["segmente"]):
            if "bogen" in s:
                festlegen(s["mitte"])
                mitte = (w(s["mitte"][0]), w(s["mitte"][1]))
                festlegen(roh[i + 1], bogenende_koordinate(uv[i + 1], mitte))
            else:
                festlegen(roh[i + 1])

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
            if "radius" in r:
                for du, dv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    self.verrunde(list(seg), (mu_ + du * b / 2, mv + dv * h / 2), r["radius"])
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
            p = element["polygon"]
            uv = [(w(q[0]), w(q[1])) for q in p["punkte"]]
            punkte = [self.zu_skizze(*q) for q in uv]
            linien = []
            for (xa, ya), (xb, yb) in zip(punkte, punkte[1:] + punkte[:1]):
                linie = self.sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)
                if linie is None:
                    raise BauFehler(SKIZZE_UNGUELTIG, "CreateLine fehlgeschlagen", schritt="skizze")
                linien.append(linie)
            for q in p["punkte"]:
                self.lage(q, (w(q[0]) + _MASS_ABSTAND_MM, w(q[1]) + _MASS_ABSTAND_MM))
            if "radien" in p:
                je_ecke = p["radien"] if isinstance(p["radien"], list) else [p["radien"]] * len(uv)
                for ecke, radius in zip(uv, je_ecke):
                    self.verrunde(linien, ecke, radius)
        elif "langloch" in element:
            self._langloch(element["langloch"])
        elif "kontur" in element:
            self._kontur(element["kontur"])
        else:
            m = element["mittellinie"]
            xa, ya = self.zu_skizze(w(m["von"][0]), w(m["von"][1]))
            xb, yb = self.zu_skizze(w(m["bis"][0]), w(m["bis"][1]))
            if self.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0) is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCenterLine fehlgeschlagen", schritt="skizze")
            for q in (m["von"], m["bis"]):
                self.lage(q, (w(q[0]) - _MASS_ABSTAND_MM, w(q[1]) + _MASS_ABSTAND_MM))


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


def positionsskizze(feature):
    """Positionsskizze eines Bohrungsassistent-Features: die Unterskizze ohne Skizzensegmente (nur Punkte) –
    Abhängig von S10 Frage 2."""
    unter = feature.GetFirstSubFeature
    while unter is not None:
        if unter.GetTypeName2 == "ProfileFeature" and not (unter.GetSpecificFeature2.GetSketchSegments or ()):
            return unter
        unter = unter.GetNextSubFeature
    raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"{feature.Name}: keine Positionsskizze gefunden", schritt="skizze")


def positionen_festlegen(ctx, feature, se: Skizzenebene, positionen: list, name: str) -> None:
    """Die erste Position steht schon (SelectByRay); weitere als Skizzenpunkte in die Positionsskizze einfügen, alle
    Punkte zum Ursprung bemaßen, die Skizze benennen und die Maße an Parameter binden (S10 Frage 2)."""
    skizze = positionsskizze(feature)
    model, sm = ctx.model, ctx.model.SketchManager
    sw.auswahl_leeren(model)
    skizze.Select2(False, 0)
    sm.InsertSketch(True)  # öffnet die selektierte Skizze (S9b)
    status, masse = None, []
    try:
        skizzierer = Skizzierer(ctx, se, sm.ActiveSketch)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            for u, v in positionen[1:]:
                x, y = skizzierer.zu_skizze(ctx.wert(u), ctx.wert(v))
                if sm.CreatePoint(x, y, 0.0) is None:
                    raise BauFehler(SKIZZE_UNGUELTIG, f"Positionspunkt ({u}, {v}) nicht angelegt", schritt="skizze")
            for p in positionen:
                skizzierer.lage(p, (ctx.wert(p[0]) + _MASS_ABSTAND_MM, ctx.wert(p[1]) + _MASS_ABSTAND_MM))
        status, masse = sm.ActiveSketch.GetConstrainedStatus, skizzierer.masse
    finally:
        sm.InsertSketch(True)
    if status != sw.SW_FULLY_CONSTRAINED:
        raise BauFehler(SKIZZE_NICHT_BESTIMMT, f"Positionsskizze {name}: Status {status} statt voll bestimmt",
                        schritt="skizze")
    skizze.Name = name
    for m in masse:
        ctx.verknuepfe(f"{m.name}@{name}", m.roh, m.vorzeichen)


def richtung(se: Skizzenebene, umkehren: bool) -> Vektor:
    return tuple(-c for c in se.normale) if umkehren else se.normale
