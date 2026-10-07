"""Handler "extrusion" (Aufsatz) und "schnitt" (verifiziert in Spike S9a, Bausteine 6 und 7; Endbedingungen
bis_flaeche und versatz_von_flaeche in Spike S10, Frage 6).

Aufsatz wächst standardmäßig in Richtung der Skizzennormale, Schnitt standardmäßig dagegen
(von einer Deckfläche also ins Material). "umkehren" dreht die Richtung (3. Parameter Dir, nicht Flip).
Die Zielfläche von bis_flaeche/versatz_von_flaeche wird über den Flächenanker aufgelöst und mit Marke 1 zur Skizze
gewählt; der Versatz geht zur Skizze hin (z. B. Restwandstärke über der Zielfläche).

Bekannte Einschränkung: Ein Aufsatz mit versatz_von_flaeche, dessen Skizze abgesetzt über der Zielfläche liegt, ergibt
einen getrennten Körper. Der Bau meldet das nicht; die allgemeine Code-Prüfung "koerper" (swki.pruefung.bewertung)
meldet es als Mangel ("2 Volumenkörper statt 1").

Formschräge (Paket Formschräge, Spike S16): Dchk1/Ddir1/Dang1 (Index 7, 9, 11 bei beiden Aufrufen); querschnitt
"kleiner"/"groesser" aus Sicht der Skizze (swki.formschraege), der Winkel per Gleichung an WINKEL_MASS[ende] gebunden.
"""

from swki.compiler import sw
from swki.compiler.fehler import FEATURE_NICHT_ERZEUGT, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import richtung, skizziere
from swki.compiler.topologie import loese_flaeche
from swki.formschraege import schraege

ENDE = {"blind": 0, "durch_alles": 1, "bis_flaeche": 4, "versatz_von_flaeche": 5, "mittig": 6}  # swEndConditions_e
MARKE_ZIELFLAECHE = 1  # Endbedingungs-Referenz (Spike S10, Frage 6)
VERSATZ_WEG_VON_SKIZZE = False  # OffsetReverse1: False = Versatz zur Skizze hin (Spike S10, Frage 6)
VERSATZ_MASS = "D1"  # Maß des Versatzes am Feature (Spike S10, Frage 6)
# Ddir1 für querschnitt "kleiner": False bei Aufsatz und Schnitt, unabhängig von umkehren (Spike S16, Frage 1 – True baut
# den Querschnitt "groesser", entgegen der API-Beschreibung "inward")
DDIR_KLEINER = {"extrusion": False, "schnitt": False}
# Maß des Formschrägenwinkels am Feature je Endbedingung: bei allen D3 (Spike S16, Frage 4; D2 gibt es nicht)
WINKEL_MASS = {"blind": "D3", "mittig": "D3", "versatz_von_flaeche": "D3", "durch_alles": "D3", "bis_flaeche": "D3"}
OHNE_SCHRAEGE = (False, False, 0.0)  # (Dchk1, Ddir1, Dang1 in rad)


def aufsatz(model, typ: int, tiefe_m: float, umkehren: bool, schraege_sw: tuple = OHNE_SCHRAEGE):
    dchk, ddir, dang = schraege_sw
    return model.FeatureManager.FeatureExtrusion3(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, dchk, False, ddir, False, dang, 0.0,
        VERSATZ_WEG_VON_SKIZZE, False, False, False, True, True, True, 0, 0.0, False,
    )


def schnitt(model, typ: int, tiefe_m: float, umkehren: bool, schraege_sw: tuple = OHNE_SCHRAEGE):
    dchk, ddir, dang = schraege_sw
    return model.FeatureManager.FeatureCut4(
        True, False, umkehren, typ, 0, tiefe_m, 0.0, dchk, False, ddir, False, dang, 0.0,
        VERSATZ_WEG_VON_SKIZZE, False, False, False, False, True, True, True, True, False, 0, 0.0, False, False,
    )


def schraege_sw(ctx, f: dict) -> tuple:
    """(Dchk1, Ddir1, Dang1) eines extrusion-/schnitt-Knotens; ohne formschraege OHNE_SCHRAEGE."""
    s = schraege(f)
    if s is None:
        return OHNE_SCHRAEGE
    kleiner = s["querschnitt"] == "kleiner"
    return True, DDIR_KLEINER[f["typ"]] == kleiner, ctx.rad(s["winkel"])


@handler("extrusion", "schnitt")
def extrusion(ctx, f: dict) -> FeatureErgebnis:
    skizze, se = skizziere(ctx, f["skizze"]["ebene"], f["skizze"]["elemente"], f"{f['id']}_skizze")
    ende = f["ende"]
    typ = ENDE[ende["typ"]]
    mass = ende.get("tiefe", ende.get("abstand"))  # blind/mittig: Tiefe; versatz_von_flaeche: Versatz
    tiefe = ctx.m(mass) if mass is not None else 0.0
    ziel = loese_flaeche(ctx, ende["flaeche"]) if "flaeche" in ende else None
    umkehren = bool(ende.get("umkehren", False))
    sw.auswahl_leeren(ctx.model)
    skizze.Select2(False, 0)
    if ziel is not None:
        sw.waehle(ctx.model, ziel.objekt, MARKE_ZIELFLAECHE, anhaengen=True)
    ist_schnitt = f["typ"] == "schnitt"
    schraege_f = schraege_sw(ctx, f)
    feature = (schnitt if ist_schnitt else aufsatz)(ctx.model, typ, tiefe, umkehren, schraege_f)
    if feature is None:
        grund = " (trifft der Schnitt Material? ggf. umkehren)" if ist_schnitt else ""
        if schraege_f[0]:
            grund += " (Formschräge zu groß für das Profil?)"
        raise BauFehler(FEATURE_NICHT_ERZEUGT, f"{f['typ']} {f['id']} nicht erzeugt{grund}", schritt="feature")
    feature.Name = f["id"]
    if "tiefe" in ende:
        ctx.verknuepfe(f"D1@{f['id']}", ende["tiefe"])
    if "abstand" in ende:
        ctx.verknuepfe(f"{VERSATZ_MASS}@{f['id']}", ende["abstand"])
    if "formschraege" in ende:
        ctx.verknuepfe(f"{WINKEL_MASS[ende['typ']]}@{f['id']}", schraege(f)["winkel"])
    return FeatureErgebnis([feature], richtung=richtung(se, umkehren != ist_schnitt))
