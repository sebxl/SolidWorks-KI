"""Validierung einer Änderungs-Spec an einer Baugruppe gegen die Baugruppen-Aufnahme (Spec Bestandsdateien §4.1 Grenzen, §4.4,
§8.2; Plan Etappe 2 Task 4).

`pruefe_baugruppe` ist der ganze Weg ohne SolidWorks: Die Teil-Punkte laufen als Scheiben durch den Code von Etappe 1
(`befunde_gegen_aufnahme`, `feature_befunde` gegen die Aufnahme der jeweiligen Datei), die Punkte ohne `in_datei` an der
Hauptbaugruppe (`eigenschaft`, `skript`) als Haupt-Scheibe. `befunde_baugruppe` prüft, was Etappe 1 nicht kennt: die Dateien der
Teil-Punkte (`in_datei`), Komponenten und Verknüpfungen, Quellen und Dateinamen neuer Komponenten, `lage_folgen`,
`kollision_erlaubt`, Bereiche und Messungen über mehrere Dateien. Alle Pfade der Befunde sind Pfade der ganzen Spec.

Namen sind die von SolidWorks (`Deckel-1`; eine Komponente in einer Unterbaugruppe `Unter-1/Welle-1`). Eine Komponente der obersten
Ebene darf Ziel eines Punkts sein, eine in einer Unterbaugruppe nur Partner einer Verknüpfung (Spec §4.1, Grenzen in Etappe 2).
"""

from collections.abc import Callable
from pathlib import Path, PureWindowsPath

from swki.baugruppe.aufloesen import ANLAGE
from swki.baugruppe.kopplung import KOPPLUNGEN
from swki.baugruppe.laden import kaufteil_quelle, normteil_quelle
from swki.bestand.fehler import BESTAND_REFERENZ, BESTAND_REFERENZ_EXTERN, MASS_GESTEUERT, NAME_BELEGT, VERKNUEPFUNGEN_FEHLEN
from swki.bestand.folgen import folgen_von
from swki.bestand.scheiben import (aenderung_an_haupt, datei_schluessel, dateien_mit_punkten, haupt_scheibe, scheibe, scheiben_karte,
                                   zurueck)
from swki.bestand.spec import (BAUGRUPPEN_TYPEN, _alt_befund, _befund, _gewaehlt, _ist_relativ, _konfig_befunde, befunde_gegen_aufnahme,
                               feature_befunde)
from swki.bestand.vergleich_baugruppe import ersetzen_ziele
from swki.spec.ausdruck import AusdruckFehler, auswerten, ist_ausdruck
from swki.spec.laden import SpecFehler, lade_spec, lade_yaml

# Teil-Typen: gehören an ein Teil (in_datei), an der Hauptbaugruppe nicht (Spec §4.1, Grenzen; Plan Präzisierung 8)
TEIL_TYPEN = frozenset({"mass", "gleichung", "unterdruecken", "aufheben", "loeschen", "feature", "material"})
# Pflichtfelder der neuen Verknüpfung je Art (Spec §4.1); die übrigen Arten brauchen keinen Wert
PFLICHT_FELDER = {"abstand": ("wert",), "winkel": ("wert",), "grenze_abstand": ("min", "max"), "grenze_winkel": ("min", "max")}
ANKER = ("a", "b", "anlage_a", "anlage_b")


def quelle_schluessel(quelle: dict) -> str:
    """Eine neue Datei je Quelle: `validieren`, Bau und Protokoll rechnen mit diesem Schlüssel."""
    art = next(k for k in ("teil", "normteil", "kaufteil") if k in quelle)
    return f"{art}:{quelle[art]}:{quelle.get('variante', '')}"


def _ref_name(eintrag) -> str:
    """Name einer Referenz in `dateien.<rel>.referenzen`: Text oder Dict mit `datei`/`pfad`/`name`."""
    if isinstance(eintrag, dict):
        eintrag = eintrag.get("datei") or eintrag.get("pfad") or eintrag.get("name") or ""
    return str(eintrag)


class _Bestand:
    """Nachschlagewerk über die Baugruppen-Aufnahme: Dateien (ohne die Hauptdatei), Komponenten, Verknüpfungen, Bewegungen."""

    def __init__(self, aufnahme: dict):
        self.haupt = aufnahme["datei"]["name"]
        self.dateien = aufnahme.get("dateien", {})
        self.komponenten = aufnahme.get("komponenten", {})
        self.verknuepfungen = aufnahme.get("verknuepfungen", {})
        self.bewegungen = aufnahme.get("bewegungen") or {}
        self.konfigurationen = aufnahme.get("konfigurationen") or []
        self.aktiv = aufnahme.get("aktiv")
        self._rel = {datei_schluessel(rel): rel for rel in self.dateien}

    def rel(self, datei: str) -> str | None:
        """Der aufgenommene Pfad der Datei (Schreibweise egal), `None` für Unbekanntes und die Hauptdatei."""
        return self._rel.get(datei_schluessel(datei))

    def ist_haupt(self, datei: str) -> bool:
        return datei_schluessel(datei) == datei_schluessel(self.haupt)

    def oberste(self) -> list[str]:
        return sorted(n for n in self.komponenten if "/" not in n)

    def instanzen(self, rel: str) -> list[str]:
        """Alle Komponenten (jede Ebene) mit dieser Datei."""
        schl = datei_schluessel(rel)
        return sorted(n for n, k in self.komponenten.items() if k.get("datei") and datei_schluessel(k["datei"]) == schl)

    def ist_virtuell(self, datei: str) -> bool:
        schl = datei_schluessel(datei)
        return "^" in PureWindowsPath(datei).name or any(
            k.get("virtuell") and k.get("datei") and datei_schluessel(k["datei"]) == schl for k in self.komponenten.values())

    def referenziert_von(self, rel: str) -> list[str]:
        """Dateien, die `rel` als Referenz tragen (Basisteil eines abgeleiteten Teils)."""
        schl, name = datei_schluessel(rel), PureWindowsPath(rel).name.casefold()
        treffer = []
        for andere, d in self.dateien.items():
            # nur ein Teil ist abgeleitet: `referenzen` einer Unterbaugruppe trägt ihre Kinder
            if andere != rel and d.get("art") == "teil" and any(datei_schluessel(_ref_name(e)) == schl or PureWindowsPath(_ref_name(e)).name.casefold() == name
                                     for e in d.get("referenzen", [])):
                treffer.append(andere)
        return sorted(treffer)

    def haengt_dran(self, komponente: str) -> list[str]:
        """Verknüpfungen, an denen die Komponente (oder eine in ihr, bei einer Unterbaugruppe) Partner ist."""
        return sorted(n for n, v in self.verknuepfungen.items()
                      if any(p is not None and (p == komponente or p.startswith(komponente + "/")) for p in v.get("partner", [])))

    def bewegungen_von(self, komponenten: list[str], verknuepfungen: list[str]) -> list[str]:
        """Bewegungen (Grenzverknüpfungen), die eine der Verknüpfungen sind oder eine der Komponenten bewegen."""
        namen = set(komponenten)
        return sorted(n for n, w in self.bewegungen.items()
                      if n in verknuepfungen or w.get("komponente") in namen or namen & set(w.get("bewegt", [])))


def _beispiele(namen: list[str], n: int = 8) -> str:
    return ", ".join(namen[:n]) + (f", … ({len(namen)} insgesamt)" if len(namen) > n else "")


def _datei_befunde(pfad: str, datei: str, b: _Bestand) -> list[dict]:
    """`in_datei` eines Teil-Punkts: relativ, aufgenommen, ein Teil (keine Unterbaugruppe, keine virtuelle Komponente), ohne
    Referenz auf eine andere Datei und nicht Basis einer anderen (Spec §8.1: allein geöffnet ist die Geometrie eingefroren, und
    `vorher_<name>` hätte die Referenz nicht daneben)."""
    if not _ist_relativ(datei):
        return [_befund(pfad, "Die Datei muss relativ zur Bestandskopie genannt werden (kein absoluter Pfad, kein ..)", BESTAND_REFERENZ)]
    rel = b.rel(datei)
    if rel is None:
        if b.ist_haupt(datei):
            return [_befund(pfad, f"{datei!r} ist die Hauptbaugruppe: in_datei weglassen", BESTAND_REFERENZ)]
        if b.ist_virtuell(datei):
            return [_befund(pfad, f"{datei!r} gehört zu einer virtuellen Komponente: Ihr Teil steckt in der Baugruppe und hat keine "
                                  "Datei, Punkte darauf gibt es nicht", BESTAND_REFERENZ)]
        return [_befund(pfad, f"Die Datei {datei!r} gibt es in der Aufnahme nicht (Dateien: {_beispiele(sorted(b.dateien))})",
                        BESTAND_REFERENZ, dateien=sorted(b.dateien))]
    d = b.dateien[rel]
    if d.get("art") != "teil":
        return [_befund(pfad, f"{rel} ist eine Unterbaugruppe: Punkte treffen in Etappe 2 nur Teile und die Hauptbaugruppe",
                        BESTAND_REFERENZ)]
    if d.get("referenzen"):
        namen = ", ".join(_ref_name(e) for e in d["referenzen"])
        return [_befund(pfad, f"{rel} referenziert {namen}: Allein geöffnet ist seine Geometrie eingefroren und die Kopie fürs "
                              "Vergleichen hätte die Referenz nicht daneben", BESTAND_REFERENZ_EXTERN, referenzen=list(d["referenzen"]))]
    if basis := b.referenziert_von(rel):
        return [_befund(pfad, f"{rel} ist Basis von {', '.join(basis)}: Eine Änderung hier verändert deren Geometrie nur beim Öffnen "
                              "im Kontext, nicht allein", BESTAND_REFERENZ_EXTERN, abhaengig=basis)]
    return []


def _komponente(pfad: str, name: str, b: _Bestand, neu: set[str], ziel: bool = False) -> list[dict]:
    """Die Komponente existiert (Aufnahme oder neuer Punkt). `ziel`: Ziel eines Punkts, dann oberste Ebene und nicht virtuell."""
    if name in neu:
        return []
    k = b.komponenten.get(name)
    if k is None:
        return [_befund(pfad, f"Komponente {name!r} gibt es in der Aufnahme nicht (oberste Ebene: {_beispiele(b.oberste())})",
                        BESTAND_REFERENZ, vorhanden=b.oberste())]
    if ziel and "/" in name:
        return [_befund(pfad, f"{name!r} steckt in einer Unterbaugruppe: Punkte treffen nur Komponenten der obersten Ebene, dort darf "
                              "sie nur Partner einer Verknüpfung sein", BESTAND_REFERENZ)]
    if ziel and k.get("virtuell"):
        return [_befund(pfad, f"{name!r} ist eine virtuelle Komponente: Sie steckt in der Baugruppe, Punkte darauf gibt es nicht",
                        BESTAND_REFERENZ)]
    return []


def _zahl_oder_none(roh, parameter: dict):
    if isinstance(roh, (int, float)):
        return float(roh)
    if ist_ausdruck(roh):
        try:
            return float(auswerten(roh, parameter))
        except AusdruckFehler:
            return None
    return None


class _Quellen:
    """Dateiname einer neuen Komponente aus ihrer Quelle und die Namenskollision mit dem Bestand (Spec §8.2: neue Dateien liegen
    flach neben der Hauptbaugruppe, ein gleicher Name im Bestand ist ein Befund). Berechnet nur, was ohne SolidWorks geht: bei
    Normteil und Kaufteil den Bibliotheksschlüssel (`swki.normteile`, `swki.kaufteile`), bei `teil` den `name` der Teil-Spec."""

    def __init__(self, b: _Bestand, ordner: Path | None):
        self.b, self.ordner = b, ordner
        self.vorhanden = {PureWindowsPath(r).name.casefold(): r for r in b.dateien}
        self.vorhanden[b.haupt.casefold()] = b.haupt
        self.neue: dict[str, str] = {}  # Dateiname klein → Schlüssel der Quelle
        self._cache: dict[str, tuple[str | None, list[dict]]] = {}

    def _teil(self, quelle: dict, pfad: str) -> tuple[str | None, list[dict]]:
        datei = quelle["teil"]
        if self.ordner is None:
            return None, []
        ziel = f"{pfad}.quelle.teil"
        try:
            roh = lade_yaml(self.ordner / datei)
        except SpecFehler as e:
            return None, [_befund(ziel, f"Teil-Spec {datei}: {e.daten['befunde'][0]['meldung']}")]
        if roh.get("art") != "teil":
            return None, [_befund(ziel, f"{datei} ist keine Teil-Spec (art: {roh.get('art')!r}): eine Quelle teil braucht art: teil")]
        try:
            spec = lade_spec(self.ordner / datei)
        except SpecFehler as e:
            return None, [{**x, "pfad": f"{datei}: {x['pfad']}"} for x in e.daten["befunde"]]
        return f"{spec['name']}.sldprt", []

    @staticmethod
    def _bibliothek(lade: Callable[[dict, str], tuple], quelle: dict, pfad: str) -> tuple[str | None, list[dict]]:
        """Normteil und Kaufteil: dieselbe Prüfung wie beim Laden einer Baugruppen-Spec (`swki/baugruppe/laden.py`), also Tabelle
        bzw. Katalog, Freigabe und Prüfer-Urteil; der Dateiname ist der Bibliotheksschlüssel."""
        q, befunde = lade(quelle, f"{pfad}.quelle")
        return (None if q is None else f"{q.schluessel}.sldprt"), befunde

    def befunde(self, quelle: dict, pfad: str) -> list[dict]:
        art = next(k for k in ("teil", "normteil", "kaufteil") if k in quelle)
        schl = quelle_schluessel(quelle)
        erstmals = schl not in self._cache
        if erstmals:
            self._cache[schl] = (self._teil(quelle, pfad) if art == "teil" else
                                 self._bibliothek(normteil_quelle if art == "normteil" else kaufteil_quelle, quelle, pfad))
        name, fehler = self._cache[schl]
        befunde = list(fehler) if erstmals else []  # Befunde einer Quelle meldet nur der erste Punkt, der sie nennt
        if name is None:
            return befunde
        klein = name.casefold()
        if klein in self.vorhanden:
            return befunde + [_befund(
                f"{pfad}.quelle", f"Die neue Datei {name} hieße wie {self.vorhanden[klein]} im Bestand: SolidWorks öffnet keine zwei "
                "Dokumente gleichen Namens und neue Dateien liegen flach neben der Hauptbaugruppe. Für eine weitere Instanz der "
                "vorhandenen Datei 'wie: <Komponente>' benutzen", NAME_BELEGT, datei=name, vorhanden=self.vorhanden[klein])]
        if self.neue.setdefault(klein, schl) != schl:
            return befunde + [_befund(f"{pfad}.quelle", f"Die neue Datei {name} hieße wie die einer anderen neuen Komponente: SolidWorks "
                                      "öffnet keine zwei Dokumente gleichen Namens", NAME_BELEGT, datei=name, vorhanden=name)]
        return befunde


def _name_befunde(p: dict, pfad: str, b: _Bestand) -> list[dict]:
    """Die Punkt-ID wird der Name der Verknüpfung (beim Scharnier auch `<id>.anlage`). Trägt ihn schon eine, bliebe `Name =` still
    alt; SolidWorks achtet dabei nicht auf die Schreibweise."""
    vorhanden = {n.casefold(): n for n in b.verknuepfungen}
    namen = [p["id"], *([f"{p['id']}{ANLAGE}"] if p["art"] == "scharnier" else [])]
    return [_befund(f"{pfad}.id", f"Die Verknüpfung {vorhanden[n.casefold()]!r} gibt es schon: Die Punkt-ID wird der Name der "
                    "neuen", NAME_BELEGT, vorhanden=vorhanden[n.casefold()]) for n in namen if n.casefold() in vorhanden]


def _verknuepfung_neu_befunde(p: dict, pfad: str, b: _Bestand, neu: set[str], parameter: dict) -> list[dict]:
    if p["art"] in KOPPLUNGEN:
        return [_befund(f"{pfad}.art", f"Eine {p['art']}-Kopplung braucht die Verzahnung aus einer freigegebenen Spec, die eine "
                        "fremde Datei nicht hat: Dem Nutzer nennen, nur auf seine Anweisung geht das über einen skript-Punkt mit "
                        "luecke")]
    befunde = _name_befunde(p, pfad, b)
    if p["art"] == "scharnier" and not {"anlage_a", "anlage_b"} <= set(p):
        befunde.append(_befund(pfad, "Ein Scharnier braucht anlage_a und anlage_b (die Flächen der Anlage). Ohne sie gibt es "
                               "hier keinen Punkt-Weg: Dem Nutzer nennen, nur auf seine Anweisung über einen skript-Punkt mit "
                               "luecke"))
    for feld in PFLICHT_FELDER.get(p["art"], ()):
        if feld not in p:
            befunde.append(_befund(f"{pfad}.{feld}", f"Eine Verknüpfung der Art {p['art']} braucht {feld}"))
    if p["art"].startswith("grenze_") and "min" in p and "max" in p:
        kleinste, groesste = _zahl_oder_none(p["min"], parameter), _zahl_oder_none(p["max"], parameter)
        if kleinste is not None and groesste is not None and kleinste > groesste:
            befunde.append(_befund(f"{pfad}.min", f"min ({kleinste:g}) ist größer als max ({groesste:g})"))
    for seite in ANKER:
        if seite in p:
            befunde += _komponente(f"{pfad}.{seite}.komponente", p[seite]["komponente"], b, neu)
    return befunde


def _alt_je_konfiguration(p: dict, v: dict, feld: str, b: _Bestand) -> dict:
    """Der Wert des Felds (`wert`/`min`/`max`) in jeder Konfiguration, die der Punkt nennt (aus `werte`); eine Aufnahme ohne
    `werte` liefert nur den Wert der aktiven Konfiguration."""
    ist = {k: ((v.get("werte") or {}).get(k) or {}).get(feld) for k in _gewaehlt(p, b.konfigurationen)}
    return ist if any(w is not None for w in ist.values()) else {b.aktiv or "aktiv": v.get(feld)}


def _verknuepfung_wert_befunde(p: dict, pfad: str, b: _Bestand) -> list[dict]:
    name = p["verknuepfung"]
    v = b.verknuepfungen.get(name)
    if v is None:
        return [_befund(f"{pfad}.verknuepfung", f"Verknüpfung {name!r} gibt es in der Aufnahme nicht "
                        f"(vorhanden: {_beispiele(sorted(b.verknuepfungen))})", BESTAND_REFERENZ)]
    if v.get("gesteuert"):
        return [_befund(f"{pfad}.verknuepfung", f"Der Wert von {name!r} ist von einer Gleichung gesteuert: Dafür gibt es hier keinen "
                        "Punkt-Weg. Dem Nutzer die Gleichung nennen; nur auf seine Anweisung geht die Änderung über einen "
                        "skript-Punkt mit luecke", MASS_GESTEUERT)]
    grenze = p.get("grenze")
    if v.get("grenze"):
        if grenze is None:
            return [_befund(f"{pfad}.grenze", f"{name!r} ist eine Grenzverknüpfung (min {v.get('min')}, max {v.get('max')}): grenze: "
                            "min oder max nennen")]
        return _alt_befund(f"{pfad}.alt", p["alt"], _alt_je_konfiguration(p, v, grenze, b))
    if grenze is not None:
        return [_befund(f"{pfad}.grenze", f"{name!r} ist keine Grenzverknüpfung: grenze weglassen")]
    if v.get("wert") is None:
        return [_befund(f"{pfad}.verknuepfung", f"{name!r} hat keinen Wert (nur Abstand und Winkel tragen einen, nicht etwa "
                        "konzentrisch oder deckungsgleich)")]
    return _alt_befund(f"{pfad}.alt", p["alt"], _alt_je_konfiguration(p, v, "wert", b))


def _entfernen_befunde(p: dict, pfad: str, b: _Bestand) -> list[dict]:
    """`verknuepfungen` nennt genau die Verknüpfungen, die mit der Komponente gehen (`VERKNUEPFUNGEN_FEHLEN`)."""
    befunde = []
    echte = set(b.haengt_dran(p["komponente"]))
    for k, name in enumerate(p["verknuepfungen"]):
        if name not in b.verknuepfungen:
            befunde.append(_befund(f"{pfad}.verknuepfungen[{k}]", f"Verknüpfung {name!r} gibt es in der Aufnahme nicht", BESTAND_REFERENZ))
        elif name not in echte:
            befunde.append(_befund(f"{pfad}.verknuepfungen[{k}]", f"Verknüpfung {name!r} hängt nicht an {p['komponente']!r}",
                                   BESTAND_REFERENZ))
    if fehlen := sorted(echte - set(p["verknuepfungen"])):
        befunde.append(_befund(f"{pfad}.verknuepfungen", f"Das Entfernen von {p['komponente']!r} nimmt auch {', '.join(fehlen)} mit: "
                               "verknuepfungen muss sie nennen", VERKNUEPFUNGEN_FEHLEN, fehlen=fehlen))
    return befunde


def _punkt_befunde(i: int, p: dict, b: _Bestand, neu: set[str], q: _Quellen, parameter: dict, datei_aufnahme: Callable) -> list[dict]:
    pfad, typ, befunde = f"punkte[{i}]", p["typ"], []
    if typ in TEIL_TYPEN and "in_datei" not in p:
        return [_befund(pfad, f"Ein Punkt typ: {typ} an der Hauptbaugruppe gibt es nicht (ein Maß der Baugruppe hat keine "
                        "Körper-Differenz als Nachweis): in_datei nennt das Teil", BESTAND_REFERENZ)]
    if "in_datei" in p:
        befunde += _datei_befunde(f"{pfad}.in_datei", p["in_datei"], b)
    elif typ == "komponente_neu":
        if "wie" in p:
            befunde += _komponente(f"{pfad}.wie", p["wie"], b, set(), ziel=True)
            rel = b.komponenten.get(p["wie"], {}).get("datei")
            if not befunde and "konfiguration" in p and rel and b.rel(rel):
                konfigurationen = datei_aufnahme(b.rel(rel))["konfigurationen"]
                if p["konfiguration"] not in konfigurationen:
                    befunde.append(_befund(f"{pfad}.konfiguration", f"Konfiguration {p['konfiguration']!r} gibt es in {b.rel(rel)} nicht "
                                           f"(Konfigurationen: {', '.join(konfigurationen)})", BESTAND_REFERENZ))
        else:
            befunde += q.befunde(p["quelle"], pfad)
    elif typ == "komponente_entfernen":
        befunde += _komponente(f"{pfad}.komponente", p["komponente"], b, set(), ziel=True)
        if not befunde:
            befunde += _entfernen_befunde(p, pfad, b)
    elif typ == "komponente_ersetzen":
        befunde += _komponente(f"{pfad}.komponente", p["komponente"], b, set(), ziel=True)
        befunde += q.befunde(p["quelle"], pfad)
    elif typ == "verknuepfung_neu":
        befunde += _verknuepfung_neu_befunde(p, pfad, b, neu, parameter)
    elif typ == "verknuepfung_wert":
        befunde += _konfig_befunde(p, pfad, b.konfigurationen) + _verknuepfung_wert_befunde(p, pfad, b)
    elif typ == "verknuepfung_loeschen" and p["verknuepfung"] not in b.verknuepfungen:
        befunde.append(_befund(f"{pfad}.verknuepfung", f"Verknüpfung {p['verknuepfung']!r} gibt es in der Aufnahme nicht "
                               f"(vorhanden: {_beispiele(sorted(b.verknuepfungen))})", BESTAND_REFERENZ))
    return befunde


def _kombinations_befunde(spec: dict, b: _Bestand) -> list[dict]:
    """Punkte, die einzeln gültig sind und zusammen nie bestehen: Der Handler löst gegen den Stand im Lauf auf, der Vergleich
    gegen den Bestand. Eine Komponente wird höchstens einmal ersetzt und nicht zugleich entfernt, ein `wie` nennt keine ersetzte
    Vorlage und keine Datei, die `alle_instanzen` tauscht (die neue Komponente trüge die alte Datei oder bräche „alle“). Alle
    Reihenfolgen gelten gleich; `alle_instanzen` neben `komponente_entfernen` geht, entfernte Instanzen gehören nicht dazu
    (`ersetzen_ziele`)."""
    punkte, befunde = spec["punkte"], []
    getroffen: dict[str, str] = {}
    getauscht: dict[str, str] = {}
    entfernt = {p["komponente"] for p in punkte if p["typ"] == "komponente_entfernen"}
    for i, p in enumerate(punkte):
        if p["typ"] != "komponente_ersetzen" or p["komponente"] not in b.komponenten:
            continue
        ziele = ersetzen_ziele(p, b.komponenten, punkte)[0]
        if p.get("alle_instanzen") and (tief := [n for n in ziele if "/" in n]):
            befunde.append(_befund(f"punkte[{i}].alle_instanzen", f"alle_instanzen träfe auch {_beispiele(tief)} in einer "
                                   "Unterbaugruppe: Punkte treffen nur die oberste Ebene, dort hieße das, die Datei der "
                                   "Unterbaugruppe zu ändern", BESTAND_REFERENZ))
        if p["komponente"] in entfernt and not p.get("alle_instanzen"):
            befunde.append(_befund(f"punkte[{i}].komponente", f"{p['komponente']!r} wird zugleich entfernt", BESTAND_REFERENZ))
        if doppelt := [n for n in ziele if n in getroffen]:
            befunde.append(_befund(f"punkte[{i}].komponente", f"{_beispiele(doppelt)} ersetzt schon Punkt "
                                   f"{getroffen[doppelt[0]]}: Eine Komponente wird höchstens einmal ersetzt", BESTAND_REFERENZ))
        getroffen.update({n: p["id"] for n in ziele if n not in getroffen})
        if p.get("alle_instanzen") and (datei := b.komponenten[p["komponente"]].get("datei")):
            getauscht[datei_schluessel(datei)] = p["id"]
    for i, p in enumerate(punkte):
        if p["typ"] != "komponente_neu" or "wie" not in p or p["wie"] not in b.komponenten:
            continue
        wie, datei = p["wie"], b.komponenten[p["wie"]].get("datei")
        punkt = getroffen.get(wie) or (getauscht.get(datei_schluessel(datei)) if datei else None)
        if punkt is not None:
            befunde.append(_befund(f"punkte[{i}].wie", f"Punkt {punkt} ersetzt {wie!r} bzw. alle Instanzen ihrer Datei: Die neue "
                                   "Komponente trüge die alte Datei. Stattdessen quelle nennen", BESTAND_REFERENZ))
    return befunde


def _bereich_befunde(spec: dict, b: _Bestand, dateien: set[str]) -> list[dict]:
    """Bereiche über mehrere Dateien: `in_datei` bekannt, genannte Punkte vorhanden und in der Datei des Bereichs (Koordinaten der
    Box gelten in dieser Datei)."""
    punkte = {p["id"]: p for p in spec["punkte"]}
    befunde = []
    for j, bereich in enumerate(spec.get("bereiche", [])):
        datei = bereich.get("in_datei")
        gilt = b.haupt
        if datei is not None:
            if not _ist_relativ(datei):
                befunde.append(_befund(f"bereiche[{j}].in_datei", "Die Datei muss relativ zur Bestandskopie genannt werden (kein "
                                       "absoluter Pfad, kein ..)", BESTAND_REFERENZ))
                gilt = None
            elif (rel := b.rel(datei)) is not None:
                gilt = rel
            elif not b.ist_haupt(datei):
                befunde.append(_befund(f"bereiche[{j}].in_datei", f"Die Datei {datei!r} gibt es in der Aufnahme nicht "
                                       f"(Dateien: {_beispiele(sorted(b.dateien))})", BESTAND_REFERENZ, dateien=sorted(b.dateien)))
                gilt = None
        for k, pid in enumerate(bereich["punkte"]):
            p = punkte.get(pid)
            if p is None:
                befunde.append(_befund(f"bereiche[{j}].punkte[{k}]", f"Der Bereich nennt den Punkt {pid!r}, den es nicht gibt"))
                continue
            if gilt is None or p["typ"] in BAUGRUPPEN_TYPEN:
                continue  # unbekannte Datei meldet der Bereich selbst; Baugruppen-Punkte brauchen keinen Bereich
            if "in_datei" in p:
                eigene = b.rel(p["in_datei"])
                if eigene is None:
                    continue  # meldet der Punkt selbst
            else:
                eigene = b.haupt
            if datei_schluessel(eigene) != datei_schluessel(gilt):
                befunde.append(_befund(f"bereiche[{j}].punkte[{k}]", f"Punkt {pid!r} gehört zu {eigene}, der Bereich gilt für {gilt}: "
                                       "Box und Features stünden in den Koordinaten der falschen Datei"))
    return befunde


def _pruefung_befunde(spec: dict, b: _Bestand, dateien: set[str]) -> list[dict]:
    befunde = []
    pruefung = spec.get("pruefung", {})
    if "volumen_delta" in pruefung:
        befunde.append(_befund("pruefung.volumen_delta", "volumen_delta gilt nicht für eine Baugruppe: Es gäbe keine Datei, deren "
                               "Körper es misst (Etappe 2)"))
    for m, messung in enumerate(pruefung.get("masse_pruefen", [])):
        pfad = f"pruefung.masse_pruefen[{m}]"
        datei = messung.get("in_datei")
        if datei is None:
            befunde.append(_befund(pfad, "masse_pruefen gilt nur für Teile (Etappe 2): in_datei nennt das Teil, in dem gemessen wird"))
        elif not _ist_relativ(datei) or b.rel(datei) is None:
            befunde.append(_befund(f"{pfad}.in_datei", f"Die Datei {datei!r} gibt es in der Aufnahme nicht oder ist kein Pfad innerhalb "
                                   f"der Bestandskopie (Dateien: {_beispiele(sorted(b.dateien))})", BESTAND_REFERENZ,
                                   dateien=sorted(b.dateien)))
        elif datei_schluessel(datei) not in dateien:
            befunde.append(_befund(f"{pfad}.in_datei", f"An {b.rel(datei)} hängt kein Punkt: Gemessen wird nur in einer Datei, die ein "
                                   "Punkt ändert"))
    return befunde


def _hinweise(spec: dict, b: _Bestand) -> list[dict]:
    hinweise = []
    for datei in dateien_mit_punkten(spec):
        rel = b.rel(datei)
        if rel is None or b.dateien[rel].get("art") != "teil":
            continue
        komponenten = b.instanzen(rel)
        if len(komponenten) >= 2:
            pfad = f"punkte[{scheiben_karte(spec, datei)['datei_punkt']}]"
            hinweise.append({"art": "instanzen", "pfad": pfad, "datei": rel, "anzahl": len(komponenten), "komponenten": komponenten,
                             "meldung": f"{rel} steckt {len(komponenten)}-mal in der Baugruppe: Die Punkte ändern alle Instanzen "
                                        f"({_beispiele(komponenten)})"})
    grenzen = sorted(n for n, v in b.verknuepfungen.items() if v.get("grenze"))
    ohne = [n for n in grenzen if not b.bewegungen.get(n, {}).get("gefahren")]
    if ohne:
        hinweise.append({"art": "grenzen_ohne_fahrt", "pfad": "bestand", "grenzen": ohne,
                         "meldung": f"Die Aufnahme hat {', '.join(ohne)} nicht gefahren (ohne Bewegung aufgenommen oder im Bestand "
                                    "gescheitert): swki pruefen meldet bewegung:* dafür als ok: None, nicht als bestanden"})
    return hinweise


def befunde_baugruppe(spec: dict, aufnahme: dict, datei_aufnahme: Callable[[str], dict], ordner: Path | None) -> tuple[list[dict], list[dict]]:
    """Was Etappe 1 an einer Baugruppen-Spec nicht prüft (Befunde, Hinweise): Dateien der Teil-Punkte, Baugruppen-Punkte,
    `lage_folgen`, `kollision_erlaubt`, Bereiche und Messungen über mehrere Dateien. `datei_aufnahme(rel)` liefert die Aufnahme
    eines Teils (`lade_datei_aufnahme`), `ordner` den Auftragsordner (Teil-Specs der Quellen). Die Prüfung der Teil-Punkte selbst
    (Maße, Features, Bereiche je Datei) macht `pruefe_baugruppe` mit dem Code von Etappe 1."""
    b = _Bestand(aufnahme)
    q = _Quellen(b, ordner)
    parameter = spec.get("parameter", {})
    alle_neu = {p["id"] for p in spec["punkte"] if p["typ"] == "komponente_neu"}
    neu_bisher: set[str] = set()
    befunde = []
    for i, p in enumerate(spec["punkte"]):
        pfad = f"punkte[{i}]"
        if p["id"] in b.komponenten:
            befunde.append(_befund(f"{pfad}.id", f"ID {p['id']!r} ist der Name einer Komponente im Bestand: Punkt-IDs dürfen keinen "
                                   "Komponentennamen tragen (Anker nennen beides)"))
        befunde += _punkt_befunde(i, p, b, neu_bisher, q, parameter, datei_aufnahme)
        for k, name in enumerate(p.get("lage_folgen", [])):
            befunde += _komponente(f"{pfad}.lage_folgen[{k}]", name, b, alle_neu)
        if p["typ"] == "komponente_neu":
            neu_bisher.add(p["id"])
    for k, eintrag in enumerate(spec.get("kollision_erlaubt", [])):
        for s, name in enumerate(eintrag["paar"]):
            befunde += _komponente(f"kollision_erlaubt[{k}].paar[{s}]", name, b, alle_neu)
    dateien = {datei_schluessel(d) for d in dateien_mit_punkten(spec)}
    befunde += _kombinations_befunde(spec, b) + _bereich_befunde(spec, b, dateien) + _pruefung_befunde(spec, b, dateien)
    return befunde, _hinweise(spec, b)


def _version_hinweise(spec: dict, aufnahme: dict, b: _Bestand) -> list[dict]:
    """Je Datei, die gespeichert wird und aus einer älteren SolidWorks-Version stammt, ein Hinweis (Spec §5.1, Entscheidung 12).
    Die Hauptbaugruppe zählt nur, wenn ein Punkt sie ändert."""
    def hinweis(datei: str, pfad: str) -> dict:
        return {"art": "version_aelter", "pfad": pfad, "datei": datei,
                "meldung": f"{datei} stammt aus einer älteren SolidWorks-Version: swki bauen speichert sie nur mit --hochstufen, danach "
                           f"lässt sie sich nur noch mit SolidWorks {aufnahme.get('sw_jahr', '')} oder neuer lesen"}

    hinweise = []
    if aenderung_an_haupt(spec) and aufnahme["datei"].get("version_aelter"):
        hinweise.append(hinweis(b.haupt, "bestand"))
    for datei in dateien_mit_punkten(spec):
        if (rel := b.rel(datei)) is not None and b.dateien[rel].get("version_aelter"):
            hinweise.append(hinweis(rel, f"punkte[{scheiben_karte(spec, datei)['datei_punkt']}].in_datei"))
    return hinweise


def pruefe_baugruppe(spec: dict, aufnahme: dict, datei_aufnahme: Callable[[str], dict], ordner: Path | None) -> tuple[list[dict], list[dict]]:
    """Die ganze Prüfung einer Baugruppen-Spec gegen die Aufnahme, ohne SolidWorks (Befunde, Hinweise): `befunde_baugruppe`, die
    Haupt-Scheibe und je Teil-Datei die Scheibe durch den Code von Etappe 1, dazu die Versionshinweise. Pfade der Scheiben sind
    auf die ganze Spec zurückgeführt. Eine Datei, die `befunde_baugruppe` nicht als Teil zulässt, hat keine Scheibe."""
    befunde, hinweise = befunde_baugruppe(spec, aufnahme, datei_aufnahme, ordner)
    b = _Bestand(aufnahme)
    haupt = scheiben_karte(spec, None)
    befunde += [{**x, "pfad": zurueck(x["pfad"], haupt)} for x in befunde_gegen_aufnahme(haupt_scheibe(spec), aufnahme, ordner)]
    for datei in dateien_mit_punkten(spec):
        rel = b.rel(datei)
        if rel is None or b.dateien[rel].get("art") != "teil":
            continue
        teil, karte = datei_aufnahme(rel), scheiben_karte(spec, datei)
        s = scheibe(spec, datei, b.dateien)
        feature_b, feature_h = feature_befunde(s, teil, ordner)
        befunde += [{**x, "pfad": zurueck(x["pfad"], karte)} for x in befunde_gegen_aufnahme(s, teil, ordner) + feature_b]
        hinweise += [{**x, "pfad": zurueck(x["pfad"], karte)} for x in feature_h]
    return befunde, hinweise + _version_hinweise(spec, aufnahme, b)


def freigabe_angaben(spec: dict, aufnahme: dict) -> dict:
    """Angaben je Punkt-ID für die Freigabe-Vorlage (aus der Aufnahme): `instanzen` (Zahl der vorhandenen Komponenten, die der
    Punkt trifft: alle Instanzen einer Teil-Datei, die ersetzten bzw. entfernten Komponenten; 0 für Punkte, die keine vorhandene
    Komponente treffen), `verknuepfungen` (die mitgehenden bzw. betroffenen Verknüpfungen) und `bewegungen` (betroffene
    Grenzverknüpfungen mit Fahrt im Bestand)."""
    b = _Bestand(aufnahme)
    angaben = {}
    for p in spec["punkte"]:
        typ, komponenten, verknuepfungen = p["typ"], [], []
        if p.get("in_datei") and (rel := b.rel(p["in_datei"])) is not None:
            komponenten = b.instanzen(rel)
        elif typ in ("komponente_entfernen", "komponente_ersetzen") and p["komponente"] in b.komponenten:
            ersetzen = typ == "komponente_ersetzen"
            komponenten = ersetzen_ziele(p, b.komponenten, spec["punkte"])[0] if ersetzen else [p["komponente"]]
            if "in_datei" not in p:
                verknuepfungen = sorted({v for k in komponenten for v in b.haengt_dran(k)})
        elif typ in ("verknuepfung_wert", "verknuepfung_loeschen") and p["verknuepfung"] in b.verknuepfungen:
            verknuepfungen = [p["verknuepfung"]]
        bewegungen = b.bewegungen_von(komponenten if typ in ("komponente_entfernen", "komponente_ersetzen") else [], verknuepfungen)
        angaben[p["id"]] = {"instanzen": len(komponenten), "verknuepfungen": verknuepfungen, "bewegungen": bewegungen}
    return angaben


def ergebnis_baugruppe(spec: dict, aufnahme: dict, datei_aufnahme: Callable[[str], dict], hinweise: list[dict]) -> dict:
    """Zusatz der Ausgabe von `swki validieren` für eine Baugruppe: `dateien` (Teile mit Punkten, relative Pfade der Aufnahme),
    `haupt_speichern`, `version_aelter` (muss eine zu speichernde Datei hochgestuft werden), `folgen` je `mass`-/`gleichung`-Punkt
    aus der Aufnahme des Teils und `angaben` je Punkt für die Freigabe-Vorlage."""
    b = _Bestand(aufnahme)
    dateien = [b.rel(d) for d in dateien_mit_punkten(spec) if b.rel(d) is not None]
    folgen = {p["id"]: folgen_von(p, datei_aufnahme(b.rel(p["in_datei"]))) for p in spec["punkte"]
              if p["typ"] in ("mass", "gleichung") and p.get("in_datei") and b.rel(p["in_datei"]) is not None}
    return {"dateien": dateien, "haupt_speichern": aenderung_an_haupt(spec), "folgen": folgen,
            "version_aelter": any(h["art"] == "version_aelter" for h in hinweise), "angaben": freigabe_angaben(spec, aufnahme)}
