"""Single source of truth for the three figures: which raw mesh each one comes
from, how it is cut into named parts, and the text shown for each part.

The part keys below become the node names in the exported .glb and the keys of
the "parts" dictionary in assets/figures.json, so they always match.

How a part is cut out
---------------------
Coordinates are the raw mesh as Blender imports it: x = figure's left (+) /
right (-), y = depth (front is negative), z = up, everything within -1..1.
Use scripts/render_grid.py + grid_overlay.py to read coordinates off a picture.

Each rule is (view, polygon, depth_range):
  view "front": polygon is in (x, z), depth_range limits y
  view "side":  polygon is in (y, z), depth_range limits x
A face goes to the first part (top to bottom) with a rule containing its centre.
Faces matching nothing go to the part marked default=True.
"""

ANY = (-9.0, 9.0)
FRONT = (-9.0, 0.0)
BACK = (0.0, 9.0)


def box(x0, z0, x1, z1):
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def disc(cx, cz, r, n=16):
    import math
    return [(cx + r * math.cos(2 * math.pi * i / n), cz + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def arc(cx, cz, r, start_deg, end_deg, step=15):
    """Part of a disc: the slice between two angles, closed by a straight edge."""
    import math
    return [(cx + r * math.cos(math.radians(a)), cz + r * math.sin(math.radians(a)))
            for a in range(start_deg, end_deg + 1, step)]


FIGURES = {
    "prithvi_narayan_shah": {
        "title": "Prithvi Narayan Shah",
        "description": "King of Gorkha who began the unification of Nepal in the 18th century, "
                       "shown in his best-known pose with one finger raised.",
        "raw_mesh": "prithvi_narayan_shah.glb",
        "height_m": 2.05,
        "parts": [
            {
                "key": "khukuri", "label": "Khukuri", "color": "#8a6a2f",
                "info": "The curved knife of the Gorkhali soldier, carried tucked into the waist sash. "
                        "It served as both an everyday tool and a weapon, and remains a national symbol of Nepal.",
                "rules": [("front", [(-0.115, -0.10), (-0.10, -0.035), (-0.02, -0.012), (0.065, -0.012),
                                     (0.06, -0.06), (-0.04, -0.105)], (-9.0, -0.10))],
            },
            {
                "key": "hands", "color": "#b9865a",
                "rules": [("front", box(-0.40, 0.81, -0.25, 1.05), ANY),
                          ("front", box(0.235, -0.215, 0.39, -0.085), (-9.0, -0.065))],
            },
            {
                "key": "tarwar", "label": "Tarwar (Sword)", "color": "#9aa0a8",
                "info": "A long curved sword held point-down in the left hand. Swords like this were carried "
                        "by Gorkhali commanders during the unification campaigns.",
                "rules": [("front", [(0.215, -0.20), (0.39, -0.20), (0.39, -0.32), (0.32, -0.45), (0.32, -0.67),
                                     (0.23, -0.75), (0.14, -0.87), (0.04, -0.985), (-0.04, -0.985), (-0.03, -0.90),
                                     (0.07, -0.80), (0.15, -0.66), (0.19, -0.45), (0.215, -0.30)], (-9.0, -0.125))],
            },
            {
                "key": "dhal", "label": "Dhal (Shield)", "color": "#3a3028",
                "info": "A round shield, traditionally made of hide or metal with raised bosses, "
                        "worn at the hip and used together with the sword.",
                "rules": [("side", disc(0.03, -0.14, 0.17), (0.135, 0.245)),
                          ("side", arc(0.03, -0.14, 0.17, -120, 120), (0.135, 0.40))],
            },
            {
                "key": "shripech", "label": "Shripech (Crown)", "color": "#d4af37",
                "info": "The jewelled royal crown of the Shah kings, topped with a plume of "
                        "bird-of-paradise feathers.",
                "rules": [("front", box(-0.16, 0.69, 0.42, 1.05), ANY)],
            },
            {
                "key": "head", "color": "#b9865a",
                "rules": [("front", [(-0.095, 0.57), (0.105, 0.57), (0.105, 0.615), (0.155, 0.615), (0.155, 0.705),
                                     (-0.14, 0.705), (-0.14, 0.615), (-0.095, 0.615)], ANY),
                          ("front", [(-0.07, 0.515), (0.075, 0.515), (0.10, 0.58), (-0.09, 0.58)], (-9.0, -0.05))],
            },
            {
                "key": "mala", "label": "Mala (Garland)", "color": "#e8791c",
                "info": "A garland worn around the neck. Statues of Prithvi Narayan Shah are garlanded with "
                        "marigolds on Prithvi Jayanti, the day that marks his birth.",
                "rules": [("front", [(-0.125, 0.61), (-0.05, 0.61), (-0.03, 0.50), (0.02, 0.31), (0.02, 0.22),
                                     (-0.04, 0.22), (-0.105, 0.36), (-0.135, 0.50)], FRONT),
                          ("front", [(0.085, 0.61), (0.175, 0.61), (0.175, 0.48), (0.125, 0.33), (0.07, 0.22),
                                     (0.02, 0.22), (0.02, 0.31), (0.075, 0.48)], FRONT),
                          ("front", box(-0.035, 0.005, 0.075, 0.24), (-9.0, -0.10))],
            },
            {
                "key": "patuka", "label": "Patuka (Waist Sash)", "color": "#f2efe6",
                "info": "A long cloth wound around the waist over the robe. It holds the khukuri in place "
                        "and supports the back.",
                "rules": [("front", box(-0.175, -0.005, 0.225, 0.118), ANY)],
            },
            {
                "key": "jutta", "label": "Jutta (Shoes)", "color": "#6b4a2b",
                "info": "Leather shoes with upturned, pointed toes, a style worn at court in the period.",
                "rules": [("front", box(-1.0, -1.05, 1.0, -0.865), ANY)],
            },
            {
                "key": "suruwal", "label": "Suruwal (Trousers)", "color": "#c9a227",
                "info": "Close-fitting trousers worn under the robe, tight from the knee down to the ankle.",
                "rules": [("front", box(-1.0, -0.865, 1.0, -0.475), ANY)],
            },
            {
                "key": "jama", "label": "Jama (Robe)", "color": "#f4f1ea", "default": True,
                "info": "A long-sleeved robe with a wide pleated skirt that falls to the knee, "
                        "the formal dress of the court.",
            },
        ],
    },

    "nepali_man": {
        "title": "Nepali Man in Daura Suruwal",
        "description": "A man in Daura Suruwal with a Dhaka Topi, the traditional dress of Nepali men.",
        "raw_mesh": "nepali_man.glb",
        "height_m": 1.70,
        "parts": [
            {
                "key": "dhaka_topi", "label": "Dhaka Topi", "color": "#2d3148",
                "info": "A cap made from Dhaka, a hand-woven patterned cotton cloth. It is taller at the "
                        "front than the back and is a symbol of Nepali identity.",
                "rules": [("side", [(-0.32, 0.90), (0.06, 0.825), (0.06, 1.05), (-0.32, 1.05)], ANY)],
            },
            {
                "key": "head", "color": "#b9865a",
                "rules": [("front", [(-0.125, 0.715), (0.135, 0.715), (0.15, 1.0), (-0.14, 1.0)], ANY)],
            },
            {
                "key": "hands", "color": "#b9865a",
                "rules": [("front", box(-0.245, -0.15, -0.075, -0.025), FRONT),
                          ("front", box(0.14, -0.15, 0.26, -0.015), (0.04, 9.0))],
            },
            {
                "key": "jutta", "label": "Jutta (Shoes)", "color": "#1c1c1e",
                "info": "Plain leather shoes, the usual footwear with Daura Suruwal today.",
                "rules": [("front", box(-1.0, -1.05, 1.0, -0.885), ANY)],
            },
            {
                "key": "daura", "label": "Daura (Shirt)", "color": "#8a97a8",
                "info": "A knee-length double-breasted shirt closed with eight ties instead of buttons. "
                        "Its closed neck and five pleats carry traditional religious meanings.",
                "rules": [("front", [(-0.045, 0.715), (0.135, 0.715), (0.065, 0.35), (0.025, 0.35)], (-9.0, -0.04)),
                          ("front", [(-0.36, -0.125), (0.0, -0.125), (0.05, -0.10), (0.25, -0.10),
                                     (0.25, -0.265), (-0.36, -0.265)], (-9.0, 0.02))],
            },
            {
                "key": "suruwal", "label": "Suruwal (Trousers)", "color": "#7f8c9d",
                "info": "Trousers that are loose at the top and narrow tightly towards the ankle.",
                "rules": [("front", box(-1.0, -0.885, 1.0, -0.265), FRONT),
                          ("front", [(-1.0, -0.885), (1.0, -0.885), (1.0, -0.30), (0.10, -0.30),
                                     (-0.05, -0.40), (-1.0, -0.20)], BACK)],
            },
            {
                "key": "coat", "label": "Coat", "color": "#22252b", "default": True,
                "info": "A Western-style coat worn over the daura. It was added to the outfit in the 19th century "
                        "and is now a standard part of formal dress.",
            },
        ],
    },

    "nepali_woman": {
        "title": "Nepali Woman in Kurtha Suruwal",
        "description": "A woman in Kurtha Suruwal with a Saal, everyday traditional dress for Nepali women.",
        "raw_mesh": "nepali_woman_a.glb",
        "height_m": 1.60,
        "parts": [
            {
                "key": "kitab", "color": "#2b2622",
                "rules": [("front", [(-0.155, 0.225), (0.075, 0.245), (0.095, -0.095), (-0.105, -0.095),
                                     (-0.145, 0.0)], (-9.0, -0.165))],
            },
            {
                "key": "hands", "color": "#c79a78",
                "rules": [("front", [(-0.335, 0.215), (-0.245, 0.225), (-0.075, 0.03), (-0.095, -0.115),
                                     (-0.205, -0.085)], (-9.0, -0.02)),
                          ("front", [(0.255, 0.215), (0.17, 0.225), (0.06, 0.03), (0.08, -0.115),
                                     (0.15, -0.065)], (-9.0, -0.06))],
            },
            {
                "key": "saal", "label": "Saal (Shawl)", "color": "#7a1f24",
                "info": "A long shawl draped over the shoulder. It is worn for warmth and modesty and is often "
                        "the most decorated piece of the outfit.",
                "rules": [("front", [(-0.345, 0.70), (-0.12, 0.735), (-0.10, 0.45), (-0.115, 0.22),
                                     (-0.27, 0.22), (-0.27, 0.50), (-0.345, 0.58)], (-9.0, 0.05)),
                          ("front", [(-0.39, 0.02), (-0.245, 0.10), (-0.135, -0.02), (-0.12, -0.30),
                                     (-0.11, -0.56), (-0.20, -0.60), (-0.20, -0.93), (-0.33, -0.93),
                                     (-0.43, -0.56)], (-9.0, 0.05)),
                          ("front", [(-0.08, 0.705), (-0.335, 0.69), (-0.30, 0.46), (-0.26, 0.46), (-0.26, 0.09),
                                     (-0.40, 0.04), (-0.43, -0.50),
                                     (-0.34, -0.93), (-0.08, -0.93), (0.04, -0.86), (0.0, -0.60),
                                     (-0.10, -0.30), (-0.10, 0.30)], (0.08, 9.0))],
            },
            {
                "key": "head", "color": "#c79a78",
                "rules": [("front", [(-0.125, 0.715), (0.04, 0.715), (0.085, 0.82), (0.06, 0.93),
                                     (-0.11, 0.93), (-0.155, 0.82)], (-9.0, -0.02)),
                          ("front", box(-0.10, 0.62, 0.02, 0.72), (-9.0, -0.02))],
            },
            {
                "key": "hair", "color": "#5a3d28",
                "rules": [("front", box(-0.22, 0.70, 0.17, 1.05), ANY),
                          ("front", [(0.0, 0.72), (0.14, 0.76), (0.13, 0.55), (0.095, 0.41),
                                     (0.035, 0.41), (0.0, 0.60)], (-9.0, -0.02))],
            },
            {
                "key": "feet", "color": "#c79a78",
                "rules": [("front", box(-1.0, -1.05, 1.0, -0.875), ANY)],
            },
            {
                "key": "suruwal", "label": "Suruwal (Trousers)", "color": "#6e1a1e",
                "info": "Trousers worn under the kurtha, gathered or fitted closely at the ankle.",
                "rules": [("front", [(-0.21, -0.56), (-0.12, -0.51), (-0.025, -0.325), (0.035, -0.325),
                                     (0.125, -0.505), (0.23, -0.505), (0.5, -1.0), (-0.4, -1.0)], FRONT),
                          ("front", box(-1.0, -1.05, 1.0, -0.465), BACK)],
            },
            {
                "key": "kurtha", "label": "Kurtha (Tunic)", "color": "#23201f", "default": True,
                "info": "A long tunic that reaches the knee, with slits at the sides so the wearer can move "
                        "freely. It is worn over the suruwal.",
            },
        ],
    },

    # Painted from a reference photograph instead of flat colours: see 05_prepare_texture.py.
    # Per part, "back" says how to colour faces the photo cannot see (the back of the figure):
    #   "project"  reuse the photo, "#rrggbb" a fixed colour, "flat" the typical colour of
    #   "swatch_box" (x0, z0, x1, z1, in raw-mesh coordinates). "back_bands" lists height
    #   ranges (z0, z1) where the photo is reused anyway, for trim that runs round the garment.
    "nepali_man_v2": {
        "title": "Nepali Man with Istakot and Dhaka Topi",
        "description": "A man in Daura Suruwal, wearing a patterned Istakot (waistcoat) and a Dhaka Topi.",
        "raw_mesh": "nepali_man_v2.glb",
        "height_m": 1.72,
        "texture": {"photo": "man_vest.jpg"},
        "parts": [
            {
                "key": "dhaka_topi", "label": "Dhaka Topi", "color": "#b5455a", "back": "project",
                "back_remap": [((-1.0, 0.70, 1.0, 1.2), 0.0, 0.05)],
                "info": "A cap cut from Dhaka, a hand-woven patterned cloth. It is taller at the front than "
                        "at the back and is a symbol of Nepali identity.",
                "rules": [("front", box(-0.25, 0.835, 0.25, 1.10), ANY)],
            },
            {
                "key": "hands", "color": "#b98a68", "back": "project",
                "rules": [("front", box(-0.32, -0.24, -0.19, -0.07), (-0.16, 0.04)),
                          ("front", box(0.17, -0.24, 0.29, -0.07), (-0.16, 0.04))],
            },
            {
                "key": "neck", "color": "#b98a68", "back": "#b78864",
                "rules": [("front", box(-0.17, 0.645, 0.15, 0.74), ANY)],
            },
            {
                "key": "head", "color": "#b98a68", "back": "#241c1a",
                "rules": [("front", box(-0.17, 0.74, 0.15, 0.835), ANY)],
            },
            {
                "key": "istakot", "label": "Istakot (Waistcoat)", "color": "#a02b3a", "back": "project",
                "back_remap": [((-0.12, 0.44, 0.12, 0.66), 0.105, -0.20)],
                "info": "A sleeveless waistcoat worn over the daura. This one is cut from patterned Dhaka-style "
                        "cloth, with the diamond motifs the fabric is known for.",
                "rules": [("front", [(-0.235, 0.60), (-0.12, 0.645), (-0.095, 0.62), (-0.02, 0.47),
                                     (0.065, 0.62), (0.12, 0.645), (0.235, 0.60), (0.215, 0.45),
                                     (0.215, -0.045), (-0.205, -0.045), (-0.205, 0.45)], ANY),
                          ("front", [(-0.235, 0.60), (-0.12, 0.645), (0.12, 0.645), (0.235, 0.60),
                                     (0.215, 0.45), (0.215, -0.045), (-0.205, -0.045), (-0.205, 0.45)],
                           (-0.06, 9.0))],
            },
            {
                "key": "shoes", "label": "Shoes", "color": "#18181a", "back": "#18181a",
                "info": "Plain black leather shoes, now the usual footwear with Daura Suruwal.",
                "rules": [("front", box(-1.0, -1.10, 1.0, -0.915), ANY)],
            },
            {
                "key": "suruwal", "label": "Suruwal (Trousers)", "color": "#a79fb2",
                "back": "flat", "swatch_box": (-0.16, -0.80, -0.06, -0.50), "back_bands": [(-0.915, -0.84)],
                "side_normal": -0.2,
                "info": "Trousers worn with the daura, traditionally loose at the top and narrowing towards the "
                        "ankle. Here they are cut straight, with a band of the Dhaka pattern at each cuff.",
                "rules": [("front", box(-1.0, -0.915, 1.0, -0.335), ANY)],
            },
            {
                "key": "daura", "label": "Daura (Shirt)", "color": "#a79fb2", "default": True,
                "back": "flat", "swatch_box": (-0.12, -0.30, 0.12, -0.10), "back_bands": [(-0.345, -0.25)],
                "side_normal": -0.2,
                "info": "A knee-length shirt with a crossed front that closes with ties at the side. It is worn "
                        "over the suruwal and under the waistcoat.",
            },
        ],
    },
}
