"""Änderungs-Spec `art: aenderung` (Spec Bestandsdateien §4): Laden, Prüfsumme, validieren, freigeben.

`lade_aenderung` prüft ohne SolidWorks und ohne Aufnahme: Schema und Plausibilität der Spec selbst. `validieren` prüft
danach gegen die Bestandsaufnahme (`bestand.json`, Spec §4.4 Punkt 2 bis 6): `befunde_gegen_aufnahme` für Namen, Altwerte,
gesteuerte Maße, Folgen, Kinder und Bereiche, `feature_befunde` für den Inhalt neuer Features. Die Aufnahme selbst (fehlt,
passt nicht zur `sha256`, ist nicht mehr die jüngste) ist eine Ausnahme (`BestandFehler`), kein Befund.

Grundsatz der Prüfsumme (Spec §4.5): Was geändert wird und wo sich die Geometrie ändern darf, ist Anforderung; wie swki es
erreicht, ist Bauweg. `bauweg_frei` liefert die Anforderung.
"""

import copy
import re
from pathlib import Path

from swki.auftrag import auftrag_name
from swki.bestand.ablage import aufnahmen, lade_aufnahme
from swki.bestand.fehler import (BEREICH_FEHLT, BESTAND_ALTWERT, BESTAND_REFERENZ, BESTAND_UNBEKANNT, BESTAND_VERALTET,
                                 FOLGEN_ABWEICHEND, KINDER_FEHLEN, MASS_GESTEUERT, BestandFehler)
from swki.bestand.folgen import folgen_von, gleicher_ausdruck, kinder_von, rechte_seite
from swki.compiler.skriptpruefung import pruefe_skript
from swki.konfig import lade_rechner
from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck
from swki.spec.freigabe import freigeben as spec_freigeben
from swki.spec.freigabe import kopie_pfad, pruefsumme
from swki.spec.hinweise import hinweise as teil_hinweise
from swki.spec.laden import (SpecFehler, _pfad, _referenzen, _werte, lade_yaml, plausibel_befunde, schema_befunde)

PRUEF_FELDER = ("art", "name", "bestand", "parameter", "bereiche", "pruefung")
# Bauweg in den Punkten: Anker und Bezug neuer Features, Einfügestelle, Skriptdatei (Reihenfolge: nach id sortiert)
BAUWEG_SCHLUESSEL = frozenset({"nach", "bezug", "flaeche", "kanten"})
# Punkte, die Geometrie ändern können: jeder steht in mindestens einem Bereich (Spec §4.4 Punkt 5)
GEOMETRIE_TYPEN = frozenset({"mass", "gleichung", "unterdruecken", "aufheben", "loeschen", "feature", "skript"})
_TOL_ALT = 1e-6  # mm bzw. Grad: Rauschen beim Lesen aus SolidWorks


def _ist_flaechenanker(wert) -> bool:
    return isinstance(wert, dict) and ("feature" in wert or "nahe" in wert)


def _ist_bauweg(schluessel: str, wert) -> bool:
    """`ebene` ist nur Bauweg, wenn sie ein Flächenanker ist (Dict mit feature oder nahe). Standardebene, versatz, basis,
    abstand und umkehren legen fest, wo das Feature entsteht, und bleiben Anforderung."""
    return schluessel in BAUWEG_SCHLUESSEL or (schluessel == "ebene" and _ist_flaechenanker(wert))


def _ohne_bauweg(obj):
    if isinstance(obj, dict):
        return {k: _ohne_bauweg(v) for k, v in obj.items() if not _ist_bauweg(k, v)}
    if isinstance(obj, list):
        return [_ohne_bauweg(v) for v in obj]
    return obj


def bauweg_frei(spec: dict) -> dict:
    """Die Anforderungen einer Änderungs-Spec (Grundlage der Prüfsumme): ohne Anker, `bezug`, `nach`, Skriptdateien und
    ohne die Reihenfolge der Punkte. Die Spec selbst bleibt unverändert."""
    kern = {feld: copy.deepcopy(spec[feld]) for feld in PRUEF_FELDER if feld in spec}
    punkte = []
    for punkt in sorted(spec.get("punkte", []), key=lambda p: str(p.get("id", ""))):
        rest = {k: v for k, v in punkt.items() if not (punkt.get("typ") == "skript" and k == "datei")}
        punkte.append(_ohne_bauweg(rest))
    kern["punkte"] = punkte
    return kern


def _plausibel_befunde(spec: dict) -> list[dict]:
    """Doppelte Punkt-IDs und Ausdrücke, deren Parameter fehlen (Anforderungen werden als `=Name` geführt)."""
    befunde, parameter = [], spec.get("parameter", {})
    ids = [p["id"] for p in spec["punkte"]]
    for i, pid in enumerate(ids):
        if pid in ids[:i]:
            befunde.append({"pfad": f"punkte[{i}].id", "meldung": f"ID {pid!r} ist doppelt"})

    zu_pruefen = [(["punkte", i, "neu"], p["neu"]) for i, p in enumerate(spec["punkte"])
                  if (p["typ"] == "mass" or "variable" in p) and ist_ausdruck(p.get("neu"))]
    zu_pruefen += [(pfad, roh) for pfad, _, roh in _werte(spec.get("pruefung", {}), ["pruefung"])]
    for pfad, roh in zu_pruefen:
        try:
            auswerten(roh, parameter)
        except AusdruckFehler as e:
            befunde.append({"pfad": _pfad(pfad), "meldung": str(e)})
    return befunde


def aenderung_befunde(spec: dict) -> list[dict]:
    """Alle Befunde einer Änderungs-Spec ohne Aufnahme: Schema, danach Plausibilität."""
    return schema_befunde(spec, "aenderung") or _plausibel_befunde(spec)


def lade_aenderung(pfad: Path) -> dict:
    """Lädt und prüft eine Änderungs-Spec; wirft SpecFehler mit allen Befunden."""
    spec = lade_yaml(pfad)
    if befunde := aenderung_befunde(spec):
        raise SpecFehler(befunde)
    return spec


def _befund(pfad: str, meldung: str, code: str | None = None, **mehr) -> dict:
    return {"pfad": pfad, **({"code": code} if code else {}), "meldung": meldung, **mehr}


def _zahl(wert) -> str:
    return f"{wert:g}"


def _ist_relativ(datei: str) -> bool:
    """Kein absoluter Pfad (auch Laufwerk und Netzpfad) und kein `..`."""
    text = datei.replace("\\", "/")
    return not (text.startswith("/") or re.match(r"^[A-Za-z]:", text) or ".." in text.split("/"))


def _nahe(a: float, b: float) -> bool:
    return abs(a - b) <= _TOL_ALT * max(1.0, abs(b))


def _gewaehlt(punkt: dict, konfigurationen: list[str]) -> list[str]:
    """Die Konfigurationen, die der Punkt nennt (`alle` = alle der Aufnahme); Unbekannte meldet `_konfig_befunde`."""
    k = punkt.get("konfigurationen", "alle")
    return list(konfigurationen) if k == "alle" else [x for x in k if x in konfigurationen]


def _konfig_befunde(punkt: dict, pfad: str, konfigurationen: list[str]) -> list[dict]:
    namen = punkt.get("konfigurationen", "alle")
    befunde = [_befund(f"{pfad}.konfigurationen[{k}]", f"Konfiguration {n!r} gibt es im Bestand nicht "
                       f"(Konfigurationen: {', '.join(konfigurationen)})", BESTAND_REFERENZ)
               for k, n in enumerate([] if namen == "alle" else namen) if n not in konfigurationen]
    if (n := punkt.get("konfiguration")) is not None and n not in konfigurationen:  # eigenschaft
        befunde.append(_befund(f"{pfad}.konfiguration", f"Konfiguration {n!r} gibt es im Bestand nicht "
                               f"(Konfigurationen: {', '.join(konfigurationen)})", BESTAND_REFERENZ))
    return befunde


def _quelle_text(m: dict) -> str:
    q = m.get("quelle") or {}
    art, name = q.get("art"), q.get("name")
    if art == "variable":
        return (f"gesteuert durch die globale Variable {name!r}: stattdessen einen gleichung-Punkt mit variable: {name} "
                "schreiben")
    if art == "gleichung":
        return (f"gesteuert durch die Gleichung für {name!r}: stattdessen die Gleichung mit einem gleichung-Punkt ändern "
                "(oder die Maße, von denen sie abhängt)")
    if art == "tabelle":
        return ("gesteuert durch eine Konstruktionstabelle: dem Nutzer die Tabelle nennen; nur auf seine Anweisung geht die "
                "Änderung über einen skript-Punkt mit luecke")
    return "gesteuert, die Aufnahme nennt die Quelle nicht"


def _alt_befund(pfad: str, alt, ist: dict) -> list[dict]:
    """`alt` gegen die gelesenen Werte (je Konfiguration); `None` (nicht lesbar) zählt nicht als Abweichung."""
    lesbar = {k: v for k, v in ist.items() if v is not None}
    if all(_nahe(v, alt) for v in lesbar.values()):
        return []
    werte = ", ".join(f"{k}: {_zahl(v)}" for k, v in lesbar.items())
    return [_befund(pfad, f"alt {_zahl(alt)} stimmt nicht mit dem Bestand überein ({werte})", BESTAND_ALTWERT, werte=lesbar)]


def _folgen_befund(punkt: dict, pfad: str, erwartet: list[str]) -> list[dict]:
    genannt = punkt.get("folgen", [])
    fehlt, zuviel = sorted(set(erwartet) - set(genannt)), sorted(set(genannt) - set(erwartet))
    if not (fehlt or zuviel):
        return []
    teile = ([f"es fehlen {', '.join(fehlt)}"] if fehlt else []) + ([f"zu viel genannt: {', '.join(zuviel)}"] if zuviel else [])
    return [_befund(f"{pfad}.folgen", f"folgen stimmt nicht mit der Aufnahme überein ({'; '.join(teile)}); erwartet "
                    f"[{', '.join(erwartet)}]", FOLGEN_ABWEICHEND, erwartet=erwartet)]


def _punkt_befunde(p: dict, pfad: str, aufnahme: dict, namen: dict, ordner: Path | None) -> list[dict]:
    """Befunde eines Punkts gegen die Aufnahme: Namen, Altwert, gesteuerte Maße, Folgen, Kinder, Skriptdatei."""
    masse, features, konfigurationen = namen["masse"], namen["features"], aufnahme["konfigurationen"]
    typ, befunde, start_ok = p["typ"], [], True

    if typ in ("mass", "unterdruecken", "aufheben", "eigenschaft"):
        befunde += _konfig_befunde(p, pfad, konfigurationen)

    if typ == "mass":
        m = masse.get(p["mass"])
        if m is None:
            befunde.append(_befund(f"{pfad}.mass", f"Maß {p['mass']!r} gibt es in der Aufnahme nicht", BESTAND_REFERENZ))
            start_ok = False
        elif m["zustand"] == "gesteuert":
            befunde.append(_befund(f"{pfad}.mass", f"Maß {p['mass']!r} ist {_quelle_text(m)}", MASS_GESTEUERT))
            start_ok = False
        elif m["zustand"] == "getrieben":
            befunde.append(_befund(f"{pfad}.mass", f"Maß {p['mass']!r} ist ein Referenzmaß (getrieben): es folgt der "
                                                   "Geometrie und lässt sich nicht setzen", MASS_GESTEUERT))
            start_ok = False
        else:
            befunde += _alt_befund(f"{pfad}.alt", p["alt"], {k: m["werte"].get(k) for k in _gewaehlt(p, konfigurationen)})
    elif typ == "gleichung" and "variable" in p:
        if p["variable"] not in aufnahme.get("variablen", {}):
            befunde.append(_befund(f"{pfad}.variable", f"Globale Variable {p['variable']!r} gibt es in der Aufnahme nicht",
                                   BESTAND_REFERENZ))
            start_ok = False
        else:
            befunde += _alt_befund(f"{pfad}.alt", p["alt"], {"Variable": aufnahme["variablen"][p["variable"]]})
    elif typ == "gleichung":
        g = next((g for g in aufnahme.get("gleichungen", []) if g["links"] == p["gleichung"]), None)
        if g is None:
            befunde.append(_befund(f"{pfad}.gleichung", f"Eine Gleichung für {p['gleichung']!r} gibt es in der Aufnahme nicht",
                                   BESTAND_REFERENZ))
            start_ok = False
        elif not gleicher_ausdruck(rechte_seite(g["text"]), p["alt"]):
            befunde.append(_befund(f"{pfad}.alt", f"alt {p['alt']!r} stimmt nicht mit der rechten Seite im Bestand überein "
                                                  f"({rechte_seite(g['text'])!r})", BESTAND_ALTWERT))

    elif typ in ("unterdruecken", "aufheben", "loeschen"):
        f = features.get(p["feature"])
        if f is None:
            befunde.append(_befund(f"{pfad}.feature", f"Feature {p['feature']!r} gibt es in der Aufnahme nicht",
                                   BESTAND_REFERENZ))
            start_ok = False
        if typ != "loeschen" and (aufnahme.get("tabelle") or (f or {}).get("tabelle")):
            # tabellengesteuerte Unterdrückung ist ohne Excel nicht lesbar (S18b): pauschal gesperrt
            befunde.append(_befund(f"{pfad}.feature", "Die Datei hat eine Konstruktionstabelle, die Unterdrückungszustände "
                                   "steuern kann und sich ohne Excel nicht lesen lässt: dem Nutzer die Tabelle nennen; nur "
                                   "auf seine Anweisung geht die Änderung über einen skript-Punkt mit luecke",
                                   MASS_GESTEUERT))
        if typ == "loeschen":
            for k, n in enumerate(p.get("kinder", [])):
                if n not in features:
                    befunde.append(_befund(f"{pfad}.kinder[{k}]", f"Feature {n!r} gibt es in der Aufnahme nicht",
                                           BESTAND_REFERENZ))
            if f is not None and (fehlt := sorted(set(kinder_von(p["feature"], aufnahme)) - set(p.get("kinder", [])))):
                befunde.append(_befund(f"{pfad}.kinder", f"Das Löschen von {p['feature']!r} nimmt auch {', '.join(fehlt)} "
                                       "mit: kinder muss sie nennen", KINDER_FEHLEN, fehlen=fehlt))

    elif typ == "feature":
        if (nach := p.get("nach")) is not None and nach not in features and nach not in namen["neu"]:
            befunde.append(_befund(f"{pfad}.nach", f"Feature {nach!r} gibt es in der Aufnahme nicht", BESTAND_REFERENZ))

    elif typ == "skript":
        if not _ist_relativ(p["datei"]):
            befunde.append(_befund(f"{pfad}.datei", "Die Skriptdatei muss relativ zum Auftragsordner liegen (kein absoluter "
                                   "Pfad, kein ..)"))
        elif ordner is not None:
            datei = ordner / p["datei"]
            if not datei.exists():
                befunde.append(_befund(f"{pfad}.datei", f"{datei} fehlt"))
            else:
                befunde += [_befund(f"{pfad}.datei", f"Zeile {b['zeile']}: {b['meldung']}")
                            for b in pruefe_skript(datei.read_text(encoding="utf-8"))]

    if start_ok:
        befunde += _folgen_befund(p, pfad, folgen_von(p, aufnahme))
    return befunde


def befunde_gegen_aufnahme(spec: dict, aufnahme: dict, ordner: Path | None = None) -> list[dict]:
    """Spec §4.4 Punkt 3 und 5 (ohne SolidWorks): genannte Maße, Features, Variablen, Konfigurationen (`BESTAND_REFERENZ`),
    `alt` (`BESTAND_ALTWERT`), gesteuerte und getriebene Maße sowie tabellengesteuerte Unterdrückung (`MASS_GESTEUERT`),
    `folgen` (`FOLGEN_ABWEICHEND`), `kinder` (`KINDER_FEHLEN`), Bereiche (`BEREICH_FEHLT`). `ordner` (Auftragsordner)
    gibt die Skriptdateien frei zur Prüfung; ohne ihn wird nur ihr Pfad geprüft. Der Inhalt neuer Features:
    `feature_befunde`."""
    punkte = spec["punkte"]
    namen = {"masse": {m["name"]: m for m in aufnahme.get("masse", [])},
             "features": {f["name"]: f for f in aufnahme.get("features", [])},
             "neu": {p["name"] for p in punkte if p["typ"] == "feature"}}
    ids = [p["id"] for p in punkte]
    befunde = []

    datei = spec["bestand"]["datei"]
    if not _ist_relativ(datei):
        befunde.append(_befund("bestand.datei", "Die Datei muss relativ zur Bestandskopie genannt werden (kein absoluter "
                               "Pfad, kein ..)", BESTAND_REFERENZ))
    elif datei.lower() != aufnahme["datei"]["name"].lower():
        befunde.append(_befund("bestand.datei", f"{datei!r} ist nicht die aufgenommene Datei "
                               f"({aufnahme['datei']['name']!r})", BESTAND_REFERENZ))

    for i, p in enumerate(punkte):
        if p["id"] in namen["features"]:
            befunde.append(_befund(f"punkte[{i}].id", f"ID {p['id']!r} ist der Name eines Features im Bestand: Punkt-IDs "
                                   "dürfen keinen Featurenamen des Bestands tragen"))
        befunde += _punkt_befunde(p, f"punkte[{i}]", aufnahme, namen, ordner)

    abgedeckt = set()
    for j, b in enumerate(spec["bereiche"]):
        for k, pid in enumerate(b["punkte"]):
            abgedeckt.add(pid)
            if pid not in ids:
                befunde.append(_befund(f"bereiche[{j}].punkte[{k}]", f"Der Bereich nennt den Punkt {pid!r}, den es nicht gibt"))
        for k, n in enumerate(b.get("features", [])):
            if n not in namen["features"] and n not in namen["neu"]:
                befunde.append(_befund(f"bereiche[{j}].features[{k}]", f"Feature {n!r} gibt es in der Aufnahme nicht",
                                       BESTAND_REFERENZ))
    for i, p in enumerate(punkte):
        if p["typ"] in GEOMETRIE_TYPEN and p["id"] not in abgedeckt:
            befunde.append(_befund(f"punkte[{i}]", f"Punkt {p['id']!r} kann Geometrie ändern und steht in keinem Bereich",
                                   BEREICH_FEHLT))

    bekannt = set(namen["features"]) | namen["neu"] | {p["id"] for p in punkte if p["typ"] == "feature"}
    for i, m in enumerate(spec.get("pruefung", {}).get("masse_pruefen", [])):
        for seite in ("von", "zu"):
            if (n := m[seite].get("feature")) is not None and n not in bekannt:
                befunde.append(_befund(f"pruefung.masse_pruefen[{i}].{seite}.feature",
                                       f"Feature {n!r} gibt es in der Aufnahme nicht", BESTAND_REFERENZ))
    return befunde


_FEATURE_PFAD = re.compile(r"^features\[(\d+)\](.*)$")


def _zurueck(pfad: str, feature_punkte: list[tuple[int, dict]]) -> str:
    """Pfad in der Teil-Spec (`features[k]…`) auf den Pfad in der Änderungs-Spec (`punkte[i].feature…`) abbilden."""
    m = _FEATURE_PFAD.match(pfad)
    if not m:
        return pfad
    i, rest = feature_punkte[int(m.group(1))][0], m.group(2)
    return f"punkte[{i}].id" if re.match(r"^\.id(\.|$)", rest) else f"punkte[{i}].feature{rest}"


def _setze(obj, pfad: list, wert) -> None:
    for schritt in pfad[:-1]:
        obj = obj[schritt]
    obj[pfad[-1]] = wert


def feature_befunde(spec: dict, aufnahme: dict, ordner: Path) -> tuple[list[dict], list[dict]]:
    """Spec §4.4 Punkt 4: Der Inhalt der `feature`-Punkte wird wie die Features einer Teil-Spec geprüft (Schema,
    Plausibilität, Hinweise). Fremde Featurenamen (Bestand) erlaubt das Teil-Schema nicht als `id`: Sie werden in einer Kopie
    durch Platzhalter `bestand_<n>` ersetzt, die als früheres Feature gelten; Namen, die weder ein früherer Punkt noch im
    Bestand sind, sind `BESTAND_REFERENZ`. Rückgabe: (Befunde, Hinweise), Pfade auf `punkte[i].feature…` abgebildet."""
    feature_punkte = [(i, p) for i, p in enumerate(spec["punkte"]) if p["typ"] == "feature"]
    if not feature_punkte:
        return [], []
    bestand = {f["name"] for f in aufnahme.get("features", [])}
    punkt_ids = {p["id"] for p in spec["punkte"]}
    belegt = set(punkt_ids)
    platzhalter: dict[str, str] = {}

    def ersatz(name: str) -> str:
        if name not in platzhalter:
            n = len(platzhalter) + 1
            while f"bestand_{n}" in belegt:
                n += 1
            platzhalter[name] = f"bestand_{n}"
            belegt.add(platzhalter[name])
        return platzhalter[name]

    befunde, teil_features = [], []
    for i, p in feature_punkte:
        inhalt = copy.deepcopy(p["feature"])
        if inhalt.get("typ") == "skript":  # der Teil-Handler nennt die Rückgabe nach der ID, auch ein fremdes Feature
            befunde.append(_befund(f"punkte[{i}].feature.typ", "typ: skript ist in einem feature-Punkt verboten: Der Notausgang "
                                   "ist der Punkt typ: skript mit luecke"))
        for pfad, ref in list(_referenzen(inhalt, [])):
            if ref in punkt_ids:
                continue  # Punkt-ID: früheres Feature (Reihenfolge prüft plausibel_befunde)
            if ref not in bestand:
                befunde.append(_befund(_pfad(["punkte", i, "feature", *pfad]),
                                       f"Feature {ref!r} gibt es weder in der Aufnahme noch als früherer Punkt",
                                       BESTAND_REFERENZ))
            _setze(inhalt, pfad, ersatz(ref))
        teil_features.append({"id": p["id"], **inhalt})
    teil = {"art": "teil", "name": spec["name"], "parameter": spec.get("parameter", {}), "features": teil_features}

    roh = schema_befunde(teil) or plausibel_befunde(teil, ordner, fremde=frozenset(platzhalter.values()))
    befunde += [{**b, "pfad": _zurueck(b["pfad"], feature_punkte)} for b in roh]
    if befunde:
        return befunde, []
    return [], [{**h, "pfad": _zurueck(h["pfad"], feature_punkte)} for h in teil_hinweise(teil)]


def aufnahme_zu(spec: dict, pfad: Path) -> dict:
    """Die Aufnahme, auf die die Spec zeigt: muss da sein, zur `sha256` passen und die jüngste des Auftrags sein. Auch
    `swki bauen` geht hier durch: Eine ältere Aufnahme verlöre die Arbeit des Kollegen."""
    r, auftrag, bestand = lade_rechner(), auftrag_name(pfad), spec["bestand"]
    aufnahme = lade_aufnahme(r, auftrag, bestand["aufnahme"])  # BESTAND_UNBEKANNT
    if aufnahme["datei"]["sha256"] != bestand["sha256"]:
        raise BestandFehler(BESTAND_UNBEKANNT, f"bestand.sha256 passt nicht zur Aufnahme {bestand['aufnahme']} des Auftrags "
                            f"{auftrag} (sha256 der Aufnahme: {aufnahme['datei']['sha256']})", auftrag=auftrag,
                            nummer=bestand["aufnahme"], spec=bestand["sha256"], aufnahme=aufnahme["datei"]["sha256"])
    if neuere := [n for n in aufnahmen(r, auftrag) if n > bestand["aufnahme"]]:
        raise BestandFehler(BESTAND_VERALTET, f"Die Aufnahme {bestand['aufnahme']} ist nicht mehr die jüngste (neuer: "
                            f"{', '.join(map(str, neuere))}): die Datei hat sich geändert. Die Spec auf die neueste "
                            "Aufnahme umstellen (bestand.aufnahme, bestand.sha256) und alt-Werte und Punkte neu prüfen",
                            auftrag=auftrag, nummer=bestand["aufnahme"], neuere=neuere)
    return aufnahme


def validieren(pfad: Path) -> dict:
    """`swki validieren` für art: aenderung: Schema und Plausibilität, dann die Prüfung gegen die Aufnahme (§4.4). Alle
    Befunde auf einmal (`SpecFehler`). `folgen`: die aus der Aufnahme berechneten Folgemaße je `mass`-/`gleichung`-Punkt,
    zum Eintragen in die Spec und für die Freigabe-Vorlage."""
    spec = lade_aenderung(pfad)
    aufnahme = aufnahme_zu(spec, pfad)
    befunde = befunde_gegen_aufnahme(spec, aufnahme, pfad.parent)
    feature_b, hinweise = feature_befunde(spec, aufnahme, pfad.parent)
    if befunde or feature_b:
        raise SpecFehler(befunde + feature_b)
    aelter = bool(aufnahme["datei"].get("version_aelter"))
    if aelter:
        hinweise.append({"art": "version_aelter", "pfad": "bestand",
                         "meldung": "Die Datei stammt aus einer älteren SolidWorks-Version: swki bauen speichert sie nur mit "
                                    "--hochstufen, danach lässt sie sich nur noch mit SolidWorks "
                                    f"{aufnahme.get('sw_jahr', '')} oder neuer lesen"})
    return {"gueltig": True, "spec": str(pfad), "art": "aenderung", "name": spec["name"], "punkte": len(spec["punkte"]),
            "pruefsumme": pruefsumme(spec), "hinweise": hinweise, "version_aelter": aelter,
            "folgen": {p["id"]: folgen_von(p, aufnahme) for p in spec["punkte"] if p["typ"] in ("mass", "gleichung")}}


def freigeben(pfad: Path) -> dict:
    """Freigabe der Anforderungen – nur nach ausdrücklichem OK des Nutzers."""
    spec = lade_aenderung(pfad)
    return {"spec": str(pfad), "art": "aenderung", "kopie": str(kopie_pfad(pfad)), **spec_freigeben(pfad, spec)}
