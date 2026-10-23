from types import SimpleNamespace
from unittest.mock import Mock, patch
import pygame
import pygame_gui
import pytest
from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.clan import Clan
from scripts.events import Events
from scripts.game_structure.game_essentials import game
from scripts.screens.RoleScreen import RoleScreen
from scripts.screens.DeputyScreen import DeputyScreen
from scripts.screens.MakeClanScreen import MakeClanScreen
from tests.test_profile_modernization import profile
from tests.test_cruel_season import colony, card_screen


def child_of(clan, leader, adopted=False, trained=True):
    child = Cat(
        status="warrior",
        moons=30,
        parent1=None if adopted else leader.ID,
        adoptive_parents=[leader.ID] if adopted else None,
    )
    child.history = History()
    clan.add_cat(child)
    child.create_inheritance_new_cat()
    if trained:
        child.former_apprentices = ["former"]
    assert child.ID in leader.get_children()
    return child


@pytest.mark.parametrize("adopted", [False, True])
@pytest.mark.parametrize("trained", [False, True])
def test_both_deputy_pools_choose_only_direct_children(profile, adopted, trained):
    clan, cats, screen = profile
    clan.cruel_cards = ["pride_and_joy"]
    leader, unrelated = cats
    leader.status = "leader"
    clan.leader = leader
    unrelated.former_apprentices = ["former"]
    child = child_of(clan, leader, adopted, trained)
    Events().check_and_promote_deputy()
    assert clan.deputy is child and child.status == "deputy"
    assert unrelated.status == "warrior"


@pytest.mark.parametrize(
    "state", ["dead", "outside", "shunned", "apprentice", "no_leader"]
)
def test_no_eligible_child_does_not_appoint_an_unrelated_fallback(profile, state):
    clan, cats, screen = profile
    clan.cruel_cards = ["pride_and_joy"]
    leader, unrelated = cats
    leader.status = "leader"
    clan.leader = leader
    unrelated.former_apprentices = ["former"]
    child = child_of(clan, leader)
    if state == "no_leader":
        clan.leader = None
    elif state == "apprentice":
        child.status = "apprentice"
    else:
        setattr(child, state, True)
    Events().check_and_promote_deputy()
    assert clan.deputy is None
    assert "Pride and Joy" in game.cur_events_list[-1].text


def test_grandchildren_and_previous_leader_children_do_not_qualify(profile):
    clan, cats, screen = profile
    clan.cruel_cards = ["pride_and_joy"]
    leader, new_leader = cats
    leader.status = "leader"
    clan.leader = leader
    child = child_of(clan, leader)
    grandchild = child_of(clan, child)
    child.outside = True
    Events().check_and_promote_deputy()
    assert clan.deputy is None and grandchild.status == "warrior"
    child.outside = False
    leader.status = "warrior"
    new_leader.status = "leader"
    clan.leader = new_leader
    Events().check_and_promote_deputy()
    assert clan.deputy is None


@pytest.mark.parametrize(
    "cards", [None, [], ["pride_and_joy"], ["pride_and_joy", "fated_paths"]]
)
def test_generation_keeps_medics_and_newborns_but_skips_initial_deputy(profile, cards):
    clan, cats, screen = profile
    clan.cruel_cards = cards
    player = Cat(status="newborn", moons=-1)
    population = [Cat(status="warrior", moons=40) for _ in range(4)]
    creator = SimpleNamespace(
        create_example_cats2=Mock(),
        leader=None,
        deputy=None,
        med_cat=None,
        members=[],
        your_cat=player,
    )
    with patch.object(
        game, "choose_cats", {str(i): cat for i, cat in enumerate(population)}
    ):
        MakeClanScreen.handle_create_other_cats(creator)
    assert creator.leader is population[0]
    assert creator.med_cat is not None and creator.med_cat.status == "medicine cat"
    assert (
        player in creator.members and player.status == "newborn" and player.moons == -1
    )
    assert (
        len({creator.leader, creator.med_cat, creator.deputy} - {None})
        + len(creator.members)
        == len(population) + 1
    )
    assert (creator.deputy is None) == bool(cards and "pride_and_joy" in cards)


@pytest.mark.parametrize("current_deputy", [False, True])
def test_manual_appointments_and_deputy_changes_are_blocked_but_other_roles_work(
    profile, current_deputy
):
    clan, cats, profile_screen = profile
    clan.cruel_cards = ["pride_and_joy"]
    if current_deputy:
        clan.deputy = cats[0]
        cats[0].status = "deputy"
    profile_screen.exit_screen()
    screen = RoleScreen("role screen")
    screen.screen_switches()
    try:
        for button in (screen.promote_leader, screen.promote_deputy):
            assert not button.is_enabled
            screen.handle_event(
                pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button)
            )
        assert clan.leader is None
        if current_deputy:
            assert not screen.switch_warrior.is_enabled
            screen.handle_event(
                pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.switch_warrior
                )
            )
            assert cats[0].status == "deputy"
        else:
            assert screen.switch_med_cat.is_enabled
            screen.handle_event(
                pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.switch_med_cat
                )
            )
            assert cats[0].status == "medicine cat"
    finally:
        screen.exit_screen()


def test_direct_deputy_chooser_cannot_bypass_dynasty_rule(profile):
    clan, cats, screen = profile
    clan.cruel_cards = ["pride_and_joy"]
    chooser = SimpleNamespace(exit_screen=Mock())
    DeputyScreen.change_cat(chooser, cats[1])
    chooser.exit_screen.assert_not_called()
    assert clan.deputy is None and cats[1].status == "warrior"


@pytest.mark.parametrize("extras", [[], ["fated_paths", "weak_stars"]])
def test_generated_colony_and_deputy_family_survive_real_save_reload(
    profile, monkeypatch, tmp_path, extras
):
    import json
    from pathlib import Path
    from scripts.cat_relations.inheritance import Inheritance
    from scripts.game_structure.load_cat import load_cats

    old, cats, screen = profile
    old.cruel_cards = ["pride_and_joy"] + extras
    player = Cat(status="newborn", moons=-1)
    player.history = History()
    population = [Cat(status="warrior", moons=70) for _ in range(4)]
    for cat in population:
        cat.history = History()
    creator = SimpleNamespace(
        create_example_cats2=Mock(),
        leader=None,
        deputy=None,
        med_cat=None,
        members=[],
        your_cat=player,
    )
    with patch.object(
        game, "choose_cats", {str(i): cat for i, cat in enumerate(population)}
    ):
        MakeClanScreen.handle_create_other_cats(creator)
    clan = Clan(
        name="PrideSave",
        biome="Forest",
        camp_bg="camp1",
        game_mode="cruel season",
        cruel_cards=old.cruel_cards,
        leader=creator.leader,
        deputy=creator.deputy,
        medicine_cat=creator.med_cat,
        starting_members=creator.members,
        your_cat=player,
    )
    monkeypatch.setattr(game, "clan", clan)
    for module in (
        "scripts.clan",
        "scripts.cat.cats",
        "scripts.game_structure.game_essentials",
        "scripts.game_structure.load_cat",
    ):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr(
        "scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0"
    )
    for name in (
        "generate_mates",
        "generate_families",
        "populate_sc",
        "populate_ur",
        "populate_df",
    ):
        monkeypatch.setattr(clan, name, Mock())

    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)

    monkeypatch.setattr(game, "safe_save", save)
    monkeypatch.setitem(game.switches, "clan_list", [clan.name])
    monkeypatch.setitem(game.switches, "clan_name", clan.name)
    player_id = player.ID
    clan.create_clan()
    assert clan.deputy is None and clan.medicine_cat is creator.med_cat
    assert player.status == "newborn" and player.moons == -1
    child = child_of(clan, clan.leader, adopted=True)
    Events().check_and_promote_deputy()
    assert clan.deputy is child
    child_id = child.ID
    game.save_cats()
    clan.save_clan()
    settings = tmp_path / clan.name / "clan_settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    data.update(leader=False, deputy=False)
    settings.write_text(json.dumps(data), encoding="utf-8")
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    loaded = game.clan
    assert loaded.cruel_cards == ["pride_and_joy"] + extras
    assert loaded.your_cat.ID == player_id and loaded.your_cat.moons == -1
    assert loaded.deputy.ID == child_id and loaded.deputy.status == "deputy"
    assert child_id in loaded.leader.get_children()
    assert loaded.clan_settings["leader"] and loaded.clan_settings["deputy"]
    Events().check_and_promote_deputy()
    assert loaded.deputy.ID == child_id


def test_succession_uses_the_new_leaders_children(profile):
    clan, cats, screen = profile
    clan.cruel_cards = ["pride_and_joy"]
    leader = cats[0]
    leader.moons = 90
    leader.status = "leader"
    clan.leader = leader
    successor = child_of(clan, leader)
    sibling = child_of(clan, leader)
    next_deputy = child_of(clan, successor, adopted=True)
    Events().check_and_promote_deputy()
    assert clan.deputy in (successor, sibling)
    clan.deputy = successor
    successor.status = "deputy"
    sibling.status = "warrior"
    leader.dead = True
    Events().check_and_promote_leader()
    assert clan.leader is successor and successor.status == "leader"
    Events().check_and_promote_deputy()
    assert clan.deputy is next_deputy and sibling.status == "warrior"


def test_card_can_be_inspected_and_selected_without_clipping_its_description(
    card_screen,
):
    screen = card_screen
    card = screen.card_buttons["pride_and_joy"]
    screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_ON_HOVERED, ui_element=card)
    )
    assert "Pride and Joy" in screen.elements["card_title"].html_text
    assert "adopted" in screen.elements["card_detail"].html_text
    assert screen.elements["card_detail"].scroll_bar is None
    screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=card)
    )
    assert screen.cruel_cards == game.clan.cruel_cards == ["pride_and_joy"]
    assert "pride_and_joy" in screen.chosen_card_buttons
    assert screen.elements["next_step"].is_enabled
