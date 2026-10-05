"""Turn each prepared RGBA picture into an untextured mesh with Hunyuan3D-2.

Run from asset_pipeline/:  .venv/Scripts/python.exe scripts/02_generate_meshes.py [name ...]
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["HY3DGEN_MODELS"] = str(ROOT / "models")
sys.path.insert(0, str(ROOT / "Hunyuan3D-2"))

import torch
from PIL import Image

from hy3dgen.shapegen import Hunyuan3DDiTFlowMatchingPipeline
from hy3dgen.shapegen.postprocessors import DegenerateFaceRemover, FaceReducer, FloaterRemover

PREPARED = ROOT / "input_images" / "prepared"
OUT = ROOT / "raw_meshes"
MAX_FACES = 60000  # per figure, before the parts are split in Blender


def main():
    names = sys.argv[1:] or sorted(p.stem for p in PREPARED.glob("*.png"))
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2")
    OUT.mkdir(exist_ok=True)
    for name in names:
        image = Image.open(PREPARED / f"{name}.png").convert("RGBA")
        mesh = pipeline(
            image=image,
            num_inference_steps=50,
            octree_resolution=380,
            num_chunks=20000,
            generator=torch.manual_seed(12345),
            output_type="trimesh",
        )[0]
        for step in (FloaterRemover(), DegenerateFaceRemover()):
            mesh = step(mesh)
        mesh = FaceReducer()(mesh, max_facenum=MAX_FACES)
        mesh.export(OUT / f"{name}.glb")
        print(f"generated {name}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces, "
              f"peak VRAM {torch.cuda.max_memory_allocated() / 2**30:.1f} GB")
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
