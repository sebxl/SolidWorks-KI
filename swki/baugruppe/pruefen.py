"""swki pruefen für Baugruppen (Spec 3b §9): erst jedes Eigenteil (Teilprüfung, Geometrie für die Baugruppenmessung),
dann die Normteil-Kopien (Kopfauflagen, Messpunkte), zuletzt die Baugruppe (Verknüpfungen, Bestimmtheit, Kollision,
Stückliste, Lage, Screenshots). Öffnet Dateien nur und speichert nie."""

import json
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner, laeufe
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import basis, instanzen
from swki.baugruppe.bewertung import BaugruppenMesswerte, bewerte_baugruppe, stueckliste_soll
from swki.baugruppe.freigabe import freigegebene_quellen, freigegebene_teile, pruefe_freigabe_baugruppe
from swki.baugruppe.geometrie import transformiere
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.modell import Baugruppe, dokument_name
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.eigenschaften import lies_eigenschaften
from swki.compiler.fehler import BauFehler
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.befehle import pruefe_lauf_gebaut, schreibe_pruefbericht
from swki.pruefung.bewertung import bewerte, messpunkt_schluessel
from swki.pruefung.bilder import screenshots
from swki.pruefung.geometrie import Messgeometrie
from swki.pruefung.messen import kontext_aus_datei, messe, messgeometrie, oeffne, rebuild_fehler
from swki.spec.ausdruck import auswerten
from swki.verbindung import verbinde

KOPFAUFLAGE = {"referenz": "EINBAU_EBENE"}


def _ohne_komponente(p: dict) -> dict:
    return {k: v for k, v in p.items() if k != "komponente"}


def teil_messpunkte(bg: Baugruppe) -> dict[str, list[dict]]:
    """Teil-Messpunkte je Quelldokument: Messpunkte von masse_pruefen und die Kopfauflage jeder Schraube ISO 4762."""
    bedarf: dict[str, list[dict]] = {}
    for mp in bg.spec.get("pruefung", {}).get("masse_pruefen", []):
        for p in (mp["von"], mp["zu"]):
            if "komponente" in p:
                punkte = bedarf.setdefault(bg.quellen[basis(p["komponente"])].schluessel_dokument, [])
                if _ohne_komponente(p) not in punkte:
                    punkte.append(_ohne_komponente(p))
    for q in bg.quellen.values():
        if q.norm == "ISO 4762" and KOPFAUFLAGE not in bedarf.setdefault(q.schluessel, []):
            bedarf[q.schluessel].append(KOPFAUFLAGE)
    return bedarf


def gewindebohrungen_teil(teil_spec: dict, protokoll_teil: dict) -> list[dict]:
    """Eintrittspunkte (Teilkoordinaten) aller Gewinde-Normbohrungen aus dem Bauprotokoll des Teils."""
    punkte = {k["id"]: k.get("punkte") or [] for k in protokoll_teil.get("knoten", [])}
    return [{"feature": f["id"], "instanz": i, "punkt": tuple(p)}
            for f in teil_spec["features"] if f["typ"] == "normbohrung" and f["art"] == "gewinde"
            for i, p in enumerate(punkte.get(f["id"], []), start=1)]


def _geometrie(ctx, punkte: list[dict]) -> dict:
    ergebnis = {}
    for p in punkte:
        try:
            ergebnis[messpunkt_schluessel(p)] = messgeometrie(ctx, ctx.spec, p)
        except BauFehler as e:
            ergebnis[messpunkt_schluessel(p)] = f"{e.code}: {e}"
    return ergebnis


def _in_baugruppe(geo, t):
    return geo if isinstance(geo, str) else transformiere(geo, t)


def _messe_baugruppe(asm, bg: Baugruppe, protokoll: dict, geometrie: dict, teilberichte: dict) -> BaugruppenMesswerte:
    namen = {k["sw_name"]: k["id"] for k in protokoll.get("komponenten", [])}
    transformationen, zustand, stueckliste = {}, {}, {}
    for komp in sw_baugruppe.komponenten(asm):
        datei = Path(komp.GetPathName).name
        stueckliste[datei] = stueckliste.get(datei, 0) + 1
        iid = namen.get(komp.Name2, komp.Name2)
        transformationen[iid] = sw_baugruppe.transform(komp)
        zustand[iid] = {"status": sw_baugruppe.status(komp), "fixiert": sw_baugruppe.ist_fixiert(komp)}
    parameter = bg.spec.get("parameter", {})
    messpunkte = {}
    for mp in bg.spec.get("pruefung", {}).get("masse_pruefen", []):
        for p in (mp["von"], mp["zu"]):
            if "punkt" in p:
                messpunkte[messpunkt_schluessel(p)] = Messgeometrie("punkt", tuple(auswerten(v, parameter) for v in p["punkt"]))
            elif p["komponente"] not in transformationen:
                messpunkte[messpunkt_schluessel(p)] = f"Komponente {p['komponente']} fehlt in der Baugruppe"
            else:
                quelle = bg.quellen[basis(p["komponente"])].schluessel_dokument
                geo = geometrie.get(quelle, {}).get(messpunkt_schluessel(_ohne_komponente(p)), "Messpunkt fehlt")
                messpunkte[messpunkt_schluessel(p)] = _in_baugruppe(geo, transformationen[p["komponente"]])
    schrauben, bohrungen = {}, []
    for i in instanzen(bg.spec, bg.quellen):
        q = bg.quellen[i.komponente]
        if i.id not in transformationen:
            continue
        if q.norm == "ISO 4762":
            geo = geometrie.get(q.schluessel, {}).get(messpunkt_schluessel(KOPFAUFLAGE), "Kopfauflage fehlt")
            schrauben[i.id] = _in_baugruppe(geo, transformationen[i.id])
        elif q.art == "teil":
            for b in gewindebohrungen_teil(q.spec, protokoll["teile"][q.datei]):
                bohrungen.append({"teil": i.id, "feature": b["feature"], "instanz": b["instanz"],
                                  "eintritt": transformiere(Messgeometrie("punkt", b["punkt"]), transformationen[i.id])})
    interferenzen = [{"paar": sorted(namen.get(n, n) for n in paar), "volumen": volumen}
                     for paar, volumen in sw_baugruppe.interferenzen(asm)]
    return BaugruppenMesswerte(
        rebuild_fehler=rebuild_fehler(asm),
        verknuepfungen={f.Name: sw_baugruppe.fehlercode(f) for f in sw_baugruppe.verknuepfungen(asm)},
        komponenten=zustand, stueckliste=stueckliste, interferenzen=interferenzen,
        box=sw_baugruppe.huellquader(asm), masse_kg=sw_baugruppe.masse_kg(asm), eigenschaften=lies_eigenschaften(asm),
        messpunkte=messpunkte, schrauben=schrauben, gewindebohrungen=bohrungen, teilberichte=teilberichte)


def pruefen(spec_pfad: Path, lauf: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    bg = lade_baugruppe(spec_pfad)
    pruefe_freigabe_baugruppe(bg)
    r, standard = lade_rechner(), lade_standard()
    tol = standard["toleranzen"]["anker_mm"]
    auftrag = auftrag_name(spec_pfad)
    if lauf is None:
        bisher = laeufe(r, auftrag)
        if not bisher:
            raise SwkiFehler(f"Auftrag {auftrag} hat noch keinen Lauf. Zuerst: swki bauen")
        lauf = bisher[-1]
    ordner = lauf_ordner(r, auftrag, lauf)
    asm_pfad = ordner / f"{dateiname(bg.spec, auftrag, standard)}.sldasm"
    if not asm_pfad.exists():
        raise SwkiFehler(f"{asm_pfad} fehlt (Lauf {lauf} ohne gespeicherte Baugruppe)")
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    pruefe_lauf_gebaut(protokoll, lauf)
    soll_teile = freigegebene_teile(bg)
    bedarf = teil_messpunkte(bg)
    app = verbinde(r.sw_jahr)
    teilberichte, geometrie = {}, {}
    for datei, teil_spec in bg.teile.items():
        model = oeffne(app, ordner / dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard))
        try:
            ctx = kontext_aus_datei(app, model, teil_spec, bg.pfad.parent / datei, tol, protokoll["teile"][datei])
            teilberichte[datei] = bewerte(teil_spec, messe(ctx, soll_teile[datei]), standard, soll_teile[datei])
            geometrie[datei] = _geometrie(ctx, bedarf.get(datei, []))
        finally:
            sw.schliesse(app, model)
    for q in {q.schluessel: q for q in bg.quellen.values() if q.art == "normteil"}.values():
        if q.schluessel not in bedarf:
            continue
        pfad = ordner / dokument_name(q, auftrag, standard)
        model = oeffne(app, pfad)
        try:
            ctx = kontext_aus_datei(app, model, q.spec, pfad.with_suffix(".yaml"), tol, {"knoten": []})
            geometrie[q.schluessel] = _geometrie(ctx, bedarf[q.schluessel])
        finally:
            sw.schliesse(app, model)
    asm = oeffne(app, asm_pfad)
    try:
        sw_baugruppe.aufloesen(asm)
        messwerte = _messe_baugruppe(asm, bg, protokoll, geometrie, teilberichte)
        bilder = screenshots(app, asm, ordner / "bilder")
    finally:
        sw.schliesse(app, asm)
    bericht = {
        "auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(asm_pfad), "art": "baugruppe",
        **bewerte_baugruppe(bg.spec, bg.quellen, messwerte, standard, stueckliste_soll(bg.spec, freigegebene_quellen(bg), auftrag, standard)),
        "normteile": protokoll.get("normteile", {}), "bilder": bilder,
    }
    schreibe_pruefbericht(spec_pfad, lauf, ordner, bericht)
    return bericht
