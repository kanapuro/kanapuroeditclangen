"""Cruel Season card definitions adapted from ClanGen and LifeGen.

Source revisions and adaptation notes are recorded in resources/dicts/cruel_season.json.
"""
from copy import deepcopy
import json


with open("resources/dicts/cruel_season.json", encoding="utf-8") as card_file:
    CARD_DATA = json.load(card_file)
CARDS = CARD_DATA["cards"]


def validate_cards(cards):
    if not isinstance(cards, list) or any(not isinstance(card, str) for card in cards):
        raise ValueError("Cruel Season cards must be a list of card IDs.")
    if len(cards) != len(set(cards)):
        raise ValueError("A Cruel Season card cannot be selected twice.")
    unknown = [card for card in cards if card not in CARDS]
    if unknown:
        raise ValueError("Unsupported Cruel Season cards: " + ", ".join(unknown))
    if len(cards) > CARD_DATA["limit"]:
        raise ValueError(f"Choose at most {CARD_DATA['limit']} Cruel Season cards.")
    for group in CARD_DATA["conflicts"].values():
        conflicts = [card for card in cards if card in group]
        if len(conflicts) > 1:
            raise ValueError("Conflicting cards: " + ", ".join(CARDS[card]["name"] for card in conflicts))
    return cards.copy()


def apply_modifiers(cards, keys, default):
    value = deepcopy(default)
    for card in cards or []:
        for path, modifier in CARDS[card]["modifiers"].items():
            parts = tuple(path.split("."))
            if parts == keys:
                if isinstance(value, dict) and isinstance(modifier, dict):
                    value.update(deepcopy(modifier))
                else:
                    value = deepcopy(modifier)
            elif parts[:len(keys)] == keys:
                target = value
                for key in parts[len(keys):-1]:
                    target = target[key]
                target[parts[-1]] = deepcopy(modifier)
            elif keys[:len(parts)] == parts:
                target = modifier
                for key in keys[len(parts):]:
                    if not isinstance(target, dict) or key not in target:
                        break
                    target = target[key]
                else:
                    value = deepcopy(target)
    return value
