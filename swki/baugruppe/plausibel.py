"""Plausibilität einer Baugruppen-Spezifikation (Spec 3b §5), ohne SolidWorks."""

from swki.baugruppe.aufloesen import anzahl_positionen, basis, je_position
from swki.baugruppe.modell import Quelle
from swki.baugruppe.passung import passung_befunde
from swki.spec.ausdruck import AusdruckFehler, auswerten

MIT_AUSRICHTUNG = ("deckungsgleich", "parallel", "abstand", "winkel")
MIT_WERT = ("abstand", "winkel")
BOHRUNGEN = ("normbohrung", "bohrung")


def _b(pfad: str, meldung: str) -> dict:
    return {"pfad": pfad, "meldung": meldung}


def _features(q: Quelle) -> dict:
    return {f["id"]: f for f in q.spec["features"]}


def _instanz_befunde(kid: str, k: str, pfad: str, spec: dict, quellen: dict) -> list[dict]:
    je = je_position(spec, k)
    if je and kid == k:
        return [_b(f"{pfad}.komponente", f"{k} hat je_position: Instanz angeben ({k}.1 …)")]
    if not je and kid != k:
        return [_b(f"{pfad}.komponente", f"{k} hat keine Instanzen (ohne .<n> angeben)")]
    if je and int(kid.split(".")[1]) > anzahl_positionen(spec, quellen, k):
        return [_b(f"{pfad}.komponente", f"{kid}: {je['komponente']}.{je['feature']} hat nicht so viele Positionen")]
    return []


def referenz_befunde(seite: dict, pfad: str, quellen: dict[str, Quelle], spec: dict,
                     instanz_id_erlaubt: bool = False) -> list[dict]:
    """Befunde einer Referenz (Verknüpfung) bzw. eines Messpunkts (instanz_id_erlaubt: komponente = Instanz-ID)."""
    kid = seite["komponente"]
    k = basis(kid) if instanz_id_erlaubt else kid
    if k not in quellen:
        return [_b(f"{pfad}.komponente", f"Komponente {kid!r} unbekannt")]
    befunde = _instanz_befunde(kid, k, pfad, spec, quellen) if instanz_id_erlaubt else []
    q = quellen[k]
    if q.art == "normteil":
        vorhanden = ", ".join(sorted(q.referenzen))
        if "referenz" not in seite:
            return befunde + [_b(pfad, f"{k} ist ein Normteil: nur über Einbaureferenzen ({vorhanden})")]
        if seite["referenz"] not in q.referenzen:
            return befunde + [_b(f"{pfad}.referenz",
                                 f"{q.norm} hat keine Einbaureferenz {seite['referenz']!r} (vorhanden: {vorhanden})")]
        return befunde
    features = _features(q)
    if "referenz" in seite:
        f = features.get(seite["referenz"])
        if f is None or f["typ"] != "referenz":
            befunde.append(_b(f"{pfad}.referenz", f"{q.datei} hat kein referenz-Feature {seite['referenz']!r}"))
    elif "feature" in seite:
        f = features.get(seite["feature"])
        if f is None:
            befunde.append(_b(f"{pfad}.feature", f"{q.datei} hat kein Feature {seite['feature']!r}"))
        elif "instanz" in seite:
            if f["typ"] not in BOHRUNGEN:
                befunde.append(_b(f"{pfad}.instanz", f"instanz nur bei normbohrung/bohrung ({seite['feature']} ist {f['typ']})"))
            elif isinstance(seite["instanz"], int) and seite["instanz"] > len(f["positionen"]):
                befunde.append(_b(f"{pfad}.instanz", f"{seite['feature']} hat nur {len(f['positionen'])} Positionen"))
    return befunde


def _komponenten_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    ids = [k["id"] for k in spec["komponenten"]]
    for i, kid in enumerate(ids):
        if kid in ids[:i]:
            befunde.append(_b(f"komponenten[{i}].id", f"ID {kid!r} ist doppelt"))
    fix = [k["id"] for k in spec["komponenten"] if k.get("fixiert")]
    if len(fix) != 1:
        befunde.append(_b("komponenten", f"genau eine Komponente muss fixiert sein (sind {len(fix)}: {', '.join(fix) or 'keine'})"))
    for i, k in enumerate(spec["komponenten"]):
        je = k.get("je_position")
        if not je:
            continue
        pfad = f"komponenten[{i}].je_position"
        if k.get("fixiert"):
            befunde.append(_b(pfad, "eine Komponente mit je_position kann nicht fixiert sein"))
        q = quellen.get(je["komponente"])
        if q is None or q.art != "teil" or je_position(spec, je["komponente"]):
            befunde.append(_b(f"{pfad}.komponente", f"{je['komponente']!r} ist kein Eigenteil ohne je_position"))
            continue
        f = _features(q).get(je["feature"])
        if f is None or f["typ"] not in BOHRUNGEN:
            befunde.append(_b(f"{pfad}.feature", f"{q.datei}: {je['feature']!r} ist keine normbohrung/bohrung"))
    return befunde


def _je_befunde(v: dict, pfad: str, spec: dict) -> list[dict]:
    je = {s: je_position(spec, v[s]["komponente"]) for s in ("a", "b") if je_position(spec, v[s]["komponente"])}
    befunde = []
    if len(je) == 2 and je["a"] != je["b"]:
        befunde.append(_b(pfad, "zwei Komponenten mit verschiedenem je_position: Instanzen lassen sich nicht paaren"))
    for s in ("a", "b"):
        if v[s].get("instanz") != "je":
            continue
        ziel = {"komponente": v[s]["komponente"], "feature": v[s].get("feature")}
        if not je:
            befunde.append(_b(f"{pfad}.{s}.instanz", "instanz: je nur zusammen mit einer Komponente mit je_position"))
        elif ziel not in je.values():
            befunde.append(_b(f"{pfad}.{s}.instanz", "instanz: je nur auf das Feature des je_position "
                                                     f"({', '.join(f'{x['komponente']}.{x['feature']}' for x in je.values())})"))
    return befunde


def _verknuepfung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    vs = spec.get("verknuepfungen", [])
    ids = [v["id"] for v in vs]
    p = spec.get("parameter", {})
    for i, v in enumerate(vs):
        pfad = f"verknuepfungen[{i}]"
        if v["id"] in ids[:i]:
            befunde.append(_b(f"{pfad}.id", f"ID {v['id']!r} ist doppelt"))
        for s in ("a", "b"):
            befunde += referenz_befunde(v[s], f"{pfad}.{s}", quellen, spec)
        if v["a"]["komponente"] == v["b"]["komponente"]:
            befunde.append(_b(pfad, "a und b gehören zur selben Komponente"))
        if v["typ"] in MIT_AUSRICHTUNG and "ausrichtung" not in v:
            befunde.append(_b(f"{pfad}.ausrichtung", f"ausrichtung (gleich | entgegengesetzt) ist bei {v['typ']} Pflicht"))
        if v["typ"] in MIT_WERT and "wert" not in v:
            befunde.append(_b(f"{pfad}.wert", f"wert ist bei {v['typ']} Pflicht"))
        if v["typ"] not in MIT_WERT and "wert" in v:
            befunde.append(_b(f"{pfad}.wert", "wert gilt nur bei abstand/winkel"))
        if "drehung_sperren" in v and v["typ"] != "konzentrisch":
            befunde.append(_b(f"{pfad}.drehung_sperren", "drehung_sperren gilt nur bei konzentrisch"))
        if "wert" in v:
            try:
                w = auswerten(v["wert"], p)
                if v["typ"] == "abstand" and w < 0:
                    befunde.append(_b(f"{pfad}.wert", f"abstand muss ≥ 0 sein (ist {w:g})"))
                if v["typ"] == "winkel" and not 0 <= w <= 180:
                    befunde.append(_b(f"{pfad}.wert", f"winkel muss in [0, 180] liegen (ist {w:g})"))
            except AusdruckFehler as e:
                befunde.append(_b(f"{pfad}.wert", str(e)))
        befunde += _je_befunde(v, pfad, spec)
    genannt = {v[s]["komponente"] for v in vs for s in ("a", "b")}
    for k in spec["komponenten"]:
        if not k.get("fixiert") and k["id"] not in genannt:
            befunde.append(_b("verknuepfungen", f"{k['id']} kommt in keiner Verknüpfung vor"))
    return befunde


def _freiheitsgrade_befunde(spec: dict) -> list[dict]:
    bekannt = {k["id"] for k in spec["komponenten"]} | {k["gruppe"] for k in spec["komponenten"] if k.get("gruppe")}
    return [_b(f"freiheitsgrade.{n}", f"{n!r} ist weder Komponente noch Gruppe")
            for n in spec.get("freiheitsgrade", {}) if n.split(".")[0] not in bekannt]


def _pruefung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    befunde = []
    pr = spec.get("pruefung", {})
    p = spec.get("parameter", {})
    werte = [("pruefung.huellquader", w) for w in pr.get("huellquader", [])]
    if "masse" in pr:
        werte.append(("pruefung.masse.soll", pr["masse"]["soll"]))
    for i, mp in enumerate(pr.get("masse_pruefen", [])):
        werte.append((f"pruefung.masse_pruefen[{i}].soll", mp["soll"]))
        for s in ("von", "zu"):
            if "komponente" in mp[s]:
                befunde += referenz_befunde(mp[s], f"pruefung.masse_pruefen[{i}].{s}", quellen, spec, instanz_id_erlaubt=True)
            else:
                werte += [(f"pruefung.masse_pruefen[{i}].{s}.punkt", w) for w in mp[s]["punkt"]]
    for pfad, w in werte:
        try:
            wert = auswerten(w, p)
        except AusdruckFehler as e:
            befunde.append(_b(pfad, str(e)))
            continue
        if pfad == "pruefung.masse.soll" and wert <= 0:  # die Prüfung rechnet die Abweichung in Prozent des Solls
            befunde.append(_b(pfad, f"Gesamtmasse (soll) muss größer als 0 sein (ist {wert:g} kg)"))
    return befunde


def plausibel_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Alle Plausibilitätsbefunde; Komponentenfehler zuerst (sonst lassen sich Instanzen nicht zählen)."""
    befunde = _komponenten_befunde(spec, quellen)
    if befunde:
        return befunde
    befunde = _verknuepfung_befunde(spec, quellen) + _freiheitsgrade_befunde(spec) + _pruefung_befunde(spec, quellen)
    return befunde + passung_befunde(spec, quellen)
