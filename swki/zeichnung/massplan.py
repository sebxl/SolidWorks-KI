"""Maßplan einer Zeichnung (Z1.3 Stufe 2; Design §6.2, Recherche Kap. 4 und 8).

Je Merkmal genau ein Maß, je Richtung ein Bezug, keine geschlossene Kette.
- Frästeil: die protokollierten Anforderungsmaße des Baus (`protokoll.json`, `knoten[].masse`, Bemaßungsbezug) als
  Quelle `modell`; Hilfsebenen, Konstruktionsmaße, Mittellinien und Bohrungsfasen (Bohrungsangabe, Stufe 3) entfallen.
- Drehteil: Durchmesser je Absatz und Längen von einer Bezugsplanfläche aus dem Rotationsprofil (Quelle `neu`), dazu
  die Modellmaße der übrigen Features (Fasen, Bohrungen). Die Skizzenmaße des Profils (Radien, Lagen ab Ursprung)
  entfallen.
"""

from dataclasses import dataclass

from swki.zeichnung.ansichten import drehachse, ist_drehteil, profilpunkte

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


def _rund(x: float) -> float:
    return round(x, 6)


def massplan_fraesteil(spec: dict, protokoll: dict, ohne: frozenset[str] = frozenset()) -> list[Mass]:
    """Modellmaße aus dem Maßprotokoll; `ohne`: Feature-IDs, deren Maße ein anderer Plan liefert (Drehprofil)."""
    typ = {f["id"]: f.get("typ") for f in spec.get("features", [])}
    plan, gesehen = [], set()
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
            plan.append(Mass(m["name"], "modell", art, _rund(m["wert"]), fid, name=m["name"]))
    return plan


def massplan_drehteil(spec: dict) -> list[Mass]:
    """Ø je Absatz (äußeres Profil, Bohrung, Einstichgrund) und Längen ab der Bezugsplanfläche.

    Bezug: die Stirnfläche (Profilsegment quer zur Achse) mit dem größten Ø, bei Gleichstand die mit der kleinsten Lage
    auf der Achse – die Anlagefläche (Plan Task 2)."""
    parameter = spec.get("parameter", {})
    rotationen = [f for f in spec.get("features", []) if f.get("typ") == "rotation"]
    if not rotationen:
        return []
    erste = rotationen[0]
    achse = drehachse(erste, parameter)
    punkte = profilpunkte(erste, parameter, achse)
    stirn: dict[float, float] = {}
    for (r0, a0), (r1, a1) in zip(punkte, punkte[1:] + punkte[:1]):
        if abs(a0 - a1) < 1e-9:
            stirn[_rund(a0)] = max(stirn.get(_rund(a0), 0), r0, r1)
    bezug = min(stirn, key=lambda a: (-stirn[a], a)) if stirn else min(a for _, a in punkte)

    plan: dict[str, Mass] = {}

    def durchmesser(fid: str, r: float, lagen: list[float]) -> None:
        mid = f"{fid}:d{_rund(2 * r):g}"
        if r > 1e-9 and mid not in plan and not any(m.art == "durchmesser" and m.wert == _rund(2 * r) for m in plan.values()):
            plan[mid] = Mass(mid, "neu", "durchmesser", _rund(2 * r), fid,
                             geometrie={"radius": r, "achse_von": min(lagen), "achse_bis": max(lagen)})

    def laenge(fid: str, a: float) -> None:
        wert = _rund(abs(a - bezug))
        mid = f"{fid}:l{wert:g}"
        if wert > 1e-9 and not any(m.art == "laenge" and m.wert == wert for m in plan.values()):
            plan[mid] = Mass(mid, "neu", "laenge", wert, fid, geometrie={"von": bezug, "bis": _rund(a)})

    for r in sorted({r for r, _ in punkte}, reverse=True):
        durchmesser(erste["id"], r, [a for rr, a in punkte if rr == r])
    for a in sorted({_rund(a) for _, a in punkte}):
        laenge(erste["id"], a)
    for f in rotationen[1:]:
        pk = profilpunkte(f, parameter, drehachse(f, parameter))
        if f.get("schnitt") and pk:
            r_grund = min(r for r, _ in pk)
            durchmesser(f["id"], r_grund, [a for r, a in pk if r == r_grund])
            for a in sorted({_rund(a) for _, a in pk}):
                laenge(f["id"], a)
    return list(plan.values())


def massplan(spec: dict, protokoll: dict) -> list[Mass]:
    """Maßplan je nach Teileart (Drehteil mit Rotationsprofil, sonst Frästeil)."""
    rotationen = frozenset(f["id"] for f in spec.get("features", []) if f.get("typ") == "rotation")
    if ist_drehteil(spec) and rotationen:
        return massplan_drehteil(spec) + massplan_fraesteil(spec, protokoll, ohne=rotationen)
    return massplan_fraesteil(spec, protokoll)
