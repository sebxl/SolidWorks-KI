"""Katalogeintrag eines Kaufteils laden und prüfen (Spec 3c §4.5): Schema, Lage im Katalog, Einbaureferenzen,
Gewindegruppen, Messpunkte, Belegregel, Schutzregel gegen genormte Teile; Hinweise; Weiche für validieren und
freigeben."""

import math
import re
from pathlib import Path
from urllib.parse import urlparse

from swki.compiler.eigenschaften import ERSTELLER
from swki.kaufteile.katalog import dateiname, ordnername, schluessel
from swki.normteile.tabelle import ORDNER as NORMTABELLEN, lade_normtabelle, norm_datei, normen
from swki.spec.freigabe import freigeben as spec_freigeben, kopie_pfad, pruefsumme
from swki.spec.laden import SpecFehler, lade_yaml, schema_befunde
from swki.spec.normen import normmasse

HERSTELLERQUELLEN = ("hersteller", "datenblatt", "nutzer")  # eine davon genügt als Beleg (Spec 3c §2)
_NORM = re.compile(r"\b(ISO|DIN|EN)\s*-?\s*(\d+(?:-\d+)?)\b", re.IGNORECASE)
_TOL_LAENGE = 1e-9


def _b(pfad: str, meldung: str) -> dict:
    return {"pfad": pfad, "meldung": meldung}


def _null(v) -> bool:
    return math.sqrt(sum(c * c for c in v)) < _TOL_LAENGE


def kennmasse(spec: dict) -> list[tuple[str, list | None]]:
    """(Pfad, Beleg-IDs oder None) aller Kennmaße: Masse, Hüllquader, Durchmesser, Maße, Gewindegruppen."""
    pr = spec.get("pruefung", {})
    ergebnis = []
    if "masse" in spec:
        ergebnis.append(("masse", spec["masse"].get("beleg")))
    if "huellquader" in pr:
        ergebnis.append(("pruefung.huellquader", pr["huellquader"].get("beleg")))
    ergebnis += [(f"pruefung.durchmesser_pruefen[{i}]", d.get("beleg")) for i, d in enumerate(pr.get("durchmesser_pruefen", []))]
    ergebnis += [(f"pruefung.masse_pruefen[{i}]", m.get("beleg")) for i, m in enumerate(pr.get("masse_pruefen", []))]
    ergebnis += [(f"gewinde.{g}", w.get("beleg")) for g, w in spec.get("gewinde", {}).items()]
    return ergebnis


def _domain(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc.removeprefix("www.")


def beleg_befunde(spec: dict) -> list[dict]:
    """Belegregel (Spec 3c §2): eine Herstellerquelle (hersteller, datenblatt) oder nutzer genügt allein; sonst ≥ 2
    Händlerquellen mit verschiedenen Domains. Kennmaße ohne Beleg sind erlaubt (Hinweis nicht_belegt)."""
    belege = spec.get("belege", {})
    befunde = []
    for pfad, ids in kennmasse(spec):
        if not ids:
            continue
        fehlend = [i for i in ids if i not in belege]
        if fehlend:
            befunde.append(_b(f"{pfad}.beleg", f"Beleg {', '.join(fehlend)} fehlt unter belege"))
            continue
        if {belege[i]["art"] for i in ids} & set(HERSTELLERQUELLEN):
            continue
        domains = {_domain(belege[i]["url"]) for i in ids}
        if len(domains) < 2:
            befunde.append(_b(f"{pfad}.beleg", f"BELEG_UNZUREICHEND: nur Händlerquellen ({', '.join(sorted(domains))}); "
                                               "nötig: Herstellerquelle, Datenblatt, Nutzer oder ≥ 2 Händler mit "
                                               "verschiedenen Domains"))
    return befunde


def genormte_normen(wissen: Path = NORMTABELLEN) -> dict[str, str]:
    """Norm und ersetzte Norm jeder Normtabelle in Dateischreibweise → Norm der Tabelle ("din912" → "ISO 4762"); bei
    Normen mit Teilnummer auch ohne sie ("DIN 125-1" → "din1251" und "din125")."""
    ergebnis = {}
    for name in normen(wissen):
        t = lade_normtabelle(name, wissen)
        for n in (t.get("norm"), t.get("ersetzt")):
            if n:
                for schreibweise in {str(n), str(n).split("-")[0]}:
                    ergebnis[norm_datei(schreibweise)] = str(t.get("norm"))
    return ergebnis


def genormt_befunde(spec: dict, wissen: Path = NORMTABELLEN) -> list[dict]:
    """Schutzregel (Spec 3c §4.5): Benennung oder Bestellnummer nennen eine Norm einer Normtabelle."""
    bekannt = genormte_normen(wissen)
    befunde = []
    for feld in ("benennung", "bestellnummer"):
        for treffer in _NORM.finditer(spec[feld]):
            # "DIN 912-12": 12 ist oft die Größe, nicht die Teilnummer – beide Lesarten prüfen
            lesarten = {treffer.group(2), treffer.group(2).split("-")[0]}
            norm = next((n for n in (norm_datei(f"{treffer.group(1)} {x}") for x in sorted(lesarten, reverse=True))
                         if n in bekannt), None)
            if norm:
                befunde.append(_b(feld, f"KAUFTEIL_GENORMT: {treffer.group(0)} ist ein Normteil ({bekannt[norm]}) – "
                                        "genormte Teile über swki normteil hole, nie als STEP"))
    return befunde


def _messpunkt_befunde(mp: dict, pfad: str, spec: dict) -> list[dict]:
    einbau, gewinde = spec["einbau"], spec.get("gewinde", {})
    if "referenz" in mp and mp["referenz"] not in einbau:
        return [_b(f"{pfad}.referenz", f"Einbaureferenz {mp['referenz']!r} fehlt unter einbau")]
    if "gewinde" in mp:
        g = gewinde.get(mp["gewinde"])
        if g is None:
            return [_b(f"{pfad}.gewinde", f"Gewindegruppe {mp['gewinde']!r} fehlt unter gewinde")]
        if mp["instanz"] > len(g["positionen"]):
            return [_b(f"{pfad}.instanz", f"{mp['gewinde']} hat nur {len(g['positionen'])} Positionen")]
    if "flaeche" in mp and _null(mp["flaeche"]["normale"]):
        return [_b(f"{pfad}.flaeche.normale", "Normale darf nicht der Nullvektor sein")]
    return []


def plausibel_befunde(spec: dict, pfad: Path | None = None) -> list[dict]:
    befunde = []
    if pfad is not None and (pfad.parent.name, pfad.stem) != (ordnername(spec["hersteller"]), dateiname(spec["bestellnummer"])):
        befunde.append(_b("(Datei)", f"Eintrag gehört nach {ordnername(spec['hersteller'])}/"
                                     f"{dateiname(spec['bestellnummer'])}.yaml (Hersteller und Bestellnummer)"))
    einbau = spec["einbau"]
    arten = {n: next(iter(e)) for n, e in einbau.items()}
    for n, e in einbau.items():
        art, w = next(iter(e.items()))
        stelle = f"einbau.{n}.{art}"
        if art == "zylinder" and "senkrecht_zu" in w and arten.get(w["senkrecht_zu"]) != "ebene":
            befunde.append(_b(f"{stelle}.senkrecht_zu", f"{w['senkrecht_zu']!r} ist keine ebene-Referenz dieses Eintrags"))
        if art == "ebene" and _null(w["normale"]):
            befunde.append(_b(f"{stelle}.normale", "Normale darf nicht der Nullvektor sein"))
        if art == "ebene_durch_achse" and arten.get(w["achse"]) != "zylinder":
            befunde.append(_b(f"{stelle}.achse", f"{w['achse']!r} ist keine zylinder-Referenz dieses Eintrags"))
    for g, w in spec.get("gewinde", {}).items():
        stelle = f"gewinde.{g}"
        if normmasse("gewinde", w["groesse"], "ISO") is None:
            befunde.append(_b(f"{stelle}.groesse", f"Gewinde {w['groesse']} nicht in swki/wissen/bohrungsnormen.yaml"))
        if w["gewindetiefe"] > w["tiefe"]:
            befunde.append(_b(f"{stelle}.gewindetiefe", "gewindetiefe darf nicht größer als tiefe sein"))
        if _null(w["normale"]):
            befunde.append(_b(f"{stelle}.normale", "Normale darf nicht der Nullvektor sein"))
        for k, p in enumerate(w["positionen"]):
            if any(math.dist(p, q) <= 1e-6 for q in w["positionen"][:k]):
                befunde.append(_b(f"{stelle}.positionen[{k}]", f"Position {k + 1} ist doppelt"))
    pr = spec.get("pruefung", {})
    for i, d in enumerate(pr.get("durchmesser_pruefen", [])):
        if "referenz" in d and arten.get(d["referenz"]) != "zylinder":
            befunde.append(_b(f"pruefung.durchmesser_pruefen[{i}].referenz",
                              f"{d['referenz']!r} ist keine zylinder-Referenz dieses Eintrags"))
    for i, m in enumerate(pr.get("masse_pruefen", [])):
        for s in ("von", "zu"):
            befunde += _messpunkt_befunde(m[s], f"pruefung.masse_pruefen[{i}].{s}", spec)
    for liste in ("durchmesser_pruefen", "masse_pruefen"):
        namen = [x["was"] for x in pr.get(liste, [])]
        for i, n in enumerate(namen):
            if n in namen[:i]:
                befunde.append(_b(f"pruefung.{liste}[{i}].was", f"was {n!r} ist doppelt"))
    return befunde


def eintrag_befunde(spec: dict, pfad: Path | None = None, wissen: Path = NORMTABELLEN) -> list[dict]:
    befunde = schema_befunde(spec, "kaufteil")
    if befunde:
        return befunde
    return plausibel_befunde(spec, pfad) + beleg_befunde(spec) + genormt_befunde(spec, wissen)


def lade_eintrag(pfad: Path) -> dict:
    """Lädt und prüft einen Katalogeintrag; wirft SpecFehler mit allen Befunden."""
    spec = lade_yaml(pfad)
    if befunde := eintrag_befunde(spec, pfad):
        raise SpecFehler(befunde)
    return spec


def hinweise_eintrag(spec: dict) -> list[dict]:
    """Hinweise (blockieren nie): Kennmaße ohne Beleg, keine belegten Kennmaße, Masse aus dem Material."""
    alle = kennmasse(spec)
    ergebnis = [{"art": "nicht_belegt", "pfad": p, "meldung": "Kennmaß ohne Beleg: wird geprüft, gilt im Bericht als "
                                                                "„nicht belegt“"} for p, ids in alle if not ids]
    if not any(ids for _, ids in alle):
        ergebnis.append({"art": "kennmasse_nicht_belegt", "pfad": "pruefung",
                         "meldung": "keine belegten Kennmaße: geprüft werden nur Import, Körperzahl, Volumen und "
                                    "Einbaureferenzen („Kennmaße nicht belegt“)"})
    if "masse" not in spec:
        ergebnis.append({"art": "masse_aus_material", "pfad": "masse",
                         "meldung": "keine Masse aus dem Datenblatt: die Masse wird aus dem Material geschätzt"})
    return ergebnis


def eigenschaften(spec: dict) -> dict[str, str]:
    """Eigenschaften im Teil (Spec 3c §5.3): Ersteller, Benennung, Hersteller, Bestellnummer, dazu die des Eintrags."""
    return {"Ersteller": ERSTELLER, "Benennung": spec["benennung"], "Hersteller": spec["hersteller"],
            "Bestellnummer": spec["bestellnummer"], **spec.get("eigenschaften", {})}


def angaben_fuer_bericht(spec: dict) -> dict[str, str]:
    """Masse und Belegstand eines Kaufteils für Protokoll und Bericht der Baugruppe (Spec 3c §8.4)."""
    masse = f"{spec['masse']['kg']:g} kg (Datenblatt)" if "masse" in spec else "aus Material geschätzt"
    belegt = any(ids for _, ids in kennmasse(spec))
    return {"masse": masse, "kennmasse": "belegt" if belegt else "nicht belegt"}


def validieren(pfad: Path) -> dict:
    spec = lade_eintrag(pfad)
    return {"gueltig": True, "spec": str(pfad), "art": "kaufteil",
            "schluessel": schluessel(spec["hersteller"], spec["bestellnummer"]), "pruefsumme": pruefsumme(spec),
            "hinweise": hinweise_eintrag(spec)}


def freigeben(pfad: Path) -> dict:
    """Freigabe des ganzen Eintrags (Spec 3c §4.6) – nur nach ausdrücklichem OK des Nutzers."""
    spec = lade_eintrag(pfad)
    return {"spec": str(pfad), "art": "kaufteil", "kopie": str(kopie_pfad(pfad)), **spec_freigeben(pfad, spec)}
