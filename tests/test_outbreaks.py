from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.cat.cats import Cat
from scripts.events import Events
from scripts.game_structure.game_essentials import game
from tests.test_cruel_season import colony


@pytest.fixture
def outbreak(colony, monkeypatch):
    monkeypatch.setattr(game, "cur_events_list", [])
    monkeypatch.setattr(
        game, "safe_save", Mock(side_effect=AssertionError("No real save writes"))
    )
    colony.current_season = "Leaf-bare"
    source = Cat(status="kitten", moons=3)
    colony.add_cat(source)
    source.get_ill("kittencough")
    for _ in range(10):
        colony.add_cat(Cat(status="warrior", moons=40))
    return colony, source, Events()


def spread(event, source):
    with patch("scripts.events.random.random", return_value=0), patch(
        "scripts.events.random.choices", return_value=[2]
    ), patch(
        "scripts.events.random.sample", side_effect=lambda cats, n: list(cats)[:n]
    ):
        event.handle_outbreaks(source)


def test_nursery_outbreak_only_announces_new_eligible_infections(outbreak):
    clan, source, event = outbreak
    sick = Cat(status="kitten", moons=2)
    newborn = Cat(status="newborn", moons=0)
    kittens = [Cat(status="kitten", moons=2) for _ in range(2)]
    for cat in [sick, newborn] + kittens:
        clan.add_cat(cat)
    sick.get_ill("whitecough")
    before = deepcopy(source.illnesses)
    spread(event, source)
    assert all("kittencough" in cat.illnesses for cat in kittens)
    assert "kittencough" not in sick.illnesses
    assert not newborn.is_ill()
    assert source.illnesses == before
    assert len(game.cur_events_list) == 1
    assert set(game.cur_events_list[0].cats_involved) == {cat.ID for cat in kittens}


@pytest.mark.parametrize("kits", [0, 1])
def test_small_nursery_does_not_stop_other_infectious_conditions(outbreak, kits):
    clan, source, event = outbreak
    for _ in range(kits):
        clan.add_cat(Cat(status="kitten", moons=2))
    source.get_ill("fleas")
    spread(event, source)
    assert len(game.cur_events_list) == 1
    infected = [
        Cat.all_cats[cat_id] for cat_id in game.cur_events_list[0].cats_involved
    ]
    assert len(infected) == 2
    assert all("fleas" in cat.illnesses for cat in infected)
    assert game.cur_events_list[0].text.startswith("Fleas")


@pytest.mark.parametrize("invalid", ["dead", "outside", "exiled", "unregistered"])
def test_invalid_source_cannot_start_outbreak(outbreak, invalid):
    clan, source, event = outbreak
    if invalid == "unregistered":
        clan.clan_cats.remove(source.ID)
    else:
        setattr(source, invalid, True)
    with patch("scripts.events.random.random") as roll:
        event.handle_outbreaks(source)
    roll.assert_not_called()
    assert not game.cur_events_list


@pytest.mark.parametrize("illness", ["whitecough", "kittencough"])
@pytest.mark.parametrize("invalid", ["dead", "outside", "exiled", "unregistered"])
def test_outbreak_never_infects_ineligible_registry_cats(
    outbreak, monkeypatch, illness, invalid
):
    clan, source, event = outbreak
    source.illnesses.clear()
    source.get_ill(illness)
    other = Cat(status="kitten", moons=2)
    if invalid != "unregistered":
        clan.add_cat(other)
        setattr(other, invalid, True)
    eligible = [Cat(status="kitten", moons=2) for _ in range(2)]
    for cat in eligible:
        clan.add_cat(cat)
    # Put the invalid cat first so sampling exposes an eligibility error.
    monkeypatch.setattr(Cat, "all_cats", {other.ID: other, **Cat.all_cats})
    spread(event, source)
    assert not other.is_ill()
    assert len(game.cur_events_list) == 1
    assert other.ID not in game.cur_events_list[0].cats_involved


@pytest.mark.parametrize("invalid", ["exiled", "unregistered"])
def test_other_registry_patients_do_not_suppress_colony_outbreak(outbreak, invalid):
    clan, source, event = outbreak
    source.illnesses.clear()
    source.get_ill("whitecough")
    for _ in range(20):
        cat = Cat(status="warrior", moons=40)
        cat.get_ill("whitecough")
        if invalid == "exiled":
            clan.add_cat(cat)
            cat.exiled = True
    spread(event, source)
    assert len(game.cur_events_list) == 1


@pytest.mark.parametrize("invalid", ["exiled", "unregistered"])
def test_unavailable_medic_cannot_prevent_outbreak(outbreak, invalid):
    clan, source, event = outbreak
    source.illnesses.clear()
    source.get_ill("whitecough")
    medic = Cat(status="medicine cat", moons=40)
    if invalid == "exiled":
        clan.add_cat(medic)
        medic.exiled = True
    rate = source.illnesses["whitecough"]["infectiousness"]
    with patch("scripts.events.random.random", return_value=1 / (rate + 1)), patch(
        "scripts.events.random.choices", return_value=[2]
    ):
        event.handle_outbreaks(source)
    assert len(game.cur_events_list) == 1


@pytest.mark.parametrize(
    "mode,cards",
    [
        ("expanded", None),
        ("cruel season", None),
        ("cruel season", []),
        ("cruel season", ["plague_ridden"]),
    ],
)
def test_actual_outbreak_conditions_and_histories_survive_reload(
    outbreak, monkeypatch, tmp_path, mode, cards
):
    clan, source, event = outbreak
    clan.game_mode, clan.cruel_cards = mode, cards
    source.illnesses.clear()
    source.get_ill("whitecough")
    spread(event, source)
    infected = [
        Cat.all_cats[cat_id] for cat_id in game.cur_events_list[0].cats_involved
    ]
    monkeypatch.setattr("scripts.cat.cats.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setitem(game.switches, "clan_name", clan.name)

    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)

    monkeypatch.setattr(game, "safe_save", save)
    for cat in infected:
        expected = deepcopy(cat.illnesses)
        assert expected["whitecough"]["event_triggered"]
        cat.save_condition()
        cat.save_history(str(tmp_path / clan.name / "history"))
        cat.illnesses.clear()
        cat.history = None
        cat.load_conditions()
        cat.load_history()
        assert cat.illnesses == expected
        assert cat.history.condition_events[-1]["condition"] == "whitecough"
    assert len(game.cur_events_list) == 1


@pytest.mark.parametrize("season", ["Newleaf", "Greenleaf", "Leaf-fall", "Leaf-bare"])
@pytest.mark.parametrize("illness", ["whitecough", "fleas"])
def test_season_rules_and_flea_exception_are_preserved(outbreak, season, illness):
    clan, source, event = outbreak
    clan.current_season = season
    source.illnesses.clear()
    source.get_ill(illness)
    spread(event, source)
    allowed = illness == "fleas" or season in game.get_config_value(
        "condition_related", "illness_outbreak_season"
    )
    assert len(game.cur_events_list) == int(allowed)


@pytest.mark.parametrize("prevent", [False, True])
def test_recovery_focus_still_prevents_outbreaks(outbreak, prevent):
    clan, source, event = outbreak
    source.illnesses.clear()
    source.get_ill("whitecough")
    clan.clan_settings["rest and recover"] = True
    prevention = game.config["focus"]["rest and recover"]["outbreak_prevention"]
    rolls = [0, 0 if prevent else 1 / prevention]
    with patch("scripts.events.random.random", side_effect=rolls), patch(
        "scripts.events.random.choices", return_value=[2]
    ):
        event.handle_outbreaks(source)
    assert len(game.cur_events_list) == int(not prevent)


@pytest.mark.parametrize("working", [False, True])
def test_only_working_colony_medics_reduce_infection(outbreak, working):
    clan, source, event = outbreak
    source.illnesses.clear()
    source.get_ill("whitecough")
    medic = Cat(status="medicine cat", moons=40)
    clan.add_cat(medic)
    if not working:
        medic.get_injured("claw-wound", severity="major")
    rate = source.illnesses["whitecough"]["infectiousness"]
    with patch("scripts.events.random.random", return_value=1 / (rate + 1)), patch(
        "scripts.events.random.choices", return_value=[2]
    ):
        event.handle_outbreaks(source)
    assert len(game.cur_events_list) == int(not working)


def test_noncontagious_illness_does_not_roll_for_outbreak(outbreak):
    clan, source, event = outbreak
    source.illnesses.clear()
    source.get_ill("grief stricken")
    assert source.illnesses["grief stricken"]["infectiousness"] == 0
    with patch("scripts.events.random.random") as roll:
        event.handle_outbreaks(source)
    roll.assert_not_called()
    assert not game.cur_events_list
