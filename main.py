"""Figures of Nepal: a gallery of 3D historical figures you can rotate and tap.

Run with:  .venv/Scripts/python.exe main.py
"""
from pathlib import Path

from kivy.config import Config
from kivy.utils import platform

if platform not in ("android", "ios"):
    # phone-shaped window for working on a computer; right-drag pans instead of faking a second finger
    Config.set("graphics", "width", "420")
    Config.set("graphics", "height", "800")
    Config.set("input", "mouse", "mouse,multitouch_on_demand")

from kivy.app import App  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.lang import Builder  # noqa: E402
from kivy.uix.screenmanager import ScreenManager, SlideTransition  # noqa: E402

from app.content import load_figures  # noqa: E402
from app.renderer import Renderer  # noqa: E402
from app.screens import GalleryScreen, ViewerScreen  # noqa: E402

ROOT = Path(__file__).resolve().parent
BACK_KEY = 27  # Android back button, Escape on a computer


class FiguresApp(App):
    title = "Figures of Nepal"

    def build(self):
        Builder.load_file(str(ROOT / "app" / "ui.kv"))
        self.renderer = Renderer()
        self.renderer.start()

        self.screens = ScreenManager(transition=SlideTransition(duration=0.22))
        self.gallery = GalleryScreen(name="gallery")
        self.viewer = ViewerScreen(name="viewer")
        self.screens.add_widget(self.gallery)
        self.screens.add_widget(self.viewer)
        self.gallery.populate(load_figures(ROOT / "assets"))

        Window.bind(on_keyboard=self._on_key)
        return self.screens

    def show_figure(self, figure):
        self.viewer.show(figure)
        self.screens.transition.direction = "left"
        self.screens.current = "viewer"

    def show_gallery(self):
        self.screens.transition.direction = "right"
        self.screens.current = "gallery"

    def _on_key(self, _window, key, *_):
        if key == BACK_KEY and self.screens.current == "viewer":
            self.show_gallery()
            return True  # handled: do not close the app
        return False

    def on_stop(self):
        self.renderer.stop()


if __name__ == "__main__":
    FiguresApp().run()
