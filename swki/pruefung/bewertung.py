"""Bewertung der Messwerte gegen die Spezifikation (ohne SolidWorks) → Prüfungen und Mängel mit Knoten-IDs."""

from dataclasses import dataclass, field

from swki.compiler.eigenschaften import gleichungen_an, material_passt
from swki.formschraege import schraege, soll_vorzeichen
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand, volumen_auto
from swki.pruefung.huellquader import huellquader_auto
from swki.spec.ausdruck import auswerten
from swki.spec.bohrungsfase import fase_abstand
from swki.spec.instanzen import MUSTER, anzahl_instanzen, traeger
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
    gleichungen: int = 0  # Anzahl Gleichungen und globale Variablen (EquationMgr.GetCount)
    muster: dict[str, dict | str] = field(default_factory=dict)  # ID → Definition (Anzahl, Abstand, Quellen) oder Fehlertext
    kanten: dict[str, dict | str] = field(default_factory=dict)  # Feature-Name → Kantenmaß und Flächenzahl oder Fehlertext


def messpunkt_schluessel(messpunkt: dict) -> str:
    return ",".join(f"{k}={messpunkt[k]}" for k in sorted(messpunkt))


def _knoten_aus(text: str, ids: list[str]) -> str:
    """SW-Name ("f2_senkung: Code 71", "f10_2/Skizze7", "f1_skizze") → Feature-ID der Spezifikation."""
    name = text.split(":")[0].split("/")[0].strip()
    passend = [i for i in ids if name == i or name.startswith(f"{i}_")]
    return max(passend, key=len) if passend else name


def eintrag(pid: str, ok: bool | None, **daten) -> dict:
    return {"id": pid, "ok": ok, **daten}


def mass_eintrag(mp: dict, messpunkte: dict, soll: float, tol: float, knoten: list[str], **daten) -> dict:
    """`mass:<was>` eines Eintrags aus `pruefung.masse_pruefen`: Abstand der beiden Messpunkte gegen `soll`. Ein Fehlertext statt eines
    Messpunkts und nicht parallele Bezüge sind Mängel, nie ein Abbruch. `daten` steht zusätzlich im Eintrag."""
    pid = f"mass:{mp['was']}"
    von, zu = messpunkte.get(messpunkt_schluessel(mp["von"])), messpunkte.get(messpunkt_schluessel(mp["zu"]))
    if not isinstance(von, Messgeometrie) or not isinstance(zu, Messgeometrie):
        fehler = next((x for x in (von, zu) if isinstance(x, str)), "Messpunkt fehlt")
        return eintrag(pid, False, soll=soll, hinweis=fehler, **daten, knoten=knoten)
    try:
        ist = round(abstand(von, zu), 6)
    except NichtMessbar as e:
        return eintrag(pid, False, soll=soll, hinweis=str(e), **daten, knoten=knoten)
    return eintrag(pid, abs(ist - soll) <= tol, ist=ist, soll=soll, tol=tol, **daten, knoten=knoten)


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


_TOL_KANTE_MM, _TOL_KANTE_GRAD = 0.001, 0.01
_HILFSFEATURES = ("_senkung", "_fase")  # vom Compiler angelegte Teilfeatures einer Bohrung, Quellen eines Musters


def _richtungen(f: dict) -> list[tuple[int, dict]]:
    return [(i, f[r]) for i, r in ((1, "richtung1"), (2, "richtung2")) if r in f]


def muster_abweichungen(f_aktuell: dict | None, f_kopie: dict | None, ist: dict | str | None, p: dict) -> list[str]:
    """Paket Konstruktionsstil: Muster/Spiegeln wie in der aktuellen Spec gebaut (Anzahl, Abstand bzw. Winkel, Quellen
    aus der Feature-Definition, Spike S20 f) und – nur für Formmuster – gegen die freigegebene Kopie. Bohrungsmuster sind
    Bauweg, ihre Wirkung prüft bohrbild_abweichungen."""
    if f_aktuell is None:
        return ["Muster der Freigabe fehlt"]
    if not isinstance(ist, dict):
        return [ist or f"Feature {f_aktuell['id']} fehlt im Teil"]
    fehler = []
    if f_aktuell["typ"] == "muster_linear":
        for i, r in _richtungen(f_aktuell):
            if ist.get(f"n{i}") != r["anzahl"]:
                fehler.append(f"anzahl Richtung {i}: ist {ist.get(f'n{i}')} statt {r['anzahl']}")
            if abs(ist.get(f"a{i}", 0.0) - auswerten(r["abstand"], p)) > _TOL_KANTE_MM:
                fehler.append(f"abstand Richtung {i}: ist {ist.get(f'a{i}'):g} statt {auswerten(r['abstand'], p):g}")
    elif f_aktuell["typ"] == "muster_kreis":
        soll_w = auswerten(f_aktuell.get("winkel", 360), p)
        if ist.get("n") != f_aktuell["anzahl"]:
            fehler.append(f"anzahl: ist {ist.get('n')} statt {f_aktuell['anzahl']}")
        if abs(ist.get("winkel", 0.0) - soll_w) > _TOL_KANTE_GRAD:
            fehler.append(f"winkel: ist {ist.get('winkel'):g} statt {soll_w:g}")
    quellen = sorted(q for q in ist.get("quellen", []) if not q.endswith(_HILFSFEATURES))
    if quellen != sorted(f_aktuell["features"]):
        fehler.append(f"Quellen: ist {quellen} statt {sorted(f_aktuell['features'])}")
    if f_kopie is not None:
        fehler += _gegen_kopie(f_aktuell, f_kopie, p)
    return fehler


def _gegen_kopie(f: dict, k: dict, p: dict) -> list[str]:
    if f["typ"] != k["typ"]:
        return [f"typ {f['typ']} statt {k['typ']} laut Freigabe"]
    fehler = []
    if sorted(f["features"]) != sorted(k["features"]):
        fehler.append(f"Quellen {sorted(f['features'])} statt {sorted(k['features'])} laut Freigabe")
    if f["typ"] == "muster_linear":
        soll = dict(_richtungen(k))
        if len(soll) != len(_richtungen(f)):
            fehler.append("Zahl der Richtungen weicht von der Freigabe ab")
        for i, r in _richtungen(f):
            if i not in soll:
                continue
            if r["anzahl"] != soll[i]["anzahl"]:
                fehler.append(f"anzahl Richtung {i}: {r['anzahl']} statt {soll[i]['anzahl']} laut Freigabe")
            a, a_soll = auswerten(r["abstand"], p), auswerten(soll[i]["abstand"], p)
            if abs(a - a_soll) > _TOL_KANTE_MM:
                fehler.append(f"abstand Richtung {i}: {a:g} statt {a_soll:g} laut Freigabe")
            if (r["achse"], bool(r.get("umkehren"))) != (soll[i]["achse"], bool(soll[i].get("umkehren"))):
                fehler.append(f"Richtung {i}: Achse oder Umkehrung weicht von der Freigabe ab")
    elif f["typ"] == "muster_kreis":
        w, w_soll = auswerten(f.get("winkel", 360), p), auswerten(k.get("winkel", 360), p)
        if (f["anzahl"], f["achse"]) != (k["anzahl"], k["achse"]) or abs(w - w_soll) > _TOL_KANTE_GRAD:
            fehler.append("anzahl, achse oder winkel weicht von der Freigabe ab")
    elif f["ebene"] != k["ebene"]:
        fehler.append(f"Spiegelebene {f['ebene']} statt {k['ebene']} laut Freigabe")
    return fehler


def kanten_abweichungen(f_kopie: dict, ist: dict | str | None, p: dict) -> list[str]:
    """Paket Konstruktionsstil: Verrundungsradius bzw. Fasenmaß aus der Feature-Definition gegen die freigegebene Kopie
    (Knoten verrundung/fase oder Feld fase einer Bohrung → Feature <id>_fase)."""
    if not isinstance(ist, dict):
        return [ist or "fehlt im Teil"]
    if f_kopie["typ"] == "verrundung":
        soll = {"radius": (auswerten(f_kopie["radius"], p), _TOL_KANTE_MM)}
    elif f_kopie["typ"] == "fase":
        soll = {"abstand": (auswerten(f_kopie["abstand"], p), _TOL_KANTE_MM),
                "winkel": (auswerten(f_kopie.get("winkel", 45), p), _TOL_KANTE_GRAD)}
    else:
        soll = {"abstand": (fase_abstand(f_kopie, p), _TOL_KANTE_MM), "winkel": (45.0, _TOL_KANTE_GRAD)}
    fehler = []
    for name, (wert, tol) in soll.items():
        if ist.get(name) is None or abs(ist[name] - wert) > tol:
            fehler.append(f"{name}: ist {ist.get(name)} statt {round(wert, 6):g}" if ist.get(name) is None
                          else f"{name}: ist {ist[name]:g} statt {round(wert, 6):g}")
    if not ist.get("flaechen"):
        fehler.append("keine Fläche")
    return fehler


def kanten_soll(spec: dict) -> dict[str, dict]:
    """Feature-Name → Knoten der Spec, deren Kantenmaß `swki pruefen` misst."""
    aus = {}
    for f in spec["features"]:
        if f["typ"] in ("fase", "verrundung"):
            aus[f["id"]] = f
        elif f["typ"] in ("bohrung", "normbohrung") and "fase" in f:
            aus[f"{f['id']}_fase"] = f
    return aus


def _bohrbild_schluessel(f: dict, p: dict) -> str:
    ende = "durch" if f.get("durch") else f"Tiefe {auswerten(f['tiefe'], p):g}"
    if f["typ"] == "normbohrung":
        gewinde = f"/{auswerten(f['gewindetiefe'], p):g}" if "gewindetiefe" in f else ""
        norm = "" if norm_von(f) == "ISO" else f" {norm_von(f)}"
        return f"{f['art']} {groesse_text(f['groesse'])}{norm} {ende}{gewinde}"
    senkung = ""
    if "senkung" in f:
        senkung = f" Senkung {auswerten(f['senkung']['durchmesser'], p):g}x{auswerten(f['senkung']['tiefe'], p):g}"
    return f"bohrung Ø{auswerten(f['durchmesser'], p):g} {ende}{senkung}"


def bohrbild(spec: dict) -> dict[str, int]:
    """Instanzen (Positionen und Musterkopien) je Bohrungsart, -größe und -tiefe."""
    p = spec.get("parameter", {})
    aus: dict[str, int] = {}
    for f in spec["features"]:
        if f["typ"] in ("bohrung", "normbohrung"):
            k = _bohrbild_schluessel(f, p)
            aus[k] = aus.get(k, 0) + anzahl_instanzen(spec, f["id"])
    return aus


def bohrbild_abweichungen(kopie: dict, aktuell: dict) -> list[str]:
    """Paket Konstruktionsstil: Bohrbilder nach Wirkung – je Art, Größe und Tiefe dieselbe Instanzzahl wie in der
    freigegebenen Kopie, gleich ob als Positionen oder als Muster gebaut."""
    soll, ist = bohrbild(kopie), bohrbild(aktuell)
    fehler = [f"{k}: {ist.get(k, 0)} Instanzen statt {n} laut Freigabe" for k, n in soll.items() if ist.get(k, 0) != n]
    return fehler + [f"{k}: {n} Instanzen, nicht in der Freigabe" for k, n in ist.items() if k not in soll]


def _formmuster(spec: dict) -> list[dict]:
    """Muster und Spiegelungen, die keine Bohrung tragen."""
    bohrungen = [f["id"] for f in spec["features"] if f["typ"] in ("bohrung", "normbohrung")]
    getragen = {t for b in bohrungen for t in traeger(spec, b)}
    return [f for f in spec["features"] if f["typ"] in MUSTER and f["id"] not in getragen]


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


def gleichungen_eintrag(spec: dict, standard: dict, anzahl: int) -> dict | None:
    """Spec Bemaßungsbezug §4: ohne Schalter gleichungen (gleichungen_an) darf das Dokument keine Gleichungen und globalen
    Variablen haben; mit Schalter gibt es den Prüfpunkt nicht. Gilt für Teil und Baugruppendokument."""
    if gleichungen_an(spec, standard):
        return None
    if anzahl == 0:
        return eintrag("gleichungen", True, ist=0, knoten=[])
    return eintrag("gleichungen", False, ist=anzahl, knoten=[], hinweis=f"GLEICHUNGEN_VORHANDEN: {anzahl} Gleichungen")


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
    aktuell_nach_id = {f["id"]: f for f in spec["features"]}
    soll_normbohrungen = [f for f in soll_spec["features"] if f["typ"] == "normbohrung"]
    if soll_normbohrungen:
        p_soll = soll_spec.get("parameter", {})
        abweichend = {}
        for f in soll_normbohrungen:
            ist = m.normbohrungen.get(f["id"])
            jetzt = aktuell_nach_id.get(f["id"])
            if jetzt is not None and jetzt["typ"] == "normbohrung":
                f = {**f, "positionen": jetzt["positionen"]}  # Positionen sind Bauweg; ihre Wirkung prüft bohrbild
            if not isinstance(ist, dict):
                abweichend[f["id"]] = [ist or f"Feature {f['id']} fehlt im Teil"]
            elif fehler := normbohrung_abweichungen(f, ist, p_soll):
                abweichend[f["id"]] = fehler
        ergebnisse.append(eintrag("normbohrungen", not abweichend, ist=abweichend, knoten=sorted(abweichend)))

    aktuell = {f["id"]: f for f in spec["features"]}
    kopie_form = {f["id"]: f for f in _formmuster(soll_spec)} if freigegeben is not None else {}
    muster_ids = [f["id"] for f in spec["features"] if f["typ"] in MUSTER] + [i for i in kopie_form if i not in aktuell]
    if muster_ids:
        abweichend = {}
        for mid in muster_ids:
            if fehler := muster_abweichungen(aktuell.get(mid), kopie_form.get(mid), m.muster.get(mid), p):
                abweichend[mid] = fehler
        ergebnisse.append(eintrag("muster", not abweichend, ist=abweichend, knoten=sorted(abweichend)))

    if soll_kanten := kanten_soll(soll_spec):
        p_soll = soll_spec.get("parameter", {})
        abweichend = {}
        for name, f in soll_kanten.items():
            if fehler := kanten_abweichungen(f, m.kanten.get(name), p_soll):
                abweichend[f["id"]] = fehler
        ergebnisse.append(eintrag("kanten", not abweichend, ist=abweichend, knoten=sorted(abweichend)))

    if any(f["typ"] in ("bohrung", "normbohrung") for f in [*soll_spec["features"], *spec["features"]]):
        fehler = bohrbild_abweichungen(soll_spec, spec)
        ergebnisse.append(eintrag("bohrbild", not fehler, ist=fehler, knoten=[]))

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

    if (e := gleichungen_eintrag(spec, standard, m.gleichungen)) is not None:
        ergebnisse.append(e)

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
        ergebnisse.append(mass_eintrag(mp, m.messpunkte, auswerten(mp["soll"], p), mp.get("tol", _TOL_MASS),
                                       sorted({x["feature"] for x in (mp["von"], mp["zu"]) if "feature" in x})))

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
