"""Korrekturrunde 1 zum Vergleich der Baugruppe (Task 5): je Befund I1 bis I11 mindestens ein Test.

Grundsatz: unlesbar ist nie gleich und nie bestanden; was der Bau nicht belegt, gibt nichts frei."""

import copy

from swki.bestand.vergleich_baugruppe import vergleiche_dateien
from tests.bestand.beispiel_baugruppe import HAUPT, SPEC, baugruppen_aufnahme, dateien_json, komponente, lauf_shas, verknuepfung
from tests.bestand.test_vergleich_baugruppe import (_ersetzt_stand, hinweise, punkt, setze_konfig, setze_wert, spec_aus, verschiebe,
                                                    vergleich, zwei_konfigurationen)


def _neue_komp(n: dict, name: str = "Neu-1", datei: str = "Neu.SLDPRT", **felder) -> None:
    n["komponenten"][name] = komponente(datei, **felder)


def _spec_neue_komp(**felder) -> dict:
    return spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}, **felder))


def _spec_ersetzen(komponente_="Platte-1", **felder) -> dict:
    return spec_aus(punkt("komponente_ersetzen", "e1", komponente=komponente_, quelle={"teil": "n.yaml"}, **felder))


# ---- I1: Konfigurationen und aktive Konfiguration

def test_i1_konfiguration_fehlt_nachher_ist_mangel():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    n["konfigurationen"] = ["Standard"]
    verschiebe(n, "Deckel-1", 50, "Variante B")
    e = vergleich(spec_aus(), n, vorher=v)
    assert e["komponenten"]["ok"] is False and "Variante B" in hinweise(e["komponenten"])
    assert e["lage"]["ok"] is None  # Variante B wurde nicht verglichen


def test_i1_konfiguration_dazugekommen_ist_mangel():
    e = vergleich(spec_aus(), zwei_konfigurationen(baugruppen_aufnahme()))
    assert e["komponenten"]["ok"] is False and "Variante B" in hinweise(e["komponenten"])
    assert e["lage"]["ok"] is None


def test_i1_aktive_konfiguration_gewechselt_ist_mangel():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    n["aktiv"] = "Variante B"
    e = vergleich(spec_aus(), n, vorher=v)
    assert e["komponenten"]["ok"] is False and "aktiv" in hinweise(e["komponenten"])


def test_i1_aktive_konfiguration_nicht_gelesen_ist_unbewiesen():
    assert vergleich(spec_aus(), baugruppen_aufnahme(aktiv=None))["komponenten"]["ok"] is None


# ---- I3: Kinder einer Unterbaugruppe aus lage_folgen wandern nicht relativ

def _spec_lage_unter(*lage_folgen) -> dict:
    return spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu=12, lage_folgen=list(lage_folgen)))


def test_i3_kind_wandert_relativ_zur_erlaubten_unterbaugruppe():
    n = baugruppen_aufnahme()
    verschiebe(n, "Unter-1", 5)
    verschiebe(n, "Unter-1/Welle-1", 50)
    e = vergleich(_spec_lage_unter("Unter-1"), n)
    assert e["lage"]["ok"] is False
    assert [x["komponente"] for x in e["lage"]["ist"]] == ["Unter-1/Welle-1"]
    n = baugruppen_aufnahme()
    verschiebe(n, "Unter-1", 5)
    verschiebe(n, "Unter-1/Welle-1", 5)
    assert vergleich(_spec_lage_unter("Unter-1"), n)["lage"]["ok"] is True


_DREHUNG_90_Z = [0, 1, 0, -1, 0, 0, 0, 0, 1]  # Zeilenvektor-Konvention wie Transform2.ArrayData


def test_i3_kind_folgt_der_gedrehten_unterbaugruppe():
    v = baugruppen_aufnahme()
    v["komponenten"]["Unter-1/Welle-1"]["transform"]["Standard"][9] = 0.1  # 100 mm neben Unter-1
    n = copy.deepcopy(v)
    for name, ort in (("Unter-1", (0, 0, 0)), ("Unter-1/Welle-1", (0, 0.1, 0))):  # starre Drehung um 90 Grad um z
        t = n["komponenten"][name]["transform"]["Standard"]
        t[0:9], t[9:12] = _DREHUNG_90_Z, ort
    assert vergleich(_spec_lage_unter("Unter-1"), n, vorher=v)["lage"]["ok"] is True
    n["komponenten"]["Unter-1/Welle-1"]["transform"]["Standard"][9] += 0.05
    assert vergleich(_spec_lage_unter("Unter-1"), n, vorher=v)["lage"]["ok"] is False


def test_i3_kind_in_lage_folgen_darf_selbst_wandern():
    n = baugruppen_aufnahme()
    verschiebe(n, "Unter-1", 5)
    verschiebe(n, "Unter-1/Welle-1", 50)
    assert vergleich(_spec_lage_unter("Unter-1", "Unter-1/Welle-1"), n)["lage"]["ok"] is True


def test_i3_ahne_nicht_gelesen_ist_unbewiesen():
    n = baugruppen_aufnahme()
    verschiebe(n, "Unter-1/Welle-1", 5)
    n["komponenten"]["Unter-1"]["transform"]["Standard"] = None
    assert vergleich(_spec_lage_unter("Unter-1"), n)["lage"]["ok"] is None


def _ersetzte_unterbaugruppe():
    n = baugruppen_aufnahme()
    n["komponenten"]["Unter-2"] = n["komponenten"].pop("Unter-1")
    n["komponenten"]["Unter-2"]["datei"] = "Neu.SLDASM"
    n["komponenten"]["Unter-2/Welle-1"] = n["komponenten"].pop("Unter-1/Welle-1")
    n["verknuepfungen"]["Konzentrisch5"]["partner"] = ["Unter-2/Welle-1", "Gehaeuse-1"]
    return n, {"Unter-1": "Unter-2"}


def test_i3_kinder_einer_ersetzten_unterbaugruppe_wandern_nicht_relativ():
    n, ersetzt = _ersetzte_unterbaugruppe()
    s = _spec_ersetzen("Unter-1")
    e = vergleich(s, n, ersetzt=ersetzt)
    assert e["lage"]["ok"] is True and e["verknuepfungen"]["ok"] is True, e
    verschiebe(n, "Unter-2/Welle-1", 50)
    e = vergleich(s, n, ersetzt=ersetzt)
    assert e["lage"]["ok"] is False and "Unter-2/Welle-1" in hinweise(e["lage"])


# ---- I4: Protokoll gegen die Punkte

def test_i4_neue_mit_unbekannter_punkt_id_gibt_keine_lage_frei():
    n = baugruppen_aufnahme()
    verschiebe(n, "Deckel-1", 50)
    e = vergleich(spec_aus(), n, neue={"xx": ["Deckel-1"]})
    assert e["lage"]["ok"] is False
    assert e["komponenten"]["ok"] is False and "xx" in hinweise(e["komponenten"])


def test_i4_neue_komponente_mit_bestandsnamen_gibt_keine_lage_frei():
    n = baugruppen_aufnahme()
    verschiebe(n, "Deckel-1", 50)
    e = vergleich(_spec_neue_komp(), n, neue={"k1": ["Deckel-1"]})
    assert e["lage"]["ok"] is False and e["punkt:k1"]["ok"] is False


def test_i4_komponente_neu_hat_genau_einen_namen():
    n = baugruppen_aufnahme()
    _neue_komp(n, "Neu-1")
    _neue_komp(n, "Neu-2")
    e = vergleich(_spec_neue_komp(), n, neue={"k1": ["Neu-1", "Neu-2"]})
    assert e["punkt:k1"]["ok"] is False and e["komponenten"]["ok"] is False


def test_i4_neue_fuer_punkt_ohne_neue_komponente_ist_mangel():
    n = baugruppen_aufnahme()
    _neue_komp(n)
    del n["verknuepfungen"]["Abstand2"]
    s = spec_aus(punkt("verknuepfung_loeschen", "d1", verknuepfung="Abstand2"))
    assert vergleich(s, n, neue={"d1": ["Neu-1"]})["komponenten"]["ok"] is False


def test_i4_ersetzt_nur_fuer_ziele_der_punkte():
    n, ersetzt = _ersetzt_stand()
    e = vergleich(spec_aus(), n, ersetzt=ersetzt)  # kein Punkt ersetzt Schraube-1
    assert e["komponenten"]["ok"] is False and "Schraube-1" in hinweise(e["komponenten"])
    e = vergleich(_spec_ersetzen("Platte-1"), n, ersetzt=ersetzt)  # der Punkt nennt eine andere Komponente
    assert e["komponenten"]["ok"] is False and e["punkt:e1"]["ok"] is False


def test_i4_ersetzende_komponente_gibt_es_schon_im_bestand():
    n = baugruppen_aufnahme()
    n["komponenten"].pop("Platte-1")
    n["verknuepfungen"]["Winkel1"]["partner"] = ["Deckel-1", "Gehaeuse-1"]
    verschiebe(n, "Deckel-1", 50)
    e = vergleich(_spec_ersetzen("Platte-1"), n, ersetzt={"Platte-1": "Deckel-1"})
    assert e["komponenten"]["ok"] is False and e["lage"]["ok"] is False


def test_i4_neue_dateien_nur_mit_einem_punkt_der_eine_datei_bringt():
    ist = lauf_shas(**{HAUPT: "a" * 64, "X.SLDPRT": "d" * 64})
    nur_eigenschaft = spec_aus(punkt("eigenschaft", "s1", name="R", neu="B"))
    e = vergleiche_dateien(nur_eigenschaft, dateien_json(), ist, ["X.SLDPRT"])
    assert e["ok"] is False and "X.SLDPRT" in hinweise(e)
    wie = spec_aus(punkt("komponente_neu", "k1", wie="Schraube-1"))
    assert vergleiche_dateien(wie, dateien_json(), ist, ["X.SLDPRT"])["ok"] is False  # `wie` bringt keine Datei
    quelle = spec_aus(punkt("komponente_neu", "k1", quelle={"teil": "x.yaml"}))
    assert vergleiche_dateien(quelle, dateien_json(), ist, ["X.SLDPRT"])["ok"] is True


# ---- I5: Verknüpfungsfelder nicht gelesen

def test_i5_verknuepfungsfeld_none_oder_fehlend_ist_unbewiesen():
    for feld in ("typ", "ausrichtung", "grenze", "gesteuert", "partner"):
        for wie in ("none", "fehlt"):
            v = baugruppen_aufnahme()
            for m in v["verknuepfungen"].values():
                if wie == "none":
                    m[feld] = None
                else:
                    m.pop(feld)
            e = vergleich(spec_aus(), copy.deepcopy(v), vorher=v)
            assert e["verknuepfungen"]["ok"] is None, (feld, wie)


def test_i5_feld_nur_nachher_nicht_gelesen_ist_unbewiesen_und_ein_mangel_hat_vorrang():
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Winkel1"]["typ"] = None
    assert vergleich(spec_aus(), n)["verknuepfungen"]["ok"] is None
    n["verknuepfungen"]["Winkel1"]["ausrichtung"] = 1
    assert vergleich(spec_aus(), n)["verknuepfungen"]["ok"] is False


# ---- I6: None-Lücken in den Punkten

def test_i6_wie_mit_nicht_gelesener_datei_ist_unbewiesen():
    v = baugruppen_aufnahme()
    v["komponenten"]["Schraube-1"]["datei"] = None
    n = copy.deepcopy(v)
    n["komponenten"]["Schraube-12"] = komponente("irgendwas.SLDPRT")
    n["komponenten"]["Schraube-12"]["datei"] = None
    e = vergleich(spec_aus(punkt("komponente_neu", "k1", wie="Schraube-1")), n, {"k1": ["Schraube-12"]}, vorher=v)
    assert e["punkt:k1"]["ok"] is None


def test_i6_quelle_neue_komponente_braucht_eine_neue_datei():
    n = baugruppen_aufnahme()
    _neue_komp(n)
    s = _spec_neue_komp()
    assert vergleich(s, n, {"k1": ["Neu-1"]}, neue_dateien=["Neu.SLDPRT"])["punkt:k1"]["ok"] is True
    e = vergleich(s, n, {"k1": ["Neu-1"]}, neue_dateien=[])  # die Datei steht nicht unter den neuen
    assert e["punkt:k1"]["ok"] is False and "Neu.SLDPRT" in hinweise(e["punkt:k1"])
    n["komponenten"]["Neu-1"]["datei"] = "teile/Deckel.SLDPRT"  # eine Datei des Bestands ist keine neue
    assert vergleich(s, n, {"k1": ["Neu-1"]}, neue_dateien=["Neu.SLDPRT"])["punkt:k1"]["ok"] is False
    n["komponenten"]["Neu-1"]["datei"] = None
    assert vergleich(s, n, {"k1": ["Neu-1"]}, neue_dateien=["Neu.SLDPRT"])["punkt:k1"]["ok"] is None


def test_i6_ersetzende_komponente_mit_nicht_gelesener_datei_ist_unbewiesen():
    n, ersetzt = _ersetzt_stand()
    n["komponenten"]["Neu-1"]["datei"] = None
    assert vergleich(_spec_ersetzen("Schraube-1"), n, ersetzt=ersetzt)["punkt:e1"]["ok"] is None
    n, ersetzt = _ersetzt_stand()
    e = vergleich(_spec_ersetzen("Schraube-1"), n, ersetzt=ersetzt, neue_dateien=[])  # Datei nicht unter den neuen
    assert e["punkt:e1"]["ok"] is False


def test_i6_ersetzen_mit_nicht_gelesener_alter_datei_ist_unbewiesen():
    v = baugruppen_aufnahme()
    v["komponenten"]["Platte-1"]["datei"] = None
    n = copy.deepcopy(v)
    n["komponenten"]["Neu-1"] = n["komponenten"].pop("Platte-1")
    n["komponenten"]["Neu-1"]["datei"] = "Neu.SLDPRT"
    n["verknuepfungen"]["Winkel1"]["partner"] = ["Neu-1", "Gehaeuse-1"]
    e = vergleich(_spec_ersetzen("Platte-1"), n, ersetzt={"Platte-1": "Neu-1"}, vorher=v)
    assert e["punkt:e1"]["ok"] is None


def test_i6_alle_instanzen_mit_nicht_gelesener_datei_ist_unbewiesen():
    v = baugruppen_aufnahme()
    v["komponenten"]["Schraube-1"]["datei"] = None  # ob sie eine Instanz ist, ist nicht zu sagen
    n, ersetzt = _ersetzt_stand(alle=True)
    e = vergleich(_spec_ersetzen("Schraube-2", alle_instanzen=True), n, ersetzt=ersetzt, vorher=v)
    assert e["punkt:e1"]["ok"] is None


def test_i6_unterdrueckt_nicht_gelesen_ist_unbewiesen():
    n = baugruppen_aufnahme()
    _neue_komp(n)
    n["komponenten"]["Neu-1"]["unterdrueckt"]["Standard"] = None
    assert vergleich(_spec_neue_komp(), n, {"k1": ["Neu-1"]})["punkt:k1"]["ok"] is None
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["K9"] = verknuepfung(1, ["Deckel-1", "Platte-1"])
    n["verknuepfungen"]["K9"]["unterdrueckt"]["Standard"] = None
    s = spec_aus(punkt("verknuepfung_neu", "v1", art="konzentrisch", a={"komponente": "Platte-1", "feature": "F"},
                       b={"komponente": "Deckel-1", "feature": "F"}))
    assert vergleich(s, n)["punkt:v1"]["ok"] is None


def test_i6_neue_komponente_ohne_fixiert_im_punkt_darf_nicht_fixiert_sein():
    n = baugruppen_aufnahme()
    _neue_komp(n, fixiert=True)
    e = vergleich(_spec_neue_komp(), n, {"k1": ["Neu-1"]})
    assert e["punkt:k1"]["ok"] is False and "fixiert" in hinweise(e["punkt:k1"])
    n["komponenten"]["Neu-1"]["fixiert"]["Standard"] = False
    assert vergleich(_spec_neue_komp(), n, {"k1": ["Neu-1"]})["punkt:k1"]["ok"] is True


# ---- I7: Ausrichtung einer neuen Verknüpfung

def _spec_deckungsgleich(**felder) -> dict:
    return spec_aus(punkt("verknuepfung_neu", "v1", art="deckungsgleich", a={"komponente": "Platte-1", "feature": "F"},
                          b={"komponente": "Deckel-1", "feature": "F"}, **felder))


def test_i7_ausrichtung_der_neuen_verknuepfung():
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["D9"] = verknuepfung(0, ["Deckel-1", "Platte-1"])
    n["verknuepfungen"]["D9"]["ausrichtung"] = 1  # entgegengesetzt
    assert vergleich(_spec_deckungsgleich(ausrichtung="gleich"), n)["punkt:v1"]["ok"] is False
    assert vergleich(_spec_deckungsgleich(ausrichtung="entgegengesetzt"), n)["punkt:v1"]["ok"] is True
    assert vergleich(_spec_deckungsgleich(), n)["punkt:v1"]["ok"] is True  # ohne Angabe keine Prüfung
    n["verknuepfungen"]["D9"]["ausrichtung"] = None
    assert vergleich(_spec_deckungsgleich(ausrichtung="gleich"), n)["punkt:v1"]["ok"] is None


def test_i7_scharnier_anlage_ist_vorgabe_entgegengesetzt():
    s = spec_aus(punkt("verknuepfung_neu", "v1", art="scharnier", a={"komponente": "Platte-1", "feature": "F"},
                       b={"komponente": "Deckel-1", "feature": "F"}, anlage_a={"komponente": "Platte-1", "feature": "G"},
                       anlage_b={"komponente": "Deckel-1", "feature": "G"}))
    n = baugruppen_aufnahme()
    n["verknuepfungen"]["Konzentrisch9"] = verknuepfung(1, ["Platte-1", "Deckel-1"])
    n["verknuepfungen"]["Deckungsgleich9"] = verknuepfung(0, ["Platte-1", "Deckel-1"])
    n["verknuepfungen"]["Deckungsgleich9"]["ausrichtung"] = 1
    assert vergleich(s, n)["punkt:v1"]["ok"] is True
    n["verknuepfungen"]["Deckungsgleich9"]["ausrichtung"] = 0
    assert vergleich(s, n)["punkt:v1"]["ok"] is False
    s["punkte"][0]["ausrichtung"] = "gleich"  # gilt für die Anlage
    assert vergleich(s, n)["punkt:v1"]["ok"] is True


# ---- I8: Partner gelöschter Verknüpfungen

def test_i8_partner_einer_geloeschten_verknuepfung_darf_nur_bis_unterbestimmt_sinken():
    s = spec_aus(punkt("verknuepfung_loeschen", "d1", verknuepfung="Winkel1"))
    n = baugruppen_aufnahme()
    del n["verknuepfungen"]["Winkel1"]
    n["komponenten"]["Platte-1"]["status"]["Standard"] = 2  # unterbestimmt: erlaubt
    assert vergleich(s, n)["bestimmtheit"]["ok"] is True
    n["komponenten"]["Platte-1"]["status"]["Standard"] = 5  # keine Lösung: nie
    assert vergleich(s, n)["bestimmtheit"]["ok"] is False
    n["komponenten"]["Platte-1"]["status"]["Standard"] = 4  # überbestimmt: nie
    assert vergleich(s, n)["bestimmtheit"]["ok"] is False
    n["komponenten"]["Platte-1"]["status"]["Standard"] = None
    assert vergleich(s, n)["bestimmtheit"]["ok"] is None


# ---- I9: Kollision summiert je Paar

def test_i9_doppelter_eintrag_desselben_paars_zaehlt_als_summe():
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 1.5},
                                         {"paar": ["Platte-1", "Deckel-1"], "volumen": 1.5}])
    e = vergleich(spec_aus(), n)
    assert e["kollision"]["ok"] is False and "3" in hinweise(e["kollision"])
    v = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 1.0},
                                         {"paar": ["Platte-1", "Deckel-1"], "volumen": 0.5}])
    assert vergleich(spec_aus(), baugruppen_aufnahme(), vorher=v)["kollision"]["ok"] is True  # 1,5 gegen 1,5


def test_i9_bestand_mit_nicht_gelesenem_volumen_bleibt_unlesbar():
    v = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": None},
                                         {"paar": ["Deckel-1", "Platte-1"], "volumen": 1.0}])
    n = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 1.0}])
    assert vergleich(spec_aus(), n, vorher=v)["kollision"]["ok"] is None


def test_i9_weggefallene_paare_stehen_im_eintrag_ohne_den_ok_zu_aendern():
    v = baugruppen_aufnahme(kollisionen=[{"paar": ["Deckel-1", "Platte-1"], "volumen": 1.5},
                                         {"paar": ["Schieber-1", "Gehaeuse-1"], "volumen": 0.8}])
    e = vergleich(spec_aus(), baugruppen_aufnahme(), vorher=v)
    assert e["kollision"]["ok"] is True
    assert e["kollision"]["weggefallen"] == [{"paar": ["Gehaeuse-1", "Schieber-1"], "volumen": 0.8}]


def test_i9_kollision_nennt_die_konfiguration_und_warnt_bei_mehreren():
    e = vergleich(spec_aus(), baugruppen_aufnahme())
    assert e["kollision"]["konfiguration"] == "Standard" and "nicht geprüft" not in hinweise(e["kollision"])
    v = zwei_konfigurationen(baugruppen_aufnahme())
    e = vergleich(spec_aus(), copy.deepcopy(v), vorher=v)
    assert e["kollision"]["ok"] is True and e["kollision"]["konfiguration"] == "Standard"
    assert "Variante B" in hinweise(e["kollision"]) and "nicht geprüft" in hinweise(e["kollision"])


# ---- I10: SHA im Bestand nicht gelesen

def test_i10_bestand_sha_none_ist_unbewiesen():
    s = {**SPEC, "punkte": [punkt("unterdruecken", "u1", in_datei="teile/Platte.SLDPRT", feature="F")]}
    ist = lauf_shas(**{"teile/Platte.SLDPRT": "b" * 64})
    b = dateien_json()
    b["teile/Platte.SLDPRT"]["sha256"] = None
    assert vergleiche_dateien(s, b, ist, [])["ok"] is None  # verlangte Datei
    b["teile/Platte.SLDPRT"].pop("sha256")
    assert vergleiche_dateien(s, b, ist, [])["ok"] is None
    b = dateien_json()
    b["teile/Schieber.SLDPRT"]["sha256"] = None  # Datei ohne Punkt: nicht vergleichbar
    assert vergleiche_dateien(s, b, ist, [])["ok"] is None


# ---- I11: Werte je Konfiguration

def test_i11_verknuepfungswert_nur_in_variante_b_geaendert():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    setze_wert(n, "Abstand2", "wert", 4.0, "Variante B")  # die aktive Konfiguration bleibt gleich
    e = vergleich(spec_aus(), n, vorher=v)
    assert e["verknuepfungen"]["ok"] is False and "Variante B" in hinweise(e["verknuepfungen"])


def test_i11_fehlender_werte_eintrag_ist_unbewiesen():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    del n["verknuepfungen"]["Abstand2"]["werte"]["Variante B"]
    assert vergleich(spec_aus(), n, vorher=v)["verknuepfungen"]["ok"] is None
    n = copy.deepcopy(v)
    del n["verknuepfungen"]["Abstand2"]["werte"]["Variante B"]["wert"]
    assert vergleich(spec_aus(), n, vorher=v)["verknuepfungen"]["ok"] is None
    n = copy.deepcopy(v)
    del n["verknuepfungen"]["Abstand2"]["werte"]
    assert vergleich(spec_aus(), n, vorher=copy.deepcopy(n))["verknuepfungen"]["ok"] is None


def test_i11_wert_punkt_gilt_in_jeder_konfiguration():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    s = spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu=12))
    setze_wert(n, "Abstand1", "wert", 12.0, "Standard")
    e = vergleich(s, n, vorher=v)
    assert e["punkt:w1"]["ok"] is False and "Variante B" in hinweise(e["punkt:w1"])
    setze_wert(n, "Abstand1", "wert", 12.0, "Variante B")
    e = vergleich(s, n, vorher=v)
    assert e["punkt:w1"]["ok"] is True and e["verknuepfungen"]["ok"] is True
    del n["verknuepfungen"]["Abstand1"]["werte"]["Variante B"]
    assert vergleich(s, n, vorher=v)["punkt:w1"]["ok"] is None


def test_i11_neue_verknuepfung_wert_in_jeder_konfiguration():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    n["verknuepfungen"]["Abstand4"] = verknuepfung(5, ["Deckel-1", "Platte-1"], wert=12.0)
    n["verknuepfungen"]["Abstand4"]["werte"]["Variante B"] = {"wert": 11.0, "min": None, "max": None}
    for feld in ("fehler", "unterdrueckt"):
        n["verknuepfungen"]["Abstand4"][feld]["Variante B"] = n["verknuepfungen"]["Abstand4"][feld]["Standard"]
    s = spec_aus(punkt("verknuepfung_neu", "v1", art="abstand", wert=12, a={"komponente": "Platte-1", "feature": "F"},
                       b={"komponente": "Deckel-1", "feature": "F"}))
    assert vergleich(s, n, vorher=v)["punkt:v1"]["ok"] is False
    n["verknuepfungen"]["Abstand4"]["werte"]["Variante B"]["wert"] = 12.0
    assert vergleich(s, n, vorher=v)["punkt:v1"]["ok"] is True


def test_i11_referenzierte_konfiguration_je_konfiguration():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    setze_konfig(n, "Deckel-1", "Andere", "Variante B")  # die aktive bleibt gleich
    e = vergleich(spec_aus(), n, vorher=v)
    assert e["komponenten"]["ok"] is False and "Variante B" in hinweise(e["komponenten"])
    n = copy.deepcopy(v)
    del n["komponenten"]["Deckel-1"]["konfigurationen"]["Variante B"]
    assert vergleich(spec_aus(), n, vorher=v)["komponenten"]["ok"] is None


def test_i11_neue_komponente_konfiguration_je_konfiguration():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    n = copy.deepcopy(v)
    _neue_komp(n)
    for feld in ("fixiert", "unterdrueckt", "status", "transform", "konfigurationen"):
        n["komponenten"]["Neu-1"][feld]["Variante B"] = copy.deepcopy(n["komponenten"]["Neu-1"][feld]["Standard"])
    s = _spec_neue_komp(konfiguration="Standard")
    assert vergleich(s, n, {"k1": ["Neu-1"]}, vorher=v)["punkt:k1"]["ok"] is True
    setze_konfig(n, "Neu-1", "Andere", "Variante B")
    assert vergleich(s, n, {"k1": ["Neu-1"]}, vorher=v)["punkt:k1"]["ok"] is False
