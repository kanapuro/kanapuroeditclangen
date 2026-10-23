from itertools import chain, repeat
from unittest.mock import Mock, patch

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.events_module.relationship.pregnancy_events import Pregnancy_Events
from scripts.game_structure.game_essentials import game
from tests.test_parentage_settings import parents
from tests.test_profile_modernization import profile
from tests.test_birth_events import birth_colony
from tests.test_cruel_season import colony, card_screen


@pytest.mark.parametrize(
    "status",
    [
        "leader",
        "loner",
        "rogue",
        "kittypet",
        "warrior",
        "deputy",
        "medicine cat",
        "mediator",
        "queen",
        "elder",
        "former colonycat",
    ],
)
@pytest.mark.parametrize("cards", [None, [], ["prideful"]])
def test_rank_rule_preserves_unrestricted_colonies_and_custom_roles(
    parents, status, cards
):
    clan, first, second = parents
    clan.cruel_cards = cards
    first.status = status
    expected = not cards or status in ("leader", "loner", "rogue", "kittypet")
    assert Pregnancy_Events.check_parent_rank(first, clan) == expected
    assert (
        Pregnancy_Events.check_if_can_have_kits(first, True, False, clan=clan)
        == expected
    )


def test_qualifying_poly_mate_and_missing_mate_ids(parents):
    clan, first, second = parents
    clan.cruel_cards = ["prideful"]
    first.mates = ["missing", second.ID]
    assert not Pregnancy_Events.check_parent_rank(first, clan)
    second.status = "leader"
    assert Pregnancy_Events.check_parent_rank(first, clan)
    first.mates.append(Cat(status="warrior", moons=40).ID)
    assert Pregnancy_Events.check_parent_rank(first, clan)
    second.status = "warrior"
    assert not Pregnancy_Events.check_parent_rank(first, clan)


def test_explicit_colony_rules_are_not_taken_from_the_active_colony(parents):
    clan, first, second = parents
    other = Clan(
        name="Other",
        camp_bg="camp1",
        game_mode="cruel season",
        cruel_cards=["prideful"],
    )
    assert Pregnancy_Events.check_if_can_have_kits(first, True, False, clan=clan)
    assert not Pregnancy_Events.check_if_can_have_kits(first, True, False, clan=other)


@pytest.mark.parametrize("bigger", [False, True])
@pytest.mark.parametrize("adoption", [False, True])
@pytest.mark.parametrize("leader_mate", [False, True])
def test_monthly_conception_and_adoption_follow_rank_rules(
    parents, bigger, adoption, leader_mate
):
    clan, first, second = parents
    clan.cruel_cards = ["prideful"]
    clan.clan_settings["bigger_litters"] = bigger
    clan.clan_settings["same sex birth"] = False
    clan.clan_settings["same sex adoption"] = adoption
    if adoption:
        second.gender = first.gender
    first.mates = [second.ID]
    second.mates = [first.ID]
    if leader_mate:
        second.status = "leader"
        clan.leader = second
    before = set(Cat.all_cats)
    with patch(
        "scripts.events_module.relationship.pregnancy_events.random.random",
        side_effect=chain([0], repeat(0.99)),
    ), patch.object(Pregnancy_Events, "get_amount_of_kits", return_value=1):
        Pregnancy_Events.handle_having_kits(first, clan)
    kits = [
        cat
        for ID, cat in Cat.all_cats.items()
        if ID not in before and cat.status == "newborn"
    ]
    if adoption and leader_mate:
        assert len(kits) == 1
        assert (
            first.ID in kits[0].adoptive_parents
            and second.ID in kits[0].adoptive_parents
        )
    else:
        assert not kits
    assert (first.ID in clan.pregnancy_data) == (leader_mate and not adoption)


@pytest.mark.parametrize(
    "handler",
    [Pregnancy_Events.handle_zero_moon_pregnant, Pregnancy_Events.handle_adoption],
)
@pytest.mark.parametrize("second_qualifies", [False, True])
def test_direct_entries_cannot_bypass_rank_rules(parents, handler, second_qualifies):
    clan, first, second = parents
    clan.cruel_cards = ["prideful"]
    if second_qualifies:
        first.status = "leader"
    before = set(Cat.all_cats)
    handler(first, second, clan)
    assert not clan.pregnancy_data and set(Cat.all_cats) == before
    assert not game.cur_events_list


@pytest.mark.parametrize("allowed", [False, True])
def test_single_parentage_is_restricted_without_changing_its_setting(parents, allowed):
    clan, first, second = parents
    clan.cruel_cards = ["prideful"]
    clan.clan_settings["single parentage"] = True
    if allowed:
        first.status = "leader"
    with patch(
        "scripts.events_module.relationship.pregnancy_events.random.random",
        return_value=0,
    ):
        Pregnancy_Events.handle_having_kits(first, clan)
    assert (first.ID in clan.pregnancy_data) == allowed
    assert clan.clan_settings["single parentage"]


@pytest.mark.parametrize("allowed", [False, True])
def test_player_affair_keeps_relationship_effects_but_respects_parent_ranks(
    parents, allowed
):
    from scripts.screens.AffairScreen import AffairScreen

    clan, first, second = parents
    clan.cruel_cards = ["prideful"]
    first.mates = [second.ID]
    second.mates = [first.ID]
    if allowed:
        first.status = "leader"
    screen = AffairScreen("prideful affair test")
    before = first.relationships[second.ID].romantic_love
    with patch.object(screen, "is_success", return_value=True), patch.object(
        screen, "exit_screen"
    ), patch(
        "scripts.screens.AffairScreen.randint", side_effect=lambda lower, upper: lower
    ):
        screen.change_cat(second)
    assert clan.affair and first.relationships[second.ID].romantic_love > before
    assert (first.ID in clan.pregnancy_data) == allowed


@pytest.mark.parametrize(
    "cards", [["prideful"], ["prideful", "pride_and_joy", "fated_paths"]]
)
def test_saved_pregnancy_survives_lost_eligibility_and_completes_after_reload(
    parents, monkeypatch, tmp_path, cards
):
    from scripts.game_structure.load_cat import load_cats

    clan, first, second = parents
    clan.game_mode = "cruel season"
    clan.cruel_cards = cards
    second.status = "leader"
    clan.leader = second
    first.mates = [second.ID]
    second.mates = [first.ID]
    clan.starting_members = [first, second]
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr(
        "scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path)
    )
    monkeypatch.setattr(
        "scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0"
    )
    for method in (
        "generate_mates",
        "generate_families",
        "populate_sc",
        "populate_ur",
        "populate_df",
    ):
        monkeypatch.setattr(clan, method, Mock())
    clan.create_clan()
    with patch(
        "scripts.events_module.relationship.pregnancy_events.random.random",
        return_value=0,
    ):
        Pregnancy_Events.handle_having_kits(first, clan)
    assert first.ID in clan.pregnancy_data
    first.mates = []
    second.mates = []
    clan.pregnancy_data[first.ID].update(moons=2, amount=1)
    first_id, second_id = first.ID, second.ID
    game.save_cats()
    clan.save_clan()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    loaded = game.clan
    mother = Cat.fetch_cat(first_id)
    assert loaded.cruel_cards == cards
    assert not Pregnancy_Events.check_parent_rank(mother, loaded)
    assert loaded.pregnancy_data[first_id]["second_parent"] == second_id
    with patch(
        "scripts.events_module.relationship.pregnancy_events.random.random",
        return_value=0.99,
    ):
        Pregnancy_Events.handle_having_kits(mother, loaded)
    assert first_id not in loaded.pregnancy_data
    kits = [cat for cat in Cat.all_cats.values() if cat.status == "newborn"]
    assert (
        len(kits) == 1 and kits[0].parent1 == first_id and kits[0].parent2 == second_id
    )
    if "pride_and_joy" in cards:
        assert kits[0].ID in loaded.leader.get_children()


@pytest.mark.parametrize("origin", ["clanborn", "outsider1", "halfclan1"])
def test_starting_player_family_is_not_filtered_as_new_conception(birth_colony, origin):
    clan, events = birth_colony
    clan.game_mode = "cruel season"
    clan.cruel_cards = ["prideful"]
    clan.clan_settings["starting backstory"] = origin
    events.generate_birth_event()
    assert clan.your_cat.status == "newborn"
    assert clan.your_cat.parent1 and clan.your_cat.parent2
    assert clan.your_cat.backstory == origin


@pytest.mark.parametrize("allowed", [False, True])
def test_profile_explains_the_restriction_and_blocks_queued_clicks(profile, allowed):
    clan, cats, screen = profile
    clan.cruel_cards = ["prideful"]
    if allowed:
        cats[0].status = "leader"
        clan.leader = cats[0]
    with patch.dict(game.switches, {"have kits": True}):
        screen.toggle_your_tab()
        assert screen.have_kits_button.is_enabled == allowed
        if not allowed:
            assert "Prideful" in screen.have_kits_button.tool_tip_text
            cats[0].no_kits = True
            with patch.object(Pregnancy_Events, "handle_having_kits") as attempt:
                screen.handle_event(
                    pygame.event.Event(
                        pygame_gui.UI_BUTTON_START_PRESS,
                        ui_element=screen.have_kits_button,
                    )
                )
                attempt.assert_not_called()
            assert cats[0].no_kits and game.switches["have kits"]


def test_card_description_and_selection_use_the_existing_card_screen(card_screen):
    card = card_screen.card_buttons["prideful"]
    card_screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_ON_HOVERED, ui_element=card)
    )
    assert "Prideful" in card_screen.elements["card_title"].html_text
    assert card_screen.elements["card_detail"].scroll_bar is None
    card_screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=card)
    )
    assert card_screen.cruel_cards == game.clan.cruel_cards == ["prideful"]


@pytest.mark.parametrize("bigger", [False, True])
def test_adopted_family_survives_reload_and_qualifies_for_pride_and_joy(
    parents, monkeypatch, tmp_path, bigger
):
    from scripts.events import Events
    from scripts.game_structure.load_cat import load_cats

    clan, first, second = parents
    clan.game_mode = "cruel season"
    clan.cruel_cards = ["prideful", "pride_and_joy"]
    clan.clan_settings["bigger_litters"] = bigger
    second.status = "leader"
    clan.leader = second
    first.mates = [second.ID]
    second.mates = [first.ID]
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr(
        "scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path)
    )
    monkeypatch.setattr(
        "scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0"
    )
    clan.starting_members = [first, second]
    for method in (
        "generate_mates",
        "generate_families",
        "populate_sc",
        "populate_ur",
        "populate_df",
    ):
        monkeypatch.setattr(clan, method, Mock())
    clan.create_clan()
    with patch.object(Pregnancy_Events, "get_amount_of_kits", return_value=1), patch(
        "scripts.events_module.relationship.pregnancy_events.random.random",
        return_value=0.99,
    ):
        Pregnancy_Events.handle_adoption(first, second, clan)
    kit = next(cat for cat in Cat.all_cats.values() if cat.status == "newborn")
    assert first.ID in kit.adoptive_parents and second.ID in kit.adoptive_parents
    assert kit.ID in second.get_children()
    kit_id = kit.ID
    game.save_cats()
    clan.save_clan()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    loaded = game.clan
    child = Cat.fetch_cat(kit_id)
    assert child.ID in loaded.leader.get_children()
    assert loaded.your_cat.ID in child.adoptive_parents
    assert loaded.cruel_cards == ["prideful", "pride_and_joy"]
    child.moons = 30
    child.status_change("warrior")
    child.former_apprentices = ["former"]
    Events().check_and_promote_deputy()
    assert loaded.deputy is child


def test_standalone_parent_check_before_loading_a_colony_preserves_mate_cleanup(
    parents, monkeypatch
):
    clan, first, second = parents
    monkeypatch.setattr(game, "clan", None)
    first.mates = ["missing_one", "missing_two"]
    assert not Pregnancy_Events.check_if_can_have_kits(first, False, False)
    assert first.mates == []
    assert Pregnancy_Events.check_if_can_have_kits(first, True, False)
