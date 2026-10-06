"""The two screens: the gallery of figures and the 3D viewer."""
from kivy.app import App
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from app.strings import number
from app.view3d import Model3DView  # noqa: F401  (used from ui.kv)


class FigureCard(ButtonBehavior, BoxLayout):
    title = StringProperty("")
    description = StringProperty("")
    thumbnail = StringProperty("")
    parts_text = StringProperty("")


class BackButton(ButtonBehavior, Widget):
    pass


class LangButton(ButtonBehavior, Label):
    """Switches the app to the other language; it is labelled with that language's name."""


class Chip(ButtonBehavior, Label):
    key = StringProperty("")
    selected = BooleanProperty(False)


class InfoCard(BoxLayout):
    title = StringProperty("")
    info = StringProperty("")
    shown = BooleanProperty(False)

    __events__ = ("on_close",)

    def on_close(self):
        pass

    def on_touch_down(self, touch):
        if not self.shown:
            return False
        if self.collide_point(*touch.pos):
            super().on_touch_down(touch)
            return True  # a tap on the card must not reach the model behind it
        return False


class GalleryScreen(Screen):
    def populate(self, figures):
        app = App.get_running_app()
        lang = app.lang
        box = self.ids.cards
        box.clear_widgets()
        for figure in figures:
            card = FigureCard(title=figure.title[lang], description=figure.description[lang],
                              thumbnail=figure.thumbnail,
                              parts_text=app.strings["parts_count"].format(number(len(figure.parts), lang)))
            card.bind(on_release=lambda _card, f=figure: App.get_running_app().show_figure(f))
            box.add_widget(card)


class ViewerScreen(Screen):
    title = StringProperty("")
    selected = StringProperty("")
    figure = ObjectProperty(None, allownone=True)

    def show(self, figure):
        lang = App.get_running_app().lang
        self.figure = figure
        self.title = figure.title[lang]
        self._set_selected("")

        chips = self.ids.chips
        chips.clear_widgets()
        for part in figure.parts.values():
            chip = Chip(text=part.label[lang], key=part.key)
            chip.bind(on_release=self._chip_pressed)
            chips.add_widget(chip)
        self.ids.chip_scroll.scroll_x = 0

        # loading a model clears any highlight in the renderer
        self.ids.view.show_model(figure.model, figure.parts.keys())

    def refresh_language(self):
        """Redo every piece of text after the language changed; the model and selection stay."""
        if self.figure is None:
            return
        lang = App.get_running_app().lang
        self.title = self.figure.title[lang]
        for chip in self.ids.chips.children:
            chip.text = self.figure.parts[chip.key].label[lang]
        self.ids.view.refresh_text()
        self._set_selected(self.selected)

    def _chip_pressed(self, chip):
        if chip.selected:
            self.select("")
        else:
            self.select(chip.key)
            self.ids.view.focus_on(chip.key)  # the part may be on the far side

    def on_leave(self, *_):
        # a quick back-then-open can finish this transition after the next figure
        # is already showing; only stop when the viewer really is off screen
        if self.manager is None or self.manager.current != self.name:
            self.ids.view.stop()

    def on_pick(self, name):
        """A tap on the model: name is the node that was hit, or None for empty space."""
        self.select(name if self.figure and name in self.figure.parts else "")

    def select(self, key):
        self._set_selected(key)
        App.get_running_app().renderer.select(key or None)

    def _set_selected(self, key):
        self.selected = key
        card = self.ids.card
        if key:
            lang = App.get_running_app().lang
            part = self.figure.parts[key]
            card.title, card.info = part.label[lang], part.info[lang]
        card.shown = bool(key)
        for chip in self.ids.chips.children:
            chip.selected = chip.key == key
            if chip.selected:
                self.ids.chip_scroll.scroll_to(chip, padding=24)
