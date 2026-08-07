"""
Module that handles the name generation for all cats.
"""

import contextlib
import os
import random

import ujson

from scripts.game_structure.game_essentials import game
from scripts.housekeeping.datadir import get_save_dir


class Name:
    """
    Stores & handles name generation.
    """

    # Load traditional warrior names
    if os.path.exists("resources/dicts/names/names.json"):
        with open("resources/dicts/names/names.json", encoding="utf-8") as read_file:
            names_dict = ujson.loads(read_file.read())
    
    # Load single names from FelGen
    single_names_list = []
    if os.path.exists("resources/dicts/names/single_names.txt"):
        with open("resources/dicts/names/single_names.txt", "r", encoding="utf-8") as read_file:
            single_names_list = [line.strip() for line in read_file if line.strip()]
    
    # Load syllables for syllable-based names
    syllables_list = []
    if os.path.exists("resources/dicts/names/syllables.txt"):
        with open("resources/dicts/names/syllables.txt", "r", encoding="utf-8") as read_file:
            syllables_list = [line.strip() for line in read_file if line.strip()]

    if os.path.exists("resources/dicts/names/names.json"):
        with open("resources/dicts/names/names.json", encoding="utf-8") as read_file:
            names_dict = ujson.loads(read_file.read())

        if os.path.exists(get_save_dir() + "/prefixlist.txt"):
            with open(get_save_dir() + "/prefixlist.txt", "r", encoding="utf-8") as read_file:
                name_list = read_file.read()
                if_names = len(name_list)
            if if_names > 0:
                new_names = name_list.split("\n")
                for new_name in new_names:
                    if new_name != "":
                        if new_name.startswith("-"):
                            while new_name[1:] in names_dict["normal_prefixes"]:
                                names_dict["normal_prefixes"].remove(new_name[1:])
                        else:
                            names_dict["normal_prefixes"].append(new_name)
    def __init__(
        self,
        prefix=None,
        suffix=None,
        biome=None,
        specsuffix_hidden=False,
        shunned=0,
        load_existing_name=False,
        cat=None,
    ):
        self.prefix = prefix
        self._suffix = None
        self.specsuffix_hidden = specsuffix_hidden
        self.shunned = shunned
        self.cat = cat
        self.name_type = None  # Track what type of name this is
        self._initializing = True
        self._explicit_suffix_override = False

        if suffix is not None:
            self.suffix = suffix

        # Determine name type for new names
        if not load_existing_name and prefix is None and suffix is None:
            # Outsiders use single names; clan cats follow settings/defaults
            if self.cat and (
                getattr(self.cat, 'outside', False)
                or getattr(self.cat, 'status', None) in ["rogue", "loner", "kittypet"]
            ):
                self.name_type = "single"
            else:
                self.name_type = self._choose_name_type()

        # If loading existing name or has prefix/suffix, assume warrior-style
        if load_existing_name or prefix is not None or suffix is not None:
            if prefix is not None and suffix is not None and suffix and " " in suffix:
                self.name_type = "ancient"
            elif prefix is not None and suffix is not None:
                self.name_type = "warrior"

        # Ancient names should default to hiding special suffixes unless explicitly requested
        if self.name_type == "ancient" and not load_existing_name:
            self.specsuffix_hidden = True

        try:
            color = cat.pelt.colour
            eyes = cat.pelt.eye_colour
            pelt = cat.pelt.name
            tortiepattern = cat.pelt.tortiepattern
        except AttributeError:
            color = None
            eyes = None
            pelt = None
            tortiepattern = None

        # Generate name based on type
        if self.name_type == "single":
            self._generate_single_name()
        elif self.name_type == "syllable":
            self._generate_syllable_name()
        elif self.name_type == "ancient":
            self._generate_ancient_name(eyes, color, pelt, biome, tortiepattern, prefix=prefix, suffix=suffix)
        else:  # Default to warrior-style
            self.name_type = "warrior"
            self._generate_warrior_name(prefix, suffix, eyes, color, pelt, biome, tortiepattern, load_existing_name)

        self._initializing = False
        if self.suffix is not None:
            self._sync_name_style_for_suffix()

    def _choose_name_type(self):
        """Choose an appropriate name type based on settings and context."""
        # Default to warrior names when no clan/settings exist (e.g., new clan creation)
        if not game.clan or not hasattr(game.clan, 'clan_settings') or not game.clan.clan_settings:
            return "warrior"

        settings = game.clan.clan_settings
        
        # If settings are empty or None, default to warrior
        if not settings:
            return "warrior"
        
        # Build list of enabled naming types from current settings
        enabled_types = []

        if settings.get("warrior_names", True):
            enabled_types.append("warrior")
        if settings.get("ancient_names", False):
            enabled_types.append("ancient")
        if settings.get("single_names", False):
            enabled_types.append("single")
        if settings.get("syllable_names", False):
            enabled_types.append("syllable")

        # Ensure at least one type is enabled (fallback to warrior)
        if not enabled_types:
            return "warrior"

        # Kits: optionally inherit naming style from parents, and keep consistent per litter
        try:
            if self.cat and getattr(self.cat, "status", None) in ("newborn", "kitten") and settings.get("kit_inherit_naming", True):
                # Use Cat.parent1/parent2 directly for a stable litter key
                p1 = getattr(self.cat, "parent1", None)
                p2 = getattr(self.cat, "parent2", None)
                parent_ids = [pid for pid in (p1, p2) if pid]

                litter_key = None
                if parent_ids:
                    # Sort to make the key order-independent
                    if len(parent_ids) == 1:
                        pid1 = str(parent_ids[0])
                        pid2 = ""
                    else:
                        pid1, pid2 = sorted([str(parent_ids[0]), str(parent_ids[1])])
                    litter_key = (pid1, pid2)

                inherit_type = None
                if litter_key is not None:
                    if not hasattr(Name, "_litter_style_cache"):
                        Name._litter_style_cache = {}
                    inherit_type = Name._litter_style_cache.get(litter_key)

                def detect_type(name_str: str) -> str:
                    if " " in name_str:
                        return "ancient"
                    for suf in self.names_dict.get("normal_suffixes", []):
                        if name_str.lower().endswith(suf.lower()):
                            return "warrior"
                    return "single"

                if inherit_type is None and parent_ids:
                    parent_types = []
                    for pid in parent_ids:
                        parent_cat = None
                        try:
                            parent_cat = self.cat.__class__.all_cats.get(pid)
                        except Exception:
                            parent_cat = None
                        if parent_cat and getattr(parent_cat, "name", None):
                            parent_types.append(detect_type(str(parent_cat.name)))

                    if parent_types:
                        # Choose randomly from parent types instead of prioritizing warrior
                        inherit_type = random.choice(parent_types)

                    if litter_key is not None and inherit_type is not None:
                        Name._litter_style_cache[litter_key] = inherit_type

                if inherit_type:
                    # If we inherited a type, always use it (add to enabled_types if needed)
                    if inherit_type not in enabled_types:
                        # Temporarily add the inherited type so kits can use parent's naming style
                        # even if it's not currently enabled in settings
                        pass  # We'll return it anyway
                    return inherit_type
        except Exception:
            pass

        return random.choice(enabled_types)

    
    
    def _generate_single_name(self):
        """Generate a single-word name from the curated list."""
        if self.single_names_list:
            self.prefix = random.choice(self.single_names_list)
            self.suffix = ""
            # Single-name cats should NOT show special suffixes by default
            self.specsuffix_hidden = True
        else:
            # Fallback to warrior name if list not loaded
            self.name_type = "warrior"
            # Warrior-style names should allow special suffixes by default
            self.specsuffix_hidden = False
            self._generate_warrior_name(None, None, None, None, None, None, None, False)
    
    def _generate_syllable_name(self):
        """Generate a 1-3 syllable name."""
        if self.syllables_list:
            num_syllables = random.randint(1, 3)
            syllables = [random.choice(self.syllables_list) for _ in range(num_syllables)]
            # Keep first syllable capitalized, lowercase the rest
            combined = syllables[0]
            for syllable in syllables[1:]:
                combined += syllable.lower()
            self.prefix = combined
            self.suffix = ""
            # Syllable-name cats should NOT show special suffixes by default
            self.specsuffix_hidden = True
        else:
            # Fallback to warrior name if list not loaded
            self.name_type = "warrior"
            # Warrior-style names should allow special suffixes by default
            self.specsuffix_hidden = False
            self._generate_warrior_name(None, None, None, None, None, None, None, False)
    
    def _generate_ancient_name(self, eyes, color, pelt, biome, tortiepattern, prefix=None, suffix=None):
        """Generate an ancient-style name (capitalized prefix + space + capitalized suffix)."""
        # Use warrior name generation logic but format as ancient; allow prefix/suffix overrides
        self._generate_warrior_name(prefix, suffix, eyes, color, pelt, biome, tortiepattern, False)
        # Convert to ancient format: store capitalized suffix WITH a leading space for persistence
        if self.suffix:
            base = self.suffix.strip()
            if base:
                self.suffix = " " + base[0].upper() + base[1:]
            # Only force specsuffix_hidden if we generated the name (not user input)
            if suffix is None:
                self.specsuffix_hidden = True
    
    def _generate_warrior_name(self, prefix, suffix, eyes, color, pelt, biome, tortiepattern, load_existing_name):
        """Generate a traditional warrior-style name."""
        name_fixpref = False
        # Set prefix
        if prefix is None:
            self.give_prefix(eyes, color, biome)
            # needed for random dice when we're changing the Prefix
            name_fixpref = True

        # Set suffix
        if self.suffix is None:
            self.give_suffix(pelt, biome, tortiepattern)
            if name_fixpref and self.prefix is None:
                # needed for random dice when we're changing the Prefix
                name_fixpref = False

        if self.suffix and not load_existing_name:
            # Prevent triple letter names from joining prefix and suffix from occurring (ex. Beeeye)
            possible_three_letter = (
                self.prefix[-2:] + self.suffix[0],
                self.prefix[-1] + self.suffix[:2],
            )
            triple_letter = all(
                i == possible_three_letter[0][0] for i in possible_three_letter[0]
            ) or all(
                i == possible_three_letter[1][0]
                for i in possible_three_letter[1]
            # Prevent double animal names (ex. Spiderfalcon)
            )
            double_animal = (
                self.prefix in self.names_dict["animal_prefixes"]
                and self.suffix in self.names_dict["animal_suffixes"]
            )
            # Prevent the inappropriate names
            nono_name = self.prefix + self.suffix
            # Prevent double names (ex. Iceice)
            # Prevent suffixes containing the prefix (ex. Butterflyfly)

            i = 0
            while (
                nono_name.lower() in self.names_dict["inappropriate_names"]
                or triple_letter
                or double_animal
                or (
                    self.prefix.lower() in self.suffix.lower()
                    and str(self.prefix) != ""
                )
                or (
                    self.suffix.lower() in self.prefix.lower()
                    and str(self.suffix) != ""
                )
            ):

                # check if random die was for prefix
                if name_fixpref:
                    self.give_prefix(eyes, color, biome)
                else:
                    self.give_suffix(pelt, biome, tortiepattern)

                nono_name = self.prefix + self.suffix
                possible_three_letter = (
                    self.prefix[-2:] + self.suffix[0],
                    self.prefix[-1] + self.suffix[:2],
                )
                if any(
                    i != possible_three_letter[0][0] for i in possible_three_letter[0]
                ) and any(
                    i != possible_three_letter[1][0] for i in possible_three_letter[1]
                ):
                    triple_letter = False
                if (
                    self.prefix not in self.names_dict["animal_prefixes"]
                    or self.suffix not in self.names_dict["animal_suffixes"]
                ):
                    double_animal = False
                i += 1

    # Generate possible prefix
    def give_prefix(self, eyes, colour, biome):
        """Generate possible prefix."""
        # decided in game config: cat_name_controls
        if game.config["cat_name_controls"]["always_name_after_appearance"]:
            named_after_appearance = True
        else:
            named_after_appearance = not random.getrandbits(
                2
            )  # Chance for True is '1/4'

        named_after_biome_ = not random.getrandbits(3)  # chance for True is 1/8

        # Add possible prefix categories to list.
        possible_prefix_categories = []
        if (
            eyes in self.names_dict["eye_prefixes"]
            and game.config["cat_name_controls"]["allow_eye_names"]
        ):
            possible_prefix_categories.append(self.names_dict["eye_prefixes"][eyes])
        if colour in self.names_dict["colour_prefixes"]:
            possible_prefix_categories.append(
                self.names_dict["colour_prefixes"][colour]
            )
        if biome is not None and biome in self.names_dict["biome_prefixes"]:
            possible_prefix_categories.append(self.names_dict["biome_prefixes"][biome])

        # Choose appearance-based prefix if possible and named_after_appearance because True.
        if (
            named_after_appearance
            and possible_prefix_categories
            and not named_after_biome_
            or named_after_biome_
            and possible_prefix_categories
        ):
            prefix_category = random.choice(possible_prefix_categories)
            self.prefix = random.choice(prefix_category).strip()
        else:
            self.prefix = random.choice(self.names_dict["normal_prefixes"]).strip()

        # This thing prevents any prefix duplications from happening.
        # Try statement stops this form running when initializing.
        with contextlib.suppress(NameError):
            if self.prefix in names.prefix_history:
                # do this recursively until a name that isn't on the history list.
                self.give_prefix(eyes, colour, biome)
                # prevent infinite recursion
                if len(names.prefix_history) > 0:
                    names.prefix_history.pop(0)
            else:
                names.prefix_history.append(self.prefix)
            # Set the maximin length to 8 just to be sure
            if len(names.prefix_history) > 8:
                # removing at zero so the oldest gets removed
                names.prefix_history.pop(0)

    # Generate possible suffix
    def give_suffix(self, pelt, biome, tortiepattern):
        """Generate possible suffix."""
        if pelt is None or pelt == "SingleColour":
            self.suffix = random.choice(self.names_dict["normal_suffixes"]).strip()
        else:
            named_after_pelt = not random.getrandbits(2)  # Chance for True is '1/8'.
            named_after_biome = not random.getrandbits(3)  # 1/8
            # Pelt name only gets used if there's an associated suffix.
            if named_after_pelt:
                if (
                    pelt in ["Tortie", "Calico"]
                    and tortiepattern in self.names_dict["tortie_pelt_suffixes"]
                ):
                    self.suffix = random.choice(
                        self.names_dict["tortie_pelt_suffixes"][tortiepattern]
                    ).strip()
                elif pelt in self.names_dict["pelt_suffixes"]:
                    self.suffix = random.choice(self.names_dict["pelt_suffixes"][pelt]).strip()
                else:
                    self.suffix = random.choice(self.names_dict["normal_suffixes"]).strip()
            elif named_after_biome:
                if biome in self.names_dict["biome_suffixes"]:
                    self.suffix = random.choice(
                        self.names_dict["biome_suffixes"][biome]
                    ).strip()
                else:
                    self.suffix = random.choice(self.names_dict["normal_suffixes"]).strip()
            else:
                self.suffix = random.choice(self.names_dict["normal_suffixes"]).strip()

    @property
    def suffix(self):
        return self._suffix

    @suffix.setter
    def suffix(self, value):
        self._suffix = value
        if getattr(self, "_initializing", False):
            return
        self._sync_name_style_for_suffix()

    def _sync_name_style_for_suffix(self):
        """Align the name style with the stored suffix when a suffix is introduced."""
        if self.suffix is None:
            return

        stripped_suffix = str(self.suffix).strip()
        if not stripped_suffix:
            return

        if self.name_type in ("single", "syllable"):
            self.name_type = "warrior"
            self.specsuffix_hidden = False
            self._explicit_suffix_override = True

        if self.name_type == "ancient" and " " in stripped_suffix:
            self.specsuffix_hidden = False

    def __repr__(self):
        if getattr(self, "_explicit_suffix_override", False) and self.suffix:
            return self.prefix.strip() + str(self.suffix).strip()

        # Apply special suffixes first whenever they are not hidden,
        # regardless of name type (including single/syllable/ancient).
        # This ensures kits/apprentices/leaders render as expected.
        if self.cat and not self.specsuffix_hidden:
            # Handle outsiders: infer a temporary status based on moons
            if self.cat.status not in ["rogue", "loner", "kittypet"] and self.cat.outside:
                adjusted_status: str = ""
                if self.cat.moons >= 15:
                    adjusted_status = "warrior"
                elif self.cat.moons >= 6:
                    adjusted_status = "apprentice"
                if self.cat.moons == 0:
                    adjusted_status = "newborn"
                elif self.cat.moons < 6:
                    adjusted_status = "kitten"
                elif self.cat.moons < 12:
                    adjusted_status = "apprentice"
                else:
                    adjusted_status = "warrior"

                if adjusted_status != "warrior" and adjusted_status in self.names_dict.get("special_suffixes", {}):
                    return self.prefix.strip() + self.names_dict["special_suffixes"][adjusted_status].strip()

            # Normal clan cat statuses
            if self.cat.status in self.names_dict.get("special_suffixes", {}):
                return self.prefix.strip() + self.names_dict["special_suffixes"][self.cat.status].strip()

        # For single and syllable names, return just the trimmed prefix
        if self.name_type in ["single", "syllable"]:
            self._sync_name_style_for_suffix()
            if self.name_type in ["single", "syllable"]:
                return self.prefix.strip()

        # Ancient names: use stored custom suffix when special suffix is hidden
        if self.name_type == "ancient":
            suffix = self.suffix
            if suffix:
                return self.prefix.strip() + suffix
            return self.prefix.strip()

        # April Fools easter egg
        if game.config["fun"]["april_fools"]:
            return f"{self.prefix.strip()}egg"

        # Base formatting - keep user input as-is for warrior/other
        return self.prefix.strip() + self.suffix


names = Name()
names.prefix_history = []
