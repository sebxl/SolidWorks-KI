"""Folgeänderungen und Kinder aus der Bestandsaufnahme (Spec Bestandsdateien §4.3, §4.4 Punkt 3).

Reine Logik über das Dict aus `bestand.json`, ohne SolidWorks. Grundlage sind die Gleichungen (links hängt von den Namen in
Anführungszeichen auf der rechten Seite ab) und die Gruppen verknüpfter Maße (jedes Mitglied setzt alle, Plan
Präzisierung 1). Getriebene Maße gehen nie in die Folgen (sie folgen der Geometrie, nicht einem Punkt).
`kinder` der Aufnahme stammen aus `GetChildren` und kennen nur erklärte Abhängigkeiten (S18).
"""

import re
from collections import defaultdict, deque

_LINKS = re.compile(r'^\s*"[^"]*"\s*=(.*)$', re.DOTALL)
_NAME = re.compile(r'"([^"]+)"')


def rechte_seite(text: str) -> str:
    """Rechte Seite einer Gleichung `"links" = rechts` (ohne führende/folgende Leerzeichen); ohne `=` der ganze Text."""
    m = _LINKS.match(text)
    return (m.group(1) if m else text).strip()


def _namen(ausdruck: str) -> list[str]:
    return _NAME.findall(ausdruck)


def _nachbarn(aufnahme: dict) -> dict[str, set[str]]:
    """Name → Namen, die mitgehen, wenn er sich ändert: Gleichungen, die ihn rechts nennen, und Partner seiner Gruppe."""
    nachbarn: dict[str, set[str]] = defaultdict(set)
    for g in aufnahme.get("gleichungen", []):
        for name in _namen(rechte_seite(g["text"])):
            nachbarn[name].add(g["links"])
    gruppen: dict[str, set[str]] = defaultdict(set)
    for m in aufnahme.get("masse", []):
        if m.get("gruppe"):
            gruppen[m["gruppe"]].add(m["name"])
    for mitglieder in gruppen.values():
        for name in mitglieder:
            nachbarn[name] |= mitglieder - {name}
    return nachbarn


def _start(punkt: dict) -> str | None:
    if punkt.get("typ") == "mass":
        return punkt.get("mass")
    if punkt.get("typ") == "gleichung":
        return punkt.get("variable") or punkt.get("gleichung")
    return None


def folgen_von(punkt: dict, aufnahme: dict) -> list[str]:
    """Namen der Maße, die bei diesem Punkt mitgehen (sortiert): transitiv über Gleichungen und Variablen, dazu die
    Mitglieder verknüpfter Gruppen. Der Punkt selbst und getriebene Maße gehören nie dazu; nur Maße der Aufnahme."""
    start = _start(punkt)
    if start is None:
        return []
    nachbarn = _nachbarn(aufnahme)
    gesehen, offen = {start}, deque([start])
    while offen:
        for n in nachbarn.get(offen.popleft(), ()):
            if n not in gesehen:
                gesehen.add(n)
                offen.append(n)
    masse = {m["name"]: m for m in aufnahme.get("masse", [])}
    return sorted(n for n in gesehen - {start} if n in masse and masse[n].get("zustand") != "getrieben")


def kinder_von(feature: str, aufnahme: dict) -> list[str]:
    """Alle Features, die unter `feature` hängen (transitiv über `kinder`, sortiert; das Feature selbst nicht)."""
    kinder = {f["name"]: f.get("kinder", []) for f in aufnahme.get("features", [])}
    gesehen, offen = {feature}, deque([feature])
    while offen:
        for k in kinder.get(offen.popleft(), ()):
            if k not in gesehen:
                gesehen.add(k)
                offen.append(k)
    return sorted(gesehen - {feature})
