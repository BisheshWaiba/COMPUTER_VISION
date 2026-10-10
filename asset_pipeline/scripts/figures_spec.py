"""Single source of truth for the figures: which raw mesh each one comes
from, how it is cut into named parts, and the text shown for each part.

The part keys below become the node names in the exported .glb and the keys of
the "parts" dictionary in assets/figures.json, so they always match.

The English text sits with each figure and part in FIGURES. The Nepali text for
the same figures and parts is in NEPALI at the bottom of this file.

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
        # Painted from the picture the mesh was made from: a bronze statue, so the metal, the
        # verdigris and the marigold garland come straight from the photo (see the notes on
        # "texture" under nepali_man_v2 for what each setting does).
        "texture": {
            "photo": "prepared/prithvi_narayan_shah.png",
            # the photo is a pale, low-colour bronze: bring out the gold and the teal patina
            "grade": {"vibrance": 1.9, "warmth": 4.0, "contrast": 1.1},
            # the plume's dark inner side sits behind the cap in the photo but lands on the
            # mesh's bigger cap: paint that corner with the cap's own colour
            "clean_front": {
                "fill": [((0.045, 0.745, 0.17, 0.835), (-0.09, 0.715, -0.03, 0.765))],
            },
            "clean_back": {
                # applied in order: the garland, beads and collar hang on the front only, so cover
                # them with robe; then the face, then the crown and plume, with the robe too
                "copy": [((-0.14, 0.10, 0.23, 0.58), 0.0, -0.58),
                         ((-0.14, 0.50, 0.20, 0.705), 0.0, -0.34),
                         ((-0.16, 0.705, 0.40, 1.0), 0.0, -0.52)],
            },
        },
        "parts": [
            {
                "key": "khukuri", "label": "Khukuri", "color": "#8a6a2f", "back": "project", "side": "front",
                "info": "The curved knife of the Gorkhali soldier, carried tucked into the waist sash. "
                        "It served as both an everyday tool and a weapon, and remains a national symbol of Nepal.",
                "rules": [("front", [(-0.115, -0.10), (-0.10, -0.035), (-0.02, -0.012), (0.065, -0.012),
                                     (0.06, -0.06), (-0.04, -0.105)], (-9.0, -0.10))],
            },
            {
                "key": "hands", "color": "#b9865a", "back": "front", "side": "front",
                "rules": [("front", box(-0.40, 0.81, -0.25, 1.05), ANY),
                          ("front", box(0.235, -0.215, 0.39, -0.085), (-9.0, -0.065))],
            },
            {
                "key": "tarwar", "label": "Tarwar (Sword)", "color": "#9aa0a8", "back": "project", "side": "front",
                "info": "A long curved sword held point-down in the left hand. Swords like this were carried "
                        "by Gorkhali commanders during the unification campaigns.",
                "rules": [("front", [(0.215, -0.20), (0.39, -0.20), (0.39, -0.32), (0.32, -0.45), (0.32, -0.67),
                                     (0.23, -0.75), (0.14, -0.87), (0.04, -0.985), (-0.04, -0.985), (-0.03, -0.90),
                                     (0.07, -0.80), (0.15, -0.66), (0.19, -0.45), (0.215, -0.30)], (-9.0, -0.125))],
            },
            {
                "key": "dhal", "label": "Dhal (Shield)", "color": "#3a3028", "back": "flat", "side": "flat", "swatch_box": (0.27, -0.30, 0.31, -0.10),
                "info": "A round shield, traditionally made of hide or metal with raised bosses, "
                        "worn at the hip and used together with the sword.",
                "rules": [("side", disc(0.03, -0.14, 0.17), (0.135, 0.245)),
                          ("side", arc(0.03, -0.14, 0.17, -120, 120), (0.135, 0.40))],
            },
            {
                "key": "shripech", "label": "Shripech (Crown)", "color": "#d4af37", "back": "project", "side": (0.0, 0.6, 0.03),
                "info": "The jewelled royal crown of the Shah kings, topped with a plume of "
                        "bird-of-paradise feathers.",
                "rules": [("front", box(-0.16, 0.69, 0.42, 1.05), ANY)],
            },
            {
                "key": "head", "color": "#b9865a", "back": "project", "side": "front",
                "rules": [("front", [(-0.095, 0.57), (0.105, 0.57), (0.105, 0.615), (0.155, 0.615), (0.155, 0.705),
                                     (-0.14, 0.705), (-0.14, 0.615), (-0.095, 0.615)], ANY),
                          ("front", [(-0.07, 0.515), (0.075, 0.515), (0.10, 0.58), (-0.09, 0.58)], (-9.0, -0.05))],
            },
            {
                "key": "mala", "label": "Mala (Garland)", "color": "#e8791c", "back": "#e5781c", "side": "flat",
                "info": "A garland worn around the neck. Statues of Prithvi Narayan Shah are garlanded with "
                        "marigolds on Prithvi Jayanti, the day that marks his birth.",
                "rules": [("front", [(-0.125, 0.61), (-0.05, 0.61), (-0.03, 0.50), (0.02, 0.31), (0.02, 0.22),
                                     (-0.04, 0.22), (-0.105, 0.36), (-0.135, 0.50)], FRONT),
                          ("front", [(0.085, 0.61), (0.175, 0.61), (0.175, 0.48), (0.125, 0.33), (0.07, 0.22),
                                     (0.02, 0.22), (0.02, 0.31), (0.075, 0.48)], FRONT),
                          ("front", box(-0.035, 0.005, 0.075, 0.24), (-9.0, -0.10))],
            },
            {
                "key": "patuka", "label": "Patuka (Waist Sash)", "color": "#f2efe6", "back": "project", "side": (0.18, 0.5),
                "info": "A long cloth wound around the waist over the robe. It holds the khukuri in place "
                        "and supports the back.",
                "rules": [("front", box(-0.175, -0.005, 0.225, 0.118), ANY)],
            },
            {
                "key": "jutta", "label": "Jutta (Shoes)", "color": "#6b4a2b", "back": "project", "side": "front",
                "info": "Leather shoes with upturned, pointed toes, a style worn at court in the period.",
                "rules": [("front", box(-1.0, -1.05, 1.0, -0.865), ANY)],
            },
            {
                "key": "suruwal", "label": "Suruwal (Trousers)", "color": "#c9a227", "back": "project", "side": (0.12, 0.5),
                "info": "Close-fitting trousers worn under the robe, tight from the knee down to the ankle.",
                "rules": [("front", box(-1.0, -0.865, 1.0, -0.475), ANY)],
            },
            {
                "key": "jama", "label": "Jama (Robe)", "color": "#f4f1ea", "default": True, "back": "project", "side": (0.2, 0.5), "side_bands": [(-1.0, 0.0, (0.15, 0.5))],
                "info": "A long-sleeved robe with a wide pleated skirt that falls to the knee, "
                        "the formal dress of the court.",
            },
        ],
    },

    # Painted from a reference photograph instead of flat colours: see 05_prepare_texture.py.
    #
    # The photo only shows the front, so 05 also makes a cleaned copy of it for the back and
    # sides ("clean_back"): things that should not show there are covered, either by copying
    # another patch of the photo over them or by filling them with a fabric colour.
    # Boxes are (x0, z0, x1, z1) in raw-mesh coordinates.
    #
    # Per part:
    #   "back"        what back-facing faces show: "project" the cleaned photo, "front" the
    #                 original photo, "#rrggbb" a fixed colour, or "flat" the typical colour of
    #                 "swatch_box"
    #   "side"        (column, spread[, lift]): side-facing faces show a vertical strip of the
    #                 photo centred on x = +/-column and widened by `spread` per unit of depth,
    #                 so the fabric continues round the side instead of smearing; `lift` reads
    #                 the strip that much higher up
    #   "side_bands"  [(z0, z1, strip)]: a different strip for side faces between those heights
    #   "side_from"   "front": take the side strip from the front photo even though the back
    #                 of the part uses the cleaned / back photo. "side": "flat" uses the swatch;
    #                 "side": "front" carries the front photo round onto the sides (best for
    #                 faces, where a strip would cut across the cheeks).
    #   "back_remap"  [(box, dx, dz)]: back faces inside box look dx, dz away in the photo
    #   "shift"       (dx, dz): the whole part is this far away in the photo from where it is
    #                 on the mesh (the mesh and the photo never line up exactly everywhere)
    "nepali_man_v2": {
        "title": "Nepali Man with Istakot and Dhaka Topi",
        "description": "A man in Daura Suruwal, wearing a patterned Istakot (waistcoat) and a Dhaka Topi.",
        "raw_mesh": "nepali_man_v2.glb",
        "height_m": 1.72,
        "texture": {
            "photo": "man_vest.jpg",
            "clean_back": {
                # applied in order: first hide the buttons, then cover the V-neck with pattern
                "copy": [((-0.04, -0.05, 0.035, 0.46), 0.075, 0.0),
                         ((-0.12, 0.44, 0.12, 0.66), 0.08, -0.20)],
                # paint the hands out with shirt fabric
                "fill": [((-0.345, -0.27, -0.175, -0.08), (-0.12, -0.30, 0.12, -0.10)),
                         ((0.165, -0.27, 0.335, -0.08), (-0.12, -0.30, 0.12, -0.10))],
            },
        },
        "parts": [
            {
                "key": "dhaka_topi", "label": "Dhaka Topi", "color": "#b5455a",
                "back": "project", "side": (0.0, 0.6, 0.03), "back_remap": [((-1.0, 0.70, 1.0, 1.2), 0.0, 0.05)],
                "info": "A cap cut from Dhaka, a hand-woven patterned cloth. It is taller at the front than "
                        "at the back and is a symbol of Nepali identity.",
                "rules": [("front", box(-0.25, 0.835, 0.25, 1.10), ANY)],
            },
            {
                "key": "hands", "color": "#b98a68", "back": "front", "side": (0.245, 0.5), "shift": (0.0, 0.04),
                "rules": [("front", box(-0.32, -0.215, -0.20, -0.07), (-0.14, 0.02)),
                          ("front", box(0.18, -0.215, 0.29, -0.07), (-0.14, 0.02))],
            },
            {
                "key": "neck", "color": "#b98a68", "side": "front",
                "back": "flat", "swatch_box": (0.03, 0.74, 0.07, 0.78),
                "rules": [("front", box(-0.17, 0.645, 0.15, 0.74), ANY)],
            },
            {
                "key": "head", "color": "#b98a68", "back": "#241c1a", "side": "front",
                "rules": [("front", box(-0.17, 0.74, 0.15, 0.835), ANY)],
            },
            {
                "key": "istakot", "label": "Istakot (Waistcoat)", "color": "#a02b3a",
                "back": "project", "side": (0.11, 0.5),
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
                "key": "shoes", "label": "Shoes", "color": "#18181a", "back": "project", "side": (0.14, 0.3),
                "info": "Plain black leather shoes, now the usual footwear with Daura Suruwal.",
                "rules": [("front", box(-1.0, -1.10, 1.0, -0.915), ANY)],
            },
            {
                "key": "suruwal", "label": "Suruwal (Trousers)", "color": "#a79fb2",
                "back": "project", "side": (0.115, 0.5),
                "info": "Trousers worn with the daura, traditionally loose at the top and narrowing towards the "
                        "ankle. Here they are cut straight, with a band of the Dhaka pattern at each cuff.",
                "rules": [("front", box(-1.0, -0.915, 1.0, -0.335), ANY)],
            },
            {
                "key": "daura", "label": "Daura (Shirt)", "color": "#a79fb2", "default": True,
                "back": "project", "side": (0.27, 0.35), "side_bands": [(-1.0, -0.07, (0.17, 0.3))],
                "info": "A knee-length shirt with a crossed front that closes with ties at the side. It is worn "
                        "over the suruwal and under the waistcoat.",
            },
        ],
    },
    # Shape from the front (namaste) photo; the back is painted from a second photo taken
    # from behind. In that back photo the arms hang down, which the model's arms do not, so
    # they are left out ("ignore", as fractions of the back photo) and the arms are skin
    # colour wherever the front photo cannot see them.
    "nepali_woman_v2": {
        "title": "Nepali Woman in Gunyu Cholo",
        "description": "A woman in Gunyu Cholo with a Patuka, Pote and gold jewellery, greeting with a namaste.",
        "raw_mesh": "nepali_woman_v2.glb",
        "height_m": 1.58,
        "texture": {
            "photo": "woman_namaste_front.png",
            "back_photo": {
                "photo": "woman_namaste_back.png",
                "ignore": [(0.07, 0.335, 0.215, 0.56), (0.625, 0.335, 0.77, 0.63)],
            },
        },
        "parts": [
            {
                "key": "shirbandi", "label": "Shirbandi (Head Ornament)", "color": "#d4a437",
                "back": "project", "side": "front",
                "info": "A gold ornament worn across the forehead and along the parting of the hair, "
                        "usually on festive occasions.",
                "rules": [("front", box(-0.20, 0.855, 0.20, 0.91), ANY),
                          ("front", box(-0.03, 0.91, 0.03, 1.02), FRONT)],
            },
            {
                "key": "head", "color": "#8a5a3c", "back": "project", "side": "front",
                "rules": [("side", [(-0.30, 0.70), (-0.10, 0.70), (0.0, 0.735), (0.14, 0.79),
                                    (0.30, 0.79), (0.30, 1.10), (-0.30, 1.10)], ANY)],
            },
            {
                "key": "kantha", "label": "Kantha (Gold Necklace)", "color": "#c9972c",
                "back": "project", "side": (0.12, 0.15), "side_from": "front",
                "info": "A heavy necklace of gold beads worn close around the neck. Longer strands of beads "
                        "hang below it on the chest.",
                "rules": [("side", [(-0.14, 0.60), (-0.04, 0.595), (0.15, 0.68), (0.15, 0.79), (0.0, 0.735),
                                    (-0.10, 0.70), (-0.14, 0.70)], (-0.165, 0.155))],
            },
            {
                "key": "chura", "label": "Chura (Bangles)", "color": "#c8452c", "back": "front", "side": (0.10, 0.2),
                "info": "Stacks of bangles worn on both wrists, here in red and gold.",
                "rules": [("front", box(-0.15, 0.355, -0.065, 0.475), (-9.0, -0.08)),
                          ("front", box(0.055, 0.355, 0.125, 0.475), (-9.0, -0.08))],
            },
            {
                "key": "arms", "color": "#8a5a3c", "back": "flat", "side": "flat",
                "swatch_box": (-0.30, 0.36, -0.20, 0.42),
                "rules": [("front", box(-0.065, 0.43, 0.06, 0.645), (-9.0, -0.14)),
                          ("front", box(-0.25, 0.31, -0.065, 0.47), (-9.0, -0.08)),
                          ("front", box(0.06, 0.31, 0.25, 0.47), (-9.0, -0.08)),
                          ("front", box(-0.42, 0.29, -0.25, 0.485), ANY),
                          ("front", box(0.25, 0.29, 0.42, 0.485), ANY)],
            },
            {
                "key": "pote", "label": "Pote (Bead Strands)", "color": "#2f6b3a", "back": "project", "side": (0.2, 0.2),
                "info": "Many strands of small glass beads, here in green, worn like a sash from one shoulder to "
                        "the opposite hip. Pote is traditionally a sign of a married woman.",
                "rules": [("front", [(-0.215, 0.62), (-0.125, 0.62), (-0.09, 0.47), (-0.18, 0.47)], FRONT),
                          ("front", [(-0.16, 0.385), (-0.10, 0.385), (0.285, 0.03), (0.285, -0.055),
                                     (0.22, -0.055), (-0.16, 0.30)], FRONT),
                          ("front", [(-0.262, 0.606), (-0.19, 0.658), (0.306, -0.004), (0.234, -0.056)], BACK)],
            },
            {
                "key": "feet", "color": "#8a5a3c", "back": "project", "side": (0.085, 0.3),
                "rules": [("front", box(-1.0, -1.10, 1.0, -0.875), ANY)],
            },
            {
                "key": "patuka", "label": "Patuka (Waistband)", "color": "#f0c93a",
                "back": "project", "side": (0.17, 0.3),
                "info": "A long cloth wound several times around the waist. It holds the skirt in place and "
                        "supports the back during work.",
                "rules": [("front", box(-1.0, 0.13, 1.0, 0.32), ANY)],
            },
            {
                "key": "cholo", "label": "Cholo (Blouse)", "color": "#8e1420", "back": "project",
                "side": (0.28, 0.2), "side_bands": [(-1.0, 0.46, (0.17, 0.25))],
                "info": "A fitted blouse, here in red velvet with gold trim on the short sleeves.",
                "rules": [("front", box(-1.0, 0.32, 1.0, 0.72), ANY)],
            },
            {
                "key": "gunyu", "label": "Gunyu (Wrap Skirt)", "color": "#c8321e", "default": True,
                "back": "project", "side": (0.15, 0.4),
                "info": "A length of printed cotton wrapped around the lower body and tucked in at the waist. "
                        "Bright floral prints like this one are typical.",
            },
        ],
    },
    # Generated outside this pipeline (ComfyUI, Pixal3D) from the well-known painted portrait,
    # and brought in with 02_import_textured_mesh.py. It arrives fully textured, so
    # "texture": {"own": True} tells 03 to keep that texture and only cut the parts.
    "prithvi_narayan_shah_v2": {
        "title": "Prithvi Narayan Shah (Portrait)",
        "description": "The king who began the unification of Nepal, modelled on his best-known painted "
                       "portrait, with one finger raised.",
        "raw_mesh": "prithvi_narayan_shah_v2.glb",
        "height_m": 1.80,
        "texture": {"own": True},
        "parts": [
            {
                "key": "khukuri", "label": 'Khukuri', "color": "#8a6a2f",
                "info": 'The curved knife of the Gorkhali soldier, carried tucked into the waist sash. It served as both an everyday tool and a weapon, and remains a national symbol of Nepal.',
                "rules": [("front", box(-0.02, 0.215, 0.11, 0.42), (-9.0, -0.13))],
            },
            {
                "key": "hands", "color": "#b9865a",
                "rules": [("front", box(-0.47, 0.80, -0.33, 1.05), ANY),
                          ("front", box(0.30, -0.13, 0.43, 0.01), ANY)],
            },
            {
                "key": "tarwar", "label": 'Tarwar (Sword)', "color": "#9aa0a8",
                "info": 'A long curved sword held point-down in the left hand. Swords like this were carried by Gorkhali commanders during the unification campaigns.',
                "rules": [("front", box(0.27, -0.24, 0.46, -0.02), ANY),
                          ("front", [(0.26, -0.22), (0.40, -0.22), (0.39, -0.68), (0.27, -0.68), (0.07, -0.80),
                                     (0.02, -0.76), (0.19, -0.60), (0.21, -0.46), (0.26, -0.46)], (-9.0, 0.05))],
            },
            {
                "key": "dhal", "label": 'Dhal (Shield)', "color": "#3a3028",
                "info": 'A round shield, traditionally made of hide or metal with raised bosses, worn at the hip and used together with the sword.',
                "rules": [("side", disc(-0.15, -0.06, 0.135), (0.09, 0.285))],
            },
            {
                "key": "shripech", "label": 'Shripech (Crown)', "color": "#d4af37",
                "info": 'The jewelled royal crown of the Shah kings, topped with a plume of bird-of-paradise feathers.',
                "rules": [("front", box(-0.21, 0.80, 0.14, 1.05), ANY),
                          ("front", box(-0.075, 0.34, 0.02, 0.80), (0.11, 9.0))],
            },
            {
                "key": "head", "color": "#b9865a",
                "rules": [("front", [(-0.15, 0.66), (-0.07, 0.61), (0.05, 0.61), (0.11, 0.66),
                                     (0.11, 0.80), (-0.15, 0.80)], ANY)],
            },
            {
                "key": "mala", "label": "Mala (Necklaces)", "color": "#e6dcc0",
                "info": "Strings of pearls and gold worn around the neck and across the chest, "
                        "a mark of royal rank.",
                "rules": [("front", [(-0.16, 0.63), (0.12, 0.63), (0.10, 0.45), (0.02, 0.30),
                                     (-0.05, 0.30), (-0.14, 0.47)], (-9.0, -0.05))],
            },
            {
                "key": "patuka", "label": 'Patuka (Waist Sash)', "color": "#f2efe6",
                "info": 'A long cloth wound around the waist over the robe. It holds the khukuri in place and supports the back.',
                "rules": [("front", box(-0.25, 0.105, 0.22, 0.255), ANY),
                          ("front", box(-0.17, 0.0, -0.01, 0.11), (-9.0, -0.15))],
            },
            {
                "key": "jutta", "label": 'Jutta (Shoes)', "color": "#6b4a2b",
                "info": "Leather court shoes, shown here in brown.",
                "rules": [("front", box(-1.0, -1.10, 1.0, -0.845), ANY)],
            },
            {
                "key": "suruwal", "label": 'Suruwal (Trousers)', "color": "#c9a227",
                "info": 'Close-fitting trousers worn under the robe, tight from the knee down to the ankle.',
                "rules": [("front", box(-0.24, -0.845, 0.20, -0.43), (-9.0, 0.21))],
            },
            {
                "key": "jama", "label": 'Jama (Robe)', "color": "#f4f1ea", "default": True,
                "info": 'A long-sleeved robe with a wide pleated skirt that falls to the knee, the formal dress of the court.',
            },
        ],
    },
}


# Nepali text: figure -> title, description, and (label, info) for every part that has a
# label in FIGURES. 04_verify_and_write_content.py refuses to run if an entry is missing.
# The app's Devanagari font has no Latin letters, so do not use any here.
NEPALI = {
    "prithvi_narayan_shah": {
        "title": "पृथ्वीनारायण शाह",
        "description": "गोरखाका राजा, जसले अठारौँ शताब्दीमा नेपाल एकीकरणको सुरुवात गरे। "
                       "यहाँ उनलाई एउटा औँला उठाएको परिचित मुद्रामा देखाइएको छ।",
        "parts": {
            "khukuri": ("खुकुरी",
                        "गोर्खाली सिपाहीको बाङ्गो धार भएको हतियार, जुन कम्मरको पटुकामा सिउरिन्छ। यो दैनिक "
                        "काममा र हतियार दुवैको रूपमा प्रयोग हुन्थ्यो र आज पनि नेपालको राष्ट्रिय प्रतीक मानिन्छ।"),
            "tarwar": ("तरवार",
                       "देब्रे हातमा टुप्पो तलतिर पारेर समातिएको लामो, बाङ्गो तरवार। एकीकरण अभियानका बेला "
                       "गोर्खाली सेनापतिहरूले यस्ता तरवार बोक्थे।"),
            "dhal": ("ढाल",
                     "छाला वा धातुबाट बनेको गोलो ढाल, जसमा उठेका बुट्टा हुन्छन्। यो कम्मरमा भिरिन्थ्यो र "
                     "तरवारसँगै प्रयोग गरिन्थ्यो।"),
            "shripech": ("श्रीपेच",
                         "शाह राजाहरूको रत्नजडित राजमुकुट, जसको टुप्पोमा स्वर्गचरीको प्वाँखको कल्की हुन्छ।"),
            "mala": ("माला",
                     "घाँटीमा लगाइने माला। पृथ्वीनारायण शाहको जन्मजयन्ती अर्थात् पृथ्वी जयन्तीका दिन उनका "
                     "सालिकमा सयपत्री फूलको माला लगाइन्छ।"),
            "patuka": ("पटुका",
                       "जामामाथि कम्मरमा बेरिने लामो कपडा। यसले खुकुरीलाई अड्याउँछ र ढाडलाई टेवा दिन्छ।"),
            "jutta": ("जुत्ता",
                      "टुप्पो माथितिर फर्केको चुच्चे छालाको जुत्ता, जुन त्यस समयमा दरबारमा लगाइन्थ्यो।"),
            "suruwal": ("सुरुवाल",
                        "जामाभित्र लगाइने कसिलो सुरुवाल, जुन घुँडादेखि गोलीगाँठोसम्म कसिएको हुन्छ।"),
            "jama": ("जामा",
                     "लामो बाहुला र घुँडासम्म आउने, चुन्ने परेको फराकिलो घेरा भएको पोसाक। यो दरबारको "
                     "औपचारिक पहिरन थियो।"),
        },
    },
    "nepali_man_v2": {
        "title": "इस्टकोट र ढाका टोपीमा नेपाली पुरुष",
        "description": "दौरा सुरुवालमाथि बुट्टेदार इस्टकोट र ढाका टोपी लगाएका पुरुष।",
        "parts": {
            "dhaka_topi": ("ढाका टोपी",
                           "हातले बुनेको बुट्टेदार ढाका कपडाबाट बनेको टोपी। यो अगाडि अग्लो र पछाडि होचो "
                           "हुन्छ र नेपाली पहिचानको प्रतीक मानिन्छ।"),
            "istakot": ("इस्टकोट",
                        "दौरामाथि लगाइने बाहुला नभएको कोट। यो ढाका शैलीको बुट्टेदार कपडाबाट बनेको छ, "
                        "जसमा यस कपडाको चिनारी मानिने हीरा आकारका बुट्टा छन्।"),
            "shoes": ("जुत्ता",
                      "कालो छालाको सादा जुत्ता, जुन आजकल दौरा सुरुवालसँग प्रायः लगाइन्छ।"),
            "suruwal": ("सुरुवाल",
                        "दौरासँग लगाइने सुरुवाल, जुन परम्परागत रूपमा माथि खुकुलो र गोलीगाँठोतिर साँघुरो हुन्छ। "
                        "यहाँ यो सिधा काटिएको छ र मोहोतामा ढाका बुट्टाको पट्टी छ।"),
            "daura": ("दौरा",
                      "घुँडासम्म आउने पोसाक, जसको अगाडिका पल्ला एकमाथि अर्को खप्टिन्छन् र छेउमा तुनाले "
                      "बाँधिन्छन्। यो सुरुवालमाथि र इस्टकोटभित्र लगाइन्छ।"),
        },
    },
    "nepali_woman_v2": {
        "title": "गुन्यू चोलोमा नेपाली महिला",
        "description": "गुन्यू चोलो, पटुका, पोते र सुनका गहनामा सजिएकी, नमस्ते गरिरहेकी महिला।",
        "parts": {
            "shirbandi": ("शिरबन्दी",
                          "निधार र सिउँदोमा लगाइने सुनको गहना, जुन प्रायः चाडपर्व र उत्सवमा लगाइन्छ।"),
            "kantha": ("कण्ठा",
                       "घाँटीमा कसिलो गरी लगाइने सुनका दानाको गह्रौँ माला। यसमुनि छातीमा लामा मालाहरू "
                       "झुन्डिएका छन्।"),
            "chura": ("चुरा",
                      "दुवै नाडीमा लगाइएका चुराका लहर, यहाँ रातो र सुनौलो रङमा।"),
            "pote": ("पोते",
                     "ससाना काँचका दानाका धेरै लहर, यहाँ हरियो रङमा, एउटा काँधबाट अर्कोतिरको कम्मरसम्म "
                     "छड्के पारेर लगाइएको। पोते परम्परागत रूपमा विवाहित महिलाको चिनो मानिन्छ।"),
            "patuka": ("पटुका",
                       "कम्मरमा धेरै फेरो बेरिने लामो कपडा। यसले गुन्यूलाई अड्याउँछ र काम गर्दा ढाडलाई "
                       "टेवा दिन्छ।"),
            "cholo": ("चोलो",
                      "जिउमा ठिक्क मिल्ने चोलो, यहाँ रातो मखमलको, छोटा बाहुलामा सुनौलो किनारा भएको।"),
            "gunyu": ("गुन्यू",
                      "छापिएको सुती कपडा, जुन शरीरको तल्लो भागमा बेरेर कम्मरमा सिउरिन्छ। यस्ता चहकिला "
                      "फूलबुट्टे छाप धेरै प्रचलित छन्।"),
        },
    },
    "prithvi_narayan_shah_v2": {
        "title": "पृथ्वीनारायण शाह (चित्र)",
        "description": "नेपाल एकीकरणको सुरुवात गर्ने राजा, उनको सबैभन्दा परिचित चित्रमा जस्तै "
                       "एउटा औँला उठाएको मुद्रामा।",
        "parts": {
            "khukuri": ('खुकुरी',
                'गोर्खाली सिपाहीको बाङ्गो धार भएको हतियार, जुन कम्मरको पटुकामा सिउरिन्छ। यो दैनिक काममा र हतियार दुवैको रूपमा प्रयोग हुन्थ्यो र आज पनि नेपालको राष्ट्रिय प्रतीक मानिन्छ।'),
            "tarwar": ('तरवार',
                'देब्रे हातमा टुप्पो तलतिर पारेर समातिएको लामो, बाङ्गो तरवार। एकीकरण अभियानका बेला गोर्खाली सेनापतिहरूले यस्ता तरवार बोक्थे।'),
            "dhal": ('ढाल',
                'छाला वा धातुबाट बनेको गोलो ढाल, जसमा उठेका बुट्टा हुन्छन्। यो कम्मरमा भिरिन्थ्यो र तरवारसँगै प्रयोग गरिन्थ्यो।'),
            "shripech": ('श्रीपेच',
                'शाह राजाहरूको रत्नजडित राजमुकुट, जसको टुप्पोमा स्वर्गचरीको प्वाँखको कल्की हुन्छ।'),
            "mala": ("माला",
                "घाँटी र छातीमा लगाइएका मोती र सुनका मालाहरू, जुन राजकीय मर्यादाको चिनो हुन्।"),
            "patuka": ('पटुका',
                'जामामाथि कम्मरमा बेरिने लामो कपडा। यसले खुकुरीलाई अड्याउँछ र ढाडलाई टेवा दिन्छ।'),
            "jutta": ("जुत्ता",
                "दरबारमा लगाइने छालाको जुत्ता, यहाँ खैरो रङमा देखाइएको।"),
            "suruwal": ('सुरुवाल',
                'जामाभित्र लगाइने कसिलो सुरुवाल, जुन घुँडादेखि गोलीगाँठोसम्म कसिएको हुन्छ।'),
            "jama": ('जामा',
                'लामो बाहुला र घुँडासम्म आउने, चुन्ने परेको फराकिलो घेरा भएको पोसाक। यो दरबारको औपचारिक पहिरन थियो।'),
        },
    },
}
