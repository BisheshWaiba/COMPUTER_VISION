"""Loads assets/figures.json, the single description of every figure in the app."""
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Part:
    key: str    # node name inside the .glb
    label: str
    info: str


@dataclass(frozen=True)
class Figure:
    id: str
    title: str
    description: str
    model: str       # absolute path to the .glb
    thumbnail: str   # absolute path to the image
    parts: dict      # node name -> Part


def load_figures(assets_dir):
    assets_dir = Path(assets_dir)
    data = json.loads((assets_dir / "figures.json").read_text(encoding="utf-8"))
    return [
        Figure(
            id=entry["id"],
            title=entry["title"],
            description=entry["description"],
            model=str(assets_dir / entry["model"]),
            thumbnail=str(assets_dir / entry["thumbnail"]),
            parts={key: Part(key, part["label"], part["info"]) for key, part in entry["parts"].items()},
        )
        for entry in data["figures"]
    ]
