"""Bewegungen gegen den Bestand (Spec Bestandsdateien §8.4, Plan Etappe 2 Task 6): Eine geänderte Baugruppe muss nachweislich noch
fahren. Fremde Baugruppen haben keine `bewegungen` in einer Spec, deshalb gilt die Datei: Jede Grenzverknüpfung der Hauptbaugruppe
ist eine Bewegung, das Soll ist die Fahrt an der Bestandskopie.

`fahre_bestand` fährt die Grenzen einer Aufnahme (Bestand oder Lauf) über `swki.baugruppe.bewegungslauf.fahre` und liefert das Feld
`bewegungen` von `bestand.json`; `vergleiche_bewegungen` hält den Lauf gegen den Bestand. Reine Logik über die Mechanik-Schnittstelle,
ohne SolidWorks. Die Einträge haben das Format `swki.pruefung.bewertung.eintrag`; `ok: False` ist ein Mangel, `ok: None` heißt
„nicht nachgewiesen". Grundsatz wie im Vergleich der Baugruppe: Unlesbar ist nie bestanden, ein falsches `ok: True` ist teurer als
ein Fehlalarm.

Regeln, die der Vergleich festlegt:
- Soll ist nur eine Grenze, die im Bestand gefahren ist. Was schon im Bestand nicht bestand (Prüfung `ok: False`), ist kein Mangel
  des Laufs, wenn dieselbe Prüfung im Lauf ebenfalls nicht besteht; es steht im Hinweis. Eine Grenze, die im Bestand nicht gefahren
  wurde (kein Weg, Fahrt gescheitert), hat kein Soll: `bewegung:<g>` ist `ok: True` mit dem Grund im Hinweis. Fehlt die Fahrt in der
  Aufnahme ganz (`--ohne-bewegung`), ist `bewegung:<g>` `ok: None`.
- Lief im Bestand eine Grenze und fehlt sie im Lauf (nicht in `bewegungen`, nicht gefahren), ist das ein Mangel, außer ein Punkt
  löscht die Verknüpfung (`verknuepfung_loeschen`, `komponente_entfernen`). Ein `verknuepfung_wert` an `min` oder `max` ändert den
  Bereich: gefahren wird der Bereich des Laufs; ohne Punkt ist ein anderer Bereich ein Mangel in `bewegung:<g>`.
- `bewegung_menge:<g>`: Dieselben Komponenten bewegen sich wie im Bestand (ersetzte unter ihrem neuen Namen). Neue Komponenten (aus
  den Punkten) dürfen mitfahren, entfernte fehlen; sonst ist jede andere Menge ein Mangel.
- `bewegung_kollision:<g>`: Eine Kollision in der Fahrt des Laufs ist ein Mangel, außer das Paar ist bekannt: statisch im Bestand,
  in der Fahrt des Bestands oder in `kollision_erlaubt` (`bekannte_paare`).
- Nicht abgedeckt, aber nie stumm (`abdeckung`, Eintrag `bewegung_abdeckung`): Grenzen in Unterbaugruppen und bewegliche
  (unterbestimmte) Komponenten ohne Grenze.
"""

from dataclasses import dataclass, field
from itertools import product

from swki.baugruppe.aufloesen import Verknuepfung
from swki.baugruppe.bewegung import Bewegung, BewegungsMesswerte, bewerte_bewegungen, ist_bewegt
from swki.baugruppe.bewegungslauf import Mechanik, StellungFehler, fahre
from swki.baugruppe.bewertung import UNTERBESTIMMT
from swki.baugruppe.sw_baugruppe import AUSRICHTUNG
from swki.bestand.vergleich_baugruppe import _ahnen, _je, _komma
from swki.pruefung.bewertung import eintrag

SW_ABSTAND, SW_WINKEL = 5, 6  # swMateType_e swMateDISTANCE / swMateANGLE
# swMateAlign_e: 0 gleich, 1 entgegengesetzt; 2 (nächste) und alles Übrige ergeben None
AUSRICHTUNG_TEXT = {zahl: text for text, zahl in AUSRICHTUNG.items()}
TOL_BEREICH = 1e-9


class SeiteUnklar(Exception):
    """Die bewegte Seite einer Grenze lässt sich nicht bestimmen (die Meldung nennt den Grund)."""


def _art(v: dict) -> str | None:
    return {SW_ABSTAND: "abstand", SW_WINKEL: "winkel"}.get(v.get("typ"))


def _partner(v: dict) -> tuple[str | None, str | None]:
    """Die beiden Partner einer Verknüpfung; `None` an einer Stelle ist eine Ebene oder Achse der Hauptbaugruppe."""
    partner = list(v.get("partner") or [])
    partner += [None] * (2 - len(partner))
    return partner[0], partner[1]


def _oberste_ebene(v: dict) -> bool:
    return all(p is None or "/" not in p for p in v.get("partner") or [])


def _unterdrueckt(v: dict, aktiv: str | None) -> bool:
    return _je(v.get("unterdrueckt"), aktiv) is True


# ------------------------------------------------------------------------------------------------------------------ Aufnahme

def grenze_als_bewegung(name: str, v: dict, komponente: str, schritte: int) -> Bewegung:
    """Die Grenzverknüpfung `name` (Eintrag aus `verknuepfungen` der Aufnahme) als Bewegung der bewegten Komponente `komponente`."""
    art = _art(v)
    if art is None:
        raise ValueError(f"{name}: swMateType {v.get('typ')} ist keine Grenze (Abstand oder Winkel)")
    if v.get("min") is None or v.get("max") is None:
        raise ValueError(f"{name}: min oder max nicht gelesen")
    return Bewegung(name, name, art, komponente, float(v["min"]), float(v["max"]), schritte)


def als_verknuepfung(name: str, v: dict) -> Verknuepfung:
    """Die Grenzverknüpfung als `Verknuepfung` für die treibende Verknüpfung (`sw_baugruppe.treibe`): Seite a und b tragen die
    Komponente und den Index der Entität in der Verknüpfung (`IMate2.MateEntity(0)` bzw. `(1)`), die Ausrichtung als Text."""
    art = _art(v)
    if art is None:
        raise ValueError(f"{name}: swMateType {v.get('typ')} ist keine Grenze (Abstand oder Winkel)")
    a, b = _partner(v)
    return Verknuepfung(id=name, vorlage=name, typ="grenze_abstand" if art == "abstand" else "grenze_winkel",
                        a={"komponente": a, "index": 0}, b={"komponente": b, "index": 1},
                        ausrichtung=AUSRICHTUNG_TEXT.get(v.get("ausrichtung")), wert=v.get("wert"), drehung_sperren=False,
                        min=v.get("min"), max=v.get("max"))


def grenzen_der_aufnahme(aufnahme: dict) -> dict[str, dict]:
    """Die Grenzverknüpfungen der Hauptbaugruppe (Name → Eintrag aus `verknuepfungen`), die gefahren werden: `grenze: true`, auf der
    obersten Ebene (kein Partner mit `/`), in der aktiven Konfiguration nicht unterdrückt. Eine Grenze mit unlesbaren Partnern
    gehört dazu: `fahre_bestand` vermerkt sie als nicht gefahren, statt sie zu übergehen."""
    aktiv = aufnahme.get("aktiv")
    return {n: v for n, v in (aufnahme.get("verknuepfungen") or {}).items()
            if v.get("grenze") and not _unterdrueckt(v, aktiv) and _oberste_ebene(v)}


def abdeckung(aufnahme: dict) -> list[str]:
    """Was die Bewegungsprüfung nicht abdeckt (Spec §8.4): Grenzen in Unterbaugruppen und bewegliche Komponenten ohne Grenze (aktive
    Konfiguration unterbestimmt, nicht fixiert, nicht unterdrückt; mit aktiver Grenze zählt eine Komponente als bestimmt)."""
    aktiv = aufnahme.get("aktiv")
    hinweise = []
    for n, v in (aufnahme.get("verknuepfungen") or {}).items():
        if v.get("grenze") and not _unterdrueckt(v, aktiv) and not _oberste_ebene(v):
            hinweise.append(f"Grenze {n} liegt in einer Unterbaugruppe ({_komma(p for p in v['partner'] if p)}), nicht gefahren")
    for n, k in (aufnahme.get("komponenten") or {}).items():
        if (_je(k.get("status"), aktiv) == UNTERBESTIMMT and _je(k.get("fixiert"), aktiv) is not True
                and _je(k.get("unterdrueckt"), aktiv) is not True):
            hinweise.append(f"Komponente {n} ist beweglich (unterbestimmt) und hat keine Grenze, nicht gefahren")
    return hinweise


def statische_paare(aufnahme: dict) -> set[frozenset]:
    """Die statischen Kollisionen der Aufnahme als Paare (für `fahre` am Bestand: sie zählen in der Fahrt nicht als neu)."""
    return {frozenset(k["paar"]) for k in aufnahme.get("kollisionen") or []}


# --------------------------------------------------------------------------------------------------------- bewegte Seite

def _seite_ohne_probe(v: dict, aufnahme: dict) -> str | None:
    """Die bewegte Seite, wenn die Aufnahme sie verrät: der Partner, der nicht die Ebene der Hauptbaugruppe ist, sonst der einzige
    nicht fixierte. `None`, wenn nur ein Probeschritt sie zeigt. `SeiteUnklar`, wenn die Grenze keine Komponente trägt."""
    a, b = _partner(v)
    if a is None and b is None:
        raise SeiteUnklar("beide Seiten der Grenze sind Ebenen oder Achsen der Hauptbaugruppe: keine bewegte Komponente")
    if a is None:
        return b
    if b is None:
        return a
    aktiv = aufnahme.get("aktiv")
    komponenten = aufnahme.get("komponenten") or {}
    fixiert = [_je(komponenten.get(k, {}).get("fixiert"), aktiv) for k in (a, b)]
    if fixiert == [True, False]:
        return b
    if fixiert == [False, True]:
        return a
    return None


def _probeschritt(mech: Mechanik, name: str, v: dict, a: str, b: str) -> str:
    """Grenze unterdrücken, mit der treibenden Verknüpfung von min nach max fahren und lesen, welche Seite sich bewegt hat; beide:
    a. Räumt immer auf (treibende Verknüpfung löschen, Grenze wieder aktivieren). `StellungFehler`, wenn der Schritt misslingt."""
    bw = grenze_als_bewegung(name, v, a, 1)
    try:
        mech.unterdruecke(bw, True)
        mech.halte(bw, bw.min)
        vorher = mech.zustand()
        if (meldung := mech.stelle(bw, bw.max)) is not None:
            raise StellungFehler(name, bw.max, meldung)
        nachher = mech.zustand()
    finally:
        for aufraeumen in (lambda: mech.loese(bw), lambda: mech.unterdruecke(bw, False)):
            try:
                aufraeumen()
            except Exception:
                pass  # Aufräumfehler verdecken die Ursache nicht (wie in `bewegungslauf.fahre`)
    fehlen = [k for k in (a, b) if k not in vorher or k not in nachher]
    if fehlen:
        raise SeiteUnklar(f"Probeschritt: {_komma(fehlen)} nicht im Modell gelesen")
    bewegt = [k for k in (a, b) if ist_bewegt(vorher[k][0], nachher[k][0])]
    if not bewegt:
        raise SeiteUnklar(f"Probeschritt: weder {a} noch {b} bewegt sich")
    return a if a in bewegt else b


def bewegte_seite(mech: Mechanik, name: str, v: dict, aufnahme: dict) -> str:
    """Die bewegte Komponente der Grenze `name`: die Seite, die nicht die Hauptbaugruppe ist, sonst der einzige nicht fixierte
    Partner, sonst zeigt sie ein Probeschritt (`fixiert` unbekannt oder beide gleich); bewegen sich beide, gilt Seite a.
    `SeiteUnklar`, wenn sich keine Seite bestimmen lässt; `StellungFehler`, wenn der Probeschritt misslingt."""
    seite = _seite_ohne_probe(v, aufnahme)
    if seite is not None:
        return seite
    a, b = _partner(v)
    return _probeschritt(mech, name, v, a, b)


# ---------------------------------------------------------------------------------------------------------------------- Fahrt

def _nicht_fahrbar(v: dict) -> str | None:
    """Warum die Grenze keinen Weg hat oder nicht lesbar ist (sonst `None`); min gleich max gäbe in `_sollweg` eine Division
    durch null."""
    partner = v.get("partner")
    if partner is None or len(partner) < 2:
        return "Partner der Grenze nicht gelesen"
    if _art(v) is None:
        return f"swMateType {v.get('typ')} ist weder Abstand noch Winkel"
    lo, hi = v.get("min"), v.get("max")
    if lo is None or hi is None:
        return "min oder max der Grenze nicht gelesen"
    if abs(hi - lo) <= TOL_BEREICH:
        return "min gleich max: kein Weg, nicht gefahren"
    if lo > hi:
        return "min größer als max, nicht gefahren"
    return None


def _nicht_gefahren(v: dict, komponente: str | None, grund: str) -> dict:
    return {"komponente": komponente, "art": _art(v), "min": v.get("min"), "max": v.get("max"), "gefahren": False, "bewegt": [],
            "raum": None, "kollisionen": [], "pruefungen": [], "hinweis": grund}


def _gefahren(b: Bewegung, m, tol_mm: float) -> dict:
    """Der Eintrag einer gefahrenen Grenze: Grundstellungslauf (bewegt, Raum), Kollisionen aller Läufe, Prüfungen der Bewertung."""
    laeufe = [lauf for lauf in m.laeufe if lauf.bewegung == b.name]
    grund = next(lauf for lauf in laeufe if not lauf.gegen)
    messwerte = BewegungsMesswerte(m.status_frei, m.status_gehalten, laeufe, [p for p in m.paare if b.name in p["bewegungen"]])
    pruefungen, _ = bewerte_bewegungen({"bewegungen": []}, [b], messwerte, tol_mm)
    hinweis = (f"Lauf bei Stellung {grund.fehler['stellung']:g} abgebrochen: {grund.fehler['meldung']}"
               if grund.fehler is not None else None)
    return {"komponente": b.komponente, "art": b.art, "min": b.min, "max": b.max, "gefahren": True, "bewegt": list(grund.bewegt),
            "raum": [round(c, 3) for c in grund.raum] if grund.raum else None,
            "kollisionen": [{"paar": list(k["paar"]), "volumen": k["volumen"]} for lauf in laeufe for k in lauf.kollisionen],
            "pruefungen": pruefungen, "hinweis": hinweis}


def fahre_bestand(mech: Mechanik, aufnahme: dict, grenzen: dict[str, dict], schritte: int, bekannt: set[frozenset],
                  grenze_mb: float, tol_mm: float, start_mb: float | None = None) -> dict:
    """Fährt die `grenzen` (`grenzen_der_aufnahme`) der Aufnahme von `min` bis `max` und liefert das Feld `bewegungen` der Aufnahme:
    Grenze → {komponente, art, min, max, gefahren, bewegt, raum, kollisionen, pruefungen, hinweis}. `aufnahme` ist die des Standes,
    der gefahren wird (Bestand oder Lauf); sie nennt die fixierten Komponenten für die bewegte Seite.

    Erst alle zusammen über `fahre` (Paarläufe, Kollisionen). Scheitert das mit `StellungFehler`, ist die benannte Grenze
    `gefahren: false` mit dem Grund, und der Rest fährt neu. Ohne Weg (min gleich max), mit unlesbaren Werten oder ohne bewegte
    Seite ist die Grenze ebenfalls `gefahren: false` mit Grund. `SpeicherKnapp` bricht ab, auch dies nie still.
    `start_mb`: Private Bytes zu Beginn der Prüfung; ohne Angabe die Abfrage vor der Fahrt."""
    ergebnis: dict[str, dict] = {}
    offen: list[Bewegung] = []
    for name, v in grenzen.items():
        if grund := _nicht_fahrbar(v):
            try:
                seite = _seite_ohne_probe(v, aufnahme) if v.get("partner") is not None else None
            except SeiteUnklar:
                seite = None
            ergebnis[name] = _nicht_gefahren(v, seite, grund)
            continue
        try:
            seite = bewegte_seite(mech, name, v, aufnahme)
        except SeiteUnklar as e:
            ergebnis[name] = _nicht_gefahren(v, None, str(e))
        except StellungFehler as e:
            ergebnis[name] = _nicht_gefahren(v, None, f"Probeschritt gescheitert: {e}")
        else:
            offen.append(grenze_als_bewegung(name, v, seite, schritte))
    if offen:
        start_mb = mech.speicher_mb() if start_mb is None else start_mb
    messwerte = None
    while offen:
        try:
            messwerte = fahre(mech, offen, bekannt, grenze_mb, tol_mm, start_mb)
            break
        except StellungFehler as e:
            b = next((x for x in offen if x.name == e.bewegung), None)
            if b is None:
                raise
            offen.remove(b)
            ergebnis[b.name] = _nicht_gefahren(grenzen[b.name], b.komponente, str(e))
    for b in offen:
        ergebnis[b.name] = _gefahren(b, messwerte, tol_mm)
    return {name: ergebnis[name] for name in grenzen}


# ------------------------------------------------------------------------------------------------------------------- Vergleich

def bekannte_paare(vorher: dict, spec: dict, neue: dict[str, list[str]], ersetzt: dict[str, str] | None = None) -> set[frozenset]:
    """Kollisionspaare, die in der Fahrt des Laufs keine neuen sind: die statischen Kollisionen des Bestands, die Kollisionen in der
    Fahrt des Bestands und `kollision_erlaubt` (eine Punkt-ID steht für die Komponenten, die der Lauf erzeugt hat; Namen ersetzter
    Komponenten gelten unter dem neuen Namen)."""
    c = _Kontext(spec, neue, ersetzt or {})
    paare = {frozenset(c.abbild(x) for x in k["paar"]) for k in vorher.get("kollisionen") or []}
    for e in (vorher.get("bewegungen") or {}).values():
        paare |= {frozenset(c.abbild(x) for x in k["paar"]) for k in e.get("kollisionen") or []}
    for e in spec.get("kollision_erlaubt") or []:
        a, b = e["paar"]
        paare |= {frozenset((x, y)) for x, y in product(c.namen(a), c.namen(b))}
    return paare


@dataclass
class _Kontext:
    spec: dict
    neue: dict[str, list[str]]
    ersetzt: dict[str, str]
    punkte: list[dict] = field(init=False)
    neue_namen: set[str] = field(init=False)   # neue und ersetzende Komponenten
    entfernt: set[str] = field(init=False)
    geloescht: set[str] = field(init=False)    # Verknüpfungen, die ein Punkt löscht
    bekannt: set[frozenset] = field(init=False, default_factory=set)

    def __post_init__(self):
        self.punkte = self.spec.get("punkte") or []
        self.neue_namen = {n for namen in self.neue.values() for n in namen} | set(self.ersetzt.values())
        self.entfernt = {p["komponente"] for p in self.punkte if p["typ"] == "komponente_entfernen"}
        self.geloescht = ({p["verknuepfung"] for p in self.punkte if p["typ"] == "verknuepfung_loeschen"}
                          | {n for p in self.punkte if p["typ"] == "komponente_entfernen" for n in p.get("verknuepfungen", [])})

    def abbild(self, name: str) -> str:
        """Der Name im Lauf: ersetzte Komponenten und ihre Kinder heißen dort anders."""
        for a in reversed(_ahnen(name)):
            if a in self.ersetzt:
                return self.ersetzt[a] + name[len(a):]
        return name

    def namen(self, name: str) -> list[str]:
        """Eine Punkt-ID steht für die Komponenten, die der Lauf erzeugt hat, ein SolidWorks-Name für sich (ein ersetzter für den
        Ersatz)."""
        return list(self.neue.get(name) or [self.abbild(name)])

    def ist_neu(self, name: str) -> bool:
        return any(a in self.neue_namen for a in _ahnen(name))

    def darf_fehlen(self, name: str) -> bool:
        return any(a in self.entfernt for a in _ahnen(name))

    def bereich_frei(self, grenze: str, feld: str) -> bool:
        """Ein `verknuepfung_wert`-Punkt nennt `min` bzw. `max` dieser Grenze."""
        return any(p["typ"] == "verknuepfung_wert" and p["verknuepfung"] == grenze and p.get("grenze") == feld for p in self.punkte)

    def id_im_lauf(self, pid: str) -> str:
        """ID einer Prüfung des Bestands unter den Komponentennamen des Laufs (`freiheitsgrad:<k>`, `sollweg:<g>:<k>`)."""
        teile = pid.split(":")
        if teile[0] in ("freiheitsgrad", "sollweg") and len(teile) >= 2:
            teile[-1] = self.abbild(teile[-1])
        return ":".join(teile)


def _bereich_befund(g: str, ve: dict, ne: dict, c: _Kontext) -> list[str]:
    """Der Bereich im Lauf weicht ab, ohne dass ein Punkt `min` bzw. `max` nennt."""
    befunde = []
    for feld in ("min", "max"):
        alt, neu = ve.get(feld), ne.get(feld)
        if alt is None or neu is None or abs(alt - neu) > TOL_BEREICH:
            if not c.bereich_frei(g, feld):
                befunde.append(f"{feld} steht auf {neu} statt {alt}, kein Punkt nennt es")
    return befunde


def _angehoben(e: dict, bestand: dict) -> dict:
    """Eine Prüfung, die im Lauf nicht besteht und im Bestand schon nicht bestand: kein Mangel des Laufs, der Befund steht im
    Hinweis."""
    grund = bestand.get("hinweis")
    teile = ["Schon im Bestand nicht bestanden, kein Mangel des Laufs" + (f" ({grund})" if grund else "")]
    if e.get("hinweis"):
        teile.append(f"im Lauf: {e['hinweis']}")
    return {**e, "ok": True, "hinweis": "; ".join(teile), "bestand_ok": False}


def _menge(g: str, ve: dict, ne: dict, c: _Kontext) -> dict:
    pid = f"bewegung_menge:{g}"
    if ve.get("bewegt") is None or ne.get("bewegt") is None:
        return eintrag(pid, None, hinweis="Die bewegten Komponenten sind nicht gelesen, nicht nachgewiesen", knoten=[])
    lauf = set(ne["bewegt"])
    erwartet = {c.abbild(x) for x in ve["bewegt"]}
    fehlen = sorted(c.abbild(x) for x in ve["bewegt"] if c.abbild(x) not in lauf and not c.darf_fehlen(x))
    zusaetzlich = sorted(y for y in lauf if y not in erwartet and not c.ist_neu(y))
    teile = ([f"bewegen sich nicht mehr: {_komma(fehlen)}"] if fehlen else []) + (
        [f"bewegen sich zusätzlich: {_komma(zusaetzlich)}"] if zusaetzlich else [])
    return eintrag(pid, not teile, ist=sorted(lauf), soll=sorted(erwartet), fehlen=fehlen, zusaetzlich=zusaetzlich,
                   knoten=fehlen + zusaetzlich, **({"hinweis": "; ".join(teile)} if teile else {}))


def _kollision(g: str, ne: dict, c: _Kontext) -> dict:
    """Neue Kollisionen in der Fahrt des Laufs: jedes Paar, das nicht bekannt ist (je Paar die größte Überlappung)."""
    pid = f"bewegung_kollision:{g}"
    if ne.get("kollisionen") is None:
        return eintrag(pid, None, hinweis="Die Kollisionen der Fahrt sind nicht gelesen, nicht nachgewiesen", knoten=[])
    neu: dict[frozenset, dict] = {}
    for k in ne["kollisionen"]:
        paar = frozenset(k["paar"])
        if paar in c.bekannt:
            continue
        if paar not in neu or (k.get("volumen") or 0) > (neu[paar].get("volumen") or 0):
            neu[paar] = {"paar": sorted(paar), "volumen": k.get("volumen")}
    ist = list(neu.values())
    return eintrag(pid, not ist, ist=ist, knoten=sorted({x for k in ist for x in k["paar"]}),
                   **({"hinweis": "Neue Kollisionen in der Fahrt: " + ", ".join(
                       f"{' / '.join(k['paar'])} ({k['volumen']} mm³)" for k in ist)} if ist else {}))


def _eintraege_der_grenze(g: str, ve: dict | None, ne: dict, c: _Kontext) -> list[dict]:
    """Die Prüfungen einer im Lauf gefahrenen Grenze; `ve` die des Bestands (`None`: neue Grenze ohne Soll)."""
    bestand = {c.id_im_lauf(e["id"]): e for e in (ve or {}).get("pruefungen") or []}
    ergebnis, gesehen = [], set()
    for e in ne.get("pruefungen") or []:
        pid = e["id"]
        gesehen.add(pid)
        if pid == f"bewegung_kollision:{g}":
            e = _kollision(g, ne, c)
        elif e.get("ok") is False and bestand.get(pid, {}).get("ok") is False:
            e = _angehoben(e, bestand[pid])
        if pid == f"bewegung:{g}" and ve is not None and (befund := _bereich_befund(g, ve, ne, c)):
            vorweg = [e["hinweis"]] if e.get("hinweis") else []
            e = {**e, "ok": False, "hinweis": "; ".join([*vorweg, "Bereich: " + "; ".join(befund)])}
        ergebnis.append(e)
    if ve is not None:
        ergebnis.append(_menge(g, ve, ne, c))
    if f"bewegung:{g}" not in gesehen:  # eine gefahrene Grenze ohne diese Prüfung beweist nichts
        ergebnis.append(eintrag(f"bewegung:{g}", None, hinweis="Die Prüfung bewegung fehlt im Lauf, nicht nachgewiesen",
                                knoten=[]))
    if f"bewegung_kollision:{g}" not in gesehen:
        ergebnis.append(_kollision(g, ne, c))
    for pid in bestand:
        if pid not in gesehen | {f"bewegung:{g}", f"bewegung_kollision:{g}"}:
            ergebnis.append(eintrag(pid, None, hinweis="Im Lauf nicht geprüft, nicht nachgewiesen", knoten=[]))
    return ergebnis


def _grenze_vergleichen(g: str, ve: dict | None, ne: dict | None, c: _Kontext) -> list[dict]:
    pid = f"bewegung:{g}"
    if ve is None or ve.get("gefahren") is None:
        return [eintrag(pid, None, hinweis="Die Aufnahme enthält keine Fahrt dieser Grenze (ohne Bewegung), nicht nachgewiesen",
                        knoten=[])]
    if ve["gefahren"] is not True:
        return [eintrag(pid, True, hinweis=f"Im Bestand nicht gefahren ({ve.get('hinweis')}), kein Soll", knoten=[],
                        bestand_gefahren=False)]
    if ne is None:
        return [eintrag(pid, False, hinweis="Die Grenze lief im Bestand und fehlt im Lauf (nicht gefahren), kein Punkt löscht sie",
                        knoten=[ve.get("komponente")] if ve.get("komponente") else [])]
    if ne.get("gefahren") is None:
        return [eintrag(pid, None, hinweis="Im Lauf ist die Fahrt nicht gelesen, nicht nachgewiesen", knoten=[])]
    if ne["gefahren"] is not True:
        return [eintrag(pid, False, hinweis=f"Im Lauf nicht gefahren, im Bestand schon: {ne.get('hinweis')}",
                        knoten=[ne["komponente"]] if ne.get("komponente") else [])]
    return _eintraege_der_grenze(g, ve, ne, c)


def _neue_grenze(g: str, ne: dict, c: _Kontext) -> list[dict]:
    """Eine Grenze, die der Bestand nicht hatte (Punkt `verknuepfung_neu`): kein Soll, nur die Fahrt selbst wird bewertet."""
    if ne.get("gefahren") is not True:
        return [eintrag(f"bewegung:{g}", None, hinweis=f"Neue Grenze, im Lauf nicht gefahren ({ne.get('hinweis')})",
                        knoten=[])]
    return _eintraege_der_grenze(g, None, ne, c)


def _zusammen(eintraege: list[dict]) -> list[dict]:
    """Jede ID einmal (`freiheitsgrad:<k>` kommt je Grenze der Komponente vor): das schlechteste Urteil, die Hinweise zusammen."""
    rang = {False: 0, None: 1, True: 2}
    zusammen: dict[str, dict] = {}
    for e in eintraege:
        alt = zusammen.get(e["id"])
        if alt is None:
            zusammen[e["id"]] = e
            continue
        hinweise = [h for h in (alt.get("hinweis"), e.get("hinweis")) if h]
        schlecht = e if rang[e["ok"]] < rang[alt["ok"]] else alt
        zusammen[e["id"]] = {**schlecht, **({"hinweis": "; ".join(dict.fromkeys(hinweise))} if hinweise else {})}
    return list(zusammen.values())


def vergleiche_bewegungen(vorher: dict, nachher: dict, spec: dict, neue: dict[str, list[str]],
                          ersetzt: dict[str, str] | None = None) -> list[dict]:
    """§8.4: Die Fahrt des Laufs gegen die des Bestands. `vorher` und `nachher` sind Baugruppen-Aufnahmen mit `bewegungen`
    (`fahre_bestand`); `neue` (Punkt-ID → SolidWorks-Namen der neuen Komponenten) und `ersetzt` (alter → neuer Name) kommen aus dem
    Protokoll des Baus wie in `vergleiche_baugruppe`. Je Grenze des Bestands `bewegung:<g>`, `bewegung_menge:<g>`,
    `bewegung_kollision:<g>`, `grenze:<g>`, `sollweg:<g>:<komponente>` und `freiheitsgrad:<komponente>`, dazu `bewegung_abdeckung`,
    wenn etwas nicht abgedeckt ist. Grenzen, die ein Punkt löscht, bleiben außen vor."""
    c = _Kontext(spec, neue, ersetzt or {})
    c.bekannt = bekannte_paare(vorher, spec, neue, ersetzt)
    vb, nb = vorher.get("bewegungen") or {}, nachher.get("bewegungen") or {}
    eintraege = []
    for g in dict.fromkeys([*grenzen_der_aufnahme(vorher), *vb]):
        if g not in c.geloescht:
            eintraege += _grenze_vergleichen(g, vb.get(g), nb.get(g), c)
    gesehen = {*grenzen_der_aufnahme(vorher), *vb}
    for g, ne in nb.items():
        if g not in gesehen and g not in c.geloescht:
            eintraege += _neue_grenze(g, ne, c)
    if hinweise := abdeckung(vorher):
        eintraege.append(eintrag("bewegung_abdeckung", True, ist=hinweise, knoten=[],
                                 hinweis="Nicht abgedeckt: " + "; ".join(hinweise)))
    return _zusammen(eintraege)
