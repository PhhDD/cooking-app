from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env.test", override=True)

from cooking_app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_create_recipe_redirects_unauthenticated_user():
    response = client.post(
        "/recipes",
        data = {},
        follow_redirects = False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "/sign-in"

def test_new_recipe_redirects_unauthenticated_user():
    response = client.get(
        "/recipes/new",
        follow_redirects = False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "/sign-in"

# Test the route exists, and a database session can be created
def test_recipe_list_page_loads():
    response = client.get("/recipes")

    assert response.status_code == 200
    assert "Public" in response.text

# Test empty search result behaviour
def test_recipe_search_with_no_results():
    response = client.get(
        "/recipes",
        params={"q": "definitely-not-a-real-recipe"},
    )

    assert response.status_code == 200
    assert "No recipes matched" in response.text

def test_missing_recipe_returns_404():
    missing_recipe_id = uuid4()

    response = client.get(
        f"/recipes/{missing_recipe_id}"
    )

    assert response.status_code == 404

def test_missing_recipe_edit_page_returns_404():
    missing_recipe_id = uuid4()

    response = client.get(
        f"/recipes/{missing_recipe_id}/edit"
    )

    assert response.status_code == 404

def test_search_by_recipe_name():
    response = client.get("/recipes?q=beef")

    assert response.status_code == 200
    assert "Chilli Beef Brisket" in response.text

def test_search_by_ingredient_name():
    response = client.get("/recipes?q=garlic")

    assert response.status_code == 200
    assert "Chilli Beef Brisket" in response.text

def test_create_recipe_requires_required_fields(authenticated_user):
    response = client.post(
        "/recipes",
        data={},
        follow_redirects=False,
    )

    assert response.status_code == 422


def test_create_recipe_rejects_invalid_numbers(authenticated_user):
    response = client.post(
        "/recipes",
        data={
            "recipe_name": "Test Recipe",
            "cuisine": "Test",
            "cook_time": "not-a-number",
            "servings": "two",
        },
        follow_redirects=False,
    )

    assert response.status_code == 422

def test_create_recipe(authenticated_user):
    response = client.post(
        "/recipes",
        data={
            "recipe_name": "Automated Test Recipe",
            "cuisine": "Test Cuisine",
            "cook_time": "15",
            "servings": "2",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "location" in response.headers

    recipe_url = response.headers["location"]

    try:
        detail_response = client.get(recipe_url)

        assert detail_response.status_code == 200
        assert "Automated Test Recipe" in detail_response.text

    finally:
        client.post(f"{recipe_url}/delete")

def test_edit_recipe(authenticated_user):
    create_response = client.post(
        "/recipes",
        data={
            "recipe_name": "Recipe Before Editing",
            "cuisine": "Test Cuisine",
            "cook_time": "15",
            "servings": "2",
        },
        follow_redirects=False,
    )

    assert create_response.status_code == 303

    recipe_url = create_response.headers["location"]

    try:
        edit_response = client.post(
            f"{recipe_url}/edit",
            data={
                "recipe_name": "Recipe After Editing",
                "cuisine": "Updated Cuisine",
                "cook_time": "30",
                "servings": "4",
            },
            follow_redirects=False,
        )

        assert edit_response.status_code == 303

        detail_response = client.get(recipe_url)

        assert detail_response.status_code == 200
        assert "Recipe After Editing" in detail_response.text
        assert "Updated Cuisine" in detail_response.text
        assert "30 minutes" in detail_response.text

    finally:
        client.post(f"{recipe_url}/delete")

def test_add_ingredient_to_recipe(authenticated_user):
    create_response = client.post(
        "/recipes",
        data={
            "recipe_name": "Ingredient Test Recipe",
            "cuisine": "Test Cuisine",
            "cook_time": "20",
            "servings": "2",
        },
        follow_redirects=False,
    )

    assert create_response.status_code == 303

    recipe_url = create_response.headers["location"]

    try:
        ingredient_response = client.post(
            f"{recipe_url}/ingredients",
            data={
                "ingredient_name": "Automated Test Garlic",
                "category": "vegetable",
                "quantity": "3",
                "unit": "cloves",
                "preparation": "minced",
            },
            follow_redirects=False,
        )

        assert ingredient_response.status_code == 303

        detail_response = client.get(recipe_url)

        assert detail_response.status_code == 200
        assert "automated test garlic" in detail_response.text
        assert "3.00" in detail_response.text
        assert "cloves" in detail_response.text
        assert "minced" in detail_response.text

    finally:
        client.post(f"{recipe_url}/delete")
