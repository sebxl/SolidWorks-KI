"""Abgleich Spec-Stand gegen Ist (Spec Bestandsdateien §8.6): Was wurde von Hand geändert? Rein, ohne SolidWorks.

Soll ist das Bauprotokoll eines Laufs (Knoten mit `sw_name`, Maßprotokoll, `komponenten`, `sha256`) plus die freigegebene Spec,
Ist die gelesene Aufnahme (Format `bestand.json`, Teile wie Etappe 1) oder der Export der Lagen. Der Abgleich benennt, was er
findet, und was er nicht prüfen konnte (`luecken`, `*_geprueft`): fehlen Daten, sagt er nie „unverändert“ und nie `vollstaendig`.

`nicht_erklaert` heißt: Der Vergleich fand nichts, was die geänderte Datei erklärt. Die Datei selbst ist dann trotzdem anders (der
Aufrufer kennt die SHA-256), und das darf niemand als „unverändert“ lesen. Was dieser Vergleich nicht sieht (gleicher Name, gleiche
Maße, aber eine Skizze verschoben oder eine andere Endbedingung; ganzzahlige Maße wie Anzahlen), deckt `--referenzbau` ab (§8.6)."""

import math
from pathlib import PureWindowsPath

from swki.aenderungen import mass_differenz
from swki.baugruppe.aufloesen import GRENZEN
from swki.baugruppe.sw_baugruppe import AUSRICHTUNG, MATE_KOPPLUNG, MATE_TYP
from swki.bestand.sw_bestand import ist_ordner
from swki.compiler.eigenschaften import eigenschaften_fuer, material_passt
from swki.spec.laden import COMPILER_ENDUNGEN, RESERVIERT

# Spec-Typ eines Features → zulässige IFeature.GetTypeName2. NUR BELEGTE NAMEN (Spikes docs/stufe0/ergebnisse: s9a_b6 Extrusion,
# s9a_b7 ICE, s9a_b8 Revolution/RevCut, s9b_b12 Fillet, s9b_b13 Chamfer, s9b_b14 LPattern, s9b_b15 CirPattern, s9b_b16 MirrorPattern,
# s10_f1 HoleWzd, s2/topologie RefPlane/RefAxis; `bohrung` baut mit FeatureCut4 wie `schnitt`). Ein Spec-Typ ohne Eintrag (skript,
# verzahnung) wird nicht verglichen, das steht als Lücke da, nie als Treffer. Task 12 ergänzt die Tabelle aus echten Dateien.
TYP_TABELLE = {
    "extrusion": frozenset({"Extrusion"}), "schnitt": frozenset({"ICE"}), "rotation": frozenset({"Revolution", "RevCut"}),
    "bohrung": frozenset({"ICE"}), "normbohrung": frozenset({"HoleWzd"}), "verrundung": frozenset({"Fillet"}),
    "fase": frozenset({"Chamfer"}), "muster_linear": frozenset({"LPattern"}), "muster_kreis": frozenset({"CirPattern"}),
    "spiegeln": frozenset({"MirrorPattern"}), "referenz": frozenset({"RefPlane", "RefAxis"}),
}
# Typen, die ein Teil aus der Vorlage mitbringt. Alles andere, was nicht aus dem Soll stammt, zählt als neu: Ein Fehlalarm ist billiger
# als ein Verschweigen. Nach den ersten echten Dateien hier ergänzen, nicht vorher.
MAX_STANDARDEBENEN = 3
# Skizzen, die der Compiler selbst benennt (`<id><Endung>` aus `COMPILER_ENDUNGEN`), und die Knoten-Typen, an denen er sie anlegt.
# `_senkung` ist ein Feature der Bohrung, seine Skizze heißt `<id>_senkung_skizze`.
_SKIZZE_AM_KNOTEN = {"_skizze": frozenset({"extrusion", "schnitt", "rotation", "bohrung", "verzahnung"}),
                     "_senkung": frozenset({"bohrung"}), "_positionen": frozenset({"normbohrung"})}
_MUSTER_TYPEN = frozenset({"muster_linear", "muster_kreis"})   # legen Referenzachsen `achse_x|y|z` an (handler/muster.py)
VERKNUEPFUNGS_TYPEN = frozenset(MATE_TYP) | frozenset(MATE_KOPPLUNG)
_MIT_WERT = {"abstand": ("wert",), "winkel": ("wert",), "grenze_abstand": ("wert", "min", "max"),
             "grenze_winkel": ("wert", "min", "max")}
_TOL_LAGE = 1e-5   # Lage nach Transform2.ArrayData: Verschiebung in m (10 µm), Drehanteile ohne Einheit
_MATE_NAMEN = {code: typ for typ, code in {**MATE_TYP, **MATE_KOPPLUNG}.items() if typ not in GRENZEN}   # swMateType_e → Spec-Typ
_AUSRICHTUNG_NAMEN = {code: name for name, code in AUSRICHTUNG.items()}
_EINHEITEN_MASS = ("mm", "Grad")   # ganzzahlige Maße (Anzahl im Muster) tragen keine Einheit und stehen nicht im Maßprotokoll


def mate_name(code, grenze: bool = False) -> str:
    """Spec-Typ zu einem swMateType_e; Abstand und Winkel mit Grenzen (`grenze`) heißen `grenze_abstand` bzw. `grenze_winkel`."""
    if grenze:
        for name in GRENZEN:
            if MATE_TYP[name] == code:
                return name
    return _MATE_NAMEN.get(code, f"typ {code}")


# --- Dateien --------------------------------------------------------------------------------------------------------

def _schluessel(rel: str) -> str:
    return rel.replace("\\", "/").lower()


def abgleich_dateien(soll: dict[str, str], ist: dict[str, str]) -> dict[str, list[str]]:
    """Dateien (relativer Pfad → SHA-256): `geaendert` (andere SHA-256), `neu` (ohne Protokolleintrag, auch Normteil-Kopien: sie
    tragen kein Soll, nur die SHA-Aussage), `fehlend` (im Protokoll, nicht im Ist). Namen ohne Beachtung der Schreibweise."""
    s = {_schluessel(rel): (rel, sha) for rel, sha in soll.items()}
    i = {_schluessel(rel): (rel, sha) for rel, sha in ist.items()}
    return {"geaendert": sorted(rel for k, (rel, sha) in i.items() if k in s and s[k][1] != sha),
            "neu": sorted(rel for k, (rel, _) in i.items() if k not in s),
            "fehlend": sorted(rel for k, (rel, _) in s.items() if k not in i)}


# --- Teile ----------------------------------------------------------------------------------------------------------

def _knoten_namen(knoten: dict) -> list[str]:
    """SolidWorks-Namen eines Knotens: `sw_namen` einzeln (Bestandsdatei), sonst `sw_name` an ", " zerlegt (Compiler: Namen aus
    Ids, ohne Komma)."""
    if knoten.get("sw_namen"):
        return list(knoten["sw_namen"])
    name = knoten.get("sw_name")
    return [n for n in name.split(", ") if n] if name else []


def _vorlage_namen(alle: dict[str, dict]) -> set[str]:
    """Features, die die Vorlage mitbringt: die ersten drei Ebenen ohne Eltern und der Ursprung, in der Reihenfolge des Baums (die
    Standardebenen stehen immer vor allem Eigenen). Jede weitere Ebene gehört nicht dazu."""
    namen, ebenen, ursprung = set(), 0, 0
    for name, f in alle.items():
        if f.get("typ") == "RefPlane" and not f.get("eltern") and ebenen < MAX_STANDARDEBENEN:
            ebenen += 1
            namen.add(name)
        elif f.get("typ") == "OriginProfileFeature" and not ursprung:
            ursprung = 1
            namen.add(name)
    return namen


def _hilfsskizzen(knoten_typen: dict[str, str]) -> set[str]:
    """Namen der Skizzen, die der Compiler am jeweiligen Knoten-Typ anlegt (`<id>_skizze`, `<id>_positionen`, `<id>_senkung_skizze`)."""
    return {f"{name}{ende}" + ("_skizze" if ende == "_senkung" else "")
            for name, typ in knoten_typen.items() for ende in COMPILER_ENDUNGEN if typ in _SKIZZE_AM_KNOTEN.get(ende, ())}


def ist_erklaert(feature: dict, soll: set[str], alle: dict[str, dict], knoten_typen: dict[str, str] | None = None,
                 hilfsnamen: frozenset[str] | set[str] = frozenset()) -> bool:
    """Gehört das Feature zum Spec-Stand? `soll`: SolidWorks-Namen der Knoten aus dem Bauprotokoll, `alle`: Ist-Features nach Name,
    `knoten_typen`: Spec-Typ je Knoten-Name, `hilfsnamen`: Feature-Namen hinter `@` im Maßprotokoll.

    Erklärt ist es, wenn es (1) im Soll steht, (2) aus der Vorlage kommt (Ursprung, Standardebenen, Ordner), (3) Unterfeature eines
    Soll-Features ist, und zwar eine Skizze (`ProfileFeature`) oder beliebiges unter einem Bohrungsassistenten (`HoleWzd`: Gewinde,
    Kosmetikgewinde), (4) eine Skizze oder Ebene ist, deren Maß das Maßprotokoll nennt (`D1@Ebene1`), (5) eine Hilfsskizze des
    Compilers am passenden Knoten-Typ ist (`<id>_skizze`, `<id>_positionen`) oder (6) eine Referenzachse `achse_x|y|z` bei einem
    Muster. Eltern und Kinder erklären nichts: Ein neues Feature an einem Soll-Feature hängt an ihm."""
    name, typ = feature["name"], feature.get("typ") or ""
    if name in soll or ist_ordner(typ) or name in _vorlage_namen(alle):
        return True
    for s in soll:
        g = alle.get(s)
        if g is not None and name in (g.get("unter") or []) and (typ == "ProfileFeature" or g.get("typ") == "HoleWzd"):
            return True
    if name in hilfsnamen and typ in ("ProfileFeature", "RefPlane"):
        return True
    knoten_typen = knoten_typen or {}
    if typ == "ProfileFeature" and name in _hilfsskizzen(knoten_typen):
        return True
    return typ == "RefAxis" and bool(RESERVIERT.match(name)) and bool(_MUSTER_TYPEN & set(knoten_typen.values()))


def _hilfsnamen(masse: list[dict]) -> set[str]:
    """Feature-Namen hinter `@` im Maßprotokoll (`D1@Ebene1`): Der Compiler legte sie selbst an, auch wenn kein Knoten sie nennt."""
    return {m["name"].split("@", 1)[1] for m in masse if "@" in m["name"]}


def ungeprueft_teil(grund: str) -> dict:
    """Ergebnis eines Teils, der nicht verglichen werden konnte: leer, `vollstaendig` falsch, `nicht_erklaert` wahr, der Grund steht
    in `luecken`. Nie ein „unverändert“."""
    return {"features_neu": [], "features_fehlen": [], "features_unterdrueckt": [], "typ_geaendert": [], "reihenfolge": None,
            "masse": [], "masse_neu": [], "material": None, "eigenschaften": {"geaendert": [], "fehlen": [], "neu": []},
            "gleichungen_neu": [], "konfigurationen_neu": [], "features_geprueft": False, "masse_geprueft": False,
            "vollstaendig": False, "luecken": [grund], "nicht_erklaert": True}


def _ist_werte(masse: list[dict], aktiv: str | None) -> dict[str, float]:
    """Betrag der Maße der aktiven Konfiguration (wie `lies_masse`: Maße sind Beträge); nicht lesbare fehlen."""
    werte = {}
    for m in masse:
        w = (m.get("werte") or {}).get(aktiv)
        if w is not None:
            werte[m["name"]] = abs(float(w))
    return werte


def _eigenschaften(spec_teil: dict, auftrag: str | None, ist: dict) -> dict[str, list[dict]]:
    """Eigenschaften der Datei gegen `eigenschaften_fuer` (was der Bau setzt); Konfigurationen tragen im Soll nichts, jede dort ist
    neu. `Auftrag` bleibt ohne Angabe des Auftrags unbeurteilt."""
    soll = {n: str(w) for n, w in eigenschaften_fuer(spec_teil, auftrag or "").items()}
    if auftrag is None:
        del soll["Auftrag"]
    datei = ist.get("datei") or {}
    geaendert = [{"name": n, "soll": w, "ist": datei[n]} for n, w in soll.items() if n in datei and str(datei[n]) != w]
    fehlen = [{"name": n, "soll": w} for n, w in soll.items() if n not in datei]
    neu = [{"name": n, "ist": w, "konfiguration": None} for n, w in datei.items() if n not in soll and n != "Auftrag"]
    for konfiguration, eigenschaften in (ist.get("konfiguration") or {}).items():
        neu += [{"name": n, "ist": w, "konfiguration": konfiguration} for n, w in (eigenschaften or {}).items()]
    return {"geaendert": geaendert, "fehlen": fehlen, "neu": neu}


def _mehrere_konfigurationen(ist: dict, luecken: list[str], was: str) -> list[str]:
    """Swki baut eine Konfiguration: Mehr als eine im Ist heißt neu. Welche die gebaute war, steht nicht im Protokoll, darum nennt die
    Liste alle; `was` der übrigen ist dann nicht verglichen (Lücke)."""
    konfigurationen = ist.get("konfigurationen")
    if konfigurationen is None:
        luecken.append("Die Aufnahme nennt keine Konfigurationen: Konfigurationen sind nicht vergleichbar")
        return []
    if len(konfigurationen) > 1:
        luecken.append(f"Mehrere Konfigurationen ({', '.join(konfigurationen)}), swki baut eine: {was} der übrigen nicht verglichen")
        return list(konfigurationen)
    return []


def abgleich_teil(protokoll_teil: dict, spec_teil: dict, ist: dict, auftrag: str | None = None) -> dict:
    """Bauprotokoll und freigegebene Spec eines Teils gegen die gelesene Aufnahme `ist` (Etappe-1-Format).

    features_neu: Ist-Features, die nicht zum Spec-Stand gehören (siehe `ist_erklaert`); features_fehlen: Features aus dem Protokoll,
    die es nicht mehr gibt (ein umbenanntes ist weg und neu); typ_geaendert: gleicher Name, anderer `GetTypeName2` (nur für Typen der
    `TYP_TABELLE`); masse: geänderte oder fehlende Maße des Maßprotokolls; masse_neu: Maße in mm/Grad, die das Protokoll nicht kennt;
    material, eigenschaften: Abweichungen von der Spec; konfigurationen_neu: mehr als eine Konfiguration. Was fehlt, steht in
    `luecken`."""
    luecken = []
    knoten = protokoll_teil.get("knoten") or []
    soll_features = [(n, k) for k in knoten for n in _knoten_namen(k)]
    features = ist.get("features")
    features_geprueft = bool(soll_features) and features is not None
    ohne_namen = [k["id"] for k in knoten if not _knoten_namen(k) and k.get("status") != "uebersprungen"]
    if ohne_namen:
        luecken.append(f"Das Bauprotokoll nennt für {', '.join(ohne_namen)} keinen SolidWorks-Namen (sw_name): nicht vergleichbar")
    elif not knoten:
        luecken.append("Das Bauprotokoll hat keine Knoten: Features sind nicht vergleichbar")
    if soll_features and features is None:
        luecken.append("Die Aufnahme enthält keine Features: Features sind nicht vergleichbar")
    masse_soll = [m for k in knoten for m in k.get("masse") or []]
    hat_masse = any("masse" in k for k in knoten)
    masse_geprueft = hat_masse and ist.get("masse") is not None
    if not hat_masse:
        luecken.append("Das Bauprotokoll hat kein Maßprotokoll (Lauf vor dem Bemaßungsbezug): Maße sind nicht vergleichbar")
    elif ist.get("masse") is None:
        luecken.append("Die Aufnahme enthält keine Maße: Maße sind nicht vergleichbar")

    neu, fehlen, unterdrueckt, typ_geaendert, reihenfolge = [], [], [], [], None
    if features_geprueft:
        alle = {f["name"]: f for f in features}
        knoten_typen = {n: k.get("typ") for n, k in soll_features}
        soll, hilfsnamen = set(knoten_typen), _hilfsnamen(masse_soll)
        for f in features:
            if not ist_erklaert(f, soll, alle, knoten_typen, hilfsnamen):
                neu.append({"name": f["name"], "typ": f.get("typ"), "eltern": list(f.get("eltern") or []),
                            "unter_von": [n for n, g in alle.items() if f["name"] in (g.get("unter") or [])]})
            unterdrueckt += [{"name": f["name"], "konfiguration": k} for k, weg in (f.get("unterdrueckt") or {}).items() if weg]
        fehlen = [{"name": n, "knoten": k["id"], "typ": k.get("typ")} for n, k in soll_features if n not in alle]
        # Typ des Hauptfeatures je Knoten (das erste der Namen) gegen die Tabelle; ein Typ ohne Beleg ist eine Lücke
        unbelegt = []
        for k in knoten:
            namen = _knoten_namen(k)
            if not namen:
                continue
            erlaubt = TYP_TABELLE.get(k.get("typ"))
            if erlaubt is None:
                unbelegt.append(f"{namen[0]} ({k.get('typ')})")
            elif namen[0] in alle and alle[namen[0]].get("typ") not in erlaubt:
                typ_geaendert.append({"name": namen[0], "knoten": k["id"], "soll": k.get("typ"), "ist": alle[namen[0]].get("typ"),
                                      "erlaubt": sorted(erlaubt)})
        if unbelegt:
            luecken.append(f"Typ von {', '.join(unbelegt)} ohne belegten SolidWorks-Typnamen (TYP_TABELLE): Typwechsel nicht erkennbar")
        # Reihenfolge der Soll-Features im Baum (`features` steht in der Reihenfolge der aktiven Konfiguration)
        vorhanden = [n for n, _ in soll_features if n in alle]
        ist_reihe = [n for n in alle if n in set(vorhanden)]
        if ist_reihe != vorhanden:
            reihenfolge = {"soll": vorhanden, "ist": ist_reihe}

    masse, masse_neu = [], []
    if masse_geprueft:
        aktiv = ist.get("aktiv") or next(iter(ist.get("konfigurationen") or []), None)
        masse = mass_differenz(masse_soll, _ist_werte(ist["masse"], aktiv))
        bekannt = {m["name"] for m in masse_soll}
        masse_neu = [{"name": m["name"], "feature": m.get("feature"), "zustand": m.get("zustand"),
                      "ist": None if (w := (m.get("werte") or {}).get(aktiv)) is None else abs(float(w))}
                     for m in ist["masse"] if m["name"] not in bekannt and m.get("einheit") in _EINHEITEN_MASS]

    material = None
    if "material" not in ist:
        luecken.append("Die Aufnahme enthält kein Material: Material ist nicht vergleichbar")
    else:
        soll_mat, ist_mat = spec_teil.get("material"), ist["material"] or ""
        if (not material_passt(ist_mat, soll_mat)) if soll_mat is not None else bool(ist_mat):
            material = {"soll": soll_mat, "ist": ist_mat}
    if ist.get("eigenschaften") is None:
        luecken.append("Die Aufnahme enthält keine Eigenschaften: Eigenschaften sind nicht vergleichbar")
        eigenschaften = {"geaendert": [], "fehlen": [], "neu": []}
    else:
        eigenschaften = _eigenschaften(spec_teil, auftrag, ist["eigenschaften"])

    gleichungen = []
    if not hat_masse:
        luecken.append("Gleichungen nicht geprüft: Läufe vor dem Bemaßungsbezug legten globale Variablen an")
    elif spec_teil.get("gleichungen") is True:
        luecken.append("Gleichungen nicht geprüft: Die Spec verlangt Gleichungen (gleichungen: true)")
    elif ist.get("gleichungen") is None:
        luecken.append("Die Aufnahme enthält keine Gleichungen: Gleichungen sind nicht vergleichbar")
    else:   # ohne gleichungen: true legt der Bau keine Gleichung und keine globale Variable an (Bemaßungsbezug §4)
        gleichungen = [{"text": g.get("text"), "links": g.get("links"), "global": bool(g.get("global"))} for g in ist["gleichungen"]]
    konfigurationen_neu = _mehrere_konfigurationen(ist, luecken, "Maße, Material und Werte")

    gefunden = bool(neu or fehlen or unterdrueckt or typ_geaendert or reihenfolge or masse or masse_neu or material or gleichungen
                    or konfigurationen_neu or any(eigenschaften.values()))
    return {"features_neu": neu, "features_fehlen": fehlen, "features_unterdrueckt": unterdrueckt, "typ_geaendert": typ_geaendert,
            "reihenfolge": reihenfolge, "masse": masse, "masse_neu": masse_neu, "material": material, "eigenschaften": eigenschaften,
            "gleichungen_neu": gleichungen, "konfigurationen_neu": konfigurationen_neu, "features_geprueft": features_geprueft,
            "masse_geprueft": masse_geprueft, "vollstaendig": not luecken, "luecken": luecken, "nicht_erklaert": not gefunden}


# --- Baugruppen -----------------------------------------------------------------------------------------------------

def normalisiere_lagen(lagen) -> dict[str, list[float]]:
    """SolidWorks-Komponentenname → Transform2.ArrayData (16 Zahlen, Verschiebung in m). Nimmt den Export (`komponenten` mit `name`,
    `transform`), eine Liste solcher Einträge, den Prüfbericht (`lagen`) oder die Zuordnung selbst."""
    if not lagen:
        return {}
    if isinstance(lagen, list):
        return {e["name"]: e["transform"] for e in lagen if isinstance(e, dict) and "name" in e and e.get("transform") is not None}
    if isinstance(lagen.get("komponenten"), list):
        return normalisiere_lagen(lagen["komponenten"])
    if isinstance(lagen.get("lagen"), dict):
        return normalisiere_lagen(lagen["lagen"])
    return {n: t for n, t in lagen.items() if isinstance(t, (list, tuple))}


def _dateiname(datei) -> str:
    """Dateiname ohne Ordner und Schreibweise: Im Protokoll steht der Name, in der Aufnahme der relative Pfad."""
    return PureWindowsPath(datei).name.lower() if datei else ""


def _transform(komponente: dict, aktiv: str | None) -> list[float] | None:
    t = komponente.get("transform")
    if isinstance(t, dict):
        t = t.get(aktiv) if aktiv in t else next(iter(t.values()), None)
    return list(t) if t else None


def _lagen(soll_namen: list[str], ist_komponenten: dict, soll_lagen: dict, aktiv: str | None) -> tuple[list[dict], list[str]]:
    """Abweichende Lagen und die Komponenten, deren Lage sich nicht prüfen ließ (nicht mehr im Ist, Soll-Lage oder Ist-Lage fehlt)."""
    abweichend, ungeprueft = [], []
    for name in soll_namen:
        if name not in ist_komponenten:
            ungeprueft.append(name)
            continue
        soll, ist = soll_lagen.get(name), _transform(ist_komponenten[name], aktiv)
        if soll is None or ist is None or len(soll) != len(ist):
            ungeprueft.append(name)
            continue
        abweichung = max(abs(a - b) for a, b in zip(soll, ist))
        if abweichung > _TOL_LAGE:
            verschiebung = math.dist(soll[9:12], ist[9:12]) * 1000 if len(soll) >= 12 else None
            abweichend.append({"name": name, "datei": ist_komponenten[name].get("datei"), "soll": list(soll), "ist": ist,
                               "abweichung": abweichung, "verschiebung_mm": verschiebung})
    return abweichend, ungeprueft


def _ist_grenze(e: dict) -> bool:
    """Trägt die Verknüpfung Grenzen? Das Feld `grenze` der Aufnahme, sonst `min`/`max`."""
    if e.get("grenze") is not None:
        return bool(e["grenze"])
    return e.get("min") is not None or e.get("max") is not None


def _verknuepfungen(soll_mates: dict[str, tuple[str, str]], soll_v: dict, ist_v: dict, luecken: list[str]) -> dict:
    """Vergleich je Verknüpfung (SolidWorks-Name → (Id, Spec-Typ) aus dem Protokoll; Soll-Daten je Id; Ist). Was das Soll nicht trägt,
    kommt in `luecken`."""
    neu = [{"name": n, "typ": mate_name(e.get("typ"), _ist_grenze(e)), "wert": e.get("wert"), "partner": e.get("partner")}
           for n, e in ist_v.items() if n not in soll_mates]
    weg = [{"id": i, "name": n, "typ": t} for n, (i, t) in soll_mates.items() if n not in ist_v]
    typ_geaendert, partner_geaendert, ausrichtung_geaendert, werte = [], [], [], []
    for name, (vid, typ) in soll_mates.items():
        if name not in ist_v:
            continue
        e = ist_v[name]
        ist_typ = mate_name(e.get("typ"), _ist_grenze(e))
        if ist_typ != typ:
            typ_geaendert.append({"id": vid, "name": name, "soll": typ, "ist": ist_typ})
        s = soll_v.get(vid)
        if s is None:
            luecken.append(f"Soll-Daten von {vid} fehlen: Partner, Ausrichtung und Werte nicht verglichen")
            continue
        partner = s.get("partner")
        if partner is None:
            luecken.append(f"Partner von {vid} fehlen im Soll: Partner nicht verglichen")
        elif None in partner:
            luecken.append(f"Partner von {vid} nicht bekannt (Komponente ohne SolidWorks-Namen im Protokoll): Partner nicht verglichen")
        elif set(partner) != set(e.get("partner") or []):
            partner_geaendert.append({"id": vid, "name": name, "soll": list(partner), "ist": list(e.get("partner") or [])})
        if s.get("ausrichtung") is not None and AUSRICHTUNG.get(s["ausrichtung"]) != e.get("ausrichtung"):
            ausrichtung_geaendert.append({"id": vid, "name": name, "soll": s["ausrichtung"],
                                          "ist": _AUSRICHTUNG_NAMEN.get(e.get("ausrichtung"), e.get("ausrichtung"))})
        if typ in MATE_KOPPLUNG:
            luecken.append(f"Übersetzung der Kopplung {vid} ist nicht vergleichbar (Teilkreise und Richtung stehen nicht im Soll)")
        fehlt = [f for f in _MIT_WERT.get(typ, ()) if s.get(f) is None]
        if fehlt:
            luecken.append(f"Soll-Wert von {vid} ({typ}) fehlt ({', '.join(fehlt)}): nicht verglichen")
        for feld in ("wert", "min", "max"):
            soll = s.get(feld)
            if soll is None:
                continue
            ist = e.get(feld)
            werte.append({"id": vid, "name": name, "feld": feld, "soll": soll, "ist": ist,
                          "delta": None if ist is None else ist - soll})
    return {"neu": neu, "weg": weg, "typ_geaendert": typ_geaendert, "partner_geaendert": partner_geaendert,
            "ausrichtung_geaendert": ausrichtung_geaendert,
            "werte": [w for w in werte if w["ist"] is None or abs(w["delta"]) > 1e-6]}


def abgleich_baugruppe(protokoll: dict, soll_verknuepfungen: dict | None, ist: dict, lagen=None) -> dict:
    """Bauprotokoll einer Baugruppe und Soll-Daten je Verknüpfungs-Id (`soll_verknuepfungen` in swki.aenderungen: `{typ, partner:
    [SolidWorks-Name, …], ausrichtung, wert, min, max}`) gegen die gelesene Aufnahme `ist` (Format `bestand.json` einer Baugruppe).
    `lagen`: Soll-Lagen (siehe `normalisiere_lagen`), ohne sie bleibt die Lage ungeprüft (`lage_geprueft` falsch).

    Komponenten stehen unter ihrem SolidWorks-Namen: komponenten_neu (auch weitere Instanzen derselben Datei, untergeordnete
    Komponenten und virtuelle), komponenten_weg, andere_datei (gleicher Name, andere Datei), umbenannt (weg und neu mit derselben
    Datei), komponenten_unterdrueckt. Verknüpfungen: verknuepfungen_neu/weg, typ_geaendert (auch Abstand ↔ Grenze), partner_geaendert
    (als Menge), ausrichtung_geaendert (nur wenn das Soll sie nennt), werte (Zahlen, bei Grenzen auch min/max), fehler, unterdrueckt.
    lagen: Komponenten, deren Lage um mehr als 10 µm bzw. 1e-5 im Drehanteil abweicht. `lage_geprueft` ist nur wahr, wenn jede
    Soll-Komponente verglichen wurde."""
    luecken = []
    soll_komponenten = protokoll.get("komponenten")
    ist_komponenten = ist.get("komponenten")
    komponenten_geprueft = soll_komponenten is not None and ist_komponenten is not None
    if soll_komponenten is None:
        luecken.append("Das Bauprotokoll nennt keine Komponenten: Komponenten sind nicht vergleichbar")
    elif ist_komponenten is None:
        luecken.append("Die Aufnahme enthält keine Komponenten: Komponenten sind nicht vergleichbar")
    knoten = protokoll.get("knoten")
    ist_v = ist.get("verknuepfungen")
    verknuepfungen_geprueft = knoten is not None and ist_v is not None
    if knoten is None:
        luecken.append("Das Bauprotokoll nennt keine Knoten: Verknüpfungen sind nicht vergleichbar")
    elif ist_v is None:
        luecken.append("Die Aufnahme enthält keine Verknüpfungen: Verknüpfungen sind nicht vergleichbar")
    aktiv = ist.get("aktiv")

    unbenannt = [k["id"] for k in soll_komponenten or [] if not k.get("sw_name")]
    unbenannt += [k["id"] for k in knoten or [] if k.get("typ") == "komponente" and not k.get("sw_name")
                  and k.get("status") != "uebersprungen" and k["id"] not in unbenannt]
    if unbenannt:
        luecken.append(f"Komponenten {', '.join(unbenannt)} ohne SolidWorks-Namen im Bauprotokoll: nicht verglichen")

    k_neu, k_weg, andere, umbenannt, unterdrueckt_k = [], [], [], [], []
    soll_namen: list[str] = []
    if komponenten_geprueft:
        soll_k = {k["sw_name"]: k for k in soll_komponenten if k.get("sw_name")}
        soll_namen = list(soll_k)
        for name, e in ist_komponenten.items():
            if name not in soll_k:
                gleiche = sorted(s for s, k in soll_k.items() if _dateiname(k.get("datei")) == _dateiname(e.get("datei")))
                k_neu.append({"name": name, "datei": e.get("datei"), "virtuell": bool(e.get("virtuell")),
                              "gleiche_datei_wie": gleiche})
            elif _dateiname(soll_k[name].get("datei")) != _dateiname(e.get("datei")):
                andere.append({"name": name, "soll": soll_k[name].get("datei"), "ist": e.get("datei")})
            for konfiguration, weg in (e.get("unterdrueckt") or {}).items():
                if weg:
                    unterdrueckt_k.append({"name": name, "konfiguration": konfiguration})
        k_weg = [{"id": k.get("id"), "name": n, "datei": k.get("datei")} for n, k in soll_k.items() if n not in ist_komponenten]
        frei = list(k_neu)
        for w in k_weg:
            treffer = next((n for n in frei if _dateiname(n["datei"]) == _dateiname(w["datei"])), None)
            if treffer is not None:
                frei.remove(treffer)
                umbenannt.append({"von": w["name"], "nach": treffer["name"], "datei": w["datei"]})

    soll_lagen = normalisiere_lagen(lagen)
    lagen_abw, lage_ungeprueft = _lagen(soll_namen, ist_komponenten or {}, soll_lagen, aktiv)
    lage_ungeprueft += [i for i in unbenannt if komponenten_geprueft]
    lage_geprueft = komponenten_geprueft and bool(soll_lagen) and not lage_ungeprueft
    if komponenten_geprueft and not soll_lagen:
        luecken.append("Lage nicht geprüft: Es gibt keine Soll-Lagen (Prüfbericht des Laufs oder --lagen)")
    elif lage_ungeprueft:
        luecken.append(f"Lage nicht für alle Komponenten geprüft: {', '.join(lage_ungeprueft)}")

    v = {"neu": [], "weg": [], "typ_geaendert": [], "partner_geaendert": [], "ausrichtung_geaendert": [], "werte": []}
    fehler, unterdrueckt_v = [], []
    if verknuepfungen_geprueft:
        mates = [k for k in knoten if k.get("typ") in VERKNUEPFUNGS_TYPEN]
        ohne_namen = [k["id"] for k in mates if not k.get("sw_name") and k.get("status") != "uebersprungen"]
        if ohne_namen:
            luecken.append(f"Verknüpfungen {', '.join(ohne_namen)} ohne SolidWorks-Namen im Bauprotokoll: nicht verglichen")
        soll_mates = {k["sw_name"]: (k["id"], k["typ"]) for k in mates if k.get("sw_name")}
        v = _verknuepfungen(soll_mates, soll_verknuepfungen or {}, ist_v, luecken)
        for name in sorted(ist_v):
            e = ist_v[name]
            fehler += [{"name": name, "konfiguration": k, "code": c, "neu": name not in soll_mates}
                       for k, c in sorted((e.get("fehler") or {}).items()) if c]
            unterdrueckt_v += [{"name": name, "konfiguration": k, "neu": name not in soll_mates}
                               for k, weg in sorted((e.get("unterdrueckt") or {}).items()) if weg]
    konfigurationen_neu = _mehrere_konfigurationen(ist, luecken, "Lagen und Werte")

    gefunden = bool(k_neu or k_weg or andere or unterdrueckt_k or lagen_abw or fehler or unterdrueckt_v or konfigurationen_neu
                    or any(v.values()))
    return {"komponenten_neu": k_neu, "komponenten_weg": k_weg, "andere_datei": andere, "umbenannt": umbenannt,
            "komponenten_unterdrueckt": unterdrueckt_k, "verknuepfungen_neu": v["neu"], "verknuepfungen_weg": v["weg"],
            "typ_geaendert": v["typ_geaendert"], "partner_geaendert": v["partner_geaendert"],
            "ausrichtung_geaendert": v["ausrichtung_geaendert"], "werte": v["werte"], "fehler": fehler, "unterdrueckt": unterdrueckt_v,
            "lagen": lagen_abw, "lage_geprueft": lage_geprueft, "lage_ungeprueft": lage_ungeprueft,
            "konfigurationen_neu": konfigurationen_neu, "komponenten_geprueft": komponenten_geprueft,
            "verknuepfungen_geprueft": verknuepfungen_geprueft, "vollstaendig": not luecken, "luecken": luecken,
            "nicht_erklaert": not gefunden}
