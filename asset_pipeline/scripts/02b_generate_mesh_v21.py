"""Turn a prepared RGBA picture into an untextured mesh with Hunyuan3D-2.1.

An alternative to 02_generate_meshes.py that uses the newer, larger shape model.
It officially needs 10 GB of VRAM; to fit in 8 GB the parts of the model take
turns on the graphics card, which makes it slower.

Run from asset_pipeline/:
    .venv/Scripts/python.exe scripts/02b_generate_mesh_v21.py <prepared name> <output name> [seed ...]
reads  input_images/prepared/<prepared name>.png
writes raw_meshes/<output name>.glb, or <output name>_s<seed>.glb for each seed given.
The seed changes what the model invents for the sides it cannot see (the back, mostly).
"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["HY3DGEN_MODELS"] = str(ROOT / "models")
sys.path.insert(0, str(ROOT / "Hunyuan3D-2.1" / "hy3dshape"))

import torch
from PIL import Image

# the checkpoint is 7 GB: map it from disk instead of reading it all into memory
_load = torch.load
torch.load = lambda *args, **kwargs: _load(*args, **{"mmap": True, **kwargs})

from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline
from hy3dshape.postprocessors import DegenerateFaceRemover, FaceReducer, FloaterRemover

MAX_FACES = 60000


def take_turns(pipeline):
    """Keep only the sub-model that is working on the graphics card.

    The pipeline uses its three sub-models strictly one after another: the image encoder,
    then the denoiser for every step, then the decoder that turns the result into a mesh.
    (The pipeline's own enable_model_cpu_offload does not work in this release.)
    """
    gpu = torch.device("cuda")
    pipeline.device = gpu  # where the pipeline creates its own tensors

    def swap(leaving, arriving):
        leaving.to("cpu")
        torch.cuda.empty_cache()
        arriving.to(gpu)

    encode_cond, export = pipeline.encode_cond, pipeline._export

    def encode_then_denoise(*args, **kwargs):
        pipeline.conditioner.to(gpu)
        cond = encode_cond(*args, **kwargs)
        swap(pipeline.conditioner, pipeline.model)
        return cond

    def decode(*args, **kwargs):
        swap(pipeline.model, pipeline.vae)
        return export(*args, **kwargs)

    pipeline.encode_cond, pipeline._export = encode_then_denoise, decode


def main():
    source, name, seeds = sys.argv[1], sys.argv[2], [int(s) for s in sys.argv[3:]]
    started = time.time()
    pipeline = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained("tencent/Hunyuan3D-2.1", device="cpu")
    take_turns(pipeline)
    print(f"loaded in {time.time() - started:.0f} s", flush=True)

    image = Image.open(ROOT / "input_images" / "prepared" / f"{source}.png").convert("RGBA")
    for seed in seeds or [12345]:
        out = f"{name}_s{seed}" if seeds else name
        torch.cuda.reset_peak_memory_stats()
        started = time.time()
        mesh = pipeline(
            image=image,
            num_inference_steps=50,
            octree_resolution=380,
            num_chunks=20000,
            generator=torch.manual_seed(seed),
            output_type="trimesh",
        )[0]
        print(f"generated in {time.time() - started:.0f} s, peak VRAM "
              f"{torch.cuda.max_memory_allocated() / 2**30:.1f} GB", flush=True)
        for step in (FloaterRemover(), DegenerateFaceRemover()):
            mesh = step(mesh)
        mesh = FaceReducer()(mesh, max_facenum=MAX_FACES)
        mesh.export(ROOT / "raw_meshes" / f"{out}.glb")
        print(f"wrote {out}: {len(mesh.vertices)} verts, {len(mesh.faces)} faces", flush=True)


if __name__ == "__main__":
    main()
