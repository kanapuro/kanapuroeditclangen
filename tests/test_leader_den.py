from copy import deepcopy
from unittest.mock import patch

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan, OtherClan
from scripts.game_structure.game_essentials import game
from scripts.screens.LeaderDenScreen import LeaderDenScreen


@pytest.fixture
def den(monkeypatch):
    for target, key, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                               (Cat, "outside_cats", {}), (Inheritance, "all_inheritances", {}),
                               (game, "all_screens", {}), (game, "cur_events_list", [])):
        monkeypatch.setattr(target, key, value)
    monkeypatch.setattr("scripts.utility.generate_sprite", lambda *args, **kwargs: pygame.Surface((50, 50), pygame.SRCALPHA))
    monkeypatch.setattr("scripts.screens.LeaderDenScreen.clan_symbol_sprite", lambda *args, **kwargs: pygame.Surface((50, 50), pygame.SRCALPHA))
    clan = Clan(name="DenTest", biome="Forest", camp_bg="camp1", game_mode="expanded")
    monkeypatch.setattr(game, "clan", clan)
    leader = Cat(status="leader", moons=40)
    leader.history = History()
    clan.leader = clan.your_cat = leader
    clan.add_cat(leader)
    outsider = Cat(status="loner", moons=30)
    outsider.outside = True
    outsider.history = History()
    neighbor = OtherClan(name="Neighbor", relations=10, chosen_symbol="symbolBEECH0")
    clan.all_clans = [neighbor]
    clan.clan_settings.update(lead_den_interaction=False, lead_den_clan_event={}, lead_den_outsider_event={})
    screen = LeaderDenScreen("leader den test")
    try:
        yield clan, leader, outsider, neighbor, screen
    finally:
        if screen.back_button and screen.back_button.alive():
            screen.exit_screen()


def press(screen, element):
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=element))


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_no_neighbors_can_open_both_tabs_and_return_to_camp(den, mode):
    clan, leader, outsider, neighbor, screen = den
    clan.game_mode = mode
    clan.all_clans = []
    screen.screen_switches()
    assert screen.focus_clan is None
    assert "no neighboring colonies" in screen.screen_elements["clan_notice_text"].html_text.lower()
    press(screen, screen.focus_frame_elements["outsiders_tab"])
    assert any(button.return_cat_object() is outsider for button in screen.outsider_cat_buttons.values())
    press(screen, screen.focus_frame_elements["clans_tab"])
    assert screen.focus_clan_container.visible
    assert "no neighboring colonies" in screen.screen_elements["clan_notice_text"].html_text.lower()
    with patch.object(screen, "change_screen") as leave:
        press(screen, screen.back_button)
        leave.assert_called_once()
    assert not clan.clan_settings["lead_den_clan_event"]


def test_reopening_saved_choices_does_not_reroll_or_replace_the_participant(den):
    clan, leader, outsider, neighbor, screen = den
    clan.clan_settings["lead_den_clan_event"] = {"cat_ID": leader.ID, "other_clan": neighbor.name,
        "player_clan_temper": clan.temperament, "interaction_type": "befriend", "success": False}
    clan.clan_settings["lead_den_outsider_event"] = {"cat_ID": outsider.ID,
        "interaction_type": "invite", "success": False}
    clan.clan_settings["lead_den_interaction"] = True
    before = deepcopy(clan.clan_settings)
    with patch("scripts.screens.LeaderDenScreen.random.random", return_value=0.99) as roll:
        screen.screen_switches()
        screen.open_outsiders_tab()
        screen.open_clans_tab()
        screen.open_outsiders_tab()
        assert clan.clan_settings == before
        roll.assert_not_called()
    assert "invite in" in screen.screen_elements["outsider_notice_text"].html_text
    assert "befriend" in screen.screen_elements["clan_notice_text"].html_text


@pytest.mark.parametrize("kind", ["colony", "outsider"])
def test_missing_saved_target_does_not_crash_or_change_the_plan(den, kind):
    clan, leader, outsider, neighbor, screen = den
    if kind == "colony":
        clan.clan_settings["lead_den_clan_event"] = {"cat_ID": leader.ID, "other_clan": "Gone",
            "player_clan_temper": clan.temperament, "interaction_type": "befriend", "success": False}
    else:
        clan.clan_settings["lead_den_outsider_event"] = {"cat_ID": "missing", "interaction_type": "invite", "success": False}
    before = deepcopy(clan.clan_settings)
    screen.screen_switches()
    screen.open_outsiders_tab()
    screen.open_clans_tab()
    assert clan.clan_settings == before


@pytest.mark.parametrize("working,expected", [(True, 0.6), (False, 0.5)])
def test_outsider_success_uses_actual_working_state(den, working, expected):
    clan, leader, outsider, neighbor, screen = den
    clan.reputation = 90
    screen.focus_cat = outsider
    with patch.object(leader, "not_working", return_value=not working), patch(
        "scripts.screens.LeaderDenScreen.random.random", return_value=0.55
    ):
        screen.handle_outsider_interaction("#outsider_invite")
    assert clan.clan_settings["lead_den_outsider_event"]["success"] == (0.55 < expected)


@pytest.mark.parametrize("unavailable", ["colony", "missing", "dead", "exiled", "outside", "no_text"])
def test_unavailable_diplomacy_does_not_block_outsider_plan_or_next_moon(den, monkeypatch, unavailable):
    from scripts.events import Events
    from scripts.events_module.generate_events import generate_events

    clan, leader, outsider, neighbor, screen = den
    clan.clan_settings["lead_den_clan_event"] = {"cat_ID": leader.ID, "other_clan": neighbor.name,
        "player_clan_temper": clan.temperament, "interaction_type": "befriend", "success": False}
    clan.clan_settings["lead_den_outsider_event"] = {"cat_ID": outsider.ID, "interaction_type": "invite", "success": False}
    clan.clan_settings["lead_den_interaction"] = True
    if unavailable == "colony":
        clan.all_clans = []
    elif unavailable == "missing":
        clan.clan_settings["lead_den_clan_event"]["cat_ID"] = "missing"
    elif unavailable != "no_text":
        setattr(leader, unavailable, True)
    observed = []
    def events(**kwargs):
        observed.append(kwargs["event_type"])
        return [] if kwargs["event_type"] == "other_clan" else [
            {"event_text": "m_c stays outside.", "rep_change": 0, "m_c": {}}]
    monkeypatch.setattr(generate_events, "possible_lead_den_events", events)
    Events().handle_lead_den_event()
    assert observed == (["other_clan", "outsider"] if unavailable == "no_text" else ["outsider"])
    assert not clan.clan_settings["lead_den_clan_event"]
    assert not clan.clan_settings["lead_den_outsider_event"]
    assert not clan.clan_settings["lead_den_interaction"]
    assert "stays outside" in game.cur_events_list[-1].text


@pytest.mark.parametrize("unavailable", ["missing", "dead", "driven_out", "joined", "no_text"])
def test_unavailable_outsider_plan_is_consumed_once(den, monkeypatch, unavailable):
    from scripts.events import Events
    from scripts.events_module.generate_events import generate_events

    clan, leader, outsider, neighbor, screen = den
    clan.clan_settings["lead_den_outsider_event"] = {"cat_ID": outsider.ID, "interaction_type": "invite", "success": True}
    clan.clan_settings["lead_den_interaction"] = True
    if unavailable == "missing":
        clan.clan_settings["lead_den_outsider_event"]["cat_ID"] = "missing"
    elif unavailable == "joined":
        outsider.outside = False
    elif unavailable != "no_text":
        setattr(outsider, unavailable, True)
    with patch.object(generate_events, "possible_lead_den_events", return_value=[]) as events:
        Events().handle_lead_den_event()
        Events().handle_lead_den_event()
        assert events.call_count == (1 if unavailable == "no_text" else 0)
    assert not clan.clan_settings["lead_den_outsider_event"]
    assert not clan.clan_settings["lead_den_interaction"]


def test_refresh_replaces_the_outsider_list_container(den):
    clan, leader, outsider, neighbor, screen = den
    screen.screen_switches()
    screen.open_outsiders_tab()
    previous = screen.outsider_cat_list_container
    screen.update_outsider_cats()
    assert not previous.alive()
    assert screen.outsider_cat_list_container.alive()


def test_clicked_choices_survive_settings_reload_and_are_only_displayed_on_return(den, monkeypatch, tmp_path):
    clan, leader, outsider, neighbor, screen = den
    monkeypatch.setattr("scripts.clan.get_save_dir", lambda: str(tmp_path))
    (tmp_path / clan.name).mkdir()
    screen.screen_switches()
    with patch("scripts.screens.LeaderDenScreen.random.random", return_value=0.99):
        press(screen, screen.focus_frame_elements["positive_interaction"])
        press(screen, screen.focus_frame_elements["outsiders_tab"])
        button = next(iter(screen.outsider_cat_buttons.values()))
        press(screen, button)
        press(screen, screen.focus_button["invite_in"])
    before = deepcopy(clan.clan_settings)
    clan.save_clan_settings()
    screen.exit_screen()
    for key in ("lead_den_clan_event", "lead_den_outsider_event"):
        clan.clan_settings[key] = {}
    clan.load_clan_settings()
    with patch("scripts.screens.LeaderDenScreen.random.random") as roll:
        screen.screen_switches()
        screen.open_outsiders_tab()
        roll.assert_not_called()
    assert clan.clan_settings == before
