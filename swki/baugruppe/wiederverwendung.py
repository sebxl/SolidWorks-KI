"""Unveränderte Eigenteile einer Baugruppe aus einem früheren Lauf übernehmen statt neu bauen (BTP Umbau 3,
Recherche O5).

Schlüssel eines Teils = SHA-256 über alles, was den Teilbau bestimmt: Teil-Spec (ganz) und ihr Dateiname, Skriptdateien
(`typ: skript`), Compiler-Code (Import-Hülle von `swki.compiler.bauen`), Wissensdateien und Teil-Schema, Einstellungen
aus `config/standard.yaml` (ohne Schalter und Prüfgrenzen), Auftrag, SolidWorks-Jahr und -Revision, Teilvorlage und –
bei `material` – die Materialdatenbanken. Quelle ist nur ein Lauf desselben Auftrags, dessen Teilprotokoll `ok` ist,
denselben Schlüssel trägt und dessen Datei noch die SHA-256 aus dem Protokoll hat (eine von Hand geänderte Datei ist
nie Quelle). Gesperrt sind Schlüssel und Datei eines Teils mit Teilmangel in irgendeinem Prüfbericht des Auftrags und
die Datei eines Teils, das ein Prüfer-Urteil bemängelt. `swki pruefen` misst jedes Teil weiter gegen die freigegebene
Kopie."""

import ast
import hashlib
import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from swki.aenderungen import sha256_datei
from swki.auftrag import lauf_datei, lauf_nummern_dateien, lauf_ordner
from swki.baugruppe.aufloesen import basis
from swki.konfig import PROJEKT, Rechner

# Einstellungen, die den Teilbau nicht berühren (alles andere zählt, auch unbekannte Schlüssel)
STANDARD_OHNE = frozenset({"wiederverwenden", "max_nachbesserungen", "bewegung_schritte", "speicher_grenze_mb"})
# Module, deren Funktionen Befehle sind (Kommandozeile, Änderungserkennung, `swki bauen` selbst): ihre Importe in
# Funktionen holen den Rest von swki (Baugruppe, Prüfen) und gehören nicht zum Teilbau
BEFEHLSMODULE = frozenset({"swki.cli", "swki.aenderungen", "swki.compiler.bauen"})


def _sha(daten) -> str:
    return hashlib.sha256(json.dumps(daten, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def _moduldatei(modul: str) -> Path | None:
    p = PROJEKT / Path(*modul.split("."))
    if (p / "__init__.py").is_file():
        return p / "__init__.py"
    return p.with_suffix(".py") if p.with_suffix(".py").is_file() else None


def code_dateien(start: str = "swki.compiler.bauen") -> list[Path]:
    """Quelldateien der Import-Hülle (AST) von `start` innerhalb von swki, samt Paket-__init__ und Importen in
    Funktionen (Handler-Registry) – außer in den Befehlsmodulen."""
    offen, gesehen = [start], {}
    while offen:
        modul = offen.pop()
        if modul in gesehen or (datei := _moduldatei(modul)) is None:
            continue
        gesehen[modul] = datei
        teile = modul.split(".")
        offen += [".".join(teile[:i]) for i in range(1, len(teile))]
        baum = ast.parse(datei.read_text(encoding="utf-8"))
        for k in (baum.body if modul in BEFEHLSMODULE else ast.walk(baum)):
            if isinstance(k, ast.Import):
                offen += [a.name for a in k.names if a.name.split(".")[0] == "swki"]
            elif isinstance(k, ast.ImportFrom) and k.level == 0 and (k.module or "").split(".")[0] == "swki":
                offen += [k.module, *(f"{k.module}.{a.name}" for a in k.names)]
    return sorted(gesehen.values())


@lru_cache(maxsize=1)
def code_pruefsumme() -> str:
    return _sha({p.relative_to(PROJEKT).as_posix(): sha256_datei(p) for p in code_dateien()})


def standard_pruefsumme(standard: dict) -> str:
    return _sha({k: v for k, v in standard.items() if k not in STANDARD_OHNE})


def _dateien_pruefsumme(pfade) -> str:
    return _sha({str(p): sha256_datei(Path(p)) if Path(p).is_file() else None for p in pfade})


def umgebung(app, r: Rechner, standard: dict, auftrag: str) -> dict:
    """Eingaben, die für alle Teile eines Laufs gleich sind (einmal je `swki bauen`)."""
    wissen = {p.name: sha256_datei(p) for p in sorted((PROJEKT / "swki" / "wissen").glob("*.yaml"))}
    return {"code": code_pruefsumme(), "wissen": _sha(wissen),
            "schema": sha256_datei(PROJEKT / "schema" / "teil.schema.json"), "standard": standard_pruefsumme(standard),
            "auftrag": auftrag, "sw": f"{r.sw_jahr}/{app.RevisionNumber}", "vorlage": sha256_datei(r.vorlage_teil),
            "material": _dateien_pruefsumme(sorted(app.GetMaterialDatabases or ()))}


def schluessel(teil_spec: dict, datei: str, spec_ordner: Path, umg: dict) -> str:
    skripte = {f["datei"]: sha256_datei(spec_ordner / f["datei"])
               for f in teil_spec.get("features", []) if f.get("typ") == "skript"}
    return _sha({"spec": teil_spec, "datei": datei, "skripte": skripte,
                 **{k: v for k, v in umg.items() if k != "material"},
                 "material": umg["material"] if "material" in teil_spec else None})


@dataclass
class Quelle:
    lauf: int
    pfad: Path        # Datei im Lauf-Ordner der Quelle
    sha256: str
    protokoll: dict   # Teilprotokoll der Quelle (Knoten mit Bohrungspunkten und Maßprotokoll)


@dataclass
class Plan:
    quellen: dict[str, Quelle] = field(default_factory=dict)   # Teil-Spec → Quelle
    gescheitert: set[str] = field(default_factory=set)         # im letzten Lauf gescheiterte Teile

    def zu_bauen(self, teile: list[str], wiederverwenden: bool) -> list[str]:
        """Bau-Reihenfolge: zuletzt gescheiterte, dann übrige ohne Quelle (neu, geändert) in Spec-Reihenfolge – ein
        Fehler zeigt sich so nach Sekunden; ohne Wiederverwenden danach die Teile mit Quelle."""
        ohne = sorted((d for d in teile if d not in self.quellen), key=lambda d: d not in self.gescheitert)
        return ohne if wiederverwenden else ohne + [d for d in teile if d in self.quellen]


def _lies(pfad: Path) -> dict | None:
    try:
        d = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return d if isinstance(d, dict) else None


def _teil_der_komponente(protokoll: dict) -> dict[str, str]:
    """Komponenten-ID → Teil-Spec, aus Komponentenliste und Dateien des Laufs."""
    nach_name = {Path(p).name.lower(): art.removeprefix("teil:")
                 for art, p in (protokoll.get("dateien") or {}).items() if art.startswith("teil:")}
    return {basis(k["id"]): nach_name[k["datei"].lower()]
            for k in protokoll.get("komponenten") or [] if (k.get("datei") or "").lower() in nach_name}


def _datei_sha(protokoll: dict, datei: str) -> str | None:
    pfad = (protokoll.get("dateien") or {}).get(f"teil:{datei}")
    return (protokoll.get("sha256") or {}).get(Path(pfad).name) if pfad else None


def _gesperrt(spec_pfad: Path, protokolle: dict[int, dict]) -> set[str]:
    gesperrt = set()
    for n, protokoll in protokolle.items():
        teil_von = _teil_der_komponente(protokoll)
        bericht = _lies(lauf_datei(spec_pfad, n, "pruefbericht")) or {}
        for komp, t in (bericht.get("teilpruefungen") or {}).items():
            if not t.get("bestanden") and (datei := teil_von.get(komp)):
                gesperrt |= {(protokoll.get("teile") or {}).get(datei, {}).get("schluessel"), _datei_sha(protokoll, datei)}
        urteil = _lies(lauf_datei(spec_pfad, n, "pruefer")) or {}
        if urteil and not urteil.get("bestanden"):
            for m in urteil.get("maengel") or []:
                knoten = m.get("knoten") or []
                for k in [knoten] if isinstance(knoten, str) else knoten:
                    if datei := teil_von.get(basis(str(k).split("/")[0])):
                        gesperrt.add(_datei_sha(protokoll, datei))
    return gesperrt - {None}


def plane(r: Rechner, auftrag: str, spec_pfad: Path, schluessel_je_teil: dict[str, str]) -> Plan:
    """Quellen aus den Läufen des eigenen Auftrags (neuester passender Lauf zuerst) und die zuletzt gescheiterten
    Teile."""
    protokolle = {n: p for n in sorted(lauf_nummern_dateien(spec_pfad), reverse=True)
                  if (p := _lies(lauf_datei(spec_pfad, n, "protokoll"))) is not None}
    gesperrt = _gesperrt(spec_pfad, protokolle)
    plan = Plan()
    if protokolle:
        letztes = protokolle[max(protokolle)]
        plan.gescheitert = {d for d, t in (letztes.get("teile") or {}).items() if t.get("status") == "fehler"}
    for n, protokoll in protokolle.items():
        ordner = lauf_ordner(r, auftrag, n)
        # Name auf der Platte (SolidWorks speichert .SLDPRT groß, das Protokoll nennt den angefragten Namen)
        auf_platte = {p.name.lower(): p for p in ordner.iterdir()} if ordner.is_dir() else {}
        for datei, tp in (protokoll.get("teile") or {}).items():
            key = schluessel_je_teil.get(datei)
            if datei in plan.quellen or key is None or tp.get("status") != "ok" or tp.get("schluessel") != key:
                continue
            soll = _datei_sha(protokoll, datei)
            if key in gesperrt or soll is None or soll in gesperrt:
                continue
            pfad = auf_platte.get(Path(protokoll["dateien"][f"teil:{datei}"]).name.lower())
            if pfad is not None and pfad.is_file() and sha256_datei(pfad) == soll:
                plan.quellen[datei] = Quelle(n, pfad, soll, tp)
    return plan
