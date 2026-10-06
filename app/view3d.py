"""The Kivy widget that shows the Panda3D picture and turns touches into
rotate / zoom / pan / tap-a-part."""
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.widget import Widget

from app.strings import number

START_VIEW = dict(yaw=-18.0, pitch=6.0, zoom=1.0, pan_x=0.0, pan_z=0.0)
ZOOM_RANGE = (0.22, 1.5)
PITCH_RANGE = (-30.0, 70.0)
TAP_SLOP = dp(12)     # a touch that moves less than this is a tap
TAP_TIME = 0.45       # ...if it also ends within this many seconds


def clamp(value, low, high):
    return max(low, min(high, value))


class Model3DView(Widget):
    has_frame = BooleanProperty(False)
    points = BooleanProperty(False)   # showing the point cloud instead of the solid model
    point_text = StringProperty("")   # how many points there are, while the cloud is on show

    __events__ = ("on_pick",)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_path = None
        self._view = dict(START_VIEW)
        self._touches = []
        self._moved = 0.0
        self._multi = False
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._layout, size=self._layout)
        self._send_size = Clock.create_trigger(self._push_size, 0.05)
        self._poll = None
        self._focus = {}
        self._glide = None
        self._point_count = 0

    @property
    def renderer(self):
        return App.get_running_app().renderer

    def on_pick(self, name):
        pass

    # ---- model and frames ------------------------------------------------

    def show_model(self, path, part_keys):
        self.model_path = path
        self.has_frame = False
        self.points = False  # the renderer opens every model solid, too
        self._point_count = 0
        self.refresh_text()
        self._view = dict(START_VIEW)
        self._focus = {}
        self._cancel_glide()
        self.renderer.load(path, part_keys, lambda focus, p=path: self._got_focus(p, focus))
        self._push_size()
        self._push_view()
        if self._poll is None:
            self._poll = Clock.schedule_interval(self._pull_frame, 0)

    def stop(self):
        self._cancel_glide()
        if self._poll is not None:
            self._poll.cancel()
            self._poll = None

    def reset_view(self):
        self._glide_to(dict(START_VIEW))

    def focus_on(self, key):
        """Turn and zoom the camera so the named part is in front of the viewer."""
        if key not in self._focus:
            return
        yaw, zoom, pan_z = self._focus[key]
        # aim a little below the part: the info card covers the bottom of the view
        self._glide_to(dict(yaw=yaw, pitch=6.0, zoom=zoom, pan_x=0.0,
                            pan_z=clamp(pan_z - 0.28 * zoom, -1.0, 1.0)))

    def _got_focus(self, path, focus):
        if path == self.model_path:
            self._focus = focus

    def toggle_points(self):
        """Switch between the solid model and its point cloud."""
        self.points = not self.points
        self._point_count = 0
        self.refresh_text()
        path = self.model_path
        self.renderer.set_points(self.points, lambda count, p=path: self._got_points(p, count))

    def _got_points(self, path, count):
        if path == self.model_path:
            self._point_count = count
            self.refresh_text()

    def refresh_text(self):
        """Write the point count in the language on screen."""
        if self.points and self._point_count:
            app = App.get_running_app()
            self.point_text = app.strings["points_count"].format(number(f"{self._point_count:,}", app.lang))
        else:
            self.point_text = ""

    def _glide_to(self, target, duration=0.35):
        self._cancel_glide()
        start = dict(self._view)
        # turn the short way round
        target["yaw"] = start["yaw"] + ((target["yaw"] - start["yaw"] + 180.0) % 360.0 - 180.0)
        elapsed = [0.0]

        def step(dt):
            elapsed[0] += dt
            t = min(elapsed[0] / duration, 1.0)
            ease = t * t * (3 - 2 * t)
            for name in start:
                self._view[name] = start[name] + (target[name] - start[name]) * ease
            self._push_view()
            if t >= 1.0:
                self._view["yaw"] %= 360.0
                self._glide = None
                return False

        self._glide = Clock.schedule_interval(step, 0)

    def _cancel_glide(self):
        if self._glide is not None:
            self._glide.cancel()
            self._glide = None

    def _layout(self, *_):
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._send_size()

    def _push_size(self, *_):
        if self.model_path and self.width > 1 and self.height > 1:
            self.renderer.set_size(self.width, self.height)

    def _push_view(self):
        v = self._view
        self.renderer.set_camera(v["yaw"], v["pitch"], v["zoom"], v["pan_x"], v["pan_z"])

    def _pull_frame(self, _dt):
        frame = self.renderer.take_frame()
        if frame is None:
            return
        width, height, data, path = frame
        if path != self.model_path:
            return  # left over from the previous figure
        texture = self._rect.texture
        if texture is None or texture.size != (width, height):
            texture = Texture.create(size=(width, height), colorfmt="rgba")
            self._rect.texture = texture
        texture.blit_buffer(data, colorfmt="rgba", bufferfmt="ubyte")
        self.canvas.ask_update()
        self.has_frame = True

    # ---- touch -----------------------------------------------------------

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return super().on_touch_down(touch)
        if touch.is_mouse_scrolling:
            factor = 0.9 if touch.button == "scrolldown" else 1 / 0.9
            self._view["zoom"] = clamp(self._view["zoom"] * factor, *ZOOM_RANGE)
            self._push_view()
            return True
        if touch.is_double_tap:
            self.reset_view()
            return True
        self._cancel_glide()
        touch.grab(self)
        self._touches.append(touch)
        if len(self._touches) == 1:
            self._moved = 0.0
            self._multi = False
        else:
            self._multi = True
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_move(touch)
        view = self._view
        self._moved += abs(touch.dx) + abs(touch.dy)
        panning = getattr(touch, "button", None) == "right"

        if len(self._touches) >= 2:
            a, b = self._touches[0], self._touches[1]
            other = b if touch is a else a
            before = ((touch.px - other.x) ** 2 + (touch.py - other.y) ** 2) ** 0.5
            after = ((touch.x - other.x) ** 2 + (touch.y - other.y) ** 2) ** 0.5
            if before > 1 and after > 1:
                view["zoom"] = clamp(view["zoom"] * before / after, *ZOOM_RANGE)
            # the midpoint of the two fingers moves by half of this finger's move
            self._pan(touch.dx / 2, touch.dy / 2)
        elif panning:
            self._pan(touch.dx, touch.dy)
        else:
            view["yaw"] = (view["yaw"] - touch.dx / self.width * 220.0) % 360.0
            view["pitch"] = clamp(view["pitch"] - touch.dy / self.height * 140.0, *PITCH_RANGE)
        self._push_view()
        return True

    def _pan(self, dx, dy):
        view = self._view
        view["pan_x"] = clamp(view["pan_x"] - dx / self.width * 4.0 * view["zoom"], -1.0, 1.0)
        view["pan_z"] = clamp(view["pan_z"] - dy / self.height * 2.2 * view["zoom"], -1.0, 1.0)

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super().on_touch_up(touch)
        touch.ungrab(self)
        if touch in self._touches:
            self._touches.remove(touch)
        is_tap = (not self._multi and self._moved < TAP_SLOP
                  and touch.time_end - touch.time_start < TAP_TIME
                  and getattr(touch, "button", "left") in ("left", None))
        if is_tap:
            nx = (touch.x - self.x) / self.width * 2 - 1
            ny = (touch.y - self.y) / self.height * 2 - 1
            self.renderer.pick(nx, ny, lambda name: self.dispatch("on_pick", name))
        return True
