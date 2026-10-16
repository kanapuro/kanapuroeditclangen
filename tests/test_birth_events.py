import json
import random
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.cat.cats import BACKSTORIES, Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.events import BirthType, Events
from scripts.game_structure.game_essentials import game


ORIGINS = list(dict.fromkeys(origin for origins in BACKSTORIES["birth_backstories"].values() for origin in origins))


@pytest.fixture
def birth_colony(monkeypatch):
    for target, key, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                               (Cat, "outside_cats", {}), (Inheritance, "all_inheritances", {}),
                               (game, "cur_events_list", [])):
        monkeypatch.setattr(target, key, value)
    monkeypatch.setitem(game.switches, "clan_list", ["BirthTest"])
    monkeypatch.setitem(game.switches, "clan_name", "BirthTest")
    monkeypatch.setitem(game.switches, "continue_after_death", False)
    clan = Clan(name="BirthTest", biome="Forest", camp_bg="camp1")
    clan.clan_cats = []
    clan.age = 1
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setattr(game, "save_cats", lambda *args, **kwargs: pytest.fail("Unexpected save"))
    monkeypatch.setattr(game, "safe_save", lambda *args, **kwargs: pytest.fail("Unexpected save"))
    player = Cat(status="newborn", moons=0, gender="female", backstory="unknown")
    clan.your_cat = player
    clan.add_cat(player)
    for status, gender in (("leader", "male"), ("warrior", "female")):
        cat = Cat(status=status, moons=30, gender=gender)
        clan.add_cat(cat)
        if status == "leader":
            clan.leader = cat
    for cat in Cat.all_cats_list:
        cat.history = History()
        cat.create_inheritance_new_cat()
    events = Events()
    events.b_txt = json.loads(Path("resources/dicts/events/lifegen_events/ceremonies.json").read_text(encoding="utf-8"))
    # Skip litter generation except in the dedicated sibling test.
    randint = random.randint
    monkeypatch.setattr("scripts.events.random.randint", lambda a, b: 1 if (a, b) == (1, 4) else randint(a, b))
    return clan, events


@pytest.mark.parametrize("origin", ORIGINS)
@pytest.mark.parametrize("single", [False, True])
def test_selected_origin_matches_family(birth_colony, origin, single):
    clan, events = birth_colony
    clan.clan_settings["starting backstory"] = origin
    clan.clan_settings["single parentage"] = single
    events.generate_birth_event()
    player = clan.your_cat
    parents = [Cat.fetch_cat(ID) for ID in (player.parent1, player.parent2) if ID]
    assert player.backstory == origin
    assert clan.clan_settings["starting backstory"] is None
    assert player.inheritance is not None
    if not single:
        assert len(parents) == 2
    if origin.startswith(("halfclan", "outsider_roots")):
        assert len(parents) == 2
        assert not parents[0].outside and not parents[0].dead
        assert parents[1].outside and not parents[1].dead
        roles = {"halfclan4": "mediator", "halfclan5": "leader", "halfclan6": "deputy",
                 "halfclan7": "medicine cat", "halfclan8": "medicine cat", "halfclan9": "leader",
                 "halfclan10": "deputy", "outsider_roots5": "kittypet", "outsider_roots6": "kittypet",
                 "outsider_roots7": "rogue", "outsider_roots8": "rogue"}
        assert parents[1].status == roles.get(origin, "warrior" if origin.startswith("halfclan") else "loner")
    elif origin == "clanborn":
        assert all(not cat.dead and not cat.outside for cat in parents)
    elif origin == "outsider1":
        assert all(not cat.dead and not cat.outside and cat.backstory != "clanborn" for cat in parents)
    else:
        assert all(cat.dead and cat.outside for cat in parents)
        if origin == "orphaned5":
            assert len(parents) == 2
        if origin == "abandoned4":
            assert all(cat.status == "kittypet" for cat in parents)
    text = game.cur_events_list[0].text
    assert text and "{PRONOUN" not in text and "m_c" not in text and "error1" not in text and "error2" not in text
    if origin not in ("clanborn", "outsider1"):
        assert str(player.name) in text


@pytest.mark.parametrize("birth_type", list(BirthType))
def test_birth_types_do_not_retry_or_lose_settings(birth_colony, birth_type):
    clan, events = birth_colony
    clan.clan_settings["single parentage"] = True
    original_choice = random.choice
    rolls = []
    def choose(values):
        if values and isinstance(values[0], BirthType):
            rolls.append(values)
            assert len(rolls) == 1
            return birth_type
        return original_choice(values)
    with patch("scripts.events.random.choice", side_effect=choose):
        events.generate_birth_event()
    assert game.cur_events_list[0].text
    assert clan.your_cat.backstory in BACKSTORIES["birth_backstories"][birth_type.value]


@pytest.mark.parametrize("empty", [False, True])
def test_clanborn_handles_missing_compatible_parents(birth_colony, empty):
    clan, events = birth_colony
    clan.clan_settings["starting backstory"] = "clanborn"
    clan.clan_settings["single parentage"] = False
    for cat in list(Cat.all_cats.values()):
        if cat is clan.your_cat:
            continue
        if empty:
            cat.outside = True
        else:
            cat.gender = "female"
            cat.mates = ["missing-cat"]
    events.generate_birth_event()
    parents = [Cat.fetch_cat(ID) for ID in (clan.your_cat.parent1, clan.your_cat.parent2)]
    assert all(parent and not parent.dead and not parent.outside for parent in parents)
    assert parents[0].gender != parents[1].gender
    assert clan.your_cat.backstory == "clanborn"


def test_selected_origin_and_family_are_shared_with_siblings(birth_colony, monkeypatch):
    clan, events = birth_colony
    clan.clan_settings["starting backstory"] = "outsider_roots5"
    randint = random.randint
    monkeypatch.setattr("scripts.events.random.randint", lambda a, b: 2 if (a, b) == (1, 4) else randint(a, b))
    events.generate_birth_event()
    player = clan.your_cat
    siblings = [cat for cat in Cat.all_cats.values() if cat is not player and cat.moons == 0]
    assert siblings
    for sibling in siblings:
        assert sibling.backstory == player.backstory
        assert (sibling.parent1, sibling.parent2) == (player.parent1, player.parent2)
        assert sibling.ID in player.inheritance.get_siblings()


def test_pending_origin_survives_real_save_and_reload(birth_colony, monkeypatch, tmp_path):
    from scripts.game_structure.load_cat import load_cats

    clan, events = birth_colony
    player = clan.your_cat
    player.moons = -1
    player_ID = player.ID
    clan.clan_settings["starting backstory"] = "orphaned5"
    for module in ("scripts.clan", "scripts.cat.cats", "scripts.game_structure.game_essentials",
                   "scripts.game_structure.load_cat"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_cats", type(game).save_cats.__get__(game))
    monkeypatch.setattr(game, "safe_save", type(game).safe_save)
    game.save_cats()
    clan.save_clan_settings()
    clan.clan_settings["starting backstory"] = None
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    clan.load_clan_settings()
    clan.your_cat = Cat.fetch_cat(player_ID)
    assert clan.your_cat.moons == -1
    assert clan.clan_settings["starting backstory"] == "orphaned5"
    clan.your_cat.one_moon()
    events.generate_birth_event()
    expected_parents = (clan.your_cat.parent1, clan.your_cat.parent2)
    expected_adoption = clan.your_cat.adoptive_parents.copy()
    assert clan.your_cat.backstory == "orphaned5"
    game.save_cats()
    clan.save_clan_settings()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    clan.load_clan_settings()
    loaded = Cat.fetch_cat(player_ID)
    assert (loaded.moons, loaded.status, loaded.backstory) == (0, "newborn", "orphaned5")
    assert (loaded.parent1, loaded.parent2) == expected_parents
    assert loaded.adoptive_parents == expected_adoption
    assert loaded.inheritance is not None
    assert clan.clan_settings["starting backstory"] is None


def test_random_birth_never_offers_unknown_second_parent_when_disabled(birth_colony):
    clan, events = birth_colony
    clan.clan_settings["single parentage"] = False
    original_choice = random.choice
    def choose(values):
        if values and isinstance(values[0], BirthType):
            assert BirthType.ONE_OUTSIDER_PARENT not in values
            return BirthType.ONE_PARENT
        return original_choice(values)
    with patch("scripts.events.random.choice", side_effect=choose):
        events.generate_birth_event()
    assert clan.your_cat.parent1 and clan.your_cat.parent2
    assert clan.your_cat.backstory.startswith(("halfclan", "outsider_roots"))
