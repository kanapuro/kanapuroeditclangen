import json
from pathlib import Path
from copy import deepcopy
from unittest.mock import Mock, patch

import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.cat_relations.relationship import Relationship
from scripts.clan import Clan
from scripts.events_module.event_frequency import select_frequency
from scripts.events_module.future_event import FutureEvent, prep_future_event, trigger_future_events
from scripts.events_module.generate_events import GenerateEvents
from scripts.events_module.patrol.patrol import Patrol
from scripts.events_module.patrol.patrol_event import PatrolEvent
from scripts.events_module.patrol.patrol_outcome import PatrolOutcome
from scripts.events_module.short.handle_short_events import HandleShortEvents
from scripts.events_module.short.short_event import ShortEvent
from scripts.game_structure.game_essentials import game


@pytest.fixture
def colony(monkeypatch):
    for target, name, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                                (Cat, "outside_cats", {}), (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, name, value)
    clan = Clan(name="ContractsTest", biome="Forest", camp_bg="camp1", game_mode="expanded")
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setattr(game, "cur_events_list", [])
    monkeypatch.setattr(game, "safe_save", Mock(side_effect=AssertionError("No real save writes")))
    cats = [Cat(prefix=prefix, status="warrior", moons=30) for prefix in ("Moss", "Bee", "Fern")]
    for cat in cats:
        cat.history = History()
        cat.create_inheritance_new_cat()
        clan.add_cat(cat)
    clan.your_cat = cats[0]
    return clan, cats


def filter_events(events, cats, **kwargs):
    return GenerateEvents.filter_possible_short_events(Cat, events, cats[0], cats[1], None, False, 1, [], **kwargs)


@pytest.mark.parametrize("roll,frequency", [(1, 4), (4, 4), (5, 3), (7, 3), (8, 2), (9, 2), (10, 1)])
def test_frequency_rolls_match_released_distribution(roll, frequency):
    events = [ShortEvent(event_id=str(f), frequency=f) for f in range(1, 5)]
    with patch("scripts.events_module.event_frequency.randint", return_value=roll):
        assert select_frequency(events) == [events[frequency - 1]]


@pytest.mark.parametrize("roll", [1, 5, 8, 10])
def test_empty_frequency_pools_fall_back_without_losing_weights(roll):
    event = ShortEvent(event_id="fallback", frequency=2)
    with patch("scripts.events_module.event_frequency.randint", return_value=roll):
        assert select_frequency([event] * 3) == [event] * 3
        assert select_frequency([]) == []


def test_legacy_pool_is_unchanged_and_shares_common_pool_with_new_events():
    old = ShortEvent(event_id="old", weight=20)
    rare = ShortEvent(event_id="rare", frequency=1)
    with patch("scripts.events_module.event_frequency.randint", side_effect=AssertionError("Legacy pool must not roll")):
        assert select_frequency([old] * 20) == [old] * 20
    with patch("scripts.events_module.event_frequency.randint", return_value=1):
        assert select_frequency([old] * 20 + [rare]) == [old] * 20


def test_constraint_weights_and_explicit_weight_compatibility():
    plain = ShortEvent(event_id="plain", frequency=4)
    limited = ShortEvent(event_id="limited", frequency=4, location=["forest:camp1"],
                         season=["newleaf"], m_c={"status": ["queen"], "age": ["adult"]})
    assert limited.weight == plain.weight + 1 + 3 + len(Cat.rank_sort_order) - 1 + len(Cat.ages) - 1
    assert ShortEvent(event_id="manual", frequency=1, weight=7).weight == 7
    plain_patrol = PatrolEvent("plain", frequency=4)
    limited_patrol = PatrolEvent("limited", frequency=4, camp=["camp1"], season=["newleaf"],
                                 relationship_constraints=["siblings"])
    assert limited_patrol.weight == plain_patrol.weight + 8 + 12 + 20
    assert PatrolEvent("manual", frequency=1, weight=9).weight == 9
    assert PatrolEvent("legacy").weight == 20


def test_readers_preserve_frequency_and_empty_companion_requirement(colony, tmp_path, monkeypatch):
    folder = tmp_path / "misc"
    folder.mkdir()
    (folder / "general.json").write_text(json.dumps([
        {"event_id": "new", "event_text": "m_c notices r_c.", "frequency": 1, "r_c": {}},
        {"event_id": "legacy", "event_text": "m_c rests.", "weight": 8}]), encoding="utf-8")
    monkeypatch.setattr("scripts.events_module.generate_events.resource_directory", str(tmp_path) + "/")
    monkeypatch.setattr(GenerateEvents, "loaded_events", {})
    new, old = GenerateEvents.generate_short_events("misc", "general")
    assert new.frequency == 1 and new.weight == 1 and new.r_c
    assert old.frequency is None and old.weight == 8
    generated = Patrol().generate_patrol_events([{"patrol_id": "new_patrol", "frequency": 2}])
    assert generated[0].frequency == 2 and generated[0].weight > 0


def test_faith_weights_do_not_decay_in_cache_and_companion_uses_own_flags(colony):
    _, cats = colony
    cats[0].faith = -1
    cats[1].faith = -1
    event = ShortEvent(event_id="faith", weight=20, faith_effect=1,
                       m_c={"affected": False}, r_c={"affected": True})
    for _ in range(6):
        assert len(filter_events([event], cats)) == 13
        assert event.weight == 20
    cats[1].faith = 1
    assert len(filter_events([event], cats)) == 20


@pytest.mark.parametrize("role", ["m_c", "r_c"])
@pytest.mark.parametrize("has_skill", [False, True])
def test_trait_and_skill_constraints_require_both(colony, role, has_skill):
    _, cats = colony
    actor = cats[0 if role == "m_c" else 1]
    event = ShortEvent(event_id="constrained", weight=1, tags=["skill_trait_required"],
                      **{role: {"trait": [actor.personality.trait], "skill": ["HUNTER,1"]}})
    with patch.object(actor.skills, "meets_skill_requirement", return_value=has_skill):
        assert bool(filter_events([event], cats)) == has_skill


def test_camp_constraint_requires_matching_camp_as_well_as_biome(colony):
    _, cats = colony
    event = ShortEvent(event_id="other_camp", weight=1, location=["forest:camp2"])
    assert not filter_events([event], cats)
    event.location = ["forest:camp1"]
    assert filter_events([event], cats)


def followup_info(delay=1, **kwargs):
    return {"event_type": "misc", "pool": {"event_id": ["followup"]}, "moon_delay": [delay, delay],
            "involved_cats": {"m_c": "r_c", "r_c": "m_c"}, **kwargs}


def test_real_parent_execution_schedules_and_followup_executes_once(colony):
    clan, cats = colony
    parent = ShortEvent(event_id="parent", weight=1, text="m_c notices r_c.",
                        r_c={"age": ["any"]}, future_event=[followup_info(2)])
    followup = ShortEvent(event_id="followup", weight=1, text="m_c remembers r_c.",
                          r_c={"age": ["any"]}, sub_type=["followup_only"])
    with patch.object(GenerateEvents, "possible_short_events", return_value=[parent]):
        assert HandleShortEvents().handle_event("misc", cats[0], cats[1], None)
    assert len(clan.future_events) == 1
    assert clan.future_events[0].involved_cats == {"m_c": cats[1].ID, "r_c": cats[0].ID}
    with patch.object(GenerateEvents, "possible_short_events", return_value=[parent, followup]):
        trigger_future_events()
        assert len(game.cur_events_list) == 1
        trigger_future_events()
        trigger_future_events()
    assert not clan.future_events
    assert len(game.cur_events_list) == 2
    assert str(cats[1].name) in game.cur_events_list[-1].text


def test_explicit_participants_are_reserved_before_random_selection(colony):
    clan, cats = colony
    info = followup_info(involved_cats={"m_c": {}, "r_c": "m_c"})
    original = deepcopy(info)
    parent = ShortEvent(event_id="parent", future_event=[info])
    prep_future_event(parent, parent.event_id, {"m_c": cats[0]})
    assert parent.future_event == [original]
    pending = clan.future_events[0]
    assert pending.involved_cats["r_c"] == cats[0].ID
    assert pending.involved_cats["m_c"] != cats[0].ID
    assert isinstance(pending.involved_cats["m_c"], str)


def test_new_cat_role_and_missing_participant_do_not_discard_later_chains(colony):
    clan, cats = colony
    parent = ShortEvent(event_id="parent", future_event=[
        followup_info(involved_cats={"m_c": "missing", "r_c": "r_c"}),
        followup_info(involved_cats={"m_c": "n_c:0", "r_c": "r_c"})])
    prep_future_event(parent, parent.event_id, {"n_c:0": cats[2], "r_c": cats[1]})
    assert len(clan.future_events) == 1
    assert clan.future_events[0].involved_cats["m_c"] == cats[2].ID


@pytest.mark.parametrize("state", ["dead", "outside", "exiled", "shunned", "missing", "removed"])
def test_unavailable_actor_cancels_pending_event(colony, state):
    clan, cats = colony
    clan.future_events = [FutureEvent("parent", "misc", {}, 1, {"m_c": cats[0].ID, "r_c": cats[1].ID})]
    if state == "missing":
        Cat.all_cats.pop(cats[0].ID)
    elif state == "removed":
        clan.clan_cats.remove(cats[0].ID)
    else:
        setattr(cats[0], state, True)
    trigger_future_events()
    assert not clan.future_events and not game.cur_events_list


def test_season_locked_followup_retries_until_valid_then_stops(colony):
    clan, cats = colony
    clan.future_events = [FutureEvent("parent", "misc", {"event_id": ["followup"]}, 1,
                                    {"m_c": cats[0].ID, "r_c": cats[1].ID})]
    followup = ShortEvent(event_id="followup", weight=1, text="m_c rests.", season=["greenleaf"])
    clan.current_season = "Newleaf"
    with patch.object(GenerateEvents, "possible_short_events", return_value=[followup]):
        trigger_future_events()
        assert len(clan.future_events) == 1 and not game.cur_events_list
        clan.current_season = "Greenleaf"
        trigger_future_events()
        trigger_future_events()
    assert not clan.future_events and len(game.cur_events_list) == 1


def test_expired_followup_is_removed_without_execution(colony):
    clan, cats = colony
    clan.future_events = [FutureEvent("parent", "misc", {}, -11, {"m_c": cats[0].ID, "r_c": cats[1].ID})]
    trigger_future_events()
    assert not clan.future_events and not game.cur_events_list


def test_newly_chained_followup_waits_for_next_moon(colony):
    clan, cats = colony
    clan.future_events = [FutureEvent("parent", "misc", {"event_id": ["followup"]}, 1,
                                    {"m_c": cats[0].ID, "r_c": cats[1].ID})]
    followup = ShortEvent(event_id="followup", weight=1, text="m_c notices r_c.", r_c={"age": ["any"]},
                          future_event=[followup_info()])
    with patch.object(GenerateEvents, "possible_short_events", return_value=[followup]):
        trigger_future_events()
    assert len(clan.future_events) == 1 and clan.future_events[0].moon_delay == 1
    assert len(game.cur_events_list) == 1


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_queue_survives_real_colony_save_reload_and_legacy_save(colony, monkeypatch, tmp_path, mode):
    from scripts.game_structure.load_cat import load_cats

    clan, cats = colony
    clan.game_mode = mode
    clan.leader = cats[0]
    clan.starting_members = cats
    expected = FutureEvent("parent", "misc", {"event_id": ["followup"]}, 2,
                           {"m_c": cats[0].ID, "r_c": cats[1].ID})
    for module in ("scripts.clan", "scripts.cat.cats", "scripts.game_structure.game_essentials", "scripts.game_structure.load_cat"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    real_save = type(game).safe_save
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return real_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    with patch.dict(game.switches, {"clan_list": [clan.name], "clan_name": clan.name}):
        clan.create_clan()
        clan.future_events = [expected]
        game.save_cats()
        clan.save_clan()
        Cat.all_cats.clear()
        Cat.all_cats_list.clear()
        Inheritance.all_inheritances.clear()
        load_cats()
        Clan().load_clan()
        assert [event.to_dict() for event in game.clan.future_events] == [expected.to_dict()]
        followup = ShortEvent(event_id="followup", text="m_c remembers r_c.", weight=1, r_c={"age": ["any"]})
        with patch.object(GenerateEvents, "possible_short_events", return_value=[followup]):
            trigger_future_events()
            assert not game.cur_events_list
            trigger_future_events()
            assert len(game.cur_events_list) == 1
        game.clan.save_clan()
        Clan().load_clan()
        assert not game.clan.future_events
        path = tmp_path / (clan.name + ".json")
        saved = json.loads(path.read_text(encoding="utf-8"))
        saved.pop("future_events")
        path.write_text(json.dumps(saved), encoding="utf-8")
        Clan().load_clan()
        assert not game.clan.future_events

        from scripts.events import Events
        game.clan.future_events = [FutureEvent("parent", "misc", {"event_id": ["followup"]}, 1,
                                               expected.involved_cats)]
        followup.sub_type = ["followup_only"]
        original_events = GenerateEvents.possible_short_events
        def events_with_followup(event_type):
            events = original_events(event_type)
            return events + [followup] if event_type == "misc" else events
        monkeypatch.setattr(Cat, "dead_cats", [])
        monkeypatch.setattr(Cat, "grief_strings", {})
        for name in ("next_events_list", "patrolled", "just_died", "dated_cats", "mediated", "told_story"):
            monkeypatch.setattr(game, name, [])
        game.clan.clan_settings["autosave"] = False
        with patch.object(GenerateEvents, "possible_short_events", side_effect=events_with_followup):
            Events().one_moon()
        assert any("remembers" in event.text for event in game.cur_events_list)
        assert not game.clan.future_events


def test_patrol_outcome_schedules_followup_with_actual_leader_role(colony):
    clan, cats = colony
    patrol = Patrol()
    patrol.add_patrol_cats(cats[:2], clan)
    patrol.patrol_event = PatrolEvent("parent_patrol")
    outcome = PatrolOutcome.generate_from_info([{
        "text": "p_l returns from patrol.", "exp": 0, "future_event": [followup_info(
            involved_cats={"m_c": "p_l", "r_c": "r_c"})]}])[0]
    outcome.execute_outcome(patrol)
    assert len(clan.future_events) == 1
    assert clan.future_events[0].parent_event == "parent_patrol"
    assert clan.future_events[0].involved_cats["m_c"] == patrol.patrol_leader.ID
    followup = ShortEvent(event_id="followup", text="m_c remembers the patrol.", weight=1)
    with patch.object(GenerateEvents, "possible_short_events", return_value=[followup]):
        trigger_future_events()
    assert len(game.cur_events_list) == 1 and not clan.future_events


def test_followup_effects_are_not_lost_when_a_participant_is_context_only(colony):
    clan, cats = colony
    cats[0].relationships[cats[1].ID] = Relationship(cats[0], cats[1])
    clan.future_events = [FutureEvent("parent", "misc", {"sub_type": ["followup_only"],
        "excluded_event_id": ["excluded"]}, 1, {"m_c": cats[0].ID, "r_c": cats[1].ID})]
    followup = ShortEvent(event_id="followup", weight=1, text="m_c trusts r_c.",
        r_c={"age": ["any"]}, sub_type=["followup_only"], exclude_involved=["r_c"],
        relationships=[{"cats_from": ["m_c"], "cats_to": ["r_c"], "values": ["trust"], "amount": 5}])
    excluded = ShortEvent(event_id="excluded", weight=100, text="Wrong event.", sub_type=["followup_only"])
    with patch.object(GenerateEvents, "possible_short_events", return_value=[followup, excluded]):
        trigger_future_events()
    assert cats[0].relationships[cats[1].ID].trust == 5
    assert game.cur_events_list[0].cats_involved == [cats[0].ID]
    assert not clan.future_events


@pytest.mark.parametrize("main_shunned", [0, 1])
@pytest.mark.parametrize("companion_shunned", [0, 1])
@pytest.mark.parametrize("required", [False, True])
def test_companion_shunning_constraint_checks_the_companion(colony, main_shunned, companion_shunned, required):
    _, cats = colony
    cats[0].shunned = main_shunned
    cats[1].shunned = companion_shunned
    event = ShortEvent(event_id="shunning", weight=1, r_c={"shunned": required})
    assert bool(filter_events([event], cats)) == (bool(companion_shunned) == required)


@pytest.mark.parametrize("revealed", [False, True])
def test_scheduled_reveal_uses_saved_victim_and_does_not_repeat_known_murder(colony, revealed):
    clan, cats = colony
    murderer, witness, victim = cats
    victim.dead = True
    murderer.history.murder = {"is_murderer": [
        {"victim": "another_victim", "revealed": False, "moon": 0}]}
    History.add_murders(victim, murderer, revealed, "Victim died.")
    clan.future_events = [FutureEvent("murder", "misc", {"sub_type": ["murder_reveal"]}, 1,
        {"m_c": murderer.ID, "r_c": witness.ID, "mur_c": victim.ID})]
    reveal = ShortEvent(event_id="reveal", weight=1, text="r_c learns what happened to mur_c.",
        r_c={"age": ["any"]}, sub_type=["murder_reveal"], tags=["LIFEGEN_no_shun"])
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal]):
        trigger_future_events()
        trigger_future_events()
    assert not clan.future_events
    assert not murderer.history.murder["is_murderer"][0]["revealed"]
    assert murderer.history.murder["is_murderer"][1]["revealed"]
    assert victim.history.murder["is_victim"][0]["revealed"]
    assert len(game.cur_events_list) == (0 if revealed else 1)


@pytest.mark.parametrize("frequency", [0, 5])
def test_invalid_frequency_is_reported_by_resource_reader(monkeypatch, frequency):
    monkeypatch.setattr(GenerateEvents, "loaded_events", {})
    with patch.object(GenerateEvents, "get_short_event_dicts", return_value=[
        {"event_id": "invalid", "event_text": "Invalid frequency.", "frequency": frequency}]), pytest.raises(
            ValueError, match="Invalid frequency for invalid"):
        GenerateEvents.generate_short_events("misc", "general")
    with pytest.raises(ValueError, match="Invalid frequency for invalid"):
        Patrol().generate_patrol_events([{"patrol_id": "invalid", "frequency": frequency}])


@pytest.mark.parametrize("roll", [1, 10])
def test_patrol_romance_uses_the_normal_patrols_frequency_pool(colony, roll):
    _, cats = colony
    patrol = Patrol()
    common = PatrolEvent("common", frequency=4, intro_text="Common patrol.")
    rare = PatrolEvent("rare", frequency=1, intro_text="Rare patrol.")
    romance = PatrolEvent("romance", frequency=4, intro_text="Romantic patrol.")
    with patch.object(patrol, "get_possible_patrols", return_value=([common, rare], [romance])), patch.object(
            Patrol, "decide_if_romantic", return_value=True), patch(
            "scripts.events_module.event_frequency.randint", return_value=roll), patch.object(
            Patrol, "used_patrols", []), patch.dict(game.switches, {"patrol_category": "clangen", "patrolled": []}):
        patrol.setup_patrol(cats[:2], "border")
    assert patrol.patrol_event is (romance if roll == 1 else rare)
