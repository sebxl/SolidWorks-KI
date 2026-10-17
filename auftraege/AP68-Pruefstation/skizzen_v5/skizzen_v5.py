"""Skizzen v5 (17.10.2026) aus den Specs: Schieberstirn D1 (schieber.yaml) und Fallschacht 7b (fallschacht.yaml).

Aufruf aus dem Repo: .venv\\Scripts\\python.exe auftraege\\AP68-Pruefstation\\skizzen_v5\\skizzen_v5.py
Die Koordinaten kommen aus den Skizzenpunkten der Specs (swki-Ausdrücke ausgewertet); Fillets des Taschen-Polygons und die
Verrundung im V-Grund werden hier nachgerechnet. Ausgabe: SVG neben diesem Skript.
"""
import math, os, sys
import yaml

HIER = os.path.dirname(os.path.abspath(__file__))
AUFTRAG = os.path.dirname(HIER)
sys.path.insert(0, os.path.dirname(os.path.dirname(AUFTRAG)))
from swki.spec.ausdruck import auswerten  # noqa: E402


def lade(name):
    s = yaml.safe_load(open(os.path.join(AUFTRAG, name), encoding="utf-8"))
    return s, s["parameter"], {f["id"]: f for f in s["features"]}


def w(v, p):
    return auswerten(v, p)


def bogen_pkt(m, a, b, n=16):
    """Bogen gegen den Uhrzeigersinn von a nach b um m."""
    r = math.hypot(a[0] - m[0], a[1] - m[1])
    w0, w1 = math.atan2(a[1] - m[1], a[0] - m[0]), math.atan2(b[1] - m[1], b[0] - m[0])
    d = (w1 - w0) % (2 * math.pi)
    return [(m[0] + r * math.cos(w0 + d * k / n), m[1] + r * math.sin(w0 + d * k / n)) for k in range(1, n + 1)]


def verrunde(pkt, i, r, n=12):
    """Ecke i eines geschlossenen Polygons tangential verrunden."""
    p, a, b = pkt[i], pkt[i - 1], pkt[(i + 1) % len(pkt)]
    ua = ((a[0] - p[0]), (a[1] - p[1])); la = math.hypot(*ua); ua = (ua[0] / la, ua[1] / la)
    ub = ((b[0] - p[0]), (b[1] - p[1])); lb = math.hypot(*ub); ub = (ub[0] / lb, ub[1] / lb)
    al = math.acos(max(-1, min(1, ua[0] * ub[0] + ua[1] * ub[1])))
    t = r / math.tan(al / 2)
    bi = (ua[0] + ub[0], ua[1] + ub[1]); lbi = math.hypot(*bi); bi = (bi[0] / lbi, bi[1] / lbi)
    c = (p[0] + bi[0] * r / math.sin(al / 2), p[1] + bi[1] * r / math.sin(al / 2))
    t1, t2 = (p[0] + ua[0] * t, p[1] + ua[1] * t), (p[0] + ub[0] * t, p[1] + ub[1] * t)
    w1, w2 = math.atan2(t1[1] - c[1], t1[0] - c[0]), math.atan2(t2[1] - c[1], t2[0] - c[0])
    d = (w2 - w1 + math.pi) % (2 * math.pi) - math.pi
    bo = [(c[0] + r * math.cos(w1 + d * k / n), c[1] + r * math.sin(w1 + d * k / n)) for k in range(n + 1)]
    return pkt[:i] + bo + pkt[i + 1:]


class Svg:
    def __init__(self, x0, y0, x1, y1, s, rand=60, breite_extra=0):
        self.x0, self.y1, self.s, self.r = x0, y1, s, rand
        self.b = (x1 - x0) * s + 2 * rand + breite_extra
        self.h = (y1 - y0) * s + 2 * rand
        self.e = []

    def P(self, x, y):
        return (self.r + (x - self.x0) * self.s, self.r + (self.y1 - y) * self.s)

    def poly(self, pts, fill="none", stroke="#222", sw=1.2, dash=None, op=1):
        d = " ".join(f"{a:.2f},{b:.2f}" for a, b in (self.P(*q) for q in pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.e.append(f'<polygon points="{d}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" stroke-width="{sw}"{da}/>')

    def linie(self, pts, stroke="#222", sw=1.2, dash=None):
        d = " ".join(f"{a:.2f},{b:.2f}" for a, b in (self.P(*q) for q in pts))
        da = f' stroke-dasharray="{dash}"' if dash else ""
        self.e.append(f'<polyline points="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}"{da}/>')

    def text(self, x, y, t, size=12, anchor="start", farbe="#111", dx=0, dy=0, fett=False):
        a, b = self.P(x, y)
        fw = ' font-weight="bold"' if fett else ""
        self.e.append(f'<text x="{a + dx:.1f}" y="{b + dy:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{farbe}"'
                      f' font-family="Segoe UI, Arial"{fw}>{t}</text>')

    def text_px(self, a, b, t, size=12, anchor="start", farbe="#111", fett=False):
        fw = ' font-weight="bold"' if fett else ""
        self.e.append(f'<text x="{a:.1f}" y="{b:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{farbe}"'
                      f' font-family="Segoe UI, Arial"{fw}>{t}</text>')

    def speichern(self, pfad):
        kopf = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.b:.0f}" height="{self.h:.0f}" '
                f'viewBox="0 0 {self.b:.0f} {self.h:.0f}"><rect width="100%" height="100%" fill="white"/>')
        open(pfad, "w", encoding="utf-8").write(kopf + "\n".join(self.e) + "</svg>")
        print(pfad)


def schieber():
    s, p, f = lade("schieber.yaml")
    KX = p["KX"]
    k = f["f1"]["skizze"]["elemente"][0]["kontur"]
    oben = [(w(k["start"][0], p) - KX, w(k["start"][1], p))]
    for seg in k["segmente"]:
        if "linie" in seg:
            oben.append((w(seg["linie"][0], p) - KX, w(seg["linie"][1], p)))
        else:
            m = (w(seg["mitte"][0], p) - KX, w(seg["mitte"][1], p))
            oben += bogen_pkt(m, oben[-1], (w(seg["bogen"][0], p) - KX, w(seg["bogen"][1], p)))
    oben = oben[:-1]
    # V-Grund-Verrundung (v1) an der Ecke (0, VG)
    iv = min(range(len(oben)), key=lambda i: math.hypot(oben[i][0], oben[i][1] - p["VG"]))
    oben = verrunde(oben, iv, p["RV"])
    # untere Ebene: Umriss oben, aber hinter der Taschenkante die Tasche (Polygon t1 mit Radien)
    tp = [(w(a, p) - KX, w(b, p)) for a, b in f["t1"]["skizze"]["elemente"][0]["polygon"]["punkte"]]
    TB, TT, VG = p["TB"], p["TT"], p["VG"]
    yk, yg = VG - TB / 2, VG - TB / 2 + TT
    hb = p["BB"] / 2 - p["SP"]
    # untere Kontur: linke Spitze bis Fase, Taschenkante R RM, Taschenwand, Grund R RK, rechts gespiegelt
    li = [q for q in oben if q[0] <= -TB / 2 - 1e-9 and q[1] < VG]
    li_spitze = [q for q in oben if q[0] < -hb + 1.0 and q[1] < VG - hb + 2]
    roh = [(-hb, VG + p["SPL"])] + [q for q in oben if q[0] < 0 and q[1] < VG - 1 and q[0] <= -TB / 2][0:]
    roh = [q for q in roh if not (q[0] > -TB / 2)]
    unten = roh + [(-TB / 2, yk), (-TB / 2, yg), (TB / 2, yg), (TB / 2, yk)]
    rechts = [(-x, y) for x, y in roh[::-1]]
    unten = unten + rechts
    # Radien Taschenkante und Grund
    for ziel, r in (((-TB / 2, yk), p["RM"]), ((-TB / 2, yg), p["RK"]), ((TB / 2, yg), p["RK"]), ((TB / 2, yk), p["RM"])):
        i = min(range(len(unten)), key=lambda j: math.hypot(unten[j][0] - ziel[0], unten[j][1] - ziel[1]))
        unten = verrunde(unten, i, r)

    y0, y1 = 270.5, 290.5
    g = Svg(-14, y0, 14, y1, 19, rand=50, breite_extra=470)
    # Bahnwände, Schacht-Rückwand
    for sx in (-1, 1):
        g.poly([(sx * 11, y0), (sx * 13.5, y0), (sx * 13.5, y1), (sx * 11, y1)], fill="#cfd6dd", stroke="#7a8794", sw=0.8)
    for yy, t in ((274.071, "Schacht-Rückwand innen Y 274,07"), (276.071, "außen 276,07")):
        g.linie([(-13.5, yy), (13.5, yy)], stroke="#2a7f3f", sw=1.2, dash="6,4")
        g.text(13.6, yy, t, 11, farbe="#2a7f3f", dy=4)
    g.poly(unten, fill="#f2a64c", stroke="#b5651d", sw=1.2, op=0.85)
    g.poly(oben, fill="#5b8fd6", stroke="#1f4f99", sw=1.8, op=0.25)
    # Maße
    def mass_x(xa, xb, y, t, dy=-8):
        g.linie([(xa, y), (xb, y)], stroke="#111", sw=0.8)
        for xx in (xa, xb):
            g.linie([(xx, y - 0.25), (xx, y + 0.25)], stroke="#111", sw=0.8)
        g.text((xa + xb) / 2, y, t, 11, "middle", dy=dy)
    mass_x(-TB / 2, TB / 2, yg + 1.6, "Tasche 15 (Wände parallel zur Schubrichtung)")
    mass_x(-hb, hb, y0 + 1.2, "Platte 21,6 (0,2 Spiel je Seite)", dy=15)
    mass_x(-hb, -TB / 2, yk - 3.0, "Steg 3,3", dy=-6)
    g.text(0, yg, "Taschengrund Y 286,5 (Pos. 2: 234,5)", 11, "middle", dy=-24, farbe="#7a3c00")
    g.text(0, 283.2, "V-Grund R 2,1 (oben)", 11, "middle", farbe="#1f4f99", dy=18)
    g.text(-TB / 2, yk, "Taschenkante R 1, Y 277,5", 11, "start", dx=6, dy=-4, farbe="#7a3c00")
    g.text(TB / 2, yk + 6, "Tasche 9 tief", 11, "end", dx=-6, farbe="#7a3c00")
    g.text(-hb, 274.2, "Spitze R 1 „an der Wand“, vorderster Punkt Y 274,61", 11, "start", dx=8, dy=30, farbe="#111")
    g.text(4.5, 279.5, "45°-Fase / V-Flanke", 11, "start", farbe="#111")
    g.text(-1.5, 285.0, "theor. V-Spitze 285,0", 10, "end", farbe="#1f4f99", dy=4)
    # Legende
    lx, ly = g.P(14, y1)
    lx += 120; ly += 10
    g.text_px(lx, ly, "Schieberstirn D1 – Draufsicht Pos. 1 (Maße mm, Y Maschine)", 15, fett=True)
    zeilen = [("#5b8fd6", "obere Ebene 3,0 … 6,4 über der Bahn: V-Kerbe 90°, von oben gefräst"),
              ("#f2a64c", "untere Ebene 0,2 … 3,0: Fase 45° + Tasche 15 × 9, von unten 2,8 tief"),
              ("#cfd6dd", "Bahnwände / Klemmleisten (Bahn 22)")]
    for i, (fa, t) in enumerate(zeilen):
        g.e.append(f'<rect x="{lx:.1f}" y="{ly + 22 + i * 22:.1f}" width="16" height="12" fill="{fa}" stroke="#555"/>')
        g.text_px(lx + 24, ly + 33 + i * 22, t, 12)
    info = ["Werkstoff 1.2312, ohne Gleiteinsatz (Worst Case µ 0,60 gerechnet)",
            "Fräser Ø 4: Innenradien R 2,1 (Taschengrund, V-Grund)",
            "Spitzen Y 274,2 (theor.), 0,1 hinter der Schacht-Rückwand",
            "Hub Pos. 1 → 2: 52 (ADNM 52Z1-82Z2), Pos. 3: 82",
            "Ergebnis Simulation (Worst Case, Stirn D1):",
            "  99,05 % prüfbar im Feld 22 × 22, 98,8 % mit heutiger",
            "  Kamera bei voller Sensorhöhe und m 0,200",
            "Quelle: schieber.yaml (v5), Simulation v-schieber-2026-10-16"]
    for i, t in enumerate(info):
        g.text_px(lx, ly + 110 + i * 19, t, 12)
    # Schnitt A–A (x = 0) klein unten rechts
    sx0, sy0, sk = lx + 10, ly + 300, 14
    g.text_px(sx0, sy0 - 12, "Längsschnitt Mitte (x = 0), Z über der Bahn", 12, fett=True)
    def ps(y, z):
        return (sx0 + (y - 272) * sk, sy0 + (8 - z) * sk)
    ygv = VG - p["RV"] * 2 ** 0.5 + p["RV"]
    for poly, fa in (([(ygv, 3.0), (295, 3.0), (295, 6.4), (ygv, 6.4)], "#5b8fd6"),
                     ([(yg, 0.2), (295, 0.2), (295, 3.0), (yg, 3.0)], "#f2a64c")):
        d = " ".join(f"{a:.1f},{b:.1f}" for a, b in (ps(*q) for q in poly))
        g.e.append(f'<polygon points="{d}" fill="{fa}" fill-opacity="0.6" stroke="#333"/>')
    a, b = ps(272, 0); c, e = ps(295, 0)
    g.e.append(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{e}" stroke="#555" stroke-width="2"/>')
    g.text_px(a, b + 16, "Bahn-OK", 11)
    g.text_px(ps(ygv, 6.4)[0] - 4, ps(ygv, 6.4)[1] - 4, f"V-Grund {ygv:.2f}", 11, "end")
    g.text_px(ps(yg, 0.2)[0] - 4, ps(yg, 0.2)[1] + 2, "Grund 286,5", 11, "end")
    g.text_px(ps(295, 6.4)[0] + 4, ps(295, 6.4)[1] + 4, "6,4", 11)
    g.text_px(ps(295, 3.0)[0] + 4, ps(295, 3.0)[1] + 4, "3,0", 11)
    g.text_px(ps(295, 0.2)[0] + 4, ps(295, 0.2)[1] + 4, "0,2", 11)
    g.speichern(os.path.join(HIER, "skizze_v5_schieber_d1.svg"))


def fallschacht():
    s, p, f = lade("fallschacht.yaml")
    aussen = [(w(a, p), w(b, p)) for a, b in f["f1"]["skizze"]["elemente"][0]["polygon"]["punkte"]]
    innen = [(w(a, p), w(b, p)) for a, b in f["f3"]["skizze"]["elemente"][0]["polygon"]["punkte"]]
    sch, ps_, _ = lade("schieber.yaml")
    sp = ps_
    BZ = -145
    g = Svg(195, -150, 395, -60, 4.2, rand=60, breite_extra=0)
    g.h += 150
    # Kanal, Glas
    g.poly([(207.5, BZ - 10), (383, BZ - 10), (383, BZ), (207.5, BZ)], fill="#cfd6dd", stroke="#7a8794", sw=0.8)
    g.poly([(209.5, BZ - 2), (243.5, BZ - 2), (243.5, BZ), (209.5, BZ)], fill="#9fd8f0", stroke="#3a87a8", sw=0.8)
    g.linie([(207.5, BZ + 6), (383, BZ + 6)], stroke="#7a8794", sw=0.8, dash="3,3")
    g.text(383, BZ + 6, "Wand-OK 6,0", 10, "end", dy=-3, farbe="#7a8794")
    # Schacht: außen grau, innen weiß (Seitenwände sind im Schnitt nicht zu sehen)
    g.poly([q for q in aussen], fill="#bfbfbf", stroke="#444", sw=1)
    g.poly([q for q in innen], fill="white", stroke="#444", sw=1)
    # Schieber Pos. 1 und Pos. 3 (Schnitt Mitte: Platte bis V-Grund, Kopf)
    VG, SPL = sp["VG"], sp["SPL"]
    ygv = VG - sp["RV"] * 2 ** 0.5 + sp["RV"]
    for hub, farbe, name in ((0, "#5b8fd6", "Pos. 1"), (82, "#9db9e3", "Pos. 3")):
        g.poly([(ygv - hub, BZ + 3), (VG + SPL - hub, BZ + 3), (VG + SPL - hub, BZ + 6.4), (ygv - hub, BZ + 6.4)],
               fill=farbe, stroke="#1f4f99", sw=0.8, op=0.8)
        g.poly([(286.5 - hub, BZ + 0.2), (VG + SPL - hub, BZ + 0.2), (VG + SPL - hub, BZ + 3), (286.5 - hub, BZ + 3)],
               fill="#f2a64c", stroke="#b5651d", sw=0.8, op=0.8)
        g.poly([(VG + SPL - 25 - hub, BZ + 6), (VG + SPL - hub, BZ + 6), (VG + SPL - hub, BZ + 6 + sp["KH"]), (VG + SPL - 25 - hub, BZ + 6 + sp["KH"])],
               fill=farbe, stroke="#1f4f99", sw=0.8, op=0.8)
        g.text(VG + SPL - 12.5 - hub, BZ + 6 + sp["KH"], f"Kopf {name}", 10, "middle", dy=-4, farbe="#1f4f99")
    g.text(VG + SPL - 82 - 25, BZ + 6 + sp["KH"], "1,9 Luft zur Rückwand", 10, "end", dx=-4, dy=-4, farbe="#1f4f99")
    # Kamera
    for y, t, fa, an, dx in ((224.65, "Kameraachse Y 224,65", "#c0392b", "end", -4), (226.5, "Prüfmitte Y 226,5", "#555", "start", 4)):
        g.linie([(y, BZ - 2), (y, -60)], stroke=fa, sw=1, dash="8,4")
        g.text(y, -60, t, 11, an, dx=dx, dy=-6, farbe=fa)
    g.poly([(224.65 - 13.05, BZ + 0.05), (224.65 + 13.05, BZ + 0.05), (224.65 + 13.05, BZ + 0.6), (224.65 - 13.05, BZ + 0.6)],
           fill="#c0392b", stroke="none", op=0.6)
    g.text(224.65, BZ, "Bildfeld 26,1 (Schubrichtung)", 10, "middle", dy=26, farbe="#c0392b")
    g.text(208, BZ - 10, "Abgabekante 207,5", 10, "start", dy=14)
    # Beschriftung Schacht
    g.text(253, -128, "Front offen unter 15", 10, "end", dx=-40, farbe="#111")
    g.text(250, -122, "Prallkeil vorn 40°", 10, "start", farbe="#111")
    g.text(262, -101, "Prallplatte hinten 40°", 10, "start", dx=4, farbe="#111")
    g.text(276.1, -95, "verbreitert +10", 10, "start", dx=6, farbe="#111")
    g.text(266, -88, "Knick Z −90,5", 10, "start", dx=6, farbe="#111")
    g.text(256, -70, "geneigt 67,6°", 10, "start", dx=8, farbe="#111")
    g.text(320, -150, "vorn ← Y →  hinten", 11, "middle", dy=22)
    g.text_px(20, g.h - 120, "Fallschacht 7b und Schieber D1 – Schnitt Kanalachse X −170 (Y-Z), Maße mm", 15, fett=True)
    for i, t in enumerate(["Schacht: Achse oben Y 305 / Z 35 und unten Y 253,25 / Z −138,5 wie bisher; senkrechtes Ende 48,",
                           "Rückwand innen Y 274,07; Durchlässe 15,73 (> Messerlänge 12, > Raumdiagonale 14,45); ABS-Druck.",
                           "Schieber 6,4 hoch fährt 0,1 unter dem Schachtende (Z −138,5) durch; Tubus entfällt.",
                           "Quelle: fallschacht.yaml / schieber.yaml (v5), Simulation varianten-2026-10-16 (Variante 7b)."]):
        g.text_px(20, g.h - 95 + i * 19, t, 12)
    g.speichern(os.path.join(HIER, "skizze_v5_fallschacht_7b.svg"))


def kamerahalter():
    s, p, f = lade("kamerahalter.yaml")
    _, ps_, _ = lade("kamerasaeule.yaml")
    X0, Y0, TA, XK, TB, Y2, Z0, H, KY = (p[k] for k in ("X0", "Y0", "TA", "XK", "TB", "Y2", "Z0", "H", "KY"))
    KX = -170
    # Draufsicht (X-Y), links; Seitenansicht von −X (Y-Z), rechts
    g = Svg(-255, 155, -145, 250, 4.0, rand=50, breite_extra=560)
    g.h += 40
    def rect(x0, y0, x1, y1, fa, st="#333", op=1.0, sw=1):
        g.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=fa, stroke=st, sw=sw, op=op)
    rect(ps_["X0"], ps_["Y0"], ps_["X0"] + ps_["B"], ps_["Y1"], "#cfd6dd")
    g.text(ps_["X0"] + 15, ps_["Y0"] + 12, "Kamerasäule", 11, "middle")
    rect(X0, Y0, XK, Y0 + TA, "#9cc58f")
    rect(XK - TB, Y0, XK, Y2, "#9cc58f")
    g.text(-215, Y0 + TA, "Schenkel A (Langlöcher ±15)", 11, "middle", dy=16)
    g.text(XK - TB, (Y0 + Y2) / 2 + 12, "Schenkel B", 11, "end", dx=-6)
    rect(XK, KY - 14.5, XK + 29, KY + 14.5, "#5b8fd6", op=0.5)
    g.text(KX, KY + 14.5, "Kamera (90° gedreht)", 11, "middle", dy=-6, farbe="#1f4f99")
    # Sensor lange Seite in Y
    g.linie([(KX, KY - 13.05), (KX, KY + 13.05)], stroke="#c0392b", sw=2.5)
    g.text(KX + 2, KY, "lange Sensorseite / Bildfeld 26,1 in Y", 11, "start", farbe="#c0392b")
    for (y, z) in [(KY + 10.5, 0), (KY - 10.5, 0), (KY, 1)]:
        g.linie([(XK - TB - 4, y), (XK + 4, y)], stroke="#c0392b", sw=1, dash="3,2")
    g.text(XK - TB, KY - 10.5, "3 × M3 × 10 von −X", 10, "end", dx=-6, dy=4)
    g.linie([(KX, 160), (KX, 248)], stroke="#555", sw=0.8, dash="8,4")
    g.text(KX, 160, "Kanalachse X −170", 10, "middle", dy=14)
    g.linie([(-255, KY), (-145, KY)], stroke="#c0392b", sw=0.8, dash="8,4")
    g.text(-255, KY, "Kameraachse Y 224,65", 10, "start", dy=-4, farbe="#c0392b")
    g.linie([(-255, 207.5), (-145, 207.5)], stroke="#777", sw=0.8, dash="2,3")
    g.text(-145, 207.5, "Abgabekante 207,5", 10, "end", dy=12, farbe="#777")
    g.text(-200, 250, "Draufsicht (X-Y), vorn = unten", 13, "middle", dy=-8, fett=True)
    # Seitenansicht von −X: Y nach rechts, Z nach oben
    lx0, ly0, sk = g.b - 520, 70, 4.0
    def P(y, z): return (lx0 + (y - 185) * sk, ly0 + (85 - z) * sk)
    def rz(y0_, z0_, y1_, z1_, fa, op=1.0):
        q = [P(y0_, z0_), P(y1_, z0_), P(y1_, z1_), P(y0_, z1_)]
        g.e.append('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in q) + f'" fill="{fa}" fill-opacity="{op}" stroke="#333"/>')
    rz(Y0, Z0, Y2, Z0 + H, "#9cc58f")
    for (y, z) in [(KY + 10.5, Z0 + 8.82), (KY - 10.5, Z0 + 8.82), (KY, Z0 + 52.96)]:
        a, b = P(y, z)
        g.e.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{3.25*sk:.1f}" fill="white" stroke="#333"/>')
        g.e.append(f'<circle cx="{a:.1f}" cy="{b:.1f}" r="{1.7*sk:.1f}" fill="none" stroke="#333"/>')
    rz(KY - 15.9, Z0 - 51.0, KY + 15.9, Z0, "#bbbbbb", 0.7)
    a, b = P(KY, Z0 - 25); g.text_px(a, b, "Objektiv", 11, "middle")
    a, b = P(KY - 13.05, Z0 + 2); c, d = P(KY + 13.05, Z0 + 2)
    g.e.append(f'<line x1="{a:.1f}" y1="{b:.1f}" x2="{c:.1f}" y2="{d:.1f}" stroke="#c0392b" stroke-width="2.5"/>')
    a, b = P(Y0, Z0 + H); g.text_px(a, b - 8, "Schenkel B von außen (−X), Kamera dahinter", 13, fett=True)
    for z, tx in ((Z0, "Z 17,9 = Objektivanlage (Mittellage)"), (Z0 + H, "Z 77,9")):
        a, b = P(Y2, z); g.text_px(a + 6, b + 4, tx, 10)
    a, b = P(Y0, Z0 - 56); g.text_px(a, b, "Y 192,5 … 241; Bohrungen Y 214,15 / 235,15 (Z 26,72) und 224,65 (Z 70,86)", 11)
    a, b = P(Y0, Z0 - 60); g.text_px(a, b + 16, "Alu 6061, Schenkel je 10 dick; Säule wie bisher, M5 × 20 in die Säule", 11)
    g.speichern(os.path.join(HIER, "skizze_v5_kamerahalter_winkel.svg"))


schieber()
fallschacht()
kamerahalter()
