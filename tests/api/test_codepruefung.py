from swki.api.codepruefung import finde_api_namen, pruefe

QUELLE = """
fm = model.FeatureManager
f = fm.FeatureExtrusion3(True)
g = fm.FeatureExtrusion4(True)
x = daten.lower()
"""


def test_finde_api_namen():
    namen = finde_api_namen(QUELLE)
    assert ("FeatureExtrusion4", 4) in namen
    assert ("FeatureManager", 2) in namen
    assert not any(n == "lower" for n, _ in namen)


def test_pruefe_meldet_zu_neue(tmp_path):
    datei = tmp_path / "handler.py"
    datei.write_text(QUELLE, encoding="utf-8")
    befunde = pruefe([datei], {"FeatureExtrusion3": 2014, "FeatureExtrusion4": 2026}, 2025)
    assert befunde == [{"datei": str(datei), "zeile": 4, "name": "FeatureExtrusion4", "seit": 2026}]


def test_pruefe_ordner_rekursiv(tmp_path):
    (tmp_path / "unter").mkdir()
    (tmp_path / "unter" / "a.py").write_text(QUELLE, encoding="utf-8")
    assert len(pruefe([tmp_path], {"FeatureExtrusion4": 2026}, 2025)) == 1
