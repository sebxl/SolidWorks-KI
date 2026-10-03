"""S12 (Stufe 3b): Baugruppen – Einfügen, Auswahl in Komponenten, Verknüpfungen, Kollision, Rücklesen, Messen.

a Einfügen: AddComponent5 mit dem Boxzentrum des Teils → liegt der Ursprung im Baugruppenursprung (Transform2)? Mit
  Bezugsebenen im Teil (Normteil); SetTransformAndSolve2(Identität); FixComponent (als Methode markiert) → IsFixed.
b Auswahl: IComponent2.FeatureByName(<Bezugsebene>) bzw. GetCorrespondingEntity(<Fläche>) liefern auswählbare Objekte
  (Select2 bzw. Select4, Marke 1).
c Verknüpfungen: AddMate5 für deckungsgleich, konzentrisch, parallel, senkrecht, abstand, winkel; Status
  (swAddMateError_e, 1 = ok); Ausrichtung bei Bezugsebene ↔ Fläche; LockRotation → Status 3 statt 2; Status der
  fixierten Komponente; Mate-Feature umbenennen; IMate2.Type; Maß "D1" und Gleichung "D1@<Name>" = "S"; Ebene + zwei
  konzentrische (überbestimmt?).
d Kollision: TreatCoincidenceAsInterference = False: Stift Ø 8 in Ø 8 → keine Interferenz; Schraube M8 (Nenn-Ø) in
  Gewinde M8 → ein Paar, Volumen gegen das Ring-Soll; nach Speichern und OpenDoc6 dieselben Werte.
e Rücklesen: globale Variablen eines gespeicherten Teils, SHA-256 vor/nach Öffnen und Schließen ohne Speichern.
f Messen: Transform-Konvention (Zeilen- oder Spaltenvektor) über die Normale einer Fläche im Baugruppenkontext;
  GetBox(0) gegen die bekannte Hülle.
g Speicher: Private Bytes notiert der Ausführende vor und nach dem Lauf.

Ergänzungen gegenüber dem Plan (nach dem ersten Lauf, siehe Bericht): Baugruppe 5 (Gegenrichtung: Schraube und Stift mit
umgekehrter Ausrichtung, damit der Kopf auf der Lasche liegt und der Stift im Sockel steckt), Baugruppe 6 (widersprüchliche
Verknüpfung), Bezugsebenen-Lage (IRefPlane.Transform), Bildvektoren über IMathVector.MultiplyTransform.

Aufruf: .venv\\Scripts\\python.exe -m spikes.s12_baugruppe
"""

import hashlib
import math
import shutil
from pathlib import Path

import pythoncom

from spikes._gemeinsam import lauf
from swki.compiler import sw
from swki.compiler.ablauf import baue_features
from swki.compiler.anker import zylinder_zu_punkten
from swki.compiler.eigenschaften import globale_variablen
from swki.compiler.kontext import Kontext
from swki.compiler.protokoll import Protokoll
from swki.compiler.registry import alle_handler
from swki.compiler.topologie import flaechen, loese_flaeche
from swki.konfig import lade_rechner
from swki.normteile import befehle as normteil_befehle
from swki.normteile.erzeugen import erzeuge_spec, vorlage_text
from swki.normteile.schluessel import loese_auf
from swki.pruefung.messen import kontext_aus_datei, oeffne
from swki.verbindung import byref_bool, byref_long, grad, in_mm, in_mm3, mm, r8_array, verbinde

MATE = {"deckungsgleich": 0, "konzentrisch": 1, "senkrecht": 2, "parallel": 3, "abstand": 5, "winkel": 6}  # swMateType_e
GLEICH, ENTGEGEN, NAECHSTE = 0, 1, 2  # swMateAlign_e: ALIGNED, ANTI_ALIGNED, CLOSEST
IDENT = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0]


def _block(name, laenge, breite, hoehe, weitere):
    return {"art": "teil", "name": name, "parameter": {"L": laenge, "B": breite, "H": hoehe}, "features": [
        {"id": "f1", "typ": "extrusion",
         "skizze": {"ebene": "oben", "elemente": [{"rechteck": {"mitte": [0, 0], "breite": "=L", "hoehe": "=B"}}]},
         "ende": {"typ": "blind", "tiefe": "=H"}}, *weitere]}


SOCKEL = _block("S12_Sockel", 100, 60, 20, [
    {"id": "f2", "typ": "normbohrung", "art": "gewinde", "groesse": "M8", "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[0, 0]], "tiefe": 16, "gewindetiefe": 12},
    {"id": "f3", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[30, 0]], "durch": True},
    {"id": "OBEN", "typ": "referenz", "ebene": {"basis": "oben", "abstand": "=H"}},
])
LASCHE = _block("S12_Lasche", 80, 60, 10, [
    {"id": "f2", "typ": "bohrung", "flaeche": {"feature": "f1", "flaeche": "+y"}, "positionen": [[0, 0]],
     "durchmesser": 9, "durch": True},
    {"id": "f3", "typ": "normbohrung", "art": "stift", "groesse": 8, "flaeche": {"feature": "f1", "flaeche": "+y"},
     "positionen": [[30, 0]], "durch": True},
])


def _teil(app, r, spec, ordner):
    model = sw.neues_teil(app, r.vorlage_teil)
    ctx = Kontext(app, model, spec, ordner / f"{spec['name']}.yaml", 0.1)
    globale_variablen(model, spec["parameter"])
    fehler = baue_features(ctx, Protokoll("S12", spec["name"], 0, r.sw_jahr), alle_handler(), lambda c: sw.rebuild(c.model))
    if fehler is not None:
        raise fehler
    sw.speichere(model, ordner / f"{spec['name']}.sldprt")
    return model, ctx


def _normteil(app, norm, groesse, ordner):
    quelle = Path(normteil_befehle.hole(norm, groesse)["pfad"])
    ziel = ordner / quelle.name
    shutil.copy2(quelle, ziel)
    t, a = loese_auf(norm, groesse)
    model = oeffne(app, ziel)
    spec = erzeuge_spec(t, a, vorlage_text(t))
    return model, kontext_aus_datei(app, model, spec, ziel.with_suffix(".yaml"), 0.1, {"knoten": []})


def _neue_baugruppe(app, r):
    asm = app.NewDocument(str(r.vorlage_baugruppe), 0, 0, 0)
    if asm is None:
        raise RuntimeError(f"NewDocument {r.vorlage_baugruppe} fehlgeschlagen")
    return asm


def _einfuegen(app, asm, model, identitaet_setzen=False):
    box = sw.teilebox_mm(model)
    komp = asm.AddComponent5(model.GetPathName, 0, "", False, "", *[mm((box[i] + box[i + 3]) / 2) for i in range(3)])
    nach_einfuegen = [round(x, 9) for x in komp.Transform2.ArrayData]
    if identitaet_setzen:
        komp.SetTransformAndSolve2(sw.mathutil(app).CreateTransform(r8_array(IDENT)))
    return komp, {"box_mm": box, "transform_nach_einfuegen": nach_einfuegen,
                  "transform": [round(x, 9) for x in komp.Transform2.ArrayData]}


def _fixiere(asm, komp):
    asm.ClearSelection2(True)
    komp.Select4(False, asm.SelectionManager.CreateSelectData, False)
    asm._FlagAsMethod("FixComponent")
    asm.FixComponent()
    asm.ClearSelection2(True)
    return bool(komp.IsFixed)


def _entitaet(komp, ctx, seite):
    """(Objekt im Baugruppenkontext, ist_feature) für eine Referenz wie in Spec 3b §4.3."""
    if "referenz" in seite:
        return komp.FeatureByName(ctx.ergebnis(seite["referenz"]).features[0].Name), True
    if "instanz" in seite:
        ergebnis = ctx.ergebnis(seite["feature"])
        [zylinder] = zylinder_zu_punkten(flaechen(ergebnis.features[0]), [ergebnis.punkte[seite["instanz"] - 1]], 0.1)
        return komp.GetCorrespondingEntity(zylinder.objekt), False
    return komp.GetCorrespondingEntity(loese_flaeche(ctx, seite).objekt), False


def _mates(asm):
    f = asm.FirstFeature
    while f is not None and f.GetTypeName2 != "MateGroup":
        f = f.GetNextFeature
    ergebnis, unter = [], (f.GetFirstSubFeature if f is not None else None)
    while unter is not None:
        ergebnis.append(unter)
        unter = unter.GetNextSubFeature
    return ergebnis


def _mate(asm, name, typ, ausrichtung, a, b, sperren=False, wert=0.0):
    asm.ClearSelection2(True)
    auswahl = []
    for (objekt, ist_feature), anhaengen in ((a, False), (b, True)):
        if objekt is None:
            auswahl.append(None)
        elif ist_feature:
            auswahl.append(bool(objekt.Select2(anhaengen, 1)))
        else:
            daten = asm.SelectionManager.CreateSelectData
            daten.Mark = 1
            auswahl.append(bool(objekt.Select4(anhaengen, daten)))
    status = byref_long()
    abstand = mm(wert) if typ == "abstand" else 0.0
    winkel = grad(wert) if typ == "winkel" else 0.0
    mate = asm.AddMate5(MATE[typ], ausrichtung, False, abstand, abstand, abstand, 1, 1, winkel, winkel, winkel, False,
                        sperren, 0, status)
    asm.ClearSelection2(True)
    ergebnis = {"auswahl": auswahl, "mate_none": mate is None, "status": status.value}
    if mate is not None:
        feature = _mates(asm)[-1]
        feature.Name = name
        ergebnis["name_gesetzt"] = feature.Name
        ergebnis["rebuild"] = bool(asm.EditRebuild3)
        ergebnis["fehlercode"] = int(feature.GetErrorCode2(byref_bool()))
        try:
            ergebnis["imate2_typ"] = feature.GetSpecificFeature2.Type
        except Exception as e:  # Spike: Fehler festhalten
            ergebnis["imate2_typ"] = repr(e)
        ergebnis["imate2_ausrichtung_flipped"] = _ausrichtung_flipped(feature)
        if typ in ("abstand", "winkel"):
            try:
                mass = feature.Parameter("D1")
                ergebnis["d1_systemwert"] = None if mass is None else mass.SystemValue
            except Exception as e:
                ergebnis["d1_systemwert"] = repr(e)
    return ergebnis


def _ausrichtung_flipped(feature):
    """[IMate2.Alignment, IMate2.Flipped] der Verknüpfung (Ergänzung: Bleibt die Ausrichtung erhalten?)."""
    try:
        spezifisch = feature.GetSpecificFeature2
        return [spezifisch.Alignment, bool(spezifisch.Flipped)]
    except Exception as e:  # Spike: Fehler festhalten
        return repr(e)


def _mate_ausrichtungen(asm):
    return {f.Name: _ausrichtung_flipped(f) for f in _mates(asm)}


def _lage(komp):
    t = list(komp.Transform2.ArrayData)
    return {"translation_mm": [round(in_mm(x), 6) for x in t[9:12]], "rotation": [round(x, 9) for x in t[:9]],
            "skalierung": t[12], "status": komp.GetConstrainedStatus, "fixiert": bool(komp.IsFixed)}


def _ebene_lage(komp, name):
    """Rohwerte von IRefPlane.Transform der Bezugsebene `name` der Komponente (Deutung im Bericht)."""
    try:
        t = list(komp.FeatureByName(name).GetSpecificFeature2.Transform.ArrayData)
        return {"rotation": [round(x, 6) for x in t[:9]], "translation_mm": [round(in_mm(x), 6) for x in t[9:12]]}
    except Exception as e:  # Spike: Fehler festhalten
        return repr(e)


def _y_bereich_mm(komp, box_mm):
    """y-Bereich der Teilebox im Baugruppenkontext (nur für Drehungen, die y erhalten oder umkehren)."""
    t = list(komp.Transform2.ArrayData)
    return sorted(round(in_mm(t[10]) + t[4] * y, 4) for y in (box_mm[1], box_mm[4]))


def _interferenzen(asm):
    idm = asm.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    try:
        return [{"komponenten": [k.Name2 for k in (i.Components or ())], "volumen_mm3": in_mm3(i.Volume)}
                for i in (idm.GetInterferences or ())]
    finally:
        idm._FlagAsMethod("Done")
        idm.Done()


def _sha(pfad):
    return hashlib.sha256(Path(pfad).read_bytes()).hexdigest()


def _soll_gewinde(d, p, kernloch, laenge):
    """Ring Nenn-Ø/Kernloch-Ø über die Einschraublänge, abzüglich der 45°-Endfase p (wie Task 9)."""
    rn, rk = d / 2, kernloch / 2
    a = rn - p
    s_von, s_bis = max(rk - a, 0.0), min(p, laenge)
    v = math.pi * (((a + s_bis) ** 3 - (a + s_von) ** 3) / 3 - rk ** 2 * (s_bis - s_von)) if s_bis > s_von else 0.0
    return v + (math.pi * (rn ** 2 - rk ** 2) * (laenge - p) if laenge > p else 0.0)


def _baugruppe_1(app, r, ordner, sockel, lasche, schraube, stift):
    asm = _neue_baugruppe(app, r)
    try:
        e = {}
        k_so, e["einfuegen_sockel"] = _einfuegen(app, asm, sockel[0])
        e["sockel_fixiert"] = _fixiere(asm, k_so)
        k_la, e["einfuegen_lasche"] = _einfuegen(app, asm, lasche[0])
        k_sc, e["einfuegen_schraube_mit_bezugsgeometrie"] = _einfuegen(app, asm, schraube[0])
        k_st, e["einfuegen_stift_identitaet"] = _einfuegen(app, asm, stift[0], identitaet_setzen=True)
        so, la, sc, st = sockel[1], lasche[1], schraube[1], stift[1]
        e["mates"] = {
            "v1.1": _mate(asm, "v1.1", "deckungsgleich", ENTGEGEN, _entitaet(k_la, la, {"feature": "f1", "flaeche": "-y"}),
                          _entitaet(k_so, so, {"referenz": "OBEN"})),
            "v2": _mate(asm, "v2", "konzentrisch", GLEICH, _entitaet(k_la, la, {"feature": "f2", "instanz": 1}),
                        _entitaet(k_so, so, {"feature": "f2", "instanz": 1})),
            "v3": _mate(asm, "v3", "parallel", GLEICH, _entitaet(k_la, la, {"feature": "f1", "flaeche": "+x"}),
                        _entitaet(k_so, so, {"feature": "f1", "flaeche": "+x"})),
            "v4": _mate(asm, "v4", "deckungsgleich", GLEICH, _entitaet(k_sc, sc, {"referenz": "EINBAU_EBENE"}),
                        _entitaet(k_la, la, {"feature": "f1", "flaeche": "+y"})),
            "v5": _mate(asm, "v5", "konzentrisch", GLEICH, _entitaet(k_sc, sc, {"referenz": "EINBAU_ACHSE"}),
                        _entitaet(k_la, la, {"feature": "f2", "instanz": 1}), sperren=True),
            "v6": _mate(asm, "v6", "deckungsgleich", ENTGEGEN, _entitaet(k_st, st, {"referenz": "EINBAU_EBENE_1"}),
                        _entitaet(k_so, so, {"feature": "f1", "flaeche": "-y"})),
            "v7": _mate(asm, "v7", "konzentrisch", GLEICH, _entitaet(k_st, st, {"referenz": "EINBAU_ACHSE"}),
                        _entitaet(k_so, so, {"feature": "f3", "instanz": 1}), sperren=False),
        }
        e["lage"] = {n: _lage(k) for n, k in (("sockel", k_so), ("lasche", k_la), ("schraube", k_sc), ("stift", k_st))}
        e["ebenen_lage"] = {"sockel.OBEN": _ebene_lage(k_so, "OBEN"), "schraube.EINBAU_EBENE": _ebene_lage(k_sc, "EINBAU_EBENE"),
                            "stift.EINBAU_EBENE_1": _ebene_lage(k_st, "EINBAU_EBENE_1")}
        e["y_bereich_mm"] = {"schraube": _y_bereich_mm(k_sc, e["einfuegen_schraube_mit_bezugsgeometrie"]["box_mm"]),
                             "stift": _y_bereich_mm(k_st, e["einfuegen_stift_identitaet"]["box_mm"])}
        e["erwartet"] = {"lasche_y_mm": 20, "schraube_y_mm": 30, "stift_y_mm": 0, "schraube_status": 3, "stift_status": 2}
        e["mate_namen"] = [f.Name for f in _mates(asm)]
        e["mate_ausrichtungen_nachher"] = _mate_ausrichtungen(asm)
        e["interferenzen"] = _interferenzen(asm)
        e["soll_gewinde_mm3"] = round(_soll_gewinde(8, 1.25, 6.8, 10.0), 4)  # Kopf auf y = 30, l = 20, Eintritt y = 20
        e["getbox_mm"] = [round(in_mm(x), 4) for x in asm.GetBox(0)]
        e["soll_box_mm"] = [-50, 0, -30, 50, 38, 30]  # Sockel 100 × 60, Schraubenkopf bis 30 + k 8
        sw.speichere(asm, ordner / "S12_B1.sldasm")
        return e
    finally:
        sw.schliesse(app, asm)


def _baugruppe_2(app, r, sockel, lasche):
    """Abstand 15 und Winkel 30°; Transform-Konvention; Gleichung bindet das Abstandsmaß."""
    asm = _neue_baugruppe(app, r)
    try:
        k_so, _ = _einfuegen(app, asm, sockel[0])
        _fixiere(asm, k_so)
        k_la, _ = _einfuegen(app, asm, lasche[0])
        la, so = lasche[1], sockel[1]
        e = {"w1": _mate(asm, "w1", "abstand", ENTGEGEN, _entitaet(k_la, la, {"feature": "f1", "flaeche": "-y"}),
                         _entitaet(k_so, so, {"feature": "f1", "flaeche": "+y"}), wert=15),
             "w2": _mate(asm, "w2", "winkel", GLEICH, _entitaet(k_la, la, {"feature": "f1", "flaeche": "+x"}),
                         _entitaet(k_so, so, {"feature": "f1", "flaeche": "+x"}), wert=30)}
        e["lage"] = _lage(k_la)
        e["erwartet_y_mm"] = 35
        t = list(k_la.Transform2.ArrayData)
        flaeche, _ = _entitaet(k_la, la, {"feature": "f1", "flaeche": "+x"})
        e["normale_plus_x_im_baugruppenkontext"] = [round(c, 9) for c in flaeche.Normal]
        e["bild_x_zeilenvektor"] = [round(c, 9) for c in t[0:3]]
        e["bild_x_spaltenvektor"] = [round(t[0], 9), round(t[3], 9), round(t[6], 9)]
        e["bild_z_zeilenvektor"] = [round(c, 9) for c in t[6:9]]
        e["bild_z_spaltenvektor"] = [round(t[2], 9), round(t[5], 9), round(t[8], 9)]
        mu = sw.mathutil(app)
        for achse, vektor in (("x", [1.0, 0.0, 0.0]), ("z", [0.0, 0.0, 1.0])):
            bild = mu.CreateVector(r8_array(vektor)).MultiplyTransform(k_la.Transform2)
            e[f"bild_{achse}_multiplytransform"] = [round(c, 9) for c in bild.ArrayData]
        gleichungen = asm.GetEquationMgr
        e["add_S"] = gleichungen.Add2(-1, '"S" = 15', True)
        e["add_D1"] = gleichungen.Add2(-1, '"D1@w1" = "S"', True)
        index = next(i for i in range(gleichungen.GetCount) if gleichungen.Equation(i).startswith('"S"'))
        dispid = gleichungen._oleobj_.GetIDsOfNames("Equation")
        gleichungen._oleobj_.Invoke(dispid, 0, pythoncom.DISPATCH_PROPERTYPUT, False, index, '"S" = 25')
        gleichungen.EvaluateAll
        e["rebuild_nach_S_25"] = bool(asm.EditRebuild3)
        e["lage_nach_S_25"] = _lage(k_la)
        e["erwartet_y_nach_S_25_mm"] = 45
        return e
    finally:
        sw.schliesse(app, asm)


def _baugruppe_3(app, r, sockel, lasche):
    """Senkrecht allein: Status der Verknüpfung, Lasche bleibt unterbestimmt."""
    asm = _neue_baugruppe(app, r)
    try:
        k_so, _ = _einfuegen(app, asm, sockel[0])
        _fixiere(asm, k_so)
        k_la, _ = _einfuegen(app, asm, lasche[0])
        e = {"s1": _mate(asm, "s1", "senkrecht", GLEICH, _entitaet(k_la, lasche[1], {"feature": "f1", "flaeche": "+x"}),
                         _entitaet(k_so, sockel[1], {"feature": "f1", "flaeche": "+y"}))}
        e["lage"] = _lage(k_la)
        return e
    finally:
        sw.schliesse(app, asm)


def _baugruppe_4(app, r, sockel, lasche):
    """Ebene + zwei konzentrische Bohrungen: überbestimmt gemeldet?"""
    asm = _neue_baugruppe(app, r)
    try:
        k_so, _ = _einfuegen(app, asm, sockel[0])
        _fixiere(asm, k_so)
        k_la, _ = _einfuegen(app, asm, lasche[0])
        la, so = lasche[1], sockel[1]
        e = {"k1": _mate(asm, "k1", "deckungsgleich", ENTGEGEN, _entitaet(k_la, la, {"feature": "f1", "flaeche": "-y"}),
                         _entitaet(k_so, so, {"referenz": "OBEN"})),
             "k2": _mate(asm, "k2", "konzentrisch", GLEICH, _entitaet(k_la, la, {"feature": "f2", "instanz": 1}),
                         _entitaet(k_so, so, {"feature": "f2", "instanz": 1})),
             "k3": _mate(asm, "k3", "konzentrisch", GLEICH, _entitaet(k_la, la, {"feature": "f3", "instanz": 1}),
                         _entitaet(k_so, so, {"feature": "f3", "instanz": 1}))}
        e["lage"] = _lage(k_la)
        return e
    finally:
        sw.schliesse(app, asm)


def _baugruppe_5(app, r, ordner, name, sockel, lasche, schraube, stift, a4, a5, a6, a7, achse_zuerst=False):
    """Wie Baugruppe 1, aber mit wählbarer Ausrichtung von v4–v7 (Kopf auf der Lasche, Stift im Sockel).

    achse_zuerst: v5 (konzentrisch der Schraube) vor v4 (Ebene) anlegen.
    """
    asm = _neue_baugruppe(app, r)
    try:
        e = {"ausrichtungen": {"v4": a4, "v5": a5, "v6": a6, "v7": a7}, "achse_zuerst": achse_zuerst}
        k_so, _ = _einfuegen(app, asm, sockel[0])
        e["sockel_fixiert"] = _fixiere(asm, k_so)
        k_la, _ = _einfuegen(app, asm, lasche[0])
        k_sc, e["einfuegen_schraube"] = _einfuegen(app, asm, schraube[0])
        k_st, e["einfuegen_stift"] = _einfuegen(app, asm, stift[0], identitaet_setzen=True)
        so, la, sc, st = sockel[1], lasche[1], schraube[1], stift[1]
        schritte = {
            "v1.1": lambda: _mate(asm, "v1.1", "deckungsgleich", ENTGEGEN,
                                  _entitaet(k_la, la, {"feature": "f1", "flaeche": "-y"}),
                                  _entitaet(k_so, so, {"referenz": "OBEN"})),
            "v2": lambda: _mate(asm, "v2", "konzentrisch", GLEICH, _entitaet(k_la, la, {"feature": "f2", "instanz": 1}),
                                _entitaet(k_so, so, {"feature": "f2", "instanz": 1})),
            "v3": lambda: _mate(asm, "v3", "parallel", GLEICH, _entitaet(k_la, la, {"feature": "f1", "flaeche": "+x"}),
                                _entitaet(k_so, so, {"feature": "f1", "flaeche": "+x"})),
            "v4": lambda: _mate(asm, "v4", "deckungsgleich", a4, _entitaet(k_sc, sc, {"referenz": "EINBAU_EBENE"}),
                                _entitaet(k_la, la, {"feature": "f1", "flaeche": "+y"})),
            "v5": lambda: _mate(asm, "v5", "konzentrisch", a5, _entitaet(k_sc, sc, {"referenz": "EINBAU_ACHSE"}),
                                _entitaet(k_la, la, {"feature": "f2", "instanz": 1}), sperren=True),
            "v6": lambda: _mate(asm, "v6", "deckungsgleich", a6, _entitaet(k_st, st, {"referenz": "EINBAU_EBENE_1"}),
                                _entitaet(k_so, so, {"feature": "f1", "flaeche": "-y"})),
            "v7": lambda: _mate(asm, "v7", "konzentrisch", a7, _entitaet(k_st, st, {"referenz": "EINBAU_ACHSE"}),
                                _entitaet(k_so, so, {"feature": "f3", "instanz": 1}), sperren=False),
        }
        reihenfolge = ["v1.1", "v2", "v3", *(["v5", "v4"] if achse_zuerst else ["v4", "v5"]), "v6", "v7"]
        e["mates"] = {n: schritte[n]() for n in reihenfolge}
        e["lage"] = {n: _lage(k) for n, k in (("sockel", k_so), ("lasche", k_la), ("schraube", k_sc), ("stift", k_st))}
        e["y_bereich_mm"] = {"schraube": _y_bereich_mm(k_sc, e["einfuegen_schraube"]["box_mm"]),
                             "stift": _y_bereich_mm(k_st, e["einfuegen_stift"]["box_mm"])}
        e["erwartet"] = {"schraube_y_bereich_mm": [10, 38], "stift_y_bereich_mm": [0, 16], "schraube_status": 3,
                         "stift_status": 2}
        e["mate_namen"] = [f.Name for f in _mates(asm)]
        e["mate_ausrichtungen_nachher"] = _mate_ausrichtungen(asm)
        e["interferenzen"] = _interferenzen(asm)
        e["soll_gewinde_mm3"] = round(_soll_gewinde(8, 1.25, 6.8, 10.0), 4)
        e["getbox_mm"] = [round(in_mm(x), 4) for x in asm.GetBox(0)]
        e["soll_box_mm"] = [-50, 0, -30, 50, 38, 30]
        sw.speichere(asm, ordner / f"{name}.sldasm")
        return e
    finally:
        sw.schliesse(app, asm)


def _baugruppe_6(app, r, sockel, lasche):
    """Widersprüchliche Verknüpfung: deckungsgleich und danach Abstand 5 zwischen denselben Entitäten."""
    asm = _neue_baugruppe(app, r)
    try:
        k_so, _ = _einfuegen(app, asm, sockel[0])
        _fixiere(asm, k_so)
        k_la, _ = _einfuegen(app, asm, lasche[0])
        la, so = lasche[1], sockel[1]
        e = {"k1": _mate(asm, "k1", "deckungsgleich", ENTGEGEN, _entitaet(k_la, la, {"feature": "f1", "flaeche": "-y"}),
                         _entitaet(k_so, so, {"referenz": "OBEN"})),
             "k2": _mate(asm, "k2", "abstand", ENTGEGEN, _entitaet(k_la, la, {"feature": "f1", "flaeche": "-y"}),
                         _entitaet(k_so, so, {"referenz": "OBEN"}), wert=5)}
        e["lage"] = _lage(k_la)
        e["mate_namen_und_fehlercodes"] = [[f.Name, int(f.GetErrorCode2(byref_bool()))] for f in _mates(asm)]
        return e
    finally:
        sw.schliesse(app, asm)


def _wieder_oeffnen(app, pfad):
    vorher = _sha(pfad)
    fehler, warnungen = byref_long(), byref_long()
    asm = app.OpenDoc6(str(pfad), 2, 1, "", fehler, warnungen)  # swDocASSEMBLY, swOpenDocOptions_Silent
    try:
        asm.ResolveAllLightWeightComponents(False)
        e = {"fehler": fehler.value, "warnungen": warnungen.value, "interferenzen": _interferenzen(asm),
             "komponenten": [{"name": k.Name2, "datei": Path(k.GetPathName).name, **_lage(k)}
                             for k in (asm.GetComponents(True) or ())],
             "mates": [[f.Name, int(f.GetErrorCode2(byref_bool()))] for f in _mates(asm)]}
    finally:
        sw.schliesse(app, asm)
    e["sha_unveraendert"] = vorher == _sha(pfad)
    return e


def _ruecklesen(app, pfad):
    vorher = _sha(pfad)
    model = oeffne(app, pfad)
    try:
        gleichungen = model.GetEquationMgr
        werte = [{"text": gleichungen.Equation(i), "wert": gleichungen.Value(i), "global": bool(gleichungen.GlobalVariable(i))}
                 for i in range(gleichungen.GetCount)]
    finally:
        sw.schliesse(app, model)
    return {"gleichungen": werte, "sha_unveraendert": vorher == _sha(pfad)}


def pruefen() -> dict:
    r = lade_rechner()
    app = verbinde(r.sw_jahr)
    ordner = r.arbeitsordner / "stufe3b" / "s12"
    ordner.mkdir(parents=True, exist_ok=True)
    ergebnis, offen = {}, []
    try:
        sockel = _teil(app, r, SOCKEL, ordner)
        offen.append(sockel[0])
        lasche = _teil(app, r, LASCHE, ordner)
        offen.append(lasche[0])
        schraube = _normteil(app, "ISO 4762", "M8x20", ordner)
        offen.append(schraube[0])
        stift = _normteil(app, "ISO 8734", "8x16", ordner)
        offen.append(stift[0])
        ergebnis["baugruppe_1"] = _baugruppe_1(app, r, ordner, sockel, lasche, schraube, stift)
        ergebnis["baugruppe_2_werte"] = _baugruppe_2(app, r, sockel, lasche)
        ergebnis["baugruppe_3_senkrecht"] = _baugruppe_3(app, r, sockel, lasche)
        ergebnis["baugruppe_4_zwei_konzentrische"] = _baugruppe_4(app, r, sockel, lasche)
        ergebnis["baugruppe_5a_gegenrichtung"] = _baugruppe_5(app, r, ordner, "S12_B5a", sockel, lasche, schraube, stift,
                                                              ENTGEGEN, GLEICH, GLEICH, GLEICH)
        ergebnis["baugruppe_5b_gegenrichtung_achse_entgegen"] = _baugruppe_5(app, r, ordner, "S12_B5b", sockel, lasche,
                                                                              schraube, stift, ENTGEGEN, ENTGEGEN, GLEICH,
                                                                              ENTGEGEN)
        ergebnis["baugruppe_5c_achse_zuerst_ebene_entgegen"] = _baugruppe_5(
            app, r, ordner, "S12_B5c", sockel, lasche, schraube, stift, ENTGEGEN, GLEICH, GLEICH, ENTGEGEN, achse_zuerst=True)
        ergebnis["baugruppe_5d_achse_zuerst_ebene_gleich"] = _baugruppe_5(
            app, r, ordner, "S12_B5d", sockel, lasche, schraube, stift, GLEICH, GLEICH, GLEICH, ENTGEGEN, achse_zuerst=True)
        ergebnis["baugruppe_5e_ebene_gleich_dann_naechste"] = _baugruppe_5(
            app, r, ordner, "S12_B5e", sockel, lasche, schraube, stift, GLEICH, NAECHSTE, GLEICH, NAECHSTE)
        ergebnis["baugruppe_5f_ebene_entgegen_dann_naechste"] = _baugruppe_5(
            app, r, ordner, "S12_B5f", sockel, lasche, schraube, stift, ENTGEGEN, NAECHSTE, ENTGEGEN, NAECHSTE)
        ergebnis["baugruppe_6_widerspruch"] = _baugruppe_6(app, r, sockel, lasche)
    finally:
        for model in reversed(offen):
            sw.schliesse(app, model)
    ergebnis["wieder_geoeffnet"] = _wieder_oeffnen(app, ordner / "S12_B1.sldasm")
    ergebnis["wieder_geoeffnet_5a"] = _wieder_oeffnen(app, ordner / "S12_B5a.sldasm")
    ergebnis["wieder_geoeffnet_5b"] = _wieder_oeffnen(app, ordner / "S12_B5b.sldasm")
    ergebnis["ruecklesen_sockel"] = _ruecklesen(app, ordner / "S12_Sockel.sldprt")
    return ergebnis


if __name__ == "__main__":
    lauf("s12_baugruppe", pruefen)
