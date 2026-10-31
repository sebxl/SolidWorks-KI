"""swki bauen für art: aenderung (Spec Bestandsdateien §6): frische Kopie der Bestandskopie, Punkte in Spec-Reihenfolge, nach
jedem Punkt Neuaufbau, vor dem Speichern alle Konfigurationen prüfen, Speichern an Ort und Stelle.

Anders als beim Teil wird nach einem Fehler **nie** gespeichert: Eine fehlgeschlagene Änderung kann eine Konfiguration still
und dauerhaft beschädigen, `Save3` meldet trotzdem Erfolg (S18c3). Der Lauf-Ordner behält dann die unveränderte Kopie, der
nächste Lauf beginnt ohnehin wieder ab der Bestandskopie. Die Datei behält ihren Namen (kein `<auftrag>_<name>`), geöffnet wird
nur die Lauf-Kopie, nie Bestandskopie oder Original."""

import time
from pathlib import Path

from swki.aenderungen import pruefe_unveraendert, pruefsummen, vermerke_befund
from swki.auftrag import auftrag_name, lauf_belegt, lauf_datei, lauf_ordner, naechster_lauf
from swki.bestand import punkte
from swki.bestand.ablage import bestand_ordner, lauf_kopie, pruefe_kopie
from swki.bestand.fehler import BESTAND_VERSION_AELTER, BestandFehler
from swki.bestand.spec import GEOMETRIE_TYPEN, aufnahme_zu, lade_aenderung
from swki.bestand.sw_bestand import _geometrie, _schalte, baum_features, lizenz, speichere_an_ort, whats_wrong
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.compiler.ablauf import durchlaufe
from swki.compiler.bauen import BauAbbruch
from swki.compiler.fehler import REBUILD_FEHLER, BauFehler, fehler_dict
from swki.compiler.protokoll import Knoten, Protokoll
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.messen import oeffne
from swki.spec.freigabe import pruefe_freigabe
from swki.verbindung import verbinde

_TOL_VOLUMEN_MM3, _TOL_VOLUMEN_ANTEIL = 0.01, 1e-6  # Rauschen der Massenberechnung; feine Abweichungen zeigt die Differenz


def bekannte_fehler_in(aufnahme: dict, konfiguration: str) -> set[str]:
    """Features, deren Fehler die Datei in dieser Konfiguration schon hatte. Warnungen zählen nicht."""
    return {e["feature"] for e in aufnahme["neuaufbau"] if e["konfiguration"] == konfiguration and not e["warnung"]}


def neue_fehler(fehler: list[dict], aufnahme: dict, konfiguration: str) -> list[str]:
    """Was die Aufnahme nicht kennt, als Tripel (Konfiguration, Feature, Code): Auch ein anderer Code am selben Feature ist neu."""
    bekannt = {(e["konfiguration"], e["feature"], e["code"]) for e in aufnahme["neuaufbau"] if not e["warnung"]}
    return [f"{e['feature']}: Code {e['code']}" for e in fehler
            if not e["warnung"] and (konfiguration, e["feature"], e["code"]) not in bekannt]


def _pruefe_baum(k: str, ist: list[str], aufnahme: dict, geloescht: set[str]) -> None:
    """Der Baum gegen die Aufnahme. Jedes Bestandsfeature muss noch da sein, außer ein `loeschen`-Punkt hat es genommen: Auch ein
    Skript darf keines verschwinden lassen, und ein anderer Name zählt als verschwunden. Die Reihenfolge der gebliebenen muss
    stimmen, neue stehen am Ende oder hinter `nach`; ein verschobenes Bestandsfeature sieht sonst nichts (S18c3: die Rippe
    steht vorn, kein Fehler in der anderen Konfiguration)."""
    soll = aufnahme["reihenfolge"][k]
    if fehlt := [n for n in soll if n not in ist and n not in geloescht]:
        raise BauFehler(REBUILD_FEHLER, f"Konfiguration {k}: Bestandsfeature fehlt, kein loeschen-Punkt nennt es: "
                                        f"{', '.join(fehlt)}", schritt="stand")
    gemeinsam = set(ist) & set(soll)
    if [n for n in ist if n in gemeinsam] != [n for n in soll if n in gemeinsam]:
        raise BauFehler(REBUILD_FEHLER, f"Konfiguration {k}: Reihenfolge der Features weicht von der Aufnahme ab", schritt="stand")


def _pruefe_volumen(k: str, volumen: float | None, aufnahme: dict, betroffen: set[str]) -> None:
    alt = aufnahme["geometrie"].get(k, {}).get("volumen")
    if alt and not volumen:
        raise BauFehler(REBUILD_FEHLER, f"Konfiguration {k}: Volumen weg (vorher {alt} mm³)", schritt="stand")
    if alt and k not in betroffen and abs(volumen - alt) > max(_TOL_VOLUMEN_MM3, _TOL_VOLUMEN_ANTEIL * alt):
        raise BauFehler(REBUILD_FEHLER, f"Konfiguration {k}: Volumen {volumen} statt {alt} mm³, obwohl kein Punkt sie nennt",
                        schritt="stand")


def pruefe_stand(model, aufnahme: dict, liste: list[dict], geloescht: set[str]) -> None:
    """Fehler, Baum und Volumen in **allen** Konfigurationen, unmittelbar vor dem Speichern (S18c3): `whats_wrong` und der Baum
    sehen nur die aktive. `geloescht`: was die `loeschen`-Punkte genommen haben. Die aktive Konfiguration kommt zuletzt und
    bleibt für `Save3` stehen (Plan Review Focus 4)."""
    aktiv = aufnahme["aktiv"]
    betroffen = {k for p in liste if p["typ"] in GEOMETRIE_TYPEN for k in punkte._konfigurationen(p, aufnahme)}
    namen = None
    for k in [*(x for x in aufnahme["konfigurationen"] if x != aktiv), aktiv]:
        _schalte(model, k)
        ok = model.EditRebuild3
        fehler = whats_wrong(model)
        neu = neue_fehler(fehler, aufnahme, k)
        if neu or not (ok or any(not e["warnung"] for e in fehler)):
            raise BauFehler(REBUILD_FEHLER, f"Konfiguration {k}: {'; '.join(neu) or 'EditRebuild3 meldet Fehler'}", schritt="stand")
        ist = [f.Name for f in baum_features(model)]
        if namen is not None and set(ist) != namen:
            raise BauFehler(REBUILD_FEHLER, f"Konfiguration {k}: andere Features als in den übrigen", schritt="stand")
        namen = set(ist)
        _pruefe_baum(k, ist, aufnahme, geloescht)
        _pruefe_volumen(k, _geometrie(model)["volumen"], aufnahme, betroffen)


def _pruefe_neuaufbau(ctx, aufnahme: dict) -> None:
    """Nach jedem Punkt. `sw.rebuild` kennt nur Featurenamen, damit Handler bekannte Fehler übergehen; ein neuer Code am selben
    Feature muss aber beim Punkt auffallen, ein späterer Punkt könnte das Feature unterdrücken und den Fehler verstecken."""
    sw.rebuild(ctx.model)
    if neu := neue_fehler(whats_wrong(ctx.model), aufnahme, aufnahme["aktiv"]):
        raise BauFehler(REBUILD_FEHLER, "; ".join(neu), schritt="rebuild")


def _wende_punkte_an(app, model, spec: dict, spec_pfad: Path, tol_mm: float, aufnahme: dict, protokoll: Protokoll,
                     geloescht: set[str]):
    """Sammelt in `geloescht`, was `loeschen`-Punkte genommen haben; sie prüfen selbst, dass das erlaubt war."""
    ctx = punkte.kontext(app, model, spec, spec_pfad, tol_mm)

    def rufe(knoten: Knoten, p: dict) -> None:
        namen = punkte.punkt_handler(p["typ"])(ctx, p, aufnahme)
        knoten.sw_name = ", ".join(namen) or None
        if p["typ"] == "loeschen":
            geloescht.update(namen)
        if (ergebnis := ctx.ergebnisse.get(p["id"])) is not None:
            knoten.punkte = [list(q) for q in ergebnis.punkte] or None

    return durchlaufe(ctx, protokoll, spec["punkte"], rufe, lambda c: _pruefe_neuaufbau(c, aufnahme))


def _aendere_und_speichere(app, model, spec: dict, spec_pfad: Path, tol_mm: float, aufnahme: dict, protokoll: Protokoll,
                           pfad: Path) -> Exception | None:
    """Der erste Fehler oder None; gespeichert ist die Datei nur bei None."""
    geloescht: set[str] = set()
    try:
        with protokoll.phase("bauen"), sw.bekannte_fehler(bekannte_fehler_in(aufnahme, aufnahme["aktiv"])):
            if fehler := _wende_punkte_an(app, model, spec, spec_pfad, tol_mm, aufnahme, protokoll, geloescht):
                return fehler
            pruefe_stand(model, aufnahme, spec["punkte"], geloescht)
        with protokoll.phase("speichern"):
            speichere_an_ort(model, pfad)
    except Exception as e:  # jeder Fehler (auch COM) heißt: nicht speichern
        return e
    return None


def _fehler_mit_punkt(fehler: Exception, protokoll: Protokoll) -> dict:
    """Spec §6: Abbruch mit Punkt-ID, Schritt, Code und Meldung. Scheitert die Prüfung davor oder danach, gibt es keinen Punkt."""
    d = fehler_dict(fehler)
    pid = next((k.id for k in protokoll.knoten if k.status == "fehler"), None)
    return d if pid is None else {**d, "punkt": pid, "meldung": f"Punkt {pid}: {d['meldung']}"}


def bauen(spec_pfad: Path, lauf: int | None = None, verwerfen: bool = False, uebernommen: bool = False,
          hochstufen: bool = False) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_aenderung(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is not None and lauf_belegt(r, auftrag, spec_pfad, lauf):
        raise SwkiFehler(f"Lauf {lauf} von {auftrag} existiert schon – ohne --lauf baut swki den nächsten freien Lauf")
    aufnahme = aufnahme_zu(spec, spec_pfad)  # BESTAND_UNBEKANNT, BESTAND_VERALTET
    kopie = bestand_ordner(r, auftrag, spec["bestand"]["aufnahme"]) / aufnahme["datei"]["name"]
    pruefe_kopie(aufnahme, kopie)  # BESTAND_ABWEICHEND
    aelter = bool(aufnahme["datei"].get("version_aelter"))
    if aelter and not hochstufen:
        raise BestandFehler(BESTAND_VERSION_AELTER, f"{kopie.name} stammt aus einer älteren SolidWorks-Version: Mit --hochstufen "
                                                    f"bestätigen, dass sie danach nur noch mit SolidWorks {r.sw_jahr} oder "
                                                    "neuer lesbar ist", sw_jahr=r.sw_jahr)
    uebergangen = pruefe_unveraendert(r, auftrag, spec_pfad, verwerfen, uebernommen)
    if lauf is None:
        lauf = naechster_lauf(r, auftrag, spec_pfad)
    ordner = lauf_ordner(r, auftrag, lauf)
    protokoll = Protokoll(auftrag, spec_pfad.name, lauf, r.sw_jahr)
    protokoll.hochgestuft = aelter
    beginn = time.perf_counter()

    app = verbinde(r.sw_jahr)
    vermerke_befund(protokoll, uebergangen, verwerfen)
    pfad = lauf_kopie(kopie, ordner)
    with protokoll.phase("vorbereiten"):
        model = oeffne(app, pfad)
    fehler = None
    try:
        fehler = _aendere_und_speichere(app, model, spec, spec_pfad, standard["toleranzen"]["anker_mm"], aufnahme, protokoll, pfad)
        protokoll.lizenz = lizenz(app, model)
    finally:
        try:
            sw.schliesse(app, model)  # ohne Speichern; nach einem Fehler bleibt die unveränderte Kopie
        except Exception as e:  # darf den Baufehler nicht verdecken, und ohne einen steht er im Protokoll
            fehler = fehler or e
    if fehler is None:
        protokoll.dateien = {"teil": str(pfad)}
        protokoll.sha256 = pruefsummen(ordner, [pfad])
    protokoll.status = "fehler" if fehler else "ok"
    protokoll.fehler = _fehler_mit_punkt(fehler, protokoll) if fehler else None
    protokoll.dauer_s = round(time.perf_counter() - beginn, 3)
    protokoll.schreibe(ordner / "protokoll.json")
    protokoll.schreibe(lauf_datei(spec_pfad, lauf, "protokoll"))
    ergebnis = {
        "status": protokoll.status,
        "auftrag": auftrag,
        "lauf": lauf,
        "ordner": str(ordner),
        "dateien": protokoll.dateien,
        "knoten": [{"id": k.id, "status": k.status, "sw_name": k.sw_name} for k in protokoll.knoten],
        "fehler": protokoll.fehler,
        "dauer_s": protokoll.dauer_s,
    }
    if fehler:
        raise BauAbbruch(ergebnis)
    return ergebnis
