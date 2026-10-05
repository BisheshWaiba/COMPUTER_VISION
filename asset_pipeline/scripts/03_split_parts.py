"""Cut each raw mesh into named parts and export the finished .glb.

blender --background --python scripts/03_split_parts.py -- [figure ...]

For every figure in figures_spec.py this:
  1. labels each face with a part using the rules in the spec
  2. smooths the borders between parts and absorbs stray islands
  3. scales the figure to its real height and stands it on the ground
  4. splits it into one object per part, named after the part key
  5. exports assets/models/<figure>.glb
"""
import os
import sys
from collections import Counter, deque

import bmesh
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from figures_spec import FIGURES  # noqa: E402

PIPELINE = os.path.dirname(HERE)
RAW = os.path.join(PIPELINE, "raw_meshes")
OUT = os.path.join(os.path.dirname(PIPELINE), "assets", "models")

SMOOTH_PASSES = 4
MIN_ISLAND_FACES = 120


def inside(poly, u, v):
    hit = False
    j = len(poly) - 1
    for i in range(len(poly)):
        (ui, vi), (uj, vj) = poly[i], poly[j]
        if (vi > v) != (vj > v) and u < (uj - ui) * (v - vi) / (vj - vi) + ui:
            hit = not hit
        j = i
    return hit


def label_face(center, parts, default_index):
    x, y, z = center
    for index, part in enumerate(parts):
        for view, poly, (lo, hi) in part.get("rules", ()):
            u, depth = (x, y) if view == "front" else (y, x)
            if lo <= depth <= hi and inside(poly, u, z):
                return index
    return default_index


def srgb_to_linear(hex_color):
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    h = hex_color.lstrip("#")
    return tuple(channel(int(h[i:i + 2], 16)) for i in (0, 2, 4)) + (1.0,)


def build(name):
    spec = FIGURES[name]
    parts = spec["parts"]
    default_index = next(i for i, p in enumerate(parts) if p.get("default"))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(RAW, spec["raw_mesh"]))
    obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
    for other in [o for o in bpy.context.scene.objects if o is not obj]:
        bpy.data.objects.remove(other)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    labels = [label_face(f.calc_center_median(), parts, default_index) for f in bm.faces]
    neighbours = [[g.index for e in f.edges for g in e.link_faces if g is not f] for f in bm.faces]

    # majority vote with the neighbours to straighten ragged borders
    for _ in range(SMOOTH_PASSES):
        new = labels[:]
        for i, near in enumerate(neighbours):
            votes = Counter(labels[j] for j in near)
            if votes:
                top, count = votes.most_common(1)[0]
                if top != labels[i] and count >= 2:
                    new[i] = top
        labels = new

    # hand small disconnected islands to whichever part surrounds them
    seen = [False] * len(labels)
    for start in range(len(labels)):
        if seen[start]:
            continue
        island, border, queue = [], Counter(), deque([start])
        seen[start] = True
        while queue:
            i = queue.popleft()
            island.append(i)
            for j in neighbours[i]:
                if labels[j] != labels[start]:
                    border[labels[j]] += 1
                elif not seen[j]:
                    seen[j] = True
                    queue.append(j)
        if len(island) < MIN_ISLAND_FACES and border:
            target = border.most_common(1)[0][0]
            for i in island:
                labels[i] = target

    # real-world size, feet on the ground, centred
    zs = [v.co.z for v in bm.verts]
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    scale = spec["height_m"] / (max(zs) - min(zs))
    cx, cy, z0 = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, min(zs)
    for v in bm.verts:
        v.co.x, v.co.y, v.co.z = (v.co.x - cx) * scale, (v.co.y - cy) * scale, (v.co.z - z0) * scale

    obj.data.materials.clear()
    for part in parts:
        mat = bpy.data.materials.new(part["key"])
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = srgb_to_linear(part["color"])
        bsdf.inputs["Roughness"].default_value = 0.8
        bsdf.inputs["Metallic"].default_value = 0.0
        mat.diffuse_color = srgb_to_linear(part["color"])
        obj.data.materials.append(mat)
    for f, label in zip(bm.faces, labels):
        f.material_index = label
        f.smooth = True
    bm.to_mesh(obj.data)
    bm.free()

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="MATERIAL")
    bpy.ops.object.mode_set(mode="OBJECT")

    root = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(root)
    counts = {}
    for piece in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        bpy.context.view_layer.objects.active = piece
        bpy.ops.object.material_slot_remove_unused()
        key = piece.data.materials[0].name
        piece.name = piece.data.name = key
        piece.parent = root
        counts[key] = len(piece.data.polygons)

    missing = [p["key"] for p in parts if p["key"] not in counts]
    if missing:
        raise RuntimeError(f"{name}: parts with no faces: {missing}")

    os.makedirs(OUT, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"{name}.glb"), export_format="GLB",
                              export_yup=True, export_apply=True)
    print("BUILT", name, counts)


argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
for figure in argv or FIGURES:
    build(figure)
