from unittest.mock import patch

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.cat_relations.inheritance import Inheritance
from scripts.cat_relations.relationship import Relationship
from scripts.clan import Clan
from scripts.game_structure.game_essentials import game
from scripts.screens.RelationshipScreen import RelationshipScreen


@pytest.fixture
def relationships(monkeypatch):
    for target, key, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                               (Cat, "outside_cats", {}), (Inheritance, "all_inheritances", {}),
                               (game, "all_screens", {})):
        monkeypatch.setattr(target, key, value)
    monkeypatch.setattr(Cat, "sprite", property(lambda cat: pygame.Surface((50, 50), pygame.SRCALPHA)))
    clan = Clan(name="RelationshipTest", biome="Forest", camp_bg="camp1")
    clan.clan_cats = []
    clan.clan_settings["show empty relation"] = True
    monkeypatch.setattr(game, "clan", clan)
    parent = Cat(status="warrior", moons=80)
    main = Cat(status="warrior", moons=30, parent1=parent.ID)
    cats = [Cat(status="warrior", moons=30) for _ in range(11)]
    cats[0].parent1 = parent.ID
    cats[1].moons = 8
    cats[1].status = "apprentice"
    main.apprentice = [cats[2].ID]
    cats[3].outside = True
    cats[4].dead = True
    for cat in [parent, main] + cats:
        cat.create_inheritance_new_cat()
        clan.add_cat(cat)
    clan.your_cat = cats[-1]
    for cat in cats:
        main.relationships[cat.ID] = Relationship(main, cat, platonic_like=25, trust=12, jealousy=5)
    with patch.dict(game.switches, {"cat": main.ID, "window_open": False}):
        screen = RelationshipScreen("relationship test")
        screen.screen_switches()
        try:
            yield clan, main, cats, screen
        finally:
            screen.exit_screen()


def select(screen, option):
    screen.handle_event(pygame.event.Event(pygame_gui.UI_DROP_DOWN_MENU_CHANGED,
        ui_element=screen.checkboxes["show_you"], text=option))


def test_family_filter_uses_real_inheritance_and_keeps_search(relationships):
    clan, main, cats, screen = relationships
    screen.search_bar.set_text(str(cats[0].name))
    select(screen, "Family")
    assert [rel.cat_to.ID for rel in screen.filtered_cats] == [cats[0].ID]
    assert clan.clan_settings["show family relation"]
    select(screen, "Everyone")
    assert all(str(cats[0].name).lower() in str(rel.cat_to.name).lower() for rel in screen.filtered_cats)


def test_romance_filter_obeys_local_age_mentor_family_and_outside_rules(relationships):
    clan, main, cats, screen = relationships
    select(screen, "Romance")
    expected = [rel for rel in screen.all_relations if main.is_dateable(rel.cat_to)]
    assert screen.filtered_cats == expected
    assert all(cat.ID not in [rel.cat_to.ID for rel in expected] for cat in cats[:5])
    assert expected
    assert not clan.clan_settings["show family relation"]
    select(screen, "Only You")
    assert [rel.cat_to.ID for rel in screen.filtered_cats] == [clan.your_cat.ID]
    assert not clan.clan_settings["show romance relation"]


def test_checkbox_changes_keep_search_and_return_to_first_page(relationships):
    clan, main, cats, screen = relationships
    screen.current_page = 2
    screen.search_bar.set_text(str(cats[-1].name))
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
        ui_element=screen.checkboxes["show_dead"]))
    assert screen.current_page == 1
    assert screen.search_bar.get_text() == str(cats[-1].name)
    assert all(str(cats[-1].name).lower() in str(rel.cat_to.name).lower() for rel in screen.filtered_cats)


def test_empty_results_have_an_explanation_and_no_invalid_page(relationships):
    clan, main, cats, screen = relationships
    screen.search_bar.set_text("NoSuchCat123")
    screen.apply_cat_filter(screen.search_bar.get_text())
    screen.update_cat_page()
    assert screen.page_number.html_text == "0 / 0"
    assert "No relationships match" in screen.relation_list_elements["empty"].html_text
    assert not screen.next_page_button.is_enabled
    assert not screen.previous_page_button.is_enabled


def test_seven_values_are_preserved_and_readable_in_hover_help(relationships):
    clan, main, cats, screen = relationships
    before = [(rel.romantic_love, rel.platonic_like, rel.dislike, rel.admiration,
               rel.comfortable, rel.jealousy, rel.trust) for rel in screen.all_relations]
    labels = ("romantic", "plantonic", "dislike", "admiration", "comfortable", "jealous", "trust")
    for label in labels:
        assert "/100" in screen.relation_list_elements[f"{label}_text0"].tool_tip_text
    select(screen, "Family")
    select(screen, "Everyone")
    assert before == [(rel.romantic_love, rel.platonic_like, rel.dislike, rel.admiration,
                       rel.comfortable, rel.jealousy, rel.trust) for rel in screen.all_relations]


def test_filter_settings_roundtrip_and_legacy_only_you(relationships, monkeypatch, tmp_path):
    clan, main, cats, screen = relationships
    monkeypatch.setattr("scripts.clan.get_save_dir", lambda: str(tmp_path))
    (tmp_path / clan.name).mkdir()
    select(screen, "Family")
    clan.save_clan_settings()
    select(screen, "Everyone")
    clan.load_clan_settings()
    screen.update_checkboxes()
    screen.apply_cat_filter()
    assert clan.clan_settings["show family relation"]
    assert [rel.cat_to.ID for rel in screen.filtered_cats] == [cats[0].ID]
    clan.clan_settings["show family relation"] = False
    clan.clan_settings["show only you"] = True
    screen.update_checkboxes()
    screen.apply_cat_filter()
    assert screen.checkboxes["show_you"].selected_option[0] == "Only You"
    assert [rel.cat_to.ID for rel in screen.filtered_cats] == [clan.your_cat.ID]


def test_inspection_profile_and_log_controls_survive_filter_changes(relationships):
    from scripts.game_structure.windows import RelationshipLog

    clan, main, cats, screen = relationships
    select(screen, "Family")
    target = next(iter(screen.sprite_buttons.values()))
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=target))
    assert screen.inspect_cat is cats[0]
    assert screen.log_icon.is_enabled
    windows = []
    def log(*args):
        window = RelationshipLog(*args)
        windows.append(window)
        return window
    with patch("scripts.screens.RelationshipScreen.RelationshipLog", side_effect=log):
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.log_icon))
    try:
        assert not screen.checkboxes["show_you"].visible
    finally:
        windows[0].closing_process()
    assert screen.checkboxes["show_you"].visible
    with patch.object(screen, "change_screen") as route:
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.view_profile_button))
        route.assert_called_once_with("profile screen")
    assert game.switches["cat"] == cats[0].ID


def test_expanded_filter_and_label_fit_without_clipping(relationships):
    from scripts.game_structure.screen_settings import MANAGER

    clan, main, cats, screen = relationships
    menu = screen.checkboxes["show_you"]
    menu.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=menu.current_state.open_button))
    MANAGER.update(0.1)
    assert MANAGER.get_root_container().rect.contains(menu.current_state.options_selection_list.rect)
    assert screen.show_you_text.scroll_bar is None
    assert not screen.show_you_text.rect.colliderect(menu.rect)


def test_wide_grid_has_eight_cards_with_inline_actions_and_no_permanent_inspector(relationships):
    from scripts.utility import ui_scale

    clan, main, cats, screen = relationships
    assert len(screen.sprite_buttons) == 8
    assert len(screen.card_actions) == 24
    assert not screen.details_container.visible
    pane = ui_scale(pygame.Rect((50, 122), (680, 500)))
    for i in range(8):
        frame = screen.relation_list_elements[f"frame{i}"].relative_rect
        assert pane.contains(frame)
        for action in ("focus", "log", "profile"):
            button = screen.relation_list_elements[f"{action}{i}"]
            assert pane.contains(button.relative_rect)
            assert not frame.colliderect(button.relative_rect)
    portrait = next(iter(screen.sprite_buttons.values()))
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=portrait))
    assert screen.details_container.visible
    assert screen.inspect_cat_elements["col2"].alive()
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.details_close_button))
    assert not screen.details_container.visible


@pytest.mark.parametrize("action", ["focus", "profile", "log"])
def test_inline_actions_route_to_the_selected_cat_and_keep_inspector_hidden(relationships, action):
    from scripts.game_structure.windows import RelationshipLog

    clan, main, cats, screen = relationships
    button = next(button for button, (cat, kind) in screen.card_actions.items() if kind == action and not cat.dead)
    target, _ = screen.card_actions[button]
    if action == "log":
        windows = []
        def log(*args):
            window = RelationshipLog(*args)
            windows.append(window)
            return window
        with patch("scripts.screens.RelationshipScreen.RelationshipLog", side_effect=log):
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
        try:
            assert windows[0].is_blocking
            assert screen.inspect_cat is target
            assert not button.is_enabled
        finally:
            windows[0].closing_process()
        assert button.is_enabled
    elif action == "profile":
        with patch.object(screen, "change_screen") as route:
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
            route.assert_called_once_with("profile screen")
        assert game.switches["cat"] == target.ID
    else:
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
        assert screen.the_cat is target
        assert game.switches["cat"] == target.ID
    assert not screen.details_container.visible


def test_dead_cat_log_and_former_mate_indicator_are_retained(relationships):
    clan, main, cats, screen = relationships
    clan.clan_settings["show dead relation"] = True
    main.previous_mates.append(cats[0].ID)
    screen.apply_cat_filter()
    screen.update_cat_page()
    assert "Former mate" in screen.relation_list_elements["ex_mate_icon0"].tool_tip_text
    dead_buttons = {kind: button for button, (cat, kind) in screen.card_actions.items() if cat.dead}
    assert not dead_buttons["focus"].is_enabled
    assert dead_buttons["log"].is_enabled
    assert dead_buttons["profile"].is_enabled


def test_native_log_close_restores_hidden_filters_and_card_actions(relationships):
    from scripts.game_structure.screen_settings import MANAGER
    from scripts.game_structure.windows import RelationshipLog

    clan, main, cats, screen = relationships
    button = screen.relation_list_elements["log0"]
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
    window = [window for window in MANAGER.get_window_stack().get_full_stack() if isinstance(window, RelationshipLog)][-1]
    window.on_close_window_button_pressed()
    assert not window.alive()
    assert screen.checkboxes["show_you"].visible
    assert button.is_enabled


def test_relationship_layout_scales_in_both_themes(relationships):
    import json
    from pathlib import Path
    from scripts.game_structure import screen_settings
    from scripts.ui.generate_screen_scale_json import _multiply_numbers
    from scripts.utility import ui_scale

    clan, main, cats, screen = relationships
    manager = screen_settings.MANAGER
    resolution, offset = manager.window_resolution, manager.offset
    original_scale = screen_settings.screen_scale
    base = json.loads(Path("resources/theme/master_screen_scale.json").read_text(encoding="utf-8"))
    dark_theme = json.loads(Path("resources/theme/themes/dark.json").read_text(encoding="utf-8"))
    screen.exit_screen()
    try:
        for scale in (1, 1.25, 1.5, 2):
            manager.set_window_resolution((int(800 * scale), int(700 * scale)))
            manager.set_offset((0, 0))
            manager.get_theme().load_theme(_multiply_numbers(base, scale))
            manager.get_theme().load_theme(dark_theme)
            for dark in (False, True):
                with patch.object(screen_settings, "screen_scale", scale), patch.dict(game.settings, {"dark mode": dark}):
                    screen.screen_switches()
                    try:
                        pane = ui_scale(pygame.Rect((50, 122), (680, 500)))
                        for i in range(8):
                            assert pane.contains(screen.relation_list_elements[f"frame{i}"].relative_rect)
                            for action in ("focus", "profile", "log"):
                                assert pane.contains(screen.relation_list_elements[f"{action}{i}"].relative_rect)
                        for _ in range(3):
                            manager.update(1 / 60)
                        assert screen.show_you_text.scroll_bar is None
                        assert not screen.show_you_text.rect.colliderect(screen.checkboxes["show_you"].rect)
                    finally:
                        screen.exit_screen()
    finally:
        manager.set_window_resolution(resolution)
        manager.set_offset(offset)
        manager.get_theme().load_theme(_multiply_numbers(base, original_scale))
        manager.get_theme().load_theme(dark_theme)
        screen.screen_switches()
