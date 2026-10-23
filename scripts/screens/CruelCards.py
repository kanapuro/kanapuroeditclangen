# Card interaction adapted from ClanGen/LifeGen UICruelCardLarge (MPL-2.0).
# Pinned source and CC BY-NC 4.0 artwork provenance: resources/dicts/cruel_season.json.
import pygame
import pygame_gui

from scripts.game_structure.ui_elements import GameWindow as CruelCardsWindow
from scripts.clan_resources.cruel_season import CARDS, CARD_DATA, validate_cards
from scripts.game_structure import image_cache
from scripts.game_structure.screen_settings import MANAGER
from scripts.game_structure.ui_elements import UISurfaceImageButton, UIImageButton, UITextBoxTweaked
from scripts.ui.generate_box import BoxStyles, get_box
from scripts.ui.generate_button import ButtonStyles, get_button_dict
from scripts.utility import ui_scale, ui_scale_dimensions


class CruelCard(pygame_gui.elements.UIImage):
    def __init__(self, position, name, container=None, size=(230, 360), lift=50,
                 interval=None, layer_count=1, starting_height=1, anchors=None):
        self.name = name
        self.start_position = ui_scale_dimensions(position)
        self.lift = ui_scale_dimensions((0, lift))[1]
        self.interval = ui_scale_dimensions((interval, 0))[0] if interval else None
        self.layer_count = layer_count
        super().__init__(ui_scale(pygame.Rect(position, size)),
            pygame.transform.scale(image_cache.load_image(
                "resources/images/cruel_cards/" + CARDS[name]["card_art"]), ui_scale_dimensions(size)),
            container=container, manager=MANAGER, starting_height=starting_height, anchors=anchors)

    def on_hovered(self):
        self.set_relative_position((self.start_position[0], self.start_position[1] - self.lift))
        self.change_layer(self.starting_height + self.layer_count)
        self.ui_container.get_container().recalculate_container_layer_thickness()
        pygame.event.post(pygame.event.Event(pygame_gui.UI_BUTTON_ON_HOVERED, ui_element=self))
        super().on_hovered()

    def on_unhovered(self):
        self.set_relative_position(self.start_position)
        self.change_layer(self.starting_height)
        self.ui_container.get_container().recalculate_container_layer_thickness()
        super().on_unhovered()

    def hover_point(self, x, y):
        rect = self.rect.copy()
        if self.hovered:
            rect.height += self.lift
            if self.interval:
                rect.width = self.interval
        return rect.collidepoint(x, y) and self.ui_container.get_container().rect.collidepoint(x, y)

    def process_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_LEFT:
            point = self.ui_manager.calculate_scaled_mouse_position(event.pos)
            if self.is_enabled and self.hover_point(*point):
                pygame.event.post(pygame.event.Event(pygame_gui.UI_BUTTON_START_PRESS, ui_element=self))
                return True
        return False


class CruelCardIcon(UIImageButton):
    def __init__(self, position, name, container=None, anchors=None):
        self.name = name
        category = CARDS[name]["category"].lower()
        # LifeGen groups cards outside its three named categories under Environment.
        if category not in ("danger", "origin", "behavior"):
            category = "environment"
        super().__init__(ui_scale(pygame.Rect(position, (26, 38))), "",
            object_id="#card_icon_" + category, container=container, manager=MANAGER, anchors=anchors)

    def on_hovered(self):
        pygame.event.post(pygame.event.Event(pygame_gui.UI_BUTTON_ON_HOVERED, ui_element=self))
        super().on_hovered()


class ViewCruelCards(CruelCardsWindow):
    def __init__(self):
        super().__init__((160, 95, 480, 510))
        from scripts.game_structure.game_essentials import game
        self.cards = list(game.clan.cruel_cards or [])
        self.card_buttons = {}
        self.art = None
        icons = pygame_gui.elements.UIAutoResizingContainer(ui_scale(pygame.Rect((40, 50), (0, 0))),
            container=self, manager=MANAGER, resize_top=False, resize_left=False)
        left = top = None
        for i, name in enumerate(self.cards, 1):
            anchors = {}
            if left:
                anchors["left_target"] = left
            if top:
                anchors["top_target"] = top
            icon = CruelCardIcon((5 if left else 0, 5 if top else 0), name, container=icons, anchors=anchors)
            self.card_buttons[name] = icon
            if i % 3 == 0:
                left, top = None, icon
            else:
                left = icon
        self.info = pygame_gui.core.UIContainer(ui_scale(pygame.Rect((25, 30), (300, 500))),
            container=self, anchors={"left_target": icons}, manager=MANAGER)
        self.title = pygame_gui.elements.UITextBox("", ui_scale(pygame.Rect((0, 360), (300, -1))),
            container=self.info, manager=MANAGER, object_id="#text_box_30_horizcenter")
        self.description = UITextBoxTweaked("", ui_scale(pygame.Rect((0, 0), (300, 70))),
            container=self.info, manager=MANAGER, object_id="#text_box_22_horizcenter_spacing_95",
            line_spacing=0.95, anchors={"top_target": self.title})
        if self.cards:
            self.show_card(self.cards[0])
        else:
            self.description.set_text("This colony uses the original Cruel Season rules, without a card deck."
                if game.clan.cruel_cards is None else "No Cruel Season cards are active.")

    def show_card(self, name):
        if self.art:
            self.art.kill()
        self.art = pygame_gui.elements.UIImage(ui_scale(pygame.Rect((0, 0), (230, 360))),
            pygame.transform.scale(image_cache.load_image("resources/images/cruel_cards/" + CARDS[name]["card_art"]),
                                   ui_scale_dimensions((230, 360))), container=self.info, manager=MANAGER,
            anchors={"centerx": "centerx"})
        self.title.set_text(CARDS[name]["name"])
        self.description.set_text(CARDS[name]["description"])

    def process_event(self, event):
        handled = super().process_event(event)
        if event.type in (pygame_gui.UI_BUTTON_ON_HOVERED, pygame_gui.UI_BUTTON_START_PRESS):
            for name, button in self.card_buttons.items():
                if event.ui_element == button:
                    self.show_card(name)
                    return True
        return handled


class DeckListWindow(CruelCardsWindow):
    def __init__(self, cards, apply_deck):
        super().__init__((180, 190, 440, 330))
        self.apply_deck = apply_deck
        text = UITextBoxTweaked("Input a list of desired card IDs, separated by a comma. This replaces the chosen deck.",
            ui_scale(pygame.Rect((0, 20), (380, -1))), container=self, manager=MANAGER,
            object_id="#text_box_30_horizcenter", anchors={"centerx": "centerx"})
        self.entry = pygame_gui.elements.UITextEntryBox(ui_scale(pygame.Rect((0, 10), (350, 150))),
            initial_text=", ".join(cards), container=self, manager=MANAGER,
            anchors={"centerx": "centerx", "top_target": text}, object_id="text_entry_line")
        self.error = UITextBoxTweaked("", ui_scale(pygame.Rect((0, -5), (380, 50))),
            container=self, manager=MANAGER, object_id="#text_box_22_horizcenter_spacing_95",
            anchors={"centerx": "centerx", "top_target": self.entry}, line_spacing=0.95)
        self.apply = UISurfaceImageButton(ui_scale(pygame.Rect((0, 50), (100, 30))), "Confirm",
            get_button_dict(ButtonStyles.SQUOVAL, (100, 30)), object_id="@buttonstyles_squoval",
            container=self, manager=MANAGER, anchors={"centerx": "centerx", "top_target": self.entry})

    def process_event(self, event):
        handled = super().process_event(event)
        if event.type == pygame_gui.UI_BUTTON_START_PRESS and event.ui_element == self.apply:
            cards = [value.strip() for value in self.entry.get_text().split(",") if value.strip()]
            try:
                self.apply_deck(validate_cards(cards))
            except ValueError as error:
                self.error.set_text(str(error))
            else:
                self.kill()
            return True
        return handled


class CruelCardConflicts(CruelCardsWindow):
    # Choices adapted from ClanGen 904012b9e9c62ab24a8988ae23d8a516232ff7e2 (MPL-2.0).
    def __init__(self, new_card, chosen_cards, apply_deck):
        self.conflicting_cards = [card for card in chosen_cards if any(
            card in group and new_card in group for group in CARD_DATA["conflicts"].values())]
        self.cards = validate_cards([card for card in chosen_cards if card not in self.conflicting_cards] + [new_card])
        self.apply_deck = apply_deck
        super().__init__((200, 240, 400, 220))
        names = ", ".join(CARDS[card]["name"] for card in self.conflicting_cards)
        self.message = UITextBoxTweaked(
            f"{CARDS[new_card]['name']} cannot be combined with {names}.<br><br>Keep your current cards, or replace the conflicting cards?",
            ui_scale(pygame.Rect((20, 20), (360, 115))), container=self, manager=MANAGER,
            object_id="#text_box_26_horizcenter",
        )
        self.keep_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((40, 160), (150, 30))), "Keep cards",
            get_button_dict(ButtonStyles.SQUOVAL, (150, 30)), object_id="@buttonstyles_squoval",
            container=self, manager=MANAGER,
        )
        self.replace_button = UISurfaceImageButton(
            ui_scale(pygame.Rect((210, 160), (150, 30))), "Replace cards",
            get_button_dict(ButtonStyles.SQUOVAL, (150, 30)), object_id="@buttonstyles_squoval",
            container=self, manager=MANAGER,
        )

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_START_PRESS:
            if event.ui_element == self.keep_button:
                self.kill()
                return True
            if event.ui_element == self.replace_button:
                self.apply_deck(self.cards)
                self.kill()
                return True
        return super().process_event(event)
