"""The app's own words in each language, and the font each language is drawn with.

The text about the figures themselves lives in assets/figures.json.
The Devanagari font has no Latin letters, so Nepali strings must not contain any.
"""
from pathlib import Path

from kivy.core.text import LabelBase

LANGUAGES = ("en", "ne")

_FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
LabelBase.register("NotoDeva",
                   fn_regular=str(_FONTS / "NotoSansDevanagari-Regular.ttf"),
                   fn_bold=str(_FONTS / "NotoSansDevanagari-Bold.ttf"))

# language -> (font name, script the text shaper should use)
FONTS = {"en": ("Roboto", "Latn"), "ne": ("NotoDeva", "Deva")}

STRINGS = {
    "en": {
        "language_name": "English",
        "app_title": "Figures of Nepal",
        "app_subtitle": "Choose a figure to explore it in 3D.",
        "parts_count": "{} parts to explore",
        "loading": "Loading…",
        "hint": "Drag to rotate  ·  Pinch to zoom  ·  Tap a part",
        "points": "Point cloud",
        "points_count": "{} points",
    },
    "ne": {
        "language_name": "नेपाली",
        "app_title": "नेपालका आकृतिहरू",
        "app_subtitle": "थ्रीडीमा हेर्न एउटा आकृति छान्नुहोस्।",
        "parts_count": "हेर्नका लागि {} वटा भाग",
        "loading": "लोड हुँदैछ…",
        "hint": "घुमाउन तान्नुहोस्,  जुम गर्न चिम्ट्नुहोस्,  भागमा थिच्नुहोस्",
        "points": "बिन्दु बादल",
        "points_count": "{} वटा बिन्दु",
    },
}

_NEPALI_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")


def number(value, lang):
    """A number written with the digits of the language."""
    text = str(value)
    return text.translate(_NEPALI_DIGITS) if lang == "ne" else text


def other(lang):
    """The language the switch button offers."""
    return "ne" if lang == "en" else "en"
