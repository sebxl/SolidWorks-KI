"""Referenzen einer Verknüpfung im Teil auflösen (Spec 3b §4.3): Geometrie im Teildokument finden. Die Übertragung in
den Baugruppenkontext übernimmt swki.baugruppe.sw_baugruppe.in_baugruppe."""

from dataclasses import dataclass

from swki.compiler import sw
from swki.compiler.anker import RICHTUNGEN, AnkerFehler, Flaeche, laenge, skalar, zylinder_zu_punkten
from swki.compiler.fehler import REFERENZ_MEHRDEUTIG, REFERENZ_NICHT_GEFUNDEN
from swki.compiler.skizze import STANDARD
from swki.compiler.topologie import flaechen, kante_aus, loese_flaeche, mit_abstand, referenz_geometrie
from swki.pruefung.geometrie import Messgeometrie
from swki.verzahnung import verzahnung_im_teil

_PARALLEL = 1.0 - 1e-6
_GLEICH_MM = 1e-4
NORMALE = {"vorne": (0.0, 0.0, 1.0), "oben": (0.0, 1.0, 0.0), "rechts": (1.0, 0.0, 0.0)}


@dataclass
class TeilReferenz:
    objekt: object             # IFace2 oder IFeature im Teildokument
    geometrie: Messgeometrie   # in Teilkoordinaten (mm)
    ist_feature: bool          # Bezugs-/Standardebene oder -achse: Auswahl über IComponent2.FeatureByName


def _einheit(v) -> tuple[float, float, float]:
    n = laenge(v)
    return tuple(c / n for c in v)


def _geometrie(f: Flaeche) -> Messgeometrie:
    if f.art == "ebene":
        return Messgeometrie("ebene", f.punkt, f.normale)
    if f.art == "zylinder":
        return Messgeometrie("achse", f.punkt, _einheit(f.achse))
    raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, "Fläche ist weder eben noch zylindrisch")


def flaeche_der_instanz(kandidaten: list[Flaeche], richtung: str) -> Flaeche:
    """Ebene Fläche mit Normale `richtung`, die der Bohrungsposition am nächsten liegt (abstand von mit_abstand), z. B.
    der Senkungsgrund genau dieser Instanz."""
    vek = RICHTUNGEN[richtung]
    passend = sorted((f for f in kandidaten if f.art == "ebene" and f.normale and skalar(f.normale, vek) > _PARALLEL),
                     key=lambda f: f.abstand)
    if not passend:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"keine ebene Fläche mit Normale {richtung} an der Bohrung")
    if len(passend) > 1 and passend[1].abstand - passend[0].abstand < _GLEICH_MM:
        raise AnkerFehler(REFERENZ_MEHRDEUTIG, f"{len(passend)} Flächen mit Normale {richtung} gleich nah an der Bohrung")
    return passend[0]


def _bohrung(ctx, fid: str, instanz: int):
    if fid not in ctx.ergebnisse:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Feature {fid!r} fehlt im Teil")
    ergebnis = ctx.ergebnis(fid)
    if instanz > len(ergebnis.punkte):
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Bohrung {fid} hat nur {len(ergebnis.punkte)} Instanzen")
    return ergebnis.features[0], ergebnis.punkte[instanz - 1]


def kopplung_referenz(ctx, fid: str) -> TeilReferenz:
    """Entität einer Kopplungsseite im Teil (Spec 4b §5.4.3; Spike S14b Zeile 6): Stirnrad – koaxiale Zylinderfläche
    (wie die Radachse {feature, instanz: 1, achse: true}); Zahnstange – gerade Kante einer Kopffläche entlang der
    Zahnreihe."""
    f = next(x for x in ctx.spec["features"] if x["id"] == fid)
    if f["art"] == "stirnrad":
        return loese_im_teil(ctx, {"feature": fid, "instanz": 1, "achse": True})
    if fid not in ctx.ergebnisse:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Feature {fid!r} fehlt im Teil")
    vz = verzahnung_im_teil(f, ctx.spec.get("parameter", {}))
    for kopf in flaechen(ctx.ergebnis(fid).features[0]):
        if kopf.art != "ebene" or skalar(kopf.normale, vz.kopfrichtung) <= _PARALLEL:
            continue
        for e in kopf.objekt.GetEdges or ():
            k = kante_aus(e)
            if k.art == "linie" and abs(skalar(k.richtung, vz.u)) > _PARALLEL:
                return TeilReferenz(e, Messgeometrie("achse", k.start, vz.u), False)
    raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"{fid}: keine Kante entlang der Zahnreihe")


def loese_im_teil(ctx, seite: dict) -> TeilReferenz:
    """seite ohne "komponente": {referenz} | {ebene} | {nahe} | {feature, instanz, achse} | {feature, instanz, flaeche} |
    {feature, flaeche}. ctx ist der Kontext des Teildokuments (Bau: Features des Laufs; Normteil: aus der Datei)."""
    if "referenz" in seite:
        if seite["referenz"] not in ctx.ergebnisse:
            raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Referenz {seite['referenz']!r} fehlt im Teil")
        feature = ctx.ergebnis(seite["referenz"]).features[0]
        return TeilReferenz(feature, Messgeometrie(*referenz_geometrie(feature)), True)
    if "ebene" in seite:
        feature = sw.standardebenen(ctx.model)[STANDARD[seite["ebene"]]]
        return TeilReferenz(feature, Messgeometrie("ebene", (0.0, 0.0, 0.0), NORMALE[seite["ebene"]]), True)
    if "nahe" in seite:
        f = loese_flaeche(ctx, {"nahe": seite["nahe"]})
        return TeilReferenz(f.objekt, _geometrie(f), False)
    if "instanz" in seite:
        feature, punkt = _bohrung(ctx, seite["feature"], seite["instanz"])
        if seite.get("achse"):
            [zylinder] = zylinder_zu_punkten(flaechen(feature), [punkt], ctx.tol_mm)
            return TeilReferenz(zylinder.objekt, _geometrie(zylinder), False)
        eben = mit_abstand([f for f in flaechen(feature) if f.art == "ebene"], punkt)
        f = flaeche_der_instanz(eben, seite["flaeche"])
        return TeilReferenz(f.objekt, _geometrie(f), False)
    if seite["feature"] not in ctx.ergebnisse:
        raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"Feature {seite['feature']!r} fehlt im Teil")
    f = loese_flaeche(ctx, {"feature": seite["feature"], "flaeche": seite["flaeche"]})
    return TeilReferenz(f.objekt, _geometrie(f), False)
