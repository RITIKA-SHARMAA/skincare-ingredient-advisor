"""Explainers: a deterministic rule-based one and Gemini on Vertex AI behind one interface.

The model never sees anything except catalogue facts for matched ingredients (or the label
image the user uploaded), and nothing it returns is trusted until `parse_explanations`
has checked it.
"""

import json
from typing import Protocol

from pydantic import TypeAdapter, ValidationError

from .config import Settings
from .schemas import CatalogueIngredient, IngredientExplanation, SkinType


class LLMError(Exception):
    """The provider failed or returned something unusable."""


class LLMClient(Protocol):
    def explain_raw(self, ingredients: list[CatalogueIngredient], skin_type: SkinType) -> str:
        """Return the model's raw text, expected to be a JSON array of explanations."""
        ...

    def extract_ingredients(self, image: bytes, mime_type: str) -> str:
        """Return the ingredient list printed on a label image as plain text."""
        ...


_EXPLANATIONS = TypeAdapter(list[IngredientExplanation])


def parse_explanations(
    raw: str, ingredients: list[CatalogueIngredient]
) -> list[IngredientExplanation]:
    """Validate model output: valid JSON, valid schema, exactly the ingredients we sent."""
    try:
        items = _EXPLANATIONS.validate_json(raw)
    except ValidationError as exc:
        raise LLMError(f"output failed schema validation: {exc.error_count()} errors") from exc
    expected = sorted(i.name.lower() for i in ingredients)
    returned = sorted(i.name.lower() for i in items)
    if returned != expected:
        missing = set(expected) - set(returned)
        invented = set(returned) - set(expected)
        raise LLMError(
            f"ingredient set mismatch: missing={sorted(missing)} extra={sorted(invented)}"
        )
    return items


# ---------------------------------------------------------------- rule-based explainer

FUNCTION_NOTES = {
    "humectant": "draws water into the skin to keep it hydrated",
    "emollient": "softens skin and fills gaps between skin cells",
    "occlusive": "forms a film that slows water loss",
    "barrier support": "replenishes lipids that hold the skin barrier together",
    "soothing agent": "helps calm redness and discomfort",
    "antioxidant": "helps neutralise free radicals from UV and pollution",
    "vitamin c": "is an antioxidant that can brighten uneven tone",
    "brightening active": "targets dullness and dark spots",
    "treatment active": "targets specific concerns such as redness or breakouts",
    "chemical exfoliant": "loosens dead skin cells so they shed faster",
    "retinoid": "speeds up cell turnover and is a common anti-ageing active",
    "retinoid alternative": "is marketed as a gentler alternative to retinoids",
    "oxidising acne treatment": "kills acne-causing bacteria",
    "acne treatment": "helps reduce breakouts",
    "peptide": "is a short chain of amino acids used in firming products",
    "uv filter": "absorbs or reflects UV light",
    "preservative": "stops bacteria and mould growing in the product",
    "chelating agent": "binds metal ions so the formula stays stable",
    "ph adjuster": "keeps the product at its intended pH",
    "thickener": "gives the product its texture",
    "emulsifier": "keeps oil and water mixed",
    "surfactant": "lifts oil and dirt so they rinse away",
    "solvent": "dissolves the other ingredients",
    "drying alcohol": "helps products absorb quickly but can dry the skin",
    "fragrance": "adds scent and is a common cause of sensitivity",
    "essential oil": "adds scent and can irritate sensitive skin",
}

IRRITANT_THRESHOLD: dict[str, int] = {
    "sensitive": 2,
    "dry": 3,
    "combination": 3,
    "normal": 4,
    "oily": 4,
}

EVENING_FUNCTIONS = {"retinoid", "chemical exfoliant", "oxidising acne treatment"}
MORNING_FUNCTIONS = {"uv filter", "vitamin c", "antioxidant"}


def rule_based_explanations(
    ingredients: list[CatalogueIngredient], skin_type: SkinType
) -> list[IngredientExplanation]:
    threshold = IRRITANT_THRESHOLD[skin_type]
    results = []
    for item in ingredients:
        function = item.function.lower()
        note = FUNCTION_NOTES.get(function, f"is used as a {function}")
        if function in EVENING_FUNCTIONS:
            slot = "evening"
        elif function in MORNING_FUNCTIONS:
            slot = "morning"
        else:
            slot = "evening" if item.irritant_level >= 3 else "morning"
        results.append(
            IngredientExplanation(
                name=item.name,
                likely_irritant=item.irritant_level >= threshold,
                explanation=f"{item.name.capitalize()} ({item.function.lower()}) {note}.",
                routine_slot=slot,
            )
        )
    return results


# ---------------------------------------------------------------- Gemini on Vertex AI

EXPLAIN_PROMPT = """You explain skincare ingredients to consumers in plain language.
Return ONLY a JSON array with exactly one object per ingredient below, using these keys:
name (copied exactly), likely_irritant (boolean), explanation (one or two sentences,
max 400 characters), routine_slot ("morning" or "evening").
Base likely_irritant on the supplied irritant_level (0-5) and the skin type. Do not add,
rename or drop ingredients. Do not give medical advice.
Skin type: {skin_type}
Ingredients: {ingredients}"""

EXTRACT_PROMPT = """This is a photo of a cosmetic product label. Copy the ingredient list
exactly as printed, as one comma-separated line. If no ingredient list is visible, return
an empty string. Return nothing else."""


class VertexGemini:
    def __init__(self, settings: Settings) -> None:
        from google import genai
        from google.genai import types

        self._types = types
        self._model = settings.vertex_model
        self._client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
            http_options=types.HttpOptions(timeout=int(settings.llm_timeout_seconds * 1000)),
        )

    def explain_raw(self, ingredients: list[CatalogueIngredient], skin_type: SkinType) -> str:
        payload = json.dumps([i.model_dump() for i in ingredients])
        prompt = EXPLAIN_PROMPT.format(skin_type=skin_type, ingredients=payload)
        config = self._types.GenerateContentConfig(
            response_mime_type="application/json", temperature=0.1
        )
        try:
            response = self._client.models.generate_content(
                model=self._model, contents=prompt, config=config
            )
        except Exception as exc:  # the SDK raises several transport and API error types
            raise LLMError(f"Vertex AI request failed: {type(exc).__name__}") from exc
        return response.text or ""

    def extract_ingredients(self, image: bytes, mime_type: str) -> str:
        part = self._types.Part.from_bytes(data=image, mime_type=mime_type)
        try:
            response = self._client.models.generate_content(
                model=self._model, contents=[part, EXTRACT_PROMPT]
            )
        except Exception as exc:
            raise LLMError(f"Vertex AI request failed: {type(exc).__name__}") from exc
        return (response.text or "").strip()
