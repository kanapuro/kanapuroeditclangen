from typing import List


class ShortEvent:
    """
    A moon event that only affects the moon it was triggered on.  Can involve two cats directly and be restricted by various constraints.
    - full documentation available on GitHub wiki
    """

    def __init__(
            self,
            event_id: str = "",
            location: List[str] = None,
            # LG
            faith_effect: int = 0,
            # ---
            season: List[str] = None,
            sub_type: List[str] = None,
            tags: List[str] = None,
            weight: int = None,
            text: str = "",
            new_accessory: List[str] = None,
            m_c=None,
            r_c=None,
            new_cat: List[list] = None,
            injury: list = None,
            history: list = None,
            relationships: list = None,
            outsider: dict = None,
            other_clan: dict = None,
            supplies: list = None,
            new_gender: List[str] = None,
            exclude_involved: List[str] = None,
            frequency: int = None,
            future_event: list = None
    ):
        if not event_id:
            print("WARNING: moon event has no event_id")
        self.frequency = frequency
        if frequency is not None and frequency not in (1, 2, 3, 4):
            raise ValueError(f"Invalid frequency for {event_id}: {frequency}")
        if frequency is not None and weight is None:
            from scripts.cat.cats import Cat
            from scripts.cat.personality import Personality
            from scripts.cat.skills import SkillPath

            weight = 1
            if location and "any" not in location:
                weight += 1
            if season and "any" not in season:
                weight += 4 - len(season)
            for constraints in (m_c, r_c):
                if not constraints:
                    continue
                for key, count in (("age", len(Cat.ages)), ("status", len(Cat.rank_sort_order)),
                                   ("skill", len(SkillPath)),
                                   ("trait", sum(len(traits) for traits in Personality.trait_ranges.values()))):
                    values = constraints.get(key)
                    if values and "any" not in values:
                        weight += max(0, count - len(values))
                for key in ("relationship_status", "not_skill", "not_trait"):
                    weight += len(constraints.get(key, []))
                if constraints.get("backstory"):
                    weight += 1
        self.future_event = future_event if future_event else []
        self.event_id = event_id
        self.location = location if location else ["any"]
        self.faith_effect = faith_effect if faith_effect else 0
        self.season = season if season else ["any"]
        self.sub_type = sub_type if sub_type else []
        self.tags = tags if tags else []
        self.weight = weight if weight is not None else 0
        self.text = text
        self.new_accessory = new_accessory
        self.m_c = m_c if m_c else {"age": ["any"]}
        if self.m_c:
            if "age" not in self.m_c:
                self.m_c["age"] = ["any"]
            if "status" not in self.m_c:
                self.m_c["status"] = ["any"]
            if "relationship_status" not in self.m_c:
                self.m_c["relationship_status"] = []
            if "skill" not in self.m_c:
                self.m_c["skill"] = []
            if "not_skill" not in self.m_c:
                self.m_c["not_skill"] = []
            if "trait" not in self.m_c:
                self.m_c["trait"] = []
            if "not_trait" not in self.m_c:
                self.m_c["not_trait"] = []
            if "age" not in self.m_c:
                self.m_c["age"] = []
            if "backstory" not in self.m_c:
                self.m_c["backstory"] = []
            if "dies" not in self.m_c:
                self.m_c["dies"] = False
            if "gender" not in self.m_c:
                self.m_c["gender"] = []

        self.r_c = r_c if r_c else {}
        if self.r_c:
            if "age" not in self.r_c:
                self.r_c["age"] = ["any"]
            if "status" not in self.r_c:
                self.r_c["status"] = ["any"]
            if "relationship_status" not in self.r_c:
                self.r_c["relationship_status"] = []
            if "skill" not in self.r_c:
                self.r_c["skill"] = []
            if "not_skill" not in self.r_c:
                self.r_c["not_skill"] = []
            if "trait" not in self.r_c:
                self.r_c["trait"] = []
            if "not_trait" not in self.r_c:
                self.r_c["not_trait"] = []
            if "age" not in self.r_c:
                self.r_c["age"] = []
            if "backstory" not in self.r_c:
                self.r_c["backstory"] = []
            if "dies" not in self.r_c:
                self.r_c["dies"] = False

        self.new_cat = new_cat if new_cat else []
        self.injury = injury if injury else []
        self.history = history if history else []
        self.relationships = relationships if relationships else []
        self.outsider = outsider if outsider else {}
        if self.outsider:
            if "current_rep" not in self.outsider:
                self.outsider["current_rep"] = []
            if "changed" not in self.outsider:
                self.outsider["changed"] = 0
        self.other_clan = other_clan if other_clan else {}
        if self.other_clan:
            if "current_rep" not in self.other_clan:
                self.other_clan["current_rep"] = []
            if "changed" not in self.other_clan:
                self.other_clan["changed"] = 0
        self.supplies = supplies if supplies else []
        self.new_gender = new_gender
        self.exclude_involved = list(exclude_involved) if exclude_involved else []
