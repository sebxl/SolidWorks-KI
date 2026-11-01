"""Größenmessung (Spec Bestandsdateien §8.7, Plan Task 14) ohne SolidWorks: Bauplan, Spec, Bewertung und Tabelle von `werkzeuge.bestand_gross`."""

from types import SimpleNamespace

import pytest

from swki.bestand import pfade
from swki.spec.laden import lade_yaml
from werkzeuge import bestand_gross as gross


def test_bohrbild_hat_rund_die_verlangte_flaechenzahl():
    punkte = gross.bohrbild(2000)
    assert len(punkte) == 2000
    assert len(set(punkte)) == len(punkte)


def test_bohrbild_passt_in_die_platte_und_laesst_die_bohrungen_getrennt():
    punkte = gross.bohrbild(2000)
    seite = gross.plattenseite(punkte)
    assert all(abs(x) + gross.BOHRUNG_D / 2 < seite and abs(y) + gross.BOHRUNG_D / 2 < seite for x, y in punkte)
    naechster = min(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(punkte, punkte[1:]))
    assert naechster >= gross.TEILUNG > gross.BOHRUNG_D


def test_plan_hat_40_dateien_und_200_komponenten():
    plan = gross.plan_komponenten()
    assert len(plan) == 200 and len({k["datei"] for k in plan}) == 40
    assert sum(k["datei"] == gross.BOHRBILD for k in plan) == 1


def test_plan_ohne_ueberlappung_und_frei_fuer_den_schieber():
    plan = [k for k in gross.plan_komponenten() if k["datei"] != gross.BOHRBILD]
    lagen = [(k["x"], k["y"]) for k in plan]
    assert len(set(lagen)) == len(lagen)
    assert min(abs(a[0] - b[0]) + abs(a[1] - b[1]) for i, a in enumerate(lagen) for b in lagen[i + 1:]) >= gross.BLOCK_MAX
    x, y = gross.SCHIEBER_LAGE[0], gross.SCHIEBER_LAGE[1]
    weg = gross.HUB + gross.BLOCK_MAX
    assert not [k for k in plan if k["y"] == y and x - weg < k["x"] < x + weg and k is not plan[0]]


def test_schieber_ist_die_erste_komponente():
    assert gross.plan_komponenten()[1]["name"] == gross.SCHIEBER and gross.plan_komponenten()[0]["datei"] == gross.BOHRBILD


@pytest.mark.parametrize("name", gross.AUFTRAEGE.values())
def test_auftraege_sind_testauftraege(name):
    assert name.startswith("LIVE-")


def test_spec_nennt_einen_teil_punkt_auf_dem_bohrbild(tmp_path):
    a = {"datei": {"name": gross.HAUPT, "sha256": "a" * 64}}
    pfad = gross.schreibe_spec(tmp_path / "LIVE-GROSS" / "aenderung.yaml", a)
    spec = lade_yaml(pfad)
    [p] = spec["punkte"]
    assert (spec["art"], p["typ"], p["in_datei"]) == ("aenderung", "mass", gross.BOHRBILD)
    assert spec["bereiche"] == [{"punkte": [p["id"]], "in_datei": gross.BOHRBILD, "box": spec["bereiche"][0]["box"]}]
    assert p["alt"] == gross.DICKE


def _bericht(**phasen) -> dict:
    return {"aufnahme": {"phasen": {"lesen": {"s": 10.0, "mb": 2000.0}}, "spitze_mb": 3000.0, "s": 20.0}, "bauen": {"phasen": {},
                                                                                                                    "spitze_mb": 2500.0, "s": 5.0},
            "pruefen": {"phasen": {}, "spitze_mb": 2600.0, "s": 5.0}} | phasen


def test_bewertung_ohne_befund():
    assert gross.bewertung(_bericht(), 20000) == []


def test_bewertung_nennt_speicher_ueber_der_grenze():
    b = _bericht(pruefen={"phasen": {}, "spitze_mb": 21000.0, "s": 5.0})
    [text] = gross.bewertung(b, 20000)
    assert "pruefen" in text and "21000" in text


def test_bewertung_nennt_eine_lange_aufnahme():
    b = _bericht(aufnahme={"phasen": {}, "spitze_mb": 3000.0, "s": 601.0})
    assert any("Aufnahme" in t and "601" in t for t in gross.bewertung(b, 20000))


def test_nicht_gelesener_speicher_ist_kein_befund_und_kein_fehler():
    assert gross.bewertung(_bericht(bauen={"phasen": {}, "spitze_mb": None, "s": 5.0}), 20000) == []


def test_tabelle_nennt_jede_phase():
    b = _bericht()
    b["aufnahme"]["phasen"]["lesen"] = {"s": 10.5, "mb": 2000.0}
    text = gross.tabelle(b)
    assert "| aufnahme | lesen | 10.5 | 2000 |" in text and "| pruefen | gesamt | 5.0 | 2600 |" in text


def test_tabelle_mit_nicht_gelesenem_speicher():
    assert "| bauen | gesamt | 5.0 | – |" in gross.tabelle(_bericht(bauen={"phasen": {}, "spitze_mb": None, "s": 5.0}))


def test_sichtbar_erzwingt_das_fenster_und_stellt_zurueck(monkeypatch):
    aufrufe = []
    monkeypatch.setattr(pfade, "oeffne", lambda app, pfad, sichtbar=True, nur_lesen=False, voll=False: aufrufe.append((sichtbar,
                                                                                                                       nur_lesen,
                                                                                                                       voll)))
    alt = pfade.oeffne
    with gross.modus("sichtbar"):
        pfade.oeffne(None, "x", sichtbar=False, nur_lesen=True, voll=True)
    assert pfade.oeffne is alt and aufrufe == [(True, True, True)]


def test_unsichtbar_laesst_alles_wie_es_ist(monkeypatch):
    alt = pfade.oeffne
    with gross.modus("unsichtbar"):
        assert pfade.oeffne is alt


def test_unbekannter_modus():
    with pytest.raises(ValueError), gross.modus("halb"):
        pass


def test_fehlendes_erzeugnis_nennt_den_aufruf(tmp_path):
    r = SimpleNamespace(arbeitsordner=tmp_path, sw_jahr=2025)
    with pytest.raises(SystemExit, match="bestand_gross erzeugen"):
        gross.haupt_pfad(r)


def test_erzeugnis_liegt_unter_dem_jahr(tmp_path):
    r = SimpleNamespace(arbeitsordner=tmp_path, sw_jahr=2025)
    ordner = tmp_path / "BESTAND-GROSS" / "2025" / "orig"
    ordner.mkdir(parents=True)
    (ordner / gross.HAUPT).write_bytes(b"x")
    assert gross.haupt_pfad(r) == ordner / gross.HAUPT
