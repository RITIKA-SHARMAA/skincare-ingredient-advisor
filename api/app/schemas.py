from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SkinType = Literal["normal", "dry", "oily", "sensitive", "combination"]
Slot = Literal["morning", "evening"]
AiStatus = Literal["ai", "rules", "fallback"]
MatchType = Literal["exact", "alias", "fuzzy"]


class AnalysisRequest(BaseModel):
    ingredient_text: str = Field(min_length=2, max_length=10_000)
    skin_type: SkinType = "normal"


class CatalogueIngredient(BaseModel):
    """The catalogue facts for one matched ingredient, which is all an explainer may see."""

    name: str
    function: str
    irritant_level: int = Field(ge=0, le=5)


class IngredientExplanation(BaseModel):
    """One item of explainer output. Gemini must return a list of these."""

    name: str
    likely_irritant: bool
    explanation: str = Field(min_length=1, max_length=600)
    routine_slot: Slot


class IngredientResult(CatalogueIngredient):
    position: int
    matched_as: str
    match_type: MatchType
    likely_irritant: bool
    explanation: str
    routine_slot: Slot


class UnmatchedIngredient(BaseModel):
    position: int
    name: str


class AnalysisResult(BaseModel):
    id: int | None = None
    ingredient_text: str
    skin_type: SkinType
    ingredients: list[IngredientResult]
    unmatched: list[UnmatchedIngredient]
    ai_status: AiStatus


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=160)
    ingredients_text: str = Field(min_length=2, max_length=10_000)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str | None
    ingredients_text: str
    ingredient_names: list[str] = []


class RoutineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    skin_type: SkinType = "normal"


class RoutineItemCreate(BaseModel):
    product_id: int
    slot: Slot = "evening"


class RoutineItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    slot: Slot


class RoutineOut(BaseModel):
    id: int
    name: str
    skin_type: SkinType
    items: list[RoutineItemOut] = []


class ConflictOut(BaseModel):
    slot: Slot
    product_a: str
    product_b: str
    severity: Literal["low", "medium", "high"]
    reason: str


class LabelUploadRequest(BaseModel):
    content_type: Literal["image/jpeg", "image/png", "image/webp"]


class LabelUploadTicket(BaseModel):
    object_name: str
    upload_url: str
    method: Literal["PUT"] = "PUT"
    headers: dict[str, str]
    expires_in_seconds: int


class LabelAnalysisRequest(BaseModel):
    skin_type: SkinType = "normal"


class LabelAnalysisResult(AnalysisResult):
    extracted_text: str
