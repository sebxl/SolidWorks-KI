"""Freigaberegel für autonome Schleifen (Spec C2 §6, vom Nutzer am 25.10.2026 bestätigt).

Die Freigabe eines Optimierungsauftrags gibt den Raum frei. `swki freigeben` legt dazu im Eintrag der Spec mit dem
Block `optimierung` die Raum-Prüfsumme ab: die Prüfsumme der Anforderungen mit maskierten Werten der Stellschrauben-
Parameter (Baugruppe: auch die der Teil-Specs), zusammen mit dem Raum (auftrag.raum, mit SHA-256 der Prüfaufgabe).
`freigeben_im_raum` gibt ein Ergebnis im Raum ohne Rückfrage frei: Raum-Prüfsumme gleich, jede Stellschraube im
`rahmen` (und auf dem `schritt`), Spec gültig. Der Nachweis (Werte vorher/nachher, Quelle) steht im Eintrag `im_raum`.
"""

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path

from swki.optimierung.auftrag import maskiert, raum, stellschrauben
from swki.spec.freigabe import FreigabeFehler, freigabe_eintrag, freigeben, freigegebene_spec, pruefsumme
from swki.spec.laden import SpecFehler, art_der_datei, lade_spec, lade_yaml


def _sha(daten) -> str:
    return hashlib.sha256(json.dumps(daten, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                                     default=str).encode("utf-8")).hexdigest()


def _namen(block: dict, eigene: str) -> dict[str, list[str]]:
    """{Datei: [Parameter]} der Geometrie-Stellschrauben."""
    out: dict[str, list[str]] = {}
    for s in stellschrauben(block, eigene):
        if s.datei is not None:
            out.setdefault(s.datei, []).append(s.parameter)
    return out


def raum_summe(spec: dict, pfad: Path, teile: dict[str, dict] | None = None, kaufteile: dict | None = None) -> str:
    """Raum-Prüfsumme der Spec mit dem Block; teile: Teil-Specs der Baugruppe {Datei: Spec}."""
    namen = _namen(spec["optimierung"], pfad.name)
    teil_summen = None
    if spec.get("art") == "baugruppe":
        teil_summen = {d: pruefsumme(maskiert(s, namen.get(d, []))) for d, s in (teile or {}).items()}
        teil_summen |= kaufteile or {}
    kern = maskiert(spec, namen.get(pfad.name, []))
    return _sha({"anforderungen": pruefsumme(kern, teil_summen), "raum": raum(spec, pfad.parent)})


def raum_eintrag(spec: dict, pfad: Path, teile: dict[str, dict] | None = None, kaufteile: dict | None = None) -> dict:
    """Eintrag `raum` für freigabe.json."""
    return {"pruefsumme": raum_summe(spec, pfad, teile, kaufteile),
            "stellschrauben": {s.name: list(s.rahmen) for s in stellschrauben(spec["optimierung"], pfad.name)}}


def _laden(pfad: Path):
    """(spec, teile, kaufteil_summen, bg) – Baugruppe über lade_baugruppe; wirft FreigabeFehler SPEC_UNGUELTIG."""
    try:
        if art_der_datei(pfad) == "baugruppe":
            from swki.baugruppe.freigabe import kaufteil_summen  # spät importiert (Kreisimport)
            from swki.baugruppe.laden import lade_baugruppe

            bg = lade_baugruppe(pfad)
            return bg.spec, bg.teile, kaufteil_summen(bg), bg
        return lade_spec(pfad), None, None, None
    except SpecFehler as e:
        raise FreigabeFehler("SPEC_UNGUELTIG", f"{pfad.name}: {e} – {e.daten['befunde'][:3]}") from e


def _werte_pruefen(pfad: Path, block: dict, aktuell: dict[str, dict]) -> dict:
    """Nachweis {Datei: {Parameter: {vorher, nachher, rahmen}}} der geänderten Stellschrauben; wirft AUSSERHALB_RAUM."""
    nachweis = {}
    for s in stellschrauben(block, pfad.name):
        if s.datei is None:
            continue
        wert = aktuell[s.datei].get("parameter", {}).get(s.parameter)
        lo, hi = s.rahmen
        if not isinstance(wert, (int, float)) or not lo - 1e-9 <= wert <= hi + 1e-9:
            raise FreigabeFehler("AUSSERHALB_RAUM", f"{s.datei}: {s.parameter} = {wert!r} liegt nicht im rahmen "
                                                    f"[{lo:g}, {hi:g}] der Stellschraube {s.name}. Nutzer fragen.")
        if s.schritt:
            k = (wert - lo) / s.schritt
            if abs(k - round(k)) > 1e-6:
                raise FreigabeFehler("AUSSERHALB_RAUM", f"{s.datei}: {s.parameter} = {wert:g} liegt nicht auf dem "
                                                        f"Schritt {s.schritt:g} ab {lo:g} (Stellschraube {s.name})")
        kopie = pfad.parent / s.datei
        try:
            vorher = freigegebene_spec(kopie).get("parameter", {}).get(s.parameter)
        except FileNotFoundError:
            vorher = None
        if vorher is None or not math.isclose(float(vorher), float(wert), abs_tol=1e-12):
            nachweis.setdefault(s.datei, {})[s.parameter] = {"vorher": vorher, "nachher": wert, "rahmen": [lo, hi]}
    return nachweis


def pruefe_im_raum(pfad: Path) -> dict:
    """Liegt der jetzige Stand im freigegebenen Raum? Wirft FreigabeFehler (RAUM_FEHLT, AUSSERHALB_RAUM,
    SPEC_UNGUELTIG, RAUM_GEAENDERT); sonst {"im_raum": True, "werte": Nachweis}."""
    eintrag = freigabe_eintrag(pfad)
    roh = lade_yaml(pfad)
    if eintrag is None or "raum" not in eintrag or "optimierung" not in roh:
        raise FreigabeFehler("RAUM_FEHLT", f"{pfad.name} hat keine Raum-Freigabe (Block optimierung mit swki "
                                           "freigeben). Bei Stellschrauben in Teil-Specs auf der Baugruppe aufrufen.")
    aktuell = {pfad.name: roh}
    for s in stellschrauben(roh["optimierung"], pfad.name):
        if s.datei is not None and s.datei not in aktuell:
            aktuell[s.datei] = lade_yaml(pfad.parent / s.datei)
    werte = _werte_pruefen(pfad, roh["optimierung"], aktuell)
    spec, teile, kaufteile, _ = _laden(pfad)
    if raum_summe(spec, pfad, teile, kaufteile) != eintrag["raum"]["pruefsumme"]:
        raise FreigabeFehler("RAUM_GEAENDERT", f"{pfad.name}: Anforderungen außerhalb der Stellschrauben oder der Raum "
                                               "(Ziel, Szenarien, Rahmen, Prüfaufgabe …) wurden nach der Freigabe "
                                               "geändert. Nutzer fragen und neu freigeben.")
    return {"im_raum": True, "werte": werte}


def freigeben_im_raum(pfad: Path, quelle: str | None = None) -> dict:
    """Gibt ein Ergebnis im Raum frei (ohne Rückfrage, Spec C2 §6); quelle: z. B. der Optimierungslauf."""
    geprueft = pruefe_im_raum(pfad)
    spec, teile, kaufteile, bg = _laden(pfad)
    alt = freigabe_eintrag(pfad)
    jetzt = datetime.now().isoformat(timespec="seconds")
    nachweis = {"werte": geprueft["werte"], "zeitpunkt": jetzt, "quelle": quelle,
                "basis_pruefsumme": alt["pruefsumme"]}
    zusatz = {"raum": alt["raum"], "im_raum": nachweis}
    if bg is not None:
        from swki.baugruppe.freigabe import freigeben_baugruppe  # spät importiert (Kreisimport)

        erg = freigeben_baugruppe(bg, zusatz=zusatz)
    else:
        erg = freigeben(pfad, spec, zusatz=zusatz)
    return {"spec": str(pfad), **erg}


def raum_hinweis(pfad: Path, fehler: FreigabeFehler) -> FreigabeFehler:
    """FREIGABE_VERALTET mit Hinweis, wenn der jetzige Stand im freigegebenen Raum liegt (für swki bauen)."""
    if fehler.daten.get("code") != "FREIGABE_VERALTET" or "raum" not in (freigabe_eintrag(pfad) or {}):
        return fehler
    try:
        pruefe_im_raum(pfad)
    except (FreigabeFehler, SpecFehler, OSError):
        return fehler
    neu = FreigabeFehler("FREIGABE_VERALTET", f"{fehler} Die Änderung liegt im freigegebenen Raum des "
                                               f"Optimierungsauftrags: swki freigeben {pfad.name} --im-raum (ohne "
                                               "Rückfrage, Spec C2 §6), dann bauen.")
    neu.daten["im_raum"] = True
    return neu
