import os
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from scripts.cat.cats import Cat, create_example_cats
from scripts.cat.names import Name
from scripts.cat_relations.relationship import Relationship
from scripts.game_structure.game_essentials import game

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"


class TestCreationAge(unittest.TestCase):
    # test that a cat with 1-5 moons has the age of a kitten
    def test_kitten(self):
        test_cat = Cat(moons=5)
        self.assertEqual(test_cat.age, "kitten")

    # test that a cat with 6-11 moons has the age of an adolescent
    def test_adolescent(self):
        test_cat = Cat(moons=6)
        self.assertEqual(test_cat.age, "adolescent")

    # test that a cat with 12-47 moons has the age of a young adult
    def test_young_adult(self):
        test_cat = Cat(moons=12)
        self.assertEqual(test_cat.age, "young adult")

    # test that a cat with 48-95 moons has the age of an adult
    def test_adult(self):
        test_cat = Cat(moons=48)
        self.assertEqual(test_cat.age, "adult")

    # test that a cat with 96-119 moons has the age of a senior adult
    def test_senior_adult(self):
        test_cat = Cat(moons=96)
        self.assertEqual(test_cat.age, "senior adult")

    # test that a cat with 120-300 moons has the age of a senior
    def test_elder(self):
        test_cat = Cat(moons=120)
        self.assertEqual(test_cat.age, "senior")


class TestRelativesFunction(unittest.TestCase):
    # test that is_parent returns True for a parent1-cat relationship and False otherwise
    def test_is_parent(self):
        parent = Cat()
        kit = Cat(parent1=parent.ID)
        self.assertFalse(kit.is_parent(kit))
        self.assertFalse(kit.is_parent(parent))
        self.assertTrue(parent.is_parent(kit))

    # test that is_sibling returns True for cats with a shared parent1 and False otherwise
    def test_is_sibling(self):
        parent = Cat()
        kit1 = Cat(parent1=parent.ID)
        kit2 = Cat(parent1=parent.ID)
        self.assertFalse(parent.is_sibling(kit1))
        self.assertFalse(kit1.is_sibling(parent))
        self.assertTrue(kit2.is_sibling(kit1))
        self.assertTrue(kit1.is_sibling(kit2))

    # test that is_uncle_aunt returns True for a uncle/aunt-cat relationship and False otherwise
    def test_is_uncle_aunt(self):
        grand_parent = Cat()
        sibling1 = Cat(parent1=grand_parent.ID)
        sibling2 = Cat(parent1=grand_parent.ID)
        kit = Cat(parent1=sibling1.ID)
        self.assertFalse(sibling1.is_uncle_aunt(kit))
        self.assertFalse(sibling1.is_uncle_aunt(sibling2))
        self.assertFalse(kit.is_uncle_aunt(sibling2))
        self.assertTrue(sibling2.is_uncle_aunt(kit))

    # test that is_grandparent returns True for a grandparent-cat relationship and False otherwise
    def test_is_grandparent(self):
        grand_parent = Cat()
        sibling1 = Cat(parent1=grand_parent.ID)
        sibling2 = Cat(parent1=grand_parent.ID)
        kit = Cat(parent1=sibling1.ID)
        self.assertFalse(sibling1.is_grandparent(kit))
        self.assertFalse(sibling1.is_grandparent(sibling2))
        self.assertFalse(kit.is_grandparent(sibling2))
        self.assertFalse(sibling2.is_grandparent(kit))
        self.assertFalse(kit.is_grandparent(grand_parent))
        self.assertTrue(grand_parent.is_grandparent(kit))


class TestPossibleMateFunction(unittest.TestCase):
    # test that is_potential_mate returns False for cats that are related to each other
    def test_relation(self):
        grand_parent = Cat()
        sibling1 = Cat(parent1=grand_parent.ID)
        sibling2 = Cat(parent1=grand_parent.ID)
        kit = Cat(parent1=sibling1.ID)
        self.assertFalse(kit.is_potential_mate(grand_parent))
        self.assertFalse(kit.is_potential_mate(sibling1))
        self.assertFalse(kit.is_potential_mate(sibling2))
        self.assertFalse(kit.is_potential_mate(kit))
        self.assertFalse(sibling1.is_potential_mate(grand_parent))
        self.assertFalse(sibling1.is_potential_mate(sibling1))
        self.assertFalse(sibling1.is_potential_mate(sibling2))
        self.assertFalse(sibling1.is_potential_mate(kit))

    # test that is_potential_mate returns False for cats that are related to each other even if for_love_interest is True
    def test_relation_love_interest(self):
        grand_parent = Cat()
        sibling1 = Cat(parent1=grand_parent.ID)
        sibling2 = Cat(parent1=grand_parent.ID)
        kit = Cat(parent1=sibling1.ID)
        self.assertFalse(kit.is_potential_mate(grand_parent, for_love_interest=True))
        self.assertFalse(kit.is_potential_mate(sibling1, for_love_interest=True))
        self.assertFalse(kit.is_potential_mate(sibling2, for_love_interest=True))
        self.assertFalse(kit.is_potential_mate(kit, for_love_interest=True))
        self.assertFalse(
            sibling1.is_potential_mate(grand_parent, for_love_interest=True)
        )
        self.assertFalse(sibling1.is_potential_mate(sibling1, for_love_interest=True))
        self.assertFalse(sibling1.is_potential_mate(sibling2, for_love_interest=True))
        self.assertFalse(sibling1.is_potential_mate(kit, for_love_interest=True))
        self.assertFalse(sibling2.is_potential_mate(sibling1, for_love_interest=True))

    # test is_potential_mate for age checks
    def test_age_mating(self):
        kitten_cat2 = Cat(moons=1)
        kitten_cat1 = Cat(moons=1)
        adolescent_cat1 = Cat(moons=6)
        adolescent_cat2 = Cat(moons=6)
        too_young_adult_cat1 = Cat(moons=12)
        too_young_adult_cat2 = Cat(moons=12)
        young_adult_cat1 = Cat(moons=20)
        young_adult_cat2 = Cat(moons=20)
        adult_cat_in_range1 = Cat(moons=60)
        adult_cat_in_range2 = Cat(moons=60)
        adult_cat_out_range1 = Cat(moons=65)
        adult_cat_out_range2 = Cat(moons=65)
        senior_adult_cat1 = Cat(moons=96)
        senior_adult_cat2 = Cat(moons=96)
        elder_cat1 = Cat(moons=120)
        elder_cat2 = Cat(moons=120)

        # check for cat mating with itself
        self.assertFalse(kitten_cat1.is_potential_mate(kitten_cat1))

        # check for setting
        self.assertFalse(
            senior_adult_cat1.is_potential_mate(
                young_adult_cat1, for_love_interest=False, age_restriction=True
            )
        )
        self.assertTrue(
            senior_adult_cat1.is_potential_mate(
                young_adult_cat1, for_love_interest=False, age_restriction=False
            )
        )

        # check invalid constellations
        self.assertFalse(kitten_cat1.is_potential_mate(kitten_cat2))
        self.assertFalse(kitten_cat1.is_potential_mate(adolescent_cat1))
        self.assertFalse(kitten_cat1.is_potential_mate(young_adult_cat1))
        self.assertFalse(kitten_cat1.is_potential_mate(adult_cat_in_range1))
        self.assertFalse(kitten_cat1.is_potential_mate(senior_adult_cat1))
        self.assertFalse(kitten_cat1.is_potential_mate(elder_cat1))

        self.assertFalse(adolescent_cat1.is_potential_mate(kitten_cat2))
        self.assertFalse(adolescent_cat1.is_potential_mate(adolescent_cat2))
        self.assertFalse(adolescent_cat1.is_potential_mate(too_young_adult_cat2))
        self.assertFalse(adolescent_cat1.is_potential_mate(young_adult_cat1))
        self.assertFalse(adolescent_cat1.is_potential_mate(adult_cat_in_range1))
        self.assertFalse(adolescent_cat1.is_potential_mate(senior_adult_cat1))
        self.assertFalse(adolescent_cat1.is_potential_mate(elder_cat1))

        self.assertFalse(too_young_adult_cat1.is_potential_mate(too_young_adult_cat2))

        self.assertFalse(young_adult_cat1.is_potential_mate(kitten_cat2))
        self.assertFalse(young_adult_cat1.is_potential_mate(adolescent_cat1))
        self.assertFalse(young_adult_cat1.is_potential_mate(adult_cat_out_range1))
        self.assertFalse(young_adult_cat1.is_potential_mate(senior_adult_cat1))
        self.assertFalse(young_adult_cat1.is_potential_mate(elder_cat1))

        self.assertFalse(adult_cat_out_range1.is_potential_mate(kitten_cat2))
        self.assertFalse(adult_cat_out_range1.is_potential_mate(adolescent_cat1))
        self.assertFalse(adult_cat_out_range1.is_potential_mate(young_adult_cat1))
        self.assertFalse(adult_cat_out_range1.is_potential_mate(elder_cat1))

        self.assertFalse(senior_adult_cat1.is_potential_mate(kitten_cat1))
        self.assertFalse(senior_adult_cat1.is_potential_mate(adolescent_cat1))
        self.assertFalse(senior_adult_cat1.is_potential_mate(young_adult_cat1))

        # check valid constellations
        self.assertTrue(young_adult_cat1.is_potential_mate(young_adult_cat2))
        self.assertTrue(young_adult_cat1.is_potential_mate(adult_cat_in_range1))
        self.assertTrue(adult_cat_in_range1.is_potential_mate(young_adult_cat1))
        self.assertTrue(adult_cat_in_range1.is_potential_mate(adult_cat_in_range2))
        self.assertTrue(adult_cat_in_range1.is_potential_mate(adult_cat_out_range1))
        self.assertTrue(adult_cat_out_range1.is_potential_mate(adult_cat_out_range2))
        self.assertTrue(adult_cat_out_range1.is_potential_mate(senior_adult_cat1))
        self.assertTrue(senior_adult_cat1.is_potential_mate(adult_cat_out_range1))
        self.assertTrue(senior_adult_cat1.is_potential_mate(senior_adult_cat2))
        self.assertTrue(senior_adult_cat1.is_potential_mate(elder_cat1))
        self.assertTrue(elder_cat1.is_potential_mate(senior_adult_cat1))
        self.assertTrue(elder_cat1.is_potential_mate(elder_cat2))

    # test is_potential_mate for age checks with for_love_interest set to True
    def test_age_love_interest(self):
        kitten_cat2 = Cat(moons=1)
        kitten_cat1 = Cat(moons=1)
        adolescent_cat1 = Cat(moons=6)
        adolescent_cat2 = Cat(moons=6)
        young_adult_cat1 = Cat(moons=12)
        young_adult_cat2 = Cat(moons=12)
        adult_cat_in_range1 = Cat(moons=52)
        adult_cat_in_range2 = Cat(moons=52)
        adult_cat_out_range1 = Cat(moons=65)
        adult_cat_out_range2 = Cat(moons=65)
        senior_adult_cat1 = Cat(moons=96)
        senior_adult_cat2 = Cat(moons=96)
        elder_cat1 = Cat(moons=120)
        elder_cat2 = Cat(moons=120)

        # check for cat mating with itself
        self.assertFalse(kitten_cat1.is_potential_mate(kitten_cat1, True))

        # check invalid constellations
        self.assertFalse(kitten_cat1.is_potential_mate(adolescent_cat1, True))
        self.assertFalse(kitten_cat1.is_potential_mate(young_adult_cat1, True))
        self.assertFalse(kitten_cat1.is_potential_mate(adult_cat_in_range1, True))
        self.assertFalse(kitten_cat1.is_potential_mate(senior_adult_cat1, True))
        self.assertFalse(kitten_cat1.is_potential_mate(elder_cat1, True))

        self.assertFalse(adolescent_cat1.is_potential_mate(kitten_cat2, True))
        self.assertFalse(adolescent_cat1.is_potential_mate(young_adult_cat1, True))
        self.assertFalse(adolescent_cat1.is_potential_mate(adult_cat_in_range1, True))
        self.assertFalse(adolescent_cat1.is_potential_mate(senior_adult_cat1, True))
        self.assertFalse(adolescent_cat1.is_potential_mate(elder_cat1, True))

        self.assertFalse(young_adult_cat1.is_potential_mate(kitten_cat2, True))
        self.assertFalse(young_adult_cat1.is_potential_mate(adolescent_cat1, True))
        self.assertFalse(young_adult_cat1.is_potential_mate(adult_cat_out_range1, True))
        self.assertFalse(young_adult_cat1.is_potential_mate(senior_adult_cat1, True))
        self.assertFalse(young_adult_cat1.is_potential_mate(elder_cat1, True))

        self.assertFalse(adult_cat_out_range1.is_potential_mate(kitten_cat2, True))
        self.assertFalse(adult_cat_out_range1.is_potential_mate(adolescent_cat1, True))
        self.assertFalse(adult_cat_out_range1.is_potential_mate(young_adult_cat1, True))
        self.assertFalse(adult_cat_out_range1.is_potential_mate(elder_cat1, True))

        self.assertFalse(senior_adult_cat1.is_potential_mate(kitten_cat1, True))
        self.assertFalse(senior_adult_cat1.is_potential_mate(adolescent_cat1, True))
        self.assertFalse(senior_adult_cat1.is_potential_mate(young_adult_cat1, True))

        # check valid constellations
        self.assertTrue(kitten_cat1.is_potential_mate(kitten_cat2, True))
        self.assertTrue(adolescent_cat1.is_potential_mate(adolescent_cat2, True))
        self.assertTrue(young_adult_cat1.is_potential_mate(young_adult_cat2, True))
        self.assertTrue(young_adult_cat1.is_potential_mate(adult_cat_in_range1, True))
        self.assertTrue(adult_cat_in_range1.is_potential_mate(young_adult_cat1, True))
        self.assertTrue(
            adult_cat_in_range1.is_potential_mate(adult_cat_in_range2, True)
        )
        self.assertTrue(
            adult_cat_in_range1.is_potential_mate(adult_cat_out_range1, True)
        )
        self.assertTrue(
            adult_cat_out_range1.is_potential_mate(adult_cat_out_range2, True)
        )
        self.assertTrue(adult_cat_out_range1.is_potential_mate(senior_adult_cat1, True))
        self.assertTrue(senior_adult_cat1.is_potential_mate(adult_cat_out_range1, True))
        self.assertTrue(senior_adult_cat1.is_potential_mate(senior_adult_cat2, True))
        self.assertTrue(senior_adult_cat1.is_potential_mate(elder_cat1, True))
        self.assertTrue(elder_cat1.is_potential_mate(senior_adult_cat1, True))
        self.assertTrue(elder_cat1.is_potential_mate(elder_cat2, True))

    # test that is_potential_mate returns False for exiled or dead cats
    def test_dead_exiled(self):
        exiled_cat = Cat()
        exiled_cat.exiled = True
        dead_cat = Cat()
        dead_cat.dead = True
        normal_cat = Cat()
        self.assertFalse(exiled_cat.is_potential_mate(normal_cat))
        self.assertFalse(normal_cat.is_potential_mate(exiled_cat))
        self.assertFalse(dead_cat.is_potential_mate(normal_cat))
        self.assertFalse(normal_cat.is_potential_mate(dead_cat))

    @patch("scripts.game_structure.game_essentials.game.settings")
    def test_possible_setting(self, settings):
        mentor = Cat(moons=50)
        former_appr = Cat(moons=20)
        mentor.former_apprentices.append(former_appr.ID)

        # TODO: check how this mocking is working
        settings["romantic with former mentor"].return_value = False
        # self.assertFalse(mentor.is_potential_mate(former_appr,False,False))
        # self.assertFalse(former_appr.is_potential_mate(mentor,False,False))
        # self.assertTrue(mentor.is_potential_mate(former_appr,False,True))
        # self.assertTrue(former_appr.is_potential_mate(mentor,False,True))

        # self.assertFalse(mentor.is_potential_mate(former_appr,True,False))
        # self.assertFalse(former_appr.is_potential_mate(mentor,True,False))
        # self.assertTrue(mentor.is_potential_mate(former_appr,True,True))
        # self.assertTrue(former_appr.is_potential_mate(mentor,True,True))


class TestMateFunctions(unittest.TestCase):
    # test that set_mate adds the mate's ID to the cat's mate list
    def test_set_mate(self):
        # given
        cat1 = Cat()
        cat2 = Cat()

        # when
        cat1.set_mate(cat2)
        cat2.set_mate(cat1)

        # then
        self.assertEqual(cat1.mates[0], cat2.ID)
        self.assertEqual(cat2.mates[0], cat1.ID)

    # test that unset_mate removes the mate's ID from the cat's mate list
    def test_unset_mate(self):
        # given
        cat1 = Cat()
        cat2 = Cat()
        cat1.mates.append(cat2.ID)
        cat2.mates.append(cat1.ID)

        # when
        cat1.unset_mate(cat2)
        cat2.unset_mate(cat1)

        # then
        self.assertNotIn(cat2, cat1.mates)
        self.assertNotIn(cat1, cat2.mates)
        self.assertEqual(len(cat1.mates), 0)
        self.assertEqual(len(cat2.mates), 0)

    # test for relationship comparisons
    def test_set_mate_relationship(self):
        # given
        cat1 = Cat()
        cat2 = Cat()
        relation1 = Relationship(cat1, cat2)
        old_relation1 = deepcopy(relation1)
        relation2 = Relationship(cat2, cat1)
        old_relation2 = deepcopy(relation1)

        cat1.relationships[cat2.ID] = relation1
        cat2.relationships[cat1.ID] = relation2

        # when
        cat1.set_mate(cat2)
        cat2.set_mate(cat1)

        # then
        # TODO: maybe not correct check
        self.assertLess(old_relation1.romantic_love, relation1.romantic_love)
        self.assertLessEqual(old_relation1.platonic_like, relation1.platonic_like)
        self.assertLessEqual(old_relation1.dislike, relation1.dislike)
        self.assertLess(old_relation1.comfortable, relation1.comfortable)
        self.assertLess(old_relation1.trust, relation1.trust)
        self.assertLessEqual(old_relation1.admiration, relation1.admiration)
        self.assertLessEqual(old_relation1.jealousy, relation1.jealousy)

        self.assertLess(old_relation2.romantic_love, relation2.romantic_love)
        self.assertLessEqual(old_relation2.platonic_like, relation2.platonic_like)
        self.assertLessEqual(old_relation2.dislike, relation2.dislike)
        self.assertLess(old_relation2.comfortable, relation2.comfortable)
        self.assertLess(old_relation2.trust, relation2.trust)
        self.assertLessEqual(old_relation2.admiration, relation2.admiration)
        self.assertLessEqual(old_relation2.jealousy, relation2.jealousy)

    # test for relationship comparisons for cats that are broken up
    def test_unset_mate_relationship(self):
        # given
        cat1 = Cat()
        cat2 = Cat()
        relation1 = Relationship(
            cat1,
            cat2,
            family=False,
            mates=True,
            romantic_love=40,
            platonic_like=40,
            dislike=0,
            comfortable=40,
            trust=20,
            admiration=20,
            jealousy=20,
        )
        old_relation1 = deepcopy(relation1)
        relation2 = Relationship(
            cat2,
            cat1,
            family=False,
            mates=True,
            romantic_love=40,
            platonic_like=40,
            dislike=0,
            comfortable=40,
            trust=20,
            admiration=20,
            jealousy=20,
        )
        old_relation2 = deepcopy(relation2)
        cat1.mates.append(cat2.ID)
        cat2.mates.append(cat1.ID)
        cat1.relationships[cat2.ID] = relation1
        cat2.relationships[cat1.ID] = relation2

        # when
        cat1.unset_mate(cat2, breakup=True)
        cat2.unset_mate(cat2, breakup=True)

        # then
        # TODO: maybe not correct check
        self.assertGreater(old_relation1.romantic_love, relation1.romantic_love)
        self.assertGreaterEqual(old_relation1.platonic_like, relation1.platonic_like)
        self.assertGreaterEqual(old_relation1.dislike, relation1.dislike)
        self.assertGreater(old_relation1.comfortable, relation1.comfortable)
        self.assertGreater(old_relation1.trust, relation1.trust)
        self.assertGreaterEqual(old_relation1.admiration, relation1.admiration)
        self.assertGreaterEqual(old_relation1.jealousy, relation1.jealousy)

        self.assertGreater(old_relation2.romantic_love, relation2.romantic_love)
        self.assertGreaterEqual(old_relation2.platonic_like, relation2.platonic_like)
        self.assertGreaterEqual(old_relation2.dislike, relation2.dislike)
        self.assertGreater(old_relation2.comfortable, relation2.comfortable)
        self.assertGreater(old_relation2.trust, relation2.trust)
        self.assertGreaterEqual(old_relation2.admiration, relation2.admiration)
        self.assertGreaterEqual(old_relation2.jealousy, relation2.jealousy)


class TestUpdateMentor(unittest.TestCase):
    # test that an exiled cat apprentice becomes a former apprentice
    def test_exile_apprentice(self):
        # given
        app = Cat(moons=7, status="apprentice")
        mentor = Cat(moons=20, status="warrior")
        app.update_mentor(mentor.ID)

        # when
        self.assertTrue(app.ID in mentor.apprentice)
        self.assertFalse(app.ID in mentor.former_apprentices)
        self.assertEqual(app.mentor, mentor.ID)
        app.exiled = True
        app.update_mentor()

        # then
        self.assertFalse(app.ID in mentor.apprentice)
        self.assertTrue(app.ID in mentor.former_apprentices)
        self.assertIsNone(app.mentor)


class TestNameRepr(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    def test_clancats(self):
        """
        Test that basic clancats return the correct names
        :return:
        """
        statuses = [
            [["newborn"], 0, "kit"],
            [["kitten"], 1, "kit"],
            [
                ["apprentice", "medicine cat apprentice", "mediator apprentice"],
                6,
                "paw",
            ],
            [["warrior", "medicine cat", "mediator", "elder", "deputy"], 14, "test"],
            [["leader"], 14, "star"],
        ]
        for testset, moons, suffix in statuses:
            for status in testset:
                with self.subTest("clancats", status=status):
                    cat = Cat(moons=moons, status=status, suffix="test")
                    self.assertTrue(str(cat.name).endswith(suffix))

    def test_specsuffix_clancats(self):
        """
        Test that clancats with suppressed special suffixes return the correct names
        :return:
        """
        statuses = [
            [["newborn"], 0, "test"],
            [["kitten"], 1, "test"],
            [
                ["apprentice", "medicine cat apprentice", "mediator apprentice"],
                6,
                "test",
            ],
            [["warrior", "medicine cat", "mediator", "elder", "deputy"], 14, "test"],
            [["leader"], 14, "test"],
        ]
        for testset, moons, suffix in statuses:
            for status in testset:
                with self.subTest("clancats specsuffix", status=status):
                    cat = Cat(moons=moons, status=status, suffix="test")
                    cat.name.specsuffix_hidden = True
                    self.assertTrue(str(cat.name).endswith(suffix))

    def test_outsiders(self):
        """
        Test that basic outsiders return the correct name
        :return:
        """
        outsider_statuses = ["loner", "rogue", "kittypet"]
        ex_clancat_statuses = ["former colonycat", "exiled"]

        age_suffix = [[0, "kit"], [1, "kit"], [6, "paw"], [14, "test"]]

        for status in outsider_statuses:
            for moons, suffix in age_suffix:
                with self.subTest("outsiders", status=status, moons=moons):
                    cat = Cat(status=status, moons=moons, suffix="test")
                    cat.outside = True
                    self.assertTrue(str(cat.name).endswith("test"))

        for status in ex_clancat_statuses:
            for moons, suffix in age_suffix:
                with self.subTest("Clan-like names", status=status, moons=moons):
                    cat = Cat(status=status, moons=moons, suffix="test")
                    cat.outside = True
                    self.assertTrue(str(cat.name).endswith(suffix))

    def test_specsuffix_outsiders(self):
        """
        Test that outsiders with hidden special suffixes return the correct name
        :return:
        """
        outsider_statuses = ["loner", "rogue", "kittypet"]
        ex_clancat_statuses = ["former colonycat", "exiled"]

        age_suffix = [[0, "kit"], [1, "kit"], [6, "paw"], [14, "test"]]

        for status in outsider_statuses:
            for moons, suffix in age_suffix:
                with self.subTest("outsiders", status=status, moons=moons):
                    cat = Cat(status=status, moons=moons, suffix="test")
                    cat.outside = True
                    cat.name.specsuffix_hidden = True
                    self.assertTrue(str(cat.name).endswith("test"))

        for status in ex_clancat_statuses:
            for moons, suffix in age_suffix:
                with self.subTest("Clan-like names", status=status, moons=moons):
                    cat = Cat(status=status, moons=moons, suffix="test")
                    cat.name.specsuffix_hidden = True
                    self.assertTrue(str(cat.name).endswith("test"))

    def test_lost(self):
        """
        Test that lost cats return the correct suffix
        :return:
        """
        statuses = [
            ["newborn", 0, "kit"],
            ["kitten", 1, "kit"],
            ["apprentice", 6, "paw"],
            ["warrior", 14, "test"],
        ]
        for status, moons, suffix in statuses:
            with self.subTest("lost clancats", moons=moons):
                cat = Cat(status=status, moons=moons, suffix="test")
                cat.outside = True
                self.assertTrue(str(cat.name).endswith(suffix))

    def test_specsuffix_lost(self):
        """
        Test that lost cats with specsuffix return the correct suffix
        :return:
        """
        statuses = [
            ["newborn", 0, "kit"],
            ["kitten", 1, "kit"],
            ["apprentice", 6, "paw"],
            ["warrior", 14, "test"],
        ]
        for status, moons, suffix in statuses:
            with self.subTest("lost clancats", status=status):
                cat = Cat(status=status, moons=moons, suffix="test")
                cat.outside = True
                cat.name.specsuffix_hidden = True
                self.assertTrue(str(cat.name).endswith("test"))


class TestNameSpecialSuffixGuardrails(unittest.TestCase):
    class _DummyPelt:
        def __init__(self):
            self.colour = None
            self.eye_colour = None
            self.name = None
            self.tortiepattern = None

    class _DummyCat:
        def __init__(self, status, moons=6, outside=False):
            self.status = status
            self.moons = moons
            self.outside = outside
            self.pelt = TestNameSpecialSuffixGuardrails._DummyPelt()

    def _name(self, status, suffix, name_type, specsuffix_hidden):
        cat = self._DummyCat(status=status, moons=6, outside=False)
        n = Name(cat=cat, prefix="Test", suffix=suffix, load_existing_name=True)
        n.name_type = name_type
        n.specsuffix_hidden = specsuffix_hidden
        return n

    def test_warrior_special_suffix_visible(self):
        n = self._name(status="apprentice", suffix="tail", name_type="warrior", specsuffix_hidden=False)
        self.assertEqual(str(n), "Testpaw")

    def test_warrior_special_suffix_hidden(self):
        n = self._name(status="apprentice", suffix="tail", name_type="warrior", specsuffix_hidden=True)
        self.assertEqual(str(n), "Testtail")

    def test_ancient_default_hidden_uses_custom(self):
        n = self._name(status="leader", suffix=" Ancient", name_type="ancient", specsuffix_hidden=True)
        self.assertEqual(str(n), "Test Ancient")

    def test_ancient_manual_visible_uses_special(self):
        n = self._name(status="leader", suffix=" Ancient", name_type="ancient", specsuffix_hidden=False)
        self.assertEqual(str(n), "Teststar")

    def test_single_never_forces_special(self):
        n = self._name(status="leader", suffix="", name_type="single", specsuffix_hidden=True)
        self.assertEqual(str(n), "Test")

    def test_syllable_never_forces_special(self):
        n = self._name(status="apprentice", suffix="", name_type="syllable", specsuffix_hidden=True)
        self.assertEqual(str(n), "Test")

    def test_suffix_on_single_name_switches_to_warrior_style(self):
        cat = self._DummyCat(status="kitten", moons=6, outside=False)
        n = Name(cat=cat, prefix="Moss", suffix="", load_existing_name=True)
        n.name_type = "single"
        n.suffix = "heart"

        self.assertEqual(n.name_type, "warrior")
        self.assertEqual(str(n), "Mossheart")

    def test_custom_suffix_can_revert_to_special_suffix(self):
        cat = self._DummyCat(status="kitten", moons=3, outside=False)
        n = Name(cat=cat, prefix="Moss", suffix="", load_existing_name=True)
        n.name_type = "single"

        n.suffix = "heart"
        self.assertEqual(str(n), "Mossheart")

        n.specsuffix_hidden = False
        self.assertEqual(str(n), "Mosskit")

    def test_ancient_name_always_has_one_separator(self):
        cat = self._DummyCat(status="warrior", moons=20, outside=False)

        for suffix in ("Legionn", " Legionn"):
            with self.subTest(suffix=suffix):
                n = Name(
                    cat=cat,
                    prefix="Paisele",
                    suffix=suffix,
                    load_existing_name=True,
                    name_type="ancient",
                    specsuffix_hidden=True,
                )
                self.assertEqual(str(n), "Paisele Legionn")

    def test_persisted_name_type_overrides_legacy_inference(self):
        cat = self._DummyCat(status="warrior", moons=20, outside=False)
        n = Name(
            cat=cat,
            prefix="Paisele",
            suffix="Legionn",
            load_existing_name=True,
            name_type="ancient",
            specsuffix_hidden=True,
        )

        self.assertEqual(n.name_type, "ancient")
        self.assertEqual(str(n), "Paisele Legionn")

    def test_name_type_is_in_cat_save_data(self):
        cat = Cat(status="warrior", moons=20)
        cat.name.name_type = "ancient"

        self.assertEqual(cat.get_save_dict()["name_type"], "ancient")

    def test_loading_preserves_saved_name_components_and_suffix_toggle(self):
        for name_type, suffix in (("single", ""), ("syllable", ""), ("ancient", "bee")):
            for hidden in (True, False):
                with self.subTest(name_type=name_type, hidden=hidden):
                    name = Name(
                        prefix="Bee", suffix=suffix, name_type=name_type,
                        specsuffix_hidden=hidden, load_existing_name=True,
                    )
                    self.assertEqual(name.prefix, "Bee")
                    self.assertEqual(name.suffix, suffix)
                    self.assertEqual(name.name_type, name_type)
                    self.assertEqual(name.specsuffix_hidden, hidden)

    def test_loading_legacy_single_name_preserves_prefix(self):
        name = Name(
            prefix="SavedName", suffix="", specsuffix_hidden=True,
            load_existing_name=True,
        )
        self.assertEqual(str(name), "SavedName")

    def test_saved_name_formatter_respects_style_and_special_suffix_toggle(self):
        ancient = {
            "name_prefix": "Paisele",
            "name_suffix": "Legionn",
            "name_type": "ancient",
            "specsuffix_hidden": True,
            "status": "warrior",
        }
        kitten = {
            "name_prefix": "Moss",
            "name_suffix": "heart",
            "name_type": "warrior",
            "specsuffix_hidden": False,
            "status": "kitten",
        }

        self.assertEqual(Name.format_saved_name(ancient), "Paisele Legionn")
        self.assertEqual(Name.format_saved_name(kitten), "Mosskit")


class TestLeaderLifeSettings(unittest.TestCase):
    def test_revival_and_one_life_history_do_not_number_deaths(self):
        from scripts.cat.history import History
        from scripts.clan import Clan
        from scripts.screens.ProfileScreen import ProfileScreen

        for revived, recorded_mode, current_mode in ((True, None, False), (False, 1, False), (False, None, True)):
            with self.subTest(revived=revived, recorded_mode=recorded_mode):
                cat = Cat(prefix="Moss", status="leader", moons=40)
                cat.leader_life_override = current_mode
                deaths = [{"text": "died in battle", "moon": moon, "involved": None} for moon in range(12)]
                if recorded_mode is not None:
                    for death in deaths:
                        death["leader_life_mode"] = recorded_mode
                cat.history = History(died_by=deaths, return_from_death=[{"text": "returned from death", "moon": 1}] if revived else [])
                with patch.object(game, "clan", Clan(name="TestClan")), patch.dict(
                    game.switches, {"show_history_moons": True}
                ), patch("scripts.screens.ProfileScreen.event_text_adjust", side_effect=lambda cls, text, **kwargs: text):
                    text = ProfileScreen.get_death_text(SimpleNamespace(the_cat=cat))
                self.assertEqual(text.count("died in battle"), 12)
                self.assertIn("(Moon 11)", text)
                self.assertNotIn("lost", text)
                self.assertNotIn("unknown life", text)

    def test_nine_life_history_keeps_normal_numbering(self):
        from scripts.cat.history import History
        from scripts.screens.ProfileScreen import ProfileScreen

        cat = Cat(status="leader", moons=40)
        cat.leader_life_override = True
        cat.history = History(died_by=[{"text": "died in battle", "moon": 1, "involved": None, "leader_life_mode": 9}])
        with patch.dict(game.switches, {"show_history_moons": False}), patch(
            "scripts.screens.ProfileScreen.event_text_adjust", side_effect=lambda cls, text, **kwargs: text
        ):
            text = ProfileScreen.get_death_text(SimpleNamespace(the_cat=cat))
        self.assertIn("first life", text)

    def test_new_death_records_remember_life_mode(self):
        from scripts.cat.history import History
        from scripts.clan import Clan

        cat = Cat(status="leader", moons=40)
        cat.history = History()
        with patch.object(game, "clan", Clan(name="TestClan")):
            for setting in (True, False):
                cat.leader_life_override = setting
                History.add_death(cat, "died in battle")
        self.assertEqual([death["leader_life_mode"] for death in cat.history.died_by], [1, 9])

    def test_revived_nonleader_deaths_are_not_labeled_as_lost_lives(self):
        from scripts.cat.history import History
        from scripts.screens.ProfileScreen import ProfileScreen

        cat = Cat(status="warrior", moons=40)
        cat.history = History(died_by=[
            {"text": "died in battle", "moon": 1, "involved": None},
            {"text": "died of illness", "moon": 3, "involved": None},
        ], return_from_death=[{"text": "returned from death", "moon": 2}])
        with patch.dict(game.switches, {"show_history_moons": False}), patch(
            "scripts.screens.ProfileScreen.event_text_adjust", side_effect=lambda cls, text, **kwargs: text
        ):
            text = ProfileScreen.get_death_text(SimpleNamespace(the_cat=cat))
        self.assertIn("died in battle", text)
        self.assertIn("died of illness", text)
        self.assertNotIn("lost a life", text)
        self.assertNotIn("remaining life", text)

    def test_current_lives_follow_one_life_limit_without_refilling(self):
        from scripts.clan import Clan

        for default, override, lives, expected in (
            (True, True, 9, 1), (True, None, 7, 1),
            (False, True, 9, 1), (True, False, 7, 7),
            (False, None, 3, 3), (True, True, 0, 0),
        ):
            with self.subTest(default=default, override=override, lives=lives):
                clan = Clan(name="TestClan")
                clan.leader = SimpleNamespace(leader_life_override=override, dead=lives == 0)
                clan.clan_settings["leader_life_default"] = default
                clan.leader_lives = lives
                clan.apply_leader_life_limit()
                self.assertEqual(clan.leader_lives, expected)

    def test_switching_default_updates_current_leader(self):
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        clan.leader = SimpleNamespace(leader_life_override=None)
        clan.clan_settings["leader_life_default"] = False
        clan.leader_lives = 9
        clan.switch_setting("leader_life_default")
        self.assertEqual(clan.leader_lives, 1)
        clan.switch_setting("leader_life_default")
        self.assertEqual(clan.leader_lives, 9)

    def test_spent_lives_survive_toggle_and_saved_balance(self):
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        clan.leader = SimpleNamespace(leader_life_override=False, dead=False)
        clan.leader_lives = 5
        clan.leader.leader_life_override = True
        clan.apply_leader_life_limit()
        self.assertEqual(clan.leader_lives, 1)
        self.assertEqual(clan.leader_lives_reserve, 5)
        loaded = Clan(name="Loaded")
        loaded.leader = clan.leader
        loaded.leader_lives = clan.leader_lives
        loaded.leader_lives_reserve = clan.leader_lives_reserve
        loaded.leader_lives_last_applied = clan.leader_lives_last_applied
        loaded.leader.leader_life_override = False
        loaded.apply_leader_life_limit()
        self.assertEqual(loaded.leader_lives, 5)
        loaded.apply_leader_life_limit()
        self.assertEqual(loaded.leader_lives, 5)

    def test_save_records_hidden_balance_without_writing_files(self):
        from contextlib import ExitStack
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        leader = SimpleNamespace(ID="leader", leader_life_override=True, dead=False)
        clan.leader = leader
        clan.your_cat = leader
        clan.instructor = clan.demon = clan.wanderer = SimpleNamespace(ID="guide")
        clan.leader_lives = 5
        with ExitStack() as stack:
            stack.enter_context(patch.object(game, "clan", clan))
            stack.enter_context(patch("scripts.clan.os.path.exists", return_value=False))
            for method in ("save_herbs", "save_disaster", "save_pregnancy", "save_clan_settings", "save_freshkill_pile"):
                stack.enter_context(patch.object(clan, method))
            save = stack.enter_context(patch.object(game, "safe_save"))
            clan.save_clan()
        data = save.call_args.args[1]
        self.assertEqual(data["leader_lives"], 1)
        self.assertEqual(data["leader_lives_reserve"], 5)
        self.assertEqual(data["leader_lives_last_applied"], 1)

    def test_revival_restores_only_unspent_balance(self):
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        clan.leader = SimpleNamespace(leader_life_override=True, dead=False)
        clan.leader_lives = 5
        clan.apply_leader_life_limit()
        clan.leader_lives = 0
        clan.leader.dead = True
        clan.apply_leader_life_limit()
        self.assertEqual(clan.leader_lives_reserve, 4)
        self.assertEqual(clan.leader_lives, 0)
        clan.leader.dead = False
        clan.leader.leader_life_override = False
        clan.apply_leader_life_limit()
        self.assertEqual(clan.leader_lives, 4)
        self.assertEqual(clan.leader_lives_reserve, 4)
        clan.leader_lives = 0
        clan.leader.dead = True
        clan.apply_leader_life_limit()
        clan.leader.dead = False
        clan.apply_leader_life_limit()
        self.assertEqual(clan.leader_lives, 1)
        self.assertEqual(clan.leader_lives_reserve, 0)
        for one_life in (True, False, True, False):
            clan.leader.leader_life_override = one_life
            clan.apply_leader_life_limit()
            self.assertEqual(clan.leader_lives, 1)
            self.assertEqual(clan.leader_lives_reserve, 0)

    def test_return_command_does_not_grant_new_lives(self):
        from scripts.clan import Clan
        from scripts.cat.history import History
        from scripts.debug_commands.return_cat import ReturnCatCommand

        clan = Clan(name="TestClan")
        cat = Cat(status="leader", moons=40)
        cat.old_status = None
        cat.leader_life_override = True
        cat.history = History()
        clan.leader = cat
        clan.your_cat = cat
        clan.leader_lives = 5
        clan.apply_leader_life_limit()
        clan.leader_lives = 0
        cat.dead = True
        with patch.object(game, "clan", clan), patch.object(Cat, "add_to_clan"), patch(
            "scripts.debug_commands.return_cat.add_output_line_to_log"
        ):
            ReturnCatCommand().callback([cat.ID])
        self.assertFalse(cat.dead)
        self.assertEqual(cat.status, "leader")
        self.assertIs(clan.leader, cat)
        self.assertEqual(clan.leader_lives, 1)
        self.assertEqual(clan.leader_lives_reserve, 4)
        self.assertEqual(len(cat.history.return_from_death), 1)
        self.assertEqual(cat.history.died_by, [])
        cat.leader_life_override = False
        clan.apply_leader_life_limit()
        self.assertEqual(clan.leader_lives, 4)

    def test_legacy_balance_is_not_invented(self):
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        clan.leader = SimpleNamespace(leader_life_override=False)
        clan.leader_lives = 1
        clan.leader_lives_reserve = None
        clan.leader_lives_last_applied = None
        clan.apply_leader_life_limit()
        self.assertEqual(clan.leader_lives, 1)

    def test_load_applies_limit_after_loading_settings(self):
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        clan.leader = SimpleNamespace(leader_life_override=None)
        clan.leader_lives = 9
        clan.clan_settings["leader_life_default"] = False
        with patch.object(game, "clan", clan), patch.dict(game.switches, {"clan_list": ["TestClan"]}), patch(
            "scripts.clan.os.path.exists", return_value=True
        ), patch.object(clan, "load_clan_json"), patch.object(
            clan, "load_clan_settings", side_effect=lambda: clan.clan_settings.update(leader_life_default=True)
        ):
            clan.load_clan()
        self.assertEqual(clan.leader_lives, 1)

    def test_new_leader_skips_missing_clan_cats(self):
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        leader = Cat(status="deputy", moons=40)
        member = SimpleNamespace(faith=1.0)
        clan.clan_cats = ["missing", "member"]

        with patch("scripts.clan.game.clan", clan), patch.object(
            clan.history, "add_lead_ceremony"
        ), patch.object(Cat, "fetch_cat", side_effect=[None, member]), patch(
            "scripts.clan.random.uniform", return_value=0.5
        ):
            clan.new_leader(leader)

        self.assertIs(clan.leader, leader)
        self.assertEqual(member.faith, 1.5)

    def test_colony_default_and_cat_override_are_resolved_consistently(self):
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        leader = SimpleNamespace(leader_life_override=None)

        clan.clan_settings["leader_life_default"] = True
        self.assertEqual(clan.get_starting_leader_lives(leader), 1)

        leader.leader_life_override = False
        self.assertEqual(clan.get_starting_leader_lives(leader), 9)

    def test_created_dark_forest_guide_is_dead_before_registration(self):
        from scripts.clan import Clan

        class GuideChecked(Exception):
            pass

        original_cats = Cat.all_cats.copy()
        original_cat_list = list(Cat.all_cats_list)
        leader = Cat(status="warrior", moons=20)
        clan = Clan(name="TestClan", leader=leader, starting_members=[])

        def check_guide(guide):
            self.assertTrue(guide.df)
            self.assertTrue(guide.dead)
            raise GuideChecked

        try:
            with patch.object(clan, "add_cat"), patch.object(
                clan, "add_to_starclan"
            ), patch.object(clan, "add_to_darkforest", side_effect=check_guide):
                with self.assertRaises(GuideChecked):
                    clan.create_clan()
        finally:
            Cat.all_cats.clear()
            Cat.all_cats.update(original_cats)
            Cat.all_cats_list[:] = original_cat_list


class TestShunnedMentors(unittest.TestCase):
    def setUp(self):
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        clan.age = 1
        clan.clan_cats = []
        for target, attribute, value in (
            (Cat, "all_cats", {}),
            (Cat, "all_cats_list", []),
            (game, "clan", clan),
        ):
            replacement = patch.object(target, attribute, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        switches = patch.dict(game.switches, {"request apprentice": False})
        switches.start()
        self.addCleanup(switches.stop)

    def test_shunned_mentor_is_replaced_and_dating_follows_mentor_rules(self):
        mentor = Cat(status="warrior", moons=30)
        replacement = Cat(status="warrior", moons=24)
        apprentice = Cat(status="apprentice", moons=18)
        game.clan.your_cat = apprentice
        game.clan.clan_settings["romantic with former mentor"] = True
        apprentice.update_mentor(mentor.ID)
        self.assertFalse(apprentice.is_dateable(mentor))
        self.assertTrue(apprentice.is_dateable(replacement))
        mentor.shunned = 1
        apprentice.update_mentor()
        self.assertEqual(apprentice.mentor, replacement.ID)
        self.assertNotIn(apprentice.ID, mentor.apprentice)
        self.assertIn(apprentice.ID, mentor.former_apprentices)
        self.assertFalse(apprentice.is_dateable(replacement))
        self.assertTrue(apprentice.is_dateable(mentor))
        game.clan.clan_settings["romantic with former mentor"] = False
        self.assertFalse(apprentice.is_dateable(mentor))
        mentor.shunned = 0
        apprentice.update_mentor()
        self.assertEqual(apprentice.mentor, replacement.ID)

    def test_event_shunning_reassigns_every_apprentice(self):
        from scripts.cat.history import History

        mentor = Cat(status="warrior", moons=30)
        replacement = Cat(status="warrior", moons=24)
        apprentices = [Cat(status="apprentice", moons=18), Cat(status="apprentice", moons=20)]
        victim = Cat(status="warrior", moons=50)
        victim.dead = True
        game.clan.your_cat = replacement
        mentor.history = History()
        victim.history = History()
        History.add_murders(victim, mentor, False)
        for apprentice in apprentices:
            apprentice.update_mentor(mentor.ID)
        with patch("scripts.cat.history.random.randint", return_value=2):
            History.reveal_murder(mentor, None, Cat, victim.ID, 0, True)
        self.assertFalse(mentor.apprentice)
        for apprentice in apprentices:
            self.assertEqual(apprentice.mentor, replacement.ID)

    def test_event_shunning_removes_an_apprentices_own_mentor_immediately(self):
        from scripts.cat.history import History

        mentor = Cat(status="warrior", moons=30)
        apprentice = Cat(status="apprentice", moons=18)
        victim = Cat(status="warrior", moons=50)
        victim.dead = True
        game.clan.your_cat = mentor
        apprentice.history = History()
        victim.history = History()
        History.add_murders(victim, apprentice, False)
        apprentice.update_mentor(mentor.ID)
        with patch("scripts.cat.history.random.randint", return_value=2):
            History.reveal_murder(apprentice, None, Cat, victim.ID, 0, True)
        self.assertIsNone(apprentice.mentor)
        self.assertNotIn(apprentice.ID, mentor.apprentice)

    def test_request_apprentice_does_not_assign_a_shunned_player(self):
        mentor = Cat(status="warrior", moons=30)
        replacement = Cat(status="warrior", moons=24)
        apprentice = Cat(status="apprentice", moons=6)
        game.clan.your_cat = mentor
        mentor.shunned = 1
        with patch.dict(game.switches, {"request apprentice": True}):
            apprentice.update_mentor()
        self.assertEqual(apprentice.mentor, replacement.ID)

    def test_request_matches_the_kitten_ceremony_role_and_assigns_one_existing_cat(self):
        from scripts.cat.history import History
        from scripts.events import Events

        events = Events()
        for role, expected in (
            ("warrior", "apprentice"), ("deputy", "apprentice"), ("leader", "apprentice"),
            ("medicine cat", "medicine cat apprentice"), ("mediator", "mediator apprentice"),
            ("queen", "queen's apprentice"),
        ):
            with self.subTest(role=role):
                mentor = Cat(status=role, moons=30)
                kitten = Cat(status="kitten", moons=6)
                for cat in (mentor, kitten):
                    cat.history = History()
                    cat.create_inheritance_new_cat()
                    game.clan.add_cat(cat)
                game.clan.your_cat = mentor
                game.switches["request apprentice"] = True
                before = set(Cat.all_cats)
                with patch.object(game, "cur_events_list", []):
                    events.ceremony(kitten, "medicine cat apprentice" if expected == "apprentice" else "apprentice")
                    self.assertEqual(set(Cat.all_cats), before)
                    self.assertEqual(kitten.status, expected)
                    self.assertEqual(kitten.name.status, expected)
                    self.assertEqual(kitten.mentor, mentor.ID)
                    self.assertEqual(mentor.apprentice, [kitten.ID])
                    self.assertFalse(game.switches["request apprentice"])
                    events.check_gain_app([0])
                    self.assertTrue(game.cur_events_list)

    def test_request_does_not_assign_an_unrelated_six_moon_recruit(self):
        mentor = Cat(status="warrior", moons=30)
        medic = Cat(status="medicine cat", moons=40)
        recruit = Cat(status="medicine cat apprentice", moons=6)
        game.clan.your_cat = mentor
        game.switches["request apprentice"] = True
        before = set(Cat.all_cats)
        recruit.update_mentor()
        self.assertEqual(set(Cat.all_cats), before)
        self.assertEqual(recruit.mentor, medic.ID)
        self.assertFalse(mentor.apprentice)
        self.assertTrue(game.switches["request apprentice"])

    def test_request_waits_when_no_kitten_is_ready(self):
        from scripts.cat.history import History
        from scripts.events import Events

        mentor = Cat(status="warrior", moons=30)
        kitten = Cat(status="kitten", moons=5)
        game.clan.your_cat = mentor
        game.clan.add_cat(mentor)
        game.clan.add_cat(kitten)
        kitten.history = History()
        kitten.create_inheritance_new_cat()
        game.switches["request apprentice"] = True
        before = set(Cat.all_cats)
        with patch.object(game, "cur_events_list", []):
            Events().perform_ceremonies(kitten)
        self.assertEqual(set(Cat.all_cats), before)
        self.assertEqual(kitten.status, "kitten")
        self.assertFalse(mentor.apprentice)
        self.assertTrue(game.switches["request apprentice"])


class TestLeaderCeremony(unittest.TestCase):
    def test_life_givers_belong_to_the_followed_afterlife(self):
        from scripts.clan import Clan

        for following in (True, False, None):
            with self.subTest(following=following), patch.object(Cat, "all_cats", {}), patch.object(
                Cat, "all_cats_list", []
            ):
                clan = Clan(name="TestClan", followingsc=following)
                clan.age = 1
                with patch.object(game, "clan", clan):
                    leader = Cat(status="leader", moons=40)
                    clan.your_cat = leader
                    correct = Cat(status="warrior", moons=50)
                    wrong = Cat(status="warrior", moons=50)
                    correct.dead = wrong.dead = True
                    clan.starclan_cats = [correct.ID if following else wrong.ID]
                    clan.darkforest_cats = [wrong.ID if following else correct.ID]
                    clan.unknown_cats = [correct.ID if following is None else wrong.ID]
                    if following is None:
                        clan.starclan_cats = clan.darkforest_cats = [wrong.ID]
                    leader.create_one_relationship(wrong)
                    with patch("scripts.cat.cats.leader_ceremony_text_adjust", return_value="text") as adjust:
                        leader.generate_lead_ceremony()
                    givers = [call.kwargs["life_giver"] for call in adjust.call_args_list
                              if call.kwargs.get("life_giver")]
                    self.assertIn(correct.ID, givers)
                    self.assertNotIn(wrong.ID, givers)

    def test_murdered_life_giver_uses_the_murder_specific_text(self):
        from scripts.cat.history import History
        from scripts.clan import Clan

        with patch.object(Cat, "all_cats", {}), patch.object(Cat, "all_cats_list", []):
            clan = Clan(name="TestClan")
            clan.age = 1
            with patch.object(game, "clan", clan):
                leader = Cat(status="leader", moons=40)
                victim = Cat(status="warrior", moons=50)
                victim.dead = True
                clan.your_cat = leader
                clan.starclan_cats = [victim.ID]
                clan.darkforest_cats = []
                leader.history = History(murder={"is_murderer": [{"victim": victim.ID}]})
                ceremony = {
                    "intros": {"intro": {"tags": [], "lead_trait": [], "text": ["intro"]}},
                    "lives": {
                        "ordinary": {"tags": [], "rank": [], "lead_trait": [], "star_trait": [],
                                     "life_giving": [{"text": "ordinary life"}]},
                        "murdered": {"tags": ["murdered"], "rank": [], "lead_trait": [], "star_trait": [],
                                     "life_giving": [{"text": "murdered life"}]},
                        "unknown": {"tags": ["unknown_blessing"], "lead_trait": [],
                                    "life_giving": [{"text": "unknown life", "virtue": "faith"}]},
                    },
                    "outros": {"outro": {"tags": [], "lead_trait": [], "text": ["outro"]}},
                    "default_life": {"text": "default life"},
                }
                with patch("scripts.cat.cats.LEAD_CEREMONY_SC", ceremony):
                    text = leader.generate_lead_ceremony()
                self.assertIn("murdered life", text)
                self.assertNotIn("ordinary life", text)

    def test_stale_afterlife_ids_do_not_crash_leader_selection(self):
        from scripts.clan import Clan

        for following in (True, False, None):
            with self.subTest(following=following), patch.object(Cat, "all_cats", {}), patch.object(
                Cat, "all_cats_list", []
            ):
                clan = Clan(name="TestClan", followingsc=following)
                clan.age = 1
                with patch.object(game, "clan", clan):
                    clan.your_cat = Cat(status="leader", moons=40)
                    clan.starclan_cats = ["missing-cat"]
                    clan.darkforest_cats = ["missing-cat"]
                    clan.unknown_cats = ["missing-cat"]
                    self.assertTrue(clan.your_cat.generate_lead_ceremony())

    def test_wanderer_ceremony_is_real_text_and_records_history(self):
        from scripts.cat.history import History
        from scripts.clan import Clan
        for age in (0, 12):
            with self.subTest(age=age), patch.object(Cat, "all_cats", {}), patch.object(Cat, "all_cats_list", []):
                clan = Clan(name="TestClan", followingsc=None)
                clan.age = age
                with patch.object(game, "clan", clan):
                    leader = Cat(status="leader", moons=40)
                    leader.history = History()
                    clan.your_cat = leader
                    giver = Cat(status="warrior", moons=50)
                    giver.dead = True
                    giver.name.prefix, giver.name.suffix = "Wander", "song"
                    living = Cat(status="warrior", moons=30)
                    clan.unknown_cats = [giver.ID, living.ID, "missing-cat"]
                    History.add_lead_ceremony(leader)
                    text = leader.history.lead_ceremony
                    self.assertIn("wanderers", text)
                    self.assertIn(str(giver.name), text)
                    self.assertNotIn(str(living.name), text)
                    for token in ("m_c", "r_c", "[virtue]", "[life_num]", "{PRONOUN"):
                        self.assertNotIn(token, text)
                    clan.unknown_cats = []
                    self.assertIn("wanderers", leader.generate_lead_ceremony())


class TestRetirementSettings(unittest.TestCase):
    def test_no_retire_is_enabled_by_default_when_setting_is_on(self):
        from scripts.cat.cats import Cat
        from scripts.game_structure.game_essentials import game
        from scripts.clan import Clan

        clan = Clan(name="TestClan")
        clan.clan_settings["retirement"] = True
        game.clan = clan

        cat = Cat(status="warrior", moons=24)
        self.assertTrue(cat.no_retire)


class TestExampleCatNamingRules(unittest.TestCase):
    def test_example_cats_follow_enabled_name_style(self):
        dummy_clan = SimpleNamespace(
            clan_settings={
                "warrior_names": False,
                "ancient_names": False,
                "single_names": True,
                "syllable_names": False,
                "kit_inherit_naming": False,
            },
            faded_ids=[],
            biome=None,
            followingsc=False,
            leader_lives=0,
            age=0,
            your_cat=None,
            starclan_cats=[],
            darkforest_cats=[],
            unknown_cats=[],
            current_season="Newleaf",
            herbs={},
            game_mode="expanded",
            simulation_mode="expanded",
            cruel_cards=None,
        )

        with patch("scripts.cat.names.game.clan", dummy_clan), patch(
            "scripts.cat.cats.game.clan", dummy_clan
        ):
            original_choose_cats = game.choose_cats
            try:
                game.choose_cats = {}
                create_example_cats()

                self.assertEqual(len(game.choose_cats), 12)
                self.assertTrue(
                    all(cat.name.name_type == "single" for cat in game.choose_cats.values())
                )
            finally:
                game.choose_cats = original_choose_cats


class TestPlayerRoleChoice(unittest.TestCase):
    def test_opt_out_only_blocks_the_current_players_automatic_career_changes(self):
        from scripts.cat.history import History
        from scripts.clan import Clan
        from scripts.events import Events
        for setting, expected in (("become_mediator", "mediator apprentice"),
                                  ("become_med", "medicine cat apprentice"), ("become_queen", "queen")):
            for player, blocked in ((True, True), (True, False), (False, True)):
                with self.subTest(setting=setting, player=player, blocked=blocked), \
                     patch.object(Cat, "all_cats", {}), patch.object(Cat, "all_cats_list", []):
                    clan = Clan(name="TestClan")
                    with patch.object(game, "clan", clan), patch.object(game, "cur_events_list", []), \
                         patch("scripts.events.random.random", return_value=0):
                        cat = Cat(status="warrior", moons=30)
                        cat.history = History()
                        clan.clan_cats = [cat.ID]
                        clan.your_cat = cat if player else Cat(status="warrior", moons=30)
                        cat.no_role_change = blocked
                        for option in ("become_mediator", "become_med", "become_queen"):
                            clan.clan_settings[option] = option == setting
                        Events.__new__(Events).mediator_events(cat)
                        self.assertEqual(cat.status, "warrior" if player and blocked else expected)
                        self.assertEqual(cat.get_save_dict()["no_role_change"], blocked)

    def test_personal_window_only_exposes_the_control_for_the_player(self):
        import pygame
        import pygame_gui
        from scripts.clan import Clan
        from scripts.game_structure.windows import ChangeCatToggles
        with patch.object(Cat, "all_cats", {}), patch.object(Cat, "all_cats_list", []):
            clan = Clan(name="TestClan")
            with patch.object(game, "clan", clan):
                clan.your_cat = Cat(status="warrior", moons=30)
                other = Cat(status="warrior", moons=30)
                for cat in (clan.your_cat, other):
                    window = ChangeCatToggles(cat)
                    try:
                        self.assertEqual("prevent_role_change" in window.checkboxes, cat == clan.your_cat)
                        if cat == clan.your_cat:
                            window.process_event(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS,
                                                                   ui_element=window.checkboxes["prevent_role_change"]))
                            self.assertTrue(cat.no_role_change)
                    finally:
                        window.kill()

    def test_conditions_remove_worn_accessories_without_requiring_inventory_copies(self):
        from scripts.cat.history import History
        from scripts.clan import Clan
        with patch.object(game, "clan", Clan(name="TestClan")):
            cat = Cat(status="warrior", moons=30)
            cat.history = History()
            cat.pelt.scars = ["NOTAIL", "NOPAW"]
            cat.pelt.accessories = ["RED FEATHERS", "ASHY PAWS"]
            cat.pelt.inventory = []
            cat.get_permanent_condition("weak leg", born_with=True)
            self.assertEqual(cat.pelt.accessories, [])
            self.assertEqual(cat.pelt.inventory, [])
