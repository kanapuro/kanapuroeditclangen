import pygame
import pygame_gui
import ujson

from scripts.cat.pelts import Pelt
from scripts.cat.sprites import sprites
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.ui_elements import UIImageButton, UISurfaceImageButton
from scripts.ui.generate_button import ButtonStyles, get_button_dict
from scripts.utility import get_text_box_theme, ui_scale, ui_scale_dimensions


def update_checkbox(button, object_id):
    if button.object_ids[-1] != object_id:
        button.change_object_id(object_id)


class CustomizerList(pygame_gui.elements.UIScrollingContainer):
    def __init__(self, rect, options, labels, buttons):
        super().__init__(ui_scale(rect), allow_scroll_x=False, manager=MANAGER)
        self.logical_width = rect.width
        self.options = options
        self.labels = labels
        self.buttons = buttons
        self.rows = {}
        self.on_change = None
        self.row_height = ui_scale_dimensions((40, 40))[1]
        self.set_scrollable_area_dimensions((self.rect.width - 20, max(self.rect.height, len(options) * self.row_height)))
        self.refresh_rows()

    def refresh_rows(self):
        first = max(0, -self.get_container().get_relative_rect().y // self.row_height - 1)
        visible = self.options[first:first + self.rect.height // self.row_height + 3]
        if set(self.rows) == set(visible):
            return
        for value in list(self.rows):
            if value not in visible:
                for widget in self.rows.pop(value):
                    widget.kill()
                self.buttons.pop(value)
        for index, value in enumerate(visible, start=first):
            if value in self.rows:
                continue
            label = self.labels(value)
            button = UIImageButton(ui_scale(pygame.Rect((0, index * 40 + 4), (34, 34))), "",
                object_id="@unchecked_checkbox", container=self, manager=MANAGER, tool_tip_text=label)
            text = pygame_gui.elements.UITextBox(label if len(label) < 16 else label[:13] + "...",
                ui_scale(pygame.Rect((32, index * 40), (self.logical_width - 50, 34))),
                object_id=get_text_box_theme("#text_box_30_horizleft"), container=self, manager=MANAGER)
            self.rows[value] = (button, text)
            self.buttons[value] = button
        if self.on_change:
            self.on_change()

    def update(self, time_delta):
        super().update(time_delta)
        self.refresh_rows()

    def scroll_to(self, value):
        index = self.options.index(value)
        if self.vert_scroll_bar:
            self.vert_scroll_bar.set_scroll_from_start_percentage(index / len(self.options))
        self.update(0)



class CatAppearanceEditor:
    categories = {
        1: ["pelt_pattern", "pelt_colour", "white_patches", "points", "vitiligo",
            "tortie_pattern", "tortie_colour", "tortie_patches"],
        2: ["eye_colour", "heterochromia", "skin", "scar", "accessory"],
    }
    attributes = {
        "pelt_pattern": "name", "pelt_colour": "colour", "tortie_pattern": "tortiepattern",
        "tortie_colour": "tortiecolour", "tortie_patches": "pattern",
        "heterochromia": "eye_colour2", "scar": "scars", "accessory": "accessories",
    }
    multiple = {"white_patches", "tortie_patches", "accessory"}
    with open("resources/dicts/acc_display.json", encoding="utf-8") as read_file:
        accessory_names = ujson.load(read_file)

    def __init__(self, page, selection, pelt, search="", alphabetical=False, creation=False, button_dicts=None, tint_buttons=None):
        self.creation = creation
        self.multiple = self.multiple if creation else self.multiple | {"scar"}
        self.selection = selection if selection in self.categories[page] else self.categories[page][0]
        if self.selection.startswith("tortie_") and pelt.name not in ("Tortie", "Calico"):
            self.selection = "pelt_pattern"
        self.elements = {}
        self.category_buttons = {}
        self.option_buttons = button_dicts[self.selection] if button_dicts is not None else {}
        self.tint_buttons = tint_buttons if tint_buttons is not None else {}
        self.pelt = pelt
        self.options = self.get_options(self.selection)
        for index, category in enumerate(self.categories[page]):
            y = 100 + index * 50 + (75 if page == 1 and index >= 5 else 0)
            self.category_buttons[category] = UISurfaceImageButton(
                ui_scale(pygame.Rect((120, y), (120, 40))), category.replace("_", " "),
                get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 40)),
                object_id="@buttonstyles_rounded_rect", manager=MANAGER)
            if category == self.selection or (category.startswith("tortie_") and pelt.name not in ("Tortie", "Calico")):
                self.category_buttons[category].disable()
        if page == 1:
            self.elements["tortie_text"] = pygame_gui.elements.UITextBox(
                "Tortie", ui_scale(pygame.Rect((120, 365), (65, 34))),
                object_id=get_text_box_theme("#text_box_30_horizleft"), manager=MANAGER)
            self.elements["tortie_checkbox"] = UIImageButton(
                ui_scale(pygame.Rect((180, 367), (30, 30))), "",
                object_id="@checked_checkbox" if pelt.name in ("Tortie", "Calico") else "@unchecked_checkbox", manager=MANAGER)
        for key, x, text in (("default", 560, "Default"), ("alphabetical", 635, "ABC")):
            self.elements[key] = UISurfaceImageButton(
                ui_scale(pygame.Rect((x, 38), (75, 34))), text,
                get_button_dict(ButtonStyles.SQUOVAL, (75, 34)), object_id="@buttonstyles_squoval", manager=MANAGER)
        self.elements["alphabetical" if alphabetical else "default"].disable()
        self.elements["search_background"] = pygame_gui.elements.UIImage(
            ui_scale(pygame.Rect((590, 575), (100, 34))),
            pygame.image.load("resources/images/search_bar.png").convert_alpha(), manager=MANAGER)
        self.elements["search_bar"] = pygame_gui.elements.UITextEntryLine(
            ui_scale(pygame.Rect((598, 577), (84, 27))), initial_text=search,
            object_id="#search_entry_box", manager=MANAGER)
        for key, x, text in (("clear", 550, "X"), ("search_button", 695, "Go")):
            self.elements[key] = UISurfaceImageButton(
                ui_scale(pygame.Rect((x, 575), (34, 34))), text,
                get_button_dict(ButtonStyles.ICON, (34, 34)), object_id="@buttonstyles_icon", manager=MANAGER)
        options = self.options
        if alphabetical:
            options = sorted(options, key=lambda value: self.display_name(value).lower())
        options = [value for value in options if value == "None" or search.lower() in self.display_name(value).lower()
                   or search.lower() in value.lower()]
        self.option_list = CustomizerList(pygame.Rect((550, 85), (175, 480)), options, self.display_name, self.option_buttons)
        self.elements["scroll_container"] = self.option_list
        if self.selection in ("pelt_colour", "white_patches", "points"):
            tints = sprites.cat_tints["tint_colours"] if self.selection == "pelt_colour" else sprites.white_patches_tints["tint_colours"]
            values = list(tints)
            if self.selection == "pelt_colour":
                values += list(sprites.cat_tints["dilute_tint_colours"])
            self.elements["tint_label"] = pygame_gui.elements.UITextBox(
                "Tint", ui_scale(pygame.Rect((275, 435), (60, 34))),
                object_id=get_text_box_theme("#text_box_30_horizleft"), manager=MANAGER)
            tint_list = CustomizerList(pygame.Rect((268, 470), (260, 130)),
                                      list(dict.fromkeys(["none"] + values)), str.capitalize, self.tint_buttons)
            self.elements["tint_list"] = tint_list
            tint_list.on_change = lambda: self.refresh(self.pelt)
        if self.selection in ("pelt_pattern", "tortie_pattern"):
            key = "match_tortie" if self.selection == "pelt_pattern" else "match_base"
            self.elements[key] = UISurfaceImageButton(
                ui_scale(pygame.Rect((340, 465), (123, 34))), key.replace("_", " "),
                get_button_dict(ButtonStyles.SQUOVAL, (123, 34)), object_id="@buttonstyles_squoval", manager=MANAGER)
            if pelt.name not in ("Tortie", "Calico"):
                self.elements[key].disable()
        self.option_list.on_change = lambda: self.refresh(self.pelt)
        self.refresh(pelt)

    def get_options(self, selection):
        pelts = [name for name in Pelt.sprites_names if name not in ("Tortie", "Calico") and (not self.creation or name != "TwoColour")]
        options = {
            "pelt_pattern": pelts, "pelt_colour": Pelt.pelt_colours,
            "white_patches": ["None"] + Pelt.little_white + Pelt.mid_white + Pelt.high_white + Pelt.mostly_white + ["FULLWHITE"],
            "points": ["None"] + Pelt.point_markings, "vitiligo": ["None"] + Pelt.vit,
            "tortie_pattern": pelts, "tortie_colour": Pelt.pelt_colours, "tortie_patches": ["None"] + Pelt.tortiepatterns,
            "eye_colour": Pelt.eye_colours, "heterochromia": ["None"] + Pelt.eye_colours,
            "skin": Pelt.skin_sprites, "scar": ["None"] + Pelt.scars1 + Pelt.scars2 + Pelt.scars3,
            "accessory": ["None"] + Pelt.plant_accessories + Pelt.wild_accessories + Pelt.collars +
            Pelt.flower_accessories + Pelt.plant2_accessories + Pelt.snake_accessories +
            Pelt.smallAnimal_accessories + Pelt.deadInsect_accessories + Pelt.aliveInsect_accessories +
            Pelt.fruit_accessories + Pelt.crafted_accessories + Pelt.tail2_accessories,
        }[selection]
        current = getattr(self.pelt, self.attributes.get(selection, selection))
        if isinstance(current, list):
            options = options + [value for value in current if value not in options]
        return list(dict.fromkeys(options))

    def display_name(self, value):
        if self.selection == "accessory":
            return str(self.accessory_names.get(value, {}).get("default", value)).capitalize()
        return value.capitalize()

    def refresh(self, pelt):
        self.pelt = pelt
        selected = getattr(pelt, self.attributes.get(self.selection, self.selection))
        if self.selection == "pelt_pattern" and pelt.name in ("Tortie", "Calico"):
            selected = "SingleColour" if pelt.tortiebase == "single" else pelt.tortiebase.capitalize()
        if self.selection == "tortie_pattern":
            selected = "SingleColour" if selected == "single" else str(selected).capitalize()
        for value, button in self.option_buttons.items():
            checked = value in selected if isinstance(selected, list) else value == selected
            checked = checked or (value == "None" and not selected)
            update_checkbox(button, "@checked_checkbox" if checked else "@unchecked_checkbox")
            button.enable()
            if checked and (self.selection not in self.multiple or value == "None"):
                button.disable()
        tint = pelt.tint if self.selection == "pelt_colour" else pelt.white_patches_tint
        for value, button in self.tint_buttons.items():
            update_checkbox(button, "@checked_checkbox" if tint == value else "@unchecked_checkbox")
            button.enable()
            if tint == value or (self.selection != "pelt_colour" and not pelt.white_patches and not pelt.points):
                button.disable()

    def kill(self):
        for widgets in (self.elements, self.category_buttons, self.option_buttons, self.tint_buttons):
            for widget in widgets.values():
                widget.kill()
