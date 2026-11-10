"""werkzeuge.schnellbau_abgleich: Ein vorhandener Auftragsordner SBREF-<ordner> wird mit den aktuellen Referenz-Specs
überschrieben, damit SolidWorks und Schnellbau nicht mit einer veralteten Kopie laufen (Befund C3a: Stehlager ohne Fasen)."""

from werkzeuge.schnellbau_abgleich import auftrag_aktualisieren


def test_vorhandener_auftrag_bekommt_aktuelle_specs(tmp_path):
    quelle = tmp_path / "referenz" / "stehlager"
    (quelle / "eingabe").mkdir(parents=True)
    (quelle / "grundplatte.yaml").write_text("neu", encoding="utf-8")
    (quelle / "eingabe" / "skizze.txt").write_text("neu", encoding="utf-8")
    auftrag = tmp_path / "SBREF-stehlager"
    (auftrag / "protokolle").mkdir(parents=True)
    (auftrag / "grundplatte.yaml").write_text("alt", encoding="utf-8")
    (auftrag / "protokolle" / "lauf-1.json").write_text("{}", encoding="utf-8")

    auftrag_aktualisieren(quelle, auftrag)

    assert (auftrag / "grundplatte.yaml").read_text(encoding="utf-8") == "neu"
    assert (auftrag / "eingabe" / "skizze.txt").read_text(encoding="utf-8") == "neu"
    assert (auftrag / "protokolle" / "lauf-1.json").exists()   # frühere Läufe bleiben


def test_neuer_auftrag_wird_angelegt(tmp_path):
    quelle = tmp_path / "referenz" / "stil"
    quelle.mkdir(parents=True)
    (quelle / "spannplatte.yaml").write_text("x", encoding="utf-8")
    auftrag = tmp_path / "SBREF-stil"

    auftrag_aktualisieren(quelle, auftrag)

    assert (auftrag / "spannplatte.yaml").read_text(encoding="utf-8") == "x"
