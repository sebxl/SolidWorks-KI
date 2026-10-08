"""Exportiert die Umgebung der Schleifmaschine als STL (mm, Blender-Koordinaten = Koordinaten der Vorgabe AP68 3.1).
statisch/: nach Fotos ergaenzte, feste Teile (ohne SolidWorks-Herkunft)
tisch_C1/, tisch_C2/: alle Teile der Tischgruppe in Tischstellung C1 (Bild 0) bzw. C2 (Bild 656)
spindel/: Spindelgruppe in Bild 0"""
import bpy, os, re, sys, json
ziel = sys.argv[-1]
sc = bpy.context.scene

def wurzel(o):
    while o.parent: o = o.parent
    return o

def ist_cad(o):
    return re.search(r"STEP|stp", o.name, re.I) is not None

AUSSCHLUSS = re.compile(r"^(Boden|Messer [+-]\d+|Schrott [+-]\d+)$")
def gruppen():
    g = {"statisch": [], "tisch": [], "spindel": []}
    for o in sc.objects:
        if o.type != 'MESH' or o.hide_render or AUSSCHLUSS.match(o.name):
            continue
        w = wurzel(o).name
        if w == "J_Tisch_Rahmen": g["tisch"].append(o)
        elif w == "J_Spindel_Rahmen": g["spindel"].append(o)
        elif not ist_cad(o): g["statisch"].append(o)
    return g

def dateiname(n):
    return re.sub(r'[^0-9A-Za-z_.+-]+', '_', n)[:120] + ".stl"

def exportiere(objs, ordner, frame):
    sc.frame_set(frame)
    os.makedirs(ordner, exist_ok=True)
    liste = []
    for o in objs:
        bpy.ops.object.select_all(action='DESELECT')
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        f = os.path.join(ordner, dateiname(o.name))
        bpy.ops.wm.stl_export(filepath=f, export_selected_objects=True, global_scale=1000.0,
                              apply_modifiers=True, ascii_format=False, forward_axis='Y', up_axis='Z')
        liste.append({"objekt": o.name, "datei": os.path.basename(f)})
    json.dump(liste, open(os.path.join(ordner, "liste.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("EXPORT", ordner, len(liste))

g = gruppen()
exportiere(g["statisch"], os.path.join(ziel, "statisch"), 0)
exportiere(g["spindel"], os.path.join(ziel, "spindel"), 0)
exportiere(g["tisch"], os.path.join(ziel, "tisch_C1"), 0)
exportiere(g["tisch"], os.path.join(ziel, "tisch_C2"), 656)
