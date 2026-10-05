# Figures of Nepal

An interactive desktop application for exploring 3D figures representing Nepali
people, clothing, and history. The application uses Kivy for the user
interface, Panda3D for off-screen 3D rendering, and glTF/GLB models for the
figure assets.

## Features

- Gallery of four Nepali figures.
- All text in English and Nepali, with a button to switch language.
- Interactive 3D rotation, zoom, and pan.
- Tap or click individual model parts to view descriptions.
- Part-selection chips that focus the camera on the selected part.
- Bundled models, thumbnails, and figure metadata under `assets/`.

## Requirements

- Windows, macOS, or Linux.
- Python 3.11 recommended.
- A graphics driver capable of OpenGL rendering.
- The dependencies listed in `requirements.txt`:
  - Kivy 2.3.1
  - Panda3D 1.10.16
  - panda3d-gltf 1.3.0

The repository currently includes a configured Windows virtual environment in
`.venv`. A separate environment is included under `asset_pipeline/.venv` for
optional asset generation.

## Run the application on Windows

Open PowerShell and run:

```powershell
cd "C:\Users\prasi\Desktop\Project II\COMPUTER_VISION"
.\.venv\Scripts\Activate.ps1
python main.py
```

Alternatively, run without activating the environment:

```powershell
cd "C:\Users\prasi\Desktop\Project II\COMPUTER_VISION"
& ".\.venv\Scripts\python.exe" ".\main.py"
```

If the environment has not been installed or needs to be refreshed:

```powershell
python -m pip install -r requirements.txt
```

When the application opens, choose a figure from the gallery. Drag to rotate,
use the mouse wheel or a pinch gesture to zoom, right-drag to pan, and click a
model part to display its information.

## Run from a new virtual environment

If the included environment is unavailable:

```powershell
cd "C:\Users\prasi\Desktop\Project II\COMPUTER_VISION"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Project structure

```text
COMPUTER_VISION/
├── main.py                  Application entry point
├── app/
│   ├── content.py           Loads assets/figures.json
│   ├── renderer.py          Panda3D off-screen renderer
│   ├── screens.py           Gallery and viewer screens
│   ├── ui.kv               Kivy layout and styling
│   └── view3d.py            3D interaction widget
├── assets/
│   ├── figures.json         Figure and part metadata
│   ├── models/              Finished .glb models
│   └── thumbnails/          Gallery thumbnail images
├── asset_pipeline/          Optional model-generation workflow
├── requirements.txt         Application dependencies
└── docs/
    └── PROJECT_DOCUMENTATION.md
```

See [docs/PROJECT_DOCUMENTATION.md](docs/PROJECT_DOCUMENTATION.md) for the
architecture, data flow, asset pipeline, and maintenance instructions.

## Optional asset pipeline

The application already contains finished assets and does not require the
pipeline to run. The pipeline can prepare source images, generate meshes with
Hunyuan3D-2, split meshes into named parts using Blender, render previews, and
write `assets/figures.json`.

The mesh-generation stage normally requires a compatible NVIDIA GPU, CUDA,
substantial VRAM, model files, and additional packages in
`asset_pipeline/.venv`. See the asset-pipeline section in the project
documentation before running it.

## Troubleshooting

- **PowerShell refuses to activate `.venv`:** run the application with the
  direct `.venv\Scripts\python.exe` command above, or allow scripts for the
  current user with `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **`ModuleNotFoundError`:** confirm that the command uses
  `.venv\Scripts\python.exe`, then run `python -m pip install -r requirements.txt`.
- **Models do not load:** run the application from the project root and verify
  that `assets/models/` contains the `.glb` files referenced by
  `assets/figures.json`.
- **A blank or failing 3D view:** update the graphics driver and verify that
  OpenGL is available on the machine.

## Credits and licensing

See [assets/CREDITS.md](assets/CREDITS.md) for asset credits and attribution.