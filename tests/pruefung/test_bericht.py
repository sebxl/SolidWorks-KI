from swki.pruefung.bericht import bericht_markdown

LAEUFE = [
    {"lauf": 1, "bau": "fehler", "code_maengel": None, "pruefer": "ausstehend", "offen": 1, "dauer_s": 8.1},
    {"lauf": 2, "bau": "ok", "code_maengel": 0, "pruefer": "bestanden", "offen": 0, "dauer_s": 9.4},
]


def test_bestandener_auftrag():
    md = bericht_markdown(
        {"name": "Platte"}, "A-1", LAEUFE, ("bestanden", "Lauf 2 bestanden: Bericht schreiben"),
        {"maengel": [], "bilder": {"iso": "C:/arbeit/A-1/lauf-2/iso.png"}}, {"bestanden": True, "maengel": []},
        {"phasen": {"bauen": 6.2, "speichern": 1.1}, "fehler": None},
        ["abc1234 compiler: fase mit Tangentenfortsetzung"],
    )
    assert md.startswith("# Bericht Platte (Auftrag A-1)\n")
    assert "**Status:** bestanden" in md
    assert "| 1 | fehler | – | ausstehend | 1 | 8.1 |" in md
    assert "- iso: `C:/arbeit/A-1/lauf-2/iso.png`" in md
    assert "| bauen | 6.2 |" in md
    assert "- abc1234 compiler: fase mit Tangentenfortsetzung" in md
    assert "## Offene Punkte (letzter Lauf)\n\n- keine" in md


def test_offene_punkte_mit_knoten():
    md = bericht_markdown(
        {"name": "Platte"}, "A-1", LAEUFE[:1], ("stopp_max", "…"),
        {"maengel": [{"knoten": ["f2"], "beschreibung": "mass:Abstand: ist 81 statt 80"}]},
        {"bestanden": False, "maengel": [{"knoten": [], "beschreibung": "Fase fehlt oben"}]},
        {"phasen": {}, "fehler": {"code": "REFERENZ_MEHRDEUTIG", "meldung": "2 Kanten"}},
        [],
    )
    assert "**Status:** offen (stopp_max)" in md
    assert "- Bau abgebrochen: REFERENZ_MEHRDEUTIG – 2 Kanten" in md
    assert "- f2: mass:Abstand: ist 81 statt 80" in md
    assert "- Teil: Fase fehlt oben (Prüfer)" in md
    assert "## Compiler-Änderungen während des Auftrags\n\n- keine" in md


def test_feature_baum():
    md = bericht_markdown(
        {"name": "Platte"}, "A-1", LAEUFE, ("bestanden", "Lauf 2 bestanden"),
        {"maengel": [], "bilder": {}, "baum": {"knoten": 10, "features": 10}}, None, None, [],
    )
    assert ("## Feature-Baum (letzter Lauf)\n\n- Knoten der Spezifikation: 10\n"
            "- erzeugte Features (ohne Skizzen, Ebenen, Achsen): 10") in md
