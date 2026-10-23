import json
from copy import deepcopy
from itertools import combinations
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan, OtherClan
from scripts.clan_resources.cruel_season import CARDS, CARD_DATA, validate_cards
from scripts.events_module.relationship.pregnancy_events import Pregnancy_Events
from scripts.game_structure.game_essentials import game
from scripts.utility import get_current_season


@pytest.fixture
def colony(monkeypatch):
    for target, key, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                               (Cat, "outside_cats", {}), (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, key, value)
    clan = Clan(name="CruelTest", biome="Forest", camp_bg="camp1", game_mode="cruel season", cruel_cards=[])
    monkeypatch.setattr(game, "clan", clan)
    with patch.dict(game.switches, {"clan_list": [clan.name], "clan_name": clan.name, "game_mode": clan.game_mode}):
        yield clan


@pytest.mark.parametrize("card", CARDS)
def test_card_definitions_have_real_config_paths(colony, card):
    assert validate_cards([card]) == [card]
    for path in CARDS[card]["modifiers"]:
        keys = tuple(path.split("."))
        game.get_config_value(*keys)


@pytest.mark.parametrize("first,second", list(combinations(CARDS, 2)))
def test_all_card_pairs_have_deterministic_conflicts(first, second):
    conflict = ((first.startswith("always_") and second.startswith("always_"))
                or {first, second} == {"mouths_to_feed", "underpopulated"}
                or {first, second} == {"weak_stars", "forsaken"}
                or {first, second} == {"crowfood", "survival_of_fittest"}
                or {first, second} == {"heartless", "mate_breakup"})
    if conflict:
        with pytest.raises(ValueError, match="Conflicting cards"):
            validate_cards([first, second])
    else:
        assert validate_cards([first, second]) == [first, second]


def test_invalid_cards_do_not_silently_change_selection(monkeypatch):
    for cards in (["unknown"], ["kit_season", "kit_season"], "kit_season", [1]):
        with pytest.raises(ValueError):
            validate_cards(cards)
    monkeypatch.setitem(CARD_DATA, "limit", 1)
    with pytest.raises(ValueError, match="at most"):
        validate_cards(["kit_season", "resolute"])
    original = ["kit_season"]
    selected = validate_cards(original)
    selected.clear()
    assert original == ["kit_season"]
    with pytest.raises(ValueError, match="require Cruel Season"):
        Clan(name="Invalid", game_mode="expanded", cruel_cards=["kit_season"])


def test_card_modifiers_do_not_mutate_shared_config_or_other_colonies(colony, monkeypatch):
    before_config, before_prey = deepcopy(game.config), deepcopy(game.prey_config)
    colony.cruel_cards = ["kit_season", "lean_meat"]
    assert game.get_config_value("pregnancy", "birth_cooldown") == 2
    assert game.get_config_value("pregnancy")["birth_cooldown"] == 2
    assert game.get_config_value("prey", "prey_requirement", "warrior") == 4
    game.get_config_value("prey", "prey_requirement")["warrior"] = 99
    assert game.get_config_value("prey", "prey_requirement", "warrior") == 4
    assert game.config == before_config and game.prey_config == before_prey
    ordinary = Clan(name="Ordinary", game_mode="expanded")
    monkeypatch.setattr(game, "clan", ordinary)
    assert game.get_config_value("pregnancy", "birth_cooldown") == before_config["pregnancy"]["birth_cooldown"]
    assert game.get_config_value("prey", "prey_requirement", "warrior") == before_prey["prey_requirement"]["warrior"]


def test_legacy_difficulty_is_preserved_and_card_mode_uses_expanded_base(colony):
    colony.cruel_cards = None
    assert game.get_config_value("death_related", "cruel season_death_chance") == game.config["death_related"]["cruel season_death_chance"]
    colony.cruel_cards = []
    assert game.get_config_value("death_related", "cruel season_death_chance") == game.config["death_related"]["expanded_death_chance"]
    colony.cruel_cards = ["miasma"]
    assert game.get_config_value("condition_related", "cruel season_illness_chance") == 175


def test_war_card_changes_modifiers_without_removing_war_logic(colony):
    colony.cruel_cards = ["tooth_and_claw"]
    assert game.get_config_value("death_related", "cruel season_death_chance") == 350
    colony.war["at_war"] = True
    assert game.get_config_value("death_related", "cruel season_death_chance") == 10
    assert game.get_config_value("death_related", "leader_death_chance") == 4
    assert game.get_config_value("condition_related", "cruel season_injury_chance") == 15


@pytest.mark.parametrize("season", ["Newleaf", "Greenleaf", "Leaf-fall", "Leaf-bare"])
def test_permanent_seasons_do_not_drift(colony, season):
    colony.cruel_cards = ["always_" + season.lower()]
    for moon in range(25):
        colony.age = moon
        assert get_current_season() == season


@pytest.mark.parametrize("larger", [False, True])
@pytest.mark.parametrize("mated", [False, True])
def test_kit_season_changes_both_pregnancy_paths(colony, larger, mated):
    first = Cat(status="warrior", moons=40, gender="female")
    second = Cat(status="warrior", moons=40, gender="male")
    for cat in (first, second):
        colony.add_cat(cat)
        cat.create_inheritance_new_cat()
        cat.init_all_relationships()
    colony.clan_settings["bigger_litters"] = larger
    if mated:
        first.mates = [second.ID]
        second.mates = [first.ID]
    ordinary = Pregnancy_Events.get_balanced_kit_chance(first, second, False, colony)
    colony.cruel_cards = ["kit_season"]
    modified = Pregnancy_Events.get_balanced_kit_chance(first, second, False, colony)
    assert modified < ordinary
    assert game.get_config_value("pregnancy", "birth_cooldown") == 2


def test_food_requirements_match_manual_feeding_and_nutrition(colony):
    colony.cruel_cards = ["lean_meat"]
    cats = [Cat(status=status, moons=moons) for status, moons in
            [("warrior", 30), ("queen", 30), ("queen's apprentice", 8), ("kitten", 3), ("newborn", 0)]]
    for cat in cats:
        colony.add_cat(cat)
    pile = colony.freshkill_pile
    pile.living_cats = cats
    pile.update_nutrition(cats)
    requirements = game.get_config_value("prey", "prey_requirement")
    pile._update_needed_food(cats)
    assert pile.needed_prey == sum(requirements[cat.status] for cat in cats)
    for cat in cats:
        nutrition = pile.nutrition_info[cat.ID]
        factor = 2 if cat.status in ("newborn", "kitten", "elder") else 3
        assert nutrition.max_score == requirements[cat.status] * factor
        nutrition.current_score = 0
        pile.add_freshkill(10)
        pile.feed_cat(cat, requirements[cat.status], 0)
        assert nutrition.current_score == requirements[cat.status]


def test_reputation_and_neighbor_caps_survive_mutations_and_keep_save_keys(colony):
    colony.cruel_cards = ["malicious_aura", "enmity"]
    colony.reputation = 90
    assert colony.reputation == 29
    neighbor = OtherClan(name="Neighbor", chosen_symbol="symbolBEECH0")
    assert 1 <= neighbor.relations <= 7
    neighbor.relations += 30
    assert neighbor.relations == 7
    assert vars(neighbor)["relations"] == 7
    zero = OtherClan(name="Zero", relations=0, chosen_symbol="symbolBEECH0")
    assert zero.relations == 0


def test_starting_supplies_use_own_cards_not_previous_colony(colony):
    colony.cruel_cards = ["barren_stocks", "malicious_aura"]
    ordinary = Clan(name="Ordinary", game_mode="expanded")
    assert ordinary.freshkill_pile.total_amount == game.prey_config["start_amount"]
    selected = Clan(name="NewCards", game_mode="cruel season", cruel_cards=["barren_stocks", "malicious_aura"])
    assert selected.freshkill_pile.total_amount == 0
    assert selected.reputation == 15
    assert selected.clan_settings["freshkill"] is False


@pytest.mark.parametrize("feeding_card", ["survival_of_fittest", "crowfood"])
@pytest.mark.parametrize("life_card", [None, "weak_stars", "forsaken"])
@pytest.mark.parametrize("litter_card", ["mouths_to_feed", "underpopulated"])
def test_cards_survive_real_clan_and_cat_reload_without_reapplying_start_effects(colony, monkeypatch, tmp_path, litter_card, life_card, feeding_card):
    from scripts.game_structure.load_cat import load_cats

    colony.cruel_cards = ["barren_stocks", "always_leaf-bare", "enmity", "burnout", "plague_ridden", "longer_illnesses", litter_card, "clumsy_paws", feeding_card, "for_the_throne", "heartless"]
    if life_card:
        colony.cruel_cards.append(life_card)
    leader = Cat(status="leader", moons=40)
    player = Cat(status="kitten", moons=1)
    colony.leader, colony.your_cat = leader, player
    colony.starting_members = [leader, player]
    for cat in (leader, player):
        cat.history = History()
        colony.add_cat(cat)
    for module in ("scripts.clan", "scripts.cat.cats", "scripts.game_structure.game_essentials", "scripts.game_structure.load_cat"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(colony, method, Mock())
    safe_save = game.safe_save
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    colony.create_clan()
    assert colony.starting_season == "Leaf-bare"
    granted = colony.leader_lives_granted
    ceremony = History.get_lead_ceremony(leader) if life_card else None
    assert not life_card or ceremony
    assert 1 <= granted <= (5 if life_card == "weak_stars" else 1 if life_card == "forsaken" else 9)
    colony.leader_lives -= 1
    colony.apply_leader_life_limit()
    saved_lives = colony.leader_lives
    saved_reserve = colony.leader_lives_reserve
    colony.herbs = {"moss": 5}
    leader.get_ill("whitecough", lethal=False)
    saved_duration = leader.illnesses["whitecough"]["duration"]
    leader_id = leader.ID
    saved_prey = {"expires_in_4": 3.5, "expires_in_3": 2.25, "expires_in_2": 1.25, "expires_in_1": 5}
    colony.freshkill_pile.pile = saved_prey.copy()
    colony.freshkill_pile.total_amount = 12
    game.save_cats()
    colony.save_clan()
    expected = colony.cruel_cards.copy()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    assert game.clan.cruel_cards == expected
    assert game.get_config_value("mates", "allow_mating") is False
    assert game.get_config_value("death_related", "murder", "deputy_prefer_leader") is True
    assert game.clan.leader_lives_granted == granted
    assert game.clan.leader_lives == saved_lives
    assert game.clan.leader_lives_reserve == saved_reserve
    if life_card:
        loaded_leader = Cat.fetch_cat(leader_id)
        game.clan.leader_lives_granted = 1 if granted > 1 else 5
        assert History.get_lead_ceremony(loaded_leader) == ceremony
        game.clan.leader_lives_granted = granted
    assert Cat.fetch_cat(leader_id).illnesses["whitecough"]["duration"] == saved_duration
    from scripts.conditions import get_amount_cat_for_one_medic
    assert get_amount_cat_for_one_medic(game.clan) == 5
    assert game.get_config_value("condition_related", "med_infection_reduction") == 0
    assert game.clan.freshkill_pile.total_amount == 12
    assert game.clan.freshkill_pile.pile == saved_prey
    assert game.get_config_value("prey", "time_to_rot") == (1 if feeding_card == "crowfood" else 4)
    assert game.clan.herbs == {"moss": 5}
    assert game.clan.starting_season == "Leaf-bare"
    assert 1 <= game.clan.all_clans[0].relations <= 7
    # A pre-card save must keep legacy behavior when the optional field is absent.
    path = tmp_path / "CruelTest.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved.pop("cruel_cards")
    saved.pop("leader_lives_granted")
    path.write_text(json.dumps(saved), encoding="utf-8")
    Clan().load_clan()
    assert game.clan.cruel_cards is None
    assert game.clan.leader_lives_granted == 9
    assert game.clan.leader_lives == saved_lives
    assert game.clan.leader_lives_reserve == saved_reserve


@pytest.mark.parametrize("kind,name", [("illness", "whitecough"), ("injury", "claw-wound"), ("permanent", "weak leg")])
def test_new_cards_keep_expanded_condition_mortality_while_old_cruel_keeps_penalties(colony, kind, name):
    def mortality(cards):
        colony.cruel_cards = cards
        cat = Cat(status="warrior", moons=30)
        if kind == "illness":
            cat.get_ill(name)
            return cat.illnesses[name]["mortality"]
        if kind == "injury":
            cat.get_injured(name)
            return cat.injuries[name]["mortality"]
        cat.get_permanent_condition(name)
        return cat.permanent_condition[name]["mortality"]
    modern = mortality([])
    old = mortality(None)
    colony.game_mode = "expanded"
    expanded = mortality(None)
    assert modern == expanded
    assert old <= expanded


def test_card_selection_navigation_and_cancel_preserve_original_colony(colony, monkeypatch):
    import pygame
    import pygame_gui
    from scripts.screens.MakeClanScreen import MakeClanScreen

    original = colony
    original.cruel_cards = ["lean_meat"]
    original.clan_settings["freshkill"] = True
    before_settings = deepcopy(original.clan_settings)
    monkeypatch.setattr(game, "choose_cats", {})
    monkeypatch.setattr("scripts.utility.generate_sprite", lambda *args, **kwargs: pygame.Surface((50, 50), pygame.SRCALPHA))
    with patch.dict(game.switches, {"customise_new_life": False, "clan_list": []}):
        screen = MakeClanScreen()
        screen.tutorial_shown = True
        screen.screen_switches()
        try:
            assert screen.sub_screen == "game settings"
            assert game.clan is not original
            assert game.clan.name is None
            screen.clan_name = "Draft"
            screen.open_game_settings()
            assert game.get_config_value("prey", "prey_requirement", "warrior") != 4
            def press(key):
                screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements[key]))
            def card(key):
                if key not in screen.chosen_card_buttons:
                    available = [name for name in CARDS if name not in screen.cruel_cards]
                    screen.card_page = available.index(key) // 12
                    screen.refresh_cruel_cards()
                button = screen.chosen_card_buttons.get(key) or screen.card_buttons[key]
                screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
            press("mode_cruel season")
            press("next_step")
            assert screen.sub_screen == "cruel cards"
            assert not screen.elements["next_step"].is_enabled
            card("always_leaf-bare")
            card("always_newleaf")
            assert screen.cruel_cards == ["always_leaf-bare"]
            from scripts.screens.CruelCards import CruelCardConflicts
            from scripts.game_structure.screen_settings import MANAGER
            window = next(w for w in MANAGER.get_window_stack().get_full_stack() if isinstance(w, CruelCardConflicts))
            assert "Newleaf" in window.message.html_text
            window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.keep_button))
            card("lean_meat")
            press("previous_step")
            press("next_step")
            assert game.clan.cruel_cards == ["always_leaf-bare", "lean_meat"]
            with patch.object(screen, "open_name_clan") as next_page:
                press("next_step")
                next_page.assert_called_once()
            screen.open_choose_background()
            screen.refresh_text_and_buttons()
            assert screen.selected_season == "Leaf-bare"
            assert all(not screen.tabs[key].is_enabled for key in ("newleaf_tab", "greenleaf_tab", "leaffall_tab", "leafbare_tab"))
            screen.open_game_settings()
            press("mode_expanded")
            assert screen.cruel_cards == []
            assert game.clan.cruel_cards is None
            assert game.get_config_value("forced_starting_season") is None
        finally:
            screen.exit_screen()
    assert game.clan is original
    assert original.cruel_cards == ["lean_meat"]
    assert original.clan_settings == before_settings


def test_hunting_rewards_use_card_food_requirements_and_expanded_bonuses(colony, monkeypatch):
    from scripts.events_module.patrol.patrol import Patrol
    from scripts.events_module.patrol.patrol_outcome import PatrolOutcome

    monkeypatch.setattr(game, "freshkill_event_list", [])
    hunter = Cat(status="warrior", moons=40)
    colony.add_cat(hunter)
    patrol = Patrol()
    patrol.add_patrol_cats([hunter], colony)
    outcome = PatrolOutcome(prey=["medium"])
    def catch():
        before = colony.freshkill_pile.total_amount
        assert outcome._handle_prey(patrol)
        return colony.freshkill_pile.total_amount - before
    modern = catch()
    colony.game_mode, colony.cruel_cards = "expanded", None
    assert catch() == pytest.approx(modern)
    colony.game_mode, colony.cruel_cards = "cruel season", ["lean_meat"]
    assert catch() > modern


def test_new_cards_keep_expanded_medical_capacity(colony):
    from scripts.conditions import get_amount_cat_for_one_medic

    assert get_amount_cat_for_one_medic(colony) == 10
    colony.cruel_cards = None
    assert get_amount_cat_for_one_medic(colony) == 7


@pytest.mark.parametrize("cards", [[], ["lean_meat"]])
@pytest.mark.parametrize("kit_moons", [1, 4])
def test_nursery_food_totals_match_actual_custom_role_meals(colony, cards, kit_moons):
    colony.cruel_cards = cards
    mother = Cat(status="queen", moons=30, gender="female")
    kit = Cat(status="kitten", moons=kit_moons, parent1=mother.ID)
    pregnant = Cat(status="queen's apprentice", moons=15, gender="female")
    pregnant.injuries["pregnant"] = {"severity": "major"}
    cats = [mother, kit, pregnant]
    for cat in cats:
        colony.add_cat(cat)
    pile = colony.freshkill_pile
    pile.living_cats = cats
    pile.update_nutrition(cats)
    requirements = pile.prey_requirement
    expected = requirements["queen/pregnant"]
    expected += (requirements["queen/pregnant"] if kit_moons < 3
                 else requirements["queen"] + requirements["kitten"])
    pile._update_needed_food(cats)
    assert pile.needed_prey == expected
    pile.pile = dict.fromkeys(pile.pile, 0)
    pile.total_amount = 0
    pile.add_freshkill(expected)
    pile.feed_cats(cats)
    assert pile.total_amount == 0
    assert all(pile.nutrition_info[cat.ID].percentage == 100 for cat in cats)
    expected_parent_max = (requirements["queen/pregnant"] if kit_moons < 3 else requirements["queen"]) * 3
    assert pile.nutrition_info[mother.ID].max_score == expected_parent_max


@pytest.fixture
def card_screen(colony, monkeypatch):
    import pygame
    from scripts.screens.MakeClanScreen import MakeClanScreen

    monkeypatch.setattr(game, "choose_cats", {})
    monkeypatch.setattr("scripts.utility.generate_sprite", lambda *args, **kwargs: pygame.Surface((50, 50), pygame.SRCALPHA))
    with patch.dict(game.switches, {"customise_new_life": False, "clan_list": []}):
        screen = MakeClanScreen()
        screen.tutorial_shown = True
        screen.screen_switches()
        screen.clan_name = "DeckTest"
        screen.open_game_settings()
        screen.game_mode = "cruel season"
        game.clan.game_mode = "cruel season"
        game.clan.cruel_cards = []
        screen.open_cruel_cards()
        try:
            yield screen
        finally:
            screen.exit_screen()


def test_card_hover_inspects_without_selecting_and_click_removes_from_deck(card_screen):
    import pygame
    import pygame_gui

    screen = card_screen
    card = screen.card_buttons["kit_season"]
    original = card.relative_rect.topleft
    card.on_hovered()
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_ON_HOVERED, ui_element=card))
    assert screen.cruel_cards == []
    assert "Kit Season" in screen.elements["card_title"].html_text
    assert card.relative_rect.y < original[1]
    assert screen.elements["card_container"].rect.contains(card.rect)
    card.on_unhovered()
    assert card.relative_rect.topleft == original
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=card))
    assert screen.cruel_cards == ["kit_season"]
    assert "kit_season" not in screen.card_buttons
    icon = screen.chosen_card_buttons["kit_season"]
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=icon))
    assert screen.cruel_cards == []
    assert not screen.elements["next_step"].is_enabled


def test_random_card_and_paging_use_only_supported_compatible_cards(card_screen):
    import pygame
    import pygame_gui

    screen = card_screen
    press = lambda key: screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements[key]))
    assert screen.elements["card_next"].is_enabled
    press("card_next")
    assert screen.card_page == 1
    assert len(screen.card_buttons) == min(12, len(CARDS) - 12)
    press("card_previous")
    screen.apply_cruel_deck(["always_leaf-bare"])
    for _ in range(20):
        press("random_card")
        assert validate_cards(screen.cruel_cards) == screen.cruel_cards
        assert [name for name in screen.cruel_cards if name.startswith("always_")] == ["always_leaf-bare"]
    assert len(screen.cruel_cards) == min(CARD_DATA["limit"], len(CARDS) - 3)


def test_deck_entry_rejects_unknown_duplicate_conflicting_ids_without_mutation(card_screen):
    import pygame
    import pygame_gui
    from scripts.screens.CruelCards import DeckListWindow

    screen = card_screen
    screen.apply_cruel_deck(["kit_season"])
    window = DeckListWindow(screen.cruel_cards, screen.apply_cruel_deck)
    try:
        for text in ("unknown", "kit_season,kit_season", "always_newleaf,always_leaf-bare"):
            window.entry.set_text(text)
            window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.apply))
            assert screen.cruel_cards == ["kit_season"]
            assert window.error.html_text
        window.entry.set_text("resolute, lean_meat")
        window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.apply))
        assert screen.cruel_cards == ["resolute", "lean_meat"]
        assert game.clan.cruel_cards == screen.cruel_cards
    finally:
        window.kill()


def test_mode_and_naming_options_keep_selections(card_screen):
    import pygame
    import pygame_gui

    screen = card_screen
    screen.apply_cruel_deck(["resolute"])
    screen.open_game_settings()
    button = screen.elements["naming_options"]
    panel = screen.elements["mode_background"]
    assert button.text == "Pregame settings"
    assert panel.rect.contains(button.rect)
    assert abs(button.rect.centerx - panel.rect.centerx) <= 1
    assert button.rect.top > screen.elements["mode_description"].rect.bottom
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
    assert screen.sub_screen == "naming settings"
    assert screen.elements["instr"].html_text == "Pregame settings"
    before = game.clan.clan_settings["single_names"]
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.game_settings_checkboxes["single_names"]))
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["previous_step"]))
    assert screen.sub_screen == "game settings"
    assert game.clan.clan_settings["single_names"] is not before
    assert screen.game_mode == "cruel season"
    assert screen.cruel_cards == ["resolute"]


@pytest.mark.parametrize("cards", [None, [], ["lean_meat", "resolute"]])
def test_active_deck_viewer_is_read_only_and_handles_legacy_saves(colony, cards):
    import pygame
    import pygame_gui
    from scripts.screens.CruelCards import ViewCruelCards

    colony.cruel_cards = deepcopy(cards)
    before = deepcopy(colony.clan_settings)
    window = ViewCruelCards()
    try:
        if cards:
            window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_ON_HOVERED, ui_element=window.card_buttons["resolute"]))
            assert window.title.html_text == CARDS["resolute"]["name"]
        else:
            assert window.description.html_text
        assert colony.cruel_cards == cards
        assert colony.clan_settings == before
    finally:
        window.kill()


def test_card_mouse_click_posts_selection_event(card_screen):
    import pygame
    import pygame_gui

    card = card_screen.card_buttons["kit_season"]
    pygame.event.clear()
    point = (card.rect.left + 4, card.rect.centery)
    assert card.process_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=pygame.BUTTON_LEFT, pos=point))
    events = [event for event in pygame.event.get() if event.type == pygame_gui.UI_BUTTON_START_PRESS]
    assert len(events) == 1 and events[0].ui_element is card
    card_screen.handle_event(events[0])
    assert card_screen.cruel_cards == ["kit_season"]


def test_colony_settings_opens_active_deck_and_hides_entry_for_ordinary_modes(colony):
    import pygame
    import pygame_gui
    from scripts.screens.ClanSettingsScreen import ClanSettingsScreen

    screen = ClanSettingsScreen("deck_settings_test")
    with patch.object(game, "save_settings"):
        screen.screen_switches()
        try:
            assert screen.view_cards_button.visible
            with patch("scripts.screens.CruelCards.ViewCruelCards") as viewer:
                screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.view_cards_button))
                viewer.assert_called_once()
        finally:
            screen.exit_screen()
        colony.game_mode, colony.cruel_cards = "expanded", None
        screen.screen_switches()
        try:
            assert not screen.view_cards_button.visible
        finally:
            screen.exit_screen()


def test_card_pages_wrap_in_both_directions(card_screen):
    import pygame
    import pygame_gui

    screen = card_screen
    pages = (len(CARDS) + 11) // 12
    for key, expected in (("card_previous", pages - 1), ("card_next", 0), ("card_next", 1), ("card_next", 2 % pages)):
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements[key]))
        assert screen.card_page == expected


def test_raised_card_stays_below_deck_dialog_and_close_cleans_up(card_screen):
    import pygame
    import pygame_gui
    from scripts.screens.CruelCards import DeckListWindow

    card = card_screen.card_buttons["kit_season"]
    card.on_hovered()
    window = DeckListWindow([], card_screen.apply_cruel_deck)
    assert window.layer > card.layer
    assert window.box.layer > card.layer
    assert window.fade.layer > card.layer
    window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.back_button))
    assert not window.alive()
    assert not window.box.alive()
    assert not window.fade.alive()
    assert card_screen.cruel_cards == []


def test_setup_keyboard_navigation_preserves_deck_and_does_not_bypass_dialog(card_screen):
    import pygame
    from scripts.screens.CruelCards import DeckListWindow

    screen = card_screen
    with patch.dict(game.settings, {"keybinds": True}):
        # An empty deck cannot proceed, including through the keyboard shortcut.
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert screen.sub_screen == "cruel cards"
        screen.apply_cruel_deck(["kit_season"])
        assert screen.elements["card_info_container"].visible == 0
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        assert screen.sub_screen == "game settings", {
            "previous_enabled": screen.elements["previous_step"].is_enabled,
            "screen_manager": id(screen.handle_event.__globals__["MANAGER"]),
            "button_manager": id(screen.elements["previous_step"].ui_manager),
            "windows": [(type(w).__name__, w.is_blocking, w.alive()) for w in
                        screen.handle_event.__globals__["MANAGER"].get_window_stack().get_full_stack()],
        }
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert screen.sub_screen == "cruel cards"
        assert screen.cruel_cards == ["kit_season"]
        window = DeckListWindow(screen.cruel_cards, screen.apply_cruel_deck)
        try:
            screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            assert screen.sub_screen == "cruel cards"
            assert window.alive()
        finally:
            window.kill()
        screen.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        assert screen.sub_screen == "name clan"


def test_random_card_shows_details_without_a_prior_mouse_hover(card_screen):
    import pygame
    import pygame_gui

    screen = card_screen
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["random_card"]))
    chosen = screen.cruel_cards[0]
    assert screen.elements["card_info_container"].visible
    assert not screen.elements["card_error"].visible
    assert screen.elements["card_title"].html_text == CARDS[chosen]["name"]


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_mode_and_cards_precede_colony_editing_and_back_keeps_draft(card_screen, mode):
    import pygame
    import pygame_gui

    screen = card_screen
    screen.open_game_settings()
    def press(key):
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements[key]))
    press("mode_" + mode)
    screen.open_naming_settings()
    game.clan.clan_settings["single_names"] = True
    press("previous_step")
    press("next_step")
    if mode == "cruel season":
        assert screen.sub_screen == "cruel cards"
        screen.apply_cruel_deck(["always_leaf-bare"])
        press("next_step")
    assert screen.sub_screen == "name clan"
    draft = game.clan
    screen.elements["name_entry"].set_text("FlowTest")
    press("large")
    press("new")
    press("previous_step")
    assert screen.sub_screen == ("cruel cards" if mode == "cruel season" else "game settings")
    assert game.clan is draft
    assert game.clan.clan_settings["single_names"]
    press("next_step")
    assert screen.sub_screen == "name clan"
    assert screen.elements["name_entry"].get_text() == "FlowTest"
    assert not screen.elements["large"].is_enabled
    assert not screen.elements["new"].is_enabled
    screen.handle_name_clan_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert screen.sub_screen == "choose leader"
    assert game.clan.name == "FlowTest"
    assert game.clan.game_mode == mode
    assert game.choose_cats
    assert game.clan.clan_settings["single_names"]
    if mode == "cruel season":
        assert game.clan.cruel_cards == ["always_leaf-bare"]
    press("previous_step")
    assert screen.sub_screen == "name clan"
    assert screen.elements["name_entry"].get_text() == "FlowTest"



def test_quick_start_toggle_survives_pregame_settings_and_changes_next_route(card_screen):
    import pygame
    import pygame_gui

    screen = card_screen
    screen.open_game_settings()
    def press(key):
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements[key]))
    assert not screen.quick_start
    press("quick_start")
    press("naming_options")
    press("previous_step")
    assert screen.quick_start
    with patch.object(screen, "random_quick_start") as generate:
        press("next_step")
        generate.assert_called_once()
    press("quick_start")
    press("next_step")
    assert screen.sub_screen == "cruel cards"


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_quick_start_generates_newborn_with_draft_settings_and_supported_choices(card_screen, mode):
    from scripts.screens.MakeClanScreen import sprites

    screen = card_screen
    screen.game_mode = game.clan.game_mode = mode
    game.clan.cruel_cards = [] if mode == "cruel season" else None
    game.clan.clan_settings["single_names"] = True
    game.clan.clan_settings["leader_life_default"] = True
    settings_before = deepcopy(game.clan.clan_settings)
    with patch.object(sprites, "clan_symbols", ["symbolBEECH0"]), patch.object(screen, "save_clan") as save, patch.object(screen, "open_clan_saved_screen") as welcome:
        screen.random_quick_start()
    save.assert_called_once()
    welcome.assert_called_once()
    assert screen.your_cat.status == "kitten"
    assert screen.your_cat in Cat.all_cats_list
    assert screen.clan_name and screen.generated_clan_prefix
    assert game.clan.name == screen.clan_name
    assert screen.symbol_selected == "symbolBEECH0"
    assert screen.biome_selected in screen.camp_counts
    assert 1 <= screen.selected_camp_tab <= screen.camp_counts[screen.biome_selected]
    assert game.clan.clan_settings == settings_before
    if mode == "cruel season":
        assert 3 <= len(screen.cruel_cards) <= 8
        assert validate_cards(screen.cruel_cards) == screen.cruel_cards
        assert game.clan.cruel_cards == screen.cruel_cards
    else:
        assert game.clan.cruel_cards is None


@pytest.mark.parametrize("food_card", ["lean_meat", "crowfood"])
def test_quick_start_keeps_chosen_cards_and_forced_starting_season(card_screen, food_card):
    from scripts.screens.MakeClanScreen import sprites

    screen = card_screen
    screen.apply_cruel_deck(["always_leaf-bare", food_card])
    with patch.object(sprites, "clan_symbols", ["symbolBEECH0"]), patch.object(screen, "save_clan"), patch.object(screen, "open_clan_saved_screen"):
        screen.random_quick_start()
    assert screen.cruel_cards == ["always_leaf-bare", food_card]
    assert screen.selected_season == "Leaf-bare"


@pytest.mark.parametrize("size,count", [("small", 10), ("medium", 15), ("large", 20)])
def test_member_generation_guarantees_officials_and_discards_kitten_candidates(card_screen, size, count):
    import random
    from scripts.cat.cats import create_example_cats

    screen = card_screen
    screen.clan_size = size
    create_example_cats()
    screen.your_cat = game.choose_cats[11]
    screen.leader = screen.deputy = screen.med_cat = None
    screen.members = []
    with patch("scripts.screens.MakeClanScreen.random.sample", wraps=random.sample) as sample:
        screen.handle_create_other_cats()
    assert sample.call_args_list[0].args == (range(count), 3)
    assert len(game.choose_cats) == count
    assert screen.leader and screen.deputy and screen.med_cat
    assert len({cat.ID for cat in (screen.leader, screen.deputy, screen.med_cat)}) == 3
    assert sum(cat is screen.your_cat for cat in screen.members) == 1
    assert len({cat.ID for cat in screen.members}) == len(screen.members)


@pytest.mark.parametrize("biome", ["Forest", "Mountainous", "Plains", "Beach"])
def test_camp_keyboard_uses_available_camps_and_enter_goes_to_symbols(card_screen, biome):
    import pygame

    screen = card_screen
    screen.biome_selected = biome
    screen.selected_camp_tab = screen.camp_counts[biome] - 1
    with patch.object(screen, "refresh_selected_camp"):
        screen.handle_choose_background_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        assert screen.selected_camp_tab == screen.camp_counts[biome]
        screen.handle_choose_background_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
        assert screen.selected_camp_tab == screen.camp_counts[biome]
    with patch.object(screen, "save_clan") as save, patch.object(screen, "open_choose_symbol") as symbols:
        screen.handle_choose_background_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        symbols.assert_called_once()
        save.assert_not_called()


def test_enabling_quick_start_then_cancelling_does_not_save_or_generate(card_screen):
    import pygame
    import pygame_gui

    screen = card_screen
    original = screen.previous_clan
    original_settings = deepcopy(original.clan_settings)
    screen.open_game_settings()
    with patch.object(screen, "save_clan") as save, patch.object(screen, "random_quick_start") as generate, patch.object(screen, "change_screen") as leave:
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["quick_start"]))
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.main_menu))
        leave.assert_called_once_with("start screen")
        save.assert_not_called()
        generate.assert_not_called()
    assert original.clan_settings == original_settings


@pytest.mark.parametrize("cards,initial,reward,expected", [(["enmity"], 7, 5, "unchanged"),
    (["enmity"], 6, 5, "improved"), (["public_enemy"], 7, 5, "improved"), ([], 0, -5, "unchanged")])
def test_diplomacy_reports_the_actual_capped_relationship_change(colony, monkeypatch, cards, initial, reward, expected):
    from scripts.events import Events
    from scripts.events_module.generate_events import generate_events

    colony.cruel_cards = cards
    leader = Cat(status="leader", moons=40)
    colony.leader = leader
    colony.add_cat(leader)
    neighbor = OtherClan(name="Neighbor", relations=initial, chosen_symbol="symbolBEECH0")
    colony.all_clans = [neighbor]
    colony.clan_settings["lead_den_clan_event"] = {"cat_ID": leader.ID, "other_clan": neighbor.name,
        "player_clan_temper": "mellow", "interaction_type": "befriend", "success": True}
    colony.clan_settings["lead_den_outsider_event"] = {}
    monkeypatch.setattr(game, "cur_events_list", [])
    monkeypatch.setattr(generate_events, "possible_lead_den_events", lambda **kwargs: [
        {"event_text": "m_c visits o_c_n.", "rel_change": reward}])
    Events().handle_lead_den_event()
    assert f"relations {expected}." in game.cur_events_list[-1].text
    assert neighbor.relations == max(0, min(7 if "enmity" in cards else 30, initial + reward))


@pytest.mark.parametrize("tier,multiplier", [(0, 1), (1, 1.5), (2, 1.75), (3, 2)])
@pytest.mark.parametrize("burnout", [False, True])
def test_burnout_reaches_real_medical_coverage_with_healing_skills(colony, burnout, tier, multiplier):
    from scripts.cat.skills import Skill, SkillPath
    from scripts.conditions import get_amount_cat_for_one_medic, medical_cats_condition_fulfilled

    colony.cruel_cards = ["burnout"] if burnout else []
    med = Cat(status="medicine cat", moons=40)
    med.experience = 0
    med.skills.primary = Skill(SkillPath.HEALER if tier else SkillPath.HUNTER, Skill.tier_ranges[tier - 1][0] if tier else 0)
    med.skills.secondary = None
    patients = [Cat(status="warrior", moons=40) for _ in range(10)]
    capacity = get_amount_cat_for_one_medic(colony)
    assert capacity == (5 if burnout else 10)
    covered = medical_cats_condition_fulfilled([med] + patients, capacity, give_clanmembers_covered=True)
    assert covered == int(multiplier * (capacity + 1))
    ordinary = Clan(name="Other", game_mode="expanded")
    assert get_amount_cat_for_one_medic(ordinary) == 10


@pytest.mark.parametrize("name", ["whitecough", "tick fever", "breathless fit"])
@pytest.mark.parametrize("medicated", [False, True])
def test_longer_illnesses_doubles_actual_acquisition_without_changing_injuries(colony, monkeypatch, name, medicated):
    from scripts.cat.cats import ILLNESSES

    monkeypatch.setattr(game, "cat_class", Cat)
    patient = Cat(status="warrior", moons=40)
    colony.add_cat(patient)
    if medicated:
        medic = Cat(status="medicine cat", moons=40)
        colony.add_cat(medic)
    with patch("scripts.cat.cats.randrange", return_value=0):
        patient.get_ill(name)
        before = patient.illnesses[name]["duration"]
        patient.illnesses.clear()
        colony.cruel_cards = ["longer_illnesses"]
        patient.get_ill(name)
        assert patient.illnesses[name]["duration"] == before * 2
        patient.get_injured("claw-wound")
        injury_duration = patient.injuries["claw-wound"]["duration"]
        patient.injuries.clear()
        colony.cruel_cards = []
        patient.get_injured("claw-wound")
        assert patient.injuries["claw-wound"]["duration"] == injury_duration
    assert ILLNESSES[name]["duration"] >= 1


@pytest.mark.parametrize("season", ["Newleaf", "Greenleaf", "Leaf-fall", "Leaf-bare"])
def test_plague_outbreaks_reach_all_seasons_and_bypass_medical_prevention(colony, monkeypatch, season):
    from scripts.events import Events

    monkeypatch.setattr(game, "cur_events_list", [])
    colony.current_season = season
    source = Cat(status="warrior", moons=40)
    medic = Cat(status="medicine cat", moons=40)
    healthy = [Cat(status="warrior", moons=40) for _ in range(8)]
    for cat in [source, medic] + healthy:
        colony.add_cat(cat)
    source.get_ill("whitecough")
    rate = source.illnesses["whitecough"]["infectiousness"]
    # This roll fails with one medic's normal protection, but succeeds without it.
    roll = 1 / (rate + 1)
    event = Events()
    with patch("scripts.events.random.random", return_value=roll), patch(
            "scripts.events.random.choices", return_value=[2]):
        event.handle_outbreaks(source)
        assert sum(cat.is_ill() for cat in Cat.all_cats.values()) == 1
        colony.cruel_cards = ["plague_ridden"]
        event.handle_outbreaks(source)
    assert sum(cat.is_ill() for cat in Cat.all_cats.values()) == 3
    assert len(game.cur_events_list) == 1


def test_plague_changes_outbreak_saturation_without_altering_default(colony, monkeypatch):
    from scripts.events import Events

    monkeypatch.setattr(game, "cur_events_list", [])
    colony.current_season = "Leaf-bare"
    cats = [Cat(status="warrior", moons=40) for _ in range(12)]
    for cat in cats:
        colony.add_cat(cat)
    for cat in cats[:4]:
        cat.get_ill("whitecough")
    event = Events()
    with patch("scripts.events.random.random", return_value=0), patch(
            "scripts.events.random.choices", return_value=[2]):
        event.handle_outbreaks(cats[0])
        assert sum(cat.is_ill() for cat in cats) == 4
        colony.cruel_cards = ["plague_ridden"]
        event.handle_outbreaks(cats[0])
    assert sum(cat.is_ill() for cat in cats) == 6



@pytest.mark.parametrize("card", ["burnout", "plague_ridden", "longer_illnesses", "mouths_to_feed", "underpopulated", "clumsy_paws", "survival_of_fittest"])
def test_new_cards_are_selected_through_actual_card_controls(card_screen, card):
    import pygame
    import pygame_gui

    available = list(CARDS)
    card_screen.card_page = available.index(card) // 12
    card_screen.refresh_cruel_cards()
    card_screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
        ui_element=card_screen.card_buttons[card]))
    assert card_screen.cruel_cards == game.clan.cruel_cards == [card]
    assert card in card_screen.chosen_card_buttons
    assert card_screen.elements["next_step"].is_enabled
    card_screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
        ui_element=card_screen.elements["next_step"]))
    assert card_screen.sub_screen == "name clan"
    assert game.clan.cruel_cards == [card]


def test_longer_illnesses_still_respond_to_herb_treatment(colony, monkeypatch):
    from scripts.cat.cats import ILLNESSES
    from scripts.events_module.short.condition_events import Condition_Events

    monkeypatch.setattr(game, "herb_events_list", [])
    colony.cruel_cards = ["longer_illnesses"]
    patient = Cat(status="warrior", moons=40)
    colony.add_cat(patient)
    patient.get_ill("tick fever", lethal=False)
    before = patient.illnesses["tick fever"]["duration"]
    colony.herbs = {"goldenrod": 1}
    with patch("scripts.events_module.short.condition_events.random.choice", return_value="duration"):
        Condition_Events.use_herbs(patient, "tick fever", patient.illnesses.copy(), ILLNESSES)
    assert patient.illnesses["tick fever"]["duration"] == max(0, before - 3)
    assert "goldenrod" not in colony.herbs


@pytest.mark.parametrize("cards,relations,help_text", [(["enmity"], 7, "Enmity"),
    (["public_enemy"], 7, None), ([], 30, "maximum")])
def test_leader_den_explains_relationship_caps_in_the_actual_panel(colony, monkeypatch, cards, relations, help_text):
    import pygame
    from scripts.screens.LeaderDenScreen import LeaderDenScreen

    monkeypatch.setattr("scripts.utility.generate_sprite", lambda *args, **kwargs: pygame.Surface((50, 50), pygame.SRCALPHA))
    monkeypatch.setattr("scripts.screens.LeaderDenScreen.clan_symbol_sprite", lambda *args, **kwargs: pygame.Surface((50, 50), pygame.SRCALPHA))
    colony.cruel_cards = cards
    leader = Cat(status="leader", moons=40)
    colony.leader = colony.your_cat = leader
    colony.add_cat(leader)
    neighbor = OtherClan(name="Neighbor", relations=relations, chosen_symbol="symbolBEECH0")
    colony.all_clans = [neighbor]
    screen = LeaderDenScreen("cruel_diplomacy_test")
    screen.screen_switches()
    try:
        screen.focus_clan = neighbor
        screen.update_other_clan_focus()
        tooltip = screen.focus_frame_elements["positive_interaction"].tool_tip_text
        assert (help_text in tooltip) if help_text else not tooltip
        assert screen.focus_clan_elements["clan_rel"].text == ("hostile" if relations == 7 else "ally")
    finally:
        screen.exit_screen()


LITTER_WEIGHTS = {
    "mouths_to_feed": [(0, 2, 9, 17, 15, 12), (4, 5, 11, 16, 7, 3), (4, 5, 8, 8, 5, 2), (2, 2, 3, 1, 0, 0)],
    "underpopulated": [(12, 11, 17, 7, 1, 1), (10, 14, 15, 4, 2, 0), (11, 16, 5, 2, 0, 0), (5, 4, 1, 0, 0, 0)],
}


@pytest.mark.parametrize("card", LITTER_WEIGHTS)
@pytest.mark.parametrize("age_index,moons", [(0, 20), (1, 50), (2, 100), (3, 130)])
@pytest.mark.parametrize("larger", [False, True])
def test_litter_cards_reach_the_actual_sampler_with_source_probabilities(colony, card, age_index, moons, larger):
    from collections import Counter

    colony.cruel_cards = [card]
    colony.clan_settings["bigger_litters"] = larger
    parent = Cat(status="warrior", moons=moons)
    populations = []
    def choose(values):
        populations.append(list(values))
        return values[-1]
    with patch("scripts.events_module.relationship.pregnancy_events.choice", side_effect=choose):
        Pregnancy_Events.get_amount_of_kits(parent)
    counts = Counter(populations[-1])
    actual = [counts[n] for n in range(1, 6)] + [sum(count for n, count in counts.items() if n >= 6)]
    expected = LITTER_WEIGHTS[card][age_index]
    for index in range(6):
        assert actual[index] * sum(expected) == expected[index] * sum(actual)
    assert max(counts) <= (12 if larger else 6)
    if larger and expected[-1]:
        assert 12 in counts
    assert game.config["pregnancy"]["one_kit_modded"]["young adult"] == 64


@pytest.mark.parametrize("card", [None, "mouths_to_feed", "underpopulated"])
@pytest.mark.parametrize("larger", [False, True])
def test_litter_cards_create_real_biological_and_adopted_litters(colony, monkeypatch, tmp_path, card, larger):
    colony.cruel_cards = [card] if card else []
    colony.clan_settings["bigger_litters"] = larger
    for module in ("scripts.cat.cats", "scripts.clan", "scripts.game_structure.game_essentials"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    parents = [Cat(status="warrior", moons=40, gender=gender) for gender in ("female", "male")]
    for cat in parents:
        cat.history = History()
        colony.add_cat(cat)
        cat.create_inheritance_new_cat()
    colony.your_cat = parents[0]
    with patch("scripts.events_module.relationship.pregnancy_events.choice", side_effect=lambda values: max(values)):
        count = Pregnancy_Events.get_amount_of_kits(parents[0])
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=.99), patch(
            "scripts.events_module.relationship.pregnancy_events.random.randrange", return_value=0):
        kittens = Pregnancy_Events.get_kits(count, *parents, clan=colony)
        adopted = Pregnancy_Events.get_kits(count, clan=colony, adoptive_parents=[parent.ID for parent in parents])
    assert len(kittens) == len(adopted) == count
    assert all(kit.parent1 == parents[0].ID and kit.parent2 == parents[1].ID for kit in kittens)
    assert all(set(kit.adoptive_parents) == {parent.ID for parent in parents} for kit in adopted)
    game.save_cats()


@pytest.mark.parametrize("roll", [0, .99])
def test_clumsy_paws_uses_the_source_curve_and_keeps_small_gains_possible(colony, roll):
    import math
    from scripts.cat.skills import Skill, SkillPath

    colony.cruel_cards = ["clumsy_paws"]
    cat = Cat(status="warrior", moons=40)
    ceiling = cat.experience_levels_range["master"][1]
    cat.experience = int(ceiling * .75)
    initial = cat.experience
    scaled = 10 * math.sqrt(1 - initial / ceiling)
    expected = int(scaled) + (roll < scaled % 1)
    with patch("scripts.cat.cats.random", return_value=roll):
        cat.add_experience(10)
    assert cat.experience == initial + expected
    skill = Skill(SkillPath.HUNTER, 28)
    with patch("scripts.cat.skills.random.random", return_value=roll):
        gain = skill.add_points(1)
    assert gain == (1 if roll == 0 else 0)
    assert skill.points == 28 + gain
    cat.experience = 200
    skill.points = 20
    assert cat.experience == 200 and skill.points == 20


@pytest.mark.parametrize("cards", [None, []])
def test_normal_learning_keeps_existing_rounding_and_does_not_draw_extra_randomness(colony, cards):
    from scripts.cat.skills import Skill, SkillPath

    colony.cruel_cards = cards
    cat = Cat(status="warrior", moons=40)
    cat.experience = 100
    skill = Skill(SkillPath.HUNTER, 10)
    with patch("scripts.cat.cats.random", side_effect=AssertionError("Unmodified learning must not roll")), patch(
            "scripts.cat.skills.random.random", side_effect=AssertionError("Unmodified learning must not roll")):
        cat.add_experience(1.75)
        skill.add_points(2)
    assert cat.experience == 101 and skill.points == 12


@pytest.mark.parametrize("roll,expected", [(0, 1), (.99, 0)])
def test_mentor_influence_records_actual_clumsy_paws_progress(colony, roll, expected):
    from scripts.cat.skills import Skill, SkillPath

    colony.cruel_cards = ["clumsy_paws"]
    mentor = Cat(status="warrior", moons=40)
    apprentice = Cat(status="apprentice", moons=8)
    mentor.skills.primary = Skill(SkillPath.HUNTER, 29)
    apprentice.skills.primary = Skill(SkillPath.HUNTER, 28)
    apprentice.skills.secondary = None
    with patch("scripts.cat.skills.random.randint", return_value=1), patch(
            "scripts.cat.skills.random.random", return_value=roll):
        result = apprentice.skills.mentor_influence(mentor)
    assert result == (mentor.ID, SkillPath.HUNTER, expected)
    assert apprentice.skills.primary.points == 28 + expected


@pytest.mark.parametrize("cards,mode,expected", [([], "cruel season", True),
    (None, "cruel season", False), (None, "expanded", True)])
def test_card_patrol_success_uses_expanded_base_while_legacy_cruel_is_preserved(colony, monkeypatch, cards, mode, expected):
    from scripts.events_module.patrol.patrol import Patrol
    from scripts.events_module.patrol.patrol_event import PatrolEvent
    from scripts.events_module.patrol.patrol_outcome import PatrolOutcome

    colony.game_mode, colony.cruel_cards = mode, cards
    cat = Cat(status="warrior", moons=40)
    cat.experience = 100
    colony.add_cat(cat)
    patrol = Patrol()
    patrol.add_patrol_cats([cat], colony)
    patrol.patrol_type = "training"
    patrol.patrol_event = PatrolEvent("difficulty_check", chance_of_success=10)
    monkeypatch.setitem(game.switches, "patrol_category", "general")
    with patch.dict(game.config["patrol_generation"], {"debug_ensure_patrol_outcome": None}), patch(
            "scripts.events_module.patrol.patrol.random.random", return_value=.25):
        _, success = patrol.calculate_success(PatrolOutcome(), PatrolOutcome(success=False))
    assert success is expected


@pytest.mark.parametrize("apprentice", [False, True])
def test_clumsy_paws_reaches_actual_patrol_experience_rewards(colony, apprentice):
    from scripts.events_module.patrol.patrol import Patrol
    from scripts.events_module.patrol.patrol_outcome import PatrolOutcome

    cat = Cat(status="apprentice" if apprentice else "warrior", moons=8 if apprentice else 40)
    cat.experience = 100
    colony.add_cat(cat)
    patrol = Patrol()
    patrol.add_patrol_cats([cat], colony)
    outcome = PatrolOutcome(exp=20)
    with patch("scripts.events_module.patrol.patrol_outcome.random.randint", return_value=7):
        outcome._handle_exp(patrol)
    ordinary = cat.experience - 100
    cat.experience = 100
    colony.cruel_cards = ["clumsy_paws"]
    with patch("scripts.events_module.patrol.patrol_outcome.random.randint", return_value=7), patch(
            "scripts.cat.cats.random", return_value=.99):
        outcome._handle_exp(patrol)
    assert 0 < cat.experience - 100 < ordinary


@pytest.mark.parametrize("outside", [False, True])
def test_clumsy_paws_reaches_monthly_apprentice_and_outside_experience(colony, outside):
    from scripts.events import Events

    cat = Cat(status="loner" if outside else "apprentice", moons=40 if outside else 8)
    cat.outside = outside
    cat.experience = 20
    event = Events()
    train = event.handle_outside_EX if outside else event.handle_apprentice_EX
    with patch("scripts.events.random.choice", return_value=10):
        train(cat)
    ordinary = cat.experience - 20
    cat.experience = 20
    colony.cruel_cards = ["clumsy_paws"]
    with patch("scripts.events.random.choice", return_value=10), patch("scripts.cat.cats.random", return_value=.99):
        train(cat)
    assert cat.experience - 20 < ordinary


@pytest.mark.parametrize("cards,expected", [([], 29), (["clumsy_paws"], 28)])
def test_clumsy_paws_reaches_monthly_adult_skill_progress(colony, cards, expected):
    from scripts.cat.skills import Skill, SkillPath

    colony.cruel_cards = cards
    cat = Cat(status="warrior", moons=40)
    cat.skills.primary = Skill(SkillPath.HUNTER, 28)
    cat.skills.secondary = Skill(SkillPath.RUNNER, 10)
    with patch("scripts.cat.skills.random.random", side_effect=[0, .99] if cards else [0]):
        cat.skills.progress_skill(cat)
    assert cat.skills.primary.points == expected



def test_survival_of_fittest_enforces_automatic_priority_and_blocks_manual_backend(colony):
    from scripts.cat.skills import Skill, SkillPath

    colony.cruel_cards = ["survival_of_fittest"]
    colony.clan_settings["feeding priorities"] = ["by-status"]
    cats = [Cat(status="warrior", moons=40) for _ in range(4)]
    for index, cat in enumerate(cats):
        colony.add_cat(cat)
        cat.skills.primary = Skill(SkillPath.HUNTER if index < 2 else SkillPath.RUNNER, 10)
        cat.skills.secondary = None
        cat.experience = (10, 30, 300, 0)[index]
    pile = colony.freshkill_pile
    pile.living_cats = cats
    pile.update_nutrition(cats)
    for info in pile.nutrition_info.values():
        info.current_score = 0
    pile.pile = dict.fromkeys(pile.pile, 0)
    pile.total_amount = 0
    pile.add_freshkill(4)
    before = {cat_id: info.current_score for cat_id, info in pile.nutrition_info.items()}
    pile.feed_cats(cats, additional_food_round=True)
    pile.feed_cat(cats[3], 1, 0, manual=True)
    assert pile.total_amount == 4
    assert before == {cat_id: info.current_score for cat_id, info in pile.nutrition_info.items()}
    assert not pile.already_fed
    assert pile.get_feeding_priorities() == ["hunter first", "more experience first"]
    pile.feed_cats(cats)
    assert [cat.ID for cat in pile.already_fed[:2]] == [cats[1].ID, cats[0].ID]
    assert pile.total_amount < 4
    assert colony.clan_settings["feeding priorities"] == ["by-status"]
    colony.cruel_cards = []
    assert pile.get_feeding_priorities() == ["by-status"]
    assert pile.manual_feeding_allowed and not pile.feeding_locked


@pytest.mark.parametrize("card,grant", [("weak_stars", 1), ("weak_stars", 3), ("weak_stars", 5), ("forsaken", 1)])
@pytest.mark.parametrize("override", [None, False, True])
def test_leader_card_grants_are_rolled_once_and_settings_never_increase_them(colony, card, grant, override):
    colony.cruel_cards = [card]
    leader = Cat(status="leader", moons=40)
    colony.leader = leader
    leader.leader_life_override = override
    with patch("scripts.clan.randint", return_value=grant) as roll:
        colony.reset_leader_lives()
        if card == "weak_stars":
            roll.assert_called_once_with(1, 5)
        else:
            roll.assert_not_called()
        for _ in range(3):
            colony.apply_leader_life_limit()
            assert colony.get_starting_leader_lives(leader) == (1 if override else grant)
    assert colony.leader_lives_granted == colony.leader_lives_reserve == grant
    assert colony.leader_lives == (1 if override else grant)
    leader.leader_life_override = False
    colony.apply_leader_life_limit()
    assert colony.leader_lives == grant
    colony.clan_settings["leader_life_default"] = True
    leader.leader_life_override = None
    colony.apply_leader_life_limit()
    assert colony.leader_lives == 1
    colony.clan_settings["leader_life_default"] = False
    colony.apply_leader_life_limit()
    assert colony.leader_lives == grant


@pytest.mark.parametrize("card,grant", [("weak_stars", 4), ("forsaken", 1)])
def test_leader_card_death_revival_command_and_successor_keep_separate_balances(colony, monkeypatch, card, grant):
    from scripts.debug_commands.return_cat import ReturnCatCommand

    colony.cruel_cards = [card]
    leader = Cat(status="leader", moons=40)
    leader.history = History()
    colony.leader = colony.your_cat = leader
    colony.add_cat(leader)
    with patch("scripts.clan.randint", return_value=grant):
        colony.reset_leader_lives()
    History.add_death(leader, "died in battle")
    assert leader.history.died_by[-1]["leader_life_mode"] == grant
    colony.leader_lives = 0
    leader.dead = True
    with patch.object(Cat, "add_to_clan"), patch("scripts.debug_commands.return_cat.add_output_line_to_log"):
        ReturnCatCommand().callback([leader.ID])
    assert not leader.dead and colony.leader is leader
    assert colony.leader_lives == 1
    assert colony.leader_lives_reserve == 0
    for override in (True, False, None):
        leader.leader_life_override = override
        colony.apply_leader_life_limit()
        assert colony.leader_lives == 1 and colony.leader_lives_reserve == 0
    successor = Cat(status="deputy", moons=35)
    successor.history = History()
    monkeypatch.setattr(colony.history, "add_lead_ceremony", Mock())
    with patch("scripts.clan.randint", return_value=grant):
        colony.new_leader(successor)
    assert colony.leader is successor
    assert colony.leader_lives == colony.leader_lives_reserve == colony.leader_lives_granted == grant


@pytest.mark.parametrize("lives", [1, 3, 5, 9])
@pytest.mark.parametrize("following", [True, False, None])
@pytest.mark.parametrize("known_givers", [False, True])
def test_leader_ceremony_blessings_match_saved_grant(colony, monkeypatch, lives, following, known_givers):
    leader = Cat(status="leader", moons=40)
    leader.history = History()
    colony.leader = colony.your_cat = leader
    colony.followingsc = following
    colony.leader_lives_granted = colony.leader_lives = lives
    givers = []
    if known_givers:
        for index in range(12):
            cat = Cat(status="leader" if index == 0 else "warrior", moons=40)
            cat.dead = True
            givers.append(cat.ID)
            leader.create_one_relationship(cat)
    colony.starclan_cats = colony.darkforest_cats = colony.unknown_cats = givers
    calls = []
    def adjust(cls, text, leader, life_giver=None, virtue=None, extra_lives=None):
        calls.append((life_giver, extra_lives))
        return text
    monkeypatch.setattr("scripts.cat.cats.leader_ceremony_text_adjust", adjust)
    ceremony = leader.generate_lead_ceremony()
    # Intro and outro surround individual gifts and, when needed, the remaining anonymous lives.
    blessings = calls[1:-1]
    assert sum(int(extra) if extra else 1 for giver, extra in blessings) == lives
    assert all(not extra or int(extra) > 0 for giver, extra in blessings)
    assert ceremony


@pytest.mark.parametrize("lives", [1, 3, 9])
def test_ceremony_text_renders_life_totals_and_singular_gifts(colony, lives):
    from scripts.utility import leader_ceremony_text_adjust

    leader = Cat(status="leader", moons=40)
    colony.leader_lives_granted = lives
    text = leader_ceremony_text_adjust(
        Cat, "[total_lives] lives; remaining [life_num] lives. Use [life_pronoun] well.",
        leader, extra_lives=str(lives))
    assert text == ("1 life; remaining 1 life. Use it well." if lives == 1 else
                    f"{'nine' if lives == 9 else lives} lives; remaining {lives} lives. Use them well.")


@pytest.mark.parametrize("card,grant", [("weak_stars", 3), ("forsaken", 1)])
def test_personal_life_checkbox_obeys_card_grant(colony, card, grant):
    import pygame
    import pygame_gui
    from scripts.game_structure.windows import ChangeCatToggles

    colony.cruel_cards = [card]
    leader = Cat(status="leader", moons=40)
    colony.leader = colony.your_cat = leader
    leader.leader_life_override = False
    with patch("scripts.clan.randint", return_value=grant):
        colony.reset_leader_lives()
    window = ChangeCatToggles(leader)
    try:
        for expected in (1, grant, 1, grant):
            checkbox = window.checkboxes["leader_life_override"]
            assert "grant" in checkbox.tool_tip_text
            window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=checkbox))
            assert colony.leader_lives == expected
            assert colony.leader_lives_granted == colony.leader_lives_reserve == grant
    finally:
        window.kill()


@pytest.mark.parametrize("cards,lifetime", [(None, 4), ([], 4), (["crowfood"], 1), (["crowfood", "lean_meat"], 1)])
def test_prey_expiry_card_reaches_initial_stock_additions_and_actual_timeskip(colony, cards, lifetime):
    from scripts.clan_resources.freshkill import FreshkillPile

    colony.cruel_cards = cards
    pile = FreshkillPile(start_amount=8)
    assert pile.pile[f"expires_in_{lifetime}"] == 8
    pile.add_freshkill(2.5)
    pile.remove_freshkill(1.25)
    assert pile.total_amount == 9.25
    logs = []
    for moon in range(1, lifetime + 1):
        pile.time_skip([], logs)
        assert pile.total_amount == (9.25 if moon < lifetime else 0)
    assert any("9.25 pieces were removed" in line for line in logs)
    assert sum(pile.pile.values()) == pile.total_amount


def test_crowfood_starting_expiry_uses_own_colony_cards(colony):
    colony.cruel_cards = ["crowfood"]
    ordinary = Clan(name="Ordinary", game_mode="expanded")
    assert ordinary.freshkill_pile.pile["expires_in_4"] == game.prey_config["start_amount"]
    colony.cruel_cards = []
    selected = Clan(name="Selected", game_mode="cruel season", cruel_cards=["crowfood"])
    assert selected.freshkill_pile.pile["expires_in_1"] == game.prey_config["start_amount"]
    assert selected.freshkill_pile.pile["expires_in_4"] == 0


@pytest.mark.parametrize("cards", [["crowfood"], ["crowfood", "lean_meat"]])
def test_crowfood_preserves_manual_meals_but_rot_precedes_automatic_feeding(colony, cards):
    from scripts.clan_resources.freshkill import FreshkillPile

    colony.cruel_cards = cards
    cat = Cat(status="warrior", moons=40)
    colony.add_cat(cat)
    pile = colony.freshkill_pile = FreshkillPile(start_amount=30)
    pile.living_cats = [cat]
    pile.update_nutrition([cat])
    info = pile.nutrition_info[cat.ID]
    info.current_score = 0
    pile._update_needed_food([cat])
    assert pile.manual_feeding_allowed
    pile.feed_cats([cat], additional_food_round=True)
    manually_fed = pile.nutrition_info[cat.ID].current_score
    assert manually_fed > 0
    remaining = pile.total_amount
    logs = []
    pile.time_skip([cat], logs)
    assert pile.total_amount == 0
    assert pile.nutrition_info[cat.ID].current_score == max(0, manually_fed - pile.prey_requirement["warrior"])
    assert any(f"{remaining:g} pieces were removed" in line for line in logs)
    assert "0 pieces of prey were consumed." in logs


@pytest.mark.parametrize("writer", ["patrol", "focus", "monthly", "event"])
def test_crowfood_receives_prey_from_real_gameplay_writers(colony, monkeypatch, writer):
    from scripts.clan_resources.freshkill import FreshkillPile
    from scripts.events import Events
    from scripts.events_module.patrol.patrol import Patrol
    from scripts.events_module.patrol.patrol_outcome import PatrolOutcome
    from scripts.events_module.short.handle_short_events import HandleShortEvents

    colony.cruel_cards = ["crowfood"]
    hunter = Cat(status="warrior", moons=40)
    colony.add_cat(hunter)
    monkeypatch.setattr(game, "freshkill_event_list", [])
    monkeypatch.setattr(game, "cur_events_list", [])
    pile = colony.freshkill_pile = FreshkillPile(start_amount=0)
    events = Events()
    if writer == "patrol":
        patrol = Patrol()
        patrol.add_patrol_cats([hunter], colony)
        assert PatrolOutcome(prey=["medium"])._handle_prey(patrol)
    elif writer == "focus":
        colony.clan_settings["business as usual"] = False
        colony.clan_settings["rest and recover"] = False
        colony.clan_settings["hunting"] = True
        with patch.object(events, "apply_relation_decay"):
            events.handle_focus()
    elif writer == "monthly":
        events.get_moon_freshkill()
    else:
        HandleShortEvents().handle_freshkill_supply({"adjust": "increase_5"}, pile)
    assert pile.total_amount > 0
    assert pile.pile["expires_in_1"] == pile.total_amount
    assert pile.pile["expires_in_4"] == 0


@pytest.mark.parametrize("adjust,expected", [("increase_5", 21), ("reduce_eighth", 14)])
def test_prey_events_add_numeric_amounts_and_losses_do_not_increase_stock(colony, adjust, expected):
    from scripts.clan_resources.freshkill import FreshkillPile
    from scripts.events_module.short.handle_short_events import HandleShortEvents

    pile = FreshkillPile(start_amount=16)
    HandleShortEvents().handle_freshkill_supply({"adjust": adjust}, pile)
    assert pile.total_amount == expected
    assert sum(pile.pile.values()) == expected


def test_crowfood_loading_keeps_saved_remaining_ages(colony):
    from scripts.clan_resources.freshkill import FreshkillPile

    colony.cruel_cards = ["crowfood"]
    saved = {"expires_in_4": 4, "expires_in_3": 3, "expires_in_2": 2, "expires_in_1": 1}
    pile = FreshkillPile(saved.copy())
    assert pile.pile == saved and pile.total_amount == 10
    pile.add_freshkill(.5)
    assert pile.pile == {**saved, "expires_in_1": 1.5}
    pile.time_skip([], [])
    assert pile.pile == {"expires_in_4": 0, "expires_in_3": 4, "expires_in_2": 3, "expires_in_1": 2}
    assert pile.total_amount == 9


def test_crowfood_conflict_is_explained_and_rejected_without_changing_the_deck(card_screen):
    import pygame
    import pygame_gui
    from scripts.screens.CruelCards import DeckListWindow

    screen = card_screen
    screen.apply_cruel_deck(["survival_of_fittest"])
    available = [card for card in CARDS if card not in screen.cruel_cards]
    screen.card_page = available.index("crowfood") // 12
    screen.refresh_cruel_cards()
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.card_buttons["crowfood"]))
    assert screen.cruel_cards == ["survival_of_fittest"]
    from scripts.screens.CruelCards import CruelCardConflicts
    from scripts.game_structure.screen_settings import MANAGER
    conflict = next(w for w in MANAGER.get_window_stack().get_full_stack() if isinstance(w, CruelCardConflicts))
    assert "Crowfood Chaos" in conflict.message.html_text
    assert "Survival of the Fittest" in conflict.message.html_text
    conflict.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=conflict.keep_button))
    with patch("scripts.screens.MakeClanScreen.choice", side_effect=lambda choices: choices[0]) as choose:
        screen.random_cruel_card()
        assert "crowfood" not in choose.call_args.args[0]
    window = DeckListWindow(screen.cruel_cards, screen.apply_cruel_deck)
    try:
        window.entry.set_text("survival_of_fittest, crowfood")
        window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.apply))
        assert "Crowfood Chaos" in window.error.html_text
        assert screen.cruel_cards == ["survival_of_fittest"]
    finally:
        window.kill()
    assert "manually" in CARDS["crowfood"]["description"]
    assert "Survival of the Fittest" in CARDS["crowfood"]["description"]


@pytest.mark.parametrize("cards", [None, [], ["for_the_throne"]])
@pytest.mark.parametrize("actor,target", [("deputy", "leader"), ("warrior", "leader"), ("deputy", "warrior"), ("leader", "deputy")])
def test_rivalry_changes_only_deputy_to_leader_interaction_weights(colony, cards, actor, target):
    colony.cruel_cards = cards
    first, second = Cat(status=actor, moons=40), Cat(status=target, moons=40)
    relation = first.create_one_relationship(second)
    for field in ("romantic_love", "platonic_like", "dislike", "admiration", "comfortable", "jealousy", "trust"):
        setattr(relation, field, 0)
    boosted = cards and actor == "deputy" and target == "leader"
    with patch("scripts.cat_relations.relationship.get_personality_compatibility", return_value=None), patch(
            "scripts.cat_relations.relationship.choice", side_effect=lambda values: values[0]) as choose:
        relation.positive_interaction()
        ballot = choose.call_args.args[0]
        assert ballot.count(False) == (2 if boosted else 1)
        for positive in (True, False):
            relation.get_interaction_type(positive)
            weights = choose.call_args.args[0]
            assert weights.count("admiration") == (4 if boosted and not positive else 1)
    assert relation.jealousy == 0



def test_rivalry_negative_respect_interaction_has_real_effects_and_a_log(colony, monkeypatch):
    from scripts.cat_relations.relationship import Relationship

    colony.cruel_cards = ["for_the_throne"]
    deputy, leader = Cat(status="deputy", moons=40), Cat(status="leader", moons=40)
    relation = deputy.create_one_relationship(leader)
    relation.admiration = relation.trust = 80
    monkeypatch.setattr(game, "cur_events_list", [])
    def choose(values):
        return "admiration" if "admiration" in values else values[0]
    with patch.object(Relationship, "positive_interaction", return_value=False), patch(
            "scripts.cat_relations.relationship.choice", side_effect=choose), patch(
            "scripts.cat_relations.relationship.random.choices", return_value=["low"]), patch.dict(
            game.config["relationship"], {"chance_for_neutral": 0}):
        relation.start_interaction()
    assert relation.admiration < 80
    assert relation.trust < 80 and relation.dislike > 0
    assert relation.log and game.cur_events_list


@pytest.mark.parametrize("biome,number,label", [("Plains", 10, "Bridge"), ("Beach", 6, "Quay")])
def test_new_camps_have_selectable_tabs_seasonal_previews_and_keyboard_access(card_screen, biome, number, label):
    import pygame
    import pygame_gui
    from scripts.utility import ui_scale

    screen = card_screen
    screen.biome_selected = biome
    screen.open_choose_background()
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.tabs[f"tab{number}"]))
    assert screen.selected_camp_tab == number
    assert screen.tabs[f"tab{number}"].text_layer.html_text == label
    assert not screen.tabs[f"tab{number}"].is_enabled
    assert ui_scale(pygame.Rect(0, 0, 800, 700)).contains(screen.tabs[f"tab{number}"].rect)
    assert not screen.tabs[f"tab{number}"].rect.colliderect(screen.elements["random_background"].rect)
    for season in ("Newleaf", "Greenleaf", "Leaf-fall", "Leaf-bare"):
        screen.selected_season = season
        for dark in (False, True):
            with patch.dict(game.settings, {"dark mode": dark}):
                screen.refresh_selected_camp()
                assert pygame.image.load(screen.get_camp_art_path(number)).get_width() > 0
    screen.handle_choose_background_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP))
    assert screen.selected_camp_tab == number - 1
    screen.handle_choose_background_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN))
    assert screen.selected_camp_tab == number
    # Switching biomes must remove the old camp tab and leave the other picker usable.
    screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["forest_biome"]))
    assert screen.selected_camp_tab == 1
    assert screen.tabs[f"tab{number}"].alive() == (number <= 8)


@pytest.mark.parametrize("biome,number", [("Plains", 10), ("Beach", 6)])
def test_random_and_quick_start_can_select_new_camps(card_screen, biome, number):
    import pygame
    import pygame_gui
    from scripts.screens.MakeClanScreen import sprites

    screen = card_screen
    def choose(values):
        return biome if biome in values else values[0]
    screen.biome_selected = "Forest"
    screen.open_choose_background()
    with patch("scripts.screens.MakeClanScreen.choice", side_effect=choose), patch(
        "scripts.screens.MakeClanScreen.random.randint", side_effect=lambda low, high: high
    ):
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.elements["random_background"]))
    assert (screen.biome_selected, screen.selected_camp_tab) == (biome, number)
    screen.game_mode = game.clan.game_mode = "expanded"
    with patch("scripts.screens.MakeClanScreen.choice", side_effect=choose), patch(
        "scripts.screens.MakeClanScreen.random.randint", side_effect=lambda low, high: high
    ), patch.object(sprites, "clan_symbols", ["symbolBEECH0"]), patch.object(screen, "save_clan"), patch.object(screen, "open_clan_saved_screen"):
        screen.random_quick_start()
    assert (screen.biome_selected, screen.selected_camp_tab) == (biome, number)
