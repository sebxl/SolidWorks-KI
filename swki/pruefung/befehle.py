"""Befehle "swki pruefen", "swki status" und "swki bericht"."""

import json
import subprocess
from pathlib import Path

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner, laeufe
from swki.cli import SwkiFehler
from swki.compiler import sw
from swki.konfig import PROJEKT, lade_rechner, lade_standard
from swki.pruefung.bericht import bericht_markdown
from swki.pruefung.bewertung import baum_kennzahl, bewerte
from swki.pruefung.bilder import screenshots
from swki.pruefung.messen import kontext_aus_datei, messe, oeffne
from swki.pruefung.schleife import empfehlung, lies_laeufe, max_laeufe
from swki.spec.freigabe import freigegebene_spec, pruefe_freigabe
from swki.spec.laden import lade_spec
from swki.verbindung import verbinde


def pruefen(spec_pfad: Path, lauf: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    pruefe_freigabe(spec_pfad, spec)
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    if lauf is None:
        bisher = laeufe(r, auftrag)
        if not bisher:
            raise SwkiFehler(f"Auftrag {auftrag} hat noch keinen Lauf. Zuerst: swki bauen")
        lauf = bisher[-1]
    ordner = lauf_ordner(r, auftrag, lauf)
    teil = ordner / f"{dateiname(spec, auftrag, standard)}.sldprt"
    if not teil.exists():
        raise SwkiFehler(f"{teil} fehlt (Lauf {lauf} ohne gespeichertes Teil)")
    app = verbinde(r.sw_jahr)
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    soll = freigegebene_spec(spec_pfad)
    model = oeffne(app, teil)
    try:
        ctx = kontext_aus_datei(app, model, spec, spec_pfad, standard["toleranzen"]["anker_mm"], protokoll)
        messwerte = messe(ctx, soll)
        bilder = screenshots(app, model, ordner / "bilder")
    finally:
        sw.schliesse(app, model)
    bericht = {
        "auftrag": auftrag, "spec": spec_pfad.name, "lauf": lauf, "datei": str(teil),
        **bewerte(spec, messwerte, standard, soll), "baum": baum_kennzahl(spec, protokoll), "bilder": bilder,
    }
    pruefer_datei = lauf_datei(spec_pfad, lauf, "pruefer")
    if pruefer_datei.exists():
        # Urteil gehört zum vorherigen Prüfbericht dieses Laufs; sonst könnte "status" ein veraltetes "bestanden" melden.
        pruefer_datei.unlink()
        bericht["pruefer_urteil_verworfen"] = True
    text = json.dumps(bericht, indent=2, ensure_ascii=False) + "\n"
    (ordner / "pruefbericht.json").write_text(text, encoding="utf-8")
    ziel = lauf_datei(spec_pfad, lauf, "pruefbericht")
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    return bericht


def status(spec_pfad: Path, anweisung: int | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    alle = lies_laeufe(spec_pfad)
    maximal = max_laeufe(spec, lade_standard(), anweisung)
    code, text = empfehlung(alle, maximal)
    return {"spec": spec_pfad.name, "laeufe": alle, "max_laeufe": maximal, "empfehlung": code, "text": text}


def _lies(pfad: Path) -> dict | None:
    return json.loads(pfad.read_text(encoding="utf-8")) if pfad.exists() else None


def _compiler_aenderungen(seit: str) -> list[str]:
    ergebnis = subprocess.run(
        ["git", "log", f"--since={seit}", "--format=%h %s", "--", "swki/compiler", "schema"],
        cwd=PROJEKT, capture_output=True, text=True, encoding="utf-8",
    )
    return [z for z in ergebnis.stdout.splitlines() if z.strip()]


def bericht(spec_pfad: Path) -> dict:
    spec_pfad = spec_pfad.resolve()
    spec = lade_spec(spec_pfad)
    stand = status(spec_pfad)
    alle = stand["laeufe"]
    letzter = alle[-1]["lauf"] if alle else None
    protokoll = _lies(lauf_datei(spec_pfad, letzter, "protokoll")) if letzter else None
    erstes = _lies(lauf_datei(spec_pfad, alle[0]["lauf"], "protokoll")) if alle else None
    text = bericht_markdown(
        spec, auftrag_name(spec_pfad), alle, (stand["empfehlung"], stand["text"]),
        _lies(lauf_datei(spec_pfad, letzter, "pruefbericht")) if letzter else None,
        _lies(lauf_datei(spec_pfad, letzter, "pruefer")) if letzter else None,
        protokoll,
        _compiler_aenderungen(erstes["gestartet"]) if erstes else [],
    )
    ziel = spec_pfad.parent / "bericht.md"
    ziel.write_text(text, encoding="utf-8")
    return {"bericht": str(ziel), "status": stand["empfehlung"]}


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("pruefen", help="gespeicherten Lauf messen, bewerten, Screenshots (pruefbericht.json)")
    p.add_argument("spec")
    p.add_argument("--lauf", type=int, help="Vorgabe: letzter Lauf")
    p.set_defaults(func=lambda a: pruefen(Path(a.spec), a.lauf))
    p = subparsers.add_parser("status", help="Stand der Nachbesserungsschleife und Empfehlung")
    p.add_argument("spec")
    p.add_argument("--max", type=int, help="maximale Nachbesserungen laut Anweisung im Chat")
    p.set_defaults(func=lambda a: status(Path(a.spec), a.max))
    p = subparsers.add_parser("bericht", help="bericht.md des Auftrags schreiben")
    p.add_argument("spec")
    p.set_defaults(func=lambda a: bericht(Path(a.spec)))
