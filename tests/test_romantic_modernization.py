from copy import deepcopy
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
from scripts.events_module.relationship.romantic_events import Romantic_Events
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.windows import MateScreen


@pytest.fixture
def romance(monkeypatch, tmp_path):
    for target, name, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                                (Cat, "outside_cats", {}), (Cat, "dead_cats", []),
                                (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, name, value)
    clan = Clan(name="RomanceTest", camp_bg="camp1", game_mode="expanded")
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setattr(game, "cur_events_list", [])
    monkeypatch.setattr(game, "switches", {**game.switches, "clan_name": clan.name, "clan_list": [clan.name],
                                          "window_open": False, "windows_dict": [], "accept": False, "reject": False})
    for module in ("scripts.cat.cats", "scripts.clan", "scripts.game_structure.game_essentials"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    first = Cat(prefix="First", gender="female", moons=40, status="warrior")
    second = Cat(prefix="Second", gender="male", moons=40, status="warrior")
    player = Cat(prefix="Player", gender="female", moons=40, status="warrior")
    for cat in (first, second, player):
        cat.history = History()
        clan.add_cat(cat)
        cat.create_inheritance_new_cat()
    for cat in (first, second, player):
        for other in (first, second, player):
            if cat != other:
                cat.create_one_relationship(other)
    clan.your_cat = player
    windows = set(MANAGER.get_window_stack().get_full_stack())
    yield clan, first, second, player
    for window in MANAGER.get_window_stack().get_full_stack().copy():
        if window not in windows:
            window.kill()


@pytest.mark.parametrize("kind", ["had_fight", "decided_to_be_friends", "lost_feelings", "bad_breakup", "chill_breakup"])
def test_typed_breakup_applies_each_directed_reaction_once(romance, kind):
    clan, first, second, player = romance
    first.set_mate(second)
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        for field in ("romantic_love", "platonic_like", "comfortable", "admiration", "trust"):
            setattr(relation, field, 60)
    config = game.config["mates"]["breakup"]
    original = deepcopy(config)
    with patch.dict(config, {"variability": [0, 0]}), patch.object(Romantic_Events, "check_if_breakup", return_value=True), patch(
            "scripts.events_module.relationship.romantic_events.random.choices", return_value=[kind]):
        assert Romantic_Events.handle_breakup(first, second)
    assert config == original
    for cat, other in ((first, second), (second, first)):
        relation = cat.relationships[other.ID]
        assert other.ID not in cat.mates and cat.previous_mates == [other.ID]
        assert relation.mates is False
        for field in ("romantic_love", "platonic_like", "comfortable", "admiration", "trust"):
            assert getattr(relation, field) == 60 + config["reactions"][kind].get(field, 0)
        assert relation.dislike == relation.jealousy == 0
        assert len(relation.log) == 1 and game.cur_events_list[0].text in relation.log[0]
    assert len(game.cur_events_list) == 1


def test_breakup_weights_do_not_accumulate_in_shared_configuration(romance):
    clan, first, second, player = romance
    config = game.config["mates"]["breakup"]
    original = deepcopy(config)
    expected = config["default_weights"].copy()
    for kind, amount in (("chill_breakup", 2), ("lost_feelings", 5), ("had_fight", 3),
                         ("bad_breakup", 2), ("decided_to_be_friends", 5)):
        expected[kind] += amount
    for _ in range(3):
        first.set_mate(second)
        for relation in (first.relationships[second.ID], second.relationships[first.ID]):
            relation.romantic_love = 10
            relation.platonic_like = 50
            relation.comfortable = relation.trust = relation.admiration = relation.dislike = 0
        with patch.object(Romantic_Events, "check_if_breakup", return_value=True), patch(
                "scripts.events_module.relationship.romantic_events.random.choices", return_value=["had_fight"]) as choose:
            Romantic_Events.handle_breakup(first, second)
        assert choose.call_args.kwargs["weights"] == list(expected.values())
        assert config == original


def test_breakup_hostility_survives_the_liking_floor_and_leaves_other_poly_mates_intact(romance):
    clan, first, second, player = romance
    first.set_mate(second)
    first.set_mate(player)
    before = deepcopy(first.relationships[player.ID].log)
    first.relationships[second.ID].platonic_like = 0
    second.relationships[first.ID].platonic_like = 0
    with patch.dict(game.config["mates"]["breakup"], {"variability": [0, 0]}), patch.object(
            Romantic_Events, "check_if_breakup", return_value=True), patch(
            "scripts.events_module.relationship.romantic_events.random.choices", return_value=["had_fight"]):
        Romantic_Events.handle_breakup(first, second)
    assert first.mates == [player.ID] and player.mates == [first.ID]
    assert first.relationships[player.ID].mates and player.relationships[first.ID].mates
    assert first.relationships[player.ID].log == before
    assert first.relationships[second.ID].dislike == second.relationships[first.ID].dislike == 10


@pytest.mark.parametrize("state", ["no_mates", "other_no_mates", "dead", "outside", "other_dead", "other_outside", "asymmetric"])
def test_ineligible_pairs_cannot_generate_breakup_events(romance, state):
    clan, first, second, player = romance
    first.set_mate(second)
    if state == "no_mates":
        first.no_mates = True
    elif state == "other_no_mates":
        second.no_mates = True
    elif state == "asymmetric":
        first.mates.clear()
    elif state.startswith("other_"):
        setattr(second, state.removeprefix("other_"), True)
    else:
        setattr(first, state, True)
    with patch("scripts.events_module.relationship.romantic_events.random.random", return_value=0):
        assert not Romantic_Events.handle_breakup(first, second)
    assert not game.cur_events_list


def test_breakup_probability_uses_both_partners_romance(romance):
    clan, first, second, player = romance
    first.relationships[second.ID].romantic_love = 20
    second.relationships[first.ID].romantic_love = 80
    with patch("scripts.events_module.relationship.romantic_events.get_personality_compatibility", return_value=None):
        assert Romantic_Events.get_breakup_chance(first, second) == Romantic_Events.get_breakup_chance(second, first) == 35


@pytest.mark.parametrize("ex_mates", [False, True])
@pytest.mark.parametrize("accepted", [False, True])
def test_confessions_use_reconciliation_pools_only_for_mutual_ex_mates(romance, ex_mates, accepted):
    clan, first, second, player = romance
    if ex_mates:
        first.set_mate(second)
        first.unset_mate(second)
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        relation.romantic_love = relation.platonic_like = relation.comfortable = relation.admiration = relation.trust = 80
    if not accepted:
        second.relationships[first.ID].romantic_love = 0
    expected = ("high_romantic_makeup" if ex_mates else "high_romantic") if accepted else ("makeup_fail" if ex_mates else "rejected")
    with patch.object(Romantic_Events, "get_mate_string", wraps=Romantic_Events.get_mate_string) as pool:
        assert Romantic_Events.handle_confession(first)
    assert pool.call_args.args[0] == expected
    assert len(game.cur_events_list) == 1
    assert not any(token in game.cur_events_list[0].text for token in ("m_c", "r_c", "{PRONOUN", "{VERB"))
    assert (second.ID in first.mates) is accepted
    if accepted:
        assert first.ID in second.mates
        assert second.ID not in first.previous_mates and first.ID not in second.previous_mates
    else:
        assert first.relationships[second.ID].romantic_love == (60 if ex_mates else 70)
        assert second.relationships[first.ID].comfortable == (60 if ex_mates else 70)
        assert second.relationships[first.ID].platonic_like == (70 if ex_mates else 80)


def test_one_sided_previous_mate_record_does_not_trigger_makeup_writing(romance):
    clan, first, second, player = romance
    first.previous_mates = [second.ID]
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        relation.romantic_love = relation.platonic_like = relation.comfortable = 80
    with patch.object(Romantic_Events, "get_mate_string", wraps=Romantic_Events.get_mate_string) as pool:
        Romantic_Events.handle_confession(first)
    assert pool.call_args.args[0] == "high_romantic"


def test_random_remating_uses_low_romantic_makeup_pool(romance):
    clan, first, second, player = romance
    first.set_mate(second)
    first.unset_mate(second)
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        relation.romantic_love = relation.platonic_like = relation.comfortable = relation.trust = 80
    with patch("scripts.events_module.relationship.romantic_events.random.random", return_value=0), patch.object(
            Romantic_Events, "get_mate_string", wraps=Romantic_Events.get_mate_string) as pool:
        assert Romantic_Events.handle_new_mates(first, second)
    assert pool.call_args.args[0] == "low_romantic_makeup"
    assert second.ID in first.mates and first.ID in second.mates


@pytest.mark.parametrize("accept", [False, True])
@pytest.mark.parametrize("player_initiates", [False, True])
def test_player_reconciliation_waits_for_the_existing_choice_window(romance, accept, player_initiates):
    clan, first, second, player = romance
    clan.your_cat = first if player_initiates else second
    first.set_mate(second)
    first.unset_mate(second)
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        relation.romantic_love = relation.platonic_like = relation.comfortable = 80
    assert Romantic_Events.handle_confession(first)
    window = MANAGER.get_window_stack().get_full_stack()[-1]
    assert isinstance(window, MateScreen)
    assert "mates again" in window.pick_path_message.html_text
    assert not first.mates and not second.mates and not game.cur_events_list
    window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
                         ui_element=window.begin_anew_button if accept else window.mediator_button))
    assert (second.ID in first.mates) is accept
    assert game.switches["accept"] is accept and game.switches["reject"] is not accept


def test_poly_reconciliation_preserves_existing_consent_requirements(romance):
    clan, first, second, player = romance
    first.set_mate(second)
    first.unset_mate(second)
    first.set_mate(player)
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        relation.romantic_love = relation.platonic_like = relation.comfortable = 80
    assert not Romantic_Events.handle_confession(first)
    assert first.mates == [player.ID]
    assert not game.cur_events_list


@pytest.mark.parametrize("key", ["high_romantic_makeup", "low_romantic_makeup", "makeup_fail"])
@pytest.mark.parametrize("partners", ["none", "m_c_mates", "r_c_mates", "both_mates"])
def test_every_reconciliation_text_renders_with_existing_partners(romance, key, partners):
    clan, first, second, player = romance
    if partners in ("m_c_mates", "both_mates"):
        first.set_mate(player)
    if partners in ("r_c_mates", "both_mates"):
        second.set_mate(player)
    texts = Romantic_Events.MATE_DICTS[key] if partners == "none" else Romantic_Events.POLY_MATE_DICTS[key][partners]
    for text in texts:
        rendered = Romantic_Events.prepare_relationship_string(text, first, second)
        assert not any(token in rendered for token in ("m_c", "r_c", "{PRONOUN", "{VERB", "mate/mates"))
        if "_mates]" in text:
            assert str(player.name) in rendered


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_created_colony_breakup_and_reconciliation_survive_save_reload(romance, monkeypatch, tmp_path, mode):
    from scripts.game_structure.load_cat import load_cats

    clan, first, second, player = romance
    clan.game_mode = mode
    clan.leader = player
    clan.starting_members = [first, second, player]
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    clan.create_clan()
    first.set_mate(second)
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        relation.romantic_love = relation.platonic_like = relation.comfortable = relation.trust = relation.admiration = 10
    with patch("scripts.events_module.relationship.romantic_events.random.random", return_value=0), patch(
            "scripts.events_module.relationship.romantic_events.random.choices", return_value=["had_fight"]):
        Romantic_Events.handle_breakup_events(first)
    assert second.ID not in first.mates
    ids = first.ID, second.ID
    values = {cat.ID: {field: getattr(cat.relationships[other.ID], field)
                      for field in ("romantic_love", "platonic_like", "dislike", "admiration", "comfortable", "jealousy", "trust")}
              for cat, other in ((first, second), (second, first))}
    logs = {cat.ID: cat.relationships[other.ID].log.copy() for cat, other in ((first, second), (second, first))}
    for reconciled in (False, True):
        game.save_cats()
        game.clan.save_clan()
        Cat.all_cats.clear()
        Cat.all_cats_list.clear()
        Inheritance.all_inheritances.clear()
        load_cats()
        Clan().load_clan()
        first, second = (Cat.fetch_cat(cat_id) for cat_id in ids)
        for cat, other in ((first, second), (second, first)):
            relation = cat.relationships[other.ID]
            assert relation.mates is reconciled
            assert (other.ID in cat.mates) is reconciled
            assert (other.ID in cat.previous_mates) is not reconciled
            if not reconciled:
                assert all(getattr(relation, field) == value for field, value in values[cat.ID].items())
                assert relation.log == logs[cat.ID]
                relation.romantic_love = relation.platonic_like = relation.comfortable = relation.trust = relation.admiration = 80
                relation.dislike = relation.jealousy = 0
        if not reconciled:
            with patch.object(Romantic_Events, "get_mate_string", wraps=Romantic_Events.get_mate_string) as pool:
                assert Romantic_Events.handle_confession(first)
            assert pool.call_args.args[0] == "high_romantic_makeup"


def test_poly_confession_names_only_partners_from_before_reconciliation(romance):
    clan, first, second, player = romance
    first.set_mate(second)
    first.unset_mate(second)
    first.set_mate(player)
    for cat in (first, second, player):
        for relation in cat.relationships.values():
            relation.romantic_love = relation.platonic_like = relation.comfortable = relation.admiration = relation.trust = 80
            relation.dislike = relation.jealousy = 0
    first.relationships[player.ID].romantic_love = 60
    text = "m_c and r_c become mates again with the support of [m_c_mates]."
    with patch.object(Romantic_Events, "get_mate_string", return_value=text):
        assert Romantic_Events.handle_confession(first)
    assert set(first.mates) == {second.ID, player.ID}
    assert game.cur_events_list[0].text == f"{first.name} and {second.name} become mates again with the support of {player.name}."


@pytest.mark.parametrize("penalties", [False, True])
def test_unset_mate_clears_both_flags_with_or_without_penalties(romance, penalties):
    clan, first, second, player = romance
    first.set_mate(second)
    first.unset_mate(second, breakup=penalties)
    assert not first.relationships[second.ID].mates and not second.relationships[first.ID].mates
    assert first.previous_mates == [second.ID] and second.previous_mates == [first.ID]


@pytest.mark.parametrize("cards", [None, [], ["mate_breakup"]])
def test_breakup_card_reaches_real_breakup_and_preserves_seven_metrics(romance, cards):
    clan, first, second, player = romance
    clan.game_mode = "cruel season"
    clan.cruel_cards = cards
    first.set_mate(second)
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        relation.romantic_love = relation.platonic_like = 0
        relation.dislike = relation.jealousy = 0
        relation.admiration = relation.comfortable = relation.trust = 0
    with patch("scripts.events_module.relationship.romantic_events.get_personality_compatibility", return_value=None), patch(
        "scripts.events_module.relationship.romantic_events.random.random", return_value=0.05
    ):
        assert Romantic_Events.get_breakup_chance(first, second) == (15 if cards else 30)
        assert Romantic_Events.handle_breakup(first, second) is bool(cards)
    assert (second.ID not in first.mates) is bool(cards)
    assert (first.ID not in second.mates) is bool(cards)
    if cards:
        assert len(game.cur_events_list) == 1
        for relation in (first.relationships[second.ID], second.relationships[first.ID]):
            assert relation.log
            for field in ("romantic_love", "platonic_like", "dislike", "admiration", "comfortable", "jealousy", "trust"):
                assert 0 <= getattr(relation, field) <= 100


@pytest.mark.parametrize("total,protected", [(360, False), (361, True)])
@pytest.mark.parametrize("reverse", [False, True])
def test_breakup_card_threshold_counts_all_bonds_and_separate_dislike(romance, total, protected, reverse):
    clan, first, second, player = romance
    clan.game_mode = "cruel season"
    clan.cruel_cards = ["mate_breakup"]
    relation = (second.relationships[first.ID] if reverse else first.relationships[second.ID])
    relation.romantic_love = 100
    relation.platonic_like = 100
    relation.admiration = 100
    relation.comfortable = 100
    relation.trust = 0
    relation.dislike = 400 - total
    with patch("scripts.events_module.relationship.romantic_events.get_personality_compatibility", return_value=None):
        chance = Romantic_Events.get_breakup_chance(first, second)
        assert (chance == 0) is protected
        assert chance == Romantic_Events.get_breakup_chance(second, first)


def test_breakup_card_replaces_confession_veto_without_changing_ordinary_couples(romance):
    clan, first, second, player = romance
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        for field, value in (("romantic_love", 50), ("platonic_like", 35), ("comfortable", 30),
                             ("dislike", 0), ("jealousy", 0), ("admiration", 0), ("trust", 0)):
            setattr(relation, field, value)
    assert Romantic_Events.get_breakup_chance(first, second) == 0
    clan.game_mode = "cruel season"
    clan.cruel_cards = ["mate_breakup"]
    assert Romantic_Events.get_breakup_chance(first, second) >= 5
    clan.cruel_cards = []
    assert Romantic_Events.get_breakup_chance(first, second) == 0


@pytest.mark.parametrize("blocked", ["no_mates", "other_no_mates", "dead", "outside", "other_dead", "other_outside"])
def test_breakup_card_keeps_pair_eligibility_controls(romance, blocked):
    clan, first, second, player = romance
    clan.game_mode = "cruel season"
    clan.cruel_cards = ["mate_breakup"]
    first.set_mate(second)
    cat = second if blocked.startswith("other_") else first
    setattr(cat, blocked.removeprefix("other_"), True)
    with patch("scripts.events_module.relationship.romantic_events.random.random", return_value=0):
        assert not Romantic_Events.handle_breakup(first, second)
    assert second.ID in first.mates and first.ID in second.mates
    assert not game.cur_events_list


@pytest.mark.parametrize("ex_mates", [False, True])
@pytest.mark.parametrize("player_involved", [False, True])
def test_heartless_blocks_all_automatic_pairing_routes_without_mutating_relationships(romance, ex_mates, player_involved):
    clan, first, second, _ = romance
    if player_involved:
        clan.your_cat = first
    if ex_mates:
        first.set_mate(second)
        first.unset_mate(second)
    for relation in (first.relationships[second.ID], second.relationships[first.ID]):
        for field in ("romantic_love", "platonic_like", "comfortable", "admiration", "trust"):
            setattr(relation, field, 100)
        relation.dislike = relation.jealousy = 0
    before = deepcopy(first.relationships[second.ID].log)
    clan.game_mode, clan.cruel_cards = "cruel season", ["heartless"]
    with patch("scripts.events_module.relationship.romantic_events.random.random", return_value=0):
        assert not Romantic_Events.handle_confession(first)
        assert Romantic_Events.check_if_new_mate(first, second) == (False, None)
        assert not Romantic_Events.handle_new_mates(first, second)
        Romantic_Events.handle_new_mate_events(first)
    assert not first.mates and not second.mates
    assert first.relationships[second.ID].romantic_love == 100
    assert first.relationships[second.ID].log == before
    assert not game.cur_events_list and not game.switches["window_open"]


@pytest.mark.parametrize("mated", [False, True])
def test_heartless_blocks_direct_manual_mate_changes_but_keeps_existing_pairs(romance, mated):
    from scripts.screens.ChooseMateScreen import ChooseMateScreen

    clan, first, second, _ = romance
    if mated:
        first.set_mate(second)
    clan.game_mode, clan.cruel_cards = "cruel season", ["heartless"]
    screen = ChooseMateScreen()
    screen.the_cat, screen.selected_cat = first, second
    before = first.mates.copy(), second.mates.copy()
    screen.change_mate()
    assert (first.mates, second.mates) == before
    clan.cruel_cards = []
    screen.change_mate()
    assert (second.ID in first.mates) is not mated


def test_heartless_does_not_disable_existing_breakups_or_historical_family_setup(romance):
    clan, first, second, _ = romance
    clan.game_mode, clan.cruel_cards = "cruel season", ["heartless"]
    first.set_mate(second)
    assert second.ID in first.mates
    with patch.object(Romantic_Events, "check_if_breakup", return_value=True):
        assert Romantic_Events.handle_breakup(first, second)
    assert not first.mates and not second.mates
    assert second.ID in first.previous_mates and first.ID in second.previous_mates


def test_heartless_rejects_forged_confession_acceptance_with_visible_help(romance):
    clan, first, second, _ = romance
    clan.your_cat = first
    clan.game_mode, clan.cruel_cards = "cruel season", ["heartless"]
    game.switches["new_mate"] = second
    window = MateScreen("events screen")
    try:
        assert not window.begin_anew_button.is_enabled
        assert "prevents new mate bonds" in window.begin_anew_button.tool_tip_text
        window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.begin_anew_button))
        assert not first.mates and not second.mates and not game.switches["accept"]
        assert window.alive()
    finally:
        window.kill()


@pytest.mark.parametrize("mated", [False, True])
def test_heartless_picker_disables_visible_control_and_rejects_queued_actions(romance, monkeypatch, mated):
    from scripts.screens.ChooseMateScreen import ChooseMateScreen

    clan, first, second, _ = romance
    monkeypatch.setattr(Cat, "sprite", property(lambda cat: pygame.Surface((50, 50), pygame.SRCALPHA)))
    if mated:
        first.set_mate(second)
    clan.game_mode, clan.cruel_cards = "cruel season", ["heartless"]
    monkeypatch.setitem(game.switches, "cat", first.ID)
    screen = ChooseMateScreen("choose mate screen")
    screen.screen_switches()
    try:
        screen.selected_cat = second
        screen.update_selected_cat()
        button = screen.toggle_mate
        assert not button.is_enabled
        assert "manual mate changes" in button.tool_tip_text
        with patch.object(screen, "loading_screen_start_work") as worker:
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
        worker.assert_not_called()
        assert (second.ID in first.mates) is mated
    finally:
        screen.exit_screen()


def test_heartless_existing_pairs_and_rivalry_survive_real_creation_and_reload(romance, monkeypatch, tmp_path):
    from scripts.game_structure.load_cat import load_cats

    clan, first, second, player = romance
    clan.game_mode, clan.cruel_cards = "cruel season", ["heartless", "for_the_throne"]
    clan.leader = second
    clan.deputy = first
    first.status, second.status = "deputy", "leader"
    clan.starting_members = [first, second, player]
    first.set_mate(second)
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    clan.create_clan()
    first.relationships[second.ID].dislike = 20
    ids = first.ID, second.ID
    game.save_cats()
    clan.save_clan()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    first, second = (Cat.fetch_cat(id_) for id_ in ids)
    assert game.clan.cruel_cards == ["heartless", "for_the_throne"]
    assert second.ID in first.mates and first.ID in second.mates
    assert first.relationships[second.ID].mates
    assert first.relationships[second.ID].dislike == 20
    assert game.get_config_value("mates", "allow_mating") is False
    assert game.get_config_value("death_related", "murder", "deputy_prefer_leader") is True
    assert not Romantic_Events.handle_confession(first)
