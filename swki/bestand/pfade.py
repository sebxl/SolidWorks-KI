"""Pfadschutz (Spec §8.1a): Fehlt eine Datei neben der Baugruppe, lädt SolidWorks still vom gespeicherten Pfad, also womöglich
vom Original (S18g, Warnung 0). Zwei Sperren für jedes Öffnen einer Bestandskopie oder eines Laufs: vor dem Öffnen die
Abhängigkeiten nach Suchregeln auflösen, nach dem Öffnen alles Geladene gegen den Ordner prüfen. Bei einem Fund wird ohne
Speichern geschlossen.

Unterdrückte Komponenten (S19c, T8.9): `GetPathName` nennt in der aktiven Konfiguration den gespeicherten Pfad, geladen ist
nichts; nach dem Umschalten nennen sie und ihre Kinder die Kopie. Die zweite Sperre nimmt sie darum aus, ihren Pfad sichert die
erste: Ihre Datei muss unter den aufgelösten Referenzen im Ordner stehen. Nach jedem Konfigurationswechsel beim Lesen läuft die
zweite Sperre erneut (`sperre_beim_umschalten`), dann ist die Komponente geladen und zeigt, woher."""

import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from swki.bestand.ablage import ist_virtuell
from swki.bestand.fehler import BESTAND_PFAD_FREMD, BestandFehler
from swki.compiler import sw
from swki.pruefung.bewertung import eintrag
from swki.pruefung.messen import oeffne
from swki.verbindung import wert

SW_UNTERDRUECKT = 0  # swComponentSuppressionState_e.swComponentSuppressed


@dataclass(frozen=True)
class _Schutz:
    """Was `oeffne_in` für die Sperre nach einem Konfigurationswechsel braucht."""

    app: object
    wurzel: Path
    aufgeloest: tuple[str, ...]  # Sperre 1: aufgelöste Referenzen, alle unter `wurzel`


_GESCHUETZT: dict[str, _Schutz] = {}  # normierter Pfad → Schutz, je über `oeffne_in` geöffnetes Dokument


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


def _eintraege(pfade: list[str]) -> list[dict]:
    return [{"name": Path(p).name, "pfad": p, "virtuell": False} for p in pfade]


def pruefe_vor_dem_oeffnen(app, pfad: Path, wurzel: Path) -> list[str]:
    """Sperre 1: Zeigt eine aufgelöste Referenz aus `wurzel` heraus, wird nicht geöffnet (`BESTAND_PFAD_FREMD`). Gibt die
    aufgelösten Referenzen zurück."""
    aufgeloest = aufgeloeste_referenzen(app, pfad)
    fremd = fremde_pfade(_eintraege(aufgeloest), wurzel)
    if fremd:
        raise _fremd(fremd, "vor dem Öffnen", pfad)
    return aufgeloest


def _norm(pfad: str) -> str:
    return os.path.normcase(os.path.abspath(pfad))


def offene_dokumente(app) -> set[str]:
    """Pfade der Dokumente, die in SolidWorks jetzt offen sind (normiert), als Stand vor dem Öffnen."""
    return {_norm(wert(d.GetPathName)) for d in wert(app.GetDocuments) or () if wert(d.GetPathName)}


def _unterdrueckt(komp) -> bool:
    """Unlesbar zählt als geladen: Die strengere Prüfung gilt."""
    try:
        return wert(komp.GetSuppression2) == SW_UNTERDRUECKT
    except Exception:
        return False


def geladene_pfade(app, model, vorher: set[str]) -> list[dict]:
    """Alles, was nach dem Öffnen von `model` im Speicher steht: das Dokument, bei einer Baugruppe jede Komponente auf allen
    Ebenen (`GetComponents(False)`, auch unterdrückte) und die Dokumente, die seit `vorher` (`offene_dokumente`) dazugekommen
    sind. Ein vorher schon offenes Dokument zählt nur, wenn die Baugruppe es als Komponente nennt. Ein Teil hat kein
    `GetComponents`. `unterdrueckt`: Jede Komponente mit diesem Pfad ist in der aktiven Konfiguration unterdrückt."""
    gefunden: dict[str, dict] = {}

    def nimm(pfad: str, virtuell: bool, unterdrueckt: bool = False) -> None:
        e = gefunden.setdefault(_norm(pfad) if pfad else f"#{len(gefunden)}",
                                {"name": Path(pfad).name, "pfad": pfad, "virtuell": virtuell or ist_virtuell(pfad),
                                 "unterdrueckt": unterdrueckt})
        e["unterdrueckt"] = e["unterdrueckt"] and unterdrueckt  # eine aktive Instanz lädt wirklich von dort

    haupt = wert(model.GetPathName)
    nimm(haupt, False)
    if Path(haupt).suffix.lower() == ".sldasm":
        for komp in wert(model.GetComponents(False)) or ():
            nimm(wert(komp.GetPathName), bool(wert(komp.IsVirtual)), _unterdrueckt(komp))
    for d in wert(app.GetDocuments) or ():
        pfad = wert(d.GetPathName)
        if pfad and _norm(pfad) not in vorher:
            nimm(pfad, False)
    return list(gefunden.values())


def pruefe_geladen(app, model, wurzel: Path, vorher: set[str], aufgeloest: list[str] | None = None) -> dict:
    """Sperre 2 als Prüfungseintrag `pfade` (Format von `bewertung.eintrag`): `ok` heißt, alles Geladene liegt unter
    `wurzel`. Eine unterdrückte Komponente außerhalb zählt nicht, wenn Sperre 1 ihre Datei im Ordner aufgelöst hat (`aufgeloest`,
    ohne Angabe die von `oeffne_in`; fehlt beides, ist sie ein Fund)."""
    if aufgeloest is None:
        schutz = _GESCHUETZT.get(_norm(wert(model.GetPathName)))
        aufgeloest = list(schutz.aufgeloest) if schutz else []
    im_ordner = {e["name"].casefold() for e in _eintraege(aufgeloest) if not fremde_pfade([e], wurzel)}
    geladen = geladene_pfade(app, model, vorher)
    fremd = [e["pfad"] for e in fremde_pfade(geladen, wurzel) if not (e["unterdrueckt"] and e["name"].casefold() in im_ordner)]
    return eintrag("pfade", not fremd, geladen=len(geladen), fremd=fremd)


def _schliesse_still(app, model) -> str | None:
    """Schließt ohne Speichern; ein Fehler dabei verdeckt nie den eigentlichen Befund und kommt als Text zurück."""
    try:
        sw.schliesse(app, model)
    except Exception as e:
        return f"{type(e).__name__}: {e}"
    return None


def oeffne_in(app, pfad: Path, wurzel: Path, sichtbar: bool = False, nur_lesen: bool = True):
    """Öffnet `pfad` (Teil oder Baugruppe, Typ nach der Endung) mit beiden Sperren; `wurzel` ist der Ordner `bestand-<n>` bzw.
    `lauf-<n>`. Geöffnet wird voll geladen, damit jede Komponente ihren Pfad zeigt. Bei einem Fund nach dem Laden wird das
    Dokument ohne Speichern geschlossen und `BESTAND_PFAD_FREMD` geworfen; scheitert die Prüfung selbst, wird ebenfalls
    geschlossen und die Ursache weitergereicht. Danach kennt `sperre_beim_umschalten` das Dokument."""
    aufgeloest = pruefe_vor_dem_oeffnen(app, pfad, wurzel)
    vorher = offene_dokumente(app)
    model = oeffne(app, pfad, sichtbar=sichtbar, nur_lesen=nur_lesen, voll=True)
    try:
        geladen = pruefe_geladen(app, model, wurzel, vorher, aufgeloest)
    except BaseException:
        _schliesse_still(app, model)  # scheitert die Prüfung selbst, bleibt das Dokument nicht offen; die Ursache kommt durch
        raise
    if not geladen["ok"]:
        fehler = _fremd([{"pfad": p} for p in geladen["fremd"]], "nach dem Öffnen", pfad)
        schliessfehler = _schliesse_still(app, model)
        if schliessfehler is not None:
            fehler.daten["schliessen_fehlgeschlagen"] = schliessfehler  # der Pfadbefund bleibt, das Dokument ist noch offen
        raise fehler
    _GESCHUETZT[_norm(str(pfad))] = _Schutz(app, Path(wurzel), tuple(aufgeloest))
    return model


@contextmanager
def sperre_beim_umschalten(model, konfiguration: str):
    """Sperre 2 nach einem Konfigurationswechsel (§8.1a, S19c T8.9): Der Block schaltet um und baut neu auf, danach muss alles
    Geladene wieder im Ordner liegen, auch eine eben aufgehobene Komponente; ein Dokument, das der Wechsel nachlädt, zählt mit.
    `BESTAND_PFAD_FREMD`, geschlossen wird vom Aufrufer (alle schließen im `finally`). Ein Dokument, das nicht über `oeffne_in`
    aufging, gehört nicht zum Bestand und wird nicht geprüft."""
    pfad = wert(model.GetPathName)
    schutz = _GESCHUETZT.get(_norm(pfad)) if pfad else None
    if schutz is None:
        yield
        return
    vorher = offene_dokumente(schutz.app)
    yield
    geladen = pruefe_geladen(schutz.app, model, schutz.wurzel, vorher, list(schutz.aufgeloest))
    if not geladen["ok"]:
        raise _fremd([{"pfad": p} for p in geladen["fremd"]], f"nach dem Umschalten auf {konfiguration}", Path(pfad))
