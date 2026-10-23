import pygame
import pygame_gui
import pytest
from scripts.clan_resources.cruel_season import CARDS, CARD_DATA, validate_cards
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.screens.CruelCards import CruelCardConflicts
from tests.test_cruel_season import colony, card_screen


@pytest.mark.parametrize("group", list(CARD_DATA["conflicts"].values()))
@pytest.mark.parametrize("action", ["keep", "replace", "escape", "close"])
def test_conflict_dialog_preserves_or_replaces_only_conflicting_cards(card_screen, group, action):
    screen = card_screen
    old, new = group[:2]
    unaffected = next(card for card in CARDS if card not in group and _compatible([old, card]) and _compatible([new, card]))
    screen.apply_cruel_deck([old, unaffected])
    original = screen.cruel_cards.copy()
    window = CruelCardConflicts(new, screen.cruel_cards, screen.apply_cruel_deck)
    assert screen.cruel_cards == original and game.clan.cruel_cards == original
    try:
        if action in ("keep", "replace"):
            window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
                ui_element=window.keep_button if action == "keep" else window.replace_button))
        elif action == "escape":
            window.process_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        else:
            window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.back_button))
        expected = [unaffected, new] if action == "replace" else original
        assert screen.cruel_cards == game.clan.cruel_cards == expected
        assert not window.alive()
        validate_cards(expected)
    finally:
        if window.alive(): window.kill()


def _compatible(cards):
    try:
        validate_cards(cards)
    except ValueError:
        return False
    return True


def test_real_card_selection_opens_dialog_without_mutating_the_deck(card_screen):
    screen = card_screen
    screen.apply_cruel_deck(["always_newleaf"])
    screen.handle_cruel_cards_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
        ui_element=screen.card_buttons["always_leaf-bare"]))
    windows = [w for w in MANAGER.get_window_stack().get_full_stack() if isinstance(w, CruelCardConflicts)]
    assert len(windows) == 1
    window = windows[0]
    try:
        assert screen.cruel_cards == ["always_newleaf"]
        window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.replace_button))
        assert screen.cruel_cards == ["always_leaf-bare"]
        assert "always_leaf-bare" in screen.chosen_card_buttons
        assert screen.elements["next_step"].is_enabled
    finally:
        if window.alive(): window.kill()


def test_replacement_at_full_deck_limit_preserves_all_other_choices(card_screen):
    screen = card_screen
    cards = ["always_newleaf"]
    for card in CARDS:
        if len(cards) == CARD_DATA["limit"]:
            break
        if card not in cards and card != "always_leaf-bare" and _compatible(cards + [card]):
            cards.append(card)
    assert len(cards) == CARD_DATA["limit"]
    screen.apply_cruel_deck(cards)
    window = CruelCardConflicts("always_leaf-bare", cards, screen.apply_cruel_deck)
    try:
        window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.replace_button))
        assert screen.cruel_cards == cards[1:] + ["always_leaf-bare"]
        assert len(screen.cruel_cards) == CARD_DATA["limit"]
    finally:
        if window.alive(): window.kill()


def test_pending_conflict_blocks_background_card_actions_and_navigation(card_screen):
    screen = card_screen
    screen.apply_cruel_deck(["always_newleaf"])
    window = CruelCardConflicts("always_leaf-bare", screen.cruel_cards, screen.apply_cruel_deck)
    try:
        for button in (screen.elements["random_card"], screen.elements["next_step"], screen.chosen_card_buttons["always_newleaf"]):
            screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
            assert screen.cruel_cards == ["always_newleaf"]
            assert screen.sub_screen == "cruel cards"
            assert window.alive()
    finally:
        window.kill()
