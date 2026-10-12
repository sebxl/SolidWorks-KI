"""swki durchlauf <spec>: validieren → (freigeben) → bauen → prüfen → status in einem Aufruf, mit kompakter Ausgabe.

Spart dem Agenten Runden und Kontext (Messstand Umbau 1). `--freigeben` nur, wenn der Nutzer die Anforderungen
ausdrücklich freigegeben hat (CLAUDE.md); ohne die Option braucht der Durchlauf eine gültige Freigabe.
Bei einem Fehler endet der Durchlauf im betreffenden Schritt und nennt ihn (`schritt`). `--neustart` startet
SolidWorks vor dem Bauen und vor dem Prüfen frisch (werkzeuge.sw_neustart; nur ohne offene Dokumente) – Standardweg für
Baugruppen mit Bewegungen."""

from argparse import Namespace
from pathlib import Path

from swki.cli import SwkiFehler, ganzzahl_ab


def _kurz_pruefung(bericht: dict) -> dict:
    fehlgeschlagen = [{k: v for k, v in p.items() if k != "ok"}
                      for p in bericht.get("pruefungen", []) if p.get("ok") is False]
    ungeprueft = [p["id"] for p in bericht.get("pruefungen", []) if p.get("ok") is None]
    erg = {"bestanden": bericht.get("bestanden"), "maengel": bericht.get("maengel", []),
           "fehlgeschlagen": fehlgeschlagen, "ohne_urteil": ungeprueft,
           "geprueft": len(bericht.get("pruefungen", [])), "baum": bericht.get("baum"),
           "bilder": sorted(set(str(Path(b).parent) for b in (bericht.get("bilder") or {}).values()))}
    if bericht.get("steckbrief_text"):
        erg["steckbrief"] = bericht["steckbrief_text"].splitlines()
    return erg


def _neustart(erg: dict, vor: str) -> dict | None:
    """SolidWorks frisch starten; None = gut, sonst das Abbruch-Ergebnis (schritt: neustart)."""
    from werkzeuge.sw_neustart import NeustartFehler, neustart   # spät: werkzeuge liegt neben swki im Repo

    try:
        n = neustart()
    except NeustartFehler as e:
        return {**erg, "schritt": "neustart", "vor": vor, "fehler": str(e)}
    if not n.get("einstellungen_ok"):
        return {**erg, "schritt": "neustart", "vor": vor, "einstellungen": n.get("einstellungen"),
                "fehler": "Einstellungen nach dem Neustart nicht wie erwartet (Toggle 10 = False, Integer 6 = 1)"}
    erg.setdefault("neustart", []).append({"vor": vor, **{k: n.get(k) for k in ("privat_mb_vorher", "beendet_s",
                                                                               "gestartet_s")}})
    return None


def pruefer_auftrag(spec_pfad: Path, lauf: int, bericht: dict) -> str:
    """Fertiger Prompt für den Prüfer-Agenten (nur erlaubte Eingaben: Eingabe, Freigabe-Kopien, Prüfbericht, Bilder,
    Steckbrief – keine Protokolle, keine Skripte)."""
    from swki.auftrag import lauf_datei

    ordner = spec_pfad.parent
    kopien = ", ".join(str(p) for p in sorted(ordner.glob("*.freigegeben.yaml")))
    bilder = sorted({str(Path(b).parent) for b in (bericht.get("bilder") or {}).values()})
    laufordner = Path(bericht["datei"]).parent if bericht.get("datei") else None
    steck = laufordner / "steckbrief.txt" if laufordner and (laufordner / "steckbrief.txt").exists() else None
    teile = [f"Prüfe Lauf {lauf} von {spec_pfad.name}.", f"Eingabe des Nutzers: {ordner / 'eingabe'} (und aufgabe.md, falls vorhanden).",
             f"Freigegebene Spezifikation(en): {kopien}.", f"Prüfbericht: {lauf_datei(spec_pfad, lauf, 'pruefbericht')}."]
    if bilder:
        teile.append(f"Screenshots: {', '.join(bilder)}.")
    if steck:
        teile.append(f"Geometrie-Steckbrief: {steck} (Lage und Vorzeichen zuerst daran prüfen).")
    teile.append("Antworte nur mit dem JSON-Urteil.")
    return " ".join(teile)


def durchlauf(spec_pfad: Path, freigeben: bool = False, maximal: int | None = None, neustart: bool = False) -> dict:
    from swki.compiler.bauen import BauAbbruch, _bauen
    from swki.pruefung.befehle import pruefen, status
    from swki.spec.befehle import _freigeben, _validieren

    spec_pfad = spec_pfad.resolve()
    erg: dict = {"spec": spec_pfad.name}
    try:
        v = _validieren(Namespace(spec=str(spec_pfad)))
    except SwkiFehler as e:
        return {**erg, "schritt": "validieren", "fehler": str(e), **getattr(e, "daten", {})}
    erg["hinweise"] = v.get("hinweise", [])
    if "auto" in v:
        erg["auto"] = v["auto"]
    pruefwerte = [h for h in erg["hinweise"] if h.get("art") == "pruefwert"]
    if freigeben and pruefwerte:   # nach der Freigabe kostet ein falscher Prüfwert eine neue Freigabe
        return {**erg, "schritt": "validieren", "pruefwerte": pruefwerte,
                "fehler": "Prüfwert weicht von der Rechnung aus den Features ab – Spec korrigieren (oder bewusst "
                          "abweichend: swki freigeben, dann swki durchlauf ohne --freigeben)"}
    if freigeben:
        try:
            f = _freigeben(Namespace(spec=str(spec_pfad)))
        except SwkiFehler as e:
            return {**erg, "schritt": "freigeben", "fehler": str(e), **getattr(e, "daten", {})}
        erg["freigegeben"] = f.get("kopie", True)
    if neustart and (abbruch := _neustart(erg, "bauen")):
        return abbruch
    try:
        b = _bauen(Namespace(spec=str(spec_pfad), lauf=None, verwerfen=False, uebernommen=False))
    except BauAbbruch as e:
        d, f = e.daten, e.daten.get("fehler") or {}
        return {**erg, "schritt": "bauen", "lauf": d.get("lauf"), "code": f.get("code"), "meldung": f.get("meldung"),
                "knoten": [k for k in d.get("knoten", []) if k.get("status") not in ("ok", "uebersprungen")]}
    except SwkiFehler as e:
        return {**erg, "schritt": "bauen", "fehler": str(e), **getattr(e, "daten", {})}
    erg |= {"lauf": b["lauf"], "bau_s": b.get("dauer_s")}
    if neustart and (abbruch := _neustart(erg, "pruefen")):
        return abbruch
    try:
        p = pruefen(spec_pfad, b["lauf"])
    except SwkiFehler as e:
        return {**erg, "schritt": "pruefen", "fehler": str(e), **getattr(e, "daten", {})}
    erg["pruefung"] = _kurz_pruefung(p)
    if p.get("bestanden"):
        erg["pruefer_auftrag"] = pruefer_auftrag(spec_pfad, b["lauf"], p)
    st = status(spec_pfad, maximal)
    erg |= {"schritt": "fertig", "empfehlung": st["empfehlung"], "empfehlung_text": st["text"],
            "naechstes": "Prüfer-Agent starten (Eingabe, freigegebene Spec, Prüfbericht, Bilder)"
            if p.get("bestanden") else "nachbessern (Bauweg) und erneut swki durchlauf"}
    return erg


def einrichten(subparsers) -> None:
    p = subparsers.add_parser("durchlauf", help="validieren, (freigeben), bauen, prüfen, status in einem Aufruf")
    p.add_argument("spec")
    p.add_argument("--freigeben", action="store_true",
                   help="vorher freigeben – nur nach ausdrücklichem OK des Nutzers zu den Anforderungen")
    p.add_argument("--max", type=ganzzahl_ab(0, "--max"), help="maximale Nachbesserungen laut Anweisung im Chat")
    p.add_argument("--neustart", action="store_true",
                   help="SolidWorks vor dem Bauen und vor dem Prüfen frisch starten (Baugruppen mit Bewegungen)")
    p.set_defaults(func=lambda a: durchlauf(Path(a.spec), a.freigeben, a.max, neustart=a.neustart))
