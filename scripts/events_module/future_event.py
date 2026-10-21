import logging
from copy import deepcopy
from random import choice, randint

from scripts.game_structure.game_essentials import game

logger = logging.getLogger(__name__)


class FutureEvent:
    def __init__(self, parent_event, event_type, pool, moon_delay, involved_cats, murder_index=None):
        self.parent_event = parent_event
        self.event_type = event_type
        self.pool = deepcopy(pool)
        self.moon_delay = moon_delay
        self.involved_cats = dict(involved_cats)
        # Murder histories are append-only, including repeated attacks in the same moon.
        self.murder_index = murder_index

    def to_dict(self):
        data = {"parent_event": self.parent_event, "event_type": self.event_type,
                "pool": self.pool, "moon_delay": self.moon_delay,
                "involved_cats": self.involved_cats}
        if self.murder_index is not None:
            data["murder_index"] = self.murder_index
        return data


def prep_future_event(event, event_id, possible_cats):
    from scripts.cat.cats import Cat
    from scripts.cat.history import History
    from scripts.events_module.generate_events import GenerateEvents
    from scripts.events_module.short.short_event import ShortEvent

    for info in event.future_event:
        available = [cat for cat in Cat.all_cats.values()
                     if cat.ID in game.clan.clan_cats and not (cat.dead or cat.outside or cat.exiled or cat.shunned)]
        roles = {"m_c": {}, "r_c": {}, **info["involved_cats"]}
        gathered = {}
        # Reserve explicitly assigned cats before choosing any additional participants.
        for role, source in roles.items():
            if isinstance(source, dict):
                continue
            cat = possible_cats.get(source)
            if cat is None:
                break
            gathered[role] = cat.ID
            if cat in available:
                available.remove(cat)
        else:
            for role, constraints in roles.items():
                if not isinstance(constraints, dict):
                    continue
                candidate = ShortEvent(event_id=event_id, weight=1, m_c=deepcopy(constraints),
                                       tags=["skill_trait_required"])
                eligible = [cat for cat in available if GenerateEvents.filter_possible_short_events(
                    Cat, [candidate], cat, None, None, False, 1, [])]
                if not eligible:
                    break
                cat = choice(eligible)
                gathered[role] = cat.ID
                available.remove(cat)
            else:
                murder_index = None
                if isinstance(event, ShortEvent) and "murder" in event.sub_type and "mur_c" in gathered:
                    murderer = Cat.fetch_cat(gathered["m_c"])
                    murders = (History.get_murders(murderer) or {}).get("is_murderer", [])
                    murder_index = next((index for index in range(len(murders) - 1, -1, -1)
                                         if murders[index]["victim"] == gathered["mur_c"]), None)
                game.clan.future_events.append(FutureEvent(
                    event_id, info["event_type"], info["pool"], randint(*info["moon_delay"]), gathered,
                    murder_index=murder_index))
                continue
        logger.info("Could not find participants for the future event of %s", event_id)


def trigger_future_events():
    from scripts.cat.cats import Cat
    from scripts.events_module.short.handle_short_events import HandleShortEvents

    # Follow-ups scheduled by these events must wait until the next moon.
    for event in list(game.clan.future_events):
        event.moon_delay -= 1
        participants = {role: Cat.all_cats.get(cat_id) for role, cat_id in event.involved_cats.items()}
        unavailable = any(cat is None or (role != "mur_c" and
                          (cat.dead or cat.outside or cat.exiled or cat.shunned or cat.ID not in game.clan.clan_cats))
                          for role, cat in participants.items())
        if unavailable or event.moon_delay <= -12:
            game.clan.future_events.remove(event)
            continue
        if event.moon_delay <= 0:
            completed = HandleShortEvents().handle_event(
                event.event_type, participants["m_c"], participants.get("r_c"),
                game.clan.freshkill_pile, sub_type=event.pool.get("sub_type"), future_event=event)
            if completed:
                game.clan.future_events.remove(event)
