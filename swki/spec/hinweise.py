"""Hinweise zu einer gültigen Spezifikation, die nicht verhindern, dass sie gebaut wird (Spec 2c §6.2).

art "feste_zahl": feste Zahlen in maßtragenden Feldern der Features deckt die Freigabe-Prüfsumme nicht ab (sie gehören
zum Bauweg). Anforderungsmaße sollen deshalb als Parameter geführt werden ("=Name"); validieren meldet die übrigen.
art "bezug": Lagekoordinaten ≠ 0 ohne Bemaßungsbezug auf dieser Achse (Positionen von bohrung/normbohrung, Mitte von
rechteck/kreis/langloch in Skizzen auf Flächen) – ohne Bezug wird zum Ursprung bemaßt.
art "zusammenfassen": Knoten, die sich nach den Modellierregeln (Skill konstruieren) für einen kompakteren
Feature-Baum zusammenfassen lassen, auch Kandidaten für Muster und Spiegeln (Regel 3).
art "fertigung": Innenecken unter der Fräserregel R ≥ T/5 (Regel 8) und Bohrungseintritte ohne Fase (Regel 6).
"""

import json

from swki.bemassung import ebene_ist_flaeche
from swki.spec.ausdruck import AusdruckFehler, auswerten
from swki.spec.konturen import eckradien, kontur_punkte
from swki.spec.normen import lade_tabelle

MASS_FELDER = frozenset({
    "tiefe", "durchmesser", "radius", "abstand", "winkel", "breite", "hoehe", "mitte", "punkte", "positionen", "von", "bis",
    "gewindetiefe", "laenge", "radien", "start", "linie", "bogen", "modul", "zaehne", "zahndickenabmass",
})
_ANKER = frozenset({"nahe", "kanten", "flaeche"})  # Anker wählen Geometrie aus, sie sind keine Maße
_TOL_NORM_MM = 0.01
_MUSTER = ("muster_linear", "muster_kreis", "spiegeln")
_NULL_MM = 1e-6  # Lage, unterhalb der eine Koordinate als 0 gilt
_BEZUG_ELEMENTE = ("rechteck", "kreis", "langloch")  # Elemente mit Bemaßungsbezug (Schema)


_KEINE_MASSE = _ANKER | {"mittellinie"}  # Rotationsachse: Konstruktionslinie, kein Anforderungsmaß
_SAMMELN = frozenset({"punkte", "kontur"})  # viele Koordinaten einer Kontur → ein Hinweis statt einer je Zahl


def _feste_zahlen(wert) -> int:
    if isinstance(wert, dict):
        return sum(_feste_zahlen(v) for v in wert.values())
    if isinstance(wert, list):
        return sum(_feste_zahlen(v) for v in wert)
    return int(isinstance(wert, (int, float)) and not isinstance(wert, bool) and wert != 0)


def _standardwert(feature_typ: str, schluessel: str, wert) -> bool:
    """Werte, die keine Anforderung tragen: Vollkreis 360° (Muster, Rotation), Fase 45°."""
    return schluessel == "winkel" and (wert == 360 or (feature_typ == "fase" and wert == 45))


def feste_masse(spec: dict) -> list[dict]:
    """Feste Zahlen ≠ 0 in maßtragenden Feldern der Features als [{"art", "pfad", "meldung"}] (0 = Lage auf Achse/Ebene).
    Konturen (polygon.punkte, kontur) ergeben je Element einen Sammelhinweis; Mittellinien, 360° und Fase 45° nie."""
    hinweise = []

    def melde(pfad: str, meldung: str) -> None:
        hinweise.append({"art": "feste_zahl", "pfad": pfad, "meldung": meldung})

    def gehe(wert, pfad: str, mass: bool, typ: str) -> None:
        if isinstance(wert, dict):
            for k, v in wert.items():
                if k in _KEINE_MASSE or _standardwert(typ, k, v):
                    continue
                if k in _SAMMELN:
                    if n := _feste_zahlen(v):
                        melde(f"{pfad}.{k}", f"{n} feste Zahlen in {k}: als Parameter führen, wenn die Kontur eine "
                                             "Anforderung ist, sonst deckt die Freigabe sie nicht ab")
                    continue
                gehe(v, f"{pfad}.{k}", mass or k in MASS_FELDER, typ)
        elif isinstance(wert, list):
            for i, v in enumerate(wert):
                gehe(v, f"{pfad}[{i}]", mass, typ)
        elif mass and isinstance(wert, (int, float)) and not isinstance(wert, bool) and wert != 0:
            melde(pfad, f"feste Zahl {wert:g}: als Parameter führen, sonst deckt die Freigabe dieses Maß nicht ab")

    for i, feature in enumerate(spec.get("features", [])):
        gehe(feature, f"features[{i}]", False, feature.get("typ", ""))
    return hinweise


def _bezug_meldung(achse: int) -> str:
    return (f"Lage ohne Bemaßungsbezug auf Achse {'uv'[achse]}: bezug angeben (mitte oder rand), "
            "sonst wird zum Ursprung bemaßt")


def bezug_hinweise(spec: dict) -> list[dict]:
    """Bemaßungsbezug (Spec §6): Lagekoordinate ≠ 0 ohne Bezug-Schlüssel auf der Achse, als Hinweis art "bezug" – in
    bohrung/normbohrung-Positionen (ein Hinweis je Achse am Feld positionen) und in rechteck/kreis/langloch auf einer
    Skizzenfläche (am Feld mitte). Nicht für Konturen, Mittellinien und Skizzen auf Standard- oder Versatzebenen; ein
    ausdrückliches `ursprung` unterdrückt den Hinweis, ein Ausdrucksfehler (anderswo gemeldet) den Hinweis der Achse."""
    parameter = spec.get("parameter", {})
    ergebnis = []

    def pruefe(punkte: list, bezug: dict | None, pfad: str) -> None:
        for achse in (0, 1):
            if "uv"[achse] in (bezug or {}):
                continue
            try:
                lage = [auswerten(p[achse], parameter) for p in punkte]
            except AusdruckFehler:
                continue
            if any(abs(x) > _NULL_MM for x in lage):
                ergebnis.append({"art": "bezug", "pfad": pfad, "meldung": _bezug_meldung(achse)})

    for i, f in enumerate(spec.get("features", [])):
        if f.get("typ") in ("bohrung", "normbohrung"):
            pruefe(f["positionen"], f.get("bezug"), f"features[{i}].positionen")
        elif "skizze" in f and ebene_ist_flaeche(f["skizze"]["ebene"]):
            for k, e in enumerate(f["skizze"]["elemente"]):
                for art in _BEZUG_ELEMENTE:
                    if art in e:
                        pruefe([e[art]["mitte"]], e[art].get("bezug"), f"features[{i}].skizze.elemente[{k}].{art}.mitte")
    return ergebnis


def _gruppen(features: list[dict], typen: tuple[str, ...], ohne: str) -> list[list[tuple[int, dict]]]:
    """Knoten gleichen Typs, die sich nur in id und dem Feld `ohne` unterscheiden (Reihenfolge des ersten Auftretens)."""
    gruppen: dict[str, list] = {}
    for i, f in enumerate(features):
        if f["typ"] in typen:
            schluessel = json.dumps({k: v for k, v in f.items() if k not in ("id", ohne)}, sort_keys=True, ensure_ascii=False)
            gruppen.setdefault(schluessel, []).append((i, f))
    return [g for g in gruppen.values() if len(g) > 1]


def _hinweis(eintraege: list[tuple[int, dict]], meldung: str) -> dict:
    return {"art": "zusammenfassen", "pfad": ", ".join(f"features[{i}]" for i, _ in eintraege),
            "knoten": [f["id"] for _, f in eintraege], "meldung": meldung}


def _iso_4762(f: dict, parameter: dict) -> str | None:
    """Größe, deren ISO-4762-Senkung (Durchgang und Senkungs-Ø laut Maßtabelle) die Bohrung mit Senkung trifft."""
    try:
        d, ds = auswerten(f["durchmesser"], parameter), auswerten(f["senkung"]["durchmesser"], parameter)
    except AusdruckFehler:
        return None
    for groesse, m in lade_tabelle()["normen"].get("ISO", {}).get("zylinderschraube", {}).items():
        if abs(d - m["durchgang"]) <= _TOL_NORM_MM and abs(ds - m["senkung_d"]) <= _TOL_NORM_MM:
            return groesse
    return None


_TEILUNG_TOL = 1e-6
_FORM_ELEMENTE = ("rechteck", "kreis", "langloch")  # Elemente mit `mitte`, die als Form gemustert/gespiegelt werden
_PROFIL_ELEMENTE = ("rechteck", "langloch")  # mehrere gleiche Profile einer Skizze (Kreise sind dort meist Löcher)


def _zahl(text: float) -> str:
    return f"{round(text, 6):g}".replace(".", ",")


def _reihe(punkte: list[tuple[float, float]]) -> tuple[int, float, str] | None:
    """Längste Reihe aus ≥ 3 Punkten auf einer Linie parallel zu u oder v mit gleicher Teilung: (Anzahl, Teilung, Achse)."""
    beste = None
    for achse in (0, 1):
        linien: dict[float, list[float]] = {}
        for p in punkte:
            linien.setdefault(round(p[1 - achse], 6), []).append(p[achse])
        for werte in linien.values():
            werte = sorted(werte)
            lauf = 1
            for k in range(1, len(werte)):
                schritt = werte[k] - werte[k - 1]
                if schritt > _TEILUNG_TOL and (lauf == 1 or abs(schritt - (werte[k - 1] - werte[k - 2])) <= _TEILUNG_TOL):
                    lauf += 1
                else:
                    lauf = 2 if schritt > _TEILUNG_TOL else 1
                if lauf >= 3 and (beste is None or lauf > beste[0]):
                    beste = (lauf, schritt, "uv"[achse])
    return beste


def _spiegelbildlich(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """Spiegelbildlich zu einer Mittelebene durch den Ursprung (u = 0 oder v = 0)."""
    gleich = lambda x, y: abs(x - y) <= _TEILUNG_TOL  # noqa: E731
    return ((gleich(a[0], -b[0]) and gleich(a[1], b[1]) and abs(a[0]) > _TEILUNG_TOL)
            or (gleich(a[1], -b[1]) and gleich(a[0], b[0]) and abs(a[1]) > _TEILUNG_TOL))


def _punkt(p, parameter: dict) -> tuple[float, float]:
    return (auswerten(p[0], parameter), auswerten(p[1], parameter))


def _form(f: dict) -> tuple[str, tuple] | None:
    """Schlüssel einer Form (Feature ohne id und ohne Lage seines einzigen Elements) und die Lage des Elements."""
    if f.get("typ") not in ("extrusion", "schnitt") or len(f["skizze"]["elemente"]) != 1:
        return None
    [element] = f["skizze"]["elemente"]
    art = next((a for a in _FORM_ELEMENTE if a in element), None)
    if art is None:
        return None
    ohne_lage = {**f, "id": None, "skizze": {**f["skizze"], "elemente": [{art: {**element[art], "mitte": None}}]}}
    return json.dumps(ohne_lage, sort_keys=True, ensure_ascii=False), element[art]["mitte"]


def muster_kandidaten(spec: dict) -> list[dict]:
    """Regel 3 (Paket Konstruktionsstil): Lochreihen ab 3 Stück, gleiche Formen in Reihe, zwei spiegelbildliche Formen
    und spiegelbildliche Profile einer Skizze als Hinweis art "zusammenfassen". Ausdrucksfehler meldet validieren."""
    features = spec.get("features", [])
    parameter = spec.get("parameter", {})
    ergebnis = []
    for i, f in enumerate(features):
        try:
            if f.get("typ") in ("bohrung", "normbohrung"):
                if reihe := _reihe([_punkt(p, parameter) for p in f["positionen"]]):
                    n, t, achse = reihe
                    ergebnis.append(_hinweis([(i, f)], f"{n} Positionen in einer Reihe (Teilung {_zahl(t)} mm in {achse}): "
                                                        "eine Position und muster_linear (Regel 3)"))
            elif "skizze" in f and len(f["skizze"]["elemente"]) >= 2:
                profile: dict[str, list] = {}
                for e in f["skizze"]["elemente"]:
                    art = next((a for a in _PROFIL_ELEMENTE if a in e), None)
                    if art:
                        schluessel = json.dumps({art: {**e[art], "mitte": None}}, sort_keys=True, ensure_ascii=False)
                        profile.setdefault(schluessel, []).append(_punkt(e[art]["mitte"], parameter))
                if any(len(m) == 2 and _spiegelbildlich(*m) for m in profile.values()):
                    ergebnis.append(_hinweis([(i, f)], "spiegelbildliche Profile in einer Skizze: ein Profil skizzieren "
                                                        "und spiegeln (Regel 3)"))
        except AusdruckFehler:
            continue
    formen: dict[str, list[tuple[int, dict, tuple]]] = {}
    for i, f in enumerate(features):
        if form := _form(f):
            formen.setdefault(form[0], []).append((i, f, form[1]))
    for gruppe in formen.values():
        try:
            lagen = [_punkt(m, parameter) for _, _, m in gruppe]
        except AusdruckFehler:
            continue
        eintraege = [(i, f) for i, f, _ in gruppe]
        if len(gruppe) == 2 and _spiegelbildlich(*lagen):
            ergebnis.append(_hinweis(eintraege, "zwei spiegelbildliche Formen: eine bauen und spiegeln (Regel 3)"))
        elif len(gruppe) >= 3 and (reihe := _reihe(lagen)) and reihe[0] == len(gruppe):
            ergebnis.append(_hinweis(eintraege, f"{len(gruppe)} gleiche Formen in einer Reihe (Teilung "
                                                f"{_zahl(reihe[1])} mm in {reihe[2]}): eine bauen und muster_linear "
                                                "(Regel 3)"))
    return ergebnis


def zusammenfassen(spec: dict) -> list[dict]:
    """Spec 2c §6.2 und Paket Konstruktionsstil: gleiche Bohrungen (Regel 2), gleiche Kantenmaße außerhalb von
    Musterquellen (Regel 6), Kandidaten für Muster und Spiegeln (Regel 3), Bohrung mit ISO-4762-Senkung (→ normbohrung,
    Regel 2)."""
    features = spec.get("features", [])
    parameter = spec.get("parameter", {})
    ergebnis = [_hinweis(g, "gleiche Bohrungen auf derselben Fläche: in einen Knoten mit mehreren positionen "
                            "zusammenfassen (Regel 2)")
                for g in _gruppen(features, ("bohrung", "normbohrung"), "positionen")]
    in_quellen = {q for f in features if f.get("typ") in _MUSTER for q in f["features"]}
    kanten = [f for f in features if f["id"] not in in_quellen]
    ergebnis += [_hinweis([(features.index(f), f) for _, f in g],
                          "gleiches Maß: Kanten in einem Knoten zusammenfassen (Regel 6)")
                 for g in _gruppen(kanten, ("fase", "verrundung"), "kanten")]
    ergebnis += muster_kandidaten(spec)
    for i, f in enumerate(features):
        if f["typ"] == "bohrung" and "senkung" in f and (groesse := _iso_4762(f, parameter)):
            ergebnis.append(_hinweis([(i, f)], f"Bohrung mit Senkung entspricht ISO 4762 {groesse}: als normbohrung "
                                               f"(art: zylinderschraube, groesse: {groesse}) führen (Regel 2)"))
    return ergebnis


FRAESER_TIEFE = 5.0  # R ≥ T/5: Schaftfräser Ø D bis 2,5·D Tiefe (Nutzer 01.11.2026, Ø 2 bis 5 mm)
_EINTRITT = {"gewinde": "fase: nenn", "stift": "fase: 0,5", "zylinderschraube": "fase: 0,5"}  # bohrung: fase: 0,5


def _fraestiefe(f: dict, nach_id: dict, parameter: dict) -> float | None:
    """Frästiefe an den Ecken eines Schnitts oder Aufsatzes: Tiefe bei blind/mittig, Dicke bei durch_alles, sonst None."""
    ende = f["ende"]
    if ende["typ"] in ("blind", "mittig"):
        return auswerten(ende["tiefe"], parameter)
    if ende["typ"] == "durch_alles" and f["typ"] == "schnitt":
        from swki.pruefung.geometrie import _dicke  # spät importiert: swki.pruefung nutzt swki.spec

        return _dicke(nach_id, f["skizze"]["ebene"], parameter)
    return None


def _ecken(punkte: list[tuple[float, float]], scharf: list[bool]) -> list[tuple[int, bool]]:
    """(Index, konvex) je scharfer Ecke eines geschlossenen Linienzugs; konvex gegen die Umlaufrichtung des Profils."""
    n = len(punkte)
    flaeche = sum(punkte[i][0] * punkte[(i + 1) % n][1] - punkte[(i + 1) % n][0] * punkte[i][1] for i in range(n))
    ecken = []
    for i in range(n):
        if not scharf[i]:
            continue
        a, b, c = punkte[i - 1], punkte[i], punkte[(i + 1) % n]
        kreuz = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(kreuz) > _NULL_MM:
            ecken.append((i, (kreuz > 0) == (flaeche > 0)))
    return ecken


def _eckradien(element: dict, parameter: dict) -> list[tuple[str, float, bool]] | None:
    """(Ort, Radius, konvex) je Ecke des Elements; None für Elemente ohne Ecken (Kreis, Langloch)."""
    if "rechteck" in element:
        r = auswerten(element["rechteck"].get("radius", 0), parameter)
        return [("Ecken", r, True)]
    if "polygon" in element:
        poly = element["polygon"]
        punkte = [_punkt(q, parameter) for q in poly["punkte"]]
        radien = eckradien(poly, parameter)
        return [(_ort(punkte[i]), radien[i], konvex) for i, konvex in _ecken(punkte, [True] * len(punkte))]
    if "kontur" in element:
        k = element["kontur"]
        punkte = kontur_punkte(k, parameter)[:-1]
        segmente = k["segmente"]
        # Ecke i liegt am Anfang von Segment i: scharf, wenn das Segment davor und dieses Linien sind
        scharf = ["linie" in segmente[i - 1] and "linie" in segmente[i] for i in range(len(segmente))]
        return [(_ort(punkte[i]), 0.0, konvex) for i, konvex in _ecken(punkte, scharf)]
    return None


def _ort(p: tuple[float, float]) -> str:
    return f"[{_zahl(p[0])}, {_zahl(p[1])}]"


def _innenecken(f: dict, element: dict, ist_profil: bool, parameter: dict) -> list[tuple[str, float]]:
    """Innenecken des Werkstücks (Ort, Radius): beim Schnitt und bei inneren Profilen eines Aufsatzes die konvexen
    Ecken des Profils, beim äußeren Profil eines Aufsatzes die konkaven."""
    ecken = _eckradien(element, parameter)
    if ecken is None:
        return []
    innen_konvex = f["typ"] == "schnitt" or not ist_profil
    return [(ort, r) for ort, r, konvex in ecken if konvex == innen_konvex]


def fertigung_hinweise(spec: dict) -> list[dict]:
    """Paket Konstruktionsstil: Innenecken unter der Fräserregel R ≥ T/5 (Regel 8; Radius aus der Skizze oder aus einem
    Knoten verrundung mit senkrechte_kanten auf dem Feature) und Bohrungseintritte ohne Feld fase (Regel 6) als
    Hinweis art "fertigung". Unbekannte Tiefe (bis_flaeche, versatz_von_flaeche) und Ausdrucksfehler: kein Hinweis."""
    features = spec.get("features", [])
    parameter = spec.get("parameter", {})
    nach_id = {f["id"]: f for f in features}
    ergebnis = []
    for i, f in enumerate(features):
        if f.get("typ") in ("bohrung", "normbohrung") and "fase" not in f:
            vorschlag = "fase: 0,5" if f["typ"] == "bohrung" else _EINTRITT.get(f["art"])
            if vorschlag:
                ergebnis.append({"art": "fertigung", "pfad": f"features[{i}]",
                                 "meldung": f"Bohrungseintritt ohne Fase: {vorschlag} (Regel 6)"})
            continue
        if f.get("typ") not in ("extrusion", "schnitt"):
            continue
        try:
            t = _fraestiefe(f, nach_id, parameter)
            if t is None:
                continue
            knoten_r = max((auswerten(v["radius"], parameter) for v in features if v.get("typ") == "verrundung"
                            and any(k.get("feature") == f["id"] and k.get("auswahl") == "senkrechte_kanten"
                                    for k in v["kanten"])), default=0.0)
            r_min = t / FRAESER_TIEFE
            for k, element in enumerate(f["skizze"]["elemente"]):
                ecken = [(ort, max(r, knoten_r)) for ort, r in _innenecken(f, element, k == 0, parameter)]
                if not ecken or (zu_klein := min(ecken, key=lambda e: e[1]))[1] >= r_min - _NULL_MM:
                    continue
                ort, r = zu_klein
                was = "scharfe Innenecke" if r <= _NULL_MM else f"Innenecke R {_zahl(r)}"
                stelle = "" if ort == "Ecken" else f" bei {ort}"
                ergebnis.append({"art": "fertigung", "pfad": f"features[{i}].skizze.elemente[{k}]",
                                 "meldung": f"{was}{stelle} bei Frästiefe {_zahl(t)}: R ≥ {_zahl(r_min)} (Fräser Ø ≥ "
                                            f"Tiefe/2,5), größer ist besser; kleiner nur mit Grund (Regel 8)"})
        except AusdruckFehler:
            continue
    return ergebnis


ABMASS_GROSS = 0.1  # × Modul (Spec 4b §4.3)


def verzahnung_hinweise(spec: dict) -> list[dict]:
    """Spec 4b §4.3: auffällig großes Zahndickenabmaß (|A_s| > 0,1·m) als Hinweis art "abmass_gross"."""
    ergebnis = []
    p = spec.get("parameter", {})
    for i, f in enumerate(spec.get("features", [])):
        if f.get("typ") != "verzahnung":
            continue
        try:
            m, a = auswerten(f["modul"], p), auswerten(f["zahndickenabmass"], p)
        except AusdruckFehler:
            continue
        if abs(a) > ABMASS_GROSS * m:
            ergebnis.append({"art": "abmass_gross", "pfad": f"features[{i}].zahndickenabmass",
                             "meldung": f"Zahndickenabmaß {a:g} mm ist größer als {ABMASS_GROSS:g}·m ({ABMASS_GROSS * m:g} "
                                        "mm) – Flankenspiel prüfen"})
    return ergebnis


def pruefwert_hinweise(spec: dict) -> list[dict]:
    """Retro Messstand: ein von Hand angegebener Hüllquader, der von der Rechnung aus den Features abweicht, als
    Hinweis art "pruefwert" – vor der Freigabe, denn danach kostet ein Rechenfehler eine neue Freigabe. Kein Befund:
    Schnitte, die den Hüllquader doch verkleinern, kennt die Rechnung nicht."""
    pr = spec.get("pruefung", {})
    if not isinstance(pr.get("huellquader"), list):
        return []
    from swki.pruefung.huellquader import huellquader_auto  # spät importiert: swki.pruefung nutzt swki.spec

    try:
        soll = [auswerten(v, spec.get("parameter", {})) for v in pr["huellquader"]]
    except AusdruckFehler:
        return []
    hq, _ = huellquader_auto(spec)
    tol = pr.get("huellquader_tol", 0.01)
    if hq is None or all(abs(a - b) <= tol for a, b in zip(hq, soll)):
        return []
    def text(werte: list[float]) -> str:
        return "[" + ", ".join(f"{x:g}" for x in werte) + "]"
    return [{"art": "pruefwert", "pfad": "pruefung.huellquader",
             "meldung": f"huellquader {text(soll)} weicht von der Rechnung aus den Features {text(hq)} ab – "
                        "Prüfwert nachrechnen oder huellquader: auto"}]


def hinweise(spec: dict) -> list[dict]:
    """Alle Hinweise für swki validieren: erst Prüfwerte, dann feste Zahlen, Bemaßungsbezug, Zusammenfassbares und
    Verzahnung. Hinweise blockieren nie (swki durchlauf --freigeben hält bei art "pruefwert" vor der Freigabe an)."""
    return (pruefwert_hinweise(spec) + feste_masse(spec) + bezug_hinweise(spec) + zusammenfassen(spec)
            + fertigung_hinweise(spec) + verzahnung_hinweise(spec))
