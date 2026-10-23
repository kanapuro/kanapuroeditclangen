from itertools import permutations
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.cat.cats import Cat
from scripts.cat.skills import Skill, SkillPath
from scripts.cat_relations.interaction import GroupInteraction
from scripts.events_module.relationship.group_events import GroupEvents
from scripts.game_structure.game_essentials import game
from tests.test_patrol_feedback import patrol_feedback


FIELDS = {
    "romantic": "romantic_love",
    "platonic": "platonic_like",
    "dislike": "dislike",
    "admiration": "admiration",
    "comfortable": "comfortable",
    "jealousy": "jealousy",
    "trust": "trust",
}


@pytest.mark.parametrize("metric", FIELDS)
@pytest.mark.parametrize(
    "direction,delta", [("increase", 8), ("decrease", -8), ("neutral", 0)]
)
def test_general_group_effects_change_only_the_requested_metric(
    patrol_feedback, metric, direction, delta
):
    patrol, clan, cats, outcome = patrol_feedback
    members = cats[:3]
    roles = dict(zip(("m_c", "r_c1", "r_c2"), (cat.ID for cat in members)))
    for first, second in permutations(members, 2):
        for field in FIELDS.values():
            setattr(first.relationships[second.ID], field, 40)
    interaction = GroupInteraction(
        "group_effect_test", general_reaction={metric: direction}
    )
    with patch.object(Cat, "is_potential_mate", return_value=True):
        GroupEvents.influence_general_relationship(8, roles, interaction)
    for first, second in permutations(members, 2):
        for key, field in FIELDS.items():
            assert getattr(first.relationships[second.ID], field) == 40 + (
                delta if key == metric else 0
            )
    assert all(cat.ID not in cat.relationships for cat in members)


def test_authored_group_talk_works_with_exactly_three_members(
    patrol_feedback, monkeypatch
):
    patrol, clan, cats, outcome = patrol_feedback
    members = cats[:3]
    record = next(
        item
        for item in GroupEvents.GROUP_INTERACTION_MASTER_DICT["3"]["neutral"]
        if item.id == "group_3_neutral_talk2"
    )
    monkeypatch.setattr(game, "cur_events_list", [])
    monkeypatch.setattr(
        GroupEvents, "GROUP_INTERACTION_MASTER_DICT", {"3": {"neutral": [record]}}
    )
    for first, second in permutations(members, 2):
        first.relationships[second.ID].dislike = 20

    def choose(values):
        if values == ["negative", "positive", "neutral"]:
            return "neutral"
        return values[0]

    with patch(
        "scripts.events_module.relationship.group_events.choice", side_effect=choose
    ):
        ids = GroupEvents.start_interaction(members[0], members[1:])
    assert set(ids) == {cat.ID for cat in members}
    assert len(game.cur_events_list) == 1
    event = game.cur_events_list[0]
    assert set(event.cats_involved) == set(ids)
    assert all(role not in event.text for role in ("m_c", "r_c1", "r_c2"))
    for first, second in permutations(members, 2):
        rel = first.relationships[second.ID]
        assert rel.comfortable == 8 and rel.platonic_like == 8 and rel.dislike == 12


def test_unmet_relationship_constraint_still_fails_after_relationship_creation(
    patrol_feedback,
):
    patrol, clan, cats, outcome = patrol_feedback
    first, second = cats[:2]
    first.relationships.clear()
    second.relationships.clear()
    interaction = GroupInteraction(
        "group_constraint_test",
        relationship_constraint={"m_c_to_r_c1": ["platonic_20"]},
    )
    roles = {"m_c": first.ID, "r_c1": second.ID}
    assert not GroupEvents.relationship_allow_interaction(interaction, roles)
    assert first.relationships[second.ID].platonic_like == 0


def test_group_skill_participants_use_the_current_skill_api(patrol_feedback):
    patrol, clan, cats, outcome = patrol_feedback
    cats[0].skills.primary = Skill(SkillPath.HEALER, 30)
    cats[0].skills.secondary = None
    cats[1].skills.primary = Skill(SkillPath.HUNTER, 30)
    cats[1].skills.secondary = None
    interaction = GroupInteraction(
        "group_skill_test", cat_amount=2, skill_constraint={"r_c1": ["HEALER,1"]}
    )
    options, counter = GroupEvents.get_abbreviations_possibilities(
        [interaction], 2, cats[:2]
    )
    assert options[interaction.id]["r_c1"] == [cats[0].ID]


SOURCE_GROUPS = [
    ("positive", "group_{size}_pos_medteachingapps", "medicine cat", "apprentice"),
    (
        "negative",
        "group_{size}_negative_seniordisrespected_apprentices",
        "warrior",
        "medicine cat apprentice",
    ),
    ("negative", "muddypaws_{size}_app", "apprentice", "mediator apprentice"),
]


@pytest.mark.parametrize("size", [3, 4, 5])
@pytest.mark.parametrize("kind,template,main_status,other_status", SOURCE_GROUPS)
def test_source_apprentice_groups_run_with_exact_roles_and_directed_effects(
    patrol_feedback,
    monkeypatch,
    tmp_path,
    size,
    kind,
    template,
    main_status,
    other_status,
):
    patrol, clan, cats, outcome = patrol_feedback
    members = cats[:size]
    members[0].status = main_status
    members[0].moons = (
        96 if "senior" in template else 8 if main_status == "apprentice" else 40
    )
    for cat in members[1:]:
        cat.status = other_status
        cat.moons = 8
    for first, second in permutations(members, 2):
        first.relationships[second.ID].admiration = 20
    record = next(
        item
        for item in GroupEvents.GROUP_INTERACTION_MASTER_DICT[str(size)][kind]
        if item.id == template.format(size=size)
    )
    monkeypatch.setattr(
        GroupEvents, "GROUP_INTERACTION_MASTER_DICT", {str(size): {kind: [record]}}
    )
    monkeypatch.setattr(game, "cur_events_list", [])

    def choose(values):
        return kind if values == ["negative", "positive", "neutral"] else values[0]

    with patch(
        "scripts.events_module.relationship.group_events.choice", side_effect=choose
    ):
        ids = GroupEvents.start_interaction(members[0], members[1:])
    assert set(ids) == {cat.ID for cat in members}
    assert len(game.cur_events_list) == 1
    event = game.cur_events_list[0]
    assert set(event.cats_involved) == set(ids)
    assert all(
        role not in event.text
        for role in ["m_c", "multi_cat"] + ["r_c" + str(i) for i in range(1, size)]
    )
    roles = dict(zip(["m_c"] + ["r_c" + str(i) for i in range(1, size)], ids))
    for text in record.interactions:
        prepared = GroupEvents.prepare_text(text, roles)
        assert all(tag not in prepared for tag in roles)
        assert "{PRONOUN/" not in prepared and "{VERB/" not in prepared
    for cat in members[1:]:
        to_student = members[0].relationships[cat.ID]
        to_teacher = cat.relationships[members[0].ID]
        if kind == "positive":
            assert to_student.admiration == 30 and to_teacher.admiration == 30
            assert to_student.dislike == to_teacher.dislike == 0
        elif "senior" in template:
            assert to_student.admiration == 10 and to_teacher.admiration == 15
            assert to_student.dislike == 10 and to_teacher.dislike == 0
        else:
            assert to_student.admiration == 20 and to_teacher.admiration == 10
            assert to_student.dislike == 0 and to_teacher.dislike == 10
    for first, second in permutations(members[1:], 2):
        assert first.relationships[second.ID].admiration == 20
        assert first.relationships[second.ID].dislike == 0

    monkeypatch.setattr("scripts.cat.cats.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setitem(game.switches, "clan_name", clan.name)

    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)

    monkeypatch.setattr(game, "safe_save", save)
    for cat in members:
        expected = {
            other.ID: {
                field: getattr(cat.relationships[other.ID], field)
                for field in FIELDS.values()
            }
            for other in members
            if other != cat
        }
        cat.save_relationship_of_cat(str(tmp_path / clan.name / "relationships"))
        cat.relationships.clear()
        cat.load_relationship_of_cat()
        for other_id, values in expected.items():
            assert {
                field: getattr(cat.relationships[other_id], field)
                for field in FIELDS.values()
            } == values


@pytest.mark.parametrize(
    "moons,expected",
    [
        (0, False),
        (4, False),
        (8, False),
        (20, False),
        (50, False),
        (95, False),
        (96, True),
        (130, True),
    ],
)
def test_source_senior_lecturer_requires_the_correct_age(
    patrol_feedback, moons, expected
):
    patrol, clan, cats, outcome = patrol_feedback
    main = cats[0]
    main.moons = moons
    record = next(
        item
        for item in GroupEvents.GROUP_INTERACTION_MASTER_DICT["3"]["negative"]
        if item.id == "group_3_negative_seniordisrespected_apprentices"
    )
    assert (
        bool(
            GroupEvents.get_main_cat_interactions(
                [record], "forest", "Newleaf", {"m_c": main.ID}
            )
        )
        is expected
    )


@pytest.mark.parametrize(
    "constraint,target_age,expected", [(["adolescent"], 8, True), (["adult"], 8, False)]
)
def test_group_companion_age_constraints_apply_during_selection_and_final_check(
    patrol_feedback, constraint, target_age, expected
):
    patrol, clan, cats, outcome = patrol_feedback
    cats[1].moons = target_age
    record = GroupInteraction(
        "group_age_test", cat_amount=2, age_constraint={"r_c1": constraint}
    )
    options, counts = GroupEvents.get_abbreviations_possibilities(
        [record], 2, [cats[1]]
    )
    assert bool(options[record.id]["r_c1"]) is expected
    assert (
        GroupEvents.cat_allow_interaction(
            record, {"m_c": cats[0].ID, "r_c1": cats[1].ID}
        )
        is expected
    )


def test_monthly_relationship_entry_point_reaches_source_teaching_group(
    patrol_feedback, monkeypatch
):
    from scripts.events_module.relationship.relation_events import Relation_Events

    patrol, clan, cats, outcome = patrol_feedback
    main = cats[0]
    main.status = "medicine cat"
    for cat in cats[1:3]:
        cat.status = "apprentice"
        cat.moons = 8
    record = next(
        item
        for item in GroupEvents.GROUP_INTERACTION_MASTER_DICT["3"]["positive"]
        if item.id == "group_3_pos_medteachingapps"
    )
    monkeypatch.setattr(
        GroupEvents, "GROUP_INTERACTION_MASTER_DICT", {"3": {"positive": [record]}}
    )
    monkeypatch.setattr(Relation_Events, "cats_triggered_events", {})
    monkeypatch.setattr(game, "cur_events_list", [])

    def choose(values):
        return (
            "positive" if values == ["negative", "positive", "neutral"] else values[0]
        )

    with patch(
        "scripts.events_module.relationship.relation_events.randint", return_value=0
    ), patch(
        "scripts.events_module.relationship.group_events.choice", side_effect=choose
    ):
        Relation_Events.group_events(main)
    assert len(game.cur_events_list) == 1
    assert set(game.cur_events_list[0].cats_involved) == {cat.ID for cat in cats[:3]}
    assert Relation_Events.cats_triggered_events == {cat.ID: 1 for cat in cats[:3]}
    assert main.relationships[cats[1].ID].admiration == 10
    assert cats[1].relationships[main.ID].admiration == 10
