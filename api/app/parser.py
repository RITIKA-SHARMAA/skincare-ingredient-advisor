"""Turn a raw ingredient list into catalogue matches without silently dropping anything."""

import re
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Ingredient
from .schemas import MatchType

# Below this pg_trgm similarity a fuzzy match is more likely wrong than right.
FUZZY_MIN_SIMILARITY = 0.45

_SPLIT = re.compile(r"[,;\n•·]+")
_PARENTHETICAL = re.compile(r"\((?:and|ci|nano)[^)]*\)|\[[^\]]*\]")
_SPACES = re.compile(r"\s+")


@dataclass(frozen=True)
class Match:
    position: int
    raw: str
    ingredient: Ingredient
    match_type: MatchType


@dataclass(frozen=True)
class Unmatched:
    position: int
    raw: str


def normalise(name: str) -> str:
    name = _PARENTHETICAL.sub("", name.lower())
    name = name.strip(" .:-*")
    return _SPACES.sub(" ", name)


def split_ingredients(raw: str) -> list[str]:
    """Split on commas, semicolons, bullets and newlines; drop empty fragments."""
    names = (normalise(part) for part in _SPLIT.split(raw))
    return [name for name in names if name]


class IngredientMatcher:
    """Resolves names against the catalogue: exact name, then alias, then trigram similarity."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.by_name: dict[str, Ingredient] = {}
        self.by_alias: dict[str, Ingredient] = {}
        for ingredient in db.scalars(select(Ingredient)):
            self.by_name[ingredient.name.lower()] = ingredient
            for alias in ingredient.alias_list():
                self.by_alias.setdefault(alias, ingredient)

    def match(self, name: str) -> tuple[Ingredient, MatchType] | None:
        if name in self.by_name:
            return self.by_name[name], "exact"
        if name in self.by_alias:
            return self.by_alias[name], "alias"
        fuzzy = self._fuzzy(name)
        return (fuzzy, "fuzzy") if fuzzy else None

    def _fuzzy(self, name: str) -> Ingredient | None:
        similarity = func.similarity(Ingredient.name, name)
        # `%` is the pg_trgm operator that can use ix_ingredients_name_trgm.
        statement = (
            select(Ingredient)
            .where(Ingredient.name.op("%")(name))
            .where(similarity >= FUZZY_MIN_SIMILARITY)
            .order_by(similarity.desc())
            .limit(1)
        )
        return self.db.scalar(statement)

    def resolve(self, raw: str) -> tuple[list[Match], list[Unmatched]]:
        matches: list[Match] = []
        unmatched: list[Unmatched] = []
        for position, name in enumerate(split_ingredients(raw)):
            found = self.match(name)
            if found is None:
                unmatched.append(Unmatched(position, name))
            else:
                ingredient, match_type = found
                matches.append(Match(position, name, ingredient, match_type))
        return matches, unmatched
