import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame
import pygame_gui

from scripts.cat.cats import Cat
from scripts.clan import Clan, OtherClan
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.ui_elements import UICatListDisplay, UISpriteButton
from scripts.screens.AllegiancesScreen import AllegiancesScreen
from scripts.screens.LeaderDenScreen import LeaderDenScreen
from scripts.screens.ProfileScreen import ProfileScreen
from scripts.utility import get_text_box_theme, ui_scale


class TestScreenLists(unittest.TestCase):
    def setUp(self):
        clan = Clan(name="TestClan")
        clan.clan_cats = []
        clan.all_clans = []
        for target, attribute, value in (
            (Cat, "all_cats", {}),
            (Cat, "all_cats_list", []),
            (game, "clan", clan),
        ):
            replacement = patch.object(target, attribute, value)
            replacement.start()
            self.addCleanup(replacement.stop)

    def test_every_neighbor_clan_can_be_selected_and_scrolled(self):
        game.clan.all_clans = [
            OtherClan(name=f"Colony{i}", chosen_symbol="symbolTEST") for i in range(8)
        ]
        screen = LeaderDenScreen()
        with patch(
            "scripts.screens.LeaderDenScreen.clan_symbol_sprite",
            return_value=pygame.Surface((50, 50)),
        ):
            screen.create_other_clan_selection_box()
        self.addCleanup(screen.other_clan_selection_container.kill)
        self.assertTrue(screen.other_clan_scroll_container.horiz_scroll_bar.is_enabled)
        screen.outsider_selection_elements = {"page_right": Mock(), "page_left": Mock()}
        with patch.object(screen, "update_other_clan_focus") as update:
            for i, clan in enumerate(game.clan.all_clans):
                screen.handle_event(
                    pygame.event.Event(
                        pygame_gui.UI_BUTTON_START_PRESS,
                        ui_element=screen.other_clan_selection_elements[f"button{i}"],
                    )
                )
                self.assertIs(screen.focus_clan, clan)
            self.assertEqual(update.call_count, 8)

    def test_five_neighbor_clans_fit_without_scrolling(self):
        game.clan.all_clans = [
            OtherClan(name=f"Colony{i}", chosen_symbol="symbolTEST") for i in range(5)
        ]
        screen = LeaderDenScreen()
        with patch(
            "scripts.screens.LeaderDenScreen.clan_symbol_sprite",
            return_value=pygame.Surface((50, 50)),
        ):
            screen.create_other_clan_selection_box()
        self.addCleanup(screen.other_clan_selection_container.kill)
        self.assertFalse(screen.other_clan_scroll_container.horiz_scroll_bar.is_enabled)

    def test_caretaker_heading_shares_its_row_with_the_cat_list(self):
        queen = Cat(status="queen", moons=30)
        game.clan.add_cat(queen)
        rows = AllegiancesScreen().get_allegiances_text()
        caretakers = next(row for row in rows if "CARETAKERS" in row[0])
        self.assertIn(str(queen.name).upper(), caretakers[1])

    def test_cat_names_wrap_without_truncation(self):
        container = pygame_gui.core.UIContainer(
            ui_scale(pygame.Rect((0, 0), (120, 133))), manager=MANAGER
        )
        self.addCleanup(container.kill)
        sprite = UISpriteButton(
            ui_scale(pygame.Rect((0, 15), (50, 50))),
            pygame.Surface((50, 50), pygame.SRCALPHA),
            container=container,
            manager=MANAGER,
        )
        display = UICatListDisplay.__new__(UICatListDisplay)
        display.cat_names = {}
        display.cat_sprites = {"sprite0": sprite}
        display.text_theme = get_text_box_theme("#text_box_30_horizcenter")
        name = "Herald of the Distant Skies"
        display.create_name(0, SimpleNamespace(name=name), container)
        box = display.cat_names["name0"]
        self.assertIsInstance(box, pygame_gui.elements.UITextBox)
        self.assertEqual(box.html_text, name)
        self.assertGreater(box.rect.height, 30)
        self.assertLessEqual(box.rect.bottom, container.rect.bottom)

    def test_complete_cat_grid_renders_and_changes_pages(self):
        container = pygame_gui.core.UIContainer(
            ui_scale(pygame.Rect((0, 0), (600, 450))), manager=MANAGER
        )
        self.addCleanup(container.kill)
        previous = pygame_gui.elements.UIButton(
            pygame.Rect((0, 400), (40, 30)), "<", container=container, manager=MANAGER
        )
        next_button = pygame_gui.elements.UIButton(
            pygame.Rect((50, 400), (40, 30)), ">", container=container, manager=MANAGER
        )
        cats = [
            SimpleNamespace(
                ID=str(i),
                name=f"Herald of the Distant Skies {i}",
                favourite=0,
                sprite=pygame.Surface((50, 50), pygame.SRCALPHA),
            )
            for i in range(16)
        ]
        display = UICatListDisplay(
            ui_scale(pygame.Rect((0, 0), (600, 400))),
            container=container,
            starting_height=1,
            object_id="#cat_list_display",
            manager=MANAGER,
            cat_list=cats,
            cats_displayed=15,
            x_px_between=120,
            columns=5,
            current_page=1,
            next_button=next_button,
            prev_button=previous,
            show_names=True,
            text_theme=get_text_box_theme("#text_box_30_horizcenter"),
        )
        self.assertEqual(display.total_pages, 2)
        self.assertEqual(len(display.cat_sprites), 15)
        self.assertEqual(display.cat_names["name0"].html_text, str(cats[0].name))
        display.current_page = 2
        display._display_cats()
        self.assertEqual(display.cat_names["name0"].html_text, str(cats[15].name))
        MANAGER.update(0.1)
        MANAGER.draw_ui(pygame.Surface(MANAGER.window_resolution))

    def test_shunning_demotes_a_deputy_and_removal_preserves_the_new_role(self):
        cat = Cat(status="deputy", moons=30)
        game.clan.your_cat = cat
        game.clan.deputy = cat
        game.clan.add_cat(cat)
        screen = ProfileScreen.__new__(ProfileScreen)
        screen.open_tab = "roles"
        screen.the_cat = cat
        screen.manage_roles = Mock()
        screen.change_mentor_button = Mock()
        screen.shun_button = Mock()
        screen.clear_profile = Mock()
        screen.build_profile = Mock()
        screen.update_disabled_buttons_and_text = Mock()
        event = SimpleNamespace(ui_element=screen.shun_button)
        screen.handle_tab_events(event)
        self.assertEqual(cat.shunned, 1)
        self.assertEqual(cat.status, "warrior")
        self.assertIsNone(game.clan.deputy)
        screen.handle_tab_events(event)
        self.assertEqual(cat.shunned, 0)
        self.assertEqual(cat.forgiven, 1)
        self.assertEqual(cat.status, "warrior")

    def test_shun_button_is_disabled_for_dead_and_outside_cats(self):
        screen = ProfileScreen.__new__(ProfileScreen)
        screen.the_cat = Cat(status="warrior", moons=30)
        screen.open_tab = "roles"
        screen.accessories_tab_button = Mock()
        screen.manage_roles = Mock()
        screen.change_mentor_button = Mock()
        screen.shun_button = Mock()
        for dead, outside in ((True, False), (False, True), (False, False)):
            with self.subTest(dead=dead, outside=outside):
                screen.the_cat.dead, screen.the_cat.outside = dead, outside
                screen.shun_button.reset_mock()
                screen.update_disabled_buttons_and_text()
                if dead or outside:
                    screen.shun_button.disable.assert_called_once()
                else:
                    screen.shun_button.enable.assert_called_once()


class TestCustomizer(unittest.TestCase):
    def setUp(self):
        from scripts.cat.history import History
        from scripts.screens.CustomizeCatScreen import CustomizeCatScreen
        clan = Clan(name="TestClan")
        clan.age = 12
        for target, attribute, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []), (game, "clan", clan)):
            replacement = patch.object(target, attribute, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.cat = Cat(status="warrior", moons=30)
        self.cat.history = History()
        clan.clan_cats = [self.cat.ID]
        clan.your_cat = self.cat
        self.screen = CustomizeCatScreen()
        self.screen.change_screen = Mock()
        replacement = patch("scripts.screens.CatCustomizer.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA))
        replacement.start()
        self.addCleanup(replacement.stop)
        replacement = patch("scripts.utility.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA))
        replacement.start()
        self.addCleanup(replacement.stop)
        with patch.dict(game.switches, {"cat": self.cat.ID}):
            self.screen.screen_switches()
        self.addCleanup(self.screen.exit_screen)

    def press(self, widget):
        self.screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=widget))

    def option(self, value):
        editor = self.screen.elements["appearance_editor"]
        editor.option_list.scroll_to(value)
        self.press(editor.option_buttons[value])

    def test_both_entry_points_use_the_exact_same_full_editor(self):
        from scripts.screens.MakeClanScreen import MakeClanScreen
        from scripts.screens.CustomizeCatScreen import CustomizeCatScreen
        for method in ("open_customize_cat", "randomize_custom_cat", "handle_customize_cat_event",
                       "get_customizer_state", "apply_customizer_locks", "setup_customizer_lock_buttons"):
            self.assertIs(getattr(MakeClanScreen, method), getattr(CustomizeCatScreen, method))
        for key in ("random_customize", "undo_customize", "redo_customize", "lock_adult_pose"):
            self.assertIn(key, self.screen.elements)

    def test_randomization_locks_undo_redo_and_cancel_leave_live_cat_unchanged(self):
        original = self.cat.get_save_dict()
        self.press(self.screen.elements["lock_adult_pose"])
        locked = self.screen.get_customizer_state()
        self.press(self.screen.elements["random_customize"])
        self.assertEqual(self.screen.length, locked["length"])
        self.assertEqual(self.screen.adult_pose, locked["adult_pose"])
        self.assertEqual(self.cat.get_save_dict(), original)
        self.press(self.screen.elements["undo_customize"])
        self.assertEqual(self.screen.get_customizer_state(), locked)
        self.press(self.screen.elements["redo_customize"])
        self.assertEqual(set(Cat.all_cats), {self.cat.ID})
        self.assertEqual(Cat.all_cats_list, [self.cat])
        self.press(self.screen.elements["previous_step"])
        self.assertEqual(self.cat.get_save_dict(), original)
        self.screen.change_screen.assert_called_with("profile screen")

    def test_virtual_checklists_remove_individual_items_and_retain_history(self):
        self.press(self.screen.elements["right"])
        self.press(self.screen.current_selection_buttons["white_patches"])
        self.screen.white_patches = []
        self.screen.update_sprite()
        self.screen.update_disabled_buttons()
        editor = self.screen.elements["appearance_editor"]
        self.assertLessEqual(len(editor.option_buttons), 15)
        self.assertGreater(len(editor.option_list.options), 200)
        for value in ("VAN", "TUXEDO", "VAN"):
            self.option(value)
        self.assertEqual(self.screen.white_patches, ["TUXEDO"])
        self.press(self.screen.elements["undo_customize"])
        self.assertEqual(self.screen.white_patches, ["VAN", "TUXEDO"])
        self.press(self.screen.elements["redo_customize"])
        self.assertEqual(self.screen.white_patches, ["TUXEDO"])
        editor = self.screen.elements["appearance_editor"]
        button = next(iter(editor.option_buttons.values()))
        with patch.object(button, "change_object_id", wraps=button.change_object_id) as rebuild:
            self.screen.update_disabled_buttons()
            self.screen.update_disabled_buttons()
            rebuild.assert_not_called()
        self.press(self.screen.elements["next_step"])
        self.assertEqual(self.cat.pelt.white_patches, ["TUXEDO"])

    def test_apply_updates_skills_conditions_and_details_without_changing_identity(self):
        identity = (self.cat.ID, self.cat.moons, self.cat.status)
        points = self.cat.skills.primary.points
        self.screen.page = 3
        self.screen.current_selection = "condition"
        self.screen.open_customize_cat()
        self.press(self.screen.condition_buttons["paralyzed"])
        self.assertNotIn("paralyzed", self.cat.permanent_condition)
        self.press(self.screen.current_selection_buttons["skill"])
        from scripts.cat.skills import SkillPath
        self.press(self.screen.skill_buttons[SkillPath.HUNTER.value[0]])
        self.press(self.screen.elements["right"])
        self.press(self.screen.current_selection_buttons["height"])
        self.press(self.screen.detail_buttons["towering"])
        self.press(self.screen.elements["next_step"])
        self.assertEqual((self.cat.ID, self.cat.moons, self.cat.status), identity)
        self.assertTrue(self.cat.pelt.paralyzed)
        self.assertIn("paralyzed", self.cat.permanent_condition)
        self.assertEqual(self.cat.skills.primary.path, SkillPath.HUNTER)
        self.assertEqual(self.cat.skills.primary.points, points)
        self.assertEqual(self.cat.pelt.height, "towering")
        self.assertEqual(self.cat.history.condition_events[-1]["condition"], "paralyzed")

    def test_invalid_condition_choice_cannot_partially_apply_changes(self):
        before = self.cat.get_save_dict()
        self.screen.sex = "female"
        self.screen.permanent_condition = "excess testosterone"
        self.screen.page = 3
        self.screen.current_selection = "condition"
        self.screen.open_customize_cat()
        self.assertFalse(self.screen.elements["next_step"].is_enabled)
        self.assertFalse(self.screen.condition_buttons["excess testosterone"].is_enabled)
        self.assertEqual(self.cat.get_save_dict(), before)

    def test_newborn_without_skills_can_open_and_cancel_the_same_editor(self):
        newborn = Cat(status="newborn", moons=0)
        game.clan.clan_cats.append(newborn.ID)
        self.screen.exit_screen()
        with patch.dict(game.switches, {"cat": newborn.ID}):
            self.screen.screen_switches()
        self.assertEqual(self.screen.skill, "None")
        self.assertIn("random_customize", self.screen.elements)
        self.press(self.screen.elements["previous_step"])
        self.assertIsNone(newborn.skills.primary)



class TestClanCreationCancellation(unittest.TestCase):
    def setUp(self):
        for target, attribute, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", [])):
            replacement = patch.object(target, attribute, value)
            replacement.start()
            self.addCleanup(replacement.stop)

    def test_cancel_restores_unsaved_clan_and_registry(self):
        from scripts.screens.MakeClanScreen import MakeClanScreen
        from scripts.screens.Screens import Screens
        screen = MakeClanScreen.__new__(MakeClanScreen)
        clan = Clan(name="Original", biome="Mountainous", camp_bg="camp2")
        original_cat = Cat(status="warrior", moons=30)
        original_cat.name.prefix = "Unsaved"
        screen.previous_clan = clan
        screen.previous_cats = {original_cat.ID: original_cat}
        screen.previous_cat_list = [original_cat]
        screen.previous_choices = {1: original_cat}
        screen.clan_saved = False
        screen.main_menu = Mock()
        screen.clear_all_page = Mock()
        screen.set_mute_button_position = Mock()
        with patch.object(game, "clan", Clan(name="Draft")), \
             patch.object(Cat, "all_cats", {}), \
             patch.object(Cat, "all_cats_list", []), \
             patch.object(game, "choose_cats", {}), \
             patch.dict(game.switches, {"customise_new_life": True}), \
             patch.object(Screens, "exit_screen"):
            screen.exit_screen()
            self.assertIs(game.clan, clan)
            self.assertEqual(game.clan.biome, "Mountainous")
            self.assertEqual(game.clan.camp_bg, "camp2")
            self.assertIs(Cat.all_cats[original_cat.ID], original_cat)
            self.assertEqual(original_cat.name.prefix, "Unsaved")
            self.assertEqual(Cat.all_cats_list, [original_cat])
            self.assertEqual(game.choose_cats, {1: original_cat})
            self.assertFalse(game.switches["customise_new_life"])

    def test_completed_clan_is_kept(self):
        from scripts.screens.MakeClanScreen import MakeClanScreen
        from scripts.screens.Screens import Screens
        screen = MakeClanScreen.__new__(MakeClanScreen)
        screen.clan_saved = True
        screen.main_menu = Mock()
        screen.clear_all_page = Mock()
        screen.set_mute_button_position = Mock()
        clan = Clan(name="Completed")
        with patch.object(game, "clan", clan), patch.object(Screens, "exit_screen"):
            screen.exit_screen()
            self.assertIs(game.clan, clan)

    def test_cancel_without_loaded_clan_restores_empty_registry(self):
        from scripts.screens.MakeClanScreen import MakeClanScreen
        from scripts.screens.Screens import Screens
        screen = MakeClanScreen.__new__(MakeClanScreen)
        screen.previous_clan = None
        screen.previous_cats = {}
        screen.previous_cat_list = []
        screen.previous_choices = {}
        screen.clan_saved = False
        screen.main_menu = Mock()
        screen.clear_all_page = Mock()
        screen.set_mute_button_position = Mock()
        Cat(status="kitten", moons=3, example=True)
        with patch.object(game, "clan", Clan(name="Draft")), \
             patch.object(game, "choose_cats", {}), \
             patch.dict(game.switches, {"customise_new_life": False}), \
             patch.object(Screens, "exit_screen"):
            screen.exit_screen()
            self.assertIsNone(game.clan)
            self.assertEqual(Cat.all_cats, {})
            self.assertEqual(Cat.all_cats_list, [])

    def test_creation_customizer_native_undo_redo_and_randomization(self):
        from scripts.screens.MakeClanScreen import MakeClanScreen
        screen = MakeClanScreen()
        screen.tutorial_shown = True
        with patch.object(game, "clan", None), \
             patch.object(game, "choose_cats", {}), \
             patch.dict(game.switches, {"customise_new_life": False}), \
             patch("scripts.screens.CatCustomizer.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA)), \
             patch("scripts.utility.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA)):
            screen.screen_switches()
            try:
                screen.open_customize_cat()
                before = screen.get_customizer_state()
                def press(widget):
                    screen.handle_customize_cat_event(pygame.event.Event(
                        pygame_gui.UI_BUTTON_START_PRESS, ui_element=widget))
                self.assertFalse(screen.elements["undo_customize"].is_enabled)
                press(screen.elements["lock_adult_pose"])
                self.assertIn("adult_pose", screen.customizer_locks)
                locked = screen.get_customizer_state()
                press(screen.elements["random_customize"])
                self.assertEqual(screen.adult_pose, locked["adult_pose"])
                self.assertEqual(screen.length, locked["length"])
                press(screen.elements["undo_customize"])
                self.assertEqual(screen.get_customizer_state(), locked)
                press(screen.elements["undo_customize"])
                self.assertEqual(screen.customizer_locks, set())
                press(screen.elements["redo_customize"])
                self.assertIn("adult_pose", screen.customizer_locks)
                press(screen.elements["lock_adult_pose"])
                screen.customizer_undo.clear()
                screen.customizer_redo.clear()
                screen.update_customizer_history_buttons()
                press(screen.elements["random_customize"])
                randomized = screen.get_customizer_state()
                self.assertNotEqual(randomized, before)
                press(screen.elements["undo_customize"])
                self.assertEqual(screen.get_customizer_state(), before)
                press(screen.elements["redo_customize"])
                self.assertEqual(screen.get_customizer_state(), randomized)
                press(screen.elements["undo_customize"])
                press(screen.kitten_pose_buttons["1"])
                self.assertEqual(screen.customizer_redo, [])
                edited = screen.get_customizer_state()
                press(screen.elements["right"])
                self.assertEqual(len(screen.customizer_undo), 1)
                press(screen.elements["undo_customize"])
                self.assertEqual(screen.get_customizer_state(), before)
                press(screen.elements["redo_customize"])
                self.assertEqual(screen.get_customizer_state(), edited)
                press(screen.elements["left"])
                with patch("scripts.screens.CatCustomizer.random.randint", return_value=2):
                    press(screen.elements["randomise_selection"])
                self.assertEqual(len(screen.customizer_undo), 2)
                press(screen.elements["undo_customize"])
                self.assertEqual(screen.get_customizer_state(), edited)
                press(screen.elements["lock_kitten_pose"])
                self.assertFalse(screen.elements["randomise_selection"].is_enabled)
                locked = screen.get_customizer_state()
                press(screen.elements["randomise_selection"])
                self.assertEqual(screen.get_customizer_state(), locked)
                press(screen.kitten_pose_buttons["2"])
                self.assertEqual(screen.kitten_sprite, 2)
                self.assertIn("kitten_pose", screen.customizer_locks)
                press(screen.elements["right"])
                press(screen.current_selection_buttons["white_patches"])
                with patch("scripts.screens.CatCustomizer.random.choice", return_value="FULLWHITE"):
                    press(screen.elements["randomise_selection"])
                self.assertEqual(screen.white_patches, ["FULLWHITE"])
                for value in ("VAN", "TUXEDO", "VAN"):
                    screen.elements["appearance_editor"].option_list.scroll_to(value)
                    press(screen.white_patches_buttons[value])
                self.assertEqual(screen.white_patches, ["FULLWHITE", "TUXEDO"])
                self.assertEqual(screen.custom_cat.pelt.white_patches, screen.white_patches)
                press(screen.elements["undo_customize"])
                self.assertEqual(screen.white_patches, ["FULLWHITE", "VAN", "TUXEDO"])
                press(screen.elements["redo_customize"])
                self.assertEqual(screen.white_patches, ["FULLWHITE", "TUXEDO"])
                press(screen.elements["lock_white_patches"])
                saved = screen.get_customizer_state()
                press(screen.elements["random_customize"])
                self.assertEqual(screen.white_patches, saved["white_patches"])
                self.assertEqual(screen.white_patches_tint, saved["white_patches_tint"])
                screen.customizer_locks = set(screen.customizer_lock_groups)
                saved = screen.get_customizer_state()
                screen.randomize_custom_cat()
                self.assertEqual(screen.get_customizer_state(), saved)
                screen.customizer_locks = {"accessory"}
                screen.permanent_condition = None
                screen.paralyzed = False
                screen.scars = []
                screen.accessories = [screen.notail_accs[0]]
                screen.inventory = screen.accessories.copy()
                saved = screen.get_customizer_state()
                screen.permanent_condition = "born without a tail"
                screen.scars = ["NOTAIL"]
                screen.accessories = []
                screen.inventory = []
                screen.apply_customizer_locks(saved)
                self.assertEqual(screen.accessories, saved["accessories"])
                self.assertIsNone(screen.permanent_condition)
                self.assertEqual(screen.scars, [])
                screen.customizer_locks = {"length"}
                screen.length = "short"
                saved = screen.get_customizer_state()
                screen.length = "long"
                screen.adult_pose = 9
                screen.apply_customizer_locks(saved)
                self.assertEqual(screen.length, "short")
                self.assertEqual(screen.adult_pose, 6)
            finally:
                screen.exit_screen()
