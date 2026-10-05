"""Join the four view renders of a model into one image: contact_sheet.py <prefix>"""
import sys

from PIL import Image

prefix = sys.argv[1]
views = [Image.open(f"{prefix}_{v}.png").convert("RGB") for v in ("front", "right", "back", "left")]
sheet = Image.new("RGB", (sum(v.width for v in views), views[0].height), "white")
x = 0
for v in views:
    sheet.paste(v, (x, 0))
    x += v.width
sheet.save(f"{prefix}_sheet.jpg", quality=90)
