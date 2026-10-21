from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.events_module.patrol.patrol import Patrol, PatrolEvent
from scripts.game_structure.game_essentials import game


@pytest.fixture
def mode_colony(monkeypatch):
    for target, key, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                               (Cat, "outside_cats", {}), (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, key, value)
    for field in ("clan_cats", "starclan_cats", "darkforest_cats", "unknown_cats"):
        monkeypatch.setattr(Clan, field, [])
    clan = Clan(name="ModeTest", biome="Forest", camp_bg="camp1")
    clan.clan_cats = []
    monkeypatch.setattr(game, "clan", clan)
    cat = Cat(status="warrior", moons=30)
    cat.history = History()
    cat.create_inheritance_new_cat()
    clan.add_cat(cat)
    clan.your_cat = cat
    with patch.dict(game.switches, {"clan_list": ["ModeTest"], "clan_name": "ModeTest",
                                  "patrol_category": "clangen", "patrolled": []}):
        yield clan, cat


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_cruel_patrols_are_filtered_by_saved_mode(mode_colony, mode):
    clan, cat = mode_colony
    clan.game_mode = mode
    patrol = Patrol()
    patrol.add_patrol_cats([cat], clan)
    ordinary = PatrolEvent("mode_ordinary", types=["border"])
    cruel = PatrolEvent("mode_cruel", types=["border"], tags=["cruel_season"])
    filtered, romantic = patrol._filter_patrols([ordinary, cruel], "Forest", "camp1", "Newleaf", "border")
    assert ordinary in filtered
    assert (cruel in filtered) == (mode == "cruel season")
    assert not romantic


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
@pytest.mark.parametrize("previous_mode", [None, "classic", "expanded"])
def test_initial_creation_keeps_mode_in_memory_and_first_save(mode_colony, monkeypatch, tmp_path, mode, previous_mode):
    import json

    clan, cat = mode_colony
    clan = Clan(name="ModeTest", biome="Forest", camp_bg="camp1", game_mode=mode,
                leader=cat, starting_members=[cat], your_cat=cat)
    monkeypatch.setattr(game, "clan", clan)
    game.switches["game_mode"] = previous_mode
    for module in ("scripts.clan", "scripts.cat.cats", "scripts.game_structure.game_essentials"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    safe_save = game.safe_save
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    clan.create_clan()
    saved = json.loads((tmp_path / "ModeTest.json").read_text(encoding="utf-8"))
    assert clan.game_mode == mode
    assert game.switches["game_mode"] == mode
    assert saved["gamemode"] == mode


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
@pytest.mark.parametrize("biome,camp", [("Forest", 1), ("Plains", 10), ("Beach", 6)])
def test_creation_screen_passes_its_mode_to_new_colony(mode_colony, mode, biome, camp):
    from scripts.screens.MakeClanScreen import MakeClanScreen

    original, cat = mode_colony
    screen = MakeClanScreen.__new__(MakeClanScreen)
    screen.game_mode = mode
    screen.clan_name = "ModeTest"
    screen.generated_clan_prefix = "Mode"
    screen.symbol_selected = "symbolMODE0"
    screen.biome_selected = biome
    screen.selected_camp_tab = camp
    screen.selected_season = "Newleaf"
    screen.clan_age = "established"
    screen.leader = cat
    screen.deputy = screen.med_cat = None
    screen.members = [cat]
    screen.your_cat = cat
    screen.backstory = "Random"
    screen.handle_create_other_cats = Mock()
    observed = []
    with patch.dict(game.switches, {"customise_new_life": False}), patch.object(
        Clan, "create_clan", lambda clan: observed.append((clan.game_mode, clan.biome, clan.camp_bg))
    ), patch.object(game, "clan", original):
        screen.save_clan()
    assert observed == [(mode, biome, f"camp{camp}")]


def test_new_colony_does_not_share_members_or_afterlives(mode_colony):
    _, cat = mode_colony
    first = Clan(name="First")
    first.add_cat(cat)
    first.starclan_cats.append(cat.ID)
    first.darkforest_cats.append(cat.ID)
    first.unknown_cats.append(cat.ID)
    second = Clan(name="Second")
    for field in ("clan_cats", "starclan_cats", "darkforest_cats", "unknown_cats"):
        assert getattr(second, field) == []
        assert getattr(first, field) == [cat.ID]


@pytest.mark.parametrize("focus", ["", "starving"])
def test_classic_dialogue_focus_does_not_require_prey(mode_colony, focus):
    from scripts.events import Events

    clan, _ = mode_colony
    clan.game_mode = "classic"
    clan.freshkill_pile = None
    clan.focus = focus
    with patch.object(game, "cur_events_list", []):
        Events().generate_dialogue_focus()
    assert clan.focus != "starving"


@pytest.mark.parametrize("rank,abbrev", [("leader", "l_n"), ("deputy", "d_n")])
def test_apprentice_ceremony_preserves_leader_pronoun_tags(mode_colony, rank, abbrev):
    from scripts.events import Events

    clan, player = mode_colony
    player.status_change("apprentice")
    official = Cat(status=rank, moons=40, gender="female")
    clan.add_cat(official)
    setattr(clan, rank, official)
    player.mentor = official.ID
    events = Events()
    key = "apprentice ceremony" + (" no leader" if rank == "deputy" else "")
    events.b_txt = {key: [abbrev + " welcomes you to {PRONOUN/" + abbrev + "/poss} den."]}
    with patch.object(game, "cur_events_list", []):
        events.generate_app_ceremony()
        assert len(game.cur_events_list) == 1
        text = game.cur_events_list[0].text
    assert str(official.name) in text
    assert "error1" not in text and "error2" not in text
    assert "{PRONOUN" not in text
