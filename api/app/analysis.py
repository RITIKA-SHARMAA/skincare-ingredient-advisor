"""Analysis pipeline: parse, match, explain (Gemini or rules), validate, fall back, persist."""

import logging

from sqlalchemy.orm import Session

from .llm import LLMClient, LLMError, parse_explanations, rule_based_explanations
from .models import Analysis
from .parser import IngredientMatcher
from .schemas import (
    AiStatus,
    AnalysisResult,
    CatalogueIngredient,
    IngredientExplanation,
    IngredientResult,
    SkinType,
    UnmatchedIngredient,
)

log = logging.getLogger(__name__)

LLM_ATTEMPTS = 2


class TooManyIngredients(Exception):
    pass


def explain(
    llm: LLMClient | None, ingredients: list[CatalogueIngredient], skin_type: SkinType
) -> tuple[list[IngredientExplanation], AiStatus]:
    """Ask the LLM up to twice; any failure or invalid output falls back to rules."""
    if llm is None:
        return rule_based_explanations(ingredients, skin_type), "rules"
    if not ingredients:
        return [], "ai"
    for attempt in range(1, LLM_ATTEMPTS + 1):
        try:
            return parse_explanations(llm.explain_raw(ingredients, skin_type), ingredients), "ai"
        except LLMError as exc:
            log.warning("llm attempt %d of %d rejected: %s", attempt, LLM_ATTEMPTS, exc)
    return rule_based_explanations(ingredients, skin_type), "fallback"


def analyse(
    db: Session,
    llm: LLMClient | None,
    ingredient_text: str,
    skin_type: SkinType,
    max_ingredients: int,
) -> AnalysisResult:
    matches, unmatched = IngredientMatcher(db).resolve(ingredient_text)
    if len(matches) + len(unmatched) > max_ingredients:
        raise TooManyIngredients(f"at most {max_ingredients} ingredients per request")

    # The same catalogue ingredient can appear twice under different names; explain it once.
    unique: dict[str, CatalogueIngredient] = {}
    for m in matches:
        unique.setdefault(
            m.ingredient.name,
            CatalogueIngredient(
                name=m.ingredient.name,
                function=m.ingredient.function,
                irritant_level=m.ingredient.irritant_level,
            ),
        )
    explanations, status = explain(llm, list(unique.values()), skin_type)
    by_name = {e.name.lower(): e for e in explanations}

    results = []
    for m in matches:
        facts = unique[m.ingredient.name]
        exp = by_name[facts.name.lower()]
        results.append(
            IngredientResult(
                **facts.model_dump(),
                position=m.position,
                matched_as=m.raw,
                match_type=m.match_type,
                likely_irritant=exp.likely_irritant,
                explanation=exp.explanation,
                routine_slot=exp.routine_slot,
            )
        )
    result = AnalysisResult(
        ingredient_text=ingredient_text,
        skin_type=skin_type,
        ingredients=results,
        unmatched=[UnmatchedIngredient(position=u.position, name=u.raw) for u in unmatched],
        ai_status=status,
    )
    row = Analysis(
        ingredient_text=ingredient_text,
        skin_type=skin_type,
        ai_status=status,
        result_json=result.model_dump_json(),
    )
    db.add(row)
    db.commit()
    result.id = row.id
    return result
