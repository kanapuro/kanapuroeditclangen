from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame
import pygame_gui
import pytest

from scripts.clan import Clan
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.screens.Screens import Screens
from scripts.screens.screens_core import screens_core as core


@pytest.fixture
def navigation(monkeypatch):
    with monkeypatch.context() as isolated:
        clan = Clan(name="NavigationTest", game_mode="expanded", camp_bg="camp1")
        clan.clan_settings["moons and seasons"] = True
        isolated.setattr(game, "clan", clan)
        isolated.setattr(game, "all_screens", {})
        core.rebuild_core(should_rebuild_bgs=False)
        screen = Screens("navigation test")
        screen.screen_switches()
        screen.set_disabled_menu_buttons()
        screen.show_menu_buttons()
        yield screen
        screen.hide_menu_buttons()
    core.rebuild_core(should_rebuild_bgs=False)
    Screens.menu_buttons = core.menu_buttons


@pytest.mark.parametrize("key,target", [
    ("events_screen", "events screen"), ("catlist_screen", "list screen"),
    ("patrol_screen", "patrol screen"), ("camp_screen", "camp screen"),
    ("heading", "camp screen"),
    ("lead_den", "leader den screen"),
    ("med_cat_den", "med den screen"), ("warrior_den", "warrior den screen"),
    ("clearing", "clearing screen"), ("allegiances", "allegiances screen"),
    ("clan_settings", "clan settings screen"),
])
def test_shared_navigation_preserves_destinations(navigation, key, target):
    with patch.object(navigation, "change_screen") as change:
        navigation.menu_button_pressed(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
            ui_element=core.menu_buttons[key]))
        change.assert_called_once_with(target)


def dropdown_state(dropdown):
    manager = dropdown.ui_manager
    return {
        "manager": id(manager), "expected_manager": id(MANAGER),
        "parent": (dropdown.parent_button.visible, dropdown.parent_button.is_enabled,
                   tuple(dropdown.parent_button.rect)),
        "open": dropdown.is_open,
        "windows": [(type(window).__name__, window.is_blocking, window.alive(), window.visible)
                    for window in manager.get_window_stack().get_full_stack()],
        "offset": manager.offset,
    }


def test_dropdowns_open_on_hover_stay_open_over_children_and_close_outside(navigation):
    dropdown = core.menu_dropdowns["dens"]
    assert not dropdown.is_open
    with patch.object(MANAGER, "get_mouse_position", return_value=core.menu_buttons["dens"].rect.center):
        dropdown.update(0.01)
    assert dropdown.is_open and core.menu_buttons["lead_den"].visible, dropdown_state(dropdown)
    with patch.object(MANAGER, "get_mouse_position", return_value=core.menu_buttons["lead_den"].rect.center):
        dropdown.update(0.01)
    assert dropdown.is_open
    with patch.object(MANAGER, "get_mouse_position", return_value=(0, 0)):
        dropdown.update(0.01)
    assert not dropdown.is_open and not core.menu_buttons["lead_den"].visible


def test_hidden_navigation_and_modal_windows_close_dropdowns(navigation):
    dropdown = core.menu_dropdowns["supplies"]
    dropdown.open()
    navigation.hide_menu_buttons()
    with patch.object(MANAGER, "get_mouse_position", return_value=core.menu_buttons["supplies"].rect.center):
        dropdown.update(0.01)
    assert not dropdown.is_open
    navigation.show_menu_buttons()
    window = pygame_gui.elements.UIWindow(pygame.Rect(100, 100, 200, 150), manager=MANAGER)
    window.set_blocking(True)
    try:
        with patch.object(MANAGER, "get_mouse_position", return_value=core.menu_buttons["supplies"].rect.center):
            dropdown.update(0.01)
        assert not dropdown.is_open
    finally:
        window.kill()


def test_classic_layout_hides_supplies_and_retains_health_dens(navigation):
    game.clan.game_mode = "classic"
    navigation.screen_switches()
    navigation.set_disabled_menu_buttons(["catlist_screen"])
    navigation.show_menu_buttons()
    assert not core.menu_buttons["supplies"].visible
    assert core.menu_buttons["catlist_screen"].rect.left == core.menu_buttons["events_screen"].rect.right
    assert not core.menu_buttons["catlist_screen"].is_enabled
    assert not core.menu_buttons["clearing"].is_enabled
    assert core.menu_buttons["med_cat_den"].is_enabled
    assert core.menu_buttons["lead_den"].is_enabled
    with patch.object(navigation, "change_screen") as change:
        navigation.menu_button_pressed(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
            ui_element=core.menu_buttons["freshkill"]))
        change.assert_not_called()


def test_header_honors_visibility_preference_and_updates_after_moons(navigation):
    game.clan.clan_settings["moons and seasons"] = False
    navigation.update_moon_and_season()
    assert not core.menu_buttons["moon_indicator"].visible
    assert not core.menu_buttons["season_indicator"].visible
    game.clan.clan_settings["moons and seasons"] = True
    game.clan.age = 1
    game.clan.current_season = "Leaf-bare"
    navigation.update_moon_and_season()
    assert core.menu_buttons["moon_indicator"].tool_tip_text == "1 moon"
    assert core.menu_buttons["moon_indicator"].visible
    assert core.menu_buttons["season_indicator"].visible
    assert not core.menu_buttons["season_indicator"].check_hover(0.01, False)
    phase = core.moon_phase
    navigation.update_moon_and_season()
    assert core.moon_phase == phase
    game.clan.age = 2
    navigation.update_moon_and_season()
    assert core.menu_buttons["moon_indicator"].tool_tip_text == "2 moons"
    assert game.clan.current_season == "Leaf-bare"


def test_core_rebuild_cleans_up_widgets_and_heading_display_state(navigation):
    navigation.update_heading_text("Long Colony")
    state = navigation.display_change_save()
    assert state["heading"] == "Long Colony"
    count = len(MANAGER.get_sprite_group().sprites())
    for _ in range(3):
        old = core.menu_buttons["heading"]
        children = core.menu_dropdowns["dens"].child_button_container
        core.rebuild_core(should_rebuild_bgs=False)
        assert not old.alive() and not children.alive()
        assert len(MANAGER.get_sprite_group().sprites()) == count
    Screens.menu_buttons = core.menu_buttons
    navigation.display_change_load(state)
    assert core.menu_buttons["heading"].text == "Long Colony"


def test_camp_dispatches_dropdown_press_once(navigation):
    from scripts.screens.ClanScreen import ClanScreen

    screen = ClanScreen.__new__(ClanScreen)
    screen.cat_buttons = []
    for key in ("save_button", "label_toggle", "med_den_label", "clearing_label", "warrior_den_label", "leader_den_label"):
        setattr(screen, key, object())
    with patch.object(screen, "menu_button_pressed") as dispatch:
        event = pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=core.menu_buttons["dens"])
        screen.handle_event(event)
        dispatch.assert_called_once_with(event)


def test_long_heading_fits_without_losing_saved_name(navigation):
    name = "A Very Long Colony Name With Forty Eight Letters"
    navigation.update_heading_text(name)
    heading = core.menu_buttons["heading"]
    assert heading.text.endswith("...")
    assert heading.full_text == name
    assert name in heading.tool_tip_text
    state = navigation.display_change_save()
    navigation.update_heading_text("Other")
    navigation.display_change_load(state)
    assert heading.full_text == name
    assert game.clan.name == "NavigationTest"


def test_navigation_buttons_fit_text_with_matching_padding(navigation):
    for key in ("allegiances", "clan_settings"):
        button = core.menu_buttons[key]
        assert 18 <= button.rect.width - button.font.get_rect(button.text).width <= 21
    assert core.menu_buttons["allegiances"].rect.right == core.menu_buttons["clan_settings"].rect.right


def test_allegiances_heading_uses_plain_text(navigation):
    from scripts.screens.AllegiancesScreen import AllegiancesScreen

    screen = AllegiancesScreen("allegiances screen")
    with patch.object(screen, "get_allegiances_text", return_value=[]):
        screen.screen_switches()
    try:
        assert core.menu_buttons["heading"].text == "Allegiances"
    finally:
        screen.exit_screen()


def test_camp_dropdown_click_wins_over_large_colony_hitboxes(navigation, monkeypatch):
    from scripts.cat.cats import Cat
    from scripts.screens.ClanScreen import ClanScreen

    monkeypatch.setattr(Cat, "all_cats", {})
    monkeypatch.setattr(Cat, "all_cats_list", [])
    monkeypatch.setattr(Cat, "sprite", property(lambda cat: pygame.Surface((50, 50), pygame.SRCALPHA)))
    cats = [Cat(status="warrior", moons=30) for _ in range(35)]
    game.clan.clan_cats = [cat.ID for cat in cats]
    for cat in cats:
        cat.placement = (445, 170)
    screen = ClanScreen("camp screen")
    with patch.object(screen, "choose_cat_positions"):
        screen.screen_switches()
    try:
        dropdown = core.menu_dropdowns["dens"]
        dropdown.open()
        target = core.menu_buttons["clearing"]
        point = target.rect.center
        assert any(button.get_abs_rect().collidepoint(point) for button in screen.cat_buttons)
        assert all(button.button.get_top_layer() < target.get_top_layer() for button in screen.cat_buttons)
        pygame.event.clear()
        with patch.object(MANAGER, "get_mouse_position", return_value=point):
            MANAGER.update(0.016)
            MANAGER.process_events(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
            MANAGER.process_events(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=point))
        pressed = [event.ui_element for event in pygame.event.get() if event.type == pygame_gui.UI_BUTTON_START_PRESS]
        assert target in pressed, dropdown_state(dropdown)
        assert not any(button.button in pressed for button in screen.cat_buttons)
        screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=point))
        assert screen._dragging_cat_id is None
    finally:
        screen.exit_screen()


@pytest.fixture
def access_colony(monkeypatch):
    from scripts.cat.cats import Cat
    from scripts.cat.history import History
    from scripts.cat_relations.inheritance import Inheritance

    monkeypatch.setattr(Cat, "all_cats", {})
    monkeypatch.setattr(Cat, "all_cats_list", [])
    monkeypatch.setattr(Cat, "outside_cats", {})
    monkeypatch.setattr(Cat, "sprite", property(lambda cat: pygame.Surface((50, 50), pygame.SRCALPHA)))
    monkeypatch.setattr(Inheritance, "all_inheritances", {})
    monkeypatch.setattr(game, "all_screens", {})
    monkeypatch.setattr(game, "settings", game.settings.copy())
    monkeypatch.setattr(game, "safe_save", Mock(side_effect=AssertionError("No real save writes")))
    clan = Clan(name="AccessTest", game_mode="expanded", camp_bg="camp1")
    clan.clan_cats = []
    monkeypatch.setattr(game, "clan", clan)
    cats = [Cat(status="warrior", moons=30) for _ in range(2)]
    for cat in cats:
        cat.history = History()
        cat.create_inheritance_new_cat()
        clan.add_cat(cat)
    clan.your_cat = cats[0]
    clan.instructor = clan.demon = clan.wanderer = SimpleNamespace(ID="guide")
    clan.clan_settings["all accessories"] = False
    core.rebuild_core(should_rebuild_bgs=False)
    with patch.dict(game.switches, {"cat": cats[1].ID, "cur_screen": "profile screen"}):
        yield clan, cats
    Screens.hide_menu_buttons()


def test_colony_settings_routes_to_game_settings_and_cleans_up(access_colony):
    from scripts.screens.ClanSettingsScreen import ClanSettingsScreen

    screen = ClanSettingsScreen("clan settings screen")
    screen.screen_switches()
    button = screen.game_settings_button
    try:
        assert button.visible and button.is_enabled
        assert not button.rect.colliderect(screen.view_cards_button.rect)
        assert not button.rect.colliderect(screen.open_data_directory_button.rect)
        with patch.object(screen, "change_screen") as route:
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
            route.assert_called_once_with("settings screen")
    finally:
        screen.exit_screen()
    assert not button.alive()


@pytest.mark.parametrize("origin", ["start screen", "clan settings screen"])
def test_game_settings_returns_to_entry_after_display_rebuild(access_colony, monkeypatch, origin):
    from scripts.screens.SettingsScreen import SettingsScreen

    monkeypatch.setattr(game, "last_screen_forupdate", origin)
    screen = SettingsScreen("settings screen")
    screen.screen_switches()
    state = screen.display_change_save()
    screen.exit_screen()
    # Fullscreen changes replace the screen instance.
    screen = SettingsScreen("settings screen")
    screen.screen_switches()
    screen.display_change_load(state)
    try:
        assert screen.return_screen == origin
        with patch.object(screen, "change_screen") as route:
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.main_menu_button))
            route.assert_called_once_with(origin)
        monkeypatch.setitem(game.settings, "keybinds", True)
        with patch.object(screen, "change_screen") as route:
            screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            route.assert_called_once_with(origin)
    finally:
        screen.exit_screen()


@pytest.mark.parametrize("success", [True, False])
def test_settings_save_feedback_requires_success(access_colony, monkeypatch, success):
    from scripts.screens.SettingsScreen import SettingsScreen

    monkeypatch.setattr(game, "last_screen_forupdate", "clan settings screen")
    screen = SettingsScreen("settings screen")
    screen.screen_switches()
    screen.settings_changed = True
    screen.update_save_button()
    try:
        with patch.object(game, "save_settings", return_value=success) as save:
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.save_settings_button))
            save.assert_called_once_with(screen)
        assert screen.settings_changed is not success
        assert screen.save_settings_button.is_enabled is not success
    finally:
        screen.exit_screen()


@pytest.mark.parametrize("status,target", [
    ("leader", "leader den screen"), ("deputy", "warrior den screen"),
    ("warrior", "warrior den screen"), ("apprentice", "warrior den screen"),
    ("mediator", "mediation screen"), ("mediator apprentice", "mediation screen"),
    ("queen", "queen screen"), ("queen's apprentice", "queen screen"),
    ("medicine cat", "med den screen"), ("medicine cat apprentice", "med den screen"),
])
@pytest.mark.parametrize("is_player", [False, True])
def test_profile_den_shortcuts_follow_rank(access_colony, status, target, is_player):
    from scripts.screens.ProfileScreen import ProfileScreen

    clan, cats = access_colony
    cats[1].status = status
    if is_player:
        clan.your_cat = cats[1]
    screen = ProfileScreen("profile screen")
    screen.screen_switches()
    try:
        button = screen.profile_elements["med_den" if target == "med den screen" else "den"]
        assert button.visible and button.is_enabled
        with patch.object(screen, "change_screen") as route:
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
            route.assert_called_once_with(target)
        if target != "med den screen":
            cats[1].get_injured("sprain")
            screen.clear_profile()
            screen.build_profile()
            assert screen.profile_elements["med_den"].visible
            assert "den" not in screen.profile_elements
    finally:
        screen.exit_screen()


@pytest.mark.parametrize("state", ["dead", "outside", "shunned"])
def test_profile_shortcuts_preserve_activity_restrictions(access_colony, state):
    from scripts.screens.ProfileScreen import ProfileScreen

    clan, cats = access_colony
    cat = cats[1]
    cat.status = "queen"
    setattr(cat, state, 1 if state == "shunned" else True)
    screen = ProfileScreen("profile screen")
    screen.screen_switches()
    try:
        if state == "shunned":
            assert not screen.profile_elements["den"].is_enabled
        else:
            assert "den" not in screen.profile_elements
            assert not screen.profile_elements["med_den"].visible
    finally:
        screen.exit_screen()


@pytest.mark.parametrize("extra", [0, 3])
def test_moon_animation_matches_source_timing_and_survives_rebuild(navigation, extra):
    initial = core.moon_phase
    game.clan.age += 1
    with patch.object(core, "randint", return_value=extra):
        navigation.update_moon_and_season()
    frames = [(initial + i) % 8 for i in range(5 + extra)]
    assert core.moon_frames == frames
    moon = core.menu_buttons["moon_indicator"]
    moon.update(.124)
    assert core.moon_phase == initial and core.moon_frames == frames
    moon.update(.001)
    assert core.moon_phase == frames[0]
    moon.update(.125)
    assert core.moon_phase == frames[1]
    remaining = core.moon_frames.copy()
    core.rebuild_core(should_rebuild_bgs=False)
    Screens.menu_buttons = core.menu_buttons
    assert not moon.alive()
    assert core.moon_frames == remaining
    core.menu_buttons["moon_indicator"].update(1)
    assert not core.moon_frames
    assert core.moon_phase == frames[-1]
    assert str(game.clan.age) in core.menu_buttons["moon_indicator"].tool_tip_text


def test_moon_animation_updates_while_hidden_and_does_not_restart(navigation):
    game.clan.age += 1
    navigation.update_moon_and_season()
    final = core.moon_frames[-1]
    navigation.hide_menu_buttons()
    core.menu_buttons["moon_indicator"].update(2)
    assert not core.moon_frames and core.moon_phase == final
    navigation.show_menu_buttons()
    assert not core.moon_frames and core.moon_phase == final


def test_switching_colonies_at_same_age_resets_moon_without_animation(navigation):
    age = game.clan.age
    replacement = Clan(name="OtherMoonTest", game_mode="expanded", camp_bg="camp1")
    replacement.age = age
    with patch.object(game, "clan", replacement), patch.object(core, "randint", return_value=3):
        navigation.update_moon_and_season()
        assert core.moon_clan is replacement
        assert core.moon_phase == 3 and not core.moon_frames


def test_rewinding_colony_age_clears_pending_moon_cycle(navigation):
    game.clan.age += 2
    navigation.update_moon_and_season()
    assert core.moon_frames
    game.clan.age -= 1
    with patch.object(core, "randint", return_value=6):
        navigation.update_moon_and_season()
    assert core.moon_phase == 6 and not core.moon_frames



def test_heartless_profile_mate_control_is_explained_and_cannot_be_pressed(access_colony):
    from scripts.screens.ProfileScreen import ProfileScreen

    clan, cats = access_colony
    clan.game_mode, clan.cruel_cards = "cruel season", ["heartless"]
    screen = ProfileScreen("profile screen")
    screen.screen_switches()
    try:
        screen.toggle_relations_tab()
        screen.update_disabled_buttons_and_text()
        button = screen.choose_mate_button
        assert not button.is_enabled
        assert "manual mate changes" in button.tool_tip_text
        with patch.object(screen, "change_screen") as route:
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
        route.assert_not_called()
        clan.cruel_cards = []
        screen.update_disabled_buttons_and_text()
        assert button.is_enabled
    finally:
        screen.exit_screen()


@pytest.mark.parametrize("version,label", [("v2.0.0-alpha.1", "v2.0.0-alpha.1"),
    ("v2.0.0-alpha.1+0123456789abcdef", "v2.0.0-alpha.1+01234567"),
    ("0123456789abcdef", "01234567")])
def test_build_footer_preserves_prerelease_and_shortens_only_commit_metadata(navigation, monkeypatch, version, label):
    info = SimpleNamespace(version_number=version, is_source_build=True, is_dev=lambda: True)
    with monkeypatch.context() as patcher:
        patcher.setattr(core, "get_version_info", lambda: info)
        core.rebuild_core(should_rebuild_bgs=False)
        assert core.dev_watermark.text == "Build: " + label
        if "+" in version:
            bounds = MANAGER.get_root_container().get_rect()
            assert bounds.left <= core.dev_watermark.rect.left < core.dev_watermark.rect.right <= bounds.right
            assert core.dev_watermark.font.get_rect(core.dev_watermark.text).width <= core.dev_watermark.rect.width
    core.rebuild_core(should_rebuild_bgs=False)
