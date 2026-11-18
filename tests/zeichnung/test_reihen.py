"""Zeichnungsableitung Z1.3 Stufe 2, Nachtrag (Nutzer 18.11.2026: Maße übereinander, Maßzahlen von Linien gekreuzt):
lineare Maße je Ansichtsseite in Reihen legen. Fälle nach der Spannplatte (Live, spikes/z1_diag_masslinien.py)."""

from swki.zeichnung.reihen import LinMass, reihen

UMRISS = (123.1, 176.0, 235.0, 247.9)  # Hauptansicht der Spannplatte, Blatt-mm


def _h(k, von, bis, lage=153.9, text=12.0):
    return LinMass(k, "h", von, bis, lage, text)


def _v(k, von, bis, lage=100.0, text=12.0):
    return LinMass(k, "v", von, bis, lage, text)


def test_verschachtelte_spannen_nie_in_einer_reihe():
    """50, 100, 10 lagen live auf einer Maßlinie übereinander; 150 und 200 außen."""
    masse = [_h("200", 129.1, 229.1, 141.9, 16.8), _h("50", 139.1, 164.1, 153.9, 12.4), _h("150", 141.6, 216.6, 147.9, 16.8),
             _h("100", 129.1, 179.1, 153.9, 16.8), _h("10", 174.1, 179.1, 153.9, 14.2)]
    lage = reihen(masse, UMRISS)
    quer = {k: q for k, (_, q) in lage.items()}
    assert all(q < UMRISS[1] for q in quer.values())  # alle unter der Ansicht
    assert quer["50"] > quer["100"] > quer["150"] > quer["200"]  # kurz innen, lang außen
    assert len(set(quer.values())) >= 4


def test_text_auf_einer_reihe_ueberlappt_nicht():
    masse = [_h("50", 139.1, 164.1, text=12.4), _h("10", 174.1, 179.1, text=14.2), _h("100", 129.1, 179.1, text=16.8)]
    lage = reihen(masse, UMRISS)
    belegt = {}
    for m in masse:
        mitte, q = lage[m.schluessel]
        lo, hi = min(m.von, mitte - m.text / 2), max(m.bis, mitte + m.text / 2)
        for lo2, hi2 in belegt.get(q, []):
            assert hi <= lo2 or hi2 <= lo, (m.schluessel, q)
        belegt.setdefault(q, []).append((lo, hi))


def test_kurze_spanne_text_aussen():
    """10 mm Spanne bei 14 mm Text: Zahl außerhalb der Hilfslinien, nicht zwischen ihnen (sonst kreuzen sie die Zahl)."""
    [(mitte, _)] = reihen([_h("10", 174.1, 179.1, text=14.2)], UMRISS).values()
    assert mitte - 7.1 >= 179.1 or mitte + 7.1 <= 174.1


def test_lange_spanne_text_mittig():
    [(mitte, _)] = reihen([_h("200", 129.1, 229.1, text=16.8)], UMRISS).values()
    assert abs(mitte - 179.1) < 0.01


def test_seite_bleibt_erhalten():
    """Maß über der Ansicht bleibt oben, links bleibt links; erste Reihe mit Abstand zum Umriss."""
    oben = reihen([_h("40", 129.1, 149.1, 251.9)], UMRISS)["40"][1]
    links = reihen([_v("120", 181.9, 241.9, 103.8)], UMRISS)["120"][1]
    rechts = reihen([_v("x", 181.9, 241.9, 240.0)], UMRISS)["x"][1]
    assert oben > UMRISS[3] + 3 and links < UMRISS[0] - 3 and rechts > UMRISS[2] + 3


def test_senkrechte_masse_links_gestaffelt():
    masse = [_v("120", 181.9, 241.9, 103.8, 16.8), _v("30", 204.4, 219.4, 97.8), _v("27", 198.4, 211.9, 97.8),
             _v("20a", 181.9, 191.9, 115.8), _v("20b", 231.9, 241.9, 121.8)]
    quer = {k: q for k, (_, q) in reihen(masse, UMRISS).items()}
    assert quer["30"] != quer["27"]  # überlappende Spannen
    assert quer["120"] == min(quer.values())  # längste ganz außen


def _textintervall(m, mitte):
    return mitte - m.text / 2, mitte + m.text / 2


def test_zahl_nicht_auf_hilfslinie_aeusserer_reihe():
    """Live 18.11.: „10,00“ (Spanne 174–179, Zahl außen links) lag auf der Hilfslinie der 50 bei 164,1; „27,00“ auf der
    Hilfslinie der 30. Hilfslinien äußerer Reihen laufen durch alle inneren Reihen."""
    masse = [_h("50", 139.1, 164.1, text=12.4), _h("10", 174.1, 179.1, text=14.2), _h("100", 129.1, 179.1, text=16.8),
             _v("27", 198.4, 211.9, 97.8), _v("30", 204.4, 219.4, 97.8), _v("20a", 181.9, 191.9, 115.8)]
    lage = reihen(masse, UMRISS)
    for m in masse:
        mitte, q = lage[m.schluessel]
        lo, hi = _textintervall(m, mitte)
        for n in masse:
            if n.richtung == m.richtung and abs(lage[n.schluessel][1] - (UMRISS[1] if m.richtung == "h" else UMRISS[0])) \
                    > abs(q - (UMRISS[1] if m.richtung == "h" else UMRISS[0])):
                for kante in (n.von, n.bis):
                    assert not lo < kante < hi, (m.schluessel, n.schluessel, kante)


def test_aussen_stehende_zahl_bleibt_in_der_ansichtsbreite():
    """Live 18.11.: „20,00“ (Spanne am linken Rand) stand links außerhalb der Ansicht in der Ecke der senkrechten Maße."""
    [(mitte, _)] = reihen([_h("20", 129.1, 139.1, 251.9, 12.0)], UMRISS).values()
    assert mitte - 6.0 >= UMRISS[0]


def test_klemmende_zahl_rueckt_eine_reihe_nach_aussen():
    """Live 18.11.: „20,00“ (Spanne 129,1–139,1, Zahl 14,2) passt nicht zwischen die Hilfslinien der 30 (149,1–164,1)
    und der 40 (129,1–149,1); außen links stünde sie in der Ecke. Lösung: eine Reihe weiter außen als 30 und 40."""
    masse = [_h("20", 129.1, 139.1, 252.9, 14.2), _h("30", 149.1, 164.1, 260.9, 14.2), _h("40", 129.1, 149.1, 268.9, 14.2)]
    lage = reihen(masse, UMRISS)
    mitte, q = lage["20"]
    assert mitte - 7.1 >= UMRISS[0]  # in der Ansichtsbreite
    for n in ("30", "40"):
        if lage[n][1] > q:  # weiter außen → Hilfslinien dürfen die Zahl nicht kreuzen
            for kante in (masse[1 if n == "30" else 2].von, masse[1 if n == "30" else 2].bis):
                assert not mitte - 7.1 < kante < mitte + 7.1, n


def test_vorlauf_rueckt_die_seite_nach_aussen():
    """Live 18.11.: „0,50“ auf „SCHNITT A-A“ unter dem Schnitt – Vorlauf je Seite schiebt alle Reihen dort nach außen."""
    m = [_h("x", 140.0, 200.0, 150.0)]
    ohne = reihen(m, UMRISS)["x"][1]
    mit = reihen(m, UMRISS, {("h", "-"): 8.0})["x"][1]
    assert mit == ohne - 8.0 and reihen(m, UMRISS, {("h", "+"): 8.0})["x"][1] == ohne
