import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import ujson

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.cat_relations.inheritance import Inheritance
from scripts.clan import Clan
from scripts.debug_commands.territory import RenameClanCommand
from scripts.game_structure.game_essentials import game


class TestClanCommands(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.clan = Clan(name="Old", game_mode="classic", camp_bg="camp1")
        self.screen = SimpleNamespace(
            name="list screen", clan_name="Old",
            menu_buttons={"heading": SimpleNamespace(full_text="Old")},
            update_heading_text=Mock(), change_screen=Mock(),
        )
        for target, attribute, value in (
            (Inheritance, "all_inheritances", {}),
            (game, "patrolled", []), (game, "told_story", []), (game, "mediated", []),
            (Cat, "all_cats", {}), (Cat, "all_cats_list", []), (Cat, "outside_cats", {}),
            (Clan, "clan_cats", []), (Clan, "starclan_cats", []), (Clan, "darkforest_cats", []),
            (Clan, "unknown_cats", []), (Clan, "all_clans", []),
            (game, "clan", self.clan), (game, "cat_class", Cat), (game, "cat_to_fade", []),
            (game, "current_screen", "list screen"), (game, "all_screens", {"list screen": self.screen}),
            (game, "rpc", SimpleNamespace(update_rpc=Mock())),
        ):
            replacement = patch.object(target, attribute, value)
            replacement.start()
            self.addCleanup(replacement.stop)
        replacement = patch.dict(game.switches, {"clan_name": "Old", "clan_list": ["Old", "Other"], "cat": None, "window_open": False})
        replacement.start()
        self.addCleanup(replacement.stop)
        for module in ("scripts.debug_commands.territory", "scripts.game_structure.game_essentials",
                       "scripts.cat.cats", "scripts.clan", "scripts.game_structure.load_cat"):
            replacement = patch(f"{module}.get_save_dir", return_value=str(self.root))
            replacement.start()
            self.addCleanup(replacement.stop)
        replacement = patch("scripts.debug_commands.territory.add_output_line_to_log")
        self.output = replacement.start()
        self.addCleanup(replacement.stop)
        self.cat = Cat(status="warrior", moons=30, gender="female")
        self.cat.history = History()
        self.clan.your_cat = self.cat
        self.clan.instructor = self.clan.demon = self.clan.wanderer = self.cat
        self.clan.add_cat(self.cat)
        game.save_cats()
        self.clan.save_clan()
        game.save_clanlist("Old")
        metadata = ujson.loads((self.root / "Old.json").read_text(encoding="utf-8"))
        metadata["future_field"] = {"keep": "value"}
        (self.root / "Old.json").write_text(ujson.dumps(metadata), encoding="utf-8")
        (self.root / "Other").mkdir()
        (self.root / "Other.json").write_text('{"clanname": "Other"}', encoding="utf-8")
        (self.root / "Old" / "custom").mkdir()
        (self.root / "Old" / "custom" / "data.bin").write_bytes(b"saved custom data")

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob("*") if path.is_file()}

    def assert_original_save(self, before):
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.clan.name, "Old")
        self.assertEqual(game.switches["clan_name"], "Old")
        self.assertEqual(game.switches["clan_list"], ["Old", "Other"])
        self.screen.update_heading_text.assert_not_called()

    def test_rename_moves_every_saved_file_and_updates_discovery_and_memory(self):
        before = self.snapshot()
        self.cat.moons = 31
        RenameClanCommand().callback(["New", "Colony"])
        self.assertFalse((self.root / "Old").exists())
        self.assertFalse((self.root / "Old.json").exists())
        for path, data in before.items():
            if Path(path).parts[0] == "Old":
                self.assertEqual((self.root / "New Colony" / Path(path).relative_to("Old")).read_bytes(), data)
        metadata = ujson.loads((self.root / "New Colony.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["clanname"], "New Colony")
        self.assertEqual(metadata["future_field"], {"keep": "value"})
        self.assertEqual(self.clan.name, "New Colony")
        self.assertEqual(self.cat.moons, 31)
        self.assertIs(self.clan.your_cat, self.cat)
        self.assertEqual(game.switches["clan_name"], "New Colony")
        self.assertEqual(game.switches["clan_list"], ["New Colony", "Other"])
        self.assertEqual(game.read_clans()[0], "New Colony")
        self.assertEqual((self.root / "currentclan.txt").read_text(), "New Colony")
        self.assertEqual((self.root / "Other.json").read_bytes(), before["Other.json"])
        self.assertEqual(self.screen.clan_name, "New Colony")
        self.screen.update_heading_text.assert_called_once_with("New Colony")
        game.rpc.update_rpc.set.assert_called_once()

    def test_normal_save_and_reload_use_the_new_name(self):
        from scripts.game_structure.load_cat import load_cats

        RenameClanCommand().callback(["New"])
        self.cat.moons = 31
        self.cat.history = History()
        self.cat.get_permanent_condition("allergies", cause="Test condition")
        self.cat.pelt.scars = ["ONE", "TWO"]
        game.save_cats()
        game.clan.save_clan()
        Cat.all_cats.clear()
        Cat.all_cats_list.clear()
        load_cats()
        game.clan.load_clan()
        loaded = Cat.all_cats[self.cat.ID]
        loaded.load_history()
        self.assertEqual(game.clan.name, "New")
        self.assertEqual(game.clan.your_cat.ID, self.cat.ID)
        self.assertEqual(loaded.moons, 31)
        self.assertEqual(loaded.pelt.scars, ["ONE", "TWO"])
        self.assertIn("allergies", loaded.permanent_condition)
        self.assertEqual(loaded.history.condition_events[-1]["condition"], "allergies")
        self.assertFalse((self.root / "Old").exists())
        self.assertFalse((self.root / "Old.json").exists())

    def test_rejects_invalid_reserved_duplicate_and_unsaved_names(self):
        before = self.snapshot()
        for args in ([], ["../Escape"], ["C:/Escape"], ["Bad.Name"], ["CON"], ["LPT1"],
                     ["MyBackup"], ["a" * 251], ["Other"], ["oThEr"], ["old"]):
            with self.subTest(args=args):
                RenameClanCommand().callback(args)
                self.assert_original_save(before)
        with patch.object(game, "clan", None):
            RenameClanCommand().callback(["New"])
        with patch.object(game, "current_screen", "make clan screen"):
            RenameClanCommand().callback(["New"])
        (self.root / "Old.json").unlink()
        before = self.snapshot()
        RenameClanCommand().callback(["New"])
        self.assert_original_save(before)

    def test_rejects_metadata_collisions_and_invalid_metadata(self):
        for filename in ("New.json", "Newclan.json"):
            with self.subTest(filename=filename):
                path = self.root / filename
                path.write_bytes(b"unrelated file")
                before = self.snapshot()
                RenameClanCommand().callback(["New"])
                self.assert_original_save(before)
                path.unlink()
        for data in ('{"clanname": "Wrong"}', '[]', '{invalid'):
            with self.subTest(data=data):
                (self.root / "Old.json").write_text(data)
                before = self.snapshot()
                RenameClanCommand().callback(["New"])
                self.assert_original_save(before)

    def test_rolls_back_file_write_folder_move_pointer_and_metadata_removal_failures(self):
        original_unlink = Path.unlink
        old_file = self.root / "Old.json"

        def fail_old_unlink(path, *args, **kwargs):
            if path == old_file:
                raise PermissionError("Metadata is locked")
            return original_unlink(path, *args, **kwargs)

        def fail_pointer(name):
            (self.root / "clanlist.txt").unlink()
            (self.root / "currentclan.txt").write_bytes(b"partial write")
            raise OSError("Pointer write failed")

        def fail_write(data, output, **kwargs):
            output.write("partial write")
            raise OSError("Metadata write failed")

        failures = (
            patch("scripts.debug_commands.territory.ujson.dump", side_effect=fail_write),
            patch.object(Path, "rename", side_effect=PermissionError("Folder is locked")),
            patch.object(game, "save_clanlist", side_effect=fail_pointer),
            patch.object(Path, "unlink", fail_old_unlink),
        )
        (self.root / "clanlist.txt").write_bytes(b"Old\nOther\n")
        for failure in failures:
            with self.subTest(failure=failure):
                before = self.snapshot()
                with failure:
                    RenameClanCommand().callback(["New"])
                self.assert_original_save(before)
                self.assertIn("original save was restored", self.output.call_args.args[0])

    def test_failed_rename_restores_missing_pointers_as_missing(self):
        (self.root / "currentclan.txt").unlink()
        before = self.snapshot()

        def fail_pointer(name):
            (self.root / "currentclan.txt").write_bytes(b"partial write")
            raise OSError("Pointer write failed")

        with patch.object(game, "save_clanlist", side_effect=fail_pointer):
            RenameClanCommand().callback(["New"])
        self.assert_original_save(before)

    def test_rejects_a_source_outside_the_save_directory(self):
        before = self.snapshot()
        with patch.object(self.clan, "name", "../Outside"):
            RenameClanCommand().callback(["New"])
            self.assertEqual(self.clan.name, "../Outside")
        self.assert_original_save(before)

    def test_neighbor_regeneration_clears_old_war_focus_and_medicine_cats(self):
        from scripts.debug_commands.territory import _regenerate_other_clans

        self.clan.clans_in_focus = ["Old Neighbor"]
        self.clan.war = {"at_war": True, "enemy": "Old Neighbor", "duration": 8}
        game.switches["other_med"] = [[self.cat]]
        self.assertEqual(_regenerate_other_clans(0), (0, 0))
        self.assertEqual(self.clan.clans_in_focus, [])
        self.assertEqual(self.clan.war, {"at_war": False, "enemy": None, "duration": 0})
        self.assertNotIn("other_med", game.switches)
        self.clan.save_clan()
        metadata = ujson.loads((self.root / "Old.json").read_text())
        self.assertEqual(metadata["clans_in_focus"], [])
        self.assertFalse(metadata["war"]["at_war"])
        self.assertNotIn("other_med", metadata)

    def test_camp_lighting_moves_to_global_settings_and_preserves_legacy_choice(self):
        settings_file = self.root / "settings.json"
        legacy = self.root / "Old" / "clan_settings.json"
        legacy.write_text(ujson.dumps({"random camp lighting": True}), encoding="utf-8")
        with patch.object(game, "settings", game.settings.copy()), patch.object(game, "_random_camp_lighting_loaded", False):
            game.settings["random camp lighting"] = False
            self.assertNotIn("random camp lighting", self.clan.clan_settings)
            self.assertFalse(game.settings["random camp lighting"])
            self.clan.load_clan_settings()
            self.assertTrue(game.settings["random camp lighting"])
            self.assertTrue(ujson.loads(settings_file.read_text())["random camp lighting"])
            game.settings["random camp lighting"] = False
            game.load_settings()
            self.assertTrue(game.settings["random camp lighting"])
            game.switch_setting("random camp lighting")
            self.clan.load_clan_settings()
            self.assertFalse(game.settings["random camp lighting"])
            game.save_settings()
            game.settings["random camp lighting"] = True
            game.load_settings()
            self.assertFalse(game.settings["random camp lighting"])
            game._random_camp_lighting_loaded = False
            game.save_settings()
            self.clan.load_clan_settings()
            self.assertFalse(game.settings["random camp lighting"])

    def test_location_command_selects_or_randomizes_camps_and_saves_them(self):
        from scripts.debug_commands.territory import ChangeClanCommand, CAMP_AVAILABILITY

        outsider = Cat(status="loner", moons=30, gender="female")
        outsider.outside = True
        outsider.history = History()
        for args in (["Beach", "4", "2"], ["Mountainous", "random", "3"], ["random", "4"]):
            with self.subTest(args=args), patch("scripts.clan.clan_symbol_sprite", return_value="symbolTHORN0"), patch(
                "scripts.screens.screens_core.screens_core.rebuild_bgs"
            ) as rebuild:
                ChangeClanCommand().callback(args)
                self.assertIn(self.clan.camp_bg, CAMP_AVAILABILITY[self.clan.biome])
                if args[0] != "random":
                    self.assertEqual(self.clan.biome, args[0])
                if args[0] != "random" and args[1] == "4":
                    self.assertEqual(self.clan.camp_bg, "camp4")
                self.assertEqual(len(self.clan.all_clans), int(args[-1]))
                self.assertIn(outsider.ID, Cat.all_cats)
                rebuild.assert_called_once()
                self.screen.change_screen.assert_called_with("camp screen")
                metadata = ujson.loads((self.root / "Old.json").read_text())
                self.assertEqual((metadata["biome"], metadata["camp_bg"]), (self.clan.biome, self.clan.camp_bg))

    def test_wipe_finds_uncached_outsiders_and_rebuilds_the_cache(self):
        from scripts.debug_commands.territory import _wipe_outsider_cats

        outsider = Cat(status="loner", moons=30, gender="female")
        outsider.outside = True
        self.clan.add_cat(outsider)
        Cat.outside_cats[self.cat.ID] = self.cat
        Cat.outside_cats["missing"] = outsider
        self.assertNotIn(outsider.ID, Cat.outside_cats)
        self.assertEqual(_wipe_outsider_cats(0), (1, 0))
        self.assertNotIn(outsider.ID, Cat.all_cats)
        self.assertNotIn(outsider, Cat.all_cats_list)
        self.assertNotIn(outsider.ID, self.clan.clan_cats)
        self.assertEqual(Cat.outside_cats, {})
        self.assertIs(Cat.all_cats[self.cat.ID], self.cat)

    def test_wipe_protects_player_guides_and_colony_roles_even_when_outside(self):
        from scripts.debug_commands.territory import _wipe_outsider_cats

        protected = [self.cat]
        for role in ("instructor", "demon", "wanderer", "leader", "deputy", "medicine_cat"):
            cat = Cat(status="warrior", moons=30, gender="female")
            setattr(self.clan, role, cat)
            protected.append(cat)
        for cat in protected:
            cat.outside = True
        self.assertEqual(_wipe_outsider_cats(0), (0, 0))
        self.assertEqual(set(Cat.outside_cats), {cat.ID for cat in protected})
        for cat in protected:
            self.assertIs(Cat.all_cats[cat.ID], cat)

    def test_wipe_removes_live_references_and_orphaned_condition_history_files(self):
        from scripts.debug_commands.territory import _wipe_outsider_cats

        outsider = Cat(status="loner", moons=60, gender="female")
        outsider.outside = True
        outsider.history = History()
        self.clan.add_cat(outsider)
        outsider.get_permanent_condition("allergies", cause="Test condition")
        parent = Cat(status="warrior", moons=80, gender="female")
        parent.history = History()
        child = Cat(status="apprentice", moons=8, gender="female", parent1=outsider.ID, parent2=parent.ID)
        child.history = History()
        child.mentor = outsider.ID
        child.adoptive_parents = [outsider.ID, parent.ID]
        for cat in (self.cat, parent, child):
            cat.mates = [outsider.ID]
            cat.previous_mates = [outsider.ID]
            cat.former_mentor = [outsider.ID]
            cat.former_apprentices = [outsider.ID]
            cat.apprentice = [outsider.ID]
            cat.df_mentor = outsider.ID
            cat.df_apprentices = [outsider.ID]
            cat.create_one_relationship(outsider)
            cat.create_inheritance_new_cat()
        self.clan.pregnancy_data = {outsider.ID: {"second_parent": parent.ID}, parent.ID: {"second_parent": outsider.ID, "moons": 1}}
        self.clan.focus_cat = outsider
        self.clan.murdered = {"murderer": self.cat.ID, "victim": outsider.ID, "accomplice": [None, False]}
        game.switches["cat"] = outsider.ID
        game.patrolled.extend([outsider.ID, self.cat.ID])
        game.told_story.extend([outsider.ID, self.cat.ID])
        game.mediated.extend([[self.cat.ID, outsider.ID], [self.cat.ID, parent.ID]])
        outsider.outside = False
        game.save_cats()
        outsider.outside = True
        game.cat_to_fade.append(outsider.ID)
        history_path = self.root / "Old" / "history" / f"{outsider.ID}_history.json"
        condition_path = self.root / "Old" / "conditions" / f"{outsider.ID}_conditions.json"
        self.assertTrue(history_path.exists())
        self.assertTrue(condition_path.exists())
        self.assertEqual(_wipe_outsider_cats(0), (1, 0))
        self.assertIsNone(child.parent1)
        self.assertEqual(child.parent2, parent.ID)
        self.assertEqual(child.adoptive_parents, [parent.ID])
        self.assertIn(child.mentor, {self.cat.ID, parent.ID})
        self.assertIn(child.ID, Cat.all_cats[child.mentor].apprentice)
        for cat in (self.cat, parent, child):
            self.assertNotIn(outsider.ID, cat.relationships)
            for field in ("mates", "previous_mates", "former_mentor", "former_apprentices", "apprentice", "df_apprentices"):
                self.assertNotIn(outsider.ID, getattr(cat, field))
            self.assertIsNone(cat.df_mentor)
            self.assertNotIn(outsider.ID, cat.inheritance.all_involved)
        self.assertNotIn(outsider.ID, Inheritance.all_inheritances)
        self.assertEqual(self.clan.pregnancy_data, {parent.ID: {"second_parent": None, "moons": 1}})
        self.assertIsNone(self.clan.focus_cat)
        self.assertEqual(self.clan.murdered, {})
        self.assertEqual(game.switches["cat"], self.cat.ID)
        self.assertEqual(game.cat_to_fade, [])
        self.assertEqual(game.patrolled, [self.cat.ID])
        self.assertEqual(game.told_story, [self.cat.ID])
        self.assertEqual(game.mediated, [[self.cat.ID, parent.ID]])
        self.assertFalse(history_path.exists())
        self.assertFalse(condition_path.exists())
        from scripts.game_structure.load_cat import load_cats
        game.save_cats()
        Cat.all_cats.clear()
        Cat.all_cats_list.clear()
        load_cats()
        loaded = Cat.all_cats[child.ID]
        self.assertIsNone(loaded.parent1)
        self.assertEqual(loaded.parent2, parent.ID)
        self.assertEqual(loaded.adoptive_parents, [parent.ID])
        self.assertEqual(loaded.mates, [])
        self.assertEqual(loaded.former_mentor, [])
        self.assertIsNone(loaded.df_mentor)
        self.assertNotIn(outsider.ID, loaded.relationships)
        self.assertNotIn(outsider.ID, loaded.inheritance.all_involved)

    def test_relocation_wipe_regenerates_only_outsiders_and_survives_reload(self):
        from scripts.debug_commands.territory import ChangeClanCommand
        from scripts.game_structure.load_cat import load_cats

        guides = set()
        for role in ("instructor", "demon", "wanderer"):
            guide = Cat(status="warrior", moons=150, gender="female")
            guide.dead = guide.outside = True
            guide.history = History()
            self.clan.add_cat(guide)
            setattr(self.clan, role, guide)
            guides.add(guide.ID)
        outsider = Cat(status="loner", moons=30, gender="female")
        outsider.outside = True
        outsider.history = History()
        before = self.cat.get_save_dict()
        with patch("scripts.screens.screens_core.screens_core.rebuild_bgs"), patch.object(
            self.clan, "generate_outsider_mates"
        ) as mates, patch.object(self.clan, "generate_outsider_families") as families:
            ChangeClanCommand().callback(["Beach", "4", "0", "3", "false", "true"])
        self.assertNotIn(outsider.ID, Cat.all_cats)
        self.assertEqual(len(set(Cat.outside_cats) - guides), 3)
        self.assertEqual(self.cat.get_save_dict(), before)
        for cat_id in set(Cat.outside_cats) - guides:
            cat = Cat.outside_cats[cat_id]
            self.assertIsNotNone(cat.inheritance)
            self.assertIsNone(cat.history)
        mates.assert_not_called()
        families.assert_not_called()
        ids = set(Cat.outside_cats) - guides
        Cat.all_cats.clear()
        Cat.all_cats_list.clear()
        Cat.outside_cats.clear()
        load_cats()
        self.clan.load_clan()
        self.assertEqual({cat.ID for cat in Cat.all_cats.values() if cat.outside} - guides, ids)
        self.assertEqual((game.clan.biome, game.clan.camp_bg), ("Beach", "camp4"))
        self.assertNotIn(outsider.ID, Cat.all_cats)
        self.assertEqual(game.clan.your_cat.ID, self.cat.ID)
        from scripts.debug_commands.territory import _wipe_outsider_cats
        self.assertEqual(_wipe_outsider_cats(0), (3, 0))
        self.assertEqual(set(Cat.outside_cats), guides)
        self.assertIn(self.cat.ID, Cat.all_cats)

    def test_relocation_rejects_negative_counts_and_busy_editors_without_changes(self):
        from scripts.debug_commands.territory import ChangeClanCommand

        before = self.snapshot()
        for args in (["Beach", "4", "-1"], ["Beach", "4", "2", "-1"]):
            with self.subTest(args=args):
                ChangeClanCommand().callback(args)
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(self.clan.biome, "Forest")
        for name in ("make clan screen", "customize cat screen"):
            with patch.object(game, "current_screen", name):
                ChangeClanCommand().callback(["random"])
            self.assertEqual(self.snapshot(), before)

    def test_default_outsider_regeneration_updates_inheritance_and_cache(self):
        from scripts.debug_commands.territory import _wipe_outsider_cats

        with patch("scripts.clan.randint", side_effect=lambda low, high: 2 if (low, high) == (0, 5) else 30):
            self.assertEqual(_wipe_outsider_cats(), (0, 2))
        self.assertEqual(len(Cat.outside_cats), 2)
        self.assertTrue(all(cat.inheritance is not None for cat in Cat.outside_cats.values()))

    def test_legacy_current_pointer_is_updated(self):
        (self.root / "clanlist.txt").write_text("Old\nOther\n")
        RenameClanCommand().callback(["New"])
        self.assertFalse((self.root / "clanlist.txt").exists())
        self.assertEqual(game.read_clans()[0], "New")

    def test_rename_keeps_non_colony_screen_headings(self):
        self.screen.name = "profile screen"
        self.screen.menu_buttons["heading"].full_text = "Cat profile"
        RenameClanCommand().callback(["New"])
        self.assertEqual(self.clan.name, "New")
        self.screen.update_heading_text.assert_not_called()

    def test_rename_updates_the_live_heading_widget(self):
        from scripts.screens.Screens import Screens

        screen = Screens("camp screen")
        heading = screen.menu_buttons["heading"]
        self.addCleanup(screen.update_heading_text, heading.full_text)
        screen.update_heading_text("Old")
        with patch.object(game, "current_screen", "camp screen"):
            RenameClanCommand().callback(["New", "Colony"])
        self.assertEqual(heading.text, "New Colony")

    def test_registered_console_command_accepts_quoted_names(self):
        from scripts.debug_console import debug_mode
        debug_mode.debug_menu.process_command('renameclan "New Colony"')
        self.assertEqual(self.clan.name, "New Colony")
        self.assertTrue((self.root / "New Colony.json").is_file())
