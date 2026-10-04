"""Ablauf der Bewegungsprüfung (Spec 4a §8.2–§8.4) über eine Mechanik-Schnittstelle: Grenzen unterdrückt den Status
lesen, alle Bewegungen festhalten, je Bewegung ein Grundstellungslauf mit „Grenze wirkt“, Paarläufe, Bilder,
Speichergrenze, Aufräumen. Die SolidWorks-Umsetzung ist swki.baugruppe.sw_bewegung.SwMechanik; die Tests nutzen eine
Attrappe."""

import time
from typing import Protocol

from swki.baugruppe.bewegung import (TOL_WINKEL_GRAD, Bewegung, BewegungsMesswerte, Lauf, bewerte_bewegungen,
                                     ersatz_pruefungen, ist_bewegt, paare, soll_weg, vereinige, weg)
from swki.baugruppe.fehler import GRUNDSTELLUNG_FEHLER
from swki.cli import SwkiFehler
from swki.compiler.fehler import BauFehler

SPEICHER_KNAPP = "SPEICHER_KNAPP"


class SpeicherKnapp(SwkiFehler):
    """SolidWorks belegt mehr Private Bytes als speicher_grenze_mb (Spec 4a §8.4, Präzisierung 14)."""

    def __init__(self, privat_mb: float, grenze_mb: float):
        super().__init__(f"SolidWorks belegt {privat_mb:.0f} MB Private Bytes (Grenze {grenze_mb:.0f} MB) – SolidWorks "
                         "neu starten und swki pruefen erneut aufrufen")
        self.daten = {"code": SPEICHER_KNAPP, "privat_mb": round(privat_mb), "grenze_mb": grenze_mb}


class StellungFehler(SwkiFehler):
    """Eine Stellung, die gelingen muss (Grundstellung, Gegenstellung eines Paarlaufs), ließ sich nicht herstellen."""

    def __init__(self, bewegung: str, wert: float, meldung: str):
        super().__init__(f"Bewegung {bewegung}: Stellung {wert:g} nicht herstellbar ({meldung})")
        self.bewegung = bewegung
        self.daten = {"code": GRUNDSTELLUNG_FEHLER, "bewegung": bewegung, "stellung": wert}


class Mechanik(Protocol):
    def halte(self, b: Bewegung, wert: float) -> None:
        """Treibende Verknüpfung anlegen (falls nötig) und auf wert stellen; StellungFehler, wenn das misslingt."""

    def stelle(self, b: Bewegung, wert: float) -> str | None:
        """Wert setzen und neu aufbauen; None = gelöst, sonst die Meldung."""

    def loese(self, b: Bewegung) -> None:
        """Treibende Verknüpfung löschen (ohne Wirkung, wenn keine angelegt ist)."""

    def unterdruecke(self, b: Bewegung, ja: bool) -> None:
        """Grenzverknüpfung der Bewegung b unterdrücken (ja) bzw. wieder aktivieren und neu aufbauen."""

    def status(self) -> dict[str, int]:
        """Instanz-ID → GetConstrainedStatus."""

    def zustand(self) -> dict[str, tuple[list[float], list[float]]]:
        """Instanz-ID → (Transform2.ArrayData, Hüllquader in mm)."""

    def interferenzen(self) -> list[dict]:
        """Überlappungen {"paar": [Instanz-IDs], "volumen": mm³}."""

    def bild(self, name: str) -> str:
        """Iso-Bild der aktuellen Stellung; liefert den Pfad."""

    def speicher_mb(self) -> float:
        """Private Bytes des SolidWorks-Prozesses in MB."""


def _speicher(mech: Mechanik, grenze_mb: float) -> None:
    if (mb := mech.speicher_mb()) > grenze_mb:
        raise SpeicherKnapp(mb, grenze_mb)


def _zurueck(mech: Mechanik, b: Bewegung, wert: float) -> None:
    if (meldung := mech.stelle(b, wert)) is not None:
        raise StellungFehler(b.name, wert, meldung)


def _durchlauf(mech: Mechanik, b: Bewegung, gegen: dict[str, str], bekannt: set[frozenset], grund: bool) -> Lauf:
    """Fährt b von min bis max. Im Grundstellungslauf mit Lagen, bewegter Menge, Raum und drei Bildern; in jedem Lauf
    die Kollisionen, die nicht schon statisch bestanden (je Paar nur die erste Stellung, mit Bild)."""
    lauf = Lauf(b.name, dict(gegen))
    beginn = time.perf_counter()
    stellungen = b.stellungen()
    bilder_bei = {0: "min", b.schritte // 2: "mitte", len(stellungen) - 1: "max"} if grund else {}
    gemeldet: set[frozenset] = set()
    kisten: list[dict[str, list[float]]] = []
    for i, w in enumerate(stellungen):
        if (meldung := mech.stelle(b, w)) is not None:
            lauf.fehler = {"stellung": round(w, 6), "meldung": meldung}
            break
        lauf.stellungen.append(round(w, 6))
        if grund:
            z = mech.zustand()
            lauf.lagen.append({k: t for k, (t, _) in z.items()})
            kisten.append({k: kiste for k, (_, kiste) in z.items()})
            erste = lauf.lagen[0]
            lauf.bewegt += [k for k, t in lauf.lagen[-1].items()
                            if k not in lauf.bewegt and k in erste and ist_bewegt(erste[k], t)]
        for kollision in mech.interferenzen():
            paar = frozenset(kollision["paar"])
            if paar in bekannt or paar in gemeldet:
                continue
            gemeldet.add(paar)
            name = "-".join([b.name, "kollision", *gegen, str(len(lauf.kollisionen) + 1)])
            lauf.kollisionen.append({"paar": sorted(paar), "volumen": kollision["volumen"], "stellung": round(w, 6),
                                     "gegen": dict(gegen), "bild": mech.bild(name)})
        if i in bilder_bei:
            lauf.bilder[bilder_bei[i]] = mech.bild(f"{b.name}-{bilder_bei[i]}")
    for k in lauf.bewegt:
        for schritt in kisten:
            if k in schritt:
                lauf.raum = vereinige(lauf.raum, schritt[k])
    lauf.dauer_s = round(time.perf_counter() - beginn, 3)
    return lauf


def _grenze_geht(mech: Mechanik, b: Bewegung, wert: float, start: list[float], tol_mm: float) -> bool:
    """True, wenn der Schritt auf wert (außerhalb der Grenze) durchgeht: gelöst und die bewegte Komponente am Sollweg
    (Präzisierung 4)."""
    if mech.stelle(b, wert) is not None:
        return False
    lage = mech.zustand().get(b.komponente)
    if lage is None:
        return False
    tol = tol_mm if b.art == "abstand" else TOL_WINKEL_GRAD
    return abs(weg(b, start, lage[0]) - soll_weg(b, wert)) <= tol


def fahre(mech: Mechanik, bws: list[Bewegung], bekannt: set[frozenset], grenze_mb: float,
          tol_mm: float) -> BewegungsMesswerte:
    """Zuerst die Grenzen der Bewegungen unterdrücken und den Status lesen (eine Grenzverknüpfung zählt sonst als
    Bindung, Spike S13b), dann alle Bewegungen auf min festhalten und den Status erneut lesen, die Grenzen wieder
    aktivieren; je Bewegung ein Grundstellungslauf mit „Grenze wirkt“, dann die Paarläufe (die andere Bewegung auf
    max). Unterdrückte Grenzen werden immer wieder aktiviert, die treibenden Verknüpfungen immer gelöscht; ein Fehler
    beim Aufräumen verdeckt die Ursache nicht."""
    unterdrueckt: list[Bewegung] = []
    try:
        for b in bws:
            mech.unterdruecke(b, True)
            unterdrueckt.append(b)
        frei = mech.status()
        for b in bws:
            mech.halte(b, b.min)
        gehalten = mech.status()
        for b in reversed(bws):
            mech.unterdruecke(b, False)
            unterdrueckt.remove(b)
        laeufe: list[Lauf] = []
        grund: dict[str, Lauf] = {}
        for b in bws:
            _speicher(mech, grenze_mb)
            lauf = _durchlauf(mech, b, {}, bekannt, True)
            if lauf.fehler is None:
                start = lauf.lagen[0][b.komponente]
                lauf.grenze["oben"] = _grenze_geht(mech, b, b.max + b.schrittweite / 2, start, tol_mm)
                _zurueck(mech, b, b.min)
                lauf.grenze["unten"] = (None if b.min == 0
                                        else _grenze_geht(mech, b, b.min - b.schrittweite / 2, start, tol_mm))
            _zurueck(mech, b, b.min)
            laeufe.append(lauf)
            grund[b.name] = lauf
        gefunden = paare(bws, grund)
        for b1, b2, _ in gefunden:
            for x, y in ((b1, b2), (b2, b1)):
                if grund[x.name].fehler is not None or grund[y.name].fehler is not None:
                    continue
                _speicher(mech, grenze_mb)
                _zurueck(mech, y, y.max)
                laeufe.append(_durchlauf(mech, x, {y.name: "max"}, bekannt, False))
                _zurueck(mech, x, x.min)
                _zurueck(mech, y, y.min)
        return BewegungsMesswerte(frei, gehalten, laeufe,
                                  [{"bewegungen": [a.name, c.name], "schnitt": [round(v, 3) for v in s]}
                                   for a, c, s in gefunden])
    finally:
        for b in reversed(unterdrueckt):
            try:
                mech.unterdruecke(b, False)
            except Exception:
                pass  # Aufräumfehler verdecken die Ursache nicht
        for b in reversed(bws):
            try:
                mech.loese(b)
            except Exception:
                pass  # Aufräumfehler verdecken die Ursache nicht (Muster aus dem Aufräumen nach 3b)


def _statisch_fehlerhaft(messwerte) -> bool:
    """Rebuildfehler oder eine Verknüpfung mit Fehlercode ≠ 0 in den statischen Messwerten (die Felder, aus denen die
    Mängel rebuild und verknuepfungen entstehen)."""
    return bool(messwerte.rebuild_fehler) or any(messwerte.verknuepfungen.values())


def bewegungen_oder_ersatz(spec: dict, bws: list[Bewegung], messwerte, mech_fabrik, bekannt: set[frozenset],
                           grenze_mb: float, tol_mm: float) -> tuple[list[dict], dict, list[Lauf]]:
    """Bewegungsprüfung oder, wo sie nicht laufen kann, Mängel statt Abbruch (Spec 4a §8.2.3). Liefert Prüfungen,
    Bewegungsbericht und die Läufe (für die Bilder). mech_fabrik erzeugt die Mechanik erst, wenn gefahren wird.
    - Statische Fehler (rebuild, verknuepfungen): nicht fahren, je Bewegung bewegung:<name> mit ok=None.
    - StellungFehler/BauFehler aus fahre (nach dessen Aufräumen): bewegung:<name> mit ok=False; bei StellungFehler nur
      für die betroffene Bewegung (übrige ok=None), bei BauFehler ohne Bewegungsbezug für alle.
    - SpeicherKnapp bleibt ein Abbruch ohne Prüfbericht (Präzisierung 14)."""
    if _statisch_fehlerhaft(messwerte):
        pruefungen, bericht = ersatz_pruefungen(
            bws, "Bewegungsprüfung nicht gefahren: statische Fehler (siehe rebuild/verknuepfungen)")
        return pruefungen, bericht, []
    try:
        m = fahre(mech_fabrik(), bws, bekannt, grenze_mb, tol_mm)
    except StellungFehler as e:
        pruefungen, bericht = ersatz_pruefungen(bws, "nicht geprüft (Bewegungsprüfung abgebrochen)", {e.bewegung: str(e)})
        return pruefungen, bericht, []
    except BauFehler as e:
        pruefungen, bericht = ersatz_pruefungen(bws, "", {b.name: f"Abbruch der Bewegungsprüfung: {e}" for b in bws})
        return pruefungen, bericht, []
    pruefungen, bericht = bewerte_bewegungen(spec, bws, m, tol_mm)
    return pruefungen, bericht, m.laeufe
