from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.clan import OtherClan
from scripts.game_structure.game_essentials import game
from scripts.screens.MoonplaceScreen import MoonplaceScreen
from scripts.screens.ChooseRebornScreen import ChooseRebornScreen
from tests.test_profile_modernization import profile


@pytest.fixture
def moonplace(profile, monkeypatch):
    clan, cats, profile_screen = profile
    profile_screen.exit_screen()
    clan.age = 6
    cats[0].status, cats[0].moons = "apprentice", 10
    spirit = Cat(status="warrior", moons=40)
    spirit.dead = True
    spirit.history = History()
    spirit.create_inheritance_new_cat()
    clan.add_cat(spirit)
    clan.add_to_starclan(spirit)
    monkeypatch.setattr("scripts.screens.MoonplaceScreen.generate_sprite", lambda cat: cat.sprite)
    screen = MoonplaceScreen("moonplace screen")
    try:
        yield clan, cats, spirit, screen
    finally:
        if getattr(screen, "text", None) is not None:
            screen.exit_screen()


def test_moonplace_selects_only_available_starclan_spirits(moonplace):
    clan, cats, spirit, screen = moonplace
    invalid = []
    for state in ("living", "outside", "df", "faded"):
        cat = Cat(status="warrior", moons=30)
        cat.dead = state != "living"
        if state != "living":
            setattr(cat, state, True)
        invalid.append(cat.ID)
    clan.starclan_cats = ["missing"] + invalid + [spirit.ID]
    with patch("scripts.screens.MoonplaceScreen.choice", side_effect=lambda items: items[0]):
        screen.screen_switches()
    assert screen.the_cat is spirit
    assert cats[0].moonplace_visit_moon == 6
    assert not cats[0].can_visit_moonplace()


def test_empty_spirit_pool_does_not_consume_apprentice_visit(moonplace, capsys):
    clan, cats, spirit, screen = moonplace
    clan.starclan_cats = ["missing", cats[1].ID]
    screen.screen_switches()
    assert screen.the_cat is None
    assert cats[0].moonplace_visit_moon is None
    assert cats[0].can_visit_moonplace()
    assert screen.texts and "StarClan" in screen.texts[0]
    screen.on_use()
    assert "Moonplace screen error" not in capsys.readouterr().out


@pytest.mark.parametrize("role", ["apprentice", "queen's apprentice", "mediator apprentice", "medicine cat", "medicine cat apprentice"])
def test_successful_visit_is_not_repeatable_in_same_moon(moonplace, role):
    clan, cats, spirit, screen = moonplace
    cats[0].status = role
    clan.all_clans = []
    screen.screen_switches()
    assert cats[0].moonplace_visit_moon == 6
    assert not cats[0].can_visit_moonplace()
    clan.age = 12
    assert cats[0].can_visit_moonplace() == role.startswith("medicine cat")


def test_switching_players_does_not_share_or_reset_visit_limits(moonplace):
    clan, cats, spirit, screen = moonplace
    screen.screen_switches()
    cats[1].status, cats[1].moons = "apprentice", 10
    chooser = SimpleNamespace(exit_screen=Mock())
    ChooseRebornScreen.change_cat(chooser, cats[1])
    assert clan.your_cat is cats[1]
    assert cats[1].can_visit_moonplace()
    ChooseRebornScreen.change_cat(chooser, cats[0])
    assert not cats[0].can_visit_moonplace()


def test_no_neighboring_colonies_does_not_crash_medical_gathering(moonplace):
    clan, cats, spirit, screen = moonplace
    cats[0].status = "medicine cat"
    clan.all_clans = []
    screen.screen_switches()
    assert screen.the_cat is spirit
    assert screen.texts
    assert cats[0].moonplace_visit_moon == 6


def test_greeting_cache_follows_the_current_colony_neighbors(moonplace):
    clan, cats, spirit, screen = moonplace
    old = OtherClan(name="Old", chosen_symbol="symbolBEECH0")
    new = OtherClan(name="New", chosen_symbol="symbolBEECH0")
    with patch.dict(game.switches, {"other_med_clan": [old], "other_med": [["Wrong colony"]]}):
        clan.all_clans = [new]
        screen.handle_other_med()
        assert game.switches["other_med_clan"] == [new]
        assert all(str(name) != "Wrong colony" for name in game.switches["other_med"][0])


def test_missing_mentor_uses_mentorless_medical_intro(moonplace):
    clan, cats, spirit, screen = moonplace
    cats[0].status = "medicine cat apprentice"
    cats[0].mentor = "missing"
    assert screen.get_med_type(cats[0]) == "you_app_mentorless"
    screen.screen_switches()
    assert screen.texts
    assert all("m_n" not in text for text in screen.texts)


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
@pytest.mark.parametrize("role", ["apprentice", "queen's apprentice", "mediator apprentice", "medicine cat apprentice", "medicine cat"])
def test_visit_limit_survives_real_cat_save_and_reload(moonplace, monkeypatch, tmp_path, mode, role):
    from pathlib import Path
    import json
    from scripts.cat_relations.inheritance import Inheritance
    from scripts.game_structure.load_cat import load_cats

    clan, cats, spirit, screen = moonplace
    clan.game_mode = mode
    cats[0].status = role
    # Moon zero is a valid saved visit, not an unvisited default.
    clan.age = 0
    screen.screen_switches()
    cat_id = cats[0].ID
    assert cats[0].moonplace_visit_moon == 0
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
    game.save_cats()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    restored = Cat.fetch_cat(cat_id)
    clan.your_cat = restored
    assert restored.moonplace_visit_moon == 0
    assert not restored.can_visit_moonplace()
    clan.age = 6
    assert restored.can_visit_moonplace() == role.startswith("medicine cat")
    # Pre-feature saves cannot tell us whether a cat has already visited.
    path = tmp_path / clan.name / "clan_cats.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    for record in data:
        record.pop("moonplace_visit_moon", None)
    path.write_text(json.dumps(data), encoding="utf-8")
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    clan.your_cat = Cat.fetch_cat(cat_id)
    assert clan.your_cat.moonplace_visit_moon is None
    assert clan.your_cat.can_visit_moonplace()


def test_paired_medical_intro_selects_the_other_medicine_cat_without_retries(moonplace):
    clan, cats, spirit, screen = moonplace
    cats[0].status = cats[1].status = "medicine cat"
    with patch("scripts.screens.MoonplaceScreen.choice", side_effect=lambda items: items[0]):
        screen.screen_switches()
    assert screen.texts
    assert any(str(cats[1].name) in text for text in screen.texts)
    assert all("r_m" not in text for text in screen.texts)


@pytest.mark.parametrize("state", ["dead", "outside", "shunned", "injured", "wrong_rank", "wrong_moon"])
def test_direct_screen_entry_cannot_consume_a_blocked_visit(moonplace, state):
    clan, cats, spirit, screen = moonplace
    cat = cats[0]
    if state == "injured":
        cat.get_injured("broken bone")
    elif state == "wrong_rank":
        cat.status = "warrior"
    elif state == "wrong_moon":
        cat.status = "medicine cat"
        clan.age = 5
    else:
        setattr(cat, state, True)
    screen.screen_switches()
    assert screen.the_cat is None
    assert cat.moonplace_visit_moon is None
    assert not cat.can_visit_moonplace()
