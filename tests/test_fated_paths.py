from types import SimpleNamespace
from unittest.mock import Mock, patch
import pygame
import pygame_gui
import pytest
from scripts.cat.cats import Cat
from scripts.clan import Clan
from scripts.events import Events
from scripts.game_structure.game_essentials import game
from scripts.screens.RoleScreen import RoleScreen
from scripts.screens.DeputyScreen import DeputyScreen
from scripts.screens.ChooseMateScreen import ChooseMateScreen
from scripts.screens.ClanSettingsScreen import ClanSettingsScreen
from tests.test_profile_modernization import profile


@pytest.mark.parametrize(
    "cards,locked",
    [
        (None, False),
        ([], False),
        (["fated_paths"], True),
        (["fated_paths", "heartless"], True),
    ],
)
def test_card_rules_and_existing_colonies(profile, cards, locked):
    clan, cats, screen = profile
    clan.cruel_cards = cards
    assert game.get_config_value("ranks", "can_manually_change", "all") == (not locked)
    assert game.get_config_value("mates", "allow_manual") == (not locked)
    assert game.get_config_value("settings", "force_enable", "deputy") == locked
    clan.switch_setting("deputy")
    assert clan.clan_settings["deputy"]
    clan.switch_setting("deputy")
    assert clan.clan_settings["deputy"] == locked


def test_new_card_colony_and_old_saved_settings_force_deputy(
    profile, monkeypatch, tmp_path
):
    import json

    clan = Clan(name="Fated", game_mode="cruel season", cruel_cards=["fated_paths"])
    assert clan.clan_settings["deputy"]
    monkeypatch.setattr("scripts.clan.get_save_dir", lambda: str(tmp_path))
    folder = tmp_path / clan.name
    folder.mkdir()
    (folder / "clan_settings.json").write_text(
        json.dumps({"deputy": False}), encoding="utf-8"
    )
    clan.load_clan_settings()
    assert clan.clan_settings["deputy"]


@pytest.mark.parametrize("cards", [["fated_paths"], ["fated_paths", "heartless"]])
def test_role_screen_and_direct_role_events_cannot_bypass_card(profile, cards):
    clan, cats, profile_screen = profile
    clan.cruel_cards = cards
    profile_screen.exit_screen()
    screen = RoleScreen("role screen")
    screen.screen_switches()
    try:
        for name in (
            "promote_leader",
            "promote_deputy",
            "switch_med_cat",
            "switch_mediator",
            "switch_queen",
            "retire",
            "switch_med_app",
            "switch_warrior_app",
            "switch_mediator_app",
            "switch_queen_app",
        ):
            button = getattr(screen, name)
            assert not button.is_enabled
            assert "Fated Paths" in button.tool_tip_text
            screen.handle_event(
                pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button)
            )
            assert cats[0].status == "warrior"
            assert clan.leader is None and clan.deputy is None
    finally:
        screen.exit_screen()


def test_profile_blocks_rank_and_mate_entry_but_keeps_mentor_access(profile):
    clan, cats, screen = profile
    clan.cruel_cards = ["fated_paths"]
    screen.toggle_roles_tab()
    screen.update_disabled_buttons_and_text()
    assert not screen.manage_roles.is_enabled
    with patch.object(screen, "change_screen") as route:
        screen.handle_event(
            pygame.event.Event(
                pygame_gui.UI_BUTTON_START_PRESS, ui_element=screen.manage_roles
            )
        )
        route.assert_not_called()
    screen.toggle_relations_tab()
    screen.update_disabled_buttons_and_text()
    assert not screen.choose_mate_button.is_enabled


def test_direct_deputy_and_mate_methods_cannot_bypass_card(profile):
    clan, cats, screen = profile
    clan.cruel_cards = ["fated_paths"]
    target = SimpleNamespace(exit_screen=Mock())
    DeputyScreen.change_cat(target, cats[1])
    target.exit_screen.assert_not_called()
    assert cats[1].status == "warrior" and clan.deputy is None
    mates = SimpleNamespace(the_cat=cats[0], selected_cat=cats[1])
    ChooseMateScreen.change_mate(mates)
    assert not cats[0].mates and not cats[1].mates


def test_automatic_deputy_selection_still_operates_with_a_false_saved_toggle(profile):
    clan, cats, screen = profile
    clan.cruel_cards = ["fated_paths"]
    clan.clan_settings["deputy"] = False
    clan.leader = cats[0]
    cats[0].status = "leader"
    cats[1].former_apprentices = ["former"]
    Events().check_and_promote_deputy()
    assert clan.deputy is cats[1] and cats[1].status == "deputy"
    assert game.cur_events_list


@pytest.mark.parametrize("setting", ["leader", "deputy"])
def test_settings_checkbox_explains_and_cannot_disable_automatic_deputy(
    profile, setting
):
    clan, cats, profile_screen = profile
    clan.cruel_cards = ["fated_paths"]
    profile_screen.exit_screen()
    screen = ClanSettingsScreen("clan settings screen")
    screen.screen_switches()
    try:
        screen.open_roles_settings()
        button = screen.checkboxes[setting]
        assert not button.is_enabled
        assert "automatic succession" in button.tool_tip_text
        screen.handle_checkbox_events(
            pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=button)
        )
        assert clan.clan_settings[setting]
    finally:
        screen.exit_screen()


@pytest.mark.parametrize("extras", [[], ["weak_stars"], ["forsaken", "heartless"]])
def test_newborn_colony_creation_and_real_reload_keep_card_rules(
    profile, monkeypatch, tmp_path, extras
):
    import json
    from pathlib import Path
    from scripts.cat.history import History
    from scripts.cat_relations.inheritance import Inheritance
    from scripts.game_structure.load_cat import load_cats

    old, cats, screen = profile
    leader, warrior = cats
    leader.status = "leader"
    player = Cat(status="newborn", moons=-1)
    player.history = History()
    cards = ["fated_paths"] + extras
    clan = Clan(
        name="FatedSave",
        biome="Forest",
        camp_bg="camp1",
        game_mode="cruel season",
        cruel_cards=cards,
        leader=leader,
        your_cat=player,
    )
    monkeypatch.setattr(game, "clan", clan)
    clan.starting_members = [leader, warrior, player]
    for module in (
        "scripts.clan",
        "scripts.cat.cats",
        "scripts.game_structure.game_essentials",
        "scripts.game_structure.load_cat",
    ):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr(
        "scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0"
    )
    for name in (
        "generate_mates",
        "generate_families",
        "populate_sc",
        "populate_ur",
        "populate_df",
    ):
        monkeypatch.setattr(clan, name, Mock())

    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)

    monkeypatch.setattr(game, "safe_save", save)
    monkeypatch.setitem(game.switches, "clan_list", [clan.name])
    monkeypatch.setitem(game.switches, "clan_name", clan.name)
    player_id = player.ID
    clan.create_clan()
    assert player.status == "newborn" and player.moons == -1
    assert clan.clan_settings["deputy"]
    granted = clan.leader_lives_granted
    # An older or externally edited false toggle must not defeat a saved card.
    settings = tmp_path / clan.name / "clan_settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    data["deputy"] = False
    data["leader"] = False
    settings.write_text(json.dumps(data), encoding="utf-8")
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    assert game.clan.cruel_cards == cards
    assert game.clan.your_cat.ID == player_id and game.clan.your_cat.moons == -1
    assert game.clan.clan_settings["deputy"] and game.clan.clan_settings["leader"]
    assert not game.get_config_value("mates", "allow_manual")
    assert not game.get_config_value("ranks", "can_manually_change", "all")
    assert game.clan.leader_lives_granted == granted


def test_natural_leadership_and_mates_remain_available(profile):
    clan, cats, screen = profile
    clan.cruel_cards = ["fated_paths"]
    leader, deputy = cats
    clan.leader = leader
    leader.status = "leader"
    leader.dead = True
    clan.deputy = deputy
    deputy.status = "deputy"
    clan.clan_settings["leader"] = False
    Events().check_and_promote_leader()
    assert clan.leader is deputy and deputy.status == "leader"
    assert clan.leader_lives > 0
    leader.dead = False
    leader.status = "warrior"
    assert game.get_config_value("mates", "allow_mating")
    deputy.set_mate(leader)
    assert leader.ID in deputy.mates and deputy.ID in leader.mates


def test_deputy_offer_cannot_open_manual_appointment(profile):
    from scripts.game_structure.windows import DeputyScreen as DeputyOffer

    clan, cats, screen = profile
    clan.cruel_cards = ["fated_paths"]
    clan.deputy = cats[1]
    cats[1].status = "deputy"
    offer = DeputyOffer("profile screen")
    try:
        assert not offer.mediator_button.is_enabled
        offer.process_event(
            pygame.event.Event(
                pygame_gui.UI_BUTTON_START_PRESS, ui_element=offer.mediator_button
            )
        )
        assert clan.deputy is cats[1] and cats[1].status == "deputy"
        assert offer.alive()
    finally:
        offer.kill()


@pytest.mark.parametrize("setting", ["leader", "deputy"])
def test_forced_settings_cannot_be_switched_off(profile, setting):
    clan, cats, screen = profile
    clan.cruel_cards = ["fated_paths"]
    clan.clan_settings[setting] = False
    clan.switch_setting(setting)
    assert clan.clan_settings[setting]
    clan.switch_setting(setting)
    assert clan.clan_settings[setting]


def test_ordinary_manual_deputy_choice_registers_successor(profile):
    clan, cats, screen = profile
    old, new = cats
    old.status = "deputy"
    clan.deputy = old
    chooser = SimpleNamespace(exit_screen=Mock())
    DeputyScreen.change_cat(chooser, new)
    chooser.exit_screen.assert_called_once()
    assert old.status == "warrior"
    assert new.status == "deputy" and clan.deputy is new
    clan.clan_settings["leader"] = True
    Events().check_and_promote_leader()
    assert clan.leader is new and new.status == "leader"
