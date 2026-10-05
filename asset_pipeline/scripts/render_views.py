"""Render front / right / back / left views of a .glb so it can be checked by eye.

blender --background --python scripts/render_views.py -- <model.glb> <out_prefix> [object|material]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
glb, prefix = os.path.abspath(argv[0]), os.path.abspath(argv[1])
color_type = (argv[2] if len(argv) > 2 else "material").upper()

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]

corners = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector(min(c[i] for c in corners) for i in range(3))
hi = Vector(max(c[i] for c in corners) for i in range(3))
center, size = (lo + hi) / 2, max(hi - lo)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = 900
scene.render.film_transparent = False
scene.world = bpy.data.worlds.new("w")
scene.world.color = (1, 1, 1)
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = color_type
shading.show_cavity = True
shading.show_shadows = False

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = size * 1.08
scene.collection.objects.link(cam)
scene.camera = cam

# Blender front view looks along +Y
for name, angle in (("front", 0), ("right", 90), ("back", 180), ("left", 270)):
    a = math.radians(angle)
    cam.location = center + Vector((math.sin(a), -math.cos(a), 0)) * size * 3
    cam.rotation_euler = (math.radians(90), 0, a)
    scene.render.filepath = f"{prefix}_{name}.png"
    bpy.ops.render.render(write_still=True)

print("OBJECTS", [(o.name, len(o.data.polygons)) for o in meshes])
print("BOUNDS", tuple(round(v, 3) for v in lo), tuple(round(v, 3) for v in hi))
