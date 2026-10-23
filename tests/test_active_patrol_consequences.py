import json
from pathlib import Path

from unittest.mock import patch

import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.events_module.patrol.patrol import Patrol
from scripts.events_module.patrol.patrol_event import PatrolEvent
from scripts.events_module.patrol.patrol_outcome import PatrolOutcome
from scripts.game_structure.game_essentials import game
from tests.test_patrol_feedback import patrol_feedback
from tests.test_stolen_vitality import revival, member
from tests.test_murder_modernization import crime


def test_screen_patrol_resolves_the_tested_outcome_class():
    import scripts.screens.PatrolScreen as screen

    assert screen.Patrol is Patrol
    assert PatrolEvent.__module__ == "scripts.events_module.patrol.patrol_event"
    assert PatrolOutcome.__module__ == "scripts.events_module.patrol.patrol_outcome"
    from scripts.events_module.patrol import patrol_event

    assert patrol_event.PatrolOutcome is PatrolOutcome


@pytest.mark.parametrize("hidden", [False, True])
def test_multiple_condition_blocks_keep_all_visible_results(patrol_feedback, hidden):
    patrol, clan, cats, outcome = patrol_feedback
    first, second = patrol.patrol_leader, patrol.random_cat
    outcome.injury = [
        {"cats": ["p_l"], "injuries": ["bruises"]},
        {"cats": ["r_c"], "injuries": ["whitecough"], "no_results": hidden},
    ]
    text, result, art = outcome.execute_outcome(patrol)
    assert "bruises" in first.injuries
    assert "whitecough" in second.illnesses
    assert f"{first.name} got: bruises." in result
    assert (f"{second.name} got: whitecough." in result) is not hidden
    assert first.history.condition_events[-1]["cause"] == text
    assert second.history.condition_events[-1]["cause"] == text


def test_rejected_condition_does_not_report_empty_infection_or_history(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    cat = patrol.patrol_leader
    outcome.injury = [{"cats": ["p_l"], "injuries": ["kittencough"]}]
    before = History.make_dict(cat)
    result = outcome._handle_condition_and_scars(patrol)
    assert result == ""
    assert not cat.is_ill()
    assert History.make_dict(cat) == before


@pytest.mark.parametrize(
    "tags,lives,expected",
    [([], 9, 1), (["some_lives"], 9, 3), (["all_lives"], 9, 8), ([], 1, 0)],
)
def test_active_patrol_charges_stolen_vitality_after_original_deaths(
    revival, tags, lives, expected
):
    clan, leader, cats = revival
    cats += [member(clan) for _ in range(8)]
    clan.leader_lives = lives
    patrol = Patrol()
    patrol.add_patrol_cats([leader, cats[0]], clan)
    patrol.patrol_leader = leader
    outcome = PatrolOutcome(dead_cats=["p_l"] + tags)
    with patch(
        "scripts.events_module.patrol.patrol_outcome.random.randint", return_value=3
    ):
        result = outcome._handle_death(patrol)
    assert sum(cat.dead for cat in cats) == expected
    assert ("revival" in result) is bool(expected)
    assert leader.dead is (bool(tags and tags[0] == "all_lives") or lives == 1)
    assert len(leader.history.died_by) == 1


def test_no_neighbor_death_history_does_not_require_a_neighbor(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    patrol.other_clan = None
    outcome.dead_cats = ["p_l"]
    result = outcome._handle_death(patrol)
    assert patrol.patrol_leader.dead
    assert "died" in result
    assert len(patrol.patrol_leader.history.died_by) == 1


@pytest.mark.parametrize("hidden", [False, True])
def test_rejected_hidden_condition_has_no_potential_history(patrol_feedback, hidden):
    patrol, clan, cats, outcome = patrol_feedback
    cat = patrol.patrol_leader
    before = History.make_dict(cat)
    outcome.injury = [
        {"cats": ["p_l"], "injuries": ["kittencough"], "no_results": hidden}
    ]
    assert outcome._handle_condition_and_scars(patrol) == ""
    assert History.make_dict(cat) == before


def test_dead_patrol_member_does_not_receive_new_conditions(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    cat = patrol.patrol_leader
    cat.dead = True
    outcome.injury = [{"cats": ["p_l"], "injuries": ["bruises"]}]
    assert outcome._handle_condition_and_scars(patrol) == ""
    assert not cat.injuries and not cat.history.condition_events


def test_existing_condition_is_removed_from_the_choice_pool(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    cat = patrol.patrol_leader
    cat.get_injured("bruises")
    outcome.injury = [{"cats": ["p_l"], "injuries": ["bruises", "whitecough"]}]
    with patch(
        "scripts.events_module.patrol.patrol_outcome.choice",
        side_effect=lambda values: values[0],
    ) as choose:
        result = outcome._handle_condition_and_scars(patrol)
    choose.assert_called_once_with(["whitecough"])
    assert "whitecough" in cat.illnesses and "whitecough" in result


@pytest.mark.parametrize("path", ["proceed", "antag"])
def test_authored_multiple_condition_patrol_reaches_screen_results(
    patrol_feedback, path
):
    from scripts.screens.PatrolScreen import PatrolScreen

    patrol, clan, cats, outcome = patrol_feedback
    data = json.loads(
        Path("resources/dicts/patrols/beach/med/greenleaf.json").read_text(
            encoding="utf-8"
        )
    )
    record = next(
        item
        for item in data
        if item["patrol_id"] == "bch_med_greenleaf_tansy_storylorehealerlocked1"
    )
    event = patrol.generate_patrol_events([record])[0]
    outcome = next(item for item in event.fail_outcomes if len(item.injury) == 2)
    apprentice = patrol.random_cat
    apprentice.status = "medicine cat apprentice"
    apprentice.moons = 8
    patrol.patrol_apprentices = [apprentice]
    patrol.patrol_cat_dict["app1"] = apprentice
    patrol.patrol_event = event
    screen = PatrolScreen("patrol screen")
    screen.patrol_obj = patrol
    with patch.object(patrol, "calculate_success", return_value=(outcome, False)):
        screen.run_patrol_proceed(path)
    assert "stomachache" in apprentice.illnesses
    assert "diarrhea" in apprentice.illnesses
    assert f"{apprentice.name} got: stomachache." in screen.results_text
    assert f"{apprentice.name} got: diarrhea." in screen.results_text
    assert "app1" not in screen.display_text
