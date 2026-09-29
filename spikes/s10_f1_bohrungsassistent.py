"""S10 Frage 1: HoleWizard5 für die vier Arten (ISO) – Größen-Strings, Endbedingung durch/blind, Gewindetiefe.

Prüfblock 60 × 60 × 30 (Y 0…30), Bohrung von der Deckfläche bei (X 0, Z 0), je Fall ein neues Teil.
a) Größen-Strings: je Größe werden Schreibweisen probiert (blind 20, Gewinde 12); die erste mit fehlerfreiem Feature und
   Volumenabnahme ist der „gewinner“ (Frage 2–4 und bohrungsnormen.yaml verwenden ihn).
b) Endbedingungen: blind/durch je Art, Gewinde blind mit Gewindetiefe, durch mit durchgehendem bzw. begrenztem Gewinde.
Soll Gewinde M8 blind 16 (S9b Baustein 21): 605,80 mm³.
"""

from spikes._gemeinsam import lauf
from spikes.s9a_gemeinsam import feature_masse, kasten_oben, start, teil, volumen_mm3
from spikes.s9b_gemeinsam import whatswrong
from spikes.s10_gemeinsam import DICKE_MM, bohrung, daten, geometrie, unterfeatures

SCHREIBWEISEN = {
    "gewinde": {
        **{f"M{d}": [f"M{d}"] for d in (5, 6, 8, 10, 12, 16)},
        **{f"M{d}x{p:g}": [f"M{d}x{p:g}", f"M{d}x{p:.1f}", f"M{d} x {p:.1f}", f"M{d}x{p:.2f}"]
           for d, p in ((8, 1), (10, 1), (12, 1.5), (16, 1.5))},
    },
    "zylinderschraube": {f"M{d}": [f"M{d}"] for d in (5, 6, 8, 10, 12)},
    "senkschraube": {f"M{d}": [f"M{d}"] for d in (5, 6, 8, 10)},
    "stift": {f"{d}": [f"{d}", f"D{d}", f"Ø{d}.0", f"Ø{d}", f"{d}.0", f"{d} mm"] for d in (4, 5, 6, 8, 10, 12)},
}


def fall(app, r, art, groesse, **kw) -> dict:
    with teil(app, r) as model:
        kasten_oben(model, 60, 60, DICKE_MM)
        v0 = volumen_mm3(model)
        try:
            treffer, f = bohrung(model, art, groesse, [(0.0, 0.0)], **kw)
        except Exception as e:  # Spike: alles protokollieren
            return {"fehler": repr(e)}
        out = {"selectbyray": treffer, "feature": f.Name if f else None, "typ": f.GetTypeName2 if f else None,
               "abnahme_mm3": round(v0 - volumen_mm3(model), 3), "whatswrong": whatswrong(model)}
        if f:
            out.update(unterfeatures=unterfeatures(f), geometrie=geometrie(f), masse=feature_masse(f), daten=daten(f))
        return out


def gelungen(e: dict) -> bool:
    return bool(e.get("feature")) and e.get("abnahme_mm3", 0) > 0 and e.get("whatswrong", {}).get("anzahl", 1) == 0


def pruefen() -> dict:
    r, app = start()
    d: dict = {"gewinner": {}, "groessen": {}, "enden": {}}
    for art, groessen in SCHREIBWEISEN.items():
        for groesse, kandidaten in groessen.items():
            versuche = {}
            for text in kandidaten:
                # Erkennung blind (HoleWizard5 gibt bei ungültiger Größe still None zurück); der CreateDefinition-Weg
                # (Stift durch) bekäme bei ungültigem Text womöglich einen Dialog und hängt – darum nur mit bekanntem Text.
                versuche[text] = fall(app, r, art, text, tiefe_mm=20, gewindetiefe_mm=12 if art == "gewinde" else None)
                if gelungen(versuche[text]):
                    d["gewinner"].setdefault(art, {})[groesse] = text
                    break
            d["groessen"][f"{art} {groesse}"] = versuche
    faelle = {
        "gewinde M8 blind 16, Gewinde 12 (Soll 605,80)": ("gewinde", "M8", {"tiefe_mm": 16, "gewindetiefe_mm": 12}),
        "gewinde M8 durch, Gewinde durch": ("gewinde", "M8", {}),
        "gewinde M8 durch, Gewinde 12": ("gewinde", "M8", {"gewindetiefe_mm": 12}),
        "zylinderschraube M8 blind 20": ("zylinderschraube", "M8", {"tiefe_mm": 20}),
        "zylinderschraube M8 durch": ("zylinderschraube", "M8", {}),
        "senkschraube M6 blind 20": ("senkschraube", "M6", {"tiefe_mm": 20}),
        "senkschraube M6 durch": ("senkschraube", "M6", {}),
    }
    stift8 = d["gewinner"].get("stift", {}).get("8")
    if stift8:
        faelle |= {"stift 8 blind 20": ("stift", stift8, {"tiefe_mm": 20}), "stift 8 durch": ("stift", stift8, {})}
    for name, (art, groesse, kw) in faelle.items():
        d["enden"][name] = fall(app, r, art, groesse, **kw)
        d["enden"][name]["gelungen"] = gelungen(d["enden"][name])
    return d


if __name__ == "__main__":
    lauf("s10_f1_bohrungsassistent", pruefen)
