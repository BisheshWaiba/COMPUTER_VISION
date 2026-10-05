"""Loads assets/figures.json, the single description of every figure in the app.

Every piece of text is stored per language: {"en": "...", "ne": "..."}.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from app.strings import LANGUAGES


@dataclass(frozen=True)
class Part:
    key: str     # node name inside the .glb
    label: dict  # language -> text
    info: dict


@dataclass(frozen=True)
class Figure:
    id: str
    title: dict        # language -> text
    description: dict
    model: str         # absolute path to the .glb
    thumbnail: str     # absolute path to the image
    parts: dict        # node name -> Part


def _texts(value):
    """Text per language; a plain string is used for every language."""
    if isinstance(value, str):
        return {lang: value for lang in LANGUAGES}
    return {lang: value.get(lang) or value["en"] for lang in LANGUAGES}


def load_figures(assets_dir):
    assets_dir = Path(assets_dir)
    data = json.loads((assets_dir / "figures.json").read_text(encoding="utf-8"))
    return [
        Figure(
            id=entry["id"],
            title=_texts(entry["title"]),
            description=_texts(entry["description"]),
            model=str(assets_dir / entry["model"]),
            thumbnail=str(assets_dir / entry["thumbnail"]),
            parts={key: Part(key, _texts(part["label"]), _texts(part["info"]))
                   for key, part in entry["parts"].items()},
        )
        for entry in data["figures"]
    ]
