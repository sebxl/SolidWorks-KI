"""swki pruefen für art: aenderung an einer Baugruppe (Spec Bestandsdateien §7, §8.1a, §8.3, §8.4, §8.7; Plan Etappe 2 Task 11).

Hier laufen die Prüfungen zusammen: je Datei mit geänderter SHA-256 und Punkten die Teil-Prüfung von Etappe 1 (`pruefe_teil`,
Einträge mit Präfix `<rel>/`, außer `punkt:<id>`), je Teil-Quelle die Messung gegen ihre freigegebene Spec (ebenfalls `<rel>/`,
Normteile und Kaufteile sind in ihrer Bibliothek geprüft), dann die Hauptbaugruppe (`vergleiche_baugruppe`, `vergleiche_dateien`,
`vergleiche_bewegungen`, eine Etappe-1-Prüfung der Hauptdatei über `haupt_scheibe`, Pfadschutz). Gleiche SHA-256 plus gleiche
Transformation beweisen, dass eine Komponente unverändert ist; darum wird nur verglichen, was sich geändert hat, auch in großen
Baugruppen. Eine geänderte Datei ohne Punkt ist ein Mangel `dateien`, sie braucht keine Teil-Prüfung.

Die Bestandskopie der Baugruppe bleibt zu: Vorher steht in der Aufnahme, ihre Bilder hat `aufnehmen` gemacht. Teile gehen einzeln
über `vorher_<rel flach>` in die Differenz und sind zu, bevor die Baugruppe aufgeht, gleiche Dateinamen sind nie zugleich offen
(S18d). Alles geht nur lesend auf, gelesen wird unsichtbar, Kollision, Bilder und Fahrt haben ein Fenster: Ohne Fenster ist
`InterferenceDetectionManager` `None` (S19d P.d1), `kollision` stünde immer auf `ok: None`. Nichts wird gespeichert, die
treibenden Verknüpfungen der Fahrt bleiben im Speicher.

`SpeicherKnapp` bricht ohne Bericht ab wie in Stufe 4a. Ein `BauFehler` der Fahrt (Kollision nicht lesbar, Stand kippt) nimmt nur
den Nachweis: `bewegung:*` steht dann auf `ok: None`, sonst fehlte der Bericht zu allem anderen.

UNGEMESSEN: Diese Schicht steht gegen Attrappen, S19 kann sie korrigieren. Offen: Fahrt und Bilder an einem nur lesend geöffneten
Lauf, Dauer von `lies_baugruppe` ohne `sw.schnell`, Fenster je Teil-Bild neben der großen Baugruppe."""

from pathlib import Path

from swki.aenderungen import sha256_datei
from swki.auftrag import auftrag_name, lauf_ordner
from swki.bestand.ablage import bestand_ordner, flach, lade_datei_aufnahme, lade_dateien
from swki.bestand.aufnahme_baugruppe import BEWEGUNG_ABDECKUNG, _Messung
from swki.bestand.bau_baugruppe import pruefe_bestand
from swki.bestand.bewegung_bestand import (abdeckung, bekannte_paare, fahre_bestand, grenzen_der_aufnahme, ohne_fahrt,
                                           vergleiche_bewegungen)
from swki.bestand.fehler import BestandFehler
from swki.bestand.pfade import offene_dokumente, oeffne_in, pruefe_geladen
from swki.bestand.pruefen import _skript_lauf, bewerte_aenderung, pruefe_teil
from swki.bestand.scheiben import dateien_mit_punkten, haupt_scheibe, scheibe
from swki.bestand.sw_baugruppe_bestand import VERKNUEPFUNG_UNERREICHT, lies_baugruppe, lies_kollisionen, mechanik_fuer
from swki.bestand.vergleich import vergleiche
from swki.bestand.vergleich_baugruppe import vergleiche_baugruppe, vergleiche_dateien
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.fehler import BauFehler
from swki.pruefung.befehle import schreibe_pruefbericht
from swki.pruefung.bewertung import bewerte, eintrag
from swki.pruefung.bilder import ANSICHTEN, screenshots
from swki.pruefung.messen import kontext_aus_datei, messe
from swki.spec.freigabe import freigegebene_spec
from swki.verbindung import verbinde

BILDER_VORHER_FEHLEN = "BILDER_VORHER_FEHLEN"  # Warnung: Die Aufnahme hat keine Bilder der Baugruppe


def _ist_summen(ordner: Path, protokoll: dict) -> dict[str, str | None]:
    """SHA-256 der Dateien des Protokolls, am Lauf gemessen: Geprüft wird, was dort liegt. `None`: nicht lesbar, also nie gleich."""
    def summe(rel: str) -> str | None:
        try:
            return sha256_datei(ordner / rel)
        except OSError:
            return None

    return {rel: summe(rel) for rel in protokoll.get("sha256") or {}}


def _dateien_pruefung(spec: dict, dateien: dict, ist: dict, neue_dateien: list[str], protokoll: dict) -> dict:
    """`vergleiche_dateien`, dazu der Stand des Baus: Was nach dem Bau anders ist als in `protokoll.sha256`, ist nicht geprüft, was gebaut
    wurde, auch bei einer Datei mit Punkt oder einer neuen, deren SHA-256 sonst niemand kennt."""
    e = vergleiche_dateien(spec, dateien, ist, neue_dateien)
    summen = protokoll.get("sha256") or {}
    if not (spaeter := sorted(rel for rel, sha in ist.items() if sha is not None and sha != summen[rel])):
        return e
    text = f"Nach dem Bau geändert: {', '.join(spaeter)}"
    return {**e, "ok": False, "nach_dem_bau": spaeter, "hinweis": "; ".join(filter(None, [e.get("hinweis"), text]))}


def _mit_datei(e: dict, rel: str) -> dict:
    return e if e["id"].startswith("punkt:") else {**e, "id": f"{rel}/{e['id']}"}


def _pruefe_teile(app, m: _Messung, r, spec: dict, freigegeben: dict, spec_pfad: Path, vorher: dict, ordner: Path, quelle: Path,
                  ist: dict, standard: dict, protokoll: dict) -> tuple[dict[str, dict], list[dict]]:
    """(rel → Ergebnis von `pruefe_teil`, Einträge für Punkte einer Datei, die nicht verglichen wurde): Eine Datei mit Punkten und
    gleicher SHA-256 hat nichts bewirkt, eine nicht lesbare beweist nichts. Beides ist kein Grund zu schweigen, `dateien` allein
    nennt keinen Punkt."""
    tol, nummer = standard["toleranzen"]["anker_mm"], spec["bestand"]["aufnahme"]
    ergebnisse, ohne = {}, []
    for datei in dateien_mit_punkten(spec):
        teil = scheibe(spec, datei, vorher["dateien"])
        rel = teil["bestand"]["datei"]
        sha = ist.get(rel)
        if sha is None or sha == vorher["dateien"][rel]["sha256"]:
            ok, grund = (None, "nicht lesbar") if sha is None else (False, "unverändert, nichts gespeichert")
            ohne += [eintrag(f"punkt:{p['id']}", ok, knoten=[p["id"]], hinweis=f"{rel} ist im Lauf {grund}, der Punkt ist nicht geprüft")
                     for p in teil["punkte"]]
            continue
        aufnahme = lade_datei_aufnahme(r, auftrag_name(spec_pfad), nummer, rel)
        with m.phase(f"teile:{rel}"):
            ergebnisse[rel] = pruefe_teil(app, teil, scheibe(freigegeben, datei, vorher["dateien"]), spec_pfad, aufnahme,
                                          quelle / rel, ordner / rel, ordner, tol, standard, protokoll, bilder_unter=flach(rel))
    return ergebnisse, ohne


def _miss_neues_teil(app, pfad: Path, ordner: Path, soll: dict, spec_datei: Path, standard: dict, protokoll_teil: dict) -> dict:
    """Wie `swki.baugruppe.pruefen`: gegen die freigegebene Teil-Spec, aus der auch gebaut wurde. Unsichtbar, nur lesend."""
    model = oeffne_in(app, pfad, ordner, sichtbar=False, nur_lesen=True)
    try:
        ctx = kontext_aus_datei(app, model, soll, spec_datei, standard["toleranzen"]["anker_mm"], protokoll_teil)
        with sw.schnell(app, model):  # Messen ohne Bildschirmarbeit (Messstand Umbau 5)
            return bewerte(soll, messe(ctx, soll), standard, soll)
    finally:
        sw.schliesse(app, model)


def _pruefe_neue_teile(app, m: _Messung, spec: dict, spec_pfad: Path, ordner: Path, neue_dateien: list[str], standard: dict,
                       protokoll: dict) -> tuple[list[dict], dict]:
    """(Einträge mit Präfix `<rel>/`, rel → `{bestanden, maengel}`) je Teil-Quelle: Ein Punkt belegt nur, dass die Komponente da ist, die
    Datei selbst misst erst dies. Scheitert die Messung, steht `<rel>/messung` auf `ok: None`; ein fremder Pfad bleibt laut (§8.1a)."""
    eintraege, uebersicht = [], {}
    for datei in sorted({p["quelle"]["teil"] for p in spec["punkte"] if "teil" in p.get("quelle", {})}):
        rel = datei  # bis die Datei im Lauf gefunden ist
        try:
            soll = freigegebene_spec(spec_pfad.parent / datei)
            rel = next(n for n in neue_dateien if Path(n).stem.casefold() == soll["name"].casefold())
            with m.phase(f"teile:{rel}"):
                bewertet = _miss_neues_teil(app, ordner / rel, ordner, soll, spec_pfad.parent / datei, standard, protokoll["teile"][datei])
        except BestandFehler:
            raise
        except (Exception, StopIteration) as e:
            eintraege.append(eintrag(f"{rel}/messung", None, knoten=[], hinweis=f"{datei} nicht gemessen: {type(e).__name__}: {e}"))
            uebersicht[rel] = {"bestanden": False, "maengel": 1}
            continue
        eintraege += [_mit_datei(e, rel) for e in bewertet["pruefungen"]]
        uebersicht[rel] = {"bestanden": bewertet["bestanden"], "maengel": len(bewertet["maengel"])}
    return eintraege, uebersicht


def _lies_lauf(app, m: _Messung, asm_pfad: Path, ordner: Path, weitere: list[str]) -> tuple[dict, dict]:
    """(Aufnahme des Laufs nach dem Neuaufbau ohne `kollisionen`, Eintrag `pfade`): unsichtbar, die Baugruppe geht wieder zu."""
    with m.phase("oeffnen"):
        offen = offene_dokumente(app)
        asm = oeffne_in(app, asm_pfad, ordner, sichtbar=False, nur_lesen=True)
    try:
        pfade = pruefe_geladen(app, asm, ordner, offen)
        with m.phase("lesen"):
            nachher = lies_baugruppe(app, asm, weitere, kollision=False)
    finally:
        sw.schliesse(app, asm)
    return nachher, pfade


def _fahre(app, asm, spec: dict, vorher: dict, nachher: dict, neue: dict, ersetzt: dict, bilder: Path, standard: dict,
           start_mb: float | None) -> dict:
    """Das Feld `bewegungen` des Laufs (§8.4). Bekannt sind die Verknüpfungsfehler des Bestands, nicht die des Laufs: Neue stoppen die
    Fahrt."""
    grenzen = grenzen_der_aufnahme(nachher)
    if not grenzen:
        return {}
    bekannt = bekannte_paare(vorher, spec, neue, ersetzt, nachher)
    try:
        return fahre_bestand(mechanik_fuer(app, asm, grenzen, vorher, bilder), nachher, grenzen, standard["bewegung_schritte"], bekannt,
                             standard["speicher_grenze_mb"], standard["toleranzen"]["anker_mm"], start_mb)
    except BauFehler as e:
        return ohne_fahrt(grenzen, f"Fahrt abgebrochen: {e}")


def _im_fenster(app, m: _Messung, asm_pfad: Path, ordner: Path, spec: dict, vorher: dict, nachher: dict, neue: dict,
               ersetzt: dict, standard: dict, start_mb: float | None) -> tuple[list[dict] | None, dict, dict]:
    """(`kollisionen`, Bilder, `bewegungen`) im Fenster, Kollision und Fahrt brauchen es (S19d); geschlossen wird ohne Speichern,
    auch nach `SpeicherKnapp`. Neu aufgebaut wird zuerst: Ein geändertes Teil neben einer ungespeicherten Baugruppe zeigte sonst
    den alten Stand, Kollision, Bilder und Fahrt gälten nicht dem Lauf. `nachher` bekommt die Kollisionen vor der Fahrt."""
    with m.phase("fenster"):
        asm = oeffne_in(app, asm_pfad, ordner, sichtbar=True, nur_lesen=True)
    try:
        with m.phase("neuaufbau"):
            asm.ForceRebuild3(False)
        with m.phase("kollision"):
            kollisionen = lies_kollisionen(asm)
        with m.phase("bilder"):
            bilder = screenshots(app, asm, ordner / "bilder")
        with m.phase("fahrt"):
            nachher = {**nachher, "kollisionen": kollisionen}
            return kollisionen, bilder, _fahre(app, asm, spec, vorher, nachher, neue, ersetzt, ordner / "bilder", standard, start_mb)
    finally:
        sw.schliesse(app, asm)


def _bilder_vorher(quelle: Path) -> dict[str, str]:
    """Die Bilder, die `aufnehmen` von der Bestandskopie gemacht hat, dieselben Ansichten wie im Lauf. Nur diese: `swki bestand zeige`
    legt seine Bilder daneben."""
    pfade = {name: quelle / "bilder" / f"{name}.png" for name in ANSICHTEN}
    return {name: str(p) for name, p in pfade.items() if p.is_file()}


def _je_datei(teile: dict[str, dict], feld: str) -> dict:
    return {f"{rel}/{name}": pfad for rel, erg in teile.items() for name, pfad in erg[feld].items()}


def _warnungen(r, spec_pfad: Path, spec: dict, vorher: dict, nachher: dict, bilder_vorher: dict) -> list[dict]:
    """Was der Bericht nennen muss, ohne dass es ein Mangel ist: die Warnungen beider Stände (Gegenprobe `VERKNUEPFUNG_UNERREICHT`,
    `BESTAND_OFFEN`, Abdeckung), die Gegenprobe der Unterbaugruppen aus ihrer Aufnahme, fehlende Vorher-Bilder. Jede einmal."""
    auftrag, nummer = auftrag_name(spec_pfad), spec["bestand"]["aufnahme"]
    aus = [*(vorher.get("warnungen") or ()), *(nachher.get("warnungen") or ())]
    aus += [{"code": BEWEGUNG_ABDECKUNG, "meldung": h} for h in abdeckung(nachher)]
    for rel in (rel for rel, d in vorher["dateien"].items() if d.get("art") == "baugruppe"):
        try:
            aus += [{**w, "datei": rel} for w in lade_datei_aufnahme(r, auftrag, nummer, rel).get("warnungen") or ()]
        except BestandFehler as e:
            aus.append({"code": VERKNUEPFUNG_UNERREICHT, "datei": rel, "verknuepfungen": None,
                        "meldung": f"Gegenprobe von {rel} nicht gelesen: {e}"})
    if not bilder_vorher:
        aus.append({"code": BILDER_VORHER_FEHLEN,
                    "meldung": "Vorher-Bilder der Baugruppe fehlen in der Aufnahme, der Prüfer sieht nur den Lauf"})
    eindeutig: dict[tuple, dict] = {}
    for w in aus:
        eindeutig.setdefault((w["code"], w.get("datei"), w["meldung"]), w)
    return list(eindeutig.values())


def _nicht_abgedeckt(vorher: dict, nachher: dict) -> list[str]:
    """Was die Prüfung nicht abdeckt, nie stumm (§8.4): Bewegung, und was die Kollision nur in der aktiven Konfiguration sieht."""
    aus = list(dict.fromkeys([*abdeckung(vorher), *abdeckung(nachher)]))
    if uebrige := [k for k in nachher["konfigurationen"] if k != nachher["aktiv"]]:
        was = "Kollisionen und Fahrt" if nachher["bewegungen"] else "Kollisionen"
        aus.append(f"{was} nur in der aktiven Konfiguration {nachher['aktiv']} geprüft, nicht in: {', '.join(uebrige)}")
    return aus


def _bestandsfehler(vorher: dict, pruefungen: list[dict]) -> dict:
    """Was schon der Bestand hatte: kein Mangel des Laufs, aber der Bericht nennt es."""
    je = {e["id"]: e for e in pruefungen}
    return {"neuaufbau": [f"{x['feature']}: Code {x['code']} ({x['konfiguration']})" for x in vorher.get("neuaufbau") or ()
                          if not x["warnung"]],
            "verknuepfungen": je["verknuepfungen"].get("bekannt", []), "kollisionen": je["kollision"].get("bekannt", []),
            "bewegungen": [{"pruefung": e["id"], "hinweis": e.get("hinweis")} for e in pruefungen
                           if "bestand_ok" in e or "bestand_gefahren" in e]}


def _haupt_pruefungen(spec: dict, vorher: dict, nachher: dict, quelle: Path, ordner: Path, protokoll: dict) -> list[dict]:
    """Etappe 1 an der Hauptdatei: Nur `eigenschaft` und `skript` kommen als Punkte an, Baum, Maße, Gleichungen und Konfigurationen
    laufen so mit. Eine Baugruppe hat keine Körper-Differenz: Ein Bereich an der Hauptbaugruppe bleibt unbelegt, das sagt der Punkt."""
    haupt = haupt_scheibe(spec)
    v = {**vorher, "datei": {**vorher["datei"], "ordner": str(quelle)}}  # für `externe_referenzen`
    n = {**nachher, "datei": {"name": vorher["datei"]["name"], "ordner": str(ordner)}}
    aus = vergleiche(haupt, v, n, spec.get("parameter", {}), *_skript_lauf(haupt, protokoll))
    return aus + [eintrag(f"punkt:{pid}", None, knoten=[pid], hinweis="Bereich an der Hauptbaugruppe: Eine Baugruppe hat keine "
                          "Körper-Differenz, er bleibt unbelegt. Geometrie gehört an ein Teil (in_datei)")
                  for pid in sorted({pid for b in haupt["bereiche"] for pid in b["punkte"]})]


def pruefen_baugruppe(spec_pfad: Path, spec: dict, vorher: dict, lauf: int, protokoll: dict, standard: dict, r) -> dict:
    """Aufgerufen von `pruefen.pruefen` nach Freigabe und `aufnahme_zu`. Bericht wie bei einem Teil, zusätzlich: `pruefungen` mit
    Präfix `<rel>/` für Teilprüfungen außer `punkt:<id>`, `differenzen` und `bilder` je Datei, `dateien`, `bewegungen`,
    `bilder_bewegung`, `warnungen`, `bestandsfehler`, `nicht_abgedeckt`, `messung`."""
    auftrag = auftrag_name(spec_pfad)
    ordner, quelle = lauf_ordner(r, auftrag, lauf), bestand_ordner(r, auftrag, spec["bestand"]["aufnahme"])
    asm_pfad = ordner / vorher["datei"]["name"]
    if not asm_pfad.is_file():
        raise SwkiFehler(f"{asm_pfad} fehlt (Lauf {lauf} ohne gespeicherte Baugruppe)")
    dateien = lade_dateien(r, auftrag, spec["bestand"]["aufnahme"])
    pruefe_bestand(quelle, dateien, vorher)  # BESTAND_ABWEICHEND
    neue, ersetzt, neue_dateien = protokoll.get("neue") or {}, protokoll.get("ersetzt") or {}, protokoll.get("neue_dateien") or []
    ist = _ist_summen(ordner, protokoll)

    app = verbinde(r.sw_jahr)
    m = _Messung(app)
    start_mb = m.speicher_mb()  # frisches SolidWorks? (SWKI-11), vor den Teilen und ihren Fenstern
    teile, ohne_vergleich = _pruefe_teile(app, m, r, spec, freigegebene_spec(spec_pfad), spec_pfad, vorher, ordner, quelle, ist,
                                          standard, protokoll)
    neue_teile, teil_uebersicht = _pruefe_neue_teile(app, m, spec, spec_pfad, ordner, neue_dateien, standard, protokoll)
    gelesen, pfade = _lies_lauf(app, m, asm_pfad, ordner, [*vorher["dateien"], *neue_dateien])
    kollisionen, bilder, bewegungen = _im_fenster(app, m, asm_pfad, ordner, spec, vorher, gelesen, neue, ersetzt, standard, start_mb)
    nachher = {**gelesen, "kollisionen": kollisionen, "bewegungen": bewegungen}

    datei_pruefung = _dateien_pruefung(spec, dateien, ist, neue_dateien, protokoll)
    pruefungen = [pfade, datei_pruefung, *vergleiche_baugruppe(spec, vorher, nachher, neue, ersetzt, neue_dateien),
                  *_haupt_pruefungen(spec, vorher, nachher, quelle, ordner, protokoll),
                  *vergleiche_bewegungen(vorher, nachher, spec, neue, ersetzt), *ohne_vergleich, *neue_teile,
                  *(_mit_datei(e, rel) for rel, erg in teile.items() for e in erg["pruefungen"])]
    vor_bilder = _bilder_vorher(quelle)
    bericht = {"auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(asm_pfad),
               "vorher": str(quelle / vorher["datei"]["name"]), **bewerte_aenderung(pruefungen),
               "differenzen": {rel: erg["differenzen"] for rel, erg in teile.items()},
               "teilpruefungen": {**{rel: {"bestanden": erg["bestanden"], "maengel": len(erg["maengel"])} for rel, erg in teile.items()},
                                  **teil_uebersicht},
               "dateien": {feld: datei_pruefung[feld] for feld in ("geaendert", "neu", "erwartet_geaendert")},
               "bewegungen": bewegungen, "bilder": {**bilder, **_je_datei(teile, "bilder")},
               "bilder_vorher": {**vor_bilder, **_je_datei(teile, "bilder_vorher")},
               "bilder_bewegung": {name: pfad for e in bewegungen.values() for name, pfad in (e.get("bilder") or {}).items()},
               "warnungen": _warnungen(r, spec_pfad, spec, vorher, nachher, vor_bilder),
               "bestandsfehler": _bestandsfehler(vorher, pruefungen), "nicht_abgedeckt": _nicht_abgedeckt(vorher, nachher),
               "messung": m.daten}
    schreibe_pruefbericht(spec_pfad, lauf, ordner, bericht)
    return bericht
