from typing import List

from scripts.cat.cats import Cat
from scripts.cat.history import History
from scripts.debug_commands.command import Command
from scripts.debug_commands.utils import add_output_line_to_log
from scripts.game_structure.game_essentials import game

class ReturnCatCommand(Command):
    name = "return"
    description = "Return a LOST, EXILED, or DEAD cat to the clan. Usage: return <cat id>"
    aliases = []
    usage = "<cat id>"

    def callback(self, args: List[str]):
        if len(args) == 0:
            add_output_line_to_log("Please specify a cat ID")
            return
        cat_id = args[0]
        cat = Cat.all_cats.get(cat_id)
        if not cat:
            add_output_line_to_log(f"Could not find cat with ID {cat_id}")
            return
        # Consider cat LOST/EXILED/DEAD if exiled, outside, dead, or status is lost/exiled/former colonycat
        # This forcibly and immediately returns the cat, bypassing in-game random chance or moon skip.
        lost_statuses = ["lost", "exiled", "former colonycat"]
        if not (cat.exiled or cat.outside or cat.dead or cat.status.lower() in lost_statuses):
            add_output_line_to_log(f"Cat {cat.name} (ID {cat.ID}) is not LOST, EXILED, or DEAD.")
            return
        # Save previous status if available
        prev_status = getattr(cat, 'old_status', None)
        was_dead = cat.dead
        cat.exiled = False
        cat.outside = False
        cat.dead = False
        Cat.add_to_clan(cat)
        # Restore previous status if available and valid, else default by moons
        valid_roles = [
            "newborn", "kitten", "queen's apprentice", "queen", "elder", "apprentice", "warrior",
            "mediator apprentice", "mediator", "medicine cat apprentice", "medicine cat", "deputy", "leader"
        ]
        if prev_status and prev_status in valid_roles:
            cat.status_change(prev_status)
        else:
            if cat.moons > 119:
                cat.status_change("elder")
            elif cat.moons > 12:
                cat.status_change("warrior")
            elif cat.moons > 6:
                cat.status_change("apprentice")
            else:
                cat.status_change("kitten")
        # Set a positive thought for feedback
        if was_dead:
            cat.thought = "Is surprised to find themselves back in the colony"
        else:
            cat.thought = "Is overjoyed to be home!"
        # Add history event for return from death (only if cat was actually dead)
        if was_dead:
            History.add_return_from_death(cat, f"returned from death.")
        add_output_line_to_log(f"Returned {cat.name} (ID {cat.ID}) to the colony as {cat.status}.")
