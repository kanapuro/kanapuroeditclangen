import unittest
from unittest.mock import patch

from scripts.cat.cats import Cat
from scripts.clan import Clan
from scripts.game_structure.game_essentials import game
from scripts.events_module.short.handle_short_events import HandleShortEvents


class TestHandleEvent(unittest.TestCase):
    def test_faith_events_requiring_a_companion_are_filtered_when_alone(self):
        from scripts.events_module.generate_events import GenerateEvents

        clan = Clan(name="Alone")
        cat = Cat(status="warrior", moons=30)
        with patch.object(game, "clan", clan):
            events = GenerateEvents.possible_short_events("faith")
            self.assertTrue(any(event.r_c for event in events))
            filtered = GenerateEvents.filter_possible_short_events(
                Cat, events, cat, None, None, False, 1, [])
        self.assertTrue(all(not event.r_c for event in filtered))

    def test_no_neighbors_passes_absent_neighbor_to_event_filter(self):
        from scripts.events_module.generate_events import GenerateEvents

        clan = Clan(name="Alone")
        clan.all_clans = []
        with patch.object(game, "clan", clan), patch.object(
            GenerateEvents, "possible_short_events", return_value=[]
        ), patch.object(GenerateEvents, "filter_possible_short_events", return_value=[]) as filter_events:
            HandleShortEvents().handle_event("faith", Cat(), None, None)
        self.assertIsNone(filter_events.call_args.kwargs["other_clan"])



class TestHandleNewCats(unittest.TestCase):
    def test_recovering_from_birth_is_added_for_new_litter_with_parent(self):
        handle = HandleShortEvents()
        handle.chosen_event = type("Event", (), {"new_cat": [{}, {}], "text": "", "sub_type": []})()
        handle.types = []
        handle.new_cats = []
        handle.new_cat_objects = []
        handle.involved_cats = []

        parent = Cat(status="warrior", moons=40)
        parent.ID = "parent"
        parent.gender = "female"
        parent.dead = False
        parent.outside = False

        kit = Cat()
        kit.ID = "kit"
        kit.moons = 1
        kit.parent1 = "parent"
        kit.parent2 = None
        kit.dead = False
        kit.outside = False

        with patch(
            "scripts.events_module.short.handle_short_events.create_new_cat_block",
            side_effect=[[parent], [kit]],
        ), patch("scripts.events_module.short.handle_short_events.Relation_Events.welcome_new_cats"), patch.object(
            game, "clan", Clan(name="TestClan")
        ), patch("scripts.events_module.short.handle_short_events.random.random", return_value=0.9):
            handle.handle_new_cats()

        self.assertIn("recovering from birth", parent.injuries)


class TestHandleAccessories(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Mock classes
        cls.event_class = type('EventClass', (), dict(
            new_accessory = []
        ))
        cls.pelt_class = type('PeltClass', (), dict(
            wild_accessories=["WILD1", "WILD2"],
            plant_accessories=["PLANT1", "PLANT2"],
            collars=["COLLAR1", "COLLAR2"],
            tail_accessories=["TAIL1", "TAIL2"]
        ))

    def setUp(self):
        self.test = HandleShortEvents()
        self.test.chosen_event = self.event_class()
        self.test.main_cat = Cat()
        self.pelts = self.pelt_class()

    def test_misc_appended_to_types(self):
        self.test.types = []

        self.test.handle_accessories()
        self.assertIn("misc", self.test.types)

    def test_cat_gets_test_accessory(self):
        self.test.chosen_event.new_accessory = ["TEST"]

        self.test.handle_accessories()
        self.assertIs(self.test.main_cat.pelt.accessory, "TEST")

    def test_cat_gets_random_wild_accessory(self):
        self.test.chosen_event.new_accessory = ["WILD"]

        self.test.handle_accessories(pelts=self.pelt_class)
        self.assertIn(self.test.main_cat.pelt.accessory, self.pelts.wild_accessories)

    def test_cat_gets_random_plant_accessory(self):
        self.test.chosen_event.new_accessory = ["PLANT"]

        self.test.handle_accessories(pelts=self.pelt_class)
        self.assertIn(self.test.main_cat.pelt.accessory, self.pelts.plant_accessories)

    def test_cat_gets_random_collar_accessory(self):
        self.test.chosen_event.new_accessory = ["COLLAR"]

        self.test.handle_accessories(pelts=self.pelt_class)
        self.assertIn(self.test.main_cat.pelt.accessory, self.pelts.collars)

    def test_notail_cats_do_not_get_tail_accessories(self):
        self.test.chosen_event.new_accessory = self.pelts.tail_accessories
        self.test.main_cat.pelt.scars = "NOTAIL"

        self.test.handle_accessories(pelts=self.pelt_class)
        self.assertIsNone(self.test.main_cat.pelt.accessory)

    def test_halftail_cats_do_not_get_tail_accessories(self):
        self.test.chosen_event.new_accessory = self.pelts.tail_accessories
        self.test.main_cat.pelt.scars = "HALFTAIL"

        self.test.handle_accessories(pelts=self.pelt_class)
        self.assertIsNone(self.test.main_cat.pelt.accessory)


class TestHandleDeath(unittest.TestCase):
    pass


class TestHandleMassDeath(unittest.TestCase):
    pass


class TestHandleDeathHistory(unittest.TestCase):
    pass


class TestHandleInjury(unittest.TestCase):
    pass


class TestHandleInjuryHistory(unittest.TestCase):
    pass


class TestHandleFreshkillSupply(unittest.TestCase):
    pass


class TestHandleHerbSupply(unittest.TestCase):
    pass


class TestReset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Mock class
        cls.handle = type('HandleShortEventsClass', (), dict(
            herb_notice=None,
            types=[],
            sub_types=[],
            text=None,
            involved_cats=[],
            main_cat=None,
            random_cat=None,
            new_cat_objects=[],
            new_cats=[],
            victim_cat=None,
            murder_index=None,
            multi_cat=[],
            dead_cats=[],
            chosen_herb=None,
            other_clan=None,
            other_clan_name=None,
            chosen_event=None,
            additional_event_text=""
        ))

    def test_reset_resets_all_attributes_to_default_values(self):
        default = self.handle()
        test = self.handle()
        # Check these are 2 separate instances
        self.assertNotEqual(test, default)

        # Given
        test.herb_notice = "herb notice"
        test.types = ["type1", "type2"]
        test.sub_types = ["type1", "type2"]
        test.text = "text"
        test.involved_cats = ["cat1", "cat2"]
        test.main_cat = "main cat"
        test.random_cat = "random cat"
        test.new_cat_objects = ["cat1", "cat2"]
        test.new_cats = [[Cat()]]
        test.victim_cat = "victim cat"
        test.murder_index = "murder index"
        test.multi_cat = ["cat1", "cat2"]
        test.dead_cats = ["cat1", "cat2"]
        test.chosen_herb = "chosen herb"
        test.other_clan = "other clan"
        test.other_clan_name = "other clan name"
        test.chosen_event = "chosen event"
        test.additional_event_text = "additional event text"

        # When
        HandleShortEvents.reset(test)

        # Then
        self.assertEqual(test.herb_notice, default.herb_notice)
        self.assertEqual(test.types, default.types)
        self.assertEqual(test.sub_types, default.sub_types)
        self.assertEqual(test.text, default.text)
        self.assertEqual(test.involved_cats, default.involved_cats)
        self.assertEqual(test.main_cat, default.main_cat)
        self.assertEqual(test.random_cat, default.random_cat)
        self.assertEqual(test.new_cat_objects, default.new_cat_objects)
        self.assertEqual(test.new_cats, default.new_cats)
        self.assertEqual(test.victim_cat, default.victim_cat)
        self.assertEqual(test.murder_index, default.murder_index)
        self.assertEqual(test.multi_cat, default.multi_cat)
        self.assertEqual(test.dead_cats, default.dead_cats)
        self.assertEqual(test.chosen_herb, default.chosen_herb)
        self.assertEqual(test.other_clan, default.other_clan)
        self.assertEqual(test.other_clan_name, default.other_clan_name)
        self.assertEqual(test.chosen_event, default.chosen_event)
        self.assertEqual(test.additional_event_text, default.additional_event_text)


class TestExcludedParticipants(unittest.TestCase):
    def setUp(self):
        from unittest.mock import Mock
        from scripts.cat.history import History
        from scripts.cat_relations.inheritance import Inheritance
        from scripts.cat_relations.relationship import Relationship

        for target, field, value in ((Cat, "all_cats", {}), (Cat, "all_cats_list", []),
                                     (Cat, "outside_cats", {}), (Inheritance, "all_inheritances", {}),
                                     (game, "cur_events_list", [])):
            replacement = patch.object(target, field, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        clan = Clan(name="ExcludedTest", game_mode="expanded")
        clan.clan_cats = []
        clan.all_clans = []
        replacement = patch.object(game, "clan", clan)
        replacement.start()
        self.addCleanup(replacement.stop)
        replacement = patch.object(game, "safe_save", Mock(side_effect=AssertionError("No real save writes")))
        replacement.start()
        self.addCleanup(replacement.stop)
        self.cats = [Cat(status="warrior", moons=30) for _ in range(5)]
        for cat in self.cats:
            cat.history = History()
            cat.create_inheritance_new_cat()
            clan.add_cat(cat)
        clan.your_cat = self.cats[0]
        self.cats[0].relationships[self.cats[1].ID] = Relationship(self.cats[0], self.cats[1])

    def execute(self, excluded=None, new_cat=None):
        from scripts.events_module.generate_events import GenerateEvents
        from scripts.events_module.short.short_event import ShortEvent

        event = ShortEvent(event_id="excluded_test", text="m_c watches r_c.", r_c={"age": ["any"]},
            relationships=[{"cats_from": ["m_c"], "cats_to": ["r_c"], "values": ["trust"], "amount": 5}],
            exclude_involved=excluded, new_cat=new_cat)
        handler = HandleShortEvents()
        with patch.object(GenerateEvents, "possible_short_events", return_value=[event]), patch.object(
            GenerateEvents, "filter_possible_short_events", return_value=[event]):
            handler.handle_event("misc", self.cats[0], self.cats[1], None)
        return handler, game.cur_events_list[-1]

    def test_excluded_cats_still_receive_effects_but_are_not_displayed(self):
        from scripts.event_class import Single_Event

        handler, event = self.execute(["r_c"])
        self.assertEqual(self.cats[0].relationships[self.cats[1].ID].trust, 5)
        self.assertIn(self.cats[1].ID, handler.involved_cats)
        self.assertEqual(event.cats_involved, [self.cats[0].ID])
        self.assertIn(str(self.cats[1].name), event.text)
        self.assertEqual(Single_Event.from_dict(event.to_dict()).cats_involved, event.cats_involved)

    def test_legacy_events_keep_their_participants(self):
        _, event = self.execute()
        self.assertEqual(event.cats_involved, [cat.ID for cat in self.cats[:2]])

    def test_all_participants_can_be_context_only(self):
        _, event = self.execute(["m_c", "r_c"])
        self.assertEqual(event.cats_involved, [])
        self.assertEqual(self.cats[0].relationships[self.cats[1].ID].trust, 5)

    def test_excluding_new_cat_group_removes_the_whole_litter(self):
        with patch("scripts.events_module.short.handle_short_events.create_new_cat_block",
                   side_effect=[self.cats[2:4], [self.cats[4]]]), patch(
            "scripts.events_module.short.handle_short_events.Relation_Events.welcome_new_cats"), patch(
            "scripts.events_module.short.handle_short_events.random.random", return_value=.9):
            handler, event = self.execute(["n_c:0"], [["join"], ["join"]])
        self.assertEqual(handler.new_cats[0], self.cats[2:4])
        self.assertNotIn(self.cats[2].ID, event.cats_involved)
        self.assertNotIn(self.cats[3].ID, event.cats_involved)
        self.assertIn(self.cats[4].ID, event.cats_involved)


def test_short_event_loader_reads_optional_participant_exclusions(tmp_path, monkeypatch):
    import json
    import scripts.events_module.generate_events as generation

    directory = tmp_path / "misc"
    directory.mkdir()
    (directory / "forest.json").write_text(json.dumps([
        {"event_id": "context_only", "event_text": "m_c notices r_c.", "exclude_involved": ["r_c"]},
        {"event_id": "legacy", "event_text": "m_c rests."},
    ]), encoding="utf-8")
    monkeypatch.setattr(generation, "resource_directory", str(tmp_path) + "/")
    monkeypatch.setattr(generation.GenerateEvents, "loaded_events", {})
    events = generation.GenerateEvents.generate_short_events("misc", "forest")
    assert events[0].exclude_involved == ["r_c"]
    assert events[1].exclude_involved == []
