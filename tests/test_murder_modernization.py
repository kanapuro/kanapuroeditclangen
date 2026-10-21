from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.events_module.future_event import FutureEvent, trigger_future_events
from scripts.events_module.generate_events import GenerateEvents
from scripts.events_module.short.handle_short_events import HandleShortEvents
from scripts.events_module.short.short_event import ShortEvent
from scripts.game_structure.game_essentials import game


@pytest.fixture
def crime(monkeypatch, tmp_path):
    for target, name, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                                (Cat, "outside_cats", {}), (Cat, "dead_cats", []),
                                (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, name, value)
    clan = Clan(name="CrimeTest", camp_bg="camp1", game_mode="expanded")
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setattr(game, "cur_events_list", [])
    monkeypatch.setattr(game, "switches", {**game.switches, "clan_name": clan.name, "clan_list": [clan.name]})
    for module in ("scripts.cat.cats", "scripts.clan", "scripts.game_structure.game_essentials"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    cats = [Cat(prefix=name, gender="female", moons=40, status="warrior")
            for name in ("Culprit", "Witness", "Victim", "Other")]
    for cat in cats:
        cat.history = History()
        clan.add_cat(cat)
        cat.create_inheritance_new_cat()
    clan.your_cat = cats[-1]
    return clan, cats


def reveal_event(public=False):
    return ShortEvent(event_id="crime_reveal", weight=1, text="r_c learns that m_c killed mur_c.",
                      sub_type=["murder_reveal"], r_c={"age": ["any"]},
                      tags=["clan_wide"] if public else ["LIFEGEN_no_shun"])


def test_private_knowledge_can_spread_then_become_public(crime):
    clan, (culprit, witness, victim, other) = crime
    victim.dead = True
    History.add_murders(victim, culprit, False, "Victim was murdered.")
    event = reveal_event()
    handler = HandleShortEvents()
    with patch.object(GenerateEvents, "possible_short_events", return_value=[event]):
        assert handler.handle_event("misc", culprit, witness, clan.freshkill_pile)
        assert not handler.handle_event("misc", culprit, witness, clan.freshkill_pile)
        assert handler.handle_event("misc", culprit, other, clan.freshkill_pile)
    for record in (culprit.history.murder["is_murderer"][0], victim.history.murder["is_victim"][0]):
        assert record["revealed"] and not record["clan_discovery"]
        assert record["aware_individuals"] == [witness.ID, other.ID]
    assert not culprit.shunned
    assert len(game.cur_events_list) == 2
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal_event(True)]), patch(
            "scripts.cat.history.random.randint", return_value=2):
        assert handler.handle_event("misc", culprit, witness, clan.freshkill_pile)
        assert not handler.handle_event("misc", culprit, witness, clan.freshkill_pile)
    assert culprit.shunned
    for record in (culprit.history.murder["is_murderer"][0], victim.history.murder["is_victim"][0]):
        assert record["clan_discovery"]
    assert len(game.cur_events_list) == 3


@pytest.mark.parametrize("tell_clan", [False, True])
def test_existing_witness_choice_controls_public_knowledge_and_shunning(crime, tell_clan):
    clan, (culprit, witness, victim, other) = crime
    victim.dead = True
    History.add_murders(victim, culprit, False)
    event = reveal_event()
    event.tags.clear()
    with patch.object(GenerateEvents, "possible_short_events", return_value=[event]), patch(
            "scripts.events_module.short.handle_short_events.random.random", return_value=0 if tell_clan else .9), patch(
            "scripts.cat.history.random.randint", return_value=2):
        assert HandleShortEvents().handle_event("misc", culprit, witness, clan.freshkill_pile)
    for record in (culprit.history.murder["is_murderer"][0], victim.history.murder["is_victim"][0]):
        assert record["clan_discovery"] is tell_clan
        assert record["aware_individuals"] == [witness.ID]
        assert str(witness.name) in record["revelation_text"]
    assert bool(culprit.shunned) is tell_clan
    assert ("told the Clan" in game.cur_events_list[0].text) is tell_clan


@pytest.mark.parametrize("same_moon", [False, True])
@pytest.mark.parametrize("index", [1, -1])
def test_reveal_matches_the_attack_and_murderer_on_the_victim(crime, same_moon, index):
    clan, (culprit, witness, victim, other) = crime
    History.add_murders(victim, other, False)
    History.add_murders(victim, culprit, False)
    if not same_moon:
        clan.age += 1
    History.add_murders(victim, culprit, False)
    History.reveal_murder(culprit, witness, Cat, victim, index, False)
    assert not culprit.history.murder["is_murderer"][0]["revealed"]
    assert culprit.history.murder["is_murderer"][1]["revealed"]
    assert [record["revealed"] for record in victim.history.murder["is_victim"]] == [False, False, True]
    assert not other.history.murder["is_murderer"][0]["revealed"]


def test_private_discovery_does_not_capture_leader_demotion_or_change_lives(crime):
    clan, (culprit, witness, victim, other) = crime
    culprit.status = "leader"
    clan.leader = culprit
    clan.leader_lives = 7
    clan.leader_lives_reserve = 8
    History.add_murders(victim, culprit, False)
    History.reveal_murder(culprit, witness, Cat, victim, 0, False)
    record = culprit.history.murder["is_murderer"][0]
    assert "demoted_from" not in record and "remaining_lives" not in record
    assert clan.leader_lives == 7 and clan.leader_lives_reserve == 8


@pytest.mark.parametrize("revealed", [False, True])
def test_old_reveal_flags_keep_their_existing_meaning_without_rewriting_history(crime, revealed):
    clan, (culprit, witness, victim, other) = crime
    victim.dead = True
    History.add_murders(victim, culprit, revealed)
    record = culprit.history.murder["is_murderer"][0]
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal_event()]):
        result = HandleShortEvents().handle_event("misc", culprit, witness, clan.freshkill_pile)
    assert bool(result) is not revealed
    if revealed:
        assert "clan_discovery" not in record and "aware_individuals" not in record


def test_missing_victim_does_not_block_another_unresolved_crime(crime):
    clan, (culprit, witness, victim, other) = crime
    culprit.history.murder = {"is_murderer": [{"victim": "missing", "revealed": False, "moon": 0}]}
    victim.dead = True
    History.add_murders(victim, culprit, False)
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal_event()]):
        assert HandleShortEvents().handle_event("misc", culprit, witness, clan.freshkill_pile)
    assert culprit.history.murder["is_murderer"][1]["revealed"]


def test_known_scheduled_reveals_finish_without_repeating_or_retrying(crime):
    clan, (culprit, witness, victim, other) = crime
    victim.dead = True
    History.add_murders(victim, culprit, False)
    History.reveal_murder(culprit, witness, Cat, victim, 0, False)
    scheduled = FutureEvent("crime", "misc", {"sub_type": ["murder_reveal"]}, 1,
                            {"m_c": culprit.ID, "r_c": witness.ID, "mur_c": victim.ID})
    clan.future_events = [scheduled]
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal_event()]):
        trigger_future_events()
    assert not clan.future_events and not game.cur_events_list
    with patch("scripts.cat.history.random.randint", return_value=2):
        History.reveal_murder(culprit, None, Cat, victim, 0, True)
    scheduled.moon_delay = 1
    clan.future_events = [scheduled]
    with patch.object(GenerateEvents, "possible_short_events", return_value=[]):
        trigger_future_events()
    assert not clan.future_events and not game.cur_events_list


@pytest.mark.parametrize("mode,event_id", [
    (mode, event_id) for mode in ("classic", "expanded", "cruel season")
    for event_id in ("gen_death_murder_any1", "gen_death_murder_any2", "gen_death_murder_any3")
] + [("expanded", event_id) for event_id in (
    "gen_death_murder_any4", "gen_death_murder_anymed1", "gen_death_murder_anymed2",
    "gen_death_murder_anymed3", "gen_death_murder_anymed4", "gen_death_murder_anymed5",
    "gen_death_murder_anydep1", "gen_death_murder_anydep2")])
def test_released_murder_followups_run_after_created_colony_save_reload(crime, monkeypatch, tmp_path, mode, event_id):
    from scripts.cat.personality import Personality
    from scripts.cat.skills import Skill, SkillPath
    from scripts.game_structure.load_cat import load_cats

    clan, cats = crime
    culprit, witness, victim, player = cats
    clan.game_mode = mode
    clan.leader = player
    clan.starting_members = cats
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    monkeypatch.setattr(GenerateEvents, "loaded_events", {})
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    clan.create_clan()
    neighbors = [vars(other).copy() for other in clan.all_clans]
    culprit.personality = Personality(trait="oblivious")
    culprit.skills.primary = Skill(SkillPath.FIGHTER, 29)
    culprit.skills.secondary = None
    victim.skills.primary = Skill(SkillPath.HUNTER, 0)
    victim.skills.secondary = None
    if "anymed" in event_id:
        culprit.status_change("medicine cat")
    if "anydep" in event_id:
        clan.new_deputy(victim)
        culprit.personality = Personality(trait="righteous")
        if event_id.endswith("2"):
            culprit.skills.primary = Skill(SkillPath.CLEVER, 29)
    culprit_status = culprit.status
    death = next(event for event in GenerateEvents.generate_short_events("death", "general") if event.event_id == event_id)
    reveal_id = "gen_misc_murderreveal_any3" if "anydep" in event_id else "gen_misc_murderreveal_any2"
    reveal = next(event for event in GenerateEvents.generate_short_events("misc", "general")
                  if event.event_id == reveal_id)
    with patch.object(GenerateEvents, "possible_short_events", return_value=[death]):
        assert HandleShortEvents().handle_event("birth_death", victim, culprit, clan.freshkill_pile, ["murder"])
    assert victim.dead
    assert (culprit.ID in game.cur_events_list[-1].cats_involved) is ("r_c" not in death.exclude_involved)
    assert len(clan.future_events) == 1
    queued = clan.future_events[0].to_dict()
    assert 1 <= queued["moon_delay"] <= 12
    assert queued["involved_cats"]["m_c"] == culprit.ID and queued["involved_cats"]["mur_c"] == victim.ID
    culprit_id, victim_id = culprit.ID, victim.ID
    for stage in ("queued", "private", "public"):
        game.save_cats()
        game.clan.save_clan()
        Cat.all_cats.clear()
        Cat.all_cats_list.clear()
        Inheritance.all_inheritances.clear()
        load_cats()
        Clan().load_clan()
        assert [vars(other) for other in game.clan.all_clans] == neighbors
        culprit, victim = Cat.fetch_cat(culprit_id), Cat.fetch_cat(victim_id)
        assert culprit.status == culprit_status
        if stage != "queued":
            for record in (History.get_murders(culprit)["is_murderer"][0], History.get_murders(victim)["is_victim"][0]):
                assert record["revealed"] and record["clan_discovery"] is (stage == "public")
                assert record["aware_individuals"] == [queued["involved_cats"]["r_c"]]
            assert not game.clan.future_events
            if stage == "private":
                History.reveal_murder(culprit, None, Cat, victim, 0, False)
            continue
        assert game.clan.future_events[0].to_dict() == queued
        with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal]), patch(
                "scripts.events_module.short.handle_short_events.random.random", return_value=.9):
            for _ in range(queued["moon_delay"]):
                trigger_future_events()
        assert not game.clan.future_events
        for record in (History.get_murders(culprit)["is_murderer"][0], History.get_murders(victim)["is_victim"][0]):
            assert record["revealed"] and not record["clan_discovery"]
            assert record["aware_individuals"] == [queued["involved_cats"]["r_c"]]
        assert not culprit.shunned


def test_neighboring_clans_are_owned_by_each_colony():
    first = Clan(name="First")
    second = Clan(name="Second")
    empty = Clan()
    first.all_clans.append("first neighbor")
    assert second.all_clans == empty.all_clans == []
    assert not Clan.all_clans


def test_player_punishment_without_a_crime_record_retains_existing_shunning(crime):
    from scripts.screens.MurderScreen import MurderScreen

    clan, (culprit, witness, victim, other) = crime
    clan.your_cat = victim
    victim.dead = True
    culprit.faith = 3
    screen = object.__new__(MurderScreen)
    screen.is_self_harm = True
    with patch("scripts.cat.history.random.randint", return_value=2):
        screen.choose_discover_punishment(victim, victim, culprit, True)
    assert culprit.shunned and culprit.faith == 2
    assert culprit.history.murder == victim.history.murder == {}
    assert len(game.cur_events_list) == 1


def test_delayed_reveals_remain_bound_to_the_attack_that_scheduled_them(crime):
    from scripts.events_module.future_event import prep_future_event

    clan, (culprit, witness, victim, other) = crime
    parent = ShortEvent(event_id="repeated_attack", sub_type=["murder"], future_event=[{
        "event_type": "misc", "pool": {"sub_type": ["murder_reveal"]}, "moon_delay": [1, 1],
        "involved_cats": {"m_c": "r_c", "mur_c": "m_c", "r_c": {"age": ["any"]}}}])
    History.add_murders(victim, culprit, False, "First attack.")
    prep_future_event(parent, parent.event_id, {"m_c": victim, "r_c": culprit})
    first = clan.future_events[-1]
    History.add_murders(victim, culprit, False, "Second attack.")
    prep_future_event(parent, parent.event_id, {"m_c": victim, "r_c": culprit})
    second = clan.future_events[-1]
    # Discover the later attack first, including serialization of the queued event.
    clan.future_events = [FutureEvent(**second.to_dict())]
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal_event()]):
        trigger_future_events()
    assert [record["revealed"] for record in culprit.history.murder["is_murderer"]] == [False, True]
    assert [record["revealed"] for record in victim.history.murder["is_victim"]] == [False, True]
    clan.future_events = [FutureEvent(**first.to_dict())]
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal_event()]):
        trigger_future_events()
    assert all(record["revealed"] for record in culprit.history.murder["is_murderer"])
    assert len(game.cur_events_list) == 2


@pytest.mark.parametrize("mode,event_id,lives", [
    ("expanded", event_id, lives)
    for event_id in ("gen_death_murder_any5", "gen_death_murder_leafbareice1", "gen_death_murder_anymonster1",
                     "gen_death_murder_anylead2", "gen_death_murder_anylead4", "gen_death_trapmurder1", "gen_death_angrymurder1")
    for lives in ((1, 3) if event_id in ("gen_death_murder_anymonster1", "gen_death_trapmurder1", "gen_death_angrymurder1") else (1, 9))
] + [(mode, "gen_death_murder_any5", 9) for mode in ("classic", "cruel season")]
  + [("cruel season", "gen_death_murder_anylead2", lives) for lives in (1, 9)])
def test_leader_murder_followups_preserve_lives_history_and_saved_identity(crime, monkeypatch, tmp_path, mode, event_id, lives):
    from scripts.cat.personality import Personality
    from scripts.cat.skills import Skill, SkillPath
    from scripts.game_structure.load_cat import load_cats

    clan, cats = crime
    culprit, witness, victim, player = cats
    clan.game_mode = mode
    rivalry = mode == "cruel season" and event_id == "gen_death_murder_anylead2"
    if rivalry:
        clan.cruel_cards = ["for_the_throne", "heartless"]
    clan.leader = victim
    victim.leader_life_override = lives == 1
    clan.starting_members = cats
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    monkeypatch.setattr(GenerateEvents, "loaded_events", {})
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    clan.create_clan()
    clan.leader_lives = clan.leader_lives_reserve = clan.leader_lives_last_applied = lives
    victim.skills.primary = Skill(SkillPath.HUNTER, 0)
    victim.skills.secondary = None
    culprit.personality = Personality(trait="oblivious")
    if event_id == "gen_death_murder_leafbareice1":
        clan.current_season = "Leaf-bare"
        victim.personality = Personality(trait="oblivious")
    if event_id == "gen_death_murder_anylead2":
        clan.new_deputy(culprit)
        culprit.skills.primary = Skill(SkillPath.FIGHTER, 29)
        culprit.personality = Personality(trait="righteous")
    if event_id == "gen_death_trapmurder1":
        culprit.skills.primary = Skill(SkillPath.CLEVER, 9)
        culprit.personality = Personality(trait="sneaky")
    if event_id == "gen_death_angrymurder1":
        culprit.personality = Personality(trait="vengeful")
    death = next(event for event in GenerateEvents.generate_short_events("death", "general") if event.event_id == event_id)
    with patch.object(GenerateEvents, "possible_short_events", return_value=[death]):
        if rivalry:
            from scripts.events import Events

            culprit.relationships[victim.ID].dislike = 20
            with patch("scripts.events.random.getrandbits", return_value=1):
                Events().handle_murder(culprit)
        else:
            assert HandleShortEvents().handle_event("birth_death", victim, culprit, clan.freshkill_pile, ["murder"])
    remaining = 0 if "all_lives" in death.tags else lives - 1
    assert clan.leader_lives == remaining and victim.dead is (remaining == 0)
    assert len(victim.history.died_by) == lives - remaining
    assert sum(record["text"] == "multi_lives" for record in victim.history.died_by) == lives - remaining - 1
    assert len(victim.history.murder["is_victim"]) == len(culprit.history.murder["is_murderer"]) == 1
    queued = clan.future_events[0].to_dict()
    assert queued["murder_index"] == 0
    ids = culprit.ID, victim.ID
    histories = [record.copy() for record in victim.history.died_by]
    game.save_cats()
    clan.save_clan()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    culprit, victim = (Cat.fetch_cat(cat_id) for cat_id in ids)
    assert game.clan.leader_lives == remaining and victim.dead is (remaining == 0)
    if rivalry:
        assert game.clan.cruel_cards == ["for_the_throne", "heartless"]
        assert game.get_config_value("death_related", "murder", "deputy_prefer_leader") is True
    assert History.get_death_or_scars(victim, death=True) == histories
    assert game.clan.future_events[0].to_dict() == queued
    # An actual legacy reveal resource remains eligible for this culprit's trait.
    reveal = next(event for event in GenerateEvents.generate_short_events("misc", "general")
                  if event.event_id == "gen_misc_murderreveal_any3")
    culprit.personality = Personality(trait="righteous")
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal]), patch(
            "scripts.events_module.short.handle_short_events.random.random", return_value=.9):
        for _ in range(queued["moon_delay"]):
            trigger_future_events()
    assert not game.clan.future_events
    assert History.get_murders(culprit)["is_murderer"][0]["revealed"]
    assert History.get_murders(victim)["is_victim"][0]["revealed"]
    assert game.clan.leader_lives == remaining
    game.save_cats()
    game.clan.save_clan()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    assert game.clan.leader_lives == remaining
    assert History.get_murders(Cat.fetch_cat(ids[0]))["is_murderer"][0]["clan_discovery"] is False


@pytest.mark.parametrize("index", [0, 9])
def test_stale_bound_revelations_do_not_select_a_different_attack(crime, index):
    clan, (culprit, witness, victim, other) = crime
    History.add_murders(other, culprit, False)
    History.add_murders(victim, culprit, False)
    clan.future_events = [FutureEvent("stale", "misc", {"sub_type": ["murder_reveal"]}, 1,
        {"m_c": culprit.ID, "r_c": witness.ID, "mur_c": victim.ID}, murder_index=index)]
    trigger_future_events()
    assert not clan.future_events and not game.cur_events_list
    assert not any(record["revealed"] for record in culprit.history.murder["is_murderer"])


def test_publicly_known_bound_attack_does_not_reveal_an_earlier_secret(crime):
    clan, (culprit, witness, victim, other) = crime
    History.add_murders(victim, culprit, False)
    History.add_murders(victim, culprit, True)
    clan.future_events = [FutureEvent("known", "misc", {"sub_type": ["murder_reveal"]}, 1,
        {"m_c": culprit.ID, "r_c": witness.ID, "mur_c": victim.ID}, murder_index=1)]
    trigger_future_events()
    assert not clan.future_events and not game.cur_events_list
    assert [record["revealed"] for record in culprit.history.murder["is_murderer"]] == [False, True]


HIDDEN_REVEALS = (
    "gen_misc_hiddenmurderreveal_medcat1", "gen_misc_hiddenmurderreveal_remorse1",
    "gen_misc_accidentmurderreveal_failuretoact", "gen_misc_hiddenmurderreveal_remorse2",
    "gen_misc_hiddenmurderreveal_simple1", "gen_misc_hiddenmurderreveal_sc_forgives",
    "gen_misc_murderreveal_ghostgossip1",
)


@pytest.mark.parametrize("event_id", HIDDEN_REVEALS)
def test_hidden_discoveries_apply_personality_reactions_and_named_logs(crime, monkeypatch, event_id):
    from scripts.cat.personality import Personality
    from scripts.cat.skills import Skill, SkillPath

    clan, (culprit, witness, victim, other) = crime
    monkeypatch.setattr(GenerateEvents, "loaded_events", {})
    reveal = next(event for event in GenerateEvents.generate_short_events("misc", "general")
                  if event.event_id == event_id)
    culprit.personality = Personality(trait="confident")
    witness.personality = Personality(lawful=9, stable=9)
    other.personality = Personality(lawful=8, stable=8)
    if event_id.endswith("medcat1"):
        witness.status = "medicine cat"
    if event_id.endswith("sc_forgives"):
        witness.skills.primary = Skill(SkillPath.STAR, 10)
    if event_id.endswith("ghostgossip1"):
        witness.skills.primary = Skill(SkillPath.GHOST, 20)
    if event_id.endswith("remorse2"):
        clan.biome = "Plains"
        clan.current_season = "Newleaf"
    victim.dead = True
    History.add_murders(victim, culprit, False, "m_c was killed by r_c.",
                        unrevealed_text="m_c was found dead.", hidden=True)
    for cat in (witness, other):
        cat.create_one_relationship(culprit)
        rel = cat.relationships[culprit.ID]
        rel.platonic_like = 10
        rel.dislike = 7
        rel.trust = rel.comfortable = 90
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal]), patch(
            "scripts.events_module.short.handle_short_events.random.random", return_value=.9), patch(
            "scripts.cat.history.random.randint", return_value=2):
        assert HandleShortEvents().handle_event("misc", culprit, witness, clan.freshkill_pile)
    public = "clan_wide" in reveal.tags
    assert bool(culprit.shunned) is public
    for record in (culprit.history.murder["is_murderer"][0], victim.history.murder["is_victim"][0]):
        assert record["revealed"] and record["clan_discovery"] is public and record["hidden"]
    assert str(victim.name) in game.cur_events_list[-1].text
    assert not any(token in game.cur_events_list[-1].text for token in ("m_c", "r_c", "mur_c", "{PRONOUN", "{VERB"))
    for cat in ((witness, other) if public else (witness,)):
        rel = cat.relationships[culprit.ID]
        assert rel.platonic_like == 0 and rel.dislike > 7
        assert rel.trust < 90 and rel.comfortable < 90
        assert str(cat.name) in rel.log[-1] and str(culprit.name) in rel.log[-1]
        assert str(victim.name) in rel.log[-1]
        assert not any(token in rel.log[-1] for token in ("cat_from", "cat_to", "mur_c", "{PRONOUN"))
    if event_id.endswith("simple1"):
        assert witness.relationships[culprit.ID].dislike == 57
        assert other.relationships[culprit.ID].dislike == 27
    if event_id.endswith("ghostgossip1"):
        assert other.relationships[witness.ID].trust == 0
        assert witness.ID not in witness.relationships


@pytest.mark.parametrize("event_id", ("gen_death_drown_multi2_murder", "gen_death_wander_any1_murder"))
@pytest.mark.parametrize("mode", ("classic", "expanded", "cruel season"))
@pytest.mark.parametrize("lives", (None, 1, 9))
def test_hidden_death_discovery_and_profile_survive_save_reload(crime, monkeypatch, tmp_path, event_id, mode, lives):
    from types import SimpleNamespace
    from scripts.cat.skills import Skill, SkillPath
    from scripts.game_structure.load_cat import load_cats
    from scripts.screens.ProfileScreen import ProfileScreen

    clan, cats = crime
    culprit, witness, victim, player = cats
    clan.game_mode = mode
    clan.starting_members = cats
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    monkeypatch.setattr(GenerateEvents, "loaded_events", {})
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    clan.leader = victim if lives else player
    clan.create_clan()
    clan.biome = "Forest"
    clan.current_season = "Newleaf"
    victim.pronouns = [victim.pronouns[0].copy()]
    if lives:
        victim.status = "leader"
        victim.leader_life_override = lives == 1
        clan.leader = victim
        clan.leader_lives = clan.leader_lives_reserve = clan.leader_lives_last_applied = lives
    victim.skills.primary = Skill(SkillPath.HUNTER, 0)
    victim.skills.secondary = None
    death = next(event for event in GenerateEvents.generate_short_events("death", "general") if event.event_id == event_id)
    with patch.object(GenerateEvents, "possible_short_events", return_value=[death]):
        assert HandleShortEvents().handle_event("birth_death", victim, culprit, clan.freshkill_pile, ["murder"])
    assert victim.dead and len(clan.future_events) == 1
    assert culprit.ID not in game.cur_events_list[-1].cats_involved
    assert str(culprit.name) not in game.cur_events_list[-1].text
    queued = clan.future_events[0].to_dict()
    assert queued["murder_index"] == 0 and queued["pool"]["sub_type"] == ["hidden_murder_reveal"]
    profile = ProfileScreen.get_death_text(SimpleNamespace(the_cat=victim))
    assert str(culprit.name) not in profile
    assert profile.count(str(victim.name)) == 1
    assert ("drowned" if "drown" in event_id else "found dead") in profile
    ids = culprit.ID, victim.ID
    game.save_cats()
    clan.save_clan()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    culprit, victim = (Cat.fetch_cat(cat_id) for cat_id in ids)
    assert History.get_murders(culprit)["is_murderer"][0]["hidden"]
    History.check_load(victim)
    assert ProfileScreen.get_death_text(SimpleNamespace(the_cat=victim)) == profile
    assert game.clan.future_events[0].to_dict() == queued
    reveal = next(event for event in GenerateEvents.generate_short_events("misc", "general")
                  if event.event_id == "gen_misc_hiddenmurderreveal_simple1")
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal]), patch(
            "scripts.cat.history.random.randint", return_value=2):
        for _ in range(queued["moon_delay"]):
            trigger_future_events()
    assert not game.clan.future_events and culprit.shunned
    assert History.get_murders(culprit)["is_murderer"][0]["clan_discovery"]
    assert History.get_murders(victim)["is_victim"][0]["clan_discovery"]
    assert str(culprit.name) in ProfileScreen.get_death_text(SimpleNamespace(the_cat=victim))
    if lives:
        assert game.clan.leader_lives == 0 and len(victim.history.died_by) == lives


@pytest.mark.parametrize("amount,expected", [(-30, (0, 32)), (-5, (5, 12)), (5, (10, 7)), (30, (28, 0))])
def test_signed_liking_preserves_local_metrics_and_feedback(crime, amount, expected):
    from scripts.utility import unpack_rel_block

    clan, (culprit, witness, victim, other) = crime
    witness.create_one_relationship(culprit)
    rel = witness.relationships[culprit.ID]
    rel.platonic_like, rel.dislike = 10, 12
    rel.admiration, rel.jealousy = 33, 44
    changes = {}
    unpack_rel_block(Cat, [{"cats_from": ["m_c"], "cats_to": ["r_c"], "values": ["like"], "amount": amount}],
                     event=Mock(main_cat=witness, random_cat=culprit, text="An encounter."), changes=changes)
    assert (rel.platonic_like, rel.dislike) == expected
    assert (rel.admiration, rel.jealousy) == (33, 44)
    for field, initial in (("platonic_like", 10), ("dislike", 12)):
        final = getattr(rel, field)
        assert changes[(witness.ID, culprit.ID)].get(field) == ((initial, final) if initial != final else None)


@pytest.mark.parametrize("public", [False, True])
def test_hidden_discoveries_deduplicate_private_and_saved_public_reveals(crime, public):
    clan, (culprit, witness, victim, other) = crime
    victim.dead = True
    History.add_murders(victim, culprit, False, hidden=True)
    History.reveal_murder(culprit, witness, Cat, victim, 0, public)
    reveal = reveal_event(public)
    reveal.sub_type = ["hidden_murder_reveal"]
    clan.future_events = [FutureEvent("hidden", "misc", {"sub_type": reveal.sub_type}, 1,
        {"m_c": culprit.ID, "r_c": witness.ID, "mur_c": victim.ID}, murder_index=0)]
    with patch.object(GenerateEvents, "possible_short_events", return_value=[reveal]):
        trigger_future_events()
    assert not clan.future_events and not game.cur_events_list


def test_source_relationship_logs_keep_original_roles_when_mutual(crime):
    from scripts.utility import unpack_rel_block

    clan, (culprit, witness, victim, other) = crime
    event = HandleShortEvents()
    event.main_cat, event.random_cat, event.victim_cat = culprit, witness, victim
    event.text = "An encounter."
    unpack_rel_block(Cat, [{"cats_from": ["m_c"], "cats_to": ["r_c"], "values": ["trust"], "amount": 4,
                           "mutual": True, "log": {
                               "cats_from": "cat_from believed cat_to about mur_c and {PRONOUN/cat_to/poss} fate.",
                               "cats_to": "cat_to appreciated cat_from's trust in r_c."}}], event=event)
    assert f"{culprit.name} believed {witness.name} about {victim.name}" in culprit.relationships[witness.ID].log[-1]
    assert f"{witness.name} appreciated {culprit.name}'s trust in {witness.name}" in witness.relationships[culprit.ID].log[-1]
    assert culprit.relationships[witness.ID].trust == witness.relationships[culprit.ID].trust == 4


@pytest.mark.parametrize("selector,facet", [("lawful", "lawfulness"), ("stable", "stability")])
def test_personality_groups_filter_existing_actors_at_the_source_boundary(crime, selector, facet):
    from scripts.utility import gather_cat_objects

    clan, (culprit, witness, victim, other) = crime
    setattr(culprit.personality, facet, 8)
    setattr(witness.personality, facet, 9)
    event = HandleShortEvents()
    event.main_cat, event.random_cat = culprit, witness
    assert gather_cat_objects(Cat, ["m_c", "high_" + selector], event) == []
    assert gather_cat_objects(Cat, ["m_c", "low_" + selector], event) == [culprit]
    assert gather_cat_objects(Cat, ["r_c", "high_" + selector], event) == [witness]
    assert gather_cat_objects(Cat, ["r_c", "low_" + selector], event) == []


@pytest.mark.parametrize("revealed_index", [0, 1])
def test_hidden_profile_matches_repeated_same_moon_attack_histories(crime, revealed_index):
    from types import SimpleNamespace
    from scripts.screens.ProfileScreen import ProfileScreen

    clan, (culprit, witness, victim, other) = crime
    text = "m_c was killed by r_c."
    for _ in range(2):
        History.add_murders(victim, culprit, False, text, unrevealed_text="m_c was found dead.", hidden=True)
        History.add_death(victim, text, other_cat=culprit)
    History.reveal_murder(culprit, witness, Cat, victim, revealed_index, False)
    profile = ProfileScreen.get_death_text(SimpleNamespace(the_cat=victim))
    assert profile.count("was found dead") == 1
    assert profile.count(str(culprit.name)) == 1


@pytest.mark.parametrize("cards", [None, [], ["for_the_throne"]])
@pytest.mark.parametrize("random_attack", [True, False])
def test_deputy_rivalry_prefers_only_eligible_leader_targets(crime, cards, random_attack):
    from scripts.events import Events

    clan, (deputy, other, leader, player) = crime
    clan.game_mode, clan.cruel_cards = "cruel season", cards
    clan.leader, clan.deputy = leader, deputy
    deputy.status, leader.status = "deputy", "leader"
    for target in (other, leader):
        relation = deputy.create_one_relationship(target)
        relation.dislike = 20
    with patch("scripts.events.random.getrandbits", side_effect=[1] if random_attack else [0, 1]), patch(
            "scripts.events.random.random", return_value=0), patch("scripts.events.random.choice", side_effect=lambda values: values[0]), patch(
            "scripts.events.handle_short_events.handle_event") as handle:
        Events().handle_murder(deputy)
    assert handle.call_args.kwargs["main_cat"] is (leader if cards else other)
    assert handle.call_args.kwargs["random_cat"] is deputy
    assert handle.call_args.kwargs["sub_type"] == ["murder"]


@pytest.mark.parametrize("cards", [None, [], ["for_the_throne"]])
@pytest.mark.parametrize("actor_rank,target_rank", [("deputy", "leader"), ("warrior", "leader"), ("deputy", "warrior")])
def test_rivalry_murder_odds_boost_is_confined_to_deputy_leader_pair(crime, cards, actor_rank, target_rank):
    from scripts.cat.personality import Personality
    from scripts.events import Events

    clan, (actor, _, target, _) = crime
    clan.game_mode, clan.cruel_cards = "cruel season", cards
    actor.status, target.status = actor_rank, target_rank
    actor.personality = Personality(trait="calm")
    relation = actor.create_one_relationship(target)
    for field in ("romantic_love", "platonic_like", "admiration", "comfortable", "jealousy", "trust"):
        setattr(relation, field, 0)
    relation.dislike = 20
    with patch.dict(game.config["death_related"], {"base_murder_kill_chance": 80}), patch(
            "scripts.events.random.getrandbits", side_effect=[0, 1]), patch(
            "scripts.events.random.random", return_value=.02), patch("scripts.events.handle_short_events.handle_event") as handle:
        Events().handle_murder(actor)
    # At this roll 70 misses, while the card's 30 succeeds.
    assert handle.called is bool(cards and actor_rank == "deputy" and target_rank == "leader")


@pytest.mark.parametrize("state", ["dead", "outside", "exiled", "missing", "friendly"])
@pytest.mark.parametrize("random_attack", [True, False])
def test_rivalry_does_not_force_attacks_on_ineligible_leaders(crime, state, random_attack):
    from scripts.events import Events

    clan, (deputy, other, leader, _) = crime
    clan.game_mode, clan.cruel_cards = "cruel season", ["for_the_throne"]
    deputy.status, leader.status = "deputy", "leader"
    for target in (other, leader):
        deputy.create_one_relationship(target).dislike = 20
    if state == "missing":
        Cat.all_cats.pop(leader.ID)
    elif state == "friendly":
        deputy.relationships[leader.ID].dislike = 0
    else:
        setattr(leader, state, True)
    with patch("scripts.events.random.getrandbits", side_effect=[1] if random_attack else [0, 1]), patch(
            "scripts.events.random.random", return_value=0), patch("scripts.events.handle_short_events.handle_event") as handle:
        Events().handle_murder(deputy)
    assert handle.call_args.kwargs["main_cat"] is other


def test_rivalry_never_automates_player_murder(crime):
    from scripts.events import Events

    clan, cats = crime
    clan.game_mode, clan.cruel_cards = "cruel season", ["for_the_throne"]
    clan.your_cat = cats[0]
    cats[0].status = "deputy"
    with patch("scripts.events.random.getrandbits") as roll, patch("scripts.events.handle_short_events.handle_event") as handle:
        Events().handle_murder(cats[0])
    roll.assert_not_called()
    handle.assert_not_called()
