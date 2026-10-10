# Figures of Nepal - Project Documentation

## 1. Overview

Figures of Nepal is an interactive 3D gallery built with Python. It presents
four figures as explorable GLB models:

1. Prithvi Narayan Shah
2. Nepali Man with Istakot and Dhaka Topi (painted from a photograph)
3. Nepali Woman in Gunyu Cholo (painted from front and back photographs)
4. Prithvi Narayan Shah (Portrait) (generated and textured in ComfyUI, then imported)

All text is available in English and Nepali. A button at the top right of both screens
switches language. The app's own words and fonts are in `app/strings.py`; the text about
the figures is stored per language in `assets/figures.json` as `{"en": ..., "ne": ...}`.
Nepali is drawn with the bundled Noto Sans Devanagari font, which has no Latin letters,
so Nepali text must not contain any.

The application is designed for desktop use, but its Kivy layout and touch
handling also support a phone-shaped interaction model. Each model is divided
into named parts. Selecting a part highlights it and shows cultural or
historical information.

## 2. Technology stack

| Component | Purpose |
|---|---|
| Python 3.11 | Application language |
| Kivy | Window, widgets, layouts, and input handling |
| Panda3D | 3D model loading, lighting, picking, and off-screen rendering |
| panda3d-gltf | GLB/glTF model loading |
| Blender | Optional mesh splitting and GLB export |
| Hunyuan3D-2 | Optional image-to-3D mesh generation |

The application dependencies are pinned in `requirements.txt`.

## 3. Architecture

### 3.1 Application entry point

`main.py` creates the Kivy application and:

1. Configures a phone-shaped desktop window.
2. Loads `app/ui.kv`.
3. Starts the Panda3D renderer thread.
4. Creates the gallery and viewer screens.
5. Loads figure metadata from `assets/figures.json`.
6. Handles navigation and the Escape/Android back key.
7. Stops the renderer when the application exits.

### 3.2 User interface

`app/screens.py` defines the interactive widgets and screen behavior:

- `GalleryScreen` creates one card for each figure.
- `ViewerScreen` loads the selected model and creates a chip for each
  documented part.
- `InfoCard` displays the label and description for the selected part.

`app/ui.kv` defines the visual layout, colors, spacing, cards, buttons, and
viewer overlay.

### 3.3 3D rendering

`app/renderer.py` runs Panda3D on a dedicated daemon thread. This separation is
important because Kivy owns the application window and Panda3D owns its
off-screen OpenGL context.

The renderer:

- Loads and caches GLB models.
- Creates an off-screen framebuffer.
- Applies camera movement and lighting.
- Draws only when a camera, selection, model, or viewport change occurs.
- Performs ray-based picking to identify the model part under the pointer.
- Sends raw RGBA frames back to Kivy.

`app/view3d.py` is the Kivy-side widget. It converts user input into renderer
commands:

- Left-drag: rotate.
- Right-drag: pan.
- Mouse wheel or pinch: zoom.
- Double-click: reset the view.
- Short left click: pick a model part.

## 4. Asset and metadata format

The application reads `assets/figures.json`. Each figure entry contains:

- `id`: stable identifier.
- `title`: gallery and viewer title.
- `description`: gallery description.
- `model`: relative path to a GLB file.
- `thumbnail`: relative path to a thumbnail image.
- `parts`: mapping from GLB node names to a label and information text.

`title`, `description`, `label` and `info` each hold the text per language.

The keys under `parts` must match mesh-node names inside the corresponding GLB.
For example, the key `dhaka_topi` must identify a node named
`dhaka_topi` in the model. This relationship is required for highlighting,
camera focusing, and picking.

When adding or replacing a finished model:

1. Put the GLB in `assets/models/`.
2. Put its thumbnail in `assets/thumbnails/`.
3. Add or update its entry in `assets/figures.json`.
4. Ensure every interactive part key exists in the GLB.
5. Run the application and test gallery selection, model loading, and every
   part chip.

## 5. Running the application

From the project root on Windows:

```powershell
cd "C:\Users\prasi\Desktop\Project II\COMPUTER_VISION"
& ".\.venv\Scripts\python.exe" ".\main.py"
```

To install dependencies into the included environment:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

The application should open a window titled **Figures of Nepal**.

## 6. Optional asset-generation pipeline

The pipeline is under `asset_pipeline/` and has its own environment. It is not
needed when using the checked-in assets.

### 6.1 Pipeline stages

1. `scripts/01_prepare_images.py`
   - Reads source images from `input_images/source/`.
   - Crops each subject.
   - Removes the background with `rembg`.
   - Writes square RGBA images to `input_images/prepared/`.

2. `scripts/02_generate_meshes.py`
   - Reads prepared images.
   - Runs Hunyuan3D-2.
   - Removes floaters and degenerate faces.
   - Reduces the mesh to the configured face limit.
   - Writes raw GLB meshes to `raw_meshes/`.

   Alternative to steps 1 and 2, for a mesh generated elsewhere that already has its own
   texture (for example a ComfyUI export): `scripts/02_import_textured_mesh.py`, run
   through Blender. It welds the texture seams, reduces the triangle count, caps triangle
   size so parts cut cleanly, keeps only the base colour picture at 2048 px, and writes
   the result to `raw_meshes/`. Such a figure has `"texture": {"own": True}` in the
   spec and skips the texture step below.

3. `scripts/05_prepare_texture.py`
   - Only for figures whose specification has a `texture` entry.
   - Cuts the person out of the reference photo and lines the photo up with the raw mesh.
   - Makes the picture used for the back and sides: a separate back-view photo if the
     spec names one under `back_photo` (mirrored, lined up with the mesh, and with any
     `ignore` boxes left out), otherwise a copy of the front photo. Front-only details
     (hands, buttons, a V-neck) are covered up as listed under `clean_back`.
   - Builds `input_images/texture/<figure>_atlas.png` (the photo, the cleaned copy and a
     few flat colour swatches) and `<figure>_uv.json`.
   - Run it after step 2 and before step 4 below.

4. `scripts/03_split_parts.py`
   - Must be run through Blender.
   - Reads part rules from `scripts/figures_spec.py`.
   - Assigns mesh faces to named parts.
   - Smooths boundaries and removes small disconnected islands.
   - Scales and grounds the figure.
   - Exports one named mesh object per part to `assets/models/`.
   - For textured figures, projects the photo onto front faces, the cleaned copy onto
     back faces, and a strip of each part's own fabric onto side faces, as set by each
     part's `back`, `side`, `side_bands`, `side_from`, `shift`, `swatch_box` and
     `back_remap` entries in `figures_spec.py`.

5. `scripts/04_verify_and_write_content.py`
   - Verifies that expected part names exist in each GLB.
   - Loads models through Panda3D.
   - Creates thumbnails from rendered previews.
   - Writes `assets/figures.json`.

### 6.2 Example pipeline commands

Run these commands from `asset_pipeline/`:

```powershell
cd "C:\Users\prasi\Desktop\Project II\COMPUTER_VISION\asset_pipeline"
& ".\.venv\Scripts\python.exe" ".\scripts\01_prepare_images.py"
& ".\.venv\Scripts\python.exe" ".\scripts\02_generate_meshes.py"
```

The mesh-generation script accepts optional figure names:

```powershell
& ".\.venv\Scripts\python.exe" ".\scripts\02_generate_meshes.py" nepali_man_v2
```

The mesh-splitting stage is run with Blender:

```powershell
blender --background --python ".\scripts\03_split_parts.py" -- nepali_man_v2
```

For a textured figure, run the texture step before the Blender step:

```powershell
& ".\.venv\Scripts\python.exe" ".\scripts\05_prepare_texture.py" nepali_man_v2
```

Finally, verify the exported assets and regenerate metadata:

```powershell
& ".\.venv\Scripts\python.exe" ".\scripts\04_verify_and_write_content.py"
```

The exact Blender executable and pipeline dependencies depend on the local
installation. Hunyuan3D-2 can require a CUDA-capable NVIDIA GPU, significant
VRAM, and downloaded model weights.

## 7. Maintenance and extension

### Add a new figure

For the application-only path, add a model, thumbnail, and metadata entry to
`assets/`. For the full generation path, also add a specification to
`asset_pipeline/scripts/figures_spec.py` and a source-image job to
`01_prepare_images.py`.

### Change part information

Update the relevant `parts` entry in `assets/figures.json`. If the metadata is
generated by the pipeline, update the source specification instead and rerun
the verification/content step so the generated file is not overwritten later.

### Change appearance or controls

- Modify layout and styling in `app/ui.kv`.
- Modify screen state and navigation in `app/screens.py`.
- Modify gestures and camera limits in `app/view3d.py`.
- Modify lighting, picking, and GLB handling in `app/renderer.py`.

## 8. Troubleshooting

### Import errors

Use the virtual-environment interpreter explicitly:

```powershell
& ".\.venv\Scripts\python.exe" -c "import kivy, panda3d; print('imports OK')"
```

If an import fails, reinstall the application dependencies:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

### Models are missing

Check that the paths in `assets/figures.json` are relative to `assets/` and
that the referenced files exist under `assets/models/` and
`assets/thumbnails/`.

### Parts cannot be selected

Check that the part key in `assets/figures.json` exactly matches a node name in
the GLB. The pipeline verification script is intended to catch this mismatch.

### Rendering problems

Update the graphics driver and check that OpenGL is available. Panda3D is
configured for off-screen rendering, so a machine with unavailable or
incompatible graphics support may show a blank viewer.

## 9. Credits

See `assets/CREDITS.md` for asset attribution and credits.
