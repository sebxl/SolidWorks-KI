"""Bewertung der Messwerte gegen die Spezifikation (ohne SolidWorks) → Prüfungen und Mängel mit Knoten-IDs."""

from dataclasses import dataclass, field

from swki.compiler.eigenschaften import material_passt
from swki.formschraege import schraege, soll_vorzeichen
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand, volumen_auto
from swki.pruefung.huellquader import huellquader_auto
from swki.spec.ausdruck import auswerten
from swki.spec.normen import (
    SW_BEFESTIGUNG, SW_BEFESTIGUNG_STIFT_DURCH, SW_END_BLIND, SW_END_DURCH_ALLES, SW_LOCH_DURCH, SW_NORM, groesse_text,
    norm_von, normmasse,
)
from swki.verzahnung import KOPFHOEHE, Stirnrad, aus_feature

SKIZZE_VOLL_BESTIMMT = 3  # swConstrainedStatus_e.swFullyConstrained
_TOL_HUELLQUADER = 0.01
_TOL_MASS = 0.01
_TOL_SCHWERPUNKT = 0.05
_TOL_TIEFE = 0.01


@dataclass
class Messwerte:
    rebuild_fehler: list[str]  # ["f3: Code 71"]
    skizzen: dict[str, int]  # Skizzenname → swConstrainedStatus_e
    box: list[float]  # [xmin, ymin, zmin, xmax, ymax, zmax] mm
    volumen: float  # mm³
    schwerpunkt: tuple[float, float, float]  # mm
    material: str
    eigenschaften: dict[str, str]
    messpunkte: dict[str, Messgeometrie | str] = field(default_factory=dict)  # Schlüssel → Geometrie oder Fehlertext
    normbohrungen: dict[str, dict | str] = field(default_factory=dict)  # ID → Bohrungsassistent-Daten oder Fehlertext
    koerper: int = 1  # Anzahl Volumenkörper im Teil (Soll: genau 1)
    durchmesser: dict[str, dict | str] = field(default_factory=dict)  # was → {"durchmesser", "achse", "referenz"?} oder Fehlertext
    verzahnungen: dict[str, dict | str] = field(default_factory=dict)  # ID → Messwerte der Verzahnung oder Fehlertext
    formschraegen: dict[str, dict | str] = field(default_factory=dict)  # ID → {"flaechen": [...]} oder Fehlertext


def messpunkt_schluessel(messpunkt: dict) -> str:
    return ",".join(f"{k}={messpunkt[k]}" for k in sorted(messpunkt))


def _knoten_aus(text: str, ids: list[str]) -> str:
    """SW-Name ("f2_senkung: Code 71", "f10_2/Skizze7", "f1_skizze") → Feature-ID der Spezifikation."""
    name = text.split(":")[0].split("/")[0].strip()
    passend = [i for i in ids if name == i or name.startswith(f"{i}_")]
    return max(passend, key=len) if passend else name


def eintrag(pid: str, ok: bool | None, **daten) -> dict:
    return {"id": pid, "ok": ok, **daten}


def normbohrung_abweichungen(f: dict, ist: dict, parameter: dict) -> list[str]:
    """Spec 2c §3.4: normbohrung-Knoten (freigegebene Kopie) gegen die Bohrungsassistent-Daten des gleichnamigen
    Features (swki.pruefung.messen.lies_normbohrung, Längen in mm). Leere Liste = passt.

    Die Art ergibt sich aus FastenerType2. Ausnahme Stiftloch mit durch (CreateDefinition): dort liest FastenerType2
    −1, die Art zeigt nur Type = swHoleThru (Spike S10, Frage 4)."""
    norm = norm_von(f)
    durch = bool(f.get("durch"))
    soll = {"norm": SW_NORM.get(norm), "positionen": len(f["positionen"]),
            "ende": SW_END_DURCH_ALLES if durch else SW_END_BLIND}
    if f["art"] == "stift" and durch:
        soll = {"befestigung": SW_BEFESTIGUNG_STIFT_DURCH, "typ": SW_LOCH_DURCH, **soll}
    else:
        soll = {"befestigung": SW_BEFESTIGUNG[f["art"]], **soll}
    abweichungen = [f"{k}: ist {ist.get(k)} statt {v}" for k, v in soll.items() if ist.get(k) != v]
    masse = normmasse(f["art"], f["groesse"], norm) or {}
    if ist.get("groesse") not in {masse.get("sw_groesse"), masse.get("gelesen")} - {None}:
        abweichungen.append(f"groesse: ist {ist.get('groesse')} statt {masse.get('sw_groesse', groesse_text(f['groesse']))}")
    for feld in ("tiefe", "gewindetiefe"):
        if feld in f:
            wert = auswerten(f[feld], parameter)
            if abs(ist.get(feld, 0.0) - wert) > _TOL_TIEFE:
                abweichungen.append(f"{feld}: ist {ist.get(feld, 0.0):g} statt {wert:g}")
    return abweichungen


def verzahnung_abweichungen(f: dict, ist: dict, parameter: dict, tol_mm: float) -> list[str]:
    """Spec 4b §4.5: verzahnung-Knoten (freigegebene Kopie) gegen die Messwerte des gleichnamigen Features
    (swki.pruefung.messen.verzahnungen, mm). Leere Liste = passt."""
    geo = aus_feature(f, parameter)
    abweichungen = [ist["fehler"]] if "fehler" in ist else []
    if ist.get("zaehne") != geo.z:
        abweichungen.append(f"zaehne: ist {ist.get('zaehne')} statt {geo.z}")

    def vergleiche(name: str, wert, soll: float) -> None:
        werte = wert if isinstance(wert, list) else [wert]
        falsch = [w for w in werte if w is None or abs(w - soll) > tol_mm]
        if falsch or not werte:
            abweichungen.append(f"{name}: ist {wert} statt {round(soll, 6)}")

    if isinstance(geo, Stirnrad):
        vergleiche("kopfkreis", ist.get("kopfkreis"), 2 * geo.ra)
        vergleiche("fusskreis", ist.get("fusskreis"), 2 * geo.rf)
        if "zahnweite" in ist:
            vergleiche(f"zahnweite W{geo.messzaehnezahl()}", ist["zahnweite"], geo.zahnweite())
    else:
        vergleiche("kopflinie", ist.get("kopflinie"), KOPFHOEHE * geo.m)
        vergleiche("teilung", ist.get("teilung"), geo.p)
        if "zahndicke" in ist:
            vergleiche("zahndicke", ist["zahndicke"], geo.s)
    return abweichungen


def formschraege_abweichungen(f: dict, ist: dict, parameter: dict, tol_grad: float) -> list[str]:
    """Spec Formschräge §6.1: Seitenflächen des Features (swki.pruefung.messen.formschraegen) gegen Winkel und Richtung des
    Knotens der freigegebenen Kopie. Leere Liste = passt."""
    s = schraege(f)
    flaechen = ist["flaechen"]
    if not flaechen:
        return ["keine geschrägte Seitenfläche gefunden"]
    winkel, vorzeichen = auswerten(s["winkel"], parameter), soll_vorzeichen(f["typ"], s["querschnitt"])
    fehler = []
    falsch = [x["winkel"] for x in flaechen if abs(x["winkel"] - winkel) > tol_grad]
    if falsch:
        werte = ", ".join(f"{w:g}" for w in sorted({round(w, 3) for w in falsch}))
        fehler.append(f"Winkel {werte}° statt {winkel:g}° ({len(falsch)} von {len(flaechen)} Seitenflächen)")
    gegen = sum(1 for x in flaechen if x["vorzeichen"] != vorzeichen)
    if gegen:
        fehler.append(f"Querschnitt nicht {s['querschnitt']} ({gegen} von {len(flaechen)} Seitenflächen)")
    return fehler


def baum_kennzahl(spec: dict, protokoll: dict | None) -> dict:
    """Spec 2c §6.3: Knoten der Spezifikation und vom Bau erzeugte Features (Namen aus dem Bauprotokoll; Skizzen,
    Ebenen und Achsen legt der Compiler nebenbei an und zählen nicht)."""
    namen = [n for k in (protokoll or {}).get("knoten", []) if k.get("sw_name") for n in k["sw_name"].split(", ")]
    return {"knoten": len(spec["features"]), "features": len(namen)}


def bewerte(spec: dict, m: Messwerte, standard: dict, freigegeben: dict | None = None) -> dict:
    """freigegeben: Spezifikation im Stand der Freigabe; das Sollvolumen "auto" wird aus ihr berechnet,
    damit ein nachgebesserter Bauweg das Soll nicht mitverschiebt. Normbohrungen und Formschrägen werden gegen die
    freigegebene Kopie geprüft (Größen und Richtungen sind Text, die Prüfsumme schützt sie nicht)."""
    p = spec.get("parameter", {})
    pr = spec.get("pruefung", {})
    ergebnisse = []

    ids = [f["id"] for f in spec["features"]]
    knoten = sorted({_knoten_aus(t, ids) for t in m.rebuild_fehler})
    ergebnisse.append(eintrag("rebuild", not m.rebuild_fehler, ist=m.rebuild_fehler, knoten=knoten))

    offen = {n: s for n, s in m.skizzen.items() if s != SKIZZE_VOLL_BESTIMMT}
    ergebnisse.append(eintrag("skizzen", not offen, ist=offen, knoten=sorted({_knoten_aus(n, ids) for n in offen})))

    soll_spec = freigegeben or spec
    soll_normbohrungen = [f for f in soll_spec["features"] if f["typ"] == "normbohrung"]
    if soll_normbohrungen:
        p_soll = soll_spec.get("parameter", {})
        abweichend = {}
        for f in soll_normbohrungen:
            ist = m.normbohrungen.get(f["id"])
            if not isinstance(ist, dict):
                abweichend[f["id"]] = [ist or f"Feature {f['id']} fehlt im Teil"]
            elif fehler := normbohrung_abweichungen(f, ist, p_soll):
                abweichend[f["id"]] = fehler
        ergebnisse.append(eintrag("normbohrungen", not abweichend, ist=abweichend, knoten=sorted(abweichend)))

    soll_verzahnungen = [f for f in soll_spec["features"] if f["typ"] == "verzahnung"]
    if soll_verzahnungen:
        p_soll, tol = soll_spec.get("parameter", {}), standard["toleranzen"]["verzahnung_mm"]
        abweichend = {}
        for f in soll_verzahnungen:
            ist = m.verzahnungen.get(f["id"])
            if not isinstance(ist, dict):
                abweichend[f["id"]] = [ist or f"Feature {f['id']} fehlt im Teil"]
            elif fehler := verzahnung_abweichungen(f, ist, p_soll, tol):
                abweichend[f["id"]] = fehler
        ergebnisse.append(eintrag("verzahnungen", not abweichend, ist=abweichend, knoten=sorted(abweichend)))

    soll_schraegen = [f for f in soll_spec["features"] if schraege(f) is not None]
    if soll_schraegen:
        p_soll, tol = soll_spec.get("parameter", {}), standard["toleranzen"]["winkel_grad"]
        abweichend, gemessen = {}, {}
        for f in soll_schraegen:
            ist = m.formschraegen.get(f["id"])
            if not isinstance(ist, dict):
                abweichend[f["id"]] = [ist or f"Feature {f['id']} fehlt im Teil"]
                continue
            gemessen[f["id"]] = sorted({round(x["winkel"], 3) for x in ist["flaechen"]})
            if fehler := formschraege_abweichungen(f, ist, p_soll, tol):
                abweichend[f["id"]] = fehler
        ergebnisse.append(eintrag("formschraegen", not abweichend, ist=abweichend, gemessen=gemessen,
                                  knoten=sorted(abweichend)))

    # Allgemeine Prüfung: ein Teil ist ein Volumenkörper. Ein Aufsatz mit Abstand zum Körper (z. B. versatz_von_flaeche
    # bei abgesetzter Skizze) besteht sonst alle anderen Prüfungen, obwohl er getrennt im Teil steht.
    if m.koerper == 1:
        ergebnisse.append(eintrag("koerper", True, ist=1, soll=1, knoten=[]))
    else:
        ergebnisse.append(eintrag("koerper", False, ist=m.koerper, soll=1, knoten=[],
                                    hinweis=f"{m.koerper} Volumenkörper statt 1"))

    if "huellquader" in pr:
        ist = [round(m.box[i + 3] - m.box[i], 6) for i in range(3)]
        if pr["huellquader"] == "auto":
            soll, grund = huellquader_auto(freigegeben or spec)
        else:
            soll, grund = [auswerten(v, p) for v in pr["huellquader"]], "vorgegeben"
        tol = pr.get("huellquader_tol", _TOL_HUELLQUADER)
        if soll is None:
            ergebnisse.append(eintrag("huellquader", None, ist=ist, hinweis=f"Sollhüllquader nicht berechenbar ({grund})",
                                        knoten=[]))
        else:
            ok = all(abs(a - b) <= tol for a, b in zip(ist, soll))
            ergebnisse.append(eintrag("huellquader", ok, ist=ist, soll=soll, tol=tol, knoten=[]))

    if "volumen" in pr:
        roh = pr["volumen"]["soll"]
        soll, grund = volumen_auto(freigegeben or spec) if roh == "auto" else (auswerten(roh, p), "vorgegeben")
        prozent = pr["volumen"].get("toleranz_prozent", standard["toleranzen"]["volumen_prozent"])
        if soll is None:
            ergebnisse.append(eintrag("volumen", None, ist=m.volumen, hinweis=f"Sollvolumen nicht berechenbar ({grund})",
                                        knoten=[]))
        else:
            abweichung = abs(m.volumen - soll) / soll * 100
            ergebnisse.append(eintrag("volumen", abweichung <= prozent, ist=round(m.volumen, 3), soll=round(soll, 3),
                                        abweichung_prozent=round(abweichung, 4), tol_prozent=prozent, knoten=[]))

    for mp in pr.get("masse_pruefen", []):
        von, zu = m.messpunkte.get(messpunkt_schluessel(mp["von"])), m.messpunkte.get(messpunkt_schluessel(mp["zu"]))
        knoten = sorted({x["feature"] for x in (mp["von"], mp["zu"]) if "feature" in x})
        soll, tol = auswerten(mp["soll"], p), mp.get("tol", _TOL_MASS)
        if isinstance(von, str) or isinstance(zu, str) or von is None or zu is None:
            fehler = next(x for x in (von, zu, "Messpunkt fehlt") if isinstance(x, str))
            ergebnisse.append(eintrag(f"mass:{mp['was']}", False, soll=soll, hinweis=fehler, knoten=knoten))
            continue
        try:
            ist = round(abstand(von, zu), 6)
        except NichtMessbar as e:
            ergebnisse.append(eintrag(f"mass:{mp['was']}", False, soll=soll, hinweis=str(e), knoten=knoten))
            continue
        ergebnisse.append(eintrag(f"mass:{mp['was']}", abs(ist - soll) <= tol, ist=ist, soll=soll, tol=tol, knoten=knoten))

    for dp in pr.get("durchmesser_pruefen", []):
        pid, knoten = f"durchmesser:{dp['was']}", [dp["feature"]]
        soll, tol = auswerten(dp["soll"], p), dp.get("tol", _TOL_MASS)
        ist = m.durchmesser.get(dp["was"], "Messung fehlt")
        if isinstance(ist, str):
            ergebnisse.append(eintrag(pid, False, soll=soll, hinweis=ist, knoten=knoten))
            continue
        ok = abs(ist["durchmesser"] - soll) <= tol
        daten = {"ist": ist["durchmesser"], "soll": soll, "tol": tol}
        if "referenz" in dp:
            try:
                daten["achsversatz"] = round(abstand(ist["achse"], ist["referenz"]), 6)
                ok = ok and daten["achsversatz"] <= tol
            except NichtMessbar as e:
                ok, daten["hinweis"] = False, f"nicht koaxial zu {dp['referenz']}: {e}"
        ergebnisse.append(eintrag(pid, ok, **daten, knoten=knoten))

    if "schwerpunkt" in pr:
        soll = [None if v is None else auswerten(v, p) for v in pr["schwerpunkt"]["soll"]]
        tol = pr["schwerpunkt"].get("tol", _TOL_SCHWERPUNKT)
        ist = [round(v, 6) for v in m.schwerpunkt]
        ok = all(s is None or abs(i - s) <= tol for i, s in zip(ist, soll))
        ergebnisse.append(eintrag("schwerpunkt", ok, ist=ist, soll=soll, tol=tol, knoten=[]))

    if "material" in spec:
        ergebnisse.append(eintrag("material", material_passt(m.material, spec["material"]), ist=m.material, soll=spec["material"],
                                    knoten=[]))

    soll_eig = spec.get("eigenschaften", {})
    abweichend = {k: m.eigenschaften.get(k) for k, v in soll_eig.items() if m.eigenschaften.get(k) != v}
    ergebnisse.append(eintrag("eigenschaften", not abweichend, ist=abweichend, soll=soll_eig, knoten=[]))

    maengel = [
        {"pruefung": e["id"], "knoten": e["knoten"], "beschreibung": beschreibung(e)}
        for e in ergebnisse if e["ok"] is False
    ]
    return {"bestanden": not maengel, "pruefungen": ergebnisse, "maengel": maengel}


def beschreibung(e: dict) -> str:
    if "hinweis" in e:
        return f"{e['id']}: {e['hinweis']}"
    if "soll" in e:
        return f"{e['id']}: ist {e.get('ist')} statt {e['soll']}"
    return f"{e['id']}: {e.get('ist')}"
