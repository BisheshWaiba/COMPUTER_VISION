"""Make a point cloud from a figure's reference photo with monocular depth estimation,
and check the generated mesh against it.

Run from asset_pipeline/ (after 02 and 05, which give the raw mesh and how the photo lines up with it):
    <python with the packages in requirements_depth.txt> scripts/06_depth_pointcloud.py [figure ...]

For each figure that has a "texture" photo in figures_spec.py this
  1. runs Depth Anything V2 on the photo, which gives how near every pixel is, but only
     relative to the other pixels (no scale, no zero)
  2. casts a ray through every pixel of the person into the raw mesh (using the alignment
     05 found, input_images/texture/<figure>_uv.json) to get the depth the mesh has there
  3. fits the scale, offset and tilt that turn the photo's relative depth into the mesh's depth
     (a robust fit, so the places where the two disagree do not drag it off). The tilt is a
     small turn of the photo's camera relative to the mesh: a photo taken from below makes the
     feet look nearer than the head, which the mesh does not do
  4. back-projects the photo's pixels with that depth into a coloured point cloud, in metres
  5. measures how far the cloud lies from the mesh surface and writes the numbers and a
     picture of where they differ

The cloud covers the front only: a photo cannot see the back. The scale, offset and tilt come
from the mesh, so this checks the SHAPE of the mesh's front against an independent estimate; it
does not show that the mesh has the right overall depth or leans the right way. Both estimates
start from the same photo, so agreement means they are consistent, not that either one is right.

The mesh's front is fairly flat, so the numbers are read against a baseline: the error you would
get from the best flat tilted plane, which uses no photo at all ("flat_plane_rms"). The share
the photo explains is how far below that baseline the error falls. Depth from one photo is also
smoother and shallower than the mesh, which "relief_ratio" shows.

Writes to pointclouds/: <figure>_depth.ply (open it in MeshLab or CloudCompare),
<figure>_report.png, and metrics.json for all figures run.
"""
import importlib.util
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import open3d as o3d
import torch
import trimesh
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from figures_spec import FIGURES  # noqa: E402

_spec = importlib.util.spec_from_file_location("prepare_texture", HERE / "05_prepare_texture.py")
prepare_texture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prepare_texture)  # for cut_out(): the same photo and mask 05 used
# The mask here only decides which pixels become points, and its edge is trimmed anyway, so a
# light model will do: 05's default (birefnet-general) needs several GB of free memory.
prepare_texture.SEGMENTER = "isnet-general-use"

RAW = ROOT / "raw_meshes"
UV = ROOT / "input_images" / "texture"
OUT = ROOT / "pointclouds"

MODEL = "depth-anything/Depth-Anything-V2-Small-hf"  # Apache-2.0; the larger sizes are non-commercial
INPUT_SIDE = 770    # the photo is fed to the network at this size (a multiple of 14), pixels
EDGE_ERODE = 4      # pixels trimmed off the person's outline: depth is unreliable at the silhouette
STRIDE = 2          # one point per STRIDE x STRIDE pixels, to keep the files small
JUMP = 0.012        # a pixel whose depth differs from a neighbour by more than this fraction of
                    # the figure's height is a "flying" point between two surfaces and is dropped
TOLERANCES_CM = (1.0, 2.0, 5.0)


def load_depth_model():
    processor = AutoImageProcessor.from_pretrained(MODEL)
    return processor, AutoModelForDepthEstimation.from_pretrained(MODEL).eval()


def estimate_depth(photo, processor, model):
    """How near each pixel is, as a float image the size of the photo. Larger means nearer."""
    inputs = processor(images=Image.fromarray(photo), return_tensors="pt", do_resize=True,
                       size={"height": INPUT_SIDE, "width": INPUT_SIDE}, keep_aspect_ratio=False)
    with torch.no_grad():
        predicted = model(**inputs).predicted_depth[None]
    size = photo.shape[:2]
    return torch.nn.functional.interpolate(predicted, size=size, mode="bicubic", align_corners=False)[0, 0].numpy()


def mesh_scene(mesh):
    scene = o3d.t.geometry.RaycastingScene()
    scene.add_triangles(o3d.core.Tensor(mesh.vertices.astype(np.float32)),
                        o3d.core.Tensor(mesh.faces.astype(np.uint32)))
    return scene


def pixel_to_mesh(uv, rows, cols):
    """Mesh x and y (y up) under the given photo pixels, by undoing 05's alignment."""
    return (cols - uv["tu"]) / uv["su"], (uv["tz"] - rows) / uv["sz"]


def mesh_front_depth(scene, mesh, uv, shape):
    """The z (towards the viewer) of the mesh's front surface under every pixel; NaN where it misses."""
    rows, cols = np.indices(shape).astype(np.float32)
    x, y = pixel_to_mesh(uv, rows.ravel(), cols.ravel())
    top = float(mesh.vertices[:, 2].max()) + 1.0
    origins = np.stack([x, y, np.full_like(x, top)], axis=1)
    rays = np.concatenate([origins, np.tile([0, 0, -1], (len(x), 1))], axis=1).astype(np.float32)
    hit = scene.cast_rays(o3d.core.Tensor(rays))["t_hit"].numpy()
    return np.where(np.isfinite(hit), top - hit, np.nan).reshape(shape)


def robust_fit(features, target, rounds=6, spread=2.5):
    """Coefficients c with target ~ features @ c, found by least squares and then refitted
    without the points that sit far from the bulk (the places where the two disagree)."""
    keep = np.ones(len(target), bool)
    for _ in range(rounds):
        coef = np.linalg.lstsq(features[keep], target[keep], rcond=None)[0]
        residual = target - features @ coef
        centre = np.median(residual[keep])
        scale = 1.4826 * np.median(np.abs(residual[keep] - centre)) + 1e-9
        keep = np.abs(residual - centre) < spread * scale
    return coef


def remove_plane(values, x, y):
    """`values` with the best-fitting tilted plane (in x and y) taken away."""
    plane = np.stack([np.ones_like(x), x, y], axis=1)
    return values - plane @ np.linalg.lstsq(plane, values, rcond=None)[0]


def flying_pixels(depth, limit):
    """True where the depth jumps by more than `limit` to a neighbour (an edge between two surfaces)."""
    jump = np.zeros(depth.shape, bool)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        shifted = np.roll(depth, (dy, dx), axis=(0, 1))
        jump |= np.abs(depth - shifted) > limit
    return jump


def metres(units, mesh, height_m):
    """Raw-mesh units to metres, the way 03_split_parts.py scales the finished model."""
    return units * height_m / float(np.ptp(mesh.vertices[:, 1]))


def evaluate(name, processor, model):
    figure = FIGURES[name]
    uv = json.loads((UV / f"{name}_uv.json").read_text())
    photo, person = prepare_texture.cut_out(figure["texture"]["photo"])
    mesh = trimesh.load(RAW / figure["raw_mesh"], force="mesh")
    scene = mesh_scene(mesh)
    to_m = lambda units: metres(units, mesh, figure["height_m"])

    disparity = estimate_depth(photo, processor, model)
    mesh_z = mesh_front_depth(scene, mesh, uv, person.shape)
    inside = cv2.erode(person.astype(np.uint8), np.ones((2 * EDGE_ERODE + 1,) * 2, np.uint8)) > 0
    usable = inside & np.isfinite(mesh_z)

    # depth = scale * disparity + offset + tilt in x and y. The tilt is a small turn of the photo's
    # camera relative to the mesh: a photo taken from below puts the feet nearer than the head.
    gx, gy = pixel_to_mesh(uv, *np.indices(person.shape).astype(np.float32))
    design = np.stack([disparity, np.ones_like(disparity), gx, gy], axis=-1)
    coef = robust_fit(design[usable], mesh_z[usable])
    depth = design @ coef                           # the photo's depth, in the mesh's units
    scale = float(coef[0])

    error_cm = 100 * to_m(depth - mesh_z)           # + : the photo's surface is nearer than the mesh's
    error = error_cm[usable]

    # What the photo adds: compare with the best flat tilted plane, which uses no photo at all.
    x_u, y_u, z_u = gx[usable], gy[usable], mesh_z[usable]
    mesh_relief = remove_plane(z_u, x_u, y_u)
    photo_relief = remove_plane(disparity[usable], x_u, y_u)
    correlation = float(np.corrcoef(photo_relief, mesh_relief)[0, 1])
    plane_rms_cm = float(100 * to_m(mesh_relief.std()))
    rms_cm = float(np.sqrt(np.mean(error ** 2)))
    relief_ratio = float(scale * photo_relief.std() / mesh_relief.std())
    if scale <= 0 or correlation < 0.3:
        print(f"  warning: the photo's depth and the mesh's front barely agree (r={correlation:.2f}); "
              "the mesh may be mirrored or not match this photo")

    grid_rows, grid_cols = np.indices(person.shape)
    keep = (inside & ~flying_pixels(depth, JUMP * float(np.ptp(mesh.vertices[:, 1])))
            & (grid_rows % STRIDE == 0) & (grid_cols % STRIDE == 0))
    rows, cols = np.nonzero(keep)
    x, y = pixel_to_mesh(uv, rows.astype(np.float32), cols.astype(np.float32))
    points = np.stack([x, y, depth[rows, cols]], axis=1)
    to_ground = float(mesh.vertices[:, 1].min())
    centre = float(mesh.vertices[:, 0].min() + mesh.vertices[:, 0].max()) / 2
    metric = np.stack([to_m(points[:, 0] - centre), to_m(points[:, 1] - to_ground), to_m(points[:, 2])], axis=1)

    distance_cm = 100 * to_m(scene.compute_distance(o3d.core.Tensor(points.astype(np.float32))).numpy())

    cloud = o3d.geometry.PointCloud()
    cloud.points = o3d.utility.Vector3dVector(metric)
    cloud.colors = o3d.utility.Vector3dVector(photo[rows, cols] / 255.0)
    OUT.mkdir(exist_ok=True)
    o3d.io.write_point_cloud(str(OUT / f"{name}_depth.ply"), cloud)

    save_report(OUT / f"{name}_report.png", name, photo, person, disparity, mesh_z, error_cm, usable,
                mesh, points, photo[rows, cols], distance_cm.mean())

    stats = dict(
        figure=name, points=len(points), height_m=figure["height_m"], compared_pixels=int(usable.sum()),
        mesh_relief_std_cm=round(float(100 * to_m(z_u.std())), 2),
        relief_correlation=round(correlation, 3),          # photo vs mesh, tilt taken out of both
        relief_ratio=round(relief_ratio, 3),               # how much of the mesh's relief the photo's depth has
        depth_error_cm=dict(median_abs=round(float(np.median(np.abs(error))), 2),
                            rms=round(rms_cm, 2),
                            flat_plane_rms=round(plane_rms_cm, 2),   # error with no photo at all
                            share_explained=round(1 - (rms_cm / plane_rms_cm) ** 2, 3),
                            **{f"within_{t:g}cm": round(float(np.mean(np.abs(error) < t)), 3) for t in TOLERANCES_CM}),
        cloud_to_mesh_cm=dict(mean=round(float(distance_cm.mean()), 2),
                              p95=round(float(np.percentile(distance_cm, 95)), 2)),
        fit=dict(scale=round(scale, 4), offset=round(float(coef[1]), 4),
                 tilt_x=round(float(coef[2]), 4), tilt_y=round(float(coef[3]), 4)),
    )
    e, c = stats["depth_error_cm"], stats["cloud_to_mesh_cm"]
    print(f"{name}: {len(points)} points | mesh front relief {stats['mesh_relief_std_cm']} cm | "
          f"photo-vs-mesh relief r={correlation:.2f}, photo has {relief_ratio:.0%} of the mesh's relief | "
          f"depth error rms {e['rms']} cm (flat plane {e['flat_plane_rms']} cm, photo explains {e['share_explained']:.0%}) | "
          f"within 2 cm {e['within_2cm']:.0%} | cloud-to-mesh mean {c['mean']} cm, 95% {c['p95']} cm")
    return stats


def colour_map(values, low, high):
    scaled = np.clip((values - low) / (high - low), 0, 1)
    return cv2.cvtColor(cv2.applyColorMap((scaled * 255).astype(np.uint8), cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB)


def render_cloud(points, colours, size, background, yaw_deg=35.0):
    """The cloud seen from a little to one side, as coloured dots with the nearest drawn last."""
    yaw = np.radians(yaw_deg)
    across = points[:, 0] * np.cos(yaw) + points[:, 2] * np.sin(yaw)
    nearness = points[:, 2] * np.cos(yaw) - points[:, 0] * np.sin(yaw)
    up = points[:, 1]
    scale = size * 0.85 / np.ptp(up)
    px = np.clip(((across - across.mean()) * scale + size / 2).astype(int), 0, size - 2)
    py = np.clip(((up.max() - up) * scale + size * 0.075).astype(int), 0, size - 2)
    picture = np.tile(background, (size, size, 1))
    order = np.argsort(nearness)
    for dy in (0, 1):
        for dx in (0, 1):
            picture[py[order] + dy, px[order] + dx] = colours[order]
    return picture


def save_report(path, name, photo, person, disparity, mesh_z, error_cm, usable, mesh, points, colours, mean_cm):
    """Photo, photo depth, mesh depth, where they differ, a side view of both, and the cloud."""
    size = 512
    shrink = lambda image, nearest=False: cv2.resize(
        image, (size, size), interpolation=cv2.INTER_NEAREST if nearest else cv2.INTER_AREA)

    near = np.where(person, disparity, np.nan)
    depth_picture = colour_map(np.nan_to_num(near, nan=np.nanmin(near)), np.nanmin(near), np.nanmax(near))
    mesh_valid = np.isfinite(mesh_z)
    mesh_picture = colour_map(np.nan_to_num(mesh_z, nan=np.nanmin(mesh_z)), np.nanmin(mesh_z), np.nanmax(mesh_z))
    limit = 5.0
    diff = np.full(error_cm.shape, np.nan, np.float32)
    diff[usable] = error_cm[usable]
    diff_picture = cv2.cvtColor(cv2.applyColorMap(
        (np.clip((np.nan_to_num(diff) / limit + 1) / 2, 0, 1) * 255).astype(np.uint8), cv2.COLORMAP_JET), cv2.COLOR_BGR2RGB)
    blank = np.array([243, 240, 233], np.uint8)
    for picture, valid in ((depth_picture, person), (mesh_picture, mesh_valid), (diff_picture, usable)):
        picture[~valid] = blank

    side = np.tile(blank, (size, size, 1))
    low, high = mesh.vertices[:, 1].min(), mesh.vertices[:, 1].max()
    front, back = mesh.vertices[:, 2].min(), mesh.vertices[:, 2].max()
    span = max(high - low, back - front)
    def plot(z, y, colour, radius):
        px = ((z - front) / span * (size * 0.8) + size * 0.1).astype(int)
        py = ((high - y) / span * (size * 0.8) + size * 0.1).astype(int)
        for u, v in zip(px, py):
            cv2.circle(side, (int(u), int(v)), radius, colour, -1)
    plot(mesh.vertices[::6, 2], mesh.vertices[::6, 1], (170, 170, 175), 1)
    plot(points[::9, 2], points[::9, 1], (200, 40, 40), 1)

    cloud_picture = render_cloud(points, colours, size, blank)
    panels = [shrink(photo), shrink(depth_picture, True), shrink(mesh_picture, True), shrink(diff_picture, True),
              side, cloud_picture]
    titles = ["photo", "depth from photo", "depth of the mesh", f"photo - mesh (blue far, red near, +/-{limit:g} cm)",
              "side view: mesh grey, photo cloud red", "the cloud, from 35 degrees to the side"]
    strip = np.hstack(panels)
    header = np.tile(blank, (34, strip.shape[1], 1))
    for i, title in enumerate(titles):
        cv2.putText(header, title, (i * size + 8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (30, 28, 26), 1, cv2.LINE_AA)
    cv2.putText(strip, f"{name}   cloud-to-mesh mean {mean_cm:.1f} cm", (8, size - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 28, 26), 1, cv2.LINE_AA)
    Image.fromarray(np.vstack([header, strip])).save(path)


def main():
    names = sys.argv[1:] or [n for n, f in FIGURES.items() if f.get("texture")]
    processor, model = load_depth_model()
    results = [evaluate(n, processor, model) for n in names]
    OUT.mkdir(exist_ok=True)
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
