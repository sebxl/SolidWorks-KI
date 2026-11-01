"""Vergleich der Baugruppe vorher/nachher (Spec Bestandsdateien §8.3, Plan Etappe 2 Task 5), ohne SolidWorks."""

import copy

from swki.baugruppe.bewegung import TOL_BEWEGT_MM
from swki.bestand.vergleich_baugruppe import vergleiche_baugruppe, vergleiche_dateien
from tests.bestand.beispiel_baugruppe import (HAUPT, NEUE_DATEI, NEUE_KOMPONENTE, SPEC, baugruppen_aufnahme, dateien_json,
                                              komponente, lauf_shas, nachher_zu_spec, verknuepfung)

KOMPONENTEN_IDS = ["komponenten", "verknuepfungen", "bestimmtheit", "kollision", "lage"]


def punkt(typ: str, pid: str, **felder) -> dict:
    return {"id": pid, "typ": typ, **felder}


def spec_aus(*punkte, **rest) -> dict:
    return {"art": "aenderung", "name": "T", "bestand": {"datei": HAUPT, "sha256": "x" * 64, "aufnahme": 1},
            "parameter": {"ABSTAND_NEU": 12, "W": 30}, "punkte": list(punkte) or [punkt("eigenschaft", "s1", name="Revision", neu="B")],
            **rest}


def vergleich(spec, nachher, neue=None, ersetzt=None, vorher=None, neue_dateien="auto") -> dict[str, dict]:
    """Die Einträge von `vergleiche_baugruppe` nach ID. `neue_dateien` "auto": die Dateien der Komponenten, die der Bestand nicht kennt."""
    vorher = vorher if vorher is not None else baugruppen_aufnahme()
    if neue_dateien == "auto":
        bekannt = {k["datei"] for k in vorher["komponenten"].values()}
        neue_dateien = sorted({k["datei"] for k in nachher["komponenten"].values() if k["datei"] not in bekannt and k["datei"]})
    eintraege = vergleiche_baugruppe(spec, vorher, nachher, neue or {}, ersetzt or {}, neue_dateien)
    assert len({e["id"] for e in eintraege}) == len(eintraege)
    return {e["id"]: e for e in eintraege}


def hinweise(e: dict) -> str:
    return e.get("hinweis", "")


def verschiebe(aufnahme: dict, name: str, mm: float, konfiguration: str = "Standard") -> None:
    aufnahme["komponenten"][name]["transform"][konfiguration][9] += mm / 1000


def zwei_konfigurationen(a: dict) -> dict:
    """Die Aufnahme mit einer zweiten Konfiguration 'Variante B', die in jedem Wert der ersten gleicht."""
    a["konfigurationen"] = ["Standard", "Variante B"]
    for k in a["komponenten"].values():
        for feld in ("fixiert", "unterdrueckt", "status", "transform", "konfigurationen"):
            k[feld]["Variante B"] = copy.deepcopy(k[feld]["Standard"])
    for v in a["verknuepfungen"].values():
        for feld in ("fehler", "unterdrueckt", "werte"):
            v[feld]["Variante B"] = copy.deepcopy(v[feld]["Standard"])
    return a


def setze_wert(a: dict, name: str, feld: str, wert, konfiguration: str | None = None) -> None:
    """`wert`/`min`/`max` einer Verknüpfung: in allen Konfigurationen (oder nur `konfiguration`); die aktive auch als Feld oben."""
    m = a["verknuepfungen"][name]
    for k, w in m["werte"].items():
        if konfiguration in (None, k):
            w[feld] = wert
    if konfiguration in (None, a["aktiv"]):
        m[feld] = wert


def setze_konfig(a: dict, name: str, text: str, konfiguration: str | None = None) -> None:
    """Die referenzierte Konfiguration einer Komponente: in allen Konfigurationen (oder nur `konfiguration`)."""
    k = a["komponenten"][name]
    for kfg in k["konfigurationen"]:
        if konfiguration in (None, kfg):
            k["konfigurationen"][kfg] = text
    if konfiguration in (None, a["aktiv"]):
        k["konfiguration"] = text


# ---------------------------------------------------------------------------------------------------------- Grundfall

def test_unveraendert_alles_ok():
    e = vergleich(spec_aus(), baugruppen_aufnahme())
    assert list(e) == KOMPONENTEN_IDS
    assert all(x["ok"] is True for x in e.values()), e


def test_der_lauf_zur_beispiel_spec_ist_ok():
    nachher, neue, ersetzt = nachher_zu_spec()
    e = vergleich(SPEC, nachher, neue, ersetzt, neue_dateien=[NEUE_DATEI])
    assert list(e) == [*KOMPONENTEN_IDS, "punkt:k1", "punkt:v1", "punkt:w1"]
    assert all(x["ok"] is True for x in e.values()), {k: x for k, x in e.items() if x["ok"] is not True}


def test_teil_punkte_und_haupt_punkte_haben_hier_keinen_eintrag():
    e = vergleich(SPEC, baugruppen_aufnahme())
    assert not any(i in e for i in ("punkt:p1", "punkt:p2", "punkt:p3", "punkt:s1"))


# ------------------------------------------------------------------------------------------------------- Komponenten

def test_komponente_weg_ohne_punkt_ist_mangel():
    n = baugruppen_aufnahme()
    del n["komponenten"]["Platte-1"]
    e = vergleich(spec_aus(), n)
    assert e["komponenten"]["ok"] is False
    assert e["komponenten"]["fehlen"] == ["Platte-1"]
    assert "Platte-1" in hinweise(e["komponenten"])


def test_komponente_entfernen_mit_punkt_ist_ok():
    n = baugruppen_aufnahme()
    del n["komponenten"]["Platte-1"], n["verknuepfungen"]["Winkel1"]
    e = vergleich(spec_aus(punkt("komponente_entfernen", "r1", komponente="Platte-1", verknuepfungen=["Winkel1"])), n)
    assert all(x["ok"] is True for x in e.values()), e


def test_komponente_entfernen_punkt_ohne_wirkung_ist_mangel():
    e = vergleich(spec_aus(punkt("komponente_entfernen", "r1", komponente="Platte-1", verknuepfungen=["Winkel1"])), baugruppen_aufnahme())
    assert e["punkt:r1"]["ok"] is False
    assert "Platte-1" in hinweise(e["punkt:r1"])


def test_verknuepfung_des_entfernten_bleibt_ist_mangel():
    n = baugruppen_aufnahme()
    del n["komponenten"]["Platte-1"]
    e = vergleich(spec_aus(punkt("komponente_entfernen", "r1", komponente="Platte-1", verknuepfungen=["Winkel1"])), n)
    assert e["punkt:r1"]["ok"] is False and "Winkel1" in hinweise(e["punkt:r1"])


def test_neue_komponente_aus_punkt_ist_ok():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT")
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"normteil": "ISO 4762 M6x16"}))
    e = vergleich(s, n, {"k1": ["Neu-1"]})
    assert all(x["ok"] is True for x in e.values()), e
    fremd = vergleich(s, n)  # das Protokoll kennt sie nicht
    assert fremd["komponenten"]["ok"] is False and fremd["komponenten"]["fremd"] == ["Neu-1"]
    assert fremd["punkt:k1"]["ok"] is False


def test_neue_komponente_fehlt_im_lauf():
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"normteil": "ISO 4762 M6x16"}))
    e = vergleich(s, baugruppen_aufnahme(), {"k1": ["Neu-1"]})
    assert e["punkt:k1"]["ok"] is False and "Neu-1" in hinweise(e["punkt:k1"])
    assert e["komponenten"]["ok"] is False


def test_neue_komponente_wie_traegt_datei_und_konfiguration_der_vorlage():
    n = baugruppen_aufnahme()
    n["komponenten"]["Schraube-12"] = komponente("teile/Schraube.SLDPRT")
    s = spec_aus(punkt("komponente_neu", "k1", wie="Schraube-1"))
    assert vergleich(s, n, {"k1": ["Schraube-12"]})["punkt:k1"]["ok"] is True
    n["komponenten"]["Schraube-12"]["datei"] = "teile/Platte.SLDPRT"
    assert vergleich(s, n, {"k1": ["Schraube-12"]})["punkt:k1"]["ok"] is False


def test_neue_komponente_fixiert_und_konfiguration_aus_dem_punkt():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT", fixiert=True)
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}, fixiert=True, konfiguration="Standard"))
    assert vergleich(s, n, {"k1": ["Neu-1"]})["punkt:k1"]["ok"] is True
    n["komponenten"]["Neu-1"]["fixiert"]["Standard"] = False
    assert vergleich(s, n, {"k1": ["Neu-1"]})["punkt:k1"]["ok"] is False
    n["komponenten"]["Neu-1"]["fixiert"]["Standard"] = True
    setze_konfig(n, "Neu-1", "Andere")
    assert vergleich(s, n, {"k1": ["Neu-1"]})["punkt:k1"]["ok"] is False


def test_andere_konfiguration_ist_mangel():
    n = baugruppen_aufnahme()
    setze_konfig(n, "Deckel-1", "Variante")
    e = vergleich(spec_aus(), n)
    assert e["komponenten"]["ok"] is False and "Deckel-1" in hinweise(e["komponenten"])
    assert e["komponenten"]["ist"][0]["feld"] == "konfiguration"


def test_andere_datei_ist_mangel_auch_in_anderer_schreibweise_nicht():
    n = baugruppen_aufnahme()
    n["komponenten"]["Deckel-1"]["datei"] = "TEILE\\deckel.sldprt"  # gleiche Datei, andere Schreibweise
    assert vergleich(spec_aus(), n)["komponenten"]["ok"] is True
    n["komponenten"]["Deckel-1"]["datei"] = "teile/Platte.SLDPRT"
    assert vergleich(spec_aus(), n)["komponenten"]["ok"] is False


def test_fixiert_geaendert_ist_mangel():
    n = baugruppen_aufnahme()
    n["komponenten"]["Gehaeuse-1"]["fixiert"]["Standard"] = False
    e = vergleich(spec_aus(), n)
    assert e["komponenten"]["ok"] is False


def test_unterdrueckungszustand_geaendert_ohne_punkt_ist_mangel():
    n = baugruppen_aufnahme()
    n["komponenten"]["Deckel-1"]["unterdrueckt"]["Standard"] = True
    n["komponenten"]["Deckel-1"]["transform"]["Standard"] = None
    e = vergleich(spec_aus(), n)
    assert e["komponenten"]["ok"] is False
    assert e["komponenten"]["ist"][0]["feld"] == "unterdrueckt"


def test_lesen_gescheitert_macht_komponenten_unsicher_ein_mangel_hat_vorrang():
    n = baugruppen_aufnahme()
    n["komponenten"]["Deckel-1"]["fixiert"]["Standard"] = None
    assert vergleich(spec_aus(), n)["komponenten"]["ok"] is None
    del n["komponenten"]["Platte-1"]
    assert vergleich(spec_aus(), n)["komponenten"]["ok"] is False


def test_kinder_einer_neuen_unterbaugruppe_gehoeren_dazu():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDASM")
    n["komponenten"]["Neu-1/Teil-1"] = komponente("teile/Welle.SLDPRT")
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}))
    assert vergleich(s, n, {"k1": ["Neu-1"]})["komponenten"]["ok"] is True


# ------------------------------------------------------------------------------------------------------------- Lage

def test_lage_verschoben_ohne_erlaubnis():
    n = baugruppen_aufnahme()
    verschiebe(n, "Deckel-1", TOL_BEWEGT_MM + 0.01)
    e = vergleich(spec_aus(), n)
    assert e["lage"]["ok"] is False and "Deckel-1" in hinweise(e["lage"])
    assert e["komponenten"]["ok"] is True  # die Lage meldet nur `lage`


def test_lage_innerhalb_der_toleranz_ist_ok():
    n = baugruppen_aufnahme()
    verschiebe(n, "Deckel-1", TOL_BEWEGT_MM / 2)
    assert vergleich(spec_aus(), n)["lage"]["ok"] is True


def test_lage_gedreht_ist_verschoben():
    n = baugruppen_aufnahme()
    n["komponenten"]["Deckel-1"]["transform"]["Standard"][1] = 0.01
    assert vergleich(spec_aus(), n)["lage"]["ok"] is False


def test_lage_folgen_erlaubt_nur_genannte():
    n = baugruppen_aufnahme()
    verschiebe(n, "Deckel-1", 1)
    verschiebe(n, "Platte-1", 1)
    s = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu=12, lage_folgen=["Deckel-1"]))
    e = vergleich(s, n)
    assert e["lage"]["ok"] is False
    assert [x["komponente"] for x in e["lage"]["ist"]] == ["Platte-1"]


def test_lage_folgen_eines_punkts_gilt_fuer_den_ganzen_lauf():
    n = baugruppen_aufnahme()
    verschiebe(n, "Deckel-1", 1)
    s = spec_aus(punkt("eigenschaft", "s1", name="R", neu="B"), punkt("verknuepfung_loeschen", "d1", verknuepfung="Abstand2", lage_folgen=["Deckel-1"]))
    n["verknuepfungen"].pop("Abstand2")
    assert vergleich(s, n)["lage"]["ok"] is True


def test_lage_folgen_mit_punkt_id_einer_neuen_komponente_stoert_nicht():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT")
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}, lage_folgen=["k1"]))
    assert vergleich(s, n, {"k1": ["Neu-1"]})["lage"]["ok"] is True


def test_jede_instanz_einzeln():
    n = baugruppen_aufnahme()
    verschiebe(n, "Schraube-1", 2)
    verschiebe(n, "Schraube-3", 2)  # gleiche Datei, andere Instanz
    s = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu=12, lage_folgen=["Schraube-1"]))
    e = vergleich(s, n)
    assert e["lage"]["ok"] is False
    assert [x["komponente"] for x in e["lage"]["ist"]] == ["Schraube-3"]
    n2 = baugruppen_aufnahme()
    verschiebe(n2, "Schraube-1", 2)
    assert vergleich(s, n2)["lage"]["ok"] is True


def test_kind_einer_unterbaugruppe_verschoben():
    n = baugruppen_aufnahme()
    verschiebe(n, "Unter-1/Welle-1", 1)  # Datei der Unterbaugruppe gleich, ihr Kind wandert
    e = vergleich(spec_aus(), n)
    assert e["lage"]["ok"] is False and "Unter-1/Welle-1" in hinweise(e["lage"])


def test_lage_folgen_der_unterbaugruppe_nimmt_ihre_kinder_mit():
    n = baugruppen_aufnahme()
    verschiebe(n, "Unter-1", 1)
    verschiebe(n, "Unter-1/Welle-1", 1)
    s = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu=12, lage_folgen=["Unter-1"]))
    assert vergleich(s, n)["lage"]["ok"] is True
    s2 = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu=12, lage_folgen=["Unter-1/Welle-1"]))
    assert vergleich(s2, n)["lage"]["ok"] is False  # nur das Kind ist erlaubt, nicht Unter-1 selbst


def test_unterdrueckte_komponente_ohne_transform():
    v = baugruppen_aufnahme()
    for a in (v,):
        a["komponenten"]["Deckel-1"]["unterdrueckt"]["Standard"] = True
        a["komponenten"]["Deckel-1"]["transform"]["Standard"] = None
    n = copy.deepcopy(v)
    assert vergleich(spec_aus(), n, vorher=v)["lage"]["ok"] is True  # in beiden unterdrückt: zählt nicht
    aktiv = baugruppen_aufnahme()
    aktiv["komponenten"]["Deckel-1"]["transform"]["Standard"] = None  # aktiv, aber nicht gelesen
    e = vergleich(spec_aus(), aktiv)
    assert e["lage"]["ok"] is None and "Deckel-1" in hinweise(e["lage"])


def test_lage_unlesbar_und_mangel_mangel_hat_vorrang():
    n = baugruppen_aufnahme()
    n["komponenten"]["Deckel-1"]["transform"]["Standard"] = None
    verschiebe(n, "Platte-1", 1)
    assert vergleich(spec_aus(), n)["lage"]["ok"] is False


def test_unterdrueckungswechsel_laesst_die_lage_unbewiesen():
    n = baugruppen_aufnahme()
    n["komponenten"]["Deckel-1"]["unterdrueckt"]["Standard"] = True
    n["komponenten"]["Deckel-1"]["transform"]["Standard"] = None
    e = vergleich(spec_aus(), n)
    assert e["lage"]["ok"] is None and e["komponenten"]["ok"] is False


def test_je_konfiguration():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    verschiebe(n, "Deckel-1", 1, "Variante B")  # Abweichung nur in Variante B
    e = vergleich(spec_aus(), n, vorher=v)
    assert e["lage"]["ok"] is False
    assert e["lage"]["ist"][0]["konfiguration"] == "Variante B"
    n = copy.deepcopy(v)
    n["komponenten"]["Platte-1"]["unterdrueckt"]["Variante B"] = True
    assert vergleich(spec_aus(), n, vorher=v)["komponenten"]["ok"] is False
    n = copy.deepcopy(v)
    n["komponenten"]["Platte-1"]["status"]["Variante B"] = 2
    assert vergleich(spec_aus(), n, vorher=v)["bestimmtheit"]["ok"] is False
    n = copy.deepcopy(v)
    n["verknuepfungen"]["Abstand2"]["fehler"]["Variante B"] = 4
    assert vergleich(spec_aus(), n, vorher=v)["verknuepfungen"]["ok"] is False


def test_keine_gemeinsame_konfiguration_ist_mangel_und_unbewiesen():
    v = baugruppen_aufnahme()
    n = baugruppen_aufnahme(konfigurationen=["Andere"], aktiv="Andere")
    e = vergleich(spec_aus(), n, vorher=v)
    assert e["komponenten"]["ok"] is False
    assert e["lage"]["ok"] is None and e["bestimmtheit"]["ok"] is None and e["verknuepfungen"]["ok"] is None


# ----------------------------------------------------------------------------------------------------------- Ersetzen

def _ersetzt_stand(alle: bool = False):
    n = baugruppen_aufnahme()
    ersetzt = {}
    for alt in ([f"Schraube-{i}" for i in range(1, 12)] if alle else ["Schraube-1"]):
        neu = alt.replace("Schraube", "Neu")
        n["komponenten"][neu] = n["komponenten"].pop(alt)
        n["komponenten"][neu]["datei"] = "Neu.SLDPRT"
        setze_konfig(n, neu, "Andere")  # Datei und Konfiguration dürfen abweichen
        for v in n["verknuepfungen"].values():
            v["partner"] = [neu if p == alt else p for p in v["partner"]]
        ersetzt[alt] = neu
    return n, ersetzt


def test_ersetzte_komponente_ist_kein_fehlt_und_fremd():
    n, ersetzt = _ersetzt_stand()
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}))
    e = vergleich(s, n, ersetzt=ersetzt)
    assert all(x["ok"] is True for x in e.values()), {k: x for k, x in e.items() if x["ok"] is not True}


def test_ersetzte_komponente_ohne_zuordnung_ist_fehlt_und_fremd():
    n, _ = _ersetzt_stand()
    e = vergleich(spec_aus(), n)
    assert e["komponenten"]["fehlen"] == ["Schraube-1"] and e["komponenten"]["fremd"] == ["Neu-1"]


def test_ersetzen_mit_alle_instanzen():
    n, ersetzt = _ersetzt_stand(alle=True)
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}, alle_instanzen=True))
    e = vergleich(s, n, {"e1": sorted(ersetzt.values())}, ersetzt)
    assert all(x["ok"] is True for x in e.values()), {k: x for k, x in e.items() if x["ok"] is not True}


def test_ersetzen_alle_instanzen_verlangt_jede_instanz():
    n, ersetzt = _ersetzt_stand()  # nur Schraube-1 ersetzt
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}, alle_instanzen=True))
    e = vergleich(s, n, ersetzt=ersetzt)
    assert e["punkt:e1"]["ok"] is False and "Schraube-2" in hinweise(e["punkt:e1"])


def test_ersetzen_ohne_wirkung_ist_mangel():
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}))
    assert vergleich(s, baugruppen_aufnahme())["punkt:e1"]["ok"] is False


def test_ersetzte_komponente_verlangt_gleiche_lage_ausser_lage_folgen():
    n, ersetzt = _ersetzt_stand()
    verschiebe(n, "Neu-1", 1)
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}))
    assert vergleich(s, n, ersetzt=ersetzt)["lage"]["ok"] is False
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}, lage_folgen=["Schraube-1"]))
    assert vergleich(s, n, ersetzt=ersetzt)["lage"]["ok"] is True
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}, lage_folgen=["Neu-1"]))
    assert vergleich(s, n, ersetzt=ersetzt)["lage"]["ok"] is True


def test_ersetzte_komponente_verliert_verknuepfung_ist_mangel():
    n, ersetzt = _ersetzt_stand()
    del n["verknuepfungen"]["Abstand1"]  # SolidWorks konnte sie nicht neu zuordnen
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}))
    assert vergleich(s, n, ersetzt=ersetzt)["verknuepfungen"]["ok"] is False


def test_ersetzte_komponente_status_nicht_schlechter():
    n, ersetzt = _ersetzt_stand()
    n["komponenten"]["Neu-1"]["status"]["Standard"] = 2
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}))
    assert vergleich(s, n, ersetzt=ersetzt)["bestimmtheit"]["ok"] is False


def test_ersetzte_komponente_alte_kollision_bleibt_bekannt():
    v = baugruppen_aufnahme(kollisionen=[{"paar": ["Schraube-1", "Gehaeuse-1"], "volumen": 2.0}])
    n, ersetzt = _ersetzt_stand()
    n["kollisionen"] = [{"paar": ["Gehaeuse-1", "Neu-1"], "volumen": 2.0}]
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}))
    assert vergleich(s, n, ersetzt=ersetzt, vorher=v)["kollision"]["ok"] is True


# ----------------------------------------------------------------------------------------------------- Verknüpfungen

def test_verknuepfung_weg_ohne_punkt():
    n = baugruppen_aufnahme()
    del n["verknuepfungen"]["Abstand2"]
    e = vergleich(spec_aus(), n)
    assert e["verknuepfungen"]["ok"] is False and "Abstand2" in hinweise(e["verknuepfungen"])
    s = spec_aus(punkt("verknuepfung_loeschen", "d1", verknuepfung="Abstand2"))
    e = vergleich(s, n)
    assert e["verknuepfungen"]["ok"] is True and e["punkt:d1"]["ok"] is True


def test_verknuepfung_loeschen_ohne_wirkung_ist_mangel():
    e = vergleich(spec_aus(punkt("verknuepfung_loeschen", "d1", verknuepfung="Abstand2")), baugruppen_aufnahme())
    assert e["punkt:d1"]["ok"] is False


def test_verknuepfung_fehler_aus_dem_bestand_zaehlt_nicht():
    v = baugruppen_aufnahme()
    v["verknuepfungen"]["Abstand2"]["fehler"]["Standard"] = 7
    n = copy.deepcopy(v)
    e = vergleich(spec_aus(), n, vorher=v)
    assert e["verknuepfungen"]["ok"] is True
    assert e["verknuepfungen"]["bekannt"] == [{"verknuepfung": "Abstand2", "konfiguration": "Standard", "code": 7}]


def test_neuer_verknuepfungsfehler_ist_mangel():
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Abstand2"]["fehler"]["Standard"] = 7
    e = vergleich(spec_aus(), n)
    assert e["verknuepfungen"]["ok"] is False and "Abstand2" in hinweise(e["verknuepfungen"])
    assert e["verknuepfungen"]["bekannt"] == []


def test_anderer_fehlercode_am_alten_fehler_ist_neu():
    v = baugruppen_aufnahme()
    v["verknuepfungen"]["Abstand2"]["fehler"]["Standard"] = 7
    n = copy.deepcopy(v)
    n["verknuepfungen"]["Abstand2"]["fehler"]["Standard"] = 8
    assert vergleich(spec_aus(), n, vorher=v)["verknuepfungen"]["ok"] is False


def test_behobener_fehler_ist_kein_mangel():
    v = baugruppen_aufnahme()
    v["verknuepfungen"]["Abstand2"]["fehler"]["Standard"] = 7
    assert vergleich(spec_aus(), baugruppen_aufnahme(), vorher=v)["verknuepfungen"]["ok"] is True


def test_fehler_nicht_lesbar_ist_unbewiesen():
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Abstand2"]["fehler"]["Standard"] = None
    assert vergleich(spec_aus(), n)["verknuepfungen"]["ok"] is None


def test_wert_geaendert_nur_mit_punkt():
    n = baugruppen_aufnahme()
    setze_wert(n, "Abstand1", "wert", 11.0)
    assert vergleich(spec_aus(), n)["verknuepfungen"]["ok"] is False
    s = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu=11))
    e = vergleich(s, n)
    assert e["verknuepfungen"]["ok"] is True and e["punkt:w1"]["ok"] is True
    setze_wert(n, "Abstand2", "wert", 4.0)  # ein anderer Abstand ändert sich mit
    assert vergleich(s, n)["verknuepfungen"]["ok"] is False


def test_wert_punkt_ohne_wirkung_oder_falscher_wert_ist_mangel():
    s = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu="=ABSTAND_NEU"))
    assert vergleich(s, baugruppen_aufnahme())["punkt:w1"]["ok"] is False
    n = baugruppen_aufnahme()
    setze_wert(n, "Abstand1", "wert", 12.5)
    e = vergleich(s, n)
    assert e["punkt:w1"]["ok"] is False and "12.5" in hinweise(e["punkt:w1"])
    setze_wert(n, "Abstand1", "wert", 12.0)
    assert vergleich(s, n)["punkt:w1"]["ok"] is True


def test_grenzwert_punkt_nur_das_genannte_feld():
    s = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Grenze_Abstand1", grenze="max", alt=5, neu=8))
    n = baugruppen_aufnahme()
    setze_wert(n, "Grenze_Abstand1", "max", 8.0)
    e = vergleich(s, n)
    assert e["punkt:w1"]["ok"] is True and e["verknuepfungen"]["ok"] is True
    setze_wert(n, "Grenze_Abstand1", "min", 1.0)  # min war nicht gemeint
    assert vergleich(s, n)["verknuepfungen"]["ok"] is False
    n2 = baugruppen_aufnahme()
    setze_wert(n2, "Grenze_Abstand1", "min", 8.0)  # falsches Feld statt max
    assert vergleich(s, n2)["punkt:w1"]["ok"] is False


def test_verknuepfung_partner_oder_typ_geaendert_ist_mangel():
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Abstand1"]["partner"] = ["Schraube-1", "Platte-1"]
    assert vergleich(spec_aus(), n)["verknuepfungen"]["ok"] is False
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Winkel1"]["typ"] = 5
    assert vergleich(spec_aus(), n)["verknuepfungen"]["ok"] is False
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Abstand1"]["gesteuert"] = True
    assert vergleich(spec_aus(), n)["verknuepfungen"]["ok"] is False


def test_verknuepfung_unterdrueckt_ist_mangel():
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Winkel1"]["unterdrueckt"]["Standard"] = True
    assert vergleich(spec_aus(), n)["verknuepfungen"]["ok"] is False


def test_zusaetzliche_verknuepfung_ohne_punkt_ist_mangel():
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Parallel9"] = verknuepfung(3, ["Deckel-1", "Platte-1"])
    e = vergleich(spec_aus(), n)
    assert e["verknuepfungen"]["ok"] is False and "Parallel9" in hinweise(e["verknuepfungen"])


def test_neue_verknuepfung_aus_punkt_ist_ok():
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Abstand4"] = verknuepfung(5, ["Deckel-1", "Platte-1"], wert=12.0)
    s = spec_aus(punkt("verknuepfung_neu", "v1", art="abstand", wert="=ABSTAND_NEU", a={"komponente": "Platte-1", "feature": "F"},
                       b={"komponente": "Deckel-1", "feature": "F"}))
    e = vergleich(s, n)
    assert e["punkt:v1"]["ok"] is True and e["verknuepfungen"]["ok"] is True, e


def test_neue_verknuepfung_falscher_wert_oder_fehlend_oder_falsche_partner():
    s = spec_aus(punkt("verknuepfung_neu", "v1", art="abstand", wert=12, a={"komponente": "Platte-1", "feature": "F"},
                       b={"komponente": "Deckel-1", "feature": "F"}))
    assert vergleich(s, baugruppen_aufnahme())["punkt:v1"]["ok"] is False
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Abstand4"] = verknuepfung(5, ["Deckel-1", "Platte-1"], wert=11.0)
    e = vergleich(s, n)
    assert e["punkt:v1"]["ok"] is False and "11" in hinweise(e["punkt:v1"])
    n["verknuepfungen"]["Abstand4"] = verknuepfung(5, ["Deckel-1", "Schieber-1"], wert=12.0)
    e = vergleich(s, n)
    assert e["punkt:v1"]["ok"] is False
    assert e["verknuepfungen"]["ok"] is False  # und die Verknüpfung gehört keinem Punkt


def test_neue_verknuepfung_mit_fehler_oder_unterdrueckt_ist_mangel():
    s = spec_aus(punkt("verknuepfung_neu", "v1", art="konzentrisch", a={"komponente": "Platte-1", "referenz": "F"},
                       b={"komponente": "Deckel-1", "referenz": "F"}))
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Konzentrisch9"] = verknuepfung(1, ["Deckel-1", "Platte-1"])
    assert vergleich(s, n)["punkt:v1"]["ok"] is True
    n["verknuepfungen"]["Konzentrisch9"]["fehler"]["Standard"] = 3
    e = vergleich(s, n)
    assert e["punkt:v1"]["ok"] is False and e["verknuepfungen"]["ok"] is False
    n["verknuepfungen"]["Konzentrisch9"]["fehler"]["Standard"] = 0
    n["verknuepfungen"]["Konzentrisch9"]["unterdrueckt"]["Standard"] = True
    assert vergleich(s, n)["punkt:v1"]["ok"] is False


def test_neue_grenzverknuepfung_prueft_min_und_max_und_grenze():
    s = spec_aus(punkt("verknuepfung_neu", "v1", art="grenze_abstand", min=0, max="=W", a={"komponente": "Platte-1", "feature": "F"},
                       b={"komponente": "Deckel-1", "feature": "F"}))
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Grenze_Abstand2"] = verknuepfung(5, ["Platte-1", "Deckel-1"], wert=3.0, min_=0.0, max_=30.0, grenze=True)
    assert vergleich(s, n)["punkt:v1"]["ok"] is True
    setze_wert(n, "Grenze_Abstand2", "max", 25.0)
    assert vergleich(s, n)["punkt:v1"]["ok"] is False
    setze_wert(n, "Grenze_Abstand2", "max", 30.0)
    n["verknuepfungen"]["Grenze_Abstand2"]["grenze"] = False  # ein gewöhnlicher Abstand ist keine Grenze
    assert vergleich(s, n)["punkt:v1"]["ok"] is False


def test_scharnier_braucht_konzentrisch_und_anlage():
    s = spec_aus(punkt("verknuepfung_neu", "v1", art="scharnier", a={"komponente": "Platte-1", "feature": "F"},
                       b={"komponente": "Deckel-1", "feature": "F"}, anlage_a={"komponente": "Platte-1", "feature": "G"},
                       anlage_b={"komponente": "Deckel-1", "feature": "G"}))
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Konzentrisch9"] = verknuepfung(1, ["Platte-1", "Deckel-1"])
    assert vergleich(s, n)["punkt:v1"]["ok"] is False  # die Anlage fehlt
    n["verknuepfungen"]["Deckungsgleich9"] = verknuepfung(0, ["Platte-1", "Deckel-1"])
    n["verknuepfungen"]["Deckungsgleich9"]["ausrichtung"] = 1  # die Anlage ist vorgabegemäß entgegengesetzt
    e = vergleich(s, n)
    assert e["punkt:v1"]["ok"] is True and e["verknuepfungen"]["ok"] is True


def test_zwei_punkte_beanspruchen_nicht_dieselbe_verknuepfung():
    anker = {"a": {"komponente": "Platte-1", "feature": "F"}, "b": {"komponente": "Deckel-1", "feature": "F"}}
    s = spec_aus(punkt("verknuepfung_neu", "v1", art="abstand", wert=12, **anker), punkt("verknuepfung_neu", "v2", art="abstand", wert=12, **anker))
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Abstand4"] = verknuepfung(5, ["Deckel-1", "Platte-1"], wert=12.0)
    e = vergleich(s, n)
    assert {e["punkt:v1"]["ok"], e["punkt:v2"]["ok"]} == {True, False}


def test_neue_verknuepfung_an_neuer_komponente_ueber_punkt_id():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT")
    n["verknuepfungen"]["Konzentrisch9"] = verknuepfung(1, ["Neu-1", "Gehaeuse-1"])
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}),
                 punkt("verknuepfung_neu", "v1", art="konzentrisch", a={"komponente": "k1", "feature": "F"},
                       b={"komponente": "Gehaeuse-1", "feature": "F"}))
    e = vergleich(s, n, {"k1": ["Neu-1"]})
    assert all(x["ok"] is True for x in e.values()), e


def test_fehler_an_neuer_komponente_stoert_den_punkt():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT")
    n["verknuepfungen"]["Konzentrisch9"] = verknuepfung(1, ["Neu-1", "Gehaeuse-1"])
    n["verknuepfungen"]["Konzentrisch9"]["fehler"]["Standard"] = 2
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}))
    assert vergleich(s, n, {"k1": ["Neu-1"]})["punkt:k1"]["ok"] is False


# ------------------------------------------------------------------------------------------------------ Bestimmtheit

def test_bestimmtheit_schlechter_ist_mangel():
    n = baugruppen_aufnahme()
    n["komponenten"]["Deckel-1"]["status"]["Standard"] = 2  # 3 → 2 ohne Punkt
    e = vergleich(spec_aus(), n)
    assert e["bestimmtheit"]["ok"] is False and "Deckel-1" in hinweise(e["bestimmtheit"])


def test_bestimmtheit_nur_hochstufen_ist_kein_mangel():
    v = baugruppen_aufnahme()
    v["komponenten"]["Deckel-1"]["status"]["Standard"] = 2
    assert vergleich(spec_aus(), baugruppen_aufnahme(), vorher=v)["bestimmtheit"]["ok"] is True
    v["komponenten"]["Deckel-1"]["status"]["Standard"] = 4  # überbestimmt war schlechter
    assert vergleich(spec_aus(), baugruppen_aufnahme(), vorher=v)["bestimmtheit"]["ok"] is True


def test_bestimmtheit_ueberbestimmt_ist_schlechter_als_unterbestimmt():
    v = baugruppen_aufnahme()
    v["komponenten"]["Deckel-1"]["status"]["Standard"] = 2
    n = baugruppen_aufnahme()
    n["komponenten"]["Deckel-1"]["status"]["Standard"] = 4
    assert vergleich(spec_aus(), n, vorher=v)["bestimmtheit"]["ok"] is False


def test_bestimmtheit_unterbestimmt_aus_dem_bestand_bleibt_erlaubt():
    v = baugruppen_aufnahme()
    v["komponenten"]["Deckel-1"]["status"]["Standard"] = 2
    assert vergleich(spec_aus(), copy.deepcopy(v), vorher=v)["bestimmtheit"]["ok"] is True


def test_bestimmtheit_nicht_lesbar_und_unterdrueckt():
    n = baugruppen_aufnahme()
    n["komponenten"]["Deckel-1"]["status"]["Standard"] = None
    assert vergleich(spec_aus(), n)["bestimmtheit"]["ok"] is None
    v = baugruppen_aufnahme()
    v["komponenten"]["Deckel-1"]["unterdrueckt"]["Standard"] = True
    v["komponenten"]["Deckel-1"]["status"]["Standard"] = None
    n = copy.deepcopy(v)
    assert vergleich(spec_aus(), n, vorher=v)["bestimmtheit"]["ok"] is True


def test_bestimmtheit_partner_einer_geloeschten_verknuepfung_darf_sinken():
    n = baugruppen_aufnahme()
    del n["verknuepfungen"]["Winkel1"]
    n["komponenten"]["Platte-1"]["status"]["Standard"] = 2
    assert vergleich(spec_aus(), n)["bestimmtheit"]["ok"] is False
    s = spec_aus(punkt("verknuepfung_loeschen", "d1", verknuepfung="Winkel1"))
    assert vergleich(s, n)["bestimmtheit"]["ok"] is True
    n["komponenten"]["Deckel-1"]["status"]["Standard"] = 2  # Deckel-1 hängt nicht an Winkel1
    assert vergleich(s, n)["bestimmtheit"]["ok"] is False


def test_neue_komponente_muss_voll_bestimmt_sein():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT")
    n["komponenten"]["Neu-1"]["status"]["Standard"] = 2
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}))
    e = vergleich(s, n, {"k1": ["Neu-1"]})
    assert e["bestimmtheit"]["ok"] is False and "Neu-1" in hinweise(e["bestimmtheit"])
    assert e["punkt:k1"]["ok"] is False


def test_neue_komponente_als_grenze_partner_darf_unterbestimmt_sein():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT")
    n["komponenten"]["Neu-1"]["status"]["Standard"] = 2
    n["verknuepfungen"]["Grenze_Abstand2"] = verknuepfung(5, ["Neu-1", "Gehaeuse-1"], wert=1.0, min_=0.0, max_=4.0, grenze=True)
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}),
                 punkt("verknuepfung_neu", "v1", art="grenze_abstand", min=0, max=4, a={"komponente": "k1", "feature": "F"},
                       b={"komponente": "Gehaeuse-1", "feature": "F"}))
    e = vergleich(s, n, {"k1": ["Neu-1"]})
    assert all(x["ok"] is True for x in e.values()), e
    n["komponenten"]["Neu-1"]["status"]["Standard"] = 4  # überbestimmt ist nie erlaubt
    assert vergleich(s, n, {"k1": ["Neu-1"]})["punkt:k1"]["ok"] is False


def test_neue_komponente_nicht_lesbarer_status_ist_unbewiesen():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT")
    n["komponenten"]["Neu-1"]["status"]["Standard"] = None
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}))
    e = vergleich(s, n, {"k1": ["Neu-1"]})
    assert e["bestimmtheit"]["ok"] is None and e["punkt:k1"]["ok"] is None


def test_neue_komponente_unterdrueckt_ist_mangel():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT")
    n["komponenten"]["Neu-1"]["unterdrueckt"]["Standard"] = True
    n["komponenten"]["Neu-1"]["transform"]["Standard"] = None
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}))
    assert vergleich(s, n, {"k1": ["Neu-1"]})["punkt:k1"]["ok"] is False


# ------------------------------------------------------------------------------------------------------------ Kollision

def test_alte_kollision_ist_kein_mangel_steht_aber_da():
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Platte-1", "Deckel-1"], "volumen": 1.5}])  # andere Reihenfolge
    e = vergleich(spec_aus(), n)
    assert e["kollision"]["ok"] is True
    assert e["kollision"]["bekannt"] == [{"paar": ["Deckel-1", "Platte-1"], "volumen": 1.5}]
    assert e["kollision"]["ist"] == []


def test_kollision_innerhalb_der_toleranz_ist_bekannt():
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 1.514}])  # unter 1 %
    assert vergleich(spec_aus(), n)["kollision"]["ok"] is True
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 1.6}])  # über 1 %
    assert vergleich(spec_aus(), n)["kollision"]["ok"] is False
    v = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 0.0}])
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 0.005}])  # unter 0,01 mm³
    assert vergleich(spec_aus(), n, vorher=v)["kollision"]["ok"] is True


def test_neue_kollision_ist_mangel():
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 1.5},
                                         {"paar": ["Schieber-1", "Gehaeuse-1"], "volumen": 0.8}])
    e = vergleich(spec_aus(), n)
    assert e["kollision"]["ok"] is False
    assert e["kollision"]["ist"][0]["paar"] == ["Gehaeuse-1", "Schieber-1"] and "Schieber-1" in hinweise(e["kollision"])


def test_kollision_weggefallen_ist_kein_mangel():
    assert vergleich(spec_aus(), baugruppen_aufnahme(kollisionen=[]))["kollision"]["ok"] is True


def test_kollision_erlaubt_nimmt_nur_das_paar():
    n = baugruppen_aufnahme()
    n["komponenten"]["Neu-1"] = komponente("Neu.SLDPRT")
    n["kollisionen"] += [{"paar": ["Neu-1", "Gehaeuse-1"], "volumen": 3.0}, {"paar": ["Neu-1", "Platte-1"], "volumen": 0.4}]
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}),
                 kollision_erlaubt=[{"paar": ["k1", "Gehaeuse-1"], "grund": "Schraube im Kernloch"}])
    e = vergleich(s, n, {"k1": ["Neu-1"]})
    assert e["kollision"]["ok"] is False
    assert [x["paar"] for x in e["kollision"]["ist"]] == [["Neu-1", "Platte-1"]]
    assert e["kollision"]["erlaubt"] == [{"paar": ["Gehaeuse-1", "Neu-1"], "volumen": 3.0}]
    s["kollision_erlaubt"].append({"paar": ["Platte-1", "k1"], "grund": "auch das"})
    assert vergleich(s, n, {"k1": ["Neu-1"]})["kollision"]["ok"] is True


def test_kollision_erlaubt_nimmt_nur_dieses_paar_aus_der_groessenpruefung():
    # ein erlaubtes Paar darf beliebig groß sein, ein anderes bekanntes Paar nicht
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 9.0}])
    s = spec_aus(kollision_erlaubt=[{"paar": ["Gehaeuse-1", "Schieber-1"], "grund": "x"}])
    assert vergleich(s, n)["kollision"]["ok"] is False
    s["kollision_erlaubt"] = [{"paar": ["Platte-1", "Deckel-1"], "grund": "x"}]
    assert vergleich(s, n)["kollision"]["ok"] is True


def test_kollision_nicht_gelesen_ist_unbewiesen():
    assert vergleich(spec_aus(), baugruppen_aufnahme(kollisionen=None))["kollision"]["ok"] is None
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": None}])
    assert vergleich(spec_aus(), n)["kollision"]["ok"] is None
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": None}, {"paar": ["A", "B"], "volumen": 1.0}])
    assert vergleich(spec_aus(), n)["kollision"]["ok"] is False


# ------------------------------------------------------------------------------------------------------------- Dateien

def _dateien(spec=None, **geaendert):
    return vergleiche_dateien(spec or SPEC, dateien_json(), lauf_shas(**geaendert), [NEUE_DATEI])


def test_dateien_nur_erwartete_geaendert():
    e = _dateien(**{HAUPT: "a" * 64, "teile/Platte.SLDPRT": "b" * 64, "teile/Deckel.SLDPRT": "c" * 64, NEUE_DATEI: "d" * 64})
    assert e["id"] == "dateien" and e["ok"] is True, e


def test_dateien_weitere_datei_geaendert_ist_mangel():
    e = _dateien(**{HAUPT: "a" * 64, "teile/Platte.SLDPRT": "b" * 64, "teile/Deckel.SLDPRT": "c" * 64, NEUE_DATEI: "d" * 64,
                    "teile/Schieber.SLDPRT": "e" * 64})
    assert e["ok"] is False and "teile/Schieber.SLDPRT" in hinweise(e)


def test_haupt_gleich_obwohl_punkt_verlangt():
    e = _dateien(**{"teile/Platte.SLDPRT": "b" * 64, "teile/Deckel.SLDPRT": "c" * 64, NEUE_DATEI: "d" * 64})
    assert e["ok"] is False and HAUPT in hinweise(e) and "gespeichert" in hinweise(e)


def test_teil_gleich_obwohl_punkt_verlangt():
    e = _dateien(**{HAUPT: "a" * 64, "teile/Deckel.SLDPRT": "c" * 64, NEUE_DATEI: "d" * 64})
    assert e["ok"] is False and "teile/Platte.SLDPRT" in hinweise(e)


def test_haupt_geaendert_ohne_baugruppen_punkt_ist_mangel():
    punkte = [{k: v for k, v in p.items() if k != "lage_folgen"} for p in SPEC["punkte"] if p.get("in_datei")]
    s = {**SPEC, "punkte": punkte}
    e = vergleiche_dateien(s, dateien_json(), lauf_shas(**{HAUPT: "a" * 64, "teile/Platte.SLDPRT": "b" * 64,
                                                           "teile/Deckel.SLDPRT": "c" * 64}), [])
    assert e["ok"] is False and HAUPT in hinweise(e)


def test_haupt_bei_lage_folgen_wird_immer_gespeichert():  # Korrektur I2
    s = {**SPEC, "punkte": [p for p in SPEC["punkte"] if p.get("in_datei")]}
    teile = {"teile/Platte.SLDPRT": "b" * 64, "teile/Deckel.SLDPRT": "c" * 64}
    e = vergleiche_dateien(s, dateien_json(), lauf_shas(**teile), [])
    assert e["ok"] is False and HAUPT in hinweise(e) and "gespeichert" in hinweise(e)
    assert vergleiche_dateien(s, dateien_json(), lauf_shas(**teile, **{HAUPT: "a" * 64}), [])["ok"] is True


def test_datei_fehlt_im_lauf():
    ist = lauf_shas(**{HAUPT: "a" * 64, "teile/Platte.SLDPRT": "b" * 64, "teile/Deckel.SLDPRT": "c" * 64, NEUE_DATEI: "d" * 64})
    del ist["teile/Schieber.SLDPRT"]
    e = vergleiche_dateien(SPEC, dateien_json(), ist, [NEUE_DATEI])
    assert e["ok"] is False and "teile/Schieber.SLDPRT" in hinweise(e)


def test_neue_datei_ohne_punkt():
    ist = lauf_shas(**{HAUPT: "a" * 64, "teile/Platte.SLDPRT": "b" * 64, "teile/Deckel.SLDPRT": "c" * 64, "Fremd.SLDPRT": "d" * 64})
    e = vergleiche_dateien(SPEC, dateien_json(), ist, [])
    assert e["ok"] is False and "Fremd.SLDPRT" in hinweise(e)


def test_neue_datei_fehlt_im_lauf():
    ist = lauf_shas(**{HAUPT: "a" * 64, "teile/Platte.SLDPRT": "b" * 64, "teile/Deckel.SLDPRT": "c" * 64})
    e = vergleiche_dateien(SPEC, dateien_json(), ist, [NEUE_DATEI])
    assert e["ok"] is False and NEUE_DATEI in hinweise(e)


def test_dateien_schreibweise_egal():
    ist = {rel.upper(): sha for rel, sha in lauf_shas(**{HAUPT: "a" * 64, "teile/Platte.SLDPRT": "b" * 64,
                                                       "teile/Deckel.SLDPRT": "c" * 64, NEUE_DATEI: "d" * 64}).items()}
    assert vergleiche_dateien(SPEC, dateien_json(), ist, [NEUE_DATEI.lower()])["ok"] is True


def test_dateien_sha_nicht_gelesen_ist_unbewiesen():
    e = _dateien(**{HAUPT: "a" * 64, "teile/Platte.SLDPRT": "b" * 64, "teile/Deckel.SLDPRT": "c" * 64, NEUE_DATEI: "d" * 64,
                    "teile/Schieber.SLDPRT": None})
    assert e["ok"] is None
    e = _dateien(**{"teile/Schieber.SLDPRT": None})  # ein Mangel hat Vorrang
    assert e["ok"] is False


def test_dateien_ohne_punkte_an_teilen_nur_haupt():
    s = spec_aus(punkt("eigenschaft", "s1", name="R", neu="B"))
    ist = lauf_shas(**{HAUPT: "a" * 64})
    assert vergleiche_dateien(s, dateien_json(), ist, [])["ok"] is True
    assert vergleiche_dateien(s, dateien_json(), lauf_shas(), [])["ok"] is False


def test_dateien_punkt_auf_unbekannte_datei_ist_mangel():
    s = spec_aus(punkt("unterdruecken", "u1", in_datei="teile/Gibts.SLDPRT", feature="F"))
    e = vergleiche_dateien(s, dateien_json(), lauf_shas(), [])
    assert e["ok"] is False and "Gibts" in hinweise(e)
