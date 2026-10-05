"""Geometrie der Evolventenverzahnung (Spec 4b §4.2, §4.5) ohne SolidWorks."""

import math

import pytest

from swki.verzahnung import (ALPHA, Bogen, Linie, Spline, Stirnrad, VerzahnungFehler, Zahnstange, aus_feature,
                             genormte_module, inv, ist_genormt)


def _enden(s):
    return (s.punkte[0], s.punkte[-1]) if isinstance(s, Spline) else (s.a, s.b)


def _geschlossen(kontur, tol=1e-9):
    for s, t in zip(kontur, kontur[1:] + kontur[:1]):
        assert math.dist(_enden(s)[1], _enden(t)[0]) <= tol, (s, t)


def _dicht(kontur, n=400):
    """Kontur als dichter Polygonzug (Bögen fein abgetastet) – unabhängige Flächenrechnung für die Tests."""
    pts = []
    for s in kontur:
        if isinstance(s, Spline):
            pts += list(s.punkte[:-1])
        elif isinstance(s, Linie):
            pts.append(s.a)
        else:
            r = math.dist(s.mitte, s.a)
            wa = math.atan2(s.a[1] - s.mitte[1], s.a[0] - s.mitte[0])
            wb = math.atan2(s.b[1] - s.mitte[1], s.b[0] - s.mitte[0])
            d = (wb - wa) % (2 * math.pi) if s.gegen_uhrzeigersinn else -((wa - wb) % (2 * math.pi))
            pts += [(s.mitte[0] + r * math.cos(wa + d * i / n), s.mitte[1] + r * math.sin(wa + d * i / n))
                    for i in range(n)]
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2


def test_evolventenfunktion():
    assert inv(ALPHA) == pytest.approx(0.014904383867, rel=1e-9)


@pytest.mark.parametrize(("z", "k", "w"), [(17, 2, 4.6663), (20, 3, 7.6604), (50, 6, 16.9370)])
def test_zahnweite_tabellenwerte_modul_1(z, k, w):
    # Zahnweiten für m = 1, α = 20°, x = 0 (Tabellenwerte z. B. DIN 3960 / KHK-Tafeln)
    rad = Stirnrad(1.0, z)
    assert rad.messzaehnezahl() == k
    assert rad.zahnweite() == pytest.approx(w, abs=1e-4)


def test_zahnweite_mit_abmass_und_modul():
    ohne, mit = Stirnrad(2.0, 20), Stirnrad(2.0, 20, -0.05)
    assert ohne.zahnweite() == pytest.approx(2 * 7.66044, abs=1e-4)
    assert mit.zahnweite() - ohne.zahnweite() == pytest.approx(-0.05 * math.cos(ALPHA), abs=1e-12)


def test_kreise_stirnrad():
    rad = Stirnrad(2.0, 20)
    assert (2 * rad.r, 2 * rad.ra, 2 * rad.rf) == pytest.approx((40.0, 44.0, 35.0))
    assert 2 * rad.rb == pytest.approx(37.5877, abs=1e-4)
    assert rad.tau == pytest.approx(math.radians(18))


@pytest.mark.parametrize("z", [17, 20, 25, 41, 42, 50, 80])
def test_profil_stirnrad_geschlossen_und_auf_der_evolvente(z):
    rad = Stirnrad(2.0, z, -0.05)
    [kontur] = rad.profil(mitte=(5.0, -3.0), winkel=10.0)
    _geschlossen(kontur)
    splines = [s for s in kontur if isinstance(s, Spline)]
    assert len(splines) == 2 * z
    kopf = [s for s in kontur if isinstance(s, Bogen) and s.mitte == (5.0, -3.0)
            and abs(math.dist(s.mitte, s.a) - rad.ra) < 1e-9]
    assert len(kopf) == z
    for q in splines[0].punkte:  # rechte Flanke von Zahn 1: Winkel zur Zahnmitte = −psi(ρ)
        rho = math.dist(q, (5.0, -3.0))
        phi = math.atan2(q[1] + 3.0, q[0] - 5.0)
        assert phi == pytest.approx(math.radians(10.0) - rad.psi(rho), abs=1e-12)


def test_zahndicke_am_teilkreis():
    rad = Stirnrad(2.0, 20, -0.05)
    links, rechts = rad.flankenpunkt(1, "links", rad.r), rad.flankenpunkt(1, "rechts", rad.r)
    bogen = rad.r * (math.atan2(links[1], links[0]) - math.atan2(rechts[1], rechts[0]))
    assert bogen == pytest.approx(math.pi + -0.05, abs=1e-12)


def test_flaeche_stirnrad_gegen_dichten_polygonzug():
    rad = Stirnrad(2.0, 20, -0.05)
    [kontur] = rad.profil(n=200)
    assert rad.flaeche() == pytest.approx(_dicht(kontur), rel=1e-5)
    assert math.pi * rad.rf ** 2 < rad.flaeche() < math.pi * rad.ra ** 2


def test_radiale_verlaengerung_nur_unter_dem_grundkreis():
    assert any(isinstance(s, Linie) for s in Stirnrad(2.0, 20).profil()[0])   # Grundkreis über der Fußrundung
    assert not any(isinstance(s, Linie) for s in Stirnrad(2.0, 50).profil()[0])  # Evolvente ab der Fußrundung


def test_stirnrad_nicht_konstruierbar():
    with pytest.raises(VerzahnungFehler, match="spitz"):
        Stirnrad(1.0, 20, -1.5).pruefe()
    with pytest.raises(VerzahnungFehler, match="Lücke"):
        Stirnrad(1.0, 20, 1.0).pruefe()


def test_zahnstange_profil():
    st = Zahnstange(2.0, 5, -0.05)
    konturen = st.profil(mitte=(10.0, 20.0))
    assert len(konturen) == 5
    for j, k in enumerate(konturen, start=1):
        _geschlossen(k)
        kopf = k[3]
        assert kopf.a[1] == pytest.approx(22.0) and kopf.b[1] == pytest.approx(22.0)  # Kopflinie v0 + m
        assert k[0].a[1] == pytest.approx(17.5)                                         # Fußlinie v0 − 1,25 m
        assert (kopf.a[0] + kopf.b[0]) / 2 == pytest.approx(10.0 + (j - 1) * 2 * math.pi)
    assert st.flankenmitte(1, "rechts", 10.0) - st.flankenmitte(1, "links", 10.0) == pytest.approx(math.pi - 0.05)
    assert st.flankenmitte(2, "links") - st.flankenmitte(1, "links") == pytest.approx(2 * math.pi)


def test_zahnstange_fussrundung_beruehrt_flanke():
    st = Zahnstange(2.0, 1)
    c, t1, t2 = st._fussrundung(0.0, 1)
    assert math.dist(c, t1) == pytest.approx(st.rho) and math.dist(c, t2) == pytest.approx(st.rho)
    # t1 liegt auf der rechten Flanke u = s/2 − v·tan α
    assert t1[0] == pytest.approx(st.s / 2 - t1[1] * math.tan(ALPHA))
    assert t1[1] == pytest.approx(-2.0, abs=1e-3)  # DIN 867: die Fußrundung endet etwa bei −m


def test_zahnstange_flaeche_und_spiegelung():
    st = Zahnstange(2.0, 3, -0.05)
    assert st.flaeche() == pytest.approx(sum(_dicht(k) for k in st.profil()), rel=1e-6)
    unten = st.profil(mitte=(0.0, 0.0), kopf="-v")
    assert unten[0][3].a[1] == pytest.approx(-2.0)
    assert sum(_dicht(k) for k in unten) == pytest.approx(st.flaeche(), rel=1e-6)


def test_zahnstange_spitz():
    with pytest.raises(VerzahnungFehler, match="spitz"):
        Zahnstange(1.0, 3, -1.3).pruefe()


def test_genormte_module():
    assert genormte_module()[0] == 0.05 and 20.0 in genormte_module()
    assert ist_genormt(2) and ist_genormt(0.7) and not ist_genormt(2.25) and not ist_genormt(25)


def test_aus_feature():
    p = {"M": 2, "Z": 20, "AS": -0.05}
    rad = aus_feature({"art": "stirnrad", "modul": "=M", "zaehne": "=Z", "zahndickenabmass": "=AS"}, p)
    assert rad == Stirnrad(2.0, 20, -0.05)
    st = aus_feature({"art": "zahnstange", "modul": 2, "zaehne": 9, "zahndickenabmass": -0.05}, {})
    assert st == Zahnstange(2.0, 9, -0.05)
