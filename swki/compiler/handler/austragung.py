"""Handler "austragung" – Profil entlang eines offenen Pfads als Aufsatz oder Schnitt (Paket Konstruktionsstil, Spike S20 e).

Profilskizze <id>_skizze und Pfadskizze <id>_pfad sind voll bestimmt (Maße zum Ursprung, Maßprotokoll); die Lage von
Profil und Pfad zueinander prüft swki validieren (swki.spec.austragung).
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import skizziere

PROFIL_MARKE, PFAD_MARKE = 1, 4  # Auswahlmarken von InsertProtrusionSwept4/InsertCutSwept5 (Spike S20 e)


@handler("austragung")
def austragung(ctx, f: dict) -> FeatureErgebnis:
    pfad = ctx.pfad(f["id"])
    profil, _ = skizziere(ctx, f["profil"]["ebene"], f["profil"]["elemente"], f"{f['id']}_skizze",
                          [f"{pfad}.profil.elemente[0]"], ebene_pfad=f"{pfad}.profil.ebene")
    linienzug = {"pfad": {"start": f["pfad"]["start"], "segmente": f["pfad"]["segmente"]}}
    weg, _ = skizziere(ctx, f["pfad"]["ebene"], [linienzug], f"{f['id']}_pfad",
                       [{"start": f"{pfad}.pfad.start", "segmente": f"{pfad}.pfad.segmente"}],
                       ebene_pfad=f"{pfad}.pfad.ebene")
    sw.auswahl_leeren(ctx.model)
    profil.Select2(False, PROFIL_MARKE)
    weg.Select2(True, PFAD_MARKE)
    fm = ctx.model.FeatureManager
    # Werte wie in Spike S20 e: ohne Verdrehung, Tangentenanschluss, Dünnwand und Kreisprofil; Merge/Bereich wahr
    if f.get("schnitt"):
        feature = fm.InsertCutSwept5(False, False, 0, False, False, 0, 0, False, 0.0, 0.0, 0, 0, True, True, 0.0, True,
                                     False, False, False, False, 0.0, 0)
    else:
        feature = fm.InsertProtrusionSwept4(False, False, 0, False, False, 0, 0, False, 0.0, 0.0, 0, 0, True, True,
                                            True, 0.0, True, False, 0.0, 0)
    sw.auswahl_leeren(ctx.model)
    if feature is None:
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"austragung {f['id']} nicht erzeugt", schritt="feature")
    feature.Name = f["id"]
    return FeatureErgebnis([feature])
