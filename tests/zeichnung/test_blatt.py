"""Zeichnungsableitung Z1.3 Stufe 1 (Plan 2026-11-17 Task 2): Format und Vorzugsmaßstab (R-Kap. 2)."""

from swki.zeichnung.blatt import FORMATE, MASSSTAEBE, SCHRIFTFELD_MM, passt, waehle, zeichenfeld


def test_formate_und_massstaebe():
    assert FORMATE == {"A4": (210, 297), "A3quer": (420, 297)}
    assert (1, 1) in MASSSTAEBE and (5, 1) in MASSSTAEBE and (1, 20) in MASSSTAEBE
    assert SCHRIFTFELD_MM == (180, 55)


def test_zeichenfeld_raender():
    assert zeichenfeld("A4") == (20, 10, 200, 287)  # links 20 mm, sonst 10 mm (ISO 5457)


def test_passt_ueber_oder_neben_schriftfeld():
    assert passt((180, 222), "A4")          # über dem Schriftfeld volle Breite
    assert not passt((181, 222), "A4")
    assert passt((200, 277), "A3quer")      # links neben dem Schriftfeld volle Höhe (390 − 180 = 210)
    assert not passt((211, 230), "A3quer")


def test_mittleres_teil_a4_1zu1():
    assert waehle((150, 100)) == ("A4", (1, 1))


def test_lange_welle_a3_1zu2():
    assert waehle((420, 60)) == ("A3quer", (1, 2))


def test_kleiner_stift_vergroessert():
    assert waehle((30, 25))[0] == "A4" and waehle((30, 25))[1] in ((2, 1), (5, 1))


def test_grosses_teil_1zu10():
    assert waehle((2000, 1500))[1] == (1, 10)
