"""swki bestand ausgabe (Spec Bestandsdateien §9): die geänderten Dateien eines bestandenen Laufs nach
`<arbeitsordner>/<auftrag>/ausgabe/`, unter dem Originalnamen. Zurückkopiert wird nie von swki: Der Nutzer tut es selbst.

Ausgegeben wird nur, was `protokoll.dateien` als Ergebnis des Laufs nennt, nie etwas, das sonst im Lauf-Ordner liegt (Vorher-Kopie,
Bilder). Jede Datei muss noch die geprüfte sein (SHA-256 aus dem Bauprotokoll) und im Lauf-Ordner liegen. „Geändert“ heißt: andere
SHA-256 als die Bestandskopie. Das Original wird nur gelesen (SHA-256), nie geöffnet oder beschrieben.

Auf Warnungen wird trotzdem kopiert (`warnungen: [{code, meldung}]`): Das Original kann inzwischen neuer sein, gesperrt oder weg, und
die Sitzung kann keine Vollversion gewesen sein. Beides zugleich ist möglich, darum eine Liste."""

import json
import shutil
from pathlib import Path

from swki.aenderungen import AenderungFehler, sha256_datei
from swki.auftrag import auftrag_name, lauf_datei, lauf_ordner
from swki.bestand.ablage import bestand_ordner, lade_aufnahme
from swki.bestand.fehler import (BESTAND_LIZENZ, BESTAND_NICHT_LESBAR, BESTAND_ORIGINAL_GEAENDERT, LAUF_NICHT_BESTANDEN,
                                 BestandFehler)
from swki.bestand.spec import lade_aenderung
from swki.cli import SwkiFehler
from swki.konfig import Rechner, lade_rechner
from swki.pruefung.schleife import lies_laeufe
from swki.spec.freigabe import pruefe_freigabe

AUSGABE_ORDNER = "ausgabe"
# swLicenseType_e: Full, Full_Office, Full_Professional, Full_Premium, Full_Ultimate; alles andere (Educational, Student,
# StudentDesignKit, PersonalEdition, Maker) ist keine Vollversion (Ruling 5)
VOLLVERSIONEN = frozenset({0, 5, 6, 7, 9})


def _warnung(code: str, meldung: str) -> dict:
    return {"code": code, "meldung": meldung}


def lizenz_warnung(lizenz: dict | None) -> dict | None:
    """Warnung, wenn die Sitzung des Laufs keine Vollversion war oder das Protokoll die Lizenz nicht kennt (`lizenz` im Protokoll:
    `{"sitzung": {typ, name}, "datei": {typ, name}}`, bei kommerziellen Lizenzen trägt auch die Datei Typ 0)."""
    if not lizenz or not isinstance(lizenz.get("sitzung"), dict):
        return _warnung(BESTAND_LIZENZ, "Das Protokoll vermerkt keine Lizenz (Abfrage gescheitert oder älterer Lauf): ob die Datei den "
                                        "Vermerk einer Nicht-Vollversion trägt, ist unbekannt. Vor dem Zurückkopieren klären.")
    sitzung = lizenz["sitzung"]
    if sitzung.get("typ") in VOLLVERSIONEN:
        return None
    datei = lizenz.get("datei") or {}
    return _warnung(BESTAND_LIZENZ, f"SolidWorks lief beim Bau mit {sitzung.get('name', 'unbekannt')} (Typ {sitzung.get('typ')}), die "
                                    f"gespeicherte Datei trägt {datei.get('name', 'unbekannt')}: keine Vollversion. Solche Dateien "
                                    "tragen den Vermerk der Lern- bzw. Nicht-Vollversion; ob sie sich im Betrieb verwenden lassen, "
                                    "vor dem Zurückkopieren klären.")


def _original_warnung(original: Path, soll: str) -> dict | None:
    """Gegenprobe am Original (§9 Punkt 3): nur lesen. Gesperrt oder weg ist eine Warnung, kein Abbruch."""
    try:
        ist = sha256_datei(original)
    except OSError as e:
        return _warnung(BESTAND_NICHT_LESBAR, f"Das Original {original} lässt sich nicht lesen ({e.strerror or e}): ob es sich seit "
                                              "der Aufnahme geändert hat, ist unbekannt. Vor dem Zurückkopieren prüfen.")
    if ist == soll:
        return None
    return _warnung(BESTAND_ORIGINAL_GEAENDERT, f"Das Original {original} hat sich seit der Aufnahme geändert: Das Zurückkopieren "
                                                "würde die Arbeit des Kollegen überschreiben.")


def _ziel(r: Rechner, auftrag: str, rel: Path) -> Path:
    """Zielpfad unter `ausgabe/`. swki schreibt nie außerhalb des Arbeitsordners, auch nicht über Auftragsnamen oder Dateipfade."""
    wurzel = r.arbeitsordner.resolve()
    basis = (wurzel / auftrag / AUSGABE_ORDNER).resolve()
    ziel = (basis / rel).resolve()
    if not (basis.is_relative_to(wurzel) and ziel.is_relative_to(basis)):
        raise SwkiFehler(f"{rel} würde außerhalb des Arbeitsordners {wurzel} landen – swki schreibt dort nie")
    return r.arbeitsordner / auftrag / AUSGABE_ORDNER / rel


def _bestandener_lauf(spec_pfad: Path, auftrag: str, lauf: int | None) -> int:
    alle = lies_laeufe(spec_pfad)
    if lauf is None:
        if not alle:
            raise SwkiFehler(f"Auftrag {auftrag} hat noch keinen Lauf. Zuerst: swki bauen")
        lauf = alle[-1]["lauf"]
    eintrag = next((e for e in alle if e["lauf"] == lauf), None)
    if eintrag is None:
        raise SwkiFehler(f"Lauf {lauf} von {auftrag} hat kein Protokoll")
    if not eintrag["bestanden"]:
        offen = "nicht geprüft" if eintrag["code_maengel"] is None else f"{eintrag['code_maengel']} Mängel"
        raise BestandFehler(LAUF_NICHT_BESTANDEN, f"Lauf {lauf} ist nicht bestanden (Bau: {eintrag['bau']}, Prüfbericht: {offen}, "
                                                  f"Prüfer: {eintrag['pruefer']}): Ausgegeben wird nur ein geprüfter Lauf mit "
                                                  "bestandenem Prüfer-Urteil", lauf=lauf, bau=eintrag["bau"],
                            code_maengel=eintrag["code_maengel"], pruefer=eintrag["pruefer"])
    return lauf


def _bestand_sha(r: Rechner, auftrag: str, aufnahme: dict, rel: Path) -> str | None:
    """SHA-256 der Bestandskopie zu dieser Datei: die Hauptdatei aus der Aufnahme, sonst die Datei in der Bestandskopie."""
    if rel.as_posix() == aufnahme["datei"]["name"]:
        return aufnahme["datei"]["sha256"]
    kopie = bestand_ordner(r, auftrag, aufnahme["nummer"]) / rel
    return sha256_datei(kopie) if kopie.is_file() else None


def _lauf_datei_pruefen(ordner: Path, lauf: int, name: str, pfad: str, summen: dict) -> tuple[Path, str]:
    """(relativer Pfad im Lauf-Ordner, SHA-256), wenn die Datei im Lauf-Ordner liegt und noch die gebaute ist."""
    datei = Path(pfad)
    try:
        rel = datei.resolve().relative_to(ordner.resolve())
    except ValueError:
        raise SwkiFehler(f"{pfad} ({name}) liegt nicht im Lauf-Ordner {ordner} – daraus gibt swki nichts aus") from None
    try:
        ist = sha256_datei(datei)
    except OSError:
        ist = None
    if ist is None or ist != summen.get(rel.as_posix()):
        raise AenderungFehler(f"{rel.as_posix()} im Lauf {lauf} ist nicht mehr die gebaute Datei (oder war nie in der Prüfsumme) – "
                              "die Ausgabe wäre nicht das, was geprüft wurde. swki aenderungen nennt den Befund",
                              geaendert=[rel.as_posix()] if ist else [], fehlend=[] if ist else [rel.as_posix()])
    return rel, ist


def _plane(spec_pfad: Path, lauf: int | None) -> tuple[dict, Path]:
    """(Plan, Lauf-Ordner): alle Prüfungen, nichts wird geschrieben."""
    spec_pfad = spec_pfad.resolve()
    spec = lade_aenderung(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, auftrag = lade_rechner(), auftrag_name(spec_pfad)
    lauf = _bestandener_lauf(spec_pfad, auftrag, lauf)
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    ordner = lauf_ordner(r, auftrag, lauf)
    nummer = spec["bestand"]["aufnahme"]
    aufnahme = {**lade_aufnahme(r, auftrag, nummer), "nummer": nummer}
    original = Path(aufnahme["datei"]["original"])

    dateien, unveraendert = [], []
    for name, pfad in (protokoll.get("dateien") or {}).items():
        rel, sha = _lauf_datei_pruefen(ordner, lauf, name, pfad, protokoll.get("sha256") or {})
        if sha == _bestand_sha(r, auftrag, aufnahme, rel):
            unveraendert.append(rel.as_posix())
            continue
        hauptdatei = rel.as_posix() == aufnahme["datei"]["name"]
        dateien.append({"datei": rel.as_posix(), "original": str(original if hauptdatei else original.parent / rel),
                        "ausgabe": str(_ziel(r, auftrag, rel)), "sha256": sha})
    warnungen = [w for w in (lizenz_warnung(protokoll.get("lizenz")),
                             _original_warnung(original, aufnahme["datei"]["sha256"]) if dateien else None) if w]
    return ({"auftrag": auftrag, "lauf": lauf, "ordner": str(r.arbeitsordner / auftrag / AUSGABE_ORDNER), "dateien": dateien,
             "unveraendert": unveraendert, "warnungen": warnungen}, ordner)


def ausgabe_liste(spec_pfad: Path, lauf: int | None = None) -> dict:
    """Was `ausgabe` täte, ohne etwas zu schreiben (für den Bericht). Fehler wie bei `ausgabe`: `LAUF_NICHT_BESTANDEN`, Lauf-Datei
    verändert, Freigabe veraltet."""
    return _plane(spec_pfad, lauf)[0]


def ausgabe(spec_pfad: Path, lauf: int | None = None) -> dict:
    """Spec §9: geänderte Dateien des bestandenen Laufs nach `ausgabe/` kopieren. Erst wird alles geplant und geprüft, dann kopiert.

    `{"auftrag", "lauf", "ordner", "dateien": [{datei, original, ausgabe, sha256}], "unveraendert": [...], "warnungen": [{code,
    meldung}]}`"""
    plan, quelle = _plane(spec_pfad, lauf)
    for d in plan["dateien"]:
        ziel = Path(d["ausgabe"])
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(quelle / d["datei"], ziel)
        if sha256_datei(ziel) != d["sha256"]:
            raise SwkiFehler(f"Die Kopie {ziel} weicht von {d['datei']} im Lauf ab – nicht zurückkopieren")
    return plan
