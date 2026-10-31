"""swki durchlauf für art: aenderung ohne SolidWorks: validieren, freigeben, bauen und status sind echt (Attrappe wie in `test_bau`),
nur das Prüfen ist ersetzt. Kern: Der Prüfer bekommt für Änderungen auch die Vorher-Bilder."""

import pytest

from swki import durchlauf as d
from swki.auftrag import lauf_ordner
from swki.bestand import pruefen as pruef_modul
from swki.pruefung import befehle
from tests.bestand.test_bau import MASS, Lauf


@pytest.fixture
def u(tmp_path, monkeypatch):
    lauf = Lauf(tmp_path, monkeypatch)
    monkeypatch.setattr(befehle, "lade_standard", lambda: {"max_nachbesserungen": 3})
    lauf.pruefen_aufrufe = []

    def pruefen(spec_pfad, nummer):
        ordner = lauf_ordner(lauf.r, "A", nummer)
        lauf.pruefen_aufrufe.append(nummer)
        bericht = {"auftrag": "A", "spec": spec_pfad.name, "lauf": nummer, "datei": str(lauf.lauf_datei(nummer)), "bestanden": True,
                   "maengel": [], "pruefungen": [{"id": "baum", "ok": True}, {"id": "punkt:p1", "ok": True}],
                   "differenzen": {"Standard": []},
                   "bilder": {"iso": str(ordner / "bilder" / "iso.png")},
                   "bilder_vorher": {"iso": str(ordner / "vergleich" / "bilder" / "iso.png")}}
        befehle.schreibe_pruefbericht(spec_pfad, nummer, ordner, bericht)
        return bericht

    monkeypatch.setattr(pruef_modul, "pruefen", pruefen)
    return lauf


def test_durchlauf_mit_aenderung(u):
    u.schreibe(MASS, freigeben=False)
    erg = d.durchlauf(u.spec_pfad, freigeben=True)
    assert erg["schritt"] == "fertig", erg
    assert erg["freigegeben"] and erg["lauf"] == 1 and u.pruefen_aufrufe == [1]  # validieren → freigeben → bauen → prüfen
    assert erg["pruefung"]["bestanden"] is True and erg["empfehlung"] == "pruefer"
    assert u.lauf_datei(1).is_file()
    auftrag = erg["pruefer_auftrag"]
    ordner = lauf_ordner(u.r, "A", 1)
    assert str(ordner / "bilder" / "iso.png") in auftrag
    assert str(ordner / "vergleich" / "bilder" / "iso.png") in auftrag and "Vorher" in auftrag


def test_durchlauf_ohne_freigabe_scheitert_im_schritt_bauen(u):
    u.schreibe(MASS, freigeben=False)
    erg = d.durchlauf(u.spec_pfad)
    assert erg["schritt"] == "bauen" and u.pruefen_aufrufe == []


def test_durchlauf_validieren_scheitert_vor_dem_bau(u):
    u.schreibe({**MASS, "alt": 41}, freigeben=False)  # der Bestand hat 40
    erg = d.durchlauf(u.spec_pfad, freigeben=True)
    assert erg["schritt"] == "validieren" and not u.lauf_datei(1).exists()


def test_durchlauf_bauabbruch_endet_im_schritt_bauen(u):
    u.schreibe(MASS, freigeben=False)

    def fehler_nach_setzen(teil):
        teil.bei_neuaufbau = lambda t: t.fehler.__setitem__(t.aktiv, [("Fase3", 7, False)]) if t.masse["D2@Skizze4"].gesetzt else None

    u.vor_teil = fehler_nach_setzen
    erg = d.durchlauf(u.spec_pfad, freigeben=True)
    assert erg["schritt"] == "bauen" and erg["code"] == "REBUILD_FEHLER" and u.pruefen_aufrufe == []


def test_pruefer_auftrag_ohne_vorher_bilder_wie_bisher(tmp_path):
    ordner = tmp_path / "lauf-3"
    text = d.pruefer_auftrag(tmp_path / "a.yaml", 3, {"datei": str(ordner / "a.sldprt"), "bilder": {"iso": str(ordner / "iso.png")}})
    assert "Vorher" not in text and str(ordner / "iso.png") in text


def test_pruefer_auftrag_nennt_vorher_bilder_sortiert(tmp_path):
    iso, vorne = str(tmp_path / "vergleich" / "iso.png"), str(tmp_path / "vergleich" / "vorne.png")
    text = d.pruefer_auftrag(tmp_path / "a.yaml", 3, {"datei": str(tmp_path / "a.sldprt"), "bilder": {},
                                                      "bilder_vorher": {"vorne": vorne, "iso": iso}})
    assert f"Vorher-Bilder (Bestand, dieselben Ansichten wie die Screenshots): {iso}, {vorne}." in text
