"""Punkt-Handler der Baugruppe (Spec Bestandsdateien §4.1, §8.2, §8.3; Plan Etappe 2 Task 9): schreibender Kern für Komponenten
und Verknüpfungen, Signatur `(b: BauKontext, p) -> list[str]` mit den betroffenen SolidWorks-Namen. Die Teil-Punkte laufen weiter
über `swki.bestand.punkte`, auch `eigenschaft` und `skript` an der Hauptbaugruppe.

UNGEMESSEN: Diese Schicht steht gegen den API-Index, seine Hilfetexte und Attrappen, Spike S19 Zeile e korrigiert sie. Belegt sind
nur `AddMate5`, `Select2` mit `EditDelete` und `SetSystemValue3` an `D1` (S6, S12, S13). Offen sind die Schreibwege
`ReplaceComponents2`, `ModifyDefinition`, `IComponent2.SetSuppression2`, `ReferencedConfiguration =`, `DeleteSelection2` an einer
Komponente und alles, was davon je Konfiguration wirkt.

Rückgaben von SolidWorks beweisen nichts (S18c): Jeder Handler misst nach dem Neuaufbau nach, über `lies_komponenten` bzw.
`lies_verknuepfungen`, in allen Konfigurationen. Am Ende steht die aktive der Aufnahme. Ein Handler bricht mit `BauFehler` ab,
dann wird nie gespeichert. Neuaufbau-Fehler der ganzen Baugruppe entscheidet der Bau, die Handler prüfen nur, was sie selbst
anfassen.

Ein neues Objekt gilt in allen Konfigurationen: Das Nachmessen verlangt es aktiv, weil `vergleiche_baugruppe` Unterdrücktes als
Mangel wertet. Punkt-IDs und alte Namen führt `_lauf_name` auf den Namen im Lauf (eine Komponente nach `komponente_ersetzen` heißt
anders).

API (swki api methode, Parameterzahl laut Index; Enums laut swki api enum):
  IAssemblyDoc.AddComponent5(8), .ReplaceComponents2(5: FileName, ConfigName, ReplaceAllInstance, UseConfigChoice, ReAttachMates;
    swReplaceComponentsConfiguration_e MatchName 0, ManuallySelect 1), .GetComponents(1), .FixComponent(0), .AddMate5(15)
  IModelDocExtension.DeleteSelection2(1: swDeleteSelectionOptions_e, 0 keine)
  IComponent2.Select4(3), .Name2, .GetPathName(0), .GetModelDoc2(0), .IsFixed(0), .SetSuppression2(1: swComponentFullyResolved 2 →
    swSuppressionError_e), .GetSuppression2(0: swComponentSuppressed 0), .ReferencedConfiguration (get, put), .FeatureByName(1),
    .GetCorrespondingEntity(1)
  IFeature.GetDefinition(0), .ModifyDefinition(3: Data, TopDoc, Component), .SetSuppression2(3: swUnSuppressFeature 1;
    swSpecifyConfiguration 3), .Parameter(1)
  IDistanceMateFeatureData.MinimumDistance, .MaximumDistance; IAngleMateFeatureData.MinimumAngle, .MaximumAngle (absolut, m bzw.
    rad, Hilfetext: gültig bei IsAdvancedMate)
  IDimension.SetSystemValue3(3: swSetValue_InAllConfigurations 2, _InSpecificConfigurations 3 → swSetValue_Successful 0)
  IModelDoc2.GetType(0: swDocPART 1)
Hilfetexte, die hier zählen: `AddComponent5` verlangt eine geladene Datei; `ReplaceComponents2` wirkt auf die Vorauswahl, nur
oberste Ebene, schließt laut Hilfe Komponentendateien, und nach dem Beispiel zeigt der alte `IComponent2` den neuen `Name2`."""

import shutil
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from swki.baugruppe import sw_baugruppe
from swki.baugruppe.aufloesen import _einzeln
from swki.baugruppe.bau import _mit_kontext, kaufteil_protokoll, normteil_protokoll
from swki.baugruppe.fehler import KOMPONENTE_FEHLER, TEIL_BAU, VERKNUEPFUNG_FEHLER
from swki.baugruppe.kopplung import KOPPLUNGEN
from swki.baugruppe.laden import kaufteil_quelle, normteil_quelle
from swki.baugruppe.modell import Quelle
from swki.baugruppe.referenzen import loese_im_teil
from swki.bestand import punkte
from swki.bestand.bewegung_bestand import SW_ABSTAND
from swki.bestand.fehler import BESTAND_ALTWERT, BESTAND_REFERENZ, NAME_BELEGT, VERKNUEPFUNGEN_FEHLEN
from swki.bestand.pfade import oeffne_in
from swki.bestand.scheiben import datei_schluessel
from swki.bestand.spec_baugruppe import quelle_schluessel
from swki.bestand.sw_baugruppe_bestand import SW_UNTERDRUECKT, _je_konfiguration, lies_komponenten, lies_verknuepfungen
from swki.bestand.sw_bestand import SW_BENANNTE_KONFIGURATIONEN, bstr_array
from swki.bestand.vergleich_baugruppe import (_ahnen, _gleich, _wert_gelesen, _wert_gleich, abbild_name, ersetzen_ziele,
                                              namen_im_lauf, neuer_verknuepfungsfehler, soll_ausrichtung, soll_werte)
from swki.compiler import sw
from swki.compiler.bauen import baue_teil_dokument
from swki.compiler.fehler import UNBEKANNTER_TYP, BauFehler, fehler_dict
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.protokoll import Protokoll
from swki.kaufteile import befehle as kaufteil_befehle
from swki.kaufteile.fehler import KaufteilFehler
from swki.konfig import lade_rechner
from swki.normteile import befehle as normteil_befehle
from swki.normteile.fehler import NormteilFehler
from swki.pruefung.messen import SW_DOC_PART, kontext_aus_datei
from swki.spec.ausdruck import auswerten
from swki.spec.freigabe import freigegebene_spec
from swki.verbindung import callout_leer, grad, mm
from swki.verbindung import wert as primitiv

SW_AUFGELOEST = 2                     # swComponentSuppressionState_e.swComponentFullyResolved
SW_AUFHEBEN = 1                       # swFeatureSuppressionAction_e.swUnSuppressFeature
SW_ERSETZEN_GLEICHER_NAME = 0         # swReplaceComponentsConfiguration_e.swReplaceComponentsConfiguration_MatchName
SW_ERSETZEN_BENANNT = 1               # swReplaceComponentsConfiguration_e.swReplaceComponentsConfiguration_ManuallySelect
SW_LOESCHEN = 0                       # swDeleteSelectionOptions_e: keine Option, Kinder einer Komponente gehen ohnehin mit (S19e)
SW_WERT_ALLE, SW_WERT_BENANNT = 2, 3  # swSetValueInConfiguration_e
SW_WERT_ERFOLG = 0                    # swSetValueReturnStatus_e.swSetValue_Successful
KEINE_BOX = [0.0] * 6                 # `fuege_ein` setzt die Lage danach ohnehin auf die Identität
WERTFELDER = ("wert", "min", "max")
GRENZ_ATTRIBUT = {True: {"min": "MinimumDistance", "max": "MaximumDistance"},
                  False: {"min": "MinimumAngle", "max": "MaximumAngle"}}  # True: Abstand


@dataclass
class NeueDatei:
    """Eine Datei, die `hole_neue_dateien` neben die Hauptbaugruppe gelegt und geöffnet hat."""

    pfad: Path
    art: str      # "teil" | "normteil" | "kaufteil"
    ctx: object   # Kontext des Teildokuments, wie `b.kontexte`


@dataclass
class BauKontext:
    app: object
    asm: object                                          # `None`, bis die Baugruppe offen ist: `hole_neue_dateien` läuft davor
    spec: dict
    spec_pfad: Path
    ordner: Path                                         # lauf-<n>, die Hauptbaugruppe liegt direkt darin
    aufnahme: dict
    standard: dict
    neue: dict[str, list] = field(default_factory=dict)  # Punkt-ID → SolidWorks-Namen (Protokoll)
    ersetzt: dict[str, str] = field(default_factory=dict)  # alter → neuer Name (Protokoll)
    kontexte: dict = field(default_factory=dict)         # Dateiname klein → Kontext des Teildokuments
    protokoll: Protokoll | None = None                   # nimmt die Herkunft neuer Dateien auf
    quellen: dict[str, NeueDatei] = field(default_factory=dict)  # `quelle_schluessel(quelle)` → neue Datei
    offen: list = field(default_factory=list)            # selbst geöffnete Teildokumente, schließt der Bau
    gesetzt: dict = field(default_factory=dict)          # Verknüpfung → ausdrücklich gesetzte Ausrichtung (`verknuepfe`)

    @property
    def konfigurationen(self) -> list[str]:
        return list(self.aufnahme["konfigurationen"])


PUNKTE: dict[str, Callable] = {}


def punkt(*typen: str):
    def dekorator(funktion):
        for typ in typen:
            PUNKTE[typ] = funktion
        return funktion

    return dekorator


def punkt_handler(typ: str) -> Callable:
    funktion = PUNKTE.get(typ)
    if funktion is None:
        raise BauFehler(UNBEKANNTER_TYP, f"Kein Handler für Punkt {typ!r}", schritt="handler")
    return funktion


def _komponenten(b: BauKontext) -> dict:
    return lies_komponenten(b.asm, b.konfigurationen, b.aufnahme.get("dateien", ()))


def _verknuepfungen(b: BauKontext) -> dict:
    return lies_verknuepfungen(b.asm, b.konfigurationen)


def _lauf_name(b: BauKontext, name: str) -> str:
    """Der Name im Lauf, die erste Komponente einer Punkt-ID (`verknuepfung_neu` nennt nur `komponente_neu`, das hat genau
    eine)."""
    return namen_im_lauf(name, b.neue, b.ersetzt)[0]


def _komponente(b: BauKontext, name: str):
    """`IComponent2` auf allen Ebenen. Nach dem Umschalten neu holen, ein gehaltener Handle zeigt womöglich den alten Stand
    (S18c)."""
    ziel = _lauf_name(b, name)
    komp = next((k for k in b.asm.GetComponents(False) or () if k.Name2 == ziel), None)
    if komp is None:
        raise BauFehler(BESTAND_REFERENZ, f"Komponente {ziel!r} gibt es in der Baugruppe nicht", schritt="referenz")
    return komp


def _verknuepfung(b: BauKontext, name: str):
    feature = next((f for f in sw_baugruppe.verknuepfungen(b.asm) if f.Name == name), None)
    if feature is None:
        raise BauFehler(BESTAND_REFERENZ, f"Verknüpfung {name!r} gibt es in der Baugruppe nicht", schritt="referenz")
    return feature


def _dateiname(komp) -> str:
    return Path(primitiv(komp.GetPathName)).name.casefold()


def _gleiche_datei(a: str | None, b: str | None) -> bool:
    """Relative Pfade der Aufnahme; nicht gelesen ist nie gleich."""
    return a is not None and b is not None and datei_schluessel(a) == datei_schluessel(b)


# --- Neue Dateien ---------------------------------------------------------------------------------------------------------

def _ziel(b: BauKontext, name: str) -> Path:
    """Flach neben der Hauptbaugruppe (Plan Präzisierung 2). `validieren` meldet gleiche Namen (`NAME_BELEGT`); hier nur die
    Sperre, damit nie eine Datei des Kollegen überschrieben wird."""
    ziel = b.ordner / name
    if ziel.exists():
        raise BauFehler(NAME_BELEGT, f"{name} liegt schon im Lauf-Ordner, die neue Datei überschriebe sie", schritt="datei")
    return ziel


def _lege_ab(b: BauKontext, q: Quelle, datei: str) -> NeueDatei:
    """Kopie aus der Bibliothek neben die Baugruppe, ohne Fenster öffnen, Kontext aus der Datei. `AddComponent5` verlangt eine
    geladene Datei (API-Hilfe), offen bleibt sie bis zum Ende des Baus."""
    ziel = _ziel(b, f"{q.schluessel}.sldprt")
    shutil.copy2(datei, ziel)
    model = oeffne_in(b.app, ziel, b.ordner, sichtbar=False, nur_lesen=False)
    b.offen.append(model)
    ctx = kontext_aus_datei(b.app, model, q.spec, ziel.with_suffix(".yaml"), b.standard["toleranzen"]["anker_mm"], {"knoten": []})
    return NeueDatei(ziel, q.art, ctx)


def _quelle_oder_abbruch(ergebnis: tuple[Quelle | None, list[dict]], text: str) -> Quelle:
    q, befunde = ergebnis
    if q is None or befunde:
        raise BauFehler(BESTAND_REFERENZ, f"{text}: {'; '.join(x['meldung'] for x in befunde)}", schritt="datei")
    return q


def _normteil(b: BauKontext, quelle: dict) -> NeueDatei:
    q = _quelle_oder_abbruch(normteil_quelle(quelle, "quelle"), quelle["normteil"])
    try:
        ergebnis = normteil_befehle.hole(q.norm, q.hole_groesse, q.variante)
    except NormteilFehler as e:
        raise BauFehler(e.daten["code"], f"{quelle['normteil']}: {e}", schritt="normteil") from e
    b.protokoll.normteile[q.schluessel] = normteil_protokoll(lade_rechner(), q.schluessel, ergebnis)
    return _lege_ab(b, q, ergebnis["pfad"])


def _kaufteil(b: BauKontext, quelle: dict) -> NeueDatei:
    q = _quelle_oder_abbruch(kaufteil_quelle(quelle, "quelle"), quelle["kaufteil"])
    try:
        ergebnis = kaufteil_befehle.hole(q.kaufteil)
    except KaufteilFehler as e:
        raise BauFehler(e.daten["code"], f"{quelle['kaufteil']}: {e}", schritt="kaufteil") from e
    b.protokoll.kaufteile[q.schluessel] = kaufteil_protokoll(q, ergebnis)
    return _lege_ab(b, q, ergebnis["pfad"])


def _teil(b: BauKontext, quelle: dict) -> NeueDatei:
    """Aus der freigegebenen Teil-Spec, nie aus der Datei daneben. Anders als beim eigenen Teil wird ein gescheiterter Bau nicht
    zur Diagnose gespeichert: Nach einem Fehler speichert hier nichts mehr."""
    datei, pfad = quelle["teil"], b.spec_pfad.parent / quelle["teil"]
    teil = freigegebene_spec(pfad)
    ziel = _ziel(b, f"{teil['name']}.sldprt")
    tp = Protokoll(b.protokoll.auftrag, datei, b.protokoll.lauf, b.protokoll.sw_jahr)
    model, ctx, fehler = baue_teil_dokument(b.app, lade_rechner(), b.standard, teil, pfad, b.protokoll.auftrag, tp)
    b.offen.append(model)
    if fehler is None:
        try:
            sw.speichere(model, ziel)
        except Exception as e:
            fehler = e
    tp.status = "fehler" if fehler else "ok"
    tp.fehler = fehler_dict(fehler) if fehler else None
    b.protokoll.teile[datei] = tp.als_dict()
    if fehler is not None:
        f = fehler_dict(fehler)
        raise BauFehler(TEIL_BAU, f"{datei}: {f['code']} – {f['meldung']}", schritt="teil")
    return NeueDatei(Path(model.GetPathName), "teil", ctx)  # GetPathName schreibt die Endung groß (S12)


def hole_neue_dateien(b: BauKontext, spec: dict) -> dict[str, Path]:
    """Die Dateien aller Punkte mit `quelle` flach neben der Hauptbaugruppe, je Quelle einmal: Dateiname → Pfad. Läuft vor dem
    Öffnen der Baugruppe und setzt `b.quellen` und `b.kontexte`. Die Dokumente bleiben offen (`b.offen`), schließen muss der
    Bau."""
    holen = {"normteil": _normteil, "kaufteil": _kaufteil, "teil": _teil}
    dateien = {}
    for p in spec["punkte"]:
        quelle = p.get("quelle")
        if quelle is None or quelle_schluessel(quelle) in b.quellen:
            continue
        art = next(k for k in holen if k in quelle)
        neu = b.quellen[quelle_schluessel(quelle)] = holen[art](b, quelle)
        b.kontexte[neu.pfad.name.casefold()] = neu.ctx
        dateien[neu.pfad.name] = neu.pfad
    return dateien


# --- Komponenten ----------------------------------------------------------------------------------------------------------

def loesche_komponente(asm, komp) -> None:
    """Komponente löschen, ohne Neuaufbau und ohne Nachmessen: Was mitgeht, prüft der Handler. `sw_baugruppe.loesche` kennt nur
    Verknüpfungen."""
    sw.auswahl_leeren(asm)
    _waehle(asm, komp)
    asm.Extension.DeleteSelection2(SW_LOESCHEN)
    sw.auswahl_leeren(asm)


def _waehle(asm, komp) -> None:
    if not komp.Select4(False, asm.SelectionManager.CreateSelectData, False):
        raise BauFehler(KOMPONENTE_FEHLER, f"{komp.Name2}: Auswahl fehlgeschlagen", schritt="auswahl")


def _in_allen_aktiv(b: BauKontext, name: str, soll: dict[str, str], fixiert: bool) -> None:
    """Je Konfiguration aufheben, referenzierte Konfiguration setzen, fixieren: Alle drei gelten je Konfiguration (Annahme bis
    S19e, S18c misst das nur für Features). Ein neues Objekt ist in den übrigen unterdrückt."""

    def setze(k: str) -> None:
        komp = _komponente(b, name)
        if primitiv(komp.GetSuppression2) == SW_UNTERDRUECKT:
            komp.SetSuppression2(SW_AUFGELOEST)
        if soll.get(k) and komp.ReferencedConfiguration != soll[k]:
            komp.ReferencedConfiguration = soll[k]
        if fixiert and not komp.IsFixed:
            sw_baugruppe.fixiere(b.asm, komp)

    _je_konfiguration(b.asm, b.konfigurationen, setze)


def _pruefe_neue_komponente(b: BauKontext, name: str, datei: str, soll: dict[str, str], fixiert: bool) -> None:
    ist = _komponenten(b).get(name)
    if ist is None:
        raise BauFehler(KOMPONENTE_FEHLER, f"{name} fehlt nach dem Einfügen", schritt="nachmessen")
    probleme = [] if _gleiche_datei(ist["datei"], datei) else [f"Datei {ist['datei']!r} statt {datei!r}"]
    for k in b.konfigurationen:
        if ist["unterdrueckt"].get(k) is not False:
            probleme.append(f"unterdrückt in {k}")
        if soll.get(k) and ist["konfigurationen"].get(k) != soll[k]:
            probleme.append(f"Konfiguration {ist['konfigurationen'].get(k)!r} statt {soll[k]!r} in {k}")
        if ist["fixiert"].get(k) is not fixiert:
            probleme.append(f"{'nicht ' if fixiert else ''}fixiert in {k}")
    if probleme:
        raise BauFehler(KOMPONENTE_FEHLER, f"{name}: {'; '.join(probleme)}", schritt="nachmessen")


def _wie(b: BauKontext, p: dict) -> tuple[Path, str, dict[str, str]]:
    """(Pfad im Lauf, relativer Pfad, Konfiguration je Baugruppen-Konfiguration) einer vorhandenen Komponente. Der Pfad kommt aus
    der Aufnahme, nie aus `GetPathName`: Unterdrückt nennt das den gespeicherten Pfad, in der Kopie also den Kundenordner (§8.1a).
    `AddComponent5` verlangt eine geladene Datei; ist in der aktiven Konfiguration keine Instanz da, lädt sie der Pfadschutz."""
    komponenten = _komponenten(b)
    vorlage = komponenten.get(_lauf_name(b, p["wie"]))
    if vorlage is None:
        raise BauFehler(BESTAND_REFERENZ, f"Komponente {p['wie']!r} gibt es in der Baugruppe nicht", schritt="referenz")
    datei = vorlage["datei"]
    if datei is None:
        raise BauFehler(KOMPONENTE_FEHLER, f"Die Datei von {p['wie']} ist nicht lesbar", schritt="referenz")
    fest = p.get("konfiguration")
    soll = {k: fest or vorlage["konfigurationen"].get(k) for k in b.konfigurationen}
    if unlesbar := [k for k, w in soll.items() if w is None]:
        raise BauFehler(KOMPONENTE_FEHLER, f"Die Konfiguration von {p['wie']} ist in {', '.join(unlesbar)} nicht lesbar",
                        schritt="referenz")
    pfad, aktiv = b.ordner / datei, b.aufnahme["aktiv"]
    if not any(_gleiche_datei(k["datei"], datei) and k["unterdrueckt"].get(aktiv) is False for k in komponenten.values()):
        b.offen.append(oeffne_in(b.app, pfad, b.ordner, sichtbar=False, nur_lesen=False))
    return pfad, datei, soll


@punkt("komponente_neu")
def komponente_neu(b: BauKontext, p: dict) -> list[str]:
    """Aus einer Quelle oder `wie` eine vorhandene Komponente: gleiche Datei, gleiche Konfiguration, und zwar je Konfiguration der
    Baugruppe (`vergleich_baugruppe._punkt_komponente_neu`). Die Lage ist die Identität, Verknüpfungen setzen die Punkte
    danach."""
    konfigurationen, fest = b.konfigurationen, p.get("konfiguration")
    if "wie" in p:
        pfad, datei, soll = _wie(b, p)
        box = KEINE_BOX
    else:
        neu = b.quellen[quelle_schluessel(p["quelle"])]
        pfad, box, datei = neu.pfad, sw.teilebox_mm(neu.ctx.model), neu.pfad.name
        soll = dict.fromkeys(konfigurationen, fest) if fest else {}
    komp = sw_baugruppe.fuege_ein(b.app, b.asm, pfad, box, soll.get(b.aufnahme["aktiv"]) or "")
    name, fixiert = komp.Name2, bool(p.get("fixiert"))
    _in_allen_aktiv(b, name, soll, fixiert)
    _pruefe_neue_komponente(b, name, datei, soll, fixiert)
    b.neue[p["id"]] = [name]
    return [name]


@punkt("komponente_entfernen")
def komponente_entfernen(b: BauKontext, p: dict) -> list[str]:
    """`verknuepfungen` nennt alle, die mitgehen, `validieren` prüft das gegen die Aufnahme; hier zählt, was wirklich geschah.
    Eine genannte, die stehen bleibt, ist auch ein Fehler: Ohne ihre Komponente trüge sie einen Fehler in die Datei des
    Kollegen."""
    name = _lauf_name(b, p["komponente"])
    vorher_k, vorher_v = _komponenten(b), _verknuepfungen(b)
    loesche_komponente(b.asm, _komponente(b, name))
    nachher_k, nachher_v = _komponenten(b), _verknuepfungen(b)
    weg = sorted(set(vorher_k) - set(nachher_k))
    if name in nachher_k or (fremd := [n for n in weg if name not in _ahnen(n)]):
        grund = f"{name} ist noch da" if name in nachher_k else f"Das Entfernen von {name} nahm auch {', '.join(fremd)} mit"
        raise BauFehler(KOMPONENTE_FEHLER, grund, schritt="nachmessen")
    if ungenannt := sorted(set(vorher_v) - set(nachher_v) - set(p["verknuepfungen"])):
        raise BauFehler(VERKNUEPFUNGEN_FEHLEN, f"Das Entfernen von {name} nahm auch {', '.join(ungenannt)} mit: verknuepfungen "
                                               "muss sie nennen", schritt="nachmessen")
    if geblieben := sorted(set(p["verknuepfungen"]) & set(nachher_v)):
        raise BauFehler(KOMPONENTE_FEHLER, f"{name} ist entfernt, aber {', '.join(geblieben)} steht noch im Baum",
                        schritt="nachmessen")
    return weg


def _ziele(b: BauKontext, p: dict) -> list[str]:
    """Die Komponenten, die der Punkt ersetzt: dieselbe Menge wie `vergleiche_baugruppe`, aus der Aufnahme und nicht aus dem Lauf,
    sonst hinge sie an der Reihenfolge der Punkte. Die Sperren stehen auch in `validieren`, hier als zweite Linie."""
    ziele, unlesbar = ersetzen_ziele(p, b.aufnahme["komponenten"], b.spec["punkte"])
    if unlesbar:
        raise BauFehler(KOMPONENTE_FEHLER, f"Die Instanzen sind nicht zu bestimmen: {'; '.join(unlesbar)}", schritt="referenz")
    if tief := [n for n in ziele if "/" in n]:
        raise BauFehler(KOMPONENTE_FEHLER, f"alle_instanzen träfe auch {', '.join(tief)} in einer Unterbaugruppe: Punkte treffen "
                                           "nur die oberste Ebene", schritt="referenz")
    return ziele


def _pruefe_verknuepfungen_nach_ersetzen(b: BauKontext, name: str, zuordnung: dict[str, str], vorher: dict,
                                         nachher: dict) -> None:
    """Sie bleiben, soweit sie sich neu zuordnen lassen. Was verloren ging, hat keinen Punkt, also Abbruch mit allen Namen; ein
    Fehler, den die Verknüpfung vorher nicht hatte, zählt als verloren, nicht lesbare Partner oder Codes auch."""
    verloren, falsch, fehlerhaft = sorted(set(vorher) - set(nachher)), [], []
    for n in sorted(set(vorher) & set(nachher)):
        v, m = vorher[n], nachher[n]
        if v["partner"] is None or m["partner"] is None:
            falsch.append(f"{n} (nicht lesbar)")
        elif Counter(m["partner"]) != Counter(abbild_name(x, zuordnung) for x in v["partner"]):
            falsch.append(n)
        if meldungen := [text for k in b.konfigurationen if (text := neuer_verknuepfungsfehler(v, m, k))]:
            fehlerhaft.append(f"{n}: {', '.join(meldungen)}")
    if verloren or falsch or fehlerhaft:
        teile = [*([f"verloren: {', '.join(verloren)}"] if verloren else []),
                 *([f"andere Partner: {', '.join(falsch)}"] if falsch else []), *fehlerhaft]
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Das Ersetzen von {name} trifft Verknüpfungen, {'; '.join(teile)}. Muss eine "
                                             "gehen: verknuepfung_loeschen davor", schritt="nachmessen")


def _pruefe_komponenten_nach_ersetzen(b: BauKontext, p: dict, zuordnung: dict[str, str], neu: NeueDatei, vorher: dict,
                                      nachher: dict) -> None:
    probleme = [f"{n} ist noch da" for n in zuordnung if n in nachher]
    probleme += [f"{n} (Ersatz für {alt}) fehlt" for alt, n in zuordnung.items() if n not in nachher]
    probleme += [f"{n} gibt es schon im Bestand" for n in zuordnung.values() if n in vorher]
    if len(set(zuordnung.values())) != len(zuordnung):
        probleme.append(f"Der Ersatz hat nicht je Komponente einen Namen: {zuordnung}")
    probleme += [f"{n} ist weg" for n in vorher if n not in nachher and not set(_ahnen(n)) & set(zuordnung)]
    for n in (x for x in zuordnung.values() if x in nachher):
        if not _gleiche_datei(nachher[n]["datei"], neu.pfad.name):
            probleme.append(f"{n} hat die Datei {nachher[n]['datei']!r} statt {neu.pfad.name!r}")
        if "konfiguration" in p:
            ist = nachher[n]["konfigurationen"]
            probleme += [f"{n} steht in {k} in der Konfiguration {ist.get(k)!r} statt {p['konfiguration']!r}"
                         for k in b.konfigurationen if ist.get(k) != p["konfiguration"]]
    if probleme:
        raise BauFehler(KOMPONENTE_FEHLER, f"Ersetzen: {'; '.join(probleme)}", schritt="nachmessen")


@punkt("komponente_ersetzen")
def komponente_ersetzen(b: BauKontext, p: dict) -> list[str]:
    """`ReplaceComponents2` mit Neuzuordnung der Verknüpfungen, je Ziel ein Aufruf ohne `ReplaceAllInstance`: Das träfe auch die
    Instanz, die ein späterer `komponente_entfernen` nennt, und die Menge stünde nicht mehr fest. Den neuen Namen nennt der alte
    Handle der gewählten Komponente (Beispiel der API-Hilfe)."""
    ziele, name = _ziele(b, p), p["komponente"]
    vorher_k, vorher_v = _komponenten(b), _verknuepfungen(b)
    neu, konfiguration = b.quellen[quelle_schluessel(p["quelle"])], p.get("konfiguration", "")
    zuordnung = {}
    for alt in ziele:
        komp = _komponente(b, alt)
        sw.auswahl_leeren(b.asm)
        _waehle(b.asm, komp)
        b.asm.ReplaceComponents2(str(neu.pfad), konfiguration, False,
                                 SW_ERSETZEN_BENANNT if konfiguration else SW_ERSETZEN_GLEICHER_NAME, True)
        sw.auswahl_leeren(b.asm)
        zuordnung[alt] = komp.Name2
    nachher_k, nachher_v = _komponenten(b), _verknuepfungen(b)
    _pruefe_komponenten_nach_ersetzen(b, p, zuordnung, neu, vorher_k, nachher_k)
    _pruefe_verknuepfungen_nach_ersetzen(b, name, zuordnung, vorher_v, nachher_v)
    b.ersetzt.update(zuordnung)
    b.neue[p["id"]] = sorted(zuordnung.values())
    return sorted(zuordnung.values())


# --- Verknüpfungen --------------------------------------------------------------------------------------------------------

def _kontext(b: BauKontext, komp, name: str):
    """Kontext des Teildokuments, je Datei einer: bei neuen Dateien aus `hole_neue_dateien`, bei fremden wie `punkte.kontext`.
    Eine Unterbaugruppe ist kein Anker, ihre Teile sind es (`{komponente: "Sub-1/Teil-1"}`)."""
    schluessel = _dateiname(komp)
    ctx = b.kontexte.get(schluessel)
    if ctx is None:
        model = komp.GetModelDoc2
        if model is None:
            raise BauFehler(BESTAND_REFERENZ, f"{name} ist unterdrückt oder nicht geladen, an ihr lässt sich nichts verknüpfen",
                            schritt="referenz")
        if primitiv(model.GetType) != SW_DOC_PART:
            raise BauFehler(BESTAND_REFERENZ, f"{name} ist eine Unterbaugruppe: Der Anker nennt ein Teil darin, {name}/Teil-1",
                            schritt="referenz")
        spec = {"punkte": [], "parameter": b.spec.get("parameter", {})}
        ctx = b.kontexte[schluessel] = punkte.kontext(b.app, model, spec, b.spec_pfad, b.standard["toleranzen"]["anker_mm"])
    return ctx


def _entitaet(b: BauKontext, seite: dict) -> tuple[object, bool]:
    """Anker in Koordinaten des Teils (`{komponente, nahe}`) oder mit fremden Namen (`{komponente, feature, flaeche}`,
    `{komponente, referenz}`): Fremde Namen kommen wie bei `punkte.kontext` in `ctx.ergebnisse`."""
    name = seite["komponente"]
    anker = {k: v for k, v in seite.items() if k != "komponente"}
    try:
        komp = _komponente(b, name)
        ctx = _kontext(b, komp, name)
        for schluessel in ("feature", "referenz"):
            if schluessel in anker and anker[schluessel] not in ctx.ergebnisse:
                ctx.ergebnisse[anker[schluessel]] = FeatureErgebnis([punkte._feature(ctx.model, anker[schluessel])])
        return sw_baugruppe.in_baugruppe(komp, loese_im_teil(ctx, anker))
    except Exception as e:  # Komponente nennen: Die Anker-Meldungen kennen sie nicht
        raise _mit_kontext(e, VERKNUEPFUNG_FEHLER, f"Komponente {name}", "referenz") from e


def _drehung_sperren(b: BauKontext, p: dict) -> bool:
    """Wie Spec 3b §4.4: Vorgabe bei konzentrisch mit einem Norm- oder Kaufteil. Fremde Teile geben das nicht her, sie zählen
    nicht; ein Teil des Kollegen, das eine Schraube ist, braucht `drehung_sperren`."""
    if "drehung_sperren" in p:
        return p["drehung_sperren"]
    norm = {n.pfad.name.casefold() for n in b.quellen.values() if n.art in ("normteil", "kaufteil")}
    return p["art"] == "konzentrisch" and any(_dateiname(_komponente(b, p[s]["komponente"])) in norm for s in ("a", "b"))


def _nachmesse_neue(b: BauKontext, p: dict, teile: list, vorher: set[str]) -> None:
    """Name, Typ, Partner und die genannte Ausrichtung, dazu je Konfiguration aktiv, ohne Fehler, mit den Werten des Punkts. Ein
    Wert gehört zur ersten Verknüpfung, die Anlage eines Scharniers hat keinen. `vorher`: Namen vor dem Anlegen, klein. Ein Name,
    den es schon gab, bleibt still alt (S18c), gelesen würde dann die alte Verknüpfung, und die könnte zufällig stimmen."""
    nachher = _verknuepfungen(b)
    soll, probleme = soll_werte(p, b.spec.get("parameter", {})), []
    for i, t in enumerate(teile):
        e = nachher.get(t.id)
        if t.id.casefold() in vorher:
            probleme.append(f"{t.id}: Den Namen gibt es schon, die neue Verknüpfung heißt anders")
            continue
        if e is None:
            probleme.append(f"{t.id} fehlt")
            continue
        if e["typ"] != sw_baugruppe.MATE_TYP[t.typ]:
            probleme.append(f"{t.id} hat den Typ {e['typ']} statt {sw_baugruppe.MATE_TYP[t.typ]}")
        partner = {_lauf_name(b, t.a["komponente"]), _lauf_name(b, t.b["komponente"])}
        if not partner <= set(e["partner"] or ()):
            probleme.append(f"{t.id} verbindet {e['partner']} statt {sorted(partner)}")
        if (ausrichtung := soll_ausrichtung(p, i)) is not None and e["ausrichtung"] != ausrichtung:
            probleme.append(f"{t.id}: Ausrichtung {e['ausrichtung']} statt {ausrichtung}")
        for k in b.konfigurationen:
            if e["unterdrueckt"].get(k) is not False:
                probleme.append(f"{t.id} ist unterdrückt in {k}")
            if e["fehler"].get(k) != 0:
                probleme.append(f"{t.id} hat in {k} den Fehler {e['fehler'].get(k)}")
            for feld, w in (soll.items() if i == 0 else ()):
                ist = (e["werte"].get(k) or {}).get(feld)
                if ist is None or not _gleich(ist, w):
                    probleme.append(f"{t.id}: {feld} steht in {k} auf {ist} statt {w:g}")
    if probleme:
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Punkt {p['id']}: {'; '.join(probleme)}", schritt="nachmessen")


@punkt("verknuepfung_neu")
def verknuepfung_neu(b: BauKontext, p: dict) -> list[str]:
    """Über `aufloesen._einzeln` und `sw_baugruppe.verknuepfe`, der Name ist die Punkt-ID. Eine neue Verknüpfung ist in den
    übrigen Konfigurationen unterdrückt (Annahme wie bei Features, S18c), darum aufheben. Kopplungen brauchen Verzahnungsdaten aus
    einer freigegebenen Spec, die eine fremde Datei nicht hat: Notausgang `skript`."""
    art = p["art"]
    if art in KOPPLUNGEN:
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Eine {art}-Kopplung in einer fremden Baugruppe gibt es in Etappe 2 nicht (keine "
                                             "freigegebene Verzahnung): Notausgang skript", schritt="verknuepfung")
    if art == "scharnier" and not {"anlage_a", "anlage_b"} <= set(p):
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Punkt {p['id']}: Ein Scharnier braucht anlage_a und anlage_b",
                        schritt="verknuepfung")
    v = {**p, "typ": art, "drehung_sperren": _drehung_sperren(b, p)}
    teile = _einzeln(v, p["id"], p["a"], p["b"], {}, p.get("anlage_a"), p.get("anlage_b"))
    vorher = {f.Name.casefold() for f in sw_baugruppe.verknuepfungen(b.asm)}
    for t in teile:
        f = sw_baugruppe.verknuepfe(b.asm, t, _entitaet(b, t.a), _entitaet(b, t.b), b.spec.get("parameter", {}), b.gesetzt)
        f.SetSuppression2(SW_AUFHEBEN, SW_BENANNTE_KONFIGURATIONEN, bstr_array(b.konfigurationen))
    _nachmesse_neue(b, p, teile, vorher)
    return [t.id for t in teile]


def _setze_wert(b: BauKontext, p: dict, name: str, si: float) -> None:
    """Wie `punkte.mass`, an `D1`. Benannt nur, was der Punkt nennt: Die übrigen Konfigurationen bleiben, wie der Kollege sie
    gebaut hat (Spec §4.1)."""
    alle = p.get("konfigurationen", "alle") == "alle"
    wo = (SW_WERT_ALLE, None) if alle else (SW_WERT_BENANNT, bstr_array(punkte._konfigurationen(p, b.aufnahme)))
    mass = _verknuepfung(b, name).Parameter(sw_baugruppe.MASS_NAME)
    if mass is None:
        raise BauFehler(BESTAND_REFERENZ, f"Verknüpfung {name} trägt kein Maß", schritt="referenz")
    status = mass.SetSystemValue3(si, *wo)
    if status != SW_WERT_ERFOLG:
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Verknüpfung {name}: SolidWorks lehnt den Wert ab (Status {status})",
                        schritt="setzen")


def _setze_grenze(b: BauKontext, p: dict, name: str, abstand: bool, si: float) -> None:
    """Über die Definition, die Maße gibt es nur als `D1` (S13). Absolute Werte, anders als `IMate2.Min/MaximumVariation`.
    Einmal, in der aktiven Konfiguration: `ModifyDefinition` wirkt in allen (S19e T9.27, P.e4), und je Konfiguration gesetzt war die
    Grenze danach in Standard unterdrückt, ebenso nach einem Aufruf aus „Ohne Antrieb“ (S19e3); das Nachmessen sieht es. Die
    Rückgabe zählt nicht (True auch ohne Änderung, T9.26)."""
    f = _verknuepfung(b, name)
    daten = f.GetDefinition
    setattr(daten, GRENZ_ATTRIBUT[abstand][p["grenze"]], si)
    f.ModifyDefinition(daten, b.asm, callout_leer())


def _pruefe_alt(p: dict, name: str, feld: str, mate: dict, konfigurationen: list[str]) -> None:
    """`alt` muss in allen genannten stimmen (Spec §4.1). Strenger als `punkte.mass`: Nicht lesbar zählt als Abweichung, denn das
    Nachmessen einer Verknüpfung kennt keinen Ersatzwert wie die Aufnahme eines Maßes."""
    abweichend = {k: w for k in konfigurationen if (w := _wert_gelesen(mate, k, feld)[1]) is None or not _gleich(w, p["alt"])}
    if abweichend:
        raise BauFehler(BESTAND_ALTWERT, f"Verknüpfung {name}: {feld} alt {p['alt']} stimmt nicht mit der Datei überein "
                                         f"({punkte._werte_text(abweichend)})", schritt="alt")


def _ausgeschlossen(feld: str, neu: float, genannt: list[str], vorher: dict) -> list[str]:
    """Eine Grenze, die den aktuellen Wert ausschlösse, übernimmt SolidWorks nicht (S19e T9.26); `validieren` meldet das schon, wo
    die Aufnahme den Wert kennt."""
    if feld not in ("min", "max"):
        return []
    aus = {k: w for k in genannt if (w := _wert_gelesen(vorher, k, "wert")[1]) is not None and not _gleich(w, neu)
           and (neu > w if feld == "min" else neu < w)}
    if not aus:
        return []
    return [f"{feld} {neu:g} schlösse den aktuellen Wert aus ({punkte._werte_text(aus)}), SolidWorks übernimmt so eine Grenze nicht"]


def _nachmesse_wert(b: BauKontext, name: str, feld: str, neu: float, genannt: list[str], vorher: dict, nachher: dict) -> None:
    """Das Feld steht in den genannten auf `neu`, alles andere wie vorher, in allen Konfigurationen, auch die Unterdrückung (S19e3:
    nach `ModifyDefinition` war die Grenze in Standard unterdrückt). Eine geänderte Grenze darf den aktuellen Wert mitnehmen, wie
    `vergleich_baugruppe.wert_frei`, ausschließen darf sie ihn nicht. Nicht gelesen ist nie gleich; `None` in einem gelesenen
    Eintrag heißt, das Feld trägt keinen Wert (Abstand ohne Grenzen)."""
    if name not in nachher:
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Verknüpfung {name} ist nach dem Setzen weg", schritt="nachmessen")
    probleme = _ausgeschlossen(feld, neu, genannt, vorher[name])
    for k in b.konfigurationen:
        if vorher[name]["unterdrueckt"].get(k) is False and nachher[name]["unterdrueckt"].get(k) is not False:
            probleme.append(f"unterdrückt in {k}")
        for f in WERTFELDER:
            if k in genannt and f == "wert" != feld:
                continue
            soll_gelesen, soll = (True, neu) if k in genannt and f == feld else _wert_gelesen(vorher[name], k, f)
            gelesen, ist = _wert_gelesen(nachher[name], k, f)
            if not (gelesen and soll_gelesen):
                probleme.append(f"{f} in {k} nicht lesbar")
            elif not _wert_gleich(ist, soll):
                probleme.append(f"{f} steht in {k} auf {ist} statt {soll}")
        if text := neuer_verknuepfungsfehler(vorher[name], nachher[name], k):
            probleme.append(text)
    if probleme:
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Verknüpfung {name}: {'; '.join(probleme)} – gesteuert?", schritt="nachmessen")


@punkt("verknuepfung_wert")
def verknuepfung_wert(b: BauKontext, p: dict) -> list[str]:
    """Wert oder Grenze, nur in den genannten Konfigurationen (Vorgabe alle). `alt` wird live je genannter gegengeprüft, auch für
    `grenze`; nachgemessen wird in allen. Die Art liest `lies_verknuepfungen`, die Einheit folgt aus ihr."""
    name, feld = p["verknuepfung"], p.get("grenze") or "wert"
    genannt = punkte._konfigurationen(p, b.aufnahme)
    if "grenze" in p and set(genannt) != set(b.konfigurationen):  # `validieren` weist das ab, hier die zweite Linie
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Verknüpfung {name}: Eine Grenze gilt für alle Konfigurationen (ModifyDefinition), "
                                             f"nicht nur für {', '.join(genannt)}: Notausgang skript", schritt="referenz")
    vorher = _verknuepfungen(b)
    if name not in vorher:
        raise BauFehler(BESTAND_REFERENZ, f"Verknüpfung {name!r} gibt es in der Baugruppe nicht", schritt="referenz")
    _pruefe_alt(p, name, feld, vorher[name], genannt)
    neu = float(auswerten(p["neu"], b.spec.get("parameter", {})))
    abstand = vorher[name]["typ"] == SW_ABSTAND
    si = mm(neu) if abstand else grad(neu)
    if "grenze" in p:
        _setze_grenze(b, p, name, abstand, si)
    else:
        _setze_wert(b, p, name, si)
    _nachmesse_wert(b, name, feld, neu, genannt, vorher, _verknuepfungen(b))
    return [name]


@punkt("verknuepfung_loeschen")
def verknuepfung_loeschen(b: BauKontext, p: dict) -> list[str]:
    """`sw_baugruppe.loesche` prüft nur die eine; hier zählt auch, dass keine andere mitgeht, in allen Konfigurationen."""
    name, vorher = p["verknuepfung"], _verknuepfungen(b)
    sw_baugruppe.loesche(b.asm, _verknuepfung(b, name))
    weg = set(vorher) - set(_verknuepfungen(b))
    if name not in weg:
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Verknüpfung {name} ist noch da", schritt="nachmessen")
    if andere := sorted(weg - {name}):
        raise BauFehler(VERKNUEPFUNG_FEHLER, f"Das Löschen von {name} nahm auch {', '.join(andere)} mit", schritt="nachmessen")
    return [name]
