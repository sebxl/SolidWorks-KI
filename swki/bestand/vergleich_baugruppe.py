"""Vergleich der Baugruppe vorher/nachher (Spec Bestandsdateien §8.3, Plan Etappe 2 Task 5): der Präzisionsschutz der Baugruppe.

Reine Logik über zwei Baugruppen-Aufnahmen im Format `bestand.json` (Bestandskopie und Lauf nach dem Neuaufbau), ohne SolidWorks.
Die Einträge haben das Format `swki.pruefung.bewertung.eintrag`; `ok: False` ist ein Mangel, `ok: None` heißt „nicht
nachgewiesen" (kein Mangel, aber auch kein Bestanden), ein Mangel hat Vorrang. Grundsatz wie in `swki.bestand.vergleich`: Ein
Fehlalarm kostet eine Rückfrage, ein falsches `ok: True` die Datei des Kollegen.

`vergleiche_baugruppe`: `komponenten`, `verknuepfungen`, `bestimmtheit`, `kollision`, `lage`, dann `punkt:<id>` je Baugruppen-Punkt
(die Teil-Punkte laufen als Scheiben durch Etappe 1). `vergleiche_dateien`: Eintrag `dateien`. Aus dem Protokoll des Baus kommen
`neue` (Punkt-ID → SolidWorks-Namen der neuen Komponenten) und `ersetzt` (alter → neuer Name).

Regeln, die der Vergleich festlegt:
- `None` als Wert heißt: Lesen gescheitert, nie „keine Änderung". Ausnahme: `wert`, `min`, `max` einer Verknüpfung (None heißt dort
  „trägt keinen Wert") und `transform` einer in beiden Ständen unterdrückten Komponente (sie zählt nicht).
- Komponenten tragen alle Ebenen (`Sub-1/Teil-1`); sie werden je Konfiguration verglichen, die beide Aufnahmen haben. Gibt es keine
  gemeinsame, ist nichts nachgewiesen.
- Die Lage darf sich ändern bei neuen Komponenten, Zielen von `komponente_entfernen` und den Komponenten in `lage_folgen` aller Punkte,
  jeweils samt ihren Kindern in einer Unterbaugruppe. Eine ersetzte Komponente behält ihre Lage, außer `lage_folgen` nennt sie (alt oder
  neu); ihre Datei und Konfiguration dürfen abweichen. Kinder einer ersetzten Unterbaugruppe vergleicht der Vergleich nicht einzeln.
- Neue Verknüpfungen kennt das Protokoll nicht beim Namen: Jeder `verknuepfung_neu`-Punkt beansprucht je erwartetem Typ die Verknüpfung
  mit seinen Partnern (die mit passendem Wert zuerst, eine Verknüpfung gehört einem Punkt); übrig bleibende neue sind ein Mangel.
- Der Status (swConstrainedStatus_e) darf steigen, nie sinken (Rang wie `SKIZZE_RANG`); Partner einer von einem Punkt gelöschten
  Verknüpfung dürfen sinken. Eine neue Komponente muss voll bestimmt sein, als Partner einer Grenzverknüpfung auch unterbestimmt.
- Verknüpfungsfehler: ein Tripel (Verknüpfung, Konfiguration, Code), das der Bestand nicht kennt, ist ein Mangel; Bekanntes steht in
  `bekannt`. Kollisionen: ein Paar, das der Bestand nicht kennt, oder ein bekanntes mit mehr Volumen (Toleranz 1 % bzw. 0,01 mm³)
  ist ein Mangel, außer `kollision_erlaubt` nennt das Paar.
"""

from dataclasses import dataclass, field
from itertools import product

from swki.baugruppe.bewegung import ist_bewegt, verschiebung_mm
from swki.bestand.scheiben import aenderung_an_haupt, datei_schluessel, dateien_mit_punkten, haupt_punkte
from swki.bestand.vergleich import SKIZZE_RANG, TOL
from swki.pruefung.bewertung import eintrag
from swki.spec.ausdruck import auswerten

TOL_KOLLISION_REL = 0.01  # 1 % des Volumens im Bestand
TOL_KOLLISION_MM3 = 0.01
VOLL_BESTIMMT, UNTERBESTIMMT = 3, 2  # swConstrainedStatus_e

# Welche swMateType_e eine neue Verknüpfung der Art `art` in SolidWorks ergibt (`swki.baugruppe.sw_baugruppe.MATE_TYP`, `MATE_KOPPLUNG`,
# `aufloesen._einzeln`): ein Typ je Eintrag der Liste; ein Scharnier ist konzentrisch plus deckungsgleich der Anlageflächen
MATE_TYPEN = {"deckungsgleich": [0], "konzentrisch": [1], "senkrecht": [2], "parallel": [3], "abstand": [5], "winkel": [6],
              "grenze_abstand": [5], "grenze_winkel": [6], "scharnier": [1, 0], "zahnrad": [10], "zahnstange": [13]}
PUNKT_TYPEN = ("komponente_neu", "komponente_entfernen", "komponente_ersetzen", "verknuepfung_neu", "verknuepfung_wert",
               "verknuepfung_loeschen")
KOMPONENTE_FELDER = ("datei", "konfiguration", "virtuell", "muster", "loesen")  # je Komponente
KOMPONENTE_JE_KONFIGURATION = ("fixiert", "unterdrueckt")


def _gleich(a: float, b: float) -> bool:
    return abs(a - b) <= TOL + 1e-12


def _rang(status) -> int:
    return SKIZZE_RANG.get(status, -1)


def _ahnen(name: str) -> list[str]:
    """Die Komponente selbst und die Unterbaugruppen, in denen sie steckt (`A/B/C` → `A`, `A/B`, `A/B/C`)."""
    teile = name.split("/")
    return ["/".join(teile[:i]) for i in range(1, len(teile) + 1)]


def _je(werte, konfiguration: str):
    """Wert einer Komponente oder Verknüpfung in einer Konfiguration; `None`, wenn er nicht gelesen wurde."""
    return (werte or {}).get(konfiguration)


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


@dataclass
class _Lauf:
    spec: dict
    vorher: dict
    nachher: dict
    neue: dict[str, list[str]]
    ersetzt: dict[str, str]
    punkte: list[dict] = field(init=False)           # die Baugruppen-Punkte
    parameter: dict = field(init=False)
    konfigs: list[str] = field(init=False)           # die beide Aufnahmen gemeinsam haben, in der Reihenfolge des Bestands
    v_komp: dict = field(init=False)
    n_komp: dict = field(init=False)
    v_mate: dict = field(init=False)
    n_mate: dict = field(init=False)
    erwartet_neu: set[str] = field(init=False)       # Namen aus dem Protokoll: neue und ersetzende Komponenten
    reine_neue: set[str] = field(init=False)         # nur die neuen (ohne ersetzende)
    weg: set[str] = field(init=False)                # Komponenten, die verschwinden dürfen: entfernte und ersetzte samt Kindern
    lage_frei: set[str] = field(init=False)          # Komponenten, deren Lage sich ändern darf (samt Kindern)
    geloeschte_mates: set[str] = field(init=False)
    wert_felder: dict[str, frozenset[str]] = field(init=False)
    bekannte_fehler: set[tuple] = field(init=False)
    zuordnung: dict[str, list[str | None]] = field(init=False)  # Punkt-ID → beanspruchte neue Verknüpfung je erwartetem Typ
    mates_frei: list[str] = field(init=False)        # neue Verknüpfungen, die kein Punkt beansprucht

    def __post_init__(self):
        self.punkte = [p for p in self.spec.get("punkte", []) if p["typ"] in PUNKT_TYPEN]
        alle = self.spec.get("punkte", [])
        self.parameter = self.spec.get("parameter", {})
        self.konfigs = [k for k in self.vorher["konfigurationen"] if k in self.nachher["konfigurationen"]]
        self.v_komp, self.n_komp = self.vorher["komponenten"], self.nachher["komponenten"]
        self.v_mate, self.n_mate = self.vorher["verknuepfungen"], self.nachher["verknuepfungen"]
        self.erwartet_neu = {n for namen in self.neue.values() for n in namen} | set(self.ersetzt.values())
        self.reine_neue = {n for namen in self.neue.values() for n in namen} - set(self.ersetzt.values())
        entfernt = {p["komponente"] for p in alle if p["typ"] == "komponente_entfernen"}
        self.weg = entfernt | set(self.ersetzt)
        self.lage_frei = entfernt | self.reine_neue | {n for p in alle for n in p.get("lage_folgen", [])}
        self.geloeschte_mates = ({n for p in alle if p["typ"] == "komponente_entfernen" for n in p["verknuepfungen"]}
                                 | {p["verknuepfung"] for p in alle if p["typ"] == "verknuepfung_loeschen"})
        self.wert_felder = {}
        for p in alle:
            if p["typ"] == "verknuepfung_wert":
                felder = frozenset({"wert"} if p.get("grenze") is None else {p["grenze"], "wert"})
                self.wert_felder[p["verknuepfung"]] = self.wert_felder.get(p["verknuepfung"], frozenset()) | felder
        self.bekannte_fehler = {(n, k, code) for n, m in self.v_mate.items() for k, code in (m.get("fehler") or {}).items()
                                if code not in (0, None)}
        self._ordne_verknuepfungen()

    # ------------------------------------------------------------------------------------------------------ Namen

    def namen(self, name: str) -> list[str]:
        """Eine Punkt-ID steht für die Komponenten, die sie im Lauf erzeugt hat, ein SolidWorks-Name für sich."""
        return list(self.neue.get(name) or [name])

    def ist_neu(self, name: str) -> bool:
        return any(a in self.erwartet_neu for a in _ahnen(name))

    def darf_fehlen(self, name: str) -> bool:
        return any(a in self.weg for a in _ahnen(name))

    def lage_erlaubt(self, *namen: str) -> bool:
        return any(a in self.lage_frei for n in namen for a in _ahnen(n))

    def paare(self) -> list[tuple[str, str]]:
        """Komponenten in beiden Ständen: gleicher Name, oder (alt, neu) einer Ersetzung."""
        gleiche = [(x, x) for x in self.v_komp if x in self.n_komp and x not in self.ersetzt]
        return gleiche + [(a, b) for a, b in self.ersetzt.items() if a in self.v_komp and b in self.n_komp]

    def grenze_partner(self) -> set[str]:
        return {p for m in self.n_mate.values() if m.get("grenze") for p in m.get("partner", [])}

    def partner_vorher(self, name: str) -> tuple:
        """Partner einer Verknüpfung im Bestand, mit den Namen der ersetzenden Komponenten."""
        return tuple(sorted(self.ersetzt.get(p, p) for p in self.v_mate[name].get("partner", [])))

    # ------------------------------------------------------------------------------------------------ Verknüpfungen

    def soll_werte(self, p: dict) -> dict[str, float]:
        """Wert bzw. Grenzen einer neuen Verknüpfung, ausgewertet mit den Parametern der Spec (mm und Grad)."""
        felder = ("wert",) if p["art"] in ("abstand", "winkel") else ("min", "max") if p["art"].startswith("grenze_") else ()
        return {f: float(auswerten(p[f], self.parameter)) for f in felder if f in p}

    def wert_passt(self, soll: dict[str, float], mate: dict) -> bool:
        return all(mate.get(f) is not None and _gleich(mate[f], w) for f, w in soll.items())

    def _passt(self, name: str, typ: int, grenze: bool | None, a: list[str], b: list[str]) -> bool:
        m = self.n_mate[name]
        partner = set(m.get("partner", []))
        if m.get("typ") != typ or (grenze is not None and bool(m.get("grenze")) != grenze):
            return False
        return any(x in partner and y in partner and x != y for x, y in product(a, b))

    def _ordne_verknuepfungen(self) -> None:
        """Jeder `verknuepfung_neu`-Punkt beansprucht je erwartetem Typ eine neue Verknüpfung zwischen seinen Partnern, die mit
        passendem Wert zuerst."""
        frei = sorted(n for n in self.n_mate if n not in self.v_mate)
        self.zuordnung = {}
        for p in self.punkte:
            if p["typ"] != "verknuepfung_neu":
                continue
            soll = self.soll_werte(p)
            gewaehlt = []
            for i, typ in enumerate(MATE_TYPEN[p["art"]]):
                anlage = p["art"] == "scharnier" and i == 1
                a = self.namen((p.get("anlage_a") if anlage and "anlage_a" in p else p["a"])["komponente"])
                b = self.namen((p.get("anlage_b") if anlage and "anlage_b" in p else p["b"])["komponente"])
                grenze = p["art"].startswith("grenze_") if typ in (5, 6) else None
                kandidaten = [n for n in frei if self._passt(n, typ, grenze, a, b)]
                kandidaten.sort(key=lambda n: not (i == 0 and self.wert_passt(soll, self.n_mate[n])))
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
            if not ((namen is not None and n in namen) or (komponenten is not None and komponenten & set(m.get("partner", [])))):
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
            if _je(k.get("unterdrueckt"), konfig) is True:
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
    """Gleiche Komponenten außer den Punkten: keine fehlende (außer entfernte und ersetzte), keine fremde (außer neue), Datei,
    Konfiguration, fixiert, unterdrückt usw. unverändert. Eine ersetzte Komponente darf Datei und Konfiguration wechseln."""
    fehlen = sorted({x for x in c.v_komp if x not in c.n_komp and not c.darf_fehlen(x)}
                    | {n for n in c.erwartet_neu if n not in c.n_komp})
    fremd = sorted(x for x in c.n_komp if x not in c.v_komp and not c.ist_neu(x))
    abweichungen, unlesbar = [], []
    if not c.konfigs:
        unlesbar.append("keine gemeinsame Konfiguration")
    for x, y in c.paare():
        a, b = c.v_komp[x], c.n_komp[y]
        name = x if x == y else f"{x} → {y}"
        for feld in KOMPONENTE_FELDER if x == y else ():
            va, vb = a.get(feld), b.get(feld)
            if va is None or vb is None:
                unlesbar.append(f"{name}: {feld}")
            elif (datei_schluessel(va) != datei_schluessel(vb)) if feld == "datei" else va != vb:
                abweichungen.append({"komponente": name, "feld": feld, "vorher": va, "nachher": vb})
        for feld in KOMPONENTE_JE_KONFIGURATION:
            for k in c.konfigs:
                va, vb = _je(a.get(feld), k), _je(b.get(feld), k)
                if va is None or vb is None:
                    unlesbar.append(f"{name}: {feld} ({k})")
                elif va != vb:
                    abweichungen.append({"komponente": name, "feld": feld, "konfiguration": k, "vorher": va, "nachher": vb})
    teile = []
    if fehlen:
        teile.append("fehlen: " + _komma(fehlen))
    if fremd:
        teile.append("neu ohne Punkt: " + _komma(fremd))
    if abweichungen:
        teile.append("verändert: " + ", ".join(f"{q['komponente']} ({_wo(q)}: {q['vorher']} → {q['nachher']})" for q in abweichungen))
    return _ergebnis("komponenten", fehlen + fremd + abweichungen, unlesbar,
                     ["Komponenten außerhalb der Punkte verändert; " + "; ".join(teile)] if teile else [],
                     ist=abweichungen, fehlen=fehlen, fremd=fremd, knoten=[])


def _lage(c: _Lauf) -> dict:
    """Nicht betroffene Komponenten haben dieselbe Transformation in jeder Konfiguration (Maßstab `ist_bewegt`). In beiden
    Ständen unterdrückt zählt nicht; aktiv ohne gelesene Transformation ist nicht nachgewiesen."""
    abweichungen, unlesbar = [], []
    if not c.konfigs:
        unlesbar.append("keine gemeinsame Konfiguration")
    for x, y in c.paare():
        if c.lage_erlaubt(x, y):
            continue
        a, b = c.v_komp[x], c.n_komp[y]
        name = x if x == y else f"{x} → {y}"
        for k in c.konfigs:
            if _je(a.get("unterdrueckt"), k) is True and _je(b.get("unterdrueckt"), k) is True:
                continue
            t0, t1 = _je(a.get("transform"), k), _je(b.get("transform"), k)
            if t0 is None or t1 is None:
                unlesbar.append(f"{name} ({k})")
            elif ist_bewegt(t0, t1):
                abweichungen.append({"komponente": name, "konfiguration": k, "vorher": t0, "nachher": t1})
    beschreibung = ", ".join(f"{q['komponente']} ({q['konfiguration']}: {_lage_text(q['vorher'], q['nachher'])})" for q in abweichungen)
    teile = ["Lage ohne Punkt verändert: " + beschreibung] if abweichungen else []
    return _ergebnis("lage", abweichungen, unlesbar, teile, ist=abweichungen, knoten=[])


def _bestimmtheit(c: _Lauf) -> dict:
    """Der Status je Komponente und Konfiguration steigt höchstens (`SKIZZE_RANG`); Partner einer Verknüpfung, die ein Punkt löscht,
    sind ausgenommen. Neue Komponenten müssen voll bestimmt sein (Grenze-Partner auch unterbestimmt)."""
    frei = {p for n in c.geloeschte_mates if n in c.v_mate for p in c.v_mate[n].get("partner", [])}
    schlechter, unlesbar, probleme = [], [], []
    if not c.konfigs:
        unlesbar.append("keine gemeinsame Konfiguration")
    for x, y in c.paare():
        if x in frei or y in frei:
            continue
        a, b = c.v_komp[x], c.n_komp[y]
        name = x if x == y else f"{x} → {y}"
        for k in c.konfigs:
            if _je(a.get("unterdrueckt"), k) is True and _je(b.get("unterdrueckt"), k) is True:
                continue
            s0, s1 = _je(a.get("status"), k), _je(b.get("status"), k)
            if s0 is None or s1 is None:
                unlesbar.append(f"{name} ({k}): Status")
            elif _rang(s1) < _rang(s0):
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

def _wert_gleich(a, b) -> bool:
    """Wert, Minimum, Maximum: `None` heißt hier „trägt keinen Wert"."""
    if a is None or b is None:
        return a is None and b is None
    return _gleich(a, b)


def _verknuepfungen(c: _Lauf) -> dict:
    """Gleiche Verknüpfungen und Werte außer den Punkten, keine neuen Fehler. Fehlende nur, wenn ein Punkt sie nimmt; neue nur, wenn ein
    `verknuepfung_neu`-Punkt sie beansprucht. Typ, Ausrichtung, Grenze, Partner (mit ersetzten Namen), Unterdrückung, Wert und
    Grenzen ändern sich nur, wo ein `verknuepfung_wert`-Punkt es nennt."""
    probleme, unlesbar, bekannt = [], [], []
    for name, a in c.v_mate.items():
        b = c.n_mate.get(name)
        if b is None:
            if name not in c.geloeschte_mates:
                probleme.append({"art": "fehlt", "verknuepfung": name})
            continue
        for feld in ("typ", "ausrichtung", "grenze", "gesteuert"):
            if a.get(feld) != b.get(feld):
                probleme.append({"art": "geaendert", "verknuepfung": name, "feld": feld, "vorher": a.get(feld),
                                 "nachher": b.get(feld)})
        if c.partner_vorher(name) != tuple(sorted(b.get("partner", []))):
            probleme.append({"art": "geaendert", "verknuepfung": name, "feld": "partner", "vorher": list(c.partner_vorher(name)),
                             "nachher": sorted(b.get("partner", []))})
        for feld in ("wert", "min", "max"):
            if feld not in c.wert_felder.get(name, ()) and not _wert_gleich(a.get(feld), b.get(feld)):
                probleme.append({"art": "geaendert", "verknuepfung": name, "feld": feld, "vorher": a.get(feld),
                                 "nachher": b.get(feld)})
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
    if not c.konfigs:
        unlesbar.append("keine gemeinsame Konfiguration")
    teile = []
    for q in probleme:
        n = q["verknuepfung"]
        teile.append({"fehlt": f"{n} fehlt", "zusaetzlich": f"{n} ist neu und gehört zu keinem Punkt",
                      "geaendert": f"{n}: {q.get('feld')} {q.get('vorher')} → {q.get('nachher')}",
                      "unterdrueckung": f"{n} ({q.get('konfiguration')}): Unterdrückung {q.get('vorher')} → {q.get('nachher')}",
                      "fehler": f"{n} ({q.get('konfiguration')}): neuer Fehler {q.get('code')}"}[q["art"]])
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


def _kollision(c: _Lauf) -> dict:
    """Keine neue statische Kollision: ein Paar, das der Bestand nicht hatte, oder ein bekanntes mit größerem Volumen (Toleranz 1 %
    bzw. 0,01 mm³), außer `kollision_erlaubt` nennt das Paar. Alte Kollisionen stehen in `bekannt`, erlaubte in `erlaubt`."""
    vor, nach = c.vorher.get("kollisionen"), c.nachher.get("kollisionen")
    if vor is None or nach is None:
        return eintrag("kollision", None, ist=[], bekannt=[], erlaubt=[], knoten=[],
                       hinweis="Kollisionen nicht gelesen, nicht nachgewiesen")
    alt: dict[tuple, float | None] = {}
    for e in vor:  # die ersetzende Komponente erbt die Kollisionen der ersetzten
        paar = _paar(c.ersetzt.get(x, x) for x in e["paar"])
        alt[paar] = max(alt.get(paar) or 0.0, e["volumen"] or 0.0) if e["volumen"] is not None else alt.get(paar)
    erlaubt_paare = _erlaubte_paare(c)
    neu, bekannt, erlaubt, unlesbar = [], [], [], []
    for e in nach:
        paar, volumen = _paar(e["paar"]), e["volumen"]
        eintrag_ = {"paar": list(paar), "volumen": volumen}
        if paar in erlaubt_paare:
            erlaubt.append(eintrag_)
        elif paar not in alt:
            neu.append({**eintrag_, "art": "neu"})
        elif volumen is None or alt[paar] is None:
            unlesbar.append(" / ".join(paar))
        elif volumen > alt[paar] + max(TOL_KOLLISION_MM3, TOL_KOLLISION_REL * alt[paar]):
            neu.append({**eintrag_, "art": "groesser", "vorher": alt[paar]})
        else:
            bekannt.append(eintrag_)
    teile = ["Neue Kollisionen: " + ", ".join(f"{' / '.join(q['paar'])} ({q['volumen']} mm³)" for q in neu)] if neu else []
    return _ergebnis("kollision", neu, unlesbar, teile, ist=neu, bekannt=bekannt, erlaubt=erlaubt, knoten=[])


# --------------------------------------------------------------------------------------------------------------- Punkte

def _punkt_komponente_neu(p: dict, c: _Lauf) -> dict:
    pid = f"punkt:{p['id']}"
    namen = c.neue.get(p["id"], [])
    probleme, unlesbar = ([] if namen else ["das Protokoll nennt keine neue Komponente"]), []
    for name in namen:
        k = c.n_komp.get(name)
        if k is None:
            probleme.append(f"{name} fehlt nach der Änderung")
            continue
        if name in c.v_komp:
            probleme.append(f"{name} gab es schon im Bestand")
        if "wie" in p:
            vorlage = c.v_komp.get(p["wie"], {})
            if datei_schluessel(str(k.get("datei"))) != datei_schluessel(str(vorlage.get("datei"))):
                probleme.append(f"{name} hat die Datei {k.get('datei')!r} statt {vorlage.get('datei')!r} von {p['wie']}")
            soll_konfig = p.get("konfiguration", vorlage.get("konfiguration"))
        else:
            soll_konfig = p.get("konfiguration")
        if soll_konfig is not None and k.get("konfiguration") != soll_konfig:
            probleme.append(f"{name} steht in der Konfiguration {k.get('konfiguration')!r} statt {soll_konfig!r}")
        for konfig in c.konfigs:
            if "fixiert" in p:
                fixiert = _je(k.get("fixiert"), konfig)
                if fixiert is None:
                    unlesbar.append(f"{name} ({konfig}): fixiert")
                elif fixiert != p["fixiert"]:
                    probleme.append(f"{name} ist in {konfig} {'' if fixiert else 'nicht '}fixiert")
            if _je(k.get("unterdrueckt"), konfig) is True:
                probleme.append(f"{name} ist unterdrückt ({konfig})")
        m, u = c.status_neu(name)
        probleme += m
        unlesbar += u
    m, u = c.neue_fehler_an(komponenten=set(namen))
    probleme += m
    unlesbar += u
    return _ergebnis(pid, probleme, unlesbar, ["; ".join(probleme)] if probleme else [], ist=namen, knoten=[p["id"]])


def _instanzen(c: _Lauf, name: str) -> list[str]:
    """Alle Komponenten (jede Ebene) mit der Datei der genannten im Bestand."""
    datei = c.v_komp.get(name, {}).get("datei")
    if not datei:
        return [name]
    return sorted(n for n, k in c.v_komp.items() if k.get("datei") and datei_schluessel(k["datei"]) == datei_schluessel(datei))


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
    ziele = _instanzen(c, p["komponente"]) if p.get("alle_instanzen") else [p["komponente"]]
    probleme, unlesbar, ersatz = [], [], []
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
        if datei_schluessel(str(k.get("datei"))) == datei_schluessel(str(c.v_komp.get(alt, {}).get("datei"))):
            probleme.append(f"{neu} hat noch die Datei von {alt}")
        if "konfiguration" in p and k.get("konfiguration") != p["konfiguration"]:
            probleme.append(f"{neu} steht in der Konfiguration {k.get('konfiguration')!r} statt {p['konfiguration']!r}")
    m, u = c.neue_fehler_an(komponenten=set(ersatz))
    return _ergebnis(pid, probleme + m, unlesbar + u, ["; ".join(probleme + m)] if probleme + m else [], ist=ersatz, soll=ziele,
                     knoten=[p["id"]])


def _punkt_verknuepfung_neu(p: dict, c: _Lauf) -> dict:
    pid, soll = f"punkt:{p['id']}", c.soll_werte(p)
    probleme, unlesbar, gewaehlt = [], [], c.zuordnung[p["id"]]
    for i, (typ, name) in enumerate(zip(MATE_TYPEN[p["art"]], gewaehlt)):
        if name is None:
            a, b = p["a"]["komponente"], p["b"]["komponente"]
            probleme.append(f"keine neue Verknüpfung (swMateType {typ}) zwischen {a} und {b}")
            continue
        m = c.n_mate[name]
        if i == 0:
            for feld, w in soll.items():
                if m.get(feld) is None or not _gleich(m[feld], w):
                    probleme.append(f"{name}: {feld} steht auf {m.get(feld)} statt {w:g}")
        if any(_je(m.get("unterdrueckt"), k) is True for k in c.konfigs):
            probleme.append(f"{name} ist unterdrückt")
    belegt = {n for n in gewaehlt if n}
    f, u = c.neue_fehler_an(namen=belegt)
    return _ergebnis(pid, probleme + f, unlesbar + u, ["; ".join(probleme + f)] if probleme + f else [], ist=sorted(belegt),
                     soll=soll, knoten=[p["id"]])


def _punkt_verknuepfung_wert(p: dict, c: _Lauf) -> dict:
    pid, name = f"punkt:{p['id']}", p["verknuepfung"]
    m = c.n_mate.get(name)
    if m is None:
        return eintrag(pid, False, soll=None, hinweis=f"Verknüpfung {name} fehlt nach der Änderung", knoten=[p["id"]])
    feld = p.get("grenze") or "wert"
    soll, ist = float(auswerten(p["neu"], c.parameter)), m.get(feld)
    if ist is None or not _gleich(ist, soll):
        return eintrag(pid, False, ist=ist, soll=soll, knoten=[p["id"]], hinweis=f"{name}: {feld} steht auf {ist} statt {soll:g}")
    probleme, unlesbar = c.neue_fehler_an(namen={name})
    return _ergebnis(pid, probleme, unlesbar, ["; ".join(probleme)] if probleme else [], ist=ist, soll=soll, knoten=[p["id"]])


def _punkt_verknuepfung_loeschen(p: dict, c: _Lauf) -> dict:
    pid, name = f"punkt:{p['id']}", p["verknuepfung"]
    if name in c.n_mate:
        return eintrag(pid, False, ist=name, soll=None, knoten=[p["id"]], hinweis=f"Verknüpfung {name} ist noch da")
    return eintrag(pid, True, ist=None, soll=None, knoten=[p["id"]])


_PUNKT = {"komponente_neu": _punkt_komponente_neu, "komponente_entfernen": _punkt_komponente_entfernen,
          "komponente_ersetzen": _punkt_komponente_ersetzen, "verknuepfung_neu": _punkt_verknuepfung_neu,
          "verknuepfung_wert": _punkt_verknuepfung_wert, "verknuepfung_loeschen": _punkt_verknuepfung_loeschen}


def vergleiche_baugruppe(spec: dict, vorher: dict, nachher: dict, neue: dict[str, list[str]],
                         ersetzt: dict[str, str]) -> list[dict]:
    """§8.3: Einträge `komponenten`, `verknuepfungen`, `bestimmtheit`, `kollision`, `lage`, dann `punkt:<id>` je Baugruppen-Punkt.
    `vorher` und `nachher` sind Baugruppen-Aufnahmen (`bestand.json`, der Lauf nach dem Neuaufbau). Aus dem Protokoll: `neue` (Punkt-ID
    → SolidWorks-Namen der neuen Komponenten, bei `alle_instanzen` mehrere), `ersetzt` (alter → neuer Name)."""
    c = _Lauf(spec, vorher, nachher, neue, ersetzt)
    allgemein = [_komponenten(c), _verknuepfungen(c), _bestimmtheit(c), _kollision(c), _lage(c)]
    return allgemein + [_PUNKT[p["typ"]](p, c) for p in c.punkte]


# ---------------------------------------------------------------------------------------------------------------- Dateien

def vergleiche_dateien(spec: dict, bestand: dict, ist: dict[str, str | None],
                       neue_dateien: list[str] | tuple[str, ...] = ()) -> dict:
    """`dateien`: SHA-256 jeder Datei wie in der Bestandskopie, außer Dateien mit Punkten (`in_datei`) und neuen Dateien. `bestand` ist
    `dateien.json` der Aufnahme einschließlich der Hauptdatei (`haupt: true`), `ist` relativer Pfad → SHA-256 im Lauf (`None`: nicht
    gelesen), `neue_dateien` die Pfade, die der Bau angelegt hat. Verlangt ist eine Änderung an Dateien mit Punkten und an der
    Hauptbaugruppe, wenn ein Punkt ohne `in_datei` (Baugruppen-Punkt, `eigenschaft`, `skript`) sie ändert; nur `lage_folgen` erlaubt
    die Änderung der Hauptbaugruppe, verlangt sie nicht. Ein Punkt, der nichts gespeichert hat, ist ein Mangel."""
    s = datei_schluessel
    alt = {s(rel): (rel, d.get("sha256")) for rel, d in bestand.items()}
    lauf = {s(rel): (rel, sha) for rel, sha in ist.items()}
    haupt = next((s(rel) for rel, d in bestand.items() if d.get("haupt")), None)
    neu = {s(rel): rel for rel in neue_dateien}
    verlangt = {s(d): d for d in dateien_mit_punkten(spec)}
    unlesbar, probleme = [], []
    if haupt is not None and haupt_punkte(spec):
        verlangt[haupt] = alt[haupt][0]
    elif haupt is None and (haupt_punkte(spec) or aenderung_an_haupt(spec)):
        unlesbar.append("die Hauptdatei ist in dateien.json nicht gekennzeichnet")
    erlaubt = set(verlangt) | ({haupt} if haupt is not None and aenderung_an_haupt(spec) else set())
    for schl, (rel, sha) in alt.items():
        if schl not in lauf:
            probleme.append({"art": "fehlt", "datei": rel})
            continue
        gelaufen = lauf[schl][1]
        if gelaufen is None:
            unlesbar.append(f"{rel}: SHA-256")
        elif gelaufen.lower() == str(sha).lower():
            if schl in verlangt:
                probleme.append({"art": "ungespeichert", "datei": rel})
        elif schl not in erlaubt:
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
    text = {"fehlt": "fehlt im Lauf", "geaendert": "verändert, ohne dass ein Punkt sie nennt",
            "ungespeichert": "unverändert, obwohl ein Punkt sie ändern sollte (nichts gespeichert)",
            "unbekannt": "nicht in der Bestandskopie", "fremd": "neu, ohne dass der Bau sie anlegen sollte",
            "neu_im_bestand": "soll neu sein, gibt es aber schon im Bestand", "neu_fehlt": "neu angelegt, aber nicht im Lauf"}
    teile = [f"{q['datei']} {text[q['art']]}" for q in probleme]
    geaendert = sorted(rel for schl, (rel, sha) in alt.items() if schl in lauf and lauf[schl][1] not in (None, sha))
    return _ergebnis("dateien", probleme, unlesbar, ["Dateien: " + "; ".join(teile)] if teile else [], ist=probleme,
                     erwartet_geaendert=sorted(verlangt.values()), geaendert=geaendert, neu=sorted(neu.values()), knoten=[])
