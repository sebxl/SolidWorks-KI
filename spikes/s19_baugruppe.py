"""S19 a–f: Baugruppen live (Spec Bestandsdateien §11, Plan Etappe 2 Task 12). Die Schicht aus den Tasks 8 bis 11 steht gegen den
Index und Attrappen; dieser Spike misst sie an echten Dateien und beantwortet die Pflichtfragen aus den Berichten, nummeriert in
`FRAGEN`: `T8.n`, `T9.n`, `T10.n`, `T11.n`, `T11.Kn` (Korrekturrunde von Task 11), `P.<zeile>n` (Plan-Tabelle und Hinweise aus
progress.md).

Wegwerf-Qualität wie S18. Jede Zeile läuft einzeln, mit Zeitlimit von außen, weil ein modaler Dialog COM hängen lassen kann; jeder
Schritt steht sofort in docs/bestandsdateien/s19_<zeile>.json, mit Zeit und Private Bytes. Eine gescheiterte Frage kostet nur sich
selbst (`Lauf.frage`), ihr Fehler ist die Antwort. `halt` nennt, was den Plan anhält (Plan Task 12 Step 3): `teile/` nicht
getragen, Auflösung vor dem Öffnen anders als das Öffnen.

Schutz, im Skript selbst geprüft: Geöffnet und geschrieben wird nur unter <arbeitsordner>/S19/ (`pruefe_pfad`, einziger Weg zu
`OpenDoc6` ist `oeffne`, die swki-Wege bekommen nur Pfade aus `frisch`), nie ein Pfad unter AP68-Pruefstation, und vor jeder Zeile
muss SolidWorks leer sein (`pruefe_leer`). Ausnahme ist Zeile v: Sie baut die Referenz Schlitten über `swki bauen` im eigenen
Testauftrag und arbeitet dann an einer Kopie unter S19/.

Reihenfolge nach Risiko (`REIHENFOLGE`), vor jeder Zeile SolidWorks frisch starten (S18: ab 5,4 GB RPC_E_DISCONNECTED).
Voraussetzung: `-m werkzeuge.bestand_muster hubeinheit`.

Aufruf (SolidWorks offen, frei): timeout 600 ..\\..\\..\\.venv\\Scripts\\python.exe -m spikes.s19_baugruppe c

API (swki api methode, Parameterzahl laut Index; Enums laut swki api enum):
  ISldWorks.GetDocumentDependencies2(4), .OpenDoc6(6), .CloseDoc(1), .GetDocuments(0), .GetDocumentCount(0), .DocumentVisible(2),
    .GetProcessID(0), .VersionHistory(1)
  swOpenDocOptions_e: Silent 1, ReadOnly 2, OverrideDefaultLoadLightweight 64
  swFileLoadWarning_e: IdMismatch 1, ReadOnly 2, NeedsRegen 32, AlreadyOpen 128, MissingExternalReferences 1048576
  IModelDoc2.Save3(3), .ShowConfiguration2(1), .GetConfigurationNames(0), .ForceRebuild3(1), .EditRebuild3(0), .GetSaveFlag(0),
  .GetType(0),
    .IsOpenedReadOnly(0), .Parameter(1), .SelectionManager, .FeatureManager, .Extension, .ConfigurationManager
  IModelDocExtension.GetWhatsWrongCount(0), .ListExternalFileReferences(9), .CustomPropertyManager(1), .SelectByRay(11)
  IAssemblyDoc.GetComponents(1), .AddComponent5(8), .AddMate5(15), .CreateMateData(1), .CreateMate(1), .InsertNewVirtualPart(2),
    .ReplaceComponents2(5), .FixComponent(0), .InterferenceDetectionManager
  IInterferenceDetectionMgr.GetInterferenceCount(0), .GetInterferences(0), .TreatCoincidenceAsInterference, .Done(0)
  IComponent2.Name2, .GetPathName(0), .GetSuppression2(0), .SetSuppression2(1), .GetModelDoc2(0), .IsVirtual,
  .IsPatternInstance(0), .Solving,
    .IsFixed(0), .GetConstrainedStatus(0), .ReferencedConfiguration, .Transform2, .Select4(3), .FeatureByName(1),
    .GetCorrespondingEntity(1),
    .SetTransformAndSolve2(1)
  IFeature.GetTypeName2(0), .GetSpecificFeature2(0), .GetDefinition(0), .ModifyDefinition(3), .GetErrorCode2(1), .Parameter(1),
  .IsSuppressed2(2),
    .SetSuppression2(3), .GetFirstSubFeature(0), .GetNextSubFeature(0), .GetFirstDisplayDimension(0), .GetNextDisplayDimension(1),
    .Select2(2)
  IDisplayDimension.GetDimension2(1); IDimension.FullName, .SystemValue, .SetSystemValue3(3)
  IMate2.Type, .Alignment, .GetMateEntityCount(0), .MateEntity(1), .MinimumVariation, .MaximumVariation
  IMateEntity2.Reference, .ReferenceComponent, .ReferenceType2
  IDistanceMateFeatureData.Distance, .MinimumDistance, .MaximumDistance, .FlipDimension, .IsAdvancedMate, .EntitiesToMate
  IWidthMateFeatureData.WidthSelection, .TabSelection; ISymmetricMateFeatureData.EntitiesToMate, .SymmetryPlane
  ISelectionMgr.GetSelectedObjectCount2(1), .GetSelectedObjectType3(2), .GetSelectedObjectsComponent4(2), .CreateSelectData(0)
  IFeatureManager.GetFeatures(1), .InsertFeatureTreeFolder2(1: swFeatureTreeFolder_Containing 2), .CreateDefinition(1:
  swFmLocalLPattern 108),
    .CreateFeature(1); ILocalLinearPatternFeatureData.D1Spacing, .D1TotalInstances, .D1ReverseDirection, .D2TotalInstances
  swMateType_e: Abstand 5, Symmetrie 8, Breite 11; swMateAlign_e: gleich 0, entgegengesetzt 1, nächste 2; swAddMateError_e:
  NoError 1
  swComponentSuppressionState_e: Suppressed 0, FullyResolved 2, Resolved 3
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import time
import traceback
from contextlib import contextmanager
from functools import cache
from pathlib import Path

import pythoncom
import win32com.client

from swki.baugruppe import sw_baugruppe
from swki.bestand import punkte, punkte_baugruppe
from swki.bestand.bewegung_bestand import (abdeckung, als_verknuepfung, fahre_bestand, grenzen_der_aufnahme, statische_paare)
from swki.bestand.pfade import aufgeloeste_referenzen, offene_dokumente, oeffne_in, pruefe_geladen
from swki.bestand.spec_baugruppe import quelle_schluessel
from swki.bestand.sw_baugruppe_bestand import (_entitaeten, baum_ohne_glieder, gegenprobe_verknuepfungen, lies_baugruppe,
                                               lies_kollisionen,
                                               lies_komponenten, lies_verknuepfungen, mechanik_fuer)
from swki.bestand.sw_bestand import datei_referenzen, eigenschaften_von, schalte, unterdrueckt, whats_wrong, zeige_komponente
from swki.compiler import sw
from swki.compiler.protokoll import Protokoll
from swki.konfig import PROJEKT, lade_rechner, lade_standard
from swki.pruefung.bilder import iso_bild, screenshots
from swki.pruefung.messen import kontext_aus_datei, messe
from swki.speicher import Spitzenmessung, privat_mb
from swki.verbindung import byref_long, byref_str, byref_variant, callout_leer, dispatch_array, in_mm, mm, verbinde
from swki.verbindung import wert as primitiv
from werkzeuge.bestand_muster import HUB_DATEIEN, HUBEINHEIT, KONFIG_OHNE, baue_block, hubeinheit_ordner, volumen

ERGEBNIS = PROJEKT / "docs" / "bestandsdateien"
GESPERRT = "ap68-pruefstation"  # Präfix, klein: auch AP68-Pruefstation-Rev1
AUFTRAG_SCHLITTEN = "LIVE-S19-SCHLITTEN"
OFFEN, NUR_LESEN, VOLL = 1, 2, 64  # swOpenDocOptions_e
SW_DOC_PART, SW_DOC_ASSEMBLY = 1, 2
SW_WERT_ALLE, SW_WERT_BENANNT = 2, 3  # swSetValueInConfiguration_e
SW_UNTERDRUECKT, SW_AUFGELOEST, SW_AUFGELOEST_LEICHT = 0, 2, 3  # swComponentSuppressionState_e
SW_ABSTAND, SW_SYMMETRIE, SW_BREITE = 5, 8, 11  # swMateType_e
SW_ORDNER_MIT_INHALT = 2    # swFeatureTreeFolderType_e.swFeatureTreeFolder_Containing
SW_LOKALES_MUSTER = 108     # swFeatureNameID_e.swFmLocalLPattern
WARNUNGEN = {1: "id_abweichung", 2: "nur_lesen", 32: "neuaufbau_noetig", 128: "schon_offen", 1048576: "referenz_fehlt"}
AUFSATZ = "Aufsatz-Linear austragen1"
DICKE = f"D1@{AUFSATZ}"  # Dicke der Grundplatte, Höhe von Schlitten und Anschlag

ZEIT = {"c": 600, "b": 600, "a": 300, "f": 300, "d": 600, "e": 900, "e2": 600, "v": 1500}  # Sekunden, Zeitlimit von außen
REIHENFOLGE = ("c", "b", "a", "f", "d", "e", "e2", "v")

FRAGEN: dict[str, tuple[str, str]] = {
    # Bericht Task 8
    "T8.1": ("a",
             "Ist Variation ungleich 0 der richtige Test auf eine Grenze, oder Typname MateLimitDistanceDim, IsAdvancedMate? "
             "min = max?"),
    "T8.2": ("a", "Trägt jeder Abstand und Winkel ein Maß D1? Heißen fremde anders, gibt es Variation ohne Grenze?"),
    "T8.3": ("a", "Tragen andere Typen Werte (Breite, Nut, Schraube, Symmetrie)?"),
    "T8.4": ("a", "ReferenceComponent an einer Ebene der Hauptbaugruppe: None oder Wurzelkomponente? In einer Unterbaugruppe?"),
    "T8.5": ("a", "Gibt eine unterdrückte Verknüpfung GetSpecificFeature2, Type, MateEntity, Parameter(D1) her?"),
    "T8.6": ("b",
             "Typ von MateEntity(i).Reference, ist eine Ebene ein IFeature, Entität im Baugruppenkontext? Sonst EntitiesToMate"),
    "T8.7": ("b", "Ist D1 der Grenze der Abstand, den treibe braucht, auch bei umgekehrter Bemaßung?"),
    "T8.8": ("b", "Reicht Probeschritt plus stelle zurück, oder springt die Komponente nach loese und Reaktivieren?"),
    "T8.9": ("c",
             "GetPathName unterdrückter und leicht geladener Komponenten: gespeichert oder aufgelöst? Blockiert der Pfadschutz?"),
    "T8.10": ("c", "Bleibt ein als-gespeichert-Pfad auch nach voll (Option 64)?"),
    "T8.11": ("c", "Enthält GetDocumentDependencies2 andere Dateitypen (Tabelle, .step eines Imports, .sldlfp)?"),
    "T8.12": ("d",
              "GetInterferenceCount unsichtbar und nur lesend verlässlich, gleich Länge von GetInterferences? Läuft die "
              "Berechnung zweimal?"),
    "T8.13": ("d", "Darf Done nach dem Lesen der IInterference kommen?"),
    "T8.14": ("f", "Liefert GetComponents(False) Unterdrückte und Kinder unterdrückter Unterbaugruppen?"),
    "T8.15": ("f",
              "Name2 in IInterference.Components und ReferenceComponent gleich wie in GetComponents, auch in Unterbaugruppen?"),
    "T8.16": ("f", "IsFixed bei Kindern?"),
    "T8.17": ("f", "Typnamen Reference, ReferencePattern, MateGroup; Komponenten als Features in der Kette, Unterfeatures?"),
    "T8.18": ("f", "Wo stehen Verknüpfungen in einem Ordner unter MateGroup?"),
    "T8.19": ("f", "Was meldet ListExternalFileReferences an einer Baugruppe, nennt es Komponenten?"),
    "T8.20": ("f", "Geht Anlegen und Löschen der treibenden Verknüpfung am schreibgeschützten Dokument?"),
    "T8.21": ("d", "Ist eine per Select4 gewählte Komponente im gespeicherten Bild sichtbar?"),
    "T8.22": ("b", "Bleiben die Zeiger aus MateEntity(i).Reference über Neuaufbauten gültig?"),
    "T8.23": ("c", "Bleiben nach CloseDoc verdeckt Dokumente offen, trifft das einzelne Lesen gleichnamige?"),
    "T8.24": ("f", "GetFeatures(False): Verknüpfungen auch in Ordnern, nur die der Hauptbaugruppe? Weitere Typen mit Mate vorn?"),
    "T8.25": ("f", "Ordner-Verknüpfung: Abstieg über GetFirstSubFeature oder flach mit Abschluss-Eintrag?"),
    "T8.26": ("a", "IsSuppressed2 an einer Verknüpfung je Konfiguration?"),
    # Bericht Task 9, Zeile e
    "T9.1": ("e", "AddComponent5 mit benannter Konfiguration: Wird sie genommen?"),
    "T9.2": ("e", "Neue Komponente in den übrigen Konfigurationen unterdrückt?"),
    "T9.3": ("e", "IComponent2.SetSuppression2: nur aktive Konfiguration? 2 oder 3? Rückgabe 2 verlässlich?"),
    "T9.4": ("e", "Nennt GetComponents(False) die neue Komponente auch dort, wo sie unterdrückt ist?"),
    "T9.5": ("e", "ReferencedConfiguration = x: je Baugruppen-Konfiguration, Neuaufbau nötig?"),
    "T9.6": ("e", "FixComponent je Konfiguration?"),
    "T9.7": ("e", "wie: Identität bewegt nur die neue? Keine aktive Instanz: reicht oeffne_in? wie an einer Unterbaugruppe?"),
    "T9.8": ("e", "Bleibt ein unsichtbar geöffnetes Teil geladen, wenn die Baugruppe sichtbar öffnet?"),
    "T9.9": ("e", "Name einer Datei mit .sldprt klein (Name2-Stamm, GetPathName)?"),
    "T9.10": ("e", "DeleteSelection2(0) an einer Komponente: reicht 0, Verknüpfungen und Kinder, Dialog?"),
    "T9.11": ("e", "Verknüpfung in einem Ordner unter MateGroup: Geht sie mit?"),
    "T9.12": ("e", "Reicht die Vorauswahl über Select4 für ReplaceComponents2?"),
    "T9.13": ("e", "Zeigt der alte IComponent2 danach den neuen Name2?"),
    "T9.14": ("e", "ConfigName leer mit MatchName und Name mit ManuallySelect, in allen Konfigurationen?"),
    "T9.15": ("e", "Bleiben neues Dokument, ctx.model, b.kontexte, b.offen nach dem Ersetzen gültig?"),
    "T9.16": ("e", "Verknüpfung, die sich nicht neu zuordnen lässt: gelöscht oder Fehlercode, Name?"),
    "T9.17": ("e", "Lässt sich eine unterdrückte Instanz wählen und ersetzen?"),
    "T9.18": ("e", "IFeature.SetSuppression2(1, 3, Namen) an einer neuen Verknüpfung: wirkt es, ist sie dort unterdrückt?"),
    "T9.19": ("e", "Partner in einer Konfiguration unterdrückt: Gilt die neue Verknüpfung dort als unterdrückt?"),
    "T9.20": ("e", "Doppelter Name an einer Verknüpfung still alt? Name mit Punkt in einer fremden Datei?"),
    "T9.21": ("e", "GetModelDoc2 gegen ReferencedConfiguration: Passen nahe, flaeche, GetCorrespondingEntity bei Abweichung?"),
    "T9.22": ("e", "GetCorrespondingEntity bei mehreren Instanzen und in einer Unterbaugruppe, nimmt Select4 das? Name2 mit /?"),
    "T9.23": ("e", "komp.FeatureByName für referenz in einem fremden Teil?"),
    "T9.24": ("e", "SetSystemValue3 an D1 mit Option 3 und 2: je Konfiguration, nach ForceRebuild3? Status? Vorzeichen?"),
    "T9.25": ("e", "GetDefinition über late binding: MinimumDistance direkt, IsAdvancedMate bei fremden Grenzen immer wahr?"),
    "T9.26": ("e", "Minimum/Maximum absolut, konsistent zu D1 und Variation? D1 außerhalb der neuen Grenzen?"),
    "T9.27": ("e", "ModifyDefinition je Konfiguration oder in allen?"),
    "T9.28": ("e", "ModifyDefinition(daten, asm, callout_leer()): VT_DISPATCH None als Nothing, oder None? AccessSelections?"),
    "T9.29": ("e", "Select2 plus EditDelete an einer fremden Verknüpfung, in allen Konfigurationen und im Ordner?"),
    "T9.30": ("e", "IFeature in ctx.ergebnisse gültig, wenn zwischen zwei Punkten die Konfiguration umschaltet?"),
    "T9.31": ("e", "Neuaufbau nach ModifyDefinition nötig, bevor die nächste Konfiguration umschaltet?"),
    # Bericht Task 10
    "T10.1": ("e", "Save3 an der Baugruppe: schreibt es geänderte Komponenten mit? Baugruppe ohne echte Änderung neu?"),
    "T10.2": ("e",
              "Teil in einer Unterbaugruppe geändert: bleibt Unter.SLDASM ungespeichert, zeigt die Hauptbaugruppe den neuen "
              "Stand?"),
    "T10.3": ("e", "Teil-Scheibe unsichtbar: laufen die Handler von Etappe 1 ohne Fenster? Speicher?"),
    "T10.4": ("e", "GetWhatsWrong an Verknüpfungen: nennt es sie, Feature-Name, Code gleich GetErrorCode2?"),
    "T10.5": ("e", "Rückgabe von ForceRebuild3 bei alten Fehlern?"),
    "T10.6": ("e", "EditRebuild3 nach einem Punkt: reicht das an der Baugruppe oder braucht es ForceRebuild3?"),
    "T10.7": ("c", "Öffnen nach geänderten Teilen: Warnung 32, Dialog, Neuaufbau beim Öffnen?"),
    "T10.8": ("e", "Baugruppe öffnen, während neue Teile unsichtbar offen sind: Meldung, trifft oeffne_in alles Geladene?"),
    "T10.9": ("e", "CloseDoc einer neu aufgebauten, ungespeicherten Baugruppe: still, Frage nach Komponenten?"),
    "T10.10": ("e", "Schließreihenfolge, schließt SolidWorks Unsichtbare mit, toter Handle AttributeError oder com_error?"),
    "T10.11": ("c", "Sperre 1 am Lauf: löst GetDocumentDependencies2 auf den Lauf-Ordner auf, auch teile/ und flach?"),
    "T10.12": ("e", "Öffnet die Lauf-Kopie in aufnahme[aktiv]?"),
    "T10.13": ("e", "Teil gespeichert in seiner aktiven Konfiguration: bleibt ReferencedConfiguration unverändert?"),
    "T10.14": ("e", "skript an der Hauptbaugruppe: fuehre_aus mit ctx.model als Baugruppe?"),
    "T10.15": ("e", "Laufzeit: Neuaufbau je Konfiguration und je Handler"),
    "T10.16": ("e", "Stimmt baum_ohne_glieder, ändern neue Komponente und Verknüpfung die Reihenfolge der übrigen Features?"),
    # Bericht Task 11
    "T11.1": ("b", "Read-only-Lauf: treibende Verknüpfung anlegen, stellen, löschen, Iso-Bild speichern?"),
    "T11.2": ("b", "CloseDoc nach der Fahrt still, Lauf-Datei byteweise gleich?"),
    "T11.3": ("d",
              "ForceRebuild3 am read-only Lauf je Konfiguration: Lage und Status, geändertes Teil neben ungespeicherter "
              "Baugruppe?"),
    "T11.4": ("f", "datei_referenzen der Hauptbaugruppe: Nennt es Komponentendateien?"),
    "T11.5": ("f",
              "baum, masse, skizzen, neuaufbau über vergleiche: Reihenfolge nach neuer Komponente, Codes GetWhatsWrong gegen "
              "GetErrorCode2?"),
    "T11.6": ("d", "Zweimal öffnen, erst unsichtbar, dann mit Fenster: zu, kein Titel-Fehler, Komponenten im Speicher?"),
    "T11.7": ("d", "Teil nach CloseDoc aus dem Speicher? vorher_*-Datei in vergleich/: Greift eine Suchregel darauf zu?"),
    "T11.8": ("c", "pruefe_vor_dem_oeffnen an vorher_<rel>: leer, auch bei abgeleiteter Konfiguration oder Tabelle?"),
    "T11.9": ("d", "Bilder: gleiche Ansicht und Zoom in Bestand und Lauf, aktive Konfiguration?"),
    "T11.10": ("d", "Speicher: Spitze mit Fenstern und Fahrt, SPEICHER_KNAPP mit frisch"),
    "T11.11": ("d", "Laufzeit: lies_baugruppe ohne sw.schnell"),
    "T11.12": ("b", "Neuer Verknüpfungsfehler in der Fahrt: StellungFehler oder BauFehler?"),
    "T11.13": ("f", "lies_baugruppe_einzeln: Gegenprobe je Unterbaugruppe gleich, wenn sich ein Kind geändert hat?"),
    "T11.14": ("e", "Trägt protokoll.neue_dateien den Namen, den GetPathName zeigt?"),
    "T11.K1": ("d", "Wirkt ForceRebuild3(False) am nur lesend geöffneten Lauf?"),
    "T11.K2": ("d", "Lässt sich ausgabe/ umbenennen, wenn der Explorer den Ordner zeigt?"),
    "T11.K3": ("d", "Geht messe an einem unsichtbaren, nur lesend geöffneten Teil?"),
    "T11.K4": ("e", "Trägt GetPathName in neue_dateien den Namen der Teil-Spec, auch bei Sonderzeichen?"),
    # Plan Task 12 und Hinweise aus progress.md
    "P.a1": ("a", "Woran erkennt man eine Grenzverknüpfung: IMate2 oder GetDefinition?"),
    "P.a2": ("a", "Werte in mm?"),
    "P.a3": ("a", "Partner bei Ebene der Baugruppe?"),
    "P.a4": ("a", "Abstandswerte exakt oder Betrag (Task 5)?"),
    "P.a5": ("a", "Fehlercode 0 heißt kein Fehler (Task 5)?"),
    "P.a6": ("v", "Scharnier gleich zwei Verknüpfungen (Task 5)?"),
    "P.a7": ("a", "Solving und IsPatternInstance lesbar (Task 5)?"),
    "P.b1": ("b", "Reference oder EntitiesToMate für treibe auswählbar?"),
    "P.b2": ("b", "Überleben die Zeiger das Unterdrücken der Grenze und den Neuaufbau?"),
    "P.b3": ("b", "Antrieb bei umgekehrter Bemaßung auf der richtigen Seite (verknuepfe setzt Flip False)?"),
    "P.b4": ("b", "Fährt das an nur lesend geöffneter Kopie?"),
    "P.b5": ("b", "SHA-256 danach gleich?"),
    "P.b6": ("b", "Index in als_verknuepfung: Entität 0 ist Partner 0 (Task 6)?"),
    "P.c1": ("c", "Struktur teile/ bei vorhandenem Original: aus der Kopie geladen?"),
    "P.c2": ("c", "Datei flach daneben?"),
    "P.c3": ("c", "Löst GetDocumentDependencies2(…, True, True, False) genauso auf wie das Öffnen?"),
    "P.c4": ("c", "Auch bei einem Original im Arbeitsordner, im Speicher?"),
    "P.c5": ("c", "Zurückkopierte Baugruppe mit Lauf-Pfaden lädt was?"),
    "P.c6": ("c", "Schließt SolidWorks nach einem Pfad-Fund nachgeladene fremde Dokumente mit (Task 2)?"),
    "P.c7": ("c", "Geänderte Hauptbaugruppe plus flaches Fremdteil nach dem Zurückkopieren (Task 11)?"),
    "P.d1": ("d", "Unsichtbar mit Option 1|64|2: Kollision, Transform2, Status lesbar?"),
    "P.d2": ("d", "Zeit und Speicher gegenüber sichtbar?"),
    "P.e1": ("e", "Einfügen an fremder Baugruppe"),
    "P.e2": ("e", "ReplaceComponents2: Bleibt Name2?"),
    "P.e3": ("e", "Löschen"),
    "P.e4": ("e", "Grenze über ModifyDefinition, je Konfiguration"),
    "P.f1": ("f", "GetTypeName2 von Komponente, Verknüpfung, Komponentenmuster, virtuellem Teil"),
    "P.f2": ("f", "Wie erscheint ein virtuelles Teil in GetDocumentDependencies2?"),
    "P.f3": ("f", "Name2 und Transform2 in Unterbaugruppen: Bezug oberste Baugruppe?"),
    "P.f4": ("f", "Was meldet ListExternalFileReferences an einer Baugruppe?"),
    "P.f5": ("v", "Abgleich auf unverändertem Lauf leer (Task 7)?"),
    "P.f6": ("v", "TYP_TABELLE gegen echte Dateien (Task 7, Extrusion, ICE, Cut)"),
    "P.f7": ("v", "VORLAGE_TYPEN an einem swki-Teil, Fehlalarme (Task 8)?"),
    "P.f8": ("f", "abdeckung: Partner mit weiteren freien Richtungen (Task 11)?"),
}


class Sperre(RuntimeError):
    """Das Skript bricht ab, bevor es etwas anfasst, das nicht ihm gehört."""


@cache
def rechner():
    return lade_rechner()


def s19_ordner() -> Path:
    return rechner().arbeitsordner / "S19"


def _gesperrt(p: Path) -> bool:
    return any(teil.casefold().startswith(GESPERRT) for teil in p.parts)


def pruefe_pfad(pfad: Path, wurzel: Path | None = None) -> Path:
    """Nur unter `<arbeitsordner>/S19/`, nie unter AP68-Pruefstation; aufgelöst, damit `..` nichts umgeht."""
    p, s19 = Path(pfad).resolve(), Path(wurzel if wurzel is not None else s19_ordner()).resolve()
    if _gesperrt(p):
        raise Sperre(f"{p}: Die Prüfstation gehört dem Nutzer, S19 fasst sie nicht an (AP68-Pruefstation)")
    if not p.is_relative_to(s19):
        raise Sperre(f"{p} liegt nicht unter {s19}: S19 läuft nur an Kopien dort")
    return p


def pruefe_quelle(pfad: Path) -> Path:
    """Eine Quelle zum Kopieren darf außerhalb von S19 liegen, die Prüfstation ist es nie."""
    p = Path(pfad).resolve()
    if _gesperrt(p):
        raise Sperre(f"{p}: Die Prüfstation gehört dem Nutzer, S19 fasst sie nicht an (AP68-Pruefstation)")
    return p


def pruefe_leer(app) -> None:
    """Der Spike schließt am Ende alles: Ein offenes Dokument gehörte dem Nutzer."""
    offen = [primitiv(d.GetPathName) or primitiv(d.GetTitle) for d in primitiv(app.GetDocuments) or ()]
    if offen:
        raise Sperre(f"In SolidWorks sind Dokumente offen, S19 startet nicht: {', '.join(offen)}")


def warnbits(wert: int) -> list[str]:
    return [name for bit, name in WARNUNGEN.items() if wert & bit]


def versuch(lesen):
    """Wert von `lesen()` oder der Fehler als Text: Eine Messung, die nicht geht, ist ein Ergebnis."""
    try:
        return lesen() if callable(lesen) else lesen
    except Exception as e:
        return {"fehler": f"{type(e).__name__}: {e}", "stelle": traceback.format_exc(limit=-2)}


class Lauf:
    """Sammelt die Antworten einer Zeile und schreibt sie nach jedem Schritt weg (Hänger verlieren nichts)."""

    def __init__(self, app, zeile: str):
        self.app, self.zeile = app, zeile
        self.pid = int(primitiv(app.GetProcessID))
        self.t0 = time.monotonic()
        self.d: dict = {"zeile": zeile, "start_mb": round(privat_mb(self.pid)), "spitze_mb": 0, "halt": [], "fragen": {}}

    def __setitem__(self, k, v) -> None:
        self.d[k] = v
        self.schreibe()

    def __getitem__(self, k):
        return self.d[k]

    def frage(self, nummer: str, lesen, fall: str | None = None):
        """Beantwortet eine Pflichtfrage; mehrere Fälle je Frage stehen untereinander. `lesen`: Wert oder Funktion."""
        wert = versuch(lesen)
        eintrag = self.d["fragen"].setdefault(nummer, {"frage": FRAGEN[nummer][1], "antworten": []})
        eintrag["antworten"].append({**({"fall": fall} if fall else {}), "wert": wert})
        self.schreibe()
        return wert

    def halt(self, grund: str) -> None:
        self.d["halt"].append(grund)
        self.schreibe()

    def schreibe(self) -> None:
        mb = round(privat_mb(self.pid))
        self.d |= {"sekunden": round(time.monotonic() - self.t0, 1), "ende_mb": mb, "spitze_mb": max(self.d["spitze_mb"], mb)}
        ERGEBNIS.mkdir(parents=True, exist_ok=True)
        (ERGEBNIS / f"s19_{self.zeile}.json").write_text(json.dumps(self.d, indent=1, ensure_ascii=False, default=str),
                                                         encoding="utf-8")

    def schliesse(self) -> None:
        self.d["unbeantwortet"] = [n for n, (z, _) in FRAGEN.items() if z == self.zeile and n not in self.d["fragen"]]
        self.schreibe()


# ---------------------------------------------------------------------- Helfer


def frisch(name: str) -> Path:
    p = pruefe_pfad(s19_ordner() / name)
    if p.exists():
        for k in p.rglob("*"):
            if k.is_file():
                k.chmod(stat.S_IWRITE)
        shutil.rmtree(p)
    p.mkdir(parents=True)
    return p


def kopiere_stand(quelle: Path, ziel: Path, ohne=()) -> Path:
    """Alle Dateien der Hubeinheit mit Struktur, beschreibbar; `ohne`: relative Pfade, die fehlen sollen."""
    pruefe_pfad(ziel)
    for rel in HUB_DATEIEN:
        if rel not in ohne:
            (ziel / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pruefe_quelle(quelle / rel), ziel / rel)
            (ziel / rel).chmod(stat.S_IWRITE)
    return ziel


def bestuecke(name: str) -> Path:
    return kopiere_stand(hubeinheit_ordner(rechner()), frisch(name))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def shas(ordner: Path) -> dict:
    return {p.relative_to(ordner).as_posix(): sha(p) for p in sorted(ordner.rglob("*"))
            if p.is_file() and p.suffix.lower() in (".sldprt", ".sldasm") and not p.name.startswith("~$")}  # ~$: Sperrdatei offener


def schreibschuetze(ordner: Path) -> None:
    for p in ordner.rglob("*"):
        if p.is_file():
            p.chmod(stat.S_IREAD)


def namen(liste):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_BSTR, list(liste))


def oeffne(app, pfad: Path, optionen: int = OFFEN | VOLL, konf: str = "", sichtbar: bool = True):
    """Der einzige `OpenDoc6` des Skripts."""
    pfad = pruefe_pfad(pfad)
    typ = SW_DOC_ASSEMBLY if pfad.suffix.lower() == ".sldasm" else SW_DOC_PART
    e, w = byref_long(), byref_long()
    t = time.monotonic()
    if not sichtbar:
        app.DocumentVisible(False, typ)
    try:
        model = app.OpenDoc6(str(pfad), typ, optionen, konf, e, w)
    finally:
        if not sichtbar:
            app.DocumentVisible(True, typ)
    return model, {"fehler": e.value, "warnungen": warnbits(w.value), "s": round(time.monotonic() - t, 2)}


def offene(app) -> list:
    return [primitiv(d.GetPathName) or primitiv(d.GetTitle) for d in primitiv(app.GetDocuments) or ()]


def alle_zu(app) -> None:
    for _ in range(4):
        docs = primitiv(app.GetDocuments) or ()
        if not docs:
            return
        for d in docs:
            try:
                app.CloseDoc(d.GetTitle)
            except Exception:
                pass


def speichern(model) -> dict:
    e, w = byref_long(), byref_long()
    return {"ok": model.Save3(1, e, w), "fehler": e.value, "warnungen": warnbits(w.value)}


@contextmanager
def arbeit(app, name: str):
    """Eine frische beschreibbare Kopie, die Baugruppe offen wie im Bau (Fenster, voll, Pfadschutz); am Ende alles zu."""
    ordner = bestuecke(name)
    asm = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=True, nur_lesen=False)
    try:
        yield asm, ordner
    finally:
        alle_zu(app)


def lage_mm(k) -> list | None:
    try:
        return [round(in_mm(x), 3) for x in k.Transform2.ArrayData[9:12]]
    except Exception:
        return None


def stand_der_komponente(k) -> dict:
    return {"name": k.Name2, "pfad": versuch(lambda: primitiv(k.GetPathName)),
            "zustand": versuch(lambda: primitiv(k.GetSuppression2)),
            "dokument": versuch(lambda: k.GetModelDoc2 is not None), "virtuell": versuch(lambda: bool(primitiv(k.IsVirtual))),
            "status": versuch(lambda: primitiv(k.GetConstrainedStatus)), "lage": lage_mm(k)}


def komponenten(asm) -> list:
    return list(asm.GetComponents(False) or ())


def komp(asm, name: str):
    return next((k for k in komponenten(asm) if k.Name2 == name), None)


def mate(asm, name: str):
    return next(f for f in sw_baugruppe.verknuepfungen(asm) if f.Name == name)


def verknuepfe_roh(asm, name: str, typ: int, ausrichtung: int, a, b, wert=0.0, oben=None, unten=None, flip=False):
    """`AddMate5` an den Entitäten (Objekt, ist Feature), wie `sw_baugruppe.waehle`, Name gesetzt, kein Neuaufbau."""
    vorher = {f.Name for f in sw_baugruppe.verknuepfungen(asm)}
    sw.auswahl_leeren(asm)
    sw_baugruppe.waehle(asm, a, False)
    sw_baugruppe.waehle(asm, b, True)
    status = byref_long()
    asm.AddMate5(typ, ausrichtung, flip, mm(wert), mm(oben if oben is not None else wert), mm(unten
            if unten is not None else wert), 1,
            1,
                 0.0, 0.0, 0.0, False, False, 0, status)
    sw.auswahl_leeren(asm)
    neu = [f for f in sw_baugruppe.verknuepfungen(asm) if f.Name not in vorher]
    if neu:
        neu[-1].Name = name
    return {"status": status.value, "neu": [f.Name for f in neu]}


def loesche_roh(asm, feature) -> None:
    sw.auswahl_leeren(asm)
    feature.Select2(False, 0)
    sw_baugruppe.rufe(asm, "EditDelete")
    sw.auswahl_leeren(asm)


def setze_dicke(app, pfad: Path, wert: float) -> dict:
    """Ein Kennzeichen in der Datei selbst: Die Geometrie sagt, woher sie geladen wurde, nicht nur der Pfad."""
    m, s = oeffne(app, pfad)
    status = m.Parameter(DICKE).SetSystemValue3(mm(wert), SW_WERT_ALLE, None)
    m.EditRebuild3
    aus = {"oeffnen": s, "status": status, "speichern": speichern(m), "volumen": volumen(m)}
    app.CloseDoc(m.GetTitle)
    return aus


def als_original(app, ordner: Path, aktiv: str | None = None) -> dict:
    """Öffnet und speichert hier, damit die gespeicherten Pfade auf diesen Ordner zeigen: Er spielt das Original des Kollegen.
    Erst die
    Unterbaugruppe, dann die Hauptbaugruppe, `aktiv` wählt die gespeicherte Konfiguration."""
    d = {}
    m, s = oeffne(app, ordner / "Muster.SLDASM")
    d["muster"] = {"oeffnen": s, "speichern": speichern(m)}
    alle_zu(app)
    asm, s = oeffne(app, ordner / HUBEINHEIT)
    if aktiv:
        schalte(asm, aktiv)
    d["haupt"] = {"oeffnen": s, "speichern": speichern(asm)}
    alle_zu(app)
    return d


def _menge(pfade) -> set[str]:
    return {os.path.normcase(os.path.normpath(p)) for p in pfade if p}


def aufloesung(app, ordner: Path, rel: str = HUBEINHEIT, optionen: int = OFFEN | VOLL) -> dict:
    """Vor dem Öffnen aufgelöst gegen wirklich geladen: Die erste Sperre ist nur so gut wie diese Gleichheit (Spec §8.1a).
    `ausserhalb`
    nennt, was nicht unter `ordner` liegt. Volumen der Grundplatte: Der Kennzeichenwert zeigt die Quelle unabhängig vom Pfad."""
    pfad = ordner / rel
    vor = aufgeloeste_referenzen(app, pfad)
    roh = app.GetDocumentDependencies2(str(pfad), True, True, False)
    asm, s = oeffne(app, pfad, optionen)
    aus: dict = {"oeffnen": s, "vorher": vor, "vorher_roh": list(roh or ())}
    if asm is None:
        return aus | {"offen": False}
    stand = [stand_der_komponente(k) for k in komponenten(asm)]
    platte = komp(asm, "Grundplatte-1")
    doc = platte.GetModelDoc2 if platte is not None else None
    geladen = [e["pfad"] for e in stand if isinstance(e["pfad"], str) and e["pfad"]]
    dokumente = [p for p in offene(app) if p and Path(p).name != pfad.name]
    aus |= {"komponenten": stand, "dokumente": dokumente, "grundplatte_volumen": volumen(doc) if doc is not None else None,
            "gleich": _menge(vor) == _menge(geladen) | _menge(dokumente),
            "nur_vorher": sorted(_menge(vor) - _menge(geladen) - _menge(dokumente)),
            "nur_geladen": sorted((_menge(geladen) | _menge(dokumente)) - _menge(vor)),
            "ausserhalb": [p for p in [*geladen, *dokumente] if not Path(p).resolve().is_relative_to(ordner.resolve())]}
    alle_zu(app)
    return aus


def fahrt(app, asm, ordner: Path | None, gelesen: dict, mech_aufnahme: dict | None = None) -> dict:
    """Die echte Fahrt wie `aufnehmen`: alle Grenzen der Aufnahme, ohne Speichern."""
    standard = lade_standard()
    grenzen = grenzen_der_aufnahme(gelesen)
    mech = mechanik_fuer(app, asm, grenzen, mech_aufnahme or gelesen, ordner)
    # Umgehung im Spike (Zeile b, live): `ForceRebuild3` trennt die Zeiger aus `MateEntity(i).Reference`, `mechanik_fuer` liest sie
    # aber nur einmal. Hier je Antrieb frisch aus der (dann unterdrückten) Grenze, das geht auch nach `ForceRebuild3`.
    mech.entitaet = lambda seite: _entitaeten(mate(asm, seite["grenze"]))[seite["index"]]
    return fahre_bestand(mech, gelesen, grenzen, standard["bewegung_schritte"], statische_paare(gelesen),
                         standard["speicher_grenze_mb"],
                         standard["toleranzen"]["anker_mm"], None)


def rels() -> dict:
    return {rel: {} for rel in HUB_DATEIEN if rel != HUBEINHEIT}


# ---------------------------------------------------------------------- Zeile c: Pfade


def zeile_c(app) -> None:
    lauf = Lauf(app, "c")
    basis = frisch("c")
    original = kopiere_stand(hubeinheit_ordner(rechner()), basis / "original")
    lauf["original"] = als_original(app, original)
    lauf["gespeicherte_pfade_original"] = list(app.GetDocumentDependencies2(str(original / HUBEINHEIT), True, False, False) or ())

    # P.c1, P.c3, T10.7, T10.11: Struktur teile/ bei vorhandenem Original, das Kennzeichen liegt nur in der Kopie
    kopie = kopiere_stand(original, basis / "lauf-1")
    lauf["kennzeichen"] = setze_dicke(app, kopie / "teile/Grundplatte.SLDPRT", 17)
    r = aufloesung(app, kopie)
    lauf.frage("P.c1", r, fall="teile/, Original vorhanden")
    lauf.frage("P.c3", {"gleich": r.get("gleich"), "nur_vorher": r.get("nur_vorher"), "nur_geladen": r.get("nur_geladen")},
               fall="teile/")
    lauf.frage("T10.7", r.get("oeffnen"), fall="Grundplatte geändert neben alter Baugruppe")
    lauf.frage("T10.11", {"vorher": r.get("vorher"), "ausserhalb": r.get("ausserhalb")})
    # 200×80×17: Das Kennzeichen zeigt die Kopie
    if r.get("ausserhalb") or abs((r.get("grundplatte_volumen") or 0.0) - 272000.0) > 0.1:
        lauf.halt(f"Struktur teile/ nicht aus der Kopie geladen: {r.get('ausserhalb')}, Volumen {r.get('grundplatte_volumen')}")
    if not r.get("gleich"):
        lauf.halt(f"Auflösung vor dem Öffnen anders als das Öffnen (teile/): {r.get('nur_vorher')} / {r.get('nur_geladen')}")

    # P.c2 Datei flach daneben, teile/ fehlt
    flach = kopiere_stand(original, basis / "flach", ohne=("teile/Schlitten.SLDPRT",))
    shutil.copy2(original / "teile/Schlitten.SLDPRT", flach / "Schlitten.SLDPRT")
    r = aufloesung(app, flach)
    lauf.frage("P.c2", r, fall="flach statt teile/")
    if not r.get("gleich"):
        lauf.halt(f"Auflösung vor dem Öffnen anders als das Öffnen (flach): {r.get('nur_vorher')} / {r.get('nur_geladen')}")

    # Beide da: Was hat Vorrang? `ordne_referenzen` nimmt die Datei neben der Baugruppe
    beide = kopiere_stand(original, basis / "beide")
    shutil.copy2(original / "teile/Schlitten.SLDPRT", beide / "Schlitten.SLDPRT")
    lauf.frage("P.c2", aufloesung(app, beide), fall="flach und teile/ zugleich")

    # P.c3, P.c6: Datei fehlt in der Kopie, das Original liegt am gespeicherten Pfad
    fehlt = kopiere_stand(original, basis / "fehlt", ohne=("teile/Schlitten.SLDPRT",))
    lauf.frage("P.c3", aufloesung(app, fehlt), fall="Datei fehlt, Original da")
    lauf.frage("P.c6", lambda: c_pfad_fund(app, fehlt), fall="oeffne_in")
    lauf.frage("P.c6", lambda: {"offen_danach": offene(app), "anzahl": primitiv(app.GetDocumentCount)}, fall="danach")
    alle_zu(app)

    # P.c4 Original im Speicher: eine Datei des Originals ist offen, wenn die Kopie aufgelöst und geöffnet wird
    speicher = kopiere_stand(original, basis / "speicher")
    m, s = oeffne(app, original / "teile/Schlitten.SLDPRT", sichtbar=False)
    lauf.frage("P.c4", lambda: {"original_offen": s, "vorher": aufgeloeste_referenzen(app, speicher / HUBEINHEIT)},
               fall="Auflösung")
    r = aufloesung(app, speicher)
    lauf.frage("P.c4", r, fall="Schlitten des Originals im Speicher")
    if r.get("ausserhalb") and not r.get("gleich"):
        lauf.halt(f"Original im Speicher gewinnt, die Auflösung sah es nicht: {r.get('ausserhalb')}")
    alle_zu(app)

    # Original weg: gespeicherter Pfad zeigt ins Leere, die Kopie soll sich selbst genügen
    weg = kopiere_stand(original, basis / "ohne_original")
    versteck = original.with_name("original_weg")
    original.rename(versteck)
    try:
        lauf.frage("P.c1", aufloesung(app, weg), fall="teile/, Original nicht da")
    finally:
        versteck.rename(original)

    c_unterdrueckt(app, lauf, basis)
    c_zurueck(app, lauf, basis, original)
    lauf.frage("T8.11", lambda: c_dateitypen(app, kopie))
    lauf.frage("T8.23", lambda: c_verdeckt(app, kopie))
    lauf.frage("T11.8", lambda: c_vorher(app, kopie))
    lauf.schliesse()


def c_pfad_fund(app, ordner: Path) -> dict:
    try:
        model = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=False, nur_lesen=True)
    except Exception as e:
        return {"code": getattr(e, "daten", {}).get("code"), "meldung": str(e), "wo": getattr(e, "daten", {}).get("wo")}
    sw.schliesse(app, model)
    return {"code": None, "meldung": "oeffne_in ließ durch"}


def c_unterdrueckt(app, lauf: Lauf, basis: Path) -> None:
    """T8.9, T8.10: Gespeichert in der Konfiguration mit unterdrückter Unterbaugruppe, die Pfade zeigen aufs Original."""
    original = kopiere_stand(hubeinheit_ordner(rechner()), basis / "original_b")
    lauf["original_b"] = als_original(app, original, KONFIG_OHNE)
    kopie = kopiere_stand(original, basis / "kopie_b")
    for optionen, fall in ((OFFEN, "ohne voll"), (OFFEN | VOLL, "voll")):
        asm, s = oeffne(app, kopie / HUBEINHEIT, optionen)
        z = {"oeffnen": s, "aktiv": asm.ConfigurationManager.ActiveConfiguration.Name, "vor": [stand_der_komponente(k)
                for k in komponenten(asm)],
             "offen": offene(app)}
        lauf.frage("T8.9", z, fall=fall)
        lauf.frage("T8.10", {"pfade": [e["pfad"] for e in z["vor"]]}, fall=fall)
        schalte(asm, "Standard")  # jetzt muss Muster-1 laden: aus der Kopie oder vom gespeicherten Pfad?
        asm.ForceRebuild3(False)
        lauf.frage("T8.9", {"nach_umschalten": [stand_der_komponente(k) for k in komponenten(asm)], "offen": offene(app)},
                   fall=f"{fall}, nach dem Umschalten")
        alle_zu(app)
    wert = lauf.frage("T8.9", lambda: c_pfad_fund(app, kopie), fall="oeffne_in mit Unterdrücktem")
    if isinstance(wert, dict) and wert.get("code"):
        lauf.halt(f"Pfadschutz sperrt eine Baugruppe mit unterdrückter Komponente: {wert['meldung']} (Task 8, Bedenken 1: §8.1a)")
    alle_zu(app)


def c_zurueck(app, lauf: Lauf, basis: Path, original: Path) -> None:
    """P.c5, P.c7: Eine geänderte Hauptbaugruppe trägt Lauf-Pfade. Zurück neben die Originale, mit und ohne Lauf-Ordner."""
    lauf1 = kopiere_stand(original, basis / "rueck_lauf")
    asm, s = oeffne(app, lauf1 / HUBEINHEIT)
    mate(asm, "Anschlag1 Lage").Parameter("D1").SetSystemValue3(mm(32), SW_WERT_ALLE, None)
    asm.ForceRebuild3(False)
    lauf["rueck_lauf"] = {"oeffnen": s, "speichern": speichern(asm), "pfade": [k.GetPathName for k in komponenten(asm)]}
    alle_zu(app)
    ziel = kopiere_stand(original, basis / "zurueck")
    shutil.copy2(lauf1 / HUBEINHEIT, ziel / HUBEINHEIT)
    lauf.frage("P.c5", aufloesung(app, ziel), fall="Lauf-Ordner noch da")
    flach = kopiere_stand(original, basis / "zurueck_flach", ohne=("teile/Schlitten.SLDPRT",))
    shutil.copy2(original / "teile/Schlitten.SLDPRT", flach / "Schlitten.SLDPRT")
    shutil.copy2(lauf1 / HUBEINHEIT, flach / HUBEINHEIT)
    lauf.frage("P.c7", aufloesung(app, flach), fall="Lauf-Ordner noch da")
    versteck = lauf1.with_name("rueck_lauf_weg")
    lauf1.rename(versteck)
    try:
        lauf.frage("P.c5", aufloesung(app, ziel), fall="Lauf-Ordner weg")
        lauf.frage("P.c7", aufloesung(app, flach), fall="Lauf-Ordner weg")
    finally:
        versteck.rename(lauf1)


def c_dateitypen(app, kopie: Path) -> dict:
    """Dateitypen in den Abhängigkeiten. Ein Teil mit Konstruktionstabelle aus S18 Zeile t, wenn es den Lauf gab, als Kopie."""
    aus = {"hubeinheit": sorted({Path(p).suffix.lower() for p in aufgeloeste_referenzen(app, kopie / HUBEINHEIT)}),
           "motor": list(app.GetDocumentDependencies2(str(kopie / "gm42-10.SLDPRT"), True, True, False) or ()),
           "version": [app.VersionHistory(p)[-1:] for p in aufgeloeste_referenzen(app, kopie / HUBEINHEIT)]}
    tabelle = rechner().arbeitsordner / "S18" / "t" / "k" / "Lagerdeckel.SLDPRT"
    if tabelle.is_file():
        ziel = kopie.parent / "tabelle" / tabelle.name
        ziel.parent.mkdir(exist_ok=True)
        shutil.copy2(tabelle, ziel)
        ziel.chmod(stat.S_IWRITE)
        aus["tabelle"] = list(app.GetDocumentDependencies2(str(ziel), True, True, False) or ())
    return aus


def c_verdeckt(app, kopie: Path) -> dict:
    asm = oeffne_in(app, kopie / HUBEINHEIT, kopie, sichtbar=False, nur_lesen=True)
    aus = {"offen_mit_baugruppe": offene(app), "anzahl": primitiv(app.GetDocumentCount)}
    sw.schliesse(app, asm)
    aus |= {"offen_danach": offene(app), "anzahl_danach": primitiv(app.GetDocumentCount),
            "offene_dokumente": sorted(offene_dokumente(app))}
    m = oeffne_in(app, kopie / "teile/Grundplatte.SLDPRT", kopie, sichtbar=False, nur_lesen=True)
    aus["teil_danach"] = {"offen": offene(app), "titel": m.GetTitle}
    sw.schliesse(app, m)
    aus["zuletzt"] = offene(app)
    return aus


def c_vorher(app, kopie: Path) -> dict:
    ziel = kopie / "vergleich" / "vorher_teile_Grundplatte.SLDPRT"
    ziel.parent.mkdir(exist_ok=True)
    shutil.copy2(kopie / "teile/Grundplatte.SLDPRT", ziel)
    aus = {"vorher": aufgeloeste_referenzen(app, ziel)}
    deckel = kopie / "vergleich" / "vorher_Lagerdeckel.SLDPRT"  # zwei Konfigurationen
    shutil.copy2(kopie / "Lagerdeckel.SLDPRT", deckel)
    aus["zwei_konfigurationen"] = aufgeloeste_referenzen(app, deckel)
    return aus


# ---------------------------------------------------------------------- Zeile b: Antrieb


def b_entitaeten(asm, name: str) -> dict:
    """Was `MateEntity(i).Reference` und `EntitiesToMate` sind und ob sie sich wählen lassen: Das braucht `treibe`."""
    f = mate(asm, name)
    m, aus = f.GetSpecificFeature2, {"typ": f.GetTypeName2, "seiten": []}

    def probe(objekt, ist_feature: bool) -> dict:
        sw.auswahl_leeren(asm)
        try:
            sw_baugruppe.waehle(asm, (objekt, ist_feature), False)
            sm = asm.SelectionManager
            k = versuch(lambda: sm.GetSelectedObjectsComponent4(1, -1))
            return {"gewaehlt": sm.GetSelectedObjectCount2(-1), "art": sm.GetSelectedObjectType3(1, -1),
                    "komponente": k.Name2 if hasattr(k, "Name2") else k}
        finally:
            sw.auswahl_leeren(asm)

    for i in range(int(primitiv(m.GetMateEntityCount))):
        s = m.MateEntity(i)
        ref, typ = s.Reference, primitiv(s.ReferenceType2)
        rk = s.ReferenceComponent
        aus["seiten"].append({"i": i, "referenz_typ": typ, "objekt": repr(type(ref)), "komponente": None
                              if rk is None else rk.Name2,
                              "als_entitaet": versuch(lambda: probe(ref, False)), "als_feature": versuch(lambda: probe(ref,
                True))})
    aus["entities_to_mate"] = versuch(lambda: [{"objekt": repr(type(e)), "wahl": versuch(lambda e=e: probe(e, False))}
                                               for e in (f.GetDefinition.EntitiesToMate or ())])
    return aus


def b_zeiger(app, asm, gelesen: dict, name: str) -> dict:
    """Handles der Grenze einmal gelesen, dann wie `SwMechanik`: unterdrücken, Antrieb, stellen, löschen, aktivieren."""
    f = mate(asm, name)
    h = _entitaeten(f)
    v = als_verknuepfung(name, gelesen["verknuepfungen"][name])
    schlitten = "Schlitten-1"
    aus: dict = {"lage_vorher": lage_mm(komp(asm, schlitten))}

    def noch_gueltig() -> list:
        ergebnis = []
        for objekt, ist_feature in h:
            sw.auswahl_leeren(asm)
            ergebnis.append(versuch(lambda objekt=objekt, ist_feature=ist_feature: sw_baugruppe.waehle(asm, (objekt, ist_feature),
                    False) or True))
        sw.auswahl_leeren(asm)
        return ergebnis

    aus["frisch"] = noch_gueltig()
    sw_baugruppe.unterdruecke(asm, f, True)
    aus["nach_unterdruecken"] = noch_gueltig()
    antrieb = aus["treibe"] = versuch(lambda: sw_baugruppe.treibe(asm, v, h[0], h[1], 10.0))
    if isinstance(antrieb, dict):
        sw_baugruppe.unterdruecke(asm, mate(asm, name), False)
        return aus
    aus["treibe"] = antrieb.Name
    aus["lage_10"] = lage_mm(komp(asm, schlitten))
    aus["stelle_20"] = sw_baugruppe.stelle(asm, antrieb, "abstand", 20.0)
    aus["lage_20"] = lage_mm(komp(asm, schlitten))
    aus["d1_grenze_gefahren"] = versuch(lambda: sw_baugruppe.grenzwert(mate(asm, name), "abstand"))
    aus["nach_neuaufbau"] = noch_gueltig()
    sw_baugruppe.stelle(asm, antrieb, "abstand", float(gelesen["verknuepfungen"][name]["wert"]))
    aus["lage_zurueck"] = lage_mm(komp(asm, schlitten))
    sw_baugruppe.loesche(asm, antrieb)
    aus["nach_loeschen"] = lage_mm(komp(asm, schlitten))
    sw_baugruppe.unterdruecke(asm, mate(asm, name), False)
    aus["nach_aktivieren"] = lage_mm(komp(asm, schlitten))
    aus["zum_schluss"] = noch_gueltig()
    return aus


def zeile_b(app) -> None:
    lauf = Lauf(app, "b")
    frisch("b")
    ordner = bestuecke("b/ro")
    vorher = shas(ordner)
    schreibschuetze(ordner)
    asm, s = oeffne(app, ordner / HUBEINHEIT, OFFEN | VOLL | NUR_LESEN, sichtbar=False)
    lauf["oeffnen"] = s | {"nur_lesen": asm.IsOpenedReadOnly}
    gelesen = lies_baugruppe(app, asm, rels())
    lauf["hub"] = gelesen["verknuepfungen"].get("Hub")
    for name in ("Hub", "Anschlag1 Lage", "Antrieb vorne"):  # Flächen, Ebene eines Teils, Ebene der Baugruppe
        lauf.frage("T8.6", lambda name=name: b_entitaeten(asm, name), fall=name)
        lauf.frage("P.b1", lambda name=name: b_entitaeten(asm, name), fall=name)
    lauf.frage("P.b6", lambda: {"partner": gelesen["verknuepfungen"]["Hub"]["partner"],
                                "entitaeten": [e["komponente"] for e in b_entitaeten(asm, "Hub")["seiten"]]})
    wert = lauf.frage("T8.22", lambda: b_zeiger(app, asm, gelesen, "Hub"), fall="nur lesend, unsichtbar")
    lauf.frage("P.b2", wert)
    lauf.frage("T8.7", wert, fall="Bemaßung wie angelegt")
    lauf.frage("T8.8", lambda: b_probeschritt(app, asm, gelesen))
    lauf.frage("P.b4", lambda: fahrt(app, asm, None, gelesen), fall="unsichtbar, nur lesend")
    t = time.monotonic()
    lauf.frage("T11.2", lambda: {"close": alle_zu(app), "s": round(time.monotonic() - t, 2), "offen": offene(app)},
               fall="unsichtbar")
    lauf.frage("P.b5", {"gleich": vorher == shas(ordner), "abweichend": sorted(k for k, v in shas(ordner).items()
            if vorher[k] != v)}, fall="unsichtbar")

    # T11.1 Fenster, Bilder der Fahrt, wie swki pruefen am Lauf
    asm, s = oeffne(app, ordner / HUBEINHEIT, OFFEN | VOLL | NUR_LESEN)
    gelesen = lies_baugruppe(app, asm, rels())
    bilder = frisch("b/bilder")
    wert = lauf.frage("T11.1", lambda: fahrt(app, asm, bilder, gelesen), fall="Fenster, nur lesend")
    lauf.frage("T11.1", {"bilder": sorted(p.name for p in bilder.glob("*.png")), "groesse": sum(p.stat().st_size
            for p in bilder.glob("*.png")),
                         "iso": versuch(lambda: iso_bild(app, asm, bilder / "iso_ro.png"))}, fall="Bilder")
    lauf.frage("P.b4", wert, fall="Fenster, nur lesend")
    alle_zu(app)
    lauf.frage("T11.2", {"gleich": vorher == shas(ordner)}, fall="Fenster")
    lauf.frage("P.b5", {"gleich": vorher == shas(ordner)}, fall="Fenster")

    b_flip(app, lauf)
    lauf.frage("T11.12", lambda: b_neuer_fehler(app))
    alle_zu(app)
    lauf.schliesse()


def b_probeschritt(app, asm, gelesen: dict) -> dict:
    from swki.baugruppe.bewegungslauf import StellungFehler
    from swki.bestand.bewegung_bestand import _probeschritt

    grenzen = grenzen_der_aufnahme(gelesen)
    mech = mechanik_fuer(app, asm, grenzen, gelesen, None)
    vorher, hinweise = lage_mm(komp(asm, "Schlitten-1")), []
    try:
        seite = _probeschritt(mech, "Hub", grenzen["Hub"], "Schlitten-1", "Grundplatte-1", hinweise)
    except StellungFehler as e:
        seite = f"StellungFehler: {e}"
    asm.ForceRebuild3(False)
    return {"seite": seite, "hinweise": hinweise, "vorher": vorher, "nachher": lage_mm(komp(asm, "Schlitten-1"))}


def b_flip(app, lauf: Lauf) -> None:
    """P.b3, T8.7: Dieselbe Grenze mit `Flip` wahr. `verknuepfe` setzt den Antrieb immer auf False: Liegt er dann anders?"""
    ordner = bestuecke("b/flip")
    asm, _ = oeffne(app, ordner / HUBEINHEIT)
    f = mate(asm, "Hub")
    a, b = _entitaeten(f)
    loesche_roh(asm, f)
    lauf["flip_anlegen"] = verknuepfe_roh(asm, "Hub", SW_ABSTAND, 0, a, b, 0.0, 25.0, 0.0, flip=True)
    asm.ForceRebuild3(False)
    lauf["flip_speichern"] = speichern(asm)
    alle_zu(app)
    schreibschuetze(ordner)
    asm, _ = oeffne(app, ordner / HUBEINHEIT, OFFEN | VOLL | NUR_LESEN, sichtbar=False)
    gelesen = lies_baugruppe(app, asm, rels())
    lauf.frage("P.b3", {"gelesen": gelesen["verknuepfungen"].get("Hub"), "definition": b_definition(mate(asm, "Hub"))},
               fall="gelesen")
    wert = lauf.frage("T8.7", lambda: b_zeiger(app, asm, gelesen, "Hub"), fall="umgekehrte Bemaßung")
    lauf.frage("P.b3", wert, fall="Antrieb von Hand")
    lauf.frage("P.b3", lambda: fahrt(app, asm, None, gelesen), fall="Fahrt")
    alle_zu(app)


def b_definition(f) -> dict:
    d = f.GetDefinition
    return {n: versuch(lambda n=n: getattr(d, n)) for n in ("Distance", "MinimumDistance", "MaximumDistance", "FlipDimension",
                                                            "IsAdvancedMate")}


def b_neuer_fehler(app) -> dict:
    """Eine neue Verknüpfung nur im Lauf widerspricht der Fahrt: Sie stoppt, die Aufnahme kennt sie nicht als alten Fehler."""
    ordner = bestuecke("b/konflikt")
    asm, _ = oeffne(app, ordner / HUBEINHEIT)
    gelesen = lies_baugruppe(app, asm, rels())
    a, b = _entitaeten(mate(asm, "Hub"))
    aus = {"anlegen": verknuepfe_roh(asm, "Konflikt", SW_ABSTAND, 0, a, b, 5.0)}
    asm.ForceRebuild3(False)
    aus["fehler_vor_der_fahrt"] = versuch(lambda: whats_wrong(asm))
    try:
        aus["fahrt"] = fahrt(app, asm, None, gelesen)
    except Exception as e:
        aus["fahrt"] = {"ausnahme": type(e).__name__, "meldung": str(e)}
    return aus


# ---------------------------------------------------------------------- Zeile a: Verknüpfungen


def a_verknuepfung(f, k: str) -> dict:
    """Roh, ohne die Annahmen von `lies_verknuepfungen`."""
    aus: dict = {"name": f.Name, "typname": f.GetTypeName2, "unterdrueckt_alt": versuch(lambda: bool(f.IsSuppressed)),
                 "unterdrueckt": versuch(lambda: unterdrueckt(f, k)), "fehler": versuch(lambda: sw_baugruppe.fehlercode(f))}
    m = versuch(lambda: f.GetSpecificFeature2)
    if isinstance(m, dict) or m is None:
        return aus | {"mate": m}
    aus |= {"typ": versuch(lambda: int(m.Type)), "ausrichtung": versuch(lambda: int(m.Alignment)),
            "entitaeten": versuch(lambda: [a_partner(m.MateEntity(i)) for i in range(int(primitiv(m.GetMateEntityCount)))]),
            "variation": versuch(lambda: [m.MinimumVariation, m.MaximumVariation]),
            "d1": versuch(lambda: None if f.Parameter("D1") is None else f.Parameter("D1").SystemValue),
            "masse": versuch(lambda: a_masse(f))}
    d = versuch(lambda: f.GetDefinition)
    if not isinstance(d, dict) and d is not None:
        aus["definition"] = {n: versuch(lambda n=n: getattr(d, n))
                             for n in ("Distance", "MinimumDistance", "MaximumDistance", "Angle", "MinimumAngle", "MaximumAngle",
                                       "FlipDimension", "IsAdvancedMate")}
    return aus


def a_partner(s) -> dict:
    k = s.ReferenceComponent
    return {"komponente_none": k is None, "name": None if k is None else repr(k.Name2),
            "referenz_typ": versuch(lambda: primitiv(s.ReferenceType2))}


def a_masse(f) -> list:
    aus, dd = [], f.GetFirstDisplayDimension
    while dd is not None:
        aus.append(dd.GetDimension2(0).FullName)
        dd = f.GetNextDisplayDimension(dd)
    return aus


def zeile_a(app) -> None:
    lauf = Lauf(app, "a")
    frisch("a")
    ordner = bestuecke("a/k")
    asm, s = oeffne(app, ordner / HUBEINHEIT)
    lauf["oeffnen"] = s
    je_konfiguration: dict = {}

    def lies(k: str) -> None:
        je_konfiguration[k] = {f.Name: a_verknuepfung(f, k) for f in sw_baugruppe.verknuepfungen(asm)}

    aktiv = asm.ConfigurationManager.ActiveConfiguration.Name
    konfigurationen = [aktiv] + [k for k in asm.GetConfigurationNames if k != aktiv]
    for k in konfigurationen:
        schalte(asm, k)
        asm.ForceRebuild3(False)
        lies(k)
    schalte(asm, aktiv)
    lauf["roh"] = je_konfiguration
    standard = je_konfiguration[aktiv]
    lauf.frage("T8.1", {"Hub": standard["Hub"], "Abstand": standard["Schlitten Seite"]}, fall="Grenze gegen Abstand")
    lauf.frage("P.a1", {"Hub": standard["Hub"].get("definition"), "variation": standard["Hub"].get("variation"),
                        "typname": standard["Hub"]["typname"]})
    lauf.frage("P.a2", {"d1_roh": standard["Schlitten Seite"].get("d1"), "soll_mm": 15, "lesen": lies_verknuepfungen(asm,
            [aktiv])["Schlitten Seite"]})
    lauf.frage("T8.2", {n: {"d1": e.get("d1"), "masse": e.get("masse"), "variation": e.get("variation")} for n,
                        e in standard.items()})
    lauf.frage("T8.4", {n: standard[n].get("entitaeten") for n in ("Antrieb vorne", "Antrieb rechts", "Antrieb Abstand")},
               fall="Hauptbaugruppe")
    lauf.frage("T8.4", lambda: a_unterbaugruppe(asm), fall="Verknüpfung in der Unterbaugruppe")
    lauf.frage("P.a3", {"lesen": lies_verknuepfungen(asm, [aktiv])["Antrieb vorne"]["partner"],
                        "roh": standard["Antrieb vorne"].get("entitaeten")})
    lauf.frage("T8.5", je_konfiguration[KONFIG_OHNE].get("Antrieb Abstand"))
    lauf.frage("T8.26", lambda: {n: dict(zip(konfigurationen, f.IsSuppressed2(SW_WERT_BENANNT, namen(konfigurationen))))
                                 for n, f in ((x.Name, x) for x in sw_baugruppe.verknuepfungen(asm))})
    lauf.frage("P.a5", {n: e.get("fehler") for n, e in standard.items()})
    lauf.frage("P.a7", lambda: {k.Name2: {"loesen": versuch(lambda k=k: int(primitiv(k.Solving))),
                                          "muster": versuch(lambda k=k: bool(primitiv(k.IsPatternInstance)))} for k in komponenten(asm)})
    alle_zu(app)
    a_varianten(app, lauf)
    lauf.frage("T8.3", lambda: a_andere_typen(app))
    alle_zu(app)
    lauf.schliesse()


def a_unterbaugruppe(asm) -> dict:
    doc = komp(asm, "Muster-1").GetModelDoc2
    return {f.Name: [a_partner(f.GetSpecificFeature2.MateEntity(i))
                     for i in range(int(primitiv(f.GetSpecificFeature2.GetMateEntityCount)))]
            for f in sw_baugruppe.verknuepfungen(doc)}


def a_varianten(app, lauf: Lauf) -> None:
    """T8.1 min = max, P.a4 Vorzeichen bei Flip: nur im Speicher, nichts gespeichert."""
    ordner = bestuecke("a/varianten")
    asm, _ = oeffne(app, ordner / HUBEINHEIT)
    f = mate(asm, "Hub")
    a, b = _entitaeten(f)
    loesche_roh(asm, f)
    lauf.frage("T8.1", lambda: {"anlegen": verknuepfe_roh(asm, "Hub gleich", SW_ABSTAND, 0, a, b, 10.0, 10.0, 10.0),
                                "neuaufbau": asm.ForceRebuild3(False),
                                "roh": a_verknuepfung(mate(asm, "Hub gleich"), "Standard"),
                                "lesen": lies_verknuepfungen(asm, ["Standard"]).get("Hub gleich")}, fall="min gleich max")
    loesche_roh(asm, mate(asm, "Hub gleich"))
    lauf.frage("P.a4", lambda: {"anlegen": verknuepfe_roh(asm, "Hub flip", SW_ABSTAND, 0, a, b, 10.0, flip=True),
                                "neuaufbau": asm.ForceRebuild3(False),
                                "roh": a_verknuepfung(mate(asm, "Hub flip"), "Standard"), "lage": lage_mm(komp(asm,
            "Schlitten-1"))},
            fall="Abstand 10 "
            "umgekehrt")
    alle_zu(app)


def a_andere_typen(app) -> dict:
    """Breite und Symmetrie über `CreateMate`: Schlitten zwischen den Anschlägen, die Seite wird dafür frei. Nur im Speicher."""
    ordner = bestuecke("a/typen")
    asm, _ = oeffne(app, ordner / HUBEINHEIT)
    seite = mate(asm, "Schlitten Seite")
    a, b = _entitaeten(seite)
    loesche_roh(asm, seite)
    aus: dict = {}

    def probe(typ: int, name: str, fuellen) -> dict:
        daten = asm.CreateMateData(typ)
        fuellen(daten)
        neu = asm.CreateMate(daten)
        sw.auswahl_leeren(asm)
        f = sw_baugruppe.verknuepfungen(asm)[-1]
        z = {"angelegt": neu is not None, "name_vorher": f.Name}
        f.Name = name
        z["roh"] = a_verknuepfung(f, "Standard")
        loesche_roh(asm, f)
        return z

    platte, schlitten = komp(asm, "Grundplatte-1"), komp(asm, "Schlitten-1")
    ebene = platte.FeatureByName(ebenen_namen(platte)[1])

    def breite(d) -> None:
        d.WidthSelection = dispatch_array([b[0], flaeche_gegenueber(asm, platte, "+y")])
        d.TabSelection = dispatch_array([a[0], flaeche_gegenueber(asm, schlitten, "+y")])

    def symmetrie(d) -> None:
        d.SymmetryPlane = ebene
        d.EntitiesToMate = dispatch_array([a[0], flaeche_gegenueber(asm, schlitten, "+y")])

    aus["breite"] = versuch(lambda: probe(SW_BREITE, "Probe Breite", breite))
    aus["symmetrie"] = versuch(lambda: probe(SW_SYMMETRIE, "Probe Symmetrie", symmetrie))
    return aus


def ebenen_namen(k) -> list[str]:
    return [e.Name for e in sw.standardebenen(k.GetModelDoc2)]


def flaeche_gegenueber(asm, k, richtung: str):
    """Fläche der Komponente im Baugruppenkontext mit der Normalen `+y`: im Teil gesucht, wie `sw_baugruppe.in_baugruppe`."""
    ziel = {"+y": (0, 1, 0)}[richtung]
    for f in k.GetModelDoc2.GetBodies2(0, False)[0].GetFaces():
        n = f.Normal
        if all(abs(p - q) < 1e-6 for p, q in zip(n, ziel)):
            return k.GetCorrespondingEntity(f)
    raise RuntimeError(f"{k.Name2}: keine Fläche {richtung}")


# ---------------------------------------------------------------------- Zeile f: Baum


def f_baum(asm) -> list:
    aus, f = [], asm.FirstFeature
    while f is not None:
        unter, s = [], f.GetFirstSubFeature
        while s is not None:
            unter.append({"name": s.Name, "typ": s.GetTypeName2})
            s = s.GetNextSubFeature
        aus.append({"name": f.Name, "typ": f.GetTypeName2, "unter": unter[:20], "unter_anzahl": len(unter)})
        f = f.GetNextFeature
    return aus


def zeile_f(app) -> None:
    lauf = Lauf(app, "f")
    frisch("f")
    with arbeit(app, "f/k") as (asm, ordner):
        baum = f_baum(asm)
        lauf.frage("T8.17", {"baum": baum, "ohne_glieder": versuch(lambda: [f.Name for f in baum_ohne_glieder(asm)])})
        je = {}
        for k in ("Standard", KONFIG_OHNE):
            schalte(asm, k)
            asm.ForceRebuild3(False)
            je[k] = [stand_der_komponente(x) for x in komponenten(asm)]
        schalte(asm, "Standard")
        lauf.frage("T8.14", je)
        lauf.frage("P.f3", {"lage": {e["name"]: e["lage"] for e in je["Standard"]}, "muster": lage_mm(komp(asm, "Muster-1"))})
        lauf.frage("T8.16", {x.Name2: versuch(lambda x=x: bool(x.IsFixed)) for x in komponenten(asm)})
        lauf.frage("T8.19", lambda: {"roh": f_externe(asm), "datei_referenzen": datei_referenzen(asm)})
        lauf.frage("P.f4", lambda: f_externe(asm))
        lauf.frage("T11.4", lambda: datei_referenzen(asm))
        lauf.frage("T8.24", lambda: f_gegenprobe(asm), fall="ohne Ordner")
        lauf.frage("T8.15", lambda: f_namen(asm), fall="Kollision und Partner")
        lauf.frage("P.f1", lambda: f_typen(app, asm, ordner), fall="Komponente, Verknüpfung, Muster, virtuell")
        lauf.frage("T8.18", lambda: f_ordner(asm), fall="Ordner mit Verknüpfungen")
        lauf.frage("T8.25", {"baum": f_baum(asm)[:12], "verknuepfungen": [f.Name for f in sw_baugruppe.verknuepfungen(asm)]})
        lauf.frage("T8.24", lambda: f_gegenprobe(asm), fall="mit Ordner")
        lauf.frage("T11.5", lambda: f_reihenfolge(app, asm, ordner))
    # Jede Probe beginnt leer: Eine gescheiterte ließe ihre Hubeinheit offen, die nächste bekäme „gleicher Titel“ (Zeile f, live)
    alle_zu(app)
    lauf.frage("P.f2", lambda: f_virtuell(app))
    alle_zu(app)
    lauf.frage("T8.20", lambda: f_schreibgeschuetzt(app))
    alle_zu(app)
    lauf.frage("T11.13", lambda: f_unterbaugruppe(app))
    alle_zu(app)
    lauf.frage("P.f8", lambda: f_abdeckung(app))
    alle_zu(app)
    lauf.schliesse()


def f_externe(asm) -> dict:
    a = [byref_variant() for _ in range(7)]
    co, cn = byref_long(), byref_str()
    asm.Extension.ListExternalFileReferences(*a, co, cn)
    return {"modell": a[0].value, "komponente": a[1].value, "feature": a[2].value, "typ": a[3].value, "status": a[4].value,
            "entity": a[5].value}


def f_gegenprobe(asm) -> dict:
    alle = asm.FeatureManager.GetFeatures(False) or ()
    typen = sorted({f.GetTypeName2 for f in alle})
    return {"typen": typen, "mate_typen": [t for t in typen if t.startswith("Mate")], "mate_namen": sorted(f.Name for f in alle
            if f.GetTypeName2.startswith("Mate")),
            "warnung": gegenprobe_verknuepfungen(asm, {f.Name for f in sw_baugruppe.verknuepfungen(asm)})}


def f_namen(asm) -> dict:
    """Anschläge ineinander: `Lage` von Anschlag 1 auf 60, in Anschlag 2 hinein (10×20×30 = 6000 mm³). Nur im Speicher."""
    lage = mate(asm, "Anschlag1 Lage")
    alt = lage.Parameter("D1").SystemValue
    lage.Parameter("D1").SetSystemValue3(mm(60), SW_WERT_ALLE, None)
    asm.ForceRebuild3(False)
    kollisionen = lies_kollisionen(asm)
    lage.Parameter("D1").SetSystemValue3(alt, SW_WERT_ALLE, None)
    asm.ForceRebuild3(False)
    m = mate(asm, "Antrieb Abstand").GetSpecificFeature2
    return {"kollisionen": kollisionen, "partner": [m.MateEntity(i).ReferenceComponent.Name2
                                                    for i in range(int(primitiv(m.GetMateEntityCount)))],
            "komponenten": [k.Name2 for k in komponenten(asm)]}


def f_typen(app, asm, ordner: Path) -> dict:
    aus: dict = {}
    baum = {f.Name: f.GetTypeName2 for f in asm.FeatureManager.GetFeatures(False) or ()}
    aus["komponente"], aus["verknuepfung"] = baum.get("Grundplatte-1"), baum.get("Hub")
    aus["muster"] = versuch(lambda: f_komponentenmuster(asm))
    aus["virtuell"] = versuch(lambda: f_neues_virtuelles(asm))
    return aus


def f_komponentenmuster(asm) -> dict:
    """Beispiel der API-Hilfe: Richtung Marke 2, Komponente Marke 1. Eine Kante der Grundplatte gibt die Richtung."""
    sm = asm.SelectionManager
    sw.auswahl_leeren(asm)
    asm.Extension.SelectByID2("", "EDGE", mm(0), mm(40), mm(15), False, 2, callout_leer(), 0)
    daten = sm.CreateSelectData
    daten.Mark = 1
    komp(asm, "Anschlag-2").Select4(True, daten, False)
    fd = asm.FeatureManager.CreateDefinition(SW_LOKALES_MUSTER)
    fd.D1Spacing = mm(15)
    fd.D1TotalInstances = 2
    fd.D1ReverseDirection = False
    fd.D2TotalInstances = 1
    f = asm.FeatureManager.CreateFeature(fd)
    sw.auswahl_leeren(asm)
    asm.ForceRebuild3(False)
    return {"feature": None if f is None else {"name": f.Name, "typ": f.GetTypeName2},
            "komponenten": [{"name": k.Name2, "muster": versuch(lambda k=k: bool(primitiv(k.IsPatternInstance))),
                             "pfad": k.GetPathName} for k in komponenten(asm)]}


def f_neues_virtuelles(asm) -> dict:
    # Umgehung (Zeile f, live): `None` und `byref_variant` geben „Typenkonflikt“; Ebene vorne der Baugruppe und ein Dispatch-Byref
    neu = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_DISPATCH, None)
    vorher = {x.Name2 for x in komponenten(asm)}
    status = asm.InsertNewVirtualPart(sw.standardebenen(asm)[0].GetSpecificFeature2, neu)  # IRefPlane wie im Beispiel der Hilfe
    k = neu.value or next((x for x in komponenten(asm) if x.Name2 not in vorher), None)  # das Byref bleibt unter late binding leer
    if k is None:
        return {"status": status, "neu": None, "namen": [x.Name2 for x in komponenten(asm)]}
    return {"status": status, "name": k.Name2, "pfad": k.GetPathName, "virtuell": bool(primitiv(k.IsVirtual)),
            "typ": next((f.GetTypeName2 for f in asm.FeatureManager.GetFeatures(False) or () if f.Name == k.Name2), None),
            "namen": [x.Name2 for x in komponenten(asm)]}


def f_ordner(asm) -> dict:
    sw.auswahl_leeren(asm)
    for i, n in enumerate(("Anschlag2 Auflage", "Anschlag2 Mitte", "Anschlag2 Lage")):
        mate(asm, n).Select2(i > 0, 0)
    ordner = asm.FeatureManager.InsertFeatureTreeFolder2(SW_ORDNER_MIT_INHALT)
    sw.auswahl_leeren(asm)
    asm.ForceRebuild3(False)
    return {"ordner": None if ordner is None else {"name": ordner.Name, "typ": ordner.GetTypeName2}, "baum": [e
            for e in f_baum(asm) if e["typ"] == "MateGroup"],
            "verknuepfungen": [f.Name for f in sw_baugruppe.verknuepfungen(asm)]}


def f_reihenfolge(app, asm, ordner: Path) -> dict:
    """Reihenfolge der übrigen Features nach einer neuen Komponente und einer neuen Verknüpfung."""
    vorher = lies_baugruppe(app, asm, rels(), kollision=False)
    k = asm.AddComponent5(str(ordner / "teile/Anschlag.SLDPRT"), 0, "", False, "", 0.0, mm(-100), mm(50))
    a, b = _entitaeten(mate(asm, "Anschlag1 Mitte"))
    z = {"neu": k.Name2, "mate": verknuepfe_roh(asm, "Probe neu", 0, 2, (k.FeatureByName(ebenen_namen(k)[1]), True), b)}
    asm.ForceRebuild3(False)
    nachher = lies_baugruppe(app, asm, rels(), kollision=False)
    return z | {"reihenfolge_gleich": vorher["reihenfolge"] == nachher["reihenfolge"], "vorher": vorher["reihenfolge"],
                "nachher": nachher["reihenfolge"],
                "masse_gleich": vorher["masse"] == nachher["masse"], "skizzen": [vorher["skizzen"], nachher["skizzen"]],
                "externe": [vorher["externe_referenzen"], nachher["externe_referenzen"]], "neuaufbau": [vorher["neuaufbau"],
            nachher["neuaufbau"]]}


def f_virtuell(app) -> dict:
    """Ein virtuelles Teil gespeichert: Woran erkennt man es vor dem Öffnen?"""
    ordner = bestuecke("f/virtuell")
    asm, _ = oeffne(app, ordner / HUBEINHEIT)
    z = {"neu": f_neues_virtuelles(asm), "speichern": speichern(asm)}
    alle_zu(app)
    z["abhaengigkeiten"] = list(app.GetDocumentDependencies2(str(ordner / HUBEINHEIT), True, True, False) or ())
    z["aufgeloest"] = aufgeloeste_referenzen(app, ordner / HUBEINHEIT)
    z["oeffne_in"] = c_pfad_fund(app, ordner)
    return z


def f_schreibgeschuetzt(app) -> dict:
    ordner = bestuecke("f/ro")
    schreibschuetze(ordner)
    asm, _ = oeffne(app, ordner / HUBEINHEIT, OFFEN | VOLL | NUR_LESEN, sichtbar=False)
    a, b = _entitaeten(mate(asm, "Hub"))
    z = {"anlegen": verknuepfe_roh(asm, "Probe", SW_ABSTAND, 0, a, b, 5.0)}
    f = next((x for x in sw_baugruppe.verknuepfungen(asm) if x.Name == "Probe"), None)
    z["loeschen"] = versuch(lambda: sw_baugruppe.loesche(asm, f) or "gelöscht") if f is not None else "nicht angelegt"
    z["uebrig"] = [x.Name for x in sw_baugruppe.verknuepfungen(asm) if x.Name == "Probe"]
    alle_zu(app)
    return z


def f_unterbaugruppe(app) -> dict:
    from swki.bestand.aufnahme_baugruppe import lies_baugruppe_einzeln

    ordner = bestuecke("f/unter")
    m, _ = oeffne(app, ordner / "Muster.SLDASM", OFFEN | VOLL | NUR_LESEN, sichtbar=False)
    vorher = lies_baugruppe_einzeln(app, m)["warnungen"]
    alle_zu(app)
    aendern, _ = oeffne(app, ordner / "Lagerdeckel.SLDPRT")
    aendern.Parameter(DICKE).SetSystemValue3(mm(21), SW_WERT_ALLE, None)
    aendern.EditRebuild3
    speichern(aendern)
    alle_zu(app)
    m, _ = oeffne(app, ordner / "Muster.SLDASM", OFFEN | VOLL | NUR_LESEN, sichtbar=False)
    nachher = lies_baugruppe_einzeln(app, m)["warnungen"]
    alle_zu(app)
    return {"vorher": vorher, "nachher": nachher}


def f_abdeckung(app) -> dict:
    ordner = bestuecke("f/abdeckung")
    asm, _ = oeffne(app, ordner / HUBEINHEIT)
    z = {"bestand": abdeckung(lies_baugruppe(app, asm, rels(), kollision=False))}
    loesche_roh(asm, mate(asm, "Schlitten Seite"))  # Schlitten hat jetzt zwei freie Richtungen und eine Grenze
    asm.ForceRebuild3(False)
    gelesen = lies_baugruppe(app, asm, rels(), kollision=False)
    z["ohne_seite"] = abdeckung(gelesen)
    z["status"] = gelesen["komponenten"]["Schlitten-1"]["status"]
    alle_zu(app)
    return z


# ---------------------------------------------------------------------- Zeile d: Unsichtbar


def d_kollisionsstand(app) -> Path:
    """Anschlag 1 steckt in Anschlag 2 (10×20×30 = 6000 mm³), gespeichert: Eine Kollision, die sich nur lesen lässt."""
    ordner = bestuecke("d/kollision")
    asm, _ = oeffne(app, ordner / HUBEINHEIT)
    mate(asm, "Anschlag1 Lage").Parameter("D1").SetSystemValue3(mm(60), SW_WERT_ALLE, None)
    asm.ForceRebuild3(False)
    speichern(asm)
    alle_zu(app)
    schreibschuetze(ordner)
    return ordner


def d_kollision(asm) -> dict:
    idm = asm.InterferenceDetectionManager
    idm.TreatCoincidenceAsInterference = False
    t = time.monotonic()
    anzahl = int(primitiv(idm.GetInterferenceCount))
    t1 = time.monotonic()
    liste = list(idm.GetInterferences or ())
    t2 = time.monotonic()
    zweite = int(primitiv(idm.GetInterferenceCount))
    gelesen = [{"paar": sorted(k.Name2 for k in (i.Components or ())), "volumen": round(i.Volume * 1e9, 3)} for i in liste]
    t3 = time.monotonic()
    sw_baugruppe.rufe(idm, "Done")
    nach_done = versuch(lambda: [round(i.Volume * 1e9, 3) for i in liste])
    return {"anzahl": anzahl, "laenge": len(liste), "zweite_anzahl": zweite, "gelesen": gelesen, "zaehlen_s": round(t1 - t, 3),
            "liste_s": round(t2 - t1, 3),
            "lesen_s": round(t3 - t2, 3), "nach_done": nach_done}


def d_vergleich(app, lauf: Lauf, ordner: Path) -> None:
    """P.d1, P.d2, T8.12, T8.13, T11.10, T11.11: gleicher Stand sichtbar und unsichtbar, je frisch geöffnet."""
    for art, sichtbar in (("sichtbar", True), ("unsichtbar", False)):
        with Spitzenmessung(lauf.pid) as spitze:
            asm, s = oeffne(app, ordner / HUBEINHEIT, OFFEN | VOLL | NUR_LESEN, sichtbar=sichtbar)
            z: dict = {"oeffnen": s, "nur_lesen": asm.IsOpenedReadOnly}
            t = time.monotonic()
            gelesen = lies_baugruppe(app, asm, rels(), kollision=False)
            z["lesen_s"] = round(time.monotonic() - t, 2)
            t = time.monotonic()
            with sw.schnell(app, asm):
                lies_baugruppe(app, asm, rels(), kollision=False)
            z["lesen_schnell_s"] = round(time.monotonic() - t, 2)
            z["kollision"] = versuch(lambda: d_kollision(asm))
            z["kollision_swki"] = versuch(lambda: lies_kollisionen(asm))
            z["lagen"] = {n: {"t": (e["transform"].get(gelesen["aktiv"]) or [None] * 12)[9:12], "status": e["status"]} for n,
                          e in gelesen["komponenten"].items()}
            alle_zu(app)
        z["speicher"] = spitze.als_dict()
        lauf.frage("P.d1", z, fall=art)
        lauf.frage("P.d2", {"oeffnen_s": s["s"], "lesen_s": z["lesen_s"], "speicher": z["speicher"]}, fall=art)
        lauf.frage("T8.12", z["kollision"], fall=art)
        lauf.frage("T8.13", (z["kollision"] or {}).get("nach_done") if isinstance(z["kollision"], dict) else z["kollision"],
                   fall=art)
        lauf.frage("T11.10", z["speicher"], fall=art)
        lauf.frage("T11.11", {"lesen_s": z["lesen_s"], "schnell_s": z["lesen_schnell_s"]}, fall=art)


def d_rebuild(app, ordner: Path) -> dict:
    """Grundplatte 15 auf 18 von außen, die Baugruppe bleibt alt: Der Schlitten muss nach dem Neuaufbau 3 mm höher stehen."""
    setze_dicke(app, ordner / "teile/Grundplatte.SLDPRT", 18)
    alle_zu(app)
    asm, s = oeffne(app, ordner / HUBEINHEIT, OFFEN | VOLL | NUR_LESEN, sichtbar=False)
    aus: dict = {"oeffnen": s, "nur_lesen": asm.IsOpenedReadOnly, "vor_neuaufbau": lage_mm(komp(asm, "Schlitten-1"))}
    for k in asm.GetConfigurationNames:
        schalte(asm, k)
        aus[k] = {"edit": asm.EditRebuild3, "nach_edit": lage_mm(komp(asm, "Schlitten-1")), "force": asm.ForceRebuild3(False),
                  "nach_force": lage_mm(komp(asm, "Schlitten-1")), "status": versuch(lambda: primitiv(komp(asm,
                "Schlitten-1").GetConstrainedStatus))}
    alle_zu(app)
    return aus


def d_zweimal(app, ordner: Path) -> dict:
    asm = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=False, nur_lesen=True)
    aus = {"unsichtbar_offen": offene(app)}
    sw.schliesse(app, asm)
    aus["zu"] = offene(app)
    vorher = offene_dokumente(app)
    asm = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=True, nur_lesen=True)
    aus |= {"fenster_offen": offene(app), "pfade": pruefe_geladen(app, asm, ordner, vorher)}
    alle_zu(app)
    return aus


def d_teil_zuerst(app, ordner: Path) -> dict:
    m = oeffne_in(app, ordner / "teile/Grundplatte.SLDPRT", ordner, sichtbar=False, nur_lesen=True)
    sw.schliesse(app, m)
    aus = {"nach_closedoc": offene(app)}
    ziel = ordner / "vergleich" / "vorher_teile_Schlitten.SLDPRT"
    ziel.parent.mkdir(exist_ok=True)
    shutil.copy2(ordner / "teile/Schlitten.SLDPRT", ziel)
    ziel.chmod(stat.S_IWRITE)
    asm = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=False, nur_lesen=True)
    aus["geladen"] = [k.GetPathName for k in komponenten(asm)]
    aus["vorher_geladen"] = [p for p in offene(app) if "vorher_" in p]
    alle_zu(app)
    return aus


def d_bilder(app, ordner: Path) -> dict:
    """Gleiche Datei, zwei Ordner wie Bestand und Lauf: Bilder gleich groß und byteweise gleich, gleiche aktive Konfiguration?"""
    zweiter = kopiere_stand(hubeinheit_ordner(rechner()), ordner.with_name("bilder_lauf"))
    aus = {}
    for name, o in (("bestand", ordner), ("lauf", zweiter)):
        asm, _ = oeffne(app, o / HUBEINHEIT, OFFEN | VOLL | NUR_LESEN)
        aus[name] = {"aktiv": asm.ConfigurationManager.ActiveConfiguration.Name,
                     "bilder": {k: Path(p).stat().st_size for k, p in screenshots(app, asm, o / "bilder").items()}}
        alle_zu(app)
    aus["gleich"] = {p.name: p.read_bytes() == (zweiter / "bilder" / p.name).read_bytes()
                     for p in (ordner / "bilder").glob("*.png")}
    return aus


def d_messe(app, ordner: Path) -> dict:
    m = oeffne_in(app, ordner / "teile/Anschlag.SLDPRT", ordner, sichtbar=False, nur_lesen=True)
    ctx = kontext_aus_datei(app, m, {"name": "Anschlag", "features": [], "parameter": {}, "pruefung": {}}, ordner / "spec.yaml",
                            0.01, {"knoten": []})
    w = messe(ctx)
    aus = {"volumen": getattr(w, "volumen", None), "felder": sorted(vars(w))[:20]}
    sw.schliesse(app, m)
    return aus


def d_bild_mit_auswahl(app, ordner: Path) -> dict:
    asm, _ = oeffne(app, ordner / HUBEINHEIT, OFFEN | VOLL | NUR_LESEN)
    ohne, mit = ordner / "iso_ohne.png", ordner / "iso_mit.png"
    iso_bild(app, asm, ohne)
    zeige_komponente(app, asm, "Schlitten-1", mit)
    alle_zu(app)
    return {"ohne": ohne.stat().st_size, "mit": mit.stat().st_size, "unterschiedlich": ohne.read_bytes() != mit.read_bytes(),
            "bild": str(mit)}


def zeile_d(app) -> None:
    lauf = Lauf(app, "d")
    frisch("d")
    d_vergleich(app, lauf, d_kollisionsstand(app))
    wert = lauf.frage("T11.3", lambda: d_rebuild(app, bestuecke("d/rebuild")))
    lauf.frage("T11.K1", wert)
    ordner = bestuecke("d/k")
    lauf.frage("T11.6", lambda: d_zweimal(app, ordner))
    lauf.frage("T11.7", lambda: d_teil_zuerst(app, ordner))
    lauf.frage("T11.9", lambda: d_bilder(app, ordner))
    lauf.frage("T11.K2", "nicht messbar: im Explorer von Hand prüfen (ausgabe/ offen, swki bestand ausgabe zweimal)")
    lauf.frage("T11.K3", lambda: d_messe(app, ordner))
    lauf.frage("T8.21", lambda: d_bild_mit_auswahl(app, ordner))
    alle_zu(app)
    lauf.schliesse()


# ---------------------------------------------------------------------- Zeile e: Schreiben


def e_kontext(app, asm, ordner: Path, punkte_: list | None = None) -> punkte_baugruppe.BauKontext:
    aufnahme = lies_baugruppe(app, asm, rels(), kollision=False) | {"datei": {"name": HUBEINHEIT}, "dateien": rels()}
    return punkte_baugruppe.BauKontext(app, asm, {"punkte": punkte_ or [], "parameter": {}}, ordner / "spec.yaml", ordner,
                                       aufnahme, lade_standard(),
                                       protokoll=Protokoll("S19", "spec.yaml", 1, rechner().sw_jahr))


def e_neue_datei(app, b, pfad: Path, hoehe: float = 40) -> dict:
    """Ein neues Teil neben der Baugruppe, geöffnet wie `hole_neue_dateien`; liefert die Quelle für einen Punkt."""
    baue_block(app, rechner(), pfad, (-10, -10, 10, 10), hoehe, pfad.stem)
    model = oeffne_in(app, pfad, b.ordner, sichtbar=False, nur_lesen=False)
    b.offen.append(model)
    ctx = punkte.kontext(app, model, {"punkte": [], "parameter": {}}, b.spec_pfad, 0.01)
    quelle = {"teil": f"{pfad.stem}.yaml"}
    b.quellen[quelle_schluessel(quelle)] = punkte_baugruppe.NeueDatei(pfad, "teil", ctx)
    b.kontexte[pfad.name.casefold()] = ctx
    return quelle


def e_lagen(asm) -> dict:
    return {k.Name2: lage_mm(k) for k in komponenten(asm)}


def e_einfuegen(app, lauf: Lauf) -> None:
    with arbeit(app, "e/einfuegen") as (asm, ordner):
        k = asm.AddComponent5(str(ordner / "Lagerdeckel.SLDPRT"), 0, "", True, "Variante B", 0.0, mm(-150), mm(10))
        n = k.Name2
        lauf.frage("T9.1", {"angelegt": k is not None, "name": n, "referenziert": k.ReferencedConfiguration,
                            "pfad": k.GetPathName})
        lauf.frage("P.e1", {"name": n, "pfad": k.GetPathName})

        def stand() -> dict:
            aus = {}
            for z in ("Standard", KONFIG_OHNE):
                schalte(asm, z)
                asm.ForceRebuild3(False)
                x = komp(asm, n)
                aus[z] = None if x is None else {"zustand": primitiv(x.GetSuppression2),
                                                 "referenziert": x.ReferencedConfiguration, "fixiert": bool(x.IsFixed)}
            schalte(asm, "Standard")
            return aus

        lauf.frage("T9.2", stand)
        lauf.frage("T9.4", stand)
        schalte(asm, KONFIG_OHNE)
        x = komp(asm, n)
        lauf.frage("T9.3", lambda: {"auf_2": x.SetSuppression2(SW_AUFGELOEST), "stand": stand()},
                   fall="aufheben in der zweiten Konfiguration")
        schalte(asm, KONFIG_OHNE)
        x = komp(asm, n)
        lauf.frage("T9.3", lambda: {"auf_0": x.SetSuppression2(SW_UNTERDRUECKT), "stand": stand()}, fall="unterdrücken nur dort")
        schalte(asm, KONFIG_OHNE)
        x = komp(asm, n)
        lauf.frage("T9.3", lambda: {"auf_3": x.SetSuppression2(SW_AUFGELOEST_LEICHT), "stand": stand()}, fall="Resolved")
        schalte(asm, KONFIG_OHNE)
        x = komp(asm, n)

        def bezug() -> dict:
            x.ReferencedConfiguration = "Standard"
            return {"ohne_neuaufbau": x.ReferencedConfiguration, "stand": stand()}

        lauf.frage("T9.5", bezug)
        schalte(asm, KONFIG_OHNE)
        lauf.frage("T9.6", lambda: {"fixiere": sw_baugruppe.fixiere(asm, komp(asm, n)), "stand": stand()})
    with arbeit(app, "e/wie") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        vor = e_lagen(asm)
        p = {"id": "k1", "typ": "komponente_neu", "wie": "Anschlag-1"}
        lauf.frage("T9.7", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_neu"](b, p),
                                    "bewegt": [n for n, w in e_lagen(asm).items() if n in vor and w != vor[n]]}, fall="wie Teil")
        lauf.frage("T9.7", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_neu"](b, {**p, "id": "k2",
                "wie": "Muster-1"})},
                fall="wie Unterbaugruppe")
        schalte(asm, KONFIG_OHNE)
        b.aufnahme["aktiv"] = KONFIG_OHNE
        lauf.frage("T9.7", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_neu"](b, {**p, "id": "k3",
                "wie": "Muster-1"})},
                fall="keine aktive Instanz")
    ordner = bestuecke("e/verdeckt")
    baue_block(app, rechner(), ordner / "Zusatz.SLDPRT", (-10, -10, 10, 10), 40, "Zusatz")
    teil = oeffne_in(app, ordner / "Zusatz.SLDPRT", ordner, sichtbar=False, nur_lesen=False)
    asm = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=True, nur_lesen=False)
    lauf.frage("T9.8", lambda: {"offen": offene(app), "titel": teil.GetTitle, "sichtbar": versuch(lambda: bool(teil.Visible))})
    lauf.frage("T10.8", lambda: {"offen": offene(app), "einfuegen": asm.AddComponent5(str(ordner / "Zusatz.SLDPRT"), 0, "", False,
            "", 0.0, mm(-100), 0.0).Name2})

    def zu() -> dict:
        titel = asm.GetTitle
        app.CloseDoc(titel)
        aus: dict = {"offen": offene(app)}
        try:
            aus["alter_handle"] = teil.GetTitle
        except Exception as e:
            aus["alter_handle"] = type(e).__name__
        aus["schliesse"] = versuch(lambda: sw.schliesse(app, teil) or "ohne Fehler")
        return aus

    lauf.frage("T10.10", zu)
    alle_zu(app)
    ordner = bestuecke("e/klein")
    baue_block(app, rechner(), ordner / "klein.SLDPRT", (-10, -10, 10, 10), 40, "klein")
    (ordner / "klein.SLDPRT").rename(ordner / "klein.tmp")
    (ordner / "klein.tmp").rename(ordner / "klein.sldprt")
    asm = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=True, nur_lesen=False)
    t, _ = oeffne(app, ordner / "klein.sldprt", sichtbar=False)
    x = asm.AddComponent5(str(ordner / "klein.sldprt"), 0, "", False, "", 0.0, mm(-100), 0.0)
    lauf.frage("T9.9", {"name": x.Name2, "pfad": x.GetPathName, "datei": [p.name for p in ordner.glob("klein*")]})
    alle_zu(app)


def e_entfernen(app, lauf: Lauf) -> None:
    namen_v = ["Anschlag2 Auflage", "Anschlag2 Mitte", "Anschlag2 Lage"]
    with arbeit(app, "e/entfernen") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        p = {"id": "w1", "typ": "komponente_entfernen", "komponente": "Anschlag-2", "verknuepfungen": namen_v}
        wert = lauf.frage("T9.10", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_entfernen"](b, p), "uebrig": [k.Name2
                for k in komponenten(asm)]},
                          fall="Teil mit Verknüpfungen")
        lauf.frage("P.e3", wert)
        lauf.frage("T9.10", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_entfernen"](b, {
            **p, "id": "w2", "komponente": "Muster-1", "verknuepfungen": ["Antrieb vorne", "Antrieb rechts", "Antrieb Abstand"]}),
                                     "uebrig": [k.Name2 for k in komponenten(asm)]}, fall="Unterbaugruppe mit Kindern")
    with arbeit(app, "e/entfernen_ordner") as (asm, ordner):
        f_ordner(asm)
        b = e_kontext(app, asm, ordner)
        p = {"id": "w1", "typ": "komponente_entfernen", "komponente": "Anschlag-2", "verknuepfungen": namen_v}
        lauf.frage("T9.11", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_entfernen"](b, p), "uebrig": [f.Name
                for f in sw_baugruppe.verknuepfungen(asm)]})


def e_ersetzen(app, lauf: Lauf) -> None:
    with arbeit(app, "e/ersetzen") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        quelle = e_neue_datei(app, b, ordner / "Zusatz.SLDPRT")
        neu = b.quellen[quelle_schluessel(quelle)]
        alt = komp(asm, "Anschlag-1")
        sw.auswahl_leeren(asm)
        lauf.frage("T9.12", lambda: {"select4": alt.Select4(False, asm.SelectionManager.CreateSelectData, False),
                                     "gewaehlt": asm.SelectionManager.GetSelectedObjectCount2(-1)})
        ergebnis = lauf.frage("T9.14", lambda: {"ersetzen": asm.ReplaceComponents2(str(neu.pfad), "", False, 0, True)},
                              fall="leer, MatchName")
        sw.auswahl_leeren(asm)
        lauf.frage("T9.13", lambda: {"alter_handle": alt.Name2, "ersetzen": ergebnis, "namen": [k.Name2
                for k in komponenten(asm)]})
        lauf.frage("P.e2", lambda: {"alter_handle": alt.Name2, "namen": [k.Name2 for k in komponenten(asm)]})
        asm.ForceRebuild3(False)
        lauf.frage("T9.15", lambda: {"neu_titel": versuch(lambda: neu.ctx.model.GetTitle),
                                     "ctx_flaechen": versuch(lambda: neu.ctx.model.GetBodies2(0, False)[0].GetFaceCount),
                                     "offen": offene(app), "handles_offen": [versuch(lambda m=m: m.GetTitle) for m in b.offen]})
        lauf.frage("T9.14", lambda: {"je_konfiguration": e_je_konfiguration(asm, "Zusatz-1")},
                   fall="leer, in allen Konfigurationen")
    with arbeit(app, "e/ersetzen_handler") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        quelle = e_neue_datei(app, b, ordner / "Zusatz.SLDPRT")
        p = {"id": "r1", "typ": "komponente_ersetzen", "komponente": "Anschlag-1", "quelle": quelle}
        lauf.frage("P.e2", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_ersetzen"](b, p), "ersetzt": b.ersetzt,
                                    "neue": b.neue}, fall="Handler")
    with arbeit(app, "e/ersetzen_schlitten") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        quelle = e_neue_datei(app, b, ordner / "Zusatz.SLDPRT")
        p = {"id": "r1", "typ": "komponente_ersetzen", "komponente": "Schlitten-1", "quelle": quelle}
        lauf.frage("T9.16", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_ersetzen"](b, p)},
                   fall="Handler, Flächen-Verknüpfungen")
        lauf.frage("T9.16", lambda: {"verknuepfungen": {f.Name: sw_baugruppe.fehlercode(f)
                                                        for f in sw_baugruppe.verknuepfungen(asm)}}, fall="Stand")
    with arbeit(app, "e/ersetzen_unterdrueckt") as (asm, ordner):
        k = komp(asm, "Anschlag-2")
        lauf.frage("T9.17", lambda: {"unterdruecken": k.SetSuppression2(SW_UNTERDRUECKT)}, fall="Anschlag-2 unterdrücken")
        b = e_kontext(app, asm, ordner)
        quelle = e_neue_datei(app, b, ordner / "Zusatz.SLDPRT")
        p = {"id": "r1", "typ": "komponente_ersetzen", "komponente": "Anschlag-1", "quelle": quelle, "alle_instanzen": True}
        b.spec["punkte"] = [p]
        lauf.frage("T9.17", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_ersetzen"](b, p)}, fall="alle_instanzen")


def e_je_konfiguration(asm, name: str) -> dict:
    aus = {}
    for z in ("Standard", KONFIG_OHNE):
        schalte(asm, z)
        asm.ForceRebuild3(False)
        k = komp(asm, name)
        aus[z] = None if k is None else {"zustand": primitiv(k.GetSuppression2), "referenziert": k.ReferencedConfiguration,
                                         "pfad": k.GetPathName}
    schalte(asm, "Standard")
    return aus


def e_verknuepfungen(app, lauf: Lauf) -> None:
    from swki.bestand.punkte_baugruppe import _entitaet

    with arbeit(app, "e/mate") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        quelle = e_neue_datei(app, b, ordner / "Zusatz.SLDPRT")
        b.spec["punkte"] = [{"id": "k1", "typ": "komponente_neu", "quelle": quelle}]
        lauf.frage("P.e1", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_neu"](b, b.spec["punkte"][0]), "neue": b.neue},
                   fall="Handler, aus Quelle")
        neu = b.neue.get("k1", ["Zusatz-1"])[0]
        lauf.frage("T11.14", lambda: {"protokoll": sorted(n.pfad.name for n in b.quellen.values()), "get_path_name": komp(asm,
                neu).GetPathName})
        anker = {"id": "m1", "typ": "verknuepfung_neu", "art": "deckungsgleich", "a": {"komponente": neu, "ebene": "oben"},
                 "b": {"komponente": "Grundplatte-1", "ebene": "oben"}}
        h = punkte_baugruppe.PUNKTE["verknuepfung_neu"]
        wert = lauf.frage("T9.18", lambda: {"handler": h(b, anker), "lesen": lies_verknuepfungen(asm,
                b.konfigurationen).get("m1")},
                fall="Standardebenen")
        lauf.frage("T9.20", lambda: {"doppelt": e_doppelt(asm), "mit_punkt": h(b, {**anker, "id": "v1.anlage",
                "b": {"komponente": "Anschlag-1",
                "ebene": "oben"}})})
        lauf.frage("T9.19", lambda: {"handler": h(b, {**anker, "id": "m3", "b": {"komponente": "Muster-1/Lagerdeckel-1",
                "ebene": "oben"}})})
        lauf.frage("T9.19", lambda: {"lesen": lies_verknuepfungen(asm, b.konfigurationen).get("m3")}, fall="Stand danach")
        lauf.frage("T9.23", lambda: {"referenz": repr(_entitaet(b, {"komponente": "Anschlag-1", "ebene": "vorne"})[1]),
                                     "feature": versuch(lambda: komp(asm, "Anschlag-1").FeatureByName(AUFSATZ) is not None)})
        lauf.frage("T9.22", lambda: e_gegenstueck(asm, b, {"komponente": "Anschlag-2", "nahe": [0, 0, 30]}),
                   fall="zweite Instanz")
        lauf.frage("T9.22", lambda: e_gegenstueck(asm, b, {"komponente": "Muster-1/Lagerdeckel-1", "nahe": [0, -30, 10]}),
                   fall="Unterbaugruppe")
        ctx = b.kontexte[Path(komp(asm, "Anschlag-1").GetPathName).name.casefold()]
        f = punkte._feature(ctx.model, AUFSATZ)

        def umgeschaltet() -> dict:
            schalte(asm, KONFIG_OHNE)
            asm.ForceRebuild3(False)
            schalte(asm, "Standard")
            return {"name": f.Name, "flaechen": len(f.GetFaces or ())}

        lauf.frage("T9.30", umgeschaltet)
    with arbeit(app, "e/mate_konfiguration") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        k = asm.AddComponent5(str(ordner / "Lagerdeckel.SLDPRT"), 0, "", True, "Variante B", 0.0, mm(-150), mm(10))
        lauf.frage("T9.21", lambda: {"komponente": k.ReferencedConfiguration,
                                     "dokument": k.GetModelDoc2.ConfigurationManager.ActiveConfiguration.Name,
                                     "nahe": versuch(lambda: e_gegenstueck(asm, b, {"komponente": k.Name2, "nahe": [0, -30,
                10]})),
                                     "fase": versuch(lambda: e_gegenstueck(asm, b, {"komponente": k.Name2, "feature": "Fase1",
                "flaeche": "+y"}))})


def e_doppelt(asm) -> dict:
    f = mate(asm, "Hub")
    alt = f.Name
    f.Name = "Schlitten Seite"
    aus = {"gewollt": "Schlitten Seite", "ist": f.Name}
    f.Name = alt
    return aus


def e_gegenstueck(asm, b, seite: dict) -> dict:
    from swki.bestand.punkte_baugruppe import _entitaet

    objekt, ist_feature = _entitaet(b, seite)
    sw_baugruppe.waehle(asm, (objekt, ist_feature), False)
    sm = asm.SelectionManager
    k = sm.GetSelectedObjectsComponent4(1, -1)
    aus = {"gewaehlt": sm.GetSelectedObjectCount2(-1), "komponente": None if k is None else k.Name2}
    sw.auswahl_leeren(asm)
    return aus


def e_werte(app, lauf: Lauf) -> None:
    h = punkte_baugruppe.PUNKTE["verknuepfung_wert"]
    with arbeit(app, "e/werte") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        lauf.frage("T9.24", lambda: {"handler": h(b, {"id": "w1", "verknuepfung": "Schlitten Seite", "alt": 15, "neu": 16}),
                                     "lesen": lies_verknuepfungen(asm, b.konfigurationen)["Schlitten Seite"]},
                                     fall="alle, Option 2")
        lauf.frage("T9.24", lambda: {"handler": h(b, {"id": "w2", "verknuepfung": "Schlitten Seite", "alt": 16, "neu": 17,
                                                      "konfigurationen": [KONFIG_OHNE]}),
                                     "lesen": lies_verknuepfungen(asm, b.konfigurationen)["Schlitten Seite"]},
                                     fall="benannt, Option 3")
        f = mate(asm, "Hub")
        d = f.GetDefinition
        lauf.frage("T9.25", {n: versuch(lambda n=n: getattr(d, n)) for n in ("MinimumDistance", "MaximumDistance", "Distance",
                "IsAdvancedMate", "FlipDimension")})
    with arbeit(app, "e/grenze") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        p = {"id": "w1", "verknuepfung": "Hub", "grenze": "max", "alt": 25, "neu": 30}
        wert = lauf.frage("T9.27", lambda: {"handler": h(b, p), "lesen": lies_verknuepfungen(asm, b.konfigurationen)["Hub"]},
                          fall="alle")
        lauf.frage("P.e4", wert)
        lauf.frage("T9.27", lambda: {"handler": h(b, {**p, "id": "w2", "alt": 30, "neu": 28, "konfigurationen": ["Standard"]}),
                                     "lesen": lies_verknuepfungen(asm, b.konfigurationen)["Hub"]}, fall="nur Standard")
        lauf.frage("P.e4", lambda: lies_verknuepfungen(asm, b.konfigurationen)["Hub"]["werte"], fall="je Konfiguration")
        lauf.frage("T9.26", lambda: {"handler": h(b, {**p, "id": "w3", "grenze": "min", "alt": 0, "neu": 5,
                                                      "konfigurationen": "alle"}),
                                     "lesen": lies_verknuepfungen(asm, b.konfigurationen)["Hub"], "lage": lage_mm(komp(asm,
                "Schlitten-1"))}, fall="D1 unter der neuen Grenze")
    with arbeit(app, "e/definition") as (asm, _):
        for name, leer in (("callout_leer", callout_leer()), ("None", None)):
            def setze(leer=leer) -> dict:
                f = mate(asm, "Hub")
                daten = f.GetDefinition
                daten.MaximumDistance = daten.MaximumDistance + mm(1)
                r = f.ModifyDefinition(daten, asm, leer)
                ohne_neuaufbau = mate(asm, "Hub").GetDefinition.MaximumDistance
                asm.ForceRebuild3(False)
                return {"rueckgabe": r, "ohne_neuaufbau": ohne_neuaufbau, "nach_neuaufbau": mate(asm,
                        "Hub").GetDefinition.MaximumDistance}

            lauf.frage("T9.28", setze, fall=name)
        lauf.frage("T9.28", "IDistanceMateFeatureData hat laut Index kein AccessSelections, nur IMateControllerFeatureData",
                   fall="AccessSelections")

        def ohne_neuaufbau() -> dict:
            f2 = mate(asm, "Hub")
            d2 = f2.GetDefinition
            d2.MaximumDistance = mm(40)
            f2.ModifyDefinition(d2, asm, callout_leer())
            schalte(asm, KONFIG_OHNE)
            aus = {"zweite": mate(asm, "Hub").GetDefinition.MaximumDistance}
            schalte(asm, "Standard")
            aus["zurueck"] = mate(asm, "Hub").GetDefinition.MaximumDistance
            return aus

        lauf.frage("T9.31", ohne_neuaufbau)
    with arbeit(app, "e/loeschen") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        h2 = punkte_baugruppe.PUNKTE["verknuepfung_loeschen"]
        lauf.frage("T9.29", lambda: {"handler": h2(b, {"id": "l1", "verknuepfung": "Anschlag1 Mitte"})}, fall="fremd")
        f_ordner(asm)
        lauf.frage("T9.29", lambda: {"handler": h2(b, {"id": "l2", "verknuepfung": "Anschlag2 Mitte"}),
                                     "je": {k: len(sw_baugruppe.verknuepfungen(asm)) for k in ("Standard",)}},
                   fall="im Ordner")


def e_speichern(app, lauf: Lauf) -> None:
    with arbeit(app, "e/save_leer") as (asm, ordner):
        vorher = shas(ordner)
        lauf.frage("T10.1", lambda: {"dirty": asm.GetSaveFlag, "speichern": speichern(asm), "geaendert": [k for k,
                v in shas(ordner).items() if vorher[k] != v]}, fall="ohne Änderung")
    with arbeit(app, "e/save_komponente") as (asm, ordner):
        vorher = shas(ordner)
        doc = komp(asm, "Anschlag-1").GetModelDoc2
        doc.Parameter(DICKE).SetSystemValue3(mm(33), SW_WERT_ALLE, None)
        asm.ForceRebuild3(False)
        lauf.frage("T10.1", lambda: {"dirty": [asm.GetSaveFlag, doc.GetSaveFlag], "speichern": speichern(asm), "geaendert": [k
                for k, v in shas(ordner).items() if vorher[k] != v]},
                   fall="Komponente im Speicher geändert")
    ordner = bestuecke("e/unter")
    vorher = shas(ordner)
    deckel = oeffne_in(app, ordner / "Lagerdeckel.SLDPRT", ordner, sichtbar=True, nur_lesen=False)
    deckel.Parameter(DICKE).SetSystemValue3(mm(21), SW_WERT_ALLE, None)
    deckel.EditRebuild3
    speichern(deckel)
    alle_zu(app)
    asm = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=True, nur_lesen=False)
    asm.ForceRebuild3(False)
    lauf.frage("T10.2", lambda: {"geaendert": [k for k, v in shas(ordner).items() if vorher[k] != v],
                                 "volumen": volumen(komp(asm, "Muster-1/Lagerdeckel-1").GetModelDoc2), "dirty": asm.GetSaveFlag})
    alle_zu(app)
    with arbeit(app, "e/konflikt") as (asm, ordner):
        a, b = _entitaeten(mate(asm, "Schlitten Seite"))
        lauf["konflikt"] = verknuepfe_roh(asm, "Konflikt", SW_ABSTAND, 0, a, b, 5.0)
        ok = asm.ForceRebuild3(False)
        fehler = whats_wrong(asm)
        lauf.frage("T10.4", lambda: {"whats_wrong": fehler, "codes": {f.Name: sw_baugruppe.fehlercode(f)
                                                                      for f in sw_baugruppe.verknuepfungen(asm)}})
        lauf.frage("T10.5", {"force": ok, "edit": asm.EditRebuild3, "fehler": len(fehler)})
        vorher_z = shas(ordner)
        lauf.frage("T10.9", lambda: {"dirty": asm.GetSaveFlag, "zu": alle_zu(app), "offen": offene(app),
                                     "dateien_gleich": vorher_z == shas(ordner)})
    with arbeit(app, "e/rebuild") as (asm, _):
        doc = komp(asm, "Grundplatte-1").GetModelDoc2
        doc.Parameter(DICKE).SetSystemValue3(mm(18), SW_WERT_ALLE, None)
        doc.EditRebuild3
        aus = {"vor": lage_mm(komp(asm, "Schlitten-1")), "edit": asm.EditRebuild3, "nach_edit": lage_mm(komp(asm, "Schlitten-1"))}
        aus |= {"force": asm.ForceRebuild3(False), "nach_force": lage_mm(komp(asm, "Schlitten-1"))}
        lauf.frage("T10.6", aus)
    ordner = bestuecke("e/aktiv")
    als_original(app, ordner, KONFIG_OHNE)
    asm, s = oeffne(app, ordner / HUBEINHEIT)
    lauf.frage("T10.12", {"oeffnen": s, "aktiv": asm.ConfigurationManager.ActiveConfiguration.Name, "soll": KONFIG_OHNE})
    alle_zu(app)
    ordner = bestuecke("e/teil_konfiguration")
    deckel = oeffne_in(app, ordner / "Lagerdeckel.SLDPRT", ordner, sichtbar=True, nur_lesen=False)
    deckel.ShowConfiguration2("Variante B")
    speichern(deckel)
    alle_zu(app)
    asm = oeffne_in(app, ordner / HUBEINHEIT, ordner, sichtbar=True, nur_lesen=False)
    lauf.frage("T10.13", lambda: {"referenziert": komp(asm, "Muster-1/Lagerdeckel-1").ReferencedConfiguration,
                                  "dokument": komp(asm,
                                                   "Muster-1/Lagerdeckel-1").GetModelDoc2.ConfigurationManager.ActiveConfiguration.Name})
    alle_zu(app)
    e_haupt(app, lauf)


def e_unsichtbar(app, lauf: Lauf, sichtbar: bool = False) -> dict:
    """T10.3: Handler von Etappe 1 an einem Teil ohne Fenster, Normbohrung auf der fremden Oberseite; zum Vergleich mit Fenster."""
    from swki.compiler.handler.normbohrung import normbohrung
    from swki.compiler.kontext import Kontext

    ordner = bestuecke(f"e/scheibe_{'fenster' if sichtbar else 'unsichtbar'}")
    try:
        with Spitzenmessung(lauf.pid) as spitze:
            m = oeffne_in(app, ordner / "teile/Grundplatte.SLDPRT", ordner, sichtbar=sichtbar, nur_lesen=False)
            v0 = volumen(m)
            f = {"id": "neu1", "typ": "normbohrung", "art": "gewinde", "groesse": "M6", "flaeche": {"nahe": [50, 0, 15]},
                 "positionen": [[50, 20]], "tiefe": 10}
            ctx = Kontext(app, m, {"parameter": {}, "features": [f]}, ordner / "spec.yaml", 0.01)
            ctx.knoten = "neu1"
            normbohrung(ctx, f)
            aus = {"volumen": [v0, volumen(m)], "baum": m.FeatureByPositionReverse(0).Name, "speichern": speichern(m)}
    finally:
        alle_zu(app)  # ein offenes Teil gewänne sonst beim nächsten Auflösen (P.c4)
    return aus | {"speicher": spitze.als_dict()}


def e_partner_unterdrueckt(app, lauf: Lauf) -> None:
    """T9.19 neu: eine neue Komponente ohne andere Bindung, Verknüpfung an die Unterbaugruppe, die in „Ohne Antrieb“ unterdrückt ist."""
    with arbeit(app, "e/partner") as (asm, ordner):
        b = e_kontext(app, asm, ordner)
        quelle = e_neue_datei(app, b, ordner / "Zusatz.SLDPRT")
        b.spec["punkte"] = [{"id": "k1", "typ": "komponente_neu", "quelle": quelle}]
        punkte_baugruppe.PUNKTE["komponente_neu"](b, b.spec["punkte"][0])
        neu = b.neue.get("k1", ["Zusatz-1"])[0]
        p = {"id": "m3", "typ": "verknuepfung_neu", "art": "deckungsgleich", "a": {"komponente": neu, "ebene": "rechts"},
             "b": {"komponente": "Muster-1/Lagerdeckel-1", "ebene": "rechts"}}
        lauf.frage("T9.19", lambda: {"handler": punkte_baugruppe.PUNKTE["verknuepfung_neu"](b, p)}, fall="Handler, ohne Widerspruch")
        lauf.frage("T9.19", lambda: {"lesen": lies_verknuepfungen(asm, b.konfigurationen).get("m3"),
                                     "je": e_je_konfiguration(asm, neu)}, fall="Stand danach")


def e_haupt(app, lauf: Lauf) -> None:
    lauf.frage("T10.3", lambda: e_unsichtbar(app, lauf), fall="unsichtbar")
    lauf.frage("T10.3", lambda: e_unsichtbar(app, lauf, sichtbar=True), fall="Fenster")
    with arbeit(app, "e/skript") as (asm, ordner):
        skript = ordner / "skript.py"
        skript.write_text('def bauen(ctx):\n    ctx.model.Extension.CustomPropertyManager("").Add3("Skript", 30, "ja", 2)\n',
                          encoding="utf-8")
        spec = {"punkte": [{"id": "s1", "typ": "skript", "datei": "skript.py", "luecke": "S19"}], "parameter": {}}
        ctx = punkte.kontext(app, asm, spec, ordner / "spec.yaml", 0.01)
        aufnahme = e_kontext(app, asm, ordner).aufnahme
        lauf.frage("T10.14", lambda: {"handler": punkte.punkt_handler("skript")(ctx, spec["punkte"][0], aufnahme),
                                      "eigenschaft": eigenschaften_von(asm, "").get("Skript")})
    with arbeit(app, "e/baum") as (asm, ordner):
        vorher = [f.Name for f in baum_ohne_glieder(asm)]
        t = time.monotonic()
        lies_komponenten(asm, ["Standard", KONFIG_OHNE], rels())
        lies_verknuepfungen(asm, ["Standard", KONFIG_OHNE])
        lauf.frage("T10.15", {"lesen_je_handler_s": round(time.monotonic() - t, 2),
                              "hinweis": "Hubeinheit: 7 Komponenten, Zahlen für lauf-30 in Task 16"})
        b = e_kontext(app, asm, ordner)
        quelle = e_neue_datei(app, b, ordner / "Zusatz_ä-1.SLDPRT")
        b.spec["punkte"] = [{"id": "k1", "typ": "komponente_neu", "quelle": quelle}]
        lauf.frage("T11.K4", lambda: {"handler": punkte_baugruppe.PUNKTE["komponente_neu"](b, b.spec["punkte"][0]),
                                      "pfad": [k.GetPathName for k in komponenten(asm) if "Zusatz" in k.Name2]})
        neu = b.neue.get("k1", ["?"])[0]
        lauf.frage("T10.16", lambda: {"mate": punkte_baugruppe.PUNKTE["verknuepfung_neu"](b, {"id": "m1",
                "typ": "verknuepfung_neu",
                "art": "deckungsgleich",
                "a": {"komponente": neu,
                "ebene": "oben"},
                "b": {"komponente": "Grundplatte-1", "ebene": "oben"}}),
                                      "vorher": vorher, "nachher": [f.Name for f in baum_ohne_glieder(asm)]})


def zeile_e(app) -> None:
    lauf = Lauf(app, "e")
    frisch("e")
    alt = app.GetUserPreferenceToggle(10)
    app.SetUserPreferenceToggle(10, False)  # swInputDimValOnCreate: `baue_block` bemaßt ohne Dialog
    try:
        for abschnitt in (e_einfuegen, e_entfernen, e_ersetzen, e_verknuepfungen, e_werte, e_speichern):
            try:
                abschnitt(app, lauf)
            except Exception:  # ein Abschnitt kostet nur sich selbst, die übrigen Fragen laufen weiter
                lauf[f"abbruch_{abschnitt.__name__}"] = traceback.format_exc()
                alle_zu(app)
    finally:
        app.SetUserPreferenceToggle(10, alt)
    lauf.schliesse()


# ---------------------------------------------------------------------- Zeile v: Referenz Schlitten


def v_baue_schlitten() -> Path:
    """Baut die Referenz im Testauftrag über die normalen Befehle: eigene Datei, nichts von Bestand. Liefert den Lauf-Ordner."""
    from argparse import Namespace

    from swki.auftrag import lauf_ordner
    from swki.compiler.bauen import _bauen
    from swki.spec.befehle import _freigeben, _validieren

    r = rechner()
    ordner = r.arbeitsordner / "S19" / "spec" / AUFTRAG_SCHLITTEN
    if ordner.exists():
        shutil.rmtree(ordner)
    shutil.copytree(PROJEKT / "tests" / "referenz" / "schlitten", ordner)
    spec = ordner / "linearschlitten.yaml"
    _validieren(Namespace(spec=str(spec)))
    _freigeben(Namespace(spec=str(spec)))
    aus = _bauen(Namespace(spec=str(spec), lauf=None, verwerfen=False, uebernommen=False, alles_neu=False))
    return lauf_ordner(r, AUFTRAG_SCHLITTEN, aus["lauf"])


def zeile_v(app) -> None:
    lauf = Lauf(app, "v")
    lauf_ordner_ = v_baue_schlitten()
    pruefe_quelle(lauf_ordner_)
    lauf["gebaut"] = str(lauf_ordner_)
    spec = s19_ordner() / "spec" / AUFTRAG_SCHLITTEN / "linearschlitten.yaml"
    from swki.aenderungen import aenderungen

    wert = lauf.frage("P.f5", lambda: aenderungen(spec), fall="swki aenderungen am unveränderten Lauf")
    lauf.frage("P.f6", wert)
    lauf.frage("P.f7", wert)
    alle_zu(app)
    ziel = frisch("v/schlitten")
    for p in lauf_ordner_.iterdir():
        if p.is_file() and p.suffix.lower() in (".sldprt", ".sldasm"):
            shutil.copy2(p, ziel / p.name)
            (ziel / p.name).chmod(stat.S_IWRITE)
    haupt = next(p for p in ziel.glob("*.SLDASM"))
    lauf["kopie"] = shas(ziel)
    asm, s = oeffne(app, haupt, OFFEN | VOLL | NUR_LESEN, sichtbar=False)
    lauf["oeffnen"] = s
    gelesen = lies_baugruppe(app, asm, {})
    lauf["verknuepfungen"] = gelesen["verknuepfungen"]
    lauf.frage("P.a6", {n: {"typ": v["typ"], "partner": v["partner"]} for n, v in gelesen["verknuepfungen"].items()
                        if n.startswith("s1")})
    lauf["fahrt"] = versuch(lambda: fahrt(app, asm, None, gelesen))
    alle_zu(app)
    # unsichtbar gibt es keine Kollision (Zeile d): die Fahrt mit Fenster, wie `swki pruefen` sie fährt
    asm, s = oeffne(app, haupt, OFFEN | VOLL | NUR_LESEN)
    gelesen = lies_baugruppe(app, asm, {})
    lauf["fahrt_fenster"] = versuch(lambda: fahrt(app, asm, frisch("v/bilder"), gelesen))
    alle_zu(app)
    lauf["kopie_danach_gleich"] = shas(ziel) == lauf["kopie"]
    lauf.schliesse()


def zeile_e2(app) -> None:
    """Nachlauf zu Zeile e: `e_speichern` brach im ersten Lauf ab, T9.19 brauchte eine Komponente ohne Widerspruch."""
    lauf = Lauf(app, "e2")
    alt = app.GetUserPreferenceToggle(10)
    app.SetUserPreferenceToggle(10, False)
    try:
        for abschnitt in (e_partner_unterdrueckt, e_speichern):
            try:
                abschnitt(app, lauf)
            except Exception:
                lauf[f"abbruch_{abschnitt.__name__}"] = traceback.format_exc()
                alle_zu(app)
    finally:
        app.SetUserPreferenceToggle(10, alt)
    lauf.schliesse()


ZEILEN = {"a": zeile_a, "b": zeile_b, "c": zeile_c, "d": zeile_d, "e": zeile_e, "e2": zeile_e2, "f": zeile_f, "v": zeile_v}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Spike S19: Baugruppen live")
    parser.add_argument("zeile", choices=sorted(ZEILEN), help=f"Reihenfolge nach Risiko: {' '.join(REIHENFOLGE)}")
    args = parser.parse_args(argv)
    app = verbinde(rechner().sw_jahr)
    pruefe_leer(app)  # vor allem anderen: Ein offenes Dokument gehört dem Nutzer
    try:
        ZEILEN[args.zeile](app)
    except Exception:
        print(traceback.format_exc())
        ERGEBNIS.mkdir(parents=True, exist_ok=True)
        (ERGEBNIS / f"s19_{args.zeile}.fehler.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        alle_zu(app)
    print((ERGEBNIS / f"s19_{args.zeile}.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    sys.exit(main())
