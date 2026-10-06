import json
from collections.abc import Callable

from fastapi.testclient import TestClient

from app.llm import LLMError
from app.schemas import CatalogueIngredient
from tests.conftest import FakeLLM

TEXT = "Aqua, Glycerin, Retinol, Unobtainium Extract"


def valid_json(ingredients: list[CatalogueIngredient]) -> str:
    return json.dumps(
        [
            {
                "name": i.name,
                "likely_irritant": i.irritant_level >= 3,
                "explanation": f"Gemini says {i.name} is fine.",
                "routine_slot": "evening",
            }
            for i in ingredients
        ]
    )


def post(client: TestClient, text: str = TEXT, skin_type: str = "normal") -> dict:  # type: ignore[type-arg]
    response = client.post("/analyses", json={"ingredient_text": text, "skin_type": skin_type})
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def test_rules_mode_explains_matches_and_keeps_unmatched(client: TestClient) -> None:
    body = post(client, skin_type="sensitive")
    assert body["ai_status"] == "rules"
    assert [i["name"] for i in body["ingredients"]] == ["water", "glycerin", "retinol"]
    assert body["ingredients"][0]["match_type"] == "alias"
    assert body["ingredients"][0]["matched_as"] == "aqua"
    retinol = body["ingredients"][2]
    assert retinol["likely_irritant"] is True and retinol["routine_slot"] == "evening"
    assert body["unmatched"] == [{"position": 3, "name": "unobtainium extract"}]


def test_valid_llm_output_is_used(
    client: TestClient, use_llm: Callable[[FakeLLM], FakeLLM]
) -> None:
    fake = use_llm(FakeLLM(responses=[valid_json]))
    body = post(client)
    assert body["ai_status"] == "ai"
    assert body["ingredients"][1]["explanation"] == "Gemini says glycerin is fine."
    assert fake.calls == 1


def test_invalid_output_is_retried_once(
    client: TestClient, use_llm: Callable[[FakeLLM], FakeLLM]
) -> None:
    fake = use_llm(FakeLLM(responses=["{not json", valid_json]))
    assert post(client)["ai_status"] == "ai"
    assert fake.calls == 2


def test_two_bad_answers_fall_back_to_rules(
    client: TestClient, use_llm: Callable[[FakeLLM], FakeLLM]
) -> None:
    invented = json.dumps(
        [
            {
                "name": "mercury",
                "likely_irritant": True,
                "explanation": "x",
                "routine_slot": "evening",
            }
        ]
    )
    fake = use_llm(FakeLLM(responses=[invented, LLMError("timeout")]))
    body = post(client)
    assert body["ai_status"] == "fallback"
    assert fake.calls == 2
    assert body["ingredients"][1]["explanation"].startswith("Glycerin (humectant)")


def test_duplicate_names_are_explained_once(
    client: TestClient, use_llm: Callable[[FakeLLM], FakeLLM]
) -> None:
    sent: list[list[str]] = []

    def record(ingredients: list[CatalogueIngredient]) -> str:
        sent.append([i.name for i in ingredients])
        return valid_json(ingredients)

    use_llm(FakeLLM(responses=[record]))
    body = post(client, "Water, Aqua, Glycerin")
    assert sent == [["water", "glycerin"]]
    assert [i["position"] for i in body["ingredients"]] == [0, 1, 2]


def test_analysis_is_persisted_and_retrievable(client: TestClient) -> None:
    created = post(client)
    fetched = client.get(f"/analyses/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_missing_analysis_is_a_problem_document(client: TestClient) -> None:
    response = client.get("/analyses/999")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["detail"] == "Analysis not found"


def test_validation_errors_are_problem_documents(client: TestClient) -> None:
    response = client.post("/analyses", json={"ingredient_text": "x", "skin_type": "alien"})
    assert response.status_code == 422
    body = response.json()
    assert body["title"] == "Validation failed"
    assert {tuple(e["loc"]) for e in body["detail"]} == {
        ("body", "ingredient_text"),
        ("body", "skin_type"),
    }


def test_ingredient_cap(client: TestClient) -> None:
    text = ", ".join(f"ingredient {n}" for n in range(101))
    response = client.post("/analyses", json={"ingredient_text": text})
    assert response.status_code == 413


def test_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "abc123"})
    assert response.headers["X-Request-ID"] == "abc123"
    assert response.json() == {"status": "ok"}
