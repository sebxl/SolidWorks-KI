"""SolidWorks-Topologie → Flaeche/Kante (swki.compiler.anker) und Auflösung der Anker aus der Spezifikation.

Formate verifiziert in Spike S9a: IFace2.Normal = äußere Normale (nicht PlaneParams verwenden),
CylinderParams = (ox, oy, oz, ax, ay, az, r), LineParams = (px, py, pz, dx, dy, dz),
CircleParams = (cx, cy, cz, ax, ay, az, r), GetClosestPointOn(x, y, z) → 5 Werte, die ersten 3 sind der Punkt.
"""

from swki.compiler.anker import (
    AnkerFehler, Flaeche, Kante, Vektor, differenz, flaeche_in_richtung, laenge, naechste, senkrechte_kanten,
)
from swki.compiler.fehler import REFERENZ_NICHT_GEFUNDEN, BauFehler
from swki.verbindung import in_mm, mm

SW_SOLID_BODY = 0  # swBodyType_e.swSolidBody


def _mm3(werte) -> tuple[float, float, float]:
    return (in_mm(werte[0]), in_mm(werte[1]), in_mm(werte[2]))


def flaeche_aus(face) -> Flaeche:
    s = face.GetSurface
    if s.IsPlane:
        p = s.PlaneParams
        return Flaeche("ebene", _mm3(p[3:6]), normale=tuple(face.Normal), objekt=face)
    if s.IsCylinder:
        c = s.CylinderParams
        return Flaeche("zylinder", _mm3(c[0:3]), achse=tuple(c[3:6]), radius=in_mm(c[6]), objekt=face)
    box = face.GetBox
    mitte = ((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2)
    return Flaeche("sonstige", _mm3(mitte), objekt=face)


def kante_aus(edge) -> Kante:
    c = edge.GetCurve
    start_v, ende_v = edge.GetStartVertex, edge.GetEndVertex
    if c.IsLine:
        lp = c.LineParams
        return Kante("linie", _mm3(start_v.GetPoint), _mm3(ende_v.GetPoint), richtung=tuple(lp[3:6]), objekt=edge)
    if c.IsCircle:
        cp = c.CircleParams
        mitte = _mm3(cp[0:3])
        start = _mm3(start_v.GetPoint) if start_v is not None else mitte
        ende = _mm3(ende_v.GetPoint) if ende_v is not None else mitte
        return Kante("kreis", start, ende, richtung=tuple(cp[3:6]), objekt=edge)
    start = _mm3(start_v.GetPoint) if start_v is not None else (0.0, 0.0, 0.0)
    ende = _mm3(ende_v.GetPoint) if ende_v is not None else start
    return Kante("sonstige", start, ende, objekt=edge)


def flaechen(feature) -> list[Flaeche]:
    return [flaeche_aus(f) for f in (feature.GetFaces or ())]


def _eindeutig(app, edges) -> list:
    eindeutig = []
    for e in edges:
        if not any(app.IsSame(e, x) == 1 for x in eindeutig):  # 1 = swObjectSame
            eindeutig.append(e)
    return eindeutig


def kanten(app, feature) -> list[Kante]:
    edges = [e for f in (feature.GetFaces or ()) for e in (f.GetEdges or ())]
    return [kante_aus(e) for e in _eindeutig(app, edges)]


def koerper(model) -> list:
    """Volumenkörper. Achtung (S9b): IBody2 hat Typinfo – nullargumentige Methoden MIT () aufrufen."""
    return list(model.GetBodies2(SW_SOLID_BODY, False) or ())


def mit_abstand(kandidaten: list, punkt_mm) -> list:
    """Setzt .abstand (mm) jedes Kandidaten zum Punkt über GetClosestPointOn."""
    x, y, z = (mm(v) for v in punkt_mm)
    for k in kandidaten:
        q = k.objekt.GetClosestPointOn(x, y, z)
        k.abstand = laenge((in_mm(q[0]) - punkt_mm[0], in_mm(q[1]) - punkt_mm[1], in_mm(q[2]) - punkt_mm[2]))
    return kandidaten


def loese_flaeche(ctx, anker: dict) -> Flaeche:
    """{feature, flaeche: "+y"} oder {nahe: [x, y, z]} → Flaeche."""
    if "nahe" in anker:
        punkt = tuple(ctx.wert(v) for v in anker["nahe"])
        alle = [flaeche_aus(f) for b in koerper(ctx.model) for f in (b.GetFaces() or ())]
        return naechste(mit_abstand(alle, punkt), ctx.tol_mm, "Fläche")
    feature = ctx.ergebnis(anker["feature"]).features[0]
    return flaeche_in_richtung(flaechen(feature), anker["flaeche"])


def loese_kanten(ctx, anker: dict) -> list[Kante]:
    """{feature, auswahl}, {feature, kanten_an} oder {nahe} → Kanten."""
    if "nahe" in anker:
        punkt = tuple(ctx.wert(v) for v in anker["nahe"])
        alle = [kante_aus(e) for b in koerper(ctx.model) for e in (b.GetEdges() or ())]
        return [naechste(mit_abstand(alle, punkt), ctx.tol_mm, "Kante")]
    ergebnis = ctx.ergebnis(anker["feature"])
    feature = ergebnis.features[0]
    if "kanten_an" in anker:
        flaeche = flaeche_in_richtung(flaechen(feature), anker["kanten_an"])
        return [kante_aus(e) for e in (flaeche.objekt.GetEdges or ())]
    alle = kanten(ctx.app, feature)
    if anker["auswahl"] == "alle_kanten":
        return alle
    if ergebnis.richtung is None:
        raise BauFehler(REFERENZ_NICHT_GEFUNDEN, f"Feature {anker['feature']!r} hat keine Richtung für senkrechte_kanten")
    return senkrechte_kanten(alle, ergebnis.richtung)


REF_ACHSE, REF_EBENE = "RefAxis", "RefPlane"  # IFeature.GetTypeName2 (Spike S11 Frage 2)


def referenz_geometrie(feature) -> tuple[str, Vektor, Vektor]:
    """Bezugsachse → ("achse", Punkt, Richtung); Bezugsebene → ("ebene", Ursprung, Normale). Punkte in mm, Richtungen
    als Einheitsvektoren. Die Normale ist die dritte Zeile der Rotationsmatrix von IRefPlane.Transform (Spike S11)."""
    typ = feature.GetTypeName2
    if typ == REF_ACHSE:
        p = feature.GetSpecificFeature2.GetRefAxisParams
        a, b = _mm3(p[0:3]), _mm3(p[3:6])
        d = differenz(b, a)
        return "achse", a, tuple(c / laenge(d) for c in d)
    if typ == REF_EBENE:
        t = feature.GetSpecificFeature2.Transform.ArrayData
        n = (t[6], t[7], t[8])
        return "ebene", _mm3(t[9:12]), tuple(c / laenge(n) for c in n)
    raise AnkerFehler(REFERENZ_NICHT_GEFUNDEN, f"{feature.Name} ist keine Bezugsachse oder -ebene ({typ})")
