from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pygame
import pygame_gui
import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat.names import Name
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.game_structure.game_essentials import game
from scripts.game_structure.load_cat import load_cats
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.windows import ChangeCatName
from scripts.screens.MakeClanScreen import MakeClanScreen


@pytest.fixture
def naming(monkeypatch, tmp_path):
    for target, name, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                                (Cat, "outside_cats", {}), (Cat, "dead_cats", []),
                                (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, name, value)
    clan = Clan(name="NamingTest", camp_bg="camp1", game_mode="expanded")
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "switches", {**game.switches, "clan_name": clan.name, "clan_list": [clan.name],
                                          "customise_new_life": False})
    for module in ("scripts.cat.cats", "scripts.game_structure.game_essentials", "scripts.game_structure.load_cat"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    monkeypatch.setitem(game.all_screens, "profile screen", Mock())
    cat = Cat(prefix="Moss", suffix="heart", gender="female", status="warrior", moons=40)
    cat.history = History()
    clan.add_cat(cat)
    clan.your_cat = cat
    windows = set(MANAGER.get_window_stack().get_full_stack())
    elements = []
    yield clan, cat, elements
    for window in MANAGER.get_window_stack().get_full_stack().copy():
        if window not in windows:
            window.kill()
    for element in elements:
        element.kill()


def press(window, button):
    window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button))


def reload_cat(cat):
    cat_id = cat.ID
    game.save_cats()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    return Cat.fetch_cat(cat_id)


@pytest.mark.parametrize("style", ["warrior", "ancient", "single", "syllable"])
def test_creation_dice_keep_the_rolled_style_and_visibility_through_save_reload(naming, style):
    clan, cat, elements = naming
    for setting in ("warrior", "ancient", "single", "syllable"):
        clan.clan_settings[setting + "_names"] = setting == style
    screen = object.__new__(MakeClanScreen)
    screen.your_cat = cat
    screen.pending_name_type = cat.name.name_type
    screen.specsuffix_hidden = cat.name.specsuffix_hidden
    screen.open_choose_background = Mock()
    prefix = pygame_gui.elements.UITextEntryLine(pygame.Rect(0, 0, 150, 30), manager=MANAGER)
    suffix = pygame_gui.elements.UITextEntryLine(pygame.Rect(0, 35, 150, 30), manager=MANAGER)
    elements.extend((prefix, suffix))
    screen.elements = {"prefix_entry": prefix, "suffix_entry": suffix, "random": object(),
                       "next_step": object(), "use_spec_suffix": Mock()}
    before = cat.name.prefix, cat.name.suffix, cat.name.name_type, cat.name.specsuffix_hidden
    screen.handle_choose_name_event(SimpleNamespace(ui_element=screen.elements["random"]))
    assert (cat.name.prefix, cat.name.suffix, cat.name.name_type, cat.name.specsuffix_hidden) == before
    expected = Name.format_components(prefix.get_text(), suffix.get_text(), style)
    screen.handle_choose_name_event(SimpleNamespace(ui_element=screen.elements["next_step"]))
    assert cat.name.name_type == style
    assert cat.name.specsuffix_hidden is (style != "warrior")
    assert str(cat.name) == expected
    restored = reload_cat(cat)
    assert restored.name.name_type == style and str(restored.name) == expected
    assert restored.name.specsuffix_hidden is (style != "warrior")


def test_closing_rename_after_toggling_special_suffix_does_not_commit_edits(naming):
    clan, cat, elements = naming
    cat.status = "apprentice"
    cat.name.specsuffix_hidden = True
    window = ChangeCatName(cat)
    window.suffix_entry_box.set_text("Wildeharbor")
    press(window, window.toggle_spec_block_off)
    press(window, window.back_button)
    assert cat.name.suffix == "heart" and cat.name.specsuffix_hidden
    assert str(cat.name) == "Mossheart"


@pytest.mark.parametrize("save", [False, True])
def test_rename_special_suffix_toggle_preserves_the_draft_until_done(naming, save):
    clan, cat, elements = naming
    cat.status = "apprentice"
    cat.name.specsuffix_hidden = True
    window = ChangeCatName(cat)
    window.suffix_entry_box.set_text("Wildeharbor")
    press(window, window.toggle_spec_block_off)
    assert cat.name.suffix == "heart"
    press(window, window.toggle_spec_block_on)
    assert window.suffix_entry_box.get_text() == "Wildeharbor"
    if save:
        press(window, window.done_button)
        assert cat.name.suffix == "Wildeharbor" and cat.name.specsuffix_hidden
        assert str(reload_cat(cat).name) == "MossWildeharbor"


@pytest.mark.parametrize("style,prefix,suffix", [("warrior", "Moss", "Wildeharbor"),
    ("ancient", "Moss", "Wildeharbor"), ("single", "Fireheart", ""), ("syllable", "Kyra", "")])
def test_newborn_inherits_stored_parent_style_instead_of_guessing_from_display(naming, style, prefix, suffix):
    clan, parent, elements = naming
    parent.status = "leader" if style == "ancient" else "warrior"
    parent.name = Name(prefix=prefix, suffix=suffix, name_type=style, cat=parent,
                       specsuffix_hidden=style in ("single", "syllable"), load_existing_name=True)
    kitten = Cat(gender="female", status="newborn", moons=0, parent1=parent.ID)
    assert kitten.name.name_type == style


def test_a_later_litter_uses_the_parents_current_naming_style(naming):
    clan, parent, elements = naming
    parent.name = Name(prefix="Kyra", suffix="", name_type="syllable", cat=parent,
                       specsuffix_hidden=True, load_existing_name=True)
    first = Cat(gender="female", status="newborn", moons=0, parent1=parent.ID)
    clan.age += 1
    parent.name = Name(prefix="Moss", suffix="Wildeharbor", name_type="ancient", cat=parent,
                       specsuffix_hidden=True, load_existing_name=True)
    second = Cat(gender="female", status="newborn", moons=0, parent1=parent.ID)
    assert first.name.name_type == "syllable" and second.name.name_type == "ancient"


@pytest.mark.parametrize("status", ["warrior", "apprentice", "leader"])
@pytest.mark.parametrize("style", ["warrior", "ancient", "single", "syllable"])
@pytest.mark.parametrize("hidden", [False, True])
def test_rename_done_without_edits_preserves_all_styles_and_rank_suffixes(naming, status, style, hidden):
    clan, cat, elements = naming
    cat.status = status
    cat.name = Name(prefix="Moss", suffix="Wildeharbor" if style in ("warrior", "ancient") else "",
                    name_type=style, specsuffix_hidden=hidden, cat=cat, load_existing_name=True)
    expected = str(cat.name), cat.name.suffix, cat.name.name_type, cat.name.specsuffix_hidden
    window = ChangeCatName(cat)
    press(window, window.done_button)
    assert (str(cat.name), cat.name.suffix, cat.name.name_type, cat.name.specsuffix_hidden) == expected
    restored = reload_cat(cat)
    assert (str(restored.name), restored.name.suffix, restored.name.name_type, restored.name.specsuffix_hidden) == expected


@pytest.mark.parametrize("status,suffix", [("apprentice", "paw"), ("leader", "star")])
def test_done_keeps_the_draft_custom_suffix_behind_the_visible_rank_suffix(naming, status, suffix):
    clan, cat, elements = naming
    cat.status = status
    cat.name.specsuffix_hidden = True
    window = ChangeCatName(cat)
    window.suffix_entry_box.set_text("Wildeharbor")
    press(window, window.toggle_spec_block_off)
    press(window, window.done_button)
    assert cat.name.suffix == "Wildeharbor" and not cat.name.specsuffix_hidden
    assert str(cat.name) == "Moss" + suffix
    restored = reload_cat(cat)
    assert restored.name.suffix == "Wildeharbor" and not restored.name.specsuffix_hidden
    assert str(restored.name) == "Moss" + suffix


def test_naming_cache_is_separate_for_different_colonies(naming, monkeypatch):
    clan, parent, elements = naming
    parent.name = Name(prefix="Kyra", suffix="", name_type="syllable", cat=parent,
                       specsuffix_hidden=True, load_existing_name=True)
    first = Cat(gender="female", status="newborn", moons=0, parent1=parent.ID)
    other = Clan(name="OtherNaming", camp_bg="camp1", game_mode="expanded")
    monkeypatch.setattr(game, "clan", other)
    parent.name = Name(prefix="Moss", suffix="Wildeharbor", name_type="ancient", cat=parent,
                       specsuffix_hidden=True, load_existing_name=True)
    second = Cat(gender="female", status="newborn", moons=0, parent1=parent.ID)
    assert first.name.name_type == "syllable" and second.name.name_type == "ancient"
    assert clan._litter_style_cache is not other._litter_style_cache


def test_mixed_style_litter_stays_consistent_and_can_disable_inheritance(naming):
    clan, parent, elements = naming
    parent.name = Name(prefix="Kyra", suffix="", name_type="syllable", cat=parent,
                       specsuffix_hidden=True, load_existing_name=True)
    other = Cat(prefix="Moss", suffix="Wildeharbor", gender="female", status="warrior", moons=40,
                name_type="ancient", loading_cat=True, pelt=parent.pelt)
    kittens = [Cat(gender="female", status="newborn", moons=0, parent1=parent.ID, parent2=other.ID)
               for _ in range(4)]
    assert len({cat.name.name_type for cat in kittens}) == 1
    assert kittens[0].name.name_type in ("ancient", "syllable")
    clan.clan_settings["kit_inherit_naming"] = False
    independent = Cat(gender="female", status="newborn", moons=0, parent1=parent.ID, parent2=other.ID)
    assert independent.name.name_type == "warrior"


def test_creation_back_discards_name_dice_and_suffix_toggle_drafts(naming):
    clan, cat, elements = naming
    clan.clan_settings.update(warrior_names=False, ancient_names=True)
    screen = object.__new__(MakeClanScreen)
    screen.your_cat = cat
    screen.pending_name_type = cat.name.name_type
    screen.specsuffix_hidden = cat.name.specsuffix_hidden
    screen.open_choose_leader = Mock()
    prefix = pygame_gui.elements.UITextEntryLine(pygame.Rect(0, 0, 150, 30), manager=MANAGER)
    suffix = pygame_gui.elements.UITextEntryLine(pygame.Rect(0, 35, 150, 30), manager=MANAGER)
    elements.extend((prefix, suffix))
    screen.elements = {"prefix_entry": prefix, "suffix_entry": suffix, "random": object(),
                       "next_step": object(), "previous_step": object(), "use_spec_suffix": Mock()}
    before = cat.name.prefix, cat.name.suffix, cat.name.name_type, cat.name.specsuffix_hidden
    for key in ("random", "use_spec_suffix", "previous_step"):
        screen.handle_choose_name_event(SimpleNamespace(ui_element=screen.elements[key]))
    assert (cat.name.prefix, cat.name.suffix, cat.name.name_type, cat.name.specsuffix_hidden) == before
    screen.open_choose_leader.assert_called_once()
