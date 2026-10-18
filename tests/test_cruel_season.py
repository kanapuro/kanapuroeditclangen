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
    conflict = first.startswith("always_") and second.startswith("always_")
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


def test_cards_survive_real_clan_and_cat_reload_without_reapplying_start_effects(colony, monkeypatch, tmp_path):
    from scripts.game_structure.load_cat import load_cats

    colony.cruel_cards = ["barren_stocks", "always_leaf-bare", "enmity"]
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
    colony.herbs = {"moss": 5}
    colony.freshkill_pile.pile = {"expires_in_4": 12}
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
    assert game.clan.freshkill_pile.total_amount == 12
    assert game.clan.herbs == {"moss": 5}
    assert game.clan.starting_season == "Leaf-bare"
    assert 1 <= game.clan.all_clans[0].relations <= 7
    # A pre-card save must keep legacy behavior when the optional field is absent.
    path = tmp_path / "CruelTest.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved.pop("cruel_cards")
    path.write_text(json.dumps(saved), encoding="utf-8")
    Clan().load_clan()
    assert game.clan.cruel_cards is None


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
            assert "Conflicting" in screen.elements["card_error"].html_text
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
    assert len(screen.card_buttons) == 1
    press("card_previous")
    screen.apply_cruel_deck(["always_leaf-bare"])
    for _ in range(20):
        press("random_card")
        assert validate_cards(screen.cruel_cards) == screen.cruel_cards
        assert [name for name in screen.cruel_cards if name.startswith("always_")] == ["always_leaf-bare"]
    assert len(screen.cruel_cards) == 10


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
    for key, expected in (("card_previous", 1), ("card_next", 0), ("card_next", 1), ("card_next", 0)):
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
        assert screen.sub_screen == "game settings"
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


def test_quick_start_keeps_chosen_cards_and_forced_starting_season(card_screen):
    from scripts.screens.MakeClanScreen import sprites

    screen = card_screen
    screen.apply_cruel_deck(["always_leaf-bare", "lean_meat"])
    with patch.object(sprites, "clan_symbols", ["symbolBEECH0"]), patch.object(screen, "save_clan"), patch.object(screen, "open_clan_saved_screen"):
        screen.random_quick_start()
    assert screen.cruel_cards == ["always_leaf-bare", "lean_meat"]
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
