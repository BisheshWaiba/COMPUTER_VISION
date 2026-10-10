"""Prepare the photo that paints a figure, for figures whose spec has a "texture" entry.

Run from asset_pipeline/ (after 01 and 02, before 03):
    .venv/Scripts/python.exe scripts/05_prepare_texture.py [figure ...]

For each such figure this
  1. cuts the person out of the reference photo (a photo that is already a cut-out, with a
     transparent background, is used as it is: its transparency is the outline)
  2. finds how the raw mesh lines up with the photo, by searching for the position
     and scale where the mesh's front outline best covers the person's outline
  3. cleans the photo's edges (no background colour bleeding onto the model), and, if the
     spec has "clean_front", touches up the front photo itself (the same "copy" / "fill"
     steps as "clean_back", for something in the photo that lands on the wrong part of the mesh),
     and, if the spec has "grade", brings out a pale photo's colour (vibrance, warmth, contrast)
  4. makes the picture used for the back and sides of the model: a separate back-view
     photo if the spec names one ("back_photo"), otherwise a copy of the front photo;
     either way with the things that should not show there covered up ("clean_back")
  5. builds one picture, the "atlas": the photo and the cleaned copy side by side,
     with a strip of flat colour swatches under them
  6. writes input_images/texture/<figure>_atlas.png, <figure>_uv.json and a
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
FEATHER = 4       # softness, in pixels, of the edges of cleaned-up patches
RASTER = 1024     # resolution of the mesh outline used for the search
HALF = 1.1        # the outline covers x and z from -HALF to +HALF


def cut_out(photo_name, ignore=()):
    """The photo as a square RGB image, and a mask of the person.

    `ignore` lists boxes (x0, y0, x1, y1), as fractions of the original photo, that are
    dropped from the mask: parts of the person that must not be used.

    `photo_name` is looked up in input_images/source/, then in input_images/ (so a prepared
    cut-out can be named "prepared/<figure>.png"). If the file has a transparent background,
    that transparency is the mask and no background removal is run.
    """
    path = next(p for p in (SRC / photo_name, SRC.parent / photo_name) if p.exists())
    source = Image.open(path)
    cutout = source.mode == "RGBA" and source.getchannel("A").getextrema()[0] < 255
    img = source.convert("RGB")
    scale = PHOTO / max(img.size)
    size = (round(img.width * scale), round(img.height * scale))
    img = img.resize(size, Image.LANCZOS)
    left, top = (PHOTO - img.width) // 2, (PHOTO - img.height) // 2
    canvas = Image.new("RGB", (PHOTO, PHOTO), img.getpixel((0, 0)))
    canvas.paste(img, (left, top))

    if cutout:
        mask = Image.new("L", (PHOTO, PHOTO), 0)
        mask.paste(source.getchannel("A").resize(size, Image.LANCZOS), (left, top))
        alpha = np.array(mask) > 127
    else:
        from rembg import new_session, remove  # only needed for photos with a background
        alpha = np.array(remove(canvas, session=new_session("birefnet-general")))[:, :, 3] > 127
    for x0, y0, x1, y1 in ignore:
        alpha[top + round(y0 * img.height):top + round(y1 * img.height),
              left + round(x0 * img.width):left + round(x1 * img.width)] = False
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


def to_pixels(box, params):
    su, sz, tu, tz = params
    x0, z0, x1, z1 = box
    u0, u1 = sorted((su * x0 + tu, su * x1 + tu))
    v0, v1 = sorted((-sz * z0 + tz, -sz * z1 + tz))
    return [int(np.clip(round(n), 0, PHOTO)) for n in (u0, v0, u1, v1)]


def soft_mask(box, params):
    u0, v0, u1, v1 = to_pixels(box, params)
    mask = np.zeros((PHOTO, PHOTO), np.float32)
    mask[v0:v1, u0:u1] = 1
    return cv2.GaussianBlur(mask, (0, 0), FEATHER)[:, :, None]


def clean_copy(photo, clean, steps, params):
    """The photo with things that belong only to the front covered up, for the back and sides."""
    su, sz = params[0], params[1]
    result = photo.astype(np.float32)
    for box, dx, dz in steps.get("copy", ()):
        source = np.roll(result, (-round(-sz * dz), -round(su * dx)), axis=(0, 1))
        mask = soft_mask(box, params)
        result = result * (1 - mask) + source * mask
    for box, sample in steps.get("fill", ()):
        colour = np.array(median_colour(photo, clean, sample, params), np.float32)
        mask = soft_mask(box, params)
        result = result * (1 - mask) + colour * mask
    return np.clip(result, 0, 255).astype(np.uint8)


def grade_photo(rgb, vibrance=1.0, warmth=0.0, contrast=1.0):
    """Bring out the colour of a pale photo, in the Lab colour space so lightness is kept.

    vibrance  multiplies the colour of muted pixels; strong colours (a marigold garland) are
              multiplied much less, so they are not blown out
    warmth    pushes every colour toward yellow (positive) or blue (negative), in Lab units
    contrast  stretches lightness around the middle grey
    """
    lab = cv2.cvtColor(rgb.astype(np.float32) / 255, cv2.COLOR_RGB2LAB)
    a, b = lab[:, :, 1], lab[:, :, 2]
    muted = np.clip(1 - np.hypot(a, b) / 60, 0, 1)         # 1 for grey, 0 for vivid
    boost = 1 + (vibrance - 1) * muted
    lab[:, :, 1], lab[:, :, 2] = a * boost, b * boost + warmth
    lab[:, :, 0] = np.clip(50 + (lab[:, :, 0] - 50) * contrast, 0, 100)
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB) * 255 + 0.5, 0, 255).astype(np.uint8)


def spread_edges(rgb, person):
    """Pixels near or outside the person's edge take the colour of the nearest clean pixel,
    so no background colour bleeds onto the model."""
    clean = cv2.erode(person.astype(np.uint8), np.ones((2 * EDGE_ERODE + 1,) * 2, np.uint8)) > 0
    nearest = distance_transform_edt(~clean, return_distances=False, return_indices=True)
    return rgb[nearest[0], nearest[1]], clean


def save_alignment(path, rgb, outline, params):
    """The mesh outline in red over the photo, to check the fit by eye."""
    shape = cv2.warpAffine(outline, warp_matrix(*params), (PHOTO, PHOTO))
    contours, _ = cv2.findContours((shape > 127).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    preview = rgb.copy()
    cv2.drawContours(preview, contours, -1, (255, 0, 0), 2)
    Image.fromarray(preview).resize((768, 768), Image.LANCZOS).save(path, quality=92)


def back_view(texture, outline, mesh, params, name):
    """A separate photo of the person's back, moved into the same frame as the front photo.

    It is mirrored first: the model looks every point up as if seen from the front, and a
    back view seen 'through' the body from the front is the back photo flipped left-right.
    """
    spec = texture["back_photo"]
    rgb, person = cut_out(spec["photo"], spec.get("ignore", ()))
    rgb, person = np.ascontiguousarray(rgb[:, ::-1]), np.ascontiguousarray(person[:, ::-1])
    su_b, sz_b, tu_b, tz_b, iou = fit(outline, person, mesh)
    print(f"  back photo: outline overlap {iou:.3f}  scale {su_b:.0f}/{sz_b:.0f}  offset {tu_b:.0f}/{tz_b:.0f}")
    save_alignment(OUT / f"{name}_alignment_back.jpg", rgb, outline, (su_b, sz_b, tu_b, tz_b))

    filled, clean = spread_edges(rgb, person)
    su, sz, tu, tz = params
    move = np.array([[su / su_b, 0, tu - su / su_b * tu_b], [0, sz / sz_b, tz - sz / sz_b * tz_b]], np.float32)
    filled = cv2.warpAffine(filled, move, (PHOTO, PHOTO), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    clean = cv2.warpAffine(clean.astype(np.uint8), move, (PHOTO, PHOTO), flags=cv2.INTER_NEAREST) > 0
    return filled, clean


def prepare(name):
    spec = FIGURES[name]
    texture = spec["texture"]
    rgb, person = cut_out(texture["photo"])
    mesh = trimesh.load(RAW / spec["raw_mesh"], force="mesh")
    outline = mesh_outline(mesh)
    su, sz, tu, tz, iou = fit(outline, person, mesh)
    params = (su, sz, tu, tz)
    print(f"{name}: outline overlap {iou:.3f}  scale {su:.0f}/{sz:.0f}  offset {tu:.0f}/{tz:.0f}")
    if iou < 0.80:
        print("  warning: low overlap, the photo may not match the mesh well")

    photo, clean = spread_edges(rgb, person)
    if "clean_front" in texture:   # touch up the front photo itself (same steps as clean_back)
        photo = clean_copy(photo, clean, texture["clean_front"], params)
    grading = texture.get("grade")
    if grading:
        photo = grade_photo(photo, **grading)
    OUT.mkdir(parents=True, exist_ok=True)
    if "back_photo" in texture:
        behind, behind_clean = back_view(texture, outline, mesh, params, name)
        if grading:
            behind = grade_photo(behind, **grading)
    else:
        behind, behind_clean = photo, clean
    cleaned = clean_copy(behind, behind_clean, texture.get("clean_back", {}), params)

    atlas_width, atlas_height = 2 * PHOTO, PHOTO + SWATCH
    swatches = {}
    strip = np.zeros((SWATCH, atlas_width, 3), np.uint8)
    for part in spec["parts"]:
        mode = part.get("back", "project")
        if mode in ("project", "front"):
            continue
        colour = hex_to_rgb(mode) if mode.startswith("#") else median_colour(
            photo, clean, part["swatch_box"], params)
        index = len(swatches)
        strip[:, index * SWATCH:(index + 1) * SWATCH] = colour
        swatches[part["key"]] = [(index + 0.5) * SWATCH / atlas_width, 1 - (PHOTO + SWATCH / 2) / atlas_height]
        print(f"  {part['key']:<12} back colour #{colour[0]:02x}{colour[1]:02x}{colour[2]:02x}")

    Image.fromarray(np.vstack([np.hstack([photo, cleaned]), strip])).save(OUT / f"{name}_atlas.png")
    (OUT / f"{name}_uv.json").write_text(json.dumps(
        dict(photo=PHOTO, atlas_width=atlas_width, atlas_height=atlas_height,
             su=su, sz=sz, tu=tu, tz=tz, overlap=iou, swatches=swatches),
        indent=2) + "\n", encoding="utf-8")

    save_alignment(OUT / f"{name}_alignment.jpg", rgb, outline, params)


if __name__ == "__main__":
    names = sys.argv[1:] or [n for n, s in FIGURES.items()
                             if s.get("texture") and not s["texture"].get("own")]
    for n in names:
        prepare(n)
