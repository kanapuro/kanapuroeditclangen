from typing import List
from random import choice, randint

from scripts.cat.names import names
from scripts.clan import OtherClan
from scripts.debug_commands.command import Command
from scripts.debug_commands.utils import add_output_line_to_log
from scripts.game_structure.game_essentials import game


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
        
        # If camp type specified, validate and set it
        if len(args) >= 2:
            camp_input = args[1].lower()
            if not camp_input.startswith("camp"):
                camp_input = f"camp{camp_input}"
            
            if camp_input in CAMP_AVAILABILITY.get(biome, []):
                game.clan.camp_bg = camp_input
                add_output_line_to_log(f"Clan location changed from {old_biome} ({old_camp}) to {biome} ({camp_input}).")
            else:
                game.clan.camp_bg = "camp1"  # Default to camp1
                add_output_line_to_log(f"Camp '{camp_input}' not available in {biome}. Defaulting to camp1.")
                add_output_line_to_log(f"Available camps for {biome}: {', '.join(CAMP_AVAILABILITY[biome])}")
        else:
            # Keep existing camp if compatible, otherwise default to camp1
            if old_camp not in CAMP_AVAILABILITY.get(biome, []):
                game.clan.camp_bg = "camp1"
                add_output_line_to_log(f"Clan location changed from {old_biome} to {biome}. Camp reset to camp1.")
            else:
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
        
        old_count = len(game.clan.all_clans)
        game.clan.all_clans.clear()
        
        number_other_clans = randint(3, 5)
        for _ in range(number_other_clans):
            other_clan_names = [str(i.name) for i in game.clan.all_clans] + [game.clan.name]
            # Generate clan name using all prefixes + clan suffix
            all_prefixes = names.names_dict["normal_prefixes"] + names.names_dict["clan_prefixes"]
            clan_prefix = choice(all_prefixes)
            clan_suffix = choice(names.names_dict.get("clan_suffixes", ["Clan"]))
            other_clan_name = clan_prefix + clan_suffix
            while other_clan_name in other_clan_names:
                clan_prefix = choice(all_prefixes)
                clan_suffix = choice(names.names_dict.get("clan_suffixes", ["Clan"]))
                other_clan_name = clan_prefix + clan_suffix
            other_clan = OtherClan(name=other_clan_name)
            game.clan.all_clans.append(other_clan)
        
        add_output_line_to_log(f"Regenerated outsider clans. Removed {old_count}, created {len(game.clan.all_clans)}.")
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
