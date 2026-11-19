"""Zeichnungsableitung Z1.3 Stufe 2, Nachtrag (Nutzer 18.11.2026: Mittellinien für Maße ab Teilmitte): Bezugspunkt eines
Maßes ohne Kante finden, Mittellinien über den Körper legen. Werte nach der Spannplatte (Live, Hauptansicht 1:2,
Ursprung bei (129,5 | 223,0), spikes/z1_diag_mittellinie.py)."""

from swki.zeichnung.mittellinien import bezugspunkt, linien, ohne_kante

KANTEN = [((79.5, 193.0), (179.5, 193.0)), ((179.5, 193.0), (179.5, 253.0)), ((179.5, 253.0), (79.5, 253.0)),
          ((79.5, 253.0), (79.5, 193.0))]  # Plattenumriss 200 × 120 bei 1:2
BOHRUNGEN = [((92.0, 203.0), 2.0), ((167.0, 203.0), 2.0)]


def test_bezugspunkt_liegt_eine_luecke_vor_der_hilfslinie():
    """SolidWorks lässt zwischen Bezug und Hilfslinie ~1 mm Lücke (Live: Ursprung 223,0, Hilfslinie ab 222,0)."""
    assert bezugspunkt((129.5, 222.0), (129.5, 165.0), luecke=1.0) == (129.5, 223.0)


def test_ursprung_ohne_kante_kante_und_kreismitte_mit():
    assert ohne_kante((129.5, 223.0), KANTEN, BOHRUNGEN)          # Plattenmitte: keine Kante
    assert not ohne_kante((79.5, 210.0), KANTEN, BOHRUNGEN)       # linke Plattenkante
    assert not ohne_kante((92.0, 203.0), KANTEN, BOHRUNGEN)       # Bohrungsmitte (Mittelpunktkreuz)


def test_linien_ueber_den_koerper_mit_ueberstand_und_ohne_doppel():
    """Waagrechte Maße (Hilfslinie senkrecht) brauchen eine senkrechte Mittellinie, senkrechte Maße eine waagrechte."""
    box = (79.5, 193.0, 179.5, 253.0)
    aus = linien([("h", (129.5, 223.0)), ("h", (129.6, 223.0)), ("v", (129.5, 223.0))], box, ueberstand=3.0)
    assert sorted(aus) == sorted([((129.5, 190.0), (129.5, 256.0)), ((76.5, 223.0), (182.5, 223.0))])


def test_gedachte_scharfe_ecke_gilt_als_kante():
    """Live 19.11.: 50/30 der Tasche setzen an der gedachten scharfen Ecke an (Ecken gerundet) – das ist kein Bezug ohne
    Kante. Punkt auf der Verlängerung einer geraden Kante (nahe ihrem Ende) zählt als Kante."""
    tasche = [((121.5, 212.5), (138.5, 212.5)), ((142.5, 216.5), (142.5, 223.5))]  # Unterkante, rechte Kante (R4 → 2 mm)
    assert not ohne_kante((142.5, 212.5), tasche, [])   # Schnitt beider Verlängerungen
    assert ohne_kante((160.0, 212.5), tasche, [])       # weit auf der Verlängerung: kein Eckpunkt


def test_kante_parallel_zur_messrichtung_legt_nichts_fest():
    """Live 19.11., Seitenansicht: „24,00“ (senkrechtes Maß) setzt in halber Höhe auf der linken, senkrechten Plattenkante
    an – die Kante legt die Höhe nicht fest, der Bezug ist die Mitte. Eckpunkte legen dagegen beides fest."""
    seite = [((275.0, 190.0), (275.0, 250.0)), ((275.0, 250.0), (285.0, 250.0))]
    assert ohne_kante((275.0, 220.0), seite, [], richtung="v")          # Mitte der senkrechten Kante
    assert not ohne_kante((275.0, 220.0), seite, [], richtung="h")      # waagrechtes Maß: senkrechte Kante legt x fest
    assert not ohne_kante((275.0, 250.0), seite, [], richtung="v")      # Eckpunkt



def test_hilfslinie_beginnt_am_kreis_bezug_ist_die_mitte():
    """Live 19.11.: Bei Bohrungen beginnt die Hilfslinie außen am Kreis (Mitte 240,0, Anfang 243,5 → Bezugspunkt 242,5).
    Ein Kreismittelpunkt auf der Achse der Hilfslinie, höchstens Radius + Lücke entfernt, ist der Bezug."""
    bohrung = [((131.0, 240.0), 1.5)]
    assert not ohne_kante((131.0, 242.5), [], bohrung, richtung="h")
    assert ohne_kante((133.0, 242.5), [], bohrung, richtung="h")    # neben der Achse
    assert ohne_kante((131.0, 246.0), [], bohrung, richtung="h")    # zu weit weg
