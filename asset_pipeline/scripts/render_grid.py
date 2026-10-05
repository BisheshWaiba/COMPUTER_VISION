"""Render fixed-scale orthographic views of a .glb for marking out parts.

blender --background --python scripts/render_grid.py -- <model.glb> <out_prefix> [object|material]

Every view is centred on the origin and covers SPAN model units, so a pixel maps
straight to model coordinates (see grid_overlay.py).
"""
import math
import os
import sys

import bpy
from mathutils import Vector

SPAN = 2.2
RES = 1000

argv = sys.argv[sys.argv.index("--") + 1:]
glb, prefix = os.path.abspath(argv[0]), os.path.abspath(argv[1])
color_type = (argv[2] if len(argv) > 2 else "material").upper()

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = RES
scene.world = bpy.data.worlds.new("w")
scene.world.color = (1, 1, 1)
shading = scene.display.shading
shading.light = "STUDIO"
shading.color_type = color_type
shading.show_cavity = True

cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.type = "ORTHO"
cam.data.ortho_scale = SPAN
scene.collection.objects.link(cam)
scene.camera = cam

for name, angle in (("front", 0), ("right", 90), ("back", 180), ("left", 270)):
    a = math.radians(angle)
    cam.location = Vector((math.sin(a), -math.cos(a), 0)) * 10
    cam.rotation_euler = (math.radians(90), 0, a)
    scene.render.filepath = f"{prefix}_{name}.png"
    bpy.ops.render.render(write_still=True)
