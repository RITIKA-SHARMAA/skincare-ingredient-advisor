import json
from typing import Protocol
from .config import settings
from .schemas import IngredientResult

class LLMClient(Protocol):
    def explain(self, ingredients: list[dict], skin_type: str) -> list[dict]: ...

class FakeLLM:
    def explain(self, ingredients, skin_type):
        out=[]
        for x in ingredients:
            irritant=x["irritant_level"] >= 3 and skin_type == "sensitive"
            slot="evening" if x["irritant_level"] >= 3 else "morning"
            out.append({**x,"likely_irritant":irritant,"explanation":f"{x['name'].capitalize()} is commonly used for {x['function'].lower()}. This catalogue explanation is illustrative, not medical advice.","routine_slot":slot})
        return out

class VertexGemini:
    def __init__(self):
        from google import genai
        from google.genai.types import GenerateContentConfig
        self.client=genai.Client(vertexai=True, project=settings.google_cloud_project, location=settings.google_cloud_location)
        self.config=GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
    def explain(self, ingredients, skin_type):
        prompt=("Return ONLY a JSON array. For each supplied ingredient return keys name,function,irritant_level,likely_irritant,explanation,routine_slot. "
                "Do not invent ingredients. likely_irritant should reflect the supplied catalogue level and chosen skin type. "
                f"Skin type: {skin_type}. Ingredients: {json.dumps(ingredients)}")
        response=self.client.models.generate_content(model=settings.vertex_model, contents=prompt, config=self.config)
        return json.loads(response.text)

def get_llm():
    return VertexGemini() if settings.llm_provider.lower()=="vertex" else FakeLLM()
