"""Korrekturrunde 3 zum Vergleich der Baugruppe (Task 5): mehrere `verknuepfung_wert`-Punkte an derselben Verknüpfung, je mit eigener
Konfiguration, geben sich ihre Konfigurationen gegenseitig frei."""

import copy

from tests.bestand.beispiel_baugruppe import baugruppen_aufnahme
from tests.bestand.test_vergleich_baugruppe import hinweise, punkt, setze_wert, spec_aus, vergleich, zwei_konfigurationen


def _bestand_10_20():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    setze_wert(v, "Abstand1", "wert", 20.0, "Variante B")
    return v


def _zwei_punkte(**w2) -> dict:
    return spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Abstand1", alt=10, neu=12, konfigurationen=["Standard"]),
                    punkt("verknuepfung_wert", "w2", verknuepfung="Abstand1", alt=20, neu=25, konfigurationen=["Variante B"], **w2))


def test_k3_zwei_punkte_je_eigene_konfiguration_bestehen():
    v = _bestand_10_20()
    n = copy.deepcopy(v)
    setze_wert(n, "Abstand1", "wert", 12.0, "Standard")
    setze_wert(n, "Abstand1", "wert", 25.0, "Variante B")
    e = vergleich(_zwei_punkte(), n, vorher=v)
    assert e["punkt:w1"]["ok"] is True and e["punkt:w2"]["ok"] is True and e["verknuepfungen"]["ok"] is True, e


def test_k3_ein_punkt_nicht_umgesetzt_bleibt_mangel_nur_an_diesem_punkt():
    v = _bestand_10_20()
    n = copy.deepcopy(v)
    setze_wert(n, "Abstand1", "wert", 12.0, "Standard")  # Variante B steht noch auf 20
    e = vergleich(_zwei_punkte(), n, vorher=v)
    assert e["punkt:w1"]["ok"] is True and e["punkt:w2"]["ok"] is False and e["verknuepfungen"]["ok"] is True


def test_k3_wert_den_kein_punkt_in_dieser_konfiguration_nennt_bleibt_mangel():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    setze_wert(v, "Abstand1", "wert", 20.0, "Variante B")
    for m in v["verknuepfungen"].values():  # eine dritte Konfiguration, die kein Punkt nennt
        m["werte"]["Variante C"] = copy.deepcopy(m["werte"]["Standard"])
    v["konfigurationen"].append("Variante C")
    for k in v["komponenten"].values():
        for feld in ("fixiert", "unterdrueckt", "status", "transform", "konfigurationen"):
            k[feld]["Variante C"] = copy.deepcopy(k[feld]["Standard"])
    for m in v["verknuepfungen"].values():
        for feld in ("fehler", "unterdrueckt"):
            m[feld]["Variante C"] = copy.deepcopy(m[feld]["Standard"])
    n = copy.deepcopy(v)
    setze_wert(n, "Abstand1", "wert", 12.0, "Standard")
    setze_wert(n, "Abstand1", "wert", 25.0, "Variante B")
    assert vergleich(_zwei_punkte(), n, vorher=v)["punkt:w1"]["ok"] is True
    setze_wert(n, "Abstand1", "wert", 99.0, "Variante C")  # niemand nennt Variante C
    e = vergleich(_zwei_punkte(), n, vorher=v)
    assert e["verknuepfungen"]["ok"] is False and "Variante C" in hinweise(e["verknuepfungen"])
    assert e["punkt:w1"]["ok"] is False and e["punkt:w2"]["ok"] is False


def test_k3_ein_punkt_gibt_das_feld_dem_anderen_nicht_in_der_eigenen_konfiguration_frei():
    v = _bestand_10_20()
    n = copy.deepcopy(v)
    setze_wert(n, "Abstand1", "wert", 12.0, "Standard")
    setze_wert(n, "Abstand1", "wert", 25.0, "Variante B")
    setze_wert(n, "Abstand1", "min", 3.0, "Variante B")  # min nennt keiner
    e = vergleich(_zwei_punkte(), n, vorher=v)
    assert e["verknuepfungen"]["ok"] is False and e["punkt:w2"]["ok"] is False


def _grenzen_bestand():
    v = zwei_konfigurationen(baugruppen_aufnahme())
    setze_wert(v, "Grenze_Abstand1", "max", 9.0, "Variante B")
    setze_wert(v, "Grenze_Abstand1", "min", 1.0, "Variante B")
    return v


def _spec_grenzen() -> dict:
    return spec_aus(punkt("verknuepfung_wert", "w1", verknuepfung="Grenze_Abstand1", grenze="max", alt=5, neu=8,
                          konfigurationen=["Standard"]),
                    punkt("verknuepfung_wert", "w2", verknuepfung="Grenze_Abstand1", grenze="min", alt=1, neu=2,
                          konfigurationen=["Variante B"]))


def test_k3_grenze_max_und_min_je_eigene_konfiguration_bestehen():
    v = _grenzen_bestand()
    n = copy.deepcopy(v)
    setze_wert(n, "Grenze_Abstand1", "max", 8.0, "Standard")
    setze_wert(n, "Grenze_Abstand1", "min", 2.0, "Variante B")
    e = vergleich(_spec_grenzen(), n, vorher=v)
    assert e["punkt:w1"]["ok"] is True and e["punkt:w2"]["ok"] is True and e["verknuepfungen"]["ok"] is True, e


def test_k3_grenze_feld_das_in_der_konfiguration_niemand_nennt_bleibt_mangel():
    v = _grenzen_bestand()
    n = copy.deepcopy(v)
    setze_wert(n, "Grenze_Abstand1", "max", 8.0, "Standard")
    setze_wert(n, "Grenze_Abstand1", "min", 2.0, "Variante B")
    setze_wert(n, "Grenze_Abstand1", "max", 7.0, "Variante B")  # w2 nennt nur min
    e = vergleich(_spec_grenzen(), n, vorher=v)
    assert e["verknuepfungen"]["ok"] is False
    assert e["punkt:w2"]["ok"] is False and "max" in hinweise(e["punkt:w2"])
    n2 = copy.deepcopy(v)
    setze_wert(n2, "Grenze_Abstand1", "max", 8.0, "Standard")
    setze_wert(n2, "Grenze_Abstand1", "min", 2.0, "Variante B")
    setze_wert(n2, "Grenze_Abstand1", "min", 0.5, "Standard")  # w1 nennt nur max
    assert vergleich(_spec_grenzen(), n2, vorher=v)["punkt:w1"]["ok"] is False
