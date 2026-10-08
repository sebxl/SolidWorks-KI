import bpy, json, sys
from mathutils import Vector
out = []
sc = bpy.context.scene
for o in sc.objects:
    if o.type != 'MESH':
        continue
    bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
    root = o
    while root.parent: root = root.parent
    out.append({"n": o.name, "root": root.name, "parent": o.parent.name if o.parent else None,
                "colls": [c.name for c in o.users_collection], "vis": not o.hide_render,
                "verts": len(o.data.vertices), "min": [round(x*1000,1) for x in mn], "max": [round(x*1000,1) for x in mx]})
json.dump(out, open(sys.argv[-1], "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("OBJEKTE", len(out), "FRAME", sc.frame_current, sc.frame_start, sc.frame_end, "UNIT", sc.unit_settings.scale_length)
