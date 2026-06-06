"""Каталог напитков и лимиты по категориям."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    key: str
    label: str


SIMPLE_ITEMS: list[Item] = [
    Item("beer", "Пиво"),
    Item("cola", "Кола"),
    Item("cola_zero", "Кола зеро"),
    Item("fanta", "Фанта"),
    Item("sprite", "Спрайт"),
    Item("juice", "Сок"),
    Item("tonic", "Тоник"),
    Item("water", "Вода"),
    Item("slivki", "Сливки"),
]

TEA_ITEMS: list[Item] = [
    Item("tea_black", "Чай чёрный"),
    Item("tea_green", "Чай зелёный"),
    Item("tea_strawberry_mango", "Чай стробери манго"),
    Item("tea_chamomile", "Чай ромашка"),
    Item("tea_earl_grey", "Чай ирл грей"),
]

COFFEE_ITEMS: list[Item] = [
    Item("coffee_decaf", "Кофе декаф"),
    Item("coffee_lungo", "Кофе лунго"),
    Item("coffee_espresso", "Кофе эспрессо"),
]

ALL_ITEMS_LIST: list[Item] = [*SIMPLE_ITEMS, *TEA_ITEMS, *COFFEE_ITEMS]
DISPLAY_ORDER: list[str] = [i.key for i in ALL_ITEMS_LIST]

ALL_ITEMS: dict[str, str] = {i.key: i.label for i in ALL_ITEMS_LIST}

TEA_KEYS = {i.key for i in TEA_ITEMS}
COFFEE_KEYS = {i.key for i in COFFEE_ITEMS}

LIMITS: dict[str, int] = {
    "tea": 2,
    "coffee": 3,
}


def category_total(counts: dict[str, int], keys: set[str]) -> int:
    return sum(counts.get(k, 0) for k in keys)


def category_limit(keys: set[str]) -> int | None:
    if keys <= TEA_KEYS:
        return LIMITS["tea"]
    if keys <= COFFEE_KEYS:
        return LIMITS["coffee"]
    return None
