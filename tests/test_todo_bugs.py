from types import SimpleNamespace

import pygame
import pytest

from scripts.cat.cats import Cat
from scripts.cat.names import Name
from scripts.clan import OtherClan
from scripts.events import Events
from scripts.screens.ListScreen import ListScreen
from scripts.utility import change_clan_relations
from scripts.game_structure.game_essentials import game
from tests.test_condition_modernization import clinic
from tests.test_profile_modernization import profile
from tests.test_leader_den import den
from tests.test_naming_workflows import naming, press, reload_cat
from tests.test_newborn_relationships import family
from scripts.game_structure.windows import ChangeCatName
from scripts.events_module.relationship.pregnancy_events import Pregnancy_Events
from scripts.events_module.patrol.patrol_outcome import PatrolOutcome


@pytest.mark.parametrize("group", ["sc", "df", "ur", "cotc"])
def test_cat_list_preserves_current_group_without_a_profile_override(
    clinic, monkeypatch, group
):
    clan, first, second = clinic
    monkeypatch.setattr(game, "last_list_forProfile", None)
    screen = ListScreen("list screen")
    {
        "sc": screen.get_sc_cats,
        "df": screen.get_df_cats,
        "ur": screen.get_ur_cats,
        "cotc": screen.get_cotc_cats,
    }[group]()
    screen.get_cat_list()
    assert screen.current_group == group
    assert screen.death_status == ("living" if group == "cotc" else "dead")


def test_profile_condition_cards_align_with_their_actual_background(profile):
    clan, cats, screen = profile
    cats[0].get_injured("bruises")
    screen.toggle_conditions_tab()
    screen.display_conditions_page()
    for key, panel in screen.condition_data.items():
        if key.startswith("bg_"):
            assert screen.conditions_background.rect.contains(panel.rect), (
                screen.conditions_background.rect,
                panel.rect,
            )
            assert panel.rect.top >= screen.conditions_background.rect.top + 15


@pytest.mark.parametrize(
    "prefix,suffix,kind,expected",
    [
        ("River ", "Song", "ancient", "River Song"),
        ("River  ", " Song", "ancient", "River   Song"),
        (" River ", "Song", "warrior", " River Song"),
    ],
)
def test_name_formatter_preserves_explicit_component_spacing(
    prefix, suffix, kind, expected
):
    assert Name.format_components(prefix, suffix, kind) == expected


@pytest.mark.parametrize(
    "initial,delta,expected", [(20, -3, 17), (2, -3, 0), (20, 3, 23)]
)
def test_intercolony_relation_deltas_reach_the_neighbor(
    clinic, initial, delta, expected
):
    clan, first, second = clinic
    neighbor = OtherClan(
        name="Neighbor", relations=initial, chosen_symbol="symbolBEECH0"
    )
    clan.all_clans = [neighbor]
    change_clan_relations(neighbor, delta)
    assert neighbor.relations == expected


def test_disabled_warrior_style_cannot_be_reintroduced_by_parent_inheritance(clinic):
    clan, parent, other = clinic
    clan.clan_settings.update(
        warrior_names=False,
        ancient_names=False,
        single_names=True,
        syllable_names=False,
        kit_inherit_naming=True,
    )
    parent.name.name_type = "warrior"
    kitten = Cat(status="newborn", moons=0, parent1=parent.ID)
    assert kitten.name.name_type == "single"
    assert kitten.name.specsuffix_hidden


@pytest.mark.parametrize("style", ["ancient", "single", "syllable"])
def test_real_birth_uses_enabled_style_with_warrior_parents(
    family, monkeypatch, tmp_path, style
):
    clan, _, parent, partner, *_ = family
    for kind in ("warrior", "ancient", "single", "syllable"):
        clan.clan_settings[kind + "_names"] = kind == style
    clan.clan_settings["kit_inherit_naming"] = True
    parent.name.name_type = partner.name.name_type = "warrior"
    kittens = Pregnancy_Events.get_kits(3, parent, partner, clan=clan)
    assert len(kittens) == 3
    assert {kit.name.name_type for kit in kittens} == {style}
    monkeypatch.setattr(
        "scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path)
    )
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    assert reload_cat(kittens[0]).name.name_type == style


@pytest.mark.parametrize(
    "prefix,suffix,expected,style",
    [
        ("River", "Song", "RiverSong", "warrior"),
        ("River  ", " Song", "River   Song", "ancient"),
        ("River", "Long Song", "RiverLong Song", "warrior"),
    ],
)
def test_native_rename_retains_typed_spacing_after_reload(
    naming, prefix, suffix, expected, style
):
    clan, cat, elements = naming
    cat.name.name_type = "ancient"
    cat.name.specsuffix_hidden = True
    window = ChangeCatName(cat)
    window.prefix_entry_box.set_text(prefix)
    window.suffix_entry_box.set_text(suffix)
    press(window, window.done_button)
    assert str(cat.name) == expected
    restored = reload_cat(cat)
    assert str(restored.name) == expected
    assert restored.name.name_type == style


@pytest.mark.parametrize("route", ["patrol", "sabotage", "drift"])
def test_negative_relations_from_active_gameplay_routes(clinic, monkeypatch, route):
    clan, first, second = clinic
    neighbor = OtherClan(name="Neighbor", relations=21, chosen_symbol="symbolBEECH0")
    clan.all_clans = [neighbor]
    clan.age = 3
    clan.clan_settings["relation drift"] = route == "drift"
    events = Events()
    if route == "patrol":
        outcome = object.__new__(PatrolOutcome)
        outcome.other_clan_rep = -3
        result = outcome._handle_other_clan_relations(
            SimpleNamespace(other_clan=neighbor)
        )
        assert "worsened" in result
        expected = 18
    elif route == "sabotage":
        for focus in (
            "business as usual",
            "rest and recover",
            "hunting",
            "herb gathering",
            "seek outsiders",
            "socializing",
            "hoarding",
            "aid other clans",
        ):
            clan.clan_settings[focus] = False
        clan.clan_settings["sabotage other clans"] = True
        clan.clans_in_focus = [neighbor.name]
        events.handle_focus()
        expected = 21 - game.config["focus"]["other clans"]["relation"]
    else:
        events.apply_relation_decay()
        expected = 20
        assert game.cur_events_list
        assert "other_clans" in game.cur_events_list[-1].types
    assert neighbor.relations == expected


def test_diplomacy_displays_decreases_within_the_ally_category(den):
    clan, leader, outsider, neighbor, screen = den
    neighbor.relations = 21
    screen.screen_switches()
    assert "21" in screen.focus_clan_elements["clan_rel"].text
    change_clan_relations(neighbor, -3)
    screen.exit_screen()
    screen.screen_switches()
    assert "18" in screen.focus_clan_elements["clan_rel"].text
    assert "18" in screen.other_clan_selection_elements["clan_rel0"].text


def test_changing_enabled_styles_invalidates_a_cached_litter_style(clinic):
    clan, parent, other = clinic
    clan.clan_settings.update(
        warrior_names=True,
        ancient_names=False,
        single_names=False,
        syllable_names=False,
        kit_inherit_naming=True,
    )
    parent.name.name_type = "warrior"
    first = Cat(status="newborn", moons=0, parent1=parent.ID)
    assert first.name.name_type == "warrior"
    clan.clan_settings.update(warrior_names=False, single_names=True)
    second = Cat(status="newborn", moons=0, parent1=parent.ID)
    assert second.name.name_type == "single"


@pytest.mark.parametrize("group", ["sc", "df", "ur", "cotc"])
def test_native_cat_list_return_keeps_selected_group(clinic, monkeypatch, group):
    clan, cat, other = clinic
    monkeypatch.setattr(game, "last_list_forProfile", None)
    monkeypatch.setattr(
        "scripts.utility.generate_sprite",
        lambda *args, **kwargs: pygame.Surface((50, 50), pygame.SRCALPHA),
    )
    clan.instructor = cat
    clan.demon = other
    clan.wanderer = cat
    screen = ListScreen("list screen")
    screen.current_group = group
    try:
        screen.screen_switches()
        assert screen.current_group == group
        screen.exit_screen()
        screen.screen_switches()
        assert screen.current_group == group
        assert game.last_list_forProfile is None
    finally:
        screen.exit_screen()


def test_changing_only_an_ancient_prefix_preserves_the_existing_separator(naming):
    clan, cat, elements = naming
    cat.name.name_type = "ancient"
    cat.name.specsuffix_hidden = True
    window = ChangeCatName(cat)
    window.prefix_entry_box.set_text("River")
    press(window, window.done_button)
    assert str(reload_cat(cat).name) == "River heart"


@pytest.mark.parametrize(
    "style,prefix,suffix,tail",
    [
        ("warrior", "Moss", "heart", "kit"),
        ("ancient", "Moss", "Song", " Song"),
        ("single", "Moss", "", ""),
        ("syllable", "Moss", "", ""),
    ],
)
def test_newborn_naming_fields_match_the_kittens_actual_style(
    naming, monkeypatch, style, prefix, suffix, tail
):
    from unittest.mock import Mock
    from scripts.screens.NameKitsScreen import NameKitsScreen

    clan, cat, elements = naming
    monkeypatch.setattr(
        "scripts.utility.generate_sprite",
        lambda *args, **kwargs: pygame.Surface((50, 50), pygame.SRCALPHA),
    )
    cat.status = "newborn"
    cat.moons = 0
    cat.name = Name(
        prefix=prefix,
        suffix=suffix,
        name_type=style,
        cat=cat,
        specsuffix_hidden=style != "warrior",
        load_existing_name=True,
    )
    screen = NameKitsScreen("name kits screen")
    screen.selected_cat = cat
    screen.confirm_mentor = Mock()
    screen.update_selected_cat()
    elements.extend(screen.selected_details.values())
    assert screen.selected_details["name_entry"].get_text() == prefix
    assert screen.selected_details["clan"].html_text == tail
    assert not screen.selected_details["clan"].rect.colliderect(
        screen.selected_details["name_entry"].rect
    )
    screen.change_cat()
    assert str(reload_cat(cat).name) == prefix + tail
