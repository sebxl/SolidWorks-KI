"""Trichter als dünnwandige Ausformung (Loft) zwischen Öffnung oben und Auslauf unten.

Notausgang: Das Spezifikationsformat kennt keine Ausformung. Beide Profile sind voll bestimmte Skizzen wie in der
Spezifikation (Parameter aus trichter.yaml); die Profile werden mit Marke 1 an derselben Ecke (−X/−Y) gewählt, damit die
Ausformung nicht verdreht. Wandstärke T_W als Dünnwand-Feature nach außen (IFeatureManager.InsertProtrusionBlend2,
18 Parameter; swThinWallType_e 0 = eine Richtung, 1 = Gegenrichtung).
"""

DUENN_TYP = 0  # Richtung der Wand: nach außen (im Lauf am Hüllquader geprüft)
MARKE_PROFIL = 1
SKIZZE = "SKETCH"

NEIGUNG = "(S_OY-S_UY171)/(S_OZ-Z171)"  # dY/dZ der Schachtachse (wie fallschacht.yaml)
AUSLAUF_TIEFE = f"=SB*(1+({NEIGUNG})**2)**0.5"  # waagerechte Weite des Auslaufs in Y


def _waehle_profil(ctx, skizze, x_mm, y_mm, z_mm, anhaengen):
    ok = ctx.model.Extension.SelectByID2(skizze.Name, SKIZZE, x_mm / 1000, y_mm / 1000, z_mm / 1000, anhaengen,
                                         MARKE_PROFIL, ctx.callout_leer(), 0)
    if not ok:
        raise RuntimeError(f"Profil {skizze.Name} nicht wählbar")


def bauen(ctx):
    oben, _ = ctx.skizze({"versatz": {"ebene": "oben", "abstand": "=T_OK"}}, [{"rechteck": {
        "mitte": ["=(T_X0+T_X1)/2", "=(T_Y0+T_Y1)/2"], "breite": "=T_X1-T_X0", "hoehe": "=T_Y1-T_Y0",
        "radius": "=T_R"}}], "oben")
    unten, _ = ctx.skizze({"versatz": {"ebene": "oben", "abstand": "=S_OZ"}}, [{"rechteck": {
        "mitte": ["=KX", "=S_OY"], "breite": "=SB", "hoehe": AUSLAUF_TIEFE, "radius": "=A_R"}}], "unten")
    # Punkte auf der Kante Y min nahe der Ecke −X (Modell: x = X, y = Z, z = −Y)
    x_oben, y_oben = ctx.wert("=T_X0+T_R+1"), ctx.wert("=T_Y0")
    x_unten = ctx.wert("=KX-SB/2+A_R+0.5")
    y_unten = ctx.wert("=S_OY") - ctx.wert(AUSLAUF_TIEFE) / 2
    ctx.auswahl_leeren()
    _waehle_profil(ctx, oben, x_oben, ctx.wert("=T_OK"), -y_oben, False)
    _waehle_profil(ctx, unten, x_unten, ctx.wert("=S_OZ"), -y_unten, True)
    feature = ctx.model.FeatureManager.InsertProtrusionBlend2(
        False, False, False, 1.0, 0, 0, 1.0, 1.0, True, True,  # offen, ohne Tangentenbedingungen
        True, ctx.m("=T_W"), 0.0, DUENN_TYP,                 # Dünnwand T_W
        True, False, True, 0,                                # verschmelzen, alle Körper
    )
    ctx.auswahl_leeren()
    return feature
