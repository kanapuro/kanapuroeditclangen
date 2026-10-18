from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.cat_relations.relationship import Relationship
from scripts.clan import Clan
from scripts.events_module.patrol.patrol import Patrol
from scripts.events_module.patrol.patrol_event import PatrolEvent
from scripts.events_module.patrol.patrol_outcome import PatrolOutcome
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.windows import RelChangeDetailWindow
from scripts.screens.PatrolScreen import PatrolScreen
from scripts.screens.RelationshipScreen import RelationshipScreen
from scripts.screens.screens_core import screens_core as core
from scripts.utility import change_relationship_values


@pytest.fixture
def patrol_feedback(monkeypatch):
    for target, key, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                               (Cat, "outside_cats", {}), (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, key, value)
    monkeypatch.setattr(Cat, "sprite", property(lambda cat: pygame.Surface((50, 50)).convert_alpha()))
    monkeypatch.setattr(game, "all_screens", {})
    monkeypatch.setattr(game, "patrolled", [])
    monkeypatch.setattr(game, "safe_save", Mock(side_effect=AssertionError("No real save writes")))
    monkeypatch.setattr(game, "rpc", SimpleNamespace(update_rpc=Mock()))
    clan = Clan(name="PatrolFeedbackTest", biome="Forest", camp_bg="camp1", game_mode="expanded")
    clan.clan_cats = []
    monkeypatch.setattr(game, "clan", clan)
    cats = [Cat(status="warrior", moons=30) for _ in range(15)]
    for cat in cats:
        cat.history = History()
        cat.create_inheritance_new_cat()
        clan.add_cat(cat)
    clan.your_cat = cats[0]
    for source in cats:
        for target in cats:
            if source != target:
                source.relationships[target.ID] = Relationship(source, target)
    core.rebuild_core(should_rebuild_bgs=False)
    patrol = Patrol()
    with patch.dict(game.switches, {"patrol_category": "clangen", "patrolled": [],
                                   "window_open": False, "cat": cats[0].ID}), patch("scripts.screens.Screens.music_manager.check_music"):
        patrol.add_patrol_cats(cats[:2], clan)
        patrol.get_patrol_art = Mock(return_value=pygame.Surface((300, 300), pygame.SRCALPHA))
        outcome = PatrolOutcome(text="p_l and r_c return to camp.", exp=0)
        patrol.patrol_event = PatrolEvent("feedback_test", intro_text="The patrol leaves camp.",
            decline_text="The patrol stays in camp.", success_outcomes=[outcome], fail_outcomes=[outcome],
            antag_success_outcomes=[outcome], antag_fail_outcomes=[outcome])
        yield patrol, clan, cats, outcome
        for window in MANAGER.get_window_stack().get_full_stack().copy():
            window.kill()


def test_actual_changes_respect_caps_romance_restrictions_and_all_seven_values(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    source, target = cats[:2]
    rel = source.relationships[target.ID]
    rel.trust = 98
    changes = {}
    with patch.object(source, "is_potential_mate", return_value=False):
        result = change_relationship_values([target], [source], romantic_love=10, platonic_like=4,
            dislike=5, admiration=6, comfortable=7, jealousy=-3, trust=10, changes=changes)
    assert result is None
    assert changes == {(source.ID, target.ID): {
        "platonic_like": (0, 4), "dislike": (0, 5), "admiration": (0, 6),
        "comfortable": (0, 7), "trust": (98, 100)}}
    with patch.object(source, "is_potential_mate", return_value=True):
        change_relationship_values([target], [source], romantic_love=3, jealousy=2, changes=changes)
    assert changes[(source.ID, target.ID)]["romantic_love"] == (0, 3)
    assert changes[(source.ID, target.ID)]["jealousy"] == (0, 2)
    assert (target.ID, source.ID) not in changes


def test_repeated_blocks_report_net_change_without_stale_zero_effects(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    source, target = cats[:2]
    changes = {}
    change_relationship_values([target], [source], trust=5, changes=changes)
    change_relationship_values([target], [source], trust=7, changes=changes)
    assert changes[(source.ID, target.ID)]["trust"] == (0, 12)
    change_relationship_values([target], [source], trust=-12, changes=changes)
    assert changes == {}
    change_relationship_values([source], [source], trust=9, changes=changes)
    assert changes == {}


def test_mutual_and_clan_blocks_include_cats_outside_the_patrol(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    outcome.relationship_effects = [{"cats_from": ["p_l"], "cats_to": ["clan"],
        "values": ["trust"], "amount": 5, "mutual": True, "log": "They return together."}]
    result = outcome.execute_outcome(patrol)
    assert len(result) == 3
    leader = patrol.patrol_leader
    assert len(patrol.relationship_changes) == 28
    for cat in cats:
        if cat != leader:
            assert patrol.relationship_changes[(leader.ID, cat.ID)] == {"trust": (0, 5)}
            assert patrol.relationship_changes[(cat.ID, leader.ID)] == {"trust": (0, 5)}
            assert cat.relationships[leader.ID].log


@pytest.mark.parametrize("success", [True, False])
def test_date_feedback_includes_direct_and_outcome_changes(patrol_feedback, success):
    patrol, clan, cats, outcome = patrol_feedback
    game.switches["patrol_category"] = "date"
    target = cats[1]
    patrol.random_cat = target
    for source, other in ((clan.your_cat, target), (target, clan.your_cat)):
        source.relationships[other.ID].romantic_love = 20
        source.relationships[other.ID].trust = 20
        source.relationships[other.ID].comfortable = 20
    def calculate(*args):
        # The date chance calculation has its own mutual romance bonus.
        clan.your_cat.relationships[target.ID].romantic_love += 10
        target.relationships[clan.your_cat.ID].romantic_love += 10
        return outcome, success
    with patch.object(patrol, "calculate_success", side_effect=calculate), patch("scripts.events_module.patrol.patrol.randint", return_value=2):
        result = patrol.proceed_patrol()
    assert len(result) == 3
    expected = 32 if success else 28
    assert patrol.relationship_changes[(target.ID, clan.your_cat.ID)]["romantic_love"] == (20, expected)
    assert patrol.relationship_changes[(target.ID, clan.your_cat.ID)]["trust"] == (20, 22 if success else 18)


def test_decline_clears_previous_feedback_without_changing_relationships(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    patrol.relationship_changes = {("old", "cat"): {"trust": (0, 5)}}
    result = patrol.proceed_patrol("decline")
    assert len(result) == 3 and result[1] == ""
    assert patrol.relationship_changes == {}
    assert cats[0].relationships[cats[1].ID].trust == 0


def test_feedback_window_pages_tooltips_and_relationship_route(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    changes = {(cat.ID, cats[-1].ID): {"trust": (2, 7), "dislike": (9, 6)} for cat in cats[:-1]}
    screen = PatrolScreen("patrol screen")
    with patch.object(screen, "change_screen") as route:
        window = RelChangeDetailWindow(changes, screen)
        assert window.is_blocking
        assert len(window.cat_list.cat_sprites) == 12
        first = window.cat_list.cat_sprites["sprite0"].button
        assert "Trust +5" in first.tool_tip_text and "Dislike -3" in first.tool_tip_text
        assert not window.previous_page_button.is_enabled
        window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=window.next_page_button))
        assert window.current_page == 2
        assert len(window.cat_list.cat_sprites) == 2
        last = window.cat_list.cat_sprites["sprite1"].button
        assert last.return_cat_id() == cats[13].ID and "Trust +5" in last.tool_tip_text
        window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_PRESSED, ui_element=last))
        route.assert_called_once_with("relationship screen")
        assert game.switches["cat"] == cats[13].ID
        assert not window.alive() and not window.fade.alive() and not window.box.alive()


@pytest.mark.parametrize("key", [pygame.K_ESCAPE, None])
def test_feedback_close_preserves_outcome_and_removes_overlay(patrol_feedback, key):
    patrol, clan, cats, outcome = patrol_feedback
    window = RelChangeDetailWindow({(cats[0].ID, cats[1].ID): {"trust": (0, 4)}}, Mock())
    event = pygame.event.Event(pygame.KEYDOWN, key=key) if key else pygame.event.Event(
        pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.back_button)
    assert window.process_event(event)
    assert not window.alive() and not window.fade.alive() and not window.box.alive()


def prepare_result(patrol, cats):
    screen = PatrolScreen("patrol screen")
    screen.patrol_obj = patrol
    screen.current_patrol = cats[:2]
    screen.display_text = "The patrol returns."
    screen.results_text = "Everyone is safe."
    screen.open_patrol_event_screen()
    screen.open_patrol_complete_screen()
    return screen


def test_outcome_button_and_return_do_not_run_the_patrol_twice(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    patrol.relationship_changes = {(cats[0].ID, cats[1].ID): {"trust": (0, 4)}}
    screen = prepare_result(patrol, cats)
    with patch.object(patrol, "proceed_patrol", side_effect=AssertionError("Outcome replayed")):
        screen.handle_patrol_complete_events(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
            ui_element=screen.elements["rel_detail"]))
        window = MANAGER.get_window_stack().get_full_stack()[-1]
        assert isinstance(window, RelChangeDetailWindow)
        window.kill()
        screen.exit_screen()
        screen.screen_switches()
        assert screen.patrol_stage == "patrol_complete"
        assert screen.results_text == "Everyone is safe."
        assert "rel_detail" in screen.elements
        assert not screen.elements["proceed"].is_enabled
        screen.exit_screen()


def test_feedback_button_hidden_without_changes_and_return_clears_cache(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    screen = prepare_result(patrol, cats)
    assert "rel_detail" not in screen.elements
    screen.handle_patrol_complete_events(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
        ui_element=screen.elements["clan_return"]))
    screen.exit_screen()
    assert screen.in_progress_data is None


@pytest.mark.parametrize("origin,expected", [("patrol screen", "patrol screen"), ("profile screen", "profile screen")])
def test_relationship_back_preserves_existing_profile_route(patrol_feedback, monkeypatch, origin, expected):
    monkeypatch.setattr(game, "last_screen_forupdate", origin)
    screen = RelationshipScreen("relationship screen")
    screen.screen_switches()
    try:
        with patch.object(screen, "change_screen") as route:
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.back_button))
            route.assert_called_once_with(expected)
    finally:
        screen.exit_screen()


@pytest.mark.parametrize("path", ["proceed", "antag"])
@pytest.mark.parametrize("success", [True, False])
def test_all_outcome_paths_capture_actual_effects(patrol_feedback, path, success):
    patrol, clan, cats, outcome = patrol_feedback
    outcome.relationship_effects = [{"cats_from": ["p_l"], "cats_to": ["r_c"],
        "values": ["respect", "comfort"], "amount": 5}]
    with patch.object(patrol, "calculate_success", return_value=(outcome, success)):
        assert len(patrol.proceed_patrol(path)) == 3
    pair = (patrol.patrol_leader.ID, patrol.random_cat.ID)
    assert patrol.relationship_changes[pair] == {"admiration": (0, 5), "comfortable": (0, 5)}


@pytest.mark.parametrize("invalid", ["moon", "colony"])
def test_old_outcomes_are_not_restored_after_moon_or_colony_changes(patrol_feedback, monkeypatch, invalid):
    patrol, clan, cats, outcome = patrol_feedback
    screen = prepare_result(patrol, cats)
    screen.exit_screen()
    if invalid == "moon":
        clan.age += 1
    else:
        replacement = Clan(name=clan.name, biome="Forest", camp_bg="camp1", game_mode="expanded")
        replacement.clan_cats = clan.clan_cats.copy()
        replacement.your_cat = clan.your_cat
        monkeypatch.setattr(game, "clan", replacement)
    screen.screen_switches()
    try:
        assert screen.patrol_stage == "choose_cats"
        assert screen.patrol_obj is not patrol
        assert screen.in_progress_data is None
    finally:
        screen.exit_screen()


def test_display_rebuild_waits_for_pending_outcome_without_replaying_it(patrol_feedback):
    from scripts.game_structure.propagating_thread import PropagatingThread

    patrol, clan, cats, outcome = patrol_feedback
    screen = prepare_result(patrol, cats)
    screen.patrol_stage = "patrol_events"
    with patch.object(patrol, "proceed_patrol", return_value=("Finished.", "Safe.", None)) as proceed:
        screen.proceed_patrol_thread = PropagatingThread(target=screen.run_patrol_proceed, args=("proceed",))
        screen.proceed_patrol_thread.start()
        state = screen.display_change_save()
        assert state["patrol_stage"] == "patrol_complete"
        screen.exit_screen()
        rebuilt = PatrolScreen("patrol screen")
        rebuilt.screen_switches()
        rebuilt.display_change_load(state)
        try:
            assert rebuilt.patrol_stage == "patrol_complete"
            assert rebuilt.display_text == "Finished." and rebuilt.results_text == "Safe."
            assert rebuilt.proceed_patrol_thread is None
            proceed.assert_called_once_with("proceed")
        finally:
            rebuilt.exit_screen()


@pytest.mark.parametrize("favorite", [0, 1, 2, 3])
def test_real_hover_reaches_selected_and_favorite_cat_sprites(patrol_feedback, favorite):
    patrol, clan, cats, outcome = patrol_feedback
    cats[0].favourite = favorite
    clan.clan_settings["show fav"] = True
    window = RelChangeDetailWindow({(cats[0].ID, cats[1].ID): {"trust": (0, 4)}}, Mock())
    MANAGER.update(.01)
    sprite = window.cat_list.cat_sprites["sprite0"].button
    window.cat_list.selection_boxes["sprite0"].show()
    with patch.object(MANAGER, "get_mouse_position", return_value=sprite.rect.center):
        for _ in range(15):
            MANAGER.update(.1)
    try:
        assert sprite.hovered
        assert sprite.tool_tip is not None
        assert sprite.tool_tip.text_block.layer > window.cat_list.cat_sprites["sprite0"].image.layer
        assert "Trust +4" in sprite.tool_tip_text
    finally:
        sprite.on_unhovered()
        window.kill()


def test_missing_patrol_does_not_cache_a_failed_event(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    screen = PatrolScreen("patrol screen")
    screen.patrol_obj = patrol
    screen.current_patrol = cats[:2]
    screen.display_text = None
    with patch.object(screen, "change_screen") as route:
        screen.open_patrol_event_screen()
        route.assert_called_once_with("camp screen")
    screen.exit_screen()
    assert screen.in_progress_data is None
