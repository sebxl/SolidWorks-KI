"""swki pruefen für Baugruppen (Spec 3b §9): erst jedes Eigenteil (Teilprüfung, Geometrie für die Baugruppenmessung),
dann die Normteil-Kopien (Kopfauflagen, Messpunkte), zuletzt die Baugruppe (Verknüpfungen, Bestimmtheit, Kollision,
Stückliste, Lage, Screenshots). Öffnet Dateien nur und speichert nie."""

import json
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner, laeufe
from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import GRENZEN, basis, instanzen, verknuepfungen
from swki.baugruppe.bewegung import bewegungen, ergaenze_bericht
from swki.baugruppe.bewegungslauf import bewegungen_oder_ersatz
from swki.baugruppe.bewertung import BaugruppenMesswerte, bewerte_baugruppe, stueckliste_soll
from swki.baugruppe.freigabe import freigegebene_quellen, freigegebene_teile, pruefe_freigabe_baugruppe
from swki.baugruppe.geometrie import transformiere
from swki.baugruppe.kopplung import in_baugruppe, kopplungen, verzahnung_der_seite
from swki.baugruppe.laden import lade_baugruppe
from swki.baugruppe.modell import Baugruppe, dokument_name
from swki.baugruppe.referenzen import loese_im_teil
from swki.baugruppe.sw_bewegung import SwMechanik
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.eigenschaften import lies_eigenschaften
from swki.compiler.fehler import BauFehler
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.befehle import pruefe_lauf_gebaut, schreibe_pruefbericht
from swki.pruefung.bewertung import bewerte, messpunkt_schluessel
from swki.pruefung.bilder import kopplungsbild, screenshots
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


def gewindebohrungen_kaufteil(teil_spec: dict) -> list[dict]:
    """Eintrittspunkte (STEP-Koordinaten = Teilkoordinaten) aller Gewindepositionen eines Kaufteils (Spec 3c §6.4)."""
    return [{"feature": g, "instanz": i, "punkt": tuple(p)}
            for g, w in teil_spec.get("gewinde", {}).items() for i, p in enumerate(w["positionen"], start=1)]


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
        elif q.art in ("teil", "kaufteil"):
            liste = (gewindebohrungen_teil(q.spec, protokoll["teile"][q.datei]) if q.art == "teil"
                     else gewindebohrungen_kaufteil(q.spec))
            for b in liste:
                bohrungen.append({"teil": i.id, "feature": b["feature"], "instanz": b["instanz"],
                                  "eintritt": transformiere(Messgeometrie("punkt", b["punkt"]), transformationen[i.id])})
    interferenzen = [{"paar": sorted(namen.get(n, n) for n in paar), "volumen": volumen}
                     for paar, volumen in sw_baugruppe.interferenzen(asm)]
    mates = sw_baugruppe.verknuepfungen(asm)
    ids = {v["id"] for v in kopplungen(bg.spec)}
    gelesen: dict[str, dict | str] = {}
    for f in mates:
        if f.Name in ids:
            try:
                gelesen[f.Name] = sw_baugruppe.lies_kopplung(f)
            except Exception as e:  # COM-Fehler beim Lesen → Mangel statt Abbruch der Prüfung
                gelesen[f.Name] = f"Kopplung {f.Name} nicht lesbar: {e}"
    return BaugruppenMesswerte(
        rebuild_fehler=rebuild_fehler(asm),
        verknuepfungen={f.Name: sw_baugruppe.fehlercode(f) for f in mates},
        komponenten=zustand, stueckliste=stueckliste, interferenzen=interferenzen,
        box=sw_baugruppe.huellquader(asm), masse_kg=sw_baugruppe.masse_kg(asm), eigenschaften=lies_eigenschaften(asm),
        messpunkte=messpunkte, schrauben=schrauben, gewindebohrungen=bohrungen, teilberichte=teilberichte,
        lagen=transformationen, kopplungen=gelesen, unterdrueckt=[f.Name for f in mates if sw_baugruppe.ist_unterdrueckt(f)],
        gewinde_modelle={s: k.get("gewinde_modell", {}) for s, k in protokoll.get("kaufteile", {}).items()})


def _kopplungsbilder(app, asm, bg: Baugruppe, protokoll: dict, messwerte: BaugruppenMesswerte, ordner: Path) -> dict:
    """Je Kopplung ein Bild entlang der Radachse von Seite a, gezoomt auf beide Komponenten, die übrigen Komponenten
    während der Aufnahme verborgen (Spec 4b §5.7)."""
    komponenten = _komponenten(asm, protokoll)
    bilder = {}
    for v in kopplungen(bg.spec):
        ka, kb = v["a"]["komponente"], v["b"]["komponente"]
        if ka not in komponenten or kb not in komponenten:
            continue
        achse = in_baugruppe(verzahnung_der_seite(bg.quellen, v["a"]), messwerte.lagen[ka]).achse
        name = f"{v['id']}-eingriff"
        uebrige = [k for iid, k in komponenten.items() if iid not in (ka, kb)]
        bilder[name] = kopplungsbild(app, asm, ordner / f"{name}.png", achse, [komponenten[ka], komponenten[kb]], uebrige)
    return bilder


def _grenzen(bg: Baugruppe) -> dict:
    return {v.id: v for v in verknuepfungen(bg.spec, bg.quellen) if v.typ in GRENZEN}


def _dokumente_der_grenzen(bg: Baugruppe) -> set[str]:
    """Quelldokumente, deren Flächen die Grenzverknüpfungen nennen: sie bleiben für die treibenden Verknüpfungen offen."""
    return {bg.quellen[basis(seite["komponente"])].schluessel_dokument
            for v in _grenzen(bg).values() for seite in (v.a, v.b)}


def _komponenten(asm, protokoll: dict) -> dict:
    """Instanz-ID → IComponent2 der geöffneten Baugruppe (SolidWorks-Namen aus dem Bauprotokoll)."""
    namen = {k["sw_name"]: k["id"] for k in protokoll.get("komponenten", [])}
    return {namen.get(k.Name2, k.Name2): k for k in sw_baugruppe.komponenten(asm)}


def _pruefe_bewegungen(app, asm, bg: Baugruppe, protokoll: dict, kontexte: dict, messwerte, standard: dict,
                       ordner: Path) -> tuple[list[dict], dict, dict]:
    """Bewegungsprüfung am geöffneten Lauf-Dokument (Spec 4a §8.2); liefert Prüfungen, Bewegungsbericht und Bilder.
    Bei statischen Fehlern oder einem Fehler der Läufe entstehen Mängel bewegung:<name> statt eines Abbruchs (nur
    SpeicherKnapp bricht ab). Die treibenden Verknüpfungen verschwinden wieder; der Aufrufer schließt ohne Speichern."""
    komponenten = _komponenten(asm, protokoll)

    def entitaet(seite: dict):
        ctx = kontexte[bg.quellen[basis(seite["komponente"])].schluessel_dokument]
        ref = loese_im_teil(ctx, {k: v for k, v in seite.items() if k != "komponente"})
        return sw_baugruppe.in_baugruppe(komponenten[seite["komponente"]], ref)

    def mechanik() -> SwMechanik:
        return SwMechanik(app, asm, _grenzen(bg), entitaet, komponenten, ordner / "bilder")

    bws = bewegungen(bg.spec, standard)
    tol = standard["toleranzen"]["anker_mm"]
    pruefungen, bericht, laeufe = bewegungen_oder_ersatz(
        bg.spec, bws, messwerte, mechanik, {frozenset(i["paar"]) for i in messwerte.interferenzen},
        standard["speicher_grenze_mb"], tol, [v.id for v in verknuepfungen(bg.spec, bg.quellen)])
    bilder = {Path(p).stem: p for lauf in laeufe
              for p in [*lauf.bilder.values(), *(k["bild"] for k in lauf.kollisionen)] if p}
    return pruefungen, bericht, bilder


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
    mit_bewegung = bool(bg.spec.get("bewegungen"))
    offen_halten = _dokumente_der_grenzen(bg) if mit_bewegung else set()
    app = verbinde(r.sw_jahr)
    teilberichte, geometrie, kontexte, offen = {}, {}, {}, []
    bewegung = None
    try:
        for datei, teil_spec in bg.teile.items():
            model = oeffne(app, ordner / dokument_name(bg.quellen[bg.komponente_von(datei)], auftrag, standard))
            behalten = False
            try:
                ctx = kontext_aus_datei(app, model, teil_spec, bg.pfad.parent / datei, tol, protokoll["teile"][datei])
                with sw.schnell(app, model):   # Messen ohne Bildschirmarbeit (Messstand Umbau 5)
                    teilberichte[datei] = bewerte(teil_spec, messe(ctx, soll_teile[datei]), standard, soll_teile[datei])
                    geometrie[datei] = _geometrie(ctx, bedarf.get(datei, []))
                if datei in offen_halten:
                    kontexte[datei], behalten = ctx, True
                    offen.append(model)
            finally:
                if not behalten:
                    sw.schliesse(app, model)
        for q in {q.schluessel: q for q in bg.quellen.values() if q.art in ("normteil", "kaufteil")}.values():
            if q.schluessel not in bedarf and q.schluessel not in offen_halten:
                continue
            pfad = ordner / dokument_name(q, auftrag, standard)
            model = oeffne(app, pfad)
            behalten = False
            try:
                ctx = kontext_aus_datei(app, model, q.spec, pfad.with_suffix(".yaml"), tol, {"knoten": []})
                geometrie[q.schluessel] = _geometrie(ctx, bedarf.get(q.schluessel, []))
                if q.schluessel in offen_halten:
                    kontexte[q.schluessel], behalten = ctx, True
                    offen.append(model)
            finally:
                if not behalten:
                    sw.schliesse(app, model)
        asm = oeffne(app, asm_pfad)
        try:
            sw_baugruppe.aufloesen(asm)
            with sw.schnell(app, asm):
                messwerte = _messe_baugruppe(asm, bg, protokoll, geometrie, teilberichte)
            bilder = screenshots(app, asm, ordner / "bilder")
            bilder |= _kopplungsbilder(app, asm, bg, protokoll, messwerte, ordner / "bilder")
            if mit_bewegung:
                bewegung = _pruefe_bewegungen(app, asm, bg, protokoll, kontexte, messwerte, standard, ordner)
        finally:
            sw.schliesse(app, asm)  # ohne Speichern: keine treibende Verknüpfung bleibt in der Datei (Spec 4a §8)
    finally:
        for model in reversed(offen):
            sw.schliesse(app, model)
    bericht = {
        "auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(asm_pfad), "art": "baugruppe",
        **bewerte_baugruppe(bg.spec, bg.quellen, messwerte, standard,
                            stueckliste_soll(bg.spec, freigegebene_quellen(bg), auftrag, standard)),
        "normteile": protokoll.get("normteile", {}), "bilder": bilder,
        **({"kaufteile": protokoll["kaufteile"]} if protokoll.get("kaufteile") else {}),
    }
    if bewegung is not None:
        bericht = ergaenze_bericht(bericht, *bewegung)
    schreibe_pruefbericht(spec_pfad, lauf, ordner, bericht)
    return bericht
