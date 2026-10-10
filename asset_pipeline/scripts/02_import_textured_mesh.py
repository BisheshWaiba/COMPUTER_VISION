"""Bring in a mesh that was generated elsewhere and already has its own texture
(for example a ComfyUI Pixal3D / TRELLIS.2 export), and shrink it to app size.

blender --background --python scripts/02_import_textured_mesh.py -- <source.glb> <figure> [faces] [texture_px]

This takes the place of steps 01, 02 and 05 for such a figure. It
  1. joins the source into one mesh and reduces it to about `faces` triangles (default
     60000), then splits any triangle edge longer than MAX_EDGE: reducing a mesh leaves long
     thin triangles on flat cloth, and since a part is made of whole triangles, a sash would
     otherwise "bleed" down a skirt
  2. keeps only the base colour picture, resized to `texture_px` (default 2048), and
     drops the normal / roughness / metallic maps the app does not use
  3. centres the figure and scales it to span -1..1, like the Hunyuan3D-2 meshes, so
     the part rules in figures_spec.py are written in the same coordinates
  4. writes raw_meshes/<figure>.glb

Give the figure "texture": {"own": True} in figures_spec.py so 03_split_parts.py keeps
this texture instead of painting the figure itself.
"""
import os
import sys

import bmesh
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
source, figure = os.path.abspath(argv[0]), argv[1]
target_faces = int(argv[2]) if len(argv) > 2 else 60000
texture_px = int(argv[3]) if len(argv) > 3 else 2048

MAX_EDGE = 0.035  # longest triangle edge allowed, in the -1..1 units of the finished raw mesh

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw_meshes")

bpy.ops.wm.read_factory_settings(use_empty=True)
# a textured .glb stores every texture seam as separate vertices, which leaves the surface in
# thousands of loose pieces; merging them back makes it one skin that reduces cleanly
bpy.ops.import_scene.gltf(filepath=source, merge_vertices=True)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1:
    bpy.ops.object.join()
obj = bpy.context.view_layer.objects.active
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# the picture wired into Base Color is the only one the app uses
image = None
for material in obj.data.materials:
    bsdf = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf and bsdf.inputs["Base Color"].links:
        node = bsdf.inputs["Base Color"].links[0].from_node
        if node.type == "TEX_IMAGE" and node.image:
            image = node.image
            break
if image is None:
    sys.exit("no base colour texture found in " + source)

before = len(obj.data.polygons)
modifier = obj.modifiers.new("reduce", "DECIMATE")
modifier.ratio = min(1.0, target_faces / before)
bpy.ops.object.modifier_apply(modifier="reduce")

# centre, and scale the longest side to 2 units
corners = [v.co.copy() for v in obj.data.vertices]
low = [min(c[i] for c in corners) for i in range(3)]
high = [max(c[i] for c in corners) for i in range(3)]
scale = 2.0 / max(h - l for l, h in zip(low, high))
for v in obj.data.vertices:
    for i in range(3):
        v.co[i] = (v.co[i] - (low[i] + high[i]) / 2) * scale

bm = bmesh.new()
bm.from_mesh(obj.data)
for _ in range(8):
    too_long = [e for e in bm.edges if e.calc_length() > MAX_EDGE]
    if not too_long:
        break
    bmesh.ops.subdivide_edges(bm, edges=too_long, cuts=1)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
bm.to_mesh(obj.data)
bm.free()

if max(image.size) > texture_px:
    image.scale(texture_px, texture_px)
plain = bpy.data.materials.new(figure)
plain.use_nodes = True
bsdf = plain.node_tree.nodes["Principled BSDF"]
texture = plain.node_tree.nodes.new("ShaderNodeTexImage")
texture.image = image
plain.node_tree.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.8
bsdf.inputs["Metallic"].default_value = 0.0
obj.data.materials.clear()
obj.data.materials.append(plain)
obj.name = obj.data.name = figure

os.makedirs(RAW, exist_ok=True)
out = os.path.join(RAW, f"{figure}.glb")
bpy.ops.object.select_all(action="DESELECT")
obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_yup=True, use_selection=True,
                          export_image_format="JPEG", export_image_quality=88)
print(f"IMPORTED {figure}: {before} -> {len(obj.data.polygons)} faces, texture {tuple(image.size)}, "
      f"{os.path.getsize(out) / 1e6:.2f} MB")
