"""Maßplan einer Zeichnung (Z1.3 Stufe 2; Design §6.2, Recherche Kap. 4 und 8).

Je Merkmal genau ein Maß, je Richtung ein Bezug, keine geschlossene Kette.
- Frästeil: die protokollierten Anforderungsmaße des Baus (`protokoll.json`, `knoten[].masse`, Bemaßungsbezug) als
  Quelle `modell`; Hilfsebenen, Konstruktionsmaße, Mittellinien und Bohrungsfasen (Bohrungsangabe, Stufe 3) entfallen.
- Drehteil: Durchmesser je Absatz und Längen von einer Bezugsplanfläche aus dem Rotationsprofil (Quelle `neu`), dazu
  die Modellmaße der übrigen Features (Fasen, Bohrungen). Die Skizzenmaße des Profils (Radien, Lagen ab Ursprung)
  entfallen.
- Anforderungen (Stufe 4): Toleranz je Parameter an den Maßen, die ihn treiben (`Mass.toleranz`); Rauheit, Form/Lage und
  Bezüge als eigene Plan-Einträge (Quelle `rauheit`/`form_lage`/`bezug`, `wert` 0, kein Maß – Konsumenten filtern nach
  `quelle`).
"""

from dataclasses import dataclass, replace

from swki.spec.ausdruck import AusdruckFehler, auswerten, namen
from swki.spec.funktionen import FunktionFehler, aufloesen
from swki.spec.konturen import kontur_punkte_roh
from swki.zeichnung.angaben import _enthalten, bohrbilder, bohrungsangabe, reihenzusatz, zahl
from swki.zeichnung.ansichten import achsvektor, drehachse, elementpunkte, ist_drehteil, profilpunkte
from swki.zeichnung.toleranzangaben import (FormLage, Toleranz, form_lage_angaben, parameter_toleranzen, rauheitstext,
                                            treibende_parameter)

WEG_ARTEN = {"versatz", "konstruktion", "skript"}
_ARTEN = {"groesse": "laenge"}


@dataclass(frozen=True)
class Mass:
    id: str
    quelle: str                 # modell | neu | angabe | rauheit | form_lage | bezug (die letzten drei sind keine Maße)
    art: str                    # laenge | durchmesser | radius | tiefe | lage | paarabstand | abstand | winkel | fase | angabe
                                # | rauheit | form_lage | bezug
    wert: float
    merkmal: str                # Feature-ID der Spec
    name: str | None = None     # SolidWorks-Maßname ohne Dokument, z. B. "D3@t1_skizze" (nur modell)
    geometrie: dict | None = None  # nur neu: Lage in Modellkoordinaten entlang der Drehachse (mm)
    achse: int | None = None    # Normale der Skizzenebene bzw. Tiefenrichtung (0 = x, 1 = y, 2 = z)
    modus: str | None = None    # flach: Ansicht blickt entlang achse; quer: Ansicht blickt quer dazu
    bezug: str | None = None    # aus dem Maßprotokoll: ursprung | mitte | -rand | +rand | … (Mittellinien, Nutzer 18.11.)
    text: str | None = None     # nur angabe: Angabetext mit Zeilenumbrüchen (Stufe 3)
    praefix: str = ""           # Textzusatz vor dem Maßwert, z. B. "4 × "
    suffix: str = ""            # Textzusatz nach dem Maßwert, z. B. " (= 120)" oder " × 45°"
    toleranz: Toleranz | None = None   # Stufe 4: Toleranz des Parameters, der das Maß treibt (modell/neu)
    treiber: str | None = None  # Parameter, dessen Toleranz das Maß trägt (auch bei Ø in der Bohrungsangabe)
    treiber_alle: tuple[str, ...] = ()  # alle tolerierten Parameter im Ausdruck, wenn es mehr als einer ist
    form_lage: FormLage | None = None  # nur quelle form_lage
    anker: dict | None = None   # nur quelle bezug: Flächenanker aus `bezuege`


def _rund(x: float) -> float:
    return round(x, 6)


_EBENEN = {"vorne": 2, "oben": 1, "rechts": 0}


def _ebene_achse(ebene) -> int | None:
    """Normale einer Skizzenebene der Spec: Standardebene, Flächenanker {feature, flaeche: "+y"}, Versatzebene."""
    if isinstance(ebene, str):
        return _EBENEN.get(ebene)
    if isinstance(ebene, dict):
        if isinstance(ebene.get("flaeche"), str):
            return "xyz".index(ebene["flaeche"][1])
        if isinstance(ebene.get("versatz"), dict):
            return _ebene_achse(ebene["versatz"].get("ebene"))
    return None


def _achse_modus(features: dict, fid: str, pfad: str, tiefe: int = 0) -> tuple[int | None, str | None]:
    """Nutzer 18.11.2026: Skizzenmaße in die Ansicht senkrecht zur Skizzenebene, Tiefenmaße in eine Ansicht quer dazu."""
    f = features.get(fid) or {}
    if ".ende." in pfad:
        return _ebene_achse(f.get("skizze", {}).get("ebene")), "quer"
    for wort, schluessel in ((".profil.", "profil"), (".pfad.", "pfad"), (".skizze.", "skizze")):
        if wort in pfad:
            return _ebene_achse((f.get(schluessel) or {}).get("ebene")), "flach"
    typ = f.get("typ")
    if typ in ("bohrung", "normbohrung"):
        return _ebene_achse(f.get("flaeche")), "flach"
    quellen = (f.get("features", []) if typ in ("muster_linear", "muster_kreis", "spiegeln")
               else [k.get("feature") for k in f.get("kanten", []) if isinstance(k, dict)] if typ in ("verrundung", "fase")
               else [])
    for q in quellen:
        if tiefe < 3 and q in features:
            achse, _ = _achse_modus(features, q, ".skizze." if "skizze" in features[q] else "", tiefe + 1)
            if achse is not None:
                return achse, "flach"
    return None, None


def _skizze(pfad: str) -> str:
    """Teil des Spec-Pfads bis zur Skizze (features[7].pfad, features[7].profil, features[1].skizze …)."""
    for wort in (".pfad.", ".profil.", ".skizze."):
        if wort in pfad:
            return pfad.split(wort)[0] + wort
    return pfad.split(".")[0]


def _angabe_achse(spec: dict, f: dict) -> int | None:
    """Achse der Bohrungsangabe: Fläche der Bohrung, sonst Achse des umgebenden Kreismusters, sonst Drehachse."""
    achse = _ebene_achse(f.get("flaeche"))
    if achse is not None:
        return achse
    for m in _enthalten(spec, f["id"]):
        if m["typ"] == "muster_kreis" and m.get("achse") in ("x", "y", "z"):
            return "xyz".index(m["achse"])
    if ist_drehteil(spec) and any(g.get("typ") == "rotation" for g in spec.get("features", [])):
        return next(i for i, c in enumerate(achsvektor(spec)) if c)
    return None


def _angaben(spec: dict) -> tuple[list[Mass], list[str]]:
    """Je Bohrung/Normbohrung ein Angabe-Eintrag (Quelle angabe) und die Meldungen der Angabetexte."""
    bilder = bohrbilder(spec)
    tol = parameter_toleranzen(spec)
    plan, meldungen = [], []
    for f in spec.get("features", []):
        if f.get("typ") not in ("bohrung", "normbohrung"):
            continue
        text, meld = bohrungsangabe(f, spec, bilder[f["id"]])
        achse = _angabe_achse(spec, f)
        if achse is None:
            meld.append(f"ANGABE_OHNE_ACHSE: {f['id']}")
        meldungen += meld
        alle = treibende_parameter(f.get("durchmesser"), tol) if f["typ"] == "bohrung" else []
        treiber = alle[0] if alle else None
        plan.append(Mass(f"{f['id']}:angabe", "angabe", "angabe", 0.0, f["id"], text=text, achse=achse, modus="flach",
                         treiber=treiber, treiber_alle=tuple(alle) if len(alle) > 1 else ()))
    return plan, meldungen


def massplan_fraesteil(spec: dict, protokoll: dict, ohne: frozenset[str] = frozenset()) -> list[Mass]:
    """Modellmaße aus dem Maßprotokoll; `ohne`: Feature-IDs, deren Maße ein anderer Plan liefert (Drehprofil).

    Dazu je Bohrung eine Angabe (Stufe 3): Ø und Größe der Bohrung stehen dann im Angabetext, ebenso der Teilkreis
    (Lage einer Bohrung im Kreismuster ab Mitte/Ursprung entfällt); Teilungsmaß der Reihe und Fasen bekommen Textzusätze."""
    typ = {f["id"]: f.get("typ") for f in spec.get("features", [])}
    features = {f["id"]: f for f in spec.get("features", [])}
    bilder = bohrbilder(spec)
    im_kreismuster = {fid for fid in bilder if any(m["typ"] == "muster_kreis" for m in _enthalten(spec, fid))}
    reihen = {b.reihe: b for b in bilder.values() if b.reihe}
    tol = parameter_toleranzen(spec)
    plan, gesehen, punktmasse = [], set(), set()
    for knoten in protokoll.get("knoten", []):
        fid = knoten.get("id")
        if fid in ohne:
            continue
        for m in knoten.get("masse") or []:
            pfad = m.get("pfad", "")
            if m["art"] in WEG_ARTEN or "mittellinie" in pfad or pfad.endswith(".fase") or m["name"] in gesehen:
                continue
            if typ.get(fid) == "bohrung" and (m["art"] in ("durchmesser", "groesse", "tiefe") or ".senkung." in pfad):
                continue                                              # Ø, Tiefe und Senkung stehen in der Bohrungsangabe
            if typ.get(fid) == "fase" and m["art"] == "winkel":
                continue                                              # steht im Suffix des Fasenmaßes
            if fid in im_kreismuster and m["art"] == "lage" and m.get("bezug") in ("mitte", "ursprung"):
                continue                                              # Teilkreis steht in der Bohrungsangabe
            gesehen.add(m["name"])
            art = "fase" if typ.get(fid) == "fase" else _ARTEN.get(m["art"], m["art"])
            praefix, suffix = "", ""
            if art == "fase":
                try:
                    winkel = auswerten(features[fid].get("winkel", 45), spec.get("parameter", {}))
                except (ValueError, TypeError, KeyError):
                    winkel = 45
                suffix = f" × {zahl(winkel)}°"
            elif fid in reihen and m["art"] == "abstand":
                praefix, suffix = reihenzusatz(reihen[fid])
            if art == "lage":  # Punkte gleicher Lage (waagrechter Nutpfad) ergäben dasselbe Maß doppelt (Nutzer 18.11.2026)
                schluessel = (fid, _skizze(pfad), pfad[-3:], m.get("bezug") if not isinstance(m.get("bezug"), dict)
                              else str(m["bezug"]), _rund(m["wert"]))
                if schluessel in punktmasse:
                    continue
                punktmasse.add(schluessel)
            achse, modus = _achse_modus(features, fid, pfad)
            alle = treibende_parameter(m.get("roh"), tol)
            treiber = alle[0] if alle else None
            plan.append(Mass(m["name"], "modell", art, _rund(m["wert"]), fid, name=m["name"], achse=achse, modus=modus,
                             bezug=m.get("bezug"), praefix=praefix, suffix=suffix,
                             toleranz=tol.get(treiber), treiber=treiber,
                             treiber_alle=tuple(alle) if len(alle) > 1 else ()))
    return plan + _angaben(spec)[0]


def _roh_ausdruecke(e: dict) -> list[tuple[list, list]] | None:
    """Rohausdrücke je Eckpunkt eines Profilelements in der Reihenfolge von `elementpunkte`: je Punkt die Ausdrücke,
    aus denen u bzw. v entstehen (Rechteck: Mitte und Breite/Höhe). None = nicht lesbar."""
    if "polygon" in e:
        return [([p[0]], [p[1]]) for p in e["polygon"]["punkte"]]
    if "rechteck" in e:
        r = e["rechteck"]
        return [([r["mitte"][0], r["breite"]], [r["mitte"][1], r["hoehe"]])] * 4
    if "kontur" in e:
        return [([u], [v]) for u, v in kontur_punkte_roh(e["kontur"])]
    return None


def _namen_aus(ausdruecke: list) -> set[str]:
    aus: set[str] = set()
    for x in ausdruecke:
        if isinstance(x, str) and x.startswith("="):
            try:
                aus |= namen(x)
            except AusdruckFehler:
                pass
    return aus


def _profil_roh(f: dict, parameter: dict, achse: str) -> list[tuple[float, float, set[str], set[str]]]:
    """(Radius, Lage auf der Achse, Parameter im Radius, Parameter in der Lage) je Eckpunkt – Stufe 4: aus den rohen
    Punkten der Spec, nicht aus `profilpunkte` (dort sind die Ausdrücke schon ausgewertet)."""
    ir, ia = (0, 1) if achse == "v" else (1, 0)
    aus = []
    for e in f.get("skizze", {}).get("elemente", []):
        punkte, roh = elementpunkte(e, parameter), _roh_ausdruecke(e)
        if not punkte or roh is None or len(roh) != len(punkte):
            continue
        for p, rr in zip(punkte, roh):
            aus.append((abs(p[ir]), p[ia], _namen_aus(rr[ir]), _namen_aus(rr[ia])))
    return aus


def massplan_drehteil(spec: dict) -> list[Mass]:
    """Ø je Absatz (äußeres Profil, Bohrung, Einstichgrund) und Längen ab der Bezugsplanfläche, je Lage genau einmal.

    Bezug: die Stirnfläche (Profilsegment quer zur Achse) mit dem größten Ø, bei Gleichstand die mit der kleinsten Lage
    auf der Achse (Plan Task 2; Nutzer 18.11.2026: Außenstirn bleibt Bezug). Grund eines Rotationsschnitts (Review C1): Schnitt ab der Achse = Bohrung (Ø = 2·max r),
    Schnitt ab der Bohrung des Grundkörpers = Innennut (Grund = max r), sonst Außeneinstich (Grund = min r)."""
    parameter = spec.get("parameter", {})
    rotationen = [f for f in spec.get("features", []) if f.get("typ") == "rotation"]
    if not rotationen:
        return []
    tol = parameter_toleranzen(spec)
    roh = {f["id"]: _profil_roh(f, parameter, drehachse(f, parameter)) for f in rotationen} if tol else {}

    def treiber_von(vorhanden: set[str]) -> list[str]:
        return [p for p in tol if p in vorhanden]

    erste = rotationen[0]
    achse = drehachse(erste, parameter)
    punkte = profilpunkte(erste, parameter, achse)
    if not punkte:
        return []
    stirn: dict[float, float] = {}
    for (r0, a0), (r1, a1) in zip(punkte, punkte[1:] + punkte[:1]):
        if abs(a0 - a1) < 1e-9:
            stirn[_rund(a0)] = max(stirn.get(_rund(a0), 0), r0, r1)
    bezug = min(stirn, key=lambda a: (-stirn[a], a)) if stirn else min(a for _, a in punkte)
    r_innen = min(r for r, _ in punkte)

    plan: dict[str, Mass] = {}
    lagen_gesetzt: set[float] = {_rund(bezug)}
    durchmesser_gesetzt: set[tuple] = set()

    def durchmesser(fid: str, r: float, lagen: list[float]) -> None:
        schluessel = (_rund(r), _rund(min(lagen)), _rund(max(lagen)))
        if r > 1e-9 and schluessel not in durchmesser_gesetzt:  # Review I1: nach Lage, nicht nach Wert
            durchmesser_gesetzt.add(schluessel)
            mid = f"{fid}:d{_rund(2 * r)!r}@{schluessel[1]!r}-{schluessel[2]!r}"
            alle = treiber_von(set().union(*(rt for rr, _, rt, _ in roh.get(fid, []) if abs(rr - r) < 1e-6)))
            p = alle[0] if alle else None
            plan[mid] = Mass(mid, "neu", "durchmesser", _rund(2 * r), fid,
                             geometrie={"radius": r, "achse_von": min(lagen), "achse_bis": max(lagen)},
                             toleranz=tol.get(p), treiber=p, treiber_alle=tuple(alle) if len(alle) > 1 else ())

    def laenge(fid: str, a: float) -> None:
        if _rund(a) not in lagen_gesetzt:
            lagen_gesetzt.add(_rund(a))
            mid = f"{fid}:a{_rund(a)!r}"
            alle = treiber_von(set().union(*(at for _, aa, _, at in roh.get(fid, []) if abs(aa - a) < 1e-6)))
            p = alle[0] if alle else None
            plan[mid] = Mass(mid, "neu", "laenge", _rund(abs(a - bezug)), fid, geometrie={"von": bezug, "bis": _rund(a)},
                             toleranz=tol.get(p), treiber=p, treiber_alle=tuple(alle) if len(alle) > 1 else ())

    for r in sorted({r for r, _ in punkte}, reverse=True):
        durchmesser(erste["id"], r, [a for rr, a in punkte if rr == r])
    for a in sorted({_rund(a) for _, a in punkte}):
        laenge(erste["id"], a)
    for f in rotationen[1:]:
        pk = profilpunkte(f, parameter, drehachse(f, parameter))
        if not (f.get("schnitt") and pk):
            continue
        rs = [r for r, _ in pk]
        if min(rs) <= 1e-9:
            grund = max(rs)                                   # Bohrung auf der Achse
        elif r_innen > 1e-9 and abs(min(rs) - r_innen) < 1e-6:
            grund = max(rs)                                   # Innennut ab der Bohrung
        else:
            grund = min(rs)                                   # Außeneinstich
        durchmesser(f["id"], grund, [a for r, a in pk if abs(r - grund) < 1e-9] or [a for _, a in pk])
        for a in sorted({_rund(a) for _, a in pk}):
            laenge(f["id"], a)
    return list(plan.values())


def _anforderung_achse(spec: dict, f: dict) -> tuple[int | None, str | None]:
    """Achse und Modus für Rauheit und Form/Lage eines Features: Bohrung → Achse ihrer Angabe (flach); Schnitt und
    Extrusion → Achse der Skizze, Ansicht quer dazu (Endfläche bzw. Boden); sonst unbekannt."""
    typ = f.get("typ")
    if typ in ("bohrung", "normbohrung"):
        return _angabe_achse(spec, f), "flach"
    if typ in ("extrusion", "schnitt"):
        return _ebene_achse(f.get("skizze", {}).get("ebene")), "quer"
    return None, None


def _anforderungen(spec: dict) -> tuple[list[Mass], list[str]]:
    """Plan-Einträge für Rauheit, Form/Lage und Bezüge (keine Maße) und die Meldungen zu den Anforderungen."""
    plan, meldungen = [], []
    for f in spec.get("features", []):
        fid = f["id"]
        try:
            a = aufloesen(f)
        except FunktionFehler as e:
            meldungen.append(f"FUNKTION_UNBEKANNT: {fid}: {e}")
            continue
        if a["unbestaetigt"]:
            meldungen.append(f"FUNKTION_UNBESTAETIGT: {fid}: {', '.join(a['unbestaetigt'])}")
        if f.get("typ") in ("extrusion", "schnitt", "rotation") and (a["passung"] or a["toleranz"]):
            meldungen.append(f"TOLERANZ_OHNE_MASS: {fid}")
        achse, modus = _anforderung_achse(spec, f)
        if a["rauheit"]:
            plan.append(Mass(f"{fid}:rauheit", "rauheit", "rauheit", 0.0, fid, text=rauheitstext(a["rauheit"]),
                             achse=achse, modus=modus))
        angaben, meld = form_lage_angaben(fid, a["form_lage"] or [])
        meldungen += meld
        for i, x in enumerate(angaben):
            plan.append(Mass(f"{fid}:form_lage:{i}", "form_lage", "form_lage", 0.0, fid, text=x.wert, achse=achse,
                             modus=modus, form_lage=x))
    for name, anker in (spec.get("bezuege") or {}).items():
        plan.append(Mass(f"bezug:{name}", "bezug", "bezug", 0.0, anker.get("feature", ""), text=name, anker=dict(anker)))
    return plan, meldungen


def _namen_in(x) -> set[str]:
    """Alle Parameternamen in den Ausdrücken beliebig verschachtelter Werte."""
    if isinstance(x, str):
        return _namen_aus([x])
    if isinstance(x, dict):
        return set().union(*(_namen_in(v) for v in x.values()), set())
    if isinstance(x, (list, tuple)):
        return set().union(*(_namen_in(v) for v in x), set())
    return set()


def _benutzte_parameter(spec: dict, protokoll: dict | None) -> set[str]:
    """Parameter aus `toleranzen`, die ein Maß (oder den Ø einer Bohrungsangabe) treiben. Mit Maßprotokoll genau nach
    dem Maßplan; ohne es für Frästeile näherungsweise: der Parameter steht in einem Ausdruck eines Features."""
    if protokoll is not None:
        return {m.treiber for m in massplan(spec, protokoll) if m.treiber}
    benutzt = {m.treiber for m in massplan_drehteil(spec) if m.treiber}
    for f in spec.get("features", []):
        if f.get("typ") != "rotation":
            benutzt |= _namen_in(f)
    return benutzt


def massplan_meldungen(spec: dict, protokoll: dict | None = None) -> list[str]:
    """Meldungen zum Maßplan: Profilelemente von Rotationen, die der Maßplan nicht lesen kann (nie still weglassen),
    Angabetexte und (Stufe 4) Anforderungen: TOLERANZ_OHNE_MASS, FORM_LAGE_IT_OHNE_TABELLE, FUNKTION_UNBESTAETIGT.
    `protokoll`: das Maßprotokoll des Laufs – damit prüft TOLERANZ_OHNE_MASS genau, sonst näherungsweise."""
    parameter = spec.get("parameter", {})
    aus = []
    for f in spec.get("features", []):
        if f.get("typ") != "rotation":
            continue
        for e in f.get("skizze", {}).get("elemente", []):
            if elementpunkte(e, parameter) is None:
                aus.append(f"MASS_NICHT_GEPLANT: {f['id']} – Profilelement {next(iter(e))} wird nicht bemaßt")
    anforderung = _anforderungen(spec)[1]
    tol = parameter_toleranzen(spec)
    if tol:
        benutzt = _benutzte_parameter(spec, protokoll)
        aus += [f"TOLERANZ_OHNE_MASS: {p}" for p in tol if p not in benutzt]
        plan = massplan(spec, protokoll) if protokoll is not None else massplan_drehteil(spec) + _angaben(spec)[0]
        for m in plan:
            if m.treiber_alle:
                meldung = f"TOLERANZ_MEHRDEUTIG: {m.name or m.merkmal}: {', '.join(m.treiber_alle)}"
                if meldung not in aus:
                    aus.append(meldung)
    return aus + _angaben(spec)[1] + anforderung


def massplan(spec: dict, protokoll: dict) -> list[Mass]:
    """Maßplan je nach Teileart (Drehteil mit Rotationsprofil, sonst Frästeil), dazu die Anforderungseinträge."""
    rotationen = frozenset(f["id"] for f in spec.get("features", []) if f.get("typ") == "rotation")
    if ist_drehteil(spec) and rotationen:
        # Fasenmaße in die Ansicht quer zur Drehachse (Review Task 5, I5: in der Stirnansicht setzte D1@f2 an zwei
        # konzentrischen Kreisen an und ließ sich nicht als Zeichnungsmaß setzen)
        achse = next(i for i, c in enumerate(achsvektor(spec)) if c)
        plan = massplan_drehteil(spec) + [replace(m, achse=achse, modus="quer") if m.art == "fase" else m
                                          for m in massplan_fraesteil(spec, protokoll, ohne=rotationen)]
    else:
        plan = massplan_fraesteil(spec, protokoll)
    return plan + _anforderungen(spec)[0]
