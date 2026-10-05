"""Draw a labelled model-space grid over the views from render_grid.py.

grid_overlay.py <prefix> [view ...]   ->  <prefix>_<view>_grid.jpg

Horizontal axis per view (model units, Blender axes): front = x, back = -x,
right = y, left = -y. Vertical axis is always z.
"""
import sys

from PIL import Image, ImageDraw

SPAN = 2.2
AXIS = {"front": ("x", 1), "back": ("x", -1), "right": ("y", 1), "left": ("y", -1)}

prefix = sys.argv[1]
for view in sys.argv[2:] or AXIS:
    img = Image.open(f"{prefix}_{view}.png").convert("RGB")
    res = img.width
    draw = ImageDraw.Draw(img)
    name, sign = AXIS[view]
    for i in range(-10, 11):
        v = i / 10
        major = i % 5 == 0
        color = (255, 60, 60) if major else (120, 160, 255)
        px = (v / SPAN + 0.5) * res
        draw.line([(px, 0), (px, res)], fill=color, width=1)
        draw.text((px + 2, 2), f"{name}={sign * v:+.1f}", fill=(0, 0, 0))
        py = (0.5 - v / SPAN) * res
        draw.line([(0, py), (res, py)], fill=color, width=1)
        draw.text((2, py + 1), f"z={v:+.1f}", fill=(0, 0, 0))
    img.save(f"{prefix}_{view}_grid.jpg", quality=92)
