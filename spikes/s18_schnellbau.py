"""S18 (Spike S-Schleife-1, docs/entscheidungen/2026-10-25-schnelle-konstruktionsschleife.md §7): Schnellbau – eine
swki-Teil-Spec ohne SolidWorks mit build123d/OCP (OpenCascade) bauen, als exakte B-Rep.

Dieselbe Semantik wie der SolidWorks-Compiler, soweit die Features hier vorkommen: Skizzenebenen (Standardebene,
versetzte Ebene, Fläche eines Features), (u, v) → Modellpunkt über swki.compiler.skizze.modellpunkt, Elemente rechteck
(mit radius), kreis, polygon (mit radien), kontur (linie/bogen, Bögen gegen den Uhrzeigersinn in (u, v)), langloch;
extrusion/schnitt mit blind, mittig, durch_alles, bis_flaeche, versatz_von_flaeche und umkehren; verrundung und fase an
Kanten {nahe: [x, y, z]}; bohrung (mit Flachsenkung) und normbohrung mit den Maßen aus swki/wissen/bohrungsnormen.yaml
(dieselbe Tabelle wie der Handler; Gewinde kosmetisch → Kernloch, blind mit Bohrspitze 118°). Mit bohrungen=False
werden Bohrungen übersprungen (Kollisionsgeometrie der Simulation), ihre Achsen aber trotzdem gemerkt (Verknüpfungen).
Alles andere (rotation, muster, spiegeln, verzahnung, skript, formschraege) → NichtUnterstuetzt.

Flächenanker {feature, flaeche: "+y"}: Ebene der am weitesten in Richtung liegenden Fläche des Werkzeugkörpers des
Features (Aufsatz: Normale = Richtung, Schnitt: Normale = −Richtung, weil der Schnitt die Fläche umgekehrt erzeugt).
Das entspricht swki.compiler.topologie.loese_flaeche für die Lage der Ebene; die Ausdehnung der Fläche wird nicht
gebraucht (Bezüge bemaßen nur, sie verschieben nichts).

Längen in mm, Teilkoordinaten wie in SolidWorks.

Aufruf (Einzeltest): .venv-sim\\Scripts\\python.exe -m spikes.s18_schnellbau <teil.yaml> [NAME=wert ...]
"""

import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from build123d import Edge, Face, Solid, Vector, Wire

from swki.compiler.anker import RICHTUNGEN
from swki.compiler.skizze import NORMALE, modellpunkt, orientierung_der_normale
from swki.spec.ausdruck import auswerten
from swki.spec.normen import bohrspitze_grad, normmasse

ACHSE = {"rechts": 0, "oben": 1, "vorne": 2}
DURCH_ALLES_MM = 5000.0
TOL_ANKER_MM = 0.1   # config/standard.yaml toleranzen.anker_mm
BOHRUNGEN = ("bohrung", "normbohrung")


class NichtUnterstuetzt(Exception):
    pass


@dataclass
class Ebene:
    orientierung: str
    lage: float
    normale: tuple


@dataclass
class FeatureInfo:
    typ: str
    werkzeug: Solid | None = None
    richtung: tuple | None = None
    punkte: list | None = None      # Bohrungen: Achspunkte auf der Ansatzfläche (Instanz 1, 2, …), richtung = ins Material


@dataclass
class Teil:
    name: str
    solid: Solid
    parameter: dict
    features: dict = field(default_factory=dict)
    uebersprungen: list = field(default_factory=list)
    sekunden: float = 0.0


def _v(p) -> Vector:
    return Vector(*p)


def _ebene_bei(p: Vector, normale: Vector):
    from build123d import Plane
    return Plane(origin=p, z_dir=normale)


class Schnellbau:
    def __init__(self, spec: dict, parameter: dict | None = None, name: str | None = None, bohrungen: bool = True):
        self.spec = spec
        self.mit_bohrungen = bohrungen
        self.p = {k: auswerten(v, spec.get("parameter", {})) for k, v in spec.get("parameter", {}).items()}
        self.p.update(parameter or {})
        self.name = name or spec.get("name", "teil")
        self.body: Solid | None = None
        self.features: dict[str, FeatureInfo] = {}
        self.uebersprungen: list[str] = []

    def w(self, x) -> float:
        return auswerten(x, self.p)

    # --- Ebenen ---------------------------------------------------------------------------------------------------
    def ebene(self, e) -> Ebene:
        if isinstance(e, str):
            return Ebene(e, 0.0, NORMALE[e])
        if "versatz" in e:
            basis = e["versatz"]["ebene"]
            return Ebene(basis, self.w(e["versatz"]["abstand"]), NORMALE[basis])
        return self.flaechenebene(e)

    def flaechenebene(self, anker: dict) -> Ebene:
        if "nahe" in anker:
            raise NichtUnterstuetzt("Flächenanker nahe")
        info = self.features[anker["feature"]]
        if info.werkzeug is None:
            raise NichtUnterstuetzt(f"Feature {anker['feature']} hat keinen Werkzeugkörper")
        richt = RICHTUNGEN[anker["flaeche"]]
        such = richt if info.typ != "schnitt" else tuple(-c for c in richt)
        kandidaten = []
        for f in info.werkzeug.faces():
            if f.geom_type.name != "PLANE":
                continue
            n = f.normal_at()
            if n.X * such[0] + n.Y * such[1] + n.Z * such[2] > 1 - 1e-6:
                c = f.center()
                kandidaten.append(c.X * richt[0] + c.Y * richt[1] + c.Z * richt[2])
        if not kandidaten:
            raise NichtUnterstuetzt(f"keine Fläche {anker['flaeche']} an {anker['feature']}")
        orient = orientierung_der_normale(richt)
        # Lage = Koordinate auf der Normalenachse (mit Vorzeichen der Achse, nicht der Richtung)
        lage = max(kandidaten) * (richt[ACHSE[orient]])
        return Ebene(orient, lage, richt)

    # --- Skizzen --------------------------------------------------------------------------------------------------
    def punkt(self, se: Ebene, u: float, v: float) -> Vector:
        return _v(modellpunkt(se.orientierung, u, v, se.lage))

    def _bogen(self, se, a, b, c) -> Edge:
        """Bogen gegen den Uhrzeigersinn in (u, v) von a nach b um c."""
        r = math.dist(a, c)
        a1 = math.atan2(a[1] - c[1], a[0] - c[0])
        a2 = math.atan2(b[1] - c[1], b[0] - c[0])
        if a2 <= a1 + 1e-12:
            a2 += 2 * math.pi
        am = (a1 + a2) / 2
        m = (c[0] + r * math.cos(am), c[1] + r * math.sin(am))
        return Edge.make_three_point_arc(self.punkt(se, *a), self.punkt(se, *m), self.punkt(se, *b))

    def _linie(self, se, a, b) -> Edge:
        return Edge.make_line(self.punkt(se, *a), self.punkt(se, *b))

    def _polygon(self, se, uv: list, radien: list) -> Wire:
        """Geschlossener Linienzug mit tangentialen Eckverrundungen (SolidWorks CreateFillet, Ecke bleibt Maßbezug)."""
        n = len(uv)
        ecken = []   # je Ecke: (Eintritt, Austritt, Mitte|None)
        for i in range(n):
            p, a, b = uv[i], uv[i - 1], uv[(i + 1) % n]
            r = radien[i]
            if r <= 0:
                ecken.append((p, p, None))
                continue
            d1 = ((a[0] - p[0]), (a[1] - p[1])); l1 = math.hypot(*d1); d1 = (d1[0] / l1, d1[1] / l1)
            d2 = ((b[0] - p[0]), (b[1] - p[1])); l2 = math.hypot(*d2); d2 = (d2[0] / l2, d2[1] / l2)
            cos_w = d1[0] * d2[0] + d1[1] * d2[1]
            halb = math.acos(max(-1.0, min(1.0, cos_w))) / 2
            t = r / math.tan(halb)
            t1 = (p[0] + d1[0] * t, p[1] + d1[1] * t)
            t2 = (p[0] + d2[0] * t, p[1] + d2[1] * t)
            bis = (d1[0] + d2[0], d1[1] + d2[1]); lb = math.hypot(*bis)
            c = (p[0] + bis[0] / lb * r / math.sin(halb), p[1] + bis[1] / lb * r / math.sin(halb))
            ecken.append((t1, t2, c))
        kanten = []
        for i in range(n):
            ein, aus, c = ecken[i]
            if c is not None:
                kanten.append(Edge.make_three_point_arc(
                    self.punkt(se, *ein), self.punkt(se, *self._bogenmitte(ein, aus, c)), self.punkt(se, *aus)))
            nxt = ecken[(i + 1) % n][0]
            if math.dist(aus, nxt) > 1e-9:
                kanten.append(self._linie(se, aus, nxt))
        return Wire(kanten)

    @staticmethod
    def _bogenmitte(a, b, c):
        """Mittelpunkt des kürzeren Bogens a→b um c."""
        r = math.dist(a, c)
        m = ((a[0] + b[0]) / 2 - c[0], (a[1] + b[1]) / 2 - c[1])
        lm = math.hypot(*m)
        return (c[0] + m[0] / lm * r, c[1] + m[1] / lm * r)

    def drahtzuege(self, se: Ebene, elemente: list) -> list[Wire]:
        w = self.w
        out = []
        for el in elemente:
            if "rechteck" in el:
                r = el["rechteck"]
                mu, mv, b, h = w(r["mitte"][0]), w(r["mitte"][1]), w(r["breite"]), w(r["hoehe"])
                uv = [(mu - b / 2, mv - h / 2), (mu + b / 2, mv - h / 2), (mu + b / 2, mv + h / 2), (mu - b / 2, mv + h / 2)]
                out.append(self._polygon(se, uv, [w(r.get("radius", 0))] * 4))
            elif "polygon" in el:
                p = el["polygon"]
                uv = [(w(q[0]), w(q[1])) for q in p["punkte"]]
                roh = p.get("radien", 0)
                radien = [w(x) for x in (roh if isinstance(roh, list) else [roh] * len(uv))]
                out.append(self._polygon(se, uv, radien))
            elif "kreis" in el:
                k = el["kreis"]
                c = self.punkt(se, w(k["mitte"][0]), w(k["mitte"][1]))
                from build123d import Plane
                out.append(Wire([Edge.make_circle(w(k["durchmesser"]) / 2, Plane(origin=c, z_dir=_v(se.normale)))]))
            elif "kontur" in el:
                k = el["kontur"]
                akt = (w(k["start"][0]), w(k["start"][1]))
                kanten = []
                for s in k["segmente"]:
                    if "linie" in s:
                        ziel = (w(s["linie"][0]), w(s["linie"][1]))
                        kanten.append(self._linie(se, akt, ziel))
                    else:
                        ziel = (w(s["bogen"][0]), w(s["bogen"][1]))
                        kanten.append(self._bogen(se, akt, ziel, (w(s["mitte"][0]), w(s["mitte"][1]))))
                    akt = ziel
                out.append(Wire(kanten))
            elif "langloch" in el:
                lo = el["langloch"]
                mu, mv, ln, br = w(lo["mitte"][0]), w(lo["mitte"][1]), w(lo["laenge"]), w(lo["breite"])
                a = math.radians(w(lo.get("winkel", 0)))
                du, dv = math.cos(a) * ln / 2, math.sin(a) * ln / 2
                nu, nv = -math.sin(a) * br / 2, math.cos(a) * br / 2
                p1, p2 = (mu - du, mv - dv), (mu + du, mv + dv)
                kanten = [self._linie(se, (p1[0] - nu, p1[1] - nv), (p2[0] - nu, p2[1] - nv)),
                          self._bogen(se, (p2[0] - nu, p2[1] - nv), (p2[0] + nu, p2[1] + nv), p2),
                          self._linie(se, (p2[0] + nu, p2[1] + nv), (p1[0] + nu, p1[1] + nv)),
                          self._bogen(se, (p1[0] + nu, p1[1] + nv), (p1[0] - nu, p1[1] - nv), p1)]
                out.append(Wire(kanten))
            elif "mittellinie" in el:
                continue
            else:
                raise NichtUnterstuetzt(f"Skizzenelement {list(el)}")
        return out

    # --- Features -------------------------------------------------------------------------------------------------
    def tiefe(self, f: dict, se: Ebene, richt: tuple) -> tuple[float, float]:
        """(Versatz des Profils entlang richt, Tiefe)."""
        ende = f["ende"]
        typ = ende["typ"]
        if typ == "blind":
            return 0.0, self.w(ende["tiefe"])
        if typ == "mittig":
            t = self.w(ende["tiefe"])
            return -t / 2, t
        if typ == "durch_alles":
            return 0.0, DURCH_ALLES_MM
        if typ in ("bis_flaeche", "versatz_von_flaeche"):
            ziel = self.flaechenebene(ende["flaeche"])
            i = ACHSE[se.orientierung]
            if ACHSE[ziel.orientierung] != i:
                raise NichtUnterstuetzt("Zielfläche nicht parallel zur Skizze")
            d = (ziel.lage - se.lage) * richt[i]
            if typ == "versatz_von_flaeche":
                d -= self.w(ende["abstand"])
            return 0.0, d
        raise NichtUnterstuetzt(f"Endbedingung {typ}")

    def extrusion(self, f: dict) -> None:
        if "formschraege" in f.get("ende", {}):
            raise NichtUnterstuetzt("formschraege")
        se = self.ebene(f["skizze"]["ebene"])
        schnitt = f["typ"] == "schnitt"
        richt = se.normale
        if schnitt != bool(f["ende"].get("umkehren", False)):
            richt = tuple(-c for c in richt)
        versatz, t = self.tiefe(f, se, richt)
        if t <= 0:
            raise NichtUnterstuetzt(f"{f['id']}: Tiefe {t:.4g} ≤ 0")
        rv = _v(richt)
        werkzeug = None
        for d in self.drahtzuege(se, f["skizze"]["elemente"]):
            prisma = Solid.extrude(Face(d).moved_by(rv * versatz) if versatz else Face(d), rv * t)
            # gerade/ungerade Regel wie bei geschachtelten Skizzenkonturen
            werkzeug = prisma if werkzeug is None else (werkzeug - prisma) + (prisma - werkzeug)
        self.features[f["id"]] = FeatureInfo(f["typ"], werkzeug, richt)
        if schnitt:
            if self.body is None:
                raise NichtUnterstuetzt(f"{f['id']}: Schnitt ohne Körper")
            self.body = self.body - werkzeug
        else:
            self.body = werkzeug if self.body is None else self.body + werkzeug

    def _kanten(self, anker_liste: list) -> list:
        kanten = []
        for a in anker_liste:
            if "nahe" not in a:
                raise NichtUnterstuetzt(f"Kantenanker {list(a)}")
            p = _v([self.w(c) for c in a["nahe"]])
            alle = self.body.edges()
            abst = sorted(((e.distance_to(p), i) for i, e in enumerate(alle)))
            if not abst or abst[0][0] > TOL_ANKER_MM:
                raise NichtUnterstuetzt(f"keine Kante innerhalb {TOL_ANKER_MM} mm bei {tuple(p)}")
            if len(abst) > 1 and abst[1][0] <= TOL_ANKER_MM:
                raise NichtUnterstuetzt(f"Kante bei {tuple(p)} mehrdeutig")
            kanten.append(alle[abst[0][1]])
        return kanten

    def verrundung(self, f: dict) -> None:
        self.body = self.body.fillet(self.w(f["radius"]), self._kanten(f["kanten"]))
        self.features[f["id"]] = FeatureInfo("verrundung")

    def fase(self, f: dict) -> None:
        self.body = self.body.chamfer(self.w(f["abstand"]), None, self._kanten(f["kanten"]))
        self.features[f["id"]] = FeatureInfo("fase")

    def _loch(self, p: Vector, d: Vector, stufen: list, durch: bool, tiefe: float | None) -> Solid:
        """Bohrungskörper ab p in Richtung d: stufen = [(Ø, Tiefe)] von außen nach innen (Senkung …), danach das Loch
        (letzter Ø) durch alles oder bis tiefe mit Bohrspitze."""
        from build123d import Plane
        koerper = None
        start = 0.0
        for dm, t in stufen[:-1]:
            z = Solid.make_cylinder(dm / 2, t + 0.0, Plane(origin=p + d * start, z_dir=d))
            koerper = z if koerper is None else koerper + z
            start += t
        dm = stufen[-1][0]
        laenge = DURCH_ALLES_MM if durch else tiefe - start
        z = Solid.make_cylinder(dm / 2, laenge, Plane(origin=p + d * start, z_dir=d))
        if not durch:
            h = dm / 2 / math.tan(math.radians(bohrspitze_grad() / 2))
            z = z + Solid.make_cone(dm / 2, 0.0, h, Plane(origin=p + d * (start + laenge), z_dir=d))
        return z if koerper is None else koerper + z

    def bohrung(self, f: dict) -> None:
        se = self.flaechenebene(f["flaeche"])
        d = _v(tuple(-c for c in se.normale))
        punkte = [self.punkt(se, self.w(u), self.w(v)) for u, v in f["positionen"]]
        self.features[f["id"]] = FeatureInfo(f["typ"], None, tuple(d), punkte)
        if not self.mit_bohrungen:
            self.uebersprungen.append(f["id"])
            return
        durch = bool(f.get("durch"))
        tiefe = None if durch else self.w(f["tiefe"])
        if f["typ"] == "bohrung":
            stufen = [(self.w(f["durchmesser"]), 0.0)]
            if "senkung" in f:
                stufen.insert(0, (self.w(f["senkung"]["durchmesser"]), self.w(f["senkung"]["tiefe"])))
            werkzeuge = []
            for p in punkte:   # einfache Bohrung: Flachgrund (Schnitt blind), keine Bohrspitze
                w = Solid.extrude(Face(Wire([Edge.make_circle(stufen[-1][0] / 2, _ebene_bei(p, d))])),
                                  d * (DURCH_ALLES_MM if durch else tiefe))
                if len(stufen) > 1:
                    w = w + Solid.extrude(Face(Wire([Edge.make_circle(stufen[0][0] / 2, _ebene_bei(p, d))])),
                                          d * stufen[0][1])
                werkzeuge.append(w)
        else:
            m = normmasse(f["art"], f["groesse"], f.get("norm", "ISO"))
            if m is None:
                raise NichtUnterstuetzt(f"Normbohrung {f['art']} {f['groesse']} nicht in der Tabelle")
            if f["art"] == "gewinde":
                stufen = [(m["kernloch"], 0.0)]
            elif f["art"] == "zylinderschraube":
                stufen = [(m["senkung_d"], m["senkung_t"]), (m["durchgang"], 0.0)]
            elif f["art"] == "stift":
                stufen = [(m["durchmesser"], 0.0)]
            else:
                raise NichtUnterstuetzt(f"Normbohrung {f['art']}")
            werkzeuge = [self._loch(p, d, stufen, durch, tiefe) for p in punkte]
        for w in werkzeuge:
            self.body = self.body - w

    def baue(self) -> Teil:
        t0 = time.perf_counter()
        for f in self.spec["features"]:
            typ = f["typ"]
            if typ in ("extrusion", "schnitt"):
                self.extrusion(f)
            elif typ == "verrundung":
                self.verrundung(f)
            elif typ == "fase":
                self.fase(f)
            elif typ in BOHRUNGEN:
                self.bohrung(f)
            else:
                raise NichtUnterstuetzt(f"Feature-Typ {typ} ({f['id']})")
        solids = self.body.solids()
        if len(solids) != 1:
            raise NichtUnterstuetzt(f"{len(solids)} Volumenkörper statt 1")
        return Teil(self.name, solids[0], self.p, self.features, self.uebersprungen, time.perf_counter() - t0)


def lade(pfad: Path) -> dict:
    return yaml.safe_load(Path(pfad).read_text(encoding="utf-8"))


def baue_teil(spec: dict | Path, parameter: dict | None = None, bohrungen: bool = True) -> Teil:
    if not isinstance(spec, dict):
        spec = lade(spec)
    return Schnellbau(spec, parameter, bohrungen=bohrungen).baue()


if __name__ == "__main__":
    pfad = Path(sys.argv[1])
    werte = {k: float(v) for k, v in (a.split("=", 1) for a in sys.argv[2:])}
    t = baue_teil(pfad, werte)
    bb = t.solid.bounding_box()
    print(f"{t.name}: Volumen {t.solid.volume:.3f} mm³, Hüllquader {bb.min} … {bb.max}, "
          f"{t.sekunden * 1000:.1f} ms, übersprungen {t.uebersprungen}")
