import json
from pathlib import Path
from unittest.mock import Mock, patch

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.cat_relations.relationship import Relationship
from scripts.clan import Clan
from scripts.events_module.relationship.pregnancy_events import Pregnancy_Events
from scripts.game_structure.game_essentials import game


@pytest.fixture
def parents(monkeypatch, tmp_path):
    for target, name, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                                (Cat, "outside_cats", {}), (Cat, "dead_cats", []),
                                (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, name, value)
    monkeypatch.setattr(Pregnancy_Events, "biggest_family", {})
    clan = Clan(name="ParentageTest", camp_bg="camp1", game_mode="expanded")
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setattr(game, "switches", {**game.switches, "clan_name": clan.name, "clan_list": [clan.name]})
    monkeypatch.setattr(game, "cur_events_list", [])
    for module in ("scripts.cat.cats", "scripts.clan", "scripts.game_structure.game_essentials"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    first = Cat(prefix="First", gender="female", moons=40, status="warrior")
    second = Cat(prefix="Second", gender="male", moons=40, status="warrior")
    for cat in (first, second):
        cat.history = History()
        clan.add_cat(cat)
        cat.create_inheritance_new_cat()
    first.relationships[second.ID] = Relationship(first, second, romantic_love=80)
    second.relationships[first.ID] = Relationship(second, first, romantic_love=80)
    clan.your_cat = first
    return clan, first, second


@pytest.mark.parametrize("legacy", [False, True])
def test_old_affair_preference_initializes_both_controls_without_writing_on_load(parents, tmp_path, legacy):
    clan, first, second = parents
    directory = tmp_path / clan.name
    directory.mkdir()
    path = directory / "clan_settings.json"
    original = json.dumps({"affair": legacy, "single parentage": True})
    path.write_text(original)
    clan.load_clan_settings()
    assert clan.clan_settings["affair"] is legacy
    assert clan.clan_settings["unmated parentage"] is legacy
    assert clan.clan_settings["single parentage"] is True
    assert path.read_text() == original
    clan.save_clan_settings()
    restored = Clan(name=clan.name, camp_bg="camp1")
    restored.load_clan_settings()
    assert restored.clan_settings["affair"] is legacy
    assert restored.clan_settings["unmated parentage"] is legacy


@pytest.mark.parametrize("affair,unmated", [(False, False), (False, True), (True, False), (True, True)])
def test_modern_settings_keep_independent_values_and_use_the_requested_colony(parents, tmp_path, affair, unmated):
    clan, first, second = parents
    directory = tmp_path / clan.name
    directory.mkdir()
    path = directory / "clan_settings.json"
    path.write_text(json.dumps({"affair": affair, "unmated parentage": unmated}))
    game.switches["clan_list"] = ["OtherColony"]
    clan.load_clan_settings()
    assert clan.clan_settings["affair"] is affair
    assert clan.clan_settings["unmated parentage"] is unmated


def test_new_colonies_keep_existing_off_defaults(parents):
    clan, first, second = parents
    assert not clan.clan_settings["affair"]
    assert not clan.clan_settings["unmated parentage"]


@pytest.mark.parametrize("affair", [False, True])
@pytest.mark.parametrize("unmated", [False, True])
@pytest.mark.parametrize("mated", ["neither", "first", "second", "both"])
def test_loving_candidates_respect_both_controls_for_either_participant(parents, affair, unmated, mated):
    clan, first, second = parents
    clan.clan_settings.update(affair=affair)
    clan.clan_settings["unmated parentage"] = unmated
    for cat, flag in ((first, "first"), (second, "second")):
        if mated in (flag, "both"):
            mate = Cat(gender="female", moons=40, status="warrior")
            mate.history = History()
            clan.add_cat(mate)
            cat.mates.append(mate.ID)
            mate.mates.append(cat.ID)
    mate = Cat.fetch_cat(first.mates[0]) if first.mates else None
    with patch.object(Pregnancy_Events, "get_love_affair_chance", return_value=0), patch.object(
            Pregnancy_Events, "get_unmated_love_affair_chance", return_value=0):
        partner = Pregnancy_Events.determine_love_affair(first, mate, None, True, clan=clan)
    expected = affair if mated != "neither" else unmated
    assert (partner == second) is expected


def test_forbidden_highest_romance_does_not_mask_a_permitted_coparent(parents):
    clan, first, second = parents
    clan.clan_settings["unmated parentage"] = True
    forbidden = Cat(gender="male", moons=40, status="warrior")
    forbidden.mates = ["another mate"]
    first.relationships[forbidden.ID] = Relationship(first, forbidden, romantic_love=100)
    with patch.object(Pregnancy_Events, "get_unmated_love_affair_chance", return_value=0):
        partner = Pregnancy_Events.determine_love_affair(first, None, None, False, clan=clan)
    assert partner == second


@pytest.mark.parametrize("unmated", [False, True])
def test_random_coparenting_respects_unmated_control(parents, unmated):
    clan, first, second = parents
    clan.clan_settings["unmated parentage"] = unmated
    first.relationships[second.ID].romantic_love = 0
    second.relationships[first.ID].romantic_love = 0
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=0):
        partner, is_affair = Pregnancy_Events.get_second_parent(first, clan)
    assert (partner == second) is unmated
    assert is_affair is unmated


def test_unmated_only_random_choice_cannot_select_someone_elses_mate(parents):
    clan, first, second = parents
    clan.clan_settings["unmated parentage"] = True
    second.mates = ["another mate"]
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=0):
        assert Pregnancy_Events.get_second_parent(first, clan) == (None, False)


@pytest.mark.parametrize("unmated", [False, True])
def test_actual_pregnancy_requires_the_unmated_control(parents, unmated):
    clan, first, second = parents
    clan.clan_settings["unmated parentage"] = unmated
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=0):
        Pregnancy_Events.handle_having_kits(first, clan)
    assert (first.ID in clan.pregnancy_data) is unmated
    if unmated:
        assert clan.pregnancy_data[first.ID]["second_parent"] == second.ID


def test_existing_mates_and_poly_mates_are_not_blocked_by_either_switch(parents):
    clan, first, second = parents
    additional = Cat(gender="male", moons=40, status="warrior")
    clan.add_cat(additional)
    first.mates[:] = [second.ID, additional.ID]
    second.mates.append(first.ID)
    additional.mates.append(first.ID)
    for mate in (second, additional):
        with patch("scripts.events_module.relationship.pregnancy_events.choice", return_value=mate.ID):
            assert Pregnancy_Events.get_second_parent(first, clan) == (mate, False)


@pytest.mark.parametrize("single", [False, True])
def test_unknown_parentage_remains_separate(parents, single):
    clan, first, second = parents
    clan.clan_settings["single parentage"] = single
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=0):
        Pregnancy_Events.handle_having_kits(first, clan)
    assert (first.ID in clan.pregnancy_data) is single
    if single:
        assert clan.pregnancy_data[first.ID]["second_parent"] is None


@pytest.mark.parametrize("dark", [False, True])
def test_relation_settings_show_and_toggle_independent_controls(parents, dark):
    from scripts.game_structure.screen_settings import MANAGER
    from scripts.screens.ClanSettingsScreen import ClanSettingsScreen
    from scripts.screens.screens_core import screens_core as core
    from scripts.screens.Screens import Screens

    clan, first, second = parents
    core.rebuild_core(should_rebuild_bgs=False)
    screen = ClanSettingsScreen("parentage settings test")
    with patch.dict(game.settings, {"dark mode": dark}):
        screen.screen_switches()
        screen.open_relation_settings()
        try:
            first_box = screen.checkboxes["affair"].rect
            second_box = screen.checkboxes["unmated parentage"].rect
            assert not first_box.colliderect(second_box)
            assert "unmated cats" in screen.checkboxes_text["unmated parentage"].html_text
            assert "explicit player-directed" in screen.checkboxes["affair"].tool_tip_text
            for setting in ("unmated parentage", "affair", "unmated parentage"):
                screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
                                                     ui_element=screen.checkboxes[setting]))
            assert clan.clan_settings["affair"] is True
            assert clan.clan_settings["unmated parentage"] is False
            clan.save_clan_settings()
            reloaded = Clan(name=clan.name, camp_bg="camp1")
            reloaded.load_clan_settings()
            assert reloaded.clan_settings["affair"] is True
            assert reloaded.clan_settings["unmated parentage"] is False
        finally:
            screen.exit_screen()
            core.rebuild_core(should_rebuild_bgs=False)
            Screens.menu_buttons = core.menu_buttons


@pytest.mark.parametrize("state", ["no_kits", "young", "dead", "cooldown", "recovering"])
def test_coparenting_does_not_bypass_parent_eligibility(parents, state):
    clan, first, second = parents
    clan.clan_settings["unmated parentage"] = True
    if state == "no_kits":
        first.no_kits = True
    elif state == "young":
        first.moons = 10
    elif state == "dead":
        first.dead = True
    elif state == "cooldown":
        first.birth_cooldown = 3
    else:
        first.get_injured("recovering from birth")
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=0):
        Pregnancy_Events.handle_having_kits(first, clan)
    assert first.ID not in clan.pregnancy_data


def test_existing_pregnancy_completes_after_both_controls_are_disabled(parents):
    clan, first, second = parents
    first.get_injured("pregnant")
    clan.pregnancy_data[first.ID] = {"moons": 2, "amount": 1, "second_parent": second.ID}
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=.99):
        Pregnancy_Events.handle_having_kits(first, clan)
    assert first.ID not in clan.pregnancy_data
    kits = [cat for cat in Cat.all_cats.values() if cat.status == "newborn" and not cat.dead]
    assert len(kits) == 1 and kits[0].parent1 == first.ID and kits[0].parent2 == second.ID


def test_player_directed_affair_keeps_its_explicit_pregnancy_path(parents):
    from scripts.screens.AffairScreen import AffairScreen

    clan, first, second = parents
    mate = Cat(gender="male", moons=40, status="warrior")
    bystander = Cat(gender="female", moons=40, status="warrior")
    for cat in (mate, bystander):
        cat.history = History()
        clan.add_cat(cat)
    first.mates.append(mate.ID)
    mate.mates.append(first.ID)
    screen = AffairScreen("parentage player test")
    with patch.object(screen, "is_success", return_value=True), patch.object(screen, "exit_screen"), patch(
            "scripts.screens.AffairScreen.randint", side_effect=lambda lower, upper: lower):
        screen.change_cat(second)
    assert clan.affair is True
    assert clan.pregnancy_data[first.ID]["second_parent"] == second.ID
    assert not clan.clan_settings["affair"] and not clan.clan_settings["unmated parentage"]


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_full_colony_roundtrip_preserves_coparenting_preference_and_conception(parents, monkeypatch, tmp_path, mode):
    from scripts.game_structure.load_cat import load_cats

    clan, first, second = parents
    clan.game_mode = mode
    clan.leader = second
    clan.starting_members = [first, second]
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    clan.create_clan()
    clan.clan_settings["unmated parentage"] = True
    first.relationships[second.ID] = Relationship(first, second, romantic_love=80)
    second.relationships[first.ID] = Relationship(second, first, romantic_love=80)
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=0):
        Pregnancy_Events.handle_having_kits(first, clan)
    assert first.ID in clan.pregnancy_data
    game.save_cats()
    clan.save_clan()
    first_id, second_id = first.ID, second.ID
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    assert game.clan.clan_settings["unmated parentage"] is True
    assert game.clan.clan_settings["affair"] is False
    assert game.clan.pregnancy_data[first_id]["second_parent"] == second_id


@pytest.mark.parametrize("birth,adoption", [(False, False), (False, True), (True, False)])
def test_unmated_same_sex_parentage_honors_birth_and_adoption_settings(parents, birth, adoption):
    clan, first, second = parents
    second.gender = "female"
    clan.clan_settings["unmated parentage"] = True
    clan.clan_settings["same sex birth"] = birth
    clan.clan_settings["same sex adoption"] = adoption
    with patch.object(Pregnancy_Events, "get_unmated_love_affair_chance", return_value=0), patch.object(
            Pregnancy_Events, "get_balanced_kit_chance", return_value=0), patch(
            "scripts.events_module.relationship.pregnancy_events.random.random", return_value=.99):
        Pregnancy_Events.handle_having_kits(first, clan)
    if birth:
        assert clan.pregnancy_data[first.ID]["second_parent"] == second.ID
    elif adoption:
        assert not clan.pregnancy_data
        kits = [cat for cat in Cat.all_cats.values() if cat.status == "newborn" and not cat.dead]
        assert kits and all({first.ID, second.ID} <= set(kit.adoptive_parents) for kit in kits)
    else:
        assert not clan.pregnancy_data
        assert not any(cat.status == "newborn" for cat in Cat.all_cats.values())
