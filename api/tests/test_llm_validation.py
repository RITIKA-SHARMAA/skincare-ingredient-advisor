import json

import pytest

from app.llm import LLMError, parse_explanations, rule_based_explanations
from app.schemas import CatalogueIngredient

INGREDIENTS = [
    CatalogueIngredient(name="glycerin", function="Humectant", irritant_level=0),
    CatalogueIngredient(name="retinol", function="Retinoid", irritant_level=4),
]


def explanation(name: str, **overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "name": name,
        "likely_irritant": False,
        "explanation": f"{name} explained.",
        "routine_slot": "morning",
    }
    item.update(overrides)
    return item


def test_valid_output_is_accepted_case_insensitively() -> None:
    raw = json.dumps([explanation("Glycerin"), explanation("retinol", routine_slot="evening")])
    result = parse_explanations(raw, INGREDIENTS)
    assert [r.routine_slot for r in result] == ["morning", "evening"]


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        "",
        json.dumps({"name": "glycerin"}),
        json.dumps([explanation("glycerin"), explanation("retinol", routine_slot="noon")]),
        json.dumps([explanation("glycerin"), explanation("retinol", explanation="")]),
        json.dumps([explanation("glycerin")]),
        json.dumps([explanation("glycerin"), explanation("retinol"), explanation("mercury")]),
        json.dumps([explanation("glycerin"), explanation("glycerin")]),
    ],
    ids=[
        "not-json",
        "empty",
        "object-not-array",
        "bad-slot",
        "empty-explanation",
        "missing-ingredient",
        "invented-ingredient",
        "duplicate-instead-of-missing",
    ],
)
def test_invalid_output_is_rejected(raw: str) -> None:
    with pytest.raises(LLMError):
        parse_explanations(raw, INGREDIENTS)


def test_rule_based_explanations_depend_on_skin_type() -> None:
    mild = CatalogueIngredient(name="kojic acid", function="Brightening active", irritant_level=2)
    sensitive = rule_based_explanations([mild], "sensitive")[0]
    normal = rule_based_explanations([mild], "normal")[0]
    assert sensitive.likely_irritant is True
    assert normal.likely_irritant is False


def test_rule_based_slots() -> None:
    items = [
        CatalogueIngredient(name="retinol", function="Retinoid", irritant_level=4),
        CatalogueIngredient(name="zinc oxide", function="UV filter", irritant_level=0),
        CatalogueIngredient(name="glycerin", function="Humectant", irritant_level=0),
    ]
    slots = [e.routine_slot for e in rule_based_explanations(items, "normal")]
    assert slots == ["evening", "morning", "morning"]
