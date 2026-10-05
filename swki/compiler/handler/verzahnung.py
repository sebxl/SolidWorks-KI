"""Handler "verzahnung" (Spec 4b §4.4): Evolventen-Stirnrad oder Zahnstange aus dem berechneten Profil
(swki.verzahnung). Die Skizze enthält die Konturen als Linien, Bögen und Splines durch die berechneten Punkte; alle
Elemente sind fixiert (keine Maße, keine Gleichungen – die Werte schützt die Prüfung gegen die freigegebene Kopie).
Danach Aufsatz um breite, verschmolzen mit vorhandenen Körpern (Spike S14a Zeilen 1, 2).

Ein Stirnrad trägt einen Achspunkt (FeatureErgebnis.punkte): {feature, instanz: 1, achse: true} wählt dann die
koaxiale Zylinderfläche (Fußkreis), wie bei einer Bohrung."""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, SKIZZE_NICHT_BESTIMMT, SKIZZE_UNGUELTIG, BauFehler
from swki.compiler.handler.extrusion import ENDE, aufsatz
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import SW_GEGEN_UHRZEIGERSINN, Skizzierer, ebene_aufloesen, modellpunkt, richtung
from swki.verbindung import callout_leer, dispatch_array, r8_array
from swki.verzahnung import Bogen, Linie, Stirnrad, aus_feature

FIXIERT = "sgFIXED"  # Skizzenbeziehung "Fixieren" (SketchAddConstraints, Spike S14a Zeile 1)
TOL_ABBILDUNG_M = 1e-9  # Gegenprobe der affinen Abbildung (u, v) → Skizze


def affine_abbildung(sk: Skizzierer):
    """Die Abbildung (u, v) → Skizzenkoordinaten (m) ist affin: dreimal kalibrieren statt je Punkt Skizzierer.zu_skizze
    (ca. 4 COM-Aufrufe je Punkt, Spike S14a Nachtrag: ~60 s Skizzenzeit für z 20). Die Gegenprobe vergleicht einen
    weiteren Punkt mit dem COM-Ergebnis."""
    x0, y0 = sk.zu_skizze(0, 0)
    xu, yu = sk.zu_skizze(1, 0)
    xv, yv = sk.zu_skizze(0, 1)
    ux, uy, vx, vy = xu - x0, yu - y0, xv - x0, yv - y0

    def abb(u: float, v: float) -> tuple[float, float]:
        return x0 + u * ux + v * vx, y0 + u * uy + v * vy

    probe, soll = abb(100.0, 37.0), sk.zu_skizze(100.0, 37.0)
    if abs(probe[0] - soll[0]) > TOL_ABBILDUNG_M or abs(probe[1] - soll[1]) > TOL_ABBILDUNG_M:
        raise BauFehler(SKIZZE_UNGUELTIG, f"Abbildung der Profilskizze nicht affin: {probe} statt {soll}", schritt="skizze")
    return abb


def zeichne(sk: Skizzierer, segment, abb):
    """Ein Profilsegment in die offene Skizze (abb: (u, v) → Skizzenkoordinaten); liefert das Skizzensegment oder None."""
    sm = sk.sm
    if isinstance(segment, Linie):
        (xa, ya), (xb, yb) = abb(*segment.a), abb(*segment.b)
        return sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)
    if isinstance(segment, Bogen):
        (xm, ym), (xa, ya), (xb, yb) = (abb(*q) for q in (segment.mitte, segment.a, segment.b))
        drehsinn = SW_GEGEN_UHRZEIGERSINN if segment.gegen_uhrzeigersinn == sk.gleichsinnig else -SW_GEGEN_UHRZEIGERSINN
        return sm.CreateArc(xm, ym, 0.0, xa, ya, 0.0, xb, yb, 0.0, drehsinn)
    werte = [c for q in segment.punkte for c in (*abb(*q), 0.0)]
    return sm.CreateSpline2(r8_array(werte), False)


def profilskizze(ctx, se, konturen: list, name: str):
    """Skizze mit allen Konturen, alle Elemente fixiert; BauFehler, wenn ein Segment fehlt oder die Skizze nicht voll
    bestimmt ist. Rückgabe: Skizzen-Feature (benannt)."""
    model, sm = ctx.model, ctx.model.SketchManager
    sw.auswahl_leeren(model)
    sw.waehle(model, se.objekt, 0)
    sm.InsertSketch(True)
    status = None
    try:
        sk = Skizzierer(ctx, se, sm.ActiveSketch)
        abb = affine_abbildung(sk)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            for k, kontur in enumerate(konturen, start=1):
                for i, segment in enumerate(kontur, start=1):
                    if zeichne(sk, segment, abb) is None:
                        raise BauFehler(SKIZZE_UNGUELTIG, f"{name}: Kontur {k}, Segment {i} nicht erzeugt", schritt="skizze")
            sw.auswahl_leeren(model)
            segmente = list(sm.ActiveSketch.GetSketchSegments or ())
            # Alle Segmente in einem Aufruf wählen (Spike S14a Nachtrag, Variante 4: eine Schleife von waehle kostet Zeit)
            gewaehlt = model.Extension.MultiSelect2(dispatch_array(segmente), False, callout_leer())
            if gewaehlt != len(segmente):
                raise BauFehler(SKIZZE_UNGUELTIG, f"{name}: {gewaehlt} von {len(segmente)} Segmenten gewählt",
                                schritt="skizze")
            model.SketchAddConstraints(FIXIERT)
            sw.auswahl_leeren(model)
        status = sm.ActiveSketch.GetConstrainedStatus
    finally:
        sm.InsertSketch(True)
    if status != sw.SW_FULLY_CONSTRAINED:
        raise BauFehler(SKIZZE_NICHT_BESTIMMT, f"Skizze {name}: Status {status} statt voll bestimmt", schritt="skizze")
    skizze = sw.letztes_feature(model)
    skizze.Name = name
    return skizze


@handler("verzahnung")
def verzahnung(ctx, f: dict) -> FeatureErgebnis:
    geo = aus_feature(f, ctx.spec.get("parameter", {}))
    mitte = (ctx.wert(f["mitte"][0]), ctx.wert(f["mitte"][1]))
    if isinstance(geo, Stirnrad):
        konturen = geo.profil(mitte, ctx.wert(f.get("winkel", 0)))
    else:
        konturen = geo.profil(mitte, f.get("kopf", "+v"))
    se = ebene_aufloesen(ctx, f["ebene"])
    skizze = profilskizze(ctx, se, konturen, f"{f['id']}_skizze")
    umkehren = bool(f.get("umkehren", False))
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)
    feature = aufsatz(ctx.model, ENDE["blind"], ctx.m(f["breite"]), umkehren)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"verzahnung {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    ctx.verknuepfe(f"D1@{f['id']}", f["breite"])
    punkte = [modellpunkt(se.orientierung, *mitte, se.lage)] if isinstance(geo, Stirnrad) else []
    return FeatureErgebnis([feature], richtung=richtung(se, umkehren), punkte=punkte)
