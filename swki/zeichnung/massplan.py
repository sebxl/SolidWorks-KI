"""Maßplan einer Zeichnung (Z1.3 Stufe 2; Design §6.2, Recherche Kap. 4 und 8).

Je Merkmal genau ein Maß, je Richtung ein Bezug, keine geschlossene Kette.
- Frästeil: die protokollierten Anforderungsmaße des Baus (`protokoll.json`, `knoten[].masse`, Bemaßungsbezug) als
  Quelle `modell`; Hilfsebenen, Konstruktionsmaße, Mittellinien und Bohrungsfasen (Bohrungsangabe, Stufe 3) entfallen.
- Drehteil: Durchmesser je Absatz und Längen von einer Bezugsplanfläche aus dem Rotationsprofil (Quelle `neu`), dazu
  die Modellmaße der übrigen Features (Fasen, Bohrungen). Die Skizzenmaße des Profils (Radien, Lagen ab Ursprung)
  entfallen.
"""

from dataclasses import dataclass

from swki.zeichnung.ansichten import drehachse, elementpunkte, ist_drehteil, profilpunkte

WEG_ARTEN = {"versatz", "konstruktion", "skript"}
_ARTEN = {"groesse": "laenge"}


@dataclass(frozen=True)
class Mass:
    id: str
    quelle: str                 # modell | neu
    art: str                    # laenge | durchmesser | radius | tiefe | lage | paarabstand | abstand | winkel | fase
    wert: float
    merkmal: str                # Feature-ID der Spec
    name: str | None = None     # SolidWorks-Maßname ohne Dokument, z. B. "D3@t1_skizze" (nur modell)
    geometrie: dict | None = None  # nur neu: Lage in Modellkoordinaten entlang der Drehachse (mm)
    achse: int | None = None    # Normale der Skizzenebene bzw. Tiefenrichtung (0 = x, 1 = y, 2 = z)
    modus: str | None = None    # flach: Ansicht blickt entlang achse; quer: Ansicht blickt quer dazu


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


def massplan_fraesteil(spec: dict, protokoll: dict, ohne: frozenset[str] = frozenset()) -> list[Mass]:
    """Modellmaße aus dem Maßprotokoll; `ohne`: Feature-IDs, deren Maße ein anderer Plan liefert (Drehprofil)."""
    typ = {f["id"]: f.get("typ") for f in spec.get("features", [])}
    features = {f["id"]: f for f in spec.get("features", [])}
    plan, gesehen, punktmasse = [], set(), set()
    for knoten in protokoll.get("knoten", []):
        fid = knoten.get("id")
        if fid in ohne:
            continue
        for m in knoten.get("masse") or []:
            pfad = m.get("pfad", "")
            if m["art"] in WEG_ARTEN or "mittellinie" in pfad or pfad.endswith(".fase") or m["name"] in gesehen:
                continue
            gesehen.add(m["name"])
            art = "fase" if typ.get(fid) == "fase" else _ARTEN.get(m["art"], m["art"])
            if art == "lage":  # Punkte gleicher Lage (waagrechter Nutpfad) ergäben dasselbe Maß doppelt (Nutzer 18.11.2026)
                schluessel = (fid, _skizze(pfad), pfad[-3:], m.get("bezug") if not isinstance(m.get("bezug"), dict)
                              else str(m["bezug"]), _rund(m["wert"]))
                if schluessel in punktmasse:
                    continue
                punktmasse.add(schluessel)
            achse, modus = _achse_modus(features, fid, pfad)
            plan.append(Mass(m["name"], "modell", art, _rund(m["wert"]), fid, name=m["name"], achse=achse, modus=modus))
    return plan


def massplan_drehteil(spec: dict) -> list[Mass]:
    """Ø je Absatz (äußeres Profil, Bohrung, Einstichgrund) und Längen ab der Bezugsplanfläche, je Lage genau einmal.

    Bezug: die Stirnfläche (Profilsegment quer zur Achse) mit dem größten Ø, bei Gleichstand die mit der kleinsten Lage
    auf der Achse (Plan Task 2; Nutzer 18.11.2026: Außenstirn bleibt Bezug). Grund eines Rotationsschnitts (Review C1): Schnitt ab der Achse = Bohrung (Ø = 2·max r),
    Schnitt ab der Bohrung des Grundkörpers = Innennut (Grund = max r), sonst Außeneinstich (Grund = min r)."""
    parameter = spec.get("parameter", {})
    rotationen = [f for f in spec.get("features", []) if f.get("typ") == "rotation"]
    if not rotationen:
        return []
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
            plan[mid] = Mass(mid, "neu", "durchmesser", _rund(2 * r), fid,
                             geometrie={"radius": r, "achse_von": min(lagen), "achse_bis": max(lagen)})

    def laenge(fid: str, a: float) -> None:
        if _rund(a) not in lagen_gesetzt:
            lagen_gesetzt.add(_rund(a))
            mid = f"{fid}:a{_rund(a)!r}"
            plan[mid] = Mass(mid, "neu", "laenge", _rund(abs(a - bezug)), fid, geometrie={"von": bezug, "bis": _rund(a)})

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


def massplan_meldungen(spec: dict) -> list[str]:
    """Profilelemente von Rotationen, die der Maßplan nicht lesen kann (nie still weglassen)."""
    parameter = spec.get("parameter", {})
    aus = []
    for f in spec.get("features", []):
        if f.get("typ") != "rotation":
            continue
        for e in f.get("skizze", {}).get("elemente", []):
            if elementpunkte(e, parameter) is None:
                aus.append(f"MASS_NICHT_GEPLANT: {f['id']} – Profilelement {next(iter(e))} wird nicht bemaßt")
    return aus


def massplan(spec: dict, protokoll: dict) -> list[Mass]:
    """Maßplan je nach Teileart (Drehteil mit Rotationsprofil, sonst Frästeil)."""
    rotationen = frozenset(f["id"] for f in spec.get("features", []) if f.get("typ") == "rotation")
    if ist_drehteil(spec) and rotationen:
        return massplan_drehteil(spec) + massplan_fraesteil(spec, protokoll, ohne=rotationen)
    return massplan_fraesteil(spec, protokoll)
