from types import SimpleNamespace

import pygame
import pygame_gui
import pytest

from scripts.game_structure.game_essentials import game
from scripts.game_structure import screen_settings as settings
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.ui_elements import UISpriteButton, CatButton
from scripts.screens.ClanScreen import ClanScreen


@pytest.fixture(autouse=True)
def viewport(monkeypatch):
    old_offset = MANAGER.offset
    monkeypatch.setattr(settings, "offset", (0, 0))
    monkeypatch.setattr(settings, "screen_scale", 1)
    MANAGER.set_offset((0, 0))
    yield
    MANAGER.set_offset(old_offset)


@pytest.fixture
def sprite_buttons(monkeypatch):
    monkeypatch.setitem(game.settings, "no sprite antialiasing", True)
    buttons = []
    def create(rect, color_rect, cat_id="test", container=None):
        image = pygame.Surface((50, 50), pygame.SRCALPHA)
        image.fill((255, 255, 255, 255), color_rect)
        button = UISpriteButton(pygame.Rect(rect), image, cat_id=cat_id, container=container, manager=MANAGER)
        buttons.append(button)
        return button
    yield create
    for button in buttons:
        button.kill()


def click(point):
    pygame.event.clear()
    for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        MANAGER.process_events(pygame.event.Event(kind, button=1, pos=point))
    return [event.ui_element for event in pygame.event.get() if event.type == pygame_gui.UI_BUTTON_START_PRESS]


@pytest.mark.parametrize("size", [25, 50, 75, 100])
def test_scaled_visible_pixels_and_transparent_corners(sprite_buttons, size):
    sprite = sprite_buttons((100, 100, size, size), (20, 20, 10, 10))
    assert sprite.button.hover_point(*sprite.button.rect.center)
    assert not sprite.button.hover_point(101, 101)
    assert sprite.button in click(sprite.button.rect.center)
    assert sprite.button not in click((101, 101))
    # A held button may check points outside its sprite on mouse release.
    sprite.button.held = True
    assert not sprite.button.hover_point(90, 90)
    sprite.button.held = False


def test_overlapping_cats_can_be_clicked_through_empty_sprite_space(sprite_buttons):
    left = sprite_buttons((150, 100, 50, 50), (2, 10, 12, 30), "left")
    right = sprite_buttons((150, 100, 50, 50), (35, 10, 12, 30), "right")
    assert click((157, 120)) == [left.button]
    assert click((190, 120)) == [right.button]
    assert click((175, 105)) == []


def test_sprite_refresh_moves_hit_region_with_the_new_art(sprite_buttons):
    sprite = sprite_buttons((250, 100, 50, 50), (2, 10, 10, 30))
    assert sprite.button.hover_point(257, 120)
    updated = pygame.Surface((100, 100), pygame.SRCALPHA)
    updated.fill((255, 255, 255, 255), (70, 20, 20, 60))
    sprite.set_image(updated)
    assert not sprite.button.hover_point(257, 120)
    assert sprite.button.hover_point(290, 120)


def test_move_and_container_clipping_use_current_absolute_coordinates(sprite_buttons):
    container = pygame_gui.core.UIContainer(pygame.Rect(300, 100, 40, 40), manager=MANAGER)
    sprite = sprite_buttons((0, 0, 50, 50), (0, 0, 50, 50), container=container)
    try:
        assert sprite.button.hover_point(320, 120)
        assert not sprite.button.hover_point(345, 120)
        container.set_position((350, 100))
        assert not sprite.button.hover_point(320, 120)
        assert sprite.button.hover_point(370, 120)
    finally:
        sprite.kill()
        container.kill()


def test_empty_sprite_is_not_a_click_target(sprite_buttons):
    sprite = sprite_buttons((400, 100, 50, 50), (0, 0, 0, 0))
    assert not sprite.button.hover_point(*sprite.button.rect.center)
    assert sprite.button not in click(sprite.button.rect.center)


def test_plain_cat_buttons_remain_rectangular():
    button = CatButton(pygame.Rect(450, 100, 50, 50), "", cat_id="plain", manager=MANAGER)
    try:
        assert button.hover_point(475, 125)
    finally:
        button.kill()


def test_camp_drag_only_starts_on_visible_sprite_pixels(sprite_buttons):
    sprite = sprite_buttons((500, 200, 50, 50), (20, 10, 10, 30), "cat")
    screen = ClanScreen("mask camp test")
    screen.cat_buttons = [sprite]
    screen.menu_buttons = {}
    screen._cat_button_by_id = {"cat": sprite}
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(501, 201)))
    assert screen._dragging_cat_id is None
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(525, 220)))
    assert screen._dragging_cat_id == "cat"
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=3, pos=(525, 220)))
    assert screen._dragging_cat_id is None


@pytest.mark.parametrize("scale", [1, 1.25, 1.5, 2])
def test_camp_drag_retains_string_id_and_real_scale(sprite_buttons, monkeypatch, scale):
    from scripts.cat.cats import Cat

    monkeypatch.setattr(settings, "screen_scale", scale)
    sprite = sprite_buttons((100, 100, 50, 50), (0, 0, 50, 50), "123")
    cat = SimpleNamespace(placement=None)
    monkeypatch.setattr(Cat, "all_cats", {"123": cat})
    screen = ClanScreen("scaled mask camp test")
    screen.cat_buttons = [sprite]
    screen.menu_buttons = {}
    screen._cat_button_by_id = {"123": sprite}
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=3, pos=(125, 125)))
    assert screen._dragging_cat_id == "123"
    screen.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(225, 225)))
    assert cat.placement == (round(200 / scale), round(200 / scale))
    assert sprite.button.rect.topleft == (200, 200)
    assert sprite.button.hover_point(225, 225)
    assert not sprite.button.hover_point(125, 125)
    screen.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=3, pos=(225, 225)))
