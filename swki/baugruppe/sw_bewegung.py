"""SolidWorks-Mechanik der Bewegungsprüfung (Spec 4a §8.2): treibende Verknüpfungen anlegen, stellen und löschen, Lage,
Hüllquader und Bestimmtheit der Komponenten lesen, Kollision, Iso-Bilder, Private Bytes. Erfüllt
swki.baugruppe.bewegungslauf.Mechanik."""

from pathlib import Path

from swki.baugruppe import sw_baugruppe
from swki.baugruppe.bewegung import Bewegung
from swki.baugruppe.bewegungslauf import StellungFehler
from swki.compiler import sw
from swki.pruefung.bilder import iso_bild
from swki.speicher import privat_mb
from swki.verbindung import in_mm


class SwMechanik:
    def __init__(self, app, asm, grenzen: dict, entitaet, komponenten: dict, bilder: Path | None = None):
        self.app, self.asm = app, asm
        self.grenzen = grenzen              # Verknüpfungs-ID → Verknuepfung (Grenzverknüpfungen)
        self.entitaet = entitaet            # Referenz der Spec → Entität im Baugruppenkontext
        self.komponenten = komponenten      # Instanz-ID → IComponent2
        self.bilder = bilder
        self.antriebe: dict[str, object] = {}  # Bewegung → treibende Verknüpfung
        self._namen = {k.Name2: iid for iid, k in komponenten.items()}
        self._teileboxen: dict[str, list[float] | None] = {}  # Instanz-ID → Teilebox (mm), beim 1. zustand() gelesen

    def halte(self, b: Bewegung, wert: float) -> None:
        if b.name not in self.antriebe:
            v = self.grenzen[b.grenze]
            self.antriebe[b.name] = sw_baugruppe.treibe(self.asm, v, self.entitaet(v.a), self.entitaet(v.b), wert)
        if (meldung := self.stelle(b, wert)) is not None:
            raise StellungFehler(b.name, wert, meldung)

    def stelle(self, b: Bewegung, wert: float) -> str | None:
        return sw_baugruppe.stelle(self.asm, self.antriebe[b.name], b.art, wert)

    def loese(self, b: Bewegung) -> None:
        if (antrieb := self.antriebe.pop(b.name, None)) is not None:
            sw_baugruppe.loesche(self.asm, antrieb)

    def unterdruecke(self, b: Bewegung, ja: bool) -> None:
        namen = {f.Name.lower(): f for f in sw_baugruppe.verknuepfungen(self.asm)}
        sw_baugruppe.unterdruecke(self.asm, namen[b.grenze.lower()], ja)

    def status(self) -> dict[str, int]:
        return {iid: sw_baugruppe.status(k) for iid, k in self.komponenten.items()}

    def _teilebox(self, iid: str, komp) -> list[float] | None:
        """Teilebox der Komponente in mm, je Instanz einmal gelesen (Spike S13 Zeile 6/8: GetBox je Schritt ist teuer);
        None, wenn das Teildokument nicht geladen ist (GetModelDoc2 liefert dann nichts)."""
        if iid not in self._teileboxen:
            model = komp.GetModelDoc2
            self._teileboxen[iid] = sw.teilebox_mm(model) if model is not None else None
        return self._teileboxen[iid]

    def zustand(self) -> dict[str, tuple[list[float], list[float]]]:
        ergebnis = {}
        for iid, k in self.komponenten.items():
            t = sw_baugruppe.transform(k)
            teilebox = self._teilebox(iid, k)
            kiste = ([in_mm(x) for x in k.GetBox(False, False)] if teilebox is None
                     else sw_baugruppe.kiste(t, teilebox))
            ergebnis[iid] = (t, kiste)
        return ergebnis

    def interferenzen(self) -> list[dict]:
        return [{"paar": sorted(self._namen.get(n, n) for n in paar), "volumen": round(volumen, 3)}
                for paar, volumen in sw_baugruppe.interferenzen(self.asm)]

    def bild(self, name: str) -> str:
        return "" if self.bilder is None else iso_bild(self.app, self.asm, self.bilder / f"{name}.png")

    def speicher_mb(self) -> float:
        return privat_mb(int(self.app.GetProcessID))
