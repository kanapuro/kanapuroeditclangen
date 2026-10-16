import os
from pathlib import Path, PureWindowsPath
from random import choice, randint
from re import fullmatch
from typing import List

import ujson

from scripts.cat.cats import Cat
from scripts.cat_relations.inheritance import Inheritance
from scripts.cat.names import names
from scripts.clan import OtherClan, generate_clan_name
from scripts.utility import create_new_cat
from scripts.debug_commands.command import Command
from scripts.debug_commands.utils import add_output_line_to_log
from scripts.game_structure.game_essentials import game
from scripts.housekeeping.datadir import get_save_dir


CAMP_AVAILABILITY = {
    "Forest": ["camp1", "camp2", "camp3", "camp4", "camp5", "camp6", "camp7", "camp8"],
    "Mountainous": ["camp1", "camp2", "camp3", "camp4", "camp5", "camp6", "camp7"],
    "Plains": ["camp1", "camp2", "camp3", "camp4", "camp5", "camp6", "camp7", "camp8", "camp9"],
    "Beach": ["camp1", "camp2", "camp3", "camp4", "camp5"]
}

CAMP_NAMES = {
    "Forest": {
        "camp1": "Classic",
        "camp2": "Gully",
        "camp3": "Grotto",
        "camp4": "Lakeside",
        "camp5": "Pine",
        "camp6": "Birch",
        "camp7": "Shaded Marsh",
        "camp8": "Ancient Ruins"
    },
    "Mountainous": {
        "camp1": "Cliff",
        "camp2": "Cavern",
        "camp3": "Crystal River",
        "camp4": "Rocky Slope",
        "camp5": "Quarry",
        "camp6": "Ruins",
        "camp7": "Lush Cave"
    },
    "Plains": {
        "camp1": "Grasslands",
        "camp2": "Tunnels",
        "camp3": "Wastelands",
        "camp4": "Taiga",
        "camp5": "Desert",
        "camp6": "City",
        "camp7": "Farm",
        "camp8": "Bushland",
        "camp9": "Castle"
    },
    "Beach": {
        "camp1": "Tidepools",
        "camp2": "Tidal Cave",
        "camp3": "Shipwreck",
        "camp4": "Fjord",
        "camp5": "Tropical Island"
    }
}


def _parse_bool(arg: str):
    if arg.lower() in ["true", "1", "yes", "y", "on"]:
        return True
    if arg.lower() in ["false", "0", "no", "n", "off"]:
        return False
    return None


def _set_location(biome: str, camp_bg: str):
    game.clan.biome = biome
    game.clan.camp_bg = camp_bg
    game.switches["biome"] = biome
    game.switches["camp_bg"] = camp_bg


def _regenerate_other_clans(target_count: int = None):
    """Clear and regenerate outsider clans. If target_count is provided,
    create exactly that many outsider clans; otherwise pick a random 1-5."""
    old_count = len(game.clan.all_clans)
    game.clan.all_clans.clear()
    game.clan.clans_in_focus.clear()
    game.clan.war.update(at_war=False, enemy=None, duration=0)
    game.switches.pop("other_med", None)

    if isinstance(target_count, int) and target_count >= 0:
        number_other_clans = target_count
    else:
        number_other_clans = randint(1, 5)

    other_clan_names = [game.clan.name]
    all_prefixes = names.names_dict["normal_prefixes"] + names.names_dict["clan_prefixes"]
    for _ in range(number_other_clans):
        other_clan_name, _ = generate_clan_name(all_prefixes, existing_names=other_clan_names)
        other_clan = OtherClan(name=other_clan_name)
        game.clan.all_clans.append(other_clan)
        other_clan_names.append(str(other_clan_name))

    return old_count, len(game.clan.all_clans)


def _wipe_outsider_cats(target_count: int = None):
    protected = {cat.ID for cat in (
        game.clan.your_cat, game.clan.instructor, game.clan.demon, game.clan.wanderer,
        game.clan.leader, game.clan.deputy, game.clan.medicine_cat,
    ) if cat is not None} | set(game.clan.med_cat_list)
    removed = {cat.ID for cat in Cat.all_cats.values() if cat.outside and cat.ID not in protected}
    directory = Path(get_save_dir()) / game.clan.name
    for cat_id in removed:
        game.clan.remove_cat(cat_id)
        Inheritance.all_inheritances.pop(cat_id, None)
        (directory / "history" / f"{cat_id}_history.json").unlink(missing_ok=True)
        (directory / "conditions" / f"{cat_id}_conditions.json").unlink(missing_ok=True)

    for cat in Cat.all_cats.values():
        lost_mentor = cat.mentor in removed
        lost_df_mentor = cat.df_mentor in removed
        for field in ("parent1", "parent2", "mentor", "df_mentor"):
            if getattr(cat, field) in removed:
                setattr(cat, field, None)
        for field in ("adoptive_parents", "mates", "previous_mates", "former_mentor",
                      "apprentice", "former_apprentices", "df_apprentices"):
            values = getattr(cat, field)
            values[:] = [cat_id for cat_id in values if cat_id not in removed]
        for cat_id in removed:
            cat.relationships.pop(cat_id, None)
        if lost_mentor:
            cat.update_mentor()
        if lost_df_mentor and cat.joined_df:
            cat.update_df_mentor()

    for cat in Cat.all_cats.values():
        if cat.inheritance is not None:
            cat.inheritance.update_inheritance()
    for cat_id in removed:
        game.clan.pregnancy_data.pop(cat_id, None)
    for pregnancy in game.clan.pregnancy_data.values():
        if pregnancy.get("second_parent") in removed:
            pregnancy["second_parent"] = None
    if game.clan.focus_cat and game.clan.focus_cat.ID in removed:
        game.clan.focus_cat = None
    murder = game.clan.murdered
    if (murder.get("murderer") in removed or murder.get("victim") in removed
            or (murder.get("accomplice") and murder["accomplice"][0] in removed)):
        murder.clear()
    if game.switches["cat"] in removed:
        game.switches["cat"] = game.clan.your_cat.ID
    game.cat_to_fade[:] = [cat_id for cat_id in game.cat_to_fade if cat_id not in removed]
    game.patrolled[:] = [cat_id for cat_id in game.patrolled if cat_id not in removed]
    game.told_story[:] = [cat_id for cat_id in game.told_story if cat_id not in removed]
    game.mediated[:] = [pair for pair in game.mediated if not removed.intersection(pair)]

    before = set(Cat.all_cats)
    if target_count is None:
        game.clan.generate_outsiders()
    else:
        for _ in range(target_count):
            outsider = create_new_cat(
                Cat,
                status=choice(["loner", "kittypet"]),
                age=randint(15, 120),
                outside=True,
                thought="Wanders around beyond the Clan's borders",
            )[0]
            outsider.history.beginning = None
    newcomers = [cat for cat_id, cat in Cat.all_cats.items() if cat_id not in before]
    for cat in newcomers:
        cat.create_inheritance_new_cat()
    Cat.outside_cats.clear()
    for cat in Cat.all_cats.values():
        game.clan.add_to_outside(cat)
    return len(removed), len(newcomers)


class SetBiomeCommand(Command):
    name = "set"
    description = "Set clan location (biome)"
    usage = "<biome> [camp]"

    def callback(self, args: List[str]):
        if not game.clan:
            add_output_line_to_log("No Clan loaded. Cannot set biome.")
            return
        
        if len(args) == 0:
            add_output_line_to_log("Specify a biome.")
            add_output_line_to_log(f"Available biomes: {', '.join(game.clan.BIOME_TYPES)}")
            add_output_line_to_log("Usage: location set <biome> [camp]")
            return

        biome = args[0].capitalize()
        if biome not in game.clan.BIOME_TYPES:
            add_output_line_to_log(f"Biome '{args[0]}' not recognized.")
            add_output_line_to_log(f"Available biomes: {', '.join(game.clan.BIOME_TYPES)}")
            return
        
        old_biome = game.clan.biome
        old_camp = game.clan.camp_bg
        game.clan.biome = biome
        game.switches["biome"] = biome
        
        # If camp type specified, validate and set it
        if len(args) >= 2:
            camp_input = args[1].lower()
            if not camp_input.startswith("camp"):
                camp_input = f"camp{camp_input}"
            
            if camp_input in CAMP_AVAILABILITY.get(biome, []):
                game.clan.camp_bg = camp_input
                game.switches["camp_bg"] = camp_input
                add_output_line_to_log(f"Clan location changed from {old_biome} ({old_camp}) to {biome} ({camp_input}).")
            else:
                game.clan.camp_bg = "camp1"  # Default to camp1
                game.switches["camp_bg"] = "camp1"
                add_output_line_to_log(f"Camp '{camp_input}' not available in {biome}. Defaulting to camp1.")
                add_output_line_to_log(f"Available camps for {biome}: {', '.join(CAMP_AVAILABILITY[biome])}")
        else:
            # Keep existing camp if compatible, otherwise default to camp1
            if old_camp not in CAMP_AVAILABILITY.get(biome, []):
                game.clan.camp_bg = "camp1"
                game.switches["camp_bg"] = "camp1"
                add_output_line_to_log(f"Clan location changed from {old_biome} to {biome}. Camp reset to camp1.")
            else:
                game.switches["camp_bg"] = old_camp
                add_output_line_to_log(f"Clan location changed from {old_biome} to {biome}. Kept {old_camp}.")


class GetBiomeCommand(Command):
    name = "get"
    description = "Get current clan location (biome) and camp"
    aliases = ["show"]

    def callback(self, args: List[str]):
        if not game.clan:
            add_output_line_to_log("No Clan loaded.")
            return
        
        biome = game.clan.biome
        camp = game.clan.camp_bg
        
        # Check if there's a special name for this camp
        camp_name = CAMP_NAMES.get(biome, {}).get(camp, "")
        if camp_name:
            add_output_line_to_log(f"Current clan location: {biome}, {camp} ({camp_name})")
        else:
            add_output_line_to_log(f"Current clan location: {biome}, {camp}")
        
        add_output_line_to_log(f"Available biomes: {', '.join(game.clan.BIOME_TYPES)}")
        add_output_line_to_log(f"Available camps for {biome}: {', '.join(CAMP_AVAILABILITY.get(biome, []))}")


class SetCampCommand(Command):
    name = "camp"
    description = "Set camp type for current biome"
    usage = "<camp>"
    aliases = ["setcamp"]

    def callback(self, args: List[str]):
        if not game.clan:
            add_output_line_to_log("No Clan loaded. Cannot set camp.")
            return
        
        if len(args) == 0:
            add_output_line_to_log("Specify a camp type.")
            biome = game.clan.biome
            add_output_line_to_log(f"Available camps for {biome}: {', '.join(CAMP_AVAILABILITY.get(biome, []))}")
            return
        
        camp_input = args[0].lower()
        if not camp_input.startswith("camp"):
            camp_input = f"camp{camp_input}"
        
        biome = game.clan.biome
        if camp_input in CAMP_AVAILABILITY.get(biome, []):
            old_camp = game.clan.camp_bg
            game.clan.camp_bg = camp_input
            game.switches["camp_bg"] = camp_input
            
            camp_name = CAMP_NAMES.get(biome, {}).get(camp_input, "")
            if camp_name:
                add_output_line_to_log(f"Camp changed from {old_camp} to {camp_input} ({camp_name}).")
            else:
                add_output_line_to_log(f"Camp changed from {old_camp} to {camp_input}.")
        else:
            add_output_line_to_log(f"Camp '{camp_input}' not available in {biome}.")
            add_output_line_to_log(f"Available camps for {biome}: {', '.join(CAMP_AVAILABILITY.get(biome, []))}")


class RandomCampCommand(Command):
    name = "random"
    description = "Set a random camp for current biome"
    aliases = ["rand", "randomize"]

    def callback(self, args: List[str]):
        if not game.clan:
            add_output_line_to_log("No Clan loaded. Cannot set camp.")
            return
        
        biome = game.clan.biome
        available_camps = CAMP_AVAILABILITY.get(biome, [])
        
        if not available_camps:
            add_output_line_to_log(f"No camps available for {biome}.")
            return
        
        old_camp = game.clan.camp_bg
        if len(available_camps) > 1 and old_camp in available_camps:
            other_camps = [c for c in available_camps if c != old_camp]
            new_camp = choice(other_camps)
        else:
            new_camp = choice(available_camps)
        
        game.clan.camp_bg = new_camp
        game.switches["camp_bg"] = new_camp
        camp_name = CAMP_NAMES.get(biome, {}).get(new_camp, "")
        
        if camp_name:
            add_output_line_to_log(f"Random camp selected: {new_camp} ({camp_name})")
        else:
            add_output_line_to_log(f"Random camp selected: {new_camp}")


class RegenerateClansCommand(Command):
    name = "regenerate"
    description = "Regenerate all outsider clans"
    aliases = ["regen", "reset"]

    def callback(self, args: List[str]):
        if not game.clan:
            add_output_line_to_log("No Clan loaded. Cannot regenerate outsider clans.")
            return
        
        old_count, new_count = _regenerate_other_clans()

        add_output_line_to_log(f"Regenerated outsider clans. Removed {old_count}, created {new_count}.")
        add_output_line_to_log(f"New clans: {', '.join([str(clan.name) for clan in game.clan.all_clans])}")


class ListClansCommand(Command):
    name = "list"
    description = "List all outsider clans"
    aliases = ["l"]

    def callback(self, args: List[str]):
        if not game.clan:
            add_output_line_to_log("No Clan loaded.")
            return
        
        if not game.clan.all_clans:
            add_output_line_to_log("No outsider clans exist.")
            return
        
        add_output_line_to_log(f"Outsider clans ({len(game.clan.all_clans)}):")
        for clan in game.clan.all_clans:
            add_output_line_to_log(f"  {clan.name}Clan - Relations: {clan.relations}, Temperament: {clan.temperament}")


class LocationCommand(Command):
    name = "location"
    description = "Manage clan location (biome) and camp type"
    aliases = ["biome", "loc"]

    sub_commands = [
        GetBiomeCommand(),
        SetBiomeCommand(),
        SetCampCommand(),
        RandomCampCommand()
    ]

    def callback(self, args: List[str]):
        # Default behavior: show current biome and camp
        if not game.clan:
            add_output_line_to_log("No Clan loaded.")
            return
        
        biome = game.clan.biome
        camp = game.clan.camp_bg
        
        # Check if there's a special name for this camp
        camp_name = CAMP_NAMES.get(biome, {}).get(camp, "")
        if camp_name:
            add_output_line_to_log(f"Current clan location: {biome}, {camp} ({camp_name})")
        else:
            add_output_line_to_log(f"Current clan location: {biome}, {camp}")
        
        add_output_line_to_log(f"Available biomes: {', '.join(game.clan.BIOME_TYPES)}")
        add_output_line_to_log(f"Available camps for {biome}: {', '.join(CAMP_AVAILABILITY.get(biome, []))}")
        add_output_line_to_log("To change location: location set <biome> [camp]")
        add_output_line_to_log("To change camp only: location camp <camp>")


class RenameClanCommand(Command):
    name = "renameclan"
    description = "Rename the loaded colony and its save"
    usage = "<name>"

    def callback(self, args: List[str]):
        if not game.clan:
            add_output_line_to_log("Please load a Clan first")
            return
        if game.current_screen == "make clan screen":
            add_output_line_to_log("Please finish colony creation first")
            return
        new_name = " ".join(args).strip()
        if not new_name or not fullmatch(r"[A-Za-z0-9 ]+", new_name) or len(new_name) > 250:
            add_output_line_to_log("Use a colony name of 1-250 letters, numbers, or spaces")
            return
        if PureWindowsPath(new_name).is_reserved() or "backup" in new_name.casefold():
            add_output_line_to_log("That name is reserved for system files or save backups")
            return
        old_name = game.clan.name
        if new_name.casefold() == old_name.casefold():
            add_output_line_to_log(f"The colony is already named {old_name} (names ignore capitalization)")
            return
        root = Path(get_save_dir()).resolve()
        old_folder = root / old_name
        old_file = root / f"{old_name}.json"
        new_folder = root / new_name
        new_file = root / f"{new_name}.json"
        try:
            if old_folder.resolve().parent != root or old_file.resolve().parent != root:
                add_output_line_to_log("The loaded save is outside the save directory")
                return
            if not old_folder.is_dir() or not old_file.is_file():
                add_output_line_to_log("Please save the colony before renaming it")
                return
            targets = {new_name.casefold(), f"{new_name}.json".casefold(), f"{new_name}clan.json".casefold()}
            if any(path.name.casefold() in targets for path in root.iterdir()):
                add_output_line_to_log("A save or file with that name already exists")
                return
            metadata = ujson.loads(old_file.read_text(encoding="utf-8"))
            if not isinstance(metadata, dict) or metadata.get("clanname") != old_name:
                add_output_line_to_log("The save metadata does not match the loaded colony")
                return
            pointers = [root / filename for filename in ("currentclan.txt", "clanlist.txt")]
            pointer_data = [(path, path.read_bytes() if path.exists() else None) for path in pointers]
        except (OSError, ValueError) as error:
            add_output_line_to_log(f"Could not read the colony save: {error}")
            return

        metadata["clanname"] = new_name
        created_file = moved_folder = changed_pointer = False
        try:
            # Keep the old metadata until every part of the rename has succeeded.
            with new_file.open("x", encoding="utf-8") as output:
                created_file = True
                ujson.dump(metadata, output, indent=4)
                output.flush()
                os.fsync(output.fileno())
            old_folder.rename(new_folder)
            moved_folder = True
            changed_pointer = True
            game.save_clanlist(new_name)
            old_file.unlink()
        except OSError as error:
            if moved_folder:
                new_folder.rename(old_folder)
            if changed_pointer:
                for path, data in pointer_data:
                    if data is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(data)
            if created_file:
                new_file.unlink()
            add_output_line_to_log(f"Could not rename the colony; the original save was restored: {error}")
            return

        game.clan.name = new_name
        game.switches["clan_name"] = new_name
        game.switches["clan_list"] = [new_name] + [name for name in game.switches["clan_list"] if name != old_name]
        screen = game.all_screens[game.current_screen]
        if screen.name == "list screen":
            screen.clan_name = new_name
        if screen.menu_buttons["heading"].html_text == old_name:
            screen.update_heading_text(new_name)
        game.rpc.update_rpc.set()
        add_output_line_to_log(f"Renamed {old_name} to {new_name}")


class ChangeClanCommand(Command):
    name = "changeclan"
    description = "Change clan location and regenerate clan data"
    aliases = ["relocate", "rehome"]
    usage = "<random | biome camp|random> [other_count] [outsider_count] [regenerate_other_clans] [wipe_outsiders]"

    def callback(self, args: List[str]):
        if not game.clan:
            add_output_line_to_log("No Clan loaded. Cannot change clan location.")
            return

        if (game.current_screen in ("make clan screen", "customize cat screen")
                or game.switches.get("window_open")):
            add_output_line_to_log("Please finish the current editor or window first")
            return

        if len(args) == 0:
            add_output_line_to_log(f"Usage: {self.name} {self.usage}")
            return

        # Defer defaults until after parsing so booleans can be specified freely
        regenerate_other_clans = None
        wipe_outsiders = None
        other_count = None
        outsider_count = None

        first_arg = args[0].lower()
        remaining_args = args[1:]

        if first_arg == "random":
            biome = choice(game.clan.BIOME_TYPES)
            camp_bg = choice(CAMP_AVAILABILITY[biome])
        else:
            biome = args[0].capitalize()
            if biome not in game.clan.BIOME_TYPES:
                add_output_line_to_log(f"Biome '{args[0]}' not recognized.")
                add_output_line_to_log(f"Available biomes: {', '.join(game.clan.BIOME_TYPES)}")
                return

            if len(args) < 2:
                add_output_line_to_log(f"Usage: {self.name} {self.usage}")
                return

            camp_arg = args[1].lower()
            remaining_args = args[2:]
            if camp_arg == "random":
                camp_bg = choice(CAMP_AVAILABILITY[biome])
            else:
                if not camp_arg.startswith("camp"):
                    camp_arg = f"camp{camp_arg}"

                if camp_arg not in CAMP_AVAILABILITY.get(biome, []):
                    add_output_line_to_log(f"Camp '{camp_arg}' not available in {biome}.")
                    add_output_line_to_log(f"Available camps for {biome}: {', '.join(CAMP_AVAILABILITY.get(biome, []))}")
                    return
                camp_bg = camp_arg

        # More flexible parsing: accept integers and booleans in any order
        parsed_tokens = list(remaining_args)
        i = 0
        while i < len(parsed_tokens):
            tok = parsed_tokens[i]
            # try integer
            try:
                val = int(tok)
                if val < 0:
                    add_output_line_to_log("Colony and outsider counts cannot be negative")
                    return
                if other_count is None:
                    other_count = val
                elif outsider_count is None:
                    outsider_count = val
                else:
                    add_output_line_to_log(f"Unexpected integer token '{tok}'.")
                    add_output_line_to_log(f"Usage: {self.name} {self.usage}")
                    return
                i += 1
                continue
            except ValueError:
                pass

            # try boolean
            parsed_bool = _parse_bool(tok)
            if parsed_bool is not None:
                if regenerate_other_clans is None:
                    regenerate_other_clans = parsed_bool
                elif wipe_outsiders is None:
                    wipe_outsiders = parsed_bool
                else:
                    add_output_line_to_log(f"Unexpected boolean token '{tok}'.")
                    add_output_line_to_log(f"Usage: {self.name} {self.usage}")
                    return
                i += 1
                continue

            # unrecognized token
            add_output_line_to_log(f"Unrecognized token '{tok}'.")
            add_output_line_to_log(f"Usage: {self.name} {self.usage}")
            return

        # Apply defaults if booleans weren't provided
        if regenerate_other_clans is None:
            regenerate_other_clans = True
        if wipe_outsiders is None:
            wipe_outsiders = False

        old_biome = game.clan.biome
        old_camp = game.clan.camp_bg
        _set_location(biome, camp_bg)

        if regenerate_other_clans:
            old_count, new_count = _regenerate_other_clans(other_count)
            add_output_line_to_log(f"Regenerated outsider clans. Removed {old_count}, created {new_count}.")

        if wipe_outsiders:
            wiped_count, created_count = _wipe_outsider_cats(outsider_count)
            add_output_line_to_log(f"Wiped {wiped_count} outsider cats and created {created_count} outsiders. Player, guides, and colony roles are retained.")

        game.save_cats()
        game.clan.save_clan()
        from scripts.screens.screens_core.screens_core import rebuild_bgs
        rebuild_bgs()
        game.all_screens[game.current_screen].change_screen("camp screen")

        camp_name = CAMP_NAMES.get(biome, {}).get(camp_bg, "")
        if camp_name:
            add_output_line_to_log(f"Clan location changed from {old_biome} ({old_camp}) to {biome} ({camp_bg} - {camp_name}).")
        else:
            add_output_line_to_log(f"Clan location changed from {old_biome} ({old_camp}) to {biome} ({camp_bg}).")

        if not regenerate_other_clans:
            add_output_line_to_log("Outsider clans were left unchanged.")
        if not wipe_outsiders:
            add_output_line_to_log("Outsider cats were left unchanged.")


class ClansCommand(Command):
    name = "clans"
    description = "Manage outsider clans"
    aliases = ["clan", "otherclans"]

    sub_commands = [
        ListClansCommand(),
        RegenerateClansCommand()
    ]

    def callback(self, args: List[str]):
        # Default behavior: list clans
        if not game.clan:
            add_output_line_to_log("No Clan loaded.")
            return
        
        if not game.clan.all_clans:
            add_output_line_to_log("No outsider clans exist.")
            add_output_line_to_log("To create outsider clans, use: clans regenerate")
            return
        
        add_output_line_to_log(f"Outsider clans ({len(game.clan.all_clans)}):")
        for clan in game.clan.all_clans:
            add_output_line_to_log(f"  {clan.name}Clan - Relations: {clan.relations}, Temperament: {clan.temperament}")
        add_output_line_to_log("To regenerate, use: clans regenerate")
