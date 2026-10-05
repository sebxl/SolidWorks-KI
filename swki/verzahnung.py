"""Evolventenverzahnung (Spec 4b §4.2): geradverzahntes Außen-Stirnrad und Zahnstange mit dem Bezugsprofil DIN 867
(α = 20°, Kopfhöhe m, Fußhöhe 1,25 m, Fußrundung 0,38 m), ohne Profilverschiebung. Reine Geometrie ohne SolidWorks:
Kreise, Zahnweite, Profil als Konturen aus Linien, Bögen und Splines, Profilfläche, Lage der Flanken.

Längen in mm, Winkel im Bogenmaß (Ausnahme: `winkel` der Spec in Grad). Koordinaten (u, v) wie die Skizzen des
Compilers (swki.compiler.skizze). Die Trochoide des Fußes wird vereinfacht: unter dem Grundkreis läuft die Flanke radial
weiter, die Fußrundung ρ_f berührt die radiale Verlängerung und den Fußkreis (Präzisierung 3 des Plans)."""

import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

ALPHA = math.radians(20.0)                           # Eingriffswinkel des Bezugsprofils (DIN 867)
KOPFHOEHE, FUSSHOEHE, FUSSRUNDUNG = 1.0, 1.25, 0.38  # × Modul (DIN 867)
Z_MIN = 17                                           # unterschnittfrei ohne Profilverschiebung
FLANKENPUNKTE = 10                                   # Stützpunkte je Evolventenflanke (Spike S14a Zeile 1)
FLAECHE_PUNKTE = 200                                 # Stützpunkte je Flanke für die Profilfläche
_MODULE = Path(__file__).parent / "wissen" / "module_din780.yaml"

Punkt = tuple[float, float]


class VerzahnungFehler(ValueError):
    """Das Profil lässt sich mit diesen Werten nicht konstruieren (z. B. keine Fußlücke, Zahn spitz)."""


@dataclass(frozen=True)
class Linie:
    a: Punkt
    b: Punkt


@dataclass(frozen=True)
class Bogen:
    mitte: Punkt
    a: Punkt
    b: Punkt
    gegen_uhrzeigersinn: bool  # von a nach b in (u, v)


@dataclass(frozen=True)
class Spline:
    punkte: tuple[Punkt, ...]  # durch alle Punkte, von punkte[0] nach punkte[-1]


Segment = Linie | Bogen | Spline


def inv(a: float) -> float:
    """Evolventenfunktion inv α = tan α − α."""
    return math.tan(a) - a


@cache
def genormte_module() -> tuple[float, ...]:
    """Modulreihe 1 nach DIN 780 (swki/wissen/module_din780.yaml)."""
    return tuple(float(m) for m in yaml.safe_load(_MODULE.read_text(encoding="utf-8"))["reihe_1"])


def ist_genormt(m: float) -> bool:
    return any(abs(m - n) < 1e-9 for n in genormte_module())


def _polar(mitte: Punkt, r: float, phi: float) -> Punkt:
    return (mitte[0] + r * math.cos(phi), mitte[1] + r * math.sin(phi))


def _gegen_uhrzeigersinn(mitte: Punkt, a: Punkt, b: Punkt) -> bool:
    """Drehsinn des kürzeren Bogens von a nach b um mitte (Bögen der Profile sind < 180°)."""
    return (a[0] - mitte[0]) * (b[1] - mitte[1]) - (a[1] - mitte[1]) * (b[0] - mitte[0]) > 0


def _bogen(mitte: Punkt, a: Punkt, b: Punkt) -> Bogen:
    return Bogen(mitte, a, b, _gegen_uhrzeigersinn(mitte, a, b))


@dataclass(frozen=True)
class Stirnrad:
    """Geradverzahntes Außen-Stirnrad: Modul m, Zähnezahl z, Zahndickenabmaß abmass (mm, < 0 für Flankenspiel)."""
    m: float
    z: int
    abmass: float = 0.0

    @property
    def r(self) -> float:
        return self.m * self.z / 2

    @property
    def rb(self) -> float:
        return self.r * math.cos(ALPHA)

    @property
    def ra(self) -> float:
        return self.r + KOPFHOEHE * self.m

    @property
    def rf(self) -> float:
        return self.r - FUSSHOEHE * self.m

    @property
    def rho(self) -> float:
        return FUSSRUNDUNG * self.m

    @property
    def tau(self) -> float:
        """Teilungswinkel 2π/z."""
        return 2 * math.pi / self.z

    @property
    def s(self) -> float:
        """Zahndicke am Teilkreis (Bogen) mit Abmaß."""
        return math.pi * self.m / 2 + self.abmass

    @property
    def r_beruehr(self) -> float:
        """Radius, an dem die Fußrundung die radiale Flankenverlängerung berührt."""
        return math.sqrt(self.rf ** 2 + 2 * self.rf * self.rho)

    @property
    def r_start(self) -> float:
        """Beginn der Evolvente: Grundkreis oder, wenn die Fußrundung höher reicht, deren Berührradius."""
        return max(self.rb, self.r_beruehr)

    def psi(self, rho: float) -> float:
        """Halber Zahndickenwinkel am Radius rho ≥ rb (Winkel von der Zahnmitte zur Flanke)."""
        return self.s / (2 * self.r) + inv(ALPHA) - inv(math.acos(self.rb / rho))

    @property
    def delta(self) -> float:
        """Winkel zwischen der radialen Flankenverlängerung und dem Mittelpunkt der Fußrundung."""
        return math.asin(self.rho / (self.rf + self.rho))

    def pruefe(self) -> None:
        """VerzahnungFehler, wenn das vereinfachte Profil nicht konstruierbar ist."""
        if self.z < 1 or self.m <= 0:
            raise VerzahnungFehler(f"Modul {self.m:g} und Zähnezahl {self.z} ergeben kein Rad")
        if self.r_start >= self.ra:
            raise VerzahnungFehler("die Fußrundung reicht bis an den Kopfkreis")
        if self.psi(self.ra) <= 0:
            raise VerzahnungFehler("der Zahn wird spitz (Kopfdicke ≤ 0)")
        if self.tau - 2 * (self.psi(self.r_start) + self.delta) <= 0:
            raise VerzahnungFehler("zwischen den Fußrundungen bleibt kein Fußkreis (Lücke zu eng)")

    def messzaehnezahl(self) -> int:
        """Messzähnezahl k = round(z·α/π + 0,5) (α im Bogenmaß)."""
        return max(1, round(self.z * ALPHA / math.pi + 0.5))

    def zahnweite(self) -> float:
        """Zahnweite W_k = m·cos α·[π·(k − 0,5) + z·inv α] + A_s·cos α."""
        k = self.messzaehnezahl()
        return self.m * math.cos(ALPHA) * (math.pi * (k - 0.5) + self.z * inv(ALPHA)) + self.abmass * math.cos(ALPHA)

    def zahnmitte(self, j: int, winkel: float = 0.0) -> float:
        """Winkel der Mitte von Zahn j (1 …) gegen +u; winkel = Lage von Zahn 1 in Grad."""
        return math.radians(winkel) + (j - 1) * self.tau

    def flankenpunkt(self, j: int, seite: str, rho: float, mitte: Punkt = (0.0, 0.0), winkel: float = 0.0) -> Punkt:
        """Punkt der Flanke von Zahn j am Radius rho; seite "links" (gegen den Uhrzeigersinn) bzw. "rechts"."""
        phi = self.zahnmitte(j, winkel) + (1 if seite == "links" else -1) * self.psi(rho)
        return _polar(mitte, rho, phi)

    def _flanke(self, theta: float, vorzeichen: int, mitte: Punkt, n: int) -> list[Punkt]:
        """Flanke von r_start bis ra (Wälzwinkel gleichmäßig verteilt); vorzeichen +1 links, −1 rechts."""
        t0 = math.sqrt(max((self.r_start / self.rb) ** 2 - 1, 0.0))
        t1 = math.sqrt((self.ra / self.rb) ** 2 - 1)
        punkte = []
        for i in range(n):
            rho = self.rb * math.sqrt(1 + (t0 + (t1 - t0) * i / (n - 1)) ** 2)
            punkte.append(_polar(mitte, rho, theta + vorzeichen * self.psi(rho)))
        return punkte

    def profil(self, mitte: Punkt = (0.0, 0.0), winkel: float = 0.0, n: int = FLANKENPUNKTE) -> list[list[Segment]]:
        """Eine geschlossene Kontur gegen den Uhrzeigersinn: je Zahn rechte Fußrundung, radiale Verlängerung (falls
        die Evolvente am Grundkreis beginnt), rechte Flanke, Kopfbogen, linke Flanke, Verlängerung, linke Fußrundung,
        Fußbogen bis zum nächsten Zahn."""
        self.pruefe()
        ps, d = self.psi(self.r_start), self.delta
        kontur: list[Segment] = []
        for j in range(1, self.z + 1):
            th = self.zahnmitte(j, winkel)
            th_naechst = self.zahnmitte(j + 1, winkel)
            # rechte Seite (im Uhrzeigersinn neben der Zahnmitte), von unten nach oben
            c_r = _polar(mitte, self.rf + self.rho, th - ps - d)
            t2_r, t1_r = _polar(mitte, self.rf, th - ps - d), _polar(mitte, self.r_beruehr, th - ps)
            kontur.append(_bogen(c_r, t2_r, t1_r))
            if self.r_start > self.r_beruehr + 1e-9:
                kontur.append(Linie(t1_r, _polar(mitte, self.r_start, th - ps)))
            rechts = self._flanke(th, -1, mitte, n)
            kontur.append(Spline(tuple(rechts)))
            links = self._flanke(th, 1, mitte, n)
            kontur.append(_bogen(mitte, rechts[-1], links[-1]))
            kontur.append(Spline(tuple(reversed(links))))
            t1_l = _polar(mitte, self.r_beruehr, th + ps)
            if self.r_start > self.r_beruehr + 1e-9:
                kontur.append(Linie(_polar(mitte, self.r_start, th + ps), t1_l))
            c_l = _polar(mitte, self.rf + self.rho, th + ps + d)
            t2_l = _polar(mitte, self.rf, th + ps + d)
            kontur.append(_bogen(c_l, t1_l, t2_l))
            kontur.append(_bogen(mitte, t2_l, _polar(mitte, self.rf, th_naechst - ps - d)))
        return [kontur]

    def flaeche(self) -> float:
        """Profilfläche (mm²), aus der Kontur mit fein abgetasteten Flanken."""
        return sum(_flaeche(k) for k in self.profil(n=FLAECHE_PUNKTE))


@dataclass(frozen=True)
class Zahnstange:
    """Zahnstange mit dem Bezugsprofil: Modul m, Zähnezahl z, Zahndickenabmaß abmass (mm)."""
    m: float
    z: int
    abmass: float = 0.0

    @property
    def p(self) -> float:
        return math.pi * self.m

    @property
    def s(self) -> float:
        """Zahndicke auf der Profilmittellinie mit Abmaß."""
        return self.p / 2 + self.abmass

    @property
    def rho(self) -> float:
        return FUSSRUNDUNG * self.m

    def _fussrundung(self, uc: float, seite: int) -> tuple[Punkt, Punkt, Punkt]:
        """(Mittelpunkt, Berührpunkt Flanke, Berührpunkt Fußlinie) der Fußrundung links (seite −1) bzw. rechts (+1)
        von Zahn mit Mitte uc; Profilmittellinie v = 0, Kopf nach +v."""
        hf, rho = FUSSHOEHE * self.m, self.rho
        cy = -hf + rho
        cx = uc + seite * (self.s / 2 + (rho - cy * math.sin(ALPHA)) / math.cos(ALPHA))
        n = (seite * math.cos(ALPHA), math.sin(ALPHA))  # Normale der Flanke aus dem Zahn heraus
        return (cx, cy), (cx - rho * n[0], cy - rho * n[1]), (cx, -hf)

    def pruefe(self) -> None:
        if self.z < 1 or self.m <= 0:
            raise VerzahnungFehler(f"Modul {self.m:g} und Zähnezahl {self.z} ergeben keine Zahnstange")
        if self.s / 2 - KOPFHOEHE * self.m * math.tan(ALPHA) <= 0:
            raise VerzahnungFehler("der Zahn wird spitz (Kopfdicke ≤ 0)")
        breite_fuss = self._fussrundung(0.0, 1)[2][0] - self._fussrundung(0.0, -1)[2][0]
        if breite_fuss >= self.p:
            raise VerzahnungFehler("zwischen den Fußrundungen bleibt keine Fußlinie (Lücke zu eng)")

    def zahnmitte(self, j: int, u0: float = 0.0) -> float:
        return u0 + (j - 1) * self.p

    def profil(self, mitte: Punkt = (0.0, 0.0), kopf: str = "+v") -> list[list[Segment]]:
        """Je Zahn eine geschlossene Kontur (Zahnband ohne Rücken, Spec 4b §4.2): Fußlinie unter dem Zahn, rechte
        Fußrundung, rechte Flanke, Kopflinie, linke Flanke, linke Fußrundung. Die Fußlinien zwischen den Zähnen gehören
        zum Rücken (Präzisierung 4 des Plans). kopf "-v" spiegelt an der Profilmittellinie."""
        self.pruefe()
        u0, v0 = mitte
        vz = 1.0 if kopf == "+v" else -1.0
        ha, tan_a = KOPFHOEHE * self.m, math.tan(ALPHA)

        def p(q: Punkt) -> Punkt:
            return (q[0], v0 + vz * q[1])

        def bogen(c: Punkt, a: Punkt, b: Punkt) -> Bogen:
            return _bogen(p(c), p(a), p(b))

        konturen = []
        for j in range(1, self.z + 1):
            uc = self.zahnmitte(j, u0)
            c_l, t1_l, t2_l = self._fussrundung(uc, -1)
            c_r, t1_r, t2_r = self._fussrundung(uc, 1)
            kopf_r, kopf_l = (uc + self.s / 2 - ha * tan_a, ha), (uc - self.s / 2 + ha * tan_a, ha)
            konturen.append([Linie(p(t2_l), p(t2_r)), bogen(c_r, t2_r, t1_r), Linie(p(t1_r), p(kopf_r)),
                             Linie(p(kopf_r), p(kopf_l)), Linie(p(kopf_l), p(t1_l)), bogen(c_l, t1_l, t2_l)])
        return konturen

    def flankenmitte(self, j: int, seite: str, u0: float = 0.0) -> float:
        """u des Schnittpunkts der Flanke von Zahn j mit der Profilmittellinie."""
        return self.zahnmitte(j, u0) + (-1 if seite == "links" else 1) * self.s / 2

    def flaeche(self) -> float:
        return sum(_flaeche(k) for k in self.profil())


def _flaeche(kontur: list[Segment]) -> float:
    """Betrag der Fläche einer geschlossenen Kontur (Gaußsche Formel; Bögen exakt über das Kreissegment)."""
    summe = 0.0
    for s in kontur:
        if isinstance(s, Spline):
            pts = s.punkte
        else:
            pts = (s.a, s.b)
        summe += sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:]))
        if isinstance(s, Bogen):
            r = math.dist(s.mitte, s.a)
            sehne = math.dist(s.a, s.b)
            w = 2 * math.asin(min(1.0, sehne / (2 * r)))
            segment = r * r * (w - math.sin(w)) / 2
            summe += 2 * segment if s.gegen_uhrzeigersinn else -2 * segment
    return abs(summe) / 2


def aus_feature(f: dict, parameter: dict) -> Stirnrad | Zahnstange:
    """Geometrie eines verzahnung-Features der Spec (Werte ausgewertet; zaehne gerundet, validieren prüft Ganzzahl)."""
    from swki.spec.ausdruck import auswerten

    m, z = auswerten(f["modul"], parameter), round(auswerten(f["zaehne"], parameter))
    abmass = auswerten(f["zahndickenabmass"], parameter)
    return Stirnrad(m, z, abmass) if f["art"] == "stirnrad" else Zahnstange(m, z, abmass)


Vektor = tuple[float, float, float]
# Skizzenachsen (u, v) und Normale der Standardebenen wie swki.compiler.skizze.modellpunkt:
# vorne (u, v, lage), oben (u, lage, −v), rechts (lage, v, −u)
_ACHSEN: dict[str, tuple[Vektor, Vektor, Vektor]] = {
    "vorne": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    "oben": ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
    "rechts": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
}


def _plus(a: Vektor, b: Vektor, f: float = 1.0) -> Vektor:
    return (a[0] + f * b[0], a[1] + f * b[1], a[2] + f * b[2])


def _mal(a: Vektor, f: float) -> Vektor:
    return (a[0] * f, a[1] * f, a[2] * f)


@dataclass(frozen=True)
class Verzahnung:
    """Ein verzahnung-Feature im Teil (Teilkoordinaten, mm): Geometrie, Skizzenebene und Bezug (Spec 4b §4.2)."""
    id: str
    geo: Stirnrad | Zahnstange
    mitte: Punkt          # (u, v) aus der Spec
    winkel: float         # Grad, Lage von Zahn 1 (Stirnrad)
    kopf: str             # "+v" | "-v" (Zahnstange)
    ursprung: Vektor      # Ursprung der Skizzenebene
    u: Vektor
    v: Vektor
    normale: Vektor       # Normale der Skizzenebene; die Extrusion läuft in Richtung normale·(−1 bei umkehren)
    breite: tuple[float, float]  # Bereich der Zahnbreite entlang normale (Skalarprodukt mit normale)

    def modell(self, q: Punkt) -> Vektor:
        """Skizzenpunkt (u, v) → Teilkoordinaten."""
        return _plus(_plus(self.ursprung, self.u, q[0]), self.v, q[1])

    def richtung(self, q: Punkt) -> Vektor:
        """Skizzenrichtung (u, v) → Teilkoordinaten."""
        return _plus(_mal(self.u, q[0]), self.v, q[1])

    @property
    def bezugspunkt(self) -> Vektor:
        """Stirnrad: Radachse in der Skizzenebene; Zahnstange: Mitte von Zahn 1 auf der Profilmittellinie."""
        return self.modell(self.mitte)

    @property
    def zahnrichtung(self) -> Vektor:
        """Stirnrad: von der Achse zur Mitte von Zahn 1; Zahnstange: Richtung der Zahnreihe (+u)."""
        if isinstance(self.geo, Zahnstange):
            return self.u
        w = math.radians(self.winkel)
        return self.richtung((math.cos(w), math.sin(w)))

    @property
    def kopfrichtung(self) -> Vektor:
        """Zahnstange: Richtung, in die die Zähne zeigen."""
        return self.v if self.kopf == "+v" else _mal(self.v, -1.0)


def verzahnung_im_teil(f: dict, parameter: dict) -> Verzahnung:
    """Lage eines verzahnung-Features aus der Spec (ebene nur Standardebene oder versatz, Spec 4b §4.1)."""
    from swki.spec.ausdruck import auswerten

    ebene = f["ebene"]
    if isinstance(ebene, str):
        orientierung, lage = ebene, 0.0
    else:
        orientierung, lage = ebene["versatz"]["ebene"], auswerten(ebene["versatz"]["abstand"], parameter)
    u, v, n = _ACHSEN[orientierung]
    mitte = (auswerten(f["mitte"][0], parameter), auswerten(f["mitte"][1], parameter))
    b = auswerten(f["breite"], parameter) * (-1.0 if f.get("umkehren") else 1.0)
    return Verzahnung(f["id"], aus_feature(f, parameter), mitte, auswerten(f.get("winkel", 0), parameter),
                      f.get("kopf", "+v"), _mal(n, lage), u, v, n, (min(lage, lage + b), max(lage, lage + b)))
