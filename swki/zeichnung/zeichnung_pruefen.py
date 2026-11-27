"""`swki zeichnung pruefen`: Zeichnung zurücklesen und maschinell prüfen (Plan Z1.4 Task 4a, Design §8).

Die Orchestrierung ist rein: Der Leser (`slddrw, rollen -> Ist`) kommt von außen. Vorgabe ist der COM-Rückleser aus
Task 4b (`swki.zeichnung.rueckleser`), spät importiert; Tests übergeben einen Fake-Leser. Kein COM in diesem Modul.
"""

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Callable

from swki.auftrag import auftrag_name, dateiname, lauf_datei, lauf_ordner
from swki.konfig import lade_rechner, lade_standard
from swki.spec.freigabe import freigegebene_spec
from swki.zeichnung.ist import Ist, ist_zu_dict
from swki.zeichnung.massplan import Mass, _rund, massplan, massplan_meldungen
from swki.zeichnung.pruefen import bewerte
from swki.zeichnung.regeln import lade_regeln
from swki.zeichnung.zeichnen import ZeichnungFehler, _sha, schreibe_uebergabe, waehle_lauf, zeichnungsname

Leser = Callable[[Path, dict[str, str]], Ist]


def kopf_pruefung(sha_ist: str, uebergabe: dict | None) -> list[str]:
    """Stimmt die Zeichnung noch mit der Übergabe von `swki zeichnen` überein? Eine Handänderung ist eine Meldung, kein
    Abbruch; ohne Übergabe gibt es keinen Soll-Stand und der Befehl bricht ab."""
    if not uebergabe:
        raise ZeichnungFehler("ZEICHNUNG_UEBERGABE_FEHLT", "zeichnung/zeichnung.json fehlt – zuerst swki zeichnen")
    if sha_ist != uebergabe.get("sha256_slddrw"):
        return ["ZEICHNUNG_GEAENDERT: die Zeichnung weicht von der Übergabe ab (Handänderung?) – swki aenderungen"]
    return []


def _runde(x):
    if isinstance(x, float):
        return _rund(x)
    if isinstance(x, dict):
        return {k: _runde(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_runde(v) for v in x]
    return x


def _wirkung(plan: list[Mass] | list[dict]) -> list[str]:
    """Plan nach Wirkung: ohne Id und Maßname, Geometrie gerundet, als sortierte JSON-Zeilen (Tupel und Listen sind gleich)."""
    zeilen = []
    for m in plan:
        d = asdict(m) if isinstance(m, Mass) else dict(m)
        for schluessel in ("id", "name"):
            d.pop(schluessel, None)
        if d.get("geometrie"):
            d["geometrie"] = _runde(d["geometrie"])
        zeilen.append(json.dumps(d, sort_keys=True, ensure_ascii=False, default=str))
    return sorted(zeilen)


def _standardleser() -> Leser:
    try:
        from swki.zeichnung.rueckleser import lies_zeichnung  # spät: COM erst beim Aufruf
    except ImportError as e:
        raise ZeichnungFehler("ZEICHNUNG_RUECKLESER_FEHLT", "Rückleser fehlt (Task 4b): swki.zeichnung.rueckleser") from e
    return lies_zeichnung


def zeichnung_pruefen(spec_pfad: Path, lauf: int | None = None, leser: Leser | None = None) -> dict:
    spec_pfad = spec_pfad.resolve()
    r, standard = lade_rechner(), lade_standard()
    auftrag = auftrag_name(spec_pfad)
    lauf, meldungen = waehle_lauf(spec_pfad, lauf)
    lauf_datei(spec_pfad, lauf, "zeichnung.pruefbericht").unlink(missing_ok=True)  # nie ein alter Bericht nach Abbruch
    spec = freigegebene_spec(spec_pfad)
    ordner = lauf_ordner(r, auftrag, lauf)
    ausgabe = ordner / "zeichnung"
    teil = ordner / f"{dateiname(spec, auftrag, standard)}.sldprt"
    zeichnung = ausgabe / f"{zeichnungsname(spec)}.slddrw"
    pdf, png = zeichnung.with_suffix(".pdf"), zeichnung.with_suffix(".png")
    uebergabe_pfad = ausgabe / "zeichnung.json"
    daten = json.loads(uebergabe_pfad.read_text(encoding="utf-8")) if uebergabe_pfad.exists() else None
    if not zeichnung.exists():
        raise ZeichnungFehler("ZEICHNUNG_FEHLT", f"{zeichnung} fehlt – zuerst swki zeichnen (Lauf {lauf})")
    if not teil.exists():
        raise ZeichnungFehler("ZEICHNUNG_TEIL_FEHLT", f"{teil} fehlt (Lauf {lauf})")
    sha_drw = _sha(zeichnung)
    kopf = kopf_pruefung(sha_drw, daten)
    meldungen += daten.get("meldungen") or []
    protokoll = json.loads(lauf_datei(spec_pfad, lauf, "protokoll").read_text(encoding="utf-8"))
    plan = massplan(spec, protokoll)
    meldungen_soll = massplan_meldungen(spec, protokoll)
    if _wirkung(plan) != _wirkung(daten.get("plan") or []):
        kopf.append("ZEICHNUNG_PLAN_VERALTET: der Maßplan der freigegebenen Spec weicht vom Plan der Zeichnung ab "
                    "– swki zeichnen neu ausführen")
    meldungen += kopf
    leser = leser or _standardleser()
    sha_teil = _sha(teil)
    ist = leser(zeichnung, dict(daten.get("ansichten") or {}))
    if _sha(zeichnung) != sha_drw or _sha(teil) != sha_teil:
        raise ZeichnungFehler("ZEICHNUNG_PRUEFUNG_AENDERT", "das Rücklesen hat Zeichnung oder Teil verändert")
    ist = replace(ist, sha256_slddrw=sha_drw)
    pdf_ok = pdf.exists() and not kopf
    if kopf and pdf.exists():
        meldungen.append("PDF_VERWORFEN: das PDF gehört nicht sicher zur geprüften Zeichnung")
    bericht = bewerte(ist, plan, spec, standard, lade_regeln(), pdf if pdf_ok else None, meldungen=meldungen,
                      meldungen_soll=meldungen_soll)
    if kopf:  # Handänderung oder veralteter Plan: nie still „bestanden“, die Prüfungen bleiben sichtbar
        bericht["bestanden"] = False
    bericht.update({"lauf": lauf, "kopf": {"ok": not kopf, "meldungen": kopf}, "ist": ist_zu_dict(ist),
                    "pdf": str(pdf) if pdf_ok else None,
                    "png": str(png) if png.exists() else None, "zeichnung": str(zeichnung)})
    schreibe_uebergabe(lauf_datei(spec_pfad, lauf, "zeichnung.pruefbericht"), bericht)
    return bericht
