from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.events_module.generate_events import GenerateEvents
from scripts.events_module.short.handle_short_events import HandleShortEvents
from scripts.events_module.short.condition_events import Condition_Events
from scripts.game_structure.game_essentials import game
from scripts.utility import handle_stolen_vitality
from tests.test_murder_modernization import crime
from tests.test_cruel_season import colony, card_screen


@pytest.fixture
def revival(crime, monkeypatch):
    clan, cats = crime
    clan.game_mode = "cruel season"
    clan.cruel_cards = ["stolen_vitality"]
    leader = cats[2]
    leader.status = "leader"
    clan.leader = leader
    clan.leader_lives = 9
    monkeypatch.setattr(game, "just_died", [])
    monkeypatch.setattr(game, "herb_events_list", [])
    monkeypatch.setitem(game.switches, "skip_conditions", [])
    return clan, leader, [cat for cat in cats if cat is not leader]


def member(clan, **kwargs):
    cat = Cat(status="warrior", moons=40, **kwargs)
    cat.history = History()
    cat.create_inheritance_new_cat()
    clan.add_cat(cat)
    return cat


@pytest.mark.parametrize(
    "initial,lost", [(1, 1), (3, 1), (3, 3), (9, 3), (9, 9), (9, 0)]
)
def test_actual_revivals_charge_unique_living_members_but_not_the_final_life(
    revival, initial, lost
):
    clan, leader, cats = revival
    cats += [member(clan) for _ in range(8)]
    clan.leader_lives = max(0, initial - lost)
    if lost:
        leader.die()
        for _ in range(lost):
            History.add_death(leader, "original attack")
    handle_stolen_vitality(leader, lost)
    expected = max(0, lost - (clan.leader_lives == 0))
    sacrificed = [cat for cat in cats if cat.dead]
    assert len(sacrificed) == expected
    assert leader.dead == (initial == lost)
    assert len(leader.history.died_by) == lost
    for cat in sacrificed:
        assert len(cat.history.died_by) == 1
        assert cat.history.died_by[0]["involved"] == leader.ID
        assert "paid the price" in cat.history.died_by[0]["text"]
    assert len(game.cur_events_list) == bool(expected)
    if expected:
        assert set(game.cur_events_list[-1].cats_involved) == {
            leader.ID,
            *[c.ID for c in sacrificed],
        }


@pytest.mark.parametrize("cards", [None, [], ["weak_stars"], ["forsaken"]])
def test_other_modes_and_cards_do_not_charge_a_revival(revival, cards):
    clan, leader, cats = revival
    clan.cruel_cards = cards
    clan.leader_lives = 2
    with patch(
        "scripts.utility.sample",
        side_effect=AssertionError("No card, no sacrifice roll"),
    ):
        handle_stolen_vitality(leader, 1)
    assert not any(cat.dead for cat in cats) and not game.cur_events_list


def test_candidates_exclude_outsiders_exiles_dead_and_other_colonies(revival):
    clan, leader, cats = revival
    cats[0].outside = True
    cats[1].exiled = True
    cats[2].dead = True
    stranger = member(clan)
    clan.clan_cats.remove(stranger.ID)
    kitten = member(clan)
    kitten.moons = 3
    kitten.status = "kitten"
    kitten.shunned = 1
    clan.your_cat = kitten
    clan.leader_lives = 8
    handle_stolen_vitality(leader, 1)
    assert kitten.dead and game.switches["continue_after_death"]
    assert not cats[0].dead and not cats[1].dead and not stranger.dead
    assert game.cur_events_list[-1].cats_involved == [leader.ID, kitten.ID]


@pytest.mark.parametrize("available", [0, 2])
def test_unpaid_revivals_kill_the_leader_and_record_only_remaining_lives(
    revival, available
):
    clan, leader, cats = revival
    for cat in cats[available:]:
        cat.outside = True
    clan.leader_lives = 6
    for _ in range(3):
        History.add_death(leader, "original attack")
    handle_stolen_vitality(leader, 3)
    assert leader.dead and clan.leader_lives == 0
    assert len(leader.history.died_by) == 9
    assert [record["text"] for record in leader.history.died_by[:3]] == [
        "original attack"
    ] * 3
    assert all(
        "No cat remained" in record["text"] for record in leader.history.died_by[3:]
    )
    assert sum(cat.dead for cat in cats) == available
    assert "could not be paid" in game.cur_events_list[-1].text


@pytest.mark.parametrize("kind", ["illness", "injury", "permanent", "starving"])
def test_active_condition_paths_pay_after_preserving_cause_history(revival, kind):
    from scripts.clan_resources.freshkill import Nutrition

    clan, leader, cats = revival
    if kind == "illness":
        leader.get_ill("whitecough")
        leader.illnesses["whitecough"]["mortality"] = 1
        action = lambda: Condition_Events.handle_already_ill(leader)
    elif kind == "injury":
        leader.get_injured("broken bone")
        leader.injuries["broken bone"]["mortality"] = 1
        action = lambda: Condition_Events.handle_already_injured(leader)
    elif kind == "permanent":
        leader.get_permanent_condition("raspy lungs")
        leader.permanent_condition["raspy lungs"]["mortality"] = 1
        action = lambda: Condition_Events.handle_already_disabled(leader)
    else:
        action = lambda: Condition_Events.handle_nutrient(
            leader, {leader.ID: Nutrition()}
        )
    with patch("scripts.cat.cats.random", return_value=0):
        action()
    assert clan.leader_lives == 8 and not leader.dead
    assert len(leader.history.died_by) == 1
    assert sum(cat.dead for cat in cats) == 1
    assert any("revival" in event.text for event in game.cur_events_list)


@pytest.mark.parametrize("tags,expected", [([], 1), (["all_lives"], 8)])
def test_real_patrol_outcome_applies_the_revival_price(revival, tags, expected):
    from scripts.events_module.patrol.patrol_outcome import PatrolOutcome

    clan, leader, cats = revival
    cats += [member(clan) for _ in range(8)]
    patrol = SimpleNamespace(
        patrol_leader=leader, other_clan=SimpleNamespace(name="Other")
    )
    outcome = PatrolOutcome(dead_cats=["p_l"] + tags)
    result = outcome._handle_death(patrol)
    assert "revival" in result
    assert sum(cat.dead for cat in cats) == expected
    assert leader.dead == bool(tags)
    assert len(leader.history.died_by) == 1


@pytest.mark.parametrize("all_lives", [False, True])
def test_actual_kill_dialog_uses_actual_life_loss(revival, monkeypatch, all_lives):
    from scripts.game_structure.windows import KillCat

    clan, leader, cats = revival
    cats += [member(clan) for _ in range(8)]
    monkeypatch.setattr(
        game,
        "all_screens",
        {"profile screen": SimpleNamespace(exit_screen=Mock(), screen_switches=Mock())},
    )
    with patch("scripts.game_structure.windows.update_sprite"):
        window = KillCat(leader)
        try:
            window.take_all = all_lives
            window.process_event(
                pygame.event.Event(
                    pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.done_button
                )
            )
            assert sum(cat.dead for cat in cats) == (8 if all_lives else 1)
            assert leader.dead == all_lives
            assert len(leader.history.died_by) == 1
        finally:
            window.kill()


@pytest.mark.parametrize("all_lives", [False, True])
def test_actual_short_event_murder_keeps_attack_identity_when_payment_fails(
    revival, all_lives
):
    clan, leader, cats = revival
    culprit = cats[0]
    event_id = (
        "gen_death_murder_anylead2" if all_lives else "gen_death_murder_anymonster1"
    )
    event = next(
        e
        for e in GenerateEvents.generate_short_events("death", "general")
        if e.event_id == event_id
    )
    if not all_lives:
        clan.leader_lives = 3
    if all_lives:
        culprit.status = "deputy"
        clan.deputy = culprit
        from scripts.cat.skills import Skill, SkillPath
        from scripts.cat.personality import Personality

        culprit.skills.primary = Skill(SkillPath.FIGHTER, 29)
        culprit.personality = Personality(trait="righteous")
    with patch.object(
        GenerateEvents, "possible_short_events", return_value=[event]
    ), patch("scripts.utility.sample", return_value=cats if all_lives else [cats[-1]]):
        assert HandleShortEvents().handle_event(
            "birth_death", leader, culprit, clan.freshkill_pile, ["murder"]
        )
    assert len(leader.history.murder["is_victim"]) == 1
    attack = leader.history.murder["is_victim"][0]
    assert attack["murderer"] == culprit.ID
    if all_lives:
        assert not clan.future_events
    else:
        assert clan.future_events[0].murder_index == 0
    assert len(leader.history.died_by) == (9 if all_lives else 1)
    assert sum(cat.dead for cat in cats) == (3 if all_lives else 1)


def test_card_is_visible_selectable_and_explained(card_screen):
    from scripts.clan_resources.cruel_season import CARDS

    screen = card_screen
    screen.card_page = list(CARDS).index("stolen_vitality") // 12
    screen.refresh_cruel_cards()
    card = screen.card_buttons["stolen_vitality"]
    screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_ON_HOVERED, ui_element=card)
    )
    assert "Stolen Vitality" in screen.elements["card_title"].html_text
    assert screen.elements["card_detail"].scroll_bar is None
    screen.handle_event(
        pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=card)
    )
    assert screen.cruel_cards == game.clan.cruel_cards == ["stolen_vitality"]


@pytest.mark.parametrize("neighbors", [False, True])
@pytest.mark.parametrize("cards", [None, ["stolen_vitality"]])
def test_player_murder_of_an_ordinary_cat_does_not_take_a_leaders_life(
    revival, cards, neighbors
):
    from scripts.screens.MurderScreen import MurderScreen

    clan, leader, cats = revival
    clan.cruel_cards = cards
    clan.all_clans = [SimpleNamespace(name="Neighbor")] if neighbors else []
    player = clan.your_cat
    target = cats[0]
    screen = MurderScreen("revival player murder")
    screen.cat_to_murder = target
    screen.method = "attack"
    screen.location = "camp"
    screen.time = "day"
    clan.clan_settings["player_crimes_success"] = True
    with patch.object(screen, "get_risk_chance", return_value=0), patch.object(
        screen, "get_death_chance", return_value=0
    ), patch.object(screen, "leader_death_chance", return_value=0), patch.object(
        screen, "get_discover_chance", return_value=0
    ), patch(
        "scripts.screens.MurderScreen.randint", return_value=100
    ):
        screen.choose_murder_text(player, target, None, False)
    assert target.dead and not leader.dead
    assert clan.leader_lives == 9
    assert not any("revival" in event.text for event in game.cur_events_list)


@pytest.mark.parametrize("newborn_only", [False, True])
def test_childbirth_revival_pays_once_after_the_birth_and_original_history(
    revival, newborn_only
):
    from scripts.events_module.relationship.pregnancy_events import Pregnancy_Events

    clan, leader, cats = revival
    mate = cats[0]
    mate.gender = "male"
    leader.get_injured("pregnant")
    clan.pregnancy_data[leader.ID] = {"moons": 2, "amount": 1, "second_parent": mate.ID}
    if newborn_only:
        for cat in cats:
            cat.outside = True
    with patch(
        "scripts.events_module.relationship.pregnancy_events.random.random",
        return_value=0,
    ), patch("scripts.utility.sample", side_effect=lambda options, k: options[:k]):
        Pregnancy_Events.handle_having_kits(leader, clan)
    assert leader.ID not in clan.pregnancy_data
    assert len(leader.history.died_by) == 1
    assert clan.leader_lives == 8
    assert sum(cat.dead for cat in cats) == (0 if newborn_only else 1)
    assert any("revival" in event.text for event in game.cur_events_list)


@pytest.mark.parametrize(
    "extras", [[], ["weak_stars"], ["forsaken"], ["pride_and_joy", "fated_paths"]]
)
@pytest.mark.parametrize("failure", [False, True])
@pytest.mark.parametrize("trigger", ["utility", "patrol"])
def test_real_reload_keeps_victims_histories_life_balances_and_event_participants(
    revival, monkeypatch, tmp_path, extras, failure, trigger
):
    from scripts.game_structure.load_cat import load_cats

    clan, leader, cats = revival
    clan.cruel_cards = ["stolen_vitality"] + extras
    clan.starting_members = [leader] + cats
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr(game, "other_events_list", [])
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
    before = clan.leader_lives
    if failure:
        for cat in cats:
            cat.outside = True
    if trigger == "patrol":
        from scripts.events_module.patrol.patrol import Patrol
        from scripts.events_module.patrol.patrol_outcome import PatrolOutcome

        patrol = Patrol()
        patrol.add_patrol_cats([leader], clan)
        PatrolOutcome(dead_cats=["p_l"], history_leader_death="original illness")._handle_death(patrol)
    else:
        clan.leader_lives -= 1
        leader.die()
        History.add_death(leader, "original illness")
        handle_stolen_vitality(leader, 1)
    remaining = clan.leader_lives
    leader_id = leader.ID
    for cat in [leader] + cats:
        History.check_load(cat)
    snapshots = {
        cat.ID: (cat.dead, list(cat.history.died_by)) for cat in [leader] + cats
    }
    event_records = [event.to_dict() for event in game.cur_events_list]
    game.save_cats()
    clan.save_clan()
    game.save_events()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    game.cur_events_list.clear()
    load_cats()
    Clan().load_clan()
    game.load_events()
    loaded = game.clan
    assert loaded.cruel_cards == ["stolen_vitality"] + extras
    assert loaded.leader_lives == remaining
    assert loaded.leader.dead == (failure or before == 1)
    for ID, (dead, history) in snapshots.items():
        cat = Cat.fetch_cat(ID)
        History.check_load(cat)
        assert cat.dead == dead and cat.history.died_by == history
    assert [event.to_dict() for event in game.cur_events_list] == event_records
    assert loaded.leader.ID == leader_id
    if before == 1:
        assert not any("revival" in event.text for event in game.cur_events_list)
    elif failure:
        assert remaining == 0 and len(loaded.leader.history.died_by) == before
    else:
        assert (
            remaining == before - 1
            and sum(
                Cat.fetch_cat(cat_id).dead
                for cat_id in snapshots
                if cat_id != leader_id
            )
            == 1
        )


@pytest.mark.parametrize("all_lives", [False, True])
def test_player_leader_murder_charges_after_recording_its_attack(revival, all_lives):
    from scripts.screens.MurderScreen import MurderScreen

    clan, leader, cats = revival
    screen = MurderScreen("revival leader murder")
    screen.cat_to_murder = leader
    screen.method = "attack"
    screen.location = "camp"
    screen.time = "day"
    clan.clan_settings["player_crimes_success"] = all_lives
    with patch.object(screen, "get_risk_chance", return_value=0), patch.object(
        screen, "get_death_chance", return_value=0
    ), patch.object(screen, "leader_death_chance", return_value=0), patch.object(
        screen, "get_discover_chance", return_value=0
    ), patch(
        "scripts.screens.MurderScreen.randint", return_value=100
    ):
        screen.choose_murder_text(clan.your_cat, leader, None, False)
    assert clan.leader_lives == (0 if all_lives else 8)
    assert leader.dead == all_lives
    assert sum(cat.dead for cat in cats) == (3 if all_lives else 1)
    assert leader.history.murder["is_victim"][0]["murderer"] == clan.your_cat.ID
    assert len(leader.history.died_by) == 1


def test_patrol_mass_death_does_not_charge_the_same_dead_cat_twice(revival):
    from scripts.events_module.patrol.patrol_outcome import PatrolOutcome

    clan, leader, cats = revival
    direct_victim = cats[0]
    patrol = SimpleNamespace(
        patrol_cats=[leader, direct_victim], other_clan=SimpleNamespace(name="Other")
    )
    PatrolOutcome(dead_cats=["patrol"])._handle_death(patrol)
    assert direct_victim.dead and len(direct_victim.history.died_by) == 1
    payment = next(e for e in game.cur_events_list if "revival" in e.text)
    assert direct_victim.ID not in payment.cats_involved
    assert len(payment.cats_involved) == 2
    assert clan.leader_lives == 8 and not leader.dead


def test_retaliation_revival_cannot_sacrifice_the_murder_target_twice(revival):
    from scripts.screens.MurderScreen import MurderScreen

    clan, leader, cats = revival
    clan.your_cat = leader
    target = cats[0]
    screen = MurderScreen("revival retaliation")
    screen.cat_to_murder = target
    screen.method = "attack"
    screen.location = "camp"
    screen.time = "day"

    def sacrifice(options, k):
        assert target not in options
        return options[:k]

    with patch.object(screen, "get_risk_chance", return_value=0), patch.object(
        screen, "get_death_chance", return_value=100
    ), patch.object(screen, "leader_death_chance", return_value=0), patch.object(
        screen, "get_discover_chance", return_value=0
    ), patch(
        "scripts.screens.MurderScreen.randint", return_value=50
    ), patch(
        "scripts.utility.sample", side_effect=sacrifice
    ):
        screen.choose_murder_text(leader, target, None, False)
    assert target.dead and len(target.history.died_by) == 1
    assert clan.leader_lives == 8 and not leader.dead
    assert sum(cat.dead for cat in cats) == 2


@pytest.mark.parametrize("ancestry", [False, True])
def test_one_life_card_succession_does_not_sacrifice_any_colony_cat(revival, ancestry):
    from scripts.events import Events

    clan, leader, cats = revival
    clan.cruel_cards = ["stolen_vitality", "fated_paths", "forsaken"] + (
        ["pride_and_joy"] if ancestry else []
    )
    deputy = cats[0]
    deputy.status = "deputy"
    clan.deputy = deputy
    clan.leader_lives = 0
    leader.die()
    History.add_death(leader, "original terminal death")
    with patch(
        "scripts.utility.sample",
        side_effect=AssertionError("A terminal life must not cost a sacrifice"),
    ):
        handle_stolen_vitality(leader, 1)
    clan.clan_settings["leader"] = False
    Events().check_and_promote_leader()
    assert (
        clan.leader is deputy and deputy.status == "leader" and clan.leader_lives == 1
    )
    assert not any(cat.dead for cat in cats)
    assert not any("revival" in event.text for event in game.cur_events_list)


def test_explicit_all_lives_player_death_uses_the_same_terminal_life_rule(revival):
    from scripts.screens.MurderScreen import MurderScreen

    clan, leader, cats = revival
    clan.your_cat = leader
    screen = MurderScreen("revival all lives")
    screen.method = "attack"
    screen.holding_back = False
    with patch("scripts.screens.MurderScreen.randint", return_value=1):
        screen.handle_self_harm(leader, None, False)
    assert leader.dead and clan.leader_lives == 0
    assert sum(cat.dead for cat in cats) == 3
    assert len(leader.history.died_by) == 1
    assert "could not be paid" in game.cur_events_list[-1].text
