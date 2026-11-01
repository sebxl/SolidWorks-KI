"""Vergleich der Baugruppe vorher/nachher (Spec Bestandsdateien §8.3, Plan Etappe 2 Task 5): der Präzisionsschutz der Baugruppe.

Reine Logik über zwei Baugruppen-Aufnahmen im Format `bestand.json` (Bestandskopie und Lauf nach dem Neuaufbau), ohne SolidWorks.
Die Einträge haben das Format `swki.pruefung.bewertung.eintrag`; `ok: False` ist ein Mangel, `ok: None` heißt „nicht
nachgewiesen" (kein Mangel, aber auch kein Bestanden), ein Mangel hat Vorrang. Grundsatz wie in `swki.bestand.vergleich`: Ein
Fehlalarm kostet eine Rückfrage, ein falsches `ok: True` die Datei des Kollegen. Unlesbar ist nie gleich und nie bestanden.

`vergleiche_baugruppe`: `komponenten`, `verknuepfungen`, `bestimmtheit`, `kollision`, `lage`, dann `punkt:<id>` je Baugruppen-Punkt
(die Teil-Punkte laufen als Scheiben durch Etappe 1). `vergleiche_dateien`: Eintrag `dateien`. Aus dem Protokoll des Baus kommen
`neue` (Punkt-ID → SolidWorks-Namen der neuen Komponenten), `ersetzt` (alter → neuer Name) und `neue_dateien` (was der Bau angelegt
hat). Das Protokoll gibt nur frei, was ein Punkt deckt: `neue` nur für `komponente_neu` (genau ein Name, nicht im Bestand) und
`komponente_ersetzen`, `ersetzt` nur für die Ziele der Punkte; alles andere ist ein Mangel in `komponenten` und gibt nichts frei.

Regeln, die der Vergleich festlegt:
- `None` oder ein fehlender Wert heißt: Lesen gescheitert, nie „keine Änderung". Ausnahme: `wert`, `min`, `max` einer Verknüpfung
  (innerhalb eines gelesenen `werte`-Eintrags heißt None „trägt keinen Wert") und `transform` einer in beiden Ständen unterdrückten
  Komponente (sie zählt nicht).
- Komponenten tragen alle Ebenen (`Sub-1/Teil-1`). Verglichen wird je Konfiguration, die beide Aufnahmen haben (`werte` einer
  Verknüpfung und `konfigurationen` einer Komponente nennen ihre Werte je Konfiguration). Fehlt eine Konfiguration im Lauf, ist eine
  dazugekommen oder wechselte die aktive, ist das ein Mangel in `komponenten`; die nicht verglichenen Konfigurationen lassen `lage`,
  `bestimmtheit` und `verknuepfungen` unbewiesen.
- Die Lage darf sich ändern bei neuen Komponenten, Zielen von `komponente_entfernen` und den Komponenten in `lage_folgen` aller Punkte.
  Ein Kind in einer Unterbaugruppe, die so frei ist, bleibt relativ zu ihr an seiner Stelle; bewegt es sich selbst, muss es in
  `lage_folgen` stehen. Dasselbe gilt für die Kinder einer ersetzten Unterbaugruppe, soweit beide Stände sie tragen. Eine ersetzte
  Komponente behält ihre Lage, außer `lage_folgen` nennt sie (alt oder neu); ihre Datei und Konfiguration dürfen abweichen.
- Neue Verknüpfungen kennt das Protokoll nicht beim Namen: Jeder `verknuepfung_neu`-Punkt beansprucht je erwartetem Typ die Verknüpfung
  mit seinen Partnern (die mit passendem Wert und passender Ausrichtung zuerst, eine Verknüpfung gehört einem Punkt); übrig bleibende
  neue sind ein Mangel. Die Ausrichtung prüft der Vergleich nur, wenn der Punkt sie nennt (beim Scharnier gilt sie für die Anlage, mit
  Vorgabe `entgegengesetzt`).
- Der Status (swConstrainedStatus_e) darf steigen, nie sinken (Rang wie `SKIZZE_RANG`); Partner einer von einem Punkt gelöschten
  Verknüpfung dürfen bis unterbestimmt sinken. Eine neue Komponente muss voll bestimmt sein, als Partner einer Grenzverknüpfung auch
  unterbestimmt, und darf nur fixiert sein, wenn der Punkt es verlangt.
- Verknüpfungsfehler: ein Tripel (Verknüpfung, Konfiguration, Code), das der Bestand nicht kennt, ist ein Mangel; Bekanntes steht in
  `bekannt`. Kollisionen (die der aktiven Konfiguration): je Paar die Summe beider Seiten; ein Paar, das der Bestand nicht kennt, oder
  eine größere Summe (Toleranz 1 % bzw. 0,01 mm³) ist ein Mangel, außer `kollision_erlaubt` nennt das Paar. Weggefallene Paare stehen
  im Eintrag und ändern `ok` nicht.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from itertools import product

from swki.baugruppe.bewegung import TOL_BEWEGT_DREHUNG, TOL_BEWEGT_MM, _drehung, _mal, _transponiert, ist_bewegt, verschiebung_mm
from swki.baugruppe.sw_baugruppe import AUSRICHTUNG
from swki.bestand.scheiben import aenderung_an_haupt, datei_schluessel, dateien_mit_punkten
from swki.bestand.vergleich import SKIZZE_RANG, TOL, bekannte_fehler_in
from swki.pruefung.bewertung import eintrag
from swki.spec.ausdruck import auswerten
from swki.verbindung import in_mm

TOL_KOLLISION_REL = 0.01  # 1 % des Volumens im Bestand
TOL_KOLLISION_MM3 = 0.01
VOLL_BESTIMMT, UNTERBESTIMMT = 3, 2  # swConstrainedStatus_e

# Welche swMateType_e eine neue Verknüpfung der Art `art` in SolidWorks ergibt (`swki.baugruppe.sw_baugruppe.MATE_TYP`, `MATE_KOPPLUNG`,
# `aufloesen._einzeln`): ein Typ je Eintrag der Liste; ein Scharnier ist konzentrisch plus deckungsgleich der Anlageflächen
MATE_TYPEN = {"deckungsgleich": [0], "konzentrisch": [1], "senkrecht": [2], "parallel": [3], "abstand": [5], "winkel": [6],
              "grenze_abstand": [5], "grenze_winkel": [6], "scharnier": [1, 0], "zahnrad": [10], "zahnstange": [13]}
PUNKT_TYPEN = ("komponente_neu", "komponente_entfernen", "komponente_ersetzen", "verknuepfung_neu", "verknuepfung_wert",
               "verknuepfung_loeschen")
KOMPONENTE_FELDER = ("datei", "virtuell", "muster", "loesen")  # je Komponente
# je Konfiguration: (Feld der Komponente, Name im Befund); `konfigurationen` ist die referenzierte Konfiguration des Teils
KOMPONENTE_JE_KONFIGURATION = (("fixiert", "fixiert"), ("unterdrueckt", "unterdrueckt"), ("konfigurationen", "konfiguration"))
MATE_FELDER = ("typ", "ausrichtung", "grenze", "gesteuert")
MATE_WERTE = ("wert", "min", "max")


def _gleich(a: float, b: float) -> bool:
    return abs(a - b) <= TOL + 1e-12


def _rang(status) -> int:
    return SKIZZE_RANG.get(status, -1)


def _ahnen(name: str) -> list[str]:
    """Die Komponente selbst und die Unterbaugruppen, in denen sie steckt (`A/B/C` → `A`, `A/B`, `A/B/C`)."""
    teile = name.split("/")
    return ["/".join(teile[:i]) for i in range(1, len(teile) + 1)]


def bekannte_fehler_baugruppe(aufnahme: dict, konfiguration: str) -> set[str]:
    """Features und Verknüpfungen, deren Fehler die Baugruppe in dieser Konfiguration schon hatte: `neuaufbau` und die Fehlercodes
    der Verknüpfungen. Bau und Fahrt rechnen damit."""
    return bekannte_fehler_in(aufnahme, konfiguration) | {n for n, v in (aufnahme.get("verknuepfungen") or {}).items()
                                                          if (v.get("fehler") or {}).get(konfiguration)}


def neuer_verknuepfungsfehler(vorher: dict | None, nachher: dict, konfiguration: str) -> str | None:
    """Text, wenn die Verknüpfung in dieser Konfiguration einen Fehler trägt, den `vorher` dort nicht kennt (`None`: sie ist neu).
    Ein Code, der sich nicht lesen lässt, zählt wie ein Fehler. Handler und Stand vor dem Speichern rechnen damit."""
    code = (nachher.get("fehler") or {}).get(konfiguration)
    if code is None:
        return f"Fehlercode in {konfiguration} nicht lesbar"
    alt = ((vorher or {}).get("fehler") or {}).get(konfiguration)
    return f"Fehler {code} in {konfiguration}" if code != 0 and code != alt else None


def ersetzen_ziele(p: dict, komponenten: dict, punkte: list[dict]) -> tuple[list[str], list[str]]:
    """(Komponenten, die ein `komponente_ersetzen` trifft; nicht lesbar). `komponenten`: die der Aufnahme, `punkte`: alle der
    Spec. `alle_instanzen` heißt: die Komponenten mit der Datei der genannten, jede Ebene, ohne die von `komponente_entfernen`
    genannten samt ihren Kindern. Handler, `validieren` und Vergleich rechnen mit dieser einen Menge, sonst hinge das Ergebnis an
    der Reihenfolge der Punkte. Ist eine Datei nicht gelesen, lässt sich nicht ausschließen, dass die Komponente eine Instanz
    ist."""
    name = p["komponente"]
    k = komponenten.get(name)
    if not p.get("alle_instanzen") or k is None:
        return [name], []
    if k.get("datei") is None:
        return [name], [f"{name}: Datei nicht lesbar"]
    entfernt = {x["komponente"] for x in punkte if x["typ"] == "komponente_entfernen"}
    namen, unlesbar = [], []
    for n, x in komponenten.items():
        if set(_ahnen(n)) & entfernt:
            continue
        if x.get("datei") is None:
            unlesbar.append(f"{n}: Datei nicht lesbar, Instanz von {name} nicht auszuschließen")
        elif datei_schluessel(x["datei"]) == datei_schluessel(k["datei"]):
            namen.append(n)
    return sorted(namen) or [name], unlesbar


def abbild_name(name: str | None, ersetzt: dict[str, str]) -> str | None:
    """Der Name im Lauf: ersetzte Komponenten und ihre Kinder heißen dort anders (`None`: Hauptbaugruppe)."""
    if name is None:
        return None
    for a in reversed(_ahnen(name)):
        if a in ersetzt:
            return ersetzt[a] + name[len(a):]
    return name


def namen_im_lauf(name: str, neue: dict[str, list[str]], ersetzt: dict[str, str]) -> list[str]:
    """Eine Punkt-ID steht für die Komponenten, die sie im Lauf erzeugt hat, ein SolidWorks-Name für sich, der Altname einer
    ersetzten Komponente für ihren Ersatz."""
    return list(neue.get(name) or [abbild_name(name, ersetzt)])


def soll_werte(p: dict, parameter: dict) -> dict[str, float]:
    """Wert bzw. Grenzen einer neuen Verknüpfung, ausgewertet mit den Parametern der Spec (mm und Grad)."""
    felder = ("wert",) if p["art"] in ("abstand", "winkel") else ("min", "max") if p["art"].startswith("grenze_") else ()
    return {f: float(auswerten(p[f], parameter)) for f in felder if f in p}


def soll_ausrichtung(p: dict, i: int) -> int | None:
    """Ausrichtung, die der Punkt für die i-te neue Verknüpfung verlangt (`None`: keine Prüfung)."""
    if p["art"] == "scharnier":  # die Anlage hat die Vorgabe `entgegengesetzt`, die Konzentrik bleibt frei (`aufloesen._einzeln`)
        return AUSRICHTUNG[p.get("ausrichtung", "entgegengesetzt")] if i == 1 else None
    return AUSRICHTUNG[p["ausrichtung"]] if "ausrichtung" in p else None


def _je(werte, konfiguration: str):
    """Wert einer Komponente oder Verknüpfung in einer Konfiguration; `None`, wenn er nicht gelesen wurde."""
    return (werte or {}).get(konfiguration)


def _partner_schluessel(partner) -> tuple[bool, str]:
    """Sortierschlüssel: `None` (Ebene oder Achse der Hauptbaugruppe) steht hinten und lässt sich mit Namen vergleichen."""
    return partner is None, partner or ""


def _komma(namen) -> str:
    return ", ".join(str(n) for n in namen)


def _wo(q: dict) -> str:
    """Feld und Konfiguration einer Abweichung für den Hinweis."""
    return q["feld"] + (f" {q['konfiguration']}" if "konfiguration" in q else "")


def _lage_text(t0, t1) -> str:
    """Wie die Lage abweicht, in mm und als Hinweis auf eine Drehung."""
    weg = max(abs(c) for c in verschiebung_mm(t0, t1))
    gedreht = any(abs(t1[i] - t0[i]) > 1e-6 for i in range(9))
    return f"{weg:.3f} mm" + (", gedreht" if gedreht else "")


def _relativ(ta, tk) -> tuple[list[list[float]], list[float]]:
    """Lage des Kindes `tk` in den Achsen des Ahnen `ta`: Drehung Caᵀ·Ck und Verschiebung Caᵀ·(tk − ta) in mm (Spaltenform wie
    `swki.baugruppe.bewegung`). Eine starre Bewegung beider ändert sie nicht."""
    ca, ck = _drehung(ta), _drehung(tk)
    d = [in_mm(tk[9 + i] - ta[9 + i]) for i in range(3)]
    return _mal(_transponiert(ca), ck), [sum(ca[j][i] * d[j] for j in range(3)) for i in range(3)]


def _relativ_bewegt(ta0, tk0, ta1, tk1) -> bool:
    (c0, v0), (c1, v1) = _relativ(ta0, tk0), _relativ(ta1, tk1)
    return (any(abs(v1[i] - v0[i]) > TOL_BEWEGT_MM for i in range(3))
            or any(abs(c1[i][j] - c0[i][j]) > TOL_BEWEGT_DREHUNG for i in range(3) for j in range(3)))


def _protokoll_befund(meldung: str) -> dict:
    return {"art": "protokoll", "meldung": meldung}


def _wert_gelesen(m: dict, konfiguration: str, feld: str) -> tuple[bool, float | None]:
    """(gelesen, Wert) von `wert`/`min`/`max` einer Verknüpfung in einer Konfiguration: Ohne Eintrag in `werte` ist nichts gelesen,
    `None` in einem gelesenen Eintrag heißt: trägt keinen Wert."""
    e = (m.get("werte") or {}).get(konfiguration)
    if not isinstance(e, dict) or feld not in e:
        return False, None
    return True, e[feld]


def _wert_gleich(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return _gleich(a, b)


@dataclass
class _Lauf:
    spec: dict
    vorher: dict
    nachher: dict
    neue_roh: dict[str, list[str]]
    ersetzt_roh: dict[str, str]
    neue_dateien_roh: Iterable[str] = ()
    punkte: list[dict] = field(init=False)           # die Baugruppen-Punkte
    parameter: dict = field(init=False)
    konfigs: list[str] = field(init=False)           # die beide Aufnahmen gemeinsam haben, in der Reihenfolge des Bestands
    konfig_befunde: list[dict] = field(init=False)   # Konfigurationen fehlen oder neu, aktive gewechselt
    konfig_unlesbar: list[str] = field(init=False)   # aktive Konfiguration oder alle Konfigurationen nicht gelesen
    nicht_verglichen: list[str] = field(init=False)  # Konfigurationen, die nur ein Stand hat
    v_komp: dict = field(init=False)
    n_komp: dict = field(init=False)
    v_mate: dict = field(init=False)
    n_mate: dict = field(init=False)
    neue: dict[str, list[str]] = field(init=False)   # das Protokoll, soweit ein Punkt es deckt
    ersetzt: dict[str, str] = field(init=False)
    protokoll_befunde: list[dict] = field(init=False)
    ziele: dict[str, list[str]] = field(init=False)  # Punkt-ID → alte Namen, die `komponente_ersetzen` trifft
    ziele_unlesbar: dict[str, list[str]] = field(init=False)
    neue_dateien: set[str] = field(init=False)       # Vergleichsform
    erwartet_neu: set[str] = field(init=False)       # Namen aus dem Protokoll: neue und ersetzende Komponenten
    reine_neue: set[str] = field(init=False)         # nur die neuen (ohne ersetzende)
    weg: set[str] = field(init=False)                # Komponenten, die verschwinden dürfen: entfernte und ersetzte samt Kindern
    entfernt: set[str] = field(init=False)           # nur die Ziele von komponente_entfernen
    lage_frei: set[str] = field(init=False)          # Komponenten, deren Lage sich ändern darf (ihre Kinder nur relativ dazu)
    geloeschte_mates: set[str] = field(init=False)
    wert_frei: dict[tuple[str, str], set[str]] = field(init=False)  # (Verknüpfung, Feld) → Konfigurationen, in denen der Wert wandern darf
    bekannte_fehler: set[tuple] = field(init=False)
    zuordnung: dict[str, list[str | None]] = field(init=False)  # Punkt-ID → beanspruchte neue Verknüpfung je erwartetem Typ
    mates_frei: list[str] = field(init=False)        # neue Verknüpfungen, die kein Punkt beansprucht

    def __post_init__(self):
        alle = self.spec.get("punkte", [])
        self.punkte = [p for p in alle if p["typ"] in PUNKT_TYPEN]
        self.parameter = self.spec.get("parameter", {})
        self.v_komp, self.n_komp = self.vorher["komponenten"], self.nachher["komponenten"]
        self.v_mate, self.n_mate = self.vorher["verknuepfungen"], self.nachher["verknuepfungen"]
        self.neue_dateien = {datei_schluessel(d) for d in self.neue_dateien_roh}
        self._konfigurationen()
        self._ziele(alle)
        self._protokoll(alle)
        self.erwartet_neu = {n for namen in self.neue.values() for n in namen} | set(self.ersetzt.values())
        self.reine_neue = {n for namen in self.neue.values() for n in namen} - set(self.ersetzt.values())
        entfernt = {p["komponente"] for p in alle if p["typ"] == "komponente_entfernen"}
        self.entfernt = entfernt
        self.weg = entfernt | set(self.ersetzt)
        self.lage_frei = entfernt | self.reine_neue | {n for p in alle for n in p.get("lage_folgen", [])}
        self.geloeschte_mates = ({n for p in alle if p["typ"] == "komponente_entfernen" for n in p["verknuepfungen"]}
                                 | {p["verknuepfung"] for p in alle if p["typ"] == "verknuepfung_loeschen"})
        self.wert_frei = {}
        for p in alle:
            if p["typ"] == "verknuepfung_wert":
                gewaehlt = set(self.gewaehlt(p)[0])
                for feld in ({"wert"} if p.get("grenze") is None else {p["grenze"], "wert"}):
                    self.wert_frei.setdefault((p["verknuepfung"], feld), set()).update(gewaehlt)
        self.bekannte_fehler = {(n, k, code) for n, m in self.v_mate.items() for k, code in (m.get("fehler") or {}).items()
                                if code not in (0, None)}
        self._ordne_verknuepfungen()

    # --------------------------------------------------------------------------------------------- Konfigurationen

    def _konfigurationen(self) -> None:
        """Gleiche Konfigurationen und gleiche aktive wie im Bestand (Maßstab `swki.bestand.vergleich._konfigurationen`)."""
        vk, nk = self.vorher.get("konfigurationen") or [], self.nachher.get("konfigurationen") or []
        self.konfigs = [k for k in vk if k in nk]
        fehlen, neu = [k for k in vk if k not in nk], [k for k in nk if k not in vk]
        self.konfig_befunde, self.konfig_unlesbar = [], []
        if fehlen:
            self.konfig_befunde.append({"art": "konfigurationen_fehlen", "konfigurationen": fehlen,
                                        "meldung": f"Konfigurationen fehlen im Lauf: {_komma(fehlen)}"})
        if neu:
            self.konfig_befunde.append({"art": "konfigurationen_neu", "konfigurationen": neu,
                                        "meldung": f"Konfigurationen sind neu im Lauf: {_komma(neu)}"})
        va, na = self.vorher.get("aktiv"), self.nachher.get("aktiv")
        if va is None or na is None:
            self.konfig_unlesbar.append("aktive Konfiguration")
        elif va != na:  # sonst öffnet der Kollege eine andere Variante
            self.konfig_befunde.append({"art": "aktiv", "soll": va, "ist": na,
                                        "meldung": f"Die aktive Konfiguration ist {na!r} statt {va!r}"})
        self.nicht_verglichen = [f"Konfiguration {k} nicht verglichen" for k in [*fehlen, *neu]]
        if not self.konfigs and not (fehlen or neu):
            self.konfig_unlesbar.append("keine Konfiguration gelesen")

    @property
    def konfig_offen(self) -> list[str]:
        """Was die Einträge `lage`, `bestimmtheit` und `verknuepfungen` wegen der Konfigurationen nicht nachweisen können."""
        return self.konfig_unlesbar + self.nicht_verglichen

    # --------------------------------------------------------------------------------------------------- Protokoll

    def _ziele(self, alle: list[dict]) -> None:
        self.ziele, self.ziele_unlesbar = {}, {}
        for p in alle:
            if p["typ"] == "komponente_ersetzen":
                self.ziele[p["id"]], self.ziele_unlesbar[p["id"]] = ersetzen_ziele(p, self.v_komp, alle)

    def _protokoll(self, alle: list[dict]) -> None:
        """Das Protokoll gegen die Punkte: Was kein Punkt deckt, ist ein Mangel und gibt weder Lage noch Komponenten frei."""
        ids_neu = {p["id"] for p in alle if p["typ"] == "komponente_neu"}
        ids_ersetzen = {p["id"] for p in alle if p["typ"] == "komponente_ersetzen"}
        befunde = []
        self.neue, self.ersetzt = {}, {}
        ziele = {alt for z in self.ziele.values() for alt in z}
        # jeder Name höchstens einmal über neue (komponente_neu) und ersetzt hinweg, sonst ist nicht zu sagen, was er ist
        genannt = Counter([namen[0] for pid, namen in self.neue_roh.items() if pid in ids_neu and len(namen) == 1]
                          + list(self.ersetzt_roh.values()))
        doppelt = {n for n, anzahl in genannt.items() if anzahl > 1}
        for n in sorted(doppelt):
            befunde.append(_protokoll_befund(f"Der Name {n} kommt im Protokoll mehrfach vor (neue Komponente oder Ersatz): "
                                             "Jeder Name steht für genau eine Komponente"))
        for alt, neu in self.ersetzt_roh.items():
            if alt not in ziele:
                befunde.append(_protokoll_befund(f"Das Protokoll ersetzt {alt}, aber kein Punkt komponente_ersetzen trifft sie"))
            elif alt not in self.v_komp:
                befunde.append(_protokoll_befund(f"Das Protokoll ersetzt {alt}, die es im Bestand nicht gibt"))
            elif neu in self.v_komp:
                befunde.append(_protokoll_befund(f"Die ersetzende Komponente {neu} (für {alt}) gibt es schon im Bestand"))
            elif neu not in doppelt:
                self.ersetzt[alt] = neu
        for pid, namen in self.neue_roh.items():
            if pid in ids_neu:
                if len(namen) != 1:
                    befunde.append(_protokoll_befund(f"komponente_neu {pid} hat {len(namen)} Namen im Protokoll statt einem"))
                elif namen[0] in self.v_komp:
                    befunde.append(_protokoll_befund(f"Die neue Komponente {namen[0]} (Punkt {pid}) gibt es schon im Bestand"))
                elif namen[0] not in doppelt:
                    self.neue[pid] = list(namen)
            elif pid in ids_ersetzen:
                if fremde := [n for n in namen if n not in self.ersetzt.values()]:
                    befunde.append(_protokoll_befund(f"Punkt {pid} ersetzt nicht: {_komma(fremde)}"))
            else:
                befunde.append({"art": "protokoll", "meldung": f"Das Protokoll nennt neue Komponenten für {pid}, der kein Punkt "
                                                               "komponente_neu oder komponente_ersetzen ist"})
        self.protokoll_befunde = befunde

    # ------------------------------------------------------------------------------------------------------ Namen

    def gewaehlt(self, p: dict) -> tuple[list[str], list[str]]:
        """(Konfigurationen, die der Punkt nennt und beide Stände haben; genannte, die nicht verglichen wurden). Vorgabe: alle."""
        k = p.get("konfigurationen", "alle")
        if k == "alle":
            return list(self.konfigs), []
        return [x for x in k if x in self.konfigs], [x for x in k if x not in self.konfigs]

    def namen(self, name: str) -> list[str]:
        return namen_im_lauf(name, self.neue, self.ersetzt)

    def abbild(self, name: str | None) -> str | None:
        return abbild_name(name, self.ersetzt)

    def ist_neu(self, name: str) -> bool:
        return any(a in self.erwartet_neu for a in _ahnen(name))

    def darf_fehlen(self, name: str) -> bool:
        return any(a in self.weg for a in _ahnen(name))

    def freier_ahne(self, name: str) -> str | None:
        """Die nächste Unterbaugruppe über dem Kind, deren Lage sich ändern darf."""
        return next((a for a in reversed(_ahnen(name)[:-1]) if a in self.lage_frei), None)

    def paare(self) -> list[tuple[str, str]]:
        """Komponenten in beiden Ständen: gleicher Name, oder (alt, neu) einer Ersetzung."""
        gleiche = [(x, x) for x in self.v_komp if x in self.n_komp and x not in self.ersetzt]
        return gleiche + [(a, b) for a, b in self.ersetzt.items() if a in self.v_komp and b in self.n_komp]

    def ersetzte_kinder(self) -> list[tuple[str, str, str, str]]:
        """(Kind im Bestand, Kind im Lauf, Ahne im Bestand, Ahne im Lauf) für die Kinder ersetzter Unterbaugruppen, die beide
        Stände tragen."""
        ergebnis = []
        for x in self.v_komp:
            for a in reversed(_ahnen(x)[:-1]):
                if a in self.ersetzt:
                    y = self.ersetzt[a] + x[len(a):]
                    if y in self.n_komp and a in self.v_komp and self.ersetzt[a] in self.n_komp:
                        ergebnis.append((x, y, a, self.ersetzt[a]))
                    break
        return ergebnis

    def grenze_partner(self) -> set[str]:
        return {p for m in self.n_mate.values() if m.get("grenze") for p in m.get("partner") or []}

    def partner_vorher(self, name: str) -> tuple | None:
        """Partner einer Verknüpfung im Bestand, mit den Namen der ersetzenden Komponenten; `None`, wenn nicht gelesen."""
        partner = self.v_mate[name].get("partner")
        return None if partner is None else tuple(sorted((self.abbild(p) for p in partner), key=_partner_schluessel))

    # ------------------------------------------------------------------------------------------------ Verknüpfungen

    def wert_befunde(self, name: str, soll: dict[str, float], konfigs: list[str] | None = None) -> tuple[list[str], list[str]]:
        """(Mängel, nicht lesbar): `wert`/`min`/`max` der Verknüpfung in den `konfigs` (Vorgabe: jede gemeinsame) gegen `soll`.
        Ohne Konfiguration ist nichts nachgewiesen."""
        probleme, unlesbar = [], []
        m = self.n_mate[name]
        konfigs = self.konfigs if konfigs is None else konfigs
        if soll and not konfigs:
            unlesbar.append(f"{name}: keine Konfiguration zum Vergleichen")
        for feld, w in soll.items():
            for k in konfigs:
                gelesen, ist = _wert_gelesen(m, k, feld)
                if not gelesen:
                    unlesbar.append(f"{name} ({k}): {feld}")
                elif ist is None or not _gleich(ist, w):
                    probleme.append(f"{name} ({k}): {feld} steht auf {ist} statt {w:g}")
        return probleme, unlesbar

    def _passt(self, name: str, typ: int, grenze: bool | None, a: list[str], b: list[str]) -> bool:
        m = self.n_mate[name]
        partner = set(m.get("partner") or [])
        if m.get("typ") != typ or (grenze is not None and bool(m.get("grenze")) != grenze):
            return False
        return any(x in partner and y in partner and x != y for x, y in product(a, b))

    def _ordne_verknuepfungen(self) -> None:
        """Jeder `verknuepfung_neu`-Punkt beansprucht je erwartetem Typ eine neue Verknüpfung zwischen seinen Partnern, die mit
        passendem Wert und passender Ausrichtung zuerst."""
        frei = sorted(n for n in self.n_mate if n not in self.v_mate)
        self.zuordnung = {}
        for p in self.punkte:
            if p["typ"] != "verknuepfung_neu":
                continue
            soll = soll_werte(p, self.parameter)
            gewaehlt = []
            for i, typ in enumerate(MATE_TYPEN[p["art"]]):
                anlage = p["art"] == "scharnier" and i == 1
                a = self.namen((p.get("anlage_a") if anlage and "anlage_a" in p else p["a"])["komponente"])
                b = self.namen((p.get("anlage_b") if anlage and "anlage_b" in p else p["b"])["komponente"])
                grenze = p["art"].startswith("grenze_") if typ in (5, 6) else None
                kandidaten = [n for n in frei if self._passt(n, typ, grenze, a, b)]
                ausrichtung = soll_ausrichtung(p, i)
                kandidaten.sort(key=lambda n: (not (i == 0 and not any(self.wert_befunde(n, soll))),
                                               ausrichtung is not None and self.n_mate[n].get("ausrichtung") != ausrichtung))
                wahl = kandidaten[0] if kandidaten else None
                if wahl is not None:
                    frei.remove(wahl)
                gewaehlt.append(wahl)
            self.zuordnung[p["id"]] = gewaehlt
        self.mates_frei = frei

    def neue_fehler_an(self, namen: set[str] | None = None, komponenten: set[str] | None = None) -> tuple[list[str], list[str]]:
        """(Mängel, nicht lesbar): Fehlercodes der Verknüpfungen `namen` bzw. aller mit einer der `komponenten` als Partner, die der
        Bestand nicht kennt."""
        probleme, unlesbar = [], []
        for n, m in self.n_mate.items():
            if not ((namen is not None and n in namen) or (komponenten is not None and komponenten & set(m.get("partner") or []))):
                continue
            for k in self.konfigs:
                code = _je(m.get("fehler"), k)
                if code is None:
                    unlesbar.append(f"{n} ({k}): Fehlercode nicht lesbar")
                elif code != 0 and (n, k, code) not in self.bekannte_fehler:
                    probleme.append(f"{n} ({k}): Fehler {code}")
        return probleme, unlesbar

    def status_neu(self, name: str) -> tuple[list[str], list[str]]:
        """(Mängel, nicht lesbar) für den Status einer neuen Komponente: voll bestimmt, als Partner einer Grenzverknüpfung auch
        unterbestimmt. Eine unterdrückte zählt hier nicht (das meldet ihr Punkt)."""
        k = self.n_komp.get(name)
        if k is None:
            return [], []
        erlaubt = {VOLL_BESTIMMT, UNTERBESTIMMT} if name in self.grenze_partner() else {VOLL_BESTIMMT}
        probleme, unlesbar = [], []
        for konfig in self.konfigs:
            unterdrueckt = _je(k.get("unterdrueckt"), konfig)
            if unterdrueckt is None:
                unlesbar.append(f"{name} ({konfig}): Unterdrückung nicht lesbar")
                continue
            if unterdrueckt:
                continue
            status = _je(k.get("status"), konfig)
            if status is None:
                unlesbar.append(f"{name} ({konfig}): Status nicht lesbar")
            elif status not in erlaubt:
                probleme.append(f"{name} ({konfig}): Status {status} statt voll bestimmt" +
                                (" (oder unterbestimmt als Grenze-Partner)" if len(erlaubt) > 1 else ""))
        return probleme, unlesbar


def _ergebnis(pid: str, probleme: list, unlesbar: list, hinweis_teile: list[str], **daten) -> dict:
    """Mangel vor „nicht nachgewiesen" vor bestanden; `hinweis` nur, wenn es etwas zu sagen gibt."""
    ok = False if probleme else None if unlesbar else True
    teile = hinweis_teile + ([f"Nicht lesbar, also nicht nachgewiesen: {_komma(unlesbar)}"] if unlesbar else [])
    return eintrag(pid, ok, **daten, **({"hinweis": "; ".join(teile)} if teile else {}))


# ------------------------------------------------------------------------------------------------------------ Komponenten

def _komponenten(c: _Lauf) -> dict:
    """Gleiche Komponenten außer den Punkten: gleiche Konfigurationen, keine fehlende (außer entfernte und ersetzte), keine fremde
    (außer neue), Datei, referenzierte Konfiguration, fixiert, unterdrückt usw. unverändert, das Protokoll deckt sich mit den Punkten.
    Eine ersetzte Komponente darf Datei und referenzierte Konfiguration wechseln."""
    fehlen = sorted({x for x in c.v_komp if x not in c.n_komp and not c.darf_fehlen(x)}
                    | {n for n in c.erwartet_neu if n not in c.n_komp})
    fremd = sorted(x for x in c.n_komp if x not in c.v_komp and not c.ist_neu(x))
    abweichungen, unlesbar = [], list(c.konfig_unlesbar)
    for x, y in c.paare():
        a, b = c.v_komp[x], c.n_komp[y]
        name = x if x == y else f"{x} → {y}"
        for feld in KOMPONENTE_FELDER if x == y else ():
            va, vb = a.get(feld), b.get(feld)
            if va is None or vb is None:
                unlesbar.append(f"{name}: {feld}")
            elif (datei_schluessel(va) != datei_schluessel(vb)) if feld == "datei" else va != vb:
                abweichungen.append({"komponente": name, "feld": feld, "vorher": va, "nachher": vb})
        for feld, anzeige in KOMPONENTE_JE_KONFIGURATION[:2] if x != y else KOMPONENTE_JE_KONFIGURATION:
            for k in c.konfigs:
                va, vb = _je(a.get(feld), k), _je(b.get(feld), k)
                if va is None or vb is None:
                    unlesbar.append(f"{name}: {anzeige} ({k})")
                elif va != vb:
                    abweichungen.append({"komponente": name, "feld": anzeige, "konfiguration": k, "vorher": va, "nachher": vb})
    teile = [q["meldung"] for q in c.konfig_befunde + c.protokoll_befunde]
    if fehlen:
        teile.append("fehlen: " + _komma(fehlen))
    if fremd:
        teile.append("neu ohne Punkt: " + _komma(fremd))
    if abweichungen:
        teile.append("verändert: " + ", ".join(f"{q['komponente']} ({_wo(q)}: {q['vorher']} → {q['nachher']})" for q in abweichungen))
    return _ergebnis("komponenten", fehlen + fremd + abweichungen + c.konfig_befunde + c.protokoll_befunde, unlesbar,
                     ["Komponenten außerhalb der Punkte verändert; " + "; ".join(teile)] if teile else [],
                     ist=abweichungen, fehlen=fehlen, fremd=fremd, konfigurationen=c.konfig_befunde, protokoll=c.protokoll_befunde,
                     knoten=[])


def _lage(c: _Lauf) -> dict:
    """Nicht betroffene Komponenten haben dieselbe Transformation in jeder Konfiguration (Maßstab `ist_bewegt`), Kinder einer
    freien oder ersetzten Unterbaugruppe dieselbe Lage relativ zu ihr. In beiden Ständen unterdrückt zählt nicht; aktiv ohne gelesene
    Transformation ist nicht nachgewiesen."""
    abweichungen, unlesbar = [], list(c.konfig_offen)

    def vergleiche(name: str, a: dict, b: dict, k: str, ahne: tuple[dict, dict, str] | None) -> None:
        if _je(a.get("unterdrueckt"), k) is True and _je(b.get("unterdrueckt"), k) is True:
            return
        t0, t1 = _je(a.get("transform"), k), _je(b.get("transform"), k)
        if ahne is None:
            if t0 is None or t1 is None:
                unlesbar.append(f"{name} ({k})")
            elif ist_bewegt(t0, t1):
                abweichungen.append({"komponente": name, "konfiguration": k, "vorher": t0, "nachher": t1})
            return
        a0, a1 = _je(ahne[0].get("transform"), k), _je(ahne[1].get("transform"), k)
        if None in (t0, t1, a0, a1):
            unlesbar.append(f"{name} ({k}): Lage relativ zu {ahne[2]}")
        elif _relativ_bewegt(a0, t0, a1, t1):
            abweichungen.append({"komponente": name, "konfiguration": k, "vorher": t0, "nachher": t1, "relativ_zu": ahne[2]})

    for x, y in c.paare():
        if x in c.lage_frei or y in c.lage_frei:
            continue
        name = x if x == y else f"{x} → {y}"
        ahne = c.freier_ahne(x) if x == y else None
        if ahne is not None and (ahne not in c.v_komp or ahne not in c.n_komp):
            unlesbar.append(f"{name}: Ahne {ahne} nicht gelesen")
            continue
        for k in c.konfigs:
            vergleiche(name, c.v_komp[x], c.n_komp[y], k, None if ahne is None else (c.v_komp[ahne], c.n_komp[ahne], ahne))
    for x, y, ax, ay in c.ersetzte_kinder():
        if x in c.lage_frei or y in c.lage_frei:
            continue
        for k in c.konfigs:
            vergleiche(f"{x} → {y}", c.v_komp[x], c.n_komp[y], k, (c.v_komp[ax], c.n_komp[ay], f"{ax} → {ay}"))
    beschreibung = ", ".join(
        f"{q['komponente']} ({q['konfiguration']}: {_lage_text(q['vorher'], q['nachher'])}"
        + (f", relativ zu {q['relativ_zu']}" if "relativ_zu" in q else "") + ")" for q in abweichungen)
    teile = ["Lage ohne Punkt verändert: " + beschreibung] if abweichungen else []
    return _ergebnis("lage", abweichungen, unlesbar, teile, ist=abweichungen, knoten=[])


def _bestimmtheit(c: _Lauf) -> dict:
    """Der Status je Komponente und Konfiguration steigt höchstens (`SKIZZE_RANG`); Partner einer Verknüpfung, die ein Punkt löscht,
    dürfen bis unterbestimmt sinken. Neue Komponenten müssen voll bestimmt sein (Grenze-Partner auch unterbestimmt)."""
    frei = {p for n in c.geloeschte_mates if n in c.v_mate for p in c.v_mate[n].get("partner") or []}
    schlechter, probleme, unlesbar = [], [], list(c.konfig_offen)
    for x, y in c.paare():
        a, b = c.v_komp[x], c.n_komp[y]
        name = x if x == y else f"{x} → {y}"
        for k in c.konfigs:
            if _je(a.get("unterdrueckt"), k) is True and _je(b.get("unterdrueckt"), k) is True:
                continue
            s0, s1 = _je(a.get("status"), k), _je(b.get("status"), k)
            if s0 is None or s1 is None:
                unlesbar.append(f"{name} ({k}): Status")
            elif _rang(s1) < _rang(s0) and not ((x in frei or y in frei) and _rang(s1) >= _rang(UNTERBESTIMMT)):
                schlechter.append({"komponente": name, "konfiguration": k, "vorher": s0, "nachher": s1})
    for name in sorted(c.reine_neue):
        m, u = c.status_neu(name)
        probleme += m
        unlesbar += u
    teile = []
    if schlechter:
        teile.append("schlechter bestimmt als im Bestand: "
                     + ", ".join(f"{q['komponente']} ({q['konfiguration']}: {q['vorher']} → {q['nachher']})" for q in schlechter))
    if probleme:
        teile.append("neue Komponenten nicht voll bestimmt: " + "; ".join(probleme))
    return _ergebnis("bestimmtheit", schlechter + probleme, unlesbar, teile, ist=schlechter, neue_nicht_voll=probleme, knoten=[])


# ------------------------------------------------------------------------------------------------------- Verknüpfungen

def _verknuepfungen(c: _Lauf) -> dict:
    """Gleiche Verknüpfungen und Werte außer den Punkten, keine neuen Fehler. Fehlende nur, wenn ein Punkt sie nimmt; neue nur, wenn ein
    `verknuepfung_neu`-Punkt sie beansprucht. Typ, Ausrichtung, Grenze, Partner (mit ersetzten Namen), Unterdrückung, Wert und
    Grenzen (je Konfiguration) ändern sich nur, wo ein `verknuepfung_wert`-Punkt es nennt. Ein nicht gelesenes Feld ist nie gleich."""
    probleme, unlesbar, bekannt = [], list(c.konfig_offen), []
    for name, a in c.v_mate.items():
        b = c.n_mate.get(name)
        if b is None:
            if name not in c.geloeschte_mates:
                probleme.append({"art": "fehlt", "verknuepfung": name})
            continue
        for feld in MATE_FELDER:
            va, vb = a.get(feld), b.get(feld)
            if va is None or vb is None:
                unlesbar.append(f"{name}: {feld}")
            elif va != vb:
                probleme.append({"art": "geaendert", "verknuepfung": name, "feld": feld, "vorher": va, "nachher": vb})
        pa, pb = c.partner_vorher(name), b.get("partner")
        if pa is None or pb is None:
            unlesbar.append(f"{name}: partner")
        elif pa != tuple(sorted(pb, key=_partner_schluessel)):
            probleme.append({"art": "geaendert", "verknuepfung": name, "feld": "partner", "vorher": list(pa),
                             "nachher": sorted(pb, key=_partner_schluessel)})
        for feld in MATE_WERTE:
            for k in c.konfigs:
                if k in c.wert_frei.get((name, feld), ()):
                    continue
                (ga, va), (gb, vb) = _wert_gelesen(a, k, feld), _wert_gelesen(b, k, feld)
                if not (ga and gb):
                    unlesbar.append(f"{name} ({k}): {feld}")
                elif not _wert_gleich(va, vb):
                    probleme.append({"art": "geaendert", "verknuepfung": name, "feld": feld, "konfiguration": k, "vorher": va,
                                     "nachher": vb})
        for k in c.konfigs:
            u0, u1 = _je(a.get("unterdrueckt"), k), _je(b.get("unterdrueckt"), k)
            if u0 is None or u1 is None:
                unlesbar.append(f"{name} ({k}): Unterdrückung")
            elif u0 != u1:
                probleme.append({"art": "unterdrueckung", "verknuepfung": name, "konfiguration": k, "vorher": u0, "nachher": u1})
    for name in c.mates_frei:
        probleme.append({"art": "zusaetzlich", "verknuepfung": name})
    for name, m in c.n_mate.items():
        for k in c.konfigs:
            code = _je(m.get("fehler"), k)
            if code is None:
                unlesbar.append(f"{name} ({k}): Fehlercode")
            elif code != 0:
                if (name, k, code) in c.bekannte_fehler:
                    bekannt.append({"verknuepfung": name, "konfiguration": k, "code": code})
                else:
                    probleme.append({"art": "fehler", "verknuepfung": name, "konfiguration": k, "code": code})
    teile = []
    for q in probleme:
        n, wo = q["verknuepfung"], f" ({q['konfiguration']})" if "konfiguration" in q else ""
        teile.append({"fehlt": f"{n} fehlt", "zusaetzlich": f"{n} ist neu und gehört zu keinem Punkt",
                      "geaendert": f"{n}{wo}: {q.get('feld')} {q.get('vorher')} → {q.get('nachher')}",
                      "unterdrueckung": f"{n}{wo}: Unterdrückung {q.get('vorher')} → {q.get('nachher')}",
                      "fehler": f"{n}{wo}: neuer Fehler {q.get('code')}"}[q["art"]])
    return _ergebnis("verknuepfungen", probleme, unlesbar,
                     ["Verknüpfungen außerhalb der Punkte verändert: " + "; ".join(teile)] if teile else [],
                     ist=probleme, bekannt=bekannt, knoten=[])


# ---------------------------------------------------------------------------------------------------------------- Kollision

def _paar(namen) -> tuple[str, str]:
    return tuple(sorted(namen))


def _erlaubte_paare(c: _Lauf) -> set[tuple[str, str]]:
    """Die Paare aus `kollision_erlaubt`; eine Punkt-ID steht für die Komponenten, die der Lauf erzeugt hat."""
    erlaubt = set()
    for e in c.spec.get("kollision_erlaubt", []):
        a, b = e["paar"]
        erlaubt |= {_paar((x, y)) for x, y in product(c.namen(a), c.namen(b))}
    return erlaubt


def _summen(kollisionen: list[dict], abbild=lambda n: n) -> tuple[dict[tuple, float], set[tuple]]:
    """Das Volumen je Paar, über alle Einträge des Paars summiert (wie `swki.baugruppe.bewertung._ist_volumen`); ein Paar mit
    einem nicht gelesenen Volumen steht zusätzlich in der Menge der unlesbaren."""
    summe: dict[tuple, float] = {}
    unlesbar: set[tuple] = set()
    for e in kollisionen:
        paar = _paar(abbild(x) for x in e["paar"])
        summe[paar] = summe.get(paar, 0.0) + (e["volumen"] or 0.0)
        if e["volumen"] is None:
            unlesbar.add(paar)
    return summe, unlesbar


def _kollision(c: _Lauf) -> dict:
    """Keine neue statische Kollision (in der aktiven Konfiguration): ein Paar, das der Bestand nicht hatte, oder eine größere
    Summe je Paar (Toleranz 1 % bzw. 0,01 mm³), außer `kollision_erlaubt` nennt das Paar. Alte Kollisionen stehen in `bekannt`, erlaubte
    in `erlaubt`, weggefallene in `weggefallen` (ändert `ok` nicht: ein Paar kann rechtmäßig wegfallen)."""
    aktiv = c.nachher.get("aktiv")
    uebrige = sorted({*(c.vorher.get("konfigurationen") or []), *(c.nachher.get("konfigurationen") or [])} - {aktiv})
    warnung = [f"Kollisionen nur in der aktiven Konfiguration {aktiv} geprüft; nicht geprüft: {_komma(uebrige)}"] if uebrige else []
    vor, nach = c.vorher.get("kollisionen"), c.nachher.get("kollisionen")
    if vor is None or nach is None:
        return eintrag("kollision", None, ist=[], bekannt=[], erlaubt=[], weggefallen=[], konfiguration=aktiv, knoten=[],
                       hinweis="; ".join(["Kollisionen nicht gelesen, nicht nachgewiesen", *warnung]))
    alt, alt_unlesbar = _summen(vor, c.abbild)
    jetzt, jetzt_unlesbar = _summen(nach)
    erlaubt_paare = _erlaubte_paare(c)
    neu, bekannt, erlaubt, unlesbar = [], [], [], []
    for paar, volumen in jetzt.items():
        eintrag_ = {"paar": list(paar), "volumen": round(volumen, 6)}
        if paar in erlaubt_paare:
            erlaubt.append(eintrag_)
        elif paar not in alt:
            neu.append({**eintrag_, "art": "neu"})
        elif paar in alt_unlesbar or paar in jetzt_unlesbar:
            unlesbar.append(" / ".join(paar))
        elif volumen > alt[paar] + max(TOL_KOLLISION_MM3, TOL_KOLLISION_REL * alt[paar]):
            neu.append({**eintrag_, "art": "groesser", "vorher": round(alt[paar], 6)})
        else:
            bekannt.append(eintrag_)
    weggefallen = [{"paar": list(p), "volumen": None if p in alt_unlesbar else round(v, 6)} for p, v in alt.items() if p not in jetzt]
    teile = ["Neue Kollisionen: " + ", ".join(f"{' / '.join(q['paar'])} ({q['volumen']} mm³)" for q in neu)] if neu else []
    return _ergebnis("kollision", neu, unlesbar, teile + warnung, ist=neu, bekannt=bekannt, erlaubt=erlaubt, weggefallen=weggefallen,
                     konfiguration=aktiv, knoten=[])


# --------------------------------------------------------------------------------------------------------------- Punkte

def _konfiguration_befunde(c: _Lauf, name: str, k: dict, soll_je: dict[str, str | None]) -> tuple[list[str], list[str]]:
    """(Mängel, nicht lesbar): die referenzierte Konfiguration der Komponente in jeder gemeinsamen Konfiguration gegen `soll_je`."""
    probleme, unlesbar = [], []
    for konfig in c.konfigs:
        soll = soll_je.get(konfig)
        if soll is None:
            continue
        ist = _je(k.get("konfigurationen"), konfig)
        if ist is None:
            unlesbar.append(f"{name} ({konfig}): referenzierte Konfiguration")
        elif ist != soll:
            probleme.append(f"{name} steht in {konfig} in der Konfiguration {ist!r} statt {soll!r}")
    return probleme, unlesbar


def _punkt_komponente_neu(p: dict, c: _Lauf) -> dict:
    pid = f"punkt:{p['id']}"
    namen = c.neue.get(p["id"], [])
    probleme, unlesbar = ([] if namen else ["das Protokoll nennt keine gültige neue Komponente"]), []
    soll_fixiert = p.get("fixiert", False)  # ohne Angabe darf sie nicht fixiert sein
    for name in namen:
        k = c.n_komp.get(name)
        if k is None:
            probleme.append(f"{name} fehlt nach der Änderung")
            continue
        datei = k.get("datei")
        if datei is None:
            unlesbar.append(f"{name}: Datei nicht lesbar")
        elif "wie" in p:
            vorlage = c.v_komp.get(p["wie"], {})
            if vorlage.get("datei") is None:
                unlesbar.append(f"{p['wie']}: Datei nicht lesbar")
            elif datei_schluessel(datei) != datei_schluessel(vorlage["datei"]):
                probleme.append(f"{name} hat die Datei {datei!r} statt {vorlage['datei']!r} von {p['wie']}")
        elif datei_schluessel(datei) not in c.neue_dateien:
            probleme.append(f"{name}: Die Datei {datei!r} gehört nicht zu den neuen Dateien des Baus")
        if "konfiguration" in p:
            soll = {konfig: p["konfiguration"] for konfig in c.konfigs}
        elif "wie" in p:
            vorlage = c.v_komp.get(p["wie"], {})
            soll = {konfig: _je(vorlage.get("konfigurationen"), konfig) for konfig in c.konfigs}
            unlesbar += [f"{p['wie']} ({konfig}): referenzierte Konfiguration" for konfig, w in soll.items() if w is None]
        else:
            soll = {}
        m, u = _konfiguration_befunde(c, name, k, soll)
        probleme += m
        unlesbar += u
        for konfig in c.konfigs:
            fixiert = _je(k.get("fixiert"), konfig)
            if fixiert is None:
                unlesbar.append(f"{name} ({konfig}): fixiert")
            elif fixiert != soll_fixiert:
                probleme.append(f"{name} ist in {konfig} {'' if fixiert else 'nicht '}fixiert, der Punkt verlangt "
                                f"{'' if soll_fixiert else 'nicht '}fixiert")
            if _je(k.get("unterdrueckt"), konfig) is True:
                probleme.append(f"{name} ist unterdrückt ({konfig})")
        m, u = c.status_neu(name)
        probleme += m
        unlesbar += u
    m, u = c.neue_fehler_an(komponenten=set(namen))
    probleme += m
    unlesbar += u
    return _ergebnis(pid, probleme, unlesbar, ["; ".join(probleme)] if probleme else [], ist=namen, knoten=[p["id"]])


def _punkt_komponente_entfernen(p: dict, c: _Lauf) -> dict:
    pid, name = f"punkt:{p['id']}", p["komponente"]
    probleme = []
    if noch_da := sorted(n for n in c.n_komp if name in _ahnen(n)):
        probleme.append(f"{_komma(noch_da)} ist noch da")
    if mates := sorted(n for n in p["verknuepfungen"] if n in c.n_mate):
        probleme.append(f"Verknüpfung {_komma(mates)} ist noch da")
    return _ergebnis(pid, probleme, [], ["; ".join(probleme)] if probleme else [], ist=sorted(noch_da), knoten=[p["id"]])


def _punkt_komponente_ersetzen(p: dict, c: _Lauf) -> dict:
    pid = f"punkt:{p['id']}"
    ziele, unlesbar, probleme, ersatz = c.ziele[p["id"]], list(c.ziele_unlesbar[p["id"]]), [], []
    for alt in ziele:
        neu = c.ersetzt.get(alt)
        if neu is None:
            probleme.append(f"{alt} ist nicht ersetzt (das Protokoll kennt keine neue Komponente)")
            continue
        ersatz.append(neu)
        k = c.n_komp.get(neu)
        if k is None:
            probleme.append(f"{neu} (ersetzt {alt}) fehlt nach der Änderung")
            continue
        if alt in c.n_komp:
            probleme.append(f"{alt} ist noch da")
        alte, neue_datei = c.v_komp.get(alt, {}).get("datei"), k.get("datei")
        if alte is None:
            unlesbar.append(f"{alt}: Datei nicht lesbar")
        if neue_datei is None:
            unlesbar.append(f"{neu}: Datei nicht lesbar")
        elif alte is not None and datei_schluessel(neue_datei) == datei_schluessel(alte):
            probleme.append(f"{neu} hat noch die Datei von {alt}")
        elif datei_schluessel(neue_datei) not in c.neue_dateien:
            probleme.append(f"{neu}: Die Datei {neue_datei!r} gehört nicht zu den neuen Dateien des Baus")
        if "konfiguration" in p:
            m, u = _konfiguration_befunde(c, neu, k, {konfig: p["konfiguration"] for konfig in c.konfigs})
            probleme += m
            unlesbar += u
    m, u = c.neue_fehler_an(komponenten=set(ersatz))
    return _ergebnis(pid, probleme + m, unlesbar + u, ["; ".join(probleme + m)] if probleme + m else [], ist=ersatz, soll=ziele,
                     knoten=[p["id"]])


def _punkt_verknuepfung_neu(p: dict, c: _Lauf) -> dict:
    pid, soll = f"punkt:{p['id']}", soll_werte(p, c.parameter)
    probleme, unlesbar, gewaehlt = [], [], c.zuordnung[p["id"]]
    for i, (typ, name) in enumerate(zip(MATE_TYPEN[p["art"]], gewaehlt)):
        if name is None:
            a, b = p["a"]["komponente"], p["b"]["komponente"]
            probleme.append(f"keine neue Verknüpfung (swMateType {typ}) zwischen {a} und {b}")
            continue
        m = c.n_mate[name]
        if i == 0:
            mangel, nicht_lesbar = c.wert_befunde(name, soll)
            probleme += mangel
            unlesbar += nicht_lesbar
        if (soll_a := soll_ausrichtung(p, i)) is not None:
            if m.get("ausrichtung") is None:
                unlesbar.append(f"{name}: Ausrichtung")
            elif m["ausrichtung"] != soll_a:
                probleme.append(f"{name}: Ausrichtung {m['ausrichtung']} statt {soll_a}")
        for k in c.konfigs:
            if (u := _je(m.get("unterdrueckt"), k)) is None:
                unlesbar.append(f"{name} ({k}): Unterdrückung")
            elif u:
                probleme.append(f"{name} ist unterdrückt ({k})")
    belegt = {n for n in gewaehlt if n}
    f, u = c.neue_fehler_an(namen=belegt)
    return _ergebnis(pid, probleme + f, unlesbar + u, ["; ".join(probleme + f)] if probleme + f else [], ist=sorted(belegt),
                     soll=soll, knoten=[p["id"]])


def _punkt_verknuepfung_wert(p: dict, c: _Lauf) -> dict:
    pid, name = f"punkt:{p['id']}", p["verknuepfung"]
    if name not in c.n_mate:
        return eintrag(pid, False, soll=None, hinweis=f"Verknüpfung {name} fehlt nach der Änderung", knoten=[p["id"]])
    feld = p.get("grenze") or "wert"
    soll = float(auswerten(p["neu"], c.parameter))
    gewaehlt, nicht_verglichen = c.gewaehlt(p)
    probleme, unlesbar = c.wert_befunde(name, {feld: soll}, gewaehlt)
    unlesbar += [f"Konfiguration {k} nicht verglichen" for k in nicht_verglichen]
    for k in c.konfigs:  # was kein Punkt (dieser oder ein anderer) in dieser Konfiguration nennt, bleibt wie beim Kollegen
        for f in MATE_WERTE:
            if (k in gewaehlt and f == feld) or k in c.wert_frei.get((name, f), ()):
                continue
            (ga, va), (gb, vb) = _wert_gelesen(c.v_mate[name], k, f), _wert_gelesen(c.n_mate[name], k, f)
            if not (ga and gb):
                unlesbar.append(f"{name} ({k}): {f}")
            elif not _wert_gleich(va, vb):
                probleme.append(f"{name} ({k}): {f} steht auf {vb} statt {va}, kein Punkt nennt es in dieser Konfiguration")
    f, u = c.neue_fehler_an(namen={name})
    return _ergebnis(pid, probleme + f, unlesbar + u, ["; ".join(probleme + f)] if probleme + f else [], soll=soll, knoten=[p["id"]])


def _punkt_verknuepfung_loeschen(p: dict, c: _Lauf) -> dict:
    pid, name = f"punkt:{p['id']}", p["verknuepfung"]
    if name in c.n_mate:
        return eintrag(pid, False, ist=name, soll=None, knoten=[p["id"]], hinweis=f"Verknüpfung {name} ist noch da")
    return eintrag(pid, True, ist=None, soll=None, knoten=[p["id"]])


_PUNKT = {"komponente_neu": _punkt_komponente_neu, "komponente_entfernen": _punkt_komponente_entfernen,
          "komponente_ersetzen": _punkt_komponente_ersetzen, "verknuepfung_neu": _punkt_verknuepfung_neu,
          "verknuepfung_wert": _punkt_verknuepfung_wert, "verknuepfung_loeschen": _punkt_verknuepfung_loeschen}


def vergleiche_baugruppe(spec: dict, vorher: dict, nachher: dict, neue: dict[str, list[str]], ersetzt: dict[str, str],
                         neue_dateien: Iterable[str] = ()) -> list[dict]:
    """§8.3: Einträge `komponenten`, `verknuepfungen`, `bestimmtheit`, `kollision`, `lage`, dann `punkt:<id>` je Baugruppen-Punkt.
    `vorher` und `nachher` sind Baugruppen-Aufnahmen (`bestand.json`, der Lauf nach dem Neuaufbau). Aus dem Protokoll: `neue` (Punkt-ID
    → SolidWorks-Namen der neuen Komponenten), `ersetzt` (alter → neuer Name; bei `alle_instanzen` mehrere), `neue_dateien` (relative
    Pfade der Dateien, die der Bau angelegt hat; die Datei einer Komponente aus einer `quelle` muss dazugehören)."""
    c = _Lauf(spec, vorher, nachher, neue, ersetzt, neue_dateien)
    allgemein = [_komponenten(c), _verknuepfungen(c), _bestimmtheit(c), _kollision(c), _lage(c)]
    punkte = [_PUNKT[p["typ"]](p, c) for p in c.punkte]
    if not c.konfigs:  # ohne gemeinsame Konfiguration hat kein Punkt etwas belegt
        for e in punkte:
            if e["ok"] is True:
                e["ok"], e["hinweis"] = None, "Keine gemeinsame Konfiguration gelesen, nicht nachgewiesen"
    return allgemein + punkte


# ---------------------------------------------------------------------------------------------------------------- Dateien

def vergleiche_dateien(spec: dict, bestand: dict, ist: dict[str, str | None],
                       neue_dateien: list[str] | tuple[str, ...] = ()) -> dict:
    """`dateien`: SHA-256 jeder Datei wie in der Bestandskopie, außer Dateien mit Punkten (`in_datei`) und neuen Dateien. `bestand` ist
    `dateien.json` der Aufnahme einschließlich der Hauptdatei (`haupt: true`), `ist` relativer Pfad → SHA-256 im Lauf (`None`: nicht
    gelesen), `neue_dateien` die Pfade, die der Bau angelegt hat. Verlangt ist eine Änderung an Dateien mit Punkten und an der
    Hauptbaugruppe, wenn ein Punkt sie ändert (`aenderung_an_haupt`, auch durch `lage_folgen`: der Bau speichert sie dann immer, eine
    gleiche SHA-256 heißt Speichern gescheitert). Neue Dateien nur, wenn ein Punkt eine Datei bringt (`komponente_neu` mit `quelle`,
    `komponente_ersetzen`). Eine nicht gelesene SHA-256, auch im Bestand, ist nie gleich."""
    s = datei_schluessel
    alt = {s(rel): (rel, d.get("sha256")) for rel, d in bestand.items()}
    lauf = {s(rel): (rel, sha) for rel, sha in ist.items()}
    haupt = next((s(rel) for rel, d in bestand.items() if d.get("haupt")), None)
    neu = {s(rel): rel for rel in neue_dateien}
    verlangt = {s(d): d for d in dateien_mit_punkten(spec)}
    unlesbar, probleme = [], []
    if aenderung_an_haupt(spec):
        if haupt is None:
            unlesbar.append("die Hauptdatei ist in dateien.json nicht gekennzeichnet")
        else:
            verlangt[haupt] = alt[haupt][0]
    bringt_datei = any(p["typ"] == "komponente_ersetzen" or (p["typ"] == "komponente_neu" and "quelle" in p) for p in spec["punkte"])
    for schl, (rel, sha) in alt.items():
        if schl not in lauf:
            probleme.append({"art": "fehlt", "datei": rel})
            continue
        gelaufen = lauf[schl][1]
        if gelaufen is None or sha is None:
            unlesbar.append(f"{rel}: SHA-256")
        elif gelaufen.lower() == str(sha).lower():
            if schl in verlangt:
                probleme.append({"art": "ungespeichert", "datei": rel})
        elif schl not in verlangt:
            probleme.append({"art": "geaendert", "datei": rel})
    for schl, rel in verlangt.items():
        if schl not in alt:
            probleme.append({"art": "unbekannt", "datei": rel})
    for schl, (rel, sha) in lauf.items():
        if schl in alt:
            continue
        if schl not in neu:
            probleme.append({"art": "fremd", "datei": rel})
        elif sha is None:
            unlesbar.append(f"{rel}: SHA-256")
    for schl, rel in neu.items():
        if schl in alt:
            probleme.append({"art": "neu_im_bestand", "datei": rel})
        elif schl not in lauf:
            probleme.append({"art": "neu_fehlt", "datei": rel})
        elif not bringt_datei:
            probleme.append({"art": "neu_ohne_punkt", "datei": rel})
    text = {"fehlt": "fehlt im Lauf", "geaendert": "verändert, ohne dass ein Punkt sie nennt",
            "ungespeichert": "unverändert, obwohl ein Punkt sie ändern sollte (nichts gespeichert)",
            "unbekannt": "nicht in der Bestandskopie", "fremd": "neu, ohne dass der Bau sie anlegen sollte",
            "neu_im_bestand": "soll neu sein, gibt es aber schon im Bestand", "neu_fehlt": "neu angelegt, aber nicht im Lauf",
            "neu_ohne_punkt": "neu angelegt, aber kein Punkt bringt eine Datei (komponente_neu mit quelle, komponente_ersetzen)"}
    teile = [f"{q['datei']} {text[q['art']]}" for q in probleme]
    geaendert = sorted(rel for schl, (rel, sha) in alt.items()
                       if schl in lauf and None not in (lauf[schl][1], sha) and lauf[schl][1] != sha)
    return _ergebnis("dateien", probleme, unlesbar, ["Dateien: " + "; ".join(teile)] if teile else [], ist=probleme,
                     erwartet_geaendert=sorted(verlangt.values()), geaendert=geaendert, neu=sorted(neu.values()), knoten=[])


# Öffentliche Namen für `swki.bestand.bewegung_bestand`: derselbe Stand des Protokolls und dieselben erlaubten Paare, keine zweite Logik
Vergleichsstand = _Lauf
erlaubte_paare = _erlaubte_paare
