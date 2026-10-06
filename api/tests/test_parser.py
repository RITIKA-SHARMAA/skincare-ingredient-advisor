import pytest
from sqlalchemy.orm import Session

from app.parser import IngredientMatcher, normalise, split_ingredients


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" Water,  Glycerin;Niacinamide\n", ["water", "glycerin", "niacinamide"]),
        ("Aqua • Glycerin · Panthenol", ["aqua", "glycerin", "panthenol"]),
        ("Water, , ;\n  ,Glycerin.", ["water", "glycerin"]),
        ("Titanium Dioxide (CI 77891), Zinc Oxide (nano)", ["titanium dioxide", "zinc oxide"]),
        ("Retinol*, Parfum [Fragrance]", ["retinol", "parfum"]),
        ("", []),
    ],
)
def test_split_ingredients(raw: str, expected: list[str]) -> None:
    assert split_ingredients(raw) == expected


def test_normalise_collapses_whitespace_and_case() -> None:
    assert normalise("  SODIUM   Hyaluronate. ") == "sodium hyaluronate"


def test_exact_alias_and_fuzzy_matches(db: Session) -> None:
    matches, unmatched = IngredientMatcher(db).resolve("Glycerin, Aqua, Niacinamid")
    assert [(m.ingredient.name, m.match_type) for m in matches] == [
        ("glycerin", "exact"),
        ("water", "alias"),
        ("niacinamide", "fuzzy"),
    ]
    assert unmatched == []


def test_alias_lookup_comes_from_catalogue_data(db: Session) -> None:
    matcher = IngredientMatcher(db)
    assert matcher.match("vitamin c") is not None
    found = matcher.match("bha")
    assert found is not None and found[0].name == "salicylic acid"


def test_unmatched_names_are_reported_with_position(db: Session) -> None:
    matches, unmatched = IngredientMatcher(db).resolve("Water, Unobtainium Extract, Glycerin")
    assert [m.position for m in matches] == [0, 2]
    assert [(u.position, u.raw) for u in unmatched] == [(1, "unobtainium extract")]


def test_fuzzy_match_rejects_weak_similarity(db: Session) -> None:
    assert IngredientMatcher(db).match("xyz") is None
