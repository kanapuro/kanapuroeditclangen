import json
import random
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.cat.cats import Cat, PERMANENT
from scripts.cat.history import History
from scripts.cat.skills import Skill, SkillPath
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.clan_resources.herbs import HerbSupply, HERB_INFO
from scripts.events import Events
from scripts.events_module.patrol.patrol import Patrol
from scripts.events_module.patrol.patrol_outcome import PatrolOutcome
from scripts.events_module.short.condition_events import Condition_Events
from scripts.events_module.short.handle_short_events import HandleShortEvents
from scripts.game_structure.game_essentials import game


@pytest.fixture
def herbalists(monkeypatch):
    for target, name, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                                (Cat, "outside_cats", {}), (Cat, "dead_cats", []),
                                (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, name, value)
    clan = Clan(name="HerbTest", biome="Forest", camp_bg="camp1", game_mode="expanded")
    clan.all_clans = []
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setattr(game, "safe_save", Mock(side_effect=AssertionError("No real save writes")))
    for name in ("cur_events_list", "herb_events_list", "freshkill_event_list", "just_died"):
        monkeypatch.setattr(game, name, [])
    med = Cat(prefix="Moss", status="medicine cat", moons=40, gender="male")
    patient = Cat(prefix="Bee", status="warrior", moons=40, gender="female")
    med.skills.primary = Skill(SkillPath.HEALER, 10)
    med.skills.secondary = None
    for cat in (med, patient):
        cat.history = History()
        clan.add_cat(cat)
        cat.create_inheritance_new_cat()
    clan.your_cat = patient
    clan.medicine_cat = med
    clan.med_cat_list = [med.ID]
    return clan, med, patient


def test_total_mutations_consume_oldest_batches_without_refreshing_other_stock():
    supply = HerbSupply({"storage": {"moss": [2, 3]}, "collected": {"moss": 2}})
    supply["moss"] -= 4
    assert supply["moss"] == 3
    assert supply.storage["moss"] == [1, 0] and supply.collected["moss"] == 2
    supply["moss"] += 5
    assert supply.storage["moss"] == [1, 0] and supply.collected["moss"] == 7
    snapshot = supply.copy()
    snapshot["moss"] = 500
    assert supply["moss"] == 8 and dict(supply) == {"moss": 8}
    assert supply.pop("moss") == 8 and not supply


def test_legacy_totals_are_retained_as_fresh_stock_and_roundtrip_without_aliases():
    legacy = {"moss": 5, "catmint": 3}
    supply = HerbSupply(legacy)
    assert supply == legacy
    saved = supply.to_dict()
    restored = HerbSupply(json.loads(json.dumps(saved)))
    restored["moss"] -= 2
    assert supply["moss"] == 5 and legacy["moss"] == 5
    assert restored["moss"] == 3


@pytest.mark.parametrize("herb", ["ragwort", "juniper", "moss", "cobwebs"])
def test_per_herb_expiration_preserves_freshly_gathered_batches(herb, herbalists):
    supply = HerbSupply({"storage": {herb: [0] * (HERB_INFO[herb]["expiration"] - 1) + [7]}})
    supply[herb] += 2
    supply.begin_moon([])
    assert supply.expire() == {herb: 7}
    assert supply[herb] == 2
    assert "7" in game.herb_events_list[-1] and "Expired" in game.herb_events_list[-1]


def test_depletion_keeps_zero_readable_until_existing_callers_remove_it():
    supply = HerbSupply({"moss": 1})
    supply["moss"] -= 8
    assert supply["moss"] == 0
    supply.pop("moss")
    assert not supply


def test_unknown_merged_herbs_keep_their_quantity_without_invented_lifetimes(herbalists):
    supply = HerbSupply({"merged_herb": 7})
    for _ in range(40):
        supply.begin_moon([])
        supply.expire()
    assert supply == {"merged_herb": 7}
    assert supply.storage["merged_herb"] == [7]


@pytest.mark.parametrize("succeeds", [False, True])
def test_camp_skill_delays_storage_aging_without_duplicating_herbs(herbalists, succeeds):
    clan, med, _ = herbalists
    med.skills.primary = Skill(SkillPath.CAMP, 29)
    clan.herbs = {"storage": {"moss": [2, 4]}, "collected": {"moss": 3}}
    with patch("scripts.clan_resources.herbs.randint", return_value=1 if succeeds else 2):
        clan.herbs.begin_moon([med, med])
    assert clan.herbs["moss"] == 9
    assert clan.herbs.storage["moss"] == ([5, 4] if succeeds else [3, 2, 4])
    assert not clan.herbs.collected
    assert len(game.herb_events_list) == (1 if succeeds else 0)


@pytest.mark.parametrize("biome", ["Forest", "Plains", "Mountainous", "Beach"])
@pytest.mark.parametrize("season", ["Newleaf", "Greenleaf", "Leaf-fall", "Leaf-bare"])
def test_gathering_uses_only_eligible_biome_and_season_herbs(herbalists, biome, season):
    clan, med, _ = herbalists
    clan.biome, clan.current_season = biome, season
    clan.herbs = {}
    with patch("scripts.clan_resources.herbs.randint", return_value=1):
        found = clan.herbs.gather(med, clan)
    assert found
    assert all(HERB_INFO[herb]["rarity"].get(biome.casefold(), {}).get(season.casefold(), 0) > 0 for herb in found)
    assert clan.herbs == found and clan.herbs.collected == found


def test_urgent_patient_herbs_are_prioritized_over_other_low_stocks(herbalists):
    clan, med, patient = herbalists
    patient.get_ill("whitecough")
    clan.herbs = {}
    # Only one type may be gathered; source ordered whitecough treatment includes moss.
    with patch("scripts.clan_resources.herbs.randint", return_value=1):
        found = clan.herbs.gather(med, clan, max_types=1)
    assert len(found) == 1
    assert next(iter(found)) in {"plantain", "catmint", "ragwort", "juniper", "poppy", "mullein", "tansy", "moss"}


@pytest.mark.parametrize("path,primary", [(SkillPath.SENSE, True), (SkillPath.SENSE, False),
                                        (SkillPath.CLEVER, True), (SkillPath.CLEVER, False)])
def test_gathering_skill_perks_affect_variety_or_quantity(herbalists, path, primary):
    clan, med, _ = herbalists
    with patch("scripts.clan_resources.herbs.randint", return_value=1), patch(
            "scripts.clan_resources.herbs.choices", side_effect=lambda values, **kwargs: [values[0]]):
        baseline = clan.herbs.gather(med, clan)
        clan.herbs = {}
        if primary:
            med.skills.primary = Skill(path, 20)
        else:
            med.skills.secondary = Skill(path, 20)
        modified = clan.herbs.gather(med, clan)
    if path == SkillPath.SENSE:
        assert len(modified) > len(baseline)
    else:
        assert len(modified) == len(baseline)
        assert all(modified[name] > baseline[name] for name in baseline)


@pytest.mark.parametrize("focus", ["herb gathering", "closed borders", "hoarding"])
def test_focus_harvest_adds_to_existing_stock_instead_of_overwriting(herbalists, monkeypatch, focus):
    clan, med, _ = herbalists
    clan.herbs = {"moss": 7}
    clan.clan_settings.update({name: False for name in game.config["focus"]})
    clan.clan_settings.update({"business as usual": False, "rest and recover": False, focus: True})
    monkeypatch.setattr("scripts.clan_resources.herbs.HERB_INFO", {"moss": HERB_INFO["moss"]})
    with patch("scripts.clan_resources.herbs.randint", return_value=1), patch(
            "scripts.clan_resources.herbs.choices", side_effect=lambda values, **kwargs: [values[0]]), patch(
            "scripts.clan_resources.herbs.random", return_value=0):
        Events().handle_focus()
    assert clan.herbs["moss"] == 11


@pytest.mark.parametrize("adjust,expected", [("increase_3", 8), ("reduce_half", 2), ("reduce_full", 0)])
def test_short_event_supply_changes_keep_old_batch_ages(herbalists, adjust, expected):
    clan, _, _ = herbalists
    clan.herbs = {"storage": {"moss": [0, 5]}}
    handle = HandleShortEvents()
    handle.handle_herb_supply({"type": "moss", "adjust": adjust, "trigger": ["always"]})
    assert clan.herbs.get("moss", 0) == expected
    if adjust == "increase_3":
        assert clan.herbs.storage["moss"] == [0, 5]
        assert clan.herbs.collected["moss"] == 3


def test_event_can_increase_entire_store_and_create_a_specific_missing_herb(herbalists):
    clan, _, _ = herbalists
    clan.herbs = {"moss": 2, "catmint": 3}
    HandleShortEvents().handle_herb_supply({"type": "all_herb", "adjust": "increase_2", "trigger": ["always"]})
    assert clan.herbs == {"moss": 4, "catmint": 5}
    HandleShortEvents().handle_herb_supply({"type": "juniper", "adjust": "increase_3", "trigger": ["always"]})
    assert clan.herbs["juniper"] == 3
    clan.herbs = {}
    HandleShortEvents().handle_herb_supply({"type": "all_herb", "adjust": "reduce_full", "trigger": ["always"]})
    assert not clan.herbs


def test_patrol_herbs_enter_fresh_collection_and_keep_old_stock(herbalists):
    clan, med, patient = herbalists
    clan.herbs = {"storage": {"catmint": [0, 5]}}
    patrol = Patrol()
    patrol.add_patrol_cats([med, patient], clan)
    with patch("scripts.events_module.patrol.patrol_outcome.choices", return_value=[2]):
        text = PatrolOutcome(herbs=["catmint"])._handle_herbs(patrol)
    assert clan.herbs["catmint"] == 9 and clan.herbs.storage["catmint"] == [0, 5]
    assert clan.herbs.collected["catmint"] == 4
    assert "catmint" in text and "4" in text


def test_real_herb_save_load_retains_ages_and_migrates_old_file_without_writing_on_load(herbalists, monkeypatch, tmp_path):
    clan, _, _ = herbalists
    monkeypatch.setattr("scripts.clan.get_save_dir", lambda: str(tmp_path))
    folder = tmp_path / clan.name
    folder.mkdir()
    path = folder / "herbs.json"
    old = {"moss": 7, "merged_herb": 4}
    path.write_text(json.dumps(old), encoding="utf-8")
    clan.load_herbs(clan)
    assert clan.herbs == old and json.loads(path.read_text(encoding="utf-8")) == old
    clan.herbs.begin_moon([])
    clan.herbs["moss"] += 3
    expected = clan.herbs.to_dict()
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    clan.save_herbs(clan)
    clan.herbs = {}
    clan.load_herbs(clan)
    assert clan.herbs.to_dict() == expected and clan.herbs["moss"] == 10
    other = Clan(name="OtherHerbs", camp_bg="camp1")
    (tmp_path / other.name).mkdir()
    (tmp_path / other.name / "herbs.json").write_text('{"moss": 2}', encoding="utf-8")
    clan.load_herbs(other)
    assert other.herbs == {"moss": 2} and clan.herbs["moss"] == 10


def test_stable_permanent_condition_does_not_consume_unneeded_herbs(herbalists):
    clan, _, patient = herbalists
    patient.get_permanent_condition("recurring shock")
    info = patient.permanent_condition["recurring shock"]
    info["mortality"] = 30
    for risk in info["risks"]:
        risk["chance"] = max(20, next(r["chance"] for r in PERMANENT["recurring shock"]["risks"] if r["name"] == risk["name"])) + 1
    clan.herbs = {"thyme": 5}
    before = deepcopy(info)
    Condition_Events.use_herbs(patient, "recurring shock", patient.permanent_condition.copy(), PERMANENT)
    assert info == before and clan.herbs == {"thyme": 5}


def test_risk_treatment_keeps_disabled_risks_disabled(herbalists):
    clan, _, patient = herbalists
    patient.get_permanent_condition("recurring shock")
    info = patient.permanent_condition["recurring shock"]
    info["risks"][0]["chance"] = 0
    clan.herbs = {"thyme": 5}
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="risks"):
        Condition_Events.use_herbs(patient, "recurring shock", patient.permanent_condition.copy(), PERMANENT)
    assert info["risks"][0]["chance"] == 0


@pytest.mark.parametrize("roll,expected_types", [(0, 1), (.99, 0)])
def test_fractional_focus_limit_can_succeed_or_fail_without_losing_stock(herbalists, roll, expected_types):
    clan, med, _ = herbalists
    clan.herbs = {"moss": 7}
    with patch("scripts.clan_resources.herbs.random", return_value=roll), patch(
            "scripts.clan_resources.herbs.randint", return_value=1):
        found = clan.herbs.gather(med, clan, max_types=.5)
    assert len(found) == expected_types and clan.herbs["moss"] >= 7


@pytest.mark.parametrize("state", ["dead", "outside", "exiled", "shunned", "not_member", "sick"])
def test_unavailable_medic_cannot_supply_colony_herbs(herbalists, state):
    clan, med, _ = herbalists
    clan.herbs = {}
    if state == "not_member":
        clan.clan_cats.remove(med.ID)
    elif state == "sick":
        med.get_ill("whitecough")
    else:
        setattr(med, state, True)
    Events().herb_gather()
    assert not clan.herbs


def test_actual_treatment_uses_old_stock_before_fresh_harvest(herbalists):
    clan, _, patient = herbalists
    patient.get_permanent_condition("recurring shock")
    clan.herbs = {"storage": {"thyme": [0, 3]}, "collected": {"thyme": 5}}
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="risks"):
        Condition_Events.use_herbs(patient, "recurring shock", patient.permanent_condition.copy(), PERMANENT)
    assert clan.herbs.storage["thyme"] == [0, 2] and clan.herbs.collected["thyme"] == 5


def test_specific_patrol_reward_can_include_herbs_unavailable_to_random_gathering(herbalists, monkeypatch):
    clan, med, patient = herbalists
    clan.herbs = {}
    monkeypatch.setattr("scripts.clan_resources.herbs.HERB_INFO", {})
    patrol = Patrol()
    patrol.add_patrol_cats([med, patient], clan)
    with patch("scripts.events_module.patrol.patrol_outcome.choices", return_value=[2]):
        text = PatrolOutcome(herbs=["random_herbs", "catmint"])._handle_herbs(patrol)
    assert clan.herbs == {"catmint": 4} and "catmint" in text


@pytest.mark.parametrize("mode,cards", [("classic", None), ("expanded", None),
                                       ("cruel season", []), ("cruel season", ["barren_stocks"]),
                                       ("cruel season", ["burnout", "plague_ridden", "longer_illnesses"]),
                                       ("cruel season", ["mouths_to_feed", "clumsy_paws", "survival_of_fittest"]),
                                       ("cruel season", ["underpopulated", "clumsy_paws", "survival_of_fittest"]),
                                       ("cruel season", ["weak_stars"]), ("cruel season", ["forsaken"]),
                                       ("cruel season", ["crowfood", "lean_meat"]),
                                       ("cruel season", ["crowfood", "barren_stocks"]),
                                       ("cruel season", ["for_the_throne", "heartless", "weak_stars"])])
def test_disposable_creation_full_moons_and_reload_preserve_herb_batches(herbalists, monkeypatch, tmp_path, mode, cards):
    from scripts.game_structure.load_cat import load_cats

    clan, med, player = herbalists
    clan.game_mode = mode
    clan.cruel_cards = cards
    clan.leader = player
    clan.starting_members = [med, player]
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
        with patch("scripts.clan_resources.herbs.randint", side_effect=lambda lower, upper: lower):
            clan.create_clan()
        assert bool(clan.herbs) == ("barren_stocks" not in (cards or []))
        first_save = json.loads((tmp_path / clan.name / "herbs.json").read_text(encoding="utf-8"))
        assert HerbSupply(first_save) == clan.herbs
        patients = []
        for severity in ("minor", "severe"):
            patient = Cat(status="warrior", moons=40)
            patient.history = History()
            clan.add_cat(patient)
            patient.create_inheritance_new_cat()
            patient.get_ill("tick fever", severity=severity)
            patient.illnesses["tick fever"].update(mortality=20, duration=6)
            patients.append(patient)
        clan.herbs = {"storage": {"ragwort": [0, 0, 0, 7], "catmint": [5]},
                      "collected": {"ragwort": 3, "goldenrod": 1}}
        clan.clan_settings["autosave"] = False
        events = Events()
        original_order = list(Cat.all_cats)
        visited = []
        process_cat = events.one_moon_cat
        def visit(cat):
            if not visited:
                assert patients[0].illnesses["tick fever"]["mortality"] == (24 if mode == "classic" else 19)
                assert patients[1].illnesses["tick fever"]["mortality"] == (24 if mode == "classic" else 30)
                assert clan.herbs.get("goldenrod", 0) == (1 if mode == "classic" else 0)
            visited.append(cat.ID)
            process_cat(cat)
        choose = random.choice
        def choose_effect(values):
            return "mortality" if "mortality" in values else choose(values)
        with patch("scripts.events_module.short.condition_events.random.choice", side_effect=choose_effect), patch(
                "scripts.cat.cats.random", return_value=.99):
            with patch.object(events, "one_moon_cat", side_effect=visit):
                events.one_moon()
            assert [cat_id for cat_id in visited if cat_id in original_order] == original_order
            assert any("Expired herbs" in line and "ragwort" in line for line in game.herb_events_list)
            events.one_moon()
        game.save_cats()
        clan.save_clan()
        expected = clan.herbs.to_dict()
        health = {cat.ID: deepcopy((cat.illnesses, cat.injuries, cat.permanent_condition)) for cat in patients}
        progression = {cat.ID: (cat.experience, deepcopy(cat.skills.get_skill_dict())) for cat in patients}
        prey = deepcopy(clan.freshkill_pile.pile) if mode != "classic" else None
        Cat.all_cats.clear()
        Cat.all_cats_list.clear()
        Inheritance.all_inheritances.clear()
        load_cats()
        Clan().load_clan()
        assert game.clan.herbs.to_dict() == expected
        if prey is not None:
            assert game.clan.freshkill_pile.pile == prey
        else:
            assert game.clan.freshkill_pile is None
        for cat_id, conditions in health.items():
            cat = Cat.all_cats[cat_id]
            assert (cat.illnesses, cat.injuries, cat.permanent_condition) == conditions
            assert (cat.experience, cat.skills.get_skill_dict()) == progression[cat_id]
        assert all(len(batches) <= HERB_INFO[herb]["expiration"] for herb, batches in game.clan.herbs.storage.items())


@pytest.mark.parametrize("amount, rating", [(0, "empty"), (1, "low"), (2, "low"),
                                           (3, "adequate"), (6, "adequate"),
                                           (7, "full"), (12, "full"), (13, "excess")])
def test_supply_rating_uses_source_thresholds_and_missing_varieties(herbalists, amount, rating):
    clan, med, patient = herbalists
    for _ in range(4):
        clan.add_cat(Cat(status="warrior", moons=30))
    # Six members require six of each herb; absent varieties contribute zero.
    clan.herbs = {"catmint": amount * 2}
    assert clan.herbs.get_overall_rating(clan) == rating


def test_supply_rating_counts_only_living_present_members(herbalists):
    clan, med, patient = herbalists
    clan.herbs = {herb: 3 for herb in HERB_INFO}
    assert clan.herbs.get_overall_rating(clan) == "full"
    for flag in ("dead", "outside", "exiled"):
        cat = Cat(status="warrior", moons=30)
        setattr(cat, flag, True)
        clan.add_cat(cat)
    Cat(status="warrior", moons=30)
    clan.clan_cats.append("missing cat")
    assert clan.herbs.get_overall_rating(clan) == "full"


def test_merged_herbs_and_zero_quantity_keys_have_valid_supply_ratings(herbalists):
    clan, med, patient = herbalists
    clan.herbs = {"catmint": 0, "merged_herb": 0}
    assert clan.herbs.get_overall_rating(clan) == "empty"
    clan.herbs["merged_herb"] = 20
    assert clan.herbs.get_overall_rating(clan) == "excess"


def test_all_source_supply_messages_render_without_unresolved_cat_tokens(herbalists):
    from scripts.clan_resources.herbs import HERB_MESSAGES

    clan, med, patient = herbalists
    clan.leader = patient
    clan.deputy = med
    for rating, messages in HERB_MESSAGES.items():
        with patch.object(clan.herbs, "get_overall_rating", return_value=rating):
            for message in messages:
                with patch("scripts.clan_resources.herbs.choice", return_value=message):
                    rendered = clan.herbs.get_status_message(clan, med)
                assert not any(token in rendered for token in ("m_c", "lead_name", "dep_name", "c_n", "{PRONOUN", "{VERB"))


@pytest.mark.parametrize("unavailable", ["missing", "dead", "outside", "exiled", "nonmember"])
def test_supply_messages_do_not_reference_unavailable_office_holders(herbalists, unavailable):
    from scripts.clan_resources.herbs import HERB_MESSAGES

    clan, med, patient = herbalists
    clan.leader = patient
    clan.deputy = patient
    if unavailable == "missing":
        clan.leader = clan.deputy = None
    elif unavailable == "nonmember":
        clan.clan_cats.remove(patient.ID)
    else:
        setattr(patient, unavailable, True)
    for rating, messages in HERB_MESSAGES.items():
        original = messages.copy()
        with patch.object(clan.herbs, "get_overall_rating", return_value=rating):
            with patch("scripts.clan_resources.herbs.choice", side_effect=lambda candidates: candidates[0]) as choose:
                clan.herbs.get_status_message(clan, med)
                available = choose.call_args.args[0]
                assert available
                assert all("lead_name" not in s and "dep_name" not in s for s in available)
                clan.herbs.get_status_message(clan)
                assert all("m_c" not in s for s in choose.call_args.args[0])
            assert HERB_MESSAGES[rating] == original


@pytest.mark.parametrize("mode", ["expanded", "cruel season"])
def test_scarce_herbs_go_to_severe_patients_before_earlier_minor_patients(herbalists, mode):
    clan, med, minor = herbalists
    clan.game_mode = mode
    major = Cat(prefix="Major", status="warrior", moons=40)
    severe = Cat(prefix="Severe", status="warrior", moons=40)
    for cat, severity in ((minor, "minor"), (major, "major"), (severe, "severe")):
        cat.history = History()
        clan.add_cat(cat)
        cat.get_ill("tick fever", severity=severity)
        cat.illnesses["tick fever"]["mortality"] = 20
    clan.herbs = {"goldenrod": 1}
    original_order = list(Cat.all_cats)
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="mortality"):
        Condition_Events.handle_herbs(clan)
    assert severe.illnesses["tick fever"]["mortality"] == 30
    assert major.illnesses["tick fever"]["mortality"] == 19
    assert minor.illnesses["tick fever"]["mortality"] == 19
    assert len(game.herb_events_list) == 1 and str(severe.name) in game.herb_events_list[0]
    assert not clan.herbs and list(Cat.all_cats) == original_order


def test_treatment_priority_uses_highest_revealed_severity_and_keeps_ties_stable(herbalists):
    clan, med, minor = herbalists
    major = Cat(status="warrior", moons=40, gender="female")
    severe = Cat(status="warrior", moons=40, gender="female")
    tied = Cat(status="warrior", moons=40, gender="female")
    for cat in (major, severe, tied):
        cat.history = History()
        clan.add_cat(cat)
    minor.get_injured("sore throat", severity="minor")
    minor.get_permanent_condition("recurring shock", born_with=True)
    minor.permanent_condition["recurring shock"].update(severity="severe", moons_until=5)
    major.get_ill("tick fever", severity="major")
    severe.get_injured("sore throat", severity="minor")
    severe.get_permanent_condition("recurring shock")
    severe.permanent_condition["recurring shock"]["severity"] = "severe"
    tied.get_ill("tick fever", severity="severe")
    with patch.object(Condition_Events, "use_herbs") as treat:
        Condition_Events.handle_herbs(clan)
    assert [(call.args[0], call.args[1]) for call in treat.call_args_list] == [
        (severe, "sore throat"), (severe, "recurring shock"), (tied, "tick fever"),
        (major, "tick fever"), (minor, "sore throat")]


@pytest.mark.parametrize("state", ["no_medic", "dead", "outside", "exiled", "shunned", "sick", "not_member"])
def test_no_working_medic_means_no_colony_treatment(herbalists, state):
    clan, med, patient = herbalists
    patient.get_ill("tick fever")
    patient.illnesses["tick fever"]["mortality"] = 20
    clan.herbs = {"goldenrod": 3}
    before = deepcopy(patient.illnesses)
    if state == "no_medic":
        med.status = "warrior"
    elif state == "not_member":
        clan.clan_cats.remove(med.ID)
    elif state == "sick":
        med.get_ill("whitecough")
    else:
        setattr(med, state, True)
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="mortality"):
        Condition_Events.handle_herbs(clan)
    assert patient.illnesses == before
    assert clan.herbs["goldenrod"] == 3


@pytest.mark.parametrize("rank", ["medicine cat", "medicine cat apprentice"])
def test_sick_medic_can_treat_self_but_not_other_patients(herbalists, rank):
    clan, med, patient = herbalists
    med.status = rank
    # A non-medic appears first; it must not stop the later medic's self-care.
    clan.clan_cats[:] = [patient.ID, med.ID]
    for cat in (patient, med):
        cat.get_ill("tick fever")
        cat.illnesses["tick fever"]["mortality"] = 20
    clan.herbs = {"goldenrod": 3}
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="mortality"):
        Condition_Events.handle_herbs(clan)
    assert med.illnesses["tick fever"]["mortality"] == 30
    assert patient.illnesses["tick fever"]["mortality"] == 20
    assert clan.herbs["goldenrod"] == 2


@pytest.mark.parametrize("rank", ["medicine cat", "medicine cat apprentice"])
def test_working_apprentices_and_mildly_ill_medics_can_treat_patients(herbalists, rank):
    clan, med, patient = herbalists
    med.status = rank
    med.get_ill("running nose", severity="minor")
    patient.get_ill("tick fever")
    patient.illnesses["tick fever"]["mortality"] = 20
    clan.herbs = {"goldenrod": 3}
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="mortality"):
        Condition_Events.handle_herbs(clan)
    assert patient.illnesses["tick fever"]["mortality"] == 30


@pytest.mark.parametrize("state", ["dead", "outside", "exiled", "not_member"])
def test_unavailable_patients_do_not_use_colony_herbs(herbalists, state):
    clan, med, patient = herbalists
    patient.get_ill("tick fever")
    before = deepcopy(patient.illnesses)
    clan.herbs = {"goldenrod": 3}
    if state == "not_member":
        clan.clan_cats.remove(patient.ID)
    else:
        setattr(patient, state, True)
    Condition_Events.handle_herbs(clan)
    assert patient.illnesses == before and clan.herbs["goldenrod"] == 3


def test_classic_treatment_stays_available_without_a_medic_or_stock(herbalists):
    clan, med, patient = herbalists
    clan.game_mode = "classic"
    med.status = "warrior"
    patient.get_ill("tick fever")
    patient.illnesses["tick fever"]["mortality"] = 20
    clan.herbs = {}
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="mortality"):
        Condition_Events.handle_herbs(clan)
    assert patient.illnesses["tick fever"]["mortality"] == 24
    assert not clan.herbs


def test_health_handlers_do_not_repeat_monthly_herb_treatment(herbalists):
    clan, med, patient = herbalists
    patient.get_ill("tick fever")
    patient.get_injured("sore throat")
    patient.get_permanent_condition("recurring shock")
    for conditions in (patient.illnesses, patient.injuries, patient.permanent_condition):
        for info in conditions.values():
            info["mortality"] = 20
    clan.herbs = {"goldenrod": 3, "juniper": 3, "thyme": 3}
    def choose(values):
        return "mortality" if "mortality" in values else values[0]
    with patch("scripts.events_module.short.condition_events.random.choice", side_effect=choose), patch(
            "scripts.events_module.short.condition_events.random.random", return_value=.99), patch(
            "scripts.cat.cats.random", return_value=.99):
        Condition_Events.handle_herbs(clan)
        stock = clan.herbs.to_dict()
        logs = game.herb_events_list.copy()
        Condition_Events.handle_illnesses(patient, "Newleaf")
        Condition_Events.handle_injuries(patient)
        Condition_Events.handle_already_disabled(patient)
    assert len(logs) == 3
    assert clan.herbs.to_dict() == stock and game.herb_events_list == logs


def test_unknown_saved_condition_does_not_block_other_treatments(herbalists, capsys):
    clan, med, patient = herbalists
    patient.illnesses["removed condition"] = {"severity": "minor"}
    patient.get_ill("tick fever")
    clan.herbs = {"goldenrod": 3}
    Condition_Events.handle_herbs(clan)
    assert "removed condition" in capsys.readouterr().out
    assert clan.herbs["goldenrod"] == 2
