"""Bewertung eines aufgenommenen Kaufteils (Spec 3c §6.3) ohne SolidWorks: Messwerte → Prüfungen und Mängel.

Prüfungs-IDs: rebuild, import, koerper, huellquader, volumen, einbau:<name>, gewinde:<gruppe>, durchmesser:<was>,
mass:<was>, material, eigenschaften, masse. Kennmaße tragen ihren Beleg (Liste der Beleg-IDs) oder "nicht belegt"."""

import math
from dataclasses import dataclass, field

from swki.compiler.anker import punkt_achse_abstand
from swki.compiler.eigenschaften import material_passt
from swki.kaufteile.eintrag import eigenschaften
from swki.kaufteile.ortung import TOL_WINKEL_GRAD, winkel_grad
from swki.pruefung.bewertung import beschreibung, eintrag, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand

TOL_HUELLQUADER = 0.1      # mm, Vorgabe (Spec 3c §4.4)
TOL_MASS = 0.01            # mm, Vorgabe für durchmesser_pruefen und masse_pruefen
TOL_VOLUMEN_PROZENT = 0.01  # Fingerabdruck: gleiche Datei, gleicher Import
TOL_MASSE_RELATIV = 1e-6   # überschriebene Masse
TOL_LAGE_MM = 0.01         # Bezugsgeometrie auf der georteten Fläche
NICHT_BELEGT = "nicht belegt"


@dataclass
class KaufteilMesswerte:
    rebuild_fehler: list[str]
    koerper: int                       # Volumenkörper
    flaechenkoerper: int
    koerperfehler: dict[str, int]      # Körper (1 …) → Anzahl Fehler laut IBody2.Check3
    box: list[float]                   # [xmin, ymin, zmin, xmax, ymax, zmax] in mm
    volumen: float                     # mm³
    masse_kg: float
    masse_ueberschrieben: bool
    material: str
    eigenschaften: dict[str, str]
    einbau: dict = field(default_factory=dict)       # Name → {"ist", "abweichung", "bezug": Messgeometrie} | Fehlertext
    gewinde: dict = field(default_factory=dict)      # "<gruppe>.<i>" → {"ist", "abweichung"} | Fehlertext
    messpunkte: dict = field(default_factory=dict)   # messpunkt_schluessel → Messgeometrie | Fehlertext
    durchmesser: dict = field(default_factory=dict)  # was → {"durchmesser", "achse", "referenz"?} | Fehlertext


def _beleg(daten: dict) -> list | str:
    return daten.get("beleg") or NICHT_BELEGT


def _parallel(a, b) -> float:
    """Winkel zwischen zwei Geraden (0 … 90°), Richtung egal."""
    w = winkel_grad(a, b)
    return min(w, 180.0 - w)


def _punkt_ebene(punkt, ebene: Messgeometrie) -> float:
    return abstand(Messgeometrie("punkt", tuple(punkt)), ebene)


def _einbau_fehler(art: str, soll: dict, messung: dict, bezug: Messgeometrie, alle: dict) -> list[str]:
    ist = messung.get("ist", {})
    fehler = []
    if art == "zylinder":
        if _parallel(bezug.richtung, ist["achse"]) > TOL_WINKEL_GRAD or \
                punkt_achse_abstand(bezug.punkt, ist["punkt"], ist["achse"]) > TOL_LAGE_MM:
            fehler.append("Bezugsachse liegt nicht auf der Zylinderachse")
        if "senkrecht_zu" in soll:
            andere = alle.get(soll["senkrecht_zu"])
            if not isinstance(andere, dict) or not isinstance(andere.get("bezug"), Messgeometrie):
                fehler.append(f"{soll['senkrecht_zu']} fehlt für senkrecht_zu")
            elif (w := _parallel(bezug.richtung, andere["bezug"].richtung)) > TOL_WINKEL_GRAD:
                fehler.append(f"Achse nicht senkrecht zu {soll['senkrecht_zu']} ({w:.3f}° Abweichung)")
    elif art == "ebene":
        if _parallel(bezug.richtung, ist["normale"]) > TOL_WINKEL_GRAD or _punkt_ebene(ist["punkt"], bezug) > TOL_LAGE_MM:
            fehler.append("Bezugsebene liegt nicht auf der Fläche")
    else:
        achse = alle.get(soll["achse"])
        if not isinstance(achse, dict) or not isinstance(achse.get("bezug"), Messgeometrie):
            return [f"{soll['achse']} fehlt für ebene_durch_achse"]
        a = achse["bezug"]
        if abs(90.0 - winkel_grad(bezug.richtung, a.richtung)) > TOL_WINKEL_GRAD or _punkt_ebene(a.punkt, bezug) > TOL_LAGE_MM:
            fehler.append(f"Bezugsebene enthält {soll['achse']} nicht")
        if _punkt_ebene(soll["nahe"], bezug) > TOL_LAGE_MM:
            fehler.append("Bezugsebene geht nicht durch nahe")
    return fehler


def _einbau(name: str, w: dict, m: KaufteilMesswerte) -> dict:
    pid = f"einbau:{name}"
    messung = m.einbau.get(name, "Einbaureferenz nicht angelegt")
    if isinstance(messung, str):
        return eintrag(pid, False, hinweis=messung, knoten=[name])
    art, soll = next(iter(w.items()))
    fehler = [messung["abweichung"]] if messung.get("abweichung") else []
    bezug = messung.get("bezug")
    daten = {"ist": {k: v for k, v in messung.get("ist", {}).items() if k not in ("achse", "punkt")}}
    erwartet = "achse" if art == "zylinder" else "ebene"
    if not isinstance(bezug, Messgeometrie) or bezug.art != erwartet:
        fehler.append(f"Bezugsgeometrie ist keine {erwartet}")
    else:
        daten["bezug"] = {"punkt": [round(c, 4) for c in bezug.punkt], "richtung": [round(c, 6) for c in bezug.richtung]}
        if not fehler:
            fehler += _einbau_fehler(art, soll, messung, bezug, m.einbau)
    if fehler:
        daten["hinweis"] = "; ".join(fehler)
    return eintrag(pid, not fehler, **daten, knoten=[name])


def _gewinde(gruppe: str, w: dict, m: KaufteilMesswerte) -> dict:
    ist, fehler = {}, []
    for i in range(1, len(w["positionen"]) + 1):
        messung = m.gewinde.get(f"{gruppe}.{i}", "Position nicht geortet")
        if isinstance(messung, str):
            fehler.append(f"{i}: {messung}")
            continue
        ist[str(i)] = {k: v for k, v in messung["ist"].items() if k in ("durchmesser", "modell")}
        if messung.get("abweichung"):
            fehler.append(f"{i}: {messung['abweichung']}")
    daten = {"ist": ist, "beleg": _beleg(w)}
    if fehler:
        daten["hinweis"] = "; ".join(fehler)
    return eintrag(f"gewinde:{gruppe}", not fehler, **daten, knoten=[gruppe])


def _masse_pruefen(pr: dict, m: KaufteilMesswerte) -> list[dict]:
    ergebnisse = []
    for mp in pr.get("masse_pruefen", []):
        pid, soll, tol = f"mass:{mp['was']}", mp["soll"], mp.get("tol", TOL_MASS)
        von, zu = m.messpunkte.get(messpunkt_schluessel(mp["von"])), m.messpunkte.get(messpunkt_schluessel(mp["zu"]))
        if not isinstance(von, Messgeometrie) or not isinstance(zu, Messgeometrie):
            fehler = next((x for x in (von, zu) if isinstance(x, str)), "Messpunkt fehlt")
            ergebnisse.append(eintrag(pid, False, soll=soll, hinweis=fehler, beleg=_beleg(mp), knoten=[]))
            continue
        try:
            ist = round(abstand(von, zu), 6)
        except NichtMessbar as e:
            ergebnisse.append(eintrag(pid, False, soll=soll, hinweis=str(e), beleg=_beleg(mp), knoten=[]))
            continue
        ergebnisse.append(eintrag(pid, abs(ist - soll) <= tol, ist=ist, soll=soll, tol=tol, beleg=_beleg(mp), knoten=[]))
    return ergebnisse


def _durchmesser(pr: dict, m: KaufteilMesswerte) -> list[dict]:
    ergebnisse = []
    for dp in pr.get("durchmesser_pruefen", []):
        pid, soll, tol = f"durchmesser:{dp['was']}", dp["soll"], dp.get("tol", TOL_MASS)
        ist = m.durchmesser.get(dp["was"], "Messung fehlt")
        if isinstance(ist, str):
            ergebnisse.append(eintrag(pid, False, soll=soll, hinweis=ist, beleg=_beleg(dp), knoten=[]))
            continue
        ok = abs(ist["durchmesser"] - soll) <= tol
        daten = {"ist": ist["durchmesser"], "soll": soll, "tol": tol, "beleg": _beleg(dp)}
        if "referenz" in dp:
            try:
                daten["achsversatz"] = round(abstand(ist["achse"], ist["referenz"]), 6)
                ok = ok and daten["achsversatz"] <= tol
            except (NichtMessbar, KeyError) as e:
                ok, daten["hinweis"] = False, f"nicht koaxial zu {dp['referenz']}: {e}"
        ergebnisse.append(eintrag(pid, ok, **daten, knoten=[]))
    return ergebnisse


def bewerte_kaufteil(spec: dict, m: KaufteilMesswerte) -> dict:
    pr = spec.get("pruefung", {})
    ergebnisse = [eintrag("rebuild", not m.rebuild_fehler, ist=m.rebuild_fehler, knoten=[])]
    import_ok = m.flaechenkoerper == 0 and not any(m.koerperfehler.values())
    ergebnisse.append(eintrag("import", import_ok, ist={"flaechenkoerper": m.flaechenkoerper,
                                                         "koerperfehler": m.koerperfehler}, knoten=[]))
    ergebnisse.append(eintrag("koerper", m.koerper == spec["koerper"], ist=m.koerper, soll=spec["koerper"], knoten=[]))
    if "huellquader" in pr:
        h = pr["huellquader"]
        ist = [round(m.box[i + 3] - m.box[i], 6) for i in range(3)]
        tol = h.get("tol", TOL_HUELLQUADER)
        ergebnisse.append(eintrag("huellquader", all(abs(a - b) <= tol for a, b in zip(ist, h["soll"])), ist=ist,
                                    soll=h["soll"], tol=tol, beleg=_beleg(h), knoten=[]))
    if "volumen" in pr:
        soll = pr["volumen"]["soll"]
        prozent = pr["volumen"].get("toleranz_prozent", TOL_VOLUMEN_PROZENT)
        abw = abs(m.volumen - soll) / soll * 100
        ergebnisse.append(eintrag("volumen", abw <= prozent, ist=round(m.volumen, 3), soll=soll,
                                    abweichung_prozent=round(abw, 4), tol_prozent=prozent, knoten=[]))
    ergebnisse += [_einbau(n, w, m) for n, w in spec["einbau"].items()]
    ergebnisse += [_gewinde(g, w, m) for g, w in spec.get("gewinde", {}).items()]
    ergebnisse += _durchmesser(pr, m) + _masse_pruefen(pr, m)
    ergebnisse.append(eintrag("material", material_passt(m.material, spec["material"]), ist=m.material,
                                soll=spec["material"], knoten=[]))
    soll_eig = eigenschaften(spec)
    abweichend = {k: m.eigenschaften.get(k) for k, v in soll_eig.items() if m.eigenschaften.get(k) != v}
    ergebnisse.append(eintrag("eigenschaften", not abweichend, ist=abweichend, soll=soll_eig, knoten=[]))
    if "masse" in spec:
        kg = spec["masse"]["kg"]
        ok = m.masse_ueberschrieben and math.isclose(m.masse_kg, kg, rel_tol=TOL_MASSE_RELATIV)
        ergebnisse.append(eintrag("masse", ok, ist=round(m.masse_kg, 6), soll=kg, ueberschrieben=m.masse_ueberschrieben,
                                    beleg=_beleg(spec["masse"]), knoten=[]))
    else:
        ergebnisse.append(eintrag("masse", None, ist=round(m.masse_kg, 6), hinweis="Masse aus Material geschätzt",
                                    knoten=[]))
    maengel = [{"pruefung": e["id"], "knoten": e["knoten"], "beschreibung": beschreibung(e)}
               for e in ergebnisse if e["ok"] is False]
    return {"bestanden": not maengel, "pruefungen": ergebnisse, "maengel": maengel}
