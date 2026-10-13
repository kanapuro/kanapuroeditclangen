import os
import unittest

import ujson

from scripts.cat.cats import Cat
from scripts.conditions import medical_cats_condition_fulfilled

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"


class TestsMedCondition(unittest.TestCase):
    def test_fulfilled(self):
        cat1 = Cat(moons=20)
        cat1.status = "warrior"

        med = Cat(moons=20)
        med.status = "medicine cat"

        all_cats = [cat1, med]
        self.assertTrue(medical_cats_condition_fulfilled(all_cats, 15))

    def test_fulfilled_many_cats(self):
        cat1 = Cat(moons=20)
        cat1.status = "warrior"
        cat2 = Cat(moons=20)
        cat2.status = "warrior"
        cat3 = Cat(moons=20)
        cat3.status = "warrior"
        cat4 = Cat(moons=20)
        cat4.status = "warrior"

        med1 = Cat(moons=20)
        med1.status = "medicine cat"
        med2 = Cat(moons=20)
        med2.status = "medicine cat"

        all_cats = [cat1, cat2, cat3, cat4, med1, med2]
        self.assertTrue(medical_cats_condition_fulfilled(all_cats, 2))

    def test_injured_fulfilled(self):
        cat1 = Cat(moons=20)
        cat1.status = "warrior"

        med = Cat(moons=20)
        med.status = "medicine cat"
        med.injuries["small cut"] = {"severity": "minor"}

        all_cats = [cat1, med]
        self.assertTrue(medical_cats_condition_fulfilled(all_cats, 15))

    def test_illness_fulfilled(self):
        cat1 = Cat(moons=20)
        cat1.status = "warrior"

        med = Cat(moons=20)
        med.status = "medicine cat"
        med.illnesses["running nose"] = {"severity": "minor"}

        all_cats = [cat1, med]
        self.assertTrue(medical_cats_condition_fulfilled(all_cats, 15))


class TestsIllnesses(unittest.TestCase):
    def load_resources(self):
        resource_directory = "resources/dicts/conditions/"

        illnesses = None
        with open(f"{resource_directory}Illnesses.json", 'r', encoding='utf-8') as read_file:
            illnesses = ujson.loads(read_file.read())
        return illnesses


class TestInjury(unittest.TestCase):
    def load_resources(self):
        resource_directory = "resources/dicts/conditions/"

        injuries = None
        with open(f"{resource_directory}Injuries.json", 'r', encoding='utf-8') as read_file:
            injuries = ujson.loads(read_file.read())
        return injuries


class TestConditionHistory(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        from scripts.clan import Clan
        from scripts.cat.history import History
        from scripts.game_structure.game_essentials import game
        self.game = game
        clan = Clan(name="HistoryTest")
        clan.clan_cats = []
        clan.age = 17
        for target, attribute, value in ((game, "clan", clan), (Cat, "all_cats", {}), (Cat, "all_cats_list", [])):
            replacement = patch.object(target, attribute, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        self.cat = Cat(status="warrior", moons=30)
        self.cat.history = History()
        clan.add_cat(self.cat)

    def test_acquisition_duplicate_and_recurrence(self):
        self.cat.get_ill("running nose", cause="Caught from a sick visitor.")
        self.cat.get_ill("running nose", cause="Duplicate")
        self.assertEqual(len(self.cat.history.condition_events), 1)
        event = self.cat.history.condition_events[0]
        self.assertEqual(event["condition"], "running nose")
        self.assertEqual(event["cause"], "Caught from a sick visitor.")
        self.assertEqual(event["moon"], 17)
        del self.cat.illnesses["running nose"]
        self.game.clan.age = 20
        self.cat.get_ill("running nose")
        self.assertEqual(len(self.cat.history.condition_events), 2)
        self.assertIsNone(self.cat.history.condition_events[1]["cause"])
        self.assertEqual(self.cat.history.condition_events[1]["moon"], 20)

    def test_injury_and_named_grief(self):
        from unittest.mock import patch
        lost_cat = Cat(status="warrior", moons=30)
        with patch("scripts.cat.cats.random", return_value=0.9):
            self.cat.get_injured("broken back", cause="A badger attacked.")
        self.cat.get_ill("grief stricken", grief_cat=lost_cat)
        self.assertEqual(self.cat.history.condition_events[0]["cause"], "A badger attacked.")
        self.assertIn(str(lost_cat.name), self.cat.history.condition_events[1]["cause"])

    def test_preview_does_not_create_history(self):
        preview = Cat(status="warrior", moons=30)
        preview.get_ill("running nose")
        self.assertIsNone(preview.history)

    def test_save_load_and_older_history(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from scripts.cat.history import History
        self.cat.get_ill("running nose", cause="Caught from a sick visitor.")
        expected = self.cat.history.condition_events.copy()
        with tempfile.TemporaryDirectory() as directory, \
             patch("scripts.cat.cats.get_save_dir", return_value=directory), \
             patch.dict(self.game.switches, {"clan_name": "HistoryTest"}):
            history_dir = Path(directory) / "HistoryTest" / "history"
            self.cat.save_history(str(history_dir))
            self.cat.history = None
            self.cat.load_history()
            self.assertEqual(self.cat.history.condition_events, expected)
            old_data = History.make_dict(self.cat)
            del old_data["condition_events"]
            (history_dir / f"{self.cat.ID}_history.json").write_text(ujson.dumps(old_data), encoding="utf-8")
            self.cat.history = None
            self.cat.load_history()
            self.assertEqual(self.cat.history.condition_events, [])

    def test_acquired_permanent_and_hidden_congenital_condition(self):
        from unittest.mock import patch
        self.cat.get_permanent_condition("weak leg", cause="Following a broken bone.")
        self.assertEqual(self.cat.history.condition_events[0]["cause"], "Following a broken bone.")
        self.cat.status = "kitten"
        self.cat.moons = 2
        with patch("scripts.cat.cats.random", return_value=0.9):
            self.cat.get_permanent_condition("deaf", born_with=True)
        self.assertEqual(len(self.cat.history.condition_events), 1)
        self.cat.permanent_condition["deaf"]["moons_until"] = 0
        self.assertEqual(self.cat.moon_skip_permanent_condition("deaf"), "reveal")
        self.assertEqual(len(self.cat.history.condition_events), 2)
        self.assertEqual(self.cat.history.condition_events[1]["kind"], "congenital")
        self.cat.moon_skip_permanent_condition("deaf")
        self.assertEqual(len(self.cat.history.condition_events), 2)

    def test_short_event_records_resolved_cause(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from scripts.events_module.short.handle_short_events import HandleShortEvents
        event = HandleShortEvents()
        event.main_cat = self.cat
        event.chosen_event = SimpleNamespace(
            text="m_c was attacked by a badger.",
            injury=[{"cats": ["m_c"], "injuries": ["broken back"]}], history=[])
        with patch("scripts.cat.cats.random", return_value=0.9):
            event.handle_injury()
        self.assertEqual(self.cat.history.condition_events[0]["cause"], f"{self.cat.name} was attacked by a badger.")

    def test_patrol_records_the_displayed_outcome_as_cause(self):
        from unittest.mock import patch
        from scripts.events_module.patrol.patrol import Patrol
        from scripts.events_module.patrol.patrol_outcome import PatrolOutcome
        patrol = Patrol()
        patrol.patrol_leader = self.cat
        patrol.random_cat = self.cat
        patrol.patrol_cats = [self.cat]
        patrol.patrol_cat_dict = {"p_l": self.cat}
        self.game.clan.your_cat = self.cat
        outcome = PatrolOutcome(
            text="p_l was attacked by a badger.",
            injury=[{"cats": ["p_l"], "injuries": ["broken back"]}])
        with patch("scripts.cat.cats.random", return_value=0.9):
            text, results, art = outcome.execute_outcome(patrol)
        self.assertIn("badger", text)
        self.assertEqual(self.cat.history.condition_events[0]["cause"], text)
        self.assertIn("broken back", results)

    def test_pregnancy_exemption_does_not_allow_other_major_conditions(self):
        for condition in ("pregnant", "recovering from birth"):
            with self.subTest(condition=condition):
                self.cat.injuries = {condition: {"severity": "major"}}
                self.cat.illnesses = {}
                self.assertTrue(self.cat.not_working())
                self.assertFalse(self.cat.not_working(ignored_injuries=("pregnant", "recovering from birth")))
                self.cat.injuries["broken back"] = {"severity": "major"}
                self.assertTrue(self.cat.not_working(ignored_injuries=("pregnant", "recovering from birth")))
                del self.cat.injuries["broken back"]
                self.cat.illnesses["whitecough"] = {"severity": "major"}
                self.assertTrue(self.cat.not_working(ignored_injuries=("pregnant", "recovering from birth")))

    def test_pregnant_and_recovering_cats_use_queen_library_without_changing_roles(self):
        import json
        from pathlib import Path
        from unittest.mock import patch
        from scripts.events_module.patrol.patrol import Patrol
        self.game.clan.your_cat = self.cat
        queen_ids = {event["patrol_id"] for event in json.loads(Path(
            "resources/dicts/patrols/lifegen/queen.json").read_text())}
        for condition in ("pregnant", "recovering from birth", None):
            with self.subTest(condition=condition), patch.dict(self.game.switches, {"patrol_category": "lifegen"}):
                self.cat.injuries = {condition: {"severity": "major"}} if condition else {}
                patrol = Patrol()
                with patch.object(patrol, "get_filtered_patrols", side_effect=lambda events, *args: (events, [])):
                    events, romance = patrol.get_possible_patrols("Newleaf", "Forest", "camp1", "lifegen", False, "lifegen")
                event_ids = {event.patrol_id for event in events}
                if condition:
                    self.assertTrue(queen_ids.issubset(event_ids))
                else:
                    self.assertFalse(queen_ids.intersection(event_ids))
                self.assertEqual(self.cat.status, "warrior")

    def test_daily_activity_picker_keeps_health_and_once_per_moon_limits(self):
        from unittest.mock import Mock, patch
        from scripts.screens.PatrolScreen import PatrolScreen
        screen = PatrolScreen()
        screen.clear_cat_buttons = Mock()
        screen.elements = {"next_page": Mock(), "last_page": Mock()}
        screen.patrol_screen = "cats"
        screen.current_page = 1
        self.game.clan.your_cat = self.cat
        self.cat.injuries = {"pregnant": {"severity": "major"}}
        with patch.dict(self.game.switches, {"patrol_category": "lifegen", "patrolled": []}):
            screen.current_patrol = []
            screen.update_cat_images_buttons()
            self.assertEqual(screen.current_patrol, [self.cat])
            self.cat.illnesses = {"whitecough": {"severity": "major"}}
            screen.current_patrol = []
            screen.update_cat_images_buttons()
            self.assertEqual(screen.current_patrol, [])
            self.cat.illnesses = {}
            self.game.switches["patrolled"] = ["2"]
            screen.update_cat_images_buttons()
            self.assertEqual(screen.current_patrol, [])
            self.game.switches["patrolled"] = []
            self.game.switches["patrol_category"] = "clangen"
            screen.update_cat_images_buttons()
            self.assertNotIn(self.cat, screen.able_cats)
