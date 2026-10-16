from copy import deepcopy

import pygame
import pygame_gui

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat.personality import Personality
from scripts.cat.skills import Skill
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.ui_elements import UISurfaceImageButton
from scripts.screens.CatCustomizer import CatCustomizer
from scripts.screens.Screens import Screens
from scripts.ui.generate_button import ButtonStyles, get_button_dict
from scripts.utility import ui_scale


class CustomizeCatScreen(CatCustomizer, Screens):
    def screen_switches(self):
        super().screen_switches()
        creation = game.switches.get("create_cat")
        self.creating_cat = creation is not None
        self.the_cat = creation["cat"] if self.creating_cat else Cat.fetch_cat(game.switches["cat"])
        self.init_customizer()
        self.hide_menu_buttons()
        self.set_mute_button_position("topright")
        self.show_mute_buttons()
        self.set_bg("default", "mainmenu_bg")
        pelt = self.the_cat.pelt
        self.pname = pelt.name
        for draft, stage in (("kitten_sprite", "kitten"), ("adolescent_pose", "adolescent"),
                             ("adult_pose", "adult"), ("elder_pose", "senior")):
            setattr(self, draft, pelt.cat_sprites[stage])
        for field in ("length", "colour", "white_patches", "eye_colour", "eye_colour2", "tortiebase",
                      "tortiecolour", "pattern", "tortiepattern", "vitiligo", "points", "paralyzed", "opacity",
                      "scars", "tint", "skin", "white_patches_tint", "reverse", "accessories", "inventory",
                      "fur_texture", "build", "height"):
            value = deepcopy(getattr(pelt, field))
            if field in ("white_patches", "pattern") and not isinstance(value, list):
                value = [value] if value else []
            setattr(self, field, value)
        self.sex = self.the_cat.gender
        self.personality = self.the_cat.personality.trait
        self.skill = self.the_cat.skills.primary.skill if self.the_cat.skills.primary else "None"
        self.secondary_skill = self.the_cat.skills.secondary.skill if self.the_cat.skills.secondary else "None"
        self.faith = self.the_cat.lock_faith
        self.backstory = self.the_cat.backstory
        self.permanent_conditions = list(self.the_cat.permanent_condition)
        self.preview_age = {"newborn": "kitten", "young adult": "adult", "senior adult": "adult", "senior": "elder"}.get(self.the_cat.age, self.the_cat.age)
        self.tortie_enabled = pelt.name in ("Tortie", "Calico")
        self.trait_options = list(Personality.trait_ranges["kit_traits" if self.the_cat.personality.kit else "normal_traits"])
        self.initial_customizer_state = self.get_customizer_state()
        self.main_menu = UISurfaceImageButton(ui_scale(pygame.Rect((25, 50), (153, 30))), "Back",
            get_button_dict(ButtonStyles.SQUOVAL, (153, 30)), object_id="@buttonstyles_squoval", manager=MANAGER)
        self.open_customize_cat()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            self.handle_customize_cat_event(event)
            self.mute_button_pressed(event)

    def clear_all_page(self):
        for element in self.elements.values():
            element.kill()
        self.elements.clear()
        for buttons in self.customiser_button_dicts:
            for button in buttons.values():
                button.kill()
            buttons.clear()

    def build_customizer_footer(self):
        super().build_customizer_footer()
        self.elements["previous_step"].set_text("Cancel")
        self.elements["next_step"].set_text("Create" if self.creating_cat else "Apply")

    def previous_customizer_step(self):
        self.exit_customizer()

    def exit_customizer(self):
        if self.creating_cat:
            creation = game.switches.pop("create_cat")
            game.switches["cat"] = creation["previous_cat"]
            self.change_screen(creation["return_screen"])
        else:
            self.change_screen("profile screen")

    def finish_customize_cat(self):
        before = self.initial_customizer_state
        state = self.get_customizer_state()
        pelt = self.the_cat.pelt
        for draft, field in (("pname", "name"),):
            if state[draft] != before[draft]:
                setattr(pelt, field, deepcopy(state[draft]))
        for field in ("length", "colour", "white_patches", "eye_colour", "eye_colour2", "tortiebase",
                      "tortiecolour", "pattern", "tortiepattern", "vitiligo", "points", "paralyzed", "opacity",
                      "scars", "tint", "skin", "white_patches_tint", "reverse", "accessories", "inventory",
                      "fur_texture", "build", "height"):
            if state[field] != before[field]:
                setattr(pelt, field, deepcopy(state[field]))
        for draft, stage in (("kitten_sprite", "kitten"), ("adolescent_pose", "adolescent"),
                             ("adult_pose", "adult"), ("elder_pose", "senior")):
            if state[draft] != before[draft]:
                pelt.cat_sprites[stage] = state[draft]
                if stage == "adult":
                    pelt.cat_sprites["young adult"] = pelt.cat_sprites["senior adult"] = state[draft]
        if self.facet_reset:
            self.the_cat.personality = Personality(trait=self.personality, kit_trait=self.the_cat.personality.kit)
        elif self.personality != before["personality"]:
            self.the_cat.personality.trait = self.personality
        if self.healed:
            self.the_cat.illnesses.clear()
            if "pregnant" not in self.the_cat.injuries:
                self.the_cat.injuries.clear()
        for draft, slot in (("skill", "primary"), ("secondary_skill", "secondary")):
            if state[draft] != before[draft]:
                value = state[draft]
                if value == "Random":
                    from random import choice
                    value = choice(self.skills[1:])
                current = getattr(self.the_cat.skills, slot) or self.the_cat.skills.primary
                replacement = None if value == "None" else Skill.get_skill_from_string(Skill, value)
                if replacement:
                    replacement.points = current.points if current else 0
                    replacement.interest_only = current.interest_only if current else self.the_cat.age in ("newborn", "kitten")
                setattr(self.the_cat.skills, slot, replacement)
        if self.sex != before["sex"]:
            if self.the_cat.genderalign == self.the_cat.gender:
                self.the_cat.genderalign = self.sex
            self.the_cat.gender = self.sex
        if self.faith != before["faith"]:
            self.the_cat.lock_faith = self.faith
        if self.backstory != before["backstory"]:
            self.the_cat.backstory = self.backstory
        if self.permanent_conditions != before["permanent_conditions"]:
            for name in before["permanent_conditions"]:
                if name not in self.permanent_conditions:
                    self.the_cat.permanent_condition.pop(name, None)
            for name in self.permanent_conditions:
                if name not in self.the_cat.permanent_condition:
                    self.the_cat.get_permanent_condition(name, cause="Changed in the character customizer.")
            pelt.paralyzed = "paralyzed" in self.the_cat.permanent_condition
        if self.creating_cat:
            Cat.all_cats[self.the_cat.ID] = self.the_cat
            Cat.insert_cat(self.the_cat)
            game.clan.add_cat(self.the_cat)
            History.add_beginning(self.the_cat)
            for name, condition in self.the_cat.permanent_condition.items():
                if not condition["born_with"] or condition["moons_until"] == -2:
                    History.add_condition(self.the_cat, name, "permanent", "Present when created in the character customizer.")
            self.the_cat.create_relationships_new_cat()
            self.the_cat.create_inheritance_new_cat()
            self.the_cat.update_mentor()
            game.switches.pop("create_cat")
            game.switches["cat"] = self.the_cat.ID
            self.creating_cat = False
        self.exit_customizer()

    def display_change_save(self):
        data = super().display_change_save()
        data["customizer"] = self.get_customizer_state()
        for field in ("initial_customizer_state", "customizer_undo", "customizer_redo",
                      "page", "current_selection", "search_text", "customiser_sort"):
            data[field] = deepcopy(getattr(self, field))
        return data

    def display_change_load(self, data):
        data = deepcopy(data)
        super().display_change_load(data)
        for field, value in data.pop("customizer").items():
            setattr(self, field, value)
        for field, value in data.items():
            setattr(self, field, value)
        self.open_customize_cat()

    def exit_screen(self):
        self.clear_all_page()
        self.main_menu.kill()
        self.set_mute_button_position("bottomright")
