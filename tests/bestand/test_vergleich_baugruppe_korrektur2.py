"""Korrekturrunde 2 zum Vergleich der Baugruppe (Task 5): konfigurationsabhängige Werte, Namen im Protokoll, leere Konfigurationen,
Altnamen in Ankern, `None` als Partner."""

import copy

from tests.bestand.beispiel_baugruppe import baugruppen_aufnahme, komponente, verknuepfung
from tests.bestand.test_vergleich_baugruppe import (_ersetzt_stand, hinweise, punkt, setze_wert, spec_aus, verschiebe, vergleich,
                                                    zwei_konfigurationen)
from tests.bestand.test_vergleich_baugruppe_korrektur import _neue_komp, _spec_ersetzen, _spec_neue_komp


# ---- 1: verknuepfung_wert hat `konfigurationen` (Vorgabe alle)

def _bestand_10_20():
    """Abstand1: Standard 10 mm, Variante B 20 mm."""
    v = zwei_konfigurationen(baugruppen_aufnahme())
    setze_wert(v, "Abstand1", "wert", 20.0, "Variante B")
    return v


def _spec_w(**felder) -> dict:
    return spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu=12, **felder))


def test_k2_1_alle_konfigurationen_auf_12_ueberschreibt_den_wert_des_kollegen():
    v = _bestand_10_20()
    n = copy.deepcopy(v)
    setze_wert(n, "Abstand1", "wert", 12.0)  # der Bau hat alle auf 12 gesetzt
    e = vergleich(_spec_w(konfigurationen=["Standard"]), n, vorher=v)
    assert e["punkt:w1"]["ok"] is False and "Variante B" in hinweise(e["punkt:w1"])
    assert e["verknuepfungen"]["ok"] is False and "Variante B" in hinweise(e["verknuepfungen"])


def test_k2_1_genannte_konfiguration_neu_die_uebrigen_unveraendert():
    v = _bestand_10_20()
    n = copy.deepcopy(v)
    setze_wert(n, "Abstand1", "wert", 12.0, "Standard")
    e = vergleich(_spec_w(konfigurationen=["Standard"]), n, vorher=v)
    assert e["punkt:w1"]["ok"] is True and e["verknuepfungen"]["ok"] is True, e


def test_k2_1_genannte_konfiguration_nicht_gesetzt_ist_mangel():
    v = _bestand_10_20()
    e = vergleich(_spec_w(konfigurationen=["Standard"]), copy.deepcopy(v), vorher=v)
    assert e["punkt:w1"]["ok"] is False and "Standard" in hinweise(e["punkt:w1"])


def test_k2_1_vorgabe_alle_gilt_in_jeder_konfiguration():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    setze_wert(n, "Abstand1", "wert", 12.0)
    assert vergleich(_spec_w(), n, vorher=v)["punkt:w1"]["ok"] is True
    assert vergleich(_spec_w(konfigurationen="alle"), n, vorher=v)["punkt:w1"]["ok"] is True
    setze_wert(n, "Abstand1", "wert", 10.0, "Variante B")
    assert vergleich(_spec_w(), n, vorher=v)["punkt:w1"]["ok"] is False


def test_k2_1_grenze_je_konfiguration():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    setze_wert(v, "Grenze_Abstand1", "max", 9.0, "Variante B")
    n = copy.deepcopy(v)
    setze_wert(n, "Grenze_Abstand1", "max", 8.0, "Standard")
    s = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Grenze_Abstand1", grenze="max", alt=5, neu=8,
                       konfigurationen=["Standard"]))
    assert vergleich(s, n, vorher=v)["punkt:w1"]["ok"] is True
    setze_wert(n, "Grenze_Abstand1", "max", 8.0, "Variante B")
    e = vergleich(s, n, vorher=v)
    assert e["punkt:w1"]["ok"] is False and e["verknuepfungen"]["ok"] is False


def test_k2_1_nicht_gelesener_wert_in_den_uebrigen_konfigurationen_ist_unbewiesen():
    v = _bestand_10_20()
    n = copy.deepcopy(v)
    setze_wert(n, "Abstand1", "wert", 12.0, "Standard")
    del n["verknuepfungen"]["Abstand1"]["werte"]["Variante B"]
    assert vergleich(_spec_w(konfigurationen=["Standard"]), n, vorher=v)["punkt:w1"]["ok"] is None


# ---- 2: Namen im Protokoll sind eindeutig

def test_k2_2_name_zugleich_neu_und_ersatz_macht_keine_lage_unsichtbar():
    n = baugruppen_aufnahme()
    n["komponenten"]["N-1"] = n["komponenten"].pop("Platte-1")
    n["komponenten"]["N-1"]["datei"] = "Neu.SLDPRT"
    n["verknuepfungen"]["Winkel1"]["partner"] = ["N-1", "Gehaeuse-1"]
    verschiebe(n, "N-1", 50)
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}),
                 punkt("komponente_ersetzen", "e1", komponente="Platte-1", quelle={"teil": "n.yaml"}))
    e = vergleich(s, n, neue={"k1": ["N-1"]}, ersetzt={"Platte-1": "N-1"})
    assert e["komponenten"]["ok"] is False and "N-1" in hinweise(e["komponenten"])
    assert e["punkt:k1"]["ok"] is False and e["punkt:e1"]["ok"] is False  # keiner der beiden Punkte gilt als erfüllt
    assert e["komponenten"]["fremd"] == ["N-1"]  # N-1 ist unerklärt, ihre Lage gibt nichts frei


def test_k2_2_zwei_komponente_neu_mit_demselben_namen():
    n = baugruppen_aufnahme()
    _neue_komp(n)
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}), punkt("komponente_neu", "k2", quelle={"teil": "y.yaml"}))
    e = vergleich(s, n, neue={"k1": ["Neu-1"], "k2": ["Neu-1"]})
    assert e["komponenten"]["ok"] is False and "Neu-1" in hinweise(e["komponenten"])
    assert e["punkt:k1"]["ok"] is False and e["punkt:k2"]["ok"] is False


def test_k2_2_zwei_ersetzte_auf_einen_neuen_namen():
    n, ersetzt = _ersetzt_stand()
    ersetzt = {"Schraube-1": "Neu-1", "Schraube-2": "Neu-1"}
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}),
                 punkt("komponente_ersetzen", "e2", komponente="Schraube-2", quelle={"teil": "n.yaml"}))
    e = vergleich(s, n, ersetzt=ersetzt)
    assert e["komponenten"]["ok"] is False and "Neu-1" in hinweise(e["komponenten"])
    assert e["punkt:e1"]["ok"] is False or e["punkt:e2"]["ok"] is False


def test_k2_2_eindeutige_namen_bleiben_in_ordnung():
    n, ersetzt = _ersetzt_stand()
    _neue_komp(n, "Neu-9")
    s = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}),
                 punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}))
    e = vergleich(s, n, neue={"k1": ["Neu-9"], "e1": ["Neu-1"]}, ersetzt=ersetzt)
    assert e["komponenten"]["ok"] is True and e["punkt:k1"]["ok"] is True and e["punkt:e1"]["ok"] is True, e


# ---- 3: leere Konfigurationen

def test_k2_3_ohne_gemeinsame_konfiguration_sind_die_punkte_unbewiesen():
    v = baugruppen_aufnahme()
    n = baugruppen_aufnahme(konfigurationen=[], aktiv=None)
    n["verknuepfungen"]["Abstand1"]["wert"] = 999.0
    setze_wert(n, "Abstand1", "wert", 999.0)
    e = vergleich(_spec_w(), n, vorher=v)
    assert e["punkt:w1"]["ok"] is None
    n = baugruppen_aufnahme(konfigurationen=["Andere"], aktiv="Andere")
    assert vergleich(_spec_w(), n, vorher=v)["punkt:w1"]["ok"] is None


def test_k2_3_ohne_gemeinsame_konfiguration_neue_komponente_ist_unbewiesen():
    n = baugruppen_aufnahme(konfigurationen=["Andere"], aktiv="Andere")
    _neue_komp(n)
    assert vergleich(_spec_neue_komp(), n, {"k1": ["Neu-1"]})["punkt:k1"]["ok"] is not True


# ---- 4: Altnamen ersetzter Komponenten in Ankern und kollision_erlaubt

def test_k2_4_anker_mit_dem_alten_namen_einer_ersetzten_komponente():
    n, ersetzt = _ersetzt_stand()
    n["verknuepfungen"]["Parallel9"] = verknuepfung(3, ["Neu-1", "Deckel-1"])
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}),
                 punkt("verknuepfung_neu", "v1", art="parallel", a={"komponente": "Schraube-1", "feature": "F"},
                       b={"komponente": "Deckel-1", "feature": "F"}))
    e = vergleich(s, n, ersetzt=ersetzt)
    assert e["punkt:v1"]["ok"] is True and e["verknuepfungen"]["ok"] is True, e


def test_k2_4_kollision_erlaubt_mit_dem_alten_namen():
    n, ersetzt = _ersetzt_stand()
    n["kollisionen"] = [*n["kollisionen"], {"paar": ["Neu-1", "Schieber-1"], "volumen": 2.0}]
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}),
                 kollision_erlaubt=[{"paar": ["Schraube-1", "Schieber-1"], "grund": "x"}])
    e = vergleich(s, n, ersetzt=ersetzt)
    assert e["kollision"]["ok"] is True and e["kollision"]["erlaubt"] == [{"paar": ["Neu-1", "Schieber-1"], "volumen": 2.0}]
    s["kollision_erlaubt"] = []
    assert vergleich(s, n, ersetzt=ersetzt)["kollision"]["ok"] is False


# ---- 5: `None` als Partner (Verknüpfung an eine Ebene der Hauptbaugruppe)

def test_k2_5_none_als_partner_stuerzt_nicht_ab_und_ist_lesbar():
    v = baugruppen_aufnahme()
    v["verknuepfungen"]["Ebene1"] = verknuepfung(0, ["Deckel-1", None])
    e = vergleich(spec_aus(), copy.deepcopy(v), vorher=v)
    assert all(x["ok"] is True for x in e.values()), e


def test_k2_5_partner_wechselt_von_none_auf_komponente_ist_mangel():
    v = baugruppen_aufnahme()
    v["verknuepfungen"]["Ebene1"] = verknuepfung(0, ["Deckel-1", None])
    n = copy.deepcopy(v)
    n["verknuepfungen"]["Ebene1"]["partner"] = ["Deckel-1", "Platte-1"]
    assert vergleich(spec_aus(), n, vorher=v)["verknuepfungen"]["ok"] is False


def test_k2_5_none_als_partner_neben_ersetzter_komponente():
    n, ersetzt = _ersetzt_stand()
    v = baugruppen_aufnahme()
    v["verknuepfungen"]["Ebene1"] = verknuepfung(0, ["Schraube-1", None])
    n["verknuepfungen"]["Ebene1"] = verknuepfung(0, ["Neu-1", None])
    s = spec_aus(punkt("komponente_ersetzen", "e1", komponente="Schraube-1", quelle={"teil": "n.yaml"}))
    e = vergleich(s, n, ersetzt=ersetzt, vorher=v)
    assert e["verknuepfungen"]["ok"] is True and e["punkt:e1"]["ok"] is True, e


def test_k2_5_bestimmtheit_mit_loeschung_an_none_partner():
    v = baugruppen_aufnahme()
    v["verknuepfungen"]["Ebene1"] = verknuepfung(0, ["Deckel-1", None])
    n = copy.deepcopy(v)
    del n["verknuepfungen"]["Ebene1"]
    n["komponenten"]["Deckel-1"]["status"]["Standard"] = 2
    s = spec_aus(punkt("verknuepfung_loeschen", "d1", verknuepfung="Ebene1"))
    e = vergleich(s, n, vorher=v)
    assert e["bestimmtheit"]["ok"] is True and e["verknuepfungen"]["ok"] is True and e["punkt:d1"]["ok"] is True
