from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.clan import Clan
from scripts.clan_resources.freshkill import FreshkillPile
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.supply_windows import FreshkillManagementWindow, HerbManagementWindow
from scripts.screens.Screens import Screens
from scripts.screens.screens_core import screens_core as core


@pytest.fixture
def supplies(monkeypatch):
    with monkeypatch.context() as isolated:
        isolated.setattr(Cat, "all_cats", {})
        isolated.setattr(Cat, "all_cats_list", [])
        isolated.setattr(Cat, "sprite", property(lambda cat: pygame.Surface((50, 50)).convert_alpha()))
        isolated.setattr(game, "all_screens", {})
        isolated.setattr(game, "safe_save", Mock(side_effect=AssertionError("No save writes")))
        isolated.setattr(game, "herb_events_list", [])
        isolated.setattr(game, "freshkill_event_list", [])
        clan = Clan(name="SupplyTest", game_mode="expanded", camp_bg="camp1")
        isolated.setattr(game, "clan", clan)
        cats = [Cat(status="warrior", moons=30) for _ in range(14)]
        clan.clan_cats = [cat.ID for cat in cats]
        clan.your_cat = cats[0]
        clan.herbs = {"catmint": 4, "cobwebs": 2}
        clan.freshkill_pile = FreshkillPile(start_amount=100)
        clan.freshkill_pile.living_cats = cats
        clan.freshkill_pile.update_nutrition(cats)
        for nutrition in clan.freshkill_pile.nutrition_info.values():
            nutrition.current_score = nutrition.max_score / 2
        core.rebuild_core(should_rebuild_bgs=False)
        screen = Screens("supplies test")
        screen.screen_switches()
        screen.set_disabled_menu_buttons()
        screen.show_menu_buttons()
        with patch.dict(game.switches, {"saved_clan": True}):
            yield screen, clan, cats
            for window in MANAGER.get_window_stack().get_full_stack().copy():
                window.kill()
            screen.hide_menu_buttons()
    core.rebuild_core(should_rebuild_bgs=False)
    Screens.menu_buttons = core.menu_buttons


def press(window, element):
    window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=element))


def select(window, index):
    button = window.cat_list.cat_sprites[f"sprite{index}"].button
    MANAGER.process_events(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
    MANAGER.update(0.01)


def test_herb_window_preserves_log_and_returns_to_medicine_den(supplies):
    screen, clan, cats = supplies
    game.herb_events_list = ["Catmint gathered.", "Cobwebs used."]
    with patch.object(screen, "change_screen") as route:
        window = HerbManagementWindow(screen)
        assert window.is_blocking
        assert "6" in window.log.html_text
        assert "Catmint gathered." in window.log.html_text
        press(window, window.med_den_button)
        route.assert_called_once_with("med den screen")
        assert not window.alive() and not window.fade.alive() and not window.box.alive()
    assert clan.herbs == {"catmint": 4, "cobwebs": 2}
    assert game.herb_events_list == ["Catmint gathered.", "Cobwebs used."]


def test_popup_routes_do_not_leave_current_screen_and_classic_remains_hidden(supplies):
    screen, clan, cats = supplies
    with patch.object(screen, "change_screen") as route:
        for key, kind in (("herbs", HerbManagementWindow), ("freshkill", FreshkillManagementWindow)):
            screen.menu_button_pressed(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=core.menu_buttons[key]))
            window = MANAGER.get_window_stack().get_full_stack()[-1]
            assert isinstance(window, kind)
            window.kill()
        route.assert_not_called()
        clan.game_mode = "classic"
        for key in ("herbs", "freshkill"):
            screen.menu_button_pressed(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=core.menu_buttons[key]))
        assert not MANAGER.get_window_stack().get_full_stack()


def test_supply_window_is_not_opened_during_moon_update(supplies):
    screen, clan, cats = supplies
    screen.events_thread = Mock()
    screen.events_thread.is_alive.return_value = True
    screen.menu_button_pressed(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=core.menu_buttons["freshkill"]))
    assert not MANAGER.get_window_stack().get_full_stack()


def test_selected_feeding_changes_only_selected_cats(supplies):
    screen, clan, cats = supplies
    window = FreshkillManagementWindow(screen)
    original = {key: nutrition.current_score for key, nutrition in clan.freshkill_pile.nutrition_info.items()}
    select(window, 0)
    assert window.cat_list.selected == [cats[0].ID]
    assert window.cat_list.selection_boxes["sprite0"].visible
    assert window.view_elements["feed_selected"].is_enabled
    press(window, window.view_elements["feed_selected"])
    nutrition = clan.freshkill_pile.nutrition_info
    assert len(nutrition) == len(cats)
    assert nutrition[cats[0].ID].current_score > original[cats[0].ID]
    for cat in cats[1:]:
        assert nutrition[cat.ID].current_score == original[cat.ID]
    assert not game.switches["saved_clan"]
    assert clan.freshkill_pile.total_amount < 100


def test_selection_survives_pages_and_log_switches_cleanly(supplies):
    screen, clan, cats = supplies
    window = FreshkillManagementWindow(screen)
    select(window, 0)
    press(window, window.view_elements["next"])
    assert window.current_page == 2
    select(window, 0)
    assert window.cat_list.selected == [cats[0].ID, cats[12].ID]
    press(window, window.view_elements["previous"])
    assert window.cat_list.selection_boxes["sprite0"].visible
    select(window, 0)
    assert window.cat_list.selected == [cats[12].ID]
    for _ in range(3):
        press(window, window.tabs["log"])
        assert window.open_view == "log" and window.cat_list is None
        assert "Nothing to report." in window.view_elements["log"].html_text
        press(window, window.tabs["feed"])
        assert len(window.cat_list.cat_sprites) == 12
        assert window.cat_list.selected == [cats[12].ID]
        assert all(button.button.alive() for button in window.cat_list.cat_sprites.values())


def test_ration_tooltips_and_custom_tactics_route(supplies):
    screen, clan, cats = supplies
    game.all_screens["clearing screen"] = SimpleNamespace(open_tab=None)
    window = FreshkillManagementWindow(screen)
    before = clan.clan_settings["ration prey"]
    press(window, window.view_elements["ration"])
    assert clan.clan_settings["ration prey"] != before
    assert window.view_elements["ration"].tool_tip_text == window.view_elements["ration_label"].tool_tip_text
    with patch.object(screen, "change_screen") as route:
        press(window, window.tabs["tactic"])
        route.assert_called_once_with("clearing screen")
    assert game.all_screens["clearing screen"].open_tab == "tactic"
    assert not window.alive()


def test_empty_pile_cannot_feed_and_full_cats_are_not_listed(supplies):
    screen, clan, cats = supplies
    clan.freshkill_pile.remove_freshkill(100)
    window = FreshkillManagementWindow(screen)
    assert not window.view_elements["feed_all"].is_enabled
    select(window, 0)
    assert not window.view_elements["feed_selected"].is_enabled
    for nutrition in clan.freshkill_pile.nutrition_info.values():
        nutrition.current_score = nutrition.max_score
    window.create_feed_view()
    assert not window.hungry_cats
    assert "No cats are hungry." in window.view_elements["empty"].html_text


def test_windows_close_without_leaking_overlay_or_grid(supplies):
    screen, clan, cats = supplies
    count = len(MANAGER.get_sprite_group().sprites())
    for kind in (FreshkillManagementWindow, HerbManagementWindow, FreshkillManagementWindow):
        window = kind(screen)
        window.process_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert not window.alive()
        assert not window.fade.alive() and not window.box.alive()
        assert len(MANAGER.get_sprite_group().sprites()) == count


def test_long_names_fit_source_style_single_line_labels(supplies):
    screen, clan, cats = supplies
    cats[0].name.prefix = "An Unusually Long Prefix With Several Words"
    window = FreshkillManagementWindow(screen)
    label = window.cat_list.cat_names["name0"]
    assert label.text.endswith("...")
    assert label.font.get_rect(label.text).width <= label.rect.width
    assert str(cats[0].name) in window.cat_list.cat_sprites["sprite0"].button.tool_tip_text


def test_raw_mouse_click_selects_popup_cat_once(supplies):
    screen, clan, cats = supplies
    window = FreshkillManagementWindow(screen)
    button = window.cat_list.cat_sprites["sprite0"].button
    point = button.rect.center
    pygame.event.clear()
    with patch.object(MANAGER, "get_mouse_position", return_value=point):
        MANAGER.update(0.01)
        MANAGER.process_events(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        MANAGER.process_events(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))
    for event in pygame.event.get():
        MANAGER.process_events(event)
    MANAGER.update(0.01)
    assert window.cat_list.selected == [cats[0].ID]
    assert window.view_elements["feed_selected"].is_enabled


@pytest.mark.parametrize("rule", ["by-status", "younger first", "less nutrition first", "more experience first", "hunter first", "sick/injured first", "custom"])
@pytest.mark.parametrize("target", ["parent", "kit", "pregnant"])
def test_selected_family_feeding_respects_target_and_full_family_context(supplies, rule, target):
    screen, clan, cats = supplies
    parent = Cat(status="warrior", moons=35, gender="female")
    kit = Cat(status="kitten", moons=1, parent1=parent.ID)
    pregnant = Cat(status="queen's apprentice", moons=15)
    pregnant.injuries["pregnant"] = {"severity": "major"}
    family = [parent, kit, pregnant]
    clan.clan_cats.extend(cat.ID for cat in family)
    pile = clan.freshkill_pile
    pile.living_cats = cats + family
    pile.update_nutrition(pile.living_cats)
    for nutrition in pile.nutrition_info.values():
        nutrition.current_score = nutrition.max_score / 2
    for mode in ("by-status", "younger first", "less nutrition first", "more experience first", "hunter first", "sick/injured first"):
        clan.clan_settings[mode] = mode == rule
    clan.clan_settings["feeding priorities"] = ["less nutrition first", "by-status"] if rule == "custom" else []
    selected = {"parent": parent, "kit": kit, "pregnant": pregnant}[target]
    before = {key: value.current_score for key, value in pile.nutrition_info.items()}
    amount = pile.total_amount
    pile.feed_cats([selected], additional_food_round=True)
    assert set(before) == set(pile.nutrition_info)
    assert all(value.current_score == before[key] for key, value in pile.nutrition_info.items() if key != selected.ID)
    if target == "kit":
        assert pile.total_amount == amount
        assert pile.nutrition_info[kit.ID].current_score == before[kit.ID]
    else:
        assert amount - pile.total_amount >= pile.prey_requirement["queen/pregnant"]
        assert pile.nutrition_info[selected.ID].current_score > before[selected.ID]


@pytest.mark.parametrize("dark", [False, True])
def test_supply_modal_text_keeps_source_contrast_in_both_themes(supplies, dark):
    screen, clan, cats = supplies
    with patch.dict(game.settings, {"dark mode": dark}):
        window = FreshkillManagementWindow(screen)
        label = window.cat_list.cat_names["name0"]
        assert label.text_colour.r < 100 and label.text_colour.g < 100
        assert "#dark" not in window.view_elements["status"].object_ids
        window.kill()
        window = HerbManagementWindow(screen)
        assert "#dark" not in window.log.object_ids
