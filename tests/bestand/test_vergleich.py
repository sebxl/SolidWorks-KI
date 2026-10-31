"""Vergleich vorher/nachher (Spec Bestandsdateien §7.1) ohne SolidWorks: zwei Aufnahmen im Format bestand.json und die Punkte der
Änderungs-Spec. Jeder Test ändert genau eine Sache an einer Kopie der Aufnahme."""

import copy

from swki.bestand.vergleich import SKIZZE_RANG, neue_fehler, neue_warnungen, vergleiche
from tests.bestand.beispiel_aufnahme import aufnahme as beispiel


def _vorher() -> dict:
    a = beispiel()
    a["reihenfolge"] = {k: [f["name"] for f in a["features"]] for k in a["konfigurationen"]}
    a["skizzen"] = {"Skizze1": 3, "Skizze4": 3, "Skizze5": 2}
    a["eigenschaften"] = {"datei": {"Benennung": "Lagerdeckel"}, "konfiguration": {"Standard": {}, "Variante B": {"Bemerkung": "x"}}}
    a["neuaufbau"] = [{"konfiguration": "Standard", "feature": "Verrundung1", "code": 12, "warnung": False},
                      {"konfiguration": "Standard", "feature": "Fase3", "code": 7, "warnung": True}]
    a["externe_referenzen"] = []
    return a


VORHER = _vorher()
SPEC_LEER = {"punkte": []}


def kopie(a: dict = VORHER) -> dict:
    return copy.deepcopy(a)


def eintraege(liste: list[dict]) -> dict[str, dict]:
    ids = [e["id"] for e in liste]
    assert len(ids) == len(set(ids)), ids
    return {e["id"]: e for e in liste}


def setze(a: dict, name: str, konfiguration: str, wert) -> None:
    next(m for m in a["masse"] if m["name"] == name)["werte"][konfiguration] = wert


def feature(a: dict, name: str) -> dict:
    return next(f for f in a["features"] if f["name"] == name)


def spec(*punkte) -> dict:
    return {"punkte": list(punkte)}


def vergleich(sp, nachher, parameter=None, vorher=VORHER) -> dict[str, dict]:
    return eintraege(vergleiche(sp, vorher, nachher, parameter or {}))


def nur_ok(e: dict[str, dict], erlaubt_none: tuple = ()) -> None:
    schlecht = {i: x for i, x in e.items() if x["ok"] is not True and i not in erlaubt_none}
    assert not schlecht, schlecht


def test_unveraendert_alles_ok():
    e = vergleich(SPEC_LEER, kopie())
    assert set(e) == {"baum", "masse", "gleichungen", "konfigurationen", "eigenschaften", "material", "neuaufbau", "skizzen",
                      "externe_referenzen"}
    nur_ok(e)
    assert e["masse"]["getrieben"] == []


def test_eintraege_haben_das_bewertungsformat():
    for x in vergleiche(spec({"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 40}), VORHER, kopie(), {}):
        assert {"id", "ok"} <= set(x)


# ------------------------------------------------------------------------------------------------------------------ Maße

def test_fremdes_mass_geaendert_ist_mangel():
    n = kopie()
    setze(n, "D2@Skizze4", "Standard", 41.0)
    e = vergleich(SPEC_LEER, n)
    assert e["masse"]["ok"] is False and "D2@Skizze4" in str(e["masse"])
    assert e["masse"]["ist"] == [{"name": "D2@Skizze4", "konfiguration": "Standard", "vorher": 40.0, "nachher": 41.0}]
    assert "D2@Skizze4" in e["masse"]["hinweis"]


def test_folgen_sind_erlaubt():
    """Variable L 100 → 110: D1@Skizze1 und D3@Skizze2 gehen mit, der Rest bleibt."""
    n = kopie()
    setze(n, "D1@Skizze1", "Standard", 110.0)
    setze(n, "D1@Skizze1", "Variante B", 110.0)
    setze(n, "D3@Skizze2", "Standard", 115.0)
    setze(n, "D3@Skizze2", "Variante B", 115.0)
    n["variablen"]["L"] = 110.0
    next(g for g in n["gleichungen"] if g["links"] == "L")["text"] = '"L" = 110'
    p = {"id": "p1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110}
    e = vergleich(spec(p), n)
    nur_ok(e)
    assert e["punkt:p1"]["ist"] == 110.0
    setze(n, "D3@Skizze2", "Standard", 116.0)
    assert vergleich(spec(p), n)["masse"]["ok"] is True  # D3 ist eine Folge: jeder Wert ist erlaubt
    setze(n, "D5@Skizze5", "Standard", 13.0)  # D5 ist keine
    assert vergleich(spec(p), n)["masse"]["ok"] is False


def test_verknuepftes_paar_folgt():
    n = kopie()
    for k in ("Standard", "Variante B"):
        setze(n, "D1@S5", k, 9.0)
        setze(n, "D2@S6", k, 9.0)
    e = vergleich(spec({"id": "p1", "typ": "mass", "mass": "D1@S5", "alt": 8, "neu": 9}), n)
    nur_ok(e)


def test_gleichung_links_ist_selbst_ein_mass():
    n = kopie()
    setze(n, "D1@Skizze1", "Standard", 200.0)
    setze(n, "D1@Skizze1", "Variante B", 200.0)
    setze(n, "D3@Skizze2", "Standard", 205.0)
    setze(n, "D3@Skizze2", "Variante B", 205.0)
    next(g for g in n["gleichungen"] if g["links"] == "D1@Skizze1")["text"] = '"D1@Skizze1" = "L" * 2'
    p = {"id": "p1", "typ": "gleichung", "gleichung": "D1@Skizze1", "alt": '"L"', "neu": '"L" * 2'}
    nur_ok(vergleich(spec(p), n))


def test_getriebenes_mass_nur_berichtet():
    n = kopie()
    setze(n, "D7@Skizze9", "Standard", 3.5)
    e = vergleich(SPEC_LEER, n)
    assert e["masse"]["ok"] is True
    assert e["masse"]["getrieben"] == [{"name": "D7@Skizze9", "vorher": {"Standard": 3.0}, "nachher": {"Standard": 3.5}}]
    nur_ok(e)


def test_none_heisst_lesen_gescheitert_nie_bestanden():
    """Review Fix 1: Auch unterdrückte Maße liefern Zahlen (S18b); `None` ist nie „keine Änderung"."""
    n = kopie()
    setze(n, "D5@Skizze5", "Variante B", None)  # vorher 15.0
    e = vergleich(SPEC_LEER, n)
    assert e["masse"]["ok"] is None and e["masse"]["unlesbar"] == [{"name": "D5@Skizze5", "konfiguration": "Variante B"}]
    assert "D5@Skizze5" in e["masse"]["hinweis"]
    v = kopie()
    setze(v, "D2@Skizze4", "Variante B", None)  # vorher und nachher None
    assert vergleich(SPEC_LEER, kopie(v), vorher=v)["masse"]["ok"] is None
    v = kopie()
    setze(v, "D2@Skizze4", "Variante B", None)  # vorher None, nachher Zahl
    assert vergleich(SPEC_LEER, kopie(), vorher=v)["masse"]["ok"] is None


def test_none_auch_bei_unterdrueckung_in_anderer_konfiguration():
    v = kopie()
    setze(v, "D2@Skizze4", "Variante B", 40.0)
    feature(v, "Skizze4")["unterdrueckt"]["Variante B"] = True
    n = kopie(v)
    setze(n, "D2@Skizze4", "Standard", None)
    setze(n, "D2@Skizze4", "Variante B", None)
    assert vergleich(SPEC_LEER, n, vorher=v)["masse"]["ok"] is None
    # auch das Maß eines unterdrückten Features gilt nur mit Zahl als nachgewiesen
    n2 = kopie(v)
    setze(n2, "D2@Skizze4", "Variante B", None)
    assert vergleich(SPEC_LEER, n2, vorher=v)["masse"]["ok"] is None


def test_none_bei_punkt_ziel_und_folge():
    n = kopie()
    setze(n, "D5@Skizze5", "Standard", 13.0)
    setze(n, "D5@Skizze5", "Variante B", None)
    e = vergleich(spec({"id": "p1", "typ": "mass", "mass": "D5@Skizze5", "alt": 12, "neu": 13}), n)
    assert e["punkt:p1"]["ok"] is None and "Variante B" in e["punkt:p1"]["hinweis"]
    assert e["masse"]["ok"] is None  # das Ziel selbst ist in Variante B nicht gelesen worden


def test_none_hat_hinter_einem_mangel_zurueckzustehen():
    n = kopie()
    setze(n, "D5@Skizze5", "Variante B", None)
    setze(n, "D1@S5", "Standard", 1.0)
    assert vergleich(SPEC_LEER, n)["masse"]["ok"] is False


def test_unterdruecken_punkt_none_ist_nicht_bestanden():
    n = kopie()
    n["features"][0]["unterdrueckt"]["Standard"] = None
    p = {"id": "p1", "typ": "unterdruecken", "feature": "Skizze1", "konfigurationen": ["Standard"]}
    e = vergleich(spec(p), n)
    assert e["punkt:p1"]["ok"] is None and e["konfigurationen"]["ok"] is None
    n["features"][0]["unterdrueckt"]["Standard"] = True
    assert vergleich(spec(p), n)["punkt:p1"]["ok"] is True


def test_zustand_und_gruppe_eines_masses_aendern_sich_nicht():
    n = kopie()
    next(m for m in n["masse"] if m["name"] == "D2@Skizze4")["zustand"] = "getrieben"
    e = vergleich(SPEC_LEER, n)
    assert e["masse"]["ok"] is False and e["masse"]["umgestuft"][0]["feld"] == "zustand"
    n = kopie()  # getrieben → treibend mit anderem Wert
    m = next(m for m in n["masse"] if m["name"] == "D7@Skizze9")
    m["zustand"], m["werte"]["Standard"] = "treibend", 9.0
    assert vergleich(SPEC_LEER, n)["masse"]["ok"] is False
    n = kopie()  # Verknüpfung gelöst
    next(m for m in n["masse"] if m["name"] == "D1@S5")["gruppe"] = None
    assert vergleich(SPEC_LEER, n)["masse"]["ok"] is False


def test_wert_tauscht_nur_in_genannter_konfiguration():
    n = kopie()
    setze(n, "D5@Skizze5", "Standard", 13.0)
    p = {"id": "p1", "typ": "mass", "mass": "D5@Skizze5", "alt": 12, "neu": 13, "konfigurationen": ["Standard"]}
    nur_ok(vergleich(spec(p), n))
    setze(n, "D5@Skizze5", "Variante B", 13.0)  # Variante B ging mit
    e = vergleich(spec(p), n)
    assert e["masse"]["ok"] is False and e["masse"]["ist"][0]["konfiguration"] == "Variante B"
    assert e["punkt:p1"]["ok"] is True


def test_folgen_gelten_nur_in_den_konfigurationen_des_punkts():
    """Review Fix 2: Ein Partner oder eine Gleichungsfolge in einer nicht genannten Konfiguration ist ein Mangel."""
    p = {"id": "p1", "typ": "mass", "mass": "D1@S5", "alt": 8, "neu": 9, "konfigurationen": ["Variante B"]}
    n = kopie()
    setze(n, "D1@S5", "Variante B", 9.0)
    setze(n, "D2@S6", "Variante B", 9.0)
    nur_ok(vergleich(spec(p), n))
    setze(n, "D2@S6", "Standard", 9.0)  # Partner geht in Standard mit
    e = vergleich(spec(p), n)
    assert e["masse"]["ok"] is False and e["masse"]["ist"][0] == {"name": "D2@S6", "konfiguration": "Standard", "vorher": 8.0,
                                                                  "nachher": 9.0}
    v = kopie()
    v["gleichungen"].append({"index": 3, "text": '"D8@Skizze9" = "D5@Skizze5" + 1', "links": "D8@Skizze9", "global": False})
    n = kopie(v)
    setze(n, "D5@Skizze5", "Standard", 13.0)
    setze(n, "D8@Skizze9", "Standard", 14.0)
    q = {"id": "p1", "typ": "mass", "mass": "D5@Skizze5", "alt": 12, "neu": 13, "konfigurationen": ["Standard"]}
    nur_ok(vergleich(spec(q), n, vorher=v))
    setze(n, "D8@Skizze9", "Variante B", 99.0)  # die Gleichungsfolge springt in Variante B
    assert vergleich(spec(q), n, vorher=v)["masse"]["ok"] is False


def test_gruppenpartner_traegt_den_zielwert():
    n = kopie()
    for k in n["konfigurationen"]:
        setze(n, "D1@S5", k, 9.0)
        setze(n, "D2@S6", k, 77.0)
    e = vergleich(spec({"id": "p1", "typ": "mass", "mass": "D1@S5", "alt": 8, "neu": 9}), n)
    assert e["punkt:p1"]["ok"] is False and "D2@S6" in e["punkt:p1"]["hinweis"]


def test_gleichung_punkt_wirkt_auf_alle_konfigurationen():
    n = kopie()
    for k in n["konfigurationen"]:
        setze(n, "D1@Skizze1", k, 110.0)
        setze(n, "D3@Skizze2", k, 115.0)
    n["variablen"]["L"] = 110.0
    next(g for g in n["gleichungen"] if g["links"] == "L")["text"] = '"L" = 110'
    nur_ok(vergleich(spec({"id": "p1", "typ": "gleichung", "variable": "L", "alt": 100, "neu": 110}), n))


def test_mass_ohne_konfigurationen_gilt_in_allen():
    n = kopie()
    setze(n, "D5@Skizze5", "Standard", 13.0)
    p = {"id": "p1", "typ": "mass", "mass": "D5@Skizze5", "alt": 12, "neu": 13}
    e = vergleich(spec(p), n)
    assert e["punkt:p1"]["ok"] is False and "Variante B" in e["punkt:p1"]["hinweis"]
    assert e["masse"]["ok"] is True  # gegen den Punkt wird in punkt:p1 geprüft


def test_punkt_mass_nicht_umgesetzt():
    p = {"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45}
    e = vergleich(spec(p), kopie())["punkt:p1"]
    assert e["ok"] is False and e["soll"] == 45 and e["ist"]["Standard"] == 40.0
    assert "D2@Skizze4" in e["hinweis"]


def test_punkt_mass_umgesetzt_mit_rauschen():
    n = kopie()
    setze(n, "D2@Skizze4", "Standard", 45.0000004)
    p = {"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45, "konfigurationen": ["Standard"]}
    nur_ok(vergleich(spec(p), n))


def test_punkt_mass_nirgends_lesbar_ist_none():
    n = kopie()
    for k in n["konfigurationen"]:
        setze(n, "D2@Skizze4", k, None)
    p = {"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45}
    assert vergleich(spec(p), n)["punkt:p1"]["ok"] is None


def test_punkt_mass_fehlt():
    n = kopie()
    n["masse"] = [m for m in n["masse"] if m["name"] != "D2@Skizze4"]
    p = {"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45}
    e = vergleich(spec(p), n)
    assert e["punkt:p1"]["ok"] is False
    assert e["masse"]["ok"] is False and e["masse"]["fehlen"] == ["D2@Skizze4"]


def test_punkt_neu_als_ausdruck():
    n = kopie()
    setze(n, "D2@Skizze4", "Standard", 15.0)
    p = {"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": "=A_neu", "konfigurationen": ["Standard"]}
    assert vergleich(spec(p), n, {"A_neu": 15})["punkt:p1"]["ok"] is True
    assert vergleich(spec(p), n, {"A_neu": 16})["punkt:p1"]["ok"] is False


def test_neues_mass_am_bestandsfeature_ist_mangel():
    n = kopie()
    neu = copy.deepcopy(next(m for m in n["masse"] if m["name"] == "D2@Skizze4"))
    neu["name"] = "D9@Skizze4"
    n["masse"].append(neu)
    e = vergleich(SPEC_LEER, n)
    assert e["masse"]["ok"] is False and e["masse"]["neu_am_bestand"] == ["D9@Skizze4"]


def test_masse_neuer_features_fehlen_vorher_ohne_mangel():
    n = kopie()
    neu = copy.deepcopy(n["masse"][0])
    neu.update(name="D1@Gewinde M6", feature="Gewinde M6")
    n["masse"].append(neu)
    n["features"].append({"name": "Gewinde M6", "typ": "HoleWzd", "eltern": [], "kinder": [],
                          "unterdrueckt": {"Standard": False, "Variante B": False}, "tabelle": False})
    for k in n["konfigurationen"]:
        n["reihenfolge"][k].append("Gewinde M6")
    p = {"id": "p3", "typ": "feature", "name": "Gewinde M6", "feature": {"typ": "bohrung"}}
    nur_ok(vergleich(spec(p), n))


def test_mass_gelöschter_features_darf_fehlen():
    n = _ohne(kopie(), "Bohrung2", "Skizze4", "Fase3", "Verrundung1")
    n["masse"] = [m for m in n["masse"] if m["feature"] != "Skizze4"]
    n["skizzen"].pop("Skizze4")
    p = {"id": "p1", "typ": "loeschen", "feature": "Bohrung2", "kinder": ["Fase3", "Verrundung1"]}
    nur_ok(vergleich(spec(p), n))
    ohne_punkt = vergleich(SPEC_LEER, n)
    assert ohne_punkt["masse"]["ok"] is False and ohne_punkt["baum"]["ok"] is False


# ------------------------------------------------------------------------------------------------------------------- Baum

def _ohne(a: dict, *namen: str) -> dict:
    a["features"] = [f for f in a["features"] if f["name"] not in namen]
    for f in a["features"]:
        f["eltern"] = [x for x in f["eltern"] if x not in namen]
        f["kinder"] = [x for x in f["kinder"] if x not in namen]
    a["reihenfolge"] = {k: [x for x in reihe if x not in namen] for k, reihe in a["reihenfolge"].items()}
    return a


def _neues_feature(a: dict, name: str, nach: str | None = None) -> dict:
    a["features"].append({"name": name, "typ": "HoleWzd", "eltern": [], "kinder": [],
                          "unterdrueckt": {k: False for k in a["konfigurationen"]}, "tabelle": False})
    for reihe in a["reihenfolge"].values():
        reihe.insert(len(reihe) if nach is None else reihe.index(nach) + 1, name)
    return a


PUNKT_FEATURE = {"id": "p3", "typ": "feature", "name": "Gewinde M6", "feature": {"typ": "bohrung"}}


def test_baum_neues_feature_erlaubt_nur_mit_punkt():
    n = _neues_feature(kopie(), "Gewinde M6")
    e = vergleich(SPEC_LEER, n)
    assert e["baum"]["ok"] is False and "Gewinde M6" in str(e["baum"]["ist"])
    e = vergleich(spec(PUNKT_FEATURE), n)
    nur_ok(e)
    assert e["baum"]["ungeklaert"] == []


def test_baum_neue_skizze_des_features_und_seine_unterfeatures():
    n = _neues_feature(kopie(), "Gewinde M6")
    _neues_feature(n, "Gewinde M6 Skizze")
    _neues_feature(n, "Gewinde M6 Senkung Skizze")
    _neues_feature(n, "Bohrungsgewinde1")
    feature(n, "Gewinde M6")["unter"] = ["Skizze6", "Bohrungsgewinde1"]  # behalten den SolidWorks-Namen
    _neues_feature(n, "Skizze6")
    nur_ok(vergleich(spec(PUNKT_FEATURE), n))


def test_baum_verirrte_neue_features_neben_dem_feature_punkt_sind_mangel():
    """Review Fix 3: Ein feature-Punkt macht nicht jedes neue Feature erlaubt."""
    n = _neues_feature(kopie(), "Gewinde M6")
    _neues_feature(n, "Schnitt-Linear2")
    e = vergleich(spec(PUNKT_FEATURE), n)
    assert e["baum"]["ok"] is False and "Schnitt-Linear2" in e["baum"]["hinweis"]
    n = _neues_feature(kopie(), "Gewinde M6")
    _neues_feature(n, "Bohrungsgewinde1", nach="Aufsatz")  # nicht in `unter`, mitten im Bestand
    assert vergleich(spec(PUNKT_FEATURE), n)["baum"]["ok"] is False
    n = _neues_feature(kopie(), "Gewinde M6")
    _neues_feature(n, "Gewinde M6 Zweite Bohrung")  # ein Namenspräfix erklärt nicht alles
    assert vergleich(spec(PUNKT_FEATURE), n)["baum"]["ok"] is False
    n = _neues_feature(kopie(), "Schnitt-Linear2")  # nur ein mass-Punkt
    assert vergleich(spec({"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 40}), n)["baum"]["ok"] is False


def test_baum_abgeleitete_namen_sind_genau_die_vier_formen():
    """Review Fix 2: Eine Sequenz, kein Beutel: Name, Name Skizze, Name Senkung, Name Senkung Skizze."""
    for erlaubt in ("Gewinde M6 Skizze", "Gewinde M6 Senkung", "Gewinde M6 Senkung Skizze"):
        n = _neues_feature(_neues_feature(kopie(), "Gewinde M6"), erlaubt)
        assert vergleich(spec(PUNKT_FEATURE), n)["baum"]["ok"] is True, erlaubt
    for verirrt in ("Gewinde M6 7", "Gewinde M6 Skizze 2", "Gewinde M6 Senkung Senkung", "Gewinde M6 Skizze Senkung",
                    "Gewinde M6 Skizze Skizze", "Gewinde M6 "):
        n = _neues_feature(_neues_feature(kopie(), "Gewinde M6"), verirrt)
        e = vergleich(spec(PUNKT_FEATURE), n)["baum"]
        assert e["ok"] is False and verirrt.strip() in e["hinweis"], verirrt


def test_baum_feature_punkt_mit_vorhandenem_namen():
    p = {**PUNKT_FEATURE, "name": "Aufsatz"}
    e = vergleich(spec(p), kopie())["punkt:p3"]
    assert e["ok"] is False and "schon im Bestand" in e["hinweis"]


def test_baum_feature_punkt_nach():
    n = _neues_feature(kopie(), "Gewinde M6", nach="Aufsatz")
    p = {**PUNKT_FEATURE, "nach": "Aufsatz"}
    e = vergleich(spec(p), n)
    nur_ok(e)
    # ohne nach gehört es ans Ende
    assert vergleich(spec(PUNKT_FEATURE), n)["punkt:p3"]["ok"] is False
    assert vergleich(spec({**PUNKT_FEATURE, "nach": "Fase3"}), n)["punkt:p3"]["ok"] is False


def test_baum_feature_punkt_nicht_gebaut_oder_unterdrueckt():
    assert vergleich(spec(PUNKT_FEATURE), kopie())["punkt:p3"]["ok"] is False
    n = _neues_feature(kopie(), "Gewinde M6")
    feature(n, "Gewinde M6")["unterdrueckt"]["Standard"] = True
    e = vergleich(spec(PUNKT_FEATURE), n)
    assert e["punkt:p3"]["ok"] is False and "unterdrückt" in e["punkt:p3"]["hinweis"]


def test_baum_umbenannt_ist_mangel():
    n = kopie()
    feature(n, "Fase3")["name"] = "Fase 3"
    for reihe in n["reihenfolge"].values():
        reihe[reihe.index("Fase3")] = "Fase 3"
    e = vergleich(SPEC_LEER, n)
    assert e["baum"]["ok"] is False
    gemeldet = {(q["art"], tuple(q.get("features", ()))) for q in e["baum"]["ist"]}
    assert ("fehlt", ("Fase3",)) in gemeldet and ("neu", ("Fase 3",)) in gemeldet


def test_baum_reihenfolge_ist_mangel():
    n = kopie()
    reihe = n["reihenfolge"]["Variante B"]
    reihe[0], reihe[1] = reihe[1], reihe[0]
    e = vergleich(SPEC_LEER, n)
    assert e["baum"]["ok"] is False
    assert [q["art"] for q in e["baum"]["ist"]] == ["reihenfolge"] and e["baum"]["ist"][0]["konfiguration"] == "Variante B"


def test_baum_typ_und_eltern():
    n = kopie()
    feature(n, "Fase3")["typ"] = "Fillet"
    feature(n, "Bohrung2")["eltern"] = ["Skizze1"]
    arten = sorted(q["art"] for q in vergleich(SPEC_LEER, n)["baum"]["ist"])
    assert arten == ["eltern", "typ"]


def test_baum_gelöschte_mit_kindern_und_ihre_skizze():
    n = _ohne(kopie(), "Bohrung2", "Skizze4", "Fase3", "Verrundung1")
    n["masse"] = [m for m in n["masse"] if m["feature"] != "Skizze4"]
    p = {"id": "p1", "typ": "loeschen", "feature": "Bohrung2", "kinder": ["Fase3", "Verrundung1"]}
    e = vergleich(spec(p), n)
    assert e["baum"]["ok"] is True  # Skizze4 hat nur dieses Kind und geht mit
    nur_ok(e)
    # ein nicht genanntes Kind verschwindet: Mangel
    p2 = {**p, "kinder": ["Fase3"]}
    assert vergleich(spec(p2), n)["baum"]["ok"] is False


def test_punkt_loeschen_nicht_gelöscht():
    p = {"id": "p1", "typ": "loeschen", "feature": "Fase3", "kinder": ["Verrundung1"]}
    e = vergleich(spec(p), kopie())["punkt:p1"]
    assert e["ok"] is False and "Fase3" in e["hinweis"]


# ----------------------------------------------------------------------------------------------------- Konfigurationen

def test_aktive_konfiguration_geaendert_ist_mangel():
    """Review Focus 4: Der Kollege öffnet sonst eine andere Variante."""
    n = kopie()
    n["aktiv"] = "Variante B"
    n["konfigurationen"] = ["Variante B", "Standard"]
    e = vergleich(SPEC_LEER, n)
    assert e["konfigurationen"]["ok"] is False
    assert e["konfigurationen"]["ist"] == [{"art": "aktiv", "soll": "Standard", "ist": "Variante B"}]


def test_konfiguration_fehlt_oder_neu():
    n = kopie()
    n["konfigurationen"] = ["Standard"]
    e = vergleich(SPEC_LEER, n)
    assert e["konfigurationen"]["ok"] is False and e["konfigurationen"]["ist"][0]["art"] == "fehlt"
    n["konfigurationen"] = ["Standard", "Variante B", "Variante C"]
    assert vergleich(SPEC_LEER, n)["konfigurationen"]["ist"][0]["art"] == "neu"


def test_unterdrueckung_nur_wie_der_punkt():
    n = kopie()
    feature(n, "Fase3")["unterdrueckt"]["Standard"] = True
    e = vergleich(SPEC_LEER, n)
    assert e["konfigurationen"]["ok"] is False
    assert e["konfigurationen"]["ist"] == [{"art": "unterdrueckung", "feature": "Fase3", "konfiguration": "Standard",
                                            "vorher": False, "nachher": True}]
    p = {"id": "p1", "typ": "unterdruecken", "feature": "Fase3", "konfigurationen": ["Standard"]}
    nur_ok(vergleich(spec(p), n))
    # Variante B ging mit: Mangel
    feature(n, "Fase3")["unterdrueckt"]["Variante B"] = True
    assert vergleich(spec(p), n)["konfigurationen"]["ok"] is False


def test_unterdruecken_nimmt_kinder_und_skizzen_mit():
    n = kopie()
    for name in ("Bohrung2", "Fase3", "Verrundung1", "Skizze4"):
        for k in n["konfigurationen"]:
            feature(n, name)["unterdrueckt"][k] = True
    p = {"id": "p1", "typ": "unterdruecken", "feature": "Bohrung2"}
    e = vergleich(spec(p), n)
    nur_ok(e)
    feature(n, "Aufsatz")["unterdrueckt"]["Standard"] = True  # nicht abhängig: Mangel
    assert vergleich(spec(p), n)["konfigurationen"]["ok"] is False


def test_aufheben_nimmt_die_kinder_nicht_mit():
    """Review Fix 4: Die Richtung zählt. Aufheben löst nur das Feature (und seine eigene Skizze)."""
    v = kopie()
    for x in ("Bohrung2", "Fase3", "Verrundung1", "Skizze4"):
        feature(v, x)["unterdrueckt"]["Variante B"] = True
    n = kopie(v)
    for x in ("Bohrung2", "Skizze4"):
        feature(n, x)["unterdrueckt"]["Variante B"] = False
    p = {"id": "p1", "typ": "aufheben", "feature": "Bohrung2", "konfigurationen": ["Variante B"]}
    nur_ok(vergleich(spec(p), n, vorher=v))
    feature(n, "Fase3")["unterdrueckt"]["Variante B"] = False  # das Kind ging ungewollt mit auf
    assert vergleich(spec(p), n, vorher=v)["konfigurationen"]["ok"] is False


def test_aufheben_punkt_darf_nichts_unterdruecken():
    n = kopie()
    feature(n, "Fase3")["unterdrueckt"]["Standard"] = True  # ein Kind wird unterdrückt
    p = {"id": "p1", "typ": "aufheben", "feature": "Bohrung2", "konfigurationen": ["Standard"]}
    assert vergleich(spec(p), n)["konfigurationen"]["ok"] is False


def test_aufheben_punkt_unterdrueckt_nicht_das_feature_selbst():
    n = kopie()
    feature(n, "Bohrung2")["unterdrueckt"]["Standard"] = True  # False → True trotz aufheben-Punkt
    p = {"id": "p1", "typ": "aufheben", "feature": "Bohrung2", "konfigurationen": ["Standard"]}
    e = vergleich(spec(p), n)
    assert e["konfigurationen"]["ok"] is False and e["punkt:p1"]["ok"] is False


def test_unterdruecken_darf_nichts_aufheben():
    v = kopie()
    feature(v, "Fase3")["unterdrueckt"]["Standard"] = True
    n = kopie(v)
    feature(n, "Fase3")["unterdrueckt"]["Standard"] = False
    p = {"id": "p1", "typ": "unterdruecken", "feature": "Bohrung2", "konfigurationen": ["Standard"]}
    for x in ("Bohrung2", "Verrundung1", "Skizze4"):
        feature(n, x)["unterdrueckt"]["Standard"] = True
    assert vergleich(spec(p), n, vorher=v)["konfigurationen"]["ok"] is False


def test_unterdruecken_mit_geteilter_skizze_und_unbeteiligten():
    v = kopie()
    feature(v, "Skizze4")["kinder"] = ["Bohrung2", "Aufsatz"]
    feature(v, "Aufsatz")["eltern"] = ["Skizze1", "Skizze4"]
    n = kopie(v)
    for x in ("Bohrung2", "Fase3", "Verrundung1", "Skizze4"):
        feature(n, x)["unterdrueckt"]["Standard"] = True
    p = {"id": "p1", "typ": "unterdruecken", "feature": "Bohrung2", "konfigurationen": ["Standard"]}
    assert vergleich(spec(p), n, vorher=v)["konfigurationen"]["ok"] is False  # Skizze4 hat noch ein aktives Kind
    n = kopie()
    for x in ("Bohrung2", "Fase3", "Verrundung1", "Skizze4"):
        feature(n, x)["unterdrueckt"]["Standard"] = True
        feature(n, x)["unterdrueckt"]["Variante B"] = True  # nicht genannte Konfiguration
    assert vergleich(spec(p), n)["konfigurationen"]["ok"] is False
    n = kopie()
    feature(n, "Schnitt-Linear1")["unterdrueckt"]["Standard"] = True
    assert vergleich(spec(p), n)["konfigurationen"]["ok"] is False


def test_punkt_unterdruecken_und_aufheben():
    v = kopie()
    feature(v, "Fase3")["unterdrueckt"]["Variante B"] = True
    n = kopie(v)
    feature(n, "Fase3")["unterdrueckt"]["Variante B"] = False
    aufheben = {"id": "p1", "typ": "aufheben", "feature": "Fase3", "konfigurationen": ["Variante B"]}
    nur_ok(vergleich(spec(aufheben), n, vorher=v))
    assert vergleich(spec(aufheben), v, vorher=v)["punkt:p1"]["ok"] is False
    assert vergleich(spec({**aufheben, "feature": "Gibtsnicht"}), n, vorher=v)["punkt:p1"]["ok"] is False


# ----------------------------------------------------------------------------------------------------------- Neuaufbau

def test_neuer_neuaufbau_fehler():
    n = kopie()
    n["neuaufbau"].append({"konfiguration": "Standard", "feature": "Bohrung2", "code": 71, "warnung": False})
    e = vergleich(SPEC_LEER, n)
    assert e["neuaufbau"]["ok"] is False
    assert e["neuaufbau"]["ist"] == [{"konfiguration": "Standard", "meldung": "Bohrung2: Code 71"}]
    # vorhandene bleiben ok, auch ein bekannter Fehler in anderer Konfiguration ist neu
    n = kopie()
    n["neuaufbau"].append({"konfiguration": "Variante B", "feature": "Verrundung1", "code": 12, "warnung": False})
    assert vergleich(SPEC_LEER, n)["neuaufbau"]["ok"] is False
    # anderer Code am selben Feature ist neu
    n = kopie()
    n["neuaufbau"][0]["code"] = 13
    assert vergleich(SPEC_LEER, n)["neuaufbau"]["ok"] is False


def test_neue_warnung_zaehlt():
    n = kopie()
    n["neuaufbau"].append({"konfiguration": "Standard", "feature": "Aufsatz", "code": 3, "warnung": True})
    e = vergleich(SPEC_LEER, n)
    assert e["neuaufbau"]["ok"] is False and "Warnung 3" in e["neuaufbau"]["hinweis"]
    # dieselbe Nummer als Fehler statt Warnung ist ein eigener Eintrag
    n = kopie()
    n["neuaufbau"][1]["warnung"] = False
    assert vergleich(SPEC_LEER, n)["neuaufbau"]["ok"] is False


def test_neue_fehler_und_warnungen_einzeln():
    liste = [{"feature": "Fase3", "code": 7, "warnung": True}, {"feature": "Verrundung1", "code": 12, "warnung": False},
             {"feature": "Neu", "code": 1, "warnung": False}, {"feature": "Neu", "code": 2, "warnung": True}]
    assert neue_fehler(liste, VORHER, "Standard") == ["Neu: Code 1"]
    assert neue_warnungen(liste, VORHER, "Standard") == ["Neu: Warnung 2"]
    assert neue_fehler(liste, VORHER, "Variante B") == ["Verrundung1: Code 12", "Neu: Code 1"]


def test_bau_nutzt_dieselbe_neue_fehler():
    from swki.bestand import bau
    assert bau.neue_fehler is neue_fehler


# ------------------------------------------------------------------------------------------------------------------ Skizzen

def test_skizze_schlechter_ist_mangel():
    n = kopie()
    n["skizzen"]["Skizze4"] = 2  # voll → unterbestimmt
    e = vergleich(SPEC_LEER, n)
    assert e["skizzen"]["ok"] is False and e["skizzen"]["ist"] == [{"skizze": "Skizze4", "vorher": 3, "nachher": 2}]
    n["skizzen"]["Skizze4"] = 4  # voll → überbestimmt
    assert vergleich(SPEC_LEER, n)["skizzen"]["ok"] is False
    n["skizzen"]["Skizze5"] = 4  # unterbestimmt → überbestimmt: auch schlechter
    assert len(vergleich(SPEC_LEER, n)["skizzen"]["ist"]) == 2


def test_unterbestimmte_skizze_bleibt_ok_und_bessere_auch():
    n = kopie()
    assert VORHER["skizzen"]["Skizze5"] == 2
    assert vergleich(SPEC_LEER, n)["skizzen"]["ok"] is True
    n["skizzen"]["Skizze5"] = 3
    assert vergleich(SPEC_LEER, n)["skizzen"]["ok"] is True


def test_skizzen_rangfolge_deckt_alle_status_ab():
    assert set(SKIZZE_RANG) == {1, 2, 3, 4, 5, 6, 7}  # swConstrainedStatus_e
    assert SKIZZE_RANG[3] == max(SKIZZE_RANG.values()) and SKIZZE_RANG[2] > SKIZZE_RANG[4]


def test_neue_skizzen_nur_zur_information():
    n = kopie()
    n["skizzen"]["Gewinde M6 Skizze"] = 2
    e = vergleich(SPEC_LEER, n)
    assert e["skizzen"]["ok"] is True and e["skizzen"]["neu_nicht_voll_bestimmt"] == {"Gewinde M6 Skizze": 2}


# ----------------------------------------------------------------------------------------- Material und Eigenschaften

def test_material_nur_ueber_punkte():
    n = kopie()
    n["materialien"] = {"Standard": "1.4301 (X5CrNi18-10)", "Variante B": "1.4301 (X5CrNi18-10)"}
    n["material"] = "1.4301 (X5CrNi18-10)"
    e = vergleich(SPEC_LEER, n)
    assert e["material"]["ok"] is False and "Standard" in e["material"]["hinweis"]
    p = {"id": "p4", "typ": "material", "neu": "1.4301"}
    e = vergleich(spec(p), n)
    nur_ok(e)
    n["materialien"]["Variante B"] = "1.0038"  # nur eine Konfiguration umgestellt
    e = vergleich(spec(p), n)
    assert e["punkt:p4"]["ok"] is False and "Variante B" in e["punkt:p4"]["hinweis"]


def test_eigenschaften_nur_ueber_punkte():
    n = kopie()
    n["eigenschaften"]["datei"]["Revision"] = "B"
    e = vergleich(SPEC_LEER, n)
    assert e["eigenschaften"]["ok"] is False and "Revision" in e["eigenschaften"]["hinweis"]
    p = {"id": "p5", "typ": "eigenschaft", "name": "Revision", "neu": "B"}
    nur_ok(vergleich(spec(p), n))
    # richtige Eigenschaft, falsche Stelle (Konfiguration statt Datei)
    n2 = kopie()
    n2["eigenschaften"]["konfiguration"]["Standard"]["Revision"] = "B"
    e = vergleich(spec(p), n2)
    assert e["punkt:p5"]["ok"] is False and e["eigenschaften"]["ok"] is False


def test_eigenschaft_entfernen_und_konfiguration():
    n = kopie()
    del n["eigenschaften"]["konfiguration"]["Variante B"]["Bemerkung"]
    p = {"id": "p5", "typ": "eigenschaft", "name": "Bemerkung", "neu": None, "konfiguration": "Variante B"}
    nur_ok(vergleich(spec(p), n))
    assert vergleich(spec(p), kopie())["punkt:p5"]["ok"] is False
    n["eigenschaften"]["datei"]["Benennung"] = "Neu"  # eine nicht genannte Eigenschaft
    assert vergleich(spec(p), n)["eigenschaften"]["ok"] is False


# --------------------------------------------------------------------------------------------------------- Gleichungen

def test_gleichung_geaendert_ohne_punkt():
    n = kopie()
    next(g for g in n["gleichungen"] if g["links"] == "D3@Skizze2")["text"] = '"D3@Skizze2" = "D1@Skizze1" + 6'
    e = vergleich(SPEC_LEER, n)
    assert e["gleichungen"]["ok"] is False and e["gleichungen"]["ist"][0]["links"] == "D3@Skizze2"


def test_gleichung_leerzeichen_und_zahlenformat_sind_keine_aenderung():
    n = kopie()
    next(g for g in n["gleichungen"] if g["links"] == "D3@Skizze2")["text"] = '"D3@Skizze2"="D1@Skizze1"+5'
    next(g for g in n["gleichungen"] if g["links"] == "L")["text"] = '"L" = 100.0'
    assert vergleich(SPEC_LEER, n)["gleichungen"]["ok"] is True


def test_gleichung_neu_oder_entfernt_ist_mangel():
    n = kopie()
    n["gleichungen"].append({"index": 3, "text": '"M" = 1', "links": "M", "global": True})
    assert vergleich(SPEC_LEER, n)["gleichungen"]["ok"] is False
    n = kopie()
    n["gleichungen"].pop()
    assert vergleich(SPEC_LEER, n)["gleichungen"]["ok"] is False


def test_punkt_gleichung_text_und_variable():
    n = kopie()
    next(g for g in n["gleichungen"] if g["links"] == "D1@Skizze1")["text"] = '"D1@Skizze1" = "L" * 2'
    for k in ("Standard", "Variante B"):
        setze(n, "D1@Skizze1", k, 200.0)
        setze(n, "D3@Skizze2", k, 205.0)
    p = {"id": "p1", "typ": "gleichung", "gleichung": "D1@Skizze1", "alt": '"L"', "neu": '"L" * 2'}
    nur_ok(vergleich(spec(p), n))
    assert vergleich(spec({**p, "neu": '"L" * 3'}), n)["punkt:p1"]["ok"] is False
    v = {"id": "p2", "typ": "gleichung", "variable": "L", "alt": 100, "neu": "=A"}
    assert vergleich(spec(v), n, {"A": 100})["punkt:p2"]["ok"] is True  # Variable blieb: stimmt mit neu überein
    assert vergleich(spec(v), n, {"A": 120})["punkt:p2"]["ok"] is False


# ------------------------------------------------------------------------------------------------ Externe Referenzen

def test_neue_externe_referenz():
    n = kopie()
    n["externe_referenzen"] = ["C:\\Kunde\\Basis.SLDPRT"]
    e = vergleich(SPEC_LEER, n)
    assert e["externe_referenzen"]["ok"] is False and e["externe_referenzen"]["ist"] == [
        {"art": "neu", "pfad": "C:\\Kunde\\Basis.SLDPRT"}]


def test_vorhandene_externe_referenz_in_anderem_ordner_ist_nicht_neu():
    v = kopie()
    v["datei"]["ordner"] = "C:\\Auftrag\\bestand-1"
    v["externe_referenzen"] = ["C:\\Auftrag\\bestand-1\\Teile\\Basis.SLDPRT"]
    n = kopie()
    n["datei"]["ordner"] = "C:\\Auftrag\\lauf-1"
    n["externe_referenzen"] = ["C:\\Auftrag\\lauf-1\\Teile\\Basis.SLDPRT"]
    assert vergleich(SPEC_LEER, n, vorher=v)["externe_referenzen"]["ok"] is True
    n["externe_referenzen"] = ["C:\\Auftrag\\lauf-1\\Andere\\Basis.SLDPRT"]  # gleicher Name, anderer Pfad
    assert vergleich(SPEC_LEER, n, vorher=v)["externe_referenzen"]["ok"] is False


def test_externe_referenzen_ohne_ordner_sind_nicht_nachgewiesen():
    v = kopie()
    v["externe_referenzen"] = ["C:\\Auftrag\\bestand-1\\Basis.SLDPRT"]
    n = kopie()
    n["externe_referenzen"] = ["D:\\Kunde\\Original\\Basis.SLDPRT"]  # zeigt in den Kundenordner, ohne Ordner nicht erkennbar
    assert vergleich(SPEC_LEER, n, vorher=v)["externe_referenzen"]["ok"] is None
    n["externe_referenzen"] = ["D:\\Kunde\\Original\\Andere.SLDPRT"]
    assert vergleich(SPEC_LEER, n, vorher=v)["externe_referenzen"]["ok"] is False
    assert vergleich(SPEC_LEER, kopie(), vorher=kopie())["externe_referenzen"]["ok"] is True  # keine Referenzen: nichts offen


def test_externe_referenz_ausserhalb_bleibt_nur_bei_gleichem_pfad_unveraendert():
    v = kopie()
    v["datei"]["ordner"] = "C:\\Auftrag\\bestand-1"
    v["externe_referenzen"] = ["D:\\Kunde\\Basis.SLDPRT"]
    n = kopie()
    n["datei"]["ordner"] = "C:\\Auftrag\\lauf-1"
    n["externe_referenzen"] = ["D:\\Kunde\\Basis.SLDPRT"]
    assert vergleich(SPEC_LEER, n, vorher=v)["externe_referenzen"]["ok"] is True
    n["externe_referenzen"] = ["E:\\Fremd\\Basis.SLDPRT"]
    assert vergleich(SPEC_LEER, n, vorher=v)["externe_referenzen"]["ok"] is False


def test_externe_referenz_zeigt_aus_dem_lauf_ordner_heraus():
    v = kopie()
    v["datei"]["ordner"] = "C:\\Auftrag\\bestand-1"
    v["externe_referenzen"] = ["C:\\Auftrag\\bestand-1\\Basis.SLDPRT"]
    n = kopie()
    n["datei"]["ordner"] = "C:\\Auftrag\\lauf-1"
    n["externe_referenzen"] = ["C:\\Auftrag\\bestand-1\\Basis.SLDPRT"]  # zeigt zurück auf die Bestandskopie
    e = vergleich(SPEC_LEER, n, vorher=v)
    assert e["externe_referenzen"]["ok"] is False and e["externe_referenzen"]["ist"][0]["art"] == "heraus"
    n["externe_referenzen"] = ["C:\\Auftrag\\lauf-1\\Basis.SLDPRT"]
    assert vergleich(SPEC_LEER, n, vorher=v)["externe_referenzen"]["ok"] is True


# ------------------------------------------------------------------------------------------------------------- Sonstiges

def test_skript_punkt_ist_nicht_pruefbar():
    p = {"id": "p6", "typ": "skript", "datei": "skripte/p6.py", "luecke": "x"}
    e = vergleich(spec(p), kopie())
    assert e["punkt:p6"]["ok"] is None and "Notausgang" in e["punkt:p6"]["hinweis"]


def test_skript_punkt_neue_features_sind_nicht_nachgewiesen():
    n = _neues_feature(kopie(), "Irgendwas")
    p = {"id": "p6", "typ": "skript", "datei": "skripte/p6.py", "luecke": "x"}
    e = vergleich(spec(p), n)
    assert e["baum"]["ok"] is None and e["baum"]["ungeklaert"] == ["Irgendwas"] and "Irgendwas" in e["baum"]["hinweis"]
    # ein echter Mangel im Baum hat Vorrang
    n["reihenfolge"]["Standard"].remove("Fase3")
    assert vergleich(spec(p), n)["baum"]["ok"] is False


def test_skript_durchgelaufen_ist_ok_mit_hinweis():
    p = {"id": "p6", "typ": "skript", "datei": "skripte/p6.py", "luecke": "x"}
    e = eintraege(vergleiche(spec(p), kopie(), kopie(), {}, skript_gelaufen=frozenset({"p6"})))
    assert e["punkt:p6"]["ok"] is True and e["punkt:p6"]["hinweis"] == "Notausgang, Nachweis über Bereiche, masse_pruefen und Prüfer"


def test_skript_features_gelten_als_erklaert():
    """Was `bauen(ctx)` zurückgab, samt Unterfeatures; alles andere bleibt nicht nachgewiesen."""
    n = _neues_feature(_neues_feature(kopie(), "Nut"), "Irgendwas")
    feature(n, "Nut")["unter"] = ["Skizze Nut"]
    n["reihenfolge"]["Standard"].append("Skizze Nut")
    p = {"id": "p6", "typ": "skript", "datei": "skripte/p6.py", "luecke": "x"}
    e = eintraege(vergleiche(spec(p), VORHER, n, {}, skript_features=frozenset({"Nut"})))
    assert e["baum"]["ok"] is None and e["baum"]["ungeklaert"] == ["Irgendwas"]
    e = eintraege(vergleiche(spec(p), VORHER, n, {}, skript_features=frozenset({"Nut", "Irgendwas"})))
    assert e["baum"]["ok"] is True


def test_eingaben_bleiben_unveraendert():
    v, n = kopie(), kopie()
    setze(n, "D2@Skizze4", "Standard", 45.0)
    v0, n0 = copy.deepcopy(v), copy.deepcopy(n)
    vergleiche(spec({"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45}), v, n, {})
    assert v == v0 and n == n0


def test_mehrere_punkte_haben_je_einen_eintrag_in_spec_reihenfolge():
    n = kopie()
    setze(n, "D2@Skizze4", "Standard", 45.0)
    feature(n, "Fase3")["unterdrueckt"]["Standard"] = True
    punkte = [{"id": "p1", "typ": "mass", "mass": "D2@Skizze4", "alt": 40, "neu": 45, "konfigurationen": ["Standard"]},
              {"id": "p2", "typ": "unterdruecken", "feature": "Fase3", "konfigurationen": ["Standard"]}]
    liste = vergleiche(spec(*punkte), VORHER, n, {})
    assert [x["id"] for x in liste][:2] == ["punkt:p1", "punkt:p2"]
    nur_ok(eintraege(liste))
