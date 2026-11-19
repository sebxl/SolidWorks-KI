"""Zeichnungsableitung Z1.3 Stufe 2, Nachtrag (Nutzer 18.11.2026): Lesbarkeit am PDF prüfen – Text auf Text, Linie
durch Text. Testfälle nach den Bildern des Nutzers: „20,00“ auf der Schnittkennzeichnung „A“, Maßzahl von einer Hilfslinie
gekreuzt; Gegenprobe: Maßzahl über ihrer eigenen Maßlinie."""

import pytest

pymupdf = pytest.importorskip("pymupdf")

from swki.zeichnung.lesbarkeit import pruefe_pdf, texte  # noqa: E402

MM = 72 / 25.4  # Punkte je mm
A3 = (420, 297)


def _pdf(tmp_path, zeichne):
    doc = pymupdf.open()
    seite = doc.new_page(width=A3[0] * MM, height=A3[1] * MM)
    zeichne(seite)
    pfad = tmp_path / "z.pdf"
    doc.save(pfad)
    return pfad


def _text(seite, x_mm, y_mm, text, groesse_mm=3.5):
    """Grundlinie bei (x, y) in Blatt-mm (Ursprung links unten)."""
    seite.insert_text((x_mm * MM, (A3[1] - y_mm) * MM), text, fontsize=groesse_mm * MM * 1.4)


def _linie(seite, a, b):
    seite.draw_line(((a[0]) * MM, (A3[1] - a[1]) * MM), ((b[0]) * MM, (A3[1] - b[1]) * MM), width=0.25 * MM)


def test_text_auf_text(tmp_path):
    pdf = _pdf(tmp_path, lambda s: (_text(s, 100, 200, "20,00"), _text(s, 103, 201, "A", 7)))
    befunde = pruefe_pdf(pdf)
    assert any(b.art == "text_ueber_text" and {b.text, b.anderes} == {"20,00", "A"} for b in befunde)


def test_linie_durch_text(tmp_path):
    pdf = _pdf(tmp_path, lambda s: (_text(s, 100, 100, "27,00"), _linie(s, (102, 95), (102, 110))))
    befunde = pruefe_pdf(pdf)
    assert [(b.art, b.text) for b in befunde] == [("linie_durch_text", "27,00")]


def test_eigene_masslinie_unter_der_zahl_ist_kein_befund(tmp_path):
    pdf = _pdf(tmp_path, lambda s: (_text(s, 100, 100.8, "60,00"), _linie(s, (90, 100), (130, 100))))
    assert pruefe_pdf(pdf) == []


def test_bereich_schliesst_schriftfeld_aus(tmp_path):
    pdf = _pdf(tmp_path, lambda s: (_text(s, 300, 20, "ZEICHNUNGSNR."), _linie(s, (305, 15), (305, 30))))
    assert pruefe_pdf(pdf, ausschluss_mm=[(230, 10, 410, 65)]) == []


def test_befund_traegt_lage_in_blatt_mm(tmp_path):
    pdf = _pdf(tmp_path, lambda s: (_text(s, 100, 100, "27,00"), _linie(s, (102, 95), (102, 110))))
    [b] = pruefe_pdf(pdf)
    x0, y0, x1, y1 = b.rechteck_mm
    assert 99 <= x0 <= 101 and 97.5 <= y0 <= 101 and x1 > x0 and y1 > y0  # y0 mit Unterlänge der Schrift


def test_schraeger_text_an_hinweislinie_ist_kein_befund(tmp_path):
    """Radius-/Durchmesserangabe schräg an ihrer Hinweislinie (R4,00, Ø6,00): das achsparallele Rechteck schließt die
    Linie ein, das ist kein Lesbarkeitsfehler."""
    def zeichne(s):
        s.insert_text((100 * MM, (A3[1] - 100) * MM), "R4,00", fontsize=3.5 * MM * 1.4, rotate=0,
                      morph=(pymupdf.Point(100 * MM, (A3[1] - 100) * MM), pymupdf.Matrix(45)))
        _linie(s, (95, 95), (115, 115))
    assert pruefe_pdf(_pdf(tmp_path, zeichne)) == []


def test_zahl_ausserhalb_des_zeichenfelds_oder_im_schriftfeld():
    """Review 18.11.: pruefe_pdf lässt Rand und Schriftfeld aus – eine dorthin gerückte Maßzahl braucht eigenen Befund."""
    from swki.zeichnung.lesbarkeit import ausserhalb

    feld, schrift = (20, 10, 410, 287), [(230, 10, 410, 65)]
    zahlen = [("innen", 100, 100, 12, "h"), ("rand", 25, 100, 12, "h"), ("oben", 100, 286, 12, "v"),
              ("schriftfeld", 300, 40, 12, "h")]
    assert [b.text for b in ausserhalb(zahlen, feld, schrift)] == ["rand", "oben", "schriftfeld"]


def test_linie_quer_durch_schraegen_text(tmp_path):
    """Nutzer 18.11.2026: „R4,00“ schräg an der Hinweislinie lag auf Kanten der Kabelnut – die Prüfung ließ schräge Texte
    aus. Jetzt: gedrehtes Kernrechteck; nur Linien parallel zur Schrift (eigene Hinweislinie) sind erlaubt."""
    def zeichne(s):
        s.insert_text((100 * MM, (A3[1] - 100) * MM), "R4,00", fontsize=3.5 * MM * 1.4,
                      morph=(pymupdf.Point(100 * MM, (A3[1] - 100) * MM), pymupdf.Matrix(45)))
        _linie(s, (95, 95), (115, 115))      # eigene Hinweislinie entlang der Schrift
        _linie(s, (98, 108), (112, 94))      # Kante quer durch die Schrift
    befunde = pruefe_pdf(_pdf(tmp_path, zeichne))
    assert [(b.art, b.text) for b in befunde] == [("linie_durch_text", "R4,00")]


def test_texte_mit_rechteck_in_blatt_mm(tmp_path):
    """Stufe 3: Hinweise werden am PDF vermessen – Zeile und Rechteck (Ursprung links unten)."""
    pdf = _pdf(tmp_path, lambda s: _text(s, 100, 200, "Senkung Ø6 × 90°"))  # Grundschrift ohne „–“
    (t, r), = [x for x in texte(pdf) if "Senkung" in x[0]]
    assert t == "Senkung Ø6 × 90°"
    assert r[0] == pytest.approx(100, abs=0.5) and r[1] < 200 < r[3] and r[2] > r[0] + 20
