"""Reine Prüfungen der zurückgelesenen Zeichnung (Plan Z1.4, Design §8.1): Ist-Modell gegen Maßplan und Regelkatalog.

Jede Prüfung gibt ein dict `{id, regeln, ok, maengel, hinweis?}` zurück, Mängel haben die Form
`{regel, merkmal, text}`. `ok` ist True, False (harter Mangel) oder None (Hinweisregel oder nicht prüfbar, immer mit
`hinweis` bzw. Mängeln als Begründung). „Nicht prüfbar“ ist nie „ok“."""

import re
from dataclasses import replace
from pathlib import Path

from swki.zeichnung.angaben import _enthalten, zahl
from swki.zeichnung.blatt import FORMATE, SCHRIFTFELD_MM, zeichenfeld
from swki.zeichnung.ist import Ist, IstAngabe, IstMass, IstToleranz
from swki.zeichnung.lesbarkeit import pruefe_pdf, texte
from swki.zeichnung.massplan import Mass
from swki.zeichnung.regeln import Regel, regel
from swki.zeichnung.toleranzangaben import SAMMEL_RAUHEIT, Toleranz, sammelangaben, toleranztext

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


# SolidWorks-Symboltags, wie das Rücklesen sie an Maßen und Rahmen liefert (`bemassen.DURCHMESSER` = <MOD-DIAM>;
# Maximum-Material am Rahmen `<MOD-MMC>`, `anforderungen_setzen.form_lage_setzen`): Tag → Zeichen
_TAGS = {"<MOD-EP>": "Ⓔ", "<MOD-DIAM>": "Ø", "<MOD-MMC>": "Ⓜ"}


def normtext(text: str | None) -> str:
    """Vergleichstext: Symboltags (`<MOD-EP>` → Ⓔ, `<MOD-DIAM>` → Ø, `<MOD-MMC>` → Ⓜ) werden Zeichen, Leerraum wird
    zusammengefasst."""
    text = text or ""
    for tag, zeichen in _TAGS.items():
        text = text.replace(tag, zeichen)
    return " ".join(text.split())


_norm = normtext
_TRENNER = re.compile(r"(?:\s*(?:\r?\n|\s–(?=\s|$)))+\s*")
TRENNER = " – "


def angabentext(text: str | None) -> str:
    """Vergleichstext einer Bohrungsangabe (Runde D/E): Zeilenumbruch (auch CRLF), „ – “ und ein Strich am Zeilenende
    sind derselbe Trenner und werden `TRENNER` – die dreizeilige Form „2 × Ø8 H7 Ⓔ“ / „15 tief“ / „Fase …“ gleicht
    „2 × Ø8 H7 Ⓔ – 15 tief“ / „Fase …“; mehrere Trenner hintereinander sind einer. Ein fehlender Trenner („2 × Ø8 H7 Ⓔ
    15 tief“) ist ein Unterschied (Runde E: vorher galt jeder Trenner als Leerraum). Leerraum in den Abschnitten wird
    zusammengefasst, Symboltags werden Zeichen (`normtext`)."""
    return TRENNER.join(t for t in (normtext(a) for a in _TRENNER.split(" " + (text or "") + " ")) if t)


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


def _ohne_huelle(text: str) -> str:
    return normtext(normtext(text).replace("Ⓔ", ""))


def _zusatz_ok(ist: IstMass, m: Mass) -> bool:
    """Textzusatz exakt nach `normtext`: Ist-Präfix = Plan-Präfix, Ist-Suffix = Plan-Suffix, leer passt nur zu leer.
    Ⓔ bleibt auf beiden Seiten unberücksichtigt, ebenso das Durchmesser- bzw. Radiuszeichen am Ist-Präfix. Die Hülle
    prüft `pruefe_toleranzen` (Z-TOL-2, Task 3)."""
    zeichen = {"durchmesser": "Ø", "radius": "R"}.get(ist.art, "")
    praefix = _ohne_huelle(ist.praefix)
    if zeichen and praefix.endswith(zeichen):
        praefix = praefix[:-len(zeichen)].rstrip()
    return praefix == _ohne_huelle(m.praefix) and _ohne_huelle(ist.suffix) == _ohne_huelle(m.suffix)


def _gleich(a: float | None, b: float | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= _TOL_GLEICH + 1e-9


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
    Vorrang: Toleranz und Textzusatz passen, nur Toleranz, nur Zusatz, irgendein freies. Die Plan-Maße kommen in fester
    Reihenfolge dran (zuerst mit Zusatz, dann mit Toleranz, dann der Rest, je nach id), das Ergebnis hängt also nicht
    von der Reihenfolge in Plan oder Ist ab. Die Hülle Ⓔ prüft `pruefe_toleranzen` (Z-TOL-2, Task 3). Zweiter Wert:
    die nicht zugeordneten Ist-Maße."""
    frei = sorted((m for m in ist.masse if not m.klammer), key=lambda m: (m.ansicht, m.name))
    zuordnung: dict[str, IstMass | None] = {}
    offen = []
    for m in plan:
        if m.quelle in _MASSQUELLEN:
            zuordnung[m.id] = None
            if m.art in IST_ART:
                offen.append(m)
    offen.sort(key=lambda m: (0 if normtext(m.praefix) or normtext(m.suffix) else 1 if m.toleranz is not None else 2, m.id))
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
    notizen = [angabentext(a.text) for a in ist.angaben if a.art == "hinweis"]
    frei = list(range(len(notizen)))
    texte = []
    for m in plan:
        if m.quelle != "angabe":
            continue
        text = angabentext(m.text)
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
            maengel.append(_mangel(regeln, "Z-VOLL-2", "angabe", f"doppelt: Angabe {notizen[i].split(TRENNER)[0]}"))
    return maengel


def _cluster(koordinaten: list[float]) -> list[tuple[float, float]]:
    """Sortierte Koordinaten zu Knoten (von, bis), Complete-Linkage: ein Knoten reicht höchstens 0,05 mm über seinen
    kleinsten Wert hinaus."""
    knoten: list[list[float]] = []
    for x in sorted(koordinaten):
        if knoten and x - knoten[-1][0] <= _RASTER + 1e-9:
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
               for m in ist.masse if m.art == "durchmesser" and "Ø" not in normtext(m.praefix)]
    return _pruefung("drehteil", regeln, ("Z-DRE-1",), maengel)


_GEWINDE = re.compile(r"\bM\d+(?:[.,]\d+)?")


def pruefe_gewinde(ist: Ist, plan: list[Mass], regeln: list[Regel]) -> dict:
    """Z-GEW-1: Jede Plan-Angabe eines Gewindes (Text beginnt mit M<Zahl> oder enthält „× M<Zahl>“) hat eine Notiz mit
    Bezeichnung und „tief“ (bei Durchgangsgewinde im Plan „durch“)."""
    notizen = [angabentext(a.text) for a in ist.angaben if a.art == "hinweis"]
    maengel, gefunden = [], False
    for m in plan:
        text = angabentext(m.text) if m.quelle == "angabe" else ""
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


# --- Toleranzen und Anforderungen (Task 3) -----------------------------------------------------------------------------------

def _tol_text(i: IstToleranz) -> str:
    if i.typ == "keine":
        return "keine Toleranz"
    if i.typ == "passung":
        return i.passung or "Passung ohne Angabe"
    if i.oben is None or i.unten is None:
        return i.typ
    return toleranztext(Toleranz(None, i.oben, i.unten, False))


def _soll_text(m: Mass) -> str:
    t = m.toleranz
    return t.passung if t.passung else _tol_text(IstToleranz("bilateral", None, t.oben, t.unten))


def _traegt_huelle(c: IstMass) -> bool:
    return "Ⓔ" in normtext(f"{c.praefix} {c.suffix}")


def _huelle_plan(m: Mass) -> bool:
    return m.toleranz is not None and m.toleranz.huelle


def _fl_text(symbol: str, wert: str, bezug: tuple[str, ...]) -> str:
    return f"{symbol} {wert}" + (f" zu {'/'.join(bezug)}" if bezug else "")


_ANGABEN_REGEL = {"rauheit": "Z-TOL-4", "form_lage": "Z-TOL-5", "bezug": "Z-TOL-6"}   # Plan-Quelle → Regel


def _soll_anzahl(m: Mass, anzahl: dict[str, int] | None) -> int | None:
    """Instanzen des Merkmals (Form/Lage: „n ד über dem Rahmen, Task 4b); None: nicht verglichen."""
    return None if anzahl is None else int(anzahl.get(m.merkmal, 1))


def _inhalt_plan(m: Mass, anzahl: dict[str, int] | None = None) -> tuple:
    if m.quelle == "form_lage":
        wert = m.text + (" <MOD-MMC>" if m.form_lage.mmr else "")
        n = _soll_anzahl(m, anzahl)
        return (m.form_lage.symbol, normtext(wert), tuple(m.form_lage.bezug)) + (() if n is None else (n,))
    return (normtext(m.text),)


def _inhalt_ist(art: str, a, mit_anzahl: bool = False) -> tuple:
    if art == "form_lage":
        return (a.symbol or "", normtext(a.wert), tuple(a.bezug)) + ((a.anzahl or 1,) if mit_anzahl else ())
    return (normtext(a.text),)


def _mal(n: int | None) -> str:
    return f"{n} × " if n and n > 1 else ""


def _text_plan(m: Mass, anzahl: dict[str, int] | None = None) -> str:
    if m.quelle == "rauheit":
        return f"Rauheit {m.text}"
    if m.quelle == "form_lage":
        wert = m.text + (" Ⓜ" if m.form_lage.mmr else "")
        return "Form/Lage " + _mal(_soll_anzahl(m, anzahl)) + _fl_text(m.form_lage.art, wert, tuple(m.form_lage.bezug))
    return f"Bezug {m.text}"


def _text_ist(art: str, a) -> str:
    if art == "rauheit":
        return f"Rauheit {normtext(a.text)}"
    if art == "form_lage":
        return "Form/Lage " + _mal(a.anzahl) + _fl_text(a.symbol or "?", normtext(a.wert), tuple(a.bezug))
    return f"Bezug {normtext(a.text)}"


def _angaben_je_art(ist: Ist, plan: list[Mass], regeln: list[Regel],
                    anzahl: dict[str, int] | None = None) -> tuple[list[dict], list[str]]:
    """Rauheit, Form/Lage und Bezüge des Plans gegen `ist.angaben`. Hat eine IstAngabe ein Merkmal, gleicht Pass 1 je
    Merkmal ab; eine IstAngabe ohne Merkmal (das Rücklesen kennt es nicht immer) deckt in Pass 2 einen Plan-Eintrag
    gleichen Inhalts als Multimenge (Art, Text bzw. Symbol + Wert + Bezug). Eine IstAngabe mit anderem Merkmal deckt keinen.
    Zuletzt gilt ein übrig gebliebener Ist-Eintrag derselben Art (Form/Lage: gleiches Symbol; Bezüge: nie) als „weicht
    ab“, sonst „fehlt“. Was dann noch übrig ist, ist überzählig: mit Merkmal ein harter Mangel (keine Anforderung ohne
    Funktion), ohne Merkmal nur eine Meldung (zweiter Rückgabewert). `anzahl` (Merkmal → Instanzen,
    `anforderungen_setzen.instanzen`; Task 4b): bei Form/Lage gehört „n ד über dem Rahmen zum Inhalt; None: nicht
    verglichen."""
    maengel, meldungen = [], []
    for art, regel_id in _ANGABEN_REGEL.items():
        frei = [a for a in ist.angaben if a.art == art]
        offen = [m for m in plan if m.quelle == art]
        for je_merkmal in (True, False):
            rest = []
            for m in offen:
                treffer = next((a for a in frei if _inhalt_ist(art, a, anzahl is not None) == _inhalt_plan(m, anzahl)
                                and (a.merkmal == m.merkmal if je_merkmal else a.merkmal is None)), None)
                if treffer is None:
                    rest.append(m)
                else:
                    frei.remove(treffer)
            offen = rest
        for m in offen:
            nah = None if art == "bezug" else next(
                (a for a in frei if a.merkmal in (m.merkmal, None)
                 and (art != "form_lage" or (a.symbol or "") == m.form_lage.symbol)), None)
            if nah is None:
                maengel.append(_mangel(regeln, regel_id, m.merkmal, f"fehlt: {_text_plan(m, anzahl)} ({m.merkmal})"))
            else:
                frei.remove(nah)
                maengel.append(_mangel(regeln, regel_id, m.merkmal,
                                       f"weicht ab: {_text_ist(art, nah)} statt {_text_plan(m, anzahl)} ({m.merkmal})"))
        for a in frei:
            wort = _text_ist(art, a)
            if a.merkmal is None:
                meldungen.append(f"überzählige {wort} ohne Merkmal")
            else:
                maengel.append(_mangel(regeln, regel_id, a.merkmal, f"überzählig: {wort} ({a.merkmal})"))
    return maengel, meldungen


def pruefe_toleranzen(ist: Ist, plan: list[Mass], regeln: list[Regel], anzahl: dict[str, int] | None = None) -> dict:
    """Z-TOL-1 (Passung oder Abmaße weichen ab, Ⓔ fehlt am Passmaß), Z-TOL-2 (Ⓔ an einem Maß ohne Passung), Z-TOL-3
    (Toleranz ohne Funktion), Z-TOL-4/5/6 (Rauheit, Form/Lage, Bezüge). Maße ohne zugeordnetes Ist-Maß meldet
    `pruefe_vollstaendig`. `anzahl`: Instanzen je Merkmal für „n ד über dem Rahmen (Z-TOL-5; `bewerte` gibt sie
    immer mit)."""
    maengel = []
    zuordnung = zuordnen(ist, plan)
    for m in plan:
        c = zuordnung.get(m.id)
        if m.quelle not in _MASSQUELLEN or c is None:
            continue
        etikett = _etikett(c.art, m.wert)
        if m.toleranz is None:
            if c.toleranz.typ != "keine":
                maengel.append(_mangel(regeln, "Z-TOL-3", m.merkmal,
                                       f"{etikett}: Toleranz {_tol_text(c.toleranz)} ohne Funktion im Plan"))
        else:
            if not _toleranz_ok(c, m):
                maengel.append(_mangel(regeln, "Z-TOL-1", m.merkmal,
                                       f"{etikett}: Toleranz {_tol_text(c.toleranz)} statt {_soll_text(m)}"))
            if m.toleranz.huelle and not _traegt_huelle(c):
                maengel.append(_mangel(regeln, "Z-TOL-1", m.merkmal, f"{etikett}: Ⓔ fehlt an {_soll_text(m)}"))
        if _traegt_huelle(c) and not _huelle_plan(m):
            maengel.append(_mangel(regeln, "Z-TOL-2", m.merkmal, f"{etikett}: Ⓔ an einem Maß ohne Passung"))
    mehr, meldungen = _angaben_je_art(ist, plan, regeln, anzahl)
    p = _pruefung("toleranzen", regeln, ("Z-TOL-1", "Z-TOL-2", "Z-TOL-3", "Z-TOL-4", "Z-TOL-5", "Z-TOL-6"), maengel + mehr)
    if meldungen:
        p["meldungen"] = meldungen
    return p


# --- Sammelangaben, Schriftfeld, Lesbarkeit -------------------------------------------------------------------------------

_SAM_REGEL = ("Z-SAM-1", "Z-SAM-2", "Z-SAM-6", "Z-SAM-4")   # Reihenfolge von `sammelangaben`; danach Behandlung/Halbzeug
_BS = "[-–−‑]"   # Bindestrich, Gedankenstrich, Minus, geschützter Bindestrich
# „2768 mK“, „2768-mK“, „2768-m-K“, „2768-1 mK“, „2768 – mK“, „2768-1:1989 – mK“; nicht „2768-1:1989 – m“, nicht „… m Kanten“
_ISO_2768_K = re.compile(rf"2768(?:\s*{_BS}\s*\d?(?::\d{{4}})?)?\s*{_BS}?\s*[fmcv]?\s*{_BS}?\s*K\b", re.I)


def pruefe_sammelangaben(ist: Ist, spec: dict, regeln: list[Regel]) -> dict:
    """Jede Zeile von `sammelangaben(spec)` steht (normalisiert) im Text aller Notizen, dazu die Sammelrauheit (Z-SAM-7).
    Verboten (Z-SAM-3, je Notiz geprüft, damit „… 2768-1 m“ und eine Folgenotiz „K…“ kein „mK“ ergeben): „2768-…K“ und
    „DIN 7167“. Das Muster erlaubt Leerraum, verschiedene Striche, Jahr und Groß-/Kleinschreibung."""
    notizen = [normtext(a.text) for a in ist.angaben if a.art == "hinweis"]
    alle = " ".join(notizen)
    maengel = []
    for i, zeile in enumerate(sammelangaben(spec)):
        if normtext(zeile) not in alle:
            maengel.append(_mangel(regeln, _SAM_REGEL[i] if i < len(_SAM_REGEL) else "Z-SAM-5", "sammelangabe",
                                   f"fehlt: {zeile}"))
    if not re.search(re.escape(SAMMEL_RAUHEIT) + r"(?!\d)", alle):
        maengel.append(_mangel(regeln, "Z-SAM-7", "sammelangabe", f"fehlt: Sammelrauheit {SAMMEL_RAUHEIT}"))
    for n in notizen:
        if _ISO_2768_K.search(n) or "DIN 7167" in n:
            maengel.append(_mangel(regeln, "Z-SAM-3", "sammelangabe", f"verboten: {n}"))
    return _pruefung("sammelangaben", regeln, tuple(f"Z-SAM-{i}" for i in range(1, 8)), maengel)


_PFLICHT = (("sachnummer", "Sachnummer"), ("titel", "Benennung"), ("ersteller", "Ersteller"),
            ("ausgabedatum", "Ausgabedatum"), ("dokumentart", "Dokumentart"), ("blatt", "Blatt"))


def pruefe_schriftfeld(ist: Ist, standard: dict, regeln: list[Regel]) -> dict:
    """Pflichtfelder (Z-SCH-1), „Freigegeben“ leer (Z-SCH-2), Blattmaßstab aus der Vorzugsreihe (Z-SCH-3). Die Werte
    stehen in `ist.eigenschaften` unter den Namen aus `standard["zeichnung"]["schriftfeld"]`. Eigentümer leer ist nur
    ein Hinweis (`ok` None) bis Z1.5."""
    sf = (standard.get("zeichnung") or {}).get("schriftfeld") or {}

    def wert(feld: str) -> str:
        name = sf.get(feld, "")
        return (ist.eigenschaften.get(name) or "").strip() if name else ""

    maengel = []
    for feld, bezeichnung in _PFLICHT:
        if not wert(feld):
            maengel.append(_mangel(regeln, "Z-SCH-1", bezeichnung,
                                   f"Pflichtfeld {bezeichnung} leer (Eigenschaft {sf.get(feld) or 'nicht zugeordnet'})"))
    if wert("freigegeben"):
        maengel.append(_mangel(regeln, "Z-SCH-2", "Freigegeben", f"Feld Freigegeben ist gefüllt: {wert('freigegeben')}"))
    massstab = re.sub(r"\s+", "", ist.massstab or "")
    if not massstab:
        maengel.append(_mangel(regeln, "Z-SCH-3", "Maßstab", "Maßstab des Blatts fehlt"))
    elif massstab not in VORZUGSMASSSTAEBE:
        maengel.append(_mangel(regeln, "Z-SCH-3", "Maßstab", f"Maßstab {massstab} nicht aus der Vorzugsreihe"))
    unpruefbar = None if wert("eigentuemer") else "Eigentümer leer (bis Z1.5 nur Hinweis)"
    return _pruefung("schriftfeld", regeln, ("Z-SCH-1", "Z-SCH-2", "Z-SCH-3"), maengel, unpruefbar=unpruefbar)


def _ausschluss(format_: str) -> list[tuple]:
    """Rand, Rahmen und Schriftfeld gehören nicht zur Lesbarkeitsprüfung (wie `zeichnen._ausschluss`)."""
    b, h = FORMATE[format_]
    x0, y0, x1, y1 = zeichenfeld(format_)
    return [(0, 0, b, y0), (0, y1, b, h), (0, 0, x0, h), (x1, 0, b, h),
            (x1 - SCHRIFTFELD_MM[0], y0, x1, y0 + SCHRIFTFELD_MM[1])]


def rahmen_texte(ist: Ist) -> tuple[str, ...]:
    """Text je Toleranzrahmen, wie er im PDF als eine Zeile steht: Wert ohne Symboltags und die Bezüge, mit Leerzeichen
    (wie `zeichnen` die Rahmen an `pruefe_pdf` gibt: `Anmerkung.zeilen[0]`)."""
    aus = []
    for a in ist.angaben:
        if a.art == "form_lage":
            wert = " ".join(re.sub(r"<[^>]*>", " ", a.wert or "").split())
            aus.append(" ".join((wert,) + tuple(a.bezug)))
    return tuple(aus)


def pruefe_lesbarkeit(pdf: Path | None, format_: str, regeln: list[Regel], rahmen_texte: tuple[str, ...] = ()) -> dict:
    """Z-LES-1 (Hinweis): Befunde der PDF-Prüfung stehen in `maengel`, `ok` ist dann None. Ohne PDF, mit unbekanntem
    Format oder ohne pymupdf ist die Lesbarkeit nicht geprüft (`ok` None, mit Grund). `rahmen_texte` (Task 4b): Texte
    der Toleranzrahmen; ihre Zeilen im PDF gehen als gelegte Rahmen an `pruefe_pdf` (`rahmen=`), sonst gälte jede
    Zelltrennlinie als Linie durch den Text."""
    ids = ("Z-LES-1",)
    if pdf is None:
        return _pruefung("lesbarkeit", regeln, ids, [], unpruefbar="kein PDF: Lesbarkeit nicht geprüft")
    if format_ not in FORMATE:
        return _pruefung("lesbarkeit", regeln, ids, [], unpruefbar=f"Format {format_} unbekannt: Lesbarkeit nicht geprüft")
    try:
        rahmen = tuple((t, r) for t, r in texte(pdf) if t in set(rahmen_texte)) if rahmen_texte else ()
        befunde = pruefe_pdf(pdf, _ausschluss(format_), rahmen=rahmen)
    except ImportError:
        return _pruefung("lesbarkeit", regeln, ids, [], unpruefbar="pymupdf fehlt (Extra pdf): Lesbarkeit nicht geprüft")
    maengel = []
    for b in befunde:
        text = f"{b.art}: {b.text}" + (f" mit {b.anderes}" if b.anderes else "")
        maengel.append(_mangel(regeln, "Z-LES-1", b.art, f"{text} (bei {b.rechteck_mm[0]:.0f}/{b.rechteck_mm[1]:.0f} mm)"))
    return _pruefung("lesbarkeit", regeln, ids, maengel)


# --- Soll-Lücken und Gesamturteil -----------------------------------------------------------------------------------------

_LES, _VOLL = ("lesbarkeit", "Z-LES-1"), ("vollstaendig", "Z-VOLL-1")
# Meldungscode (Maßplan, `swki zeichnen`, Rückleser) → (Prüfung, Regel): die Meldung ist ein Mangel dieser Regel
# (Plan Z1.4 Task 4b, Nachtrag 2). Hinweisregeln (Z-LES-1) machen `ok` None, nie False.
MELDUNG_REGEL: dict[str, tuple[str, str]] = {
    # Lesbarkeit und Lage der Anmerkungen (Hinweis)
    "ANMERKUNG_KREUZT": _LES, "ANMERKUNG_ZU_NAH": _LES, "ANGABE_ZU_NAH": _LES, "ANSATZ_NICHT_FREI": _LES,
    "LESBARKEIT": _LES, "LESBARKEIT_UNGEPRUEFT": _LES, "SCHRAFFUR_UNGELESEN": _LES, "ANMERKUNG_NICHT_UMGEHAENGT": _LES,
    "SAMMELANGABE_FEHLT": _LES, "SAMMELANGABE_UEBERLAUF": _LES, "MASSE_NICHT_ANGEORDNET": _LES,
    "HILFSLINIE_NICHT_MITTELLINIE": _LES,
    # Bezeichnung der Ansichten, sichtbarer Bezug
    "EINZELHEIT_BUCHSTABE": ("ansichten", "Z-ANS-2"), "SCHNITT_BUCHSTABE": ("ansichten", "Z-ANS-2"),
    "BEZUG_OHNE_KANTE": ("ansichten", "Z-ANS-1"), "MITTELLINIE_NICHT_GEZEICHNET": ("ansichten", "Z-ANS-1"),
    # Anforderungen: Regel der Angabe
    "TOLERANZ_NICHT_GESETZT": ("toleranzen", "Z-TOL-1"), "TOLERANZ_OHNE_MASS": ("toleranzen", "Z-TOL-1"),
    "TOLERANZ_MEHRDEUTIG": ("toleranzen", "Z-TOL-1"), "FORM_LAGE_IT_OHNE_TABELLE": ("toleranzen", "Z-TOL-1"),
    "FUNKTION_UNBEKANNT": ("toleranzen", "Z-TOL-1"),
    "RAUHEIT_NICHT_GESETZT": ("toleranzen", "Z-TOL-4"), "RAUHEIT_NUR_EINE_INSTANZ": ("toleranzen", "Z-TOL-4"),
    "FORM_LAGE_NICHT_GESETZT": ("toleranzen", "Z-TOL-5"), "FORM_LAGE_NUR_EINE_INSTANZ": ("toleranzen", "Z-TOL-5"),
    "BEZUG_NICHT_GESETZT": ("toleranzen", "Z-TOL-6"),   # Plan nennt Z-TOL-3; Bezüge sind im Katalog Z-TOL-6
    "SAMMELANGABEN_NICHT_GESETZT": ("sammelangaben", "Z-SAM-1"),
    # Vollständigkeit: Maß bzw. Angabe fehlt oder steht doppelt
    "MASS_NICHT_DAUERHAFT": _VOLL, "MASS_NICHT_GEPLANT": _VOLL, "MASS_NICHT_GESETZT": _VOLL, "MASS_OHNE_ANSICHT": _VOLL,
    "ANGABE_NICHT_GESETZT": _VOLL, "ANGABE_OHNE_ANSICHT": _VOLL, "ANGABE_OHNE_HINWEISLINIE": _VOLL,
    "ANGABE_UNBEKANNT": _VOLL, "ANGABE_UNVOLLSTAENDIG": _VOLL, "ANGABE_OHNE_ACHSE": _VOLL,
    "RUECKLESEN_UNVOLLSTAENDIG": _VOLL,
    "ANGABE_DOPPELT": ("vollstaendig", "Z-VOLL-2"), "ANMERKUNG_DOPPELT": ("vollstaendig", "Z-VOLL-2"),
    "MASS_NICHT_GELOESCHT": ("vollstaendig", "Z-VOLL-2"),
}
# Codes, die nur im Bericht stehen (kein Mangel), mit Begründung. Alles andere ist ein unbekannter Code → Z-VOLL-1.
NUR_BERICHT: dict[str, str] = {
    "FUNKTION_UNBESTAETIGT": "C-Werte bestätigt der Nutzer (CLAUDE.md, Zeichnungsableitung); Hinweis",
    "LAUF_NICHT_BESTANDEN": "Urteil über das Teil, nicht über die Zeichnung (Zeichnung nur zur Ansicht)",
    "ANSICHT_DICHT": "Maß ist gezeichnet; die Obergrenze je Ansicht ist Hausregel, Lesbarkeit prüft Z-LES-1",
    "ANSICHT_VOLL": "wie ANSICHT_DICHT",
    "EINZELHEIT": "Protokoll der Ansichtswahl; Maße prüft „vollständig“, die Einzelheit Z-ANS-3",
    "EINZELHEIT_NICHT_FUER": "Protokoll der Ansichtswahl (kein Merkmal ausgelagert)",
    "EINZELHEIT_NICHT_ERZEUGT": "Protokoll der Ansichtswahl; Dichte zeigt Z-LES-1",
    "EINZELHEIT_ZU_GROSS": "Protokoll der Ansichtswahl",
    "ANSICHT_GERATEN": "Ansichtswahl ohne Anker; die Darstellung beurteilt der Zeichnungsprüfer",
    "ANSICHT_NICHT_GELOESCHT": "Ansicht ohne Maß blieb; beurteilt der Zeichnungsprüfer (kein Maß fehlt)",
    "SCHNITT_NICHT_ERZEUGT": "Projektion statt Schnitt; Maße ohne sichtbaren Bezug meldet Z-ANS-1 über `verdeckt`",
    "SCHNITT_NICHT_UNTERSTUETZT": "wie SCHNITT_NICHT_ERZEUGT",
    "ZEICHNUNG_GEAENDERT": "Kopfprüfung: `zeichnung_pruefen` setzt bestanden False",
    "ZEICHNUNG_PLAN_VERALTET": "Kopfprüfung: `zeichnung_pruefen` setzt bestanden False",
    "PDF_VERWORFEN": "Folge der Kopfprüfung; Lesbarkeit dann nicht geprüft (ok None)",
}
_CODE = re.compile(r"^([A-Z][A-Z_]+):")


def meldungscode(meldung: str) -> str | None:
    t = _CODE.match(meldung or "")
    return t.group(1) if t else None


def soll_luecken(meldungen: list[str]) -> list[dict]:
    """Meldungen (Maßplan `massplan_meldungen`, Übergabe von `swki zeichnen`, Rückleser) nach `MELDUNG_REGEL` als
    Mängel `{pruefung, regel, merkmal, text}`; gleicher Text zählt einmal. Codes aus `NUR_BERICHT` bleiben Meldungen.
    Ein unbekannter Code (oder eine Meldung ohne Code) ist ein Mangel Z-VOLL-1 „unbekannte Zeichnungsmeldung“ – nie
    still (Plan Task 4b, Nachtrag 2)."""
    aus, gesehen = [], set()
    for meldung in meldungen:
        if meldung in gesehen:
            continue
        gesehen.add(meldung)
        code = meldungscode(meldung)
        if code in NUR_BERICHT:
            continue
        rest = meldung.partition(": ")[2]
        if code in MELDUNG_REGEL:
            pruefung, regel_id = MELDUNG_REGEL[code]
            aus.append({"pruefung": pruefung, "regel": regel_id, "merkmal": re.split(r"[\s:]", rest)[0],
                        "text": meldung})
        else:
            aus.append({"pruefung": "vollstaendig", "regel": "Z-VOLL-1", "merkmal": code or "meldung",
                        "text": f"unbekannte Zeichnungsmeldung: {meldung}"})
    return aus


# --- Zuordnung nach dem Rücklesen (Task 4b) -----------------------------------------------------------------------------

_ART_QUELLE = {"hinweis": "angabe", "rauheit": "rauheit", "form_lage": "form_lage", "bezug": "bezug"}


def _gehoert(features: tuple[str, ...], namen: set[str]) -> bool:
    """Wie `anforderungen_setzen._zum_merkmal`: Feature-Name im Merkmal (samt Muster/Spiegel) oder ein Unter-Feature
    `<id>_…` (Positionsskizze, Fase einer Normbohrung)."""
    return any(n in namen or any(n.startswith(z + "_") for z in namen) for n in features)


def _inhalt_gleich(a: IstAngabe, m: Mass) -> bool:
    if a.art == "hinweis":
        return angabentext(a.text).startswith(angabentext(m.text))
    if a.art == "bezug":
        return normtext(a.text) == normtext(m.text)
    return _inhalt_ist(a.art, a) == _inhalt_plan(m)


def merkmale_zuordnen(ist: Ist, spec: dict, plan: list[Mass]) -> Ist:
    """Merkmal je Angabe aus den Features der angehängten Kante (`IstAngabe.features`), mit derselben
    `enthalten`-Logik wie beim Setzen (Merkmal, seine Muster und Spiegel, Unter-Features). Kandidaten sind die
    Plan-Merkmale mit einem Eintrag dieser Art; bei mehreren entscheidet der Inhalt (Text, Symbol + Wert + Bezug),
    bleibt es mehrdeutig, None. Gehört die Kante zu keinem: die Feature-IDs der Spec an der Kante (mehrere mit „/“) –
    die Angabe ist dann überzählig an diesem Merkmal (harter Mangel). Ohne Feature-Namen bzw. ohne Spec-Feature: None
    (überzählig nur als Meldung). Gesetzte Merkmale bleiben."""
    ids = [f["id"] for f in spec.get("features", [])]
    enthalten = {}
    for m in plan:
        if m.merkmal not in enthalten:
            enthalten[m.merkmal] = {m.merkmal} | {f["id"] for f in _enthalten(spec, m.merkmal)}
    neu = []
    for a in ist.angaben:
        quelle = _ART_QUELLE.get(a.art)
        if a.merkmal is not None or not a.features or quelle is None:
            neu.append(a)
            continue
        eintraege = [m for m in plan if m.quelle == quelle and _gehoert(a.features, enthalten[m.merkmal])]
        kandidaten = sorted({m.merkmal for m in eintraege})
        if len(kandidaten) > 1:
            kandidaten = sorted({m.merkmal for m in eintraege if _inhalt_gleich(a, m)})
            merkmal = kandidaten[0] if len(kandidaten) == 1 else None
        elif kandidaten:
            merkmal = kandidaten[0]
        else:
            eigene = sorted({i for i in ids if _gehoert(a.features, {i})})
            merkmal = "/".join(eigene) or None
        neu.append(replace(a, merkmal=merkmal))
    return replace(ist, angaben=tuple(neu))


def masse_umbenennen(ist: Ist, zeichnungsmasse: dict[str, str] | None) -> Ist:
    """Zeichnungsmaße (`RD<n>@<Ansicht>`), die `swki zeichnen` aus Modellmaßen gemacht hat (Übergabe
    `zeichnungsmasse`: Modellmaß → Zeichnungsmaß), tragen wieder den Plan-Namen."""
    zurueck = {neu: alt for alt, neu in (zeichnungsmasse or {}).items()}
    if not zurueck:
        return ist
    return replace(ist, masse=tuple(replace(m, name=zurueck.get(m.name, m.name)) for m in ist.masse))


def _nachtragen(p: dict, regeln: list[Regel], neu: list[dict]) -> None:
    p["maengel"] = p["maengel"] + neu
    if any(regel(regeln, m["regel"]).art == "hart" for m in p["maengel"]):
        p["ok"] = False
    elif p["ok"] is True and neu:
        p["ok"] = None


def bewerte(ist: Ist, plan: list[Mass], spec: dict, standard: dict, regeln: list[Regel], pdf: Path | None = None,
            meldungen=(), meldungen_soll=()) -> dict:
    """Alle neun Prüfungen und das Gesamturteil. `bestanden`: keine harte Prüfung mit `ok is False`; Hinweise und
    „nicht prüfbar“ (`ok` None) stehen im Bericht, machen aber nie `ok False`. `meldungen_soll` (aus
    `massplan_meldungen(spec, protokoll)`), `meldungen` (Übergabe von `swki zeichnen`, Kopfprüfung) und die Meldungen
    des Rücklesers (`ist.meldungen`) werden über `MELDUNG_REGEL` Mängel (`soll_luecken`), alle bleiben in `meldungen`.
    Die Instanzzahl über dem Rahmen kommt aus `anforderungen_setzen.instanzen(spec, merkmal)`."""
    from swki.zeichnung.anforderungen_setzen import instanzen  # spät: das Modul zieht pywin32 nach

    anzahl = {m.merkmal: instanzen(spec, m.merkmal) for m in plan if m.quelle == "form_lage"}
    pruefungen = {p["id"]: p for p in (
        pruefe_vollstaendig(ist, plan, regeln), pruefe_ueberbestimmt(ist, regeln),
        pruefe_toleranzen(ist, plan, regeln, anzahl), pruefe_sammelangaben(ist, spec, regeln),
        pruefe_schriftfeld(ist, standard, regeln), pruefe_ansichten(ist, regeln),
        pruefe_lesbarkeit(pdf, ist.format_, regeln, rahmen_texte(ist)), pruefe_gewinde(ist, plan, regeln),
        pruefe_drehteil(ist, plan, regeln))}
    alle = list(dict.fromkeys(list(meldungen_soll) + list(meldungen) + list(ist.meldungen)))
    for luecke in soll_luecken(alle):
        _nachtragen(pruefungen[luecke["pruefung"]], regeln, [{k: luecke[k] for k in ("regel", "merkmal", "text")}])
    zusatz = [m for p in pruefungen.values() for m in p.get("meldungen", [])]
    return {"bestanden": all(p["ok"] is not False for p in pruefungen.values()),
            "nicht_geprueft": [p["id"] for p in pruefungen.values() if p["ok"] is None],
            "pruefungen": list(pruefungen.values()),
            "maengel": [{"pruefung": p["id"], **m} for p in pruefungen.values() for m in p["maengel"]],
            "meldungen": list(dict.fromkeys(list(meldungen) + list(meldungen_soll) + list(ist.meldungen) + zusatz))}
