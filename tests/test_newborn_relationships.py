from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.cat_relations.relationship import Relationship
from scripts.clan import Clan
from scripts.events_module.relationship.pregnancy_events import Pregnancy_Events
from scripts.game_structure.game_essentials import game


@pytest.fixture
def family(monkeypatch, tmp_path):
    for target, name, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                                (Cat, "outside_cats", {}), (Cat, "dead_cats", []),
                                (Inheritance, "all_inheritances", {})):
        monkeypatch.setattr(target, name, value)
    clan = Clan(name="NewbornTest", camp_bg="camp1", game_mode="expanded")
    clan.clan_settings["bigger_litters"] = False
    monkeypatch.setattr(game, "clan", clan)
    monkeypatch.setattr(game, "switches", {**game.switches, "clan_name": clan.name, "clan_list": [clan.name]})
    monkeypatch.setattr(game, "cur_events_list", [])
    for module in ("scripts.cat.cats", "scripts.clan", "scripts.game_structure.game_essentials"):
        monkeypatch.setattr(module + ".get_save_dir", lambda: str(tmp_path))
    def save(path, data, **kwargs):
        assert Path(path).resolve().is_relative_to(tmp_path.resolve())
        return type(game).safe_save(path, data, **kwargs)
    monkeypatch.setattr(game, "safe_save", save)
    grandparent = Cat(prefix="Grand", gender="female", moons=90, status="elder")
    parent = Cat(prefix="Parent", gender="female", moons=40, status="warrior", parent1=grandparent.ID)
    partner = Cat(prefix="Partner", gender="male", moons=40, status="warrior")
    aunt = Cat(prefix="Aunt", gender="female", moons=40, status="warrior", parent1=grandparent.ID)
    sibling = Cat(prefix="Sibling", gender="male", moons=15, status="apprentice", parent1=parent.ID, parent2=partner.ID)
    unrelated = Cat(prefix="Unrelated", gender="female", moons=40, status="warrior")
    for cat in (grandparent, parent, partner, aunt, sibling, unrelated):
        cat.history = History()
        clan.add_cat(cat)
        cat.create_inheritance_new_cat()
    clan.your_cat = parent
    for relative in (grandparent, aunt, sibling):
        relative.relationships[parent.ID] = Relationship(relative, parent, platonic_like=80, comfortable=40,
                                                          admiration=20, trust=60)
        relative.relationships[partner.ID] = Relationship(relative, partner, platonic_like=40, comfortable=20,
                                                           admiration=20, trust=20)
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=.99), patch(
            "scripts.events_module.relationship.pregnancy_events.random.randrange", return_value=0):
        yield clan, grandparent, parent, partner, aunt, sibling, unrelated


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
@pytest.mark.parametrize("two_parents", [False, True])
def test_extended_family_reflects_parent_relationships_after_real_birth(family, mode, two_parents):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    clan.game_mode = mode
    originals = {cat.ID: deepcopy(cat.relationships[parent.ID].log) for cat in (grandparent, aunt, sibling)}
    kits = Pregnancy_Events.get_kits(2, parent, partner if two_parents else None, clan=clan)
    expected = (30, 15, 10, 20) if two_parents else (40, 20, 10, 30)
    assert len(kits) == 2
    for kit in kits:
        for relative in (grandparent, aunt, sibling):
            relation = relative.relationships[kit.ID]
            assert (relation.platonic_like, relation.comfortable, relation.admiration, relation.trust) == expected
            assert relation.romantic_love == relation.jealousy == relation.dislike == 0
            assert len(relation.log) == 1 and "positive effect" in relation.log[0]
            assert str(relative.name) in relation.log[0] and "0 moon old" in relation.log[0]
            assert not any(token in relation.log[0] for token in ("m_c", "r_c", "{PRONOUN"))
            assert kit.relationships[relative.ID].platonic_like == 0
        assert not unrelated.relationships[kit.ID].log
        assert parent.relationships[kit.ID].platonic_like == game.config["new_cat"]["parent_buff"]["parent_to_kit"]["platonic"]
        assert kit.relationships[parent.ID].trust == game.config["new_cat"]["parent_buff"]["kit_to_parent"]["trust"]
        other_kit = next(other for other in kits if other != kit)
        assert kit.relationships[other_kit.ID].platonic_like == 20
        assert not kit.relationships[other_kit.ID].log
    for cat in (grandparent, aunt, sibling):
        assert cat.relationships[parent.ID].platonic_like == 80
        assert cat.relationships[parent.ID].log == originals[cat.ID]


def test_adoptive_relatives_are_reflected_after_parent_assignment(family):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    kit = Pregnancy_Events.get_kits(1, clan=clan, adoptive_parents=[parent.ID])[0]
    assert parent.ID in kit.adoptive_parents
    assert grandparent.ID in kit.get_relatives()
    assert grandparent.relationships[kit.ID].platonic_like == 20
    assert len(grandparent.relationships[kit.ID].log) == 1
    assert parent.relationships[kit.ID].platonic_like == game.config["new_cat"]["parent_buff"]["parent_to_kit"]["platonic"]
    assert not parent.relationships[kit.ID].log


@pytest.mark.parametrize("state", ["dead", "outside", "exiled", "nonmember"])
def test_absent_relatives_do_not_react(family, state):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    if state == "nonmember":
        clan.clan_cats.remove(aunt.ID)
    else:
        setattr(aunt, state, True)
    kit = Pregnancy_Events.get_kits(1, parent, clan=clan)[0]
    relation = aunt.relationships.get(kit.ID)
    assert relation is None or (not relation.log and relation.platonic_like == 0)


def test_hostility_uses_dislike_without_romance_or_schema_changes(family):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    grandparent.relationships[parent.ID].platonic_like = 0
    grandparent.relationships[parent.ID].dislike = 80
    kit = Pregnancy_Events.get_kits(1, parent, clan=clan)[0]
    relation = grandparent.relationships[kit.ID]
    assert relation.dislike == 40 and relation.platonic_like == 0
    assert relation.romantic_love == 0 and relation.jealousy == 0
    assert "neutral effect" in relation.log[0]
    assert grandparent.relationships[parent.ID].dislike == 80


def test_zero_surviving_kits_does_not_create_reactions(family):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    before = set(grandparent.relationships)
    assert Pregnancy_Events.get_kits(0, parent, clan=clan) == []
    assert set(grandparent.relationships) == before


def test_missing_parent_relationship_does_not_invent_affection(family):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    aunt.relationships.clear()
    kit = Pregnancy_Events.get_kits(1, parent, clan=clan)[0]
    relation = aunt.relationships[kit.ID]
    assert relation.platonic_like == relation.dislike == relation.comfortable == relation.admiration == relation.trust == 0
    assert parent.ID not in aunt.relationships


@pytest.mark.parametrize("outside_flag", ["outside", "exiled"])
def test_outside_births_do_not_gain_colony_family_visits(family, outside_flag):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    setattr(parent, outside_flag, True)
    kit = Pregnancy_Events.get_kits(1, parent, clan=clan)[0]
    assert not grandparent.relationships[kit.ID].log
    assert grandparent.relationships[kit.ID].platonic_like == 0


def test_negative_reaction_text_and_clamped_metrics(family):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    relation = grandparent.relationships[parent.ID]
    for field in ("platonic_like", "comfortable", "admiration", "trust"):
        setattr(relation, field, 10)
    def variation(start, stop):
        return -19 if start < 0 else 0
    with patch("scripts.events_module.relationship.pregnancy_events.random.randrange", side_effect=variation):
        kit = Pregnancy_Events.get_kits(1, parent, clan=clan)[0]
    reaction = grandparent.relationships[kit.ID]
    assert reaction.dislike == 14
    assert reaction.platonic_like == reaction.comfortable == reaction.admiration == reaction.trust == 0
    assert "negative effect" in reaction.log[0]
    assert not any(token in reaction.log[0] for token in ("m_c", "r_c", "{PRONOUN"))


def test_duplicate_or_missing_relative_ids_do_not_repeat_reactions_or_mutate_cache(family):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    relatives = [grandparent.ID, grandparent.ID, "missing relative", parent.ID]
    original = relatives.copy()
    with patch.object(Cat, "get_relatives", return_value=relatives):
        kits = Pregnancy_Events.get_kits(2, parent, clan=clan)
    assert relatives == original
    for kit in kits:
        assert grandparent.relationships[kit.ID].platonic_like == 40
        assert len(grandparent.relationships[kit.ID].log) == 1
        assert not parent.relationships[kit.ID].log


def test_configured_reflection_and_multiple_adoptive_parents(family):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    parent.mates.append(partner.ID)
    partner.mates.append(parent.ID)
    with patch.dict(game.config["new_cat"], {"ext_relative_modifier": 4}):
        kit = Pregnancy_Events.get_kits(1, clan=clan, adoptive_parents=[parent.ID, partner.ID])[0]
    assert set(kit.adoptive_parents) == {parent.ID, partner.ID}
    # The source divisor counts both adoptive parents and the recorded biological parent.
    assert grandparent.relationships[kit.ID].platonic_like == int(80 / 12) + int(40 / 12)
    assert grandparent.relationships[kit.ID].romantic_love == 0


def test_all_stillborn_litter_does_not_create_family_reactions(family):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    clan.clan_settings["bigger_litters"] = True
    with patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=0):
        kits = Pregnancy_Events.get_kits(2, parent, clan=clan)
    assert kits == []
    assert all(not relation.log for relation in grandparent.relationships.values())


@pytest.mark.parametrize("mode", ["classic", "expanded", "cruel season"])
def test_real_birth_and_full_save_reload_preserve_family_reactions(family, monkeypatch, tmp_path, mode):
    from scripts.game_structure.load_cat import load_cats

    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    clan.game_mode = mode
    clan.leader = partner
    clan.starting_members = list(Cat.all_cats.values())
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr(game, "save_clanlist", Mock())
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    for method in ("generate_mates", "generate_families", "populate_sc", "populate_ur", "populate_df"):
        monkeypatch.setattr(clan, method, Mock())
    clan.create_clan()
    grandparent.relationships[parent.ID] = Relationship(grandparent, parent, platonic_like=80,
                                                        comfortable=40, admiration=20, trust=60)
    grandparent.relationships[partner.ID] = Relationship(grandparent, partner, platonic_like=40,
                                                         comfortable=20, admiration=20, trust=20)
    clan.pregnancy_data[parent.ID] = {"moons": 2, "amount": 2, "second_parent": partner.ID}
    parent.get_injured("pregnant")
    parent.mates.append(partner.ID)
    partner.mates.append(parent.ID)
    monkeypatch.setattr(Pregnancy_Events, "biggest_family", {})
    monkeypatch.setattr(game, "cat_class", Cat)
    monkeypatch.setattr(game, "cat_to_fade", [])
    monkeypatch.setattr("scripts.game_structure.load_cat.get_save_dir", lambda: str(tmp_path))
    monkeypatch.setattr("scripts.clan.clan_symbol_sprite", lambda *args, **kwargs: "symbolBEECH0")
    Pregnancy_Events.handle_two_moon_pregnant(parent, clan)
    kits = [cat for cat in Cat.all_cats.values() if cat.status == "newborn" and not cat.dead]
    assert len(kits) == 2 and parent.ID not in clan.pregnancy_data
    assert game.cur_events_list
    for kit in kits:
        assert len(grandparent.relationships[kit.ID].log) == 1
    game.save_cats()
    clan.save_clan()
    expected = {kit.ID: deepcopy(grandparent.relationships[kit.ID].log) for kit in kits}
    grandparent_id, parent_id, partner_id = grandparent.ID, parent.ID, partner.ID
    Cat.all_cats.clear()
    Cat.all_cats_list.clear()
    Inheritance.all_inheritances.clear()
    load_cats()
    Clan().load_clan()
    restored = Cat.all_cats[grandparent_id]
    for kit_id, log in expected.items():
        assert restored.relationships[kit_id].log == log
        assert restored.relationships[kit_id].platonic_like == 30
        kit = Cat.all_cats[kit_id]
        assert {parent_id, partner_id} <= set(kit.get_parents())
        assert grandparent_id in kit.get_relatives()



def test_mixed_survival_litter_only_receives_reactions_for_surviving_kits(family):
    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    clan.clan_settings["bigger_litters"] = True
    with patch.object(Pregnancy_Events, "check_kit_mortality", side_effect=[True, False]) as mortality:
        kits = Pregnancy_Events.get_kits(2, parent, clan=clan)
    assert mortality.call_count == 2 and len(kits) == 1
    assert len(grandparent.relationships[kits[0].ID].log) == 1
    dead_kits = [cat for cat in Cat.all_cats.values() if cat.dead and cat.parent1 == parent.ID]
    assert len(dead_kits) == 1
    assert dead_kits[0].ID not in grandparent.relationships


@pytest.mark.parametrize("kind", ["positive_log", "neutral_log", "negative_log"])
def test_released_reaction_text_renders_every_name_and_pronoun(family, kind):
    from scripts.utility import event_text_adjust

    clan, grandparent, parent, partner, aunt, sibling, unrelated = family
    kit = Pregnancy_Events.get_kits(1, parent, clan=clan)[0]
    for text in Pregnancy_Events.NEWBORN_REL_REACTIONS[kind]:
        rendered = event_text_adjust(Cat, text, main_cat=grandparent, random_cat=kit, clan=clan)
        assert str(grandparent.name) in rendered
        assert not any(token in rendered for token in ("m_c", "r_c", "{PRONOUN", "{VERB"))
