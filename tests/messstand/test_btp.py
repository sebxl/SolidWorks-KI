"""Bewertungsbogen Tempo und Präzision (Spec 2026-10-23 §5) ohne SolidWorks: Anker, Score, Entscheidung."""

import pytest

from werkzeuge.messstand import btp


@pytest.mark.parametrize("x, s", [(400, 0.0), (300, 0.0), (187.5, 3.5), (75, 7.0), (57.5, 8.5), (40, 10.0), (10, 10.0)])
def test_anker_kleiner_ist_besser(x, s):
    assert btp.anker(x, 300, 75, 40) == pytest.approx(s)


@pytest.mark.parametrize("x, s", [(-1, 0.0), (0, 0.0), (2.5, 3.5), (5, 7.0), (5.5, 8.5), (6, 10.0), (7, 10.0)])
def test_anker_groesser_ist_besser(x, s):
    assert btp.anker(x, 0, 5, 6) == pytest.approx(s)


def _k(aufgabe, zeit, lauf=None, tokens=100_000, speicher=4000, fehler=0, richtig=True, bestanden=True, **extra):
    return {"lauf": lauf or f"d1-{aufgabe}-1", "aufgabe": aufgabe, "zeit_s": zeit, "tool_aufrufe": 20,
            "tokens": {"gewichtet": tokens}, "speicher_spitze_mb": speicher, "bauabbrueche": fehler,
            "pruefmaengel": 0, "pruefer_maengel": 0, "freigaben": 1, "richtig": richtig, "bestanden": bestanden,
            "lecks": [], "haenger": 0, **extra}


def _durchgang(faktor=1.0, **ueber):
    zeiten = {"durchlicht": 136, "kamera": 191, "zentrieraufnahme": 129, "stehlager": 365, "pruefstation": 1050}
    zeiten |= ueber
    laeufe = [_k(a, z * faktor) for a, z in zeiten.items()]
    laeufe.append(_k("durchlicht", 136 * faktor, lauf="d1-durchlicht-2"))
    return laeufe


def test_bezug_und_ausgangswert_wie_im_bogen():
    laeufe = _durchgang()
    laeufe[-2]["speicher_spitze_mb"] = 14300            # Prüfstation
    laeufe[0]["bauabbrueche"] = 1                       # 1 Fehlerpunkt = Ziel (7)
    b = btp.bezug(laeufe)
    erg = btp.bewerte(laeufe, {"treffer": 5, "fehlalarme": 0}, b)
    t = erg["teilscores"]
    assert t["zeit_teile"] == pytest.approx(7 * (300 - 152) / 225, abs=0.01)
    assert t["zeit_stehlager"] == pytest.approx(4.51, abs=0.01)
    assert t["zeit_pruefstation"] == pytest.approx(4.77, abs=0.01)
    assert t["praezision_lauf"] == pytest.approx(7.0)
    assert t["praezision_fallen"] == pytest.approx(7.0)
    assert t["aufwand"] == pytest.approx(5.0)
    assert t["robustheit"] == pytest.approx(7 * (16000 - 14300) / 8000, abs=0.01)
    assert erg["score"] == pytest.approx(5.5, abs=0.05)
    assert erg["werte"]["zeit_teile"] == pytest.approx(152, abs=0.5)


def test_nicht_fertig_strafe_und_deckel():
    b = btp.bezug(_durchgang())
    laeufe = _durchgang(0.5)
    laeufe[1]["richtig"] = False                       # kamera
    erg = btp.bewerte(laeufe, {"treffer": 6, "fehlalarme": 0}, b)
    assert erg["werte"]["zeit_kamera"] == pytest.approx(1.5 * 191)
    assert erg["score"] <= 4.0
    assert erg["nicht_richtig"] == ["kamera"]


def test_haenger_kostet_robustheit():
    b = btp.bezug(_durchgang())
    laeufe = _durchgang()
    laeufe[0]["haenger"] = 1
    erg = btp.bewerte(laeufe, {"treffer": 5, "fehlalarme": 0}, b)
    assert erg["werte"]["robustheit"] == 4000 + 2000


def test_fehlende_aufgabe_ist_fehler():
    b = btp.bezug(_durchgang())
    with pytest.raises(ValueError, match="pruefstation"):
        btp.bewerte([k for k in _durchgang() if k["aufgabe"] != "pruefstation"], {"treffer": 5, "fehlalarme": 0}, b)


def test_wiederholung_im_durchgang_0_zaehlt_fehler_mit():
    erster = _k("kamera", 400, lauf="d0-kamera-1", bestanden=False, fehler=2)
    zweiter = _k("kamera", 200, lauf="d0-kamera-1w1", wiederholung_von="d0-kamera-1", original_fehler_zaehlen=True)
    laeufe = [k for k in _durchgang() if k["aufgabe"] != "kamera"] + [erster, zweiter]
    b = btp.bezug(laeufe)
    assert b["aufgaben"]["kamera"]["zeit_s"] == 200
    erg = btp.bewerte(laeufe, {"treffer": 5, "fehlalarme": 0}, b)
    assert erg["werte"]["praezision_lauf"] == 2


def test_wiederholung_im_umbau_ersetzt_original():
    erster = _k("kamera", 400, lauf="d2-kamera-1", fehler=2)
    zweiter = _k("kamera", 190, lauf="d2-kamera-1w1", wiederholung_von="d2-kamera-1", original_fehler_zaehlen=False)
    b = btp.bezug(_durchgang())
    laeufe = [k for k in _durchgang() if k["aufgabe"] != "kamera"] + [erster, zweiter]
    erg = btp.bewerte(laeufe, {"treffer": 5, "fehlalarme": 0}, b)
    assert erg["werte"]["praezision_lauf"] == 0
    assert erg["werte"]["zeit_kamera"] == 190


def test_fallen_mit_fehlalarm():
    b = btp.bezug(_durchgang())
    erg = btp.bewerte(_durchgang(), {"treffer": 6, "fehlalarme": 1}, b)
    assert erg["werte"]["praezision_fallen"] == 5


def test_besser():
    b = btp.bezug(_durchgang())
    alt = btp.bewerte(_durchgang(), {"treffer": 5, "fehlalarme": 0}, b)
    neu = btp.bewerte(_durchgang(0.6), {"treffer": 5, "fehlalarme": 0}, b)
    ok, grund = btp.besser(neu, alt, d0=alt)
    assert ok, grund
    knapp = btp.bewerte(_durchgang(0.98), {"treffer": 5, "fehlalarme": 0}, b)
    assert not btp.besser(knapp, alt, d0=alt)[0]
    schlechtere_fallen = btp.bewerte(_durchgang(0.5), {"treffer": 4, "fehlalarme": 0}, b)
    ok, grund = btp.besser(schlechtere_fallen, alt, d0=alt)
    assert not ok and "praezision_fallen" in grund
    mit_fehler = _durchgang(0.5)
    mit_fehler[0]["pruefmaengel"] = 2
    ok, grund = btp.besser(btp.bewerte(mit_fehler, {"treffer": 5, "fehlalarme": 0}, b), alt, d0=alt)
    assert not ok and "praezision_lauf" in grund
