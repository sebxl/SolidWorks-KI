"""Grobes Layout der Prüfstation AP 6.8 in Blender (Übergabe §10.1).

Aufruf aus dem Repo (venv-Python, startet Blender selbst im Hintergrund):
  .venv\\Scripts\\python.exe auftraege\\AP68-Pruefstation\\umgebung\\layout.py [--pct 100] [--ohne-bilder]
      [--setze name=wert ...] [--name zusatz] [--aus <ordner>] [--blender <exe>] [--blend <datei>]

Ablauf: liest ../layout.yaml (einzige Maßquelle), löst die Ausdrücke auf, prüft die reinen Geometrieregeln, startet
Blender auf schleifmaschine.blend (die Datei wird NIE gespeichert), baut die Prüfstation aus groben Körpern in
Maschinenkoordinaten (Übergabe §3), prüft Kollisionen und Abstände gegen die Maschine (Tisch C1/C2) und intern
(Schieber Pos. 1/2/3), rendert die Ansichten und setzt je Tischstellung ein Blatt zusammen.
Ausgabe in <aus> (Standard ../layout/): layout_C1.png, layout_C2.png, ansichten/, ergebnis.json; Zusammenfassung auf stdout.
Pfade aus config/rechner.yaml (nie fest im Code): Blender-Exe `blender` (sonst --blender, Umgebung BLENDER oder PATH),
Szene `dateien: {schleifmaschine_blend: …}` (sonst --blend).
"""
import ast, fnmatch, json, math, os, shutil, subprocess, sys

BEWEGT = ("schieber", "weiche")  # bewegte Gruppen (Weichenschlitten: Sitzung 4)

HIER = os.path.dirname(os.path.abspath(__file__))
AUFTRAG = os.path.dirname(HIER)


def pfade_aus_rechner():
    """(blender.exe, Szene) aus config/rechner.yaml – fehlt die Datei oder ein Eintrag, je None."""
    try:
        from swki.konfig import lade_rechner
        r = lade_rechner()
    except Exception:
        return None, None
    blend = r.dateien.get("schleifmaschine_blend")
    return (str(r.blender) if r.blender else None), (str(blend) if blend else None)

# ---------------------------------------------------------------- gemeinsam: Ausdrücke und Grundgeometrie

FUNK = {"sqrt": math.sqrt, "tan": math.tan, "sin": math.sin, "cos": math.cos, "atan": math.atan,
        "radians": math.radians, "degrees": math.degrees, "min": min, "max": max, "abs": abs, "pi": math.pi}


def rechne(text, namen):
    """Sicherer Auswerter für "=…"-Ausdrücke (Zahlen, Namen, + - * / **, Funktionen aus FUNK)."""
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.Name):
            if n.id in namen: return namen[n.id]
            if n.id in FUNK: return FUNK[n.id]
            raise NameError(f"unbekannter Name {n.id!r} in {text!r}")
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            ops = {ast.Add: lambda: a + b, ast.Sub: lambda: a - b, ast.Mult: lambda: a * b,
                   ast.Div: lambda: a / b, ast.Pow: lambda: a ** b}
            return ops[type(n.op)]()
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            v = ev(n.operand); return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNK:
            return FUNK[n.func.id](*[ev(a) for a in n.args])
        raise ValueError(f"nicht erlaubt in {text!r}: {ast.dump(n)}")
    return ev(ast.parse(text, mode="eval"))


def aufloesen(wert, namen):
    if isinstance(wert, str) and wert.startswith("="): return rechne(wert[1:], namen)
    if isinstance(wert, list): return [aufloesen(w, namen) for w in wert]
    if isinstance(wert, dict): return {k: aufloesen(v, namen) for k, v in wert.items()}
    return wert


def rundrechteck(x, y, r, n=6):
    """Punkte eines Rechtecks [x0,x1]×[y0,y1] mit Eckradius r, gegen den Uhrzeigersinn ab rechts unten; 4·(n+1) Punkte."""
    (x0, x1), (y0, y1) = sorted(x), sorted(y)
    r = max(min(r, (x1 - x0) / 2 - 1e-6, (y1 - y0) / 2 - 1e-6), 1e-3)
    ecken = [(x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)]
    pts = []
    for cx, cy, a0 in ecken:
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def huellen_winkel(k):
    """Kleinster Winkel der Erzeugenden einer Hülle gegen die Waagerechte (Wände und Kehlen, Grad)."""
    o, u = k["oben"], k["unten"]
    po, pu = rundrechteck(o["x"], o["y"], o.get("r", 0)), rundrechteck(u["x"], u["y"], u.get("r", 0))
    dz = abs(o["z"] - u["z"])
    return min(math.degrees(math.atan2(dz, math.hypot(a[0] - b[0], a[1] - b[1]))) for a, b in zip(po, pu))


# ---------------------------------------------------------------- Treiber (venv-Python)

def treiber():
    import argparse, yaml
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--yaml", default=os.path.join(AUFTRAG, "layout.yaml"))
    ap.add_argument("--aus", default=os.path.join(AUFTRAG, "layout"))
    ap.add_argument("--blender", default=os.environ.get("BLENDER"))
    ap.add_argument("--blend")
    ap.add_argument("--pct", type=int, default=100)
    ap.add_argument("--ohne-bilder", action="store_true")
    ap.add_argument("--setze", action="append", default=[], help="Maß überschreiben: name=wert")
    ap.add_argument("--name", default="", help="Zusatz für die Ausgabedateien")
    a = ap.parse_args()
    exe_rechner, blend_rechner = pfade_aus_rechner()
    exe = a.blender or exe_rechner or shutil.which("blender")
    blend = a.blend or blend_rechner
    if not exe or not os.path.isfile(exe):
        sys.exit(f"Blender nicht gefunden ({exe!r}): `blender` in config/rechner.yaml eintragen oder --blender")
    if not blend or not os.path.isfile(blend):
        sys.exit(f"Szene nicht gefunden ({blend!r}): `dateien: {{schleifmaschine_blend: …}}` in config/rechner.yaml "
                 "eintragen oder --blend")

    roh = yaml.safe_load(open(a.yaml, encoding="utf-8"))
    setze = dict(s.split("=", 1) for s in a.setze)
    namen = {}
    for k, v in roh["masse"].items():
        v = setze.pop(k, v)
        if isinstance(v, str) and not v.startswith("="): v = float(v)
        namen[k] = aufloesen(v, namen)
    if setze: sys.exit(f"unbekannte Maße: {', '.join(setze)}")
    d = {k: aufloesen(v, namen) for k, v in roh.items() if k != "masse"}
    d["masse"] = namen
    d["koerper"] = [k for k in d["koerper"] if k.get("nur_wenn", 1)]
    d["regeln_geometrie"] = geometrie_regeln(d)
    os.makedirs(a.aus, exist_ok=True)
    d["ausgabe"] = {"ordner": os.path.abspath(a.aus), "name": a.name, "pct": a.pct, "bilder": not a.ohne_bilder}
    pfad = os.path.join(a.aus, f"layout{a.name}.aufgeloest.json")
    json.dump(d, open(pfad, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cmd = [exe, "-b", blend, "--python", os.path.abspath(__file__), "--", "--blender-modus", pfad]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    erg_pfad = os.path.join(a.aus, f"ergebnis{a.name}.json")
    if p.returncode != 0 or not os.path.exists(erg_pfad) or os.path.getmtime(erg_pfad) < os.path.getmtime(pfad):
        print(p.stdout[-4000:]); print(p.stderr[-4000:]); sys.exit("Blender-Lauf fehlgeschlagen")
    erg = json.load(open(erg_pfad, encoding="utf-8"))
    print("\n".join(zusammenfassung(erg)))
    for b in erg.get("blaetter", []): print("BLATT", b)


def geometrie_regeln(d):
    m, rg, k = d["masse"], d["regeln"], {k["name"]: k for k in d["koerper"]}
    out = []
    def regel(text, ok, wert=""):
        out.append({"regel": text, "ok": bool(ok), "wert": wert})
    for name, kk in k.items():
        if kk["form"] == "huelle" and "winkel_min" in kk:
            w = huellen_winkel(kk)
            regel(f"{name}: Wände/Kehlen ≥ {kk['winkel_min']:g}°", w >= kk["winkel_min"] - 1e-6, f"min {w:.1f}°")
    t = k.get("Trichter")
    if t:
        regel(f"Trichter X ≤ {rg['trichter_x_max']:g} (A1a)", t["oben"]["x"][1] + t["wand"] <= rg["trichter_x_max"],
              f"X max {t['oben']['x'][1] + t['wand']:.1f}")
        regel(f"Trichter-OK ≤ 122 (A1b)", t["oben"]["z"] <= 122, f"Z {t['oben']['z']:g}")
    lf = k.get("Leuchtfläche")
    if lf:
        (x0, y0, _), (x1, y1, _) = lf["von"], lf["bis"]
        bx, by = rg["leuchtflaeche_min"]["x"], rg["leuchtflaeche_min"]["y"]
        reserve = min(bx[0] - x0, x1 - bx[1], by[0] - y0, y1 - by[1])
        regel("Leuchtfläche deckt Bildfeld + 1,5", reserve >= 0, f"Reserve {reserve:.1f}")
        rr = m["dd"] / 2 + rg["durchblick_rand"]
        reserve = min(m["kx"] - rr - x0, x1 - m["kx"] - rr, m["pm"] - rr - y0, y1 - m["pm"] - rr)
        regel(f"Leuchtfläche deckt Ø {m['dd']:g} + {rg['durchblick_rand']:g} (Ziel)", reserve >= 0, f"Reserve {reserve:.1f}")
    dl = k.get("Durchlicht")
    if dl:
        s = m.get("s", 1)
        kante = max(dl["von"][1], dl["bis"][1]) if s > 0 else min(dl["von"][1], dl["bis"][1])
        regel("Durchlicht-Gehäuse vor der Abgabekante (Messer fällt nicht darauf)", s * kante <= s * m["ak"],
              f"Gehäuse Y {kante:.1f} / Abgabe {m['ak']:g}")
    return out


def zusammenfassung(erg):
    z = []
    for r in erg["regeln"]:
        z.append(f"{'OK      ' if r['ok'] else 'VERLETZT'} {r['regel']}  {r['wert']}")
    for titel, schl in (("Maschine", "maschine"), ("Intern", "intern")):
        for e in erg[schl]:
            wo = ", ".join(e["wo"])
            tiefe = f", {e['tiefe']:.1f} mm tief" if e.get("tiefe") else ""
            z.append(f"{titel:8} {e['art']:9} {e['teil']} – {e['gegen']}: {e['abstand']:.1f} mm{tiefe} [{wo}]")
    for e in erg["abstaende"]:
        z.append(f"Abstand  {e['teil']} – {e['gegen']}: {e['abstand']:.1f} mm [{e['wo']}]")
    return z


# ---------------------------------------------------------------- Blender

FARBEN = {"eigenteil": (0.96, 0.60, 0.20, 1), "kaufteil": (0.25, 0.50, 0.90, 1), "traeger": (0.40, 0.65, 0.50, 0.45),
          "bauraum": (0.60, 0.40, 0.95, 0.22), "sicht": (1.0, 0.85, 0.10, 0.35), "glas": (0.55, 0.90, 1.0, 0.6),
          "leuchtflaeche": (1.0, 0.25, 0.15, 1), "messer": (0.75, 0.0, 0.0, 1)}
MASCHINE = (0.80, 0.80, 0.80, 1)
MASCHINE_TREFFER = (1.0, 0.72, 0.72, 1)
KOLLISION = (0.95, 0.0, 0.0, 1)
MM = 0.001


def blender(pfad):
    import bpy, bmesh, re
    import numpy as np
    from mathutils import Vector, Matrix
    from mathutils.bvhtree import BVHTree

    d = json.load(open(pfad, encoding="utf-8"))
    aus = d["ausgabe"]
    sc = bpy.data.scenes["Maschine"]
    bpy.context.window_manager  # Hintergrundlauf, keine Fenster
    rg = d["regeln"]

    ausschluss = re.compile(r"^(Boden|Messer [+-]\d+|Schrott [+-]\d+)$")
    maschine = []
    for o in sc.objects:
        if o.type == 'MESH' and not o.hide_render:
            if ausschluss.match(o.name): o.hide_render = True
            else: maschine.append(o)

    coll = bpy.data.collections.new("Pruefstation")
    sc.collection.children.link(coll)

    # --- Körper erzeugen (mm → m)
    def bm_quader(v, b):
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        lo = Vector([min(v[i], b[i]) for i in range(3)]) * MM
        hi = Vector([max(v[i], b[i]) for i in range(3)]) * MM
        for p in bm.verts:
            p.co = Vector([lo[i] + (p.co[i] + 0.5) * (hi[i] - lo[i]) for i in range(3)])
        return bm

    def bm_zylinder(mitte, achse, dm, l):
        if l < 0:   # Länge gegen die Achsrichtung
            mitte = list(mitte); mitte["xyz".index(achse)] += l; l = -l
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=dm / 2 * MM, radius2=dm / 2 * MM, depth=l * MM)
        rot = {"z": Matrix.Identity(3), "y": Matrix.Rotation(-math.pi / 2, 3, 'X'), "x": Matrix.Rotation(math.pi / 2, 3, 'Y')}[achse]
        ax = {"x": Vector((1, 0, 0)), "y": Vector((0, 1, 0)), "z": Vector((0, 0, 1))}[achse]
        for p in bm.verts:
            p.co = rot @ p.co + Vector(mitte) * MM + ax * (l / 2 * MM)
        return bm

    def bm_polygon(ebene, punkte, tiefe):
        bm = bmesh.new()
        idx = {"xy": (0, 1, 2), "yz": (1, 2, 0), "xz": (0, 2, 1)}[ebene]
        def p3(a, b, c):
            v = [0, 0, 0]; v[idx[0]], v[idx[1]], v[idx[2]] = a, b, c
            return Vector(v) * MM
        unten = [bm.verts.new(p3(a, b, tiefe[0])) for a, b in punkte]
        oben = [bm.verts.new(p3(a, b, tiefe[1])) for a, b in punkte]
        bm.faces.new(unten[::-1]); bm.faces.new(oben)
        n = len(punkte)
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((unten[i], unten[j], oben[j], oben[i]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm

    def bm_huelle(k):
        bm = bmesh.new()
        o, u = k["oben"], k["unten"]
        def ring(f, z, plus=0.0):
            fx, fy = sorted(f["x"]), sorted(f["y"])
            x = [fx[0] - plus, fx[1] + plus]; y = [fy[0] - plus, fy[1] + plus]
            return [bm.verts.new(Vector((a, b, z)) * MM) for a, b in rundrechteck(x, y, f.get("r", 0) + plus)]
        def band(r1, r2):
            n = len(r1)
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((r1[i], r1[j], r2[j], r2[i]))
        if k.get("voll"):
            ro, ru = ring(o, o["z"]), ring(u, u["z"])
            band(ru, ro); bm.faces.new(ro); bm.faces.new(ru[::-1])
        else:
            w = k["wand"]
            io, iu, ao, au = ring(o, o["z"]), ring(u, u["z"]), ring(o, o["z"], w), ring(u, u["z"], w)
            band(io, iu); band(au, ao); band(ao, io); band(iu, au)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm

    def bm_form(k):
        f = k["form"]
        if f == "quader": return bm_quader(k["von"], k["bis"])
        if f == "zylinder": return bm_zylinder(k["mitte"], k["achse"], k["d"], k["l"])
        if f == "polygon": return bm_polygon(k["ebene"], k["punkte"], k["tiefe"])
        if f == "huelle": return bm_huelle(k)
        raise ValueError(f"unbekannte Form {f}")

    def objekt(name, bm, ziel):
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); ziel.objects.link(ob)
        return ob

    station = []   # (objekt, körper)
    for k in d["koerper"]:
        ob = objekt(k["name"], bm_form(k), coll)
        if k.get("minus"):
            for i, mk in enumerate(k["minus"]):
                cut = objekt(f"_cut{i}", bm_form(mk), coll)
                mod = ob.modifiers.new(f"m{i}", 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.solver = 'EXACT'; mod.object = cut
            dg = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
            ob.modifiers.clear(); ob.data = me
            for c in [c for c in coll.objects if c.name.startswith("_cut")]: bpy.data.objects.remove(c)
        ob.color = FARBEN.get(k["art"], (0.7, 0.7, 0.7, 1))
        ob["gruppe"] = k.get("gruppe", "fest")
        station.append((ob, k))

    # Messerweg
    cu = bpy.data.curves.new("Messerweg", 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.9 * MM
    sp = cu.splines.new('POLY'); sp.points.add(len(d["messerweg"]) - 1)
    for p, q in zip(sp.points, d["messerweg"]): p.co = (q[0] * MM, q[1] * MM, q[2] * MM, 1)
    weg = bpy.data.objects.new("Messerweg", cu); coll.objects.link(weg); weg.color = (0.85, 0.0, 0.0, 1)

    # --- Prüfung
    dg = bpy.context.evaluated_depsgraph_get

    class Teil:
        def __init__(self, o, abtast=False):
            bm = bmesh.new(); bm.from_object(o, dg()); bm.transform(o.matrix_world)
            bmesh.ops.triangulate(bm, faces=bm.faces[:])
            self.name = o.name
            self.bvh = BVHTree.FromBMesh(bm)
            pts = [v.co.copy() for v in bm.verts]
            if abtast:   # Kantenpunkte alle 4 mm, damit Fläche-Kante-Abstände erfasst werden
                for e in bm.edges:
                    a, b = e.verts[0].co, e.verts[1].co
                    n = int((b - a).length / (4 * MM))
                    pts += [a.lerp(b, i / (n + 1)) for i in range(1, n + 1)]
            self.pts = pts
            self.lo = Vector([min(p[i] for p in pts) for i in range(3)]) if pts else Vector()
            self.hi = Vector([max(p[i] for p in pts) for i in range(3)]) if pts else Vector()
            bm.free()

    def luecke(a, b):
        return max(max(a.lo[i] - b.hi[i], b.lo[i] - a.hi[i]) for i in range(3))

    def innen(p, bvh):
        r = Vector((0.5773, 0.5774, 0.5775)); n = 0; q = p.copy()
        for _ in range(100):
            hit = bvh.ray_cast(q, r)
            if hit[0] is None: break
            n += 1; q = hit[0] + r * 1e-6
        return n % 2 == 1

    def in_box(p, t, rand):
        return all(t.lo[i] - rand <= p[i] <= t.hi[i] + rand for i in range(3))

    def vergleiche(a, b, suche):
        """a: Stationsteil (abgetastet), b: anderes Teil. → (kollision, abstand_mm, tiefe_mm) oder None."""
        if luecke(a, b) > suche: return None
        koll = bool(a.bvh.overlap(b.bvh))
        if not koll and luecke(a, b) <= 0:
            koll = innen(a.pts[0], b.bvh) or any(innen(p, a.bvh) for p in b.pts[:50] if in_box(p, a, 0))
        dist = suche
        for p in a.pts:
            if in_box(p, b, suche):
                h = b.bvh.find_nearest(p, suche)
                if h[0] is not None: dist = min(dist, h[3])
        for p in b.pts:
            if in_box(p, a, suche):
                h = a.bvh.find_nearest(p, suche)
                if h[0] is not None: dist = min(dist, h[3])
        tiefe = 0.0
        if koll:
            kand = [p for p in a.pts if in_box(p, b, 0)][:600]
            for p in kand:
                if innen(p, b.bvh):
                    h = b.bvh.find_nearest(p)
                    if h[0] is not None: tiefe = max(tiefe, h[3])
            dist = 0.0
        if not koll and dist >= suche: return None
        return koll, dist / MM, tiefe / MM

    def erlaubt(a, b):
        for x, y in d["erlaubt"]:
            if (fnmatch.fnmatch(a, x) and fnmatch.fnmatch(b, y)) or (fnmatch.fnmatch(a, y) and fnmatch.fnmatch(b, x)):
                return True
        return False

    sr = d["masse"].get("s", 1)   # Schubrichtung in Y
    w_hub = d["masse"].get("w_hub", 0)   # Weichenschlitten: Pos. 1 Ruhestellung, Pos. 2/3 um w_hub in Y (Sitzung 4)

    def versatz(k, pname, off):
        if k.get("gruppe") == "schieber": return off
        if k.get("gruppe") == "weiche": return 0.0 if pname == "Pos. 1" else w_hub
        return 0.0
    pos = [("Pos. 1", 0.0), ("Pos. 2", sr * d["masse"]["hub1"]), ("Pos. 3", sr * d["masse"]["hub2"])]
    befunde = {}     # (bereich, teil, gegen) → dict
    naechste = {}    # teil → (abstand, gegen, wo)
    treffer_maschine = {}  # zustand → {maschinenteil}
    treffer_station = {}   # zustand → {stationsteil}
    ueber = {}

    def melde(bereich, teil, gegen, erg, wo, grenze):
        koll, dist, tiefe = erg
        if not koll and dist >= grenze: return
        sch = (bereich, teil, gegen)
        e = befunde.setdefault(sch, {"bereich": bereich, "teil": teil, "gegen": gegen, "art": "Kollision" if koll else "knapp",
                                     "abstand": dist, "tiefe": tiefe, "wo": []})
        if koll: e["art"] = "Kollision"
        e["abstand"] = min(e["abstand"], dist); e["tiefe"] = max(e["tiefe"], tiefe); e["wo"].append(wo)

    for z in d["zustaende"]:
        sc.frame_set(z["bild"])
        treffer_maschine[z["name"]] = set(); treffer_station[z["name"]] = set()
        # Hüllquader der ganzen Station (alle Schieberstellungen) + 40 mm
        alle = [o for o, _ in station]
        lo = Vector([min((o.matrix_world @ Vector(c))[i] for o in alle for c in o.bound_box) for i in range(3)])
        hi = Vector([max((o.matrix_world @ Vector(c))[i] for o in alle for c in o.bound_box) for i in range(3)])
        hi.y += d["masse"]["hub2"] * MM; lo.y -= d["masse"]["hub2"] * MM
        nah = []
        for o in maschine:
            bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
            if all(min(p[i] for p in bb) < hi[i] + 0.04 and max(p[i] for p in bb) > lo[i] - 0.04 for i in range(3)):
                nah.append(Teil(o))
        fest_cache = {}
        for pname, off in pos:
            for o, k in station:
                o.location = (0, versatz(k, pname, off) * MM, 0)
            bpy.context.view_layer.update()
            teile = {}
            for o, k in station:
                if not k.get("pruefen", True): continue
                if k.get("nur_pos") and int(pname[-1]) not in k["nur_pos"]: continue
                if k.get("gruppe") not in BEWEGT and o.name in fest_cache: teile[o.name] = fest_cache[o.name]
                else: teile[o.name] = Teil(o, abtast=True)
                if k.get("gruppe") not in BEWEGT: fest_cache[o.name] = teile[o.name]
            kd = {o.name: k for o, k in station}
            wo = f"{z['name']} {pname}"
            for n, t in teile.items():
                k = kd[n]
                bewegt = k.get("gruppe") in BEWEGT or k.get("nur_pos")
                if pname != "Pos. 1" and not bewegt and z is not None:
                    pass
                grenze = k.get("abstand_min", rg["mindestabstand_maschine"])
                if bewegt or pname == "Pos. 1":
                    for m in nah:
                        e = vergleiche(t, m, max(grenze, 30) * MM)
                        if e is None: continue
                        if pname == "Pos. 1" or bewegt:
                            melde("maschine", n, m.name, e, wo, grenze)
                            if e[0]: treffer_maschine[z["name"]].add(m.name); treffer_station[z["name"]].add(n)
                            if not k.get("nur_pos") and (n not in naechste or e[1] < naechste[n][0]):
                                naechste[n] = (e[1], m.name, wo)
            if z is d["zustaende"][0]:
                namen = list(teile)
                for i, a in enumerate(namen):
                    for b in namen[i + 1:]:
                        ka, kb = kd[a], kd[b]
                        bew = ka.get("gruppe") in BEWEGT or kb.get("gruppe") in BEWEGT or ka.get("nur_pos") or kb.get("nur_pos")
                        if pname != "Pos. 1" and not bew: continue
                        if erlaubt(a, b): continue
                        e = vergleiche(teile[a], teile[b], max(rg["mindestabstand_intern"], 2) * MM)
                        if e is None: continue
                        melde("intern", a, b, e, pname, rg["mindestabstand_intern"])
                        if e[0]:
                            for zz in d["zustaende"]: treffer_station.setdefault(zz["name"], set()).update({a, b})
            # Überstreichbereich: feste Teile nur bis z_max
            if pname == "Pos. 1":
                u = rg["ueberstreich"]
                for n, t in teile.items():
                    if kd[n]["art"] in ("sicht",): continue
                    zs = [p.z / MM for p in t.pts if u["x"][0] <= p.x / MM <= u["x"][1] and u["y"][0] <= p.y / MM <= u["y"][1]]
                    if zs: ueber[n] = max(ueber.get(n, -1e9), max(zs))
        for o, _ in station: o.location = (0, 0, 0)

    regeln = list(d["regeln_geometrie"])
    zmax = rg["ueberstreich"]["z_max"]
    hoch = max(ueber.items(), key=lambda kv: kv[1]) if ueber else ("–", -1e9)
    schlecht = [f"{n} Z {v:.0f}" for n, v in ueber.items() if v > zmax]
    regeln.append({"regel": f"Feste Teile im Überstreichbereich ≤ Z {zmax:g} (A1b)", "ok": not schlecht,
                   "wert": ", ".join(schlecht) or f"höchstes: {hoch[0]} Z {hoch[1]:.0f}"})

    erg = {"regeln": regeln,
           "maschine": sorted([e for e in befunde.values() if e["bereich"] == "maschine"], key=lambda e: (e["art"] != "Kollision", e["abstand"])),
           "intern": sorted([e for e in befunde.values() if e["bereich"] == "intern"], key=lambda e: (e["art"] != "Kollision", e["abstand"])),
           "abstaende": sorted([{"teil": n, "abstand": v[0], "gegen": v[1], "wo": v[2]} for n, v in naechste.items() if v[0] < 30],
                               key=lambda e: e["abstand"]),
           "blaetter": []}
    for e in erg["maschine"] + erg["intern"]:
        e["wo"] = sorted(set(e["wo"]))

    if aus["bilder"]:
        erg["blaetter"] = rendern(d, sc, station, maschine, treffer_maschine, treffer_station, erg, np)
        erg["blend"] = kopie_speichern(d, sc, station, maschine)
    json.dump(erg, open(os.path.join(aus["ordner"], f"ergebnis{aus['name']}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("FERTIG")


def kopie_speichern(d, sc, station, maschine):
    """Layout als eigene .blend-Kopie zum Ansehen (Tisch C2, Schieber an einem Empty). Das Original wird nie gespeichert."""
    import bpy
    ziel = os.path.abspath(os.path.join(d["ausgabe"]["ordner"], f"pruefstation_layout{d['ausgabe']['name']}.blend"))
    if os.path.normcase(ziel) == os.path.normcase(os.path.abspath(bpy.data.filepath)):
        raise RuntimeError("Ziel ist die Originaldatei")
    coll = bpy.data.collections["Pruefstation"]
    s = d["masse"].get("s", 1)
    leer = bpy.data.objects.new(f"Schieber (Y = 0 / {s * d['masse']['hub1']:g} / {s * d['masse']['hub2']:g} mm für Pos. 1/2/3)", None)
    coll.objects.link(leer); leer.empty_display_size = 0.02
    for o, k in station:
        if k.get("gruppe") == "schieber": o.parent = leer
    for o in sc.objects:
        if o.type == 'MESH' and o.hide_render and o.name != "Boden": o.hide_viewport = True
    for n in ("LayoutKamera", "txt"):
        if n in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[n])
    cams = [o for o in sc.objects if o.type == 'CAMERA']
    if cams: sc.camera = cams[0]
    sc.frame_set(d["zustaende"][-1]["bild"])
    for scr in bpy.data.screens:
        for ar in scr.areas:
            if ar.type == 'VIEW_3D':
                s = ar.spaces[0].shading
                s.type = 'SOLID'; s.color_type = 'OBJECT'; s.show_cavity = True; s.show_object_outline = True
                ar.spaces[0].clip_start = 0.001
    bpy.ops.wm.save_as_mainfile(filepath=ziel, copy=True, compress=True)
    return ziel


def rendern(d, sc, station, maschine, treffer_maschine, treffer_station, erg, np):
    """Workbench-Bilder je Tischstellung und Ansicht, Titel und Tafel als eigene Textbilder, zu einem Blatt gefügt."""
    import bpy
    from mathutils import Vector, Matrix
    aus = d["ausgabe"]
    ordner = os.path.join(aus["ordner"], "ansichten"); os.makedirs(ordner, exist_ok=True)
    sc.render.engine = 'BLENDER_WORKBENCH'
    sh = sc.display.shading
    sh.light = 'STUDIO'; sh.color_type = 'OBJECT'; sh.show_cavity = True; sh.cavity_type = 'WORLD'
    sh.show_object_outline = True; sh.object_outline_color = (0.15, 0.15, 0.15)
    sh.show_shadows = False; sh.show_specular_highlight = False
    sc.display.render_aa = '8'
    if sc.world: sc.world.color = (0.97, 0.97, 0.97)
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.render.resolution_percentage = aus["pct"]
    sc.view_settings.view_transform = 'Standard'
    W, H = 1400, 1050
    for o in sc.objects:
        if o.name == "Boden": o.hide_render = True

    cam_d = bpy.data.cameras.new("LayoutKamera"); cam_d.type = 'ORTHO'
    cam = bpy.data.objects.new("LayoutKamera", cam_d); sc.collection.objects.link(cam); sc.camera = cam

    def stellen(a):
        blick = Vector(a["blick"]).normalized()
        zc = -blick
        yc = (Vector(a["oben"]) - Vector(a["oben"]).dot(zc) * zc).normalized()
        xc = yc.cross(zc)
        loc = Vector(a["mitte"]) * MM - blick * 3.0
        cam.matrix_world = Matrix.Translation(loc) @ Matrix((xc, yc, zc)).transposed().to_4x4()
        cam_d.ortho_scale = a["breite"] * MM
        cam_d.clip_start = 0.001; cam_d.clip_end = 10.0
        if a.get("schnitt") is not None:
            ebene = Vector([0, 0, 0])
            ax = max(range(3), key=lambda i: abs(blick[i]))
            ebene[ax] = a["schnitt"] * MM
            cam_d.clip_start = max(0.001, (ebene - loc).dot(blick))

    def lade(pfad):
        im = bpy.data.images.load(pfad)
        x = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32); im.pixels.foreach_get(x)
        x = x.reshape(im.size[1], im.size[0], 4); bpy.data.images.remove(im)
        return x

    def textbild(zeilen, w, h, gr, pfad, transparent):
        """Text oben links auf leerem Grund (Kamera weit weg von der Maschine); gr relativ zur Bildbreite."""
        sc.render.resolution_x, sc.render.resolution_y = w, h
        sc.render.film_transparent = transparent
        stellen({"blick": [1, 0, 0], "oben": [0, 0, 1], "mitte": [-60000, 0, 0], "breite": 1000})
        s = 1.0; hs = s * h / w
        cu = bpy.data.curves.new("txt", 'FONT'); cu.body = "\n".join(zeilen); cu.size = gr
        ob = bpy.data.objects.new("txt", cu); sc.collection.objects.link(ob)
        ob.parent = cam; ob.location = (-s / 2 + 0.006, hs / 2 - gr * 1.15, -1.0); ob.color = (0.05, 0.05, 0.05, 1)
        sc.render.filepath = pfad
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(ob)
        sc.render.film_transparent = False
        return lade(pfad)

    def kurz(n):
        return n.replace(".STEP-1", "")

    blaetter = []
    for z in d["zustaende"]:
        sc.frame_set(z["bild"])
        for o in maschine:
            o.color = MASCHINE_TREFFER if o.name in treffer_maschine.get(z["name"], ()) else MASCHINE
        for o, k in station:
            o.color = KOLLISION if o.name in treffer_station.get(z["name"], ()) and k["art"] not in ("bauraum", "sicht") \
                else FARBEN.get(k["art"], (0.7, 0.7, 0.7, 1))
        bilder = []
        for a in d["ansichten"]:
            versteckt = []
            if a.get("ausblenden_vor_y") is not None:
                for o in maschine:
                    ymax = max((o.matrix_world @ Vector(c)).y for c in o.bound_box) / MM
                    if ymax < a["ausblenden_vor_y"] and not o.hide_render:
                        o.hide_render = True; versteckt.append(o)
            sc.render.resolution_x, sc.render.resolution_y = W, H
            stellen(a)
            pfad = os.path.join(ordner, f"{z['name']}_{a['name']}{aus['name']}.png")
            sc.render.filepath = pfad
            bpy.ops.render.render(write_still=True)
            for o in versteckt: o.hide_render = False
            bild = lade(pfad)
            titel = textbild([f"{a['titel']}  -  Tisch {z['name']}, Schieber Pos. 1"], W, H // 14, 0.022,
                             os.path.join(ordner, "_titel.png"), True)
            streifen = np.full_like(titel, 0.97); streifen[..., 3] = 1
            al = titel[..., 3:4]
            streifen[..., :3] = titel[..., :3] * al + streifen[..., :3] * (1 - al)
            bilder.append(np.concatenate([bild, streifen], axis=0))     # Titel über dem Bild (Pixel von unten)
        # Tafel mit den Befunden
        zeilen = [f"Prüfstation AP 6.8 - grobes Layout, Tisch {z['name']}.  Maße: layout.yaml.  Farben: Eigenteile orange, "
                  f"Kaufteile blau, Träger grün, Spritzschutz-Bauraum violett, Sichtkegel/Fallraum gelb, Messerweg rot, "
                  f"Kollision rot gefüllt (Maschinenteil rosa).", ""]
        for r in erg["regeln"]:
            zeilen.append(f"{'OK  ' if r['ok'] else 'NEIN'}  {r['regel']}: {r['wert']}")
        zeilen.append("")
        km = [e for e in erg["maschine"] if any(w.startswith(z["name"]) for w in e["wo"])]
        for e in km[:10]:
            wo = ", ".join(sorted({w.split(' ', 1)[1] for w in e['wo'] if w.startswith(z['name'])}))
            t = f", {e['tiefe']:.0f} mm tief" if e["tiefe"] >= 0.5 else ""
            zeilen.append(f"{e['art'].upper()}  {e['teil']} - {kurz(e['gegen'])}: Abstand {e['abstand']:.1f}{t}  ({wo})")
        for e in erg["intern"][:8]:
            zeilen.append(f"INTERN {e['art'].upper()}  {e['teil']} - {e['gegen']}: {e['abstand']:.1f}  ({', '.join(e['wo'])})")
        if not km and not erg["intern"]: zeilen.append("Keine Kollision, kein Abstand unter dem Mindestabstand.")
        ab = [e for e in erg["abstaende"] if 0 < e["abstand"] < 12]
        if ab:
            zeilen.append("")
            zeilen.append("Kleinste Abstände zur Maschine: " + "; ".join(f"{e['teil']} - {kurz(e['gegen'])} {e['abstand']:.0f}" for e in ab[:6]))
        zeilen = [zz.replace("≤", "<=").replace("≥", ">=").replace("–", "-") for zz in zeilen]
        spalten = 3
        tafel = textbild(zeilen, W * spalten, int((len(zeilen) + 1.5) * 0.0105 * 1.32 * W * spalten), 0.0105,
                         os.path.join(ordner, f"{z['name']}_tafel{aus['name']}.png"), False)
        blaetter.append(blatt(bilder, tafel, spalten, os.path.join(aus["ordner"], f"layout_{z['name']}{aus['name']}.png"), np))
    return blaetter


def blatt(bilder, tafel, spalten, ziel, np):
    """Ansichten im Raster (spalten breit), darunter die Tafel. Blender-Pixel zählen von unten."""
    import bpy
    h, w = bilder[0].shape[:2]
    leer = np.full_like(bilder[0], 0.97); leer[..., 3] = 1
    reihen = []
    for i in range(0, len(bilder), spalten):
        r = bilder[i:i + spalten] + [leer] * (spalten - len(bilder[i:i + spalten]))
        r = np.concatenate(r, axis=1)
        for j in range(1, spalten): r[:, j * w - 1:j * w + 1, :3] = 0.3
        r[:2, :, :3] = 0.3
        reihen.append(r)
    tf = tafel[:, :w * spalten, :]
    gesamt = np.concatenate([tf] + reihen[::-1], axis=0)
    im = bpy.data.images.new("blatt", gesamt.shape[1], gesamt.shape[0], alpha=True)
    im.pixels.foreach_set(gesamt.ravel()); im.filepath_raw = ziel; im.file_format = 'PNG'; im.save()
    bpy.data.images.remove(im)
    return ziel


if __name__ == "__main__":
    if "--blender-modus" in sys.argv:
        blender(sys.argv[sys.argv.index("--blender-modus") + 1])
    else:
        treiber()
