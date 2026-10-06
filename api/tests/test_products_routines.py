from fastapi.testclient import TestClient


def make_product(client: TestClient, name: str, ingredients: str) -> int:
    response = client.post(
        "/products", json={"name": name, "brand": "Test", "ingredients_text": ingredients}
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def make_routine(client: TestClient) -> int:
    response = client.post("/routines", json={"name": "Night", "skin_type": "dry"})
    assert response.status_code == 201
    return int(response.json()["id"])


def add(client: TestClient, routine: int, product: int, slot: str = "evening") -> int:
    response = client.post(f"/routines/{routine}/items", json={"product_id": product, "slot": slot})
    return response.status_code


def test_product_resolves_ingredients_in_order(client: TestClient) -> None:
    pid = make_product(client, "Serum", "Aqua, Niacinamide, Glycerin, Water, Mystery")
    body = client.get(f"/products/{pid}").json()
    assert body["ingredient_names"] == ["water", "niacinamide", "glycerin"]


def test_product_list_and_delete(client: TestClient) -> None:
    first = make_product(client, "A", "Water")
    second = make_product(client, "B", "Glycerin")
    assert [p["id"] for p in client.get("/products").json()] == [second, first]
    assert client.delete(f"/products/{first}").status_code == 204
    assert client.get(f"/products/{first}").status_code == 404
    assert client.delete(f"/products/{first}").status_code == 404


def test_routine_items_and_duplicate_rejection(client: TestClient) -> None:
    rid = make_routine(client)
    pid = make_product(client, "Cream", "Water, Ceramide NP")
    assert add(client, rid, pid) == 201
    assert add(client, rid, pid, "morning") == 409
    routine = client.get(f"/routines/{rid}").json()
    assert [(i["product_name"], i["slot"]) for i in routine["items"]] == [("Cream", "evening")]


def test_routine_item_validation(client: TestClient) -> None:
    rid = make_routine(client)
    pid = make_product(client, "Cream", "Water")
    assert add(client, 999, pid) == 404
    assert add(client, rid, 999) == 404
    assert add(client, rid, pid, "noon") == 422


def test_conflicts_only_within_the_same_slot(client: TestClient) -> None:
    rid = make_routine(client)
    acid = make_product(client, "Peel", "Water, Glycolic Acid")
    retinoid = make_product(client, "Night serum", "Squalane, Retinol")
    gentle = make_product(client, "Moisturiser", "Water, Glycerin")
    assert add(client, rid, acid) == 201
    assert add(client, rid, retinoid) == 201
    assert add(client, rid, gentle) == 201
    conflicts = client.get(f"/routines/{rid}/conflicts").json()
    assert conflicts == [
        {
            "slot": "evening",
            "product_a": "Peel",
            "product_b": "Night serum",
            "severity": "high",
            "reason": conflicts[0]["reason"],
        }
    ]
    item = client.get(f"/routines/{rid}").json()["items"][0]["id"]
    assert client.delete(f"/routines/{rid}/items/{item}").status_code == 204
    assert add(client, rid, acid, "morning") == 201
    assert client.get(f"/routines/{rid}/conflicts").json() == []


def test_most_severe_rule_wins_and_results_are_sorted(client: TestClient) -> None:
    rid = make_routine(client)
    vitamin_c = make_product(client, "C serum", "Ascorbic Acid")
    bpo = make_product(client, "Spot gel", "Benzoyl Peroxide")
    combo = make_product(client, "Combo", "Retinol, Lactic Acid")
    for pid in (vitamin_c, bpo, combo):
        assert add(client, rid, pid, "morning") == 201
    severities = [c["severity"] for c in client.get(f"/routines/{rid}/conflicts").json()]
    assert severities == ["high", "medium", "low"]


def test_deleting_a_routine(client: TestClient) -> None:
    rid = make_routine(client)
    assert client.delete(f"/routines/{rid}").status_code == 204
    assert client.get(f"/routines/{rid}/conflicts").status_code == 404
    assert client.get("/routines").json() == []
