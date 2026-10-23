from pathlib import Path
from unittest.mock import patch

import pygame
import pygame_gui
import pytest

from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.windows import RelationshipLog
from tests.test_relationship_screen import relationships, select


def test_log_blocks_queued_background_navigation_and_filter_changes(relationships):
    clan, main, cats, screen = relationships
    screen.handle_event(
        pygame.event.Event(
            pygame_gui.UI_BUTTON_START_PRESS,
            ui_element=screen.relation_list_elements["log0"],
        )
    )
    window = next(
        w
        for w in MANAGER.get_window_stack().get_full_stack()
        if isinstance(w, RelationshipLog)
    )
    try:
        assert window.is_blocking
        previous = dict(clan.clan_settings)
        with patch.object(screen, "change_screen") as route:
            screen.handle_event(
                pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS,
                    ui_element=screen.relation_list_elements["profile0"],
                )
            )
            route.assert_not_called()
        screen.handle_event(
            pygame.event.Event(
                pygame_gui.UI_BUTTON_START_PRESS,
                ui_element=screen.checkboxes["show_dead"],
            )
        )
        select(screen, "Family")
        assert clan.clan_settings == previous and screen.the_cat is main
    finally:
        window.closing_process()


def test_disabled_dead_cat_focus_cannot_be_activated_by_a_queued_click(relationships):
    clan, main, cats, screen = relationships
    clan.clan_settings["show dead relation"] = True
    screen.apply_cat_filter()
    screen.update_cat_page()
    button = next(
        b
        for b, (cat, action) in screen.card_actions.items()
        if cat.dead and action == "focus"
    )
    assert not button.is_enabled
    screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button)
    )
    assert screen.the_cat is main and game.switches["cat"] == main.ID


def test_filtering_closes_the_old_inspection_panel(relationships):
    clan, main, cats, screen = relationships
    portrait = next(iter(screen.sprite_buttons.values()))
    screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=portrait)
    )
    assert screen.details_container.visible
    select(screen, "Only You")
    assert not screen.details_container.visible


METRICS = (
    "romantic_love",
    "platonic_like",
    "dislike",
    "admiration",
    "comfortable",
    "jealousy",
    "trust",
)


def feeling(screen, label):
    screen.handle_event(
        pygame.event.Event(
            pygame_gui.UI_DROP_DOWN_MENU_CHANGED,
            ui_element=screen.checkboxes["feelings"],
            text=label,
        )
    )


def mixed_relations(main, cats):
    for cat in cats:
        for metric in METRICS:
            setattr(main.relationships[cat.ID], metric, 0)
    for i, values in enumerate(
        (
            dict(platonic_like=20),
            dict(dislike=20),
            dict(platonic_like=10, dislike=10),
            {},
            dict(romantic_love=1),
            dict(trust=5, dislike=5),
            dict(jealousy=1),
            dict(admiration=1),
            dict(comfortable=1),
            dict(trust=1),
            dict(platonic_like=1, dislike=2),
        )
    ):
        for metric, value in values.items():
            setattr(main.relationships[cats[i].ID], metric, value)


@pytest.mark.parametrize(
    "label,indices",
    [
        ("All feelings", set(range(11))),
        ("Positive", {0, 4, 7, 8, 9}),
        ("Negative", {1, 6, 10}),
        ("Balanced", {2, 3, 5}),
    ],
)
@pytest.mark.parametrize("dead", [False, True])
@pytest.mark.parametrize("empty", [False, True])
def test_feeling_filter_preserves_all_seven_values_and_existing_visibility_filters(
    relationships, label, indices, dead, empty
):
    clan, main, cats, screen = relationships
    mixed_relations(main, cats)
    before = [
        tuple(getattr(rel, metric) for metric in METRICS)
        for rel in screen.all_relations
    ]
    clan.clan_settings["show dead relation"] = dead
    clan.clan_settings["show empty relation"] = empty
    feeling(screen, label)
    expected = set(indices)
    if not dead:
        expected.discard(4)
    if not empty:
        expected.discard(3)
    assert {rel.cat_to.ID for rel in screen.filtered_cats} == {
        cats[i].ID for i in expected
    }
    assert before == [
        tuple(getattr(rel, metric) for metric in METRICS)
        for rel in screen.all_relations
    ]


@pytest.mark.parametrize(
    "label,expected", [("Positive", True), ("Negative", False), ("Balanced", False)]
)
def test_feeling_filters_combine_with_family_scope_and_preserve_search(
    relationships, label, expected
):
    clan, main, cats, screen = relationships
    mixed_relations(main, cats)
    select(screen, "Family")
    screen.current_page = 2
    screen.search_bar.set_text(str(cats[0].name))
    feeling(screen, label)
    assert (
        screen.search_bar.get_text() == str(cats[0].name) and screen.current_page == 1
    )
    assert [r.cat_to.ID for r in screen.filtered_cats] == (
        [cats[0].ID] if expected else []
    )


@pytest.mark.parametrize("label", ["All feelings", "Positive", "Negative", "Balanced"])
def test_actual_relationship_and_settings_roundtrip_keeps_values_and_filters(
    relationships, monkeypatch, tmp_path, label
):
    clan, main, cats, screen = relationships
    mixed_relations(main, cats)
    screen.update_focus_cat()
    directory = tmp_path / clan.name
    (directory / "relationships").mkdir(parents=True)
    for module in ("scripts.clan", "scripts.cat.cats"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setitem(game.switches, "clan_name", clan.name)

    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)

    monkeypatch.setattr(game, "safe_save", save)
    before = {
        cat.ID: tuple(getattr(main.relationships[cat.ID], metric) for metric in METRICS)
        for cat in cats
    }
    feeling(screen, label)
    selected = clan.clan_settings["relationship feeling filter"]
    expected = [r.cat_to.ID for r in screen.filtered_cats]
    clan.save_clan_settings()
    main.save_relationship_of_cat(str(directory / "relationships"))
    feeling(screen, "All feelings")
    main.relationships = {}
    clan.load_clan_settings()
    main.load_relationship_of_cat()
    screen.update_checkboxes()
    screen.update_focus_cat()
    assert clan.clan_settings["relationship feeling filter"] == selected
    assert screen.checkboxes["feelings"].selected_option[0] == label
    assert {
        ID: tuple(getattr(main.relationships[ID], metric) for metric in METRICS)
        for ID in before
    } == before
    assert [r.cat_to.ID for r in screen.filtered_cats] == expected


@pytest.mark.parametrize("only_you", [False, True])
def test_legacy_settings_default_to_all_feelings_without_rewriting_the_file(
    relationships, monkeypatch, tmp_path, only_you
):
    import json

    clan, main, cats, screen = relationships
    monkeypatch.setattr("scripts.clan.get_save_dir", lambda: str(tmp_path))
    directory = tmp_path / clan.name
    directory.mkdir()
    file = directory / "clan_settings.json"
    text = json.dumps({"show only you": only_you, "show empty relation": True})
    file.write_text(text, encoding="utf-8")
    clan.load_clan_settings()
    screen.update_checkboxes()
    screen.apply_cat_filter()
    screen.update_cat_page()
    assert clan.clan_settings["relationship feeling filter"] == "all"
    assert screen.checkboxes["feelings"].selected_option[0] == "All feelings"
    assert (
        clan.clan_settings["show only you"] == only_you
        and file.read_text(encoding="utf-8") == text
    )


@pytest.mark.parametrize("focused", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
def test_page_keys_respect_search_focus_shortcut_preference_and_page_bounds(
    relationships, monkeypatch, focused, enabled
):
    clan, main, cats, screen = relationships
    monkeypatch.setattr(screen.search_bar, "is_focused", focused)
    monkeypatch.setitem(game.settings, "keybinds", enabled)
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN))
    assert screen.current_page == (2 if enabled and not focused else 1)
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEDOWN))
    assert screen.current_page == (2 if enabled and not focused else 1)
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_PAGEUP))
    assert screen.current_page == 1


def test_keyboard_cat_navigation_matches_the_existing_buttons(
    relationships, monkeypatch
):
    clan, main, cats, screen = relationships
    monkeypatch.setitem(game.settings, "keybinds", True)
    monkeypatch.setattr(screen.search_bar, "is_focused", False)
    target = screen.next_cat
    assert screen.next_cat_button.is_enabled
    screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert screen.the_cat.ID == target and game.switches["cat"] == target


def test_escape_closes_inspection_before_returning_to_the_previous_screen(
    relationships, monkeypatch
):
    clan, main, cats, screen = relationships
    monkeypatch.setitem(game.settings, "keybinds", True)
    portrait = next(iter(screen.sprite_buttons.values()))
    screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=portrait)
    )
    with patch.object(screen, "change_screen") as route:
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert not screen.details_container.visible
        route.assert_not_called()
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        route.assert_called_once()


def test_log_blocks_frame_search_refresh_until_closed(relationships):
    clan, main, cats, screen = relationships
    original = list(screen.filtered_cats)
    screen.handle_event(
        pygame.event.Event(
            pygame_gui.UI_BUTTON_START_PRESS,
            ui_element=screen.relation_list_elements["log0"],
        )
    )
    window = next(
        w
        for w in MANAGER.get_window_stack().get_full_stack()
        if isinstance(w, RelationshipLog)
    )
    try:
        screen.search_bar.set_text("NoSuchCat123")
        screen.on_use()
        assert screen.filtered_cats == original
    finally:
        window.closing_process()
    screen.on_use()
    assert not screen.filtered_cats


def test_feeling_dropdown_opens_upward_and_escape_does_not_leave_the_screen(
    relationships, monkeypatch
):
    clan, main, cats, screen = relationships
    monkeypatch.setitem(game.settings, "keybinds", True)
    menu = screen.checkboxes["feelings"]
    menu.process_event(
        pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED, ui_element=menu.current_state.open_button
        )
    )
    MANAGER.update(0.1)
    assert menu.current_state is menu.menu_states["expanded"]
    assert menu.current_state.options_selection_list.rect.top < menu.rect.top
    assert menu.current_state.options_selection_list.rect.bottom <= menu.rect.bottom
    assert MANAGER.get_root_container().rect.contains(
        menu.current_state.options_selection_list.rect
    )
    with patch.object(screen, "change_screen") as route:
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        MANAGER.update(0.1)
        assert menu.current_state is menu.menu_states["closed"]
        route.assert_not_called()


def test_filter_explanation_reappears_on_hover_after_dropdown_reopens(relationships):
    clan, main, cats, screen = relationships
    menu = screen.checkboxes["feelings"]
    for reopened in (False, True):
        if reopened:
            menu.process_event(
                pygame.event.Event(
                    pygame_gui.UI_BUTTON_PRESSED,
                    ui_element=menu.current_state.open_button,
                )
            )
            MANAGER.update(0.1)
            menu.unfocus()
            MANAGER.update(0.1)
        screen.on_use()
        button = menu.current_state.selected_option_button
        with patch.object(MANAGER, "_update_mouse_position"), patch.object(
            MANAGER, "mouse_position", button.rect.center
        ):
            for _ in range(4):
                MANAGER.update(0.6)
            assert button.tool_tip is not None and button.tool_tip.visible
            assert (
                "subtracts dislike and jealousy" in button.tool_tip.text_block.html_text
            )
        with patch.object(MANAGER, "_update_mouse_position"), patch.object(
            MANAGER, "mouse_position", (0, 0)
        ):
            MANAGER.update(0.1)


def test_native_feeling_selection_does_not_activate_the_cards_below(relationships):
    clan, main, cats, screen = relationships
    menu = screen.checkboxes["feelings"]
    menu.process_event(
        pygame.event.Event(
            pygame_gui.UI_BUTTON_PRESSED, ui_element=menu.current_state.open_button
        )
    )
    MANAGER.update(0.1)
    entries = menu.current_state.options_selection_list.item_list
    target = next(
        item["button_element"] for item in entries if item["text"] == "Negative"
    )
    point = target.rect.center
    card_buttons = set(screen.card_actions)
    pygame.event.clear()
    pressed = []
    with patch.object(MANAGER, "get_mouse_position", return_value=point):
        MANAGER.update(0.016)
        MANAGER.process_events(
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point)
        )
        MANAGER.process_events(
            pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point)
        )
        for _ in range(5):
            for event in pygame.event.get():
                if event.type == pygame_gui.UI_BUTTON_START_PRESS:
                    pressed.append(event.ui_element)
                MANAGER.process_events(event)
                screen.handle_event(event)
            MANAGER.update(0.016)
    assert clan.clan_settings["relationship feeling filter"] == "negative"
    assert not any(button in card_buttons for button in pressed)
    assert screen.the_cat is main and not screen.details_container.visible


def test_feeling_filter_geometry_and_popup_scale_in_both_themes(relationships):
    import json
    from scripts.game_structure import screen_settings
    from scripts.ui.generate_screen_scale_json import _multiply_numbers

    clan, main, cats, screen = relationships
    resolution, offset = MANAGER.window_resolution, MANAGER.offset
    original_scale = screen_settings.screen_scale
    base = json.loads(
        Path("resources/theme/master_screen_scale.json").read_text(encoding="utf-8")
    )
    dark_theme = json.loads(
        Path("resources/theme/themes/dark.json").read_text(encoding="utf-8")
    )
    screen.exit_screen()
    try:
        for scale in (1, 1.25, 1.5, 2):
            MANAGER.set_window_resolution((int(800 * scale), int(700 * scale)))
            MANAGER.set_offset((0, 0))
            MANAGER.get_theme().load_theme(_multiply_numbers(base, scale))
            MANAGER.get_theme().load_theme(dark_theme)
            for dark in (False, True):
                with patch.object(screen_settings, "screen_scale", scale), patch.dict(
                    game.settings, {"dark mode": dark}
                ):
                    screen.screen_switches()
                    try:
                        menu = screen.checkboxes["feelings"]
                        root = MANAGER.get_root_container().rect
                        assert root.contains(menu.rect)
                        assert menu.rect.top == screen.back_button.rect.top
                        for widget in (
                            screen.page_number,
                            screen.next_page_button,
                            screen.previous_page_button,
                            screen.back_button,
                        ):
                            assert not menu.rect.colliderect(widget.rect)
                        menu.process_event(
                            pygame.event.Event(
                                pygame_gui.UI_BUTTON_PRESSED,
                                ui_element=menu.current_state.open_button,
                            )
                        )
                        MANAGER.update(0.1)
                        assert root.contains(
                            menu.current_state.options_selection_list.rect
                        )
                        assert (
                            menu.current_state.options_selection_list.rect.top
                            < menu.rect.top
                        )
                    finally:
                        screen.exit_screen()
    finally:
        MANAGER.set_window_resolution(resolution)
        MANAGER.set_offset(offset)
        MANAGER.get_theme().load_theme(_multiply_numbers(base, original_scale))
        MANAGER.get_theme().load_theme(dark_theme)
        screen.screen_switches()


def test_filter_change_discards_the_old_inspection_target_and_queued_actions(
    relationships,
):
    clan, main, cats, screen = relationships
    portrait = next(iter(screen.sprite_buttons.values()))
    screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=portrait)
    )
    old_action = screen.view_profile_button
    select(screen, "Only You")
    with patch.object(screen, "change_screen") as route:
        screen.handle_event(
            pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=old_action)
        )
        route.assert_not_called()
    assert screen.inspect_cat is None and game.switches["cat"] == main.ID


@pytest.mark.parametrize(
    "label,indices", [("Positive", {7, 8, 9}), ("Negative", {6, 10}), ("Balanced", {5})]
)
def test_romance_scope_combines_with_feelings_without_changing_dating_eligibility(
    relationships, label, indices
):
    clan, main, cats, screen = relationships
    mixed_relations(main, cats)
    before = [main.is_dateable(cat) for cat in cats]
    select(screen, "Romance")
    feeling(screen, label)
    assert {rel.cat_to.ID for rel in screen.filtered_cats} == {
        cats[i].ID for i in indices
    }
    assert [main.is_dateable(cat) for cat in cats] == before


@pytest.mark.parametrize(
    "label,shown",
    [
        ("All feelings", True),
        ("Positive", False),
        ("Negative", True),
        ("Balanced", False),
    ],
)
def test_only_you_scope_remains_independent_of_the_feeling_filter(
    relationships, label, shown
):
    clan, main, cats, screen = relationships
    mixed_relations(main, cats)
    select(screen, "Only You")
    feeling(screen, label)
    assert [rel.cat_to.ID for rel in screen.filtered_cats] == (
        [clan.your_cat.ID] if shown else []
    )
