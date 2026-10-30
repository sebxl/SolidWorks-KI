"""Präzisions-Fallen des Bewertungsbogens (Spec 2026-10-23-bewertungsbogen-design §3): fest gebaute Läufe mit einem
Deutungsfehler, den `swki pruefen` grundsätzlich nicht sieht, und richtige Läufe als Fehlalarm-Kontrolle.

Je Falle liegt unter tests/messstand/fallen/<id>/falle.yaml: id, art (falle|richtig), basis (Ordner mit Specs,
{arbeitsordner} erlaubt, sonst relativ zum Repo), dateien (aus der Basis; leer = alles), aufgabe (Messstand-Aufgabe,
deren aufgabe.md als Eingabe dient), eingaben (relativ zum Hauptcheckout), ersetzen ([{datei, alt, neu}] – der
eingebaute Fehler), spec, erwartet {knoten, stichworte}, beschreibung. Optional spec/ als Überlagerung. Die
Beschreibung sieht der Prüfer nie. Ablauf je Durchgang: `fallen auftraege` (Prüf-Prompts, dreimal je Falle) → das Prüfverfahren des gemessenen
Stands schreibt urteil-<id>-<k>.json → `fallen auswerten` (Mehrheit, entscheid.json für unklare Fälle)."""

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from werkzeuge.messstand.umgebung import AUFGABEN, QUELLREPO, REPO

FALLEN = REPO / "tests" / "messstand" / "fallen"
WIEDERHOLUNGEN = 3
KLASSEN_FALLE = ("treffer", "unklar", "verfehlt")
KLASSEN_RICHTIG = ("ok", "fehlalarm")


@dataclass
class Falle:
    id: str
    art: str                  # falle | richtig
    spec: str                 # Datei in spec/, die gebaut und geprüft wird
    ordner: Path
    eingaben: list[str] = field(default_factory=list)    # relativ zum Hauptcheckout
    knoten: list[str] = field(default_factory=list)
    stichworte: list[str] = field(default_factory=list)
    beschreibung: str = ""
    basis: str | None = None
    dateien: list[str] = field(default_factory=list)
    aufgabe: str | None = None
    ersetzen: list[dict] = field(default_factory=list)

    @property
    def auftrag(self) -> str:
        return f"MESSFALLE-{self.id}"


def fallen() -> dict[str, Falle]:
    erg = {}
    for p in sorted(FALLEN.glob("*/falle.yaml")):
        d = yaml.safe_load(p.read_text(encoding="utf-8"))
        e = d.get("erwartet") or {}
        erg[d["id"]] = Falle(d["id"], d["art"], d["spec"], p.parent, d.get("eingaben", []), e.get("knoten", []),
                             e.get("stichworte", []), d.get("beschreibung", ""), d.get("basis"),
                             d.get("dateien", []), d.get("aufgabe"), d.get("ersetzen", []))
    return erg


def einordnen(f: Falle, urteil: dict) -> str:
    """Klasse eines Prüfurteils: Falle → treffer | unklar | verfehlt, richtig → ok | fehlalarm."""
    maengel = urteil.get("maengel") or []
    if f.art == "richtig":
        return "ok" if urteil.get("bestanden") and not maengel else "fehlalarm"
    if urteil.get("bestanden") and not maengel:
        return "verfehlt"
    for m in maengel:
        knoten = [str(k).lower() for k in (m.get("knoten") or [])]
        text = " ".join(str(m.get(k, "")) for k in ("beschreibung", "text", "vorschlag")).lower()
        if any(e.lower() in k for e in f.knoten for k in knoten) or any(s.lower() in text for s in f.stichworte):
            return "treffer"
    return "unklar"


def auswerten(ordner: Path) -> dict:
    """Mehrheit je Falle über urteil-<id>-<k>.json; entscheid.json ({"<id>-<k>": klasse}) entscheidet unklare Fälle;
    swki_treffer.json (Liste von ids) = Fallen, die schon `swki pruefen` fand."""
    ordner = Path(ordner)
    entscheid = json.loads((ordner / "entscheid.json").read_text(encoding="utf-8")) \
        if (ordner / "entscheid.json").exists() else {}
    swki = set(json.loads((ordner / "swki_treffer.json").read_text(encoding="utf-8"))) \
        if (ordner / "swki_treffer.json").exists() else set()
    je_falle, treffer, fehlalarme = {}, 0, 0
    for fid, f in fallen().items():
        if fid in swki:
            je_falle[fid] = {"art": f.art, "ergebnis": "treffer" if f.art == "falle" else "fehlalarm", "quelle": "swki"}
        else:
            klassen = {}
            for p in sorted(ordner.glob(f"urteil-{fid}-*.json")):
                schluessel = p.stem[len("urteil-"):]
                klassen[schluessel] = entscheid.get(schluessel) or einordnen(f, json.loads(p.read_text(encoding="utf-8")))
            gesucht = "treffer" if f.art == "falle" else "fehlalarm"
            n = sum(1 for k in klassen.values() if k == gesucht)
            ergebnis = gesucht if klassen and n > len(klassen) / 2 else ("verfehlt" if f.art == "falle" else "ok")
            je_falle[fid] = {"art": f.art, "ergebnis": ergebnis, "klassen": klassen,
                             "unklar": [s for s, k in klassen.items() if k == "unklar"]}
        treffer += je_falle[fid]["ergebnis"] == "treffer"
        fehlalarme += je_falle[fid]["ergebnis"] == "fehlalarm"
    return {"treffer": treffer, "fehlalarme": fehlalarme, "je_falle": je_falle}


def pruefauftrag(pruefer_md: str, auftrag: str) -> str:
    """Prompt für einen Fallen-Prüfer: Anweisung aus pruefer.md (ohne Frontmatter) des gemessenen Stands + Auftrag."""
    text = pruefer_md
    if text.startswith("---"):
        text = text.split("---", 2)[2]
    return (f"{text.strip()}\n\n## Dein Auftrag\n\n{auftrag}\n\nDu änderst nichts und benutzt nur Read und Glob.")


def _basis(f: Falle, arbeitsordner: Path | None) -> Path:
    if "{arbeitsordner}" in f.basis:
        return Path(f.basis.format(arbeitsordner=arbeitsordner))
    return REPO / f.basis


def auftrag_anlegen(f: Falle, auftraege: Path, arbeitsordner: Path | None = None) -> Path:
    """auftraege/MESSFALLE-<id>: Basis (ganz oder `dateien`), Überlagerung spec/, Ersetzungen, aufgabe.md und Eingaben
    (im Hauptcheckout gelesen). Eine Ersetzung, die nicht genau einmal passt, ist ein Fehler der Falle."""
    ziel = Path(auftraege) / f.auftrag
    if ziel.exists():
        shutil.rmtree(ziel)
    ziel.mkdir(parents=True)
    if f.basis:
        b = _basis(f, arbeitsordner)
        if f.dateien:
            for rel in f.dateien:
                (ziel / rel).parent.mkdir(parents=True, exist_ok=True)
                (shutil.copytree if (b / rel).is_dir() else shutil.copy2)(b / rel, ziel / rel)
        else:
            shutil.copytree(b, ziel, dirs_exist_ok=True, ignore=shutil.ignore_patterns("protokolle", "__pycache__"))
    if (f.ordner / "spec").is_dir():
        shutil.copytree(f.ordner / "spec", ziel, dirs_exist_ok=True)
    for e in f.ersetzen:
        p = ziel / e["datei"]
        text = p.read_text(encoding="utf-8")
        if text.count(e["alt"]) != 1:
            raise ValueError(f"Falle {f.id}: '{e['alt']}' kommt in {e['datei']} {text.count(e['alt'])}-mal vor")
        p.write_text(text.replace(e["alt"], e["neu"]), encoding="utf-8")
    if f.aufgabe:
        shutil.copy2(AUFGABEN / f.aufgabe / "aufgabe.md", ziel / "aufgabe.md")
    (ziel / "eingabe").mkdir(exist_ok=True)
    for rel in f.eingaben:
        q = QUELLREPO / rel
        if q.is_dir():
            shutil.copytree(q, ziel / "eingabe" / q.name, dirs_exist_ok=True)
        else:
            shutil.copy2(q, ziel / "eingabe" / q.name)
    return ziel
