from typing import Literal
from pydantic import BaseModel, Field

SkinType = Literal["normal","dry","oily","sensitive","combination"]
class AnalysisRequest(BaseModel): ingredient_text: str = Field(min_length=2, max_length=10000); skin_type: SkinType = "normal"
class IngredientResult(BaseModel): name: str; function: str; irritant_level: int; likely_irritant: bool; explanation: str; routine_slot: Literal["morning","evening"]
class AnalysisResult(BaseModel): ingredients: list[IngredientResult]; unmatched: list[dict]; ai_status: str
class ProductCreate(BaseModel): name: str; brand: str | None = None; ingredients_text: str
class ProductOut(ProductCreate): id: int
class RoutineCreate(BaseModel): name: str; skin_type: SkinType = "normal"
class RoutineItemCreate(BaseModel): product_id: int; slot: Literal["morning","evening"] = "evening"
class RoutineOut(RoutineCreate): id: int
class ConflictOut(BaseModel): product_a: str; product_b: str; reason: str
