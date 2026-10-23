from unittest.mock import patch
import pygame
import pygame_gui
import pytest
from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.game_structure.windows import LeaveClanWindow
from tests.test_profile_modernization import profile


@pytest.mark.parametrize("status", ["loner", "rogue", "kittypet"])
@pytest.mark.parametrize("rank", ["warrior", "leader", "deputy", "medicine cat", "apprentice", "mediator", "queen"])
def test_departure_preserves_family_and_clears_duties(profile, status, rank):
    clan, cats, screen = profile
    cat, companion = cats
    cat.status = rank
    if rank == "leader":
        clan.leader = cat
    elif rank == "deputy":
        clan.deputy = cat
    elif rank == "medicine cat":
        clan.new_medicine_cat(cat)
    cat.mates = [companion.ID]
    History.add_beginning(cat, clan_born=True)
    origin = cat.history.beginning.copy()
    assert cat.leave_clan(status)
    assert cat.status == status and cat.outside and not cat.exiled
    assert Cat.outside_cats[cat.ID] is cat
    assert cat.mates == [companion.ID] and cat.history.beginning == origin
    assert clan.leader is not cat and clan.deputy is not cat
    assert cat.ID not in clan.med_cat_list
    assert not cat.leave_clan(status)


@pytest.mark.parametrize("state", ["dead", "outside", "kitten"])
def test_unavailable_departure_does_not_change_cat(profile, state):
    clan, cats, screen = profile
    cat = cats[0]
    if state == "kitten":
        cat.moons = 5
    else:
        setattr(cat, state, True)
    before = (cat.status, cat.faith)
    assert not cat.leave_clan("loner")
    assert (cat.status, cat.faith) == before


def test_departure_confirmation_and_cancel(profile):
    clan, cats, screen = profile
    screen.toggle_dangerous_tab()
    button = screen.leave_clan_button
    assert button.is_enabled
    window = LeaveClanWindow(cats[0], screen)
    assert not window.done_button.is_enabled
    window.process_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
    assert not window.alive() and not cats[0].outside
    window = LeaveClanWindow(cats[0], screen)
    window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.choices["kittypet"]))
    assert window.done_button.is_enabled
    window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=window.done_button))
    assert not window.alive()
    assert cats[0].outside and cats[0].status == "kittypet"
    assert screen.exile_return_button.visible
    assert not screen.leave_clan_button.is_enabled
    screen.close_current_tab()
    assert not button.alive()


def test_invalid_destination_is_rejected(profile):
    with pytest.raises(ValueError):
        profile[1][0].leave_clan("other clan")


def test_departing_apprentice_releases_their_mentor(profile):
    clan, cats, screen = profile
    cat, mentor = cats
    cat.status, cat.moons = "apprentice", 8
    cat.mentor = mentor.ID
    mentor.apprentice = [cat.ID]
    assert cat.leave_clan("rogue")
    assert cat.mentor is None
    assert cat.ID not in mentor.apprentice


@pytest.mark.parametrize("status", ["loner", "rogue", "kittypet"])
def test_departure_reload_and_return_home(profile, monkeypatch, tmp_path, status):
    from pathlib import Path
    from scripts.game_structure.game_essentials import game
    from scripts.game_structure.load_cat import load_cats
    from scripts.cat_relations.inheritance import Inheritance
    clan, cats, screen = profile
    cat = cats[0]
    History.add_beginning(cat, clan_born=True)
    origin = cat.history.beginning.copy()
    assert cat.leave_clan(status)
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
    cat_id = cat.ID
    game.save_cats()
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    restored = Cat.fetch_cat(cat_id)
    clan.your_cat = restored
    assert restored.status == status and restored.outside and not restored.exiled
    restored.load_history()
    assert restored.history.beginning == origin
    with patch("scripts.cat.cats.randint", return_value=1):
        restored.return_home()
    assert not restored.outside and restored.status == "warrior"
    assert restored.history.beginning == origin
