"""Messwerte eines gespeicherten Laufs aus SolidWorks lesen (Spike S9b, Bausteine 19 und 23)."""

from pathlib import Path

from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.anker import AnkerFehler, flaeche_in_richtung, laenge, zylinder_zu_punkten
from swki.compiler.eigenschaften import lies_eigenschaften
from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import FeatureErgebnis, Kontext
from swki.compiler.topologie import flaechen
from swki.pruefung.bewertung import Messwerte, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie
from swki.verbindung import byref_long, byref_str, in_mm, in_mm3

SW_DOC_PART = 1  # swDocumentTypes_e
SW_OPEN_SILENT = 1  # swOpenDocOptions_e
SW_WARNUNG_BEREITS_OFFEN = 128  # swFileLoadWarning_AlreadyOpen


class PruefFehler(SwkiFehler):
    pass


def oeffne(app, pfad: Path):
    """Öffnet ein gespeichertes Teil. Ist es schon offen (evtl. beim Nutzer), wird abgebrochen statt es zu schließen."""
    fehler, warnungen = byref_long(), byref_long()
    model = app.OpenDoc6(str(pfad), SW_DOC_PART, SW_OPEN_SILENT, "", fehler, warnungen)
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


def kontext_aus_datei(app, model, spec: dict, spec_pfad: Path, tol_mm: float, protokoll: dict) -> Kontext:
    """Kontext für ein geöffnetes Teil: Features über ihre Namen (= Feature-IDs), Bohrungspunkte aus dem Bauprotokoll.

    Anker werden bewusst nicht neu aufgelöst: im fertigen Teil kann der Ankerpunkt weggeschnitten sein.
    """
    punkte = {k["id"]: k.get("punkte") or [] for k in protokoll["knoten"]}
    ctx = Kontext(app, model, spec, spec_pfad, tol_mm)
    for f in spec["features"]:
        feature = model.FeatureByName(f["id"])
        if feature is not None:
            ctx.ergebnisse[f["id"]] = FeatureErgebnis([feature], punkte=[tuple(p) for p in punkte.get(f["id"], [])])
    return ctx


def _messgeometrie(ctx, spec: dict, mp: dict) -> Messgeometrie:
    if "punkt" in mp:
        return Messgeometrie("punkt", tuple(ctx.wert(v) for v in mp["punkt"]))
    if mp["feature"] not in ctx.ergebnisse:
        raise AnkerFehler("REFERENZ_NICHT_GEFUNDEN", f"Feature {mp['feature']!r} fehlt im Teil")
    feature = ctx.ergebnis(mp["feature"]).features[0]
    if "flaeche" in mp:
        f = flaeche_in_richtung(flaechen(feature), mp["flaeche"])
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
                ergebnis[messpunkt_schluessel(punkt)] = _messgeometrie(ctx, spec, punkt)
            except BauFehler as e:
                ergebnis[messpunkt_schluessel(punkt)] = f"{e.code}: {e}"
    return ergebnis


def messe(ctx) -> Messwerte:
    model = ctx.model
    mp = model.Extension.CreateMassProperty2
    mp.UseSystemUnits = True
    return Messwerte(
        rebuild_fehler=rebuild_fehler(model),
        skizzen=skizzenstatus(model),
        box=sw.teilebox_mm(model),
        volumen=in_mm3(mp.Volume),
        schwerpunkt=tuple(in_mm(c) for c in mp.CenterOfMass),
        material=model.GetMaterialPropertyName2("", byref_str()) or "",
        eigenschaften=lies_eigenschaften(model),
        messpunkte=messpunkte(ctx, ctx.spec),
    )
