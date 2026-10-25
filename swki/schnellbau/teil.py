"""Teil-Spec → exakte B-Rep ohne SolidWorks (Spec C1 §3), mit derselben Semantik wie der Compiler.

Skizzen: (u, v) → Modellpunkt über swki.compiler.skizze.modellpunkt; Elemente rechteck (radius), kreis, polygon (radien),
kontur (Bögen gegen den Uhrzeigersinn in (u, v)), langloch, mittellinie; mehrere Konturen nach gerade/ungerade.
Features: extrusion/schnitt (alle Endbedingungen, umkehren, formschraege), rotation, bohrung, normbohrung
(swki/wissen/bohrungsnormen.yaml), verrundung, fase (45°), muster_linear, muster_kreis, spiegeln, referenz, verzahnung
(Profil aus swki.verzahnung). skript und alles Übrige → SchnellbauFehler NICHT_UNTERSTUETZT.

Jedes Feature hinterlässt ein FeatureInfo: Werkzeugkörper und Operation (plus/minus, für Flächenanker, Muster, Spiegeln),
Richtung, Bohrungs- bzw. Radachspunkte, Bezugsebene. Längen in mm, Teilkoordinaten wie in SolidWorks.
"""

import math
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from build123d import Axis, Compound, Edge, Face, Location, Plane, Solid, Vector, Wire

from swki.compiler.anker import ACHSEN, RICHTUNGEN
from swki.compiler.skizze import NORMALE, modellpunkt, orientierung_der_normale
from swki.formschraege import schraege
from swki.konfig import lade_standard
from swki.schnellbau.fehler import ANKER, GEOMETRIE, NICHT_UNTERSTUETZT, SchnellbauFehler
from swki.spec.ausdruck import auswerten
from swki.spec.normen import bohrspitze_grad, normmasse, norm_von
from swki.verzahnung import Bogen, Linie, Stirnrad, aus_feature

ACHSE_DER = {"rechts": 0, "oben": 1, "vorne": 2}
BOHRUNGEN = ("bohrung", "normbohrung")
_PARALLEL = 1 - 1e-6
_VOLUMEN_EPS = 1e-6       # mm³: weniger Änderung durch einen Schnitt = "trifft kein Material"
_TANGENTE = 1e-4          # |sin| zwischen Kantentangenten, bis zu dem eine Kante tangential fortsetzt


@dataclass
class Ebene:
    orientierung: str    # vorne | oben | rechts
    lage: float          # Koordinate auf der Normalenachse
    normale: tuple       # Richtung, in die ein Aufsatz wächst


@dataclass
class FeatureInfo:
    typ: str
    werkzeug: Solid | None = None          # Körper, den das Feature hinzufügt oder abzieht
    op: str | None = None                  # "plus" | "minus"
    richtung: tuple | None = None
    punkte: list | None = None             # Achspunkte (Bohrung je Instanz, Stirnrad)
    ebene: Ebene | None = None             # referenz-Ebene


@dataclass
class Teil:
    name: str
    solid: Solid
    parameter: dict
    features: dict = field(default_factory=dict)
    uebersprungen: list = field(default_factory=list)
    sekunden: float = 0.0
    bau: "Schnellbau | None" = None   # für Anker-Abfragen (Flächenebenen) der Baugruppe


def _v(p) -> Vector:
    return Vector(*p)


def _t(v) -> tuple:
    return (float(v.X), float(v.Y), float(v.Z))


def _xor(a: Solid | None, b: Solid):
    return b if a is None else (a - b) + (b - a)


class Schnellbau:
    def __init__(self, spec: dict, parameter: dict | None = None, bohrungen: bool = True, tol_mm: float | None = None):
        self.spec = spec
        roh = spec.get("parameter", {})
        self.p = {k: auswerten(v, roh) for k, v in roh.items()}
        self.p.update(parameter or {})
        self.mit_bohrungen = bohrungen
        self.tol = tol_mm if tol_mm is not None else lade_standard()["toleranzen"]["anker_mm"]
        self.body = None
        self.features: dict[str, FeatureInfo] = {}
        self.uebersprungen: list[str] = []
        self.fid: str | None = None

    # --- Hilfen ------------------------------------------------------------------------------------------------
    def w(self, x) -> float:
        return auswerten(x, self.p)

    def fehler(self, code: str, meldung: str):
        return SchnellbauFehler(code, meldung, self.fid)

    def punkt(self, se: Ebene, u: float, v: float) -> Vector:
        return _v(modellpunkt(se.orientierung, u, v, se.lage))

    def _durch_mm(self) -> float:
        if self.body is None:
            return 10_000.0
        bb = self.body.bounding_box()
        return 2 * bb.diagonal + 1.0

    # --- Ebenen ------------------------------------------------------------------------------------------------
    def ebene(self, e) -> Ebene:
        if isinstance(e, str):
            return Ebene(e, 0.0, NORMALE[e])
        if "versatz" in e:
            basis = e["versatz"]["ebene"]
            return Ebene(basis, self.w(e["versatz"]["abstand"]), NORMALE[basis])
        return self.flaechenebene(e)

    def flaechenebene(self, anker: dict) -> Ebene:
        """{feature, flaeche}: Ebene der äußersten Werkzeugfläche des Features in Richtung (Schnitt: Werkzeugnormale
        entgegengesetzt, weil der Schnitt die Fläche umgekehrt erzeugt); {nahe}: nächste ebene Fläche des Körpers."""
        if "nahe" in anker:
            p = _v([self.w(c) for c in anker["nahe"]])
            kandidaten = sorted(((f.distance_to(p), i) for i, f in enumerate(self.body.faces())), key=lambda x: x[0])
            nah = [k for k in kandidaten if k[0] <= self.tol]
            if not nah:
                raise self.fehler(ANKER, f"keine Fläche innerhalb {self.tol} mm bei {tuple(anker['nahe'])}")
            if len(nah) > 1 and nah[1][0] - nah[0][0] < 1e-9:
                raise self.fehler(ANKER, f"Fläche bei {tuple(anker['nahe'])} mehrdeutig")
            f = self.body.faces()[nah[0][1]]
            if f.geom_type.name != "PLANE":
                raise self.fehler(NICHT_UNTERSTUETZT, "Skizze/Bohrung nur auf ebenen Flächen")
            n = _t(f.normal_at(p))
            orient = orientierung_der_normale(n)
            return Ebene(orient, _t(f.center())[ACHSE_DER[orient]], tuple(float(round(c)) for c in n))
        info = self.features.get(anker["feature"])
        if info is None or info.werkzeug is None:
            raise self.fehler(ANKER, f"Feature {anker['feature']!r} hat keine Flächen")
        richt = RICHTUNGEN[anker["flaeche"]]
        such = richt if info.op != "minus" else tuple(-c for c in richt)
        lagen = []
        for f in info.werkzeug.faces():
            if f.geom_type.name != "PLANE":
                continue
            n = f.normal_at()
            if n.X * such[0] + n.Y * such[1] + n.Z * such[2] > _PARALLEL:
                c = f.center()
                lagen.append(c.X * richt[0] + c.Y * richt[1] + c.Z * richt[2])
        if not lagen:
            raise self.fehler(ANKER, f"keine Fläche {anker['flaeche']} an {anker['feature']}")
        orient = orientierung_der_normale(richt)
        return Ebene(orient, max(lagen) * richt[ACHSE_DER[orient]], richt)

    # --- Skizzen -----------------------------------------------------------------------------------------------
    def _bogen(self, se, a, b, c, gegen_uhrzeigersinn: bool = True) -> Edge:
        r = math.dist(a, c)
        a1 = math.atan2(a[1] - c[1], a[0] - c[0])
        a2 = math.atan2(b[1] - c[1], b[0] - c[0])
        if gegen_uhrzeigersinn:
            if a2 <= a1 + 1e-12:
                a2 += 2 * math.pi
        elif a2 >= a1 - 1e-12:
            a2 -= 2 * math.pi
        am = (a1 + a2) / 2
        m = (c[0] + r * math.cos(am), c[1] + r * math.sin(am))
        return Edge.make_three_point_arc(self.punkt(se, *a), self.punkt(se, *m), self.punkt(se, *b))

    def _linie(self, se, a, b) -> Edge:
        return Edge.make_line(self.punkt(se, *a), self.punkt(se, *b))

    def _polygon(self, se, uv: list, radien: list) -> Wire:
        """Geschlossener Linienzug mit tangentialen Eckverrundungen (CreateFillet; die Ecke bleibt Maßbezug)."""
        n = len(uv)
        ecken = []
        for i in range(n):
            p, a, b, r = uv[i], uv[i - 1], uv[(i + 1) % n], radien[i]
            if r <= 0:
                ecken.append((p, p, None))
                continue
            d1 = (a[0] - p[0], a[1] - p[1]); l1 = math.hypot(*d1); d1 = (d1[0] / l1, d1[1] / l1)
            d2 = (b[0] - p[0], b[1] - p[1]); l2 = math.hypot(*d2); d2 = (d2[0] / l2, d2[1] / l2)
            halb = math.acos(max(-1.0, min(1.0, d1[0] * d2[0] + d1[1] * d2[1]))) / 2
            t = r / math.tan(halb)
            bis = (d1[0] + d2[0], d1[1] + d2[1]); lb = math.hypot(*bis)
            c = (p[0] + bis[0] / lb * r / math.sin(halb), p[1] + bis[1] / lb * r / math.sin(halb))
            ecken.append(((p[0] + d1[0] * t, p[1] + d1[1] * t), (p[0] + d2[0] * t, p[1] + d2[1] * t), c))
        kanten = []
        for i in range(n):
            ein, aus, c = ecken[i]
            if c is not None:
                m = ((ein[0] + aus[0]) / 2 - c[0], (ein[1] + aus[1]) / 2 - c[1])
                lm, r = math.hypot(*m), math.dist(ein, c)
                mitte = (c[0] + m[0] / lm * r, c[1] + m[1] / lm * r)
                kanten.append(Edge.make_three_point_arc(self.punkt(se, *ein), self.punkt(se, *mitte), self.punkt(se, *aus)))
            nxt = ecken[(i + 1) % n][0]
            if math.dist(aus, nxt) > 1e-9:
                kanten.append(self._linie(se, aus, nxt))
        return Wire(kanten)

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
                out.append(self._polygon(se, uv, [w(x) for x in (roh if isinstance(roh, list) else [roh] * len(uv))]))
            elif "kreis" in el:
                k = el["kreis"]
                c = self.punkt(se, w(k["mitte"][0]), w(k["mitte"][1]))
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
                out.append(Wire([self._linie(se, (p1[0] - nu, p1[1] - nv), (p2[0] - nu, p2[1] - nv)),
                                 self._bogen(se, (p2[0] - nu, p2[1] - nv), (p2[0] + nu, p2[1] + nv), p2),
                                 self._linie(se, (p2[0] + nu, p2[1] + nv), (p1[0] + nu, p1[1] + nv)),
                                 self._bogen(se, (p1[0] + nu, p1[1] + nv), (p1[0] - nu, p1[1] - nv), p1)]))
            elif "mittellinie" in el:
                continue
            else:
                raise self.fehler(NICHT_UNTERSTUETZT, f"Skizzenelement {list(el)}")
        return out

    # --- Körperoperationen -------------------------------------------------------------------------------------
    def anwenden(self, werkzeug: Solid, op: str) -> None:
        if op == "plus":
            self.body = werkzeug if self.body is None else self.body + werkzeug
            return
        if self.body is None:
            raise self.fehler(GEOMETRIE, "Schnitt ohne Körper")
        vorher = self.body.volume
        neu = self.body - werkzeug
        if neu is None or vorher - neu.volume < _VOLUMEN_EPS:
            raise self.fehler(GEOMETRIE, "Schnitt trifft kein Material")
        self.body = neu

    def _prisma(self, face: Face, richtung: Vector, versatz: float, tiefe: float, schraege_: dict | None) -> Solid:
        if versatz:
            face = face.moved(Location(richtung * versatz))
        if schraege_ is None:
            return Solid.extrude(face, richtung * tiefe)
        # querschnitt aus Sicht der Skizze: kleiner = Werkzeug verjüngt sich von der Skizzenebene weg
        winkel = self.w(schraege_["winkel"])
        taper = winkel if schraege_["querschnitt"] == "kleiner" else -winkel
        return Solid.extrude_taper(face, richtung * tiefe, taper)

    # --- Features ----------------------------------------------------------------------------------------------
    def extrusion(self, f: dict) -> None:
        se = self.ebene(f["skizze"]["ebene"])
        ende = f["ende"]
        schnitt = f["typ"] == "schnitt"
        richt = se.normale if schnitt == bool(ende.get("umkehren", False)) else tuple(-c for c in se.normale)
        typ = ende["typ"]
        if typ in ("blind", "mittig"):
            tiefe = self.w(ende["tiefe"])
        elif typ == "durch_alles":
            tiefe = self._durch_mm()
        elif typ in ("bis_flaeche", "versatz_von_flaeche"):
            ziel = self.flaechenebene(ende["flaeche"])
            i = ACHSE_DER[se.orientierung]
            if ACHSE_DER[ziel.orientierung] != i:
                raise self.fehler(NICHT_UNTERSTUETZT, "Zielfläche nicht parallel zur Skizze")
            tiefe = (ziel.lage - se.lage) * richt[i]
            if typ == "versatz_von_flaeche":
                tiefe -= self.w(ende["abstand"])
        else:
            raise self.fehler(NICHT_UNTERSTUETZT, f"Endbedingung {typ}")
        if tiefe <= 0:
            raise self.fehler(GEOMETRIE, f"Tiefe {tiefe:.6g} ≤ 0")
        rv = _v(richt)
        sch = schraege(f)
        werkzeug = None
        for d in self.drahtzuege(se, f["skizze"]["elemente"]):
            if typ == "mittig":
                prisma = self._prisma(Face(d), rv, 0.0, tiefe / 2, sch) + self._prisma(Face(d), -rv, 0.0, tiefe / 2, sch)
            else:
                prisma = self._prisma(Face(d), rv, 0.0, tiefe, sch)
            werkzeug = _xor(werkzeug, prisma)
        op = "minus" if schnitt else "plus"
        self.features[f["id"]] = FeatureInfo(f["typ"], werkzeug, op, richt)
        self.anwenden(werkzeug, op)

    def rotation(self, f: dict) -> None:
        se = self.ebene(f["skizze"]["ebene"])
        linie = next((e["mittellinie"] for e in f["skizze"]["elemente"] if "mittellinie" in e), None)
        if linie is None:
            raise self.fehler(GEOMETRIE, "rotation ohne mittellinie")
        a = self.punkt(se, self.w(linie["von"][0]), self.w(linie["von"][1]))
        b = self.punkt(se, self.w(linie["bis"][0]), self.w(linie["bis"][1]))
        achse = Axis(a, b - a)
        winkel = self.w(f.get("winkel", 360))
        werkzeug = None
        for d in self.drahtzuege(se, f["skizze"]["elemente"]):
            werkzeug = _xor(werkzeug, Solid.revolve(Face(d), winkel, achse))
        op = "minus" if f.get("schnitt") else "plus"
        self.features[f["id"]] = FeatureInfo("rotation", werkzeug, op, _t((b - a).normalized()))
        self.anwenden(werkzeug, op)

    def _loch(self, p: Vector, d: Vector, stufen: list, durch: bool, tiefe: float | None, spitze: bool) -> Solid:
        """Bohrungskörper ab p in Richtung d: stufen = [(Ø, Tiefe)] von außen nach innen, das letzte (Ø, _) ist das
        Loch – durch alles oder bis tiefe, mit Bohrspitze, wenn spitze."""
        koerper, start = None, 0.0
        for dm, t in stufen[:-1]:
            z = Solid.make_cylinder(dm / 2, t, Plane(origin=p + d * start, z_dir=d))
            koerper = z if koerper is None else koerper + z
            start += t
        dm = stufen[-1][0]
        laenge = self._durch_mm() if durch else tiefe - start
        z = Solid.make_cylinder(dm / 2, laenge, Plane(origin=p + d * start, z_dir=d))
        if spitze and not durch:
            h = dm / 2 / math.tan(math.radians(bohrspitze_grad() / 2))
            z = z + Solid.make_cone(dm / 2, 0.0, h, Plane(origin=p + d * (start + laenge), z_dir=d))
        return z if koerper is None else koerper + z

    def _senkkegel(self, p: Vector, d: Vector, d_oben: float, d_unten: float, winkel: float) -> Solid:
        h = (d_oben - d_unten) / 2 / math.tan(math.radians(winkel / 2))
        return Solid.make_cone(d_oben / 2, d_unten / 2, h, Plane(origin=p, z_dir=d))

    def bohrung(self, f: dict) -> None:
        se = self.flaechenebene(f["flaeche"])
        d = _v(tuple(-c for c in se.normale))
        punkte = [self.punkt(se, self.w(u), self.w(v)) for u, v in f["positionen"]]
        durch = bool(f.get("durch"))
        tiefe = None if durch else self.w(f["tiefe"])
        if f["typ"] == "bohrung":
            stufen = [(self.w(f["durchmesser"]), 0.0)]
            if "senkung" in f:
                stufen.insert(0, (self.w(f["senkung"]["durchmesser"]), self.w(f["senkung"]["tiefe"])))
            werkzeuge = [self._loch(p, d, stufen, durch, tiefe, spitze=False) for p in punkte]
        else:
            m = normmasse(f["art"], f["groesse"], norm_von(f))
            if m is None:
                raise self.fehler(NICHT_UNTERSTUETZT, f"Normbohrung {f['art']} {f['groesse']} nicht in der Tabelle")
            if f["art"] == "gewinde":
                werkzeuge = [self._loch(p, d, [(m["kernloch"], 0.0)], durch, tiefe, True) for p in punkte]
            elif f["art"] == "zylinderschraube":
                stufen = [(m["senkung_d"], m["senkung_t"]), (m["durchgang"], 0.0)]
                werkzeuge = [self._loch(p, d, stufen, durch, tiefe, True) for p in punkte]
            elif f["art"] == "stift":
                werkzeuge = [self._loch(p, d, [(m["durchmesser"], 0.0)], durch, tiefe, True) for p in punkte]
            elif f["art"] == "senkschraube":
                werkzeuge = [self._senkkegel(p, d, m["senkung_d"], m["durchgang"], m["senkwinkel"])
                             + self._loch(p, d, [(m["durchgang"], 0.0)], durch, tiefe, True) for p in punkte]
            else:
                raise self.fehler(NICHT_UNTERSTUETZT, f"Normbohrung {f['art']}")
        werkzeug = werkzeuge[0]
        for x in werkzeuge[1:]:
            werkzeug = werkzeug + x
        self.features[f["id"]] = FeatureInfo(f["typ"], werkzeug, "minus", _t(d), [_t(p) for p in punkte])
        if not self.mit_bohrungen:
            self.uebersprungen.append(f["id"])
            return
        self.anwenden(werkzeug, "minus")

    # Kanten ------------------------------------------------------------------------------------------------------
    def _flaechen_des_features(self, fid: str) -> list:
        """Flächen des Körpers, die auf dem Rand des Werkzeugs von fid liegen (wie IFeature.GetFaces)."""
        info = self.features.get(fid)
        if info is None or info.werkzeug is None:
            raise self.fehler(ANKER, f"Feature {fid!r} hat keine Flächen")
        rand = Compound(info.werkzeug.faces())   # nur der Rand: distance_to eines Volumenkörpers ist innen 0
        out = []
        for f in self.body.faces():
            v, dreiecke = f.tessellate(0.05, 0.5)
            if not dreiecke:
                continue
            a, b, c = (_v(v[i]) for i in dreiecke[0])
            probe = (a + b + c) * (1 / 3)        # Schwerpunkt eines Dreiecks: liegt sicher auf der Fläche
            if rand.distance_to(probe) < 1e-6:
                out.append(f)
        return out

    def _kanten(self, anker_liste: list) -> list:
        kanten = []
        for a in anker_liste:
            if "nahe" in a:
                p = _v([self.w(c) for c in a["nahe"]])
                alle = self.body.edges()
                abst = sorted(((e.distance_to(p), i) for i, e in enumerate(alle)), key=lambda x: x[0])
                if not abst or abst[0][0] > self.tol:
                    raise self.fehler(ANKER, f"keine Kante innerhalb {self.tol} mm bei {tuple(a['nahe'])}")
                if len(abst) > 1 and abst[1][0] - abst[0][0] < 1e-9:
                    raise self.fehler(ANKER, f"Kante bei {tuple(a['nahe'])} mehrdeutig")
                kanten.append(alle[abst[0][1]])
                continue
            flaechen = self._flaechen_des_features(a["feature"])
            if "kanten_an" in a:
                r = RICHTUNGEN[a["kanten_an"]]
                passend = [f for f in flaechen if f.geom_type.name == "PLANE"
                           and sum(x * y for x, y in zip(_t(f.normal_at()), r)) > _PARALLEL]
                if not passend:
                    raise self.fehler(ANKER, f"keine Fläche {a['kanten_an']} an {a['feature']}")
                f = max(passend, key=lambda f: sum(x * y for x, y in zip(_t(f.center()), r)))
                kanten += list(f.edges())
                continue
            alle = {id(e.wrapped): e for f in flaechen for e in f.edges()}.values()
            if a["auswahl"] == "alle_kanten":
                kanten += list(alle)
                continue
            r = self.features[a["feature"]].richtung
            treffer = [e for e in alle if e.geom_type.name == "LINE"
                       and abs(sum(x * y for x, y in zip(_t(e.tangent_at(0)), r))) > _PARALLEL]
            if not treffer:
                raise self.fehler(ANKER, f"keine Kante parallel zur Richtung von {a['feature']}")
            kanten += treffer
        return self._tangential(kanten)

    def _tangential(self, kanten: list) -> list:
        """Setzt die Auswahl über tangential anschließende Kanten fort (PropagateToTangentFaces/TANGENT_PROPAGATION)."""
        alle = self.body.edges()
        gewaehlt = {e.wrapped.__hash__(): e for e in kanten}
        neu = True
        while neu:
            neu = False
            for e in list(gewaehlt.values()):
                for ende, t_e in ((e @ 0, e.tangent_at(0)), (e @ 1, e.tangent_at(1))):
                    for k in alle:
                        h = k.wrapped.__hash__()
                        if h in gewaehlt:
                            continue
                        for ende_k, t_k in ((k @ 0, k.tangent_at(0)), (k @ 1, k.tangent_at(1))):
                            if (ende - ende_k).length < 1e-6 and t_e.cross(t_k).length < _TANGENTE:
                                gewaehlt[h] = k
                                neu = True
                                break
        return list(gewaehlt.values())

    def verrundung(self, f: dict) -> None:
        self.body = self.body.fillet(self.w(f["radius"]), self._kanten(f["kanten"]))
        self.features[f["id"]] = FeatureInfo("verrundung")

    def fase(self, f: dict) -> None:
        if abs(self.w(f.get("winkel", 45)) - 45) > 1e-9:
            raise self.fehler(NICHT_UNTERSTUETZT, "fase mit winkel ≠ 45°")
        self.body = self.body.chamfer(self.w(f["abstand"]), None, self._kanten(f["kanten"]))
        self.features[f["id"]] = FeatureInfo("fase")

    # Muster ------------------------------------------------------------------------------------------------------
    def _werkzeuge(self, ids: list) -> list[tuple[Solid, str]]:
        out = []
        for fid in ids:
            info = self.features.get(fid)
            if info is None or info.werkzeug is None or info.op is None:
                raise self.fehler(NICHT_UNTERSTUETZT, f"{fid!r} lässt sich nicht mustern/spiegeln")
            out.append((info.werkzeug, info.op))
        return out

    def _muster_anwenden(self, f: dict, kopien: list[tuple[Solid, str]]) -> None:
        plus = [w for w, op in kopien if op == "plus"]
        minus = [w for w, op in kopien if op == "minus"]
        for gruppe, op in ((plus, "plus"), (minus, "minus")):
            if not gruppe:
                continue
            w = gruppe[0]
            for x in gruppe[1:]:
                w = w + x
            if op == "minus" and not self.mit_bohrungen and all(
                    self.features[i].typ in BOHRUNGEN or i in self.uebersprungen for i in f["features"]):
                self.uebersprungen.append(f["id"])
                self.features[f["id"]] = FeatureInfo(f["typ"], w, op)
                return
            self.anwenden(w, op)
        ops = {op for _, op in kopien}
        alle = None
        for w, _ in kopien:
            alle = w if alle is None else alle + w
        self.features[f["id"]] = FeatureInfo(f["typ"], alle, ops.pop() if len(ops) == 1 else None)

    def muster_linear(self, f: dict) -> None:
        richtungen = []
        for r in (f["richtung1"], f.get("richtung2")):
            if r is None:
                continue
            d = _v(ACHSEN[r["achse"]]) * (-1 if r.get("umkehren") else 1)
            richtungen.append([d * (self.w(r["abstand"]) * i) for i in range(r["anzahl"])])
        versaetze = richtungen[0] if len(richtungen) == 1 else [a + b for a in richtungen[0] for b in richtungen[1]]
        kopien = [(w.moved(Location(v)), op) for w, op in self._werkzeuge(f["features"])
                  for v in versaetze if v.length > 1e-12]
        self._muster_anwenden(f, kopien)

    def muster_kreis(self, f: dict) -> None:
        n, gesamt = f["anzahl"], self.w(f.get("winkel", 360))
        schritt = gesamt / n if abs(gesamt - 360) < 1e-9 else gesamt / (n - 1)
        achse = Axis((0, 0, 0), ACHSEN[f["achse"]])
        kopien = [(w.rotate(achse, schritt * i), op) for w, op in self._werkzeuge(f["features"]) for i in range(1, n)]
        self._muster_anwenden(f, kopien)

    def spiegeln(self, f: dict) -> None:
        se = self.ebene(f["ebene"])
        ebene = Plane(origin=_v(modellpunkt(se.orientierung, 0, 0, se.lage)), z_dir=_v(NORMALE[se.orientierung]))
        kopien = [(w.mirror(ebene), op) for w, op in self._werkzeuge(f["features"])]
        self._muster_anwenden(f, kopien)

    def referenz(self, f: dict) -> None:
        if "achse" in f:
            self.features[f["id"]] = FeatureInfo("referenz", richtung=ACHSEN[f["achse"]], punkte=[(0.0, 0.0, 0.0)])
            return
        e = f["ebene"]
        lage = self.w(e.get("abstand", 0)) * (-1 if e.get("umkehren") else 1)
        self.features[f["id"]] = FeatureInfo("referenz", ebene=Ebene(e["basis"], lage, NORMALE[e["basis"]]),
                                             richtung=NORMALE[e["basis"]])

    def verzahnung(self, f: dict) -> None:
        geo = aus_feature(f, self.p)
        mitte = (self.w(f["mitte"][0]), self.w(f["mitte"][1]))
        konturen = geo.profil(mitte, self.w(f.get("winkel", 0))) if isinstance(geo, Stirnrad) \
            else geo.profil(mitte, f.get("kopf", "+v"))
        se = self.ebene(f["ebene"])
        werkzeug = None
        for kontur in konturen:
            kanten = []
            for s in kontur:
                if isinstance(s, Linie):
                    kanten.append(self._linie(se, s.a, s.b))
                elif isinstance(s, Bogen):
                    kanten.append(self._bogen(se, s.a, s.b, s.mitte, s.gegen_uhrzeigersinn))
                else:
                    kanten.append(Edge.make_spline([self.punkt(se, *q) for q in s.punkte]))
            werkzeug = _xor(werkzeug, Solid.extrude(Face(Wire(kanten)), _v(se.normale) * (
                -self.w(f["breite"]) if f.get("umkehren") else self.w(f["breite"]))))
        richt = tuple(-c for c in se.normale) if f.get("umkehren") else se.normale
        punkte = [_t(self.punkt(se, *mitte))] if isinstance(geo, Stirnrad) else None
        self.features[f["id"]] = FeatureInfo("verzahnung", werkzeug, "plus", richt, punkte)
        self.anwenden(werkzeug, "plus")

    HANDLER = {"extrusion": "extrusion", "schnitt": "extrusion", "rotation": "rotation", "bohrung": "bohrung",
               "normbohrung": "bohrung", "verrundung": "verrundung", "fase": "fase", "muster_linear": "muster_linear",
               "muster_kreis": "muster_kreis", "spiegeln": "spiegeln", "referenz": "referenz",
               "verzahnung": "verzahnung"}

    def baue(self) -> Teil:
        t0 = time.perf_counter()
        for f in self.spec["features"]:
            self.fid = f["id"]
            name = self.HANDLER.get(f["typ"])
            if name is None:
                raise self.fehler(NICHT_UNTERSTUETZT, f"Feature-Typ {f['typ']} hat im Schnellbau kein Gegenstück")
            try:
                getattr(self, name)(f)
            except SchnellbauFehler:
                raise
            except Exception as e:     # OCC-Fehler mit Feature-ID melden
                raise self.fehler(GEOMETRIE, f"{type(e).__name__}: {e}") from e
        self.fid = None
        if self.body is None:
            raise SchnellbauFehler(GEOMETRIE, "kein Körper")
        solids = self.body.solids()
        if len(solids) != 1:
            raise SchnellbauFehler(GEOMETRIE, f"{len(solids)} Volumenkörper statt 1")
        return Teil(self.spec.get("name", "teil"), solids[0], self.p, self.features, self.uebersprungen,
                    time.perf_counter() - t0, self)


def lade(pfad: Path) -> dict:
    return yaml.safe_load(Path(pfad).read_text(encoding="utf-8"))


def baue(spec: dict | Path, parameter: dict | None = None, bohrungen: bool = True) -> Teil:
    """Teil-Spec (dict oder Pfad) → Teil; parameter überschreibt Spec-Parameter (Zahlen in mm/Grad)."""
    if not isinstance(spec, dict):
        spec = lade(spec)
    return Schnellbau(spec, parameter, bohrungen).baue()
