"""Gültige Beispiel-Spezifikation für Tests (selbst formuliert)."""

GUELTIG = {
    "art": "teil",
    "name": "Platte_1",
    "material": "1.2312",
    "eigenschaften": {"Benennung": "Platte"},
    "parameter": {"L": 100, "B": 60, "H": 20},
    "features": [
        {
            "id": "f1", "typ": "extrusion",
            "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
            "ende": {"typ": "blind", "tiefe": "=H"},
        },
        {
            "id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"},
            "positionen": [["=L/2-10", 0], ["=-L/2+10", 0]], "durchmesser": 8, "durch": True,
        },
        {"id": "f3", "typ": "verrundung", "kanten": [{"feature": "f1", "auswahl": "senkrechte_kanten"}], "radius": 3},
        {"id": "f4", "typ": "fase", "kanten": [{"nahe": [50, 20, 0]}], "abstand": 1},
        {"id": "f5", "typ": "muster_linear", "features": ["f2"],
         "richtung1": {"achse": "z", "abstand": 20, "anzahl": 2}},
        {"id": "f6", "typ": "spiegeln", "features": ["f5"], "ebene": "vorne"},
    ],
    "pruefung": {
        "huellquader": ["=L", "=H", "=B"],
        "volumen": {"soll": "auto", "toleranz_prozent": 0.5},
        "masse_pruefen": [
            {"was": "Abstand Bohrungen", "von": {"feature": "f2", "instanz": 1, "achse": True},
             "zu": {"feature": "f2", "instanz": 2, "achse": True}, "soll": 80, "tol": 0.01},
        ],
        "schwerpunkt": {"soll": [0, None, 0], "tol": 0.05},
    },
}
