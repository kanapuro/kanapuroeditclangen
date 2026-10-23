from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.cat.cats import Cat
from scripts.cat.skills import Skill, SkillPath
from scripts.cat.thoughts import Thoughts
from scripts.game_structure.game_essentials import game
from tests.test_condition_modernization import clinic


def allowed(main, other, thought):
    return Thoughts.cats_fulfill_thought_constraints(
        main, other, thought, "expanded", "Forest", "Newleaf", "camp1"
    )


@pytest.mark.parametrize("tag", ["mentor/app", "app/mentor"])
def test_mentor_thought_uses_saved_cat_ids(clinic, tag):
    clan, mentor, apprentice = clinic
    apprentice.status = "apprentice"
    apprentice.moons = 8
    apprentice.update_mentor(mentor.ID)
    main, other = (mentor, apprentice) if tag == "mentor/app" else (apprentice, mentor)
    assert allowed(
        main,
        other,
        {"thoughts": ["Is thinking of r_c"], "relationship_constraint": [tag]},
    )
    stranger = Cat(status="warrior", moons=40)
    assert not allowed(
        main,
        stranger,
        {"thoughts": ["Is thinking of r_c"], "relationship_constraint": [tag]},
    )


def test_camp_skill_thought_reaches_actual_choice_without_error_fallback(clinic):
    clan, main, other = clinic
    main.dead = True
    main.skills.primary = Skill(SkillPath.CAMP, 30)
    other.skills.primary = Skill(SkillPath.CAMP, 30)
    main.skills.secondary = other.skills.secondary = None
    thoughts = Thoughts.load_thoughts(
        main, other, "expanded", "Forest", "Newleaf", "camp1"
    )
    record = next(t for t in thoughts if t["id"] == "skill_camp_h1")
    with patch(
        "scripts.cat.thoughts.choice",
        side_effect=lambda values: record if record in values else values[0],
    ):
        assert (
            Thoughts.get_chosen_thought(
                main, other, "expanded", "Forest", "Newleaf", "camp1"
            )
            in record["thoughts"]
        )
    other.skills.primary = Skill(SkillPath.HUNTER, 30)
    assert record not in Thoughts.load_thoughts(
        main, other, "expanded", "Forest", "Newleaf", "camp1"
    )


@pytest.mark.parametrize(
    "constraint,value",
    [
        ("random_status_constraint", ["warrior"]),
        ("random_age_constraint", ["adult"]),
        ("random_trait_constraint", ["bold"]),
        ("random_skill_constraint", ["CAMP,1"]),
        ("random_backstory_constraint", ["clanborn"]),
        ("random_faith_constraint", ["low_sc"]),
        ("random_cluster_constraint", ["sweet"]),
        ("random_living_status", ["living"]),
        ("random_outside_status", ["clancat"]),
        ("relationship_constraint", ["siblings"]),
    ],
)
def test_subject_constraints_require_an_actual_subject(clinic, constraint, value):
    clan, main, other = clinic
    assert not allowed(
        main, None, {"thoughts": ["Is thinking quietly"], constraint: value}
    )
    assert allowed(main, None, {"thoughts": ["Is thinking quietly"]})


@pytest.mark.parametrize("role", ["main", "random"])
@pytest.mark.parametrize(
    "clusters,expected",
    [
        (("stable", ""), False),
        (("sweet", ""), True),
        (("stable", "sweet"), True),
        (("stable", "unlawful"), False),
    ],
)
def test_personality_cluster_checks_both_present_clusters(
    clinic, role, clusters, expected
):
    clan, main, other = clinic
    with patch("scripts.cat.thoughts.get_cluster", return_value=clusters):
        assert (
            allowed(
                main,
                other,
                {
                    "thoughts": ["Is thinking quietly"],
                    role + "_cluster_constraint": ["sweet"],
                },
            )
            is expected
        )


@pytest.mark.parametrize(
    "dead,outside,df,destination",
    [
        (False, False, False, "living"),
        (False, True, False, "living"),
        (True, False, False, "starclan"),
        (True, False, True, "darkforest"),
        (True, True, False, "unknownresidence"),
        (True, True, True, "darkforest"),
    ],
)
def test_explicit_destination_constraints_keep_three_afterlives_distinct(
    clinic, dead, outside, df, destination
):
    clan, main, other = clinic
    other.dead, other.outside, other.df = dead, outside, df
    for status in ("living", "starclan", "darkforest", "unknownresidence"):
        thought = {
            "thoughts": ["Is thinking quietly"],
            "random_living_status": [status],
            "random_outside_status": ["clancat", "outside", "lost"],
        }
        assert allowed(main, other, thought) is (status == destination)


@pytest.mark.parametrize("state", ["inside", "outside", "dead"])
def test_solitary_cats_have_no_self_companion_or_retry_loop(clinic, monkeypatch, state):
    clan, main, other = clinic
    monkeypatch.setattr(Cat, "all_cats", {main.ID: main})
    main.outside = state == "outside"
    main.dead = state == "dead"
    main.relationships.clear()
    with patch(
        "scripts.cat.cats.choice", wraps=lambda values: values[0]
    ) as select, patch(
        "scripts.cat.cats.Thoughts.get_chosen_thought",
        return_value="Is resting quietly",
    ) as thought:
        main.thoughts()
    assert thought.call_args.args[1] is None
    assert select.call_count == 0
    assert main.thought == "Is resting quietly"


def test_unborn_companion_does_not_block_a_known_living_cat(clinic, monkeypatch):
    clan, main, other = clinic
    unborn = Cat(status="newborn", moons=0)
    unborn.moons = -1
    main.create_one_relationship(other)
    main.create_one_relationship(unborn)
    monkeypatch.setattr(
        Cat, "all_cats", {unborn.ID: unborn, main.ID: main, other.ID: other}
    )
    with patch(
        "scripts.cat.cats.choice", side_effect=lambda values: values[0]
    ) as select, patch(
        "scripts.cat.cats.Thoughts.get_chosen_thought",
        return_value="Is thinking about r_c",
    ) as thought:
        main.thoughts()
    assert thought.call_args.args[1] is other
    assert select.call_count == 1
    assert "r_c" not in main.thought


@pytest.mark.parametrize("state", ["inside", "outside", "dead"])
@pytest.mark.parametrize("other_dead", [False, True])
@pytest.mark.parametrize("known", [False, True])
@pytest.mark.parametrize("roll", [0, 1])
def test_companion_selection_retains_death_and_relationship_rules(
    clinic, state, other_dead, known, roll
):
    clan, main, other = clinic
    main.outside = state == "outside"
    main.dead = state == "dead"
    other.dead = other_dead
    main.relationships.clear()
    if known:
        main.create_one_relationship(other)
    with patch("scripts.cat.cats.getrandbits", return_value=roll), patch(
        "scripts.cat.cats.Thoughts.get_chosen_thought",
        return_value="Is resting quietly",
    ) as thought:
        main.thoughts()
    expected = state == "dead" or (
        known and (state == "outside" or not other_dead or roll == 1)
    )
    assert thought.call_args.args[1] is (other if expected else None)


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
@pytest.mark.parametrize("moons", [0, 4, 8, 20, 50, 95, 130])
def test_age_constraints_remain_enforced_for_both_participants(clinic, mode, moons):
    clan, main, other = clinic
    main.moons = other.moons = moons
    for key in ("main_age_constraint", "random_age_constraint"):
        for age in Cat.ages:
            thought = {"thoughts": ["Is thinking quietly"], key: [age]}
            assert Thoughts.cats_fulfill_thought_constraints(
                main, other, thought, mode, "Forest", "Newleaf", "camp1"
            ) is (main.age == age)


@pytest.mark.parametrize(
    "mode,cards",
    [
        ("classic", None),
        ("expanded", None),
        ("cruel season", None),
        ("cruel season", []),
    ],
)
@pytest.mark.parametrize("dead", [False, True])
def test_real_cat_reload_regenerates_skill_thought_and_retains_mentor_ids(
    clinic, monkeypatch, tmp_path, mode, cards, dead
):
    from scripts.cat_relations.inheritance import Inheritance
    from scripts.game_structure.load_cat import load_cats

    clan, main, other = clinic
    clan.game_mode, clan.cruel_cards = mode, cards
    main.skills.primary = Skill(SkillPath.CAMP, 30)
    other.skills.primary = Skill(SkillPath.CAMP, 30)
    main.skills.secondary = other.skills.secondary = None
    other.status = "apprentice"
    other.moons = 8
    other.update_mentor(main.ID)
    main.dead = dead
    main.create_one_relationship(other)
    other.create_one_relationship(main)
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    for module in (
        "scripts.cat.cats",
        "scripts.game_structure.game_essentials",
        "scripts.game_structure.load_cat",
    ):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setitem(game.switches, "clan_name", clan.name)
    monkeypatch.setitem(game.switches, "clan_list", [clan.name])
    monkeypatch.setitem(game.switches, "game_mode", mode)

    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)

    def choose(values):
        return next(
            (
                item
                for item in values
                if isinstance(item, dict) and item["id"] == "skill_camp_h1"
            ),
            values[0],
        )

    monkeypatch.setattr(game, "safe_save", save)
    main_id, other_id = main.ID, other.ID
    game.save_cats()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    with patch("scripts.cat.thoughts.choice", side_effect=choose):
        load_cats()
    loaded_main, loaded_other = Cat.fetch_cat(main_id), Cat.fetch_cat(other_id)
    assert loaded_other.mentor == main_id
    assert loaded_main.apprentice == [other_id]
    assert loaded_main.skills.meets_skill_requirement("CAMP", 1)
    assert loaded_other.skills.meets_skill_requirement("CAMP", 1)
    for cat in (loaded_main, loaded_other):
        assert cat.thought and "Prrrp!" not in cat.thought and "r_c" not in cat.thought
    if dead:
        assert loaded_main.thought.startswith("Gives ")
    else:
        assert Thoughts.thought_fulfill_rel_constraints(
            loaded_main, loaded_other, ["mentor/app"]
        )
