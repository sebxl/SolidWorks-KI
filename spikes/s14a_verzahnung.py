"""S14a (Stufe 4b, Etappe 1): Evolventenverzahnung im Teil – Skizze aus berechneten Punkten, Messung, Zeit, Speicher.

1 Profil eines Stirnrads (m 2, z 20) als Splines (CreateSpline2) bzw. als Polylinie, alle Elemente fixiert (sgFIXED):
  Skizzenstatus, Segmente, Aufsatz, Flächen; Abweichung der Flankenfläche von der Soll-Evolvente (GetClosestPointOn an
  Sollpunkten der rechten Flanke von Zahn 1, mittlere Breite); Zeit.
2 Ganzes Profil (Splines) für z = 17, 25, 50, 80: Zeit für Skizze und Aufsatz, Flächen, Private Bytes vorher/nachher.
3 Messung am Rad z 20: koaxiale Zylinder (Radien, Anzahl), Flanken über die Mitte der Box, IMeasure-Abstand der
  Außenflanken über k Zähne gegen W_k; Zahnstange (z 5 auf Rücken): Kopfflächen, Flankenebenen, Teilung, Zahndicke.
4 Achse: zylinder_zu_punkten(Flächen des Features, [Achspunkt]) findet eine koaxiale Zylinderfläche.
5 Zahnstange als Zahnband (eine Kontur je Zahn) auf einem Rücken bis zur Fußlinie: ein Volumenkörper.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s14a_verzahnung
"""

import math
import time

from spikes._gemeinsam import lauf
from swki.compiler import sw
from swki.compiler.anker import punkt_achse_abstand, skalar, zylinder_zu_punkten
from swki.compiler.bauen import baue_teil_dokument
from swki.compiler.fehler import BauFehler
from swki.compiler.handler.extrusion import ENDE, aufsatz
from swki.compiler.protokoll import Protokoll
from swki.compiler.skizze import SW_GEGEN_UHRZEIGERSINN, Skizzierer, ebene_aufloesen, modellpunkt
from swki.compiler.topologie import flaechen, koerper
from swki.konfig import lade_rechner, lade_standard
from swki.speicher import privat_mb
from swki.verbindung import callout_leer, in_mm, mm, r8_array, verbinde
from swki.verzahnung import ALPHA, Bogen, Linie, Spline, Stirnrad, Zahnstange

AUFTRAG = "S14A"


def _privat_mb(app) -> float:
    return privat_mb(int(app.GetProcessID))


def _welle(name: str, laenge: float) -> dict:
    return {"art": "teil", "name": name, "material": "1.0503", "eigenschaften": {"Benennung": name},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "vorne", "elemente": [{"kreis": {"mitte": [0, 0], "durchmesser": 12}}]},
                          "ende": {"typ": "blind", "tiefe": laenge}}]}


def _ruecken(st: Zahnstange, breite: float) -> dict:
    return {"art": "teil", "name": "S14a_Stange", "material": "1.0503", "eigenschaften": {"Benennung": "Stange"},
            "features": [{"id": "f1", "typ": "extrusion",
                          "skizze": {"ebene": "vorne", "elemente": [{"rechteck": {
                              "mitte": [(st.z - 1) * st.p / 2, -1.25 * st.m - 5], "breite": st.z * st.p, "hoehe": 10}}]},
                          "ende": {"typ": "blind", "tiefe": breite}}]}


def _zeichne(sk, segment, polylinie: bool) -> list:
    sm = sk.sm
    if isinstance(segment, Linie):
        (xa, ya), (xb, yb) = sk.zu_skizze(*segment.a), sk.zu_skizze(*segment.b)
        return [sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0)]
    if isinstance(segment, Bogen):
        (xm, ym), (xa, ya), (xb, yb) = (sk.zu_skizze(*q) for q in (segment.mitte, segment.a, segment.b))
        drehsinn = SW_GEGEN_UHRZEIGERSINN if segment.gegen_uhrzeigersinn == sk.gleichsinnig else -SW_GEGEN_UHRZEIGERSINN
        return [sm.CreateArc(xm, ym, 0.0, xa, ya, 0.0, xb, yb, 0.0, drehsinn)]
    punkte = [sk.zu_skizze(*q) for q in segment.punkte]
    if polylinie:
        return [sm.CreateLine(xa, ya, 0.0, xb, yb, 0.0) for (xa, ya), (xb, yb) in zip(punkte, punkte[1:])]
    return [sm.CreateSpline2(r8_array([c for x, y in punkte for c in (x, y, 0.0)]), False)]


def _verzahnung(ctx, ebene, konturen, breite: float, name: str, polylinie: bool = False) -> dict:
    """Skizze mit fixierten Elementen und Aufsatz (wie der spätere Handler); liefert Messwerte und das Feature."""
    e = {}
    se = ebene_aufloesen(ctx, ebene)
    model, sm = ctx.model, ctx.model.SketchManager
    beginn = time.perf_counter()
    sw.auswahl_leeren(model)
    sw.waehle(model, se.objekt, 0)
    sm.InsertSketch(True)
    try:
        sk = Skizzierer(ctx, se, sm.ActiveSketch)
        with sw.einstellung(ctx.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False), sw.ohne_inferenz(sm):
            erzeugt = [s for k in konturen for seg in k for s in _zeichne(sk, seg, polylinie)]
            e["segmente_none"] = sum(1 for s in erzeugt if s is None)
            segmente = list(sm.ActiveSketch.GetSketchSegments or ())
            e["segmente"] = len(segmente)
            e["punkte"] = len(sm.ActiveSketch.GetSketchPoints2 or ())
            sw.auswahl_leeren(model)
            for s in segmente:
                sw.waehle(model, s, 0, anhaengen=True)
            model.SketchAddConstraints("sgFIXED")
            sw.auswahl_leeren(model)
        e["status"] = sm.ActiveSketch.GetConstrainedStatus
    finally:
        sm.InsertSketch(True)
    e["s_skizze"] = round(time.perf_counter() - beginn, 3)
    skizze = sw.letztes_feature(model)
    skizze.Name = f"{name}_skizze"
    sw.auswahl_leeren(model)
    skizze.Select2(False, 0)
    beginn = time.perf_counter()
    feature = aufsatz(model, ENDE["blind"], mm(breite), False)
    e["aufsatz"] = feature is not None
    try:
        sw.rebuild(model)
        e["rebuild"] = "ok"
    except BauFehler as ex:
        e["rebuild"] = str(ex)
    e["s_aufsatz"] = round(time.perf_counter() - beginn, 3)
    if feature is not None:
        feature.Name = name
        e["flaechen"] = len(flaechen(feature))
        e["koerper"] = len(koerper(model))
    return e, feature, se


def _flanken(faces) -> list:
    """Flankenflächen: Splineflächen ("sonstige"); bei der Polylinie ebene Facetten quer zur Radachse (Korrektur)."""
    return [f for f in faces if f.art == "sonstige" or (f.art == "ebene" and abs(f.normale[2]) < 0.5)]


def _abweichung(rad: Stirnrad, se, feature, lage_z: float) -> dict:
    """Abstand von 40 Sollpunkten der rechten Flanke von Zahn 1 (mittlere Breite) zur nächsten Fläche des Features."""
    rho = [rad.r_start + (rad.ra - rad.r_start) * (i + 0.5) / 40 for i in range(40)]
    sonstige = _flanken(flaechen(feature))  # Korrektur: bei der Polylinie ebene Facetten
    werte = []
    for r in rho:
        u, v = rad.flankenpunkt(1, "rechts", r)
        p = modellpunkt(se.orientierung, u, v, lage_z)
        best = None
        for f in sonstige:
            q = f.objekt.GetClosestPointOn(mm(p[0]), mm(p[1]), mm(p[2]))
            d = math.dist(p, tuple(in_mm(c) for c in q[:3]))
            best = d if best is None else min(best, d)
        werte.append(best)
    return {"max_mm": round(max(werte), 6), "mittel_mm": round(sum(werte) / len(werte), 6), "flankenflaechen": len(sonstige)}


def _messe_rad(model, rad: Stirnrad, feature, achse_punkt, normale) -> dict:
    faces = flaechen(feature)
    koax = [f for f in faces if f.art == "zylinder" and abs(skalar(f.achse, normale)) > 1 - 1e-6
            and punkt_achse_abstand(achse_punkt, f.punkt, f.achse) <= 0.1]
    radien = sorted({round(f.radius, 4) for f in koax})
    e = {"radien": radien, "anzahl_je_radius": {r: sum(1 for f in koax if abs(f.radius - r) < 1e-3) for r in radien},
         "arten": {a: sum(1 for f in faces if f.art == a) for a in ("ebene", "zylinder", "sonstige")}}
    k, rho = rad.messzaehnezahl(), (rad.r_start + rad.ra) / 2
    sonstige = _flanken(faces)  # Korrektur: bei der Polylinie ebene Facetten

    def flanke(j, seite):
        u, v = rad.flankenpunkt(j, seite, rho)
        p = (u, v, achse_punkt[2])
        return min(sonstige, key=lambda f: math.hypot(f.punkt[0] - p[0], f.punkt[1] - p[1]))

    rechts, links = flanke(1, "rechts"), flanke(k, "links")
    sw.auswahl_leeren(model)
    sw.waehle(model, rechts.objekt, 0)
    sw.waehle(model, links.objekt, 0, anhaengen=True)
    messung = model.Extension.CreateMeasure
    messung._FlagAsMethod("Calculate")  # Korrektur: mit Argument sonst Attributzugriff (pywin32-fallstricke, S9b-19)
    e["calculate"] = bool(messung.Calculate(callout_leer()))
    e["zahnweite_ist"] = round(in_mm(messung.Distance), 6)
    e["zahnweite_soll"] = round(rad.zahnweite(), 6)
    e["k"] = k
    sw.auswahl_leeren(model)
    e["achse_zylinder_radius"] = round(zylinder_zu_punkten(faces, [achse_punkt], 0.1)[0].radius, 4)
    return e


def _messe_stange(st: Zahnstange, feature) -> dict:
    faces = flaechen(feature)
    kopf = [f for f in faces if f.art == "ebene" and f.normale[1] > 1 - 1e-6]
    links_n = (-math.cos(ALPHA), math.sin(ALPHA), 0.0)
    rechts_n = (math.cos(ALPHA), math.sin(ALPHA), 0.0)

    def u_bei_v0(f):
        return skalar(f.punkt, f.normale) / f.normale[0]

    links = sorted(u_bei_v0(f) for f in faces if f.art == "ebene" and skalar(f.normale, links_n) > 1 - 1e-6)
    rechts = sorted(u_bei_v0(f) for f in faces if f.art == "ebene" and skalar(f.normale, rechts_n) > 1 - 1e-6)
    return {"kopfflaechen": len(kopf), "kopf_y": sorted({round(f.punkt[1], 4) for f in kopf}),
            "teilung": [round(b - a, 5) for a, b in zip(links, links[1:])], "teilung_soll": round(st.p, 5),
            "zahndicke": [round(b - a, 5) for a, b in zip(links, rechts)], "zahndicke_soll": round(st.s, 5)}


def _rad(app, r, standard, z: int, polylinie: bool = False) -> dict:
    spec = _welle(f"S14a_z{z}{'_poly' if polylinie else ''}", 10)
    model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, r.arbeitsordner / AUFTRAG / "w.yaml", AUFTRAG,
                                            Protokoll(AUFTRAG, "w.yaml", 0, r.sw_jahr))
    try:
        if fehler is not None:
            raise fehler
        rad = Stirnrad(2.0, z, -0.05)
        vorher = _privat_mb(app)
        ebene = {"versatz": {"ebene": "vorne", "abstand": 10}}
        e, feature, se = _verzahnung(ctx, ebene, rad.profil(), 16, "z1", polylinie)
        e["privat_mb"] = [vorher, _privat_mb(app)]
        if feature is not None and z == 20:
            e["abweichung"] = _abweichung(rad, se, feature, 18.0)
            e["messung"] = _messe_rad(model, rad, feature, (0.0, 0.0, 10.0), (0.0, 0.0, 1.0))
        return e
    finally:
        sw.schliesse(app, model)


def _stange(app, r, standard) -> dict:
    st = Zahnstange(2.0, 5, -0.05)
    spec = _ruecken(st, 20)
    model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, r.arbeitsordner / AUFTRAG / "s.yaml", AUFTRAG,
                                            Protokoll(AUFTRAG, "s.yaml", 0, r.sw_jahr))
    try:
        if fehler is not None:
            raise fehler
        e, feature, _ = _verzahnung(ctx, "vorne", st.profil(), 20, "z1")
        if feature is not None:
            e["messung"] = _messe_stange(st, feature)
        return e
    finally:
        sw.schliesse(app, model)


def _naechste_flaeche(flanken, p):
    """Flanke mit dem kleinsten echten Abstand (GetClosestPointOn) zum Sollpunkt p (mm); liefert (Fläche, Abstand)."""
    def abstand(f):
        q = f.objekt.GetClosestPointOn(mm(p[0]), mm(p[1]), mm(p[2]))
        return math.dist(p, tuple(in_mm(c) for c in q[:3]))
    return min(((f, abstand(f)) for f in flanken), key=lambda t: t[1])


def _nachmessung() -> dict:
    """Nachmessung (Korrektur nach Lauf 3): Zahnweite des Splinerads z 20 mit Flankenwahl über den echten Abstand
    statt über die Boxmitte (Boxmitten benachbarter Flanken liegen ähnlich nah am Sollpunkt)."""
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    spec = _welle("S14a_z20_nach", 10)
    model, ctx, fehler = baue_teil_dokument(app, r, standard, spec, r.arbeitsordner / AUFTRAG / "n.yaml", AUFTRAG,
                                            Protokoll(AUFTRAG, "n.yaml", 0, r.sw_jahr))
    try:
        if fehler is not None:
            raise fehler
        rad = Stirnrad(2.0, 20, -0.05)
        e = {"privat_mb_vorher": _privat_mb(app)}
        ebene = {"versatz": {"ebene": "vorne", "abstand": 10}}
        mess, feature, se = _verzahnung(ctx, ebene, rad.profil(), 16, "z1")
        e.update({k: mess[k] for k in ("status", "koerper", "s_skizze", "s_aufsatz")})
        flanken = _flanken(flaechen(feature))
        k, rho = rad.messzaehnezahl(), (rad.r_start + rad.ra) / 2
        e["k"] = k
        messwerte = {}
        for j, seite in ((1, "rechts"), (k, "links"), (1, "links"), (k, "rechts")):
            u, v = rad.flankenpunkt(j, seite, rho)
            f, d = _naechste_flaeche(flanken, modellpunkt(se.orientierung, u, v, 18.0))
            messwerte[f"{j}{seite}"] = (f, d)
        e["flankenabstand_mm"] = {n: round(d, 6) for n, (f, d) in messwerte.items()}
        for name, (a, b) in {"aussen_1rechts_klinks": ("1rechts", f"{k}links"),
                             "innen_1links_krechts": ("1links", f"{k}rechts")}.items():
            sw.auswahl_leeren(model)
            sw.waehle(model, messwerte[a][0].objekt, 0)
            sw.waehle(model, messwerte[b][0].objekt, 0, anhaengen=True)
            messung = model.Extension.CreateMeasure
            messung._FlagAsMethod("Calculate")
            ok = bool(messung.Calculate(callout_leer()))
            e[name] = {"calculate": ok, "abstand_mm": round(in_mm(messung.Distance), 6)}
        sw.auswahl_leeren(model)
        e["zahnweite_soll"] = round(rad.zahnweite(), 6)
        e["privat_mb_nachher"] = _privat_mb(app)
        return e
    finally:
        sw.schliesse(app, model)


def _untersuche() -> dict:
    r, standard = lade_rechner(), lade_standard()
    app = verbinde(r.sw_jahr)
    ergebnis = {"privat_mb_start": _privat_mb(app)}
    ergebnis["1_spline_z20"] = _rad(app, r, standard, 20)
    ergebnis["1_polylinie_z20"] = _rad(app, r, standard, 20, polylinie=True)
    ergebnis["2_ganzes_profil"] = {z: _rad(app, r, standard, z) for z in (17, 25, 50, 80)}
    ergebnis["5_zahnstange"] = _stange(app, r, standard)
    ergebnis["privat_mb_ende"] = _privat_mb(app)
    return ergebnis


if __name__ == "__main__":
    import sys
    if "nachmessung" in sys.argv[1:]:
        lauf("s14a_verzahnung_nachmessung", _nachmessung)
    else:
        lauf("s14a_verzahnung", _untersuche)
