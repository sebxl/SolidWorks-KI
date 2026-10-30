"""Freigaberegel für autonome Schleifen (Spec C2 §6): die Freigabe gibt den Raum frei, die Schleife läuft darin ohne
Rückfrage; gebaut wird erst nach ausdrücklichem OK des Nutzers (`swki freigeben --im-raum` prüft dann, dass nur
Stellschrauben im Rahmen geändert sind)."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

from swki.cli import main
from swki.optimierung.raum import freigeben_im_raum, pruefe_im_raum
from swki.spec.freigabe import FreigabeFehler, freigabe_eintrag, pruefe_freigabe, pruefsumme
from swki.spec.laden import lade_spec

from .beispiel import lege_an, rampe

REFERENZ = Path(__file__).parents[1] / "referenz"


def _cli(capsys, *args) -> dict:
    code = main(list(args))
    out = json.loads(capsys.readouterr().out)
    return {"_code": code, **out}


def _setze(pfad: Path, aendern) -> None:
    spec = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    aendern(spec)
    pfad.write_text(yaml.safe_dump(spec, allow_unicode=True, sort_keys=False), encoding="utf-8")


@pytest.fixture
def freigegeben(tmp_path, capsys):
    pfad = lege_an(tmp_path)
    erg = _cli(capsys, "freigeben", str(pfad))
    assert erg["_code"] == 0, erg
    return pfad


def test_freigabe_speichert_raum(freigegeben):
    e = freigabe_eintrag(freigegeben)
    assert e["raum"]["stellschrauben"] == {"H": [5.0, 80.0], "v0": [0.0, 1.0]}
    assert len(e["raum"]["pruefsumme"]) == 64


def test_ergebnis_im_raum_wird_nach_ok_freigegeben(freigegeben, capsys):
    _setze(freigegeben, lambda s: s["parameter"].update(H=42.5))
    with pytest.raises(FreigabeFehler):
        pruefe_freigabe(freigegeben, lade_spec(freigegeben))
    assert pruefe_im_raum(freigegeben)["im_raum"] is True
    erg = _cli(capsys, "freigeben", str(freigegeben), "--im-raum")
    assert erg["_code"] == 0, erg
    pruefe_freigabe(freigegeben, lade_spec(freigegeben))
    nachweis = freigabe_eintrag(freigegeben)["im_raum"]
    assert nachweis["werte"] == {"rampe.yaml": {"H": {"vorher": 30, "nachher": 42.5, "rahmen": [5.0, 80.0]}}}
    assert "raum" in freigabe_eintrag(freigegeben)     # der Raum bleibt für die nächste Runde


def test_ausserhalb_des_rahmens_verweigert(freigegeben):
    _setze(freigegeben, lambda s: s["parameter"].update(H=90))
    with pytest.raises(FreigabeFehler) as e:
        freigeben_im_raum(freigegeben)
    assert e.value.daten["code"] in ("AUSSERHALB_RAUM", "SPEC_UNGUELTIG")


def test_schritt_wird_eingehalten(tmp_path, capsys):
    spec = rampe(stellschrauben=[{"name": "H", "parameter": "H", "rahmen": [5, 80], "schritt": 0.5}], start=[])
    pfad = lege_an(tmp_path, spec)
    assert _cli(capsys, "freigeben", str(pfad))["_code"] == 0
    _setze(pfad, lambda s: s["parameter"].update(H=42.3))
    with pytest.raises(FreigabeFehler) as e:
        freigeben_im_raum(pfad)
    assert e.value.daten["code"] == "AUSSERHALB_RAUM"
    _setze(pfad, lambda s: s["parameter"].update(H=42.5))
    freigeben_im_raum(pfad)


@pytest.mark.parametrize("aendern", [
    lambda s: s["parameter"].update(L=120),                                         # andere Anforderung
    lambda s: s["optimierung"]["ziel"].update(zielwert=0.5),                        # Ziel aufgeweicht
    lambda s: s["optimierung"]["stellschrauben"][0].update(rahmen=[1, 99]),         # Rahmen erweitert
    lambda s: s["optimierung"]["szenarien"][0]["werte"].update(mu=0.1),             # Szenario geändert
    lambda s: s["optimierung"].update(erlaubte_formaenderungen=["alles"]),
])
def test_raum_geaendert_verweigert(freigegeben, aendern):
    _setze(freigegeben, aendern)
    with pytest.raises(FreigabeFehler) as e:
        freigeben_im_raum(freigegeben)
    assert e.value.daten["code"] == "RAUM_GEAENDERT"


def test_pruefaufgabe_geaendert_verweigert(freigegeben):
    (freigegeben.parent / "aufgabe_rampe.py").write_text("# andere Bewertung\n", encoding="utf-8")
    with pytest.raises(FreigabeFehler) as e:
        freigeben_im_raum(freigegeben)
    assert e.value.daten["code"] == "RAUM_GEAENDERT"


def test_bauweg_der_schleife_frei(freigegeben):
    def aendern(s):
        s["optimierung"]["stellschrauben"][0]["bereich"] = [20, 60]
        s["optimierung"]["budget"] = {"proben": 999}
        s["optimierung"]["variante"] = "mit Wangen"
        s["parameter"]["H"] = 21
    _setze(freigegeben, aendern)
    assert freigeben_im_raum(freigegeben)["im_raum"]["werte"]["rampe.yaml"]["H"]["nachher"] == 21


def test_gewoehnliche_pruefsumme_deckt_den_raum():
    assert pruefsumme(rampe()) != pruefsumme(rampe(ziel={"kennzahl": "x", "richtung": "max", "zielwert": 1}))
    assert pruefsumme(rampe()) == pruefsumme(rampe(budget={"proben": 1}, variante="y"))


def test_ohne_raum_freigabe(tmp_path, capsys):
    pfad = lege_an(tmp_path)
    with pytest.raises(FreigabeFehler) as e:
        freigeben_im_raum(pfad)
    assert e.value.daten["code"] == "RAUM_FEHLT"


# --- Baugruppe: Stellschrauben in Teil-Specs ------------------------------------------------------------------------
@pytest.fixture
def schlitten(tmp_path, capsys):
    ordner = tmp_path / "schlitten"
    shutil.copytree(REFERENZ / "schlitten", ordner)
    (ordner / "aufgabe.py").write_text("def jobs(s, n, saat, erster=0):\n    return []\n", encoding="utf-8")
    def block(s):
        s["optimierung"] = {"pruefaufgabe": {"modul": "aufgabe.py"},
                            "ziel": {"kennzahl": "min_anteil_richtig", "richtung": "max", "zielwert": 0.9},
                            "stellschrauben": [{"name": "LH", "spec": "hebel.yaml", "parameter": "L", "rahmen": [40, 80]},
                                               {"name": "HUB", "parameter": "HUB", "rahmen": [150, 230]}],
                            "szenarien": [{"name": "s", "laeufe": 4}]}
    _setze(ordner / "linearschlitten.yaml", block)
    erg = _cli(capsys, "freigeben", str(ordner / "linearschlitten.yaml"))
    assert erg["_code"] == 0, erg
    return ordner


def test_baugruppe_ergebnis_im_raum(schlitten, capsys):
    _setze(schlitten / "hebel.yaml", lambda s: s["parameter"].update(L=70))
    _setze(schlitten / "linearschlitten.yaml", lambda s: s["parameter"].update(HUB=200))
    erg = _cli(capsys, "freigeben", str(schlitten / "linearschlitten.yaml"), "--im-raum")
    assert erg["_code"] == 0, erg
    from swki.baugruppe.freigabe import pruefe_freigabe_baugruppe
    from swki.baugruppe.laden import lade_baugruppe
    pruefe_freigabe_baugruppe(lade_baugruppe(schlitten / "linearschlitten.yaml"))
    w = freigabe_eintrag(schlitten / "linearschlitten.yaml")["im_raum"]["werte"]
    assert w == {"hebel.yaml": {"L": {"vorher": 60, "nachher": 70, "rahmen": [40.0, 80.0]}},
                 "linearschlitten.yaml": {"HUB": {"vorher": 220, "nachher": 200, "rahmen": [150.0, 230.0]}}}


def test_baugruppe_andere_teilanforderung_verweigert(schlitten):
    _setze(schlitten / "hebel.yaml", lambda s: s["parameter"].update(B=18))
    with pytest.raises(FreigabeFehler) as e:
        freigeben_im_raum(schlitten / "linearschlitten.yaml")
    assert e.value.daten["code"] == "RAUM_GEAENDERT"


def test_bauen_nennt_den_raum(freigegeben):
    from swki.optimierung.raum import raum_hinweis
    _setze(freigegeben, lambda s: s["parameter"].update(H=50))
    with pytest.raises(FreigabeFehler) as e:
        pruefe_freigabe(freigegeben, lade_spec(freigegeben))
    neu = raum_hinweis(freigegeben, e.value)
    assert neu.daten == {"code": "FREIGABE_VERALTET", "im_raum": True} and "--im-raum" in str(neu)
    assert "Nutzer" in str(neu) and "ohne Rückfrage" not in str(neu)
    _setze(freigegeben, lambda s: s["parameter"].update(L=50))
    assert raum_hinweis(freigegeben, e.value) is e.value


# --- Form und Freigabe-Kopie ------------------------------------------------------------------------------------------
NEUES_FEATURE = {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "-y"},
                 "positionen": [[20, 0]], "durchmesser": 5, "durch": True}


def test_nicht_erlaubte_formaenderung_verweigert(freigegeben):
    _setze(freigegeben, lambda s: s["features"].append(NEUES_FEATURE))
    with pytest.raises(FreigabeFehler) as e:
        freigeben_im_raum(freigegeben)
    assert e.value.daten["code"] == "FORM_GEAENDERT"


def test_erlaubte_formaenderung_steht_im_nachweis(tmp_path, capsys):
    pfad = lege_an(tmp_path, rampe(erlaubte_formaenderungen=["Bohrung in der Rampe"]))
    assert _cli(capsys, "freigeben", str(pfad))["_code"] == 0
    _setze(pfad, lambda s: s["features"].append(NEUES_FEATURE))
    assert freigeben_im_raum(pfad)["im_raum"]["formaenderungen"] == {"rampe.yaml": {"hinzu": ["f2"]}}


def test_veraenderte_freigabe_kopie_verweigert(freigegeben):
    kopie = freigegeben.with_name("rampe.freigegeben.yaml")
    kopie.write_text(kopie.read_text(encoding="utf-8") + "# von Hand\n", encoding="utf-8")
    _setze(freigegeben, lambda s: s["parameter"].update(H=40))
    with pytest.raises(FreigabeFehler) as e:
        freigeben_im_raum(freigegeben)
    assert e.value.daten["code"] == "KOPIE_GEAENDERT"


def test_abhaengigkeit_der_pruefaufgabe_gehoert_zum_raum(tmp_path, capsys):
    pfad = lege_an(tmp_path, rampe(pruefaufgabe={"modul": "aufgabe_rampe.py", "abhaengigkeiten": ["hilfe.py"]}))
    (tmp_path / "hilfe.py").write_text("x = 1\n", encoding="utf-8")
    assert _cli(capsys, "freigeben", str(pfad))["_code"] == 0
    assert pruefe_im_raum(pfad)["im_raum"] is True
    (tmp_path / "hilfe.py").write_text("x = 2\n", encoding="utf-8")
    with pytest.raises(FreigabeFehler) as e:
        pruefe_im_raum(pfad)
    assert e.value.daten["code"] == "RAUM_GEAENDERT"


def test_freigeben_vom_durchlauf_aufgerufen(tmp_path):
    """swki durchlauf ruft _freigeben mit einem Namespace nur aus spec (Regression, Review C2)."""
    from argparse import Namespace

    from swki.spec.befehle import _freigeben
    pfad = lege_an(tmp_path)
    assert _freigeben(Namespace(spec=str(pfad)))["raum"]["stellschrauben"]["H"] == [5.0, 80.0]
