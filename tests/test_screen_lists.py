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

    def test_deputy_can_replace_a_retired_leader(self):
        from scripts.screens.RoleScreen import RoleScreen

        old_leader = Cat(status="elder", moons=140)
        successor = Cat(status="warrior", moons=40)
        game.clan.leader = old_leader
        game.clan.deputy = None
        game.clan.your_cat = successor
        screen = RoleScreen()
        screen.the_cat = successor
        screen.next_cat = screen.previous_cat = 0
        with patch.object(screen, "update_selected_cat", side_effect=screen.update_disabled_buttons):
            screen.screen_switches()
            self.addCleanup(screen.exit_screen)
            self.assertTrue(screen.promote_deputy.is_enabled)
            screen.handle_event(pygame.event.Event(
                pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.promote_deputy
            ))
            self.assertIs(game.clan.deputy, successor)
            self.assertTrue(screen.promote_leader.is_enabled)
            old_leader.status = "leader"
            screen.update_disabled_buttons()
            self.assertFalse(screen.promote_leader.is_enabled)
            old_leader.status = "elder"
            screen.update_disabled_buttons()
            with patch.object(game.clan.history, "add_lead_ceremony"):
                screen.handle_event(pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.promote_leader
                ))
            self.assertIs(game.clan.leader, successor)
            self.assertEqual(successor.status, "leader")
            self.assertIsNone(game.clan.deputy)
            self.assertEqual(old_leader.status, "elder")

    def test_automatic_leader_promotion_updates_role_before_retirement(self):
        from scripts.events import Events

        successor = Cat(status="deputy", moons=140)
        game.clan.leader = None
        game.clan.deputy = successor
        game.clan.your_cat = successor
        game.clan.clan_settings["leader"] = True
        events = Events.__new__(Events)
        with patch.object(game, "cur_events_list", []), patch.object(
            events, "gain_accessories"
        ), patch.object(game.clan.history, "add_lead_ceremony"):
            events.check_and_promote_leader()
        self.assertIs(game.clan.leader, successor)
        self.assertEqual(successor.status, "leader")
        self.assertEqual(successor.name.status, "leader")
        self.assertIsNone(game.clan.deputy)
        successor.retire_cat()
        self.assertEqual(successor.status, "elder")
        self.assertIsNone(game.clan.leader)

    def test_retired_leader_allows_automatic_succession_or_leaderless_alert(self):
        from scripts.events import Events

        old_leader = Cat(status="elder", moons=140)
        successor = Cat(status="deputy", moons=40)
        game.clan.your_cat = successor
        events = Events.__new__(Events)
        for auto_promote, has_deputy in ((False, True), (True, False), (True, True)):
            with self.subTest(auto_promote=auto_promote, has_deputy=has_deputy):
                game.clan.leader = old_leader
                game.clan.deputy = successor if has_deputy else None
                game.clan.clan_settings["leader"] = auto_promote
                with patch.object(game, "cur_events_list", []), patch.object(
                    events, "gain_accessories"
                ), patch.object(game.clan.history, "add_lead_ceremony"):
                    events.check_and_promote_leader()
                    if auto_promote and has_deputy:
                        self.assertIs(game.clan.leader, successor)
                        self.assertEqual(successor.status, "leader")
                        self.assertIsNone(game.clan.deputy)
                        self.assertFalse(any("has no leader!" in event.text
                                             for event in game.cur_events_list))
                    else:
                        self.assertIs(game.clan.leader, old_leader)
                        self.assertEqual(game.cur_events_list[0].text, "TestClan has no leader!")

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
        display.truncate_names = False
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
        self.cat = Cat(status="warrior", moons=30, gender="female")
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

    def start_creation(self, moons):
        from scripts.debug_commands.cat import CreateCatCommand

        replacement = patch.dict(game.switches, {"cat": self.cat.ID, "window_open": False})
        replacement.start()
        self.addCleanup(replacement.stop)
        self.screen.exit_screen()
        with patch.object(game, "current_screen", "camp screen"), patch.object(
            game, "all_screens", {"camp screen": Mock()}
        ), patch("scripts.debug_console.debug_mode"):
            CreateCatCommand().callback([str(moons)])
        self.screen.screen_switches()
        return self.screen.the_cat

    def test_edit_and_create_keep_adult_backstories(self):
        self.assertIn("kittypet3", self.screen.details_options["backstory"])
        self.assertIn("retired_leader", self.screen.details_options["backstory"])
        self.assertIn("halfclan7", self.screen.details_options["backstory"])
        self.assertIn("orphaned7", self.screen.details_options["backstory"])
        self.assertNotIn("Random", self.screen.details_options["backstory"])
        self.screen.page = 4
        self.screen.current_selection = "backstory"
        self.screen.open_customize_cat()
        self.screen.elements["details"].scroll_to("retired_leader")
        self.press(self.screen.detail_buttons["retired_leader"])
        self.press(self.screen.elements["next_step"])
        self.assertEqual(self.cat.backstory, "retired_leader")
        draft = self.start_creation(30)
        self.screen.page = 4
        self.screen.current_selection = "backstory"
        self.screen.open_customize_cat()
        self.screen.elements["details"].scroll_to("kittypet3")
        self.press(self.screen.detail_buttons["kittypet3"])
        self.press(self.screen.elements["next_step"])
        self.assertEqual(draft.backstory, "kittypet3")

    def test_create_cancel_discards_draft_and_restores_previous_selection(self):
        before = self.cat.get_save_dict()
        draft = self.start_creation(8)
        self.assertEqual(self.screen.elements["next_step"].text, "Create")
        self.assertNotIn(draft.ID, Cat.all_cats)
        self.screen.scars = ["NOTAIL", "NOPAW"]
        self.screen.colour = "BLACK"
        self.press(self.screen.elements["previous_step"])
        self.screen.change_screen.assert_called_with("camp screen")
        self.assertNotIn("create_cat", game.switches)
        self.assertEqual(game.switches["cat"], self.cat.ID)
        self.assertEqual(Cat.all_cats, {self.cat.ID: self.cat})
        self.assertEqual(Cat.all_cats_list, [self.cat])
        self.assertEqual(game.clan.clan_cats, [self.cat.ID])
        self.assertEqual(self.cat.get_save_dict(), before)

    def test_create_confirm_registers_edited_cat_relationships_history_and_mentor(self):
        draft = self.start_creation(8)
        self.screen.colour = "BLACK"
        self.screen.set_customizer_conditions(["allergies", "partial hearing loss"])
        self.press(self.screen.elements["next_step"])
        self.assertIs(Cat.all_cats[draft.ID], draft)
        self.assertIn(draft, Cat.all_cats_list)
        self.assertIn(draft.ID, game.clan.clan_cats)
        self.assertEqual((draft.moons, draft.status, draft.pelt.colour), (8, "apprentice", "BLACK"))
        self.assertTrue({"allergies", "partial hearing loss"}.issubset(draft.permanent_condition))
        self.assertIn(self.cat.ID, draft.relationships)
        self.assertIn(draft.ID, self.cat.relationships)
        self.assertEqual(draft.mentor, self.cat.ID)
        self.assertIn(draft.ID, self.cat.apprentice)
        self.assertIsNotNone(draft.inheritance)
        self.assertEqual(draft.history.beginning["age"], 8)
        self.assertIs(game.clan.your_cat, self.cat)
        self.assertEqual(game.switches["cat"], draft.ID)
        self.assertNotIn("create_cat", game.switches)
        self.screen.change_screen.assert_called_with("profile screen")

    def test_created_cat_survives_real_save_and_reload(self):
        from tempfile import TemporaryDirectory
        from scripts.game_structure.load_cat import load_cats

        draft = self.start_creation(8)
        self.screen.set_customizer_scars(["ONE", "TWO", "THREE"])
        self.screen.set_customizer_conditions(["allergies", "partial hearing loss"])
        self.press(self.screen.elements["next_step"])
        expected_scars = draft.pelt.scars.copy()
        with TemporaryDirectory() as directory, patch(
            "scripts.game_structure.game_essentials.get_save_dir", return_value=directory
        ), patch("scripts.cat.cats.get_save_dir", return_value=directory), patch(
            "scripts.game_structure.load_cat.get_save_dir", return_value=directory
        ), patch.object(game, "cat_class", Cat), patch.object(game, "cat_to_fade", []), patch.dict(
            game.switches, {"clan_name": game.clan.name, "clan_list": [game.clan.name]}
        ):
            game.save_cats()
            Cat.all_cats.clear()
            Cat.all_cats_list.clear()
            load_cats()
            loaded = Cat.all_cats[draft.ID]
            loaded.load_history()
            self.assertEqual((loaded.moons, loaded.status), (8, "apprentice"))
            self.assertEqual(loaded.pelt.scars, expected_scars)
            self.assertTrue({"allergies", "partial hearing loss"}.issubset(loaded.permanent_condition))
            self.assertEqual(loaded.mentor, self.cat.ID)
            self.assertIn(self.cat.ID, loaded.relationships)
            self.assertIn(loaded.ID, Cat.all_cats[self.cat.ID].relationships)
            self.assertIsNotNone(loaded.inheritance)
            self.assertEqual(loaded.history.beginning["age"], 8)
            self.assertTrue({"allergies", "partial hearing loss"}.issubset(
                {event["condition"] for event in loaded.history.condition_events}
            ))

    def test_display_rebuild_retains_creation_draft_and_undo_history(self):
        draft = self.start_creation(12)
        self.press(self.screen.elements["cycle_right"])
        self.screen.page = 1
        self.screen.current_selection = "vitiligo"
        self.screen.open_customize_cat()
        self.option("VITILIGO")
        state = self.screen.get_customizer_state()
        history = self.screen.customizer_undo.copy()
        data = self.screen.display_change_save()
        self.screen.exit_screen()
        self.screen.screen_switches()
        for _ in range(2):
            self.screen.display_change_load(data)
            self.assertEqual(self.screen.get_customizer_state(), state)
            self.assertEqual(self.screen.customizer_undo, history)
            self.assertEqual((self.screen.page, self.screen.current_selection), (1, "vitiligo"))
            self.assertEqual(self.screen.elements["next_step"].text, "Create")
        self.assertIs(self.screen.the_cat, draft)
        self.assertNotIn(draft.ID, Cat.all_cats)
        self.press(self.screen.elements["undo_customize"])
        self.assertNotEqual(self.screen.get_customizer_state(), state)
        self.press(self.screen.elements["previous_step"])
        self.assertNotIn("create_cat", game.switches)

    def test_backstory_choices_have_formatted_preview_tooltips(self):
        from scripts.cat.cats import BACKSTORIES
        from scripts.screens.ProfileScreen import ProfileScreen

        self.screen.page = 4
        self.screen.current_selection = "backstory"
        self.screen.open_customize_cat()
        for value in self.screen.details_options["backstory"]:
            with self.subTest(value=value):
                self.assertIn(value, BACKSTORIES["backstories"])
                text = self.screen.customizer_description(value)
                self.assertNotIn("{PRONOUN/", text)
                self.assertNotIn("{VERB/", text)
                self.assertNotIn("m_c", text)
                self.assertNotIn("o_c_n", text)
                self.assertIn(str(self.cat.name), text)
        self.screen.elements["details"].scroll_to("unknown")
        self.assertEqual(self.screen.detail_buttons["unknown"].tool_tip_text,
                         self.screen.customizer_description("unknown"))
        self.assertEqual(self.screen.elements["details"].rows["unknown"][1].tool_tip_text,
                         self.screen.customizer_description("unknown"))
        self.press(self.screen.detail_buttons["unknown"])
        self.press(self.screen.elements["next_step"])
        self.assertEqual(self.cat.backstory, "unknown")
        profile = ProfileScreen.__new__(ProfileScreen)
        profile.the_cat = self.cat
        self.assertIn("past history is unknown", profile.get_backstory_text())
        self.cat.backstory = "abandoned5"
        self.assertIn("past history is unknown", profile.get_backstory_text())
        self.assertIn("backstory: unknown history", profile.generate_column2(self.cat))
        self.assertTrue(set(BACKSTORIES["backstory_categories"]).issubset(BACKSTORIES["backstory_display"]))

    def test_trait_tooltips_use_real_personality_ranges(self):
        from scripts.cat.personality import Personality

        self.screen.page = 3
        self.screen.current_selection = "trait"
        self.screen.open_customize_cat()
        for trait in self.screen.trait_options:
            text = self.screen.customizer_description(trait)
            for facet, bounds in Personality.trait_ranges["normal_traits"][trait].items():
                self.assertIn(f"{facet.capitalize()}: {bounds[0]}-{bounds[1]}", text)
        trait = self.screen.trait_options[-1]
        self.screen.elements["scroll_container"].scroll_to(trait)
        self.assertEqual(self.screen.trait_buttons[trait].tool_tip_text, self.screen.customizer_description(trait))

    def test_option_lists_wrap_and_open_at_the_current_value(self):
        cases = ((3, "trait", self.screen.trait_options[-1], "personality"),
                 (3, "skill", self.screen.skills[-1], "skill"),
                 (3, "condition", "partial hearing loss", "permanent_conditions"),
                 (4, "backstory", "ostracized_warrior", "backstory"),
                 (4, "secondary_skill", self.screen.skills[-1], "secondary_skill"))
        for page, selection, value, attribute in cases:
            with self.subTest(selection=selection):
                setattr(self.screen, attribute, [value] if attribute == "permanent_conditions" else value)
                self.screen.page = page
                self.screen.current_selection = selection
                self.screen.open_customize_cat()
                container = self.screen.elements["scroll_container" if page == 3 else "details"]
                for _ in range(3):
                    container.ui_manager.update(1 / 60)
                button, label = container.rows[value]
                self.assertEqual(label.html_text, value.replace("_", " ").capitalize())
                self.assertEqual(button.is_enabled, selection == "condition")
                self.assertEqual(button.object_ids[-1], "@checked_checkbox")
                viewport = container.get_container().get_relative_rect().y
                self.assertGreaterEqual(label.relative_rect.top + viewport, 0)
                self.assertLessEqual(label.relative_rect.bottom + viewport, container.rect.height)
                self.assertLessEqual(len(container.rows), 15)
                for option, (_, text) in container.rows.items():
                    index = container.options.index(option)
                    self.assertLessEqual(text.relative_rect.bottom, container.row_offsets[index + 1])
                if selection in ("condition", "backstory"):
                    self.assertGreater(len(label.text_box_layout.layout_rows), 1)
        container.scroll_to("None")
        self.press(self.screen.detail_buttons["None"])
        self.assertEqual(self.screen.secondary_skill, "None")
        self.press(self.screen.elements["undo_customize"])
        self.assertEqual(self.screen.secondary_skill, self.screen.skills[-1])
        self.assertIn(self.screen.secondary_skill, self.screen.elements["details"].rows)

    def test_tint_lists_scroll_with_wheel_over_empty_space(self):
        from scripts.screens.CatAppearanceEditor import CustomizerList
        from scripts.cat.sprites import sprites
        from scripts.game_structure import screen_settings

        old_offset = MANAGER.offset
        MANAGER.set_offset((0, 0))
        self.addCleanup(MANAGER.set_offset, old_offset)
        for tint_data in (sprites.cat_tints, sprites.white_patches_tints):
            for scale in (1, 1.5, 2):
                with patch.object(screen_settings, "screen_scale", scale):
                    listing = CustomizerList(pygame.Rect(10, 10, 260, 130),
                        list(dict.fromkeys(["none"] + list(tint_data["tint_colours"]))), str.capitalize, {})
                    try:
                        listing.update(.01)
                        bar = listing.vert_scroll_bar
                        self.assertEqual(bar.rect.width, 20)
                        self.assertGreaterEqual(bar.sliding_button.rect.height, int(28 * scale))
                        point = (listing.rect.right - bar.rect.width - 8, listing.rect.centery)
                        before = listing.get_container().relative_rect.y
                        with patch.object(MANAGER, "get_mouse_position", return_value=point):
                            MANAGER.process_events(pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=-1))
                            for _ in range(15):
                                MANAGER.update(.05)
                        self.assertLess(listing.get_container().relative_rect.y, before)
                        listing.scroll_to(listing.options[-1])
                        self.assertEqual(listing.get_container().relative_rect.y,
                            listing.rect.height - listing.row_offsets[-1], (scale, bar.is_enabled, bar.scroll_position, bar.scrollable_height, bar.sliding_button.rect.height))
                        listing.scroll_to(listing.options[0])
                        self.assertEqual(listing.get_container().relative_rect.y, 0)
                        MANAGER.update(.01)
                        thumb = bar.sliding_button
                        with patch.object(MANAGER, "get_mouse_position", return_value=thumb.rect.center):
                            MANAGER.update(.01)
                            MANAGER.process_events(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                button=1, pos=thumb.rect.center))
                            MANAGER.update(.01)
                        self.assertTrue(thumb.held)
                        target = (thumb.rect.centerx, bar.rect.bottom - bar.arrow_button_height - thumb.rect.height // 2)
                        with patch.object(MANAGER, "get_mouse_position", return_value=target):
                            for _ in range(5):
                                MANAGER.update(.05)
                            MANAGER.process_events(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=target))
                        self.assertLess(listing.get_container().relative_rect.y, 0)
                    finally:
                        listing.kill()

    def test_wrapped_lists_fit_fullscreen_scales_and_both_themes(self):
        import json
        from pathlib import Path
        from scripts.game_structure import screen_settings
        from scripts.ui.generate_screen_scale_json import _multiply_numbers

        base_theme = json.loads(Path("resources/theme/master_screen_scale.json").read_text())
        dark_theme = json.loads(Path("resources/theme/themes/dark.json").read_text())
        manager = screen_settings.MANAGER
        original_resolution = manager.window_resolution
        original_scale = screen_settings.screen_scale
        try:
            for scale in (1, 1.25, 1.5, 2):
                manager.set_window_resolution((int(800 * scale), int(700 * scale)))
                manager.get_theme().load_theme(_multiply_numbers(base_theme, scale))
                manager.get_theme().load_theme(dark_theme)
                for dark in (False, True):
                    with self.subTest(scale=scale, dark=dark), patch.object(
                        screen_settings, "screen_scale", scale
                    ), patch.dict(game.settings, {"dark mode": dark}):
                        self.screen.page = 3
                        self.screen.current_selection = "condition"
                        self.screen.permanent_conditions = ["persistent headaches"]
                        self.screen.open_customize_cat()
                        container = self.screen.elements["scroll_container"]
                        for _ in range(3):
                            manager.update(1 / 60)
                        text = container.rows["persistent headaches"][1]
                        self.assertGreater(len(text.text_box_layout.layout_rows), 1)
                        self.assertLessEqual(text.relative_rect.right, container.get_container().rect.width)
                        index = container.options.index("persistent headaches")
                        self.assertLessEqual(text.relative_rect.bottom, container.row_offsets[index + 1])
                        self.assertLessEqual(len(container.rows), 15)
        finally:
            manager.set_window_resolution(original_resolution)
            manager.get_theme().load_theme(_multiply_numbers(base_theme, original_scale))
            manager.get_theme().load_theme(dark_theme)

    def test_appearance_lists_open_at_selected_markings_and_tints(self):
        self.screen.page = 1
        self.screen.current_selection = "white_patches"
        self.screen.white_patches = ["FULLWHITE"]
        self.screen.white_patches_tint = "cream"
        self.screen.open_customize_cat()
        editor = self.screen.elements["appearance_editor"]
        self.assertIn("FULLWHITE", editor.option_list.rows)
        self.assertIn("cream", editor.elements["tint_list"].rows)
        self.assertEqual(editor.option_buttons["FULLWHITE"].object_ids[-1], "@checked_checkbox")
        self.assertTrue(editor.option_buttons["FULLWHITE"].is_enabled)
        self.press(editor.option_buttons["FULLWHITE"])
        self.assertEqual(self.screen.white_patches, [])

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

    def test_points_and_vitiligo_clicks_keep_the_live_option_list(self):
        self.screen.page = 1
        for selection in ("points", "vitiligo"):
            with self.subTest(selection=selection):
                self.screen.current_selection = selection
                self.screen.open_customize_cat()
                editor = self.screen.elements["appearance_editor"]
                for value in (editor.options[1], editor.options[-1], "None"):
                    self.option(value)
                    self.assertIs(self.screen.elements["appearance_editor"], editor)
                    self.assertEqual(getattr(self.screen, selection), None if value == "None" else value)
                self.press(self.screen.elements["undo_customize"])
                self.assertEqual(getattr(self.screen, selection), editor.options[-1])

    def test_in_game_editor_handles_every_creation_category_and_cycle_control(self):
        from copy import deepcopy
        from scripts.screens.CatAppearanceEditor import CatAppearanceEditor

        before = deepcopy(self.cat.get_save_dict())
        self.screen.page = 1
        self.screen.open_customize_cat()
        if not self.screen.tortie_enabled:
            self.press(self.screen.elements["tortie_checkbox"])
        for page, categories in CatAppearanceEditor.categories.items():
            self.screen.page = page
            self.screen.open_customize_cat()
            for category in categories:
                with self.subTest(page=page, category=category):
                    self.press(self.screen.current_selection_buttons[category])
                    editor = self.screen.elements["appearance_editor"]
                    for value in (editor.options[0], editor.options[-1]):
                        editor = self.screen.elements["appearance_editor"]
                        editor.option_list.scroll_to(value)
                        button = editor.option_buttons[value]
                        if button.is_enabled:
                            self.press(button)
                    for key in ("cycle_left", "cycle_right", "randomise_selection"):
                        self.press(self.screen.elements[key])
        for page, categories in ((3, ("condition", "trait", "skill")),
                                 (4, ("secondary_skill", "fur_texture", "build", "height", "backstory"))):
            self.screen.page = page
            self.screen.open_customize_cat()
            for category in categories:
                with self.subTest(page=page, category=category):
                    self.press(self.screen.current_selection_buttons[category])
                    container = self.screen.elements["scroll_container" if page == 3 else "details"]
                    value = container.options[-1]
                    container.scroll_to(value)
                    if container.buttons[value].is_enabled:
                        self.press(container.buttons[value])
                    for key in ("cycle_left", "cycle_right", "randomise_selection"):
                        self.press(self.screen.elements[key])
        self.assertEqual(self.cat.get_save_dict(), before)

    def test_accessory_search_sort_and_empty_results_keep_controls_valid(self):
        self.screen.page = 2
        self.screen.current_selection = "accessory"
        self.screen.open_customize_cat()
        self.screen.elements["search_bar"].set_text("yellowtie")
        self.press(self.screen.elements["search_button"])
        self.assertEqual(self.screen.accessory_options(), ["YELLOWTIE"])
        self.press(self.screen.elements["randomise_selection"])
        self.assertEqual(self.screen.accessories, ["YELLOWTIE"])
        self.screen.elements["search_bar"].set_text("no accessory matches this text")
        self.press(self.screen.elements["search_button"])
        self.assertEqual(self.screen.accessory_options(), [])
        self.assertFalse(self.screen.elements["randomise_selection"].is_enabled)
        before = self.screen.get_customizer_state()
        self.press(self.screen.elements["randomise_selection"])
        self.assertEqual(self.screen.get_customizer_state(), before)
        self.press(self.screen.elements["cycle_left"])
        self.assertEqual(self.screen.accessories, [])
        self.press(self.screen.elements["clear"])
        self.assertTrue(self.screen.elements["randomise_selection"].is_enabled)
        self.press(self.screen.elements["alphabetical"])
        editor = self.screen.elements["appearance_editor"]
        self.assertEqual(editor.option_list.options, sorted(editor.option_list.options,
                         key=lambda value: editor.display_name(value).lower()))

    def test_scar_checklist_has_no_slot_cap_and_preserves_other_scars(self):
        from scripts.cat.pelts import Pelt

        original = self.cat.get_save_dict()
        self.screen.page = 2
        self.screen.current_selection = "scar"
        self.screen.scars = []
        self.screen.open_customize_cat()
        scars = Pelt.scars1[:20]
        self.assertGreater(len(scars), 4)
        for scar in scars:
            self.option(scar)
        self.assertEqual(self.screen.scars, scars)
        self.option(scars[3])
        self.assertEqual(self.screen.scars, scars[:3] + scars[4:])
        self.press(self.screen.elements["undo_customize"])
        self.assertEqual(self.screen.scars, scars)
        self.press(self.screen.elements["redo_customize"])
        self.assertNotIn(scars[3], self.screen.scars)
        self.press(self.screen.elements["lock_condition"])
        locked = self.screen.get_customizer_state()
        self.press(self.screen.elements["random_customize"])
        self.assertEqual(self.screen.scars, locked["scars"])
        self.press(self.screen.elements["reset_customize"])
        self.assertEqual(self.screen.scars, self.screen.initial_customizer_state["scars"])
        self.press(self.screen.elements["previous_step"])
        self.assertEqual(self.cat.get_save_dict(), original)

    def test_condition_stack_retains_progress_and_round_trips_through_saved_conditions(self):
        from copy import deepcopy
        from pathlib import Path
        from tempfile import TemporaryDirectory

        self.cat.get_permanent_condition("allergies")
        self.cat.get_permanent_condition("weak leg")
        self.cat.permanent_condition["allergies"]["moons_with"] = 7
        retained = deepcopy(self.cat.permanent_condition["allergies"])
        self.cat.pelt.accessories = ["RED FEATHERS", "ASHY PAWS"]
        self.cat.pelt.scars = ["LEFTEAR"]
        self.screen.exit_screen()
        with patch.dict(game.switches, {"cat": self.cat.ID}):
            self.screen.screen_switches()
        self.assertEqual(self.screen.permanent_conditions, ["allergies", "weak leg"])
        self.screen.page = 3
        self.screen.current_selection = "condition"
        self.screen.open_customize_cat()
        for name in ("paralyzed", "born without a tail", "lost a leg", "weak leg"):
            self.screen.elements["scroll_container"].scroll_to(name)
            self.press(self.screen.condition_buttons[name])
        expected = ["allergies", "paralyzed", "born without a tail", "lost a leg"]
        self.assertEqual(self.screen.permanent_conditions, expected)
        self.assertEqual(set(self.screen.scars), {"LEFTEAR", "NOTAIL", "NOPAW"})
        self.assertEqual(self.screen.accessories, [])
        self.assertEqual(self.cat.permanent_condition["allergies"], retained)
        self.assertNotIn("paralyzed", self.cat.permanent_condition)
        self.press(self.screen.elements["undo_customize"])
        self.assertIn("weak leg", self.screen.permanent_conditions)
        self.press(self.screen.elements["redo_customize"])
        self.assertEqual(self.screen.permanent_conditions, expected)
        self.press(self.screen.elements["next_step"])
        self.assertEqual(list(self.cat.permanent_condition), expected)
        self.assertEqual(self.cat.permanent_condition["allergies"], retained)
        acquired = [event["condition"] for event in self.cat.history.condition_events]
        self.assertEqual(acquired.count("allergies"), 1)
        self.assertIn("paralyzed", acquired)
        with TemporaryDirectory() as directory, patch("scripts.cat.cats.get_save_dir", return_value=directory), patch.dict(
            game.switches, {"clan_name": game.clan.name, "clan_list": [game.clan.name]}
        ):
            (Path(directory) / game.clan.name / "conditions").mkdir(parents=True)
            self.cat.save_condition()
            loaded = Cat(ID=self.cat.ID, moons=self.cat.moons, pelt=deepcopy(self.cat.pelt),
                         gender=self.cat.gender, loading_cat=True, register=False)
            loaded.load_conditions()
            self.assertEqual(loaded.permanent_condition, self.cat.permanent_condition)
            self.assertEqual(loaded.get_save_dict()["scars"], self.cat.pelt.scars)
            self.assertTrue(loaded.pelt.paralyzed)

    def test_removing_one_linked_scar_keeps_other_scars_and_conditions(self):
        self.screen.set_customizer_scars([])
        self.screen.set_customizer_conditions(["paralyzed", "allergies", "born without a tail", "born without a leg"])
        self.screen.scars.append("LEFTEAR")
        self.screen.page = 2
        self.screen.current_selection = "scar"
        self.screen.open_customize_cat()
        self.option("NOTAIL")
        self.assertEqual(set(self.screen.scars), {"NOPAW", "LEFTEAR"})
        self.assertEqual(self.screen.permanent_conditions, ["paralyzed", "allergies", "born without a leg"])
        self.assertTrue(self.screen.paralyzed)
        self.press(self.screen.elements["undo_customize"])
        self.assertIn("NOTAIL", self.screen.scars)
        self.assertIn("born without a tail", self.screen.permanent_conditions)
        self.option("BOTHBLIND")
        self.assertIn("NOPAW", self.screen.scars)
        self.assertIn("blind", self.screen.permanent_conditions)
        self.assertIn("paralyzed", self.screen.permanent_conditions)
        self.assertTrue(self.screen.paralyzed)

    def test_condition_stack_locks_randomization_and_invalid_choices(self):
        self.screen.sex = "intersex"
        self.screen.set_customizer_conditions(["mosaicism", "allergies", "weak leg"])
        self.screen.page = 3
        self.screen.current_selection = "condition"
        self.screen.open_customize_cat()
        self.press(self.screen.elements["lock_condition"])
        locked = self.screen.get_customizer_state()
        self.press(self.screen.elements["random_customize"])
        self.assertEqual(self.screen.permanent_conditions, locked["permanent_conditions"])
        self.assertEqual(self.screen.sex, "intersex")
        self.press(self.screen.elements["lock_condition"])
        self.screen.sex = "female"
        self.screen.update_disabled_buttons()
        self.assertFalse(self.screen.elements["next_step"].is_enabled)
        self.screen.elements["scroll_container"].scroll_to("mosaicism")
        self.press(self.screen.condition_buttons["mosaicism"])
        self.assertEqual(self.screen.permanent_conditions, ["allergies", "weak leg"])
        self.assertTrue(self.screen.elements["next_step"].is_enabled)
        with patch("scripts.screens.CatCustomizer.random.choice", return_value="None"):
            self.press(self.screen.elements["randomise_selection"])
        self.assertEqual(self.screen.permanent_conditions, ["weak leg"])
        self.press(self.screen.elements["undo_customize"])
        self.assertEqual(self.screen.permanent_conditions, ["allergies", "weak leg"])
        self.screen.set_customizer_conditions(["blind"])
        self.screen.elements["scroll_container"].scroll_to("failing eyesight")
        self.screen.update_disabled_buttons()
        self.assertFalse(self.screen.condition_buttons["failing eyesight"].is_enabled)
        self.screen.elements["scroll_container"].scroll_to("blind")
        self.press(self.screen.condition_buttons["blind"])
        self.assertEqual(self.screen.permanent_conditions, [])
        self.assertTrue(self.screen.condition_buttons["failing eyesight"].is_enabled)
        self.screen.set_customizer_conditions(["blind", "failing eyesight", "deaf", "partial hearing loss"])
        self.screen.open_customize_cat()
        self.screen.elements["scroll_container"].scroll_to("None")
        self.assertTrue(self.screen.condition_buttons["None"].is_enabled)
        self.press(self.screen.condition_buttons["None"])
        self.assertEqual(self.screen.permanent_conditions, [])
        self.assertTrue(self.screen.elements["next_step"].is_enabled)

    def test_apply_updates_skills_conditions_and_details_without_changing_identity(self):
        identity = (self.cat.ID, self.cat.moons, self.cat.status)
        points = self.cat.skills.primary.points
        self.screen.page = 3
        self.screen.current_selection = "condition"
        self.screen.open_customize_cat()
        self.screen.elements["scroll_container"].scroll_to("paralyzed")
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
        self.screen.permanent_conditions = ["excess testosterone"]
        self.screen.page = 3
        self.screen.current_selection = "condition"
        self.screen.open_customize_cat()
        self.assertFalse(self.screen.elements["next_step"].is_enabled)
        self.assertTrue(self.screen.condition_buttons["excess testosterone"].is_enabled)
        self.press(self.screen.elements["next_step"])
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

    def test_creation_mode_controls_and_keyboard_path_preserve_selection(self):
        from scripts.screens.MakeClanScreen import MakeClanScreen

        screen = MakeClanScreen()
        screen.tutorial_shown = True
        with patch.object(game, "clan", None), patch.object(game, "choose_cats", {}), patch.dict(
            game.switches, {"customise_new_life": False, "clan_list": []}
        ), patch("scripts.utility.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA)):
            screen.screen_switches()
            try:
                self.assertEqual(screen.sub_screen, "game settings")
                self.assertEqual(screen.game_mode, "expanded")
                self.assertFalse(screen.elements["mode_expanded"].is_enabled)
                screen.handle_game_settings_event(pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["mode_classic"]
                ))
                screen.handle_game_settings_event(pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["next_step"]
                ))
                self.assertEqual(screen.sub_screen, "name clan")
                screen.elements["name_entry"].set_text("ModeDemo")
                screen.handle_name_clan_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
                self.assertEqual(screen.sub_screen, "game settings")
                self.assertEqual(screen.game_mode, "classic")
                self.assertFalse(screen.elements["mode_classic"].is_enabled)
                screen.handle_game_settings_event(pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["next_step"]
                ))
                self.assertEqual(screen.elements["name_entry"].get_text(), "ModeDemo")
                screen.handle_name_clan_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
                self.assertEqual(screen.sub_screen, "choose leader")
                self.assertEqual(game.clan.name, "ModeDemo")
                self.assertEqual(game.clan.game_mode, "classic")
            finally:
                screen.exit_screen()

    def test_customize_uses_selected_kit_without_changing_its_pelt(self):
        from copy import deepcopy
        from scripts.screens.MakeClanScreen import MakeClanScreen

        screen = MakeClanScreen()
        screen.tutorial_shown = True
        with patch.object(game, "clan", None), patch.object(game, "choose_cats", {}), patch.dict(
            game.switches, {"customise_new_life": False}
        ), patch("scripts.screens.CatCustomizer.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA)), patch(
            "scripts.utility.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA)
        ):
            screen.screen_switches()
            try:
                screen.handle_game_settings_event(pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["next_step"]
                ))
                screen.elements["name_entry"].set_text("KitEditorTest")
                screen.handle_name_clan_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
                selected = game.choose_cats[0]
                selected.pelt.name = "Tabby"
                selected.pelt.colour = "BLACK"
                selected.pelt.white_patches = ["BLAZE", "TAILTIP"]
                selected.pelt.pattern = []
                selected.pelt.reverse = True
                selected.gender = "female"
                before = deepcopy(vars(selected.pelt))
                screen.open_choose_leader()
                screen.handle_choose_leader_event(pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["cat0"]
                ))
                screen.handle_choose_leader_event(pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["customize"]
                ))
                self.assertEqual((screen.pname, screen.colour, screen.sex), ("Tabby", "BLACK", "female"))
                self.assertEqual(screen.white_patches, ["BLAZE", "TAILTIP"])
                self.assertTrue(screen.reverse)
                self.assertEqual(screen.backstory, "Random")
                self.assertFalse(screen.customizer_undo)
                screen.white_patches.append("VEE")
                self.assertEqual(vars(selected.pelt), before)
                with patch.object(screen, "open_name_cat"):
                    screen.finish_customize_cat()
                self.assertEqual(screen.your_cat.pelt.name, "Tabby")
                self.assertEqual(screen.your_cat.pelt.colour, "BLACK")
                self.assertEqual(vars(selected.pelt), before)
            finally:
                screen.exit_screen()

    def test_creation_confirms_multiple_scars_and_conditions(self):
        from scripts.screens.MakeClanScreen import MakeClanScreen
        screen = MakeClanScreen()
        screen.tutorial_shown = True
        with patch.object(game, "clan", None), patch.object(game, "choose_cats", {}), patch.dict(
            game.switches, {"customise_new_life": False}
        ), patch("scripts.screens.CatCustomizer.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA)), patch(
            "scripts.utility.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA)
        ):
            screen.screen_switches()
            try:
                screen.page = 2
                screen.current_selection = "scar"
                screen.open_customize_cat()
                for scar in ("LEFTEAR", "NOPAW", "NOTAIL"):
                    editor = screen.elements["appearance_editor"]
                    editor.option_list.scroll_to(scar)
                    screen.handle_customize_cat_event(pygame.event.Event(
                        pygame_gui.UI_BUTTON_START_PRESS, ui_element=editor.option_buttons[scar]
                    ))
                screen.page = 3
                screen.current_selection = "condition"
                screen.open_customize_cat()
                for name in ("paralyzed", "allergies"):
                    screen.elements["scroll_container"].scroll_to(name)
                    screen.handle_customize_cat_event(pygame.event.Event(
                        pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.condition_buttons[name]
                    ))
                from scripts.cat.personality import Personality
                from random import randint
                self.assertEqual(screen.backstory, "Random")
                screen.current_selection = "backstory"
                self.assertIn("Start as a newborn", screen.customizer_description("Random"))
                self.assertNotIn("kittypet3", screen.details_options["backstory"])
                self.assertNotIn("retired_leader", screen.details_options["backstory"])
                self.assertIn("orphaned7", screen.details_options["backstory"])
                screen.backstory = "abandoned4"
                screen.personality = list(Personality.trait_ranges["kit_traits"])[-1]
                chosen_trait = screen.personality
                self.assertEqual(set(screen.trait_options), set(Personality.trait_ranges["kit_traits"]))
                with patch.object(screen, "open_name_cat") as naming, patch(
                    "scripts.cat.cats.randint", side_effect=lambda low, high: 1 if (low, high) == (1, 25) else randint(low, high)
                ):
                    screen.handle_customize_cat_event(pygame.event.Event(
                        pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["next_step"]
                    ))
                naming.assert_called_once()
                self.assertEqual(screen.your_cat.backstory, "abandoned4")
                self.assertEqual(screen.your_cat.personality.trait, chosen_trait)
                self.assertEqual(screen.your_cat.gender, screen.sex)
                self.assertEqual(set(screen.your_cat.permanent_condition),
                                 {"born without a leg", "born without a tail", "paralyzed", "allergies"})
                self.assertEqual(screen.your_cat.pelt.scars, ["LEFTEAR", "NOPAW", "NOTAIL"])
                self.assertTrue(screen.your_cat.pelt.paralyzed)
                for condition in screen.your_cat.permanent_condition.values():
                    self.assertTrue(condition["born_with"])
                    self.assertEqual(condition["moons_until"], 1)
            finally:
                screen.exit_screen()

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
                screen.permanent_conditions = []
                screen.paralyzed = False
                screen.scars = []
                screen.accessories = [screen.notail_accs[0]]
                screen.inventory = screen.accessories.copy()
                saved = screen.get_customizer_state()
                screen.permanent_conditions = ["born without a tail"]
                screen.scars = ["NOTAIL"]
                screen.accessories = []
                screen.inventory = []
                screen.apply_customizer_locks(saved)
                self.assertEqual(screen.accessories, saved["accessories"])
                self.assertEqual(screen.permanent_conditions, [])
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


class TestCampLighting(unittest.TestCase):
    def setUp(self):
        from scripts.screens.ClanScreen import ClanScreen

        self.clan = Clan(name="CampTest", biome="Forest", camp_bg="camp1")
        self.clan.clan_cats = []
        for target, attribute, value in (
            (Cat, "all_cats", {}), (Cat, "all_cats_list", []),
            (game, "clan", self.clan), (game, "all_screens", {}),
        ):
            replacement = patch.object(target, attribute, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        replacement = patch("scripts.utility.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA))
        replacement.start()
        self.addCleanup(replacement.stop)
        cat = Cat(status="warrior", moons=30, gender="female")
        self.clan.your_cat = cat
        self.clan.clan_cats = [cat.ID]
        self.screen = ClanScreen("camp screen")

    def test_random_lighting_is_independent_of_interface_and_reshuffles_each_visit(self):
        import random
        from scripts.screens.Screens import Screens

        original_choice = random.choice
        themes = iter(("dark", "light"))
        def choose(values):
            return next(themes) if values == ("light", "dark") else original_choice(values)
        with patch.dict(game.settings, {"dark mode": False, "random camp lighting": True}), patch(
            "scripts.screens.ClanScreen.random.choice", side_effect=choose
        ), patch.object(self.screen, "choose_cat_positions", wraps=self.screen.choose_cat_positions) as positions:
            self.screen.screen_switches()
            self.assertEqual(self.screen.camp_theme, "dark")
            self.assertEqual(self.screen.theme, "light")
            self.assertFalse(game.settings["dark mode"])
            with patch.object(Screens, "show_bg") as show:
                self.screen.show_bg()
                show.assert_called_once_with("dark")
            saved = self.screen.display_change_save()
            self.screen.camp_theme = "light"
            self.screen.display_change_load(saved)
            self.assertEqual(self.screen.camp_theme, "dark")
            self.screen.exit_screen()
            self.screen.screen_switches()
            try:
                self.assertEqual(self.screen.camp_theme, "light")
                self.assertEqual(positions.call_count, 2)
            finally:
                self.screen.exit_screen()

    def test_returning_to_camp_replaces_a_manually_moved_position(self):
        cat = self.clan.your_cat
        with patch.object(self.screen, "choose_nonoverlapping_positions", side_effect=[(100, 150), (250, 300)]):
            self.screen.screen_switches()
            self.assertEqual(cat.placement, (100, 150))
            cat.placement = (400, 450)
            self.screen.exit_screen()
            self.screen.screen_switches()
            try:
                self.assertEqual(cat.placement, (250, 300))
            finally:
                self.screen.exit_screen()

    def test_default_lighting_and_disabled_backgrounds_follow_interface(self):
        from scripts.screens.Screens import Screens

        with patch.dict(game.settings, {"dark mode": True, "random camp lighting": False}):
            self.screen.screen_switches()
            try:
                self.assertEqual(self.screen.camp_theme, "dark")
                self.clan.clan_settings["backgrounds"] = False
                with patch.object(Screens, "show_bg") as show:
                    self.screen.show_bg()
                    show.assert_called_once_with(None)
            finally:
                self.screen.exit_screen()

    def test_bridge_and_quay_render_all_seasons_and_use_their_own_positions(self):
        from scripts.debug_commands.territory import CAMP_AVAILABILITY
        from scripts.screens.MakeClanScreen import MakeClanScreen

        for biome, camp in (("Plains", "camp10"), ("Beach", "camp6")):
            with self.subTest(biome=biome):
                self.assertEqual(len(CAMP_AVAILABILITY[biome]), MakeClanScreen.camp_counts[biome])
                self.clan.biome, self.clan.camp_bg = biome, camp
                for dark in (False, True):
                    with patch.dict(game.settings, {"dark mode": dark, "random camp lighting": False}):
                        self.screen.screen_switches()
                        try:
                            self.assertIs(self.screen.layout, self.clan.layouts[biome + camp])
                            self.assertTrue(self.screen.cat_buttons)
                            x, y = self.clan.your_cat.placement
                            self.assertTrue(0 <= x <= 750 and 0 <= y <= 650)
                            for season in ("Newleaf", "Greenleaf", "Leaf-fall", "Leaf-bare"):
                                self.clan.current_season = season
                                self.screen.show_bg()
                            self.assertEqual(self.screen.leader_den_label.relative_rect.topleft,
                                             ui_scale(pygame.Rect(self.screen.layout["leader den"], (112, 28))).topleft)
                        finally:
                            self.screen.exit_screen()


class TestRecoveryVisits(unittest.TestCase):
    def setUp(self):
        from scripts.cat.history import History
        from scripts.events_module.patrol.patrol import Patrol
        from scripts.screens.PatrolScreen import PatrolScreen

        self.clan = Clan(name="VisitTest", biome="Forest", camp_bg="camp1", game_mode="expanded")
        self.clan.clan_cats = []
        self.clan.all_clans = []
        for target, attribute, value in (
            (Cat, "all_cats", {}), (Cat, "all_cats_list", []),
            (game, "clan", self.clan), (game, "all_screens", {}),
            (game, "switches", dict(game.switches, patrolled=[])),
            (game, "patrolled", []), (game, "dated_cats", []),
            (Patrol, "used_patrols", []),
        ):
            replacement = patch.object(target, attribute, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        replacement = patch("scripts.utility.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA))
        replacement.start()
        self.addCleanup(replacement.stop)
        self.you = Cat(status="warrior", moons=30, gender="female")
        self.companion = Cat(status="warrior", moons=30, gender="female")
        for cat in (self.you, self.companion):
            cat.history = History()
            self.clan.add_cat(cat)
            cat.create_inheritance_new_cat()
            cat.injuries.clear()
            cat.illnesses.clear()
        self.clan.your_cat = self.you
        self.you.create_relationships_new_cat()
        self.companion.create_relationships_new_cat()
        self.screen = PatrolScreen()

    def test_native_picker_allows_recovery_visits_but_not_working_patrols(self):
        self.you.injuries = {"broken bone": {"severity": "major"}}
        self.companion.injuries = {"sprain": {"severity": "major"}}
        self.screen.screen_switches()
        try:
            self.assertTrue(self.screen.elements["date_icon"].is_enabled)
            self.assertNotIn(self.you, self.screen.able_cats)
            self.assertNotIn(self.companion, self.screen.able_cats)
            self.screen.handle_event(pygame.event.Event(
                pygame_gui.UI_BUTTON_START_PRESS, ui_element=self.screen.elements["date_icon"]
            ))
            self.assertIn(self.you, self.screen.current_patrol)
            self.assertIn(self.companion, self.screen.able_cats)
            self.companion.no_mates = True
            self.screen.update_cat_images_buttons()
            self.assertIn(self.companion, self.screen.able_cats)
            self.screen.selected_cat = self.companion
            self.screen.update_button()
            self.screen.handle_event(pygame.event.Event(
                pygame_gui.UI_BUTTON_START_PRESS, ui_element=self.screen.elements["add_remove_cat"]
            ))
            self.assertTrue(self.screen.elements["patrol_start"].is_enabled)
            self.screen.run_patrol_start()
            self.assertEqual(game.switches["patrol_category"], "outing")
            self.assertIn("recovery_den", self.screen.patrol_obj.patrol_event.patrol_id)
            self.screen.open_patrol_event_screen()
            self.assertEqual(self.screen.patrol_stage, "patrol_events")
            self.screen.patrol_obj.proceed_patrol("decline")
            self.screen.open_choose_cats_screen()
            self.screen.handle_event(pygame.event.Event(
                pygame_gui.UI_BUTTON_START_PRESS, ui_element=self.screen.elements["date_icon"]
            ))
            self.assertEqual(self.screen.current_patrol, [])
            self.assertEqual(self.screen.able_cats, [])
        finally:
            self.screen.exit_screen()

    def test_recovery_events_complete_for_either_patient_and_both_social_categories(self):
        from scripts.events_module.patrol.patrol import Patrol

        for category in ("date", "outing"):
            self.companion.no_mates = category == "outing"
            for patient in (self.you, self.companion):
                for condition, in_den in (("broken bone", True), ("sprain", False)):
                    for success in (True, False):
                        with self.subTest(category=category, patient=patient.ID, condition=condition, success=success):
                            self.you.injuries.clear()
                            self.companion.injuries.clear()
                            patient.injuries[condition] = {"severity": "major"}
                            game.switches.update(patrol_category=category, patrolled=[])
                            game.patrolled.clear()
                            game.dated_cats.clear()
                            patrol = Patrol()
                            intro = patrol.setup_patrol([self.you, self.companion], "general", category)
                            self.assertIn("recovery_den" if in_den else "recovery_camp", patrol.patrol_event.patrol_id)
                            self.assertIn(str(self.companion.name), intro)
                            self.assertNotIn("Mrrp", intro)
                            before = self.you.relationships[self.companion.ID].platonic_like
                            with patch.object(patrol, "calculate_success", side_effect=lambda yes, no: (yes if success else no, success)):
                                text, results, art = patrol.proceed_patrol()
                            self.assertIn(str(self.companion.name), text)
                            self.assertNotIn("r_c", text)
                            self.assertNotIn("Mrrp", text)
                            if category == "outing" and success:
                                self.assertGreater(self.you.relationships[self.companion.ID].platonic_like, before)
                            self.assertEqual(patient.injuries[condition]["severity"], "major")
                            self.assertEqual(game.patrolled, [] if category == "date" else [self.you.ID, self.companion.ID])
                            self.assertIn("4" if category == "date" else "5", game.switches["patrolled"])

    def test_healthy_cats_do_not_receive_recovery_events_and_excluded_cats_stay_excluded(self):
        from scripts.events_module.patrol.patrol import Patrol

        for category in ("date", "outing"):
            game.switches.update(patrol_category=category, patrolled=[])
            patrol = Patrol()
            patrol.setup_patrol([self.you, self.companion], "general", category)
            self.assertNotIn("recovery", patrol.patrol_event.patrol_id)
        self.companion.no_mates = True
        self.assertTrue(self.companion.is_friendlyable(self.you))
        for field in ("dead", "outside"):
            with patch.object(self.companion, field, True):
                self.assertFalse(self.companion.is_friendlyable(self.you))
                self.assertFalse(self.companion.is_dateable(self.you))
        kitten = Cat(status="kitten", moons=3)
        self.assertFalse(kitten.is_friendlyable(self.you))
        self.assertFalse(self.you.is_friendlyable(kitten))

    def test_illness_mixed_conditions_shunning_and_group_visits(self):
        from scripts.events_module.patrol.patrol import Patrol

        guest = Cat(status="warrior", moons=32, gender="female")
        guest.create_inheritance_new_cat()
        cases = (
            ({}, {"greencough": {"severity": "major"}}, True),
            ({}, {"grief stricken": {"severity": "major"}}, False),
            ({"sprain": {"severity": "major"}, "broken bone": {"severity": "major"}}, {}, True),
            ({"scrapes": {"severity": "minor"}}, {}, None),
        )
        for category in ("date", "outing"):
            for shunned in (0, 2):
                for injuries, illnesses, in_den in cases:
                    with self.subTest(category=category, shunned=shunned, in_den=in_den):
                        self.you.shunned = shunned
                        self.you.injuries = injuries.copy()
                        self.you.illnesses = illnesses.copy()
                        game.switches.update(patrol_category=category, patrolled=[])
                        patrol = Patrol()
                        cats = [self.you, self.companion, guest] if in_den is not None else [self.you, self.companion]
                        intro = patrol.setup_patrol(cats, "general", category)
                        if in_den is not None:
                            self.assertIn("recovery_den" if in_den else "recovery_camp", patrol.patrol_event.patrol_id)
                        else:
                            self.assertNotIn("recovery", patrol.patrol_event.patrol_id)
                        self.assertNotIn("Mrrp", intro)
                        self.assertNotIn("r_c", intro)

    def test_patrol_text_only_requires_a_neighbor_when_it_mentions_one(self):
        from scripts.events_module.patrol.patrol import Patrol

        game.switches["patrol_category"] = "clangen"
        patrol = Patrol()
        patrol.add_patrol_cats([self.you, self.companion], self.clan)
        self.assertIsNone(patrol.other_clan)
        self.assertEqual(patrol.process_text("p_l returns to camp.", None), f"{patrol.patrol_leader.name} returns to camp.")
        patrol.other_clan = OtherClan(name="Oak", chosen_symbol="symbolTEST")
        self.assertIn("Oak", patrol.process_text("p_l meets a o_c_n patrol.", None))

    def test_medicine_den_tabs_agree_with_visit_locations_regardless_of_condition_order(self):
        from scripts.screens.MedDenScreen import MedDenScreen

        for first, second in (("sprain", "broken bone"), ("broken bone", "sprain"),
                              ("scrapes", "broken bone"), ("broken bone", "scrapes")):
            with self.subTest(first=first, second=second):
                self.you.injuries = {
                    name: {"severity": "minor" if name == "scrapes" else "major"}
                    for name in (first, second)
                }
                self.companion.injuries = {"sprain": {"severity": "major"}}
                screen = MedDenScreen()
                screen.screen_switches()
                try:
                    self.assertTrue(self.you.in_medicine_den())
                    self.assertIn(self.you, screen.in_den_cats)
                    self.assertNotIn(self.you, screen.out_den_cats)
                    self.assertNotIn(self.you, screen.minor_cats)
                    self.assertFalse(self.companion.in_medicine_den())
                    self.assertIn(self.companion, screen.out_den_cats)
                    self.assertNotIn(self.companion, screen.in_den_cats)
                finally:
                    screen.exit_screen()


class TestFeedingControls(unittest.TestCase):
    def setUp(self):
        from scripts.screens.ClearingScreen import ClearingScreen

        self.clan = Clan(name="FeedingControls", biome="Forest", camp_bg="camp1", game_mode="expanded")
        self.clan.clan_cats = []
        for target, attribute, value in (
            (Cat, "all_cats", {}), (Cat, "all_cats_list", []),
            (game, "clan", self.clan), (game, "all_screens", {}),
        ):
            replacement = patch.object(target, attribute, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        replacement = patch("scripts.utility.generate_sprite", return_value=pygame.Surface((50, 50), pygame.SRCALPHA))
        replacement.start()
        self.addCleanup(replacement.stop)
        cat = Cat(status="warrior", moons=30, gender="female")
        self.clan.add_cat(cat)
        self.clan.your_cat = cat
        self.clan.freshkill_pile.update_nutrition([cat])
        self.screen = ClearingScreen()
        self.screen.screen_switches()
        self.addCleanup(self.screen.exit_screen)
        self.press(self.screen.tactic_tab)

    def press(self, button):
        self.screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))

    def test_pregnant_and_nursing_priority_is_distinct_from_the_queen_role(self):
        nursing = self.screen.additional_text["queen/pregnant"]
        queen = self.screen.additional_text["queen"]
        self.assertIn("Pregnant / nursing", nursing.html_text)
        self.assertNotIn("queen", nursing.html_text)
        self.assertIn("queen", queen.html_text)
        self.assertIn("regardless of their role", nursing.tool_tip_text)
        self.assertIn("not pregnant or nursing", queen.tool_tip_text)
        order = self.clan.freshkill_pile.get_status_order()
        self.assertEqual(order.count("queen/pregnant"), 1)
        self.assertEqual(order.count("queen"), 1)

    def test_native_multi_selection_reorder_rank_order_and_ration_independence(self):
        pile = self.clan.freshkill_pile
        self.assertEqual(pile.get_feeding_priorities(), ["by-status"])
        self.press(self.screen.tactic_boxes["sick/injured first"])
        self.press(self.screen.tactic_boxes["hunter first"])
        self.press(self.screen.tactic_boxes["by-status"])
        self.assertEqual(pile.get_feeding_priorities(), ["sick/injured first", "hunter first"])
        self.press(self.screen.tactic_moves["hunter first", -1])
        self.assertEqual(pile.get_feeding_priorities(), ["hunter first", "sick/injured first"])
        self.assertTrue(self.clan.clan_settings["hunter first"])
        self.assertFalse(self.clan.clan_settings["sick/injured first"])
        self.assertFalse(self.screen.tactic_moves["hunter first", -1].is_enabled)
        self.assertFalse(self.screen.tactic_moves["sick/injured first", 1].is_enabled)
        self.press(self.screen.tactic_boxes["sick/injured first"])
        self.assertFalse(self.screen.tactic_boxes["hunter first"].is_enabled)
        before = pile.get_status_order().copy()
        self.press(self.screen.status_moves[before[1], -1])
        self.assertEqual(pile.get_status_order()[:2], [before[1], before[0]])
        self.assertEqual(set(pile.get_status_order()), set(before))
        self.assertEqual(len(pile.get_status_order()), len(before))
        self.assertFalse(self.screen.status_moves[before[1], -1].is_enabled)
        self.press(self.screen.checkboxes["ration prey"])
        self.assertTrue(self.clan.clan_settings["ration prey"])
        self.assertEqual(pile.get_feeding_priorities(), ["hunter first"])
        self.press(self.screen.cats_tab)
        self.press(self.screen.tactic_tab)
        self.assertEqual(pile.get_status_order()[:2], [before[1], before[0]])
        self.assertIn("1. hunter first", self.screen.tactic_text["hunter first"].html_text)

    def test_survival_card_locks_native_controls_without_overwriting_custom_tactics(self):
        self.clan.game_mode = "cruel season"
        self.clan.cruel_cards = ["survival_of_fittest"]
        self.clan.clan_settings["feeding priorities"] = ["younger first"]
        original_order = self.clan.freshkill_pile.get_status_order().copy()
        self.screen.create_checkboxes()
        buttons = [self.screen.default_tactics_button, *self.screen.tactic_boxes.values(),
                   *self.screen.tactic_moves.values(), *self.screen.status_moves.values()]
        self.assertTrue(all(not button.is_enabled for button in buttons))
        for button in buttons:
            self.press(button)
        self.assertEqual(self.clan.clan_settings["feeding priorities"], ["younger first"])
        self.assertEqual(self.clan.freshkill_pile.get_status_order(), original_order)
        self.press(self.screen.checkboxes["ration prey"])
        self.assertTrue(self.clan.clan_settings["ration prey"])
        self.press(self.screen.cats_tab)
        cat = self.clan.your_cat
        self.clan.freshkill_pile.nutrition_info[cat.ID].current_score = 0
        self.screen.update_cats_list()
        self.screen.focus_cat_object = cat
        self.screen.update_focus_cat()
        self.assertFalse(self.screen.feed_one_button.is_enabled)
        self.assertFalse(self.screen.feed_max_button.is_enabled)
        before = self.clan.freshkill_pile.total_amount
        for button in (self.screen.feed_one_button, self.screen.feed_max_button, self.screen.feed_all_button):
            self.press(button)
        self.assertEqual(self.clan.freshkill_pile.total_amount, before)
        self.clan.cruel_cards = []
        self.screen.create_checkboxes()
        self.screen.update_focus_cat()
        self.assertTrue(self.screen.default_tactics_button.is_enabled)
        self.assertTrue(self.screen.feed_one_button.is_enabled)
        self.assertEqual(self.clan.freshkill_pile.get_feeding_priorities(), ["younger first"])

    def test_default_restores_rules_status_order_and_rationing(self):
        self.press(self.screen.tactic_boxes["hunter first"])
        self.press(self.screen.status_moves["leader", -1])
        self.press(self.screen.checkboxes["ration prey"])
        self.press(self.screen.default_tactics_button)
        self.assertEqual(self.clan.clan_settings["feeding priorities"], [])
        self.assertEqual(self.clan.freshkill_pile.get_feeding_priorities(), ["by-status"])
        self.assertEqual(self.clan.freshkill_pile.get_status_order(), game.prey_config["feeding_order"])
        self.assertIsNot(self.clan.freshkill_pile.get_status_order(), game.prey_config["feeding_order"])
        self.assertFalse(self.clan.clan_settings["ration prey"])
        self.assertFalse(self.clan.clan_settings["hunter first"])
        self.assertTrue(self.screen.default_tactics_button.visible)
        self.assertTrue(self.screen.cat_bg.rect.contains(self.screen.default_tactics_button.rect))
        self.assertEqual(self.screen.default_tactics_button.rect.centerx, self.screen.cat_bg.rect.centerx)
        self.assertLessEqual(self.screen.default_tactics_button.rect.bottom, self.screen.tactic_text["container_general"].rect.top)
        self.press(self.screen.cats_tab)
        self.assertFalse(self.screen.default_tactics_button.visible)

    def test_setting_explanations_open_on_hover_before_and_after_ration_toggle(self):
        from scripts.screens.ClearingScreen import settings_dict

        expected = settings_dict["freshkill_tactics"]["ration prey"][1]
        for checked in (False, True):
            self.clan.clan_settings["ration prey"] = checked
            self.screen.create_checkboxes()
            widgets = (
                (self.screen.checkboxes["ration prey"], expected),
                (self.screen.additional_text["ration prey"], expected),
                (self.screen.tactic_text["by-status"], settings_dict["freshkill_tactics"]["by-status"][1]),
            )
            for widget, description in widgets:
                with self.subTest(checked=checked, widget=type(widget).__name__), patch.object(
                    MANAGER, "_update_mouse_position"
                ), patch.object(MANAGER, "mouse_position", widget.rect.center):
                    for _ in range(4):
                        MANAGER.update(0.6)
                    self.assertIsNotNone(widget.tool_tip, (checked, type(widget).__name__, widget.hovered, widget.tool_tip_text))
                    self.assertTrue(widget.tool_tip.visible)
                    self.assertEqual(widget.tool_tip.text_block.html_text, description)
                with patch.object(MANAGER, "_update_mouse_position"), patch.object(MANAGER, "mouse_position", (0, 0)):
                    MANAGER.update(0.1)

    def test_all_rules_are_visible_and_status_scroll_survives_rebuilding_controls(self):
        container = self.screen.tactic_text["container_general"]
        for mode in self.screen.tactic_boxes:
            label = self.screen.tactic_text[mode]
            self.assertLessEqual(label.relative_rect.bottom, container.rect.height)
        bar = self.screen.additional_text["container_general"].vert_scroll_bar
        bar.set_scroll_from_start_percentage(0.25)
        self.screen.create_checkboxes()
        self.assertAlmostEqual(self.screen.additional_text["container_general"].vert_scroll_bar.start_percentage, 0.25, places=2)
        self.assertTrue(self.screen.additional_text["heading"].visible)
        self.assertTrue(self.screen.checkboxes["ration prey"].visible)

    def test_tactics_keeps_the_clearing_pile_and_tabs_and_restores_the_other_views(self):
        self.assertTrue(self.screen.pile_base.visible)
        self.assertTrue(self.screen.info_messages.visible)
        self.assertEqual(self.screen.pile_base.normal_image.get_size(), self.screen.pile_base.rect.size)
        self.assertEqual(self.screen.tactic_title.rect.centerx, self.screen.cat_bg.rect.centerx)
        self.assertLessEqual(self.screen.tactic_title.rect.bottom, self.screen.cat_bg.rect.top)
        self.assertFalse(self.screen.feed_all_button.visible)
        self.assertEqual(self.screen.cat_bg.relative_rect, ui_scale(pygame.Rect((140, 345), (560, 325))))
        positions = [button.relative_rect.topleft for button in (self.screen.cats_tab, self.screen.log_tab, self.screen.tactic_tab)]
        for button in (self.screen.cats_tab, self.screen.log_tab, self.screen.tactic_tab):
            self.assertLess(abs(button.text_layer.rect.centery - button.rect.centery), ui_scale(pygame.Rect((0, 0), (0, 20))).height)
        self.screen.cats_tab.on_hovered()
        self.assertLess(abs(self.screen.cats_tab.text_layer.rect.centery - self.screen.cats_tab.rect.centery), 20)
        self.screen.cats_tab.on_unhovered()
        self.press(self.screen.cats_tab)
        self.assertTrue(self.screen.pile_base.visible)
        self.assertTrue(self.screen.info_messages.visible)
        self.assertTrue(self.screen.feed_all_button.visible)
        self.assertEqual(self.screen.cat_bg.relative_rect, ui_scale(pygame.Rect((140, 440), (560, 200))))
        self.assertEqual(positions, [button.relative_rect.topleft for button in (self.screen.cats_tab, self.screen.log_tab, self.screen.tactic_tab)])
        self.assertEqual(self.screen.pile_base.relative_rect, ui_scale(pygame.Rect((250, 25), (300, 300))))
        self.assertEqual(self.screen.pile_base.normal_image.get_size(), self.screen.pile_base.rect.size)
        self.screen.focus_cat_object = self.clan.your_cat
        self.screen.update_focus_cat()
        self.press(self.screen.tactic_tab)
        self.assertFalse(self.screen.focus_cat.image.visible)
        self.assertFalse(self.screen.feed_max_button.visible)
        self.press(self.screen.log_tab)
        self.assertTrue(self.screen.focus_cat.image.visible)
        self.assertTrue(self.screen.feed_max_button.visible)
        self.assertFalse(self.screen.feed_all_button.visible)

    def test_labels_and_controls_fit_at_fullscreen_scales_and_both_themes(self):
        import json
        from pathlib import Path
        from scripts.game_structure import screen_settings
        from scripts.ui.generate_screen_scale_json import _multiply_numbers

        base_theme = json.loads(Path("resources/theme/master_screen_scale.json").read_text())
        dark_theme = json.loads(Path("resources/theme/themes/dark.json").read_text())
        manager = screen_settings.MANAGER
        original_scale = screen_settings.screen_scale
        original_resolution = manager.window_resolution
        self.clan.clan_settings["feeding priorities"] = ["sick/injured first", "less nutrition first", "more experience first"]
        try:
            for scale in (1, 1.25, 1.5, 2):
                manager.set_window_resolution((int(800 * scale), int(700 * scale)))
                manager.get_theme().load_theme(_multiply_numbers(base_theme, scale))
                manager.get_theme().load_theme(dark_theme)
                for dark in (False, True):
                    with self.subTest(scale=scale, dark=dark), patch.object(screen_settings, "screen_scale", scale), patch.dict(game.settings, {"dark mode": dark}):
                        self.screen.exit_screen()
                        self.screen.screen_switches()
                        self.press(self.screen.tactic_tab)
                        self.assertEqual(self.screen.tactic_title.rect.centerx, self.screen.cat_bg.rect.centerx)
                        self.assertEqual(self.screen.pile_base.normal_image.get_size(), self.screen.pile_base.rect.size)
                        for values in (self.screen.tactic_text, self.screen.additional_text):
                            for key, box in values.items():
                                if key == "container_general":
                                    continue
                                if box.ui_container is values["container_general"].get_container():
                                    self.assertLessEqual(box.relative_rect.right, values["container_general"].get_container().rect.width)
                                available_height = box.rect.height - 2 * (box.padding[1] + box.border_width + box.shadow_width)
                                self.assertLessEqual(box.text_box_layout.layout_rect.height, available_height, key)
                        order = self.clan.freshkill_pile.get_status_order()
                        for first, second in zip(order, order[1:]):
                            self.assertLessEqual(self.screen.additional_text[first].relative_rect.bottom,
                                                 self.screen.additional_text[second].relative_rect.top)
                        for button in list(self.screen.tactic_moves.values()) + list(self.screen.status_moves.values()):
                            self.assertLessEqual(button.relative_rect.right, button.ui_container.get_container().rect.width)
        finally:
            manager.set_window_resolution(original_resolution)
            manager.get_theme().load_theme(_multiply_numbers(base_theme, original_scale))
            manager.get_theme().load_theme(dark_theme)
