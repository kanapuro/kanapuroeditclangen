import json
import re
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.cat.cats import Cat, ILLNESSES, INJURIES, PERMANENT
from scripts.cat.history import History
from scripts.cat.thoughts import Thoughts
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.events_module.short.condition_events import Condition_Events
from scripts.game_structure.game_essentials import game
from scripts.utility import event_text_adjust


NEW_CONDITIONS = {"breathless fit": "illnesses", "tick fever": "illnesses", "sore throat": "injuries",
                  "absent": "permanent_condition", "damaged throat": "permanent_condition",
                  "selective mutism": "permanent_condition", "strange lump": "permanent_condition",
                  "amputated leg": "injuries", "amputated tail": "injuries"}
SOURCES = {"illnesses": ILLNESSES, "injuries": INJURIES, "permanent_condition": PERMANENT}


@pytest.fixture
def clinic(monkeypatch):
    for target, name, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                                (Cat, "outside_cats", {}), (Cat, "dead_cats", []),
                                (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, name, value)
    clan = Clan(name="ConditionTest", biome="Forest", camp_bg="camp1", game_mode="expanded")
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setattr(game, "safe_save", Mock(side_effect=AssertionError("No real save writes")))
    for name in ("cur_events_list", "herb_events_list", "just_died"):
        monkeypatch.setattr(game, name, [])
    monkeypatch.setattr(game, "switches", {**game.switches, "skip_conditions": [], "window_open": False})
    cat = Cat(prefix="Moss", status="warrior", moons=40)
    other = Cat(prefix="Bee", status="warrior", moons=40)
    for actor in (cat, other):
        actor.pelt.scars = []
        actor.history = History()
        clan.add_cat(actor)
        actor.create_inheritance_new_cat()
    clan.your_cat = other
    return clan, cat, other


def acquire(cat, name, **kwargs):
    group = NEW_CONDITIONS.get(name)
    if group is None:
        group = "illnesses" if name in ILLNESSES else "injuries" if name in INJURIES else "permanent_condition"
    with patch("scripts.cat.cats.random", return_value=.9):
        if group == "illnesses":
            cat.get_ill(name, **kwargs)
        elif group == "injuries":
            cat.get_injured(name, **kwargs)
        else:
            cat.get_permanent_condition(name, **kwargs)
    return getattr(cat, group)[name]


@pytest.mark.parametrize("name,group", NEW_CONDITIONS.items())
@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_new_conditions_acquire_and_persist_through_real_condition_and_history_files(clinic, monkeypatch, tmp_path, name, group, mode):
    clan, cat, _ = clinic
    clan.game_mode = mode
    acquire(cat, name, cause="A recorded condition event.")
    expected = deepcopy(getattr(cat, group))
    assert cat.history.condition_events[-1]["condition"] == name
    monkeypatch.setattr("scripts.cat.cats.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "switches", {**game.switches, "clan_name": clan.name})
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    cat.save_condition()
    cat.save_history(str(tmp_path / clan.name / "history"))
    getattr(cat, group).clear()
    cat.history = None
    cat.load_conditions()
    cat.load_history()
    assert getattr(cat, group) == expected
    assert cat.history.condition_events[-1]["cause"] == "A recorded condition event."


@pytest.mark.parametrize("name,group", NEW_CONDITIONS.items())
def test_new_definitions_have_known_herbs_and_complete_risk_text(name, group):
    herbs = set(json.loads(Path("resources/dicts/herbs.json").read_text(encoding="utf-8")))
    definition = SOURCES[group][name]
    assert set(definition["mortality"]) == set(Cat.ages)
    assert all(herb in herbs for tier in definition["herbs"].values() for herb in tier)
    risk_strings = {"illnesses": Condition_Events.ILLNESS_RISK_STRINGS,
                    "injuries": Condition_Events.INJURY_RISK_STRINGS,
                    "permanent_condition": Condition_Events.PERM_CONDITION_RISK_STRINGS}[group]
    for risk in definition["risks"]:
        assert any(risk["name"] in source for source in SOURCES.values())
        strings = risk_strings[name][risk["name"]]
        assert strings and any("r_c" not in text for text in strings)


RISK_LINKS = [("tick bites", "tick fever"), ("raspy lungs", "breathless fit"),
              ("greencough", "sore throat"), ("kittencough", "sore throat"),
              ("running nose", "sore throat"), ("whitecough", "sore throat"),
              ("yellowcough", "sore throat"), ("dehydrated", "sore throat"),
              ("a festering wound", "strange lump"), ("grief stricken", "selective mutism"),
              ("lasting grief", "absent"), ("recurring shock", "selective mutism"),
              ("absent", "selective mutism"), ("damaged throat", "sore throat"),
              ("strange lump", "paralyzed")]


@pytest.mark.parametrize("source,target", RISK_LINKS)
@pytest.mark.parametrize("has_medic", [False, True])
def test_risk_progression_acquires_target_and_renders_without_missing_cats(clinic, source, target, has_medic):
    clan, cat, medic = clinic
    cat.name.suffix = "terror"
    if has_medic:
        medic.status = "medicine cat"
        clan.medicine_cat = medic
        clan.med_cat_list = [medic.ID]
    if source == "kittencough":
        cat.status = "kitten"
        cat.moons = 3
    info = acquire(cat, source)
    info["risks"] = [deepcopy(next(risk for risk in SOURCES[
        "illnesses" if source in ILLNESSES else "injuries" if source in INJURIES else "permanent_condition"][source]["risks"]
        if risk["name"] == target))]
    conditions = cat.illnesses if source in cat.illnesses else cat.injuries if source in cat.injuries else cat.permanent_condition
    text = []
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0):
        Condition_Events.give_risks(cat, text, source, {}, conditions.copy(), conditions)
    assert any(target in getattr(cat, group) for group in SOURCES)
    assert text and all(not re.search(r"\berror\b", line, re.IGNORECASE) and "r_c" not in line and "{PRONOUN" not in line for line in text)
    assert cat.history.condition_events[-1]["condition"] == target
    assert cat.history.condition_events[-1]["cause"] == text[-1]


@pytest.mark.parametrize("injury,target", [("sore throat", "damaged throat"), ("broken jaw", "damaged throat"),
                                           ("lingering shock", "absent"), ("lingering shock", "selective mutism"),
                                           ("head damage", "absent")])
def test_healed_injuries_can_gain_new_scarless_conditions(clinic, injury, target):
    _, cat, _ = clinic
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0), patch(
            "scripts.events_module.short.condition_events.random.choice", side_effect=lambda values: target if target in values else values[0]):
        result = Condition_Events.handle_permanent_conditions(cat, injury_name=injury)
    assert result == target and target in cat.permanent_condition
    assert injury in cat.history.condition_events[-1]["cause"]


@pytest.mark.parametrize("name", ["selective mutism", "absent", "strange lump"])
def test_congenital_reveal_has_safe_text_without_medic_or_parents(clinic, name):
    _, cat, _ = clinic
    cat.status = "kitten"
    cat.moons = 3
    info = acquire(cat, name, born_with=True)
    info["moons_until"] = 0
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0):
        Condition_Events.handle_already_disabled(cat)
    assert info["moons_until"] == -2
    assert cat.history.condition_events[-1]["kind"] == "congenital"
    assert game.cur_events_list
    assert all(not re.search(r"\berror\b", event.text, re.IGNORECASE) and "r_c" not in event.text for event in game.cur_events_list)


@pytest.mark.parametrize("effect", ["mortality", "duration", "risks"])
@pytest.mark.parametrize("strength", [1, 3])
def test_tiered_treatment_uses_stock_and_strength_on_live_state(clinic, effect, strength):
    clan, cat, _ = clinic
    info = acquire(cat, "tick fever")
    info.update(mortality=20, duration=5, risks=[{"name": "sore throat", "chance": 20}])
    herb = "moss" if strength == 1 else "goldenrod"
    clan.herbs = {herb: 1}
    with patch("scripts.events_module.short.condition_events.random.choice", return_value=effect):
        Condition_Events.use_herbs(cat, "tick fever", cat.illnesses.copy(), ILLNESSES)
    assert herb not in clan.herbs
    assert info["mortality"] == (20 + 3 * strength + 1 if effect == "mortality" else 20)
    assert info["duration"] == (5 - strength if effect == "duration" else 5)
    assert info["risks"][0]["chance"] == (20 + 3 * strength + 1 if effect == "risks" else 20)
    assert herb in game.herb_events_list[-1]


@pytest.mark.parametrize("name", ["running nose", "tick fever", "recurring shock"])
def test_patient_risks_are_isolated_from_other_cats_and_definitions(clinic, name):
    clan, cat, other = clinic
    first = acquire(cat, name)
    second = acquire(other, name)
    group = "illnesses" if name in ILLNESSES else "permanent_condition"
    baseline = deepcopy(SOURCES[group][name]["risks"])
    first["risks"].append({"name": "sore throat", "chance": 200})
    assert second["risks"] == baseline
    assert SOURCES[group][name]["risks"] == baseline


@pytest.mark.parametrize("name", ["breathless fit", "tick fever", "sore throat"])
def test_temporary_conditions_heal_with_actual_healing_handler(clinic, name):
    clan, cat, _ = clinic
    info = acquire(cat, name)
    info.update(mortality=0, duration=0, moon_start=0)
    clan.age = 5
    with patch("scripts.cat.cats.random", return_value=.9), patch(
            "scripts.events_module.short.condition_events.random.random", return_value=.9):
        if name in ILLNESSES:
            Condition_Events.handle_illnesses(cat, "Newleaf")
        else:
            Condition_Events.handle_injuries(cat)
    assert name not in getattr(cat, NEW_CONDITIONS[name])
    assert game.cur_events_list
    assert all(not re.search(r"\berror\b", event.text, re.IGNORECASE) and "r_c" not in event.text for event in game.cur_events_list)


@pytest.mark.parametrize("role", ["m_c", "r_c"])
@pytest.mark.parametrize("condition,field", [("tick fever", "has_injuries"), ("sore throat", "has_injuries"),
                                             ("damaged throat", "perm_conditions")])
def test_condition_thoughts_match_only_the_affected_cat(clinic, role, condition, field):
    _, cat, other = clinic
    thought = {"thoughts": ["Is resting."], field: {role: [condition]}}
    assert not Thoughts.cats_fulfill_thought_constraints(cat, other, thought, "expanded", "forest", "Newleaf", "camp1")
    acquire(cat if role == "m_c" else other, condition)
    assert Thoughts.cats_fulfill_thought_constraints(cat, other, thought, "expanded", "forest", "Newleaf", "camp1")


def test_unrevealed_congenital_condition_does_not_unlock_condition_thoughts(clinic):
    _, cat, other = clinic
    cat.status = "kitten"
    cat.moons = 3
    info = acquire(cat, "strange lump", born_with=True)
    thought = {"thoughts": ["Is worried about the lump."], "perm_conditions": {"m_c": ["strange lump"]}}
    assert not Thoughts.cats_fulfill_thought_constraints(cat, other, thought, "expanded", "forest", "Newleaf", "camp1")
    info["moons_until"] = -2
    assert Thoughts.cats_fulfill_thought_constraints(cat, other, thought, "expanded", "forest", "Newleaf", "camp1")


@pytest.mark.parametrize("name,group", [("tick fever", "illnesses"), ("recurring shock", "permanent_condition")])
def test_classic_tiered_treatment_is_basic_and_does_not_consume_stock(clinic, name, group):
    clan, cat, _ = clinic
    clan.game_mode = "classic"
    info = acquire(cat, name)
    info["mortality"] = 20
    clan.herbs = {"goldenrod": 4}
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="mortality"):
        Condition_Events.use_herbs(cat, name, getattr(cat, group).copy(), SOURCES[group])
    assert info["mortality"] == 24 and clan.herbs == {"goldenrod": 4}


@pytest.mark.parametrize("name,group,herb", [("tick fever", "illnesses", "goldenrod"),
                                          ("sore throat", "injuries", "juniper"),
                                          ("damaged throat", "permanent_condition", "juniper")])
def test_treatment_survives_public_lifecycle_processing(clinic, name, group, herb):
    clan, cat, medic = clinic
    medic.status = "medicine cat"
    info = acquire(cat, name)
    info["mortality"] = 20
    clan.herbs = {herb: 2}
    def choose(values):
        return "mortality" if "mortality" in values else values[0]
    with patch("scripts.events_module.short.condition_events.random.choice", side_effect=choose), patch(
            "scripts.events_module.short.condition_events.random.random", return_value=0), patch(
            "scripts.cat.cats.random", return_value=.99):
        Condition_Events.handle_herbs(clan)
        if group == "illnesses":
            Condition_Events.handle_illnesses(cat, "Newleaf")
        elif group == "injuries":
            Condition_Events.handle_injuries(cat)
        else:
            Condition_Events.handle_already_disabled(cat)
    assert info["mortality"] > 20
    assert clan.herbs[herb] == 1


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_disposable_colony_runs_full_moons_with_all_new_conditions(clinic, monkeypatch, tmp_path, mode):
    from scripts.events import Events

    clan, cat, player = clinic
    clan.game_mode = mode
    clan.leader = player
    clan.starting_members = [cat, player]
    for module in ("scripts.clan", "scripts.cat.cats", "scripts.game_structure.game_essentials", "scripts.game_structure.load_cat"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    for field in ("next_events_list", "patrolled", "just_died", "dated_cats", "mediated", "told_story"):
        monkeypatch.setattr(game, field, [])
    monkeypatch.setattr(Cat, "grief_strings", {})
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    with patch.dict(game.switches, {"clan_list": [clan.name], "clan_name": clan.name}):
        clan.create_clan()
        patients = []
        for condition in NEW_CONDITIONS:
            patient = Cat(status="warrior", moons=40)
            patient.history = History()
            clan.add_cat(patient)
            patient.create_inheritance_new_cat()
            acquire(patient, condition)
            patients.append(patient)
        clan.herbs = {herb: 20 for herb in json.loads(Path("resources/dicts/herbs.json").read_text(encoding="utf-8"))}
        clan.clan_settings["autosave"] = False
        events = Events()
        for _ in range(2):
            events.one_moon()
        game.save_cats()
        clan.save_clan()
        for patient in patients:
            expected = deepcopy((patient.illnesses, patient.injuries, patient.permanent_condition))
            patient.load_conditions()
            assert (patient.illnesses, patient.injuries, patient.permanent_condition) == expected
        assert clan.age == 2
        assert not any("this should not show up" in event for event in game.herb_events_list)


@pytest.mark.parametrize("name", ["breathless fit", "tick fever", "strange lump"])
def test_lethal_conditions_record_actual_death_text_and_history(clinic, name):
    _, cat, _ = clinic
    acquire(cat, name)["mortality"] = 1
    with patch("scripts.cat.cats.random", return_value=0), patch(
            "scripts.events_module.short.condition_events.random.random", return_value=.9):
        if name in ILLNESSES:
            Condition_Events.handle_illnesses(cat, "Newleaf")
        else:
            Condition_Events.handle_already_disabled(cat)
    assert cat.dead and cat.history.died_by
    assert game.cur_events_list
    assert all("placeholder" not in event.text and not re.search(r"\berror\b", event.text, re.IGNORECASE) for event in game.cur_events_list)


@pytest.mark.parametrize("season", ["Newleaf", "Greenleaf"])
def test_tick_fever_is_acquired_from_actual_seasonal_pool(clinic, season):
    _, cat, _ = clinic
    pool = Condition_Events.ILLNESSES_SEASON_LIST[season]
    index = sum(pool.values()) - pool["tick fever"]
    roll = (index + .1) / sum(pool.values())
    with patch("scripts.events_module.short.condition_events.random.random", side_effect=[0, roll]):
        Condition_Events.handle_illnesses(cat, season)
    assert "tick fever" in cat.illnesses and game.cur_events_list
    assert all("tick fever" not in Condition_Events.ILLNESSES_SEASON_LIST[season]
               for season in ("Leaf-fall", "Leaf-bare"))


def test_existing_cross_group_risk_is_not_reported_or_acquired_again(clinic):
    _, cat, _ = clinic
    info = acquire(cat, "tick bites")
    acquire(cat, "tick fever")
    info["risks"] = [{"name": "tick fever", "chance": 1}]
    before = deepcopy(cat.history.condition_events)
    messages = []
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0):
        Condition_Events.give_risks(cat, messages, "tick bites", {}, cat.injuries.copy(), cat.injuries)
    assert not messages and cat.history.condition_events == before


def test_local_permanent_conditions_are_retained():
    assert {"testosterone deficiency", "excess testosterone", "aneuploidy", "mosaicism", "chimerism",
            "cleft palate", "wobbly cat syndrome"} <= PERMANENT.keys()


@pytest.mark.parametrize("name", ["running nose", "small cut"])
@pytest.mark.parametrize("focus,elapsed,complication,healed", [
    (False, 3, None, False), (True, 2, None, False), (True, 3, None, True),
    (False, 4, None, True), (True, 3, "infected", False),
])
def test_recovery_focus_heals_one_moon_earlier_without_bypassing_injury_infection(clinic, name, focus, elapsed, complication, healed):
    clan, cat, _ = clinic
    info = acquire(cat, name, lethal=False)
    info.update(duration=4, moon_start=0, event_triggered=False)
    if name in cat.injuries:
        info["complication"] = complication
    clan.age = elapsed
    cat.healed_condition = False
    clan.clan_settings["rest and recover"] = focus
    if name in cat.illnesses:
        cat.moon_skip_illness(name)
        assert cat.healed_condition is (healed or (focus and elapsed == 3))
    else:
        cat.moon_skip_injury(name)
        assert cat.healed_condition is healed


@pytest.mark.parametrize("old,new", [("LEFTBLIND", "RIGHTBLIND"), ("RIGHTBLIND", "LEFTBLIND")])
def test_healing_the_other_eye_combines_scars_without_crashing(clinic, old, new):
    from scripts.events_module.short.scar_events import Scar_Events

    clan, cat, _ = clinic
    acquire(cat, "damaged eyes", lethal=False).update(duration=1, moon_start=0, predetermined_scar=new)
    cat.pelt.scars = [old]
    clan.age = 1
    with patch("scripts.events_module.short.scar_events.random.random", return_value=0):
        event, scar = Scar_Events.handle_scars(cat, "damaged eyes")
    assert scar == "BOTHBLIND" and cat.pelt.scars == ["BOTHBLIND"]
    assert event and len(cat.history.scar_events) == 1


@pytest.mark.parametrize("equipped,stored", [(True, False), (True, True), (False, True)])
def test_paw_loss_removes_incompatible_accessories_from_the_correct_lists(clinic, equipped, stored):
    from scripts.events_module.short.scar_events import Scar_Events

    clan, cat, _ = clinic
    acquire(cat, "mangled leg", lethal=False).update(duration=1, moon_start=0, predetermined_scar="NOPAW")
    cat.pelt.scars = []
    cat.pelt.accessories = ["VINE", "BLUE COLLAR"] if equipped else ["BLUE COLLAR"]
    cat.pelt.inventory = ["VINE", "BLUE COLLAR"] if stored else ["BLUE COLLAR"]
    clan.age = 1
    with patch("scripts.events_module.short.scar_events.random.random", return_value=0):
        event, scar = Scar_Events.handle_scars(cat, "mangled leg")
    assert scar == "NOPAW" and event
    assert cat.pelt.accessories == cat.pelt.inventory == ["BLUE COLLAR"]


def test_healed_injuries_can_add_scars_beyond_four_and_preserve_history(clinic, monkeypatch, tmp_path):
    clan, cat, _ = clinic
    acquire(cat, "claw-wound", lethal=False).update(duration=1, moon_start=0, predetermined_scar="CHEEK")
    cat.pelt.scars = ["ONE", "TWO", "SNOUT", "SIDE", "BACK"]
    clan.age = 1
    with patch("scripts.events_module.short.scar_events.random.random", return_value=0):
        assert Condition_Events.handle_already_injured(cat)
    assert "claw-wound" not in cat.injuries
    assert cat.pelt.scars == ["ONE", "TWO", "SNOUT", "SIDE", "BACK", "CHEEK"]
    assert len(cat.history.scar_events) == 1 and game.cur_events_list
    from scripts.game_structure.load_cat import load_cats

    for module in ("scripts.cat.cats", "scripts.game_structure.game_essentials", "scripts.game_structure.load_cat"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setitem(game.switches, "clan_list", [clan.name])
    monkeypatch.setitem(game.switches, "clan_name", clan.name)
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    expected = cat.pelt.scars.copy()
    cat_id = cat.ID
    game.save_cats()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    restored = Cat.fetch_cat(cat_id)
    restored.load_history()
    assert restored.pelt.scars == expected and len(restored.history.scar_events) == 1


@pytest.mark.parametrize("actor", ["m_c", "r_c"])
@pytest.mark.parametrize("health,blocked", [("healthy", False), ("minor", False), ("major", True), ("permanent", False)])
def test_authored_work_constraints_use_temporary_severity_for_the_correct_cat(clinic, actor, health, blocked):
    from scripts.cat.personality import Personality
    from scripts.cat_relations.interaction import INTERACTION_MASTER_DICT, cats_fulfill_single_interaction_constraints

    _, main, other = clinic
    patient = main if actor == "m_c" else other
    if health in ("minor", "major"):
        acquire(patient, "running nose", lethal=False)["severity"] = health
    elif health == "permanent":
        acquire(patient, "weak leg")["severity"] = "severe"
    checked = 0
    for types in INTERACTION_MASTER_DICT.values():
        for interactions in types.values():
            for interaction in interactions:
                if not interaction.working_constraint:
                    continue
                if interaction.main_status_constraint:
                    main.status = interaction.main_status_constraint[0]
                if interaction.random_status_constraint:
                    other.status = interaction.random_status_constraint[0]
                if interaction.main_trait_constraint:
                    main.personality = Personality(trait=interaction.main_trait_constraint[0])
                expected = not (blocked and actor in interaction.working_constraint)
                assert cats_fulfill_single_interaction_constraints(main, other, interaction, "expanded") is expected, interaction.id
                checked += 1
    assert checked == 30


@pytest.mark.parametrize("visitor_working", [False, True])
def test_recovering_cat_can_receive_a_patrol_visit_but_cannot_join_the_patrol(clinic, monkeypatch, visitor_working):
    from scripts.cat_relations.relationship import Relationship
    from scripts.cat_relations.interaction import INTERACTION_MASTER_DICT

    clan, patient, visitor = clinic
    acquire(patient, "running nose", lethal=False)["severity"] = "major"
    if not visitor_working:
        acquire(visitor, "small cut", lethal=False)["severity"] = "major"
    relation = patient.create_one_relationship(visitor)
    variants = [event for event in INTERACTION_MASTER_DICT["comfortable"]["increase"]
                if event.id.startswith("comfort_inc_med3_working_")]
    monkeypatch.setitem(INTERACTION_MASTER_DICT["comfortable"], "increase", variants)
    monkeypatch.setitem(game.config["relationship"], "chance_for_neutral", 0)
    monkeypatch.setattr(Relationship, "used_interaction_ids", [])
    with patch.object(Relationship, "positive_interaction", return_value=True), patch.object(
            Relationship, "get_interaction_type", return_value="comfortable"), patch(
            "scripts.cat_relations.relationship.random.choices", return_value=["medium"]):
        relation.start_interaction()
    if visitor_working:
        assert relation.chosen_interaction.id == "comfort_inc_med3_working_random"
        assert relation.comfortable > 0 and relation.log and game.cur_events_list
    else:
        assert relation.chosen_interaction is None and not relation.log and not game.cur_events_list


@pytest.mark.parametrize("name", ["running nose", "small cut"])
def test_recovery_focus_completes_the_actual_healing_handler_after_reload(clinic, monkeypatch, tmp_path, name):
    clan, cat, _ = clinic
    acquire(cat, name, lethal=False).update(duration=4, moon_start=0, event_triggered=False)
    monkeypatch.setattr("scripts.cat.cats.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setitem(game.switches, "clan_name", clan.name)
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    cat.save_condition()
    cat.illnesses.clear()
    cat.injuries.clear()
    cat.load_conditions()
    clan.age = 3
    clan.clan_settings["rest and recover"] = True
    with patch("scripts.events_module.short.scar_events.random.random", return_value=.9):
        if name in ILLNESSES:
            text = Condition_Events.handle_already_ill(cat)
        else:
            assert Condition_Events.handle_already_injured(cat)
            text = game.cur_events_list[-1].text
    assert name not in cat.illnesses and name not in cat.injuries
    assert text and str(cat.name) in text
    cat.save_condition()
    cat.load_conditions()
    assert name not in cat.illnesses and name not in cat.injuries


@pytest.mark.parametrize("mode,cards", [("expanded", None), ("classic", None), ("cruel season", ["burnout", "longer_illnesses"])])
@pytest.mark.parametrize("medic_working", [False, True])
@pytest.mark.parametrize("variation", [-1, 0])
def test_injury_duration_uses_actual_medical_coverage_and_keeps_the_existing_variation(clinic, monkeypatch, tmp_path, mode, cards, medic_working, variation):
    from scripts.conditions import medical_cats_condition_fulfilled, get_amount_cat_for_one_medic

    clan, cat, medic = clinic
    clan.game_mode, clan.cruel_cards = mode, cards
    medic.status = "medicine cat"
    if not medic_working:
        acquire(medic, "running nose", lethal=False)["severity"] = "major"
    assert medical_cats_condition_fulfilled(Cat.all_cats.values(), get_amount_cat_for_one_medic(clan)) is medic_working
    with patch("scripts.cat.cats.randrange", return_value=variation):
        info = acquire(cat, "broken bone", lethal=False)
    base = INJURIES["broken bone"]["medicine_duration" if medic_working else "duration"]
    assert info["duration"] == max(1, base + variation)
    monkeypatch.setattr("scripts.cat.cats.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setitem(game.switches, "clan_name", clan.name)
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    expected = deepcopy(info)
    cat.save_condition()
    cat.injuries.clear()
    cat.load_conditions()
    assert cat.injuries["broken bone"] == expected


@pytest.mark.parametrize("name,scar", [("amputated leg", "NOPAW"), ("amputated tail", "NOTAIL")])
def test_amputation_acquisition_requires_anatomy_and_applies_one_immediate_scar(clinic, name, scar):
    _, cat, _ = clinic
    with patch("scripts.events_module.short.scar_events.random.choice", side_effect=lambda values: scar if scar in values else values[0]):
        info = acquire(cat, name)
    assert info["mortality"] == 0 and info["event_triggered"] is False
    assert cat.pelt.scars == [scar] and len(cat.history.scar_events) == 1
    before = deepcopy((cat.injuries, cat.history.condition_events, cat.history.scar_events))
    cat.get_injured(name)
    assert (cat.injuries, cat.history.condition_events, cat.history.scar_events) == before
    cat.injuries.clear()
    cat.get_injured(name)
    assert not cat.injuries and len(cat.history.scar_events) == 1


@pytest.mark.parametrize("source,target,roll", [("mangled leg", "amputated leg", .39),
    ("mangled tail", "amputated tail", .49), ("severe burn", "amputated tail", .19),
    ("severe burn", "amputated leg", .19)])
@pytest.mark.parametrize("has_medic", [False, True])
def test_actual_wound_progression_replaces_only_the_source_and_records_resolved_cause(clinic, monkeypatch, source, target, roll, has_medic):
    clan, cat, medic = clinic
    if has_medic:
        medic.status = "medicine cat"
    acquire(cat, source, lethal=False).update(duration=10, moon_start=0, event_triggered=False)
    acquire(cat, "small cut", lethal=False).update(duration=10, moon_start=0)
    monkeypatch.setattr(game, "cat_class", Cat)
    rolls = iter([.9, roll] if source == "severe burn" and target == "amputated leg" else [roll])
    with patch("scripts.events_module.short.condition_events.random.random", side_effect=lambda: next(rolls, .9)), patch(
            "scripts.cat.cats.random", return_value=.9):
        assert Condition_Events.handle_already_injured(cat)
    assert source not in cat.injuries and target in cat.injuries and "small cut" in cat.injuries
    assert cat.injuries[target]["event_triggered"] is True and target in game.switches["skip_conditions"]
    assert cat.history.condition_events[-1]["condition"] == target
    assert cat.history.condition_events[-1]["cause"] in game.cur_events_list[-1].text
    assert len(cat.history.scar_events) == 1
    assert all("r_c" not in e.text and "{PRONOUN" not in e.text and "placeholder" not in e.text for e in game.cur_events_list)


@pytest.mark.parametrize("source,roll", [("mangled leg", .4), ("mangled tail", .5), ("severe burn", .2)])
def test_progression_probability_boundary_leaves_the_original_wound(clinic, source, roll):
    _, cat, _ = clinic
    acquire(cat, source, lethal=False)
    before = deepcopy(cat.injuries)
    lines = []
    with patch("scripts.events_module.short.condition_events.random.random", return_value=roll):
        assert not Condition_Events.handle_injury_progression(cat, source, lines)
    assert cat.injuries == before and not lines and not cat.history.scar_events


@pytest.mark.parametrize("source,scar", [("mangled leg", "NOPAW"), ("mangled tail", "NOTAIL")])
def test_unavailable_required_scar_cannot_remove_the_original_wound_or_report_surgery(clinic, source, scar):
    _, cat, _ = clinic
    acquire(cat, source, lethal=False)
    cat.pelt.scars = [scar]
    before = deepcopy((cat.injuries, cat.history.condition_events))
    lines = []
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0):
        assert not Condition_Events.handle_injury_progression(cat, source, lines)
    assert (cat.injuries, cat.history.condition_events) == before and not lines


@pytest.mark.parametrize("name,target,scar", [("amputated leg", "lost a leg", "NOPAW"),
                                            ("amputated tail", "lost their tail", "HALFTAIL")])
@pytest.mark.parametrize("has_medic", [False, True])
def test_amputation_healing_keeps_recovery_and_permanent_messages_without_a_second_scar(clinic, name, target, scar, has_medic):
    clan, cat, medic = clinic
    if has_medic:
        medic.status = "medicine cat"
    with patch("scripts.events_module.short.scar_events.random.choice", side_effect=lambda values: scar if scar in values else values[0]):
        info = acquire(cat, name)
    info.update(duration=2, moon_start=0, event_triggered=False)
    clan.age = 2
    with patch("scripts.events_module.short.condition_events.random.random", return_value=.9):
        assert Condition_Events.handle_already_injured(cat)
    assert name not in cat.injuries and target in cat.permanent_condition
    assert cat.pelt.scars == [scar] and len(cat.history.scar_events) == 1
    assert len(game.herb_events_list) == 2
    text = game.cur_events_list[-1].text
    assert text == " ".join(game.herb_events_list)
    assert "healed" in game.herb_events_list[0]
    assert cat.history.condition_events[-1]["condition"] == target
    assert "r_c" not in text and "{PRONOUN" not in text


@pytest.mark.parametrize("name", ["amputated leg", "amputated tail"])
def test_amputation_wounds_can_infect_and_infection_blocks_recovery(clinic, name):
    clan, cat, _ = clinic
    info = acquire(cat, name)
    info.update(duration=2, moon_start=0, event_triggered=False)
    lines = []
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0):
        Condition_Events.give_risks(cat, lines, name, {}, cat.injuries.copy(), cat.injuries)
    assert "an infected wound" in cat.illnesses and info["complication"] == "infected"
    clan.age = 4
    with patch("scripts.cat.cats.random", return_value=.9):
        Condition_Events.handle_already_injured(cat)
    assert name in cat.injuries and len(cat.history.scar_events) == 1


def test_full_tail_loss_replaces_the_partial_tail_scar(clinic):
    _, cat, _ = clinic
    cat.pelt.scars = ["HALFTAIL"]
    acquire(cat, "amputated tail")
    assert cat.pelt.scars == ["NOTAIL"]


def test_ordinary_healed_injury_retains_its_healing_message_before_the_new_condition(clinic):
    clan, cat, _ = clinic
    acquire(cat, "sore throat", lethal=False).update(duration=1, moon_start=0)
    clan.age = 1
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0):
        assert Condition_Events.handle_already_injured(cat)
    assert "damaged throat" in cat.permanent_condition
    assert len(game.herb_events_list) == 2
    assert game.cur_events_list[-1].text == " ".join(game.herb_events_list)


@pytest.mark.parametrize("mode,cards", [("classic", None), ("expanded", None),
                                       ("cruel season", ["burnout", "longer_illnesses", "weak_stars"])])
@pytest.mark.parametrize("part,permanent,scar", [("leg", "lost a leg", "NOPAW"), ("tail", "lost their tail", "HALFTAIL")])
def test_amputation_stages_survive_real_colony_creation_and_repeated_reload(clinic, monkeypatch, tmp_path, mode, cards, part, permanent, scar):
    from scripts.game_structure.load_cat import load_cats

    clan, cat, leader = clinic
    clan.game_mode, clan.cruel_cards = mode, cards
    clan.leader = leader
    clan.starting_members = [cat, leader]
    for module in ("scripts.cat.cats", "scripts.clan", "scripts.game_structure.game_essentials", "scripts.game_structure.load_cat"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    monkeypatch.setitem(game.switches, "clan_list", [clan.name])
    monkeypatch.setitem(game.switches, "clan_name", clan.name)
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    clan.create_clan()
    original, wound = "mangled " + part, "amputated " + part
    acquire(cat, original, lethal=False).update(duration=10, moon_start=0, event_triggered=False)
    cat_id = cat.ID
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0), patch(
            "scripts.cat.cats.random", return_value=.9), patch(
            "scripts.events_module.short.scar_events.random.choice", side_effect=lambda values: scar if scar in values else values[0]):
        assert Condition_Events.handle_already_injured(cat)
    expected = deepcopy(cat.injuries)
    game.save_cats()
    clan.save_clan()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    cat = Cat.fetch_cat(cat_id)
    cat.load_history()
    assert cat.injuries == expected and cat.pelt.scars == [scar]
    assert len(cat.history.scar_events) == 1 and permanent not in cat.permanent_condition
    monkeypatch.setitem(game.switches, "skip_conditions", [])
    Condition_Events.handle_already_injured(cat)
    assert cat.injuries[wound]["event_triggered"] is False
    game.clan.age += cat.injuries[wound]["duration"] + 1
    assert Condition_Events.handle_already_injured(cat)
    assert permanent in cat.permanent_condition and wound not in cat.injuries
    assert len(cat.history.scar_events) == 1
    game.save_cats()
    game.clan.save_clan()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    cat = Cat.fetch_cat(cat_id)
    cat.load_history()
    assert cat.pelt.scars == [scar] and permanent in cat.permanent_condition
    assert wound not in cat.injuries and len(cat.history.scar_events) == 1
    assert [item["condition"] for item in cat.history.condition_events][-3:] == [original, wound, permanent]
    assert game.clan.game_mode == mode and game.clan.cruel_cards == cards


@pytest.mark.parametrize("name", ["amputated leg", "amputated tail"])
@pytest.mark.parametrize("leader", [False, True])
def test_amputation_blood_loss_can_be_fatal_and_uses_its_own_life_and_history_rules(clinic, name, leader):
    clan, cat, _ = clinic
    if leader:
        clan.leader = cat
        cat.status = "leader"
        clan.leader_lives = 9
    with patch("scripts.cat.cats.random", return_value=0):
        cat.get_injured(name)
    assert cat.injuries[name]["mortality"] == 0 and "blood loss" in cat.injuries
    cat.injuries["blood loss"].update(mortality=1, event_triggered=False)
    with patch("scripts.cat.cats.random", return_value=0), patch(
            "scripts.events_module.short.condition_events.random.random", return_value=.9):
        assert Condition_Events.handle_already_injured(cat)
    assert cat.dead is not leader
    assert not leader or clan.leader_lives == 8
    assert cat.history.died_by and "blood" in cat.history.died_by[-1]["text"]
    assert len(cat.history.scar_events) == 1


@pytest.mark.parametrize("name", ["amputated leg", "amputated tail"])
def test_amputation_treatment_uses_real_herb_strength_and_stock(clinic, name):
    clan, cat, _ = clinic
    info = acquire(cat, name)
    clan.herbs = {"goldenrod": 1}
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="risks"):
        Condition_Events.use_herbs(cat, name, cat.injuries.copy(), INJURIES)
    assert info["mortality"] == 0 and info["risks"][0]["chance"] > 5
    assert not clan.herbs and game.herb_events_list


@pytest.mark.parametrize("available", [False, True])
def test_amputation_scar_retains_the_original_injury_history_and_involved_cat(clinic, available):
    _, cat, other = clinic
    acquire(cat, "mangled leg", lethal=False)
    History.add_possible_history(cat, "mangled leg", scar_text="m_c was injured protecting r_c.", other_cat=other)
    expected = deepcopy(cat.history.possible_history)
    if not available:
        cat.pelt.scars = ["NOPAW"]
    lines = []
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0), patch(
            "scripts.cat.cats.random", return_value=.9):
        result = Condition_Events.handle_injury_progression(cat, "mangled leg", lines)
    if available:
        assert result and cat.history.scar_events[-1]["text"] == "m_c was injured protecting r_c."
        assert cat.history.scar_events[-1]["involved"] == other.ID
        assert "mangled leg" not in cat.history.possible_history
    else:
        assert not result and cat.history.possible_history == expected and not cat.history.scar_events


@pytest.mark.parametrize("part", ["leg", "tail"])
@pytest.mark.parametrize("illness,complication", [("an infected wound", "infected"), ("a festering wound", "festering")])
def test_wound_progression_preserves_existing_infection_until_it_is_cured(clinic, part, illness, complication):
    clan, cat, _ = clinic
    original, target = "mangled " + part, "amputated " + part
    acquire(cat, original, lethal=False)["complication"] = complication
    acquire(cat, illness, lethal=False).update(duration=2, moon_start=0, event_triggered=False)
    with patch("scripts.events_module.short.condition_events.random.random", return_value=0), patch(
            "scripts.cat.cats.random", return_value=.9):
        assert Condition_Events.handle_injury_progression(cat, original, [])
    assert cat.injuries[target]["complication"] == complication
    cat.injuries[target].update(duration=1, event_triggered=False)
    clan.age = 1
    with patch("scripts.events_module.short.condition_events.random.random", return_value=.9):
        Condition_Events.handle_already_injured(cat)
    assert target in cat.injuries
    clan.age = 2
    assert Condition_Events.handle_already_ill(cat)
    assert cat.injuries[target]["complication"] is None and illness not in cat.illnesses
    game.switches["skip_conditions"].clear()
    assert Condition_Events.handle_already_injured(cat)
    assert target not in cat.injuries
