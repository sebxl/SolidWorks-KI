"""Attrappe der Mechanik-Schnittstelle (swki.baugruppe.bewegungslauf.Mechanik) für die Bewegungsprobe: der Schieber
verschiebt in x um den Hub, der Hebel fährt mit und dreht um +y um den Schwenk (Drehpunkt in x = Hub − 60, z = −10)."""

import math

from swki.baugruppe.bewegung import drehmatrix

EINS = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def transform(c, v=(0.0, 0.0, 0.0)) -> list[float]:
    """Transform2.ArrayData aus der Spaltenform c und einer Verschiebung in mm."""
    return [c[k % 3][k // 3] for k in range(9)] + [x / 1000 for x in v] + [1.0, 0.0, 0.0, 0.0]


def _hebelkiste(hub: float, schwenk: float) -> list[float]:
    a = math.radians(schwenk)
    c, s = math.cos(a), math.sin(a)
    ecken = [(c * x + s * z, -s * x + c * z) for x in (-7, 43) for z in (-6, 6)]
    xs = [hub - 60 + e[0] for e in ecken]
    zs = [-10 + e[1] for e in ecken]
    return [min(xs), 40.0, min(zs), max(xs), 48.0, max(zs)]


class Attrappe:
    def __init__(self, durchlass=(), kollision=None, fehler_bei=None, speicher=1000.0, loese_wirft=False,
                 interferenz_wirft=False, halte_wirft=False):
        self.werte = {"Hub": 0.0, "Schwenk": 0.0}
        self.grenzen = {"Hub": (0.0, 100.0), "Schwenk": (0.0, 90.0)}
        self.durchlass = set(durchlass)        # Bewegungen, deren Grenze im Modell nicht wirkt
        self.kollision = kollision or (lambda werte: [])
        self.fehler_bei = fehler_bei           # (Bewegung, Wert): dort meldet stelle() einen Fehler
        self.speicher = speicher
        self.loese_wirft = loese_wirft
        self.interferenz_wirft = interferenz_wirft
        self.halte_wirft = halte_wirft
        self.unterdrueckt: set[str] = set()    # Bewegungen, deren Grenzverknüpfung unterdrückt ist
        self.gehalten: set[str] = set()        # Bewegungen mit angelegtem Antrieb
        self.aufrufe: list[tuple] = []
        self.geloest: list[str] = []
        self.bilder: list[str] = []

    def halte(self, b, wert):
        self.aufrufe.append(("halte", b.name))
        if self.halte_wirft:
            raise RuntimeError("Antrieb kaputt")
        self.gehalten.add(b.name)
        self.werte[b.name] = wert

    def stelle(self, b, wert):
        unten, oben = self.grenzen[b.name]
        if self.fehler_bei == (b.name, wert):
            return "Rebuild-Fehler"
        if not unten - 1e-9 <= wert <= oben + 1e-9 and b.name not in self.durchlass:
            return "Verknüpfungsfehler: g"
        self.werte[b.name] = wert
        return None

    def loese(self, b):
        self.geloest.append(b.name)
        self.gehalten.discard(b.name)
        if self.loese_wirft:
            raise RuntimeError("Löschen kaputt")

    def unterdruecke(self, b, ja):
        self.aufrufe.append(("unterdruecke", b.name, ja))
        if ja:
            self.unterdrueckt.add(b.name)
        else:
            self.unterdrueckt.discard(b.name)

    def status(self):
        self.aufrufe.append(("status",))

        def frei(n):
            return n in self.unterdrueckt and n not in self.gehalten

        return {"platte": 3, "schieber": 2 if frei("Hub") else 3,
                "hebel": 2 if frei("Hub") or frei("Schwenk") else 3}

    def zustand(self):
        hub, schwenk = self.werte["Hub"], self.werte["Schwenk"]
        return {"platte": (transform(EINS), [-100.0, 0.0, -30.0, 100.0, 20.0, 30.0]),
                "schieber": (transform(EINS, (hub, 0, 0)), [hub - 100, 20.0, -30.0, hub - 40, 40.0, 10.0]),
                "hebel": (transform(drehmatrix((0, 1, 0), schwenk), (hub - 60, 0, -10)), _hebelkiste(hub, schwenk))}

    def interferenzen(self):
        if self.interferenz_wirft:
            raise RuntimeError("Kollision kaputt")
        return [{"paar": ["bolzen", "schieber"], "volumen": 1.0}] + self.kollision(self.werte)

    def bild(self, name):
        self.bilder.append(name)
        return f"{name}.png"

    def speicher_mb(self):
        return self.speicher
