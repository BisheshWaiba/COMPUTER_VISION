"""Prepare the photo that paints a figure, for figures whose spec has a "texture" entry.

Run from asset_pipeline/ (after 01 and 02, before 03):
    .venv/Scripts/python.exe scripts/05_prepare_texture.py [figure ...]

For each such figure this
  1. cuts the person out of the reference photo
  2. finds how the raw mesh lines up with the photo, by searching for the position
     and scale where the mesh's front outline best covers the person's outline
  3. cleans the photo's edges (no background colour bleeding onto the model)
  4. builds one picture, the "atlas": the photo, with a strip of flat colour
     swatches under it for the parts of the model the photo cannot see
  5. writes input_images/texture/<figure>_atlas.png, <figure>_uv.json and a
     <figure>_alignment.jpg to check the fit by eye

03_split_parts.py then looks every vertex up in this picture.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import trimesh
from PIL import Image
from rembg import new_session, remove
from scipy.ndimage import distance_transform_edt
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from figures_spec import FIGURES  # noqa: E402

ROOT = HERE.parent
SRC = ROOT / "input_images" / "source"
RAW = ROOT / "raw_meshes"
OUT = ROOT / "input_images" / "texture"

PHOTO = 1024      # the photo is stored at this size, square
SWATCH = 64       # each flat-colour swatch is SWATCH x SWATCH pixels
EDGE_ERODE = 3    # pixels trimmed off the person's outline before colours are reused
RASTER = 1024     # resolution of the mesh outline used for the search
HALF = 1.1        # the outline covers x and z from -HALF to +HALF


def cut_out(photo_name):
    """The photo as a square RGB image, and a mask of the person."""
    img = Image.open(SRC / photo_name).convert("RGB")
    scale = PHOTO / max(img.size)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (PHOTO, PHOTO), img.getpixel((0, 0)))
    canvas.paste(img, ((PHOTO - img.width) // 2, (PHOTO - img.height) // 2))

    alpha = np.array(remove(canvas, session=new_session("birefnet-general")))[:, :, 3] > 127
    count, labels, stats, _ = cv2.connectedComponentsWithStats(alpha.astype(np.uint8))
    if count > 2:
        alpha = labels == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.array(canvas), alpha


def mesh_outline(mesh):
    """Front view of the mesh as a filled shape, on a RASTER x RASTER grid."""
    x, z = mesh.vertices[:, 0], mesh.vertices[:, 1]   # glTF: x right, y up
    cols = (x + HALF) * (RASTER - 1) / (2 * HALF)
    rows = (HALF - z) * (RASTER - 1) / (2 * HALF)
    triangles = np.stack([cols, rows], axis=1)[mesh.faces].astype(np.int32)
    outline = np.zeros((RASTER, RASTER), np.uint8)
    cv2.fillPoly(outline, list(triangles), 255)
    return outline


def warp_matrix(su, sz, tu, tz):
    """Maps outline pixels to photo pixels, where u = su*x + tu and v = -sz*z + tz."""
    k = 2 * HALF / (RASTER - 1)
    return np.array([[su * k, 0, tu - su * HALF], [0, sz * k, tz - sz * HALF]], np.float32)


def fit(outline, person, mesh):
    ys, xs = np.nonzero(person)
    x, z = mesh.vertices[:, 0], mesh.vertices[:, 1]
    su0 = (xs.max() - xs.min()) / (x.max() - x.min())
    sz0 = (ys.max() - ys.min()) / (z.max() - z.min())
    tu0 = xs.min() - su0 * x.min()
    tz0 = ys.min() + sz0 * z.max()

    def overlap(p):
        su, sz, tu, tz = su0 * p[0], sz0 * p[1], tu0 + 40 * p[2], tz0 + 40 * p[3]
        shape = cv2.warpAffine(outline, warp_matrix(su, sz, tu, tz), (PHOTO, PHOTO)) > 127
        return (shape & person).sum() / max((shape | person).sum(), 1)

    best = minimize(lambda p: -overlap(p), [1, 1, 0, 0], method="Nelder-Mead",
                    options=dict(xatol=1e-4, fatol=1e-6, maxiter=600,
                                 initial_simplex=[[1, 1, 0, 0], [1.03, 1, 0, 0], [1, 1.03, 0, 0],
                                                  [1, 1, 0.3, 0], [1, 1, 0, 0.3]]))
    p = best.x
    return su0 * p[0], sz0 * p[1], tu0 + 40 * p[2], tz0 + 40 * p[3], -best.fun


def median_colour(rgb, person, box, params):
    su, sz, tu, tz = params
    x0, z0, x1, z1 = box
    u0, u1 = sorted((int(su * x0 + tu), int(su * x1 + tu)))
    v0, v1 = sorted((int(-sz * z0 + tz), int(-sz * z1 + tz)))
    patch = rgb[v0:v1, u0:u1][person[v0:v1, u0:u1]]
    if len(patch) == 0:
        raise RuntimeError(f"swatch box {box} does not land on the person; check the alignment")
    return tuple(int(c) for c in np.median(patch, axis=0))


def hex_to_rgb(text):
    return tuple(int(text.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def prepare(name):
    spec = FIGURES[name]
    rgb, person = cut_out(spec["texture"]["photo"])
    mesh = trimesh.load(RAW / spec["raw_mesh"], force="mesh")
    su, sz, tu, tz, iou = fit(mesh_outline(mesh), person, mesh)
    print(f"{name}: outline overlap {iou:.3f}  scale {su:.0f}/{sz:.0f}  offset {tu:.0f}/{tz:.0f}")
    if iou < 0.85:
        print("  warning: low overlap, the photo may not match the mesh well")

    # pixels near or outside the person's edge take the colour of the nearest clean pixel
    clean = cv2.erode(person.astype(np.uint8), np.ones((2 * EDGE_ERODE + 1,) * 2, np.uint8)) > 0
    nearest = distance_transform_edt(~clean, return_distances=False, return_indices=True)
    photo = rgb[nearest[0], nearest[1]]

    swatches, atlas_height = {}, PHOTO + SWATCH
    strip = np.zeros((SWATCH, PHOTO, 3), np.uint8)
    for part in spec["parts"]:
        mode = part.get("back", "project")
        if mode == "project":
            continue
        colour = hex_to_rgb(mode) if mode.startswith("#") else median_colour(
            photo, clean, part["swatch_box"], (su, sz, tu, tz))
        index = len(swatches)
        strip[:, index * SWATCH:(index + 1) * SWATCH] = colour
        swatches[part["key"]] = [(index + 0.5) * SWATCH / PHOTO, 1 - (PHOTO + SWATCH / 2) / atlas_height]
        print(f"  {part['key']:<12} back colour #{colour[0]:02x}{colour[1]:02x}{colour[2]:02x}")

    OUT.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.vstack([photo, strip])).save(OUT / f"{name}_atlas.png")
    (OUT / f"{name}_uv.json").write_text(json.dumps(
        dict(photo=PHOTO, atlas_height=atlas_height, su=su, sz=sz, tu=tu, tz=tz, overlap=iou, swatches=swatches),
        indent=2) + "\n", encoding="utf-8")

    # preview: the mesh outline in red over the photo
    shape = cv2.warpAffine(mesh_outline(mesh), warp_matrix(su, sz, tu, tz), (PHOTO, PHOTO))
    contours, _ = cv2.findContours((shape > 127).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    preview = rgb.copy()
    cv2.drawContours(preview, contours, -1, (255, 0, 0), 2)
    Image.fromarray(preview).resize((768, 768), Image.LANCZOS).save(OUT / f"{name}_alignment.jpg", quality=92)


if __name__ == "__main__":
    names = sys.argv[1:] or [n for n, s in FIGURES.items() if s.get("texture")]
    for n in names:
        prepare(n)
