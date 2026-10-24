"""Skizzenebenen und voll bestimmte Skizzen aus der Spezifikation (verifiziert in Spike S9a, Bausteine 1–4).

2D-Koordinaten (u, v) einer Skizze folgen der Standardebene gleicher Orientierung:
vorne: X=u, Y=v · oben: X=u, Z=−v · rechts: Z=−u, Y=v. Die dritte Koordinate ist die Lage der Ebene.
Der Compiler rechnet (u, v) in einen Modellpunkt und von dort über ModelToSketchTransform in die Skizze um,
damit Skizzen auf Flächen und versetzten Ebenen genauso funktionieren.
"""

import math
from dataclasses import dataclass, field, replace

from swki.bemassung import MITTE, URSPRUNG, Auftrag, Kennpunkt, bezug_von, massplan, rechteck_kennkoordinate
from swki.compiler import sw
from swki.compiler.anker import AnkerFehler, Flaeche, Kante, Vektor, differenz, randkante, skalar
from swki.compiler.fehler import (
    FEATURE_NICHT_ERZEUGT, REFERENZ_NICHT_GEFUNDEN, SKIZZE_NICHT_BESTIMMT, SKIZZE_UNGUELTIG, BauFehler,
)
from swki.compiler.topologie import kante_aus, loese_flaeche
from swki.spec.ausdruck import ist_ausdruck
from swki.spec.konturen import bogenende_koordinate, eckradien_roh, kontur_punkte_roh
from swki.verbindung import in_mm, mm

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
SW_DECKUNGSGLEICH = 9  # swConstraintType_e.swConstraintType_COINCIDENT
SW_BEZIEHUNG_PUNKT = 2  # swSketchRelationEntityTypes_e.swSketchRelationEntityType_Point
ART_SKRIPT = "skript"  # art im Maßprotokoll für Maße ohne Spec-Pfad (Notausgang-Skripte); der Pfad ist dann das Feature
_QUER = 1.0 - 1e-6  # |cos| zwischen Flächennormale und Achse, ab dem eine Bezugsfläche quer zur Achse steht
_NUR_URSPRUNG = {0: URSPRUNG, 1: URSPRUNG}  # Bezug der Kontur-, Polygon- und Mittellinienpunkte (Spec §2)


def schluessel_element(element, typ: int) -> tuple:
    """Skizzenelement eindeutig in seiner Skizze: Punkt bzw. Segmenttyp + ID (IDs sind je Typ eindeutig)."""
    return ("punkt" if typ == SW_BEZIEHUNG_PUNKT else element.GetType, tuple(element.GetID))


def fremde_deckungen(beziehungen, alte: set) -> list:
    """Deckungsbeziehungen, die ein Element aus `alte` (vor dem Erzeugen vorhanden) betreffen – beim Erzeugen
    automatisch angelegt (Fangen trotz AddToDB, AP 6.8 Lauf 7) und neben den Lagemaßen überzählig."""
    return [b for b in beziehungen if b.GetRelationType == SW_DECKUNGSGLEICH
            and any(schluessel_element(e, t) in alte for e, t in zip(b.GetEntities or (), b.GetEntitiesType or ()))]


@dataclass
class Skizzenebene:
    objekt: object  # IFeature (Ebene) oder IFace2
    orientierung: str  # "vorne" | "oben" | "rechts"
    lage: float  # mm, Koordinate der Ebene auf ihrer Normalenachse
    normale: Vektor  # Richtung, in die ein Aufsatz standardmäßig wächst
    flaeche: Flaeche | None = None  # Skizzenfläche (Randkanten für Bezüge); None auf Standard- und Versatzebenen


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
    return Skizzenebene(flaeche.objekt, orientierung, lage, flaeche.normale, flaeche)


def feld_pfad(pfad, typ: str, feld: str):
    """Spec-Pfad eines Felds im Skizzenelement: "<pfad>.<typ>.<feld>" (pfad = Pfad des Elements, typ = sein Schlüssel,
    z. B. "kreis"). Ein Dict ordnet jedem Feld seinen Pfad selbst zu (Bohrungen: Lage in positionen[k], Durchmesser am
    Feature); None (Notausgang-Skript, kein Spec-Pfad) bleibt None."""
    if pfad is None:
        return None
    if isinstance(pfad, dict):
        return pfad[feld]
    return f"{pfad}.{typ}.{feld}"


def _index(pfad, k: int):
    return None if pfad is None else f"{pfad}[{k}]"


def _massziel(ctx, pfad, art: str) -> tuple[str, str]:
    """Pfad und art eines Maßes fürs Maßprotokoll; ohne Spec-Pfad der Pfad des laufenden Features mit art "skript"."""
    if pfad is not None:
        return pfad, art
    return (ctx.pfad(ctx.knoten) if ctx.knoten else ""), ART_SKRIPT


def ebene_aufloesen(ctx, ebene, pfad: str | None = None) -> Skizzenebene:
    """Skizzenebene der Spezifikation; pfad = Spec-Pfad dieser Ebene (für das Maßprotokoll des Versatzes)."""
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
        ziel, art = _massziel(ctx, None if pfad is None else f"{pfad}.versatz.abstand", "versatz")
        ctx.mass(f"D1@{neu.Name}", ebene["versatz"]["abstand"], ziel, art, -1 if abstand < 0 else 1)
        return Skizzenebene(neu, basis, abstand, NORMALE[basis])
    return ebene_aus_flaeche(loese_flaeche(ctx, ebene))


def _position_mm(se: Skizzenebene, u: float, v: float) -> Vektor:
    return modellpunkt(se.orientierung, u, v, se.lage)


def _vorzeichen(x: float) -> int:
    return -1 if x < 0 else 1


def _teil(x) -> str:
    return f"({x[1:]})" if ist_ausdruck(x) else repr(x)


def _seite_roh(mitte, groesse, richtung: int):
    """Rechteckseite "mitte ± groesse/2" (richtung −1/+1) als Zahl oder Ausdruck – mit Gleichungen hängt sie so an den
    Parametern (Ruling 7, wie früher die Ecke)."""
    if not ist_ausdruck(mitte) and not ist_ausdruck(groesse):
        return mitte + richtung * groesse / 2
    return f"={_teil(mitte)} {'-' if richtung < 0 else '+'} {_teil(groesse)} / 2"


def _paar_roh(roh):
    """Abstand eines zur Mitte symmetrischen Paars: 2 × Koordinate des festlegenden Punkts (Zahl oder Ausdruck)."""
    return f"=2 * {_teil(roh)}" if ist_ausdruck(roh) else 2 * roh


def _zur_kante(bezug) -> bool:
    return isinstance(bezug, dict) or bezug in ("-rand", "+rand")


def _text_zwischen(achse: int, von: float, bis: float, quer: float) -> tuple[float, float]:
    """Lage (u, v) des Maßtexts eines Maßes auf `achse` zwischen den Koordinaten von und bis, neben quer."""
    mitte = (von + bis) / 2
    return (mitte, quer + _MASS_ABSTAND_MM) if achse == 0 else (quer + _MASS_ABSTAND_MM, mitte)


@dataclass
class _Mass:
    name: str  # z. B. "D3" (vor dem Umbenennen der Skizze)
    roh: object  # Zahl oder Ausdruck aus der Spezifikation
    vorzeichen: int = 1  # Maße sind Beträge: -1, wenn der Maßwert dem negierten Ausdruck entspricht
    pfad: str = ""  # Spec-Pfad des Werts (Maßprotokoll)
    art: str = ART_SKRIPT  # lage | groesse | radius | winkel | konstruktion | skript
    bezug: object = None  # Lage: Spec-Wert des Bezugs ("ursprung", "mitte", "-rand", {"flaeche": …})
    wert: float | None = None  # Betrag in mm, wenn er nicht |roh| ist (Kontext.mass)


@dataclass
class _Ziel:
    """Was für einen Kennpunkt in der Skizze gewählt wird."""
    punkt: object = None  # Skizzenpunkt; None bei einer Rechteckmitte, deren Punkt erst bei Bedarf entsteht
    diagonale: object = None  # Rechteck: Konstruktionsdiagonale, deren Mitte der Kennpunkt ist (Spike S17 Zeile 5)
    linien: dict = field(default_factory=dict)  # Rechteck: Seite je Achse für das Maß zur Bezugskante (Spike S17 Zeile 3)
    kanten: dict = field(default_factory=dict)  # schon aufgelöste Bezugskante je Achse: (Kante, Lage), siehe _bezugskante


class Skizzierer:
    """Legt Skizzenelemente an und bestimmt sie voll. Zweiphasig: `element` legt Geometrie und Größenmaße sofort an und
    merkt die Lagen als Kennpunkte vor; `lagen_festlegen` bemaßt sie nach bemassung.massplan zu Ursprung, Mitte, Rand
    oder Fläche (Spec Bemaßungsbezug §5, Wege aus Spike S17). Erzeugt mit AddToDB=True, damit keine automatischen
    Beziehungen entstehen, die eigene Maße überbestimmen würden (live geprüft beim Schreiben von Plan 2a).

    hilfslinien=False (Rotationsskizze: ihre Mittellinie wird Achse): keine Diagonalen und Symmetrielinien – Rechtecke
    über Seitenmittelpunkte, `mitte` wie `ursprung`."""

    def __init__(self, ctx, se: Skizzenebene, skizze, hilfslinien: bool = True):
        self.ctx, self.se, self.model, self.skizze = ctx, se, ctx.model, skizze
        self.sm = ctx.model.SketchManager
        self.mu = sw.mathutil(ctx.app)
        self.ursprung = sw.ursprung(ctx.model)
        self.masse: list[_Mass] = []
        self.hilfslinien = hilfslinien
        self._kennpunkte: list[Kennpunkt] = []
        self._ziele: list[_Ziel] = []
        self._belegt: set = set()  # Skizzenpunkte, die schon einem Kennpunkt gehören
        self._verrundungen: list[tuple] = []  # nach den Lagen anzulegen (Maße bleiben am virtuellen Schnittpunkt)
        self._mittellinien: dict[int, object] = {}  # Symmetrielinie je Achse
        self._kanten: list[Kante] | None = None  # Kanten der Skizzenfläche
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

    def _eintrag(self, name: str, roh, vorzeichen: int, pfad: str | None, art: str, bezug=None,
                 wert: float | None = None) -> _Mass:
        ziel, art = _massziel(self.ctx, pfad, art)
        return _Mass(name, roh, vorzeichen, ziel, art, bezug, wert)

    def _merke(self, anzeige, roh, vorzeichen: int = 1, pfad: str | None = None, art: str = "groesse", bezug=None,
               wert: float | None = None) -> None:
        if anzeige is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "Maß konnte nicht angelegt werden", schritt="skizze")
        self.masse.append(self._eintrag(anzeige.GetDimension2(0).Name, roh, vorzeichen, pfad, art, bezug, wert))

    def groesse(self, segment, text_uv: tuple[float, float], roh, pfad: str | None = None, art: str = "groesse") -> None:
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, segment, 0)
        self._merke(self.model.AddDimension2(*self._text(*text_uv)), roh, 1, pfad, art)
        sw.auswahl_leeren(self.model)

    def hat_punkt(self, u, v) -> bool:
        x, y = self.zu_skizze(self.ctx.wert(u), self.ctx.wert(v))
        return any(abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8 for p in self.skizze.GetSketchPoints2 or ())

    def _punkt(self, x: float, y: float):
        """Skizzenpunkt an (x, y), der noch keinem Kennpunkt gehört (konzentrische Elemente haben je einen eigenen);
        None, wenn dort nur schon festgelegte liegen (AddToDB teilt Linienenden an gleicher Stelle, Spike S17)."""
        da = [p for p in self.skizze.GetSketchPoints2 or () if abs(p.X - x) < 1e-8 and abs(p.Y - y) < 1e-8]
        if not da:
            raise BauFehler(SKIZZE_UNGUELTIG, f"Skizzenpunkt ({x}, {y}) nicht gefunden", schritt="skizze")
        return next((p for p in da if schluessel_element(p, SW_BEZIEHUNG_PUNKT) not in self._belegt), None)

    # --- Lagen: Kennpunkte vormerken, dann nach bemassung.massplan festlegen ---------------------------------------------

    def kennpunkt(self, punkt_uv, roh_uv, bezug: dict, pfad, gruppe: str, achsen=(0, 1), ziel: _Ziel | None = None) -> None:
        """Lage eines Punkts (u, v in mm) vormerken; `lagen_festlegen` bemaßt sie.

        roh_uv: Spec-Werte der Koordinaten; bezug: Bezug je Achse (bemassung.bezug_von); pfad: Spec-Pfad des Punkts (das
        Maß der Achse a trägt "<pfad>[a]"); gruppe: Art und Größe des Elements (Paare für `mitte` nur innerhalb einer
        Gruppe); achsen: nur diese Koordinaten (Endpunkt eines Bogens, dessen Radius schon feststeht; S10 Frage 5);
        ziel: was gewählt wird, sonst der freie Skizzenpunkt an (u, v) – liegt dort nur ein schon festgelegter (geteiltes
        Linienende), entfällt der Kennpunkt."""
        if ziel is None:
            punkt = self._punkt(*self.zu_skizze(*punkt_uv))
            if punkt is None:
                return
            ziel = _Ziel(punkt=punkt)
        if ziel.punkt is not None:
            self._belegt.add(schluessel_element(ziel.punkt, SW_BEZIEHUNG_PUNKT))
        self._kennpunkte.append(Kennpunkt(tuple(punkt_uv), tuple(achsen), dict(bezug), pfad, tuple(roh_uv), gruppe))
        self._ziele.append(ziel)

    def lagen_festlegen(self) -> None:
        """Alle vorgemerkten Kennpunkte festlegen (bemassung.massplan: Symmetrie, Abstand im Paar, Maß zu Rand bzw.
        Fläche oder Ursprung, Ausrichtung, Deckung), danach die vorgemerkten Verrundungen – wie bisher erst die Lagen,
        dann die Ecken (ihre Maße bleiben am virtuellen Schnittpunkt)."""
        punkte = self._kennpunkte
        if not self.hilfslinien:
            punkte = [replace(p, bezug={a: URSPRUNG if b == MITTE else b for a, b in p.bezug.items()}) for p in punkte]
        kanten: dict[tuple[int, int], tuple[Kante, float]] = {}

        def bezugslage(i: int, achse: int) -> float:
            kanten[(i, achse)] = (self._ziele[i].kanten.get(achse)
                                  or self._bezugskante(punkte[i].bezug[achse], achse, punkte[i].uv))
            return kanten[(i, achse)][1]

        for auftrag in massplan(punkte, bezugslage, self.ctx.tol_mm):
            self._ausfuehren(auftrag, punkte, kanten)
        for verrundung in self._verrundungen:
            self.verrunde(*verrundung)
        self._kennpunkte, self._ziele, self._verrundungen = [], [], []

    def _ausfuehren(self, a: Auftrag, punkte: list[Kennpunkt], kanten: dict) -> None:
        p, ziel, achse = punkte[a.punkt], self._ziele[a.punkt], a.achse
        if a.art == "symmetrie":  # Spike S17 Zeilen 4 und 5: (Punkt, Punkt, Mittellinie)
            mittellinie = self._mittellinie(achse, p)
            self._beziehung("sgSYMMETRIC", self._punkt_von(a.punkt), self._punkt_von(a.partner), mittellinie)
        elif a.art == "deckung":
            self._beziehung("sgCOINCIDENT", self._punkt_von(a.punkt), self.ursprung)
        elif a.art == "ausrichtung":
            self._beziehung("sgVERTICALPOINTS2D" if self.x_von[0] == achse else "sgHORIZONTALPOINTS2D",
                            self._punkt_von(a.punkt), self.ursprung)
        elif a.art == "ursprung":
            self._ursprungsmass(a, p)
        elif a.art == "paarabstand":
            q = punkte[a.partner]
            text = _text_zwischen(achse, p.uv[achse], q.uv[achse], p.uv[1 - achse])
            anzeige = self._mass_achse(achse, (self._punkt_von(a.punkt), self._punkt_von(a.partner)), text)
            # symmetrisch zur Mitte: Abstand = 2 × Koordinate, Vorzeichen wie die Koordinate (Gleichung möglich, Ruling 7)
            self._merke(anzeige, _paar_roh(p.roh[achse]), _vorzeichen(p.uv[achse] - q.uv[achse]),
                        _index(p.pfad, achse), "lage", p.bezug[achse])
        else:  # bezug: zur Kante der Skizzenfläche (Rand bzw. Kante in der Bezugsfläche, Ruling 2)
            kante, lage = kanten[(a.punkt, achse)]
            text = _text_zwischen(achse, lage, p.uv[achse], p.uv[1 - achse])
            linie = ziel.linien.get(achse)
            if linie is None:  # Punkt + Kante achsparallel (Spike S17 Zeile 1)
                anzeige = self._mass_achse(achse, (self._punkt_von(a.punkt), kante.objekt), text)
            else:  # Rechteckseite + Kante mit AddDimension2 (Spike S17 Zeile 3)
                self._waehle(linie, kante.objekt)
                anzeige = self.model.AddDimension2(*self._text(*text))
                sw.auswahl_leeren(self.model)
            self._merke(anzeige, p.roh[achse], _vorzeichen(p.uv[achse] - lage), _index(p.pfad, achse), "lage",
                        p.bezug[achse], a.wert)

    def _ursprungsmass(self, a: Auftrag, p: Kennpunkt) -> None:
        """Maß zum Ursprung. roh ist die Spec-Koordinate, wenn Skizzen- und Modellursprung zusammenfallen, sonst die
        Skizzenkoordinate in mm; vorzeichen gehört immer zu roh. Ergibt roh die Koordinate nicht, eigener Wert (dann
        keine Gleichung)."""
        achse = a.achse
        anzeige = self._mass_achse(achse, (self._punkt_von(a.punkt), self.ursprung),
                                   _text_zwischen(achse, 0.0, p.uv[achse], p.uv[1 - achse]))
        wert = None
        if self.lage_bindbar:
            roh, vorzeichen = p.roh[achse], _vorzeichen(p.uv[achse])
            if abs(self.ctx.wert(roh) - p.uv[achse]) > 1e-9:
                wert = a.wert
        else:
            x, y = self.zu_skizze(*p.uv)
            skizzenkoordinate = x if self.x_von[0] == achse else y
            roh, vorzeichen = in_mm(skizzenkoordinate), _vorzeichen(skizzenkoordinate)
        self._merke(anzeige, roh, vorzeichen, _index(p.pfad, achse), "lage", p.bezug[achse], wert)

    def _waehle(self, *objekte) -> None:
        sw.auswahl_leeren(self.model)
        for i, o in enumerate(objekte):
            sw.waehle(self.model, o, 0, anhaengen=i > 0)

    def _beziehung(self, art: str, *objekte) -> None:
        self._waehle(*objekte)
        self.model.SketchAddConstraints(art)
        sw.auswahl_leeren(self.model)

    def _mass_achse(self, achse: int, objekte: tuple, text_uv: tuple[float, float]):
        """Achsparalleles Maß in Richtung der Spec-Achse zwischen den gewählten Objekten (Skizzen-x: horizontal)."""
        self._waehle(*objekte)
        text = self._text(*text_uv)
        anzeige = (self.model.AddHorizontalDimension2(*text) if self.x_von[0] == achse
                   else self.model.AddVerticalDimension2(*text))
        sw.auswahl_leeren(self.model)
        return anzeige

    def _punkt_von(self, i: int):
        """Skizzenpunkt des Kennpunkts i; eine Rechteckmitte bekommt ihn erst hier: Punkt mittig der Diagonale
        (Spike S17 Fall 5_rechteck_symmetrie)."""
        ziel = self._ziele[i]
        if ziel.punkt is None:
            x, y = self.zu_skizze(*self._kennpunkte[i].uv)
            ziel.punkt = self.sm.CreatePoint(x, y, 0.0)
            if ziel.punkt is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "Mittelpunkt des Rechtecks nicht angelegt", schritt="skizze")
            self._beziehung("sgATMIDDLE", ziel.punkt, ziel.diagonale)
        return ziel.punkt

    def _achsrichtung(self, achse: int) -> Vektor:
        """Richtung der Spec-Achse (0 = u, 1 = v) im Modell."""
        o = self.se.orientierung
        return differenz(modellpunkt(o, *((1.0, 0.0) if achse == 0 else (0.0, 1.0)), 0.0), modellpunkt(o, 0.0, 0.0, 0.0))

    def _flaechenkanten(self) -> list[Kante]:
        if self._kanten is None:
            self._kanten = [kante_aus(e) for e in self.se.flaeche.objekt.GetEdges or ()]
        return self._kanten

    def _bezugskante(self, bezug, achse: int, uv) -> tuple[Kante, float]:
        """Kante der Skizzenfläche für einen Rand- oder Flächenbezug und ihre Koordinate auf der Achse (mm).

        `-rand`/`+rand`: die Randkante (anker.randkante). `{flaeche}`: die Kante der Skizzenfläche, die in dieser Fläche
        liegt – SolidWorks bemaßt nicht zu Flächen (Spike S17 Zeile 2, Ruling 2)."""
        name = "flaeche" if isinstance(bezug, dict) else bezug
        if self.se.flaeche is None:
            raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"Bezug {name!r} braucht eine Skizze auf einer Fläche",
                            schritt="skizze")
        richtung, kanten = self._achsrichtung(achse), self._flaechenkanten()
        vorzeichen = 1 if bezug == "+rand" else -1
        if isinstance(bezug, dict):
            seite = loese_flaeche(self.ctx, bezug["flaeche"])
            if seite.art != "ebene" or abs(skalar(seite.normale, richtung)) < _QUER:
                raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"Bezugsfläche {bezug['flaeche']} steht nicht quer zur Achse "
                                                         f"{'uv'[achse]}", schritt="skizze")
            tol = self.ctx.tol_mm
            kanten = [k for k in kanten if k.art == "linie"
                      and all(abs(skalar(differenz(q, seite.punkt), seite.normale)) <= tol for q in (k.start, k.ende))]
            if not kanten:
                raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"Bezugsfläche {bezug['flaeche']} berührt die Skizzenfläche "
                                                         "nicht", schritt="skizze")
        try:
            kante = randkante(kanten, richtung, vorzeichen, _position_mm(self.se, *uv), self.ctx.tol_mm)
        except AnkerFehler as e:
            raise BauFehler(e.code, f"Bezug {name!r} auf {'uv'[achse]}: {e}", schritt="skizze") from e
        return kante, skalar(kante.start, richtung)

    def _randkante_der_mittellinie(self, achse: int) -> Kante | None:
        """Randkante, auf der die Symmetrielinie zu `achse` (entlang der anderen Achse) enden kann: quer zu ihr, nicht
        durch den Ursprung und über die Linie achse = 0 reichend; erst in −, dann in +. None ohne Skizzenfläche."""
        if self.se.flaeche is None:
            return None
        entlang, quer, tol = self._achsrichtung(1 - achse), self._achsrichtung(achse), self.ctx.tol_mm
        for vorzeichen in (-1, 1):
            try:
                kante = randkante(self._flaechenkanten(), entlang, vorzeichen, _position_mm(self.se, 0.0, 0.0), tol)
            except AnkerFehler:
                continue
            a, b = skalar(kante.start, quer), skalar(kante.ende, quer)
            if abs(skalar(kante.start, entlang)) > tol and min(a, b) - tol <= 0.0 <= max(a, b) + tol:
                return kante
        return None

    def _mittellinie(self, achse: int, festlegend: Kennpunkt):
        """Symmetrielinie zu `achse`: Konstruktionslinie durch den Ursprung entlang der anderen Achse, eine je Achse und
        Skizze (Spike S17 Zeile 4). Anfang deckungsgleich im Ursprung; Ende deckungsgleich auf der Randkante der
        Skizzenfläche (Ruling 4, Fall 4_mittellinie_kante), ohne Skizzenfläche oder passende Kante mit Längenmaß
        (Ruling 4a, Fall 4_mittellinie_laenge)."""
        if achse in self._mittellinien:
            return self._mittellinien[achse]
        entlang = 1 - achse
        kante = self._randkante_der_mittellinie(achse)
        laenge = 2 * _MASS_ABSTAND_MM if kante is None else skalar(kante.start, self._achsrichtung(entlang))
        ende = (laenge, 0.0) if entlang == 0 else (0.0, laenge)
        (xa, ya), (xb, yb) = self.zu_skizze(0.0, 0.0), self.zu_skizze(*ende)
        linie = self.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0)
        if linie is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "Mittellinie für die Symmetrie nicht erzeugt", schritt="skizze")
        self._beziehung("sgCOINCIDENT", linie.GetStartPoint2, self.ursprung)
        self._beziehung("sgHORIZONTAL2D" if self.x_von[0] == entlang else "sgVERTICAL2D", linie)
        if kante is not None:
            self._beziehung("sgCOINCIDENT", linie.GetEndPoint2, kante.objekt)
        else:
            self.groesse(linie, _text_zwischen(entlang, 0.0, laenge, -_MASS_ABSTAND_MM), laenge,
                         _index(festlegend.pfad, achse), "konstruktion")
        self._mittellinien[achse] = linie
        return linie

    def _diagonale(self, seg: list):
        """Konstruktionsdiagonale von Ecke (−, −) nach (+, +); AddToDB teilt die Ecken (Spike S17), sonst deckungsgleich
        binden."""
        e0, e2 = seg[0].GetStartPoint2, seg[1].GetEndPoint2
        diagonale = self.sm.CreateCenterLine(e0.X, e0.Y, 0.0, e2.X, e2.Y, 0.0)
        if diagonale is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "Diagonale des Rechtecks nicht erzeugt", schritt="skizze")
        for ende, ecke in ((diagonale.GetStartPoint2, e0), (diagonale.GetEndPoint2, e2)):
            if tuple(ende.GetID) != tuple(ecke.GetID):
                self._beziehung("sgCOINCIDENT", ende, ecke)
        return diagonale

    def _mittelpunkt_auf(self, linie, uv: tuple[float, float]):
        """Skizzenpunkt mittig auf einer Rechteckseite: CreatePoint + sgATMIDDLE (Beziehung wie Spike S17 Fall
        5_rechteck_symmetrie). Er bleibt in der Mitte der getrimmten Seite: Nach einer einzelnen Eckverrundung schiebt
        der Löser das Rechteck, erst nach allen vier symmetrischen steht es wieder (deshalb verrunde mit paar)."""
        punkt = self.sm.CreatePoint(*self.zu_skizze(*uv), 0.0)
        if punkt is None:
            raise BauFehler(SKIZZE_UNGUELTIG, f"Seitenmittelpunkt {uv} des Rechtecks nicht angelegt", schritt="skizze")
        self._beziehung("sgATMIDDLE", punkt, linie)
        return punkt

    def _rechteck_lage(self, r: dict, seg: list, pfad) -> None:
        """Kennpunkte eines Rechtecks (Spec §3, Ruling 6). Je Achse nach bemassung.rechteck_kennkoordinate entweder die
        Seite (Rand, Fläche, ursprung mit Mitte ≠ 0: zugewandte bzw. nächste Seite) oder die Mitte (mitte, ursprung mit
        Mitte auf 0):
        (a) beide Seite: die Ecke der beiden Seiten;
        (b) eine Seite: Mittelpunkt dieser Seite, ein Kennpunkt mit beiden Achsen (paarfähig);
        (c) beide Mitte, Mitte im Ursprung, oder ohne Hilfslinien: je ein Mittelpunkt einer Seite entlang u (Lage u) und
            einer entlang v (Lage v), ohne Konstruktionslinie;
        (d) beide Mitte, Mitte ≠ (0, 0): Mitte der Konstruktionsdiagonale (Spike S17 Zeile 5), paarfähig.
        Maße zur Bezugskante über die Seitenlinie (Spike S17 Zeile 3); die Kante wird einmal aufgelöst und gilt für
        Kennkoordinate und Maß. roh der Seite: "mitte ± groesse/2".
        seg: Seiten unten, rechts, oben, links (seg[i] beginnt an Ecke i: (−,−), (+,−), (+,+), (−,+))."""
        w = self.ctx.wert
        mitte, groesse = (w(r["mitte"][0]), w(r["mitte"][1])), (w(r["breite"]), w(r["hoehe"]))
        groesse_roh = (r["breite"], r["hoehe"])
        bezug = bezug_von(r)
        kanten = {a: self._bezugskante(bezug[a], a, mitte) for a in (0, 1) if _zur_kante(bezug[a])}
        kenn = {a: rechteck_kennkoordinate(mitte[a], groesse[a], bezug[a], kanten[a][1] if a in kanten else None)
                for a in (0, 1)}
        seitlich = tuple(a for a in (0, 1) if abs(kenn[a] - mitte[a]) >= groesse[a] / 4)
        richtung = {a: 1 if kenn[a] > mitte[a] else -1 for a in seitlich}
        seiten = {0: (seg[3], seg[1]), 1: (seg[0], seg[2])}  # Seite quer zur Achse a, in − und in +
        linien = {a: seiten[a][0 if richtung[a] < 0 else 1] for a in seitlich}
        uv = (kenn[0], kenn[1])
        roh = tuple(_seite_roh(r["mitte"][a], groesse_roh[a], richtung[a]) if a in seitlich else r["mitte"][a]
                    for a in (0, 1))
        gruppe, mitte_pfad = f"rechteck {groesse[0]:.6g} {groesse[1]:.6g}", feld_pfad(pfad, "rechteck", "mitte")
        if len(seitlich) == 2:  # (a)
            ecke = seg[{(-1, -1): 0, (1, -1): 1, (1, 1): 2, (-1, 1): 3}[(richtung[0], richtung[1])]].GetStartPoint2
            self.kennpunkt(uv, roh, bezug, mitte_pfad, gruppe, ziel=_Ziel(punkt=ecke, linien=linien, kanten=kanten))
        elif seitlich:  # (b)
            punkt = self._mittelpunkt_auf(linien[seitlich[0]], uv)
            self.kennpunkt(uv, roh, bezug, mitte_pfad, gruppe, ziel=_Ziel(punkt=punkt, linien=linien, kanten=kanten))
        elif self.hilfslinien and any(abs(m) > self.ctx.tol_mm for m in mitte):  # (d)
            self.kennpunkt(uv, roh, bezug, mitte_pfad, gruppe, ziel=_Ziel(diagonale=self._diagonale(seg)))
        else:  # (c)
            for achse, linie, punkt_uv in ((0, seg[0], (mitte[0], mitte[1] - groesse[1] / 2)),
                                           (1, seg[3], (mitte[0] - groesse[0] / 2, mitte[1]))):
                punkt = self._mittelpunkt_auf(linie, punkt_uv)
                self.kennpunkt(punkt_uv, roh, bezug, mitte_pfad, gruppe, (achse,), _Ziel(punkt=punkt))

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

    def verrunde(self, linien: list, ecke_uv: tuple[float, float], roh_radius, pfad: str | None = None,
                 paar: tuple | None = None) -> None:
        """Ecke (u, v) mit Skizzenverrundung runden. Die beiden Linien der Ecke werden gewählt; Maße der Ecke bleiben
        am virtuellen Schnittpunkt (swConstrainedCornerKeepGeometry). CreateFillet legt selbst ein maßgebendes
        Radiusmaß an (S10 Frage 5): es wird über den Vergleich der Maßnamen vor/nach dem Aufruf gefunden und wie
        jedes Skizzenmaß vorgemerkt, damit es später an den Parameter gebunden wird.
        paar: die beiden Linien der Ecke (Rechteck). Ohne paar werden sie über ecke_uv in linien gesucht – das setzt
        voraus, dass frühere Verrundungen die Ecke nicht verschoben haben (Seitenmittelpunkte tun das, Task 9)."""
        if self.ctx.wert(roh_radius) == 0:
            return
        if paar is None:
            paar = self._linien_an(linien, *self.zu_skizze(*ecke_uv))
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
        self.masse.append(self._eintrag(neu[0], roh_radius, 1, pfad, "radius"))

    def _richtung_zu_u(self, linie, mitte_uv: tuple[float, float], roh_winkel, mitte_punkt, pfad: str | None = None) -> None:
        """Richtung einer Linie zur u-Achse: 0°/90° über Beziehungen, sonst Winkelmaß zu einer u-parallelen
        Hilfslinie durch mitte_uv (Anfang per sgCOINCIDENT an mitte_punkt, den Slot-Mittelpunkt, gebunden, S10 Frage 5).
        pfad: Spec-Pfad des Winkels; die Hilfslinie (Konstruktionslänge) trägt ihn als art "konstruktion"."""
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
        self.groesse(hilfe, (mu_ + _MASS_ABSTAND_MM, mv - _MASS_ABSTAND_MM), 2 * _MASS_ABSTAND_MM, pfad, "konstruktion")
        sw.waehle(self.model, linie, 0)
        sw.waehle(self.model, hilfe, 0, anhaengen=True)
        halb = math.radians(winkel) / 2
        text = (mu_ + 3 * _MASS_ABSTAND_MM * math.cos(halb), mv + 3 * _MASS_ABSTAND_MM * math.sin(halb))
        self._merke(self.model.AddDimension2(*self._text(*text)), roh_winkel, 1, pfad, "winkel")
        sw.auswahl_leeren(self.model)

    def _langloch(self, l: dict, pfad=None) -> None:
        """Langloch (CreateSketchSlot, Mittelpunkt-Typ, Länge Mitte–Mitte): Breite = Abstand der geraden Seiten,
        Länge = Mittellinie, Richtung zu u, Lage der Mitte (S10 Frage 5)."""
        w = self.ctx.wert
        mu_, mv = w(l["mitte"][0]), w(l["mitte"][1])
        laenge, breite = w(l["laenge"]), w(l["breite"])
        winkel = math.radians(w(l.get("winkel", 0)))
        xm, ym = self.zu_skizze(mu_, mv)
        xe, ye = self.zu_skizze(mu_ + laenge / 2 * math.cos(winkel), mv + laenge / 2 * math.sin(winkel))
        # Neue Segmente über Typ + ID (GetSketchSegments liefert nicht in Erzeugungsreihenfolge, AP 6.8)
        def schluessel(s) -> tuple:
            return (s.GetType, tuple(s.GetID))

        vorher = {schluessel(s) for s in self.skizze.GetSketchSegments or ()}
        alte = ({schluessel_element(s, 0) for s in self.skizze.GetSketchSegments or ()}
                | {schluessel_element(p, SW_BEZIEHUNG_PUNKT) for p in self.skizze.GetSketchPoints2 or ()})
        nut = self.sm.CreateSketchSlot(SW_NUT_MITTELPUNKT, SW_NUT_MITTE_MITTE, mm(breite), xm, ym, 0.0, xe, ye, 0.0,
                                       0.0, 0.0, 0.0, SW_GEGEN_UHRZEIGERSINN, False)
        if nut is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "CreateSketchSlot fehlgeschlagen", schritt="skizze")
        # Gefangene Deckungen mit vorhandener Geometrie (z. B. Bogenmitte eines Nachbar-Langlochs auf der Mittellinie)
        # löschen: Lage und Richtung legen die Maße fest, sonst ist die Skizze überbestimmt ("Gleichungen: Code 1").
        verwalter = self.skizze.RelationManager
        for b in fremde_deckungen(verwalter.GetRelations(0) or (), alte):
            if not verwalter.DeleteRelation(b):
                raise BauFehler(SKIZZE_UNGUELTIG, "Langloch: automatische Deckungsbeziehung nicht löschbar",
                                schritt="skizze")
        neu = [s for s in self.skizze.GetSketchSegments or () if schluessel(s) not in vorher]
        seiten = [s for s in neu if s.GetType == SW_SKIZZE_LINIE and not s.ConstructionGeometry]
        achsen = [s for s in neu if s.GetType == SW_SKIZZE_LINIE and s.ConstructionGeometry]
        if len(seiten) != 2 or len(achsen) != 1:
            raise BauFehler(SKIZZE_UNGUELTIG, f"Langloch: {len(seiten)} Seiten, {len(achsen)} Mittellinien",
                            schritt="skizze")
        sw.auswahl_leeren(self.model)
        sw.waehle(self.model, seiten[0], 0)
        sw.waehle(self.model, seiten[1], 0, anhaengen=True)
        self._merke(self.model.AddDimension2(*self._text(mu_, mv + breite / 2 + _MASS_ABSTAND_MM)), l["breite"], 1,
                    feld_pfad(pfad, "langloch", "breite"), "groesse")
        sw.auswahl_leeren(self.model)
        self.groesse(achsen[0], (mu_, mv - breite / 2 - _MASS_ABSTAND_MM), l["laenge"], feld_pfad(pfad, "langloch", "laenge"))
        mitte_punkt = nut.GetCenterPointHandle
        if mitte_punkt is None:
            raise BauFehler(SKIZZE_UNGUELTIG, "Langloch: Mittelpunkt (GetCenterPointHandle) nicht verfügbar", schritt="skizze")
        self._richtung_zu_u(achsen[0], (mu_, mv), l.get("winkel", 0), mitte_punkt, feld_pfad(pfad, "langloch", "winkel"))
        self.kennpunkt((mu_, mv), l["mitte"], bezug_von(l), feld_pfad(pfad, "langloch", "mitte"),
                       f"langloch {laenge:.6g} {breite:.6g}", ziel=_Ziel(punkt=mitte_punkt))

    def _kontur(self, k: dict, pfad=None) -> None:
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

        def festlegen(p_roh, p_pfad, nur: int | None = None) -> None:
            q = (w(p_roh[0]), w(p_roh[1]))
            schluessel = (round(q[0], 6), round(q[1], 6))
            if schluessel in bemasst:
                return
            bemasst.add(schluessel)
            self.kennpunkt(q, p_roh, _NUR_URSPRUNG, p_pfad, "", (0, 1) if nur is None else (nur,))

        segmente = feld_pfad(pfad, "kontur", "segmente")
        for i, s in enumerate(k["segmente"]):
            segment = _index(segmente, i)
            if "bogen" in s:
                festlegen(s["mitte"], None if segment is None else f"{segment}.mitte")
                mitte = (w(s["mitte"][0]), w(s["mitte"][1]))
                festlegen(roh[i + 1], None if segment is None else f"{segment}.bogen",
                          bogenende_koordinate(uv[i + 1], mitte))
            else:
                festlegen(roh[i + 1], None if segment is None else f"{segment}.linie")

    def _linienzug(self, punkte: list[tuple[float, float]]) -> list:
        """Geschlossener Linienzug durch die Skizzenpunkte (m); benachbarte Linien teilen ihre Endpunkte."""
        linien = []
        for (xa, ya), (xb, yb) in zip(punkte, punkte[1:] + punkte[:1]):
            linie = self.sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)
            if linie is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateLine fehlgeschlagen", schritt="skizze")
            linien.append(linie)
        return linien

    def element(self, element: dict, pfad=None) -> None:
        """Ein Skizzenelement anlegen, seine Größen bemaßen und seine Lagen als Kennpunkte vormerken (Verrundungen
        ebenso; beides legt `lagen_festlegen` an). pfad: Spec-Pfad des Elements (z. B. "features[0].skizze.elemente[1]",
        feld_pfad ergänzt Typ und Feld); None bei Notausgang-Skripten."""
        w = self.ctx.wert
        if "rechteck" in element:
            r = element["rechteck"]
            mu_, mv = w(r["mitte"][0]), w(r["mitte"][1])
            b, h = w(r["breite"]), w(r["hoehe"])
            # Vier Linien statt eines Rechteckwerkzeugs: CreateCornerRectangle legt beim Quadrat immer, sonst sporadisch
            # selbst eine Beziehung "gleiche Länge" an (trotz AddToDB, live belegt nach Stufe 4a) – die Skizze wird
            # quadratisch, das zweite Seitenmaß überzählig und seine Gleichung scheitert ("Gleichungen: Code 1").
            # CreateCenterRectangle legte je nach SolidWorks-Zustand keinen Mittelpunkt an.
            ecken = [(mu_ - b / 2, mv - h / 2), (mu_ + b / 2, mv - h / 2), (mu_ + b / 2, mv + h / 2), (mu_ - b / 2, mv + h / 2)]
            seg = self._linienzug([self.zu_skizze(*e) for e in ecken])
            for linie in seg:  # Seiten achsparallel im Skizzensystem: Richtung festlegen wie das Rechteckwerkzeug
                p, q = linie.GetStartPoint2, linie.GetEndPoint2
                sw.auswahl_leeren(self.model)
                sw.waehle(self.model, linie, 0)
                self.model.SketchAddConstraints("sgHORIZONTAL2D" if abs(p.Y - q.Y) < 1e-9 else "sgVERTICAL2D")
            sw.auswahl_leeren(self.model)
            # seg[0] läuft in u, seg[1] in v
            self.groesse(seg[0], (mu_, mv - h / 2 - _MASS_ABSTAND_MM), r["breite"], feld_pfad(pfad, "rechteck", "breite"))
            self.groesse(seg[1], (mu_ - b / 2 - _MASS_ABSTAND_MM, mv), r["hoehe"], feld_pfad(pfad, "rechteck", "hoehe"))
            self._rechteck_lage(r, seg, pfad)
            if "radius" in r:
                # Ecke i ist Ende von seg[i−1] und Anfang von seg[i]: das Linienpaar wählen, nicht die Koordinate
                # (der Seitenmittelpunkt verschiebt das Rechteck zwischen den Verrundungen, Ruling 10)
                for i, (du, dv) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
                    self._verrundungen.append((list(seg), (mu_ + du * b / 2, mv + dv * h / 2), r["radius"],
                                               feld_pfad(pfad, "rechteck", "radius"), (seg[i - 1], seg[i])))
        elif "kreis" in element:
            k = element["kreis"]
            mu_, mv = w(k["mitte"][0]), w(k["mitte"][1])
            d = w(k["durchmesser"])
            x, y = self.zu_skizze(mu_, mv)
            seg = self.sm.CreateCircleByRadius(x, y, 0.0, mm(d / 2))
            if seg is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCircleByRadius fehlgeschlagen", schritt="skizze")
            self.groesse(seg, (mu_ + d / 2 + _MASS_ABSTAND_MM, mv + _MASS_ABSTAND_MM), k["durchmesser"],
                         feld_pfad(pfad, "kreis", "durchmesser"))
            self.kennpunkt((mu_, mv), k["mitte"], bezug_von(k), feld_pfad(pfad, "kreis", "mitte"), f"kreis {d:.6g}")
        elif "polygon" in element:
            p = element["polygon"]
            uv = [(w(q[0]), w(q[1])) for q in p["punkte"]]
            linien = self._linienzug([self.zu_skizze(*q) for q in uv])
            punkte = feld_pfad(pfad, "polygon", "punkte")
            for k, q in enumerate(p["punkte"]):
                self.kennpunkt(uv[k], q, _NUR_URSPRUNG, _index(punkte, k), "")
            if "radien" in p:
                radien = feld_pfad(pfad, "polygon", "radien")
                for k, (ecke, radius) in enumerate(zip(uv, eckradien_roh(p))):
                    self._verrundungen.append((linien, ecke, radius,
                                               _index(radien, k) if isinstance(p["radien"], list) else radien))
        elif "langloch" in element:
            self._langloch(element["langloch"], pfad)
        elif "kontur" in element:
            self._kontur(element["kontur"], pfad)
        else:
            m = element["mittellinie"]
            xa, ya = self.zu_skizze(w(m["von"][0]), w(m["von"][1]))
            xb, yb = self.zu_skizze(w(m["bis"][0]), w(m["bis"][1]))
            if self.sm.CreateCenterLine(xa, ya, 0.0, xb, yb, 0.0) is None:
                raise BauFehler(SKIZZE_UNGUELTIG, "CreateCenterLine fehlgeschlagen", schritt="skizze")
            for feld in ("von", "bis"):
                q = m[feld]
                self.kennpunkt((w(q[0]), w(q[1])), q, _NUR_URSPRUNG, feld_pfad(pfad, "mittellinie", feld), "")


def skizziere(ctx, ebene, elemente: list[dict], name: str, pfade: list | None = None, ebene_pfad: str | None = None,
              hilfslinien: bool = True):
    """Erzeugt eine voll bestimmte Skizze und benennt sie. Rückgabe: (Skizzen-Feature, Skizzenebene).

    Lagen nach ihrem Bezug (Skizzierer.lagen_festlegen, Paare für `mitte` über alle Elemente). Alle Größen- und Lagemaße
    gehen mit ihrem Spec-Pfad ins Maßprotokoll (ctx.mass); per Gleichung an Parameter gebunden werden sie nur mit
    ctx.gleichungen und bei einem Ausdruck.
    pfade[k]: Spec-Pfad des Elements k (z. B. "features[0].skizze.elemente[1]"; bei Bohrungen ein Dict, das Lage und
    Durchmesser zuordnet, siehe feld_pfad); None bei Notausgang-Skripten. ebene_pfad: Spec-Pfad der Ebene.
    hilfslinien=False (Rotation: die Mittellinie der Skizze wird Achse): keine weiteren Konstruktionslinien.
    """
    se = ebene_aufloesen(ctx, ebene, ebene_pfad)
    model, sm = ctx.model, ctx.model.SketchManager
    sw.auswahl_leeren(model)
    sw.waehle(model, se.objekt, 0)
    sm.InsertSketch(True)
    status, masse = None, []
    try:
        skizzierer = Skizzierer(ctx, se, sm.ActiveSketch, hilfslinien)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            for k, element in enumerate(elemente):
                skizzierer.element(element, None if pfade is None else pfade[k])
            skizzierer.lagen_festlegen()
        status, masse = sm.ActiveSketch.GetConstrainedStatus, skizzierer.masse
    finally:
        sm.InsertSketch(True)
    if status != sw.SW_FULLY_CONSTRAINED:
        raise BauFehler(SKIZZE_NICHT_BESTIMMT, f"Skizze {name}: Status {status} statt voll bestimmt", schritt="skizze")
    feature = sw.letztes_feature(model)
    feature.Name = name
    _protokolliere(ctx, masse, name)
    return feature, se


def _protokolliere(ctx, masse: list[_Mass], skizze: str) -> None:
    for m in masse:
        ctx.mass(f"{m.name}@{skizze}", m.roh, m.pfad, m.art, m.vorzeichen, m.bezug, m.wert)


def positionsskizze(feature):
    """Positionsskizze eines Bohrungsassistent-Features: die Unterskizze ohne Skizzensegmente (nur Punkte) –
    Abhängig von S10 Frage 2."""
    unter = feature.GetFirstSubFeature
    while unter is not None:
        if unter.GetTypeName2 == "ProfileFeature" and not (unter.GetSpecificFeature2.GetSketchSegments or ()):
            return unter
        unter = unter.GetNextSubFeature
    raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"{feature.Name}: keine Positionsskizze gefunden", schritt="skizze")


def positionen_festlegen(ctx, feature, se: Skizzenebene, positionen: list, name: str, bezug: dict | None,
                         pfad: str) -> None:
    """Die erste Position steht schon (SelectByRay); weitere als Skizzenpunkte in die Positionsskizze einfügen, alle
    Punkte nach `bezug` (Spec-Feld der Normbohrung, je Achse) bemaßen, die Skizze benennen und die Maße ins Maßprotokoll
    tragen (S10 Frage 2, Rand und Symmetrie in der Positionsskizze: Spike S17 Zeile 4).
    pfad: Spec-Pfad der Positionsliste (z. B. "features[1].positionen"); die Lage von Punkt k trägt "<pfad>[k][a]"."""
    bezug_je_achse = bezug_von({"bezug": bezug})
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
            for k, p in enumerate(positionen):
                skizzierer.kennpunkt((ctx.wert(p[0]), ctx.wert(p[1])), p, bezug_je_achse, _index(pfad, k), "position")
            skizzierer.lagen_festlegen()
        status, masse = sm.ActiveSketch.GetConstrainedStatus, skizzierer.masse
    finally:
        sm.InsertSketch(True)
    if status != sw.SW_FULLY_CONSTRAINED:
        raise BauFehler(SKIZZE_NICHT_BESTIMMT, f"Positionsskizze {name}: Status {status} statt voll bestimmt",
                        schritt="skizze")
    skizze.Name = name
    _protokolliere(ctx, masse, name)


def richtung(se: Skizzenebene, umkehren: bool) -> Vektor:
    return tuple(-c for c in se.normale) if umkehren else se.normale
