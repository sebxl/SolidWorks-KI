"""Bewertung einer Baugruppe (Spec 3b §9) ohne SolidWorks: Messwerte → Prüfungen und Mängel mit Knoten-IDs
(Instanz-, Verknüpfungs- oder Teil-Knoten wie "deckelschraube.2", "v11.1", "deckel/f4")."""

from dataclasses import dataclass, field

from swki.baugruppe.aufloesen import basis, instanzen, verknuepfungen
from swki.baugruppe.geometrie import einschraublaenge, ueberlappung_soll
from swki.baugruppe.kopplung import eingriff, in_baugruppe, kopplungen, teilkreise, verzahnung_der_seite
from swki.baugruppe.modell import Quelle, dokument_name
from swki.compiler.anker import punkt_achse_abstand
from swki.pruefung.bewertung import beschreibung, eintrag, messpunkt_schluessel
from swki.pruefung.geometrie import Messgeometrie, NichtMessbar, abstand
from swki.spec.ausdruck import auswerten
from swki.spec.normen import norm_von, normmasse

STATUS_TEXT = {1: "unbekannt", 2: "unterbestimmt", 3: "voll bestimmt", 4: "überbestimmt", 5: "keine Lösung",
               6: "ungültige Lösung", 7: "Lösen ausgeschaltet"}  # swConstrainedStatus_e
VOLL_BESTIMMT, UNTERBESTIMMT, UEBERBESTIMMT = 3, 2, 4
TOL_GEWINDE_PROZENT = 1.0  # Spike S12 Zeile 9
TOL_LAENGE = 0.01
TOL_UEBERSETZUNG = 1e-6  # relativ, zurückgelesene Übersetzung (Spec 4b §5.5)
_TOL_HUELLQUADER = 0.01
_TOL_MASS = 0.01


@dataclass
class BaugruppenMesswerte:
    rebuild_fehler: list[str]
    verknuepfungen: dict[str, int]
    komponenten: dict[str, dict]
    stueckliste: dict[str, int]
    interferenzen: list[dict]
    box: list[float]
    masse_kg: float
    eigenschaften: dict[str, str] = field(default_factory=dict)
    messpunkte: dict[str, Messgeometrie | str] = field(default_factory=dict)
    schrauben: dict[str, Messgeometrie | str] = field(default_factory=dict)
    gewindebohrungen: list[dict] = field(default_factory=list)
    teilberichte: dict[str, dict] = field(default_factory=dict)
    lagen: dict[str, list[float]] = field(default_factory=dict)       # Instanz-ID → Transform2.ArrayData (Spec 4b §5.5)
    kopplungen: dict[str, dict | str] = field(default_factory=dict)   # Kopplungs-ID → gelesene Werte oder Fehlertext
    unterdrueckt: list[str] = field(default_factory=list)             # unterdrückte Verknüpfungen (Spec 4b §5.5)


@dataclass
class Gewindepaarung:
    schraube: str
    teil: str
    feature: str
    instanz: int
    kopfauflage: Messgeometrie
    eintritt: Messgeometrie


def gewindepaarungen(schrauben: dict, bohrungen: list[dict], tol_mm: float) -> list[Gewindepaarung]:
    """Gepaart sind Schraube und Gewindebohrung, deren Eintrittspunkt auf der Schraubenachse liegt (Präzisierung 1)."""
    paare = []
    for sid, ebene in schrauben.items():
        if isinstance(ebene, str):
            continue
        for b in bohrungen:
            if punkt_achse_abstand(b["eintritt"].punkt, ebene.punkt, ebene.richtung) <= tol_mm:
                paare.append(Gewindepaarung(sid, b["teil"], b["feature"], b["instanz"], ebene, b["eintritt"]))
    return paare


def stueckliste_soll(spec: dict, quellen: dict[str, Quelle], auftrag: str, standard: dict) -> dict[str, int]:
    soll = {}
    for i in instanzen(spec, quellen):
        name = dokument_name(quellen[i.komponente], auftrag, standard)
        soll[name] = soll.get(name, 0) + 1
    return soll


def _stueckliste_abweichungen(ist: dict[str, int], soll: dict[str, int]) -> dict[str, dict]:
    """Dateinamen schreibungsunabhängig vergleichen: SolidWorks liefert bei Eigenteilen ".SLDPRT" (Spike S12 Zeile 14),
    der Soll-Name steht mit ".sldprt". Gemeldet wird unter dem Soll-Namen, Fremdes unter dem Namen aus SolidWorks."""
    ist_zaehler: dict[str, int] = {}
    for n, c in ist.items():
        ist_zaehler[n.casefold()] = ist_zaehler.get(n.casefold(), 0) + c
    soll_namen = {n.casefold() for n in soll}
    abweichend = {n: {"ist": ist_zaehler.get(n.casefold(), 0), "soll": s} for n, s in soll.items()
                  if ist_zaehler.get(n.casefold(), 0) != s}
    abweichend |= {n: {"ist": ist_zaehler[n.casefold()], "soll": 0} for n in ist if n.casefold() not in soll_namen}
    return abweichend


def _paar(a: str, b: str) -> frozenset:
    return frozenset((a, b))


def _gewinde(g: Gewindepaarung, quellen: dict[str, Quelle], m: BaugruppenMesswerte) -> tuple[dict, dict] | None:
    qs, qt = quellen[basis(g.schraube)], quellen[basis(g.teil)]
    f = next(x for x in qt.spec["features"] if x["id"] == g.feature)
    laenge = einschraublaenge(qs.laenge, g.kopfauflage, g.eintritt)
    ist = sum(i["volumen"] for i in m.interferenzen if frozenset(i["paar"]) == _paar(g.schraube, g.teil))
    if laenge <= 0 and ist == 0:
        return None  # die Schraube erreicht diese Bohrung nicht
    pid, knoten = f"gewinde:{g.schraube}", [g.schraube, g.teil]
    bericht = {"schraube": g.schraube, "teil": g.teil, "bohrung": f"{g.feature}.{g.instanz}",
               "einschraublaenge": round(laenge, 3), "volumen": round(ist, 3)}
    if f.get("durch"):
        return eintrag(pid, None, ist=round(ist, 3), einschraublaenge=round(laenge, 3), knoten=knoten,
                         hinweis="Gewinde durch: Volumen nicht geprüft (Präzisierung 2)"), bericht
    tp = qt.spec.get("parameter", {})
    tiefe, gewindetiefe = auswerten(f["tiefe"], tp), auswerten(f["gewindetiefe"], tp)
    kernloch = normmasse("gewinde", f["groesse"], norm_von(f))["kernloch"]
    soll = ueberlappung_soll(qs.masse["d"], qs.masse["p"], kernloch, laenge)
    bericht |= {"soll": round(soll, 3), "gewindetiefe": gewindetiefe, "tiefe": tiefe}
    daten = {"ist": round(ist, 3), "soll": round(soll, 3), "einschraublaenge": round(laenge, 3),
             "gewindetiefe": gewindetiefe, "tiefe": tiefe, "knoten": knoten}
    ok = abs(ist - soll) <= soll * TOL_GEWINDE_PROZENT / 100
    if laenge > min(gewindetiefe, tiefe) + TOL_LAENGE:
        ok = False
        daten["hinweis"] = (f"Einschraublänge {laenge:.2f} mm größer als Gewindetiefe {gewindetiefe:g} bzw. "
                            f"Bohrtiefe {tiefe:g} mm")
    return eintrag(pid, ok, **daten), bericht


def _erlaubt_unterbestimmt(spec: dict, instanz_id: str) -> bool:
    fg = spec.get("freiheitsgrade", {})
    k = basis(instanz_id)
    gruppe = next((x.get("gruppe") for x in spec["komponenten"] if x["id"] == k), None)
    return any(fg.get(s) in ("unterbestimmt", 1, "gekoppelt") for s in (instanz_id, k, gruppe) if s)  # Spec 4a §8.1, 4b §5.5


def _bestimmtheit(spec: dict, quellen: dict[str, Quelle], m: BaugruppenMesswerte) -> dict:
    fix = {k["id"] for k in spec["komponenten"] if k.get("fixiert")}
    offen = {}
    for i in instanzen(spec, quellen):
        w = m.komponenten.get(i.id)
        if w is None:
            grund = "fehlt in der Baugruppe"
        elif i.komponente in fix:
            # Status der fixierten Komponente ist sonst beliebig (Spike S12 Zeile 7: 3); überbestimmt ist immer ein Mangel
            grund = ("nicht fixiert" if not w["fixiert"]
                     else STATUS_TEXT[UEBERBESTIMMT] if w["status"] == UEBERBESTIMMT else None)
        elif w["fixiert"]:
            grund = "unerwartet fixiert"
        elif w["status"] == VOLL_BESTIMMT or (w["status"] == UNTERBESTIMMT and _erlaubt_unterbestimmt(spec, i.id)):
            grund = None
        else:
            grund = STATUS_TEXT.get(w["status"], str(w["status"]))
        if grund:
            offen[i.id] = grund
    return eintrag("bestimmtheit", not offen, ist=offen, knoten=sorted(offen))


def _verknuepfungen(spec: dict, quellen: dict[str, Quelle], m: BaugruppenMesswerte) -> dict:
    soll = [v.id for v in verknuepfungen(spec, quellen)]
    fehlend = [n for n in soll if n not in m.verknuepfungen]
    fehlerhaft = {n: c for n, c in m.verknuepfungen.items() if c} | {n: "unterdrückt" for n in m.unterdrueckt}
    fremd = [n for n in m.verknuepfungen if n not in soll]
    knoten = sorted({*fehlend, *fehlerhaft, *fremd})
    return eintrag("verknuepfungen", not knoten, ist={"fehlend": fehlend, "fehlerhaft": fehlerhaft, "fremd": fremd},
                     soll=len(soll), knoten=knoten)


def _eingriff(spec: dict, quellen: dict[str, Quelle], m: BaugruppenMesswerte, tol_mm: float) -> tuple[list[dict], list[dict]]:
    """Spec 4b §5.5: je Kopplung eingriff:<id> – Achslage, Achsabstand, Breitenüberdeckung, Wälzpunkt auf der Zahnstange
    und die zurückgelesene Übersetzung bzw. der Teilkreis. Fehlt die Kopplung im Modell, meldet das verknuepfungen;
    hier zählt dann nur die Geometrie. Dazu je Kopplung eine Zeile für den Prüfbericht."""
    pruefungen, bericht = [], []
    for v in kopplungen(spec):
        pid, ka, kb = f"eingriff:{v['id']}", v["a"]["komponente"], v["b"]["komponente"]
        if ka not in m.lagen or kb not in m.lagen:
            pruefungen.append(eintrag(pid, False, hinweis="Komponente fehlt in der Baugruppe", knoten=[v["id"]]))
            continue
        a = in_baugruppe(verzahnung_der_seite(quellen, v["a"]), m.lagen[ka])
        b = in_baugruppe(verzahnung_der_seite(quellen, v["b"]), m.lagen[kb])
        ist = eingriff(a, b)
        gruende = []
        if not ist["achsen_parallel"]:
            gruende.append("Achsen nicht parallel" if v["typ"] == "zahnrad" else "Radachse nicht senkrecht zur Zahnstange")
        if abs(ist["achsabstand"] - ist["soll"]) > tol_mm:
            gruende.append(f"Achsabstand {ist['achsabstand']:g} statt {ist['soll']:g} mm")
        if ist["ueberdeckung"] <= 0:
            gruende.append("Zahnbreiten überdecken sich nicht")
        if not ist["im_bereich"]:
            gruende.append("Wälzpunkt außerhalb der Zahnstange")
        zaehler, nenner = teilkreise(a.geo, b.geo)
        gelesen = m.kopplungen.get(v["id"])
        if isinstance(gelesen, str):
            gruende.append(gelesen)
        elif isinstance(gelesen, dict) and v["typ"] == "zahnrad":
            # lagenunabhängig: SolidWorks liefert Zähler und Nenner vertauscht zurück (Spike S14b Zeile 6)
            soll_u = min(zaehler, nenner) / max(zaehler, nenner)
            ist_u = min(gelesen["zaehler"], gelesen["nenner"]) / max(gelesen["zaehler"], gelesen["nenner"])
            if abs(ist_u - soll_u) > TOL_UEBERSETZUNG * soll_u:
                gruende.append(f"Übersetzung {gelesen['zaehler']:g}:{gelesen['nenner']:g} statt {zaehler:g}:{nenner:g}")
        elif isinstance(gelesen, dict) and abs(gelesen["durchmesser"] - zaehler) > tol_mm:
            gruende.append(f"Teilkreis {gelesen['durchmesser']:g} statt {zaehler:g} mm")
        pruefungen.append(eintrag(pid, not gruende, ist={**ist, "kopplung": gelesen}, knoten=[v["id"]] if gruende else [],
                                  **({"hinweis": "; ".join(gruende)} if gruende else {})))
        bericht.append({"kopplung": v["id"], "typ": v["typ"], "a": ka, "b": kb,
                        "soll": f"{zaehler:g}:{nenner:g}" if v["typ"] == "zahnrad" else f"Ø {zaehler:g}",
                        "gelesen": gelesen, "achsabstand": ist["achsabstand"], "achsabstand_soll": ist["soll"],
                        "ueberdeckung": ist["ueberdeckung"]})
    return pruefungen, bericht


def _masse_pruefen(pr: dict, p: dict, m: BaugruppenMesswerte) -> list[dict]:
    ergebnisse = []
    for mp in pr.get("masse_pruefen", []):
        pid = f"mass:{mp['was']}"
        von, zu = m.messpunkte.get(messpunkt_schluessel(mp["von"])), m.messpunkte.get(messpunkt_schluessel(mp["zu"]))
        knoten = sorted({x["komponente"] for x in (mp["von"], mp["zu"]) if "komponente" in x})
        soll, tol = auswerten(mp["soll"], p), mp.get("tol", _TOL_MASS)
        if not isinstance(von, Messgeometrie) or not isinstance(zu, Messgeometrie):
            hinweis = next((x for x in (von, zu) if isinstance(x, str)), "Messpunkt fehlt")
            ergebnisse.append(eintrag(pid, False, soll=soll, hinweis=hinweis, knoten=knoten))
            continue
        try:
            ist = round(abstand(von, zu), 6)
        except NichtMessbar as e:
            ergebnisse.append(eintrag(pid, False, soll=soll, hinweis=str(e), knoten=knoten))
            continue
        ergebnisse.append(eintrag(pid, abs(ist - soll) <= tol, ist=ist, soll=soll, tol=tol, knoten=knoten))
    return ergebnisse


def bewerte_baugruppe(spec: dict, quellen: dict[str, Quelle], m: BaugruppenMesswerte, standard: dict,
                      soll_stueckliste: dict[str, int]) -> dict:
    p = spec.get("parameter", {})
    pr = spec.get("pruefung", {})
    ergebnisse = [eintrag("rebuild", not m.rebuild_fehler, ist=m.rebuild_fehler, knoten=[]),
                  _verknuepfungen(spec, quellen, m), _bestimmtheit(spec, quellen, m)]

    abweichend = _stueckliste_abweichungen(m.stueckliste, soll_stueckliste)
    ergebnisse.append(eintrag("stueckliste", not abweichend, ist=abweichend, knoten=[]))

    gewinde_bericht, gepaart = [], set()
    for sid, ebene in m.schrauben.items():
        if isinstance(ebene, str):
            ergebnisse.append(eintrag(f"gewinde:{sid}", False, hinweis=ebene, knoten=[sid]))
    for g in gewindepaarungen(m.schrauben, m.gewindebohrungen, standard["toleranzen"]["anker_mm"]):
        if (e := _gewinde(g, quellen, m)) is not None:
            ergebnisse.append(e[0])
            gewinde_bericht.append(e[1])
            gepaart.add(_paar(g.schraube, g.teil))
    kollisionen = [i for i in m.interferenzen if frozenset(i["paar"]) not in gepaart]
    ergebnisse.append(eintrag("kollision", not kollisionen, ist=kollisionen,
                                knoten=sorted({k for i in kollisionen for k in i["paar"]})))
    eingriffe, kopplungsbericht = (_eingriff(spec, quellen, m, standard["toleranzen"]["verzahnung_mm"])
                                   if kopplungen(spec) else ([], []))
    ergebnisse += eingriffe

    if "huellquader" in pr:
        soll = [auswerten(v, p) for v in pr["huellquader"]]
        ist = [round(m.box[i + 3] - m.box[i], 6) for i in range(3)]
        tol = pr.get("huellquader_tol", _TOL_HUELLQUADER)
        ergebnisse.append(eintrag("huellquader", all(abs(a - b) <= tol for a, b in zip(ist, soll)), ist=ist,
                                    soll=soll, tol=tol, knoten=[]))
    if "masse" in pr:
        soll = auswerten(pr["masse"]["soll"], p)
        prozent = pr["masse"].get("toleranz_prozent", standard["toleranzen"]["volumen_prozent"])
        abw = abs(m.masse_kg - soll) / soll * 100
        ergebnisse.append(eintrag("masse", abw <= prozent, ist=round(m.masse_kg, 4), soll=soll,
                                    abweichung_prozent=round(abw, 4), tol_prozent=prozent, knoten=[]))
    ergebnisse += _masse_pruefen(pr, p, m)
    soll_eig = spec.get("eigenschaften", {})
    abw_eig = {k: m.eigenschaften.get(k) for k, v in soll_eig.items() if m.eigenschaften.get(k) != v}
    ergebnisse.append(eintrag("eigenschaften", not abw_eig, ist=abw_eig, soll=soll_eig, knoten=[]))

    teilpruefungen = {}
    for datei in dict.fromkeys(q.datei for q in quellen.values() if q.art == "teil"):
        if datei not in m.teilberichte:  # fail-closed: ohne Teilbericht gibt es keine Aussage über das Teil
            komp = next(k for k, q in quellen.items() if q.datei == datei)
            ergebnisse.append(eintrag(f"{komp}: teilbericht", False, knoten=[komp],
                                        hinweis=f"kein Teilbericht für {datei} (Teilprüfung nicht gelaufen)"))
            teilpruefungen[komp] = {"bestanden": False, "maengel": 1}
    for datei, tb in m.teilberichte.items():
        komp = next(k for k, q in quellen.items() if q.datei == datei)
        teilpruefungen[komp] = {"bestanden": tb["bestanden"], "maengel": len(tb["maengel"])}
        ergebnisse += [{**e, "id": f"{komp}: {e['id']}", "knoten": [f"{komp}/{k}" for k in e["knoten"]] or [komp]}
                       for e in tb["pruefungen"]]

    maengel = [{"pruefung": e["id"], "knoten": e["knoten"], "beschreibung": beschreibung(e)}
               for e in ergebnisse if e["ok"] is False]
    return {"bestanden": not maengel, "pruefungen": ergebnisse, "maengel": maengel, "stueckliste": m.stueckliste,
            "gewindepaarungen": gewinde_bericht, "teilpruefungen": teilpruefungen, "masse_kg": round(m.masse_kg, 4),
            **({"kopplungen": kopplungsbericht} if kopplungsbericht else {})}
