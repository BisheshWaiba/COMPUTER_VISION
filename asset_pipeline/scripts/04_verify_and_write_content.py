"""Check the exported models and write assets/figures.json.

Run from asset_pipeline/:  .venv/Scripts/python.exe scripts/04_verify_and_write_content.py

For every figure this checks that
  - the .glb contains exactly the part names listed in figures_spec.py
  - Panda3D (through panda3d-gltf) loads it and can find every part by name
and then writes the content file the app reads, plus a thumbnail per figure.
"""
import json
import sys
from pathlib import Path

from PIL import Image
from pygltflib import GLTF2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figures_spec import FIGURES  # noqa: E402

PIPELINE = Path(__file__).resolve().parent.parent
ASSETS = PIPELINE.parent / "assets"

from panda3d.core import Filename, loadPrcFileData  # noqa: E402

loadPrcFileData("", "window-type none\naudio-library-name null")
from direct.showbase.ShowBase import ShowBase  # noqa: E402

base = ShowBase()

content = {"figures": []}
ok = True
for name, spec in FIGURES.items():
    glb = ASSETS / "models" / f"{name}.glb"
    wanted = {p["key"] for p in spec["parts"]}

    gltf = GLTF2().load(str(glb))
    in_file = {n.name for n in gltf.nodes if n.mesh is not None}
    triangles = sum(gltf.accessors[prim.indices].count // 3 for m in gltf.meshes for prim in m.primitives)

    model = base.loader.loadModel(Filename.fromOsSpecific(str(glb)))
    in_panda = {key for key in wanted if not model.find(f"**/{key}").isEmpty()}

    good = in_file == wanted and in_panda == wanted
    ok &= good
    print(f"{'OK  ' if good else 'FAIL'} {name}: {len(in_file)} parts, {triangles} triangles, "
          f"{glb.stat().st_size / 1e6:.2f} MB")
    if not good:
        print("   missing in file:", sorted(wanted - in_file), "| unexpected:", sorted(in_file - wanted),
              "| not found by Panda3D:", sorted(wanted - in_panda))

    front = PIPELINE / "renders" / f"parts_{name}_front.png"
    thumb = ASSETS / "thumbnails" / f"{name}.png"
    thumb.parent.mkdir(parents=True, exist_ok=True)
    Image.open(front).convert("RGB").resize((512, 512), Image.LANCZOS).save(thumb)

    content["figures"].append({
        "id": name,
        "title": spec["title"],
        "model": f"models/{name}.glb",
        "thumbnail": f"thumbnails/{name}.png",
        "description": spec["description"],
        "parts": {p["key"]: {"label": p["label"], "info": p["info"]} for p in spec["parts"] if "label" in p},
    })

(ASSETS / "figures.json").write_text(json.dumps(content, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("wrote", ASSETS / "figures.json")
sys.exit(0 if ok else 1)
