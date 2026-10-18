from copy import deepcopy
from random import choice
import random

import pygame
import pygame_gui
import ujson

from scripts.cat.cats import Cat, PERMANENT, BACKSTORIES
from scripts.cat.personality import Personality
from scripts.cat.pelts import Pelt
from scripts.cat.skills import SkillPath
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.ui_elements import UIImageButton, UISpriteButton, UISurfaceImageButton
from scripts.screens.CatAppearanceEditor import CatAppearanceEditor, CustomizerList, update_checkbox
from scripts.ui.generate_button import ButtonStyles, get_button_dict
from scripts.ui.get_arrow import get_arrow
from scripts.ui.icon import Icon
from scripts.utility import ui_scale, generate_sprite, get_text_box_theme, process_text


class CatCustomizer:
    #images for the customizing screen
    sprite_preview_bg = pygame.transform.scale(pygame.image.load(
        'resources/images/sprite_preview.png').convert_alpha(), (1600, 1400))

    sprite_preview_bg_dark = pygame.transform.scale(pygame.image.load(
        'resources/images/sprite_preview_dark.png').convert_alpha(), (1600, 1400))

    poses_bg = pygame.transform.scale(pygame.image.load(
        'resources/images/poses_bg.png').convert_alpha(), (1600, 1400))

    poses_bg_dark = pygame.transform.scale(pygame.image.load(
        'resources/images/poses_bg_dark.png').convert_alpha(), (1600, 1400))

    choice_bg = pygame.transform.scale(pygame.image.load(
        'resources/images/custom_choice_bg.png').convert_alpha(), (1600, 1400))

    choice_bg_dark = pygame.transform.scale(pygame.image.load(
        'resources/images/custom_choice_bg_dark.png').convert_alpha(), (1600, 1400))


    with open(f"resources/dicts/acc_display.json", "r", encoding="utf-8") as read_file:
        ACC_DISPLAY = ujson.loads(read_file.read())



    customizer_lock_groups = {
        "kitten_pose": ("kitten_sprite",),
        "adolescent_pose": ("adolescent_pose",),
        "adult_pose": ("adult_pose", "length"),
        "elder_pose": ("elder_pose",),
        "length": ("length",),
        "reverse": ("reverse",),
        "pelt_pattern": ("pname", "tortiebase", "tortiecolour", "pattern", "tortiepattern", "tortie_enabled"),
        "pelt_colour": ("colour", "tint"),
        "white_patches": ("white_patches", "white_patches_tint"),
        "points": ("points",),
        "vitiligo": ("vitiligo",),
        "eye_colour": ("eye_colour",),
        "heterochromia": ("eye_colour2",),
        "skin": ("skin",),
        "condition": ("permanent_conditions", "paralyzed", "scars"),
        "accessory": ("accessories", "inventory"),
        "trait": ("personality",),
        "skill": ("skill",),
        "faith": ("faith",),
        "sex": ("sex",),
        "secondary_skill": ("secondary_skill",),
        "fur_texture": ("fur_texture",), "build": ("build",),
        "height": ("height",), "backstory": ("backstory",),
    }

    kit_traits = list(Personality.trait_ranges["kit_traits"])
    sex_specific_conditions = {"excess testosterone", "aneuploidy", "testosterone deficiency", "chimerism", "mosaicism"}
    random_conditions = ["born without a leg", "weak leg", "twisted leg", "born without a tail", "paralyzed",
                         "raspy lungs", "wasting disease", "blind", "one bad eye", "failing eyesight",
                         "partial hearing loss", "deaf", "constant joint pain", "seizure prone", "allergies",
                         "persistent headaches", "cleft palate", "wobbly cat syndrome"]
    noleg_accs = {"VINE", "ASHY PAWS", "MUD PAWS", "BLOODY PAWS", "MUD", "STARFLOWERS", "LAVENDERANKLET", "HOLLY2", "HOLLYVINES"}
    condition_options = ["None"] + list(PERMANENT)
    details_options = {'fur_texture': ['soft', 'curly', 'rough', 'silky', 'sleek', 'wavy', 'sparse', 'tangled', 'fuzzy',
                 'spiky'],
 'build': ['stocky', 'slender', 'lithe', 'wiry', 'muscular', 'lanky', 'delicate', 'hunched', 'hefty',
           'burly', 'bulky', 'plump', 'brawny', 'stout', 'broad', 'chubby', 'fat', 'chunky',
           'big-boned'],
 'height': ['petite', 'short', 'average', 'tall', 'towering'],
 'backstory': ['clan_founder', 'clanborn', 'halfclan1', 'halfclan2', 'outsider_roots1',
               'outsider_roots2', 'loner1', 'loner2', 'loner3', 'loner4', 'kittypet1', 'kittypet2',
               'kittypet3', 'kittypet4', 'rogue1', 'rogue2', 'rogue3', 'abandoned1', 'abandoned2',
               'abandoned3', 'abandoned4', 'otherclan1', 'otherclan2', 'otherclan3',
               'otherclan4', 'otherclan5', 'disgraced1', 'disgraced2', 'disgraced3', 'retired_leader',
               'medicine_cat', 'ostracized_warrior', 'refugee1', 'refugee2', 'refugee3', 'refugee4',
               'refugee5', 'refugee6', 'tragedy_survivor1', 'tragedy_survivor2', 'tragedy_survivor3',
               'tragedy_survivor4', 'wandering_healer1', 'wandering_healer2', 'guided1', 'guided2',
               'guided3', 'guided4', 'orphaned1', 'orphaned2', 'orphaned3', 'orphaned4', 'orphaned5',
               'orphaned6', 'outsider1', 'outsider2', 'outsider3', 'unknown']}

    def init_customizer(self):
        self.customizer_undo = []
        self.customizer_redo = []
        self.customizer_locks = set()
        if hasattr(self, "initial_customizer_state"):
            del self.initial_customizer_state
        self.custom_cat = None
        self.trait_options = self.kit_traits
        self.healed = False
        self.facet_reset = False
        defaults = Pelt()
        self.fur_texture = defaults.fur_texture
        self.build = defaults.build
        self.height = defaults.height
        self.backstory = "Random" if getattr(self, "newborn_origins", False) else "clanborn"
        newborn_origins = list(dict.fromkeys(
            origin for origins in BACKSTORIES["birth_backstories"].values() for origin in origins))
        self.details_options = dict(self.details_options)
        if getattr(self, "newborn_origins", False):
            self.details_options["backstory"] = ["Random"] + newborn_origins
        else:
            self.details_options["backstory"] = list(dict.fromkeys(self.details_options["backstory"] + newborn_origins))
        self.secondary_skill = "None"
        self.elements = {}
        self.pname="SingleColour"
        self.length="short"
        self.colour="WHITE"
        self.white_patches=[]
        self.eye_colour="BLUE"
        self.eye_colour2=None
        self.tortiebase=None
        self.tortiecolour=None
        self.pattern=[]
        self.tortiepattern=None
        self.vitiligo=None
        self.points=None
        self.paralyzed=False
        self.opacity=100
        self.scars=[]
        self.tint="None"
        self.skin="BLACK"
        self.white_patches_tint="None"
        self.kitten_sprite=0
        self.reverse=False
        self.skill = "Random"
        self.accessories=[]
        self.inventory = []
        self.sex = "male"
        self.personality = self.trait_options[0]
        self.permanent_conditions = []
        self.preview_age = "kitten"
        self.page = 0
        self.adolescent_pose = 3
        self.adult_pose = 6
        self.elder_pose = 12
        self.faith = "flexible"
        self.skills = ["Random"]

        for skillpath in SkillPath:
            count = 0
            for skill in skillpath.value:
                count += 1
                if count == 1:
                    self.skills.append(skill)

        # NEW CUSTOMISER BUTTON DICTS

        self.current_selection = "pelt_pattern"
        self.customiser_sort = "default"
        self.search_text = ""
        self.previous_search_text = "search"

        self.tortie_enabled = False
        self.current_selection_buttons = {}
        # Page 0
        self.preview_age_buttons = {}
        self.kitten_pose_buttons = {}
        self.adolescent_pose_buttons = {}
        self.adult_pose_buttons = {}
        self.elder_pose_buttons = {}
        self.fur_length_buttons = {}
        self.reverse_buttons = {}
        # Page 1
        self.pelt_colour_buttons = {}
        self.pelt_pattern_buttons = {}
        self.tint_buttons = {}

        self.tortie_patches_buttons = {}
        self.tortie_colour_buttons = {}
        self.tortie_pattern_buttons = {}

        self.pelt_colour_names = {}
        self.pelt_pattern_names = {}

        self.white_patches_buttons = {}
        self.white_patches_names = {}

        self.points_buttons = {}
        self.points_names = {}

        self.vitiligo_buttons = {}
        self.vitiligo_names = {}

        self.white_patches_tint_buttons = {}

        self.tortie_patches_names = {}
        self.tortie_colour_names = {}
        self.tortie_pattern_names = {}


        # Page 2
        self.eye_colour_buttons = {}
        self.eye_colour_names = {}

        self.heterochromia_buttons = {}
        self.heterochromia_names = {}

        self.skin_buttons = {}
        self.skin_names = {}

        self.scar_buttons = {}
        self.scar_names = {}

        self.accessory_buttons = {}
        self.accessory_names = {}

        # Page 3
        self.condition_buttons = {}
        self.condition_names = {}

        self.trait_buttons = {}
        self.trait_names = {}

        self.skill_buttons = {}
        self.skill_names = {}

        self.faith_buttons = {}
        self.faith_names = {}

        self.sex_buttons = {}

        self.customiser_button_dicts = [
            self.current_selection_buttons,
            self.preview_age_buttons,
            self.kitten_pose_buttons,
            self.adolescent_pose_buttons,
            self.adult_pose_buttons,
            self.elder_pose_buttons,
            self.fur_length_buttons,
            self.reverse_buttons,

            self.pelt_colour_buttons,
            self.pelt_pattern_buttons,
            self.tint_buttons,

            self.white_patches_buttons,
            self.white_patches_names,
            self.points_buttons,
            self.points_names,

            self.vitiligo_buttons,
            self.vitiligo_names,

            self.white_patches_tint_buttons,

            self.tortie_patches_buttons,
            self.tortie_colour_buttons,
            self.tortie_pattern_buttons,

            self.pelt_colour_names,
            self.pelt_pattern_names,

            self.tortie_patches_names,
            self.tortie_colour_names,
            self.tortie_pattern_names,

            self.eye_colour_buttons,
            self.eye_colour_names,

            self.heterochromia_buttons,
            self.heterochromia_names,

            self.skin_buttons,
            self.skin_names,

            self.scar_buttons,
            self.scar_names,

            self.accessory_buttons,
            self.accessory_names,

            self.condition_buttons,
            self.condition_names,

            self.trait_buttons,
            self.trait_names,

            self.skill_buttons,
            self.skill_names,

            self.faith_buttons,
            self.faith_names,

            self.sex_buttons
            ]

        self.notail_accs = ['RED FEATHERS', 'BLUE FEATHERS', 'JAY FEATHERS', "SEAWEED",
                            "DAISY CORSAGE", "GULL FEATHERS", "SPARROW FEATHERS", "CLOVER", "DAISY",
                            "SPRINGFEATHERS", "CLOVER", "LAVENDERTAILWRAP", "CELESTIALCHIMES",
                            "LUNARCHIMES", "SILVERLUNARCHIMES", "FLOWER MOSS", "SANVITALIAFLOWERS",
                            "STARFLOWERS", "SHELL PACK", "MOSS2", "MUSHROOMS", "CLOVERS", "MUD", "LADYBUGS",
                            "FIRBRANCHES", "CHERRYBLOSSOM", "MISTLETOE", "BROWNMOSSPELT", "BLEEDINGVINES",
                            "BLEEDINGHEART", "MOREFERN", "GRAYMOSSPELT", "FERN", "YELLOWWISTERIA", "WATTLE", "SPRINGFLOWERCORSAGE"]
        # god damn we have a lot of tail accessories

    def randomize_custom_cat(self):
        before = self.get_customizer_state()
        pelts = list(Pelt.sprites_names.keys())
        pelts.remove("Tortie")
        pelts.remove("Calico")
        pelts.remove("TwoColour")
        pelts_tortie = pelts.copy()
        pelts_tortie.remove("SingleColour")
        # pelts_tortie.remove("TwoColour")
        # pelts_tortie.append("Single")
        permanent_conditions = self.random_conditions

        white_patches = ["FULLWHITE"] + Pelt.little_white + Pelt.mid_white + Pelt.high_white + Pelt.mostly_white
        self.pname= random.choice(pelts) if random.randint(1,3) == 1 else "Tortie"
        self.length=random.choice(["short", "medium", "long"])
        self.colour=random.choice(Pelt.pelt_colours)
        self.white_patches= [choice(white_patches)] if random.randint(1,2) == 1 else []
        self.eye_colour=choice(Pelt.eye_colours)
        self.eye_colour2=choice(Pelt.eye_colours) if random.randint(1,10) == 1 else None
        self.tortiebase=choice(Pelt.tortiebases)
        self.tortiecolour=choice(Pelt.pelt_colours)
        self.pattern=[choice(Pelt.tortiepatterns)]
        self.tortiepattern=choice(pelts_tortie)
        self.vitiligo=choice(Pelt.vit) if random.randint(1,20) == 1 else None
        self.points=choice(Pelt.point_markings) if random.randint(1,5) == 1 else None
        self.scars=[choice(Pelt.scars1 + Pelt.scars2 + Pelt.scars3)] if random.randint(1,10) == 1 else []
        self.tint=choice(["pink", "gray", "red", "orange", "black", "yellow", "purple", "blue","dilute","warmdilute","cooldilute", "blush", "rosy", "redwood", "maroon", "sandy", "beige", "coral", "tan", "cream", "yolk", "gold", "rust", "lightpurple", "darkpurple", "bananaone", "bananatwo", "sunny", "peach", "salmon", "buttercup", "fall", "willow", "lilac", "plum", "cadet", "cobalt", "bluesky", "browngray", "grapefruit", "lightpink", "green", "flower", "kiwi", "dullgreen", "olive", "sky", "lightblue", "tan", "cream", "bluesky", "browngray", "bluegray", "cadet", "flint", "storm", "darkpurple", "cobalt", "steel", "ebony", "sunrise", "lightorange", "periwinkle", "navy", "graygreen", "flint", "acacia", "bronze", "sooty", "plum", "lilac", "cadet", "cobalt", "bluegray", "darkpurple", "ebony", "sunrise", "pinkgray", "flower", "sunflower", "wood", "dust"]) if random.randint(1,5) == 1 else None
        self.skin=choice(Pelt.skin_sprites)
        self.white_patches_tint=choice(["offwhite", "cream", "darkcream", "gray", "pink"]) if random.randint(1,5) == 1 else None
        self.reverse= False if random.randint(1,2) == 1 else True
        self.skill = "Random"
        self.sex = random.choice(["male", "female", "intersex"])
        self.personality = choice(self.trait_options)

        self.accessories = [choice(Pelt.plant_accessories + Pelt.wild_accessories + Pelt.collars + Pelt.flower_accessories + Pelt.plant2_accessories + Pelt.snake_accessories + Pelt.smallAnimal_accessories + Pelt.deadInsect_accessories + Pelt.aliveInsect_accessories + Pelt.fruit_accessories + Pelt.crafted_accessories + Pelt.tail2_accessories)] if random.randint(1,5) == 1 else []

        self.accessories = [choice(Pelt.plant_accessories + Pelt.wild_accessories + Pelt.collars + Pelt.flower_accessories + Pelt.plant2_accessories + Pelt.snake_accessories + Pelt.smallAnimal_accessories + Pelt.deadInsect_accessories + Pelt.aliveInsect_accessories + Pelt.fruit_accessories + Pelt.crafted_accessories + Pelt.tail2_accessories)] if random.randint(1,5) == 1 else []
        condition = choice(permanent_conditions) if random.randint(1,30) == 1 else None
        self.set_customizer_conditions([condition] if condition else [])
        if "blind" in self.permanent_conditions and random.randint(0, 10) == 1:
            self.scars.append("BOTHBLIND")
        elif "one bad eye" in self.permanent_conditions and random.randint(0, 10) == 1:
            self.scars.append(random.choice(["LEFTBLIND", "RIGHTBLIND", "BRIGHTHEART"]))
        elif any(name in self.permanent_conditions for name in ("deaf", "partial hearing loss")) and random.randint(0, 10):
            self.scars.append(random.choice(["LEFTEAR", "RIGHTEAR", "NOEAR"]))

        self.faith = random.choice(["flexible", "starclan", "dark forest", "neutral"])

        self.kitten_sprite=random.randint(0,2)
        self.adolescent_pose = random.randint(3,5)
        if self.length in ["short", "medium"]:
            self.adult_pose = random.randint(6,8)
        else:
            self.adult_pose = random.randint(9,11)
        self.elder_pose = random.randint(12,14)

        if self.pname == "Tortie":
            self.tortie_enabled = True
        else:
            self.tortie_enabled = False

        if hasattr(self, "trait_options"):
            self.personality = choice(self.trait_options)
        self.apply_customizer_locks(before)

    def selected_customizer_lock(self):
        if self.page == 0:
            return f"{self.preview_age}_pose"
        if self.current_selection.startswith("tortie_"):
            return "pelt_pattern"
        if self.current_selection == "scar":
            return "condition"
        return self.current_selection

    def apply_customizer_locks(self, before):
        if not self.customizer_locks:
            self.set_customizer_conditions(self.permanent_conditions)
            return
        for key in self.customizer_locks:
            for attribute in self.customizer_lock_groups[key]:
                setattr(self, attribute, deepcopy(before[attribute]))
        if self.length == "long" and self.adult_pose in range(6, 9):
            self.adult_pose += 3
        elif self.length != "long" and self.adult_pose in range(9, 12):
            self.adult_pose -= 3
        if "condition" in self.customizer_locks and any(name in self.sex_specific_conditions for name in self.permanent_conditions):
            self.sex = before["sex"]
        # Locked accessories require the anatomy they were chosen for.
        if "accessory" in self.customizer_locks:
            incompatible = ("NOTAIL" in self.scars and any(item in self.notail_accs for item in self.accessories)) or (
                "NOPAW" in self.scars and any(item in self.noleg_accs for item in self.accessories))
            if incompatible:
                for attribute in self.customizer_lock_groups["condition"]:
                    setattr(self, attribute, deepcopy(before[attribute]))
        self.set_customizer_conditions(self.permanent_conditions)

    def setup_customizer_lock_buttons(self):
        if self.page == 0:
            positions = {
                "kitten_pose": (55, 165), "adolescent_pose": (55, 260),
                "adult_pose": (55, 395), "elder_pose": (55, 460),
                "length": (715, 270), "reverse": (715, 455),
            }
        else:
            positions = {self.selected_customizer_lock(): (465, 425)}
            if self.page == 3:
                positions.update({"faith": (45, 375), "sex": (45, 470)})
        labels = {
            "adult_pose": "adult pose and fur length",
            "pelt_pattern": "pelt pattern and tortie details",
            "pelt_colour": "pelt colour and tint",
            "white_patches": "white patches and their tint",
            "condition": "scars and permanent condition",
        }
        for key, position in positions.items():
            if f"lock_{key}" in self.elements:
                self.elements[f"lock_{key}"].kill()
            locked = key in self.customizer_locks
            label = labels.get(key, key.replace("_", " "))
            self.elements[f"lock_{key}"] = UISurfaceImageButton(
                ui_scale(pygame.Rect(position, (65, 30))),
                "Unlock" if locked else "Lock",
                get_button_dict(ButtonStyles.SQUOVAL, (65, 30)),
                object_id="@buttonstyles_squoval",
                manager=MANAGER,
                starting_height=2,
                tool_tip_text=f"{'Unlock' if locked else 'Lock'} {label} during randomization. Manual edits are still allowed.",
            )
        self.elements["randomise_selection"].enable()
        if self.selected_customizer_lock() in self.customizer_locks:
            self.elements["randomise_selection"].disable()
        elif self.page == 2 and self.current_selection == "accessory" and not self.accessory_options():
            self.elements["randomise_selection"].disable()

    def get_customizer_state(self):
        return deepcopy({attribute: getattr(self, attribute) for attribute in (
            "pname", "length", "colour", "white_patches", "eye_colour", "eye_colour2",
            "tortiebase", "tortiecolour", "pattern", "tortiepattern", "tortie_enabled",
            "vitiligo", "points", "paralyzed", "opacity", "scars", "tint", "skin",
            "white_patches_tint", "kitten_sprite", "reverse", "skill", "accessories",
            "inventory", "sex", "personality", "permanent_conditions", "preview_age",
            "adolescent_pose", "adult_pose", "elder_pose", "faith", "customizer_locks",
            "secondary_skill", "fur_texture", "build", "height", "backstory", "healed", "facet_reset",
        )})

    def update_customizer_history_buttons(self):
        if self.customizer_undo:
            self.elements["undo_customize"].enable()
        else:
            self.elements["undo_customize"].disable()
        if self.customizer_redo:
            self.elements["redo_customize"].enable()
        else:
            self.elements["redo_customize"].disable()

    def load_customizer_appearance(self, cat):
        pelt = cat.pelt
        self.pname = pelt.name
        for draft, stage in (("kitten_sprite", "kitten"), ("adolescent_pose", "adolescent"),
                             ("adult_pose", "adult"), ("elder_pose", "senior")):
            setattr(self, draft, pelt.cat_sprites[stage])
        for field in ("length", "colour", "white_patches", "eye_colour", "eye_colour2", "tortiebase",
                      "tortiecolour", "pattern", "tortiepattern", "vitiligo", "points", "paralyzed", "opacity",
                      "scars", "tint", "skin", "white_patches_tint", "reverse", "accessories", "inventory",
                      "fur_texture", "build", "height"):
            value = deepcopy(getattr(pelt, field))
            if field in ("white_patches", "pattern") and not isinstance(value, list):
                value = [value] if value else []
            setattr(self, field, value)
        self.sex = cat.gender
        self.tortie_enabled = pelt.name in ("Tortie", "Calico")

    def open_customize_cat(self):

        if not hasattr(self, "initial_customizer_state"):
            self.initial_customizer_state = self.get_customizer_state()
        self.clear_all_page()
        self.sub_screen = "customize cat"

        self.selected_cat = None
        # clearing selected cat for the eye colour display bug

        pelt2 = Pelt(
            name=self.pname,
            length=self.length,
            colour=self.colour,
            white_patches=self.white_patches.copy(),
            eye_color=self.eye_colour,
            eye_colour2=self.eye_colour2,
            tortiebase=self.tortiebase,
            tortiecolour=self.tortiecolour,
            pattern=self.pattern.copy(),
            tortiepattern=self.tortiepattern.lower() if self.tortiepattern else None,
            vitiligo=self.vitiligo,
            points=self.points,
            accessory=None,
            paralyzed=self.paralyzed,
            scars=self.scars,
            tint=self.tint,
            skin=self.skin,
            white_patches_tint=self.white_patches_tint,
            kitten_sprite=self.kitten_sprite if self.kitten_sprite else 0,
            adol_sprite=self.adolescent_pose if self.adolescent_pose else 3,
            adult_sprite=self.adult_pose if self.adult_pose else 6,
            senior_sprite=self.elder_pose if self.elder_pose else 12,
            reverse=self.reverse,
            accessories=self.accessories,
            inventory=self.inventory.copy(),
            fur_texture=self.fur_texture, build=self.build, height=self.height,
        )
        if self.length == 'long' and self.adult_pose < 9:
            pelt2.cat_sprites['young adult'] = self.adult_pose + 9
            pelt2.cat_sprites['adult'] = self.adult_pose + 9
            pelt2.cat_sprites['senior adult'] = self.adult_pose + 9

        self.elements["left"] = UIImageButton(ui_scale(pygame.Rect((17, 310), (51, 67))), "", object_id="#arrow_right_fancy",
                                                 starting_height=2)

        self.elements["right"] = UIImageButton(ui_scale(pygame.Rect((730, 310), (51, 67))), "", object_id="#arrow_left_fancy",
                                             starting_height=2)
        if self.page == 0:
            self.elements['left'].disable()
        else:
            self.elements['left'].enable()

        if self.page == 4:
            self.elements['right'].disable()
        else:
            self.elements['right'].enable()



        column1_x = 75  # x-coordinate for column 1
        column2_x = 225  # x-coordinate for column 2
        column3_x = 450  # x-coordinate for column 3
        column4_x = 600
        x_align = 170
        x_align2 = 100
        x_align3 = 125
        y_pos = [40, 107, 140, 207, 240, 307, 340, 407, 440, 507, 540]

        self.elements['random_customize'] = UISurfaceImageButton(
            ui_scale(pygame.Rect((327, 80), (150, 30))),
            Icon.DICE + " Random cat",
            get_button_dict(ButtonStyles.SQUOVAL, (150, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            starting_height=2,
            sound_id="dice_roll",
        )

        self.elements["undo_customize"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((257, 80), (65, 30))),
            "Undo",
            get_button_dict(ButtonStyles.SQUOVAL, (65, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            starting_height=2,
        )
        self.elements["redo_customize"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((482, 80), (65, 30))),
            "Redo",
            get_button_dict(ButtonStyles.SQUOVAL, (65, 30)),
            object_id="@buttonstyles_squoval",
            manager=MANAGER,
            starting_height=2,
        )
        self.update_customizer_history_buttons()

        pelts = list(Pelt.sprites_names.keys())
        pelts.remove("Tortie")
        pelts.remove("Calico")
        pelts.remove("TwoColour")

        pelts_tortie = pelts.copy()
        # pelts_tortie.remove("SingleColour")
        # pelts_tortie.remove("TwoColour")


    # background images
    # values are ((x position, y position), (x width, y height))


        if game.settings['dark mode']:
            self.elements['spritebg'] = pygame_gui.elements.UIImage(ui_scale(pygame.Rect((275, 125), (250, 285))),
                                                                  self.sprite_preview_bg_dark, manager=MANAGER)
        else:
            self.elements['spritebg'] = pygame_gui.elements.UIImage(ui_scale(pygame.Rect((275, 125), (250, 285))),
                                                                  self.sprite_preview_bg, manager=MANAGER)

        c_moons = 1
        if self.preview_age == "adolescent":
            c_moons = 6
        elif self.preview_age == "adult":
            c_moons = 12
        elif self.preview_age == "elder":
            c_moons = 121
        custom_sprite = self.refresh_preview(pelt2, c_moons)
        self.elements["sprite"] = UISpriteButton(ui_scale(pygame.Rect
                                         ((315, 160), (175, 175))),
                                   custom_sprite,
                                   self.custom_cat.ID,
                                   starting_height=0, manager=MANAGER)

        self.elements['randomise_selection'] = UISurfaceImageButton(
            ui_scale(pygame.Rect((385, 425), (34, 34))),
            Icon.DICE,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            manager=MANAGER,
            starting_height=2,
            sound_id="dice_roll",
        )

        self.elements["cycle_left"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((345, 425), (34, 34))),
            Icon.ARROW_LEFT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            starting_height=0,
        )

        self.elements["cycle_right"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((425, 425), (34, 34))),
            Icon.ARROW_RIGHT,
            get_button_dict(ButtonStyles.ICON, (34, 34)),
            object_id="@buttonstyles_icon",
            starting_height=0,
        )

        if self.page == 0:
            # PAGE 0
            # poses

            # Preview age
            x_pos = 535
            self.elements['preview text'] = pygame_gui.elements.UITextBox(
                    'Preview Age',
                    ui_scale(pygame.Rect((x_pos, 135), (170, 34))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"), manager=MANAGER
                )
            button_count = 0
            age_y_pos = 175
            for i in ["kitten", "adolescent", "adult", "elder"]:
                self.preview_age_buttons[i] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, age_y_pos), (95, 34))),
                    i,
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (95, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 110
                button_count += 1
                if button_count == 2:
                    age_y_pos += 40
                    x_pos = 535
            # puts the last two buttons on the bottom so theyre not all in one line

            # fur length
            x_pos = 550
            self.elements['fur_length_text'] = pygame_gui.elements.UITextBox(
                    'Fur Length',
                    ui_scale(pygame.Rect((x_pos, 310),(170, 34))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"), manager=MANAGER
                )
            button_count = 0
            fur_y_pos = 350
            for i in ["short", "medium", "long"]:
                self.fur_length_buttons[i] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, fur_y_pos), (75, 34))),
                    str(i),
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (75, 34)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 95
                button_count += 1
                if button_count == 2:
                    fur_y_pos += 40
                    x_pos = 600

            x_pos = 600
            self.elements['reverse text'] = pygame_gui.elements.UITextBox(
                'Reverse',
                ui_scale(pygame.Rect((550, 455),(170, 34))),
                object_id=get_text_box_theme("#text_box_30_horizcenter"),
                manager=MANAGER
                )
            for i in [True, False]:
                self.reverse_buttons[str(i)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 495), (34, 34))),
                    str(i)[0],
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40

            # Kitten poses
            x_pos = 125
            self.elements['kitten_pose_text'] = pygame_gui.elements.UITextBox(
                    'Kitten',
                    ui_scale(pygame.Rect((x_pos, 165), (115, 30))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"), manager=MANAGER
                )

            for pose in range(0,3):
                self.kitten_pose_buttons[str(pose)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 200), (34, 34))),
                    str(pose),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40

            # Apprentice poses
            x_pos = 125
            self.elements['adolescent_pose_text'] = pygame_gui.elements.UITextBox(
                    'Apprentice',
                    ui_scale(pygame.Rect((x_pos, 260), (115, 30))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"),
                    manager=MANAGER
                )
            for pose in range(3,6):
                self.adolescent_pose_buttons[str(pose)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 295), (34, 34))),
                    str(pose),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40

            x_pos = 125
            if self.length in ["short", "medium"]:
                pose_range = range(6,9)
            else:
                pose_range = range(9,12)

            self.elements['adult_pose_text'] = pygame_gui.elements.UITextBox(
                'Adult',
                ui_scale(pygame.Rect((x_pos, 360), (115, 30))),
                object_id=get_text_box_theme("#text_box_30_horizcenter"), manager=MANAGER
            )

            for pose in pose_range:
                self.adult_pose_buttons[str(pose)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 395), (34, 34))),
                    str(pose),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40

            x_pos = 125
            self.elements['elder_pose_text'] = pygame_gui.elements.UITextBox(
                    'Elder',
                    ui_scale(pygame.Rect((x_pos, 460), (115, 30))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"),
                    manager=MANAGER
                )
            for pose in range(12,15):
                self.elder_pose_buttons[str(pose)] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, 495), (34, 34))),
                    str(pose),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                x_pos += 40

        if self.page in (1, 2):
            editor = CatAppearanceEditor(self.page, self.current_selection, pelt2,
                                         self.search_text, self.customiser_sort == "alphabetical", creation=True,
                                         button_dicts={key: getattr(self, key + "_buttons") for key in CatAppearanceEditor.categories[self.page]},
                                         tint_buttons=self.tint_buttons if self.current_selection == "pelt_colour" else self.white_patches_tint_buttons)
            self.elements["appearance_editor"] = editor
            editor.option_list.on_change = self.update_disabled_buttons
            self.current_selection = editor.selection
            self.current_selection_buttons.update(editor.category_buttons)
            for key in ("search_bar", "search_button", "clear", "default", "alphabetical", "tortie_checkbox", "match_tortie", "match_base"):
                if key in editor.elements:
                    self.elements[key] = editor.elements[key]
            getattr(self, self.current_selection + "_buttons").update(editor.option_buttons)
            if self.current_selection == "pelt_colour":
                self.tint_buttons.update(editor.tint_buttons)
            elif self.current_selection in ("white_patches", "points"):
                self.white_patches_tint_buttons.update(editor.tint_buttons)

        elif self.page == 3:

            if self.current_selection not in [
                "condition", "trait", "skill", "faith", "sex"
                ]:
                self.current_selection = "condition"

            x_pos = 120
            selection_y_pos = 150
            for i in ["condition", "trait", "skill"]:
                self.current_selection_buttons[i] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((x_pos, selection_y_pos), (120, 40))),
                    i.replace("_", " "),
                    get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 40)),
                    object_id="@buttonstyles_rounded_rect",
                    manager=MANAGER,
                    starting_height=2
                )
                if i == "skill":
                    selection_y_pos += 60
                if i == "faith":
                    selection_y_pos += 60
                selection_y_pos += 50

            faith_x_pos = 108
            self.elements["faith_label"] = pygame_gui.elements.UITextBox(
                    "Faith",
                    ui_scale(pygame.Rect((110, 375), (131, 25))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"),
                    manager=MANAGER
                )
            for faith in ["starclan", "neutral", "dark forest", "flexible"]:
                if faith == "starclan":
                    faith_text = "Ascenders"
                elif faith == "dark forest":
                    faith_text = "Parasites"
                else:
                    faith_text = faith.capitalize()
                self.faith_buttons[faith] = UIImageButton(
                    ui_scale(pygame.Rect((faith_x_pos, 400), (34, 34))),
                    "",
                    object_id=f"#faith_{faith.replace(' ', '')}_button",
                    tool_tip_text=faith_text,
                    manager=MANAGER
                )
                faith_x_pos += 34

            sex_x_pos = 137
            self.elements["sex_label"] = pygame_gui.elements.UITextBox(
                    "Sex",
                    ui_scale(pygame.Rect((110, 470), (131, 25))),
                    object_id=get_text_box_theme("#text_box_30_horizcenter"),
                    manager=MANAGER
                )
            for gender in ["male", "female", "intersex"]:
                self.sex_buttons[gender] = UISurfaceImageButton(
                    ui_scale(pygame.Rect((sex_x_pos, 500), (34, 34))),
                    gender[0].upper(),
                    get_button_dict(ButtonStyles.ICON, (34, 34)),
                    object_id="@buttonstyles_icon",
                    manager=MANAGER,
                    starting_height=2
                )
                sex_x_pos += 40

            options = {"condition": self.condition_options, "trait": self.trait_options, "skill": self.skills}
            if self.current_selection in options:
                buttons = getattr(self, self.current_selection + "_buttons")
                container = CustomizerList(pygame.Rect((550, 85), (175, 480)),
                                          options[self.current_selection], str.capitalize, buttons, self.customizer_description)
                self.elements["scroll_container"] = container
                container.on_change = self.update_disabled_buttons
                selected = {"condition": next(iter(self.permanent_conditions), "None"),
                            "trait": self.personality, "skill": self.skill}[self.current_selection]
                if selected in container.options:
                    container.scroll_to(selected)

        if self.page == 4:
            self.build_details_page()
        self.elements["reset_customize"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((345, 610), (110, 30))), "Reset",
            get_button_dict(ButtonStyles.SQUOVAL, (110, 30)), object_id="@buttonstyles_squoval", manager=MANAGER)
        self.build_customizer_footer()

        self.update_disabled_buttons()
        self.setup_customizer_lock_buttons()

    def handle_customize_cat_event(self, event):
        if event.type != pygame_gui.UI_BUTTON_START_PRESS:
            return
        if event.ui_element in (self.elements["undo_customize"], self.elements["redo_customize"]):
            if event.ui_element == self.elements["undo_customize"]:
                source, destination = self.customizer_undo, self.customizer_redo
            else:
                source, destination = self.customizer_redo, self.customizer_undo
            if source:
                destination.append(self.get_customizer_state())
                for attribute, value in source.pop().items():
                    setattr(self, attribute, deepcopy(value))
                self.open_customize_cat()
            return
        before = self.get_customizer_state()
        lock_key = next((key for key in self.customizer_lock_groups
                         if event.ui_element == self.elements.get(f"lock_{key}")), None)
        if lock_key:
            if lock_key in self.customizer_locks:
                self.customizer_locks.remove(lock_key)
            else:
                self.customizer_locks.add(lock_key)
            self.setup_customizer_lock_buttons()
        elif event.ui_element == self.elements["randomise_selection"] and not self.elements["randomise_selection"].is_enabled:
            return
        elif event.ui_element == self.elements["reset_customize"]:
            for attribute, value in self.initial_customizer_state.items():
                setattr(self, attribute, deepcopy(value))
            self.open_customize_cat()
        elif self.page == 4 and self.handle_details_event(event):
            pass
        else:
            self._handle_customize_cat_event(event)
        if self.sub_screen == "customize cat" and before != self.get_customizer_state():
            self.customizer_undo.append(before)
            self.customizer_redo.clear()
            self.update_customizer_history_buttons()

    def _handle_customize_cat_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            pelts = list(Pelt.sprites_names.keys())
            pelts.remove("Tortie")
            pelts.remove("Calico")
            pelts.remove("TwoColour")
            pelts_tortie = pelts.copy()
            # pelts_tortie.remove("SingleColour")
            # pelts_tortie.remove("TwoColour")

            # cycle buttons. oh god
            if event.ui_element == self.elements["cycle_right"] or event.ui_element == self.elements["cycle_left"]:
                if event.ui_element == self.elements["cycle_right"]:
                    num = 1
                    if self.page == 0:
                        if self.preview_age == "kitten":
                            if self.kitten_sprite < 2:
                                self.kitten_sprite += 1
                            else:
                                self.kitten_sprite = 0
                        elif self.preview_age == "adolescent":
                            if self.adolescent_pose < 5:
                                self.adolescent_pose += 1
                            else:
                                self.adolescent_pose = 3
                        elif self.preview_age == "adult":
                            if self.length in ["short", "medium"]:
                                if self.adult_pose < 8:
                                    self.adult_pose += 1
                                else:
                                    self.adult_pose = 6
                            else:
                                if self.adult_pose < 11:
                                    self.adult_pose += 1
                                else:
                                    self.adult_pose = 9
                        elif self.preview_age == "elder":
                            if self.elder_pose < 14:
                                self.elder_pose += 1
                            else:
                                self.elder_pose = 12
                elif event.ui_element == self.elements["cycle_left"]:
                    num = -1
                    if self.page == 0:
                        if self.preview_age == "kitten":
                            if self.kitten_sprite > 0:
                                self.kitten_sprite -= 1
                            else:
                                self.kitten_sprite = 2
                        elif self.preview_age == "adolescent":
                            if self.adolescent_pose > 3:
                                self.adolescent_pose -= 1
                            else:
                                self.adolescent_pose = 5
                        elif self.preview_age == "adult":
                            if self.length in ["short", "medium"]:
                                if self.adult_pose > 6:
                                    self.adult_pose -= 1
                                else:
                                    self.adult_pose = 8
                            else:
                                if self.adult_pose > 9:
                                    self.adult_pose -= 1
                                else:
                                    self.adult_pose = 11
                        elif self.preview_age == "elder":
                            if self.elder_pose > 12:
                                self.elder_pose -= 1
                            else:
                                self.elder_pose = 14
                if self.page == 1:
                    if self.current_selection == "pelt_colour":
                        colours = Pelt.pelt_colours
                        current_index = colours.index(self.colour)
                        next_index = (current_index + num) % len(colours)
                        self.colour = colours[next_index]
                    elif self.current_selection == "white_patches":
                        patch_list = Pelt.little_white + Pelt.mid_white + Pelt.high_white + Pelt.mostly_white + ["FULLWHITE"]
                        if self.customiser_sort == "alphabetical":
                            patch_list.sort()

                        # grabbing search results
                        new_patch_list = []
                        searched = self.search_text
                        if searched not in ["", "search"]:
                            for patch in patch_list:
                                if searched in patch.lower():
                                    new_patch_list.append(patch)
                        else:
                            new_patch_list = patch_list

                        patches = ["None"] + new_patch_list
                        try:
                            current_index = patches.index(self.white_patches[0] if self.white_patches else "None")
                        except ValueError:
                            current_index = 0
                        next_index = (current_index + num) % len(patches)
                        if patches[next_index] == "None":
                            self.white_patches = self.white_patches[1:]
                        else:
                            self.white_patches = [patches[next_index]] + [patch for patch in self.white_patches[1:] if patch != patches[next_index]]
                    elif self.current_selection == "points":
                        points = ["None"] + Pelt.point_markings
                        current_index = points.index(str(self.points))
                        next_index = (current_index + num) % len(points)
                        if points[next_index] == "None":
                            self.points = None
                        else:
                            self.points = points[next_index]
                    elif self.current_selection == "vitiligo":
                        vitiligo = ["None"] + Pelt.vit
                        current_index = vitiligo.index(str(self.vitiligo))
                        next_index = (current_index + num) % len(vitiligo)
                        if vitiligo[next_index] == "None":
                            self.vitiligo = None
                        else:
                            self.vitiligo = vitiligo[next_index]
                    elif self.current_selection == "pelt_pattern":
                        if self.pname in ["Tortie", "Calico"]:
                            if self.tortiebase == "single":
                                basename = "SingleColour"
                            else:
                                basename = self.tortiebase.capitalize()
                            current_index = pelts.index(basename)
                        else:
                            current_index = pelts.index(self.pname)
                            #print(f"self.pname = {self.pname}")
                            #print(f"pelts = {pelts}")
                        next_index = (current_index + num) % len(pelts)
                        if pelts[next_index] in ["SingleColour", "TwoColour", "Singlecolour", "TwoColour", "SingleColour"] and self.pname in ["Tortie", "Calico"]:
                            next_pelt = "single"
                        else:
                            next_pelt = pelts[next_index]
                        if self.pname in ["Tortie", "Calico"]:
                            self.tortiebase = next_pelt.lower()
                        else:
                            if next_pelt != "SingleColour":
                                self.pname = next_pelt.capitalize()
                            else:
                                self.pname = next_pelt
                    elif self.current_selection == "tortie_colour":
                        colours = Pelt.pelt_colours
                        current_index = colours.index(str(self.tortiecolour))
                        next_index = (current_index + num) % len(colours)
                        self.tortiecolour = colours[next_index]
                    elif self.current_selection == "tortie_patches":
                        pelts = Pelt.tortiepatterns
                        current_index = pelts.index(self.pattern[0] if self.pattern else pelts[0])
                        next_index = (current_index + num) % len(pelts)
                        self.pattern = [pelts[next_index]] + [pattern for pattern in self.pattern[1:] if pattern != pelts[next_index]]
                    elif self.current_selection == "tortie_pattern":
                        pelts = pelts_tortie
                        if self.tortiepattern == "single":
                            next_pelt = "SingleColour"
                        else:
                            next_pelt = str(self.tortiepattern).capitalize()
                        current_index = pelts.index(next_pelt)
                        next_index = (current_index + num) % len(pelts)

                        if pelts[next_index] == "SingleColour":
                            self.tortiepattern = "single"
                        else:
                            self.tortiepattern = pelts[next_index].lower()
                elif self.page == 2:
                    if self.current_selection == "eye_colour":
                        colours = Pelt.eye_colours
                        current_index = colours.index(self.eye_colour)
                        next_index = (current_index + num) % len(colours)
                        self.eye_colour = colours[next_index]
                    elif self.current_selection == "heterochromia":
                        colours = ["None"] + Pelt.eye_colours
                        current_index = colours.index(str(self.eye_colour2))
                        next_index = (current_index + num) % len(colours)
                        if colours[next_index] == "None":
                            next_eye = None
                        else:
                            next_eye = colours[next_index]
                        self.eye_colour2 = next_eye
                    elif self.current_selection == "skin":
                        colours = Pelt.skin_sprites
                        current_index = colours.index(self.skin)
                        next_index = (current_index + num) % len(colours)
                        self.skin = colours[next_index]
                    elif self.current_selection == "scar":
                        scars = ["None"] + Pelt.scars1 + Pelt.scars2 + Pelt.scars3
                        current_index = scars.index(self.scars[-1]) if self.scars else 0
                        next_index = (current_index + num) % len(scars)
                        next_scar = scars[next_index]
                        self.set_customizer_scars(self.scars[:-1] + ([next_scar] if next_scar != "None" else []))
                    elif self.current_selection == "accessory":
                        accs = ["None"] + self.accessory_options()
                        try:
                            current_index = accs.index(self.accessories[0]) if self.accessories else 0
                        except ValueError:
                            current_index = 0
                        next_index = (current_index + num) % len(accs)
                        if accs[next_index] == "None":
                            next_acc = []
                        else:
                            next_acc = [accs[next_index]]
                        self.accessories = next_acc + [accessory for accessory in self.accessories[1:] if accessory not in next_acc]
                        self.inventory = self.accessories.copy()
                elif self.page == 3:
                    if self.current_selection == "condition":
                        remaining = self.permanent_conditions[1:]
                        options = [name for name in self.condition_options if name not in remaining and self.condition_allowed(name, remaining)]
                        current = next(iter(self.permanent_conditions), "None")
                        index = options.index(current) if current in options else 0
                        name = options[(index + num) % len(options)]
                        self.set_customizer_conditions(([name] if name != "None" else []) + remaining)
                    elif self.current_selection == "trait":
                        traits = self.trait_options
                        current_index = traits.index(self.personality)
                        next_index = (current_index + num) % len(traits)
                        self.personality = traits[next_index]
                    elif self.current_selection == "skill":
                        current_index = self.skills.index(self.skill)
                        next_index = (current_index + num) % len(self.skills)
                        self.skill = self.skills[next_index]

                self.update_sprite()
                self.update_disabled_buttons()
            elif event.ui_element == self.elements["randomise_selection"]:
                random_before = self.get_customizer_state()
                if self.page == 0:
                    if self.preview_age == "kitten":
                        self.kitten_sprite=random.randint(0,2)
                    elif self.preview_age == "adolescent":
                        self.adolescent_pose = random.randint(3,5)
                    elif self.preview_age == "adult":
                        if self.length in ["short", "medium"]:
                            self.adult_pose = random.randint(6,8)
                        else:
                            self.adult_pose = random.randint(9,11)
                    else:
                        self.elder_pose = random.randint(12,14)
                if self.page == 1:
                    if self.current_selection == "pelt_pattern":
                        if self.pname in ["Tortie", "Calico"]:
                            new_pattern = random.choice(pelts)
                            if new_pattern == "SingleColour":
                                new_pattern = "single"
                            self.tortiebase = new_pattern.lower()
                        else:
                            self.pname = random.choice(pelts)
                    elif self.current_selection == "pelt_colour":
                        self.colour = random.choice(Pelt.pelt_colours)
                    elif self.current_selection == "white_patches":
                        patch = random.choice(["FULLWHITE"] + Pelt.little_white + Pelt.mid_white + Pelt.high_white + Pelt.mostly_white + [None])
                        self.white_patches = [patch] if patch else []
                    elif self.current_selection == "points":
                        self.points = random.choice(Pelt.point_markings + [None])
                    elif self.current_selection == "vitiligo":
                        self.vitiligo = random.choice(Pelt.vit + [None])
                    elif self.current_selection == "tortie_pattern":
                        new_pattern = random.choice(pelts)
                        if new_pattern == "SingleColour":
                            new_pattern = "single"
                        self.tortiepattern = new_pattern.lower()
                    elif self.current_selection == "tortie_colour":
                        self.tortiecolour = random.choice(Pelt.pelt_colours)
                    elif self.current_selection == "tortie_patches":
                        self.pattern = [random.choice(Pelt.tortiepatterns)]
                elif self.page == 2:
                    if self.current_selection == "eye_colour":
                        self.eye_colour = random.choice(Pelt.eye_colours)
                    elif self.current_selection == "heterochromia":
                        self.eye_colour2 = random.choice(Pelt.eye_colours)
                    elif self.current_selection == "skin":
                        self.skin = random.choice(Pelt.skin_sprites)
                    elif self.current_selection == "scar":
                        self.set_customizer_scars(self.scars[:-1] + [random.choice(Pelt.scars1 + Pelt.scars2 + Pelt.scars3)])
                    elif self.current_selection == "accessory":

                        self.accessories = [choice(self.accessory_options())]
                        self.inventory = self.accessories.copy()
                elif self.page == 3:
                    if self.current_selection == "condition":
                        remaining = self.permanent_conditions[1:]
                        options = [name for name in ["None"] + self.random_conditions if name not in remaining and self.condition_allowed(name, remaining)]
                        name = random.choice(options)
                        self.set_customizer_conditions(([name] if name != "None" else []) + remaining)
                    elif self.current_selection == "trait":
                        self.personality = random.choice(self.trait_options)
                    elif self.current_selection == "skill":
                        skill_choices = []
                        for i in self.skills:
                            if i != "Random":
                                skill_choices.append(i)
                        self.skill = random.choice(skill_choices)

                self.apply_customizer_locks(random_before)
                self.update_sprite()
                self.update_disabled_buttons()

            if "search_button" in self.elements and event.ui_element == self.elements["search_button"]:
                self.search_text = self.elements["search_bar"].get_text()
                self.previous_search_text = self.search_text
                self.open_customize_cat()
                return
            if "clear" in self.elements and event.ui_element == self.elements["clear"]:
                self.search_text = ""
                self.previous_search_text = self.search_text
                self.open_customize_cat()
                return
            if "match_base" in self.elements and event.ui_element == self.elements["match_base"]:
                self.tortiepattern = self.tortiebase
                self.update_sprite()
                self.update_disabled_buttons()
            if "match_tortie" in self.elements and event.ui_element == self.elements["match_tortie"]:
                self.tortiebase = self.tortiepattern.lower()
                self.update_sprite()
                self.update_disabled_buttons()

            if self.page == 0:
                for i in self.preview_age_buttons.items():
                    if event.ui_element == self.preview_age_buttons[i[0]]:
                        self.preview_age = i[0]
                        self.open_customize_cat()
                        return
                for i in self.kitten_pose_buttons.items():
                    if event.ui_element == self.kitten_pose_buttons[i[0]]:
                        self.kitten_sprite = int(i[0])
                        self.open_customize_cat()
                        return
                for i in self.adolescent_pose_buttons.items():
                    if event.ui_element == self.adolescent_pose_buttons[i[0]]:
                        self.adolescent_pose = int(i[0])
                        self.open_customize_cat()
                        return
                for i in self.adult_pose_buttons.items():
                    if event.ui_element == self.adult_pose_buttons[i[0]]:
                        self.adult_pose = int(i[0])
                        self.open_customize_cat()
                        return
                for i in self.elder_pose_buttons.items():
                    if event.ui_element == self.elder_pose_buttons[i[0]]:
                        self.elder_pose = int(i[0])
                        self.open_customize_cat()
                        return
                for i in self.fur_length_buttons.items():
                    if event.ui_element == self.fur_length_buttons[i[0]]:
                        self.length = i[0]
                        # correct long/shorthaired poses
                        if self.adult_pose in range(9,12) and self.length in ["short", "medium"]:
                            self.adult_pose -= 3
                        elif self.adult_pose in range(6,9) and self.length == "long":
                            self.adult_pose += 3
                        self.open_customize_cat()
                        return
                for i in self.reverse_buttons.items():
                    if event.ui_element == self.reverse_buttons[i[0]]:
                        if i[0] == "False":
                            self.reverse = False
                        else:
                            self.reverse = True
                        self.open_customize_cat()
                        return
            elif self.page == 1:
                if event.ui_element == self.elements["tortie_checkbox"]:
                    if self.tortie_enabled is True:
                        self.tortie_enabled = False
                        self.pname = self.tortiebase.capitalize()
                        if self.pname == "Single":
                            self.pname = "SingleColour"
                        self.tortiebase = None
                        self.tortiecolour = None
                        self.tortiepattern = None
                        self.pattern = []
                    else:
                        self.tortie_enabled = True
                        self.tortiebase = self.pname.lower()
                        if self.tortiebase == "singlecolour":
                            self.tortiebase = "single"
                        self.pname = "Tortie"
                        self.tortiecolour = "GINGER"
                        self.tortiepattern = "classic"
                        self.pattern = ["ONE"]
                    self.open_customize_cat()
                    return
                for i in self.pelt_pattern_buttons.items():
                    if event.ui_element == self.pelt_pattern_buttons[i[0]]:
                        if self.pname == "Tortie":
                            self.tortiebase = i[0].lower()
                        else:
                            self.pname = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.pelt_colour_buttons.items():
                    if event.ui_element == self.pelt_colour_buttons[i[0]]:
                        self.colour = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.tint_buttons.items():
                    if event.ui_element == self.tint_buttons[i[0]]:
                        self.tint = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.white_patches_tint_buttons.items():
                    if event.ui_element == self.white_patches_tint_buttons[i[0]]:
                        self.white_patches_tint = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.white_patches_buttons.items():
                    if event.ui_element == self.white_patches_buttons[i[0]]:
                        if i[0] == "None":
                            self.white_patches = []
                        elif i[0] in self.white_patches:
                            self.white_patches.remove(i[0])
                        else:
                            self.white_patches.append(i[0])
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.points_buttons.items():
                    if event.ui_element == self.points_buttons[i[0]]:
                        if i[0] == "None":
                            self.points = None
                        else:
                            self.points = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.vitiligo_buttons.items():
                    if event.ui_element == self.vitiligo_buttons[i[0]]:
                        if i[0] == "None":
                            self.vitiligo = None
                        else:
                            self.vitiligo = i[0]
                        self.update_sprite()
                        self.update_disabled_buttons()
                # TORTIE
                for i in self.tortie_pattern_buttons.items():
                    if event.ui_element == self.tortie_pattern_buttons[i[0]]:
                        self.tortiepattern = i[0].lower()
                        if self.tortiepattern == "singlecolour":
                            self.tortiepattern = "single"
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.tortie_colour_buttons.items():
                    if event.ui_element == self.tortie_colour_buttons[i[0]]:
                        self.tortiecolour = i[0].upper()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.tortie_patches_buttons.items():
                    if event.ui_element == self.tortie_patches_buttons[i[0]]:
                        if i[0] == "None":
                            self.pattern = []
                        elif i[0].upper() in self.pattern:
                            self.pattern.remove(i[0].upper())
                        else:
                            self.pattern.append(i[0].upper())
                        self.update_sprite()
                        self.update_disabled_buttons()
            elif self.page == 2:
                for i in self.eye_colour_buttons.items():
                    if event.ui_element == self.eye_colour_buttons[i[0]]:
                        self.eye_colour = i[0].upper()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.heterochromia_buttons.items():
                    if event.ui_element == self.heterochromia_buttons[i[0]]:
                        self.eye_colour2 = i[0].upper() if i[0] != "None" else None
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.skin_buttons.items():
                    if event.ui_element == self.skin_buttons[i[0]]:
                        self.skin = i[0].upper()
                        self.update_sprite()
                        self.update_disabled_buttons()
                for scar, button in self.scar_buttons.items():
                    if event.ui_element == button:
                        scars = self.scars.copy()
                        if scar == "None":
                            scars = []
                        elif scar in scars:
                            scars.remove(scar)
                        else:
                            scars.append(scar)
                        self.set_customizer_scars(scars)
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.accessory_buttons.items():
                    if event.ui_element == self.accessory_buttons[i[0]]:
                        if i[0] == "None":
                            self.accessories = []
                            self.inventory = []
                        elif i[0].upper() in self.accessories:
                            self.accessories.remove(i[0].upper())
                            self.inventory = self.accessories.copy()
                        else:
                            self.accessories.append(i[0].upper())
                            self.inventory = self.accessories.copy()
                        self.update_sprite()
                        self.update_disabled_buttons()
            elif self.page == 3:
                for condition, button in self.condition_buttons.items():
                    if event.ui_element == button:
                        conditions = self.permanent_conditions.copy()
                        if condition == "None":
                            conditions = []
                        elif condition in conditions:
                            conditions.remove(condition)
                        elif self.condition_allowed(condition):
                            conditions.append(condition)
                        self.set_customizer_conditions(conditions)
                        self.update_sprite()
                        self.update_disabled_buttons()
                for i in self.trait_buttons.items():
                    if event.ui_element == self.trait_buttons[i[0]]:
                        self.personality = i[0]
                        self.update_disabled_buttons()
                for i in self.skill_buttons.items():
                    if event.ui_element == self.skill_buttons[i[0]]:
                        self.skill = i[0]
                        self.update_disabled_buttons()
                for i in self.faith_buttons.items():
                    if event.ui_element == self.faith_buttons[i[0]]:
                        self.faith = i[0]
                        self.update_disabled_buttons()
                for i in self.sex_buttons.items():
                    if event.ui_element == self.sex_buttons[i[0]]:
                        self.sex = i[0]
                        self.update_disabled_buttons()

            for i in self.current_selection_buttons.items():
                if event.ui_element == self.current_selection_buttons[i[0]]:
                    self.current_selection = i[0]
                    self.open_customize_cat()
                    return
            for i in ["default", "alphabetical"]:
                if i in self.elements:
                    if event.ui_element == self.elements[i]:
                        self.customiser_sort = i
                        self.open_customize_cat()
                        return

            if event.ui_element == self.main_menu:
                self.exit_customizer()
            elif event.ui_element == self.elements['right']:
                if self.page < 4:
                    self.page += 1
                    self.open_customize_cat()
                    return
            elif event.ui_element == self.elements['left']:
                if self.page > 0:
                    self.page -= 1
                    self.open_customize_cat()
                    return
            elif event.ui_element == self.elements['random_customize']:
                self.randomize_custom_cat()
                self.open_customize_cat()
                return
            elif event.ui_element == self.elements['next_step']:
                if self.elements['next_step'].is_enabled:
                    self.finish_customize_cat()
            elif event.ui_element == self.elements['previous_step']:
                self.previous_customizer_step()

    def update_disabled_buttons(self):
        if "appearance_editor" in self.elements:
            self.elements["appearance_editor"].refresh(self.custom_cat.pelt)
        if self.page == 0:
            for i in range(0,3):
                if self.kitten_sprite != i:
                    self.kitten_pose_buttons[str(i)].enable()
                else:
                    self.kitten_pose_buttons[str(i)].disable()
            for i in range(3,6):
                if self.adolescent_pose != i:
                    self.adolescent_pose_buttons[str(i)].enable()
                else:
                    self.adolescent_pose_buttons[str(i)].disable()

            if self.length in ["short", "medium"]:
                pose_range = range(6,9)
            else:
                pose_range = range(9,12)

            for i in pose_range:
                if self.adult_pose != i:
                    self.adult_pose_buttons[str(i)].enable()
                else:
                    self.adult_pose_buttons[str(i)].disable()

            for i in range(12,15):
                if self.elder_pose != i:
                    self.elder_pose_buttons[str(i)].enable()
                else:
                    self.elder_pose_buttons[str(i)].disable()

            for i in ["kitten", "adolescent", "adult", "elder"]:
                if self.preview_age != i:
                    self.preview_age_buttons[i].enable()
                else:
                    self.preview_age_buttons[i].disable()

            for i in ["short", "medium", "long"]:
                if self.length != i:
                    self.fur_length_buttons[i].enable()
                else:
                    self.fur_length_buttons[i].disable()

            for i in [True, False]:
                if self.reverse != i:
                    self.reverse_buttons[str(i)].enable()
                else:
                    self.reverse_buttons[str(i)].disable()

        if self.page == 1:
            pelts = list(Pelt.sprites_names.keys())
            pelts.remove("Tortie")
            pelts.remove("Calico")
            pelts.remove("TwoColour")
            pelts_tortie = pelts.copy()
            # pelts_tortie.remove("SingleColour")
            # pelts_tortie.remove("TwoColour")

            for i in self.pelt_pattern_buttons.items():
                if self.pname in ["Tortie", "Calico"]:
                    pattern = self.tortiebase.capitalize()
                    if pattern == "Single":
                        pattern = "SingleColour"
                else:
                    pattern = self.pname
                if i[0] != pattern:
                    self.pelt_pattern_buttons[i[0]].enable()
                else:
                    self.pelt_pattern_buttons[i[0]].disable()

            for i in self.pelt_colour_buttons.items():
                if i[0] != self.colour:
                    self.pelt_colour_buttons[i[0]].enable()
                else:
                    self.pelt_colour_buttons[i[0]].disable()

            for i in self.tint_buttons.items():
                if i[0] != self.tint:
                    self.tint_buttons[i[0]].enable()
                else:
                    self.tint_buttons[i[0]].disable()

            for i in self.white_patches_tint_buttons.items():
                if i[0] != self.white_patches_tint:
                    self.white_patches_tint_buttons[i[0]].enable()
                else:
                    self.white_patches_tint_buttons[i[0]].disable()

            for patch, button in self.white_patches_buttons.items():
                selected = patch in self.white_patches or (patch == "None" and not self.white_patches)
                update_checkbox(button, "@checked_checkbox" if selected else "@unchecked_checkbox")
                button.enable()
                if patch == "None" and not self.white_patches:
                    button.disable()

            for i in self.points_buttons.items():
                if i[0] != str(self.points):
                    self.points_buttons[i[0]].enable()
                else:
                    self.points_buttons[i[0]].disable()

            for i in self.vitiligo_buttons.items():
                if i[0] != str(self.vitiligo):
                    self.vitiligo_buttons[i[0]].enable()
                else:
                    self.vitiligo_buttons[i[0]].disable()

            for i in self.tortie_pattern_buttons.items():
                pattern = i[0].lower()
                if pattern == "singlecolour":
                    pattern = "single"
                if pattern != self.tortiepattern: # not changing to string bc this isnt accessible when its None
                    self.tortie_pattern_buttons[i[0]].enable()
                else:
                    self.tortie_pattern_buttons[i[0]].disable()

            for i in self.tortie_colour_buttons.items():
                if i[0] != self.tortiecolour:
                    self.tortie_colour_buttons[i[0]].enable()
                else:
                    self.tortie_colour_buttons[i[0]].disable()

            for pattern, button in self.tortie_patches_buttons.items():
                update_checkbox(button, "@checked_checkbox" if pattern.upper() in self.pattern or (pattern == "None" and not self.pattern) else "@unchecked_checkbox")
                button.enable()

            if "match_tortie" in self.elements:
                if self.pname != "Tortie":
                    self.elements["match_tortie"].disable()
                else:
                    self.elements["match_tortie"].enable()

        elif self.page == 2:
            for i in self.eye_colour_buttons.items():
                if i[0] != self.eye_colour:
                    self.eye_colour_buttons[i[0]].enable()
                else:
                    self.eye_colour_buttons[i[0]].disable()
            for i in self.heterochromia_buttons.items():
                if i[0] != str(self.eye_colour2):
                    self.heterochromia_buttons[i[0]].enable()
                else:
                    self.heterochromia_buttons[i[0]].disable()
            for i in self.skin_buttons.items():
                if i[0] != str(self.skin):
                    self.skin_buttons[i[0]].enable()
                else:
                    self.skin_buttons[i[0]].disable()
            for scar, button in self.scar_buttons.items():
                checked = scar in self.scars or (scar == "None" and not self.scars)
                update_checkbox(button, "@checked_checkbox" if checked else "@unchecked_checkbox")
                button.enable()
                if scar == "None" and not self.scars:
                    button.disable()
            for i in self.accessory_buttons.items():
                if i[0] == "None" and not self.accessories:
                    self.accessory_buttons[i[0]].disable()
                else:
                    self.accessory_buttons[i[0]].enable()
                update_checkbox(self.accessory_buttons[i[0]], "@checked_checkbox" if i[0] in self.accessories or (i[0] == "None" and not self.accessories) else "@unchecked_checkbox")
                if any(name in self.permanent_conditions for name in ("born without a tail", "lost their tail")):
                    for acc in self.notail_accs:
                        if acc in self.accessory_buttons:
                            self.accessory_buttons[acc].disable()
                if any(name in self.permanent_conditions for name in ("born without a leg", "lost a leg")):
                    for acc in self.noleg_accs:
                        if acc in self.accessory_buttons:
                            self.accessory_buttons[acc].disable()

        elif self.page == 3:
            if self.current_selection == "condition":
                if "condition_name" in self.elements:
                    self.elements["condition_name"].kill()
                    del self.elements["condition_name"]

                if self.permanent_conditions:
                    self.elements["condition_name"] = pygame_gui.elements.UITextBox(
                        self.permanent_conditions[0].capitalize() if len(self.permanent_conditions) == 1 else f"{len(self.permanent_conditions)} conditions selected",
                        ui_scale(pygame.Rect((300, 470), (200, 34))),
                        object_id=get_text_box_theme("#text_box_30_horizcenter"),
                        manager=MANAGER
                    )

            for condition, button in self.condition_buttons.items():
                checked = condition in self.permanent_conditions or (condition == "None" and not self.permanent_conditions)
                update_checkbox(button, "@checked_checkbox" if checked else "@unchecked_checkbox")
                button.enable()
                if (condition == "None" and not self.permanent_conditions) or (not checked and not self.condition_allowed(condition)):
                    button.disable()
            for i in self.trait_buttons.items():
                if i[0] != self.personality:
                    self.trait_buttons[i[0]].enable()
                else:
                    self.trait_buttons[i[0]].disable()

            if self.current_selection == "trait":
                if "trait_name" in self.elements:
                    self.elements["trait_name"].kill()
                    del self.elements["trait_name"]

                if self.skill:
                    self.elements["trait_name"] = pygame_gui.elements.UITextBox(
                        self.personality.capitalize(),
                        ui_scale(pygame.Rect((276, 470), (247, 49))),
                        object_id=get_text_box_theme("#text_box_30_horizcenter"),
                        manager=MANAGER
                    )

            if self.current_selection == "skill":
                if "skill_name" in self.elements:
                    self.elements["skill_name"].kill()
                    del self.elements["skill_name"]

                if self.skill:
                    skillname = self.skill[0].upper() + self.skill[1:]
                    self.elements["skill_name"] = pygame_gui.elements.UITextBox(
                        skillname,
                        ui_scale(pygame.Rect((276, 470), (247, 49))),
                        object_id=get_text_box_theme("#text_box_30_horizcenter"),
                        manager=MANAGER
                    )

            for i in self.skill_buttons.items():
                if i[0] != self.skill:
                    self.skill_buttons[i[0]].enable()
                else:
                    self.skill_buttons[i[0]].disable()

            for i in self.faith_buttons.items():
                if i[0] != self.faith:
                    self.faith_buttons[i[0]].enable()
                else:
                    self.faith_buttons[i[0]].disable()

            for i in self.sex_buttons.items():
                if i[0] != self.sex:
                    self.sex_buttons[i[0]].enable()
                else:
                    self.sex_buttons[i[0]].disable()

        if self.page == 3 and self.current_selection in ("trait", "skill"):
            selected = {"condition": next(iter(self.permanent_conditions), "None"),
                        "trait": self.personality, "skill": self.skill}[self.current_selection]
            for value, button in getattr(self, self.current_selection + "_buttons").items():
                update_checkbox(button, "@checked_checkbox" if value == selected else "@unchecked_checkbox")
        elif self.page == 4:
            selected = getattr(self, self.current_selection) or "None"
            for value, button in self.detail_buttons.items():
                checked = value == selected
                update_checkbox(button, "@checked_checkbox" if checked else "@unchecked_checkbox")
                if checked:
                    button.disable()
                else:
                    button.enable()

        for i in self.current_selection_buttons.items():
            if self.current_selection != i[0]:
                if i[0] in ["tortie_pattern", "tortie_colour", "tortie_patches"]:
                    if self.tortie_enabled is True:
                        self.current_selection_buttons[i[0]].enable()
                else:
                    self.current_selection_buttons[i[0]].enable()
            else:
                self.current_selection_buttons[i[0]].disable()
        if "next_step" in self.elements:
            self.elements["next_step"].enable()
            before = getattr(self, "initial_customizer_state", {})
            changed = self.permanent_conditions != before.get("permanent_conditions") or self.sex != before.get("sex")
            if changed and any(not self.condition_allowed(name) for name in self.permanent_conditions):
                self.elements["next_step"].disable()
        # filter buttons
        for i in ["default", "alphabetical"]:
            if i in self.elements:
                if i == self.customiser_sort:
                    self.elements[i].disable()
                else:
                    self.elements[i].enable()

    def update_sprite(self):
        # this sucks
        if self.pname in ["Tortie", "Calico"]:
            if self.tortiepattern in ["Singlecolour", "SingleColour", "Twocolour", "TwoColour", "singlecolour", "twocolour"]:
                print("Correcting tortiepattern:", self.tortiepattern, "| Report as LifeGen bug!")
                self.tortiepattern = "single"
            if self.tortiebase in ["Singlecolour", "SingleColour", "Twocolour", "TwoColour", "singlecolour", "twocolour"]:
                print("Correcting tortiebase:", self.tortiebase, "| Report as LifeGen bug!")
                self.tortiebase = "single"
        else:
            if self.pname in ["single", "singlecolour", "Singlecolour"]:
                print("Correcting pname:", self.pname, "| Report as LifeGen bug!")
                self.pname = "SingleColour"

        pelt2 = Pelt(
            name=self.pname,
            length=self.length,
            colour=self.colour,
            white_patches=self.white_patches.copy(),
            eye_color=self.eye_colour,
            eye_colour2=self.eye_colour2,
            tortiebase=self.tortiebase,
            tortiecolour=self.tortiecolour,
            pattern=self.pattern.copy(),
            tortiepattern=self.tortiepattern.lower() if self.tortiepattern else None,
            vitiligo=self.vitiligo,
            points=self.points,
            accessory=None,
            paralyzed=self.paralyzed,
            scars=self.scars,
            tint=self.tint,
            skin=self.skin,
            white_patches_tint=self.white_patches_tint,
            kitten_sprite=self.kitten_sprite,
            adol_sprite=self.adolescent_pose if self.adolescent_pose > 2 else self.adolescent_pose + 3,
            adult_sprite=self.adult_pose if self.adult_pose > 2 else self.adult_pose + 6,
            senior_sprite=self.elder_pose if self.elder_pose > 2 else self.elder_pose + 12,
            reverse=self.reverse,
            accessories=self.accessories,
            inventory=self.inventory.copy(),
            fur_texture=self.fur_texture, build=self.build, height=self.height,
        )


        if self.length == 'long' and self.adult_pose < 9:
            pelt2.cat_sprites['young adult'] = self.adult_pose + 9
            pelt2.cat_sprites['adult'] = self.adult_pose + 9
            pelt2.cat_sprites['senior adult'] = self.adult_pose + 9
        c_moons = 1
        if self.preview_age == "adolescent":
            c_moons = 6
        elif self.preview_age == "adult":
            c_moons = 12
        elif self.preview_age == "elder":
            c_moons = 121
        custom_sprite = self.refresh_preview(pelt2, c_moons)
        self.elements['sprite'].kill()
        self.elements["sprite"] = UISpriteButton(ui_scale(pygame.Rect
                                         ((315, 160), (175, 175))),
                                   custom_sprite,
                                   self.custom_cat.ID,
                                   starting_height=0, manager=MANAGER)

    def build_customizer_footer(self):
        self.elements["previous_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((253, 645), (147, 30))),
            get_arrow(1, arrow_left=True) + " Previous Step",
            get_button_dict(ButtonStyles.MENU_LEFT, (147, 30)),
            object_id="@buttonstyles_menu_left",
            manager=MANAGER,
            starting_height=2
        )
        self.elements["next_step"] = UISurfaceImageButton(
            ui_scale(pygame.Rect((0, 645), (147, 30))),
            "Next Step " + get_arrow(3, arrow_left=False),
            get_button_dict(ButtonStyles.MENU_RIGHT, (147, 30)),
            object_id="@buttonstyles_menu_right",
            manager=MANAGER,
            starting_height=2,
            anchors={"left_target": self.elements["previous_step"]},
        )


    def customizer_description(self, value):
        if self.current_selection == "backstory":
            if value == "Random":
                return "Start as a newborn with a random origin and a matching family. All new-colony characters begin life as newborns."
            cat = getattr(self, "the_cat", None)
            name = str(cat.name) if cat else "Your cat"
            pronouns = cat.pronouns[0] if cat else Cat.default_pronouns[{"male": 2, "female": 1, "intersex": 0}[self.sex]]
            clan_name = getattr(self, "clan_name", "") or (game.clan.name if game.clan else "the colony")
            return process_text(BACKSTORIES["backstories"][value], {
                "m_c": (name, pronouns), "r_c": ("another cat", Cat.default_pronouns[0]),
                "o_c_n": ("another colony", Cat.default_pronouns[0]), "c_n": (clan_name, Cat.default_pronouns[0]),
            })
        if self.current_selection == "trait":
            cat = getattr(self, "the_cat", None)
            group = "kit_traits" if cat is None or cat.personality.kit else "normal_traits"
            ranges = Personality.trait_ranges[group][value]
            return value.capitalize() + "<br>Personality ranges (0-16):<br>" + "<br>".join(
                f"{facet.capitalize()}: {bounds[0]}-{bounds[1]}" for facet, bounds in ranges.items())
        return value.replace("_", " ").capitalize()

    def build_details_page(self):
        categories = ["secondary_skill"] + list(self.details_options)
        if self.current_selection not in categories:
            self.current_selection = categories[0]
        self.detail_buttons = {}
        for index, category in enumerate(categories):
            self.current_selection_buttons[category] = UISurfaceImageButton(
                ui_scale(pygame.Rect((120, 100 + index * 50), (120, 40))), category.replace("_", " "),
                get_button_dict(ButtonStyles.ROUNDED_RECT, (120, 40)), object_id="@buttonstyles_rounded_rect", manager=MANAGER)
        options = ["None"] + self.skills[1:] if self.current_selection == "secondary_skill" else self.details_options[self.current_selection]
        container = CustomizerList(pygame.Rect((550, 85), (175, 480)), options,
                                  lambda value: value.replace("_", " ").capitalize(), self.detail_buttons, self.customizer_description)
        self.elements["details"] = container
        container.on_change = self.update_disabled_buttons
        selected = getattr(self, self.current_selection) or "None"
        if selected in options:
            container.scroll_to(selected)
        for key, text, y in (("heal", "Heal", 470), ("reset_facets", "Reset Facets", 515)):
            self.elements[key] = UISurfaceImageButton(ui_scale(pygame.Rect((335, y), (130, 34))), text,
                get_button_dict(ButtonStyles.SQUOVAL, (130, 34)), object_id="@buttonstyles_squoval", manager=MANAGER)
        if not getattr(self, "the_cat", None) or not (self.the_cat.illnesses or self.the_cat.injuries):
            self.elements["heal"].disable()

    def handle_details_event(self, event):
        if event.ui_element == self.elements["heal"]:
            self.healed = True
            return True
        if event.ui_element == self.elements["reset_facets"]:
            self.facet_reset = True
            return True
        options = ["None"] + self.skills[1:] if self.current_selection == "secondary_skill" else self.details_options[self.current_selection]
        if event.ui_element == self.elements["randomise_selection"]:
            setattr(self, self.current_selection, choice(options))
            self.open_customize_cat()
            return True
        if event.ui_element in (self.elements["cycle_left"], self.elements["cycle_right"]):
            direction = -1 if event.ui_element == self.elements["cycle_left"] else 1
            value = getattr(self, self.current_selection)
            index = options.index(value) if value in options else 0
            setattr(self, self.current_selection, options[(index + direction) % len(options)])
            self.open_customize_cat()
            return True
        for value, button in self.detail_buttons.items():
            if event.ui_element == button:
                setattr(self, self.current_selection, value)
                self.open_customize_cat()
                return True
        return False

    def refresh_preview(self, pelt, moons):
        if self.custom_cat is None:
            self.custom_cat = Cat(moons=moons, pelt=pelt, gender=self.sex, loading_cat=True, register=False)
        else:
            self.custom_cat.pelt = pelt
            self.custom_cat.moons = moons
            self.custom_cat.gender = self.sex
        return generate_sprite(self.custom_cat)

    def accessory_options(self):
        options = self.elements["appearance_editor"].option_list.options
        return [item for item in options if item != "None"
                and not (("NOTAIL" in self.scars or "HALFTAIL" in self.scars) and item in self.notail_accs)
                and not ("NOPAW" in self.scars and item in self.noleg_accs)]

    def set_customizer_conditions(self, conditions):
        previous = set(self.permanent_conditions)
        self.permanent_conditions = list(dict.fromkeys(conditions))
        selected = set(self.permanent_conditions)
        self.paralyzed = "paralyzed" in selected
        anatomy = {"born without a leg": "NOPAW", "lost a leg": "NOPAW",
                   "born without a tail": "NOTAIL", "lost their tail": "NOTAIL"}
        retained_scars = {scar for name, scar in anatomy.items() if name in selected}
        for name, scar in anatomy.items():
            if name in previous - selected and scar not in retained_scars and scar in self.scars:
                self.scars.remove(scar)
        for name, scar in anatomy.items():
            if name in selected - previous and scar not in self.scars:
                self.scars.append(scar)
        for name, scars in (("blind", ("BOTHBLIND",)), ("one bad eye", ("LEFTBLIND", "RIGHTBLIND", "BRIGHTHEART"))):
            if name in previous - selected:
                self.scars = [scar for scar in self.scars if scar not in scars]
        invalid_accessories = set()
        if "NOTAIL" in self.scars or "HALFTAIL" in self.scars:
            invalid_accessories.update(self.notail_accs)
        if "NOPAW" in self.scars:
            invalid_accessories.update(self.noleg_accs)
        self.accessories = [item for item in self.accessories if item not in invalid_accessories]
        self.inventory = [item for item in self.inventory if item not in invalid_accessories]

    def set_customizer_scars(self, scars):
        previous = set(self.scars)
        self.scars = list(dict.fromkeys(scars))
        conditions = self.permanent_conditions.copy()
        for scar_group, names in ((("NOPAW",), ("born without a leg", "lost a leg")),
                                  (("NOTAIL",), ("born without a tail", "lost their tail")),
                                  (("BOTHBLIND",), ("blind",)),
                                  (("LEFTBLIND", "RIGHTBLIND", "BRIGHTHEART"), ("one bad eye",))):
            if any(scar in self.scars for scar in scar_group):
                if not any(name in conditions for name in names):
                    conditions.append(names[0])
            elif any(scar in previous for scar in scar_group):
                conditions = [name for name in conditions if name not in names]
        self.set_customizer_conditions(conditions)

    def condition_allowed(self, name, conditions=None):
        if name == "None":
            return True
        if name in self.sex_specific_conditions and self.sex != "intersex":
            return False
        selected = set(self.permanent_conditions if conditions is None else conditions)
        selected.add(name)
        return not ({"blind", "failing eyesight"} <= selected or {"deaf", "partial hearing loss"} <= selected)
