import json
from collections.abc import MutableMapping
from random import choice, choices, randint, random

from scripts.cat.skills import SkillPath
from scripts.game_structure.game_essentials import game

with open("resources/dicts/herb_info.json", encoding="utf-8") as read_file:
    HERB_INFO = json.load(read_file)

with open("resources/dicts/herb_messages.json", encoding="utf-8") as read_file:
    HERB_MESSAGES = json.load(read_file)


class HerbSupply(MutableMapping):
    """Integer stock totals backed by newest-first monthly batches."""

    def __init__(self, data=None):
        data = data or {}
        if "storage" in data or "collected" in data:
            self.storage = {herb: list(amounts) for herb, amounts in data.get("storage", {}).items()}
            self.collected = dict(data.get("collected", {}))
        else:
            # Old saves have no age information; retain their entire stock as fresh herbs.
            self.storage = {}
            self.collected = dict(data)

    def __getitem__(self, herb):
        if herb not in self.storage and herb not in self.collected:
            raise KeyError(herb)
        return sum(self.storage.get(herb, [])) + self.collected.get(herb, 0)

    def __setitem__(self, herb, amount):
        amount = max(0, int(amount))
        difference = amount - self.get(herb, 0)
        if difference >= 0:
            self.collected[herb] = self.collected.get(herb, 0) + difference
        else:
            remaining = -difference
            batches = self.storage.get(herb, [])
            for index in range(len(batches) - 1, -1, -1):
                used = min(batches[index], remaining)
                batches[index] -= used
                remaining -= used
                if not remaining:
                    break
            self.collected[herb] = self.collected.get(herb, 0) - remaining

    def __delitem__(self, herb):
        if herb not in self:
            raise KeyError(herb)
        self.storage.pop(herb, None)
        self.collected.pop(herb, None)

    def __iter__(self):
        return iter(dict.fromkeys(list(self.storage) + list(self.collected)))

    def __len__(self):
        return len(set(self.storage) | set(self.collected))

    def copy(self):
        return dict(self)

    def to_dict(self):
        return {"storage": {herb: list(amounts) for herb, amounts in self.storage.items()},
                "collected": dict(self.collected)}

    def get_overall_rating(self, clan):
        from scripts.cat.cats import Cat

        if not sum(self.values()):
            return "empty"
        amounts = [self.get(herb, 0) for herb in set(HERB_INFO) | set(self)]
        average = (min(amounts) + max(amounts)) / 2
        clan_size = sum(1 for cat_id in clan.clan_cats
                        if (cat := Cat.all_cats.get(cat_id)) and not (cat.dead or cat.outside or cat.exiled))
        config = game.get_config_value("clan_resources", "herbs")
        full = int(clan_size * config["required_herbs_per_cat"])
        if average <= round(full / config["adequate"]):
            return "low"
        if average <= full:
            return "adequate"
        if average <= full * config["excess"]:
            return "full"
        return "excess"

    def get_status_message(self, clan, med=None):
        from scripts.cat.cats import Cat
        from scripts.utility import event_text_adjust

        messages = HERB_MESSAGES[self.get_overall_rating(clan)]
        available = []
        for message in messages:
            if med is None and "m_c" in message:
                continue
            for token, cat_id in (("lead_name", clan.leader), ("dep_name", clan.deputy)):
                if token not in message:
                    continue
                cat = Cat.fetch_cat(cat_id)
                if not cat or cat.ID not in clan.clan_cats or cat.dead or cat.outside or cat.exiled:
                    break
            else:
                available.append(message)
        return event_text_adjust(Cat, choice(available), main_cat=med, clan=clan)

    def start_storage(self, clan_size):
        config = game.get_config_value("clan_resources", "herbs")
        full = int(clan_size * config["required_herbs_per_cat"])
        adequate = round(full / config["adequate"])
        for herb in HERB_INFO:
            if randint(1, 4) == 1:
                amount = randint(adequate, full)
                if amount:
                    self[herb] = self.get(herb, 0) + amount

    def begin_moon(self, med_cats):
        for herb in list(self):
            amount = self.collected.get(herb, 0)
            batches = self.storage.get(herb, [])
            if herb not in HERB_INFO:
                # Preserve merged/modded herbs until they have their own expiration definition.
                self.storage[herb] = [self[herb]]
                continue
            stored_better = False
            if amount and batches:
                for med in med_cats:
                    skills = [skill for skill in (med.skills.primary, med.skills.secondary)
                              if skill and skill.path == SkillPath.CAMP]
                    if skills and randint(1, 35 - max(skill.points for skill in skills)) == 1:
                        batches[0] += amount
                        stored_better = True
                        game.herb_events_list.append(f"{med.name} stored the {herb.replace('_', ' ')} carefully, delaying its expiration.")
                        break
            if not stored_better:
                batches.insert(0, amount)
            self.storage[herb] = batches
        self.collected.clear()

    def expire(self):
        expired = {}
        for herb in list(self.storage):
            if herb not in HERB_INFO:
                continue
            batches = self.storage[herb]
            expiration = HERB_INFO[herb]["expiration"]
            count = sum(batches[expiration:])
            if count:
                expired[herb] = count
            del batches[expiration:]
            while batches and batches[-1] == 0:
                batches.pop()
            if not batches:
                self.storage.pop(herb)
            if not self.get(herb, 0):
                self.collected.pop(herb, None)
        if expired:
            display = ", ".join(f"{count} {herb.replace('_', ' ')}" for herb, count in expired.items())
            game.herb_events_list.append(f"Expired herbs were discarded: {display}.")
        return expired

    def gather(self, med, clan, *, many_herbs=False, quantity_bonus=1, max_types=None):
        from scripts.cat.cats import Cat, ILLNESSES, INJURIES, PERMANENT

        config = game.get_config_value("clan_resources", "herbs")
        needed = set()
        clan_size = 0
        for cat_id in clan.clan_cats:
            cat = Cat.all_cats.get(cat_id)
            if not cat or cat.dead or cat.outside or cat.exiled:
                continue
            clan_size += 1
            for conditions, source in ((cat.illnesses, ILLNESSES), (cat.injuries, INJURIES),
                                       (cat.permanent_condition, PERMANENT)):
                for name, condition in conditions.items():
                    if condition.get("born_with") and condition.get("moons_until") != -2:
                        continue
                    if name not in source:
                        continue
                    herbs = source[name]["herbs"]
                    if isinstance(herbs, dict):
                        needed.update(herb for group in herbs.values() for herb in group)
                    else:
                        needed.update(herbs)
        adequate = round(clan_size * config["required_herbs_per_cat"] / config["adequate"])
        herb_list = sorted(HERB_INFO, key=lambda herb: (not (herb in needed and self.get(herb, 0) <= adequate),
                                                       self.get(herb, 0)))
        type_modifier = quantity_modifier = 1
        for skill, prefix in ((med.skills.primary, "primary"), (med.skills.secondary, "secondary")):
            if skill and skill.path == SkillPath.SENSE:
                type_modifier = max(type_modifier, config[prefix + "_sense"])
            elif skill and skill.path == SkillPath.CLEVER:
                quantity_modifier = max(quantity_modifier, config[prefix + "_clever"])
        weights = config[clan.biome.casefold()][clan.current_season.casefold()]
        types = choices([1, 2, 3], weights=weights)[0] + type_modifier
        if many_herbs:
            types *= config["general_amount_bonus"]
        if max_types is not None:
            limit = int(max_types)
            if max_types > limit and random() < max_types - limit:
                limit += 1
            types = min(types, limit)
        found = {}
        for herb in herb_list:
            if types <= 0:
                break
            rarity = HERB_INFO[herb]["rarity"].get(clan.biome.casefold(), {}).get(clan.current_season.casefold(), 0)
            if not rarity or randint(1, rarity) != 1:
                continue
            modifier = quantity_modifier * quantity_bonus
            if rarity in (5, 6):
                modifier /= 2
            elif rarity in (1, 2):
                modifier += 1
            amount = max(1, int(choices([2, 3, 4], weights=weights)[0] * modifier))
            self[herb] = self.get(herb, 0) + amount
            found[herb] = amount
            types -= 1
        return found
