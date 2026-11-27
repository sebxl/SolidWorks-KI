"""Reine Prüfungen der zurückgelesenen Zeichnung (Plan Z1.4, Design §8.1): Ist-Modell gegen Maßplan und Regelkatalog.

Jede Prüfung gibt ein dict `{id, regeln, ok, maengel, hinweis?}` zurück, Mängel haben die Form
`{regel, merkmal, text}`. `ok` ist True, False (harter Mangel) oder None (Hinweisregel oder nicht prüfbar, immer mit
`hinweis` bzw. Mängeln als Begründung). „Nicht prüfbar“ ist nie „ok“."""

import re

from swki.zeichnung.angaben import zahl
from swki.zeichnung.ist import Ist, IstMass
from swki.zeichnung.massplan import Mass
from swki.zeichnung.regeln import Regel, regel

# ISO 5455 (Entscheidung 5): Vorzugsreihe für das Blatt und jede Einzelheit.
VORZUGSMASSSTAEBE: tuple[str, ...] = ("1:1", "1:2", "1:5", "1:10", "1:20", "1:50", "1:100",
                                      "2:1", "5:1", "10:1", "20:1", "50:1")

# Plan-Art → Ist-Art (Entscheidung 1). Eine Plan-Art, die hier fehlt, ist ein Mangel, kein stilles Weglassen.
IST_ART: dict[str, str] = {
    "laenge": "laenge", "lage": "laenge", "tiefe": "laenge", "abstand": "laenge", "paarabstand": "laenge",
    "fase": "laenge", "durchmesser": "durchmesser", "radius": "radius", "winkel": "winkel",
}
_MASSQUELLEN = ("modell", "neu")
_RASTER = 0.05  # mm, Knotenabstand des Maßgraphen (Entscheidung 2)


def normtext(text: str | None) -> str:
    """Vergleichstext: das Rücklesen liefert Ⓔ an Maßen als Tag `<MOD-EP>`; Tag → Zeichen, Leerraum zusammenfassen."""
    return " ".join((text or "").replace("<MOD-EP>", "Ⓔ").split())


_norm = normtext
_WERT_TOL = 0.005 + 1e-9  # mm: Werte gelten als gleich, wenn sie auf 0,01 mm übereinstimmen
_TOL_GLEICH = 0.0005      # mm: Abmaße gleich


def _mangel(regeln: list[Regel], id_: str, merkmal: str, text: str) -> dict:
    regel(regeln, id_)                      # unbekannte ID sofort sichtbar (KeyError)
    return {"regel": id_, "merkmal": merkmal, "text": text}


def _pruefung(id_: str, regeln: list[Regel], ids: tuple[str, ...], maengel: list[dict], unpruefbar: str | None = None,
              hinweis: str | None = None) -> dict:
    """Gemeinsame Form: harter Mangel → False; nur Hinweismängel oder nicht prüfbar → None; sonst True."""
    if any(regel(regeln, m["regel"]).art == "hart" for m in maengel):
        ok = False
    elif maengel or unpruefbar:
        ok = None
    else:
        ok = True
    d = {"id": id_, "regeln": list(ids), "ok": ok, "maengel": maengel}
    text = "; ".join(t for t in (unpruefbar, hinweis) if t)
    if text:
        d["hinweis"] = text
    return d


def _etikett(art: str, wert: float) -> str:
    return {"durchmesser": "Ø", "radius": "R"}.get(art, "") + zahl(wert) + ("°" if art == "winkel" else "")


def _zusatz_ok(ist: IstMass, m: Mass) -> bool:
    """Präfix am Anfang, Suffix am Ende des Ist-Textzusatzes (Leerraum normalisiert); ein Ⓔ am Ende gehört zur Toleranz."""
    praefix, suffix = normtext(m.praefix), normtext(m.suffix)
    ist_suffix = normtext(ist.suffix)
    if not suffix.endswith("Ⓔ"):
        ist_suffix = ist_suffix.removesuffix("Ⓔ").rstrip()
    return normtext(ist.praefix).startswith(praefix) and ist_suffix.endswith(suffix)


def _gleich(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= _TOL_GLEICH


def _toleranz_ok(ist: IstMass, m: Mass) -> bool:
    t, i = m.toleranz, ist.toleranz
    if t is None:
        return i.typ == "keine"
    if t.passung is not None:
        return i.typ == "passung" and i.passung == t.passung
    return i.typ in ("bilateral", "symmetrisch", "grenz") and _gleich(i.oben, t.oben) and _gleich(i.unten, t.unten)


def _wert_gleich(ist: IstMass, m: Mass) -> bool:
    return abs(ist.wert - m.wert) <= _WERT_TOL


def _abgleich(ist: Ist, plan: list[Mass]) -> tuple[dict[str, IstMass | None], list[IstMass]]:
    """Multimenge je Ist-Art und Wert (auf 0,01 mm), unabhängig von der Ansicht (Entscheidung 1). Ist-Maße in Klammern
    zählen nicht. Die Ist-Maße sind fest nach (Ansicht, Name) sortiert. Je Plan-Maß, in Planreihenfolge, gilt der
    Vorrang: Toleranz und Textzusatz passen, nur Toleranz, nur Zusatz, irgendein freies. Zweiter Wert: die nicht
    zugeordneten Ist-Maße."""
    frei = sorted((m for m in ist.masse if not m.klammer), key=lambda m: (m.ansicht, m.name))
    zuordnung: dict[str, IstMass | None] = {}
    offen = []
    for m in plan:
        if m.quelle in _MASSQUELLEN:
            zuordnung[m.id] = None
            if m.art in IST_ART:
                offen.append(m)
    vorrang = (lambda c, m: _toleranz_ok(c, m) and _zusatz_ok(c, m), _toleranz_ok, _zusatz_ok, lambda c, m: True)
    for passt in vorrang:
        for m in offen:
            if zuordnung[m.id] is not None:
                continue
            treffer = next((c for c in frei if c.art == IST_ART[m.art] and _wert_gleich(c, m) and passt(c, m)), None)
            if treffer is not None:
                zuordnung[m.id] = treffer
                frei.remove(treffer)
    return zuordnung, frei


def zuordnen(ist: Ist, plan: list[Mass]) -> dict[str, IstMass | None]:
    """Je Plan-ID (Quelle modell/neu) das zugeordnete Ist-Maß, None wenn keines gezeichnet ist (oder die Art unbekannt)."""
    return _abgleich(ist, plan)[0]


def _erste_zeile(text: str) -> str:
    return (text or "").strip().splitlines()[0].strip() if (text or "").strip() else ""


def pruefe_vollstaendig(ist: Ist, plan: list[Mass], regeln: list[Regel]) -> dict:
    """Z-VOLL-1 (fehlt, Zusatz fehlt, Art unbekannt), Z-VOLL-2 (doppelt, überzählig)."""
    maengel: list[dict] = []
    zuordnung, uebrig = _abgleich(ist, plan)
    geplant = [m for m in plan if m.quelle in _MASSQUELLEN and m.art in IST_ART]
    for m in plan:
        if m.quelle in _MASSQUELLEN:
            if m.art not in IST_ART:
                maengel.append(_mangel(regeln, "Z-VOLL-1", m.merkmal, f"Art {m.art} nicht prüfbar"))
                continue
            etikett = _etikett(IST_ART[m.art], m.wert)
            treffer = zuordnung[m.id]
            if treffer is None:
                maengel.append(_mangel(regeln, "Z-VOLL-1", m.merkmal, f"fehlt: {etikett} ({m.merkmal})"))
            elif not _zusatz_ok(treffer, m):
                maengel.append(_mangel(regeln, "Z-VOLL-1", m.merkmal,
                                       f"Zusatz fehlt: {m.praefix}{etikett}{m.suffix}".strip()))
        elif m.quelle not in ("angabe", "rauheit", "form_lage", "bezug"):
            maengel.append(_mangel(regeln, "Z-VOLL-1", m.merkmal, f"Quelle {m.quelle} nicht prüfbar"))
    for m in uebrig:
        wort = "doppelt" if any(IST_ART[g.art] == m.art and _wert_gleich(m, g) for g in geplant) else "überzählig"
        maengel.append(_mangel(regeln, "Z-VOLL-2", m.name, f"{wort}: {_etikett(m.art, m.wert)}"))
    maengel += _angaben_abgleich(ist, plan, regeln)
    return _pruefung("vollstaendig", regeln, ("Z-VOLL-1", "Z-VOLL-2"), maengel)


def _angaben_abgleich(ist: Ist, plan: list[Mass], regeln: list[Regel]) -> list[dict]:
    """Plan-Angaben (Bohrungen, Gewinde) gegen die Notizen: Textanfang, Leerraum normalisiert."""
    maengel = []
    notizen = [_norm(a.text) for a in ist.angaben if a.art == "hinweis"]
    frei = list(range(len(notizen)))
    texte = []
    for m in plan:
        if m.quelle != "angabe":
            continue
        text = _norm(m.text)
        if not text:
            maengel.append(_mangel(regeln, "Z-VOLL-1", m.merkmal, f"Angabe ohne Text: {m.merkmal}"))
            continue
        texte.append(text)
        treffer = next((i for i in frei if notizen[i].startswith(text)), None)
        if treffer is None:
            maengel.append(_mangel(regeln, "Z-VOLL-1", m.merkmal, f"fehlt: Angabe {_erste_zeile(m.text)}"))
        else:
            frei.remove(treffer)
    for i in frei:
        if any(notizen[i].startswith(t) for t in texte):
            maengel.append(_mangel(regeln, "Z-VOLL-2", "angabe", f"doppelt: Angabe {notizen[i].split(' – ')[0]}"))
    return maengel


def _cluster(koordinaten: list[float]) -> list[tuple[float, float]]:
    """Sortierte Koordinaten zu Knoten: aufeinanderfolgende mit Abstand ≤ 0,05 mm bilden einen Knoten (von, bis)."""
    knoten: list[list[float]] = []
    for x in sorted(koordinaten):
        if knoten and x - knoten[-1][1] <= _RASTER + 1e-9:
            knoten[-1][1] = x
        else:
            knoten.append([x, x])
    return [(a, b) for a, b in knoten]


def _knoten(knoten: list[tuple[float, float]], x: float) -> int:
    return next(i for i, (a, b) in enumerate(knoten) if a <= x <= b)


def pruefe_ueberbestimmt(ist: Ist, regeln: list[Regel]) -> dict:
    """Z-UEB-1: je (Ansicht, Richtung) bilden die linearen Maße ohne Klammer einen Graphen über die Bezugskoordinaten
    (auf 0,05 mm gerundet). Eine Kante, die zwei schon verbundene Knoten verbindet, schließt einen Zyklus. Maße
    verschiedener Ansichten gelten als unabhängig (bekannte Grenze, Entscheidung 2)."""
    gruppen: dict[tuple, list[IstMass]] = {}
    ohne_punkte = 0
    for m in ist.masse:
        if m.art != "laenge" or m.klammer:
            continue
        if m.richtung not in ("h", "v") or m.punkte is None:
            ohne_punkte += 1
            continue
        gruppen.setdefault((m.ansicht, m.richtung), []).append(m)
    maengel = []
    for (ansicht, richtung), masse in gruppen.items():
        i = 0 if richtung == "h" else 1
        knoten = _cluster([p[i] for m in masse for p in m.punkte])
        vater: dict[int, int] = {}

        def wurzel(x):
            while vater.setdefault(x, x) != x:
                vater[x] = vater[vater[x]]
                x = vater[x]
            return x

        gesehen: set[frozenset] = set()
        for m in masse:
            a, b = (_knoten(knoten, p[i]) for p in m.punkte)
            kante = frozenset((a, b))
            if a == b or kante in gesehen:      # gleiches Knotenpaar: Doppelmaß, das meldet nur Z-VOLL-2
                continue
            gesehen.add(kante)
            wa, wb = wurzel(a), wurzel(b)
            if wa == wb:
                art = "waagrecht" if richtung == "h" else "senkrecht"
                maengel.append(_mangel(regeln, "Z-UEB-1", m.name,
                                       f"Maßkette geschlossen: {zahl(m.wert)} ({ansicht}, {art}) – Hilfsmaß in Klammern setzen"))
            else:
                vater[wa] = wb
    unpruefbar = f"{ohne_punkte} lineare Maße ohne Richtung oder Bezugspunkte nicht prüfbar" if ohne_punkte else None
    return _pruefung("ueberbestimmt", regeln, ("Z-UEB-1",), maengel, unpruefbar=unpruefbar,
                     hinweis="Maße verschiedener Ansichten gelten als unabhängig; zufällig zusammenfallende Koordinaten "
                             "verschiedener Merkmale (0–20, 20–50, 0–50) bleiben ein möglicher Fehlalarm")


def pruefe_ansichten(ist: Ist, regeln: list[Regel]) -> dict:
    """Z-ANS-1 (Maß an verdeckter Kante), Z-ANS-2 (Schnitt ohne Bezeichnung), Z-ANS-3 (Einzelheit: Maßstab fehlt oder
    nicht aus der Vorzugsreihe). Lineare Maße mit `verdeckt None` sind nicht prüfbar."""
    maengel, unbekannt = [], 0
    for m in ist.masse:
        if m.verdeckt is True:
            maengel.append(_mangel(regeln, "Z-ANS-1", m.name,
                                   f"Maß {zahl(m.wert)} an verdeckter Kante oder ohne sichtbaren Bezug ({m.ansicht})"))
        elif m.verdeckt is None and m.art == "laenge":
            unbekannt += 1
    for a in ist.ansichten:
        if a.art == "schnitt" and not _norm(a.beschriftung):
            maengel.append(_mangel(regeln, "Z-ANS-2", a.name, f"Schnittansicht {a.name} ohne Bezeichnung"))
        if a.art == "einzelheit":
            massstab = re.sub(r"\s+", "", a.massstab or "")
            if not massstab:
                maengel.append(_mangel(regeln, "Z-ANS-3", a.name, f"Einzelheit {a.name} ohne Maßstab"))
            elif massstab not in VORZUGSMASSSTAEBE:
                maengel.append(_mangel(regeln, "Z-ANS-3", a.name,
                                       f"Einzelheit {a.name}: Maßstab {massstab} nicht aus der Vorzugsreihe"))
    unpruefbar = f"{unbekannt} lineare Maße: Sichtbarkeit nicht ermittelt (verdeckt unbekannt)" if unbekannt else None
    return _pruefung("ansichten", regeln, ("Z-ANS-1", "Z-ANS-2", "Z-ANS-3"), maengel, unpruefbar=unpruefbar)


def pruefe_drehteil(ist: Ist, plan: list[Mass], regeln: list[Regel]) -> dict:
    """Z-DRE-1: An jedem Durchmessermaß eines Drehteils steht „Ø“ im Präfix. Drehteil = der Plan hat Maße aus dem
    Rotationsprofil (Quelle neu)."""
    if not any(m.quelle == "neu" for m in plan):
        return _pruefung("drehteil", regeln, ("Z-DRE-1",), [], unpruefbar="kein Drehteil")
    maengel = [_mangel(regeln, "Z-DRE-1", m.name, f"Ø-Zeichen fehlt am Durchmesser {zahl(m.wert)} ({m.ansicht})")
               for m in ist.masse if m.art == "durchmesser" and "Ø" not in m.praefix]
    return _pruefung("drehteil", regeln, ("Z-DRE-1",), maengel)


_GEWINDE = re.compile(r"\bM\d+(?:[.,]\d+)?")


def pruefe_gewinde(ist: Ist, plan: list[Mass], regeln: list[Regel]) -> dict:
    """Z-GEW-1: Jede Plan-Angabe eines Gewindes (Text beginnt mit M<Zahl> oder enthält „× M<Zahl>“) hat eine Notiz mit
    Bezeichnung und „tief“ (bei Durchgangsgewinde im Plan „durch“)."""
    notizen = [_norm(a.text) for a in ist.angaben if a.art == "hinweis"]
    maengel, gefunden = [], False
    for m in plan:
        text = _norm(m.text) if m.quelle == "angabe" else ""
        treffer = _GEWINDE.search(text)
        if not treffer or not (text.startswith("M") or "× M" in text):
            continue
        gefunden = True
        bezeichnung, anfang = treffer.group(), text[:treffer.end()]
        wort = "durch" if "durch" in text and "tief" not in text else "tief"
        notiz = next((n for n in notizen if n.startswith(anfang)), None)
        if notiz is None:
            maengel.append(_mangel(regeln, "Z-GEW-1", m.merkmal, f"Gewinde {bezeichnung}: keine Angabe gezeichnet"))
        elif wort not in notiz:
            maengel.append(_mangel(regeln, "Z-GEW-1", m.merkmal, f"Gewinde {bezeichnung}: Angabe ohne „{wort}“"))
    return _pruefung("gewinde", regeln, ("Z-GEW-1",), maengel, unpruefbar=None if gefunden else "kein Gewinde")
