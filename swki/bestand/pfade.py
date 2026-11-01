"""Pfadschutz (Spec §8.1a): Fehlt eine Datei neben der Baugruppe, lädt SolidWorks still vom gespeicherten Pfad, also womöglich
vom Original (S18g, Warnung 0). Zwei Sperren für jedes Öffnen einer Bestandskopie oder eines Laufs: vor dem Öffnen die
Abhängigkeiten nach Suchregeln auflösen, nach dem Öffnen alles Geladene gegen den Ordner prüfen. Bei einem Fund wird ohne
Speichern geschlossen."""

import os
from pathlib import Path, PureWindowsPath

from swki.bestand.ablage import ist_virtuell
from swki.bestand.fehler import BESTAND_PFAD_FREMD, BestandFehler
from swki.compiler import sw
from swki.pruefung.bewertung import eintrag
from swki.pruefung.messen import oeffne
from swki.verbindung import wert


def _schluessel(pfad: str) -> PureWindowsPath:
    """Aufgelöster Pfad ohne Beachtung der Schreibweise; verglichen wird über die Pfadteile, nie über Zeichenketten."""
    return PureWindowsPath(str(Path(pfad).resolve()).lower())


def fremde_pfade(eintraege: list[dict], wurzel: Path) -> list[dict]:
    """Die Einträge `{"name", "pfad", "virtuell"}`, deren Datei nicht unter `wurzel` liegt. Virtuelle Komponenten haben keine
    Datei und zählen nicht, ebenso wenig Einträge ohne Pfad (ungespeichert). Der Vergleich folgt nach `resolve` den Pfadteilen
    und achtet nicht auf die Schreibweise."""
    ordner = _schluessel(str(wurzel))
    return [e for e in eintraege
            if e["pfad"] and not e["virtuell"] and not _schluessel(e["pfad"]).is_relative_to(ordner)]


def aufgeloeste_referenzen(app, pfad: Path) -> list[str]:
    """Pfade aller Dateien, von denen `pfad` abhängt, nach den Suchregeln aufgelöst und ohne das Dokument zu öffnen (alle
    Ebenen, Paare Titel/Pfad, `None` ohne Referenz, S18b). Virtuelle Teile haben keine Datei und fehlen hier."""
    paare = app.GetDocumentDependencies2(str(pfad), True, True, False) or ()
    return [p for p in paare[1::2] if p and not ist_virtuell(p)]


def _fremd(fremd: list[dict], wo: str, datei: Path) -> BestandFehler:
    liste = [e["pfad"] for e in fremd]
    return BestandFehler(BESTAND_PFAD_FREMD, f"SolidWorks würde bei {datei.name} {len(liste)} Dateien außerhalb des Ordners "
                                             f"laden ({wo}): {', '.join(liste)}", pfade=liste, wo=wo, datei=str(datei))


def pruefe_vor_dem_oeffnen(app, pfad: Path, wurzel: Path) -> None:
    """Sperre 1: Zeigt eine aufgelöste Referenz aus `wurzel` heraus, wird nicht geöffnet (`BESTAND_PFAD_FREMD`)."""
    eintraege = [{"name": Path(p).name, "pfad": p, "virtuell": False} for p in aufgeloeste_referenzen(app, pfad)]
    fremd = fremde_pfade(eintraege, wurzel)
    if fremd:
        raise _fremd(fremd, "vor dem Öffnen", pfad)


def _norm(pfad: str) -> str:
    return os.path.normcase(os.path.abspath(pfad))


def offene_dokumente(app) -> set[str]:
    """Pfade der Dokumente, die in SolidWorks jetzt offen sind (normiert), als Stand vor dem Öffnen."""
    return {_norm(wert(d.GetPathName)) for d in wert(app.GetDocuments) or () if wert(d.GetPathName)}


def geladene_pfade(app, model, vorher: set[str]) -> list[dict]:
    """Alles, was nach dem Öffnen von `model` im Speicher steht: das Dokument, bei einer Baugruppe jede Komponente auf allen
    Ebenen (`GetComponents(False)`, auch unterdrückte) und die Dokumente, die seit `vorher` (`offene_dokumente`) dazugekommen
    sind. Ein vorher schon offenes Dokument zählt nur, wenn die Baugruppe es als Komponente nennt. Ein Teil hat kein
    `GetComponents`."""
    gefunden: dict[str, dict] = {}

    def nimm(pfad: str, virtuell: bool) -> None:
        gefunden.setdefault(_norm(pfad) if pfad else f"#{len(gefunden)}",
                            {"name": Path(pfad).name, "pfad": pfad, "virtuell": virtuell or ist_virtuell(pfad)})

    haupt = wert(model.GetPathName)
    nimm(haupt, False)
    if Path(haupt).suffix.lower() == ".sldasm":
        for komp in wert(model.GetComponents(False)) or ():
            nimm(wert(komp.GetPathName), bool(wert(komp.IsVirtual)))
    for d in wert(app.GetDocuments) or ():
        pfad = wert(d.GetPathName)
        if pfad and _norm(pfad) not in vorher:
            nimm(pfad, False)
    return list(gefunden.values())


def pruefe_geladen(app, model, wurzel: Path, vorher: set[str]) -> dict:
    """Sperre 2 als Prüfungseintrag `pfade` (Format von `bewertung.eintrag`): `ok` heißt, alles Geladene liegt unter
    `wurzel`."""
    geladen = geladene_pfade(app, model, vorher)
    fremd = [e["pfad"] for e in fremde_pfade(geladen, wurzel)]
    return eintrag("pfade", not fremd, geladen=len(geladen), fremd=fremd)


def oeffne_in(app, pfad: Path, wurzel: Path, sichtbar: bool = False, nur_lesen: bool = True):
    """Öffnet `pfad` (Teil oder Baugruppe, Typ nach der Endung) mit beiden Sperren; `wurzel` ist der Ordner `bestand-<n>` bzw.
    `lauf-<n>`. Geöffnet wird voll geladen, damit jede Komponente ihren Pfad zeigt. Bei einem Fund nach dem Laden wird das
    Dokument ohne Speichern geschlossen und `BESTAND_PFAD_FREMD` geworfen."""
    pruefe_vor_dem_oeffnen(app, pfad, wurzel)
    vorher = offene_dokumente(app)
    model = oeffne(app, pfad, sichtbar=sichtbar, nur_lesen=nur_lesen, voll=True)
    geladen = pruefe_geladen(app, model, wurzel, vorher)
    if not geladen["ok"]:
        sw.schliesse(app, model)
        raise _fremd([{"pfad": p} for p in geladen["fremd"]], "nach dem Öffnen", pfad)
    return model
