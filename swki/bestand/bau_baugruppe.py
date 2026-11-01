"""swki bauen für art: aenderung an einer Baugruppe (Spec Bestandsdateien §6, §8.1, §8.1a, §8.3, §8.7; Plan Etappe 2 Task 10).

Ablauf: alle Bestandsdateien gegen `dateien.json`, frische Kopie aller Dateien nach `lauf-<n>/`, Pfadschutz, je Datei mit Punkten
die Teil-Scheibe über den Kern von Etappe 1, neue Dateien holen, Baugruppe öffnen, Haupt-Punkte in Spec-Reihenfolge, Stand in
allen Konfigurationen prüfen, speichern. Die Teil-Scheiben laufen vor den Haupt-Punkten, egal wie die Punkte stehen: Eine neue
Verknüpfung kann an einem neuen Feature hängen, und `ReplaceComponents2` schließt Komponentendateien, ohne Änderungen zu sichern;
darum sind sie vorher gespeichert und geschlossen. Sperre 1 des Pfadschutzes läuft vor dem ersten Punkt, sonst stünde eine
Teil-Scheibe schon, wenn die Baugruppe abgewiesen wird.

Gespeichert wird nur, was ein Punkt ändert: jede Datei mit Punkten und die Hauptbaugruppe genau bei `aenderung_an_haupt`. Bleibt
sie ungespeichert, wird sie trotzdem geöffnet und neu aufgebaut, nur so zeigen sich Verknüpfungsfehler, die ein geändertes Teil
auslöst. Nach einem Fehler wird nichts mehr gespeichert. Ein Lauf-Ordner bleibt dann liegen, Dateien früherer Scheiben darin sind
schon geändert; er trägt immer ein `protokoll.json`, auch wenn das Kopieren scheitert, sonst sperrte er `BESTAND_AUFTRAG_BELEGT`.

UNGEMESSEN: Diese Schicht steht gegen Attrappen. Der Kern der Teil-Scheibe ist in Etappe 1 mit Fenster gemessen, darum öffnet auch
sie mit Fenster. Offen für S19: was `Save3` an der Baugruppe mit im Speicher geänderten Komponenten tut, ob `GetWhatsWrong` die
Fehler einer Verknüpfung nennt und mit welchem Code, und ob ein geändertes Teil in der ungespeicherten Baugruppe ankommt.

Bekannt ist, was die Aufnahme kennt, je Konfiguration: `neuaufbau` und die Fehlercodes der Verknüpfungen. Die Handler laufen unter
den bekannten Fehlern der aktiven Konfiguration, ein alter Fehler des Kollegen bräche `sw.rebuild` sonst ab.
"""

import time
from contextlib import contextmanager
from pathlib import Path

from swki.aenderungen import pruefe_unveraendert, pruefsummen, sha256_datei, vermerke_befund
from swki.auftrag import auftrag_name, lauf_ordner, naechster_lauf
from swki.baugruppe.aufloesen import ANLAGE
from swki.baugruppe.bau import _schliesse_alle
from swki.bestand import punkte
from swki.bestand.ablage import bestand_ordner, lade_datei_aufnahme, lade_dateien, lauf_kopie_alle
from swki.bestand.aufnahme_baugruppe import _Messung
from swki.bestand.bau import _aendere_und_speichere, _pruefe_baum, schliesse_lauf
from swki.bestand.fehler import BESTAND_ABWEICHEND, BESTAND_VERSION_AELTER, BestandFehler
from swki.bestand.pfade import oeffne_in, pruefe_vor_dem_oeffnen
from swki.bestand.punkte_baugruppe import BauKontext, hole_neue_dateien, punkt_handler
from swki.bestand.scheiben import HAUPT_TYPEN, aenderung_an_haupt, dateien_mit_punkten, haupt_punkte, haupt_scheibe, scheibe
from swki.bestand.spec import bestand_kennung
from swki.bestand.sw_baugruppe_bestand import (_komponenten_leser, _verknuepfungen_leser, _vervollstaendige, _werte_der_aktiven,
                                               baum_ohne_glieder)
from swki.bestand.sw_bestand import lizenz, schalte, speichere_an_ort, whats_wrong
from swki.bestand.vergleich import neue_fehler
from swki.bestand.vergleich_baugruppe import (_ahnen, _gleich, _wert_gelesen, bekannte_fehler_baugruppe, ersetzen_ziele,
                                              namen_im_lauf, neuer_verknuepfungsfehler, soll_werte)
from swki.compiler import sw
from swki.compiler.ablauf import durchlaufe
from swki.compiler.fehler import REBUILD_FEHLER, BauFehler, fehler_dict
from swki.compiler.protokoll import Knoten, Protokoll
from swki.konfig import lade_rechner, lade_standard
from swki.spec.ausdruck import auswerten
from swki.verbindung import verbinde


def neue_fehler_baugruppe(fehler: list[dict], aufnahme: dict, konfiguration: str) -> list[str]:
    """`neue_fehler`, aber bekannt ist auch, was die Aufnahme als Fehlercode der Verknüpfung führt: `GetErrorCode2` und
    `GetWhatsWrong` müssen nicht dasselbe nennen (S19)."""
    mates = aufnahme["verknuepfungen"]
    uebrig = [e for e in fehler if ((mates.get(e["feature"]) or {}).get("fehler") or {}).get(konfiguration) != e["code"]]
    return neue_fehler(uebrig, aufnahme, konfiguration)


def _pruefe_neuaufbau(ctx, aufnahme: dict) -> None:
    """Nach jedem Haupt-Punkt, wie bei einem Teil (`bau._pruefe_neuaufbau`)."""
    sw.rebuild(ctx.model)
    if neu := neue_fehler_baugruppe(whats_wrong(ctx.model), aufnahme, aufnahme["aktiv"]):
        raise BauFehler(REBUILD_FEHLER, "; ".join(neu), schritt="rebuild")


# --- Stand vor dem Speichern --------------------------------------------------------------------------------------------------

def _neue_verknuepfungsfehler(mates: dict, aufnahme: dict) -> list[str]:
    """Alle Verknüpfungen, auch die keines Punkts, gegen die Aufnahme."""
    return [f"{name}: {text}" for name, m in mates.items() for k in aufnahme["konfigurationen"]
            if (text := neuer_verknuepfungsfehler(aufnahme["verknuepfungen"].get(name), m, k))]


def _verschwunden(spec: dict, aufnahme: dict, komponenten: dict, mates: dict) -> list[str]:
    """Was aus dem Bestand fehlt und kein Punkt nimmt, wie `bau._pruefe_baum` für Komponenten und Verknüpfungen: Auch ein Skript
    darf nichts verschwinden lassen."""
    frei_k, frei_v = set(), set()
    for p in spec["punkte"]:
        if p["typ"] == "komponente_entfernen":
            frei_k.add(p["komponente"])
            frei_v.update(p["verknuepfungen"])
        elif p["typ"] == "komponente_ersetzen":
            frei_k.update(ersetzen_ziele(p, aufnahme["komponenten"], spec["punkte"])[0])
        elif p["typ"] == "verknuepfung_loeschen":
            frei_v.add(p["verknuepfung"])
    fehlen = [n for n in aufnahme["komponenten"] if n not in komponenten and not set(_ahnen(n)) & frei_k]
    fehlen += [n for n in aufnahme["verknuepfungen"] if n not in mates and n not in frei_v]
    return [f"{n} fehlt, kein Punkt nimmt es" for n in fehlen]


def _wirkung_neue_komponente(p: dict, aufnahme: dict, neue: dict, komponenten: dict) -> list[str]:
    """Wie im Handler: Ein neues Objekt gilt in allen Konfigurationen."""
    if not neue.get(p["id"]):
        return [f"Punkt {p['id']}: Das Protokoll nennt keine neue Komponente"]
    probleme = []
    for name in neue[p["id"]]:
        if name not in komponenten:
            probleme.append(f"{name} (Punkt {p['id']}) fehlt")
            continue
        probleme += [f"{name} (Punkt {p['id']}) ist unterdrückt in {k}" for k in aufnahme["konfigurationen"]
                     if komponenten[name]["unterdrueckt"].get(k) is not False]
    return probleme


def _wirkung_ersetzen(p: dict, spec: dict, aufnahme: dict, neue: dict, komponenten: dict) -> list[str]:
    """Unterdrückt darf der Ersatz bleiben: Er steht, wo die alte Komponente stand."""
    if not neue.get(p["id"]):
        return [f"Punkt {p['id']}: Das Protokoll nennt keinen Ersatz"]
    probleme = [f"{n} (Punkt {p['id']}) fehlt" for n in neue[p["id"]] if n not in komponenten]
    return probleme + [f"{n} ist noch da (Punkt {p['id']})" for n in ersetzen_ziele(p, aufnahme["komponenten"], spec["punkte"])[0]
                       if n in komponenten]


def _wirkung_entfernen(p: dict, neue: dict, komponenten: dict, mates: dict) -> list[str]:
    ziele = set(namen_im_lauf(p["komponente"], neue, {}))
    probleme = [f"{n} ist noch da (Punkt {p['id']})" for n in komponenten if set(_ahnen(n)) & ziele]
    return probleme + [f"{n} steht noch im Baum (Punkt {p['id']})" for n in p["verknuepfungen"] if n in mates]


def _wirkung_neue_verknuepfung(p: dict, aufnahme: dict, parameter: dict, mates: dict) -> list[str]:
    """Da, in allen Konfigurationen aktiv, mit den Werten des Punkts; Fehler zählt `_neue_verknuepfungsfehler`. Der Name ist die
    Punkt-ID, ein Wert gehört zur ersten Verknüpfung."""
    probleme = []
    for i, name in enumerate([p["id"], *([f"{p['id']}{ANLAGE}"] if p["art"] == "scharnier" else [])]):
        m = mates.get(name)
        if m is None:
            probleme.append(f"Verknüpfung {name} fehlt")
            continue
        probleme += [f"Verknüpfung {name} ist unterdrückt in {k}" for k in aufnahme["konfigurationen"]
                     if m["unterdrueckt"].get(k) is not False]
        for feld, soll in (soll_werte(p, parameter).items() if i == 0 else ()):
            probleme += _wert_abweichung(name, m, feld, soll, aufnahme["konfigurationen"])
    return probleme


def _wert_abweichung(name: str, m: dict, feld: str, soll: float, konfigurationen: list[str]) -> list[str]:
    """Nicht gelesen ist nie gleich, `None` heißt: Das Feld trägt keinen Wert."""
    ist = {k: _wert_gelesen(m, k, feld)[1] for k in konfigurationen}
    return [f"Verknüpfung {name}: {feld} steht in {k} auf {w} statt {soll:g}" for k, w in ist.items()
            if w is None or not _gleich(w, soll)]


def _wirkung_wert(p: dict, aufnahme: dict, parameter: dict, mates: dict) -> list[str]:
    name = p["verknuepfung"]
    if name not in mates:
        return [f"Verknüpfung {name} fehlt (Punkt {p['id']})"]
    soll = float(auswerten(p["neu"], parameter))
    return _wert_abweichung(name, mates[name], p.get("grenze") or "wert", soll, punkte._konfigurationen(p, aufnahme))


def _punkt_wirkungen(spec: dict, aufnahme: dict, neue: dict, komponenten: dict, mates: dict) -> list[str]:
    """Jeder Baugruppen-Punkt steht noch: Ein späterer Punkt oder ein Skript könnte ihn zurückgenommen haben."""
    parameter, probleme = spec.get("parameter", {}), []
    for p in spec["punkte"]:
        if p["typ"] == "komponente_neu":
            probleme += _wirkung_neue_komponente(p, aufnahme, neue, komponenten)
        elif p["typ"] == "komponente_ersetzen":
            probleme += _wirkung_ersetzen(p, spec, aufnahme, neue, komponenten)
        elif p["typ"] == "komponente_entfernen":
            probleme += _wirkung_entfernen(p, neue, komponenten, mates)
        elif p["typ"] == "verknuepfung_neu":
            probleme += _wirkung_neue_verknuepfung(p, aufnahme, parameter, mates)
        elif p["typ"] == "verknuepfung_wert":
            probleme += _wirkung_wert(p, aufnahme, parameter, mates)
        elif p["typ"] == "verknuepfung_loeschen" and p["verknuepfung"] in mates:
            probleme.append(f"Verknüpfung {p['verknuepfung']} ist noch da (Punkt {p['id']})")
    return probleme


def pruefe_stand_baugruppe(asm, aufnahme: dict, spec: dict, neue: dict) -> None:
    """Neuaufbau in **allen** Konfigurationen, unmittelbar vor dem Speichern (S18c3): keine neuen Fehler gegen die Aufnahme, auch
    nicht an Verknüpfungen, die kein Punkt nennt, Features wie aufgenommen, nichts aus dem Bestand verschwunden, alle
    Punkt-Wirkungen stehen. `neue`: Punkt-ID → SolidWorks-Namen. Die aktive Konfiguration kommt zuletzt und bleibt für `Save3`
    stehen."""
    aktiv, konfigurationen = aufnahme["aktiv"], aufnahme["konfigurationen"]
    komponenten, mates = {}, {}
    lies_komponenten = _komponenten_leser(asm, komponenten, aufnahme.get("dateien", ()))
    lies_verknuepfungen = _verknuepfungen_leser(asm, mates, set())
    for k in [*(x for x in konfigurationen if x != aktiv), aktiv]:
        schalte(asm, k)
        ok = asm.ForceRebuild3(False)  # wie `lies_komponenten`: Lage und Status stehen sonst über Unterbaugruppen veraltet
        fehler = whats_wrong(asm)
        neu = neue_fehler_baugruppe(fehler, aufnahme, k)
        if neu or not (ok or any(not e["warnung"] for e in fehler)):
            text = "; ".join(neu) or "ForceRebuild3 meldet Fehler"
            raise BauFehler(REBUILD_FEHLER, f"Konfiguration {k}: {text}", schritt="stand")
        _pruefe_baum(k, [f.Name for f in baum_ohne_glieder(asm)], aufnahme, set())
        lies_komponenten(k)
        lies_verknuepfungen(k)
    komponenten, mates = _vervollstaendige(komponenten, konfigurationen, aktiv), _werte_der_aktiven(mates, konfigurationen, aktiv)
    probleme = (_neue_verknuepfungsfehler(mates, aufnahme) + _verschwunden(spec, aufnahme, komponenten, mates)
                + _punkt_wirkungen(spec, aufnahme, neue, komponenten, mates))
    if probleme:
        raise BauFehler(REBUILD_FEHLER, "; ".join(probleme), schritt="stand")


# --- Vor dem Bau ----------------------------------------------------------------------------------------------------------------

def pruefe_bestand(ordner: Path, dateien: dict, aufnahme: dict) -> None:
    """Alle Bestandskopien noch wie aufgenommen: `dateien.json` und `bestand.json` nennen dieselben Dateien, jede SHA-256
    stimmt."""
    soll = {rel: d["sha256"] for rel, d in aufnahme["dateien"].items()} | {aufnahme["datei"]["name"]: aufnahme["datei"]["sha256"]}
    if soll != {rel: d["sha256"] for rel, d in dateien.items()}:
        raise BestandFehler(BESTAND_ABWEICHEND, f"dateien.json in {ordner} passt nicht zur Aufnahme – jemand hat sie geändert",
                            pfad=str(ordner))
    abweichend = sorted(rel for rel, sha in soll.items() if not (ordner / rel).is_file() or sha256_datei(ordner / rel) != sha)
    if abweichend:
        raise BestandFehler(BESTAND_ABWEICHEND, f"{', '.join(abweichend)} weicht von der Aufnahme ab – jemand hat die "
                                                "Bestandskopie geändert", dateien=abweichend, pfad=str(ordner))


def _aeltere(scheiben: dict, spec: dict, aufnahme: dict) -> list[str]:
    """Dateien aus einer älteren SolidWorks-Version, die der Lauf speichert; eine ungeänderte stört nicht."""
    aelter = [rel for rel in scheiben if aufnahme["dateien"][rel].get("version_aelter")]
    return aelter + ([aufnahme["datei"]["name"]] if aenderung_an_haupt(spec) and aufnahme["datei"].get("version_aelter") else [])


# --- Bau ------------------------------------------------------------------------------------------------------------------------

@contextmanager
def _phase(protokoll: Protokoll, messung: _Messung, name: str):
    with protokoll.phase(name), messung.phase(name):
        yield


def _mit_datei(fehler: Exception, rel: str) -> BauFehler:
    """Die Prüfungen von Etappe 1 kennen nur ihre eine Datei: Bei mehreren Scheiben nennt die Meldung sie. Code, Schritt und
    `daten` bleiben."""
    d = fehler_dict(fehler)
    neu = BauFehler(d["code"], f"{rel}: {d['meldung']}", d["schritt"])
    neu.daten = {**(getattr(fehler, "daten", None) or {}), **neu.daten}
    return neu


def _aendere_scheibe(b: BauKontext, r, rel: str, teil: dict, tol_mm: float) -> Exception | None:
    """Eine Datei mit Punkten über den Kern von Etappe 1, die Baugruppe ist dabei nicht offen. Der erste Fehler (nennt die Datei)
    oder None; die Datei ist danach geschlossen und nur bei None gespeichert."""
    fehler = None
    try:
        aufnahme = lade_datei_aufnahme(r, b.protokoll.auftrag, teil["bestand"]["aufnahme"], rel)
        pfad = b.ordner / rel
        with b.protokoll.phase("vorbereiten"):
            model = oeffne_in(b.app, pfad, b.ordner, sichtbar=True, nur_lesen=False)
        try:
            fehler = _aendere_und_speichere(b.app, model, teil, b.spec_pfad, tol_mm, aufnahme, b.protokoll, pfad, b.ordner)
        finally:
            sw.schliesse(b.app, model)
    except Exception as e:  # ein Schließfehler darf den Baufehler nicht verdecken, und ohne einen steht er im Protokoll
        fehler = fehler or e
    return None if fehler is None else _mit_datei(fehler, rel)


def _wende_punkte_an(b: BauKontext, ctx):
    """`eigenschaft` und `skript` gehen über die Handler von Etappe 1, alles andere über die Baugruppen-Punkte: Ein Teil-Typ ohne
    `in_datei` weist `validieren` ab und trifft hier auf `UNBEKANNTER_TYP`, nie auf die Baugruppe."""
    def rufe(knoten: Knoten, p: dict) -> None:
        namen = punkte.punkt_handler(p["typ"])(ctx, p, b.aufnahme) if p["typ"] in HAUPT_TYPEN else punkt_handler(p["typ"])(b, p)
        knoten.sw_name = ", ".join(namen) or None
        knoten.sw_namen = list(namen) or None

    return durchlaufe(ctx, b.protokoll, haupt_punkte(b.spec), rufe, lambda c: _pruefe_neuaufbau(c, b.aufnahme))


def _aendere_haupt(b: BauKontext, ctx, messung: _Messung, pfad: Path) -> Exception | None:
    """Der erste Fehler oder None; gespeichert ist die Baugruppe nur bei None und `aenderung_an_haupt`."""
    aktiv = b.aufnahme["aktiv"]
    try:
        with _phase(b.protokoll, messung, "bauen"), sw.bekannte_fehler(bekannte_fehler_baugruppe(b.aufnahme, aktiv)):
            if fehler := _wende_punkte_an(b, ctx):
                return fehler
            pruefe_stand_baugruppe(b.asm, b.aufnahme, b.spec, b.neue)
        if aenderung_an_haupt(b.spec):
            with _phase(b.protokoll, messung, "speichern"):
                speichere_an_ort(b.asm, pfad, b.ordner)
    except Exception as e:  # jeder Fehler (auch COM) heißt: nicht speichern
        return e
    return None


def _baue_haupt(b: BauKontext, messung: _Messung, pfad: Path, tol_mm: float) -> Exception | None:
    """Neue Dateien, Baugruppe, Haupt-Punkte. Schließt alles, auch nach einem Fehler, ohne zu speichern."""
    fehler = None
    try:
        with messung.phase("dateien"):
            hole_neue_dateien(b, b.spec)
        with _phase(b.protokoll, messung, "vorbereiten"):
            b.asm = oeffne_in(b.app, pfad, b.ordner, sichtbar=True, nur_lesen=False)
        fehler = _aendere_haupt(b, punkte.kontext(b.app, b.asm, haupt_scheibe(b.spec), b.spec_pfad, tol_mm), messung, pfad)
        b.protokoll.lizenz = lizenz(b.app, b.asm)
    except Exception as e:  # jeder Fehler (auch COM) steht im Protokoll
        fehler = e
    finally:
        schliessfehler = _schliesse_alle(b)
    return fehler or schliessfehler


def _baue(b: BauKontext, r, messung: _Messung, quelle: Path, dateien: dict, scheiben: dict, tol_mm: float) -> Exception | None:
    """Der erste Fehler oder None. Sperre 1 vor dem ersten Punkt, `oeffne_in` prüft danach noch einmal und nach dem Laden."""
    try:
        with messung.phase("kopieren"):
            pfad = lauf_kopie_alle(quelle, dateien, b.ordner)
        pruefe_vor_dem_oeffnen(b.app, pfad, b.ordner)
        with messung.phase("teile"):
            for rel, teil in scheiben.items():
                with messung.phase(f"teile:{rel}"):
                    fehler = _aendere_scheibe(b, r, rel, teil, tol_mm)
                if fehler:
                    return fehler
    except Exception as e:  # jeder Fehler (auch OSError beim Kopieren) steht im Protokoll, der Ordner sperrte sonst den Auftrag
        return e
    return _baue_haupt(b, messung, pfad, tol_mm)


def _uebersprungen(protokoll: Protokoll, spec: dict) -> None:
    """Punkte, die der Abbruch nicht mehr erreicht hat; `durchlaufe` vermerkt nur die der laufenden Liste."""
    gelaufen = {k.id for k in protokoll.knoten}
    for p in spec["punkte"]:
        if p["id"] not in gelaufen:
            protokoll.uebersprungen(p["id"], p["typ"])


def bauen_baugruppe(spec_pfad: Path, spec: dict, aufnahme: dict, lauf: int | None, verwerfen: bool, uebernommen: bool,
                    hochstufen: bool) -> dict:
    """Aufgerufen von `bau.bauen` nach Freigabe und `aufnahme_zu`. Fehler vor dem Lauf (`BESTAND_ABWEICHEND`,
    `BESTAND_VERSION_AELTER`, `MANUELL_GEAENDERT`) lassen keinen Lauf-Ordner zurück, alle späteren enden in `BauAbbruch` mit
    Protokoll. Protokoll zusätzlich zu Etappe 1: `dateien` (`haupt`, `geaendert:<rel>`), `neue`, `ersetzt`, `neue_dateien`,
    `messung`, `sha256` aller Dateien des Laufs einschließlich neuer."""
    r, standard = lade_rechner(), lade_standard()
    auftrag, nummer = auftrag_name(spec_pfad), spec["bestand"]["aufnahme"]
    quelle = bestand_ordner(r, auftrag, nummer)
    dateien = lade_dateien(r, auftrag, nummer)
    pruefe_bestand(quelle, dateien, aufnahme)  # BESTAND_ABWEICHEND
    scheiben = {t["bestand"]["datei"]: t for t in (scheibe(spec, d, aufnahme["dateien"]) for d in dateien_mit_punkten(spec))}
    aelter = _aeltere(scheiben, spec, aufnahme)
    if aelter and not hochstufen:
        raise BestandFehler(BESTAND_VERSION_AELTER, f"{', '.join(aelter)} stammt aus einer älteren SolidWorks-Version: Mit "
                                                    f"--hochstufen bestätigen, dass sie danach nur noch mit SolidWorks "
                                                    f"{r.sw_jahr} oder neuer lesbar ist", sw_jahr=r.sw_jahr, dateien=aelter)
    uebergangen = pruefe_unveraendert(r, auftrag, spec_pfad, verwerfen, uebernommen)
    if lauf is None:
        lauf = naechster_lauf(r, auftrag, spec_pfad)
    ordner = lauf_ordner(r, auftrag, lauf)
    protokoll = Protokoll(auftrag, spec_pfad.name, lauf, r.sw_jahr)
    protokoll.hochgestuft = bool(aelter)
    protokoll.bestand = bestand_kennung(spec)
    beginn = time.perf_counter()

    app = verbinde(r.sw_jahr)
    vermerke_befund(protokoll, uebergangen, verwerfen)
    b = BauKontext(app, None, spec, spec_pfad, ordner, aufnahme, standard, protokoll=protokoll)
    messung = _Messung(app)
    fehler = _baue(b, r, messung, quelle, dateien, scheiben, standard["toleranzen"]["anker_mm"])
    protokoll.neue, protokoll.ersetzt, protokoll.messung = b.neue, b.ersetzt, messung.daten
    protokoll.neue_dateien = sorted(n.pfad.name for n in b.quellen.values())
    _uebersprungen(protokoll, spec)
    if fehler is None:
        try:
            protokoll.sha256 = pruefsummen(ordner, [ordner / rel for rel in [*dateien, *protokoll.neue_dateien]])
            protokoll.dateien = {"haupt": str(ordner / aufnahme["datei"]["name"])}
            protokoll.dateien |= {f"geaendert:{rel}": str(ordner / rel) for rel in scheiben}
        except OSError as e:  # jemand hat eine Datei gesperrt: Ohne Protokoll sperrte der Ordner den Auftrag
            fehler = e
    return schliesse_lauf(protokoll, fehler, ordner, spec_pfad, beginn)
