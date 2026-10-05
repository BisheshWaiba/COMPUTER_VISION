"""Crop each source picture to the figure, remove the background, and save a
square RGBA image ready for Hunyuan3D-2.

Run from asset_pipeline/:  .venv/Scripts/python.exe scripts/01_prepare_images.py [name ...]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "input_images" / "source"
OUT = ROOT / "input_images" / "prepared"

# name -> (source file, crop box as fractions of width/height (l, t, r, b), rembg model)
JOBS = {
    "prithvi_narayan_shah": ("pns_statue.jpg", (0.10, 0.02, 0.72, 0.905), "birefnet-general"),
    "prithvi_narayan_shah_painting": ("pns_painting.jpg", (0.15, 0.02, 0.85, 1.0), "birefnet-general"),
    "nepali_man": ("man_daura.jpg", (0.33, 0.34, 0.70, 0.65), "birefnet-general"),
    "nepali_man_v2": ("man_vest.jpg", (0.0, 0.0, 1.0, 1.0), "birefnet-general"),
    "nepali_woman_a": ("woman_kurtha_a.jpg", (0.18, 0.10, 0.82, 1.0), "birefnet-general"),
    "nepali_woman_b": ("woman_kurtha_b.jpg", (0.08, 0.13, 0.76, 0.97), "birefnet-general"),
}

SIZE = 1024
MARGIN = 0.06  # empty border around the figure, as a fraction of SIZE


def prepare(name):
    src, box, model = JOBS[name]
    img = Image.open(SRC / src).convert("RGB")
    w, h = img.size
    img = img.crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)))
    cut = remove(img, session=new_session(model))

    # keep only the largest connected blob so stray background pieces are dropped
    alpha = np.array(cut)[:, :, 3]
    import cv2
    n, labels, stats, _ = cv2.connectedComponentsWithStats((alpha > 127).astype(np.uint8))
    if n > 2:
        keep = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        arr = np.array(cut)
        arr[labels != keep] = 0
        cut = Image.fromarray(arr)

    cut = cut.crop(cut.getchannel("A").point(lambda a: 255 if a > 127 else 0).getbbox())
    inner = int(SIZE * (1 - 2 * MARGIN))
    scale = inner / max(cut.size)
    cut = cut.resize((max(1, round(cut.width * scale)), max(1, round(cut.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    canvas.paste(cut, ((SIZE - cut.width) // 2, (SIZE - cut.height) // 2))
    OUT.mkdir(parents=True, exist_ok=True)
    canvas.save(OUT / f"{name}.png")

    # white-background preview for checking the cut-out by eye
    preview = Image.new("RGB", (SIZE, SIZE), (255, 255, 255))
    preview.paste(canvas, mask=canvas.getchannel("A"))
    preview.resize((512, 512)).save(OUT / f"{name}_preview.jpg")
    print("prepared", name)


if __name__ == "__main__":
    for n in sys.argv[1:] or JOBS:
        prepare(n)
