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
  des Laufs, solange er nicht schlechter ist (`_nicht_schlechter`: spätere Abbruchstellung, nicht mehr Durchgang, nicht größere
  Abweichung, gleiche Bestimmtheit); es steht im Hinweis, ein unbekanntes Format wird nie angehoben. Eine Grenze, die im Bestand nicht
  gefahren wurde (kein Weg, Fahrt gescheitert), hat kein Soll: `bewegung:<g>` ist `ok: True` mit dem Grund im Hinweis, fährt der Lauf
  sie trotzdem, werden seine Prüfungen für sich bewertet. Fehlt die Fahrt in der Aufnahme ganz (`--ohne-bewegung`), ist `bewegung:<g>`
  `ok: None`. Der Lauf muss mindestens so viele Stellungen gefahren sein wie der Bestand (`stellungen`); fehlt die Zahl, `ok: None`.
- Lief im Bestand eine Grenze und fehlt sie im Lauf (nicht in `bewegungen`, nicht gefahren), ist das ein Mangel, außer ein Punkt
  löscht die Verknüpfung (`verknuepfung_loeschen`, `komponente_entfernen`). Ein `verknuepfung_wert` an `min` oder `max` ändert den
  Bereich: gefahren wird der Bereich des Laufs; ohne Punkt ist ein anderer Bereich ein Mangel in `bewegung:<g>`.
- `bewegung_menge:<g>`: Dieselben Komponenten bewegen sich wie im Bestand (ersetzte unter ihrem neuen Namen). Neu angelegte
  Komponenten (aus den Punkten, keine ersetzenden) dürfen mitfahren, entfernte fehlen; sonst ist jede andere Menge ein Mangel.
  Namen, Protokoll und `kollision_erlaubt` laufen durch `Vergleichsstand` (`vergleich_baugruppe`), keine zweite Namenslogik.
- `bewegung_kollision:<g>`: Eine Kollision in der Fahrt des Laufs ist ein Mangel, außer das Paar ist bekannt: statisch im Bestand,
  in der Fahrt des Bestands oder in `kollision_erlaubt` (`bekannte_paare`).
- Nicht abgedeckt, aber nie stumm (`abdeckung`, Eintrag `bewegung_abdeckung`): Grenzen in Unterbaugruppen und bewegliche
  (unterbestimmte) Komponenten ohne Grenze.
"""

from swki.baugruppe.aufloesen import Verknuepfung
from swki.baugruppe.bewegung import Bewegung, BewegungsMesswerte, bewerte_bewegungen, ist_bewegt
from swki.baugruppe.bewegungslauf import Mechanik, StellungFehler, fahre
from swki.baugruppe.bewertung import UNTERBESTIMMT
from swki.baugruppe.sw_baugruppe import AUSRICHTUNG
from swki.bestand.vergleich_baugruppe import Vergleichsstand, _ahnen, _je, _komma, erlaubte_paare
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
    return {"komponente": komponente, "art": _art(v), "min": v.get("min"), "max": v.get("max"), "gefahren": False, "stellungen": 0,
            "bewegt": [], "raum": None, "kollisionen": [], "pruefungen": [], "hinweis": grund}


def _gefahren(b: Bewegung, m, tol_mm: float) -> dict:
    """Der Eintrag einer gefahrenen Grenze: Grundstellungslauf (bewegt, Raum), Kollisionen aller Läufe, Prüfungen der Bewertung."""
    laeufe = [lauf for lauf in m.laeufe if lauf.bewegung == b.name]
    grund = next(lauf for lauf in laeufe if not lauf.gegen)
    messwerte = BewegungsMesswerte(m.status_frei, m.status_gehalten, laeufe, [p for p in m.paare if b.name in p["bewegungen"]])
    pruefungen, _ = bewerte_bewegungen({"bewegungen": []}, [b], messwerte, tol_mm)
    hinweis = (f"Lauf bei Stellung {grund.fehler['stellung']:g} abgebrochen: {grund.fehler['meldung']}"
               if grund.fehler is not None else None)
    return {"komponente": b.komponente, "art": b.art, "min": b.min, "max": b.max, "gefahren": True,
            "stellungen": len(grund.stellungen), "bewegt": list(grund.bewegt),
            "raum": [round(c, 3) for c in grund.raum] if grund.raum else None,
            "kollisionen": [{"paar": list(k["paar"]), "volumen": k["volumen"]} for lauf in laeufe for k in lauf.kollisionen],
            "pruefungen": pruefungen, "hinweis": hinweis}


def fahre_bestand(mech: Mechanik, aufnahme: dict, grenzen: dict[str, dict], schritte: int, bekannt: set[frozenset],
                  grenze_mb: float, tol_mm: float, start_mb: float | None = None) -> dict:
    """Fährt die `grenzen` (`grenzen_der_aufnahme`) der Aufnahme von `min` bis `max` und liefert das Feld `bewegungen` der Aufnahme:
    Grenze → {komponente, art, min, max, gefahren, stellungen, bewegt, raum, kollisionen, pruefungen, hinweis}. `aufnahme` ist die
    des Standes, der gefahren wird (Bestand oder Lauf); sie nennt die fixierten Komponenten für die bewegte Seite.

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

def _bekannt(c: Vergleichsstand) -> set[frozenset]:
    """Die bekannten Paare eines Vergleichsstands (`bekannte_paare`); Namen und `kollision_erlaubt` über den Stand des Protokolls."""
    paare = {frozenset(c.abbild(x) for x in k["paar"]) for k in c.vorher.get("kollisionen") or []}
    for e in (c.vorher.get("bewegungen") or {}).values():
        paare |= {frozenset(c.abbild(x) for x in k["paar"]) for k in e.get("kollisionen") or []}
    return paare | {frozenset(p) for p in erlaubte_paare(c)}


def bekannte_paare(vorher: dict, spec: dict, neue: dict[str, list[str]], ersetzt: dict[str, str] | None = None,
                   nachher: dict | None = None) -> set[frozenset]:
    """Kollisionspaare, die in der Fahrt des Laufs keine neuen sind: die statischen Kollisionen des Bestands, die Kollisionen in der
    Fahrt des Bestands und `kollision_erlaubt`. Die Namen laufen über denselben Stand des Protokolls wie der Vergleich der Baugruppe
    (`Vergleichsstand`): Eine Punkt-ID steht für die Komponenten, die der Lauf erzeugt hat, Namen ersetzter Komponenten gelten unter
    dem neuen Namen; ein Protokoll, das kein Punkt deckt, gilt nicht. `nachher`: die Aufnahme des Laufs (ohne Angabe die des
    Bestands)."""
    return _bekannt(Vergleichsstand(spec, vorher, vorher if nachher is None else nachher, neue, ersetzt or {}))


def _id_im_lauf(c: Vergleichsstand, pid: str) -> str:
    """ID einer Prüfung des Bestands unter den Komponentennamen des Laufs (`freiheitsgrad:<k>`, `sollweg:<g>:<k>`)."""
    teile = pid.split(":")
    if teile[0] in ("freiheitsgrad", "sollweg") and len(teile) >= 2:
        teile[-1] = c.abbild(teile[-1])
    return ":".join(teile)


def _bereich_befund(g: str, ve: dict, ne: dict, c: Vergleichsstand) -> list[str]:
    """Der Bereich im Lauf weicht ab, ohne dass ein `verknuepfung_wert`-Punkt `min` bzw. `max` in der aktiven Konfiguration nennt."""
    aktiv = c.nachher.get("aktiv")
    befunde = []
    for feld in ("min", "max"):
        alt, neu = ve.get(feld), ne.get(feld)
        if (alt is None or neu is None or abs(alt - neu) > TOL_BEREICH) and aktiv not in c.wert_frei.get((g, feld), ()):
            befunde.append(f"{feld} steht auf {neu} statt {alt}, kein Punkt nennt es")
    return befunde


def _schluessel(gegen: dict) -> tuple:
    return tuple(sorted(gegen.items()))


def _nicht_schlechter(pid: str, lauf: dict, bestand: dict) -> bool:
    """Ist der Befund im Lauf nicht schlechter als im Bestand? Maßstab je Prüfung: `bewegung` gleiche oder spätere Abbruchstellung
    je `gegen`; `grenze` geht nur dort durch, wo es auch im Bestand durchging; `sollweg` Betrag und Anzahl der abweichenden
    Stellungen nicht größer; `freiheitsgrad` dieselbe Bestimmtheit. Ein Format, das der Maßstab nicht kennt, gilt als schlechter."""
    art, a, b = pid.split(":")[0], lauf.get("ist"), bestand.get("ist")
    try:
        if art == "bewegung":
            alt = {_schluessel(f["gegen"]): f["stellung"] for f in b}
            return bool(a) and bool(b) and all(
                f["stellung"] is not None and alt.get(_schluessel(f["gegen"])) is not None
                and f["stellung"] >= alt[_schluessel(f["gegen"])] for f in a)
        if art == "grenze":
            return {k for k in ("oben", "unten") if a.get(k)} <= {k for k in ("oben", "unten") if b.get(k)}
        if art == "sollweg":
            return (a["groesste_abweichung"]["betrag"] <= b["groesste_abweichung"]["betrag"] + TOL_BEREICH
                    and a["abweichende_stellungen"] <= b["abweichende_stellungen"])
        if art == "freiheitsgrad":
            return isinstance(a, dict) and a == b
    except (KeyError, TypeError, AttributeError):
        return False
    return False


def _angehoben(e: dict, bestand: dict) -> dict:
    """Eine Prüfung, die im Lauf nicht besteht und im Bestand schon nicht bestand, im Lauf aber nicht schlechter ist: kein Mangel des
    Laufs, der Befund steht im Hinweis."""
    grund = bestand.get("hinweis")
    teile = ["Schon im Bestand nicht bestanden, im Lauf nicht schlechter, kein Mangel des Laufs" + (f" ({grund})" if grund else "")]
    if e.get("hinweis"):
        teile.append(f"im Lauf: {e['hinweis']}")
    return {**e, "ok": True, "hinweis": "; ".join(teile), "bestand_ok": False}


def _angehoben_abbruch(e: dict) -> dict:
    """`grenze` und `sollweg` laufen nach einem Abbruch der Fahrt nicht (`ok: None`). Brach die Fahrt im Bestand ebenso ab und ist der
    Lauf dabei nicht schlechter, ist das kein Mangel des Laufs und kein Grund, die Baugruppe nie bestehen zu lassen."""
    return {**e, "ok": True, "bestand_ok": None,
            "hinweis": "Wegen des Abbruchs der Fahrt nicht gelaufen, im Bestand ebenso, kein Mangel des Laufs"}


def _bewegung_pruefen(e: dict, g: str, ve: dict, ne: dict, c: Vergleichsstand) -> dict:
    """`bewegung:<g>` zusätzlich gegen den Bestand: Bereich nur mit Punkt anders, mindestens so viele Stellungen gefahren wie im
    Bestand. Fehlt die Zahl der Stellungen in einem Stand, ist ein sonst bestandener Eintrag nicht nachgewiesen."""
    gruende = _bereich_befund(g, ve, ne, c)
    alt, neu = ve.get("stellungen"), ne.get("stellungen")
    lesbar = isinstance(alt, int) and isinstance(neu, int)
    if lesbar and neu < alt:
        gruende.append(f"der Lauf fuhr {neu} Stellungen, der Bestand {alt}")
    vorweg = [e["hinweis"]] if e.get("hinweis") else []
    if gruende:
        return {**e, "ok": False, "hinweis": "; ".join([*vorweg, "Lauf gegen Bestand: " + "; ".join(gruende)])}
    if not lesbar and e["ok"] is True:
        hinweis = "Die Zahl der gefahrenen Stellungen ist nicht gelesen, nicht nachgewiesen"
        return {**e, "ok": None, "hinweis": "; ".join([*vorweg, hinweis])}
    return e


def _menge(g: str, ve: dict, ne: dict, c: Vergleichsstand) -> dict:
    """Dieselben Komponenten bewegen sich wie im Bestand (ersetzte unter ihrem neuen Namen); mitfahren dürfen nur Komponenten, die
    ein Punkt neu anlegt (keine ersetzende), fehlen dürfen nur entfernte."""
    pid = f"bewegung_menge:{g}"
    if ve.get("bewegt") is None or ne.get("bewegt") is None:
        return eintrag(pid, None, hinweis="Die bewegten Komponenten sind nicht gelesen, nicht nachgewiesen", knoten=[])
    lauf = set(ne["bewegt"])
    erwartet = {c.abbild(x) for x in ve["bewegt"]}
    fehlen = sorted({c.abbild(x) for x in ve["bewegt"] if c.abbild(x) not in lauf and not any(a in c.entfernt for a in _ahnen(x))})
    zusaetzlich = sorted(y for y in lauf if y not in erwartet and not any(a in c.reine_neue for a in _ahnen(y)))
    teile = ([f"bewegen sich nicht mehr: {_komma(fehlen)}"] if fehlen else []) + (
        [f"bewegen sich zusätzlich: {_komma(zusaetzlich)}"] if zusaetzlich else [])
    return eintrag(pid, not teile, ist=sorted(lauf), soll=sorted(erwartet), fehlen=fehlen, zusaetzlich=zusaetzlich,
                   knoten=fehlen + zusaetzlich, **({"hinweis": "; ".join(teile)} if teile else {}))


def _kollision(g: str, ne: dict, bekannt: set[frozenset], pruefung: dict | None) -> dict:
    """Neue Kollisionen in der Fahrt des Laufs: jedes Paar, das nicht bekannt ist (je Paar die größte Überlappung). Trägt das Feld
    nichts und meldet die Prüfung des Laufs Kollision, Fehlen oder nicht geprüft, ist das nicht nachgewiesen, nie bestanden."""
    pid = f"bewegung_kollision:{g}"
    roh = ne.get("kollisionen")
    if roh is None:
        return eintrag(pid, None, hinweis="Die Kollisionen der Fahrt sind nicht gelesen, nicht nachgewiesen", knoten=[])
    neu: dict[frozenset, dict] = {}
    for k in roh:
        paar = frozenset(k["paar"])
        if paar not in bekannt and (paar not in neu or (k.get("volumen") or 0) > (neu[paar].get("volumen") or 0)):
            neu[paar] = {"paar": sorted(paar), "volumen": k.get("volumen")}
    ist = list(neu.values())
    if ist:
        return eintrag(pid, False, ist=ist, knoten=sorted({x for k in ist for x in k["paar"]}),
                       hinweis="Neue Kollisionen in der Fahrt: "
                       + ", ".join(f"{' / '.join(k['paar'])} ({k['volumen']} mm³)" for k in ist))
    if not roh and (pruefung is None or pruefung.get("ok") is not True):
        was = "fehlt" if pruefung is None else f"meldet {'Kollision' if pruefung.get('ok') is False else 'nichts'}"
        return eintrag(pid, None, ist=[], knoten=[],
                       hinweis=f"Die Prüfung der Kollision im Lauf {was}, das Feld kollisionen trägt nichts: nicht nachgewiesen")
    return eintrag(pid, True, ist=[], knoten=[])


def _eintraege_der_grenze(g: str, ve: dict | None, ne: dict, c: Vergleichsstand, bekannt: set[frozenset]) -> list[dict]:
    """Die Prüfungen einer im Lauf gefahrenen Grenze; `ve` die des Bestands (`None`: kein Soll, nur die Fahrt wird bewertet)."""
    bestand = {_id_im_lauf(c, e["id"]): e for e in (ve or {}).get("pruefungen") or []}
    pruefungen = ne.get("pruefungen") or []
    bid, kid = f"bewegung:{g}", f"bewegung_kollision:{g}"
    ergebnis = []
    abbruch_gleich = False  # die Fahrt brach im Bestand ebenso ab, der Lauf ist dabei nicht schlechter
    lauf_b, best_b = next((e for e in pruefungen if e["id"] == bid), None), bestand.get(bid)
    if ve is not None and lauf_b and best_b and lauf_b.get("ok") is False and best_b.get("ok") is False \
            and _nicht_schlechter(bid, lauf_b, best_b):
        abbruch_gleich = _bewegung_pruefen(_angehoben(lauf_b, best_b), g, ve, ne, c)["ok"] is True
    for e in pruefungen:
        pid = e["id"]
        if pid == kid:
            continue  # die Kollision bildet `_kollision` neu aus dem Feld kollisionen
        if e.get("ok") is False and bestand.get(pid, {}).get("ok") is False and _nicht_schlechter(pid, e, bestand[pid]):
            e = _angehoben(e, bestand[pid])
        elif (abbruch_gleich and e.get("ok") is None and bestand.get(pid, {}).get("ok") is None
              and pid.split(":")[0] in ("grenze", "sollweg")):
            e = _angehoben_abbruch(e)
        if pid == bid and ve is not None:
            e = _bewegung_pruefen(e, g, ve, ne, c)
        ergebnis.append(e)
    gesehen = {e["id"] for e in pruefungen}
    if bid not in gesehen:  # eine gefahrene Grenze ohne diese Prüfung beweist nichts
        ergebnis.append(eintrag(bid, None, hinweis="Die Prüfung bewegung fehlt im Lauf, nicht nachgewiesen", knoten=[]))
    ergebnis.append(_kollision(g, ne, bekannt, next((e for e in pruefungen if e["id"] == kid), None)))
    if ve is not None:
        ergebnis.append(_menge(g, ve, ne, c))
    ergebnis += [eintrag(pid, None, hinweis="Im Lauf nicht geprüft, nicht nachgewiesen", knoten=[])
                 for pid in bestand if pid not in gesehen | {bid, kid}]
    return ergebnis


def _grenze_vergleichen(g: str, ve: dict | None, ne: dict | None, c: Vergleichsstand, bekannt: set[frozenset]) -> list[dict]:
    pid = f"bewegung:{g}"
    if ve is None or ve.get("gefahren") is None:
        return [eintrag(pid, None, hinweis="Die Aufnahme enthält keine Fahrt dieser Grenze (ohne Bewegung), nicht nachgewiesen",
                        knoten=[])]
    if ve["gefahren"] is not True:  # kein Soll; was der Lauf trotzdem fährt, wird für sich bewertet
        basis = eintrag(pid, True, hinweis=f"Im Bestand nicht gefahren ({ve.get('hinweis')}), kein Soll", knoten=[],
                        bestand_gefahren=False)
        if ne is not None and ne.get("gefahren") is True:
            return [basis, *_eintraege_der_grenze(g, None, ne, c, bekannt)]
        return [basis]
    if ne is None:
        return [eintrag(pid, False, hinweis="Die Grenze lief im Bestand und fehlt im Lauf (nicht gefahren), kein Punkt löscht sie",
                        knoten=[ve.get("komponente")] if ve.get("komponente") else [])]
    if ne.get("gefahren") is None:
        return [eintrag(pid, None, hinweis="Im Lauf ist die Fahrt nicht gelesen, nicht nachgewiesen", knoten=[])]
    if ne["gefahren"] is not True:
        return [eintrag(pid, False, hinweis=f"Im Lauf nicht gefahren, im Bestand schon: {ne.get('hinweis')}",
                        knoten=[ne["komponente"]] if ne.get("komponente") else [])]
    return _eintraege_der_grenze(g, ve, ne, c, bekannt)


def _neue_grenze(g: str, ne: dict | None, c: Vergleichsstand, bekannt: set[frozenset]) -> list[dict]:
    """Eine Grenze, die der Bestand nicht hatte (Punkt `verknuepfung_neu`): kein Soll, nur die Fahrt selbst wird bewertet. Ohne
    Fahrt-Eintrag im Lauf ist sie nicht nachgewiesen."""
    if ne is None:
        return [eintrag(f"bewegung:{g}", None, hinweis="Neue Grenze ohne Fahrt im Lauf, nicht nachgewiesen", knoten=[])]
    if ne.get("gefahren") is not True:
        return [eintrag(f"bewegung:{g}", None, hinweis=f"Neue Grenze, im Lauf nicht gefahren ({ne.get('hinweis')})", knoten=[])]
    return _eintraege_der_grenze(g, None, ne, c, bekannt)


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
    Protokoll des Baus wie in `vergleiche_baugruppe` und laufen durch denselben `Vergleichsstand`. Je Grenze des Bestands
    `bewegung:<g>`, `bewegung_menge:<g>`, `bewegung_kollision:<g>`, `grenze:<g>`, `sollweg:<g>:<komponente>` und
    `freiheitsgrad:<komponente>`; neue Grenzen des Laufs ohne Soll; `bewegung_abdeckung`, wenn etwas nicht abgedeckt ist. Grenzen,
    die ein Punkt löscht, bleiben außen vor."""
    c = Vergleichsstand(spec, vorher, nachher, neue, ersetzt or {})
    bekannt = _bekannt(c)
    vb, nb = vorher.get("bewegungen") or {}, nachher.get("bewegungen") or {}
    eintraege = []
    im_bestand = dict.fromkeys([*grenzen_der_aufnahme(vorher), *vb])
    for g in im_bestand:
        if g not in c.geloeschte_mates:
            eintraege += _grenze_vergleichen(g, vb.get(g), nb.get(g), c, bekannt)
    for g in dict.fromkeys([*grenzen_der_aufnahme(nachher), *nb]):
        if g not in im_bestand and g not in c.geloeschte_mates:
            eintraege += _neue_grenze(g, nb.get(g), c, bekannt)
    if hinweise := abdeckung(vorher):
        eintraege.append(eintrag("bewegung_abdeckung", True, ist=hinweise, knoten=[],
                                 hinweis="Nicht abgedeckt: " + "; ".join(hinweise)))
    return _zusammen(eintraege)
