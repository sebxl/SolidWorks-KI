"""Vergleich vorher/nachher ohne Geometrie (Spec Bestandsdateien §7.1): der halbe Präzisionsschutz.

Reine Logik über zwei Aufnahmen im Format `bestand.json` (Bestandskopie und Lauf, beide von `lies_bestand` gelesen), ohne
SolidWorks. Die Einträge haben das Format `swki.pruefung.bewertung.eintrag`; `ok: False` ist ein Mangel, `ok: None` heißt
„nicht nachgewiesen" (kein Mangel, aber auch kein Bestanden). Grundsatz: Ein Fehlalarm kostet eine Rückfrage, ein falsches
`ok: True` die Datei des Kollegen. Geprüft wird je Konfiguration; die Unterschiede, die die Punkte der Änderungs-Spec erlauben,
sind ausdrücklich ausgenommen, alles andere ist ein Mangel.

`None` als Wert heißt: Lesen gescheitert (auch unterdrückte Maße liefern Zahlen, S18b). Es ist nie „keine Änderung", sondern
macht den Eintrag `ok: None`; ein vorhandener Mangel hat Vorrang.

Annahmen, die live noch zu bestätigen sind (Task 11):
- Folgen eines `mass`-Punkts (Gruppenpartner, Gleichungsfolgen) gelten nur in den Konfigurationen des Punkts; ein Gruppenpartner
  muss dort den Zielwert tragen. `gleichung`-Punkte wirken auf alle Konfigurationen.
- Unterdrücken nimmt Kinder und die Skizzen mit, deren Kinder alle betroffen sind (S18c: Grundplatte → Tasche, Fase), nur
  False→True; Aufheben nur das Feature und seine eigenen Skizzen, nur True→False (die Kinder bleiben unterdrückt).
- Neue Features erklärt nur ein `feature`-Punkt: sein `name`, die Namen, die `_neuer_name` im Bau daraus macht (`Name Skizze`,
  `Name Senkung`, `Name Senkung Skizze`), und die Unterfeatures (`unter`) des neuen Features. Bei `skript`-Punkten bleiben unerklärbare neue
  Features `ok: None`, außer `bauen(ctx)` hat sie zurückgegeben (`skript_features`, aus dem Protokoll).
- Optional trägt `datei.ordner` in beiden Aufnahmen den Ordner der Datei (setzt der Aufrufer); nur damit lassen sich externe
  Referenzen über den Pfad (relativ zum Ordner) vergleichen.
"""

from dataclasses import dataclass, field

from swki.bestand.folgen import folgen_von, gleicher_ausdruck, kinder_von, rechte_seite
from swki.compiler.eigenschaften import material_passt
from swki.pruefung.bewertung import eintrag
from swki.spec.ausdruck import auswerten

TOL = 1e-6  # mm bzw. Grad; die Aufnahme rundet auf 6 Stellen, die Reserve fängt Gleitkomma-Rauschen ab

# swConstrainedStatus_e (swki api enum): 1 Unknown, 2 UnderConstrained, 3 FullyConstrained, 4 OverConstrained, 5 NoSolution,
# 6 InvalidSolution, 7 AutosolveOff. Größer = besser bestimmt. Überbestimmt (Widerspruch) steht unter unterbestimmt: Eine Skizze,
# die durch die Änderung widersprüchlich wird, ist schlechter, auch wenn sie vorher unterbestimmt war.
SKIZZE_RANG = {6: 0, 5: 0, 4: 1, 1: 2, 7: 2, 2: 3, 3: 4}


def neue_fehler(fehler: list[dict], aufnahme: dict, konfiguration: str) -> list[str]:
    """Was die Aufnahme nicht kennt, als Tripel (Konfiguration, Feature, Code): Auch ein anderer Code am selben Feature ist neu.
    Warnungen zählen hier nicht (`neue_warnungen`)."""
    bekannt = {(e["konfiguration"], e["feature"], e["code"]) for e in aufnahme["neuaufbau"] if not e["warnung"]}
    return [f"{e['feature']}: Code {e['code']}" for e in fehler
            if not e["warnung"] and (konfiguration, e["feature"], e["code"]) not in bekannt]


def neue_warnungen(warnungen: list[dict], aufnahme: dict, konfiguration: str) -> list[str]:
    """Wie `neue_fehler`, für Warnungen: Dasselbe Tripel als Warnung und als Fehler sind zwei Einträge."""
    bekannt = {(e["konfiguration"], e["feature"], e["code"]) for e in aufnahme["neuaufbau"] if e["warnung"]}
    return [f"{e['feature']}: Warnung {e['code']}" for e in warnungen
            if e["warnung"] and (konfiguration, e["feature"], e["code"]) not in bekannt]


def _gleich(a: float, b: float) -> bool:
    return abs(a - b) <= TOL + 1e-12


def _gleiche_gleichung(a: str, b: str) -> bool:
    """Text gleich bis auf Leerzeichen; zwei reine Zahlen auf der rechten Seite vergleichen sich als Zahlen."""
    if gleicher_ausdruck(a, b):
        return True
    try:
        return _gleich(float(rechte_seite(a)), float(rechte_seite(b)))
    except ValueError:
        return False


def _norm(pfad: str) -> str:
    return pfad.replace("\\", "/").casefold()


def _basis(pfad: str) -> str:
    return _norm(pfad).rsplit("/", 1)[-1]


@dataclass
class _Vergleich:
    punkte: list[dict]
    vorher: dict
    nachher: dict
    parameter: dict
    skript_gelaufen: frozenset[str] = frozenset()   # Punkt-IDs der Skripte, die laut Protokoll durchliefen
    skript_features: frozenset[str] = frozenset()   # was ihr `bauen(ctx)` zurückgab
    konfigurationen: list[str] = field(init=False)  # die beiden Aufnahmen gemeinsam haben, in der Reihenfolge des Bestands
    geloescht: set[str] = field(init=False)         # was `loeschen`-Punkte nehmen dürfen
    masse_vorher: dict[str, dict] = field(init=False)
    masse_nachher: dict[str, dict] = field(init=False)
    features_nachher: dict[str, dict] = field(init=False)

    def __post_init__(self):
        self.konfigurationen = [k for k in self.vorher["konfigurationen"] if k in self.nachher["konfigurationen"]]
        self.geloescht = _geloeschte(self.punkte, self.vorher)
        self.masse_vorher = {m["name"]: m for m in self.vorher["masse"]}
        self.masse_nachher = {m["name"]: m for m in self.nachher["masse"]}
        self.features_nachher = {f["name"]: f for f in self.nachher["features"]}

    def konfig(self, p: dict) -> list[str]:
        """Die Konfigurationen des Punkts, soweit der Lauf sie noch hat (fehlende meldet `konfigurationen`)."""
        k = p.get("konfigurationen", "alle")
        return [x for x in self.vorher["konfigurationen"] if k == "alle" or x in k]

    def punkte_vom_typ(self, *typen: str) -> list[dict]:
        return [p for p in self.punkte if p["typ"] in typen]


def _eigene_skizzen(namen: set[str], vorher: dict) -> set[str]:
    """Skizzen, die Eltern der genannten Features sind und kein Kind außerhalb davon haben (eine geteilte Skizze geht nicht mit)."""
    features = {f["name"]: f for f in vorher["features"]}
    return {e for n in namen for e in features.get(n, {}).get("eltern", ())
            if features.get(e, {}).get("typ") == "ProfileFeature" and set(features[e].get("kinder", ())) <= namen}


def _geloeschte(punkte: list[dict], vorher: dict) -> set[str]:
    """Features, die verschwinden dürfen: die der `loeschen`-Punkte samt `kinder` und die Skizzen, die dann kein anderes Kind
    mehr haben (`DeleteSelection2(3)` nimmt die aufgenommene Skizze mit, S18c)."""
    weg = {n for p in punkte if p["typ"] == "loeschen" for n in (p["feature"], *p.get("kinder", ()))}
    return weg | _eigene_skizzen(weg, vorher)


def _materialien(aufnahme: dict) -> dict[str, str]:
    return aufnahme.get("materialien") or {aufnahme["aktiv"]: aufnahme.get("material", "")}


# ---------------------------------------------------------------------------------------------------------------- Punkte

def _punkt_mass(p: dict, c: _Vergleich) -> dict:
    """Das Maß steht in den genannten Konfigurationen auf `neu`, ebenso jeder Gruppenpartner (verknüpfte Maße teilen den Wert).
    Falsch hat Vorrang; ein nicht lesbarer Wert ist `None`, nie „stimmt"."""
    pid, neu = f"punkt:{p['id']}", auswerten(p["neu"], c.parameter)
    m = c.masse_nachher.get(p["mass"])
    if m is None:
        return eintrag(pid, False, soll=neu, hinweis=f"Maß {p['mass']} fehlt nach der Änderung", knoten=[p["id"]])
    konfigurationen = c.konfig(p)
    ist = {k: m["werte"].get(k) for k in konfigurationen}
    gruppe = c.masse_vorher.get(p["mass"], {}).get("gruppe")
    partner = sorted(n for n, v in c.masse_vorher.items() if gruppe and v.get("gruppe") == gruppe and n != p["mass"])
    werte = {p["mass"]: ist} | {n: {k: c.masse_nachher.get(n, {"werte": {}})["werte"].get(k) for k in konfigurationen}
                                for n in partner}
    falsch = [f"{n} steht auf {v:g} ({k})" for n, vs in werte.items() for k, v in vs.items() if v is not None and not _gleich(v, neu)]
    if falsch:
        return eintrag(pid, False, ist=ist, soll=neu, knoten=[p["id"]], hinweis="; ".join(falsch) + f" statt {neu:g}")
    if unlesbar := [f"{n} ({k})" for n, vs in werte.items() for k, v in vs.items() if v is None]:
        return eintrag(pid, None, ist=ist, soll=neu, knoten=[p["id"]], hinweis="Nicht lesbar: " + ", ".join(unlesbar))
    return eintrag(pid, True, ist=ist, soll=neu, knoten=[p["id"]])


def _punkt_gleichung(p: dict, c: _Vergleich) -> dict:
    pid = f"punkt:{p['id']}"
    if "variable" in p:
        neu, ist = auswerten(p["neu"], c.parameter), c.nachher["variablen"].get(p["variable"])
        ok = ist is not None and _gleich(float(ist), neu)
        daten = {"ist": ist, "soll": neu, "hinweis": f"Variable {p['variable']} steht auf {ist} statt {neu:g}"}
    else:
        text = next((g["text"] for g in c.nachher["gleichungen"] if g["links"] == p["gleichung"]), None)
        ist = None if text is None else rechte_seite(text)
        ok = ist is not None and gleicher_ausdruck(ist, str(p["neu"]))
        daten = {"ist": ist, "soll": p["neu"], "hinweis": f"Gleichung {p['gleichung']} lautet {ist!r} statt {p['neu']!r}"}
    if ok:
        daten.pop("hinweis")
    return eintrag(pid, ok, **daten, knoten=[p["id"]])


def _punkt_unterdruecken(p: dict, c: _Vergleich) -> dict:
    pid, soll = f"punkt:{p['id']}", p["typ"] == "unterdruecken"
    f = c.features_nachher.get(p["feature"])
    if f is None:
        return eintrag(pid, False, soll=soll, hinweis=f"Feature {p['feature']} fehlt nach der Änderung", knoten=[p["id"]])
    ist = {k: f["unterdrueckt"].get(k) for k in c.konfig(p)}
    zustand = "unterdrückt" if soll else "aufgehoben"
    if falsch := [k for k, v in ist.items() if v is not None and v != soll]:
        return eintrag(pid, False, ist=ist, soll=soll, knoten=[p["id"]],
                       hinweis=f"{p['feature']} ist nicht {zustand} ({', '.join(falsch)})")
    if unlesbar := [k for k, v in ist.items() if v is None]:
        return eintrag(pid, None, ist=ist, soll=soll, knoten=[p["id"]],
                       hinweis=f"Unterdrückung von {p['feature']} nicht lesbar ({', '.join(unlesbar)})")
    return eintrag(pid, True, ist=ist, soll=soll, knoten=[p["id"]])


def _punkt_loeschen(p: dict, c: _Vergleich) -> dict:
    pid, genannt = f"punkt:{p['id']}", [p["feature"], *p.get("kinder", ())]
    noch_da = sorted({n for n in genannt for k in c.konfigurationen if n in c.nachher["reihenfolge"].get(k, ())})
    if noch_da:
        return eintrag(pid, False, ist=noch_da, soll=[], knoten=[p["id"]], hinweis=f"Nicht gelöscht: {', '.join(noch_da)}")
    return eintrag(pid, True, ist=[], soll=[], knoten=[p["id"]])


def _punkt_feature(p: dict, c: _Vergleich) -> dict:
    pid, name = f"punkt:{p['id']}", p["name"]
    alt = {n for k in c.vorher["reihenfolge"].values() for n in k}
    probleme = [f"{name} gibt es schon im Bestand"] if name in alt else []
    for k in c.konfigurationen:
        reihe = c.nachher["reihenfolge"].get(k, [])
        if name not in reihe:
            probleme.append(f"{name} fehlt in {k}")
            continue
        bestand = [n for n in reihe if n in alt and n not in c.geloescht]
        if "nach" in p:
            if p["nach"] not in reihe or reihe.index(name) < reihe.index(p["nach"]):
                probleme.append(f"{name} steht in {k} nicht hinter {p['nach']}")
        elif bestand and reihe.index(name) < max(reihe.index(n) for n in bestand):
            probleme.append(f"{name} steht in {k} nicht am Ende des Baums")
    f = c.features_nachher.get(name)
    if f is not None and (unterdrueckt := sorted(k for k, v in f["unterdrueckt"].items() if v)):
        probleme.append(f"{name} ist unterdrückt ({', '.join(unterdrueckt)})")
    if probleme:
        return eintrag(pid, False, ist=probleme, knoten=[p["id"]], hinweis="; ".join(probleme))
    return eintrag(pid, True, ist=[], knoten=[p["id"]])


def _punkt_material(p: dict, c: _Vergleich) -> dict:
    pid, ist = f"punkt:{p['id']}", _materialien(c.nachher)
    falsch = {k: ist.get(k, "") for k in c.konfigurationen if not material_passt(ist.get(k, ""), p["neu"])}
    if falsch:
        return eintrag(pid, False, ist=falsch, soll=p["neu"], knoten=[p["id"]],
                       hinweis="Material nicht gesetzt: " + ", ".join(f"{v!r} ({k})" for k, v in falsch.items()))
    return eintrag(pid, True, ist=ist, soll=p["neu"], knoten=[p["id"]])


def _eigenschaften_von(aufnahme: dict, wo: str) -> dict:
    e = aufnahme["eigenschaften"]
    return e["datei"] if wo == "" else e["konfiguration"].get(wo, {})


def _punkt_eigenschaft(p: dict, c: _Vergleich) -> dict:
    pid, wo, name = f"punkt:{p['id']}", p.get("konfiguration", ""), p["name"]
    ist = _eigenschaften_von(c.nachher, wo).get(name)
    if ist != p["neu"]:
        return eintrag(pid, False, ist=ist, soll=p["neu"], knoten=[p["id"]],
                       hinweis=f"Eigenschaft {name} steht auf {ist!r} statt {p['neu']!r}")
    return eintrag(pid, True, ist=ist, soll=p["neu"], knoten=[p["id"]])


def _punkt_skript(p: dict, c: _Vergleich) -> dict:
    """Die Wirkung selbst ist nicht prüfbar: Durchgelaufen heißt hier ok, die Differenz je Bereich verlangt `bewerte_bereiche`."""
    if p["id"] in c.skript_gelaufen:
        return eintrag(f"punkt:{p['id']}", True, knoten=[p["id"]], hinweis="Notausgang, Nachweis über Bereiche, masse_pruefen und Prüfer")
    return eintrag(f"punkt:{p['id']}", None, knoten=[p["id"]],
                   hinweis="Notausgang-Skript: Wirkung nicht prüfbar, sie zeigt sich in den übrigen Prüfungen und der Differenz")


_PUNKT = {"mass": _punkt_mass, "gleichung": _punkt_gleichung, "unterdruecken": _punkt_unterdruecken,
          "aufheben": _punkt_unterdruecken, "loeschen": _punkt_loeschen, "feature": _punkt_feature,
          "material": _punkt_material, "eigenschaft": _punkt_eigenschaft, "skript": _punkt_skript}


def _punkt(p: dict, c: _Vergleich) -> dict:
    funktion = _PUNKT.get(p["typ"])
    if funktion is None:
        return eintrag(f"punkt:{p['id']}", None, knoten=[p["id"]], hinweis=f"Punkttyp {p['typ']!r} wird nicht verglichen")
    return funktion(p, c)


# ------------------------------------------------------------------------------------------------------------------ Baum

# Endungen, die `_neuer_name` im Bau aus den Handler-IDs `_positionen`/`_skizze`, `_senkung`, `_senkung_skizze` macht (genau diese
# vier Formen samt `Name` selbst; kein Handler hängt Ziffern an, das tut nur das Notausgang-Skript)
_ABGELEITET = {"Skizze", "Senkung", "Senkung Skizze"}


def _abgeleitet(x: str, name: str) -> bool:
    """„Name Skizze", „Name Senkung", „Name Senkung Skizze": was `_neuer_name` im Bau aus den Handler-IDs eines Features macht."""
    return x.startswith(f"{name} ") and x[len(name) + 1:] in _ABGELEITET


def _erklaerte(c: _Vergleich) -> set[str]:
    """Neue Namen, die ein `feature`-Punkt erklärt: sein Name, die abgeleiteten und die Unterfeatures (`unter`) davon; ebenso, was ein
    Skript laut Protokoll zurückgab."""
    punkte = c.punkte_vom_typ("feature")
    namen = {p["name"] for p in punkte} | c.skript_features
    gebaut = {n for reihe in c.nachher["reihenfolge"].values() for n in reihe}
    namen |= {n for n in gebaut if any(_abgeleitet(n, p["name"]) for p in punkte)}
    return namen | {u for f in c.nachher["features"] if f["name"] in namen for u in f.get("unter", ())}


def _baum(c: _Vergleich) -> dict:
    """Gleiche Features in gleicher Reihenfolge, Typ und Eltern wie im Bestand, außer neuen und gelöschten. Neue Features
    erklärt ein `feature`-Punkt oder die Rückgabe eines Skripts (`_erklaerte`); der Notausgang `skript` kann beliebige erzeugen: Was nicht
    erklärbar ist, bleibt dann `ok: None` (`ungeklaert`), ohne `skript` ist es ein Mangel."""
    v, n = c.vorher, c.nachher
    alt = {x for reihe in v["reihenfolge"].values() for x in reihe}
    erklaert, skript = _erklaerte(c), bool(c.punkte_vom_typ("skript"))
    probleme, ungeklaert = [], set()
    for k in c.konfigurationen:
        vor, nach = v["reihenfolge"].get(k, []), n["reihenfolge"].get(k, [])
        soll = [x for x in vor if x not in c.geloescht]
        if fehlt := [x for x in soll if x not in nach]:
            probleme.append({"konfiguration": k, "art": "fehlt", "features": fehlt})
        elif (ist := [x for x in nach if x in set(soll)]) != soll:
            probleme.append({"konfiguration": k, "art": "reihenfolge", "soll": soll, "ist": ist})
        if unerklaert := [x for x in nach if x not in alt and x not in erklaert]:
            if skript:
                ungeklaert |= set(unerklaert)
            else:
                probleme.append({"konfiguration": k, "art": "neu", "features": unerklaert})
    for f in v["features"]:
        g = c.features_nachher.get(f["name"])
        if g is None:
            continue  # fehlt: oben gemeldet
        if g["typ"] != f["typ"]:
            probleme.append({"art": "typ", "feature": f["name"], "soll": f["typ"], "ist": g["typ"]})
        eltern = sorted(e for e in f["eltern"] if e not in c.geloescht)
        if sorted(g["eltern"]) != eltern:
            probleme.append({"art": "eltern", "feature": f["name"], "soll": eltern, "ist": sorted(g["eltern"])})
    if probleme:
        betroffen = sorted({x for q in probleme for x in q.get("features", [q.get("feature")]) if x})
        return eintrag("baum", False, ist=probleme, knoten=[], ungeklaert=sorted(ungeklaert),
                       hinweis="Baum weicht vom Bestand ab: " + (", ".join(betroffen) or "Reihenfolge"))
    if ungeklaert:
        return eintrag("baum", None, ist=[], knoten=[], ungeklaert=sorted(ungeklaert),
                       hinweis="Neue Features, die kein feature-Punkt erklärt (Skript?): " + ", ".join(sorted(ungeklaert)))
    return eintrag("baum", True, ist=[], knoten=[], ungeklaert=[])


# ------------------------------------------------------------------------------------------------------------------ Maße

def _erlaubte_masse(c: _Vergleich) -> dict[str, set[str] | None]:
    """Maß → Konfigurationen, in denen es sich ändern darf (`None` = in allen). Ein `mass`-Punkt wirkt in seinen genannten
    Konfigurationen (Ziel und Folgen), ein `gleichung`-Punkt in allen (SolidWorks setzt sie in allen Konfigurationen); bei
    `gleichung` darf auch die linke Seite selbst abweichen."""
    aus: dict[str, set[str] | None] = {}

    def erlaube(name: str, konfigurationen: set[str] | None) -> None:
        if konfigurationen is None or (name in aus and aus[name] is None):
            aus[name] = None
        else:
            aus[name] = aus.get(name, set()) | konfigurationen

    for p in c.punkte:
        wo = set(c.konfig(p)) if p["typ"] == "mass" else None
        if p["typ"] == "mass":
            erlaube(p["mass"], wo)
        elif p["typ"] == "gleichung":
            erlaube(p.get("variable") or p["gleichung"], None)
        for name in folgen_von(p, c.vorher):
            erlaube(name, wo)
    return aus


def _masse(c: _Vergleich) -> dict:
    """Alle nicht getriebenen Maße außer den erlaubten. `None` auf einer Seite heißt: Lesen gescheitert, also nicht
    nachgewiesen (`ok: None`), und zwar ausnahmslos, auch bei unterdrückten Features und Punkt-Zielen. Zustand und Gruppe
    eines Maßes dürfen sich nicht ändern."""
    erlaubt = _erlaubte_masse(c)
    alt_features = {x for reihe in c.vorher["reihenfolge"].values() for x in reihe}
    abweichungen, fehlt, unlesbar, getrieben, umgestuft = [], [], [], [], []
    for name, m in c.masse_vorher.items():
        n = c.masse_nachher.get(name)
        if n is None:
            if m["feature"] not in c.geloescht:
                fehlt.append(name)
            continue
        for feld in ("zustand", "gruppe"):
            if m.get(feld) != n.get(feld):
                umgestuft.append({"name": name, "feld": feld, "vorher": m.get(feld), "nachher": n.get(feld)})
        ist_getrieben = m.get("zustand") == "getrieben"
        frei = erlaubt.get(name, set())
        verschieden = {}
        for k in c.konfigurationen:
            a, b = m["werte"].get(k), n["werte"].get(k)
            if a is None or b is None:
                if not ist_getrieben:
                    unlesbar.append({"name": name, "konfiguration": k})
            elif not _gleich(a, b):
                verschieden[k] = (a, b)
        if ist_getrieben:
            if verschieden:
                getrieben.append({"name": name, "vorher": {k: a for k, (a, _) in verschieden.items()},
                                  "nachher": {k: b for k, (_, b) in verschieden.items()}})
            continue
        abweichungen += [{"name": name, "konfiguration": k, "vorher": a, "nachher": b}
                         for k, (a, b) in verschieden.items() if frei is not None and k not in frei]
    an_bestand = sorted(x for x, m in c.masse_nachher.items() if x not in c.masse_vorher and m["feature"] in alt_features)
    teile = []
    if abweichungen:
        teile.append("geändert: " + ", ".join(f"{a['name']} ({a['konfiguration']}: {a['vorher']:g} → {a['nachher']:g})"
                                              for a in abweichungen))
    if umgestuft:
        teile.append("Zustand/Gruppe geändert: " + ", ".join(f"{u['name']} ({u['feld']})" for u in umgestuft))
    if fehlt:
        teile.append("fehlen: " + ", ".join(fehlt))
    if an_bestand:
        teile.append("neu an Bestandsfeatures: " + ", ".join(an_bestand))
    daten = {"ist": abweichungen, "fehlen": fehlt, "neu_am_bestand": an_bestand, "umgestuft": umgestuft,
             "getrieben": getrieben, "unlesbar": unlesbar, "knoten": []}
    if teile:
        return eintrag("masse", False, **daten, hinweis="Maße außerhalb der Punkte verändert; " + "; ".join(teile))
    if unlesbar:
        return eintrag("masse", None, **daten, hinweis="Nicht lesbar, also nicht nachgewiesen: "
                       + ", ".join(f"{u['name']} ({u['konfiguration']})" for u in unlesbar))
    return eintrag("masse", True, **daten)


# ---------------------------------------------------------------------------------------------------- Gleichungen u. a.

def _gleichungen(c: _Vergleich) -> dict:
    erlaubt = {p.get("variable") or p["gleichung"] for p in c.punkte_vom_typ("gleichung")}
    vor = {g["links"]: g["text"] for g in c.vorher["gleichungen"]}
    nach = {g["links"]: g["text"] for g in c.nachher["gleichungen"]}
    probleme = [{"links": k, "vorher": vor[k], "nachher": nach.get(k)} for k in vor
                if k not in erlaubt and (k not in nach or not _gleiche_gleichung(vor[k], nach[k]))]
    probleme += [{"links": k, "vorher": None, "nachher": nach[k]} for k in nach if k not in vor]
    if probleme:
        return eintrag("gleichungen", False, ist=probleme, knoten=[],
                       hinweis="Gleichungen ohne gleichung-Punkt verändert: " + ", ".join(q["links"] for q in probleme))
    return eintrag("gleichungen", True, ist=[], knoten=[])


def _konfigurationen(c: _Vergleich) -> dict:
    """Gleiche Konfigurationen, gleiche aktive, Unterdrückung nur wie die Punkte und nur in deren Richtung: `unterdruecken`
    erlaubt Feature, Kinder und deren eigene Skizzen von False auf True, `aufheben` nur das Feature und seine eigenen Skizzen von
    True auf False (die Kinder bleiben unterdrückt)."""
    v, n = c.vorher, c.nachher
    probleme, unlesbar = [], []
    if fehlt := [k for k in v["konfigurationen"] if k not in n["konfigurationen"]]:
        probleme.append({"art": "fehlt", "konfigurationen": fehlt})
    if neu := [k for k in n["konfigurationen"] if k not in v["konfigurationen"]]:
        probleme.append({"art": "neu", "konfigurationen": neu})
    if v["aktiv"] != n["aktiv"]:  # sonst öffnet der Kollege eine andere Variante (Review Focus 4)
        probleme.append({"art": "aktiv", "soll": v["aktiv"], "ist": n["aktiv"]})
    zu: set[tuple[str, str]] = set()
    auf: set[tuple[str, str]] = set()
    for p in c.punkte_vom_typ("unterdruecken"):
        namen = {p["feature"], *kinder_von(p["feature"], v)}
        zu |= {(x, k) for x in namen | _eigene_skizzen(namen, v) for k in c.konfig(p)}
    for p in c.punkte_vom_typ("aufheben"):
        namen = {p["feature"]}
        auf |= {(x, k) for x in namen | _eigene_skizzen(namen, v) for k in c.konfig(p)}
    for f in v["features"]:
        g = c.features_nachher.get(f["name"])
        if g is None:
            continue
        for k in c.konfigurationen:
            a, b = f["unterdrueckt"].get(k), g["unterdrueckt"].get(k)
            if a is None or b is None:
                unlesbar.append({"feature": f["name"], "konfiguration": k})
            elif a != b and (f["name"], k) not in (zu if b else auf):
                probleme.append({"art": "unterdrueckung", "feature": f["name"], "konfiguration": k, "vorher": a, "nachher": b})
    if probleme:
        return eintrag("konfigurationen", False, ist=probleme, knoten=[], hinweis="Konfigurationen weichen vom Bestand ab: "
                       + ", ".join(q.get("feature") or q["art"] for q in probleme))
    if unlesbar:
        return eintrag("konfigurationen", None, ist=[], knoten=[], unlesbar=unlesbar, hinweis="Unterdrückung nicht lesbar: "
                       + ", ".join(f"{u['feature']} ({u['konfiguration']})" for u in unlesbar))
    return eintrag("konfigurationen", True, ist=[], knoten=[])


def _eigenschaften(c: _Vergleich) -> dict:
    frei = {(p.get("konfiguration", ""), p["name"]) for p in c.punkte_vom_typ("eigenschaft")}
    probleme = []
    for wo in ["", *c.konfigurationen]:
        a, b = _eigenschaften_von(c.vorher, wo), _eigenschaften_von(c.nachher, wo)
        probleme += [{"konfiguration": wo, "name": n, "vorher": a.get(n), "nachher": b.get(n)}
                     for n in sorted(set(a) | set(b)) if a.get(n) != b.get(n) and (wo, n) not in frei]
    if probleme:
        return eintrag("eigenschaften", False, ist=probleme, knoten=[], hinweis="Eigenschaften ohne Punkt verändert: "
                       + ", ".join(f"{q['name']} ({q['konfiguration'] or 'Datei'})" for q in probleme))
    return eintrag("eigenschaften", True, ist=[], knoten=[])


def _material(c: _Vergleich) -> dict:
    a, b = _materialien(c.vorher), _materialien(c.nachher)
    if c.punkte_vom_typ("material"):
        return eintrag("material", True, ist=b, knoten=[])
    probleme = {k: {"vorher": a.get(k), "nachher": b.get(k)} for k in c.konfigurationen if a.get(k) != b.get(k)}
    if probleme:
        return eintrag("material", False, ist=probleme, knoten=[],
                       hinweis="Material ohne material-Punkt verändert: " + ", ".join(probleme))
    return eintrag("material", True, ist=b, knoten=[])


def _neuaufbau(c: _Vergleich) -> dict:
    neu = []
    for k in c.konfigurationen:
        meldungen = [e for e in c.nachher["neuaufbau"] if e["konfiguration"] == k]
        neu += [{"konfiguration": k, "meldung": m}
                for m in neue_fehler(meldungen, c.vorher, k) + neue_warnungen(meldungen, c.vorher, k)]
    if neu:
        return eintrag("neuaufbau", False, ist=neu, knoten=[],
                       hinweis="Neue Neuaufbau-Meldungen: " + "; ".join(f"{q['meldung']} ({q['konfiguration']})" for q in neu))
    return eintrag("neuaufbau", True, ist=[], knoten=[])


def _skizzen(c: _Vergleich) -> dict:
    """Keine Skizze schlechter als im Bestand; unterbestimmte des Kollegen bleiben unterbestimmt. Neue Skizzen stehen nur zur
    Information da, der Bestand hat für sie keinen Maßstab. Fehlende meldet `baum`."""
    vor, nach = c.vorher["skizzen"], c.nachher["skizzen"]
    schlechter = [{"skizze": n, "vorher": a, "nachher": nach[n]} for n, a in vor.items()
                  if n in nach and SKIZZE_RANG.get(nach[n], -1) < SKIZZE_RANG.get(a, -1)]
    nicht_voll = {n: s for n, s in nach.items() if n not in vor and s != 3}
    if schlechter:
        return eintrag("skizzen", False, ist=schlechter, knoten=[], neu_nicht_voll_bestimmt=nicht_voll,
                       hinweis="Skizzen schlechter bestimmt als im Bestand: " + ", ".join(q["skizze"] for q in schlechter))
    return eintrag("skizzen", True, ist=[], knoten=[], neu_nicht_voll_bestimmt=nicht_voll)


def _externe_referenzen(c: _Vergleich) -> dict:
    """Keine neuen und keine, die aus dem Lauf-Ordner herauszeigen. Bestandskopie und Lauf liegen in verschiedenen Ordnern, also
    zählt der Pfad relativ zum Ordner der Datei (`datei.ordner`, beide Aufnahmen); liegt eine Referenz außerhalb, zählt der ganze
    Pfad. Fehlt der Ordner, lässt sich nur der Dateiname vergleichen: Neue Namen sind ein Mangel, bekannte nicht nachgewiesen."""
    vor, nach = c.vorher["externe_referenzen"], c.nachher["externe_referenzen"]
    ordner = [_norm(a["datei"]["ordner"]).rstrip("/") + "/" if a.get("datei", {}).get("ordner") else None
              for a in (c.vorher, c.nachher)]

    def schluessel(pfad: str, wurzel: str | None) -> str:
        pfad = _norm(pfad)
        return pfad[len(wurzel):] if wurzel and pfad.startswith(wurzel) else pfad if wurzel else _basis(pfad)

    wurzeln = ordner if all(ordner) else [None, None]
    bekannt = {schluessel(p, wurzeln[0]) for p in vor}
    innen = {_basis(p) for p in vor if wurzeln[0] and _norm(p).startswith(wurzeln[0])}
    neu = [p for p in nach if schluessel(p, wurzeln[1]) not in bekannt]
    probleme = [{"art": "heraus" if _basis(p) in innen else "neu", "pfad": p} for p in neu]
    if probleme:
        return eintrag("externe_referenzen", False, ist=probleme, knoten=[],
                       hinweis="Externe Referenzen: " + ", ".join(f"{q['pfad']} ({q['art']})" for q in probleme))
    if nach and not all(ordner):
        return eintrag("externe_referenzen", None, ist=[], knoten=[], hinweis="Ohne datei.ordner lassen sich die vorhandenen "
                       "Referenzen nur nach Dateinamen vergleichen, nicht nachgewiesen: " + ", ".join(nach))
    return eintrag("externe_referenzen", True, ist=[], knoten=[])


def vergleiche(spec: dict, vorher: dict, nachher: dict, parameter: dict, skript_features: frozenset[str] = frozenset(),
               skript_gelaufen: frozenset[str] = frozenset()) -> list[dict]:
    """§7.1: Einträge `punkt:<id>` je Punkt, dann `baum`, `masse`, `gleichungen`, `konfigurationen`, `eigenschaften`,
    `material`, `neuaufbau`, `skizzen`, `externe_referenzen`. `parameter`: die Parameter der Spec für Ausdrücke wie `=A_neu`.
    Aus dem Protokoll: `skript_features`, was `bauen(ctx)` zurückgab, `skript_gelaufen`, die Punkt-IDs der durchgelaufenen Skripte."""
    c = _Vergleich(spec.get("punkte", []), vorher, nachher, parameter, skript_gelaufen, skript_features)
    return [_punkt(p, c) for p in c.punkte] + [
        _baum(c), _masse(c), _gleichungen(c), _konfigurationen(c), _eigenschaften(c), _material(c), _neuaufbau(c), _skizzen(c),
        _externe_referenzen(c)]
