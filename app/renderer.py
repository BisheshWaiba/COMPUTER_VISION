"""Panda3D running off-screen on its own thread.

Kivy owns the window and the main thread. Panda3D keeps its own OpenGL context
on this thread, draws the model into a buffer, and hands the finished picture
back as raw RGBA bytes for Kivy to show. Everything that touches Panda3D
happens here; the rest of the app only posts commands to the queue.

Frames are drawn on demand (when the camera, size or selection changes), not
continuously, so an idle viewer costs nothing.
"""
import math
import queue
import threading

from kivy.clock import Clock

FOV_V = 28.0            # vertical field of view, degrees
FIT_MARGIN = 1.20       # empty space left around the model when zoom is 1
MAX_RENDER_SIDE = 1280  # longest side of the off-screen buffer, pixels
HIGHLIGHT = (1.0, 0.72, 0.15)

# (ambient, key, fill) light colours. Flat-coloured models need shading to show their shape.
# Photo-textured models already carry the light and shadow of the photo, so they get mostly
# even light; shading them again makes them far too dark.
LIGHTS_FLAT = ((0.36, 0.36, 0.38), (0.58, 0.57, 0.54), (0.14, 0.15, 0.18))
LIGHTS_PHOTO = ((0.72, 0.72, 0.72), (0.32, 0.32, 0.31), (0.06, 0.06, 0.07))
DIM = 0.55


class Renderer(threading.Thread):
    def __init__(self, background=(0.953, 0.941, 0.914)):
        super().__init__(daemon=True, name="panda3d")
        self.background = background
        self._commands = queue.Queue()
        self._frame = None
        self._frame_lock = threading.Lock()
        self.error = None

    # ---- called from the Kivy thread -------------------------------------

    def load(self, path, part_keys, on_ready=None):
        """Show a model. on_ready(focus) runs on the Kivy thread with, for each part,
        the camera view that looks straight at it: {key: (yaw, zoom, pan_z)}."""
        self._commands.put(("load", path, tuple(part_keys), on_ready))

    def set_size(self, width, height):
        self._commands.put(("size", int(width), int(height)))

    def set_camera(self, yaw, pitch, zoom, pan_x, pan_z):
        self._commands.put(("camera", yaw, pitch, zoom, pan_x, pan_z))

    def select(self, key):
        self._commands.put(("select", key))

    def pick(self, nx, ny, callback):
        """Find the part under a point. nx, ny run from -1 to 1 across the view
        (bottom-left to top-right). callback(name or None) runs on the Kivy thread."""
        self._commands.put(("pick", nx, ny, callback))

    def stop(self):
        self._commands.put(("stop",))

    def take_frame(self):
        """Newest finished frame as (width, height, rgba_bytes, model_path), or None."""
        with self._frame_lock:
            frame, self._frame = self._frame, None
        return frame

    # ---- Panda3D thread --------------------------------------------------

    def run(self):
        try:
            self._setup()
            self._loop()
        except Exception as exc:  # surfaced by the viewer screen
            self.error = exc
            raise

    def _setup(self):
        from panda3d.core import loadPrcFileData
        loadPrcFileData("", "window-type offscreen\n"
                            "audio-library-name null\n"
                            "win-size 16 16\n"
                            "sync-video 0\n"
                            "framebuffer-multisample 1\n"
                            "multisamples 4\n")
        from direct.showbase.ShowBase import ShowBase
        from panda3d.core import (AmbientLight, AntialiasAttrib, CollisionHandlerQueue, CollisionNode,
                                  CollisionRay, CollisionTraverser, DirectionalLight, GeomNode, NodePath)

        self.base = ShowBase()
        self.scene = NodePath("scene")
        self.scene.setShaderAuto()
        self.scene.setAntialias(AntialiasAttrib.MMultisample)

        self.camera = None
        self.buffer = None
        self.texture = None
        self.size = (0, 0)
        self.model = None
        self.models = {}
        self.model_path = None
        self.parts = {}
        self.named = {}
        self.center = (0.0, 0.0, 0.0)
        self.extent = (1.0, 1.0)  # half-width, half-height of the model
        self.view = (0.0, 0.0, 1.0, 0.0, 0.0)

        ambient = AmbientLight("ambient")
        self.scene.setLight(self.scene.attachNewNode(ambient))

        # lights ride with the camera so the side facing the viewer is always lit
        self.rig = self.scene.attachNewNode("rig")
        key = DirectionalLight("key")
        key_np = self.rig.attachNewNode(key)
        key_np.setHpr(-30, -35, 0)
        self.scene.setLight(key_np)
        fill = DirectionalLight("fill")
        fill_np = self.rig.attachNewNode(fill)
        fill_np.setHpr(50, -10, 0)
        self.scene.setLight(fill_np)

        self.lights = (ambient, key, fill)
        for light, colour in zip(self.lights, LIGHTS_FLAT):
            light.setColor((*colour, 1))

        self.picker_ray = CollisionRay()
        picker = CollisionNode("picker")
        picker.addSolid(self.picker_ray)
        picker.setFromCollideMask(GeomNode.getDefaultCollideMask())
        picker.setIntoCollideMask(0)
        self.picker = picker
        self.picker_np = None
        self.pick_queue = CollisionHandlerQueue()
        self.traverser = CollisionTraverser("picker")

    def _loop(self):
        while True:
            commands = [self._commands.get()]
            while True:  # take everything waiting so a fast drag draws once
                try:
                    commands.append(self._commands.get_nowait())
                except queue.Empty:
                    break
            for command in commands:
                name, args = command[0], command[1:]
                if name == "stop":
                    return
                getattr(self, "_do_" + name)(*args)
            self._draw()

    def _do_size(self, width, height):
        from panda3d.core import FrameBufferProperties, GraphicsOutput, Texture

        longest = max(width, height, 1)
        if longest > MAX_RENDER_SIDE:
            width, height = width * MAX_RENDER_SIDE // longest, height * MAX_RENDER_SIDE // longest
        width, height = max(width, 16), max(height, 16)
        if (width, height) == self.size:
            return
        if self.buffer is not None:
            self.base.graphicsEngine.removeWindow(self.buffer)

        props = FrameBufferProperties()
        props.setRgbaBits(8, 8, 8, 8)
        props.setDepthBits(24)
        props.setMultisamples(4)
        self.texture = Texture("view")
        self.buffer = self.base.win.makeTextureBuffer("view", width, height, self.texture, True, props)
        if self.buffer is None:  # no multisampling on this device
            self.buffer = self.base.win.makeTextureBuffer("view", width, height, self.texture, True)
        self.buffer.setClearColor((*self.background, 1))
        self.buffer.setSort(-10)

        if self.camera is not None:
            self.camera.removeNode()
        self.camera = self.base.makeCamera(self.buffer, scene=self.scene, lens=None)
        self.camera.reparentTo(self.scene)
        self.rig.reparentTo(self.camera)
        self.picker_np = self.camera.attachNewNode(self.picker)
        self.traverser.clearColliders()
        self.traverser.addCollider(self.picker_np, self.pick_queue)
        self.size = (width, height)
        self._apply_view()

    def _do_load(self, path, part_keys, on_ready):
        from panda3d.core import Filename, Texture

        if self.model is not None:
            self.model.detachNode()
        if path not in self.models:
            model = self.base.loader.loadModel(Filename.fromOsSpecific(path))
            # glTF colours are linear; this pipeline lights and shows them as-is, so
            # convert once to display (sRGB) values or everything comes out too dark
            for material in model.findAllMaterials():
                r, g, b, a = material.getBaseColor()
                material.setBaseColor((r ** (1 / 2.2), g ** (1 / 2.2), b ** (1 / 2.2), a))
            # photo textures: for the same reason, show their colours as stored (an sRGB
            # texture would be darkened on the way in and never brightened again), and
            # keep one copy of each picture, not one per part
            shared = {}
            for texture in model.findAllTextures():
                if texture.getFormat() == Texture.F_srgb:
                    texture.setFormat(Texture.F_rgb)
                elif texture.getFormat() == Texture.F_srgb_alpha:
                    texture.setFormat(Texture.F_rgba)
                first = shared.setdefault(texture.getName(), texture)
                if first is not texture:
                    model.replaceTexture(texture, first)
            self.models[path] = model
        self.model = self.models[path]
        self.model_path = path
        textured = self.model.findAllTextures().getNumTextures() > 0
        for light, colour in zip(self.lights, LIGHTS_PHOTO if textured else LIGHTS_FLAT):
            light.setColor((*colour, 1))
        self.model.reparentTo(self.scene)

        self.parts = {}
        for key in part_keys:
            node = self.model.find(f"**/{key}")
            if not node.isEmpty():
                self.parts[key] = node
        self.named = {child.getName(): child for child in self.model.findAllMatches("**/+GeomNode")}
        self._do_select(None)

        low, high = self.model.getTightBounds()
        self.center = ((low.x + high.x) / 2, (low.y + high.y) / 2, (low.z + high.z) / 2)
        self.extent = (max(high.x - low.x, high.y - low.y) / 2, (high.z - low.z) / 2)
        if on_ready is not None:
            focus = self._focus_views()
            Clock.schedule_once(lambda dt: on_ready(focus), 0)

    def _focus_views(self):
        """For each part, the view that faces it: which side it is on, how high, how big."""
        cx, cy, cz = self.center
        half_w, half_h = self.extent
        views = {}
        for key, node in self.parts.items():
            low, high = node.getTightBounds(self.model)
            dx, dy = (low.x + high.x) / 2 - cx, (low.y + high.y) / 2 - cy
            off_centre = math.hypot(dx, dy) > 0.15 * half_w
            yaw = math.degrees(math.atan2(dx, -dy)) if off_centre else 0.0
            size = max((high.z - low.z) / (2 * half_h),
                       max(high.x - low.x, high.y - low.y) / (2 * half_w) * 0.5)
            zoom = min(max(size * 1.9, 0.38), 1.0)
            pan_z = ((low.z + high.z) / 2 - cz) / half_h
            views[key] = (yaw, zoom, pan_z)
        return views

    def _do_camera(self, yaw, pitch, zoom, pan_x, pan_z):
        self.view = (yaw, pitch, zoom, pan_x, pan_z)
        self._apply_view()

    def _apply_view(self):
        if self.camera is None:
            return
        width, height = self.size
        aspect = width / height
        tan_v = math.tan(math.radians(FOV_V) / 2)
        lens = self.camera.node().getLens()
        lens.setFov(math.degrees(2 * math.atan(tan_v * aspect)), FOV_V)

        yaw, pitch, zoom, pan_x, pan_z = self.view
        half_w, half_h = self.extent
        fit = max(half_h / tan_v, half_w / (tan_v * aspect)) * FIT_MARGIN
        distance = fit * zoom
        lens.setNearFar(max(distance - 4 * max(half_w, half_h), 0.05), distance + 4 * max(half_w, half_h))

        yaw_r, pitch_r = math.radians(yaw), math.radians(pitch)
        cx, cy, cz = self.center
        # pan moves the look-at point sideways (relative to the camera) and up/down
        tx = cx + pan_x * half_w * math.cos(yaw_r)
        ty = cy + pan_x * half_w * math.sin(yaw_r)
        tz = cz + pan_z * half_h
        self.camera.setPos(tx + distance * math.sin(yaw_r) * math.cos(pitch_r),
                           ty - distance * math.cos(yaw_r) * math.cos(pitch_r),
                           tz + distance * math.sin(pitch_r))
        self.camera.lookAt(tx, ty, tz)

    def _do_select(self, key):
        from panda3d.core import Material

        for name, node in self.named.items():
            holder = self.parts.get(name, node)
            holder.clearMaterial()
            holder.clearColorScale()
        if key not in self.parts:
            return
        for name, node in self.named.items():
            if name != key:
                self.parts.get(name, node).setColorScale(DIM, DIM, DIM, 1)
        chosen = self.parts[key]
        materials = chosen.findAllMaterials()
        base = materials[0].getBaseColor() if materials else (0.5, 0.5, 0.5, 1)
        glow = Material("highlight")
        glow.setBaseColor((0.45 * base[0] + 0.55 * HIGHLIGHT[0], 0.45 * base[1] + 0.55 * HIGHLIGHT[1],
                           0.45 * base[2] + 0.55 * HIGHLIGHT[2], 1))
        glow.setEmission((0.22, 0.15, 0.02, 1))
        glow.setRoughness(0.6)
        chosen.setMaterial(glow, 1)

    def _do_pick(self, nx, ny, callback):
        name = None
        if self.model is not None and self.camera is not None:
            self.picker_ray.setFromLens(self.camera.node(), nx, ny)
            self.traverser.traverse(self.model)
            if self.pick_queue.getNumEntries():
                self.pick_queue.sortEntries()
                name = self.pick_queue.getEntry(0).getIntoNodePath().getName()
        Clock.schedule_once(lambda dt: callback(name), 0)

    def _draw(self):
        if self.buffer is None or self.model is None:
            return
        self.base.graphicsEngine.renderFrame()
        data = self.texture.getRamImageAs("RGBA")
        if not data:
            return
        frame = (self.texture.getXSize(), self.texture.getYSize(), bytes(data), self.model_path)
        with self._frame_lock:
            self._frame = frame
