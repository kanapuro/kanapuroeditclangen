from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.game_structure.game_essentials import game
from scripts.screens.ProfileScreen import ProfileScreen
from scripts.screens.screens_core import screens_core as core
from scripts.utility import ui_scale


@pytest.fixture
def profile(monkeypatch):
    for target, key, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                               (Cat, "outside_cats", {}), (Inheritance, "all_inheritances", {}),
                               (game, "all_screens", {}), (game, "cur_events_list", [])):
        monkeypatch.setattr(target, key, value)
    monkeypatch.setattr(Cat, "sprite", property(lambda cat: pygame.Surface((50, 50), pygame.SRCALPHA)))
    monkeypatch.setattr(game, "safe_save", Mock(side_effect=AssertionError("No real save writes")))
    clan = Clan(name="ProfileTest", biome="Forest", camp_bg="camp1")
    clan.clan_cats = []
    clan.clan_settings["all accessories"] = False
    monkeypatch.setattr(game, "clan", clan)
    cats = [Cat(status="warrior", moons=30) for _ in range(2)]
    for cat in cats:
        cat.history = History()
        cat.create_inheritance_new_cat()
        clan.add_cat(cat)
    clan.your_cat = cats[0]
    clan.instructor = clan.demon = clan.wanderer = SimpleNamespace(ID="guide")
    core.rebuild_core(should_rebuild_bgs=False)
    with patch.dict(game.switches, {"cat": cats[0].ID, "cur_screen": "profile screen", "window_open": False}):
        screen = ProfileScreen("profile screen")
        screen.screen_switches()
        try:
            yield clan, cats, screen
        finally:
            screen.exit_screen()


def rebuild(screen):
    screen.clear_profile()
    screen.build_profile()


@pytest.mark.parametrize("role,action", [("mediator apprentice", "mediation"), ("queen's apprentice", "queen")])
def test_multiple_profile_activities_are_centered_and_separate_from_dialogue(profile, role, action):
    clan, cats, screen = profile
    cats[0].status = role
    cats[0].moons = 10
    rebuild(screen)
    first, second = screen.profile_elements[action], screen.profile_elements["halfmoon"]
    expected = ui_scale(pygame.Rect((360, 105), (79, 34)))
    assert first.relative_rect.union(second.relative_rect).centerx == expected.centerx
    assert not first.rect.colliderect(second.rect)
    assert first.tool_tip_text


@pytest.mark.parametrize("role", ["medicine cat", "medicine cat apprentice", "apprentice"])
def test_unable_to_work_cannot_use_moonplace_profile_action(profile, role):
    clan, cats, screen = profile
    cats[0].status = role
    cats[0].get_injured("broken bone")
    clan.age = 6
    rebuild(screen)
    button = screen.profile_elements["halfmoon"]
    assert not button.is_enabled
    with patch.object(screen, "change_screen") as route:
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))
        route.assert_not_called()


def test_dead_former_colonycat_has_no_return_action(profile):
    clan, cats, screen = profile
    cats[0].status = "former colonycat"
    cats[0].outside = True
    cats[0].dead = True
    rebuild(screen)
    assert not screen.exile_return_button.visible


@pytest.mark.parametrize("existing", [False, True])
def test_return_home_never_adds_none_and_accepts_more_than_four_scars(profile, existing):
    clan, cats, screen = profile
    cat = cats[0]
    cat.status, cat.outside = "former colonycat", True
    cat.pelt.scars = ["ONE", "TWO", "THREE", "TAILSCAR", "SNOUT"] + (["BRIDGE"] if existing else [])
    before = cat.pelt.scars.copy()
    def choose(options):
        return "BRIDGE" if "BRIDGE" in options else options[0]
    with patch("scripts.cat.cats.randint", return_value=2), patch("scripts.cat.cats.choice", side_effect=choose):
        cat.return_home()
    assert None not in cat.pelt.scars
    assert cat.pelt.scars == (before if existing else before + ["BRIDGE"])
    assert game.cur_events_list


@pytest.mark.parametrize("role", ["queen", "mediator", "elder"])
def test_other_cat_activities_stay_above_dialogue(profile, role):
    clan, cats, screen = profile
    cats[1].status = role
    game.switches["cat"] = cats[1].ID
    rebuild(screen)
    action = {"queen": "queen", "mediator": "mediation", "elder": "story"}[role]
    button = screen.profile_elements[action]
    assert button.relative_rect == ui_scale(pygame.Rect((383, 65), (34, 34)))
    assert "halfmoon" not in screen.profile_elements


@pytest.mark.parametrize("age,attended,shunned,enabled", [
    (5, False, False, False), (6, False, False, True),
    (6, True, False, False), (6, False, True, False),
])
def test_medicine_visit_obeys_timing_and_existing_restrictions(profile, age, attended, shunned, enabled):
    clan, cats, screen = profile
    cats[0].status = "medicine cat"
    cats[0].shunned = int(shunned)
    clan.age = age
    cats[0].moonplace_visit_moon = age if attended else None
    rebuild(screen)
    assert screen.profile_elements["halfmoon"].is_enabled == enabled


def test_return_action_allows_only_one_attempt_and_hides_inside_colony(profile):
    clan, cats, screen = profile
    cats[0].status, cats[0].outside = "former colonycat", True
    clan.exile_return = True
    rebuild(screen)
    assert screen.exile_return_button.visible
    assert not screen.exile_return_button.is_enabled
    with patch.object(Cat, "return_home") as return_home:
        screen.handle_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.exile_return_button))
        return_home.assert_not_called()
    cats[0].status, cats[0].outside = "warrior", False
    rebuild(screen)
    assert not screen.exile_return_button.visible


@pytest.mark.parametrize("existing_condition", [False, True])
def test_condition_cards_fit_wrapped_titles_and_clear_the_last_page(profile, existing_condition):
    clan, cats, screen = profile
    cat = cats[0]
    cat.permanent_condition.clear()
    cat.gender = "intersex"
    if existing_condition:
        cat.get_permanent_condition("aneuploidy")
    for name in ("persistent headaches", "testosterone deficiency", "excess testosterone", "wobbly cat syndrome", "crooked jaw"):
        cat.get_permanent_condition(name)
    screen.toggle_conditions_tab()
    screen.display_conditions_page()
    assert screen.right_conditions_arrow.is_enabled
    for key, panel in screen.condition_data.items():
        if not key.startswith("bg_"):
            continue
        name = screen.condition_data["name_" + key[3:]]
        details = screen.condition_data["desc_" + key[3:]]
        assert screen.condition_container.rect.contains(panel.rect)
        assert name.rect.bottom <= details.rect.top
        assert panel.rect.contains(details.rect)
        assert details.rect.height > 0
    screen.conditions_page = 1
    screen.display_conditions_page()
    assert len(screen.condition_data) == (6 if existing_condition else 3)
    assert not screen.right_conditions_arrow.is_enabled
    assert screen.left_conditions_arrow.is_enabled
    old = list(screen.condition_data.values())
    cat.permanent_condition.clear()
    screen.display_conditions_page()
    assert screen.conditions_page == 0
    assert not screen.condition_data
    assert not screen.left_conditions_arrow.is_enabled
    assert not screen.right_conditions_arrow.is_enabled
    assert all(not widget.alive() for widget in old)


def test_condition_cards_scale_without_title_overlap(profile):
    import json
    from pathlib import Path
    from scripts.game_structure import screen_settings
    from scripts.ui.generate_screen_scale_json import _multiply_numbers

    clan, cats, screen = profile
    for name in ("persistent headaches", "wobbly cat syndrome", "recurring shock", "crooked jaw"):
        cats[0].get_permanent_condition(name)
    manager = screen_settings.MANAGER
    resolution, offset = manager.window_resolution, manager.offset
    original_scale = screen_settings.screen_scale
    base = json.loads(Path("resources/theme/master_screen_scale.json").read_text(encoding="utf-8"))
    dark_theme = json.loads(Path("resources/theme/themes/dark.json").read_text(encoding="utf-8"))
    screen.exit_screen()
    try:
        for scale in (1, 1.25, 1.5, 2):
            manager.set_window_resolution((int(800 * scale), int(700 * scale)))
            manager.set_offset((0, 0))
            manager.get_theme().load_theme(_multiply_numbers(base, scale))
            manager.get_theme().load_theme(dark_theme)
            for dark in (False, True):
                with patch.object(screen_settings, "screen_scale", scale), patch.dict(game.settings, {"dark mode": dark}):
                    screen.screen_switches()
                    try:
                        screen.toggle_conditions_tab()
                        screen.display_conditions_page()
                        for key, panel in screen.condition_data.items():
                            if key.startswith("bg_"):
                                name = screen.condition_data["name_" + key[3:]]
                                details = screen.condition_data["desc_" + key[3:]]
                                assert screen.condition_container.rect.contains(panel.rect)
                                assert panel.rect.top >= screen.conditions_background.rect.top + int(15 * scale)
                                assert name.rect.bottom <= details.rect.top
                                assert panel.rect.contains(details.rect)
                    finally:
                        screen.exit_screen()
    finally:
        manager.set_window_resolution(resolution)
        manager.set_offset(offset)
        manager.get_theme().load_theme(_multiply_numbers(base, original_scale))
        manager.get_theme().load_theme(dark_theme)
        screen.screen_switches()


@pytest.mark.parametrize("moons,rank", [(0,"kitten"), (5,"kitten"), (6,"apprentice"), (11,"apprentice"), (12,"warrior"), (119,"warrior"), (120,"elder")])
@pytest.mark.parametrize("accepted", [True, False])
def test_return_home_uses_age_boundaries_and_preserves_origin(profile, moons, rank, accepted):
    clan, cats, screen = profile
    cat = cats[0]
    cat.moons = moons
    cat.status, cat.outside = "former colonycat", True
    History.add_beginning(cat, clan_born=True)
    beginning = cat.history.beginning.copy()
    clan.age = 30
    clan.add_to_outside(cat)
    def roll(low, high):
        return 1 if accepted or high == 50 else high
    with patch("scripts.cat.cats.randint", side_effect=roll):
        cat.return_home()
    assert cat.status == rank
    assert cat.dead == (not accepted)
    assert cat.history.beginning == beginning
    if accepted:
        assert not cat.outside
        assert cat.ID not in Cat.outside_cats


def test_joining_parent_preserves_child_origin_and_initializes_new_arrivals(profile, monkeypatch, tmp_path):
    clan, cats, screen = profile
    parent, child = cats
    child.moons = 4
    child.parent1 = parent.ID
    child.create_inheritance_new_cat()
    parent.create_inheritance_new_cat()
    History.add_beginning(parent, clan_born=True)
    History.add_beginning(child, clan_born=True)
    beginnings = [cat.history.beginning.copy() for cat in cats]
    for cat in cats:
        cat.outside = True
        clan.add_to_outside(cat)
    clan.age = 20
    assert child.ID in parent.add_to_clan()
    assert [cat.history.beginning for cat in cats] == beginnings
    newcomer = Cat(status="loner", moons=24)
    newcomer.history = History()
    newcomer.outside = True
    clan.add_to_outside(newcomer)
    newcomer.add_to_clan()
    assert newcomer.history.beginning["moon"] == 20
    assert newcomer.history.beginning["age"] == 24

    from pathlib import Path
    from scripts.game_structure.load_cat import load_cats
    for module in ("scripts.cat.cats", "scripts.game_structure.game_essentials", "scripts.game_structure.load_cat"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setitem(game.switches, "clan_list", [clan.name])
    monkeypatch.setitem(game.switches, "clan_name", clan.name)
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    ids = [cat.ID for cat in cats]
    game.save_cats()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    for cat_id, beginning in zip(ids, beginnings):
        restored = Cat.fetch_cat(cat_id)
        restored.load_history()
        assert restored.history.beginning == beginning
