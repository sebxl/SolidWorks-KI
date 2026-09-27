"""Handler "skript" – kontrollierter Notausgang für Lücken im Spezifikationsformat.

Das Skript (auftraege/<auftrag>/skripte/<id>.py) wird vor dem Laden statisch geprüft (swki.compiler.skriptpruefung)
und bekommt nur einen SkriptKontext. `bauen(ctx)` muss das erzeugte IFeature oder eine Liste davon zurückgeben.
"""

from swki.compiler import sw
from swki.compiler.fehler import SKRIPT_FEHLER, BauFehler
from swki.compiler.kontext import FeatureErgebnis
from swki.compiler.registry import handler
from swki.compiler.skizze import Skizzierer, ebene_aufloesen, modellpunkt, skizziere
from swki.compiler.skriptpruefung import pruefe_skript
from swki.compiler.topologie import loese_flaeche, loese_kanten
from swki.verbindung import byref_long, callout_leer


class SkriptKontext:
    """Was ein Notausgang-Skript darf: SW-Objekte lesen/erzeugen, Anker auflösen, Skizzen anlegen."""

    def __init__(self, ctx, fid: str):
        self._ctx = ctx
        self._fid = fid
        self.app = ctx.app
        self.model = ctx.model
        self.callout_leer = callout_leer
        self.byref_long = byref_long

    def wert(self, x) -> float:
        return self._ctx.wert(x)

    def m(self, x) -> float:
        return self._ctx.m(x)

    def rad(self, x) -> float:
        return self._ctx.rad(x)

    def feature(self, fid: str):
        return self._ctx.ergebnis(fid).features[0]

    def flaeche(self, anker: dict):
        """Flächenanker → Flaeche (mit .objekt = IFace2, .punkt, .normale in mm)."""
        return loese_flaeche(self._ctx, anker)

    def kanten(self, anker: dict) -> list:
        return loese_kanten(self._ctx, anker)

    def ebene(self, ebene):
        """Ebene wie in der Spezifikation ("oben", {versatz}, {feature, flaeche}, {nahe}) → Skizzenebene."""
        return ebene_aufloesen(self._ctx, ebene)

    def skizze(self, ebene, elemente: list[dict], name: str = "skizze"):
        """Voll bestimmte Skizze wie in der Spezifikation; Rückgabe (Skizzen-Feature, Skizzenebene)."""
        return skizziere(self._ctx, ebene, elemente, f"{self._fid}_{name}")

    def modellpunkt_m(self, skizzenebene, u, v) -> tuple[float, float, float]:
        """Skizzenkoordinaten (mm) auf einer Skizzenebene → Modellpunkt in Metern (für API-Aufrufe)."""
        p = modellpunkt(skizzenebene.orientierung, self.wert(u), self.wert(v), skizzenebene.lage)
        return tuple(c / 1000.0 for c in p)

    def punkte_festlegen(self, feature, ebene, punkte_uv: list) -> None:
        """Nicht voll bestimmte Skizzen von feature (auch Unterskizzen, z. B. Positionsskizze des Bohrungsassistenten)
        öffnen und die Lage der Punkte (u, v) wie in der Spezifikation zum Ursprung bemaßen."""
        se = ebene_aufloesen(self._ctx, ebene)
        skizzen, unter = [], feature.GetFirstSubFeature
        while unter is not None:
            if unter.GetTypeName2 == "ProfileFeature":
                skizzen.append(unter)
            unter = unter.GetNextSubFeature
        sm = self.model.SketchManager
        for skizze in skizzen:
            if skizze.GetSpecificFeature2.GetConstrainedStatus == sw.SW_FULLY_CONSTRAINED:
                continue
            sw.auswahl_leeren(self.model)
            skizze.Select2(False, 0)
            sm.InsertSketch(True)  # öffnet die selektierte Skizze (S9b)
            try:
                skizzierer = Skizzierer(self._ctx, se, sm.ActiveSketch)
                with sw.einstellung(self.app, sw.SW_INPUT_DIM_VAL_ON_CREATE, False):
                    for u, v in punkte_uv:
                        if skizzierer.hat_punkt(u, v):
                            skizzierer.lage((u, v), (self.wert(u) + 8, self.wert(v) + 8))
            finally:
                sm.InsertSketch(True)

    def waehle(self, objekt, marke: int = 0, anhaengen: bool = False) -> None:
        sw.waehle(self.model, objekt, marke, anhaengen)

    def auswahl_leeren(self) -> None:
        sw.auswahl_leeren(self.model)


@handler("skript")
def skript(ctx, f: dict) -> FeatureErgebnis:
    datei = ctx.spec_pfad.parent / f["datei"]
    quelltext = datei.read_text(encoding="utf-8")
    befunde = pruefe_skript(quelltext)
    if befunde:
        raise BauFehler(SKRIPT_FEHLER, f"{datei.name}: {befunde[0]['meldung']} (Zeile {befunde[0]['zeile']})",
                        schritt="pruefung")
    namensraum: dict = {"__name__": f"swki_skript_{f['id']}"}
    exec(compile(quelltext, str(datei), "exec"), namensraum)  # nach statischer Prüfung erlaubt
    try:
        ergebnis = namensraum["bauen"](SkriptKontext(ctx, f["id"]))
    except BauFehler:
        raise
    except Exception as e:
        raise BauFehler(SKRIPT_FEHLER, f"{datei.name}: {type(e).__name__}: {e}", schritt="ausfuehren") from e
    features = ergebnis if isinstance(ergebnis, (list, tuple)) else [ergebnis]
    if not features or any(x is None for x in features):
        raise BauFehler(SKRIPT_FEHLER, f"{datei.name}: bauen(ctx) hat kein Feature zurückgegeben", schritt="ausfuehren")
    for i, feature in enumerate(features):
        feature.Name = f["id"] if i == 0 else f"{f['id']}_{i + 1}"
    return FeatureErgebnis(list(features))
