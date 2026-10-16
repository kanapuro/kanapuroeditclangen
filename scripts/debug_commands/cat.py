from typing import List

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.utility import create_new_cat
from scripts.debug_commands.command import Command
from scripts.debug_commands.utils import add_output_line_to_log
from scripts.game_structure.game_essentials import game


class AddCatCommand(Command):
    name = "add"
    description = "Add a cat"
    aliases = ["a"]

    def callback(self, args: List[str]):
        if game.clan is None:
            add_output_line_to_log("Please load a Clan first")
            return
        cat = create_new_cat(Cat)[0]
        cat.create_inheritance_new_cat()
        add_output_line_to_log(f"Added {cat.name} with ID {cat.ID}")


class CreateCatCommand(Command):
    name = "create"
    description = "Create a cat in the character customizer (default: 1 moon)"
    usage = "[moons]"

    def callback(self, args: List[str]):
        if game.clan is None:
            add_output_line_to_log("Please load a Clan first")
            return
        if len(args) > 1:
            add_output_line_to_log("Usage: cats create [moons]")
            return
        try:
            moons = int(args[0]) if args else 1
        except ValueError:
            add_output_line_to_log("Please specify a whole number of moons")
            return
        if moons < 0:
            add_output_line_to_log("A cat's age cannot be negative")
            return
        if (game.current_screen in ("make clan screen", "customize cat screen")
                or game.switches.get("create_cat") or game.switches.get("window_open")):
            add_output_line_to_log("Please finish the current editor or window first")
            return
        if moons >= 120:
            status = "elder"
        elif moons >= 12:
            status = "warrior"
        elif moons >= 6:
            status = "apprentice"
        elif moons == 0:
            status = "newborn"
        else:
            status = "kitten"
        cat = Cat(moons=moons, status=status, register=False)
        if cat.history is None:
            cat.history = History()
        game.switches["create_cat"] = {
            "cat": cat,
            "return_screen": game.current_screen,
            "previous_cat": game.switches["cat"],
        }
        game.all_screens[game.current_screen].change_screen("customize cat screen")
        from scripts.debug_console import debug_mode
        if debug_mode.debug_menu.visible:
            debug_mode.toggle_debug_mode()


class RemoveCatCommand(Command):
    name = "remove"
    description = "Remove a cat"
    aliases = ["r"]
    usage = "<cat name|id>"

    def callback(self, args: List[str]):
        if len(args) == 0:
            add_output_line_to_log("Please specify a cat name or ID")
            return
        for cat in Cat.all_cats_list:
            if str(cat.name).lower() == args[0].lower() or cat.ID == args[0]:
                game.clan.remove_cat(cat.ID)
                add_output_line_to_log(f"Removed {cat.name} with ID {cat.ID}")
                return
        add_output_line_to_log(f"Could not find cat with name or ID {args[0]}")


class ListCatsCommand(Command):
    name = "list"
    description = "List all cats"
    aliases = ["l"]

    def callback(self, args: List[str]):
        for cat in Cat.all_cats_list:
            add_output_line_to_log(f"{cat.ID} - {cat.name}, {cat.status}, {cat.moons} moons old")


class AgeCatsCommand(Command):
    name = "age"
    description = "Age a cat"
    usage = "<cat name|id> [number]"

    def callback(self, args: List[str]):
        if len(args) == 0:
            add_output_line_to_log("Please specify a cat name or ID")
            return
        for cat in Cat.all_cats_list:
            if str(cat.name).lower() == args[0].lower() or cat.ID == args[0]:
                if len(args) == 1:
                    add_output_line_to_log(f"{cat.name} is {cat.moons} moons old")
                    return
                try:
                    age = int(args[1])
                except ValueError:
                    add_output_line_to_log("Please specify a whole number of moons")
                    return
                if args[1].startswith(("+", "-")):
                    age += cat.moons
                if age < 0:
                    add_output_line_to_log("A cat's age cannot be negative")
                    return
                cat.moons = age
                add_output_line_to_log(f"{cat.name} is now {cat.moons} moons old")
                return
        add_output_line_to_log(f"Could not find cat with name or ID {args[0]}")


class CatsCommand(Command):
    name = "cats"
    description = "Manage Cats"
    aliases = ["cat"]

    sub_commands = [
        AddCatCommand(),
        CreateCatCommand(),
        RemoveCatCommand(),
        ListCatsCommand(),
        AgeCatsCommand()
    ]

    def callback(self, args: List[str]):
        add_output_line_to_log("Please specify a subcommand")
