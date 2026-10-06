"""Turn a model's surface into a coloured point cloud.

A point cloud is what a 3D scanner or a photogrammetry run gives you before any
triangles are built: only positions and colours. The figures here are meshes, so
this module goes the other way and scatters points over their surface, with the
colour of the photo texture at each spot. It needs nothing but Panda3D.
"""
import bisect
import math
import random

from panda3d.core import (Geom, GeomNode, GeomPoints, GeomVertexData, GeomVertexFormat,
                          GeomVertexReader, GeomVertexWriter, LColor, LPoint3f, MaterialAttrib,
                          NodePath, TextureAttrib)

GREY = (0.7, 0.7, 0.7)  # a surface with neither a texture nor a material colour


def _column(data, name, width):
    """Every value of one vertex column as a list of tuples."""
    if not data.hasColumn(name):
        return None
    reader = GeomVertexReader(data, name)
    read = reader.getData3f if width == 3 else reader.getData2f
    return [tuple(read()) for _ in range(data.getNumRows())]


class Surface:
    """The triangles of one named part, ready to be sampled."""

    def __init__(self, part, model):
        self.name = part.getName()
        self.triangles = []   # (a, b, c, uv_a, uv_b, uv_c, colour_source)
        self.cumulative = []  # running total of the triangle areas
        self.area = 0.0

        node = part.node()
        to_model = part.getMat(model)
        for i in range(node.getNumGeoms()):
            geom = node.getGeom(i)
            data = geom.getVertexData()
            positions = [tuple(to_model.xformPoint(LPoint3f(*p))) for p in _column(data, "vertex", 3)]
            uvs = _column(data, "texcoord.0", 2) or _column(data, "texcoord", 2)  # glTF names the first set .0
            source = self._colour_source(part.getNetState().compose(node.getGeomState(i)), uvs is not None)
            for k in range(geom.getNumPrimitives()):
                primitive = geom.getPrimitive(k).decompose()
                for t in range(primitive.getNumVertices() // 3):
                    a, b, c = (primitive.getVertex(3 * t + n) for n in range(3))
                    area = _area(positions[a], positions[b], positions[c])
                    if area <= 0.0:
                        continue
                    self.area += area
                    self.cumulative.append(self.area)
                    self.triangles.append((positions[a], positions[b], positions[c],
                                           uvs[a] if uvs else None, uvs[b] if uvs else None,
                                           uvs[c] if uvs else None, source))

    @staticmethod
    def _colour_source(state, has_uvs):
        """(texture lookup or None, flat colour): what colours the points of one geom."""
        material = state.getAttrib(MaterialAttrib)
        tint = tuple(material.getMaterial().getBaseColor())[:3] if material and material.getMaterial() else None
        texture = state.getAttrib(TextureAttrib)
        peeker = texture.getTexture().peek() if has_uvs and texture and texture.getTexture() else None
        return peeker, tint or (GREY if peeker is None else (1.0, 1.0, 1.0))

    def sample(self, count, rng):
        """count random points on the surface, each as (x, y, z, r, g, b). Points are
        spread by area, so a large triangle gets more of them than a small one."""
        colour = LColor()
        points = []
        for _ in range(count):
            a, b, c, uv_a, uv_b, uv_c, (peeker, tint) = self.triangles[
                bisect.bisect_left(self.cumulative, rng.random() * self.area)]
            r1, r2 = math.sqrt(rng.random()), rng.random()
            wa, wb, wc = 1 - r1, r1 * (1 - r2), r1 * r2   # uniform inside the triangle
            x, y, z = (wa * a[n] + wb * b[n] + wc * c[n] for n in range(3))
            red, green, blue = tint
            if peeker is not None:
                peeker.lookup(colour, wa * uv_a[0] + wb * uv_b[0] + wc * uv_c[0],
                              wa * uv_a[1] + wb * uv_b[1] + wc * uv_c[1])
                red, green, blue = colour[0] * red, colour[1] * green, colour[2] * blue
            points.append((x, y, z, red, green, blue))
        return points


def _area(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    return 0.5 * math.sqrt((uy * vz - uz * vy) ** 2 + (uz * vx - ux * vz) ** 2 + (ux * vy - uy * vx) ** 2)


def _points_node(name, points):
    data = GeomVertexData(name, GeomVertexFormat.getV3c4(), Geom.UHStatic)
    data.setNumRows(len(points))
    position, colour = GeomVertexWriter(data, "vertex"), GeomVertexWriter(data, "color")
    for x, y, z, r, g, b in points:
        position.addData3(x, y, z)
        colour.addData4(r, g, b, 1.0)
    primitive = GeomPoints(Geom.UHStatic)
    primitive.addNextVertices(len(points))
    primitive.closePrimitive()
    geom = Geom(data)
    geom.addPrimitive(primitive)
    node = GeomNode(name)
    node.addGeom(geom)
    return node


def build(model, parts, count, seed=1234):
    """Scatter about `count` points over the named GeomNodes of `model`.

    Returns (root, per_part, spacing, total): `root` holds one points node per part and
    sits where the model sits, `per_part` maps part name to its NodePath, `spacing` is the
    typical distance between neighbouring points, in model units, for sizing them, and
    `total` is how many points there are.
    """
    surfaces = [s for s in (Surface(part, model) for part in parts) if s.triangles]
    total_area = sum(s.area for s in surfaces)
    rng = random.Random(seed)  # fixed, so every run draws the same cloud

    root = NodePath("point_cloud")
    root.setMat(model.getMat())
    per_part = {}
    total = 0
    for surface in surfaces:
        n = max(1, round(count * surface.area / total_area))
        per_part[surface.name] = root.attachNewNode(_points_node(surface.name, surface.sample(n, rng)))
        total += n
    return root, per_part, math.sqrt(total_area / count), total
