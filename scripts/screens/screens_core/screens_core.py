from math import ceil
from typing import Optional, Tuple
from random import randint

import pygame
import pygame_gui
from pygame_gui.core import ObjectID

import scripts.game_structure.screen_settings
from scripts.game_structure import image_cache
from scripts.game_structure.game_essentials import game
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.ui_elements import UISurfaceImageButton, UIImageButton, UIDropDownContainer, UIModifiedImage
from scripts.housekeeping.version import get_version_info
from scripts.ui.generate_box import get_box, BoxStyles
from scripts.ui.generate_button import get_button_dict, ButtonStyles
from scripts.ui.get_arrow import get_arrow
from scripts.ui.icon import Icon
from scripts.utility import (
    ui_scale,
    ui_scale_offset,
    ui_scale_dimensions,
    ui_scale_blit,
    get_text_box_theme,
    ui_scale_value,
)

game_frame: Optional[pygame.Surface] = None
core_vignette = pygame.image.load("resources/images/vignette.png")
vignette: Optional[pygame.Surface] = None
dropshadow: Optional[pygame.Surface] = None
fade: Optional[pygame.Surface] = None

menu_buttons = dict()
menu_dropdowns = {}
menu_mode = None
moon_phase = None
moon_age = None
moon_clan = None
moon_frames = []
moon_frame_time = 0.0

default_game_bgs = None
default_fullscreen_bgs = None

version_number = None
dev_watermark = None


def rebuild_core(*, should_rebuild_bgs=True):
    global menu_buttons
    global default_game_bgs
    global default_fullscreen_bgs
    global version_number
    global dev_watermark

    global menu_dropdowns, menu_mode
    for button in menu_buttons.values():
        button.kill()
    for dropdown in menu_dropdowns.values():
        dropdown.child_button_container.kill()
        dropdown.kill()
    for label in (version_number, dev_watermark):
        if label is not None:
            label.kill()
    menu_buttons = {}
    menu_dropdowns = {}
    menu_mode = game.clan.game_mode if game.clan else None
    x = 258 if menu_mode == "classic" else 214
    for key, text, width, style in (
        ("events_screen", "Events", 82, ButtonStyles.MENU_LEFT),
        ("supplies", "Supplies", 88, ButtonStyles.MENU_MIDDLE),
        ("catlist_screen", "Cats", 58, ButtonStyles.MENU_MIDDLE),
        ("dens", "Dens", 58, ButtonStyles.MENU_MIDDLE),
        ("patrol_screen", "Patrol", 86, ButtonStyles.MENU_RIGHT),
    ):
        menu_buttons[key] = UISurfaceImageButton(
            ui_scale(pygame.Rect((x, 60), (width, 30))), text,
            get_button_dict(style, (width, 30)), visible=False, manager=MANAGER,
            object_id=ObjectID("#events_button", "@buttonstyles_menu_left") if key == "events_screen"
            else ("#patrol_button" if key == "patrol_screen" else "@buttonstyles_" + style.value),
            starting_height=6)
        if key != "supplies" or menu_mode != "classic":
            x += width
    for key, text, rect in (
        ("main_menu", get_arrow(3) + " Main Menu", (25, 25, 153, 30)),
        ("camp_screen", "Back to Camp", (25, 60, 123, 30)),
    ):
        menu_buttons[key] = UISurfaceImageButton(ui_scale(pygame.Rect(rect)), text,
            get_button_dict(ButtonStyles.SQUOVAL, rect[2:]), visible=False, manager=MANAGER,
            object_id="@buttonstyles_squoval", starting_height=5)
    font = MANAGER.get_theme().get_font(["@buttonstyles_squoval"])
    for key, text, y in (("allegiances", "Allegiances", 25), ("clan_settings", "Colony Settings", 60)):
        width = ceil(font.get_rect(text).width / scripts.game_structure.screen_settings.screen_scale) + 20
        rect = ui_scale(pygame.Rect((0, 0), (width, 30)))
        rect.topright = ui_scale_offset((-25, y))
        menu_buttons[key] = UISurfaceImageButton(rect, text,
            get_button_dict(ButtonStyles.SQUOVAL, (width, 30)), visible=False, manager=MANAGER,
            object_id="@buttonstyles_squoval", starting_height=5,
            anchors={"top": "top", "right": "right"})
    heading_rect = ui_scale(pygame.Rect((0, 0), (220, 35)))
    heading_rect.bottomleft = ui_scale_offset((0, 0))
    menu_buttons["heading"] = UISurfaceImageButton(heading_rect, "",
        get_button_dict(ButtonStyles.CLAN_HEADER, (220, 35)), visible=False, manager=MANAGER,
        object_id="@buttonstyles_clan_header", starting_height=5,
        anchors={"bottom": "bottom", "bottom_target": menu_buttons["patrol_screen"], "centerx": "centerx"},
        tool_tip_text="Return to camp")
    menu_buttons["heading"].full_text = ""
    for key, width, children in (
        ("supplies", 88, (("freshkill", "Fresh-kill"), ("herbs", "Herbs"))),
        ("dens", 58, (("lead_den", "Leader's den"), ("med_cat_den", "Medicine cat den"),
                       ("warrior_den", "Warriors' den"), ("clearing", "Clearing"))),
    ):
        parent = menu_buttons[key]
        child_width = 150 if key == "dens" else width
        container = pygame_gui.core.UIContainer(
            ui_scale(pygame.Rect((-(width + child_width) // 2, 0), (child_width, len(children) * 28 + 2))),
            anchors={"left_target": parent, "top_target": parent},
            manager=MANAGER, starting_height=20, visible=False)
        for i, (child, text) in enumerate(children):
            menu_buttons[child] = UISurfaceImageButton(
                ui_scale(pygame.Rect((0, i * 28), (child_width, 30))), text,
                get_button_dict(ButtonStyles.DROPDOWN, (child_width, 30)),
                object_id="@buttonstyles_dropdown", container=container, manager=MANAGER)
        menu_dropdowns[key] = UIDropDownContainer(pygame.Rect(0, 0, 0, 0), container=None,
            object_id="#navigation_dropdown", starting_height=6, parent_button=parent,
            child_button_container=container, manager=MANAGER, visible=True, open_on_hover=True)
        menu_dropdowns[key].close()
    rebuild_moon_n_season_indicator()

    rebuild_mute("default")

    version_text = get_version_info().version_number
    if "+" in version_text:
        label, commit = version_text.split("+", 1)
        version_text = label + "+" + commit[:8]
    else:
        version_text = version_text if version_text.startswith("v") else version_text[:8]
    version_number = pygame_gui.elements.UILabel(
        ui_scale(pygame.Rect((50, 50), (-1, -1))),
        version_text,
        object_id=get_text_box_theme(),
        anchors={"bottom": "bottom", "right": "right"},
    )
    # Adjust position
    version_number.set_relative_position(
        ui_scale_offset(
            (
                800 - version_number.get_relative_rect()[2],
                700 - version_number.get_relative_rect()[3],
            )
        )
    )

    if get_version_info().is_source_build or get_version_info().is_dev():
        dev_watermark = pygame_gui.elements.UILabel(
            ui_scale(pygame.Rect((545, 660), (-1 if "+" in version_text else 300, 50))),
            "Build: " + version_number.text,
            object_id="#dev_watermark",
        )
        if "+" in version_text:
            watermark_rect = dev_watermark.get_relative_rect()
            right = MANAGER.get_root_container().get_rect().width - ui_scale_dimensions((20, 0))[0]
            dev_watermark.set_relative_position((right - watermark_rect.width, watermark_rect.y))
        version_number.kill()
        version_number = None

    if should_rebuild_bgs:
        rebuild_bgs()


class MoonPhaseImage(pygame_gui.elements.UIImage):
    def update(self, time_delta):
        global moon_phase, moon_frame_time
        super().update(time_delta)
        if not moon_frames:
            return
        moon_frame_time += time_delta
        while moon_frames and moon_frame_time >= 0.125:
            moon_frame_time -= 0.125
            moon_phase = moon_frames.pop(0)
            self.set_image(pygame.transform.scale(
                image_cache.load_image(f"resources/images/moon_phase{moon_phase}.png"),
                ui_scale_dimensions((22, 26))))


def rebuild_moon_n_season_indicator():
    global moon_phase, moon_age, moon_clan, moon_frames, moon_frame_time
    clan = game.clan
    age = clan.age if clan else 0
    season = clan.current_season.casefold().replace("-", "") if clan else "newleaf"
    if moon_phase is None or moon_clan is not clan or age < moon_age:
        moon_phase = randint(0, 7)
        moon_frames = []
        moon_frame_time = 0.0
    elif age > moon_age:
        # LifeGen's five-to-eight-frame cycle, advanced on the UI thread.
        moon_frames = [(moon_phase + i) % 8 for i in range(5 + randint(0, 3))]
        moon_frame_time = 0.0
    moon_clan = clan
    moon_age = age
    for key in ("moon_indicator", "season_indicator"):
        if key in menu_buttons:
            menu_buttons[key].kill()
    rect = ui_scale(pygame.Rect((0, 0), (22, 26)))
    rect.bottomright = ui_scale_offset((0, 2))
    menu_buttons["moon_indicator"] = MoonPhaseImage(rect,
        pygame.transform.scale(image_cache.load_image(f"resources/images/moon_phase{moon_phase}.png"), ui_scale_dimensions((22, 26))),
        visible=False, manager=MANAGER, starting_height=4,
        anchors={"right_target": menu_buttons["heading"], "right": "right",
                 "bottom_target": menu_buttons["events_screen"], "bottom": "bottom"})
    menu_buttons["moon_indicator"].set_tooltip(f"{age} {'moon' if age == 1 else 'moons'}")
    menu_buttons["moon_indicator"].tool_tip_delay = 0
    menu_buttons["season_indicator"] = UIModifiedImage(
        ui_scale(pygame.Rect((404, 3), (144, 67))),
        pygame.transform.scale(image_cache.load_image(f"resources/images/season_{season}.png"), ui_scale_dimensions((144, 67))),
        visible=False, manager=MANAGER, starting_height=5)
    menu_buttons["season_indicator"].disable()


def rebuild_mute(location: str):
    if "mute_button" in menu_buttons:
        menu_buttons["mute_button"].kill()
        menu_buttons["unmute_button"].kill()

    mute_pos = ui_scale(pygame.Rect((0, 0), (34, 34)))

    if location in ["bottomright", "default"]:
        mute_pos.bottomright = ui_scale_offset((-25, -25))
        anchors = {"bottom": "bottom", "right": "right"}
    elif location == "topright":
        mute_pos.topright = ui_scale_offset((-25, 25))
        anchors = {"top": "top", "right": "right"}
    elif location == "bottomleft":
        mute_pos.bottomleft = ui_scale_offset((25, -25))
        anchors = {"bottom": "bottom", "left": "left"}
    elif location == "topleft":
        mute_pos.topleft = ui_scale_offset((25, 25))
        anchors = {"top": "top", "left": "left"}
    else:
        return

    menu_buttons["mute_button"] = UISurfaceImageButton(
        mute_pos,
        Icon.SPEAKER,
        get_button_dict(ButtonStyles.ICON, (34, 34)),
        visible=False,
        manager=MANAGER,
        object_id="@buttonstyles_icon",
        starting_height=6,
        anchors=anchors,
    )

    menu_buttons["unmute_button"] = UISurfaceImageButton(
        mute_pos,
        Icon.MUTE,
        get_button_dict(ButtonStyles.ICON, (34, 34)),
        visible=False,
        manager=MANAGER,
        object_id="@buttonstyles_icon",
        starting_height=6,
        anchors=anchors,
    )


def rebuild_bgs():
    global default_fullscreen_bgs
    global default_game_bgs
    global game_frame
    global vignette
    global dropshadow
    global fade

    if (
        vignette is None
        or scripts.game_structure.screen_settings.screen.get_size()
        != vignette.get_size()
    ):
        game_frame = get_box(
            BoxStyles.FRAME,
            (820, 720),
        )

        vignette = pygame.transform.scale(
            core_vignette, scripts.game_structure.screen_settings.screen.get_size()
        ).convert_alpha()

        dropshadow = pygame.Surface(
            scripts.game_structure.screen_settings.screen.get_size(),
            flags=pygame.SRCALPHA,
        )

        fade = pygame.Surface(scripts.game_structure.screen_settings.screen.get_size())
        fade.fill(pygame.Color(113, 113, 111))  # middle grey

        game_box = pygame.Surface(
            (
                scripts.game_structure.screen_settings.screen_x + ui_scale_value(30),
                scripts.game_structure.screen_settings.screen_y + ui_scale_value(30),
            ),
            pygame.SRCALPHA,
        )
        feather_surface(game_box, 15)
        dropshadow.blit(game_box, ui_scale_blit((-15, -15)))
        del game_box

    bg = pygame.Surface(scripts.game_structure.screen_settings.game_screen_size)
    bg.fill(game.config["theme"]["light_mode_background"])
    bg_dark = pygame.Surface(scripts.game_structure.screen_settings.game_screen_size)
    bg_dark.fill(game.config["theme"]["dark_mode_background"])

    default_game_bgs = {
        "light": {"default": bg},
        "dark": {"default": bg_dark},
    }

    temp_screen_size = scripts.game_structure.screen_settings.screen.get_size()

    default_fullscreen_bgs = {
        "light": {
            "default": pygame.transform.scale(bg, temp_screen_size),
            "mainmenu_bg": pygame.transform.scale(
                pygame.image.load("resources/images/menu_logoless.png").convert(),
                temp_screen_size,
            ),
            "starclan": pygame.transform.scale(
                pygame.image.load("resources/images/starclanbg.png").convert_alpha(),
                temp_screen_size,
            ),
            "darkforest": pygame.transform.scale(
                pygame.image.load("resources/images/darkforestbg.png").convert_alpha(),
                temp_screen_size,
            ),
            "unknown_residence": pygame.transform.scale(
                pygame.image.load("resources/images/urbg.png").convert(),
                temp_screen_size,
            ),
        },
        "dark": {
            "default": pygame.transform.scale(bg_dark, temp_screen_size),
            "mainmenu_bg": pygame.transform.scale(
                pygame.image.load("resources/images/menu_logoless.png").convert(),
                temp_screen_size,
            ),
            "starclan": pygame.transform.scale(
                pygame.image.load("resources/images/starclanbg.png").convert_alpha(),
                temp_screen_size,
            ),
            "darkforest": pygame.transform.scale(
                pygame.image.load("resources/images/darkforestbg.png").convert_alpha(),
                temp_screen_size,
            ),
            "unknown_residence": pygame.transform.scale(
                pygame.image.load("resources/images/urbg.png").convert(),
                temp_screen_size,
            ),
        },
    }

    for theme in ["light", "dark"]:
        for name, bg in default_fullscreen_bgs[theme].items():
            if name not in [
                "default",
                "mainmenu_bg",
                "darkforest",
                "unknown_residence",
                "starclan",
            ]:
                default_fullscreen_bgs[theme][name] = process_blur_bg(
                    default_fullscreen_bgs[theme][name], theme=theme
                )
            elif name == "default":
                default_fullscreen_bgs[theme][name] = process_blur_bg(
                    default_fullscreen_bgs[theme][name],
                    theme=theme,
                    vignette_strength=0,
                    fade_color=None,
                )
            elif name in ["mainmenu_bg", "darkforest", "unknown_residence"]:
                default_fullscreen_bgs[theme][name] = process_blur_bg(
                    default_fullscreen_bgs[theme][name], theme=theme, blur_radius=10
                )
            elif name == "starclan":
                default_fullscreen_bgs[theme][name] = process_blur_bg(
                    default_fullscreen_bgs[theme][name], theme=theme, blur_radius=2
                )

    camp_bgs = get_camp_bgs()

    for theme in ["light", "dark"]:
        for name, camp_bg in camp_bgs[theme].items():
            default_fullscreen_bgs[theme][name] = process_blur_bg(camp_bg, theme=theme)


def get_camp_bgs():
    camp_bg_base_dir = "resources/images/camp_bg/"
    leaves = ["newleaf", "greenleaf", "leafbare", "leaffall"]
    available_biome = ["forest", "mountainous", "plains", "beach"]

    try:
        camp_nr = game.clan.camp_bg
        biome = game.clan.biome.lower()
    except AttributeError:
        camp_nr = "camp1"
        biome = available_biome[0]

    all_backgrounds = []
    for light_dark in ["light", "dark"]:
        for leaf in leaves:
            platform_dir = (
                f"{camp_bg_base_dir}/{biome}/{leaf}_{camp_nr}_{light_dark}.png"
            )
            all_backgrounds.append(platform_dir)

    return {
        "light": {
            "Newleaf": pygame.transform.scale(
                pygame.image.load(all_backgrounds[0]).convert(),
                scripts.game_structure.screen_settings.screen.get_size(),
            ),
            "Greenleaf": pygame.transform.scale(
                pygame.image.load(all_backgrounds[1]).convert(),
                scripts.game_structure.screen_settings.screen.get_size(),
            ),
            "Leaf-bare": pygame.transform.scale(
                pygame.image.load(all_backgrounds[2]).convert(),
                scripts.game_structure.screen_settings.screen.get_size(),
            ),
            "Leaf-fall": pygame.transform.scale(
                pygame.image.load(all_backgrounds[3]).convert(),
                scripts.game_structure.screen_settings.screen.get_size(),
            ),
        },
        "dark": {
            "Newleaf": pygame.transform.scale(
                pygame.image.load(all_backgrounds[4]).convert(),
                scripts.game_structure.screen_settings.screen.get_size(),
            ),
            "Greenleaf": pygame.transform.scale(
                pygame.image.load(all_backgrounds[5]).convert(),
                scripts.game_structure.screen_settings.screen.get_size(),
            ),
            "Leaf-bare": pygame.transform.scale(
                pygame.image.load(all_backgrounds[6]).convert(),
                scripts.game_structure.screen_settings.screen.get_size(),
            ),
            "Leaf-fall": pygame.transform.scale(
                pygame.image.load(all_backgrounds[7]).convert(),
                scripts.game_structure.screen_settings.screen.get_size(),
            ),
        },
    }


def process_blur_bg(
    bg,
    theme: str = None,
    blur_radius: Optional[int] = 5,
    vignette_strength: Optional[int] = None,
    fade_color: Optional[Tuple[int, int, int]] = None,
) -> pygame.Surface:
    global vignette
    global fade
    global dropshadow
    if theme is None:
        theme = "dark" if game.settings["dark mode"] else "light"

    fade.fill(game.config["theme"]["fullscreen_background"][theme]["fade_color"])
    vignette.set_alpha(
        game.config["theme"]["fullscreen_background"][theme]["vignette_alpha"]
    )
    dropshadow.set_alpha(
        game.config["theme"]["fullscreen_background"][theme]["dropshadow_alpha"]
    )

    if vignette_strength is not None:
        vignette.set_alpha(vignette_strength)

    bg = pygame.transform.scale(
        bg, scripts.game_structure.screen_settings.screen.get_size()
    ).convert_alpha()

    if blur_radius is not None:
        bg = pygame.transform.box_blur(bg, blur_radius)

    bg.blits(
        (
            (fade, (0, 0), None, pygame.BLEND_MULT),
            (vignette, (0, 0), None),
            (dropshadow, (0, 0), None),
            (game_frame, ui_scale_blit((-10, -10))),
        )
    )

    return bg


def feather_surface(surface, feather_width):
    """
    Run a per-pixel effect to make a fun fade-to-transparent border
    :param surface: The surface to add a feathered edge to
    :param feather_width: How fat to make the edge
    :return: None
    """
    width, height = surface.get_size()
    for x in range(width):
        for y in range(height):
            distance = min(x, y, width - x - 1, height - y - 1)
            if distance < feather_width:
                alpha = int(255 * (distance / feather_width))
                surface.set_at((x, y), (0, 0, 0, alpha))


rebuild_core()
