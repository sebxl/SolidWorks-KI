"""Messwerte eines gespeicherten Laufs aus SolidWorks lesen (Spike S9b, Bausteine 19 und 23)."""

import math
from dataclasses import replace
from pathlib import Path

from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.anker import (AnkerFehler, Flaeche, flaeche_in_richtung, laenge, punkt_achse_abstand, skalar,
                                 zylinder_durch_punkt, zylinder_zu_punkten)
from swki.compiler.eigenschaften import lies_eigenschaften
from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import FeatureErgebnis, Kontext
from swki.compiler.topologie import flaechen, koerper, loese_flaeche, referenz_geometrie
from swki.formschraege import TYPEN, extrusionsrichtung, schraege, seitenflaechen, skizzennormale
from swki.pruefung.bewertung import Messwerte, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from swki.spec.normen import SW_BEFESTIGUNG
from swki.verbindung import byref_long, byref_str, in_mm, in_mm3, mm, r8_array
from swki.verzahnung import ALPHA, Stirnrad, Verzahnung, verzahnung_im_teil

SW_DOC_PART = 1  # swDocumentTypes_e
SW_DOC_ASSEMBLY = 2
SW_OPEN_SILENT = 1  # swOpenDocOptions_e
SW_WARNUNG_BEREITS_OFFEN = 128  # swFileLoadWarning_AlreadyOpen


class PruefFehler(SwkiFehler):
    pass


def oeffne(app, pfad: Path):
    """Öffnet ein gespeichertes Teil oder eine Baugruppe (Typ nach der Endung). Ist das Dokument schon offen (evtl. beim
    Nutzer), wird abgebrochen statt es zu schließen."""
    typ = SW_DOC_ASSEMBLY if pfad.suffix.lower() == ".sldasm" else SW_DOC_PART
    fehler, warnungen = byref_long(), byref_long()
    model = app.OpenDoc6(str(pfad), typ, SW_OPEN_SILENT, "", fehler, warnungen)
    if model is None:
        raise PruefFehler(f"{pfad.name} ließ sich nicht öffnen (Fehler {fehler.value})")
    if warnungen.value & SW_WARNUNG_BEREITS_OFFEN:
        raise PruefFehler(f"{pfad.name} ist bereits in SolidWorks geöffnet – bitte schließen und erneut prüfen")
    return model


def skizzenstatus(model) -> dict[str, int]:
    """Bestimmtheitsstatus aller Skizzen. Von Features aufgenommene Skizzen heißen "<Feature>/<Skizze>",
    damit ein Mangel dem Knoten der Spezifikation zugeordnet werden kann (z. B. "f10/Skizze7")."""
    status = {}
    f = model.FirstFeature
    while f is not None:
        if f.GetTypeName2 == "ProfileFeature":
            status[f.Name] = f.GetSpecificFeature2.GetConstrainedStatus
        unter = f.GetFirstSubFeature
        while unter is not None:
            if unter.GetTypeName2 == "ProfileFeature":
                status[f"{f.Name}/{unter.Name}"] = unter.GetSpecificFeature2.GetConstrainedStatus
            unter = unter.GetNextSubFeature
        f = f.GetNextFeature
    return status


def rebuild_fehler(model) -> list[str]:
    try:
        sw.rebuild(model)
    except BauFehler as e:
        return [t.strip() for t in str(e).split(";")]
    return []


def lies_normbohrung(feature) -> dict:
    """Bohrungsassistent-Daten eines Features (IFeature.GetDefinition → IWizardHoleFeatureData2, beides ohne "()";
    Längen in mm). Spike S10, Frage 4: Type ist swWzdHoleTypes_e (Art und Ende zusammen), Depth liest immer 0; die Bohrungstiefe
    steht beim Gewinde in TapDrillDepth, sonst in HoleDepth."""
    d = feature.GetDefinition
    befestigung = d.FastenerType2
    tiefe = d.TapDrillDepth if befestigung == SW_BEFESTIGUNG["gewinde"] else d.HoleDepth
    return {
        "typ": d.Type, "befestigung": befestigung, "norm": d.Standard2, "groesse": d.FastenerSize,
        "ende": d.EndCondition, "tiefe": round(in_mm(tiefe), 6), "gewindetiefe": round(in_mm(d.ThreadDepth), 6),
        "positionen": d.GetSketchPointCount,
    }


def normbohrungen(model, soll_spec: dict) -> dict[str, dict | str]:
    """Für jeden normbohrung-Knoten der Soll-Spezifikation die Daten des gleichnamigen Features oder einen Fehlertext."""
    ergebnis = {}
    for f in soll_spec["features"]:
        if f["typ"] != "normbohrung":
            continue
        feature = model.FeatureByName(f["id"])
        if feature is None:
            ergebnis[f["id"]] = f"Feature {f['id']} fehlt im Teil"
        elif feature.GetTypeName2 != "HoleWzd":
            ergebnis[f["id"]] = f"Feature {f['id']} ist {feature.GetTypeName2}, kein Bohrungsassistent"
        else:
            try:
                ergebnis[f["id"]] = lies_normbohrung(feature)
            except Exception as e:  # COM-Fehler beim Lesen → Mangel statt Abbruch der Prüfung
                ergebnis[f["id"]] = f"Bohrungsassistent-Daten von {f['id']} nicht lesbar: {e}"
    return ergebnis


_PARALLEL = 1.0 - 1e-6


def _in_ebene(d, normale) -> float:
    """Länge des Anteils von d senkrecht zu normale."""
    t = skalar(d, normale)
    return laenge(tuple(d[i] - t * normale[i] for i in range(3)))


def waehle_flanke(kandidaten: list[Flaeche], erwartet, normale, tol_mm: float) -> Flaeche:
    """Die Fläche, deren Mittelpunkt (Flaeche.punkt, Mitte der Box) senkrecht zur Radachse dem erwarteten Flankenpunkt
    am nächsten liegt; AnkerFehler, wenn keine innerhalb tol_mm liegt (Spike S14a Zeile 3)."""
    if not kandidaten:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", "keine Flankenflächen")
    beste = min(kandidaten, key=lambda f: _in_ebene(tuple(f.punkt[i] - erwartet[i] for i in range(3)), normale))
    abstand = _in_ebene(tuple(beste.punkt[i] - erwartet[i] for i in range(3)), normale)
    if abstand > tol_mm:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"keine Flanke innerhalb {tol_mm:g} mm (nächste {abstand:.3f} mm)")
    return beste


def _projiziere(mu, flaeche: Flaeche, start, richtung):
    """Punkt start (mm) entlang richtung (Einheitsvektor) auf die Fläche projizieren (IFace2.GetProjectedPointOn);
    mm-Tupel oder None, wenn die Fläche nicht getroffen wird."""
    p = mu.CreatePoint(r8_array([mm(c) for c in start]))
    v = mu.CreateVector(r8_array(richtung))
    try:
        flaeche.objekt._FlagAsMethod("GetProjectedPointOn")
    except AttributeError:
        pass
    treffer = flaeche.objekt.GetProjectedPointOn(p, v)
    if treffer is None:
        return None
    werte = getattr(treffer, "ArrayData", treffer)
    return tuple(in_mm(c) for c in werte[:3])


def _zahnweite(mu, vz: Verzahnung, rechts: Flaeche, links: Flaeche) -> float:
    """Zahnweite W_k (mm): Abstand der Treffpunkte eines Strahls entlang der Grundkreistangente auf der rechten
    Außenflanke von Zahn 1 und der linken von Zahn k, in der Radebene auf halber Zahnbreite (Spike S14a Nachtrag B;
    IMeasure zwischen den Flanken liefert dagegen nur den Mindestabstand an den Flankenenden)."""
    rad: Stirnrad = vz.geo
    k = rad.messzaehnezahl()
    phi = math.radians(vz.winkel + (k - 1) * 180.0 / rad.z)  # Spannmitte
    em, ep = (math.cos(phi), math.sin(phi)), (-math.sin(phi), math.cos(phi))
    hoehe = (vz.breite[0] + vz.breite[1]) / 2 - skalar(vz.ursprung, vz.normale)  # Radebene auf halber Zahnbreite
    weit = rad.ra + 5.0

    def treffer(flaeche: Flaeche, name: str) -> tuple:
        for seite in (1, -1):  # Startpunkt außerhalb bei t = seite·(r_a + 5), Strahl zur Tangente hin
            q = (vz.mitte[0] + rad.rb * em[0] + seite * weit * ep[0], vz.mitte[1] + rad.rb * em[1] + seite * weit * ep[1])
            start = tuple(vz.modell(q)[i] + hoehe * vz.normale[i] for i in range(3))
            p = _projiziere(mu, flaeche, start, vz.richtung((-seite * ep[0], -seite * ep[1])))
            if p is not None:
                return p
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Strahl entlang der Grundkreistangente trifft die {name} nicht")

    a, b = treffer(rechts, "rechte Flanke von Zahn 1"), treffer(links, f"linke Flanke von Zahn {k}")
    return round(math.dist(a, b), 6)


def _stirnrad(mu, vz: Verzahnung, faces: list[Flaeche], tol_mm: float) -> dict:
    rad: Stirnrad = vz.geo
    achse = vz.bezugspunkt
    koaxial = [f for f in faces if f.art == "zylinder" and abs(skalar(f.achse, vz.normale)) / laenge(f.achse) > _PARALLEL
               and punkt_achse_abstand(achse, f.punkt, tuple(c / laenge(f.achse) for c in f.achse)) <= tol_mm]
    if not koaxial:
        return {"art": "stirnrad", "fehler": "keine koaxialen Zylinderflächen (Kopf-/Fußkreis)"}
    ra = max(f.radius for f in koaxial)
    ergebnis = {"art": "stirnrad", "kopfkreis": round(2 * ra, 6), "fusskreis": round(2 * min(f.radius for f in koaxial), 6),
                "zaehne": sum(1 for f in koaxial if abs(f.radius - ra) <= tol_mm), "k": rad.messzaehnezahl()}
    flanken = [f for f in faces if f.art == "sonstige"]
    rho = (rad.r_start + rad.ra) / 2
    try:
        rechts = waehle_flanke(flanken, vz.modell(rad.flankenpunkt(1, "rechts", rho, vz.mitte, vz.winkel)), vz.normale,
                               0.25 * rad.m)
        links = waehle_flanke(flanken, vz.modell(rad.flankenpunkt(ergebnis["k"], "links", rho, vz.mitte, vz.winkel)),
                              vz.normale, 0.25 * rad.m)
        ergebnis["zahnweite"] = _zahnweite(mu, vz, rechts, links)
    except BauFehler as e:
        ergebnis["fehler"] = f"Zahnweite nicht messbar: {e}"
    return ergebnis


def _zahnstange(vz: Verzahnung, faces: list[Flaeche]) -> dict:
    kopf, t = vz.kopfrichtung, vz.u
    q = vz.bezugspunkt
    koepfe = [f for f in faces if f.art == "ebene" and skalar(f.normale, kopf) > _PARALLEL]
    n_links = tuple(-math.cos(ALPHA) * t[i] + math.sin(ALPHA) * kopf[i] for i in range(3))
    n_rechts = tuple(math.cos(ALPHA) * t[i] + math.sin(ALPHA) * kopf[i] for i in range(3))

    def schnitt(f: Flaeche) -> float:
        """u des Schnitts der Flankenebene mit der Profilmittellinie (durch q in Richtung t)."""
        return skalar(tuple(f.punkt[i] - q[i] for i in range(3)), f.normale) / skalar(t, f.normale)

    links = sorted(schnitt(f) for f in faces if f.art == "ebene" and skalar(f.normale, n_links) > _PARALLEL)
    rechts = sorted(schnitt(f) for f in faces if f.art == "ebene" and skalar(f.normale, n_rechts) > _PARALLEL)
    ergebnis = {"art": "zahnstange", "zaehne": len(koepfe),
                "kopflinie": sorted({round(skalar(tuple(f.punkt[i] - q[i] for i in range(3)), kopf), 6) for f in koepfe}),
                "teilung": [round(b - a, 6) for a, b in zip(links, links[1:])]}
    if len(links) == len(rechts):
        ergebnis["zahndicke"] = [round(b - a, 6) for a, b in zip(links, rechts)]
    else:
        ergebnis["fehler"] = f"{len(links)} linke und {len(rechts)} rechte Flanken"
    return ergebnis


def _verzahnung_messlage(f_soll: dict, p_soll: dict, aktuell: dict | None) -> Verzahnung | str:
    """Verzahnung für die Messung: Geometrie (Modul, Zähnezahl, Abmaß) aus dem Feature der freigegebenen Kopie, Lage
    (Ebene, Mitte, Winkel, Breite, umkehren) aus dem gleichnamigen Feature der aktuellen Spezifikation – die Lage ist
    Bauweg und darf sich nach der Freigabe ändern. Ohne aktuelle Spezifikation gilt die Soll-Spezifikation; fehlt das
    Feature in der aktuellen oder hat es eine andere Art, kommt ein Fehlertext."""
    soll = verzahnung_im_teil(f_soll, p_soll)
    if aktuell is None:
        return soll
    f_akt = next((f for f in aktuell["features"] if f["id"] == f_soll["id"] and f["typ"] == "verzahnung"), None)
    if f_akt is None:
        return f"Verzahnung {f_soll['id']} fehlt in der aktuellen Spezifikation"
    if f_akt["art"] != f_soll["art"]:
        return (f"Verzahnung {f_soll['id']}: art {f_akt['art']} in der aktuellen Spezifikation statt {f_soll['art']} "
                "in der Freigabe")
    return replace(verzahnung_im_teil(f_akt, aktuell.get("parameter", {})), geo=soll.geo)


def verzahnungen(model, soll_spec: dict, tol_mm: float, app, aktuell_spec: dict | None = None) -> dict[str, dict | str]:
    """Für jedes verzahnung-Feature der Soll-Spezifikation die Messwerte des gleichnamigen Features (Spec 4b §4.5)
    oder einen Fehlertext. Sollwerte (Modul, Zähnezahl, Abmaß) aus der Soll-Spezifikation, Lage aus aktuell_spec
    (Standard: Soll-Spezifikation; swki.verzahnung.verzahnung_im_teil); app für die MathUtility der Zahnweitenmessung."""
    ergebnis: dict[str, dict | str] = {}
    p = soll_spec.get("parameter", {})
    mu = None
    for f in soll_spec["features"]:
        if f["typ"] != "verzahnung":
            continue
        feature = model.FeatureByName(f["id"])
        if feature is None:
            ergebnis[f["id"]] = f"Feature {f['id']} fehlt im Teil"
            continue
        try:
            vz = _verzahnung_messlage(f, p, aktuell_spec)
            if isinstance(vz, str):
                ergebnis[f["id"]] = vz
                continue
            faces = flaechen(feature)
            if isinstance(vz.geo, Stirnrad):
                mu = mu or sw.mathutil(app)
                ergebnis[f["id"]] = _stirnrad(mu, vz, faces, tol_mm)
            else:
                ergebnis[f["id"]] = _zahnstange(vz, faces)
        except Exception as e:  # COM-Fehler beim Lesen → Mangel statt Abbruch der Prüfung
            ergebnis[f["id"]] = f"Verzahnung {f['id']} nicht messbar: {e}"
    return ergebnis


def punkt_und_normale(face) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Punkt (mm) und äußere Einheitsnormale einer Fläche nahe der Mitte ihrer Box (Spike S16, Frage 5):
    ISurface.EvaluateAtPoint liefert zuerst die Normale der Trägerfläche; FaceInSurfaceSense True = die Fläche zeigt
    entgegen. Gilt für Ebenen und Kegel gleich."""
    box = face.GetBox
    q = face.GetClosestPointOn((box[0] + box[3]) / 2, (box[1] + box[4]) / 2, (box[2] + box[5]) / 2)
    werte = face.GetSurface.EvaluateAtPoint(q[0], q[1], q[2])
    n = (werte[0], werte[1], werte[2])
    if face.FaceInSurfaceSense:
        n = (-n[0], -n[1], -n[2])
    betrag = laenge(n)
    return (in_mm(q[0]), in_mm(q[1]), in_mm(q[2])), (n[0] / betrag, n[1] / betrag, n[2] / betrag)


def _skizzenebene(ctx, ebene, mit_punkt: bool) -> tuple[tuple, tuple | None]:
    """(Normale, Punkt in mm oder None) der Skizzenebene eines Knotens im fertigen Teil; den Punkt braucht nur mittig."""
    normale = skizzennormale(ebene)
    if normale is None:  # {nahe}: Normale und Punkt aus dem Modell
        flaeche = loese_flaeche(ctx, ebene)
        if flaeche.art != "ebene":
            raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", "Skizzenfläche ist nicht eben")
        return flaeche.normale, flaeche.punkt
    if not mit_punkt or isinstance(ebene, str):
        return normale, (0.0, 0.0, 0.0)
    if "versatz" in ebene:
        abstand_ = ctx.wert(ebene["versatz"]["abstand"])
        return normale, tuple(abstand_ * c for c in normale)
    if ebene["feature"] not in ctx.ergebnisse:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Feature {ebene['feature']!r} fehlt im Teil")
    flaeche = flaeche_in_richtung(flaechen(ctx.ergebnis(ebene["feature"]).features[0]), ebene["flaeche"])
    return normale, flaeche.punkt


def formschraegen(ctx, soll_spec: dict, aktuell_spec: dict | None = None) -> dict[str, dict | str]:
    """Spec Formschräge §6.1: je extrusion-/schnitt-Knoten mit formschraege (Soll: freigegebene Kopie) die Seitenflächen
    des gleichnamigen Features als {"flaechen": [{"winkel", "vorzeichen"}]} oder einen Fehlertext. Skizzenebene,
    umkehren und Endbedingung sind Bauweg und kommen aus der aktuellen Spezifikation."""
    aktuell = {f["id"]: f for f in (aktuell_spec or soll_spec)["features"]}
    ergebnis = {}
    for f in soll_spec["features"]:
        if schraege(f) is None:
            continue
        g = aktuell.get(f["id"])
        g = g if g is not None and g["typ"] in TYPEN else f
        feature = ctx.model.FeatureByName(f["id"])
        if feature is None:
            ergebnis[f["id"]] = f"Feature {f['id']} fehlt im Teil"
            continue
        try:
            mittig = g["ende"]["typ"] == "mittig"
            normale, punkt = _skizzenebene(ctx, g["skizze"]["ebene"], mittig)
            r = extrusionsrichtung(normale, g["typ"], g["ende"].get("umkehren", False))
            messungen = [punkt_und_normale(face) for face in (feature.GetFaces or ())]
            ergebnis[f["id"]] = {"flaechen": seitenflaechen(messungen, r, punkt if mittig else None)}
        except BauFehler as e:
            ergebnis[f["id"]] = f"{e.code}: {e}"
        except Exception as e:  # COM-Fehler beim Lesen → Mangel statt Abbruch der Prüfung
            ergebnis[f["id"]] = f"Formschräge {f['id']} nicht messbar: {e}"
    return ergebnis


def kontext_aus_datei(app, model, spec: dict, spec_pfad: Path, tol_mm: float, protokoll: dict) -> Kontext:
    """Kontext für ein geöffnetes Teil: Features über ihre Namen (= Feature-IDs), Bohrungspunkte aus dem Bauprotokoll.

    Anker werden bewusst nicht neu aufgelöst: im fertigen Teil kann der Ankerpunkt weggeschnitten sein.
    """
    punkte = {k["id"]: k.get("punkte") or [] for k in protokoll["knoten"]}
    ctx = Kontext(app, model, spec, spec_pfad, tol_mm)
    for f in spec["features"]:
        feature = model.FeatureByName(f["id"])
        if feature is not None:
            features = [feature]
            if f["typ"] == "bohrung" and "senkung" in f:  # der Handler legt die Senkung als zweites Feature an
                senkung = model.FeatureByName(f"{f['id']}_senkung")
                if senkung is not None:
                    features.append(senkung)
            ctx.ergebnisse[f["id"]] = FeatureErgebnis(features, punkte=[tuple(p) for p in punkte.get(f["id"], [])])
    return ctx


def messgeometrie(ctx, spec: dict, mp: dict) -> Messgeometrie:
    if "punkt" in mp:
        return Messgeometrie("punkt", tuple(ctx.wert(v) for v in mp["punkt"]))
    if "referenz" in mp:
        if mp["referenz"] not in ctx.ergebnisse:
            raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Referenz {mp['referenz']!r} fehlt im Teil")
        return Messgeometrie(*referenz_geometrie(ctx.ergebnis(mp["referenz"]).features[0]))
    if mp["feature"] not in ctx.ergebnisse:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Feature {mp['feature']!r} fehlt im Teil")
    feature = ctx.ergebnis(mp["feature"]).features[0]
    if "flaeche" in mp:
        f = flaeche_in_richtung(flaechen(feature), mp["flaeche"], koplanar_ok=True)
        return Messgeometrie("ebene", f.punkt, f.normale)
    punkte = ctx.ergebnis(mp["feature"]).punkte
    if not punkte:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Feature {mp['feature']} hat keine Bohrungsinstanzen im Protokoll")
    if mp["instanz"] > len(punkte):
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Bohrung {mp['feature']} hat nur {len(punkte)} Instanzen")
    punkt = punkte[mp["instanz"] - 1]
    [zylinder] = zylinder_zu_punkten(flaechen(feature), [punkt], ctx.tol_mm)
    n = laenge(zylinder.achse)
    # Protokollpunkt diente nur der Zuordnung; gemessen wird der echte Achspunkt der Zylinderfläche.
    return Messgeometrie("achse", zylinder.punkt, tuple(c / n for c in zylinder.achse))


def messpunkte(ctx, spec: dict) -> dict[str, Messgeometrie | str]:
    ergebnis = {}
    for mp in spec.get("pruefung", {}).get("masse_pruefen", []):
        for punkt in (mp["von"], mp["zu"]):
            try:
                ergebnis[messpunkt_schluessel(punkt)] = messgeometrie(ctx, spec, punkt)
            except BauFehler as e:
                ergebnis[messpunkt_schluessel(punkt)] = f"{e.code}: {e}"
    return ergebnis


def durchmesser(ctx, spec: dict) -> dict[str, dict | str]:
    """Durchmesser je pruefung.durchmesser_pruefen: Zylinderfläche des Features einschließlich Senkung (`<id>_senkung`
    einer Bohrung), auf deren Mantel `nahe` liegt; mit
    `referenz` zusätzlich die Bezugsachse (Koaxialität bewertet bewertung.bewerte)."""
    ergebnis = {}
    for dp in spec.get("pruefung", {}).get("durchmesser_pruefen", []):
        try:
            for fid in (dp["feature"], dp.get("referenz")):
                if fid is not None and fid not in ctx.ergebnisse:
                    raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Feature {fid!r} fehlt im Teil")
            nahe = tuple(ctx.wert(v) for v in dp["nahe"])
            alle = [f for sw_feature in ctx.ergebnis(dp["feature"]).features for f in flaechen(sw_feature)]
            z = zylinder_durch_punkt(alle, nahe, ctx.tol_mm)
            n = laenge(z.achse)
            wert = {"durchmesser": round(2 * z.radius, 6),
                    "achse": Messgeometrie("achse", z.punkt, tuple(c / n for c in z.achse))}
            if "referenz" in dp:
                wert["referenz"] = Messgeometrie(*referenz_geometrie(ctx.ergebnis(dp["referenz"]).features[0]))
            ergebnis[dp["was"]] = wert
        except BauFehler as e:
            ergebnis[dp["was"]] = f"{e.code}: {e}"
    return ergebnis


def messe(ctx, freigegeben: dict | None = None) -> Messwerte:
    """freigegeben: Spezifikation im Stand der Freigabe (Soll der Prüfungen normbohrungen, verzahnungen und formschraegen); ohne Angabe
    ctx.spec."""
    model = ctx.model
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return Messwerte(
        rebuild_fehler=rebuild_fehler(model),
        skizzen=skizzenstatus(model),
        box=sw.huellquader_eng_mm(model),
        volumen=in_mm3(mp.Volume),
        schwerpunkt=tuple(in_mm(c) for c in mp.CenterOfMass),
        material=model.GetMaterialPropertyName2("", byref_str()) or "",
        eigenschaften=lies_eigenschaften(model),
        messpunkte=messpunkte(ctx, ctx.spec),
        normbohrungen=normbohrungen(model, freigegeben or ctx.spec),
        koerper=len(koerper(model)),
        durchmesser=durchmesser(ctx, ctx.spec),
        verzahnungen=verzahnungen(model, freigegeben or ctx.spec, ctx.tol_mm, ctx.app, ctx.spec),
        formschraegen=formschraegen(ctx, freigegeben or ctx.spec, ctx.spec),
    )
