"""swki pruefen für art: aenderung (Spec Bestandsdateien §7): Lauf gegen Bestand, ohne etwas zu speichern.

Vorher ist die Aufnahme aus `bestand.json`, nachher liest `lies_bestand` den Lauf gleich. Für die Differenz müssen beide Dokumente
zugleich offen sein, SolidWorks öffnet aber keine zwei gleichnamigen (S18d: Fehler 65536). Die Bestandskopie wird darum nach
`<lauf>/vergleich/vorher_<name>` kopiert und bleibt dort zur Analyse liegen; die Bestandskopie selbst und die Protokoll-Prüfsummen
berührt das nicht, die Änderungserkennung kennt nur die Dateien aus `protokoll.sha256`.

Beide Dokumente gehen unsichtbar auf (S18d: +0 MB gegen +3,2 GB) und nur lesend, nur die Bilder brauchen ein Fenster.

`ok: None` heißt hier nicht bestanden (Ruling): `bewerte_aenderung` führt solche Einträge in `maengel`, mit `nicht_nachgewiesen`, also
zählt `lies_laeufe` sie als offen. Anders als beim Teil: Dort heißt `None` „kein Soll berechenbar“, hier „der Schutz hat nicht
gegriffen“."""

import json
from pathlib import Path

from swki.auftrag import auftrag_name, lauf_datei, lauf_ordner, laeufe
from swki.bestand.ablage import bestand_ordner, pruefe_kopie, vorher_kopie
from swki.bestand.differenz import DifferenzFehler, alle_feature_boxen, bewerte_bereiche, in_konfigurationen, koerper_differenz
from swki.bestand.feature_messung import bewerte, messart, teil_spec
from swki.bestand.punkte import fremde_namen
from swki.bestand.spec import aufnahme_zu, lade_aenderung, pruefe_lauf_bestand
from swki.bestand.sw_bestand import lies_bestand
from swki.bestand.vergleich import vergleiche
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.fehler import BauFehler
from swki.compiler.kontext import FeatureErgebnis, Kontext
from swki.compiler.topologie import flaechen
from swki.kaufteile.bewertung import TOL_MASS
from swki.kaufteile.sw_kaufteil import alle_flaechen, messpunkt
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.befehle import pruefe_lauf_gebaut, schreibe_pruefbericht
from swki.pruefung.bewertung import beschreibung, mass_eintrag, messpunkt_schluessel
from swki.pruefung.bilder import screenshots
from swki.pruefung.geometrie import Messgeometrie
from swki.pruefung.messen import formschraegen, messgeometrie, normbohrungen, oeffne, verzahnungen
from swki.spec.ausdruck import auswerten
from swki.spec.freigabe import freigegebene_spec, pruefe_freigabe
from swki.verbindung import verbinde


def _masse_vorgaben(spec: dict) -> list[dict]:
    return spec.get("pruefung", {}).get("masse_pruefen", [])


def _messkontext(app, model, spec: dict, spec_pfad: Path, tol_mm: float) -> Kontext:
    """Kontext zum Messen: `{feature: …}` nennt ein Bestandsfeature, die `name` eines neuen Features oder dessen Punkt-ID, auch in den
    Ankern neuer Features. Was es nicht gibt, fehlt hier und wird beim Messen zum Mangel, nie zum Abbruch der Prüfung."""
    ctx = Kontext(app, model, {"parameter": spec.get("parameter", {}), "features": []}, spec_pfad, tol_mm, gleichungen=False)
    neu = {p["id"]: p["name"] for p in spec["punkte"] if p["typ"] == "feature"}
    for name in [*fremde_namen(spec), *neu, *neu.values()]:
        if (feature := model.FeatureByName(neu.get(name, name))) is not None:
            ctx.ergebnisse[name] = FeatureErgebnis([feature])
    return ctx


def _messpunkte(app, model, spec: dict, spec_pfad: Path, tol_mm: float) -> dict[str, Messgeometrie | str]:
    """Messgeometrie je Messpunkt in der aktiven Konfiguration, ein Fehlertext statt eines Abbruchs. Punkte und Features wie beim Teil,
    `flaeche` ohne Feature (`nahe` und `normale`, nach Lage statt nach Feature) wie beim Kaufteil, nur mit aufgelösten Ausdrücken."""
    if not _masse_vorgaben(spec):
        return {}
    ctx = _messkontext(app, model, spec, spec_pfad, tol_mm)
    flaechen, aus = None, {}
    for mp in (m[seite] for m in _masse_vorgaben(spec) for seite in ("von", "zu")):
        try:
            if "flaeche" in mp and "feature" not in mp:
                flaechen = alle_flaechen(model) if flaechen is None else flaechen
                aufgeloest = {k: [ctx.wert(c) for c in v] for k, v in mp["flaeche"].items()}
                aus[messpunkt_schluessel(mp)] = messpunkt({"flaeche": aufgeloest}, {}, {}, flaechen, tol_mm)
            else:
                aus[messpunkt_schluessel(mp)] = messgeometrie(ctx, spec, mp)
        except BauFehler as e:
            aus[messpunkt_schluessel(mp)] = f"{e.code}: {e}"
    return aus


def _masse_pruefen(spec: dict, punkte: dict[str, Messgeometrie | str], konfiguration: str) -> list[dict]:
    """`mass:<was>` wie beim Teil, gemessen in der aktiven Konfiguration; `soll` darf ein Ausdruck sein."""
    return [mass_eintrag(mp, punkte, auswerten(mp["soll"], spec.get("parameter", {})), mp.get("tol", TOL_MASS),
                         sorted({x["feature"] for x in (mp["von"], mp["zu"]) if "feature" in x}), konfiguration=konfiguration)
            for mp in _masse_vorgaben(spec)]


def _achsen(feature) -> list | str:
    """(Achspunkt, Richtung) je Zylinderfläche; ein Fehlertext macht die Position zum Mangel, nicht die Prüfung zum Abbruch."""
    try:
        return [(z.punkt, z.achse) for z in flaechen(feature) if z.art == "zylinder"]
    except Exception as e:  # COM-Fehler beim Lesen
        return f"Bohrungsachsen nicht lesbar: {e}"


def _miss_features(app, model, spec: dict, soll: dict, aktuell: dict, spec_pfad: Path, tol_mm: float) -> dict[str, dict | str]:
    """Messwerte der neuen Features in der aktiven Konfiguration: dieselben Bausteine wie beim Teil, Soll aus `soll` (freigegebene
    Kopie), Lage als Bauweg aus `aktuell`. Der Kontext hält `IFeature` und entsteht darum je Konfiguration neu (S18c)."""
    bohrungen = normbohrungen(model, soll)
    for name, ist in bohrungen.items():
        if isinstance(ist, dict):
            ist["achsen"] = _achsen(model.FeatureByName(name))
    ctx = _messkontext(app, model, spec, spec_pfad, tol_mm)
    return {**bohrungen, **verzahnungen(model, soll, tol_mm, app, aktuell), **formschraegen(ctx, soll, aktuell)}


def _feature_messungen(app, model, spec: dict, freigegeben: dict, spec_pfad: Path, konfigurationen: list[str], tol_mm: float) -> dict:
    """Konfiguration → Featurename → Messwerte (`swki.bestand.feature_messung.bewerte`); ohne messbares Feature wird nicht umgeschaltet."""
    soll, aktuell = teil_spec(freigegeben), teil_spec(spec)
    if not any(messart(f) for f in soll["features"]):
        return {}
    return in_konfigurationen(model, konfigurationen, lambda: _miss_features(app, model, spec, soll, aktuell, spec_pfad, tol_mm))


def _skript_lauf(spec: dict, protokoll: dict) -> tuple[frozenset[str], frozenset[str]]:
    """Aus dem Protokoll: (Features, die `bauen(ctx)` zurückgab; Punkt-IDs der durchgelaufenen Skripte)."""
    knoten = {k["id"]: k for k in protokoll.get("knoten", [])}
    gelaufen = [knoten[p["id"]] for p in spec["punkte"]
                if p["typ"] == "skript" and knoten.get(p["id"], {}).get("status") == "ok"]
    return frozenset(n for k in gelaufen for n in k.get("sw_namen") or ()), frozenset(k["id"] for k in gelaufen)


_RANG = {False: 0, None: 1, True: 2}


def _ein_eintrag_je_punkt(pruefungen: list[dict]) -> list[dict]:
    """`punkt:<id>` kommt aus `vergleiche` (Wert, Zustand) und aus `bewerte_bereiche` (Wirkung): ein Eintrag, der schlechtere Wert gilt."""
    aus: dict[str, dict] = {}
    for i, e in enumerate(pruefungen):
        schluessel = e["id"] if e["id"].startswith("punkt:") else str(i)
        alt = aus.get(schluessel)
        aus[schluessel] = e if alt is None else {**alt, **e} if _RANG[e["ok"]] < _RANG[alt["ok"]] else {**e, **alt}
    return list(aus.values())


def bewerte_aenderung(pruefungen: list[dict]) -> dict:
    """`bestanden` nur, wenn jeder Eintrag `ok: True` trägt: `None` steht als `nicht_nachgewiesen` in `maengel`."""
    pruefungen = _ein_eintrag_je_punkt(pruefungen)
    maengel = [{"pruefung": e["id"], "knoten": e.get("knoten", []), "beschreibung": beschreibung(e),
                "nicht_nachgewiesen": e["ok"] is None} for e in pruefungen if e["ok"] is not True]
    return {"bestanden": not maengel, "maengel": maengel, "pruefungen": pruefungen}


def _differenz(app, model_vorher, model, konfiguration: str) -> list | str:
    """Kein stiller Rückfall: Scheitert die Differenz, steht für diese Konfiguration der Grund da (`ok: None`, S18d: STL ist kein
    Nachweis der 0,01 mm und stürzt an unsichtbaren Dokumenten ab)."""
    try:
        return koerper_differenz(app, model_vorher, model, konfiguration)
    except DifferenzFehler as e:
        return str(e)


def _bereichs_features(spec: dict) -> set[str]:
    return {n for b in spec["bereiche"] for n in b.get("features", ())}


def _vergleiche_dokumente(app, vorher_pfad: Path, teil: Path, spec: dict, freigegeben: dict, spec_pfad: Path, vorher: dict,
                          tol_mm: float) -> tuple:
    """(nachher, abweichungen, feature_boxen, messpunkte, feature_messungen). Nichts wird gespeichert, beide Dokumente gehen wieder zu."""
    model_vorher = oeffne(app, vorher_pfad, sichtbar=False, nur_lesen=True)
    try:
        model = oeffne(app, teil, sichtbar=False, nur_lesen=True)
        try:
            nachher = lies_bestand(app, model)
            konfigurationen = [k for k in vorher["konfigurationen"] if k in nachher["konfigurationen"]]
            abweichungen = {k: _differenz(app, model_vorher, model, k) for k in konfigurationen}
            boxen = alle_feature_boxen([model_vorher, model], konfigurationen, _bereichs_features(spec))
            return (nachher, abweichungen, boxen, _messpunkte(app, model, spec, spec_pfad, tol_mm),
                    _feature_messungen(app, model, spec, freigegeben, spec_pfad, konfigurationen, tol_mm))
        finally:
            sw.schliesse(app, model)
    finally:
        sw.schliesse(app, model_vorher)


def _bilder(app, pfad: Path, ordner: Path) -> dict[str, str]:
    """Die gespeicherte aktive Konfiguration, in eigenem Fenster: Bilder gehen nur sichtbar."""
    model = oeffne(app, pfad, nur_lesen=True)
    try:
        return screenshots(app, model, ordner)
    finally:
        sw.schliesse(app, model)


def pruefen(spec_pfad: Path, lauf: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_aenderung(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is None:
        bisher = laeufe(r, auftrag)
        if not bisher:
            raise SwkiFehler(f"Auftrag {auftrag} hat noch keinen Lauf. Zuerst: swki bauen")
        lauf = bisher[-1]
    protokoll_datei = lauf_datei(spec_pfad, lauf, "protokoll")
    if not protokoll_datei.exists():
        raise SwkiFehler(f"Lauf {lauf} von {auftrag} hat kein Protokoll")
    protokoll = json.loads(protokoll_datei.read_text(encoding="utf-8"))
    pruefe_lauf_gebaut(protokoll, lauf)
    pruefe_lauf_bestand(spec, protokoll, lauf)  # BESTAND_VERALTET
    ordner, teil = lauf_ordner(r, auftrag, lauf), Path(protokoll["dateien"]["teil"])
    if not teil.exists():
        raise SwkiFehler(f"{teil} fehlt (Lauf {lauf} ohne gespeichertes Teil)")
    vorher = aufnahme_zu(spec, spec_pfad)  # BESTAND_UNBEKANNT, BESTAND_VERALTET
    kopie = bestand_ordner(r, auftrag, spec["bestand"]["aufnahme"]) / vorher["datei"]["name"]
    pruefe_kopie(vorher, kopie)  # BESTAND_ABWEICHEND
    vorher_pfad = vorher_kopie(kopie, ordner)

    app = verbinde(r.sw_jahr)
    freigegeben = freigegebene_spec(spec_pfad)
    nachher, abweichungen, boxen, punkte, gemessen = _vergleiche_dokumente(app, vorher_pfad, teil, spec, freigegeben, spec_pfad, vorher,
                                                                           standard["toleranzen"]["anker_mm"])
    bilder = _bilder(app, teil, ordner / "bilder")
    bilder_vorher = _bilder(app, vorher_pfad, vorher_pfad.parent / "bilder")

    vorher["datei"] = {**vorher["datei"], "ordner": str(kopie.parent)}  # für `externe_referenzen`
    nachher = {**nachher, "datei": {"name": teil.name, "ordner": str(ordner)}}
    bereiche = bewerte_bereiche(spec, abweichungen, boxen, volumen_prozent=standard["toleranzen"]["volumen_prozent"])
    feature_messung = bewerte(freigegeben, gemessen, standard["toleranzen"])
    pruefungen = (vergleiche(spec, vorher, nachher, spec.get("parameter", {}), *_skript_lauf(spec, protokoll), feature_messung) + bereiche
                  + _masse_pruefen(spec, punkte, nachher["aktiv"]))
    bericht = {"auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(teil), "vorher": str(vorher_pfad),
               **bewerte_aenderung(pruefungen),
               "differenzen": {e["konfiguration"]: e["ist"] for e in bereiche if e["id"] == "bereich"},
               "bilder": bilder, "bilder_vorher": bilder_vorher}
    schreibe_pruefbericht(spec_pfad, lauf, ordner, bericht)
    return bericht
