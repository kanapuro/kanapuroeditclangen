# pylint: disable=line-too-long
import pygame
import pygame_gui
import ujson

from scripts.game_structure.game_essentials import game
from scripts.game_structure.ui_elements import UISurfaceImageButton, UIImageButton
from scripts.utility import get_text_box_theme, ui_scale, ui_scale_dimensions
from .Screens import Screens
from ..game_structure.screen_settings import MANAGER
from ..ui.generate_button import get_button_dict, ButtonStyles
from ..ui.get_arrow import get_arrow

with open("resources/gamesettings.json", "r", encoding="utf-8") as f:
    settings_dict = ujson.load(f)


class ContentSettingsScreen(Screens):
    """
    Screen for managing content warnings and sensitive content settings
    """

    settings_at_open = {}
    settings_changed = False
    checkboxes = {}
    checkboxes_text = {}

    def __init__(self, name="content settings screen"):
        super().__init__(name)

    def handle_event(self, event):
        """Handle events for this screen"""
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.main_menu_button:
                self.change_screen("start screen")
                return
            elif event.ui_element == self.save_settings_button:
                self.save_settings()
                game.save_settings(self)
                self.settings_changed = False
                self.update_save_button()
                return

            if event.ui_element in self.checkboxes.values():
                for key, value in self.checkboxes.items():
                    if value == event.ui_element:
                        game.settings[key] = not game.settings[key]
                        value.change_object_id(
                            "@checked_checkbox"
                            if game.settings[key]
                            else "@unchecked_checkbox"
                        )
                        self.settings_changed = True
                        self.update_save_button()
                        break

        elif event.type == pygame.KEYDOWN and game.settings.get("keybinds", False):
            if event.key == pygame.K_ESCAPE:
                self.change_screen("start screen")

    def screen_switches(self):
        """Set up the screen"""
        super().screen_switches()
        
        self.show_mute_buttons()
        self.settings_changed = False
        
        for code, desc in settings_dict.get("content", {}).items():
            if code not in game.settings:
                game.settings[code] = desc[2]

        self.main_menu_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((25, 25), (152, 30))),
            get_arrow(3) + " Main Menu",
            get_button_dict(ButtonStyles.SQUOVAL, (152, 30)),
            manager=MANAGER,
            object_id="@buttonstyles_squoval",
            starting_height=1,
        )

        self.checkboxes_text["instr"] = pygame_gui.elements.UITextBox(
            "This game contains dark content not suitable for children. You can use these settings to manage your experience and toggle sensitive features. These settings are saved globally.",
            ui_scale(pygame.Rect((100, 100), (600, 80))),
            object_id=get_text_box_theme("#text_box_30_horizcenter"),
            manager=MANAGER,
        )

        self.checkboxes_text["container_content"] = pygame_gui.elements.UIScrollingContainer(
            ui_scale(pygame.Rect((0, 200), (700, 320))),
            allow_scroll_x=False,
            manager=MANAGER,
        )

        for i, (code, desc) in enumerate(settings_dict.get("content", {}).items()):
            self.checkboxes_text[code] = pygame_gui.elements.UITextBox(
                desc[0],
                ui_scale(pygame.Rect((225, 34 if i < 0 else 0), (500, 34))),
                container=self.checkboxes_text["container_content"],
                object_id=get_text_box_theme("#text_box_30_horizleft_vertcenter"),
                manager=MANAGER,
                anchors={
                    "top_target": self.checkboxes_text[list(self.checkboxes_text)[-1]]
                }
                if i > 0
                else None,
            )
            self.checkboxes_text[code].disable()

        self.checkboxes_text["container_content"].set_scrollable_area_dimensions(
            ui_scale_dimensions((680, (len(settings_dict.get("content", {}).keys()) * 39 + 40)))
        )

        self.save_settings_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 550), (150, 30))),
            "Save Settings",
            get_button_dict(ButtonStyles.SQUOVAL, (150, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            anchors={"centerx": "centerx"},
        )
        self.update_save_button()

        self.set_bg("default", "mainmenu_bg")
        self.settings_at_open = game.settings.copy()
        self.refresh_checkboxes()

    def refresh_checkboxes(self):
        """Refresh all checkboxes to match current settings"""
        for checkbox in self.checkboxes.values():
            checkbox.kill()
        self.checkboxes = {}

        for i, (code, desc) in enumerate(settings_dict.get("content", {}).items()):
            if code not in game.settings:
                game.settings[code] = desc[2]
            
            if game.settings[code]:
                box_type = "@checked_checkbox"
            else:
                box_type = "@unchecked_checkbox"
            
            self.checkboxes[code] = UIImageButton(
                ui_scale(pygame.Rect((170, 34 if i < 0 else 0), (34, 34))),
                "",
                object_id=box_type,
                container=self.checkboxes_text["container_content"],
                tool_tip_text=desc[1],
                anchors={
                    "top_target": self.checkboxes_text[list(self.checkboxes)[-1]]
                }
                if i > 0
                else None,
            )

    def update_save_button(self):
        """Updates the disabled state of the save button"""
        if not self.settings_changed:
            self.save_settings_button.disable()
        else:
            self.save_settings_button.enable()

    def exit_screen(self):
        """Clean up when leaving the screen"""
        for element in self.checkboxes_text.values():
            if hasattr(element, 'kill'):
                element.kill()
        for element in self.checkboxes.values():
            if hasattr(element, 'kill'):
                element.kill()

        self.checkboxes_text = {}
        self.checkboxes = {}

        if hasattr(self, 'main_menu_button'):
            self.main_menu_button.kill()
            del self.main_menu_button
        if hasattr(self, 'save_settings_button'):
            self.save_settings_button.kill()
            del self.save_settings_button

        if self.settings_changed:
            game.settings = self.settings_at_open.copy()

    def save_settings(self):
        """Saves the settings"""
        self.settings_at_open = game.settings.copy()
