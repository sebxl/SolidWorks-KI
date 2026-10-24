"""Aufgaben, Lauf-Ordner und git-Worktrees des Messstands (Spec §1.2)."""

import fnmatch
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from swki.konfig import lade_rechner

REPO = Path(__file__).resolve().parents[2]


def _hauptcheckout() -> Path:
    """Hauptcheckout des Repos (auch wenn der Messstand aus einem Worktree läuft): dort liegen auftraege/ und
    Herstellerdateien, die nicht im Git sind."""
    try:
        gemeinsam = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=REPO,
                                   capture_output=True, text=True, check=True).stdout.strip()
        return Path(gemeinsam).parent
    except (OSError, subprocess.CalledProcessError):
        return REPO


QUELLREPO = _hauptcheckout()
# Vorlage einer Änderungsaufgabe: Bauweg und Eingabe, keine Protokolle, Layouts, Simulationen, Berichte
VORLAGE_DATEIEN = ["*.yaml", "freigabe.json"]
VORLAGE_ORDNER = ["eingabe", "skripte"]
VORLAGE_OHNE = ["layout.*.yaml"]
AUFGABEN = REPO / "tests" / "messstand" / "aufgaben"
IMMER_ENTFERNEN = ["docs", "tests/messstand", "tests/live", "tests/baugruppe/test_referenzen.py"]


@dataclass
class Aufgabe:
    id: str
    ordner: Path
    art: str                 # teil | baugruppe
    skill: str               # konstruieren | baugruppe
    eingaben: list[str]      # Pfade relativ zum Hauptrepo
    referenz: dict           # {datei: <pfad mit {arbeitsordner}>} oder {spec_ordner: <pfad im Repo>, spec: <datei>}
    entfernen: list[str]     # im Worktree zu löschen (Referenzen)
    verboten: list[str]      # Pfadteile, deren Lesen den Lauf ungültig macht
    vorlage: str | None = None   # Änderungsaufgabe: eingefrorener Auftrag ({arbeitsordner} erlaubt)
    spec: str | None = None      # Spec der Vorlage, die geändert wird
    ausgangslauf: bool = False   # vorbereiten baut und prüft die Vorlage mit dem gemessenen Stand

    @property
    def text(self) -> str:
        return (self.ordner / "aufgabe.md").read_text(encoding="utf-8")

    def vorlage_pfad(self, arbeitsordner: Path) -> Path | None:
        return Path(self.vorlage.format(arbeitsordner=arbeitsordner)) if self.vorlage else None


def aufgaben() -> dict[str, Aufgabe]:
    erg = {}
    for p in sorted(AUFGABEN.glob("*/aufgabe.yaml")):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        erg[d["id"]] = Aufgabe(d["id"], p.parent, d["art"], d["skill"], d.get("eingaben", []), d["referenz"],
                               d.get("entfernen", []), d.get("verboten", []), d.get("vorlage"), d.get("spec"),
                               bool(d.get("ausgangslauf")))
    return erg


def vorlage_kopieren(quelle: Path, ziel: Path) -> Path:
    """Friert einen Auftrag als Vorlage ein (nur Specs, freigegebene Kopien, freigabe.json, eingabe/, skripte/)."""
    quelle, ziel = Path(quelle), Path(ziel)
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.mkdir(parents=True)
    for p in sorted(quelle.iterdir()):
        if p.is_file() and any(fnmatch.fnmatch(p.name, m) for m in VORLAGE_DATEIEN)                 and not any(fnmatch.fnmatch(p.name, m) for m in VORLAGE_OHNE):
            shutil.copy2(p, ziel / p.name)
        elif p.is_dir() and p.name in VORLAGE_ORDNER:
            shutil.copytree(p, ziel / p.name, ignore=shutil.ignore_patterns("__pycache__"))
    return ziel


def messordner() -> Path:
    return lade_rechner().arbeitsordner / "MESSSTAND"


def lauf_id(durchgang: int, aufgabe: str, nr: int) -> str:
    return f"d{durchgang}-{aufgabe}-{nr}"


def auftrag_name(lauf: str) -> str:
    return f"MESS-{lauf}"


def lauf_ordner(lauf: str) -> Path:
    durchgang = lauf.split("-", 1)[0]
    return messordner() / f"durchgang-{durchgang[1:]}" / lauf


def _git(*args, cwd=REPO) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def worktree_anlegen(lauf: str, commit: str, alle: dict[str, Aufgabe]) -> Path:
    wt = messordner() / "wt" / lauf
    worktree_entfernen(wt)
    wt.parent.mkdir(parents=True, exist_ok=True)
    _git("worktree", "add", "--detach", str(wt), commit)
    subprocess.run(["cmd", "/c", "mklink", "/J", str(wt / ".venv"), str(REPO / ".venv")], check=True,
                   capture_output=True)
    (wt / "config").mkdir(exist_ok=True)
    shutil.copy2(REPO / "config" / "rechner.yaml", wt / "config" / "rechner.yaml")
    for a in alle.values():   # Referenzen aller Aufgaben entfernen, nicht nur der eigenen
        for rel in a.entfernen:
            p = wt / rel
            if p.is_dir():
                shutil.rmtree(p)
            elif p.exists():
                p.unlink()
    # Dokumente und Tests, die Referenzlösungen enthalten (Pläne, Ergebnisse, Live-Tests), fehlen in jedem Lauf
    for rel in IMMER_ENTFERNEN:
        p = wt / rel
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        elif p.exists():
            p.unlink()
    return wt


def worktree_entfernen(wt: Path) -> None:
    if not wt.exists():
        return
    venv = wt / ".venv"
    if venv.exists():
        subprocess.run(["cmd", "/c", "rmdir", str(venv)], capture_output=True)   # nur die Junction
    subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=REPO, capture_output=True)
    if wt.exists():
        shutil.rmtree(wt, ignore_errors=True)
    _git("worktree", "prune")


def auftrag_anlegen(wt: Path, lauf: str, a: Aufgabe) -> Path:
    auftrag = wt / "auftraege" / auftrag_name(lauf)
    if a.vorlage:
        arbeit = lade_rechner().arbeitsordner if "{arbeitsordner}" in a.vorlage else Path()
        shutil.copytree(a.vorlage_pfad(arbeit), auftrag, dirs_exist_ok=True)
    (auftrag / "eingabe").mkdir(parents=True, exist_ok=True)
    (auftrag / "aufgabe.md").write_text(a.text, encoding="utf-8")
    for rel in a.eingaben:
        q = QUELLREPO / rel
        shutil.copy2(q, auftrag / "eingabe" / q.name)
    return auftrag


PROMPT = """Messstand-Lauf {lauf}. Du bist der Konstruktions-Agent; der Nutzer ist nicht erreichbar.

Arbeitsverzeichnis (git-Worktree des Repos): {wt}
Jeder Shell-Befehl beginnt mit `cd "{wt}" && …` (die Shell springt sonst ins Hauptrepo zurück), z. B.
`cd "{wt}" && .venv\\Scripts\\python.exe -m swki validieren auftraege\\{auftrag}\\<spec>.yaml`.
Lies und schreibe nur unter {wt}. Das Hauptrepo {repo} (insbesondere dessen auftraege\\ und tests\\referenz\\), {messrepo} sowie
{arbeit}\\AP68-Pruefstation und {arbeit}\\MESSSTAND sind tabu; swki selbst schreibt in {arbeit}\\{auftrag}.

Auftrag: Ordner {wt}\\auftraege\\{auftrag}\\ – Aufgabe in aufgabe.md, Eingaben in eingabe\\.
Vorgehen wie im echten Betrieb nach dem Skill `{skill}` bis Prüfer bestanden und `swki bericht`. Lies den Skill mit dem
Read-Tool aus {wt}\\.claude\\skills\\{skill}\\SKILL.md (nicht mit dem Skill-Tool: es liefert einen älteren Stand).

Anweisungen des Nutzers für diesen Lauf (gehen den Skills vor):
- Keine Rückfragen. Wo der Skill den Nutzer fragen würde, entscheide selbst und dokumentiere die Annahme als Kommentar
  in der Spec.
- Die Freigabe für diesen Auftrag ist erteilt: `swki freigeben` ohne Rückfrage, sobald `validieren` gültig ist.
  Alle Schritte vor der Freigabe-Vorlage (auch der Konstruktionsreview, wo der Skill ihn verlangt) laufen wie im
  Betrieb; nur die Rückfrage an den Nutzer entfällt.
- Kein Brainstorming, keine Pläne, kein git, keine Commits, keine Änderungen an swki/ oder an den Skills.
- SolidWorks ist frisch gestartet. Neu starten nur bei SPEICHER_KNAPP oder Hänger: `cd "{wt}" && .venv\\Scripts\\python.exe -m werkzeuge.sw_neustart`.
- Arbeite zügig; Zeit, Tool-Aufrufe, Tokens und Fehler werden gemessen.
- Starte Subagenten (Prüfer) und Befehle im Vordergrund und warte auf ihr Ergebnis (nicht im Hintergrund).

Antworte am Ende nur mit: Status (bestanden / nicht bestanden), letzter Lauf, Pfad der Spec, offene Punkte (1–3 Zeilen).
"""


def prompt(lauf: str, wt: Path, a: Aufgabe) -> str:
    arbeit = lade_rechner().arbeitsordner
    return PROMPT.format(lauf=lauf, wt=wt, repo=QUELLREPO, messrepo=REPO, arbeit=arbeit, auftrag=auftrag_name(lauf),
                         skill=a.skill)


def schreibe_json(p: Path, d: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def lies_json(p: Path) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8"))
