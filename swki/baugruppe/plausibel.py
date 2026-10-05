"""Plausibilität einer Baugruppen-Spezifikation (Spec 3b §5, 4a §5, 4b §5.2), ohne SolidWorks."""

import math

from swki.baugruppe.aufloesen import GRENZEN, anzahl_positionen, basis, je_position
from swki.baugruppe.kopplung import (GEKOPPELT, KOPPLUNGEN, antriebsmenge, endlagen_wege, gekoppelte, soll_drehungen,
                                     verzahnung_der_seite)
from swki.baugruppe.modell import Quelle
from swki.baugruppe.passung import passung_befunde
from swki.konfig import lade_standard
from swki.spec.ausdruck import PI, AusdruckFehler, auswerten, ist_ausdruck

MIT_AUSRICHTUNG = ("deckungsgleich", "parallel", "abstand", "winkel", *GRENZEN)
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
        elif "instanz" in seite and f["typ"] == "verzahnung":
            if f["art"] != "stirnrad" or seite["instanz"] != 1 or not seite.get("achse"):
                befunde.append(_b(f"{pfad}.instanz", f"{seite['feature']}: nur die Radachse eines Stirnrads "
                                                     "({feature, instanz: 1, achse: true})"))
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


def _ist_eben(seite: dict, quellen: dict[str, Quelle]) -> bool:
    """Referenz einer Grenze ist eine ebene Fläche bzw. Ebene (Spec 4a §4.1, 4b §6.3): Fläche, Standardebene oder
    referenz-Ebene; nicht Achse, nicht Punktanker."""
    if "flaeche" in seite or "ebene" in seite:
        return True
    if "referenz" in seite:
        q = quellen[basis(seite["komponente"])]
        if q.art == "normteil":
            return "ACHSE" not in seite["referenz"]
        f = next((x for x in q.spec["features"] if x["id"] == seite["referenz"]), None)
        return f is not None and "ebene" in f
    return False


def _grenze_befunde(v: dict, pfad: str, p: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """min/max einer Grenzverknüpfung: Pflicht, 0 oder Parameter-Ausdruck (GRENZE_FESTE_ZAHL), min < max, Bereich;
    a und b ebene Flächen (GRENZE_REFERENZ)."""
    if v["typ"] not in GRENZEN:
        return [_b(f"{pfad}.{s}", "min/max gelten nur bei grenze_abstand/grenze_winkel") for s in ("min", "max") if s in v]
    befunde, werte = [], {}
    for s in ("a", "b"):
        if basis(v[s]["komponente"]) in quellen and not _ist_eben(v[s], quellen):
            befunde.append(_b(f"{pfad}.{s}", f"GRENZE_REFERENZ: {s} einer {v['typ']} ist eine ebene Fläche (flaeche, ebene "
                                             "oder referenz-Ebene), keine Achse und kein Punktanker"))
    for s in ("min", "max"):
        if s not in v:
            befunde.append(_b(f"{pfad}.{s}", f"{s} ist bei {v['typ']} Pflicht"))
            continue
        w = v[s]
        if not ist_ausdruck(w) and w != 0:
            befunde.append(_b(f"{pfad}.{s}", f"GRENZE_FESTE_ZAHL: {s} = {w:g} als Parameter-Ausdruck führen (\"=NAME\"); "
                                             "nur so schützt die Freigabe den Bewegungsbereich"))
            continue
        try:
            werte[s] = auswerten(w, p)
        except AusdruckFehler as e:
            befunde.append(_b(f"{pfad}.{s}", str(e)))
    if len(werte) == 2:
        unten, oben = werte["min"], werte["max"]
        if not unten < oben:
            befunde.append(_b(pfad, f"min ({unten:g}) muss kleiner als max ({oben:g}) sein"))
        elif v["typ"] == "grenze_abstand" and unten < 0:
            befunde.append(_b(f"{pfad}.min", f"grenze_abstand: min muss ≥ 0 sein (ist {unten:g})"))
        elif v["typ"] == "grenze_winkel" and not (0 <= unten and oben <= 360):
            befunde.append(_b(pfad, f"grenze_winkel: min und max müssen in [0, 360] liegen (sind {unten:g}, {oben:g})"))
    return befunde


def _scharnier_befunde(v: dict, pfad: str, spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Scharnier: a und b Achsen; anlage_a ebene Fläche der drehenden Komponente (a), anlage_b ebene Fläche des
    Gegenstücks, auf dem sie aufliegt – nicht unbedingt die Komponente von b (b ist oft der Drehbolzen; Spec 4a §4.2)."""
    if v["typ"] != "scharnier":
        return [_b(f"{pfad}.{s}", "anlage_a/anlage_b gelten nur bei scharnier") for s in ("anlage_a", "anlage_b") if s in v]
    befunde = []
    for s in ("a", "b"):
        if not (v[s].get("achse") or "referenz" in v[s]):
            befunde.append(_b(f"{pfad}.{s}", "scharnier: a und b sind Achsen (achse: true oder Achsreferenz wie EINBAU_ACHSE)"))
    for s in ("anlage_a", "anlage_b"):
        if s not in v:
            befunde.append(_b(f"{pfad}.{s}", f"{s} ist bei scharnier Pflicht (ebene Anlagefläche)"))
            continue
        befunde += referenz_befunde(v[s], f"{pfad}.{s}", quellen, spec)
        if v[s].get("achse"):
            befunde.append(_b(f"{pfad}.{s}", f"{s} ist eine ebene Fläche, keine Achse"))
    if "anlage_a" in v and v["anlage_a"]["komponente"] != v["a"]["komponente"]:
        befunde.append(_b(f"{pfad}.anlage_a.komponente", f"anlage_a gehört zur Komponente von a ({v['a']['komponente']})"))
    if "anlage_b" in v and v["anlage_b"]["komponente"] == v["a"]["komponente"]:
        befunde.append(_b(f"{pfad}.anlage_b.komponente", "anlage_b gehört zum Gegenstück, nicht zur Komponente von a"))
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
        befunde += _grenze_befunde(v, pfad, p, quellen) + _scharnier_befunde(v, pfad, spec, quellen)
        if v["typ"] in (*GRENZEN, "scharnier", *KOPPLUNGEN) and any(je_position(spec, v[s]["komponente"]) for s in ("a", "b")):
            befunde.append(_b(pfad, f"{v['typ']} nicht mit Komponenten mit je_position"))
    genannt = {v[s]["komponente"] for v in vs for s in ("a", "b")}
    for k in spec["komponenten"]:
        if not k.get("fixiert") and k["id"] not in genannt:
            befunde.append(_b("verknuepfungen", f"{k['id']} kommt in keiner Verknüpfung vor"))
    return befunde


def _freiheitsgrade_befunde(spec: dict) -> list[dict]:
    bekannt = {k["id"] for k in spec["komponenten"]} | {k["gruppe"] for k in spec["komponenten"] if k.get("gruppe")}
    befunde = [_b(f"freiheitsgrade.{n}", f"{n!r} ist weder Komponente noch Gruppe")
               for n in spec.get("freiheitsgrade", {}) if n.split(".")[0] not in bekannt]
    return befunde + [_b(f"freiheitsgrade.{n}", f"FREIHEITSGRADE_NICHT_UNTERSTUETZT: {w} Freiheitsgrade – in Stufe 4a "
                                                 "höchstens 1 je Komponente oder Gruppe")
                      for n, w in spec.get("freiheitsgrade", {}).items() if isinstance(w, int) and w > 1]


def bewegte_komponente(spec: dict, bewegung: dict) -> str | None:
    """Seite a der Grenzverknüpfung einer Bewegung, None wenn grenze keine Grenzverknüpfung ist."""
    v = next((x for x in spec.get("verknuepfungen", []) if x["id"] == bewegung["grenze"]), None)
    return v["a"]["komponente"] if v is not None and v["typ"] in GRENZEN else None


def _gruppe(spec: dict, kid: str) -> str | None:
    return next((k.get("gruppe") for k in spec["komponenten"] if k["id"] == kid), None)


def _endlage_befunde(e: dict, pfad: str, spec: dict, quellen: dict[str, Quelle], p: dict) -> list[dict]:
    kid = e["komponente"]
    if basis(kid) not in quellen:
        return [_b(f"{pfad}.komponente", f"Komponente {kid!r} unbekannt")]
    befunde = _instanz_befunde(kid, basis(kid), pfad, spec, quellen)
    werte = e["verschiebung"] if "verschiebung" in e else [*e["drehung"]["achse"], e["drehung"]["winkel"]]
    try:
        zahlen = [auswerten(w, p) for w in werte]
    except AusdruckFehler as ex:
        return befunde + [_b(pfad, str(ex))]
    if "drehung" in e and not any(zahlen[:3]):
        befunde.append(_b(f"{pfad}.drehung.achse", "Drehachse darf nicht der Nullvektor sein"))
    return befunde


def _bewegungen_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Spec 4a §4.3/§4.4 und Präzisierung 3."""
    befunde = []
    bws = spec.get("bewegungen", [])
    namen = [b["name"] for b in bws]
    fg = spec.get("freiheitsgrade", {})
    fix = {k["id"] for k in spec["komponenten"] if k.get("fixiert")}
    p = spec.get("parameter", {})
    genutzt: dict[str, str] = {}
    for i, b in enumerate(bws):
        pfad = f"bewegungen[{i}]"
        if b["name"] in namen[:i]:
            befunde.append(_b(f"{pfad}.name", f"Name {b['name']!r} ist doppelt"))
        kid = bewegte_komponente(spec, b)
        if kid is None:
            befunde.append(_b(f"{pfad}.grenze", f"{b['grenze']!r} ist keine grenze_abstand/grenze_winkel"))
            continue
        if b["grenze"] in genutzt:
            befunde.append(_b(f"{pfad}.grenze", f"Grenze {b['grenze']} treibt schon {genutzt[b['grenze']]}"))
        genutzt.setdefault(b["grenze"], b["name"])
        if kid in fix:
            befunde.append(_b(f"{pfad}.grenze", f"{kid} ist fixiert und kann sich nicht bewegen"))
        if fg.get(kid) != 1 and fg.get(_gruppe(spec, kid)) != 1:
            befunde.append(_b(f"{pfad}.grenze", f"Bewegung {b['name']}: {kid} braucht freiheitsgrade: 1 "
                                                "(Komponente oder Gruppe)"))
        for j, e in enumerate(b.get("erwartet", {}).get("endlagen", [])):
            befunde += _endlage_befunde(e, f"{pfad}.erwartet.endlagen[{j}]", spec, quellen, p)
    for n, w in fg.items():
        if w != 1:
            continue
        mitglieder = {n} | {k["id"] for k in spec["komponenten"] if k.get("gruppe") == n}
        anzahl = sum(1 for b in bws if bewegte_komponente(spec, b) in mitglieder)
        if anzahl == 0:
            befunde.append(_b(f"freiheitsgrade.{n}", f"BEWEGUNG_FEHLT: {n} hat freiheitsgrade: 1, aber keine Bewegung "
                                                     "treibt es"))
        elif anzahl > 1:
            befunde.append(_b(f"freiheitsgrade.{n}", f"BEWEGUNG_DOPPELT: {anzahl} Bewegungen treiben {n}"))
    return befunde


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


def _nur_feature(seite: dict) -> bool:
    """Referenzform {komponente, feature} (Verzahnung einer Kopplung)."""
    return set(seite) == {"komponente", "feature"}


def _verzahnung(seite: dict, quellen: dict[str, Quelle]) -> dict | None:
    q = quellen.get(basis(seite["komponente"]))
    if q is None or q.art != "teil" or not _nur_feature(seite):
        return None
    f = next((x for x in q.spec["features"] if x["id"] == seite["feature"]), None)
    return f if f is not None and f["typ"] == "verzahnung" else None


def _kopplung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Spec 4b §5.2: Art der Seiten (KOPPLUNG_ART), gleiche Module (MODUL_UNGLEICH), Reihenfolge und feste Seite b
    (KOPPLUNG_REIHENFOLGE); {komponente, feature} nur bei Kopplungen."""
    befunde = []
    vs = spec.get("verknuepfungen", [])
    fg = spec.get("freiheitsgrade", {})
    seite_a: dict[str, int] = {}  # Komponente → Index der Kopplung, in der sie Seite a ist
    for i, v in enumerate(vs):
        pfad = f"verknuepfungen[{i}]"
        if v["typ"] not in KOPPLUNGEN:
            befunde += [_b(f"{pfad}.{s}", "{komponente, feature} nur bei zahnrad/zahnstange; sonst flaeche, achse oder "
                                          "referenz angeben") for s in ("a", "b", "anlage_a", "anlage_b") if s in v and _nur_feature(v[s])]
            continue
        arten = {"a": "stirnrad", "b": "stirnrad" if v["typ"] == "zahnrad" else "zahnstange"}
        moduln = {}
        for s, art in arten.items():
            f = _verzahnung(v[s], quellen)
            if f is None or f["art"] != art:
                befunde.append(_b(f"{pfad}.{s}", f"KOPPLUNG_ART: {v['typ']}: {s} ist eine Verzahnung art: {art} "
                                                 "({komponente, feature})"))
            else:
                moduln[s] = verzahnung_der_seite(quellen, v[s]).geo.m
        if len(moduln) == 2 and abs(moduln["a"] - moduln["b"]) > 1e-9:
            befunde.append(_b(pfad, f"MODUL_UNGLEICH: Modul {moduln['a']:g} (a) und {moduln['b']:g} (b)"))
        ka, kb = v["a"]["komponente"], v["b"]["komponente"]
        if fg.get(ka) != GEKOPPELT:
            befunde.append(_b(f"{pfad}.a", f"KOPPLUNG_REIHENFOLGE: {ka} wird beim Bau in Phase gedreht und braucht "
                                           "freiheitsgrade: gekoppelt"))
        if ka in seite_a:
            befunde.append(_b(f"{pfad}.a", f"KOPPLUNG_REIHENFOLGE: {ka} ist schon Seite a von {vs[seite_a[ka]]['id']}"))
        seite_a.setdefault(ka, i)
        if fg.get(kb) == GEKOPPELT and seite_a.get(kb, i) >= i:
            befunde.append(_b(f"{pfad}.b", f"KOPPLUNG_REIHENFOLGE: {kb} steht beim Anlegen noch nicht fest (gekoppelt, "
                                           "aber nicht Seite a einer früheren Kopplung)"))
        spaeter = [w["id"] for w in vs[i + 1:] if w["typ"] not in KOPPLUNGEN
                   and {ka, kb} & {w[s]["komponente"] for s in ("a", "b", "anlage_a", "anlage_b") if s in w}]
        if spaeter:
            befunde.append(_b(pfad, f"KOPPLUNG_REIHENFOLGE: Kopplungen nach den übrigen Verknüpfungen von {ka} und {kb} "
                                    f"(danach noch: {', '.join(spaeter)})"))
    return befunde


def _kopplung_bewegung_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Spec 4b §5.2: GEKOPPELT_OHNE_ANTRIEB, ENDLAGE_FEHLT, UEBERSETZUNG_WIDERSPRUCH, SCHRITTE_ZU_GROB."""
    befunde = []
    p = spec.get("parameter", {})
    vorgabe = lade_standard()["bewegung_schritte"]
    getrieben: set[str] = set()
    grenzen = {v["id"]: v for v in spec.get("verknuepfungen", []) if v["typ"] in GRENZEN}
    for i, b in enumerate(spec.get("bewegungen", [])):
        pfad = f"bewegungen[{i}]"
        kid = bewegte_komponente(spec, b)
        if kid is None:
            continue
        menge = antriebsmenge(spec, kid)
        treibt = gekoppelte(spec, menge)
        getrieben |= set(treibt)
        endlagen = b.get("erwartet", {}).get("endlagen", [])
        drehungen = {e["komponente"] for e in endlagen if "drehung" in e}
        for k in treibt:
            if k not in drehungen:
                befunde.append(_b(f"{pfad}.erwartet.endlagen", f"ENDLAGE_FEHLT: {k} ist gekoppelt und braucht in "
                                                               f"{b['name']} eine Endlage drehung"))
        g = grenzen[b["grenze"]]
        if "min" not in g or "max" not in g:
            continue  # bereits bei den Grenzen gemeldet
        try:
            bereich = auswerten(g["max"], p) - auswerten(g["min"], p)
            soll = soll_drehungen(spec, quellen, menge, "abstand" if g["typ"] == "grenze_abstand" else "winkel", bereich,
                                  endlagen_wege(b, p))
            schritte = b.get("schritte", vorgabe)
            for j, e in enumerate(endlagen):
                if "drehung" not in e:
                    continue
                winkel = abs(auswerten(e["drehung"]["winkel"], p))
                epfad = f"{pfad}.erwartet.endlagen[{j}]"
                if e["komponente"] in soll and abs(winkel - soll[e["komponente"]]) > 0.01:
                    befunde.append(_b(epfad, f"UEBERSETZUNG_WIDERSPRUCH: {e['komponente']} dreht laut Übersetzung "
                                             f"{soll[e['komponente']]:.4f}°, erwartet sind {winkel:g}°"))
                if winkel / schritte >= 180:
                    befunde.append(_b(epfad, f"SCHRITTE_ZU_GROB: {winkel:g}° in {schritte} Schritten – mindestens "
                                             f"{math.floor(winkel / 180) + 1} Schritte"))
        except AusdruckFehler:
            continue  # bereits bei den Bewegungen gemeldet
    for n, w in spec.get("freiheitsgrade", {}).items():
        if w == GEKOPPELT and n not in getrieben:
            befunde.append(_b(f"freiheitsgrade.{n}", f"GEKOPPELT_OHNE_ANTRIEB: {n} erreicht über Kopplungen keine "
                                                     "Komponente oder Gruppe mit freiheitsgrade: 1 und Bewegung"))
    return befunde


def plausibel_befunde(spec: dict, quellen: dict[str, Quelle]) -> list[dict]:
    """Alle Plausibilitätsbefunde; Komponentenfehler zuerst (sonst lassen sich Instanzen nicht zählen)."""
    befunde = _komponenten_befunde(spec, quellen)
    if PI in spec.get("parameter", {}):
        befunde.append(_b(f"parameter.{PI}", f"{PI} ist die Kreiszahl und kein Parametername"))
    if befunde:
        return befunde
    befunde = (_verknuepfung_befunde(spec, quellen) + _freiheitsgrade_befunde(spec) + _pruefung_befunde(spec, quellen)
               + _bewegungen_befunde(spec, quellen))
    kopplung = _kopplung_befunde(spec, quellen)
    befunde += kopplung
    if not kopplung:
        befunde += _kopplung_bewegung_befunde(spec, quellen)
    return befunde + passung_befunde(spec, quellen)
