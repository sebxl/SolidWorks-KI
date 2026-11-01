"""`swki bestand aufnehmen` für Baugruppen (Spec Bestandsdateien §8.1, §8.1a, §8.5, §8.7; Plan Etappe 2 Task 8).

Das Original wird nur gelesen (Version, Abhängigkeiten, Kopie), geöffnet wird nur die schreibgeschützte Bestandskopie, jedes
Dokument über `oeffne_in`, und gespeichert wird nichts, auch nicht nach der Fahrt: Die treibende Verknüpfung bleibt im Speicher.
Ablauf: Format, Auftrag frei, Version und Abhängigkeiten am Original, Zuordnung der Dateien, Version je Datei, Kopie; dann die
Baugruppe unsichtbar lesen, Kollision, Fahrt, schließen; danach jede Datei einmal einzeln lesen (das Durchschalten der
Konfigurationen soll nicht in einer geladenen Baugruppe laufen), zuletzt das Bild im Fenster. `bestand.json` entsteht als
Letztes: Fehlt sie, lässt sich das Lesen nachholen, eine abgelehnte Aufnahme entfernt ihren Ordner. Zeit und Private Bytes je
Phase stehen in `messung` (§8.7)."""

import time
from contextlib import contextmanager
from pathlib import Path

from swki.bestand.abgleich import mate_name
from swki.bestand.ablage import (AUFNAHME_DATEI, bestand_ordner, herkunft_von, ist_baugruppe, ist_virtuell, kopiere_baugruppe,
                                 lade_aufnahme,
                                 lade_herkunft, ordne_referenzen, pruefe_auftrag_frei, schreibe_aufnahme, schreibe_datei_aufnahme,
                                 schreibe_dateien, schreibe_herkunft, sha_original, spec_laeufe, sperrdateien, verwirf_aufnahme)
from swki.bestand.befehle import zusammenfassung
from swki.bestand.bewegung_bestand import abdeckung, fahre_bestand, grenzen_der_aufnahme, ohne_fahrt, statische_paare
from swki.bestand.fehler import BESTAND_OFFEN, BESTAND_PFAD_FREMD, BESTAND_REFERENZ_EXTERN, BestandFehler
from swki.bestand.pfade import oeffne_in
from swki.bestand.sw_baugruppe_bestand import lies_baugruppe, lies_kollisionen, mechanik_fuer
from swki.bestand.sw_bestand import externe_referenzen, lies_bestand, pruefe_version
from swki.compiler import sw
from swki.konfig import lade_rechner, lade_standard
from swki.pruefung.bilder import screenshots
from swki.speicher import privat_mb
from swki.verbindung import verbinde

BEWEGUNG_ABDECKUNG = "BEWEGUNG_ABDECKUNG"  # Warnung der Aufnahme: was die Bewegungsprüfung nicht abdeckt
_ABLEHNUNG = (BESTAND_PFAD_FREMD, BESTAND_REFERENZ_EXTERN)


class _Messung:
    """Zeit und Private Bytes je Phase. Nicht lesbarer Speicher ist nur eine Lücke, kein Abbruch."""

    def __init__(self, app):
        self.app, self.daten = app, {}

    @contextmanager
    def phase(self, name: str):
        beginn = time.perf_counter()
        try:
            yield
        finally:
            self.daten[name] = {"s": round(time.perf_counter() - beginn, 3), "mb": self.speicher_mb()}

    def speicher_mb(self) -> float | None:
        try:
            return privat_mb(int(self.app.GetProcessID))
        except Exception:
            return None


def _art(rel: str) -> str:
    return "baugruppe" if ist_baugruppe(rel) else "teil"


def _angaben_der_datei(app, rel: str, quelle: Path, namen: dict[str, str]) -> dict:
    """Art, Version und eigene Referenzen einer Datei, am Original ohne Öffnen (`BESTAND_VERSION_NEUER`, kein Dokument offen).
    Ein Ziel, das nicht zur Baugruppe gehört, läge nicht in der Kopie: `BESTAND_REFERENZ_EXTERN`. Referenzen stehen als
    relativer Pfad."""
    versionen, aelter = pruefe_version(app, quelle)
    ziele = [z for z in externe_referenzen(app, quelle) if z and not ist_virtuell(z)]
    fremd = [z for z in ziele if Path(z).name.lower() not in namen]
    if fremd:
        raise BestandFehler(BESTAND_REFERENZ_EXTERN, f"{rel} referenziert Dateien außerhalb der Baugruppe: {', '.join(fremd)}",
                            datei=rel,
                            referenzen=fremd)
    return {"art": _art(rel), "versionen": versionen, "version_aelter": aelter,
            "referenzen": [namen[Path(z).name.lower()] for z in ziele]}


def _warnungen_offen(quellen: dict[str, Path]) -> list[dict]:
    return [{"code": BESTAND_OFFEN, "datei": rel,
             "meldung": f"{rel} hat jemand offen (`~$`-Datei daneben), kopiert ist der gespeicherte Stand"}
            for rel in sperrdateien(quellen)]


def _bewegungen(app, asm, gelesen: dict, standard: dict, ohne_bewegung: bool, start_mb: float | None) -> dict:
    """Das Feld `bewegungen`: Jede Grenzverknüpfung der Hauptbaugruppe wird an der Kopie gefahren. Ohne Fenster, also ohne
    Bilder. `start_mb`: Private Bytes vor dem Öffnen, `SPEICHER_KNAPP` erkennt daran frisches SolidWorks."""
    grenzen = grenzen_der_aufnahme(gelesen)
    if ohne_bewegung:
        return ohne_fahrt(grenzen, "ohne Bewegung aufgenommen (--ohne-bewegung)")
    if not grenzen:
        return {}
    return fahre_bestand(mechanik_fuer(app, asm, grenzen, gelesen, None), gelesen, grenzen, standard["bewegung_schritte"],
                         statische_paare(gelesen), standard["speicher_grenze_mb"], standard["toleranzen"]["anker_mm"], start_mb)


def lies_baugruppe_einzeln(app, model) -> dict:
    """Unterbaugruppe beim Lesen je Datei: ohne Kollision (die gehört zur Hauptbaugruppe)."""
    return lies_baugruppe(app, model, kollision=False)


def _lies_datei(app, r, auftrag: str, nummer: int, ordner: Path, rel: str, d: dict) -> None:
    """Eine weitere Datei einmal, einzeln, unsichtbar, über den Pfadschutz; `datei.name` ist der relative Pfad."""
    model = oeffne_in(app, ordner / rel, ordner, sichtbar=False, nur_lesen=True)
    try:
        gelesen = lies_baugruppe_einzeln(app, model) if d["art"] == "baugruppe" else lies_bestand(app, model)
    finally:
        sw.schliesse(app, model)
    schreibe_datei_aufnahme(r, auftrag, nummer, rel, {
        **gelesen, "sw_jahr": r.sw_jahr,
        "datei": {"name": rel, "original": d["original"], "sha256": d["sha256"], "versionen": d["versionen"],
                  "version_aelter": d["version_aelter"]}})


def _lies_kopie(app, m: _Messung, r, auftrag: str, nummer: int, ordner: Path, pfad: Path, dateien: dict, standard: dict,
                ohne_bewegung: bool) -> dict:
    """Die Kopie lesen: `bestand.json` ohne `datei`, in der Reihenfolge des Moduldocstrings. Schließt auch nach einem Fehler."""
    weitere = {rel: d for rel, d in dateien.items() if not d.get("haupt")}
    start_mb = m.speicher_mb()
    with m.phase("oeffnen"):
        asm = oeffne_in(app, pfad, ordner, sichtbar=False, nur_lesen=True)
    try:
        with m.phase("lesen"):
            gelesen = lies_baugruppe(app, asm, weitere, kollision=False)
        with m.phase("kollision"):
            gelesen["kollisionen"] = lies_kollisionen(asm)
        with m.phase("fahrt"):
            gelesen["bewegungen"] = _bewegungen(app, asm, gelesen, standard, ohne_bewegung, start_mb)
    finally:
        sw.schliesse(app, asm)
    with m.phase("dateien"):
        for rel, d in weitere.items():
            _lies_datei(app, r, auftrag, nummer, ordner, rel, d)
    with m.phase("bilder"):
        asm = oeffne_in(app, pfad, ordner, sichtbar=True, nur_lesen=True)
        try:
            screenshots(app, asm, ordner / "bilder")
        finally:
            sw.schliesse(app, asm)
    gelesen["messung"] = m.daten
    return gelesen


def ausgabe(auftrag: str, nummer: int, a: dict, ordner: Path, neu: bool, herkunft: dict | None) -> dict:
    """`zusammenfassung` plus das, was die Zuordnung der Punkte braucht; die Rohdaten stehen in `bestand.json`."""
    aktiv = a["aktiv"]
    aus = zusammenfassung(auftrag, nummer, a, ordner, neu)
    aus["zaehler"] |= {"komponenten": len(a["komponenten"]), "verknuepfungen": len(a["verknuepfungen"]),
                       "dateien": len(a["dateien"]),
                       "grenzen": len(a["bewegungen"])}
    komponenten = []
    for name, k in a["komponenten"].items():
        weg = [x for x, u in k["unterdrueckt"].items() if u]
        komponenten.append({"name": name, "datei": k["datei"], "konfiguration": k["konfiguration"],
                            **({"unterdrueckt": weg} if weg else {})})
    verknuepfungen = []
    for name, v in a["verknuepfungen"].items():
        fehler = {x: c for x, c in v["fehler"].items() if c}
        verknuepfungen.append({"name": name, "typ": mate_name(v["typ"], bool(v["grenze"])), "wert": v["wert"],
                               "partner": v["partner"],
                               **({"fehler": fehler} if fehler else {}),
                               **({"unterdrueckt": True} if v["unterdrueckt"].get(aktiv) else {})})
    grenzen = [{"name": n, **{f: g.get(f) for f in ("komponente", "art", "min", "max", "gefahren", "stellungen", "bewegt",
                                                    "hinweis")}}
               for n, g in a["bewegungen"].items()]
    dateien = [{"datei": rel, "art": d["art"], "version_aelter": d["version_aelter"]} for rel, d in a["dateien"].items()]
    return aus | {"komponenten": komponenten, "verknuepfungen": verknuepfungen, "grenzen": grenzen,
                  "kollisionen": a["kollisionen"],
                  "dateien": dateien, "warnungen": a["warnungen"], "herkunft": herkunft, "messung": a["messung"]}


def aufnehmen(original: Path, auftrag: str, ohne_bewegung: bool = False) -> dict:
    """Spec §8.1: Bestandsaufnahme einer Baugruppe in `<auftrag>/bestand-<n>/`. Gleiche Dateien (alle SHA-256) → keine neue
    Aufnahme; ob zu lesen ist, entscheidet die fehlende `bestand.json`, wie in Etappe 1. `--ohne-bewegung` lässt die Fahrt weg,
    `pruefen` meldet `bewegung:*` dann als `ok: None`."""
    sha_original(original)  # BESTAND_NICHT_LESBAR, bevor SolidWorks gefragt wird
    r, standard = lade_rechner(), lade_standard()
    pruefe_auftrag_frei(r, auftrag, spec_laeufe(r, auftrag))
    app = verbinde(r.sw_jahr)
    pfad = original.absolute()
    versionen, aelter = pruefe_version(app, pfad)
    quellen = ordne_referenzen(pfad, externe_referenzen(app, pfad))
    namen = {Path(rel).name.lower(): rel for rel in quellen} | {pfad.name.lower(): pfad.name}  # auch ein In-Context-Teil
    angaben = {rel.lower(): _angaben_der_datei(app, rel, quelle, namen) for rel, quelle in quellen.items()}
    angaben[pfad.name.lower()] = {"art": "baugruppe", "versionen": versionen, "version_aelter": aelter,
                                  "referenzen": sorted(quellen)}
    m = _Messung(app)
    with m.phase("kopieren"):
        kopie = kopiere_baugruppe(r, auftrag, pfad, quellen)
    nummer, ordner = kopie["nummer"], bestand_ordner(r, auftrag, kopie["nummer"])
    if (ordner / AUFNAHME_DATEI).is_file():
        return ausgabe(auftrag, nummer, lade_aufnahme(r, auftrag, nummer), ordner, False, lade_herkunft(r, auftrag, nummer))
    dateien = {rel: {**d, **angaben[rel.lower()]} for rel, d in kopie["dateien"].items()}
    schreibe_dateien(r, auftrag, nummer, dateien)
    herkunft = herkunft_von(r, pfad)
    if herkunft is not None:
        schreibe_herkunft(r, auftrag, nummer, herkunft)
    try:
        gelesen = _lies_kopie(app, m, r, auftrag, nummer, ordner, kopie["pfad"], dateien, standard, ohne_bewegung)
    except BestandFehler as e:
        if e.daten["code"] in _ABLEHNUNG:  # abgelehnt, auch wenn die Kopie aus einem abgebrochenen Versuch stammt
            verwirf_aufnahme(ordner)
        raise
    abgedeckt = [{"code": BEWEGUNG_ABDECKUNG, "meldung": h} for h in abdeckung(gelesen)]
    warnungen = gelesen["warnungen"] + _warnungen_offen({pfad.name: pfad, **quellen}) + abgedeckt
    daten = {**gelesen, "sw_jahr": r.sw_jahr, "warnungen": warnungen,
             "datei": {"name": kopie["pfad"].name, "original": str(pfad), "sha256": kopie["sha256"], "versionen": versionen,
                       "version_aelter": aelter},
             "dateien": {rel: d for rel, d in dateien.items() if not d.get("haupt")}}
    schreibe_aufnahme(r, auftrag, nummer, daten)
    return ausgabe(auftrag, nummer, daten, ordner, True, herkunft)
