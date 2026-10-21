from unittest.mock import Mock, patch

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.clan import Clan
from scripts.event_class import Single_Event
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.screens.EventsScreen import EventsScreen
from scripts.screens.Screens import Screens
from scripts.screens.screens_core import screens_core as core


@pytest.fixture
def events_screen(monkeypatch):
    with monkeypatch.context() as isolated:
        isolated.setattr(Cat, "all_cats", {})
        isolated.setattr(Cat, "all_cats_list", [])
        isolated.setattr(Cat, "sprite", property(lambda cat: pygame.Surface((50, 50), pygame.SRCALPHA)))
        isolated.setattr(game, "all_screens", {})
        isolated.setattr(game, "cur_events_list", [])
        isolated.setattr(game, "safe_save", Mock(side_effect=AssertionError("No save writes")))
        clan = Clan(name="EventTest", game_mode="expanded", camp_bg="camp1")
        clan.age = 12
        player = Cat(status="warrior", moons=30)
        clan.your_cat = player
        clan.clan_cats = [player.ID]
        isolated.setattr(game, "clan", clan)
        core.rebuild_core(should_rebuild_bgs=False)
        with patch.dict(game.switches, {"saved_scroll_positions": {}, "continue_after_death": False, "saved_clan": False}), patch(
            "scripts.screens.EventsScreen.clan_symbol_sprite", return_value=pygame.Surface((50, 50))
        ):
            screen = EventsScreen("events screen")
            screen.screen_switches()
            yield screen
            screen.exit_screen()
            screen.hide_menu_buttons()
    core.rebuild_core(should_rebuild_bgs=False)
    Screens.menu_buttons = core.menu_buttons


def press(screen, button):
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=button))


def populate(screen, count, kind="misc", cats=None):
    game.cur_events_list = [Single_Event(f"Event {i}", kind, cats) for i in range(count)]
    screen.update_events_display()


@pytest.mark.parametrize("count,pages,rows", [(0, 1, 0), (1, 1, 1), (10, 1, 10), (11, 2, 10), (300, 30, 10)])
def test_event_pages_bound_rendered_rows(events_screen, count, pages, rows):
    populate(events_screen, count)
    assert events_screen.current_page_amount == pages
    assert len(events_screen.event_display_boxes) == rows
    assert bool(events_screen.page_control) == (pages > 1)


def test_page_routes_boundaries_tab_memory_and_profile_return(events_screen):
    screen = events_screen
    populate(screen, 23, cats=[game.clan.your_cat.ID])
    assert not screen.page_control["first"].is_enabled
    press(screen, screen.page_control["next"])
    assert screen.current_page == 2
    assert screen.event_display_boxes[0].html_text == "Event 10"
    press(screen, screen.page_control["last"])
    assert len(screen.event_display_boxes) == 3
    assert not screen.page_control["next"].is_enabled
    screen.handle_tab_switch("health")
    assert screen.current_page == 1 and not screen.page_control
    screen.handle_tab_switch("all events")
    assert screen.current_page == 3
    screen.exit_screen()
    with patch("scripts.screens.EventsScreen.clan_symbol_sprite", return_value=pygame.Surface((50, 50))):
        screen.screen_switches()
    assert screen.current_page == 3
    press(screen, screen.page_control["previous"])
    assert screen.current_page == 2
    press(screen, screen.page_control["first"])
    assert screen.current_page == 1


def test_favorite_union_is_ordered_unique_and_refreshes_on_deselect(events_screen):
    screen = events_screen
    player = game.clan.your_cat
    player.favourite = 1
    friend = Cat(status="warrior", moons=30)
    friend.favourite = 1
    shared = Single_Event("Shared", "misc", [player.ID, friend.ID])
    interaction = Single_Event("Interaction", ["relation", "interaction"], [friend.ID])
    ordinary = Single_Event("Ordinary", "misc", ["unavailable"])
    game.cur_events_list = [ordinary, shared, interaction]
    screen.update_events_display()
    press(screen, screen.fave_filter_elements["fave_group_1"])
    assert [event.text for event in screen.display_events] == ["Shared", "Interaction"]
    assert len(screen.event_display_boxes) == 2
    press(screen, screen.fave_filter_elements["fave_group_1_selected"])
    assert [event.text for event in screen.display_events] == ["Ordinary", "Shared"]
    assert len(screen.event_display_boxes) == 2
    press(screen, screen.fave_filter_elements["yourcat_filter"])
    assert [event.text for event in screen.display_events] == ["Shared"]


def test_filter_and_faith_changes_reset_page_and_clear_old_scroll(events_screen):
    screen = events_screen
    player = game.clan.your_cat
    populate(screen, 30, cats=[player.ID])
    press(screen, screen.page_control["last"])
    game.switches["saved_scroll_positions"]["all events"] = 0.75
    press(screen, screen.fave_filter_elements["yourcat_filter"])
    assert screen.current_page == 1
    assert "all events" not in game.switches["saved_scroll_positions"]
    game.cur_events_list += [Single_Event("Interaction", ["relation", "interaction"], [player.ID])] * 21
    game.cur_events_list += [Single_Event("Faith", "faith", [player.ID])]
    screen.handle_tab_switch("relationships")
    press(screen, screen.page_control["last"])
    press(screen, screen.faith_toggle_button)
    assert screen.current_page == 1
    assert [event.text for event in screen.display_events] == ["Faith"]
    assert not screen.page_control


def test_display_restore_keeps_filters_page_and_scroll(events_screen):
    screen = events_screen
    populate(screen, 30, cats=[game.clan.your_cat.ID])
    press(screen, screen.fave_filter_elements["yourcat_filter"])
    press(screen, screen.page_control["next"])
    screen.filters_open = True
    MANAGER.update(0.1)
    screen.event_display.vert_scroll_bar.set_scroll_from_start_percentage(0.4)
    state = screen.display_change_save()
    scroll = game.switches["saved_scroll_positions"]["all events"]
    assert scroll > 0
    screen.selected_fave_filter = []
    screen.saved_page_positions = {}
    screen.display_change_load(state)
    assert screen.selected_fave_filter == ["yourcat_filter"]
    assert screen.current_page == 2
    assert screen.filters_open
    bar = screen.event_display.vert_scroll_bar
    assert bar.scroll_position / bar.scrollable_height == pytest.approx(scroll)
    assert screen.fave_filter_elements["yourcat_filter_selected"].visible


def test_missing_cat_ids_do_not_break_involved_links_or_page_changes(events_screen):
    screen = events_screen
    player = game.clan.your_cat
    populate(screen, 12, cats=["missing", player.ID, "missing-again"])
    press(screen, screen.involved_cat_buttons[0])
    assert [button.cat_id for button in screen.cat_profile_buttons] == [player.ID]
    press(screen, screen.involved_cat_buttons[0])
    assert not screen.cat_profile_buttons and screen.involved_cat_container is None
    press(screen, screen.involved_cat_buttons[0])
    opened = screen.open_involved_cat_button
    press(screen, screen.page_control["next"])
    assert not opened.alive()
    assert screen.open_involved_cat_button is None
    press(screen, screen.involved_cat_buttons[0])
    assert screen.cat_profile_buttons[0].cat_id == player.ID


def test_shorter_list_and_new_moon_clear_page_state(events_screen):
    screen = events_screen
    populate(screen, 30)
    press(screen, screen.page_control["last"])
    populate(screen, 1)
    assert screen.current_page == 1 and not screen.page_control
    screen.saved_page_positions["health"] = 9
    screen.timeskip_done()
    assert screen.current_page == 1
    assert screen.saved_page_positions == {}


def test_empty_moon_keeps_existing_message_and_new_clan_clears_pager(events_screen):
    screen = events_screen
    game.cur_events_list = []
    screen.timeskip_done()
    assert screen.event_display_boxes[0].html_text == "Nothing interesting happened this moon."
    populate(screen, 30)
    game.clan.age = 0
    screen.update_events_display()
    assert not screen.event_display_boxes and not screen.page_control


def test_timeskip_from_other_tab_restores_favorite_controls(events_screen):
    screen = events_screen
    populate(screen, 12)
    screen.handle_tab_switch("health")
    assert not screen.fave_filter_elements["cat_icon"].visible
    screen.timeskip_done()
    assert screen.current_display == "all events"
    assert screen.fave_filter_elements["cat_icon"].visible


@pytest.mark.parametrize("ids", [["missing"], ["missing", "missing-again", "missing-third"]])
def test_unavailable_involved_cats_leave_no_profile_buttons(events_screen, ids):
    populate(events_screen, 1, cats=ids)
    press(events_screen, events_screen.involved_cat_buttons[0])
    assert not events_screen.cat_profile_buttons
    press(events_screen, events_screen.involved_cat_buttons[0])
    assert events_screen.involved_cat_container is None


def test_colony_switch_does_not_reuse_old_event_pages(events_screen):
    screen = events_screen
    populate(screen, 30)
    press(screen, screen.page_control["last"])
    screen.exit_screen()
    other = Clan(name="OtherEvents", game_mode="expanded", camp_bg="camp1")
    other.age = 3
    other.your_cat = game.clan.your_cat
    with patch.object(game, "clan", other), patch(
        "scripts.screens.EventsScreen.clan_symbol_sprite", return_value=pygame.Surface((50, 50))
    ):
        screen.screen_switches()
        assert screen.current_page == 1
        assert not screen.saved_page_positions


def test_pager_is_below_the_event_viewport(events_screen):
    populate(events_screen, 30)
    for button in events_screen.page_control.values():
        assert button.rect.top > events_screen.events_frame.rect.bottom
        assert not button.rect.colliderect(events_screen.event_display.rect)


def test_events_save_runs_existing_save_steps_and_confirms_success(events_screen):
    screen = events_screen
    with patch.object(game, "save_cats") as cats, patch.object(game.clan, "save_clan") as clan, patch.object(
        game.clan, "save_pregnancy"
    ) as pregnancy, patch.object(game, "save_events") as events, patch.object(game, "save_settings") as settings:
        press(screen, screen.save_button)
        cats.assert_called_once_with()
        clan.assert_called_once_with()
        pregnancy.assert_called_once_with(game.clan)
        events.assert_called_once_with()
        settings.assert_called_once_with(screen)
        assert game.switches["saved_clan"]
        assert screen.save_states["saved"].visible
        assert not screen.save_states["saving"].visible
        assert not screen.save_button.is_enabled
        press(screen, screen.save_button)
        cats.assert_called_once()
    assert not screen.save_button.rect.colliderect(screen.timeskip_button.rect)
    assert not screen.save_button.rect.colliderect(screen.death_button.rect)


def test_events_cannot_save_during_timeskip(events_screen):
    screen = events_screen
    screen.events_thread = Mock()
    screen.events_thread.is_alive.return_value = True
    with patch.object(game, "save_cats") as save:
        press(screen, screen.save_button)
        save.assert_not_called()
    screen.update_save_button()
    assert not screen.save_button.is_enabled
    screen.events_thread.is_alive.return_value = False
    screen.update_save_button()
    assert screen.save_button.is_enabled


def test_events_save_error_does_not_report_success(events_screen):
    screen = events_screen
    with patch.object(game, "save_cats", side_effect=RuntimeError("Save failed")), patch(
        "scripts.screens.EventsScreen.SaveError"
    ) as error, patch.object(screen, "change_screen") as route:
        press(screen, screen.save_button)
        error.assert_called_once()
        assert "Save failed" in error.call_args.args[0]
        route.assert_called_once_with("start screen")
    assert not game.switches["saved_clan"]
    assert not screen.save_states["saved"].visible


def test_settings_save_failure_does_not_mark_colony_saved(events_screen):
    screen = events_screen
    with patch.object(game, "save_cats"), patch.object(game.clan, "save_clan"), patch.object(
        game.clan, "save_pregnancy"
    ), patch.object(game, "save_events"), patch.object(game, "safe_save", side_effect=RuntimeError("Settings failed")), patch(
        "scripts.game_structure.windows.SaveError"
    ) as error, patch.object(screen, "change_screen") as route:
        press(screen, screen.save_button)
        error.assert_called_once()
        route.assert_called_once_with("start screen")
    assert not game.switches["saved_clan"]
    assert not screen.save_states["saved"].visible


def test_timeskip_completion_starts_header_animation_and_refreshes_age(events_screen):
    game.clan.age += 1
    assert not core.moon_frames
    events_screen.timeskip_done()
    assert core.moon_age == game.clan.age
    assert 5 <= len(core.moon_frames) <= 8
    assert str(game.clan.age) in core.menu_buttons["moon_indicator"].tool_tip_text


def test_context_only_cats_stay_out_of_links_and_filters_after_reload(events_screen, tmp_path, monkeypatch):
    import json
    from scripts.cat.history import History
    from scripts.events_module.short.handle_short_events import HandleShortEvents
    from scripts.events_module.short.short_event import ShortEvent
    from scripts.events_module.generate_events import GenerateEvents

    screen = events_screen
    actor = game.clan.your_cat
    actor.history = History()
    context = Cat(status="warrior", moons=30)
    context.favourite = 1
    event = ShortEvent(event_id="context_test", text="m_c notices r_c.",
        r_c={"age": ["any"]}, exclude_involved=["r_c"])
    with patch.object(GenerateEvents, "possible_short_events", return_value=[event]), patch.object(
        GenerateEvents, "filter_possible_short_events", return_value=[event]):
        HandleShortEvents().handle_event("misc", actor, context, None)
    monkeypatch.setattr(game, "other_events_list", [])
    monkeypatch.setattr("scripts.game_structure.game_essentials.get_save_dir", lambda: str(tmp_path))
    (tmp_path / game.clan.name).mkdir()
    guard = game.safe_save
    with patch.object(game, "safe_save", type(game).safe_save):
        game.save_events()
    assert game.safe_save is guard
    data = json.loads((tmp_path / game.clan.name / "events.json").read_text(encoding="utf-8"))
    assert data[0]["cats_involved"] == [actor.ID]
    game.cur_events_list = []
    game.load_events()
    assert game.cur_events_list[0].cats_involved == [actor.ID]
    screen.update_events_display()
    press(screen, screen.involved_cat_buttons[0])
    assert [button.cat_id for button in screen.cat_profile_buttons] == [actor.ID]
    press(screen, screen.fave_filter_elements["fave_group_1"])
    assert not screen.display_events
