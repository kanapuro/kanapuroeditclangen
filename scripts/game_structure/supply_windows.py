# Supplies layouts adapted from LifeGen bab3814eee64852125c004dac588fab809a730e9 (MPL-2.0).
import pygame
import pygame_gui

from scripts.cat.cats import Cat
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.ui_elements import GameWindow, UIImageButton, UISurfaceImageButton, UITextBoxTweaked, UICatListDisplay
from scripts.ui.generate_button import ButtonStyles, get_button_dict
from scripts.ui.icon import Icon
from scripts.utility import ui_scale, ui_scale_dimensions


class HerbManagementWindow(GameWindow):
    def __init__(self, screen):
        super().__init__((125, 150, 550, 400))
        self.screen = screen
        self.help_button = UIImageButton(
            ui_scale(pygame.Rect((18, 18), (34, 34))), "", object_id="#help_button",
            container=self, manager=MANAGER,
            tool_tip_text="Medicine cats gather herbs each timeskip and treat their patients. Gathered and used herbs are reported in this log. Visit the medicine cat den to inspect the stores and sick or injured cats.",
        )
        log = [f"<b>Herbs in store:</b> {sum(game.clan.herbs.values()):g}"]
        log.extend(game.herb_events_list or ["Nothing to report."])
        self.log = UITextBoxTweaked(
            "<br>-------------------------------<br>".join(log),
            ui_scale(pygame.Rect((25, 77), (500, 250))), container=self, manager=MANAGER,
            object_id="#text_box_26_horizleft_verttop_pad_14_0_10",
        )
        self.med_den_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((199, 347), (151, 28))), "Medicine cat den",
            get_button_dict(ButtonStyles.ROUNDED_RECT, (151, 28)),
            object_id="@buttonstyles_rounded_rect", container=self, manager=MANAGER,
        )

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED and event.ui_element == self.med_den_button:
            self.kill()
            self.screen.change_screen("med den screen")
            return True
        return super().process_event(event)


class FreshkillManagementWindow(GameWindow):
    def __init__(self, screen):
        super().__init__((125, 150, 550, 420))
        self.screen = screen
        self.open_view = "feed"
        self.current_page = 1
        self.view_elements = {}
        self.cat_list = None
        self.selected_ids = []
        self.help_button = UIImageButton(
            ui_scale(pygame.Rect((18, 18), (34, 34))), "", object_id="#help_button",
            container=self, manager=MANAGER,
            tool_tip_text="Hunting patrols add prey to the pile. Prey spoils after four moons. Select cats to feed them now, or feed all hungry cats using your feeding priorities. Change tactics opens your full feeding rules and status order.",
        )
        self.tabs = {}
        for key, text, x, width, style in (
            ("feed", "Feed cats", 121, 105, ButtonStyles.PROFILE_LEFT),
            ("log", "Log", 226, 65, ButtonStyles.PROFILE_MIDDLE),
            ("tactic", "Change tactics", 291, 140, ButtonStyles.PROFILE_RIGHT),
        ):
            self.tabs[key] = UISurfaceImageButton(
                ui_scale(pygame.Rect((x, 20), (width, 30))), text,
                get_button_dict(style, (width, 30)), object_id="@buttonstyles_" + style.value,
                container=self, manager=MANAGER,
            )
        self.create_feed_view()

    def close_view(self):
        if self.cat_list is not None:
            self.selected_ids = self.cat_list.selected.copy()
            self.cat_list._generate_grid_cached.cache_clear()
        for element in self.view_elements.values():
            element.kill()
        self.view_elements = {}
        self.cat_list = None

    def create_feed_view(self):
        from scripts.screens.ClearingScreen import settings_dict
        self.close_view()
        self.open_view = "feed"
        self.tabs["feed"].disable()
        self.tabs["log"].enable()
        pile = game.clan.freshkill_pile
        living = [cat for cat in Cat.all_cats_list if not (cat.dead or cat.outside or cat.exiled)]
        pile.living_cats = living
        pile.update_nutrition(living)
        self.hungry_cats = [cat for cat in living if cat.ID in pile.nutrition_info and pile.nutrition_info[cat.ID].percentage <= 99]
        self.current_page = max(1, min(self.current_page, (len(self.hungry_cats) + 11) // 12))
        for key, icon, x in (("previous", Icon.ARROW_LEFT, 20), ("next", Icon.ARROW_RIGHT, 496)):
            self.view_elements[key] = UISurfaceImageButton(
                ui_scale(pygame.Rect((x, 160), (34, 34))), icon,
                get_button_dict(ButtonStyles.ICON, (34, 34)), object_id="@buttonstyles_icon",
                container=self, manager=MANAGER,
            )
        self.cat_list = UICatListDisplay(
            ui_scale(pygame.Rect((45, 40), (455, 270))), container=self, manager=MANAGER,
            starting_height=1, object_id="#supply_cats", cat_list=self.hungry_cats,
            cats_displayed=12, columns=4, rows=3, current_page=self.current_page,
            x_px_between=ui_scale_dimensions((5, 0))[0], y_px_between=ui_scale_dimensions((0, 5))[1],
            next_button=self.view_elements["next"], prev_button=self.view_elements["previous"],
            show_names=True, allow_selection=True, tool_tip_nutrition=True, truncate_names=True,
            text_theme="#text_box_30_horizcenter",
        )
        self.view_elements["cat_list"] = self.cat_list
        self.cat_list.selected = [cat.ID for cat in self.hungry_cats if cat.ID in self.selected_ids]
        for key, button in self.cat_list.cat_sprites.items():
            if button.return_cat_id() in self.cat_list.selected:
                self.cat_list.selection_boxes[key].show()
        if not self.hungry_cats:
            self.view_elements["empty"] = pygame_gui.elements.UITextBox(
                "No cats are hungry.", ui_scale(pygame.Rect((25, 160), (500, 40))),
                object_id="#text_box_30_horizcenter", container=self, manager=MANAGER,
            )
        self.view_elements["status"] = UITextBoxTweaked(
            f"<b>Current amount:</b> {pile.total_amount:g} pieces  -  <b>Needed amount:</b> {pile.amount_food_needed():g} pieces<br><b>Expiring soon:</b> {pile.pile['expires_in_1']:g} pieces",
            ui_scale(pygame.Rect((10, 300), (530, 60))),
            object_id="#text_box_30_horizcenter", line_spacing=1, container=self, manager=MANAGER,
        )
        for key, text, x, width in (("feed_all", "Feed all", 95, 85), ("feed_selected", "Feed selected", 200, 125)):
            self.view_elements[key] = UISurfaceImageButton(
                ui_scale(pygame.Rect((x, 370), (width, 30))), text,
                get_button_dict(ButtonStyles.SQUOVAL, (width, 30)), object_id="@buttonstyles_squoval",
                container=self, manager=MANAGER,
            )
        self.view_elements["feed_selected"].disable()
        if not self.hungry_cats or pile.total_amount <= 0:
            self.view_elements["feed_all"].disable()
        self.view_elements["ration"] = UIImageButton(
            ui_scale(pygame.Rect((340, 365), (34, 34))), "",
            object_id="@checked_checkbox" if game.clan.clan_settings["ration prey"] else "@unchecked_checkbox",
            tool_tip_text=settings_dict["freshkill_tactics"]["ration prey"][1], container=self, manager=MANAGER,
        )
        self.view_elements["ration_label"] = pygame_gui.elements.UITextBox(
            "Ration prey", ui_scale(pygame.Rect((374, 365), (150, 35))),
            object_id="#text_box_30_horizleft", container=self, manager=MANAGER,
        )
        self.view_elements["ration_label"].set_tooltip(self.view_elements["ration"].tool_tip_text)

    def create_log_view(self):
        self.close_view()
        self.open_view = "log"
        self.tabs["feed"].enable()
        self.tabs["log"].disable()
        self.view_elements["log"] = UITextBoxTweaked(
            "<br>-------------------------------<br>".join(game.freshkill_event_list or ["Nothing to report."]),
            ui_scale(pygame.Rect((25, 75), (500, 320))),
            object_id="#text_box_26_horizleft_verttop_pad_14_0_10", container=self, manager=MANAGER,
        )

    def feed_cats(self, cats):
        if not cats:
            return
        pile = game.clan.freshkill_pile
        pile.already_fed = []
        pile.feed_cats(cats, additional_food_round=True)
        pile.already_fed = []
        game.switches["saved_clan"] = False
        self.cat_list.selected.clear()
        self.create_feed_view()

    def update(self, time_delta):
        super().update(time_delta)
        if self.open_view == "feed" and self.cat_list is not None:
            selected = bool(self.cat_list.selected) and game.clan.freshkill_pile.total_amount > 0
            self.view_elements["feed_selected"].enable() if selected else self.view_elements["feed_selected"].disable()

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            element = event.ui_element
            if element == self.tabs["feed"]:
                self.create_feed_view()
            elif element == self.tabs["log"]:
                self.create_log_view()
            elif element == self.tabs["tactic"]:
                game.all_screens["clearing screen"].open_tab = "tactic"
                self.kill()
                self.screen.change_screen("clearing screen")
            elif self.open_view == "feed":
                if element == self.view_elements["feed_all"] and element.is_enabled:
                    self.feed_cats(self.hungry_cats)
                elif element == self.view_elements["feed_selected"] and element.is_enabled:
                    self.feed_cats([cat for cat in self.hungry_cats if cat.ID in self.cat_list.selected])
                elif element == self.view_elements["ration"]:
                    game.clan.switch_setting("ration prey")
                    game.switches["saved_clan"] = False
                    self.view_elements["ration"].change_object_id("@checked_checkbox" if game.clan.clan_settings["ration prey"] else "@unchecked_checkbox")
                elif element in (self.view_elements["previous"], self.view_elements["next"]):
                    self.current_page += 1 if element == self.view_elements["next"] else -1
                    self.cat_list.update_display(self.current_page, self.hungry_cats)
                    self.current_page = self.cat_list.current_page
            return True
        return super().process_event(event)

    def kill(self):
        if getattr(self, "cat_list", None) is not None:
            self.cat_list._generate_grid_cached.cache_clear()
        super().kill()
