"""Ablage der Bestandsdateien: <arbeitsordner>/<auftrag>/bestand-<n>/ enthält die schreibgeschützte Kopie des Originals
und die Aufnahme (bestand.json). Das Original wird nur gelesen. Ein Auftrag nimmt genau eine Datei auf; ändert sich
ihr Inhalt, entsteht eine neue Aufnahme (nie überschreiben)."""

import json
import os
import re
import shutil
import stat
from pathlib import Path, PureWindowsPath

from swki.aenderungen import sha256_datei
from swki.bestand.fehler import (BESTAND_ABWEICHEND, BESTAND_ANDERE_DATEI, BESTAND_AUFTRAG_BELEGT, BESTAND_FORMAT,
                                 BESTAND_NICHT_LESBAR, BESTAND_REFERENZ_EXTERN, BESTAND_REFERENZ_FEHLT, BESTAND_UNBEKANNT,
                                 BestandFehler)
from swki.konfig import Rechner

ENDUNG = ".sldprt"
AUFNAHME_DATEI = "bestand.json"
DATEIEN_DATEI = "dateien.json"
HERKUNFT_DATEI = "herkunft.json"
AUFNAHME_ORDNER = "aufnahme"
_ORDNER = re.compile(r"^bestand-(\d+)$")
_LAUF = re.compile(r"^lauf-(\d+)$")


def bestand_ordner(r: Rechner, auftrag: str, nummer: int) -> Path:
    return r.arbeitsordner / auftrag / f"bestand-{nummer}"


def aufnahmen(r: Rechner, auftrag: str) -> list[int]:
    """Nummern der vorhandenen Aufnahmen des Auftrags, aufsteigend."""
    wurzel = r.arbeitsordner / auftrag
    if not wurzel.is_dir():
        return []
    return sorted(int(m.group(1)) for p in wurzel.iterdir() if p.is_dir() and (m := _ORDNER.match(p.name)))


def pruefe_format(pfad: Path) -> None:
    if pfad.suffix.lower() != ENDUNG:
        raise BestandFehler(BESTAND_FORMAT, f"{pfad.name}: nur Teile ({ENDUNG}) – Baugruppen und andere Formate sind "
                                            "hier nicht möglich", erlaubt=[ENDUNG])


def _kopie_in(ordner: Path) -> Path | None:
    """Die Bestandskopie einer Aufnahme: die Hauptdatei aus `dateien.json` (Baugruppe, daneben liegen weitere Teile),
    sonst die einzige .sldprt im Ordner selbst (Etappe 1)."""
    dateien = _lies_dateien(ordner)
    if dateien is not None:
        haupt = next((rel for rel, d in dateien.items() if d.get("haupt")), None)
        pfad = ordner / haupt if haupt else None
        return pfad if pfad is not None and pfad.is_file() else None
    treffer = sorted(p for p in ordner.iterdir() if p.is_file() and p.suffix.lower() == ENDUNG) if ordner.is_dir() else []
    return treffer[0] if treffer else None


def sha_original(original: Path) -> str:
    """SHA-256 des Originals; `BESTAND_NICHT_LESBAR`, wenn es fehlt oder gesperrt ist."""
    try:
        return sha256_datei(original)
    except OSError as e:
        raise BestandFehler(BESTAND_NICHT_LESBAR, f"{original} lässt sich nicht lesen ({e.strerror or e}) – fehlt die "
                                                  "Datei, ist das Laufwerk nicht da oder hat sie ein Kollege offen?",
                            pfad=str(original)) from e


def kopiere_original(r: Rechner, auftrag: str, original: Path) -> dict:
    """Original lesen und als schreibgeschützte Kopie in bestand-<n>/ ablegen. Gleiche Datei (gleicher Name ohne
    Beachtung der Groß-/Kleinschreibung, gleiche SHA-256 wie die jüngste Aufnahme) → keine neue Aufnahme."""
    pruefe_format(original)
    sha = sha_original(original)
    nummern = aufnahmen(r, auftrag)
    if nummern:
        jung = nummern[-1]
        kopie = _kopie_in(bestand_ordner(r, auftrag, jung))
        if kopie is not None:
            if kopie.name.lower() != original.name.lower():
                raise BestandFehler(BESTAND_ANDERE_DATEI,
                                    f"Der Auftrag {auftrag} hat schon {kopie.name} aufgenommen – ein Auftrag nimmt "
                                    f"genau eine Datei auf, für {original.name} einen neuen Auftrag anlegen",
                                    vorhanden=kopie.name, neu=original.name)
            if sha256_datei(kopie) == sha:
                return {"nummer": jung, "pfad": kopie, "sha256": sha, "neu": False}
    nummer = (nummern[-1] if nummern else 0) + 1
    ziel = bestand_ordner(r, auftrag, nummer) / original.name
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, ziel)
    if sha256_datei(ziel) != sha:
        os.chmod(ziel, stat.S_IWRITE)  # `copy2` bringt den Schreibschutz des Originals mit, löschen ginge sonst nicht
        ziel.unlink()
        ziel.parent.rmdir()  # eben angelegt, eine abgelehnte Datei hinterlässt keine Aufnahme
        raise BestandFehler(BESTAND_NICHT_LESBAR, f"Die Kopie von {original.name} weicht vom Original ab – speichert gerade ein Kollege "
                                                  "die Datei?", pfad=str(original))
    os.chmod(ziel, stat.S_IREAD)
    return {"nummer": nummer, "pfad": ziel, "sha256": sha, "neu": True}


def verwirf_aufnahme(ordner: Path) -> None:
    """Eine Aufnahme ohne `bestand.json` entfernen, deren Datei erst nach dem Kopieren abgelehnt wurde: Der Ordner zählte sonst als
    neueste Aufnahme. Die Kopien sind schreibgeschützt (bei einer Baugruppe alle, auch in Unterordnern), unter Windows
    gingen sie sonst nicht weg."""
    for ort, _, dateien in os.walk(ordner):
        for name in dateien:
            os.chmod(Path(ort) / name, stat.S_IWRITE)
    shutil.rmtree(ordner)


def lade_aufnahme(r: Rechner, auftrag: str, nummer: int) -> dict:
    pfad = bestand_ordner(r, auftrag, nummer) / AUFNAHME_DATEI
    if not pfad.is_file():
        raise BestandFehler(BESTAND_UNBEKANNT, f"Keine Aufnahme {nummer} im Auftrag {auftrag} – zuerst "
                                               "swki bestand aufnehmen", auftrag=auftrag, nummer=nummer)
    return json.loads(pfad.read_text(encoding="utf-8"))


def schreibe_aufnahme(r: Rechner, auftrag: str, nummer: int, daten: dict) -> Path:
    pfad = bestand_ordner(r, auftrag, nummer) / AUFNAHME_DATEI
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
    return pfad


def lauf_kopie(quelle: Path, ordner: Path) -> Path:
    """Arbeitskopie für einen Lauf: Kopie der (schreibgeschützten) Bestandskopie, beschreibbar."""
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / quelle.name
    shutil.copy2(quelle, ziel)
    os.chmod(ziel, stat.S_IREAD | stat.S_IWRITE)
    return ziel


def vorher_kopie(quelle: Path, ordner: Path) -> Path:
    """Kopie der Bestandskopie für den Vergleich im Lauf-Ordner `ordner`: unter anderem Namen (SolidWorks öffnet keine zwei
    gleichnamigen Dokumente, S18d) und beschreibbar (sonst Warnung beim Öffnen). Sie steht in keiner Prüfsumme des Laufs."""
    ziel = ordner / "vergleich" / f"vorher_{quelle.name}"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(quelle, ziel)
    os.chmod(ziel, stat.S_IREAD | stat.S_IWRITE)
    return ziel


def pruefe_kopie(aufnahme: dict, pfad: Path) -> None:
    """Die Bestandskopie muss noch die aufgenommene sein (SHA-256 aus `aufnahme["datei"]["sha256"]`)."""
    soll = aufnahme["datei"]["sha256"]
    ist = sha256_datei(pfad)
    if ist != soll:
        raise BestandFehler(BESTAND_ABWEICHEND, f"{pfad.name} weicht von der Aufnahme ab – jemand hat die "
                                                "Bestandskopie geändert", pfad=str(pfad), aufnahme=soll, vorhanden=ist)


# --- Baugruppen: Hauptdatei plus alle referenzierten Dateien in einer Aufnahme (Spec §8.1) ---------------------------

def _schluessel(pfad: Path | str) -> str:
    return os.path.normcase(os.path.abspath(pfad))


def ordne_referenzen(haupt: Path, gespeichert: list[str]) -> dict[str, Path]:
    """Relativer Pfad in der Kopie → Quelle für alle gespeicherten Pfade der Referenzen (`GetDocumentDependencies2`). Wie beim
    Öffnen hat die Datei neben der Hauptbaugruppe Vorrang vor dem gespeicherten Pfad (S18g). Sonst: was im Ordner der
    Baugruppe liegt, behält seine relative Struktur, alles andere liegt flach daneben. Virtuelle Komponenten (Name mit `^`)
    und die Hauptbaugruppe selbst sind keine Referenz."""
    ordner = PureWindowsPath(haupt.parent)
    gefunden: list[tuple[str, str, Path]] = []  # (rel, Name klein, Quelle), nie überschreiben: gleiche rel prüft der Namensvergleich
    fehlen: list[str] = []
    for text in gespeichert:
        pfad = PureWindowsPath(text)
        if "^" in pfad.name:
            continue
        daneben = haupt.parent / pfad.name
        if daneben.is_file():
            quelle, rel = daneben, pfad.name
        else:
            quelle = Path(text)
            if not quelle.is_file():
                fehlen.append(text)
                continue
            try:
                rel = pfad.relative_to(ordner).as_posix()
            except ValueError:
                rel = pfad.name
        if _schluessel(quelle) != _schluessel(haupt):
            gefunden.append((rel, pfad.name.lower(), quelle))
    if fehlen:
        raise BestandFehler(BESTAND_REFERENZ_FEHLT, f"{len(fehlen)} referenzierte Dateien fehlen (weder neben {haupt.name} noch am "
                                                    f"gespeicherten Pfad): {', '.join(fehlen)}", fehlen=fehlen)
    je_name: dict[str, dict[str, Path]] = {}
    for _, name, quelle in gefunden:
        je_name.setdefault(name, {})[_schluessel(quelle)] = quelle
    doppelt = {name: sorted(str(q) for q in quellen.values()) for name, quellen in je_name.items() if len(quellen) > 1}
    if doppelt:
        raise BestandFehler(BESTAND_REFERENZ_EXTERN,
                            f"Gleiche Dateinamen aus verschiedenen Ordnern: {', '.join(sorted(doppelt))} – SolidWorks öffnet "
                            "keine zwei gleichnamigen Dokumente, die Baugruppe lässt sich so nicht kopieren", gleiche_namen=doppelt)
    return {rel: quelle for rel, _, quelle in gefunden}


def sperrdateien(quellen: dict[str, Path]) -> list[str]:
    """Relative Pfade der Quellen, die jemand offen hat (`~$<Name>` daneben). Die Sperrdatei selbst wird nie kopiert; kopiert
    wird der gespeicherte Stand, die Aufnahme meldet `BESTAND_OFFEN`."""
    return [rel for rel, quelle in quellen.items() if (quelle.parent / f"~${quelle.name}").exists()]


def _lies_dateien(ordner: Path) -> dict | None:
    pfad = ordner / DATEIEN_DATEI
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.is_file() else None


def lade_dateien(r: Rechner, auftrag: str, nummer: int) -> dict:
    """`dateien.json` der Aufnahme: relativer Pfad → {original, sha256, …}; die Hauptdatei trägt `haupt: true`."""
    dateien = _lies_dateien(bestand_ordner(r, auftrag, nummer))
    if dateien is None:
        raise BestandFehler(BESTAND_UNBEKANNT, f"Aufnahme {nummer} im Auftrag {auftrag} hat keine {DATEIEN_DATEI} – keine "
                                               "Baugruppen-Aufnahme", auftrag=auftrag, nummer=nummer)
    return dateien


def schreibe_dateien(r: Rechner, auftrag: str, nummer: int, dateien: dict) -> Path:
    pfad = bestand_ordner(r, auftrag, nummer) / DATEIEN_DATEI
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(dateien, ensure_ascii=False, indent=2), encoding="utf-8")
    return pfad


def _gleiche_dateien(alt: dict, neu: dict) -> bool:
    """Gleiche Aufnahme heißt: dieselben Dateien (Name ohne Beachtung der Schreibweise) mit derselben SHA-256."""
    a = {rel.lower(): d["sha256"] for rel, d in alt.items()}
    n = {rel.lower(): d["sha256"] for rel, d in neu.items()}
    return a == n


def kopiere_baugruppe(r: Rechner, auftrag: str, haupt: Path, quellen: dict[str, Path]) -> dict:
    """Hauptbaugruppe und alle Referenzen (`quellen`: relativer Pfad → Quelle, aus `ordne_referenzen`) lesen und als
    schreibgeschützte Kopien in bestand-<n>/ ablegen, `dateien.json` daneben. Originale werden nur gelesen. Gleiche Aufnahme
    (alle SHA-256 gleich zur jüngsten) → keine neue. Ergebnis: `{nummer, pfad (Hauptkopie), sha256 (Haupt), neu, dateien}`."""
    if haupt.name.lower() in {rel.lower() for rel in quellen}:
        raise BestandFehler(BESTAND_REFERENZ_EXTERN, f"{haupt.name} ist zugleich Hauptbaugruppe und Referenz", pfad=str(haupt))
    sha = sha_original(haupt)
    dateien = {haupt.name: {"original": str(haupt), "sha256": sha, "haupt": True}}
    for rel, quelle in quellen.items():
        dateien[rel] = {"original": str(quelle), "sha256": sha_original(quelle)}
    nummern = aufnahmen(r, auftrag)
    if nummern:
        jung = nummern[-1]
        ordner = bestand_ordner(r, auftrag, jung)
        kopie = _kopie_in(ordner)
        if kopie is not None:
            if kopie.name.lower() != haupt.name.lower():
                raise BestandFehler(BESTAND_ANDERE_DATEI,
                                    f"Der Auftrag {auftrag} hat schon {kopie.name} aufgenommen – ein Auftrag nimmt "
                                    f"genau eine Datei auf, für {haupt.name} einen neuen Auftrag anlegen",
                                    vorhanden=kopie.name, neu=haupt.name)
            alt = _lies_dateien(ordner)
            if alt is not None and _gleiche_dateien(alt, dateien):
                return {"nummer": jung, "pfad": kopie, "sha256": sha, "neu": False, "dateien": alt}
    nummer = (nummern[-1] if nummern else 0) + 1
    ordner = bestand_ordner(r, auftrag, nummer)
    try:
        for rel, d in dateien.items():
            ziel = ordner / rel
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(haupt if d.get("haupt") else quellen[rel], ziel)
            if sha256_datei(ziel) != d["sha256"]:
                raise BestandFehler(BESTAND_NICHT_LESBAR, f"Die Kopie von {rel} weicht vom Original ab – speichert gerade ein "
                                                          "Kollege die Datei?", pfad=d["original"])
        schreibe_dateien(r, auftrag, nummer, dateien)
    except (BestandFehler, OSError) as e:
        if ordner.exists():
            verwirf_aufnahme(ordner)  # eine abgelehnte Aufnahme hinterlässt nichts, der Ordner zählte sonst als neueste
        if isinstance(e, BestandFehler):
            raise
        raise BestandFehler(BESTAND_NICHT_LESBAR, f"Kopieren der Baugruppe {haupt.name} gescheitert ({e.strerror or e})",
                            pfad=str(e.filename or haupt)) from e
    for rel in dateien:
        os.chmod(ordner / rel, stat.S_IREAD)
    return {"nummer": nummer, "pfad": ordner / haupt.name, "sha256": sha, "neu": True, "dateien": dateien}


def lauf_kopie_alle(ordner_bestand: Path, dateien: dict, lauf: Path) -> Path:
    """Arbeitskopie aller Dateien einer Baugruppen-Aufnahme im Lauf-Ordner: gleiche relative Struktur, beschreibbar.
    Rückgabe: die Hauptbaugruppe im Lauf-Ordner."""
    haupt = None
    for rel, d in dateien.items():
        ziel = lauf / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ordner_bestand / rel, ziel)
        os.chmod(ziel, stat.S_IREAD | stat.S_IWRITE)
        if d.get("haupt"):
            haupt = ziel
    if haupt is None:
        raise BestandFehler(BESTAND_UNBEKANNT, f"{DATEIEN_DATEI} in {ordner_bestand} nennt keine Hauptdatei",
                            pfad=str(ordner_bestand))
    return haupt


# --- Herkunft: das Original liegt in einem eigenen Lauf (Spec §8.5) -----------------------------------------------------

def herkunft_von(r: Rechner, original: Path) -> dict | None:
    """`{auftrag, lauf, spec}`, wenn `original` in `<arbeitsordner>/<auftrag>/lauf-<n>/` liegt (auch tiefer) und dort ein
    `protokoll.json` steht. Der Lauf-Ordner wird nur gelesen. Sonst None."""
    wurzel = _schluessel(r.arbeitsordner)
    for ordner in Path(os.path.abspath(original)).parents:
        if _LAUF.match(ordner.name) and _schluessel(ordner.parent.parent) == wurzel:
            try:
                protokoll = json.loads((ordner / "protokoll.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
            if not isinstance(protokoll, dict) or "spec" not in protokoll:
                return None
            return {"auftrag": protokoll.get("auftrag", ordner.parent.name),
                    "lauf": protokoll.get("lauf", int(_LAUF.match(ordner.name).group(1))), "spec": protokoll["spec"]}
    return None


def pruefe_auftrag_frei(r: Rechner, auftrag: str, spec_laeufe: list[int]) -> None:
    """Ein Auftrag mit eigenen Läufen aus Specs nimmt nichts auf: Zählung und `MANUELL_GEAENDERT` liefen durcheinander."""
    if spec_laeufe:
        raise BestandFehler(BESTAND_AUFTRAG_BELEGT,
                            f"Der Auftrag {auftrag} hat schon Läufe aus Specs ({', '.join(map(str, spec_laeufe))}) – die "
                            "Bestandsaufnahme gehört in einen neuen Auftrag", auftrag=auftrag, laeufe=list(spec_laeufe))


def schreibe_herkunft(r: Rechner, auftrag: str, nummer: int, herkunft: dict) -> Path:
    """`herkunft.json` der Aufnahme: `{auftrag, lauf, spec}` des Laufs, aus dem das Original stammt (von `herkunft_von`)."""
    pfad = bestand_ordner(r, auftrag, nummer) / HERKUNFT_DATEI
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(herkunft, ensure_ascii=False, indent=2), encoding="utf-8")
    return pfad


def aufnahmen_aus_lauf(r: Rechner, ordner: Path) -> list[dict]:
    """Aufnahmen, deren Herkunft der Lauf-Ordner `<arbeitsordner>/<auftrag>/lauf-<n>` ist: `[{auftrag, nummer, herkunft}]`.
    Gelesen werden nur die `herkunft.json` der Aufnahmen, nichts im Lauf-Ordner."""
    lauf = _LAUF.match(ordner.name)
    if lauf is None or not r.arbeitsordner.is_dir():
        return []
    auftrag, nummer = ordner.parent.name, int(lauf.group(1))
    treffer = []
    for pfad in sorted(r.arbeitsordner.glob(f"*/bestand-*/{HERKUNFT_DATEI}")):
        m = _ORDNER.match(pfad.parent.name)
        try:
            herkunft = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if m and isinstance(herkunft, dict) and herkunft.get("auftrag") == auftrag and herkunft.get("lauf") == nummer:
            treffer.append({"auftrag": pfad.parent.parent.name, "nummer": int(m.group(1)), "herkunft": herkunft})
    return sorted(treffer, key=lambda t: (t["auftrag"], t["nummer"]))


# --- Rohdaten je weitere Datei einer Baugruppen-Aufnahme: aufnahme/<rel>.json -------------------------------------------

def _datei_aufnahme_pfad(r: Rechner, auftrag: str, nummer: int, rel: str) -> Path:
    teile = PureWindowsPath(rel)
    if teile.is_absolute() or teile.drive or teile.root or ".." in teile.parts or not rel.strip():
        raise BestandFehler(BESTAND_UNBEKANNT, f"{rel} ist kein relativer Pfad innerhalb der Aufnahme", pfad=rel)
    return bestand_ordner(r, auftrag, nummer) / AUFNAHME_ORDNER / f"{rel}.json"


def lade_datei_aufnahme(r: Rechner, auftrag: str, nummer: int, rel: str) -> dict:
    pfad = _datei_aufnahme_pfad(r, auftrag, nummer, rel)
    if not pfad.is_file():
        raise BestandFehler(BESTAND_UNBEKANNT, f"Keine Aufnahme von {rel} in Aufnahme {nummer} des Auftrags {auftrag}",
                            auftrag=auftrag, nummer=nummer, datei=rel)
    return json.loads(pfad.read_text(encoding="utf-8"))


def schreibe_datei_aufnahme(r: Rechner, auftrag: str, nummer: int, rel: str, daten: dict) -> Path:
    pfad = _datei_aufnahme_pfad(r, auftrag, nummer, rel)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(daten, ensure_ascii=False, indent=2), encoding="utf-8")
    return pfad
