from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from app.llm import LLMError
from app.storage import ObjectNotFound, validate_object_name
from tests.conftest import FakeLLM

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


def upload(client: TestClient, data: bytes = PNG, content_type: str = "image/png") -> str:
    ticket = client.post("/labels/upload-url", json={"content_type": "image/png"}).json()
    assert ticket["method"] == "PUT"
    path = ticket["upload_url"].removeprefix("http://testserver")
    response = client.put(path, content=data, headers={"Content-Type": content_type})
    assert response.status_code == 204, response.text
    return str(ticket["object_name"])


def test_label_photo_is_read_then_analysed(
    client: TestClient, use_llm: Callable[[FakeLLM], FakeLLM]
) -> None:
    use_llm(FakeLLM(responses=[LLMError("x"), LLMError("y")], extracted_text="Aqua, Retinol"))
    name = upload(client)
    response = client.post(
        "/labels/analyses", params={"object_name": name}, json={"skin_type": "oily"}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["extracted_text"] == "Aqua, Retinol"
    assert [i["name"] for i in body["ingredients"]] == ["water", "retinol"]
    assert body["ai_status"] == "fallback"


def test_rules_mode_cannot_read_labels(client: TestClient) -> None:
    name = upload(client)
    response = client.post("/labels/analyses", params={"object_name": name}, json={})
    assert response.status_code == 503


def test_empty_extraction_is_reported(
    client: TestClient, use_llm: Callable[[FakeLLM], FakeLLM]
) -> None:
    use_llm(FakeLLM(extracted_text=""))
    name = upload(client)
    response = client.post("/labels/analyses", params={"object_name": name}, json={})
    assert response.status_code == 422


def test_extraction_failure_is_a_bad_gateway(
    client: TestClient, use_llm: Callable[[FakeLLM], FakeLLM]
) -> None:
    use_llm(FakeLLM(extracted_text=LLMError("down")))
    name = upload(client)
    response = client.post("/labels/analyses", params={"object_name": name}, json={})
    assert response.status_code == 502


def test_unknown_object_is_not_found(
    client: TestClient, use_llm: Callable[[FakeLLM], FakeLLM]
) -> None:
    use_llm(FakeLLM(extracted_text="Water"))
    response = client.post(
        "/labels/analyses", params={"object_name": "labels/" + "0" * 32 + ".png"}, json={}
    )
    assert response.status_code == 404


def test_upload_rejects_wrong_type_and_oversize(client: TestClient) -> None:
    ticket = client.post("/labels/upload-url", json={"content_type": "image/png"}).json()
    path = ticket["upload_url"].removeprefix("http://testserver")
    wrong = client.put(path, content=PNG, headers={"Content-Type": "image/jpeg"})
    assert wrong.status_code == 415
    big = client.put(
        path, content=b"0" * (5 * 1024 * 1024 + 1), headers={"Content-Type": "image/png"}
    )
    assert big.status_code == 413


def test_upload_url_rejects_unsupported_types(client: TestClient) -> None:
    response = client.post("/labels/upload-url", json={"content_type": "application/pdf"})
    assert response.status_code == 422


@pytest.mark.parametrize(
    "name", ["../etc/passwd", "labels/../../x.png", "labels/abc.png", "labels/" + "0" * 32 + ".gif"]
)
def test_object_names_are_strictly_validated(name: str) -> None:
    with pytest.raises(ObjectNotFound):
        validate_object_name(name)
