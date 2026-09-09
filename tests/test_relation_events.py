import os
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from scripts.cat.cats import Cat
from scripts.cat_relations.relationship import Relationship
from scripts.clan import Clan
from scripts.game_structure.game_essentials import game
from scripts.events_module.relationship.pregnancy_events import Pregnancy_Events
from scripts.events_module.relationship.romantic_events import Romantic_Events

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"


class CanHaveKits(unittest.TestCase):
    def test_prevent_kits(self):
        # given
        cat = Cat()
        cat.no_kits = True

        # then
        self.assertFalse(Pregnancy_Events.check_if_can_have_kits(cat, single_parentage=True, allow_affair=True))

    @patch('scripts.events_module.relationship.pregnancy_events.Pregnancy_Events.check_if_can_have_kits')
    def test_no_kit_setting(self, check_if_can_have_kits):
        # given
        test_clan = Clan(name="clan")
        test_clan.pregnancy_data = {}
        cat1 = Cat(gender='female')
        cat1.no_kits = True
        cat2 = Cat(gender='male')

        cat1.mates.append(cat2.ID)
        cat2.mates.append(cat1.ID)
        relation1 = Relationship(cat1, cat2, mates=True, family=False, romantic_love=100)
        relation2 = Relationship(cat2, cat1, mates=True, family=False, romantic_love=100)
        cat1.relationships[cat2.ID] = relation1
        cat2.relationships[cat1.ID] = relation2

        # when
        check_if_can_have_kits.return_value = True
        Pregnancy_Events.handle_having_kits(cat=cat1, clan=test_clan)

        # then
        self.assertNotIn(cat1.ID, test_clan.pregnancy_data.keys())


class SameSexAdoptions(unittest.TestCase):
    def test_kits_are_adopted(self):
        # given

        cat1 = Cat(gender='female', age="adult", moons=40)
        cat2 = Cat(gender='female', age="adult", moons=40)
        cat1.mates.append(cat2.ID)
        cat2.mates.append(cat1.ID)

        # when
        single_parentage = False
        allow_affair = False
        self.assertTrue(Pregnancy_Events.check_if_can_have_kits(cat1, single_parentage, allow_affair))
        self.assertTrue(Pregnancy_Events.check_if_can_have_kits(cat2, single_parentage, allow_affair))

        can_have_kits, kits_are_adopted = Pregnancy_Events.check_second_parent(
            cat=cat1,
            second_parent=cat2,
            single_parentage=single_parentage,
            allow_affair=allow_affair,
            same_sex_birth=False,
            same_sex_adoption=True
        )
        self.assertTrue(can_have_kits)
        self.assertTrue(kits_are_adopted)


class Pregnancy(unittest.TestCase):
    def setUp(self):
        cats = Cat.all_cats.copy()
        cat_list = list(Cat.all_cats_list)
        family = Pregnancy_Events.biggest_family
        clan_patch = patch.object(game, "clan", None)
        clan_patch.start()
        self.addCleanup(clan_patch.stop)

        def restore_cats():
            Cat.all_cats.clear()
            Cat.all_cats.update(cats)
            Cat.all_cats_list[:] = cat_list
            Pregnancy_Events.biggest_family = family

        self.addCleanup(restore_cats)

    def test_family_size_check_does_not_modify_cached_relatives(self):
        cat = Cat(moons=40)
        relatives = ["relative"]
        cat.inheritance = SimpleNamespace(all_involved=relatives)
        with patch.object(Cat, "all_cats", {cat.ID: cat}), patch.object(
            Pregnancy_Events, "biggest_family", []
        ):
            Pregnancy_Events.set_biggest_family()
            Pregnancy_Events.set_biggest_family()
            self.assertEqual(Pregnancy_Events.biggest_family, ["relative", cat.ID])
            self.assertEqual(cat.get_relatives(), ["relative"])

    def test_family_size_check_handles_no_cats(self):
        with patch.object(Cat, "all_cats", {}), patch.object(
            Pregnancy_Events, "biggest_family", []
        ):
            Pregnancy_Events.set_biggest_family()
            self.assertFalse(Pregnancy_Events.biggest_family_is_big())

    def test_entirely_stillborn_litter_still_completes_childbirth(self):
        clan = Clan(name="clan")
        cat = Cat(gender="female", moons=40)
        cat.injuries["pregnant"] = {"mortality": 40}
        clan.pregnancy_data = {cat.ID: {"moons": 2, "amount": 3}}
        with patch.object(game, "clan", clan), patch.object(game, "cur_events_list", []), patch.object(
            Pregnancy_Events, "get_kits", return_value=[]
        ), patch.object(Pregnancy_Events, "set_biggest_family"), patch.object(
            Pregnancy_Events, "handle_stillbirths"
        ) as stillbirths, patch(
            "scripts.events_module.relationship.pregnancy_events.random.random", return_value=0.5
        ), patch.object(cat, "get_injured") as get_injured:
            Pregnancy_Events.handle_two_moon_pregnant(cat, clan)
            get_injured.assert_called_once_with("recovering from birth", event_triggered=True)
            stillbirths.assert_called_once_with(cat, None, 3, clan)
            self.assertTrue(game.cur_events_list)
            self.assertNotIn("pregnant", cat.injuries)
            self.assertEqual(cat.birth_cooldown, game.config["pregnancy"]["birth_cooldown"])
            self.assertNotIn(cat.ID, clan.pregnancy_data)

    def test_childbirth_filters_do_not_modify_shared_event_strings(self):
        for branch, roll, mate_is_medic in (
            ("death", 0.0, False), ("difficult_birth", 0.5, False),
            ("death", 0.0, True), ("difficult_birth", 0.5, True),
        ):
            with self.subTest(branch=branch, mate_is_medic=mate_is_medic):
                clan = Clan(name="clan")
                cat = Cat(gender="female", moons=40)
                cat.injuries["pregnant"] = {"mortality": 40}
                if branch == "difficult_birth":
                    cat.injuries["blood loss"] = {}
                clan.pregnancy_data = {cat.ID: {"moons": 2, "amount": 1}}
                strings = deepcopy(Pregnancy_Events.PREGNANT_STRINGS)
                options = ["A medicine cat arrives.", "Another medicine cat arrives.", "The birth is difficult."]
                strings["birth"][branch] = list(options)
                kit = SimpleNamespace(ID="kit")
                med = SimpleNamespace(ID="med")
                if mate_is_medic:
                    cat.mates = [med.ID]
                with patch.object(game, "clan", clan), patch.object(game, "cur_events_list", []), patch.object(
                    Pregnancy_Events, "PREGNANT_STRINGS", strings
                ), patch.object(Pregnancy_Events, "get_kits", return_value=[kit]), patch.object(
                    Pregnancy_Events, "set_biggest_family"
                ), patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=roll), patch(
                    "scripts.events_module.relationship.pregnancy_events.get_alive_status_cats",
                    return_value=[med] if mate_is_medic else [],
                ), patch(
                    "scripts.events_module.relationship.pregnancy_events.choice", side_effect=lambda choices: choices[0]
                ), patch("scripts.events_module.relationship.pregnancy_events.History"), patch.object(
                    cat, "get_injured"
                ), patch.object(cat, "die"):
                    Pregnancy_Events.handle_two_moon_pregnant(cat, clan)
                    self.assertNotIn("medicine cat", game.cur_events_list[0].text)
                self.assertEqual(strings["birth"][branch], options)

    def test_no_kits_does_not_interrupt_an_existing_pregnancy(self):
        clan = Clan(name="clan")
        cat = Cat(gender='female', age="adult", moons=40)
        clan.pregnancy_data = {cat.ID: {"moons": 2, "amount": 1}}
        cat.no_kits = True

        with patch.object(Pregnancy_Events, "handle_two_moon_pregnant") as birth, patch.object(
            Pregnancy_Events, "check_if_can_have_kits"
        ) as conceive:
            Pregnancy_Events.handle_having_kits(cat, clan)
        birth.assert_called_once_with(cat, clan)
        conceive.assert_not_called()

    def test_birth_relationships_skip_missing_colony_member(self):
        clan = Clan(name="clan")
        parent = Cat(status="warrior", gender="female", moons=40)
        clan.clan_cats = ["missing-cat", parent.ID]
        clan.clan_settings["bigger_litters"] = False
        with patch.object(game, "clan", clan), patch.object(Cat, "all_cats", {parent.ID: parent}), patch(
            "scripts.events_module.relationship.pregnancy_events.History"
        ), patch("scripts.events_module.relationship.pregnancy_events.random.random", return_value=1.0):
            kits = Pregnancy_Events.get_kits(1, parent, clan=clan)
        self.assertEqual(len(kits), 1)
        self.assertIn(parent.ID, kits[0].relationships)
        self.assertIn(kits[0].ID, parent.relationships)
        self.assertNotIn("missing-cat", kits[0].relationships)

    def test_invalid_mates_are_pruned_without_skipping_entries(self):
        cat = Cat(gender='female', age="adult", moons=40)
        cat.mates = ["missing-1", "missing-2"]
        cat.all_cats = {}

        self.assertFalse(Pregnancy_Events.check_if_can_have_kits(cat, single_parentage=False, allow_affair=False))
        self.assertEqual(cat.mates, [])

    @patch('scripts.events_module.relationship.pregnancy_events.Pregnancy_Events.check_if_can_have_kits')
    def test_single_cat_female(self, check_if_can_have_kits):
        # given
        clan = Clan(name="clan")
        cat = Cat(gender='female', age="adult", moons=40)
        clan.pregnancy_data = {}

        # when
        check_if_can_have_kits.return_value = True
        Pregnancy_Events.handle_zero_moon_pregnant(cat, None, clan)

        # then
        self.assertIn(cat.ID, clan.pregnancy_data.keys())

    @patch('scripts.events_module.relationship.pregnancy_events.Pregnancy_Events.check_if_can_have_kits')
    def test_pair(self, check_if_can_have_kits):
        # given
        clan = Clan(name="clan")
        cat1 = Cat(gender='female', age="adult", moons=40)
        cat2 = Cat(gender='male', age="adult", moons=40)

        clan.pregnancy_data = {}

        # when
        check_if_can_have_kits.return_value = True
        Pregnancy_Events.handle_zero_moon_pregnant(cat1, cat2, clan)

        # then
        self.assertIn(cat1.ID, clan.pregnancy_data.keys())
        self.assertEqual(clan.pregnancy_data[cat1.ID]["second_parent"], cat2.ID)


class Mates(unittest.TestCase):
    def test_platonic_kitten_mating(self):
        # given
        cat1 = Cat(moons=3)
        cat2 = Cat(moons=3)

        relationship1 = Relationship(cat1, cat2)
        relationship2 = Relationship(cat2, cat1)
        relationship1.opposite_relationship = relationship2
        relationship2.opposite_relationship = relationship1
        cat1.relationships[cat2.ID] = relationship1
        cat2.relationships[cat1.ID] = relationship2

        # when
        relationship1.platonic_like = 100
        relationship2.platonic_like = 100

        # then
        self.assertFalse(Romantic_Events.check_if_new_mate(cat1, cat2)[0])

    def test_platonic_apprentice_mating(self):
        # given
        cat1 = Cat(moons=6)
        cat2 = Cat(moons=6)

        relationship1 = Relationship(cat1, cat2)
        relationship2 = Relationship(cat2, cat1)
        relationship1.opposite_relationship = relationship2
        relationship2.opposite_relationship = relationship1
        cat1.relationships[cat2.ID] = relationship1
        cat2.relationships[cat1.ID] = relationship2

        # when
        relationship1.platonic_like = 100
        relationship2.platonic_like = 100

        # then
        self.assertFalse(Romantic_Events.check_if_new_mate(cat1, cat2)[0])

    def test_romantic_kitten_mating(self):
        # given
        cat1 = Cat(moons=3)
        cat2 = Cat(moons=3)

        relationship1 = Relationship(cat1, cat2)
        relationship2 = Relationship(cat2, cat1)
        relationship1.opposite_relationship = relationship2
        relationship2.opposite_relationship = relationship1
        cat1.relationships[cat2.ID] = relationship1
        cat2.relationships[cat1.ID] = relationship2

        # when
        relationship1.romantic_love = 100
        relationship2.romantic_love = 100

        # then
        self.assertFalse(Romantic_Events.check_if_new_mate(cat1, cat2)[0])

    def test_romantic_apprentice_mating(self):
        # given
        cat1 = Cat(moons=6)
        cat2 = Cat(moons=6)

        relationship1 = Relationship(cat1, cat2)
        relationship2 = Relationship(cat2, cat1)
        relationship1.opposite_relationship = relationship2
        relationship2.opposite_relationship = relationship1
        cat1.relationships[cat2.ID] = relationship1
        cat2.relationships[cat1.ID] = relationship2

        # when
        relationship1.romantic_love = 100
        relationship2.romantic_love = 100

        # then
        self.assertFalse(Romantic_Events.check_if_new_mate(cat1, cat2)[0])
