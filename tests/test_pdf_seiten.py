"""werkzeuge.pdf_seiten ohne SolidWorks: Seitentext, Seitenbild und Ausschnitt aus einer selbst erzeugten Test-PDF."""

import pytest

from werkzeuge import pdf_seiten

PNG_SIGNATUR = b"\x89PNG\r\n\x1a\n"


def test_seitenliste():
    assert pdf_seiten.seitenliste(None, 4) == [1, 2, 3, 4]
    assert pdf_seiten.seitenliste("3,1-2", 4) == [3, 1, 2]
    assert pdf_seiten.seitenliste("2-", 4) == [2, 3, 4]


@pytest.mark.parametrize("angabe", ["0", "5", "3-2", "a"])
def test_seitenliste_ungueltig(angabe):
    with pytest.raises(ValueError, match="Seite"):
        pdf_seiten.seitenliste(angabe, 4)


def test_hilfe_nennt_modi(capsys):
    with pytest.raises(SystemExit):
        pdf_seiten.main(["--help"])
    hilfe = capsys.readouterr().out
    for modus in ("text", "seite", "ausschnitt"):
        assert modus in hilfe


@pytest.fixture
def test_pdf(tmp_path):
    """Zwei Seiten 300 × 420 pt; Seite 2 hat ein schwarzes Rechteck im linken oberen Viertel."""
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    s1 = doc.new_page(width=300, height=420)
    s1.insert_text((40, 60), "Hub 25 mm", fontsize=14)
    s2 = doc.new_page(width=300, height=420)
    s2.insert_text((40, 300), "Kolben-Ø 16", fontsize=14)
    s2.draw_rect(pymupdf.Rect(0, 0, 150, 210), color=(0, 0, 0), fill=(0, 0, 0))
    p = tmp_path / "datenblatt.pdf"
    doc.save(p)
    doc.close()
    return p


def png_groesse(p):
    d = p.read_bytes()
    assert d[:8] == PNG_SIGNATUR
    return int.from_bytes(d[16:20], "big"), int.from_bytes(d[20:24], "big")


def test_text_je_seite(test_pdf):
    seiten = pdf_seiten.seitentext(test_pdf)
    assert [n for n, _ in seiten] == [1, 2]
    assert "Hub 25 mm" in seiten[0][1]
    assert "Kolben-Ø 16" in seiten[1][1]
    assert pdf_seiten.seitentext(test_pdf, "2")[0][0] == 2


def test_text_cli(test_pdf, capsys):
    assert pdf_seiten.main(["text", str(test_pdf), "--seiten", "1"]) == 0
    aus = capsys.readouterr().out
    assert "Seite 1" in aus and "Hub 25 mm" in aus and "Kolben" not in aus


def test_seitenbild_png_mit_aufloesung(test_pdf, tmp_path):
    ordner = tmp_path / "bilder"
    pfade = pdf_seiten.seitenbilder(test_pdf, ordner, seiten="1-2", dpi=72)
    assert [p.name for p in pfade] == ["datenblatt_s1.png", "datenblatt_s2.png"]
    assert png_groesse(pfade[0]) == (300, 420)
    assert png_groesse(pdf_seiten.seitenbilder(test_pdf, ordner, seiten="1", dpi=144)[0]) == (600, 840)


def test_ausschnitt_trifft_bereich(test_pdf, tmp_path):
    import pymupdf

    p = pdf_seiten.ausschnitt(test_pdf, 2, (0, 0, 50, 50), tmp_path, dpi=72)
    assert p.name == "datenblatt_s2_x0-50_y0-50.png"
    assert png_groesse(p) == (150, 210)
    pix = pymupdf.Pixmap(str(p))
    assert pix.pixel(pix.width // 2, pix.height // 2)[:3] == (0, 0, 0)
    rechts = pdf_seiten.ausschnitt(test_pdf, 2, (60, 0, 100, 40), tmp_path, dpi=72)
    pix = pymupdf.Pixmap(str(rechts))
    assert pix.pixel(pix.width // 2, pix.height // 2)[:3] == (255, 255, 255)


def test_ausschnitt_ungueltiges_rechteck(test_pdf, tmp_path):
    with pytest.raises(ValueError, match="Rechteck"):
        pdf_seiten.ausschnitt(test_pdf, 1, (50, 0, 40, 100), tmp_path)


def test_seite_und_ausschnitt_cli(test_pdf, tmp_path, capsys):
    ordner = tmp_path / "aus"
    assert pdf_seiten.main(["seite", str(test_pdf), str(ordner), "--seiten", "2", "--dpi", "72"]) == 0
    assert pdf_seiten.main(["ausschnitt", str(test_pdf), str(ordner), "--seite", "1",
                            "--rechteck", "0", "0", "100", "20"]) == 0
    aus = capsys.readouterr().out
    assert (ordner / "datenblatt_s2.png").exists() and "datenblatt_s2.png" in aus
    assert png_groesse(ordner / "datenblatt_s1_x0-100_y0-20.png") == (1250, 350)


def test_ohne_pymupdf_nennt_installation(monkeypatch, tmp_path):
    monkeypatch.setitem(__import__("sys").modules, "pymupdf", None)
    with pytest.raises(SystemExit, match=r"pip install -e \"\.\[pdf\]\""):
        pdf_seiten.seitentext(tmp_path / "fehlt.pdf")
