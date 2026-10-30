"""Block `optimierung` lesen und prüfen (Spec C2 §2); der Raum ist der Teil, den die Freigabe schützt (§6).

Stellschrauben verweisen auf Zahlen-Parameter einer Spec (Geometrie) oder sind Ablaufgrößen (an jeden Lauf übergeben).
`rahmen` ist der freigegebene Raum, `bereich` der Startbereich der Suche (⊆ rahmen, darf von der Automatik und von
Claude im Rahmen geändert werden).
"""

import copy
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from swki.spec.ausdruck import ist_ausdruck

# Raum = Teil der Freigabe; alles Übrige im Block ist Bauweg der Schleife (variante, budget, plateau, automatik, start)
RAUM_FELDER = ("pruefaufgabe", "ziel", "stellschrauben", "nebenbedingungen", "szenarien", "nachlauf", "pruefstufe2",
               "erlaubte_formaenderungen")
MASKE = "<raum>"


@dataclass(frozen=True)
class Stellschraube:
    name: str
    rahmen: tuple
    bereich: tuple
    datei: str | None = None       # Spec-Datei des Parameters (None: Ablaufgröße)
    parameter: str | None = None
    ablauf: str | None = None
    schritt: float | None = None


@dataclass
class Auftrag:
    spec_pfad: Path
    block: dict
    stellschrauben: list
    modul: Path
    simulation: Path | None
    ziel: dict
    szenarien: list
    rest: dict = field(default_factory=dict)

    @property
    def ordner(self) -> Path:
        return self.spec_pfad.parent

    @property
    def maximieren(self) -> bool:
        return self.ziel["richtung"] == "max"

    def erreicht(self, wert: float | None) -> bool:
        if wert is None:
            return False
        return wert >= self.ziel["zielwert"] if self.maximieren else wert <= self.ziel["zielwert"]


def stellschrauben(block: dict, eigene: str | None) -> list[Stellschraube]:
    """Stellschrauben des Blocks; eigene: Dateiname der Spec, die den Block trägt (Ziel ohne `spec`)."""
    out = []
    for s in block.get("stellschrauben", []):
        rahmen = tuple(float(x) for x in s["rahmen"])
        datei = None if "ablauf" in s else s.get("spec", eigene)
        out.append(Stellschraube(s["name"], rahmen, tuple(float(x) for x in s.get("bereich", rahmen)), datei,
                                 s.get("parameter"), s.get("ablauf"), s.get("schritt")))
    return out


def je_datei(schrauben: list[Stellschraube], werte: dict) -> dict[str, dict]:
    """{Spec-Datei: {Parameter: Wert}} für die Geometrie-Stellschrauben einer Probe."""
    out: dict[str, dict] = {}
    for s in schrauben:
        if s.datei is not None and s.name in werte:
            out.setdefault(s.datei, {})[s.parameter] = werte[s.name]
    return out


def auf_schritt(wert: float, lo: float, schritt: float | None) -> bool:
    if not schritt:
        return True
    k = (wert - lo) / schritt
    return abs(k - round(k)) <= 1e-6


def abhaengigkeiten(block: dict, ordner: Path) -> list[Path]:
    """Weitere Dateien der Bewertung (pruefaufgabe.abhaengigkeiten), relativ zum Auftragsordner oder absolut."""
    return [ordner / d for d in block.get("pruefaufgabe", {}).get("abhaengigkeiten", [])]


def _b(pfad: str, meldung: str) -> dict:
    return {"pfad": pfad, "meldung": meldung}


def auftrag_befunde(block: dict, ordner: Path, specs: dict[str, dict], eigene: str | None) -> list[dict]:
    """Plausibilität des Blocks. specs: {Datei: Spec} der erreichbaren Specs (Teil: nur die eigene; Baugruppe: die
    Teil-Specs und die Baugruppe selbst); eigene: Dateiname der Spec mit dem Block (None, wenn unbekannt)."""
    befunde = []
    p = "optimierung"
    namen = [s["name"] for s in block.get("stellschrauben", [])]
    for i, s in enumerate(block.get("stellschrauben", [])):
        q = f"{p}.stellschrauben[{i}]"
        if s["name"] in namen[:i]:
            befunde.append(_b(f"{q}.name", f"Stellschraube {s['name']!r} doppelt"))
        lo, hi = s["rahmen"]
        if lo >= hi:
            befunde.append(_b(f"{q}.rahmen", f"rahmen muss aufsteigend sein (ist [{lo:g}, {hi:g}])"))
            continue
        b = s.get("bereich")
        if b is not None and not (lo <= b[0] < b[1] <= hi):
            befunde.append(_b(f"{q}.bereich", f"bereich [{b[0]:g}, {b[1]:g}] muss aufsteigend im rahmen "
                                              f"[{lo:g}, {hi:g}] liegen"))
        if "parameter" not in s:
            continue
        datei = s.get("spec", eigene)
        ziel = specs.get(datei) if datei is not None else next(iter(specs.values()), None)
        if ziel is None:
            befunde.append(_b(f"{q}.spec", f"{datei} ist keine Spec dieses Auftrags"))
            continue
        wert = ziel.get("parameter", {}).get(s["parameter"])
        if wert is None:
            befunde.append(_b(f"{q}.parameter", f"Parameter {s['parameter']!r} fehlt in {datei or 'der Spec'}"))
        elif ist_ausdruck(wert) or not isinstance(wert, (int, float)):
            befunde.append(_b(f"{q}.parameter", f"Parameter {s['parameter']!r} muss eine Zahl sein, kein Ausdruck "
                                                f"({wert!r}); abhängige Maße als Ausdruck davon schreiben"))
        elif not lo <= wert <= hi:
            befunde.append(_b(f"{q}.rahmen", f"Wert {wert:g} von {s['parameter']} liegt nicht im rahmen "
                                             f"[{lo:g}, {hi:g}]"))
        elif not auf_schritt(wert, lo, s.get("schritt")):
            befunde.append(_b(f"{q}.schritt", f"Wert {wert:g} von {s['parameter']} liegt nicht auf dem schritt "
                                              f"{s['schritt']:g} ab {lo:g}"))
    rahmen = {s["name"]: s["rahmen"] for s in block.get("stellschrauben", [])}
    schritt = {s["name"]: s.get("schritt") for s in block.get("stellschrauben", [])}
    for i, punkt in enumerate(block.get("start", [])):
        for name, wert in punkt.items():
            if name not in rahmen:
                befunde.append(_b(f"{p}.start[{i}].{name}", f"{name!r} ist keine Stellschraube"))
            elif not rahmen[name][0] <= wert <= rahmen[name][1]:
                befunde.append(_b(f"{p}.start[{i}].{name}", f"{wert:g} liegt nicht im rahmen {rahmen[name]}"))
            elif not auf_schritt(wert, rahmen[name][0], schritt[name]):
                befunde.append(_b(f"{p}.start[{i}].{name}", f"{wert:g} liegt nicht auf dem schritt {schritt[name]:g}"))
    for feld in ("modul", "simulation"):
        datei = block.get("pruefaufgabe", {}).get(feld)
        if datei and not (ordner / datei).is_file():
            befunde.append(_b(f"{p}.pruefaufgabe.{feld}", f"{ordner / datei} fehlt"))
    for i, pfad in enumerate(abhaengigkeiten(block, ordner)):
        if not pfad.is_file():
            befunde.append(_b(f"{p}.pruefaufgabe.abhaengigkeiten[{i}]", f"{pfad} fehlt"))
    for liste in ("szenarien",):
        szen = [s["name"] for s in block.get(liste, [])] + [s["name"] for s in
                                                             block.get("pruefstufe2", {}).get("szenarien", [])]
        for i, n in enumerate(szen):
            if n in szen[:i]:
                befunde.append(_b(f"{p}.{liste}", f"Szenario {n!r} doppelt"))
    return befunde


def sha256_datei(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def raum_felder(spec: dict) -> dict:
    """Raum-Felder des Blocks, Stellschrauben ohne `bereich` (Teil der gewöhnlichen Freigabe-Prüfsumme)."""
    block = spec["optimierung"]
    r = {k: copy.deepcopy(block[k]) for k in RAUM_FELDER if k in block}
    for s in r.get("stellschrauben", []):
        s.pop("bereich", None)
    return r


def raum(spec: dict, ordner: Path) -> dict:
    """Der freigegebene Raum des Blocks: raum_felder und SHA-256 von Prüfaufgabe, Simulations-Datei und Abhängigkeiten
    (fehlende Dateien als None)."""
    r = raum_felder(spec)
    pa = r.get("pruefaufgabe", {})
    for feld in ("modul", "simulation"):
        if feld in pa:
            pfad = ordner / pa[feld]
            pa[f"{feld}_sha256"] = sha256_datei(pfad) if pfad.is_file() else None
    if pa.get("abhaengigkeiten"):
        pa["abhaengigkeiten_sha256"] = [sha256_datei(d) if d.is_file() else None
                                        for d in abhaengigkeiten(spec["optimierung"], ordner)]
    return r


def maskiert(spec: dict, parameter: list[str]) -> dict:
    """Kopie der Spec, in der die Werte der genannten Parameter durch MASKE ersetzt sind (Raum-Prüfsumme)."""
    if not parameter:
        return spec
    kopie = dict(spec, parameter=dict(spec.get("parameter", {})))
    for name in parameter:
        if name in kopie["parameter"]:
            kopie["parameter"][name] = MASKE
    return kopie


def lies_auftrag(spec: dict, spec_pfad: Path) -> Auftrag:
    block = spec["optimierung"]
    pa = block["pruefaufgabe"]
    ordner = spec_pfad.parent
    return Auftrag(spec_pfad, block, stellschrauben(block, spec_pfad.name), ordner / pa["modul"],
                   ordner / pa["simulation"] if pa.get("simulation") else None, block["ziel"], block["szenarien"],
                   {k: v for k, v in block.items() if k not in ("stellschrauben", "ziel", "szenarien", "pruefaufgabe")})
