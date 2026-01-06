import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from main import app, Base, engine

# Create test database tables (NOTE: does not add new columns if tables already exist)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean database before each test"""
    yield
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM order_items;"))
        connection.execute(text("DELETE FROM orders;"))
        connection.execute(text("DELETE FROM items;"))
        connection.execute(text("DELETE FROM users;"))

def test_hello():
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json()["message"] == "Hello World! Backend is running"

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_create_user():
    response = client.post(
        "/api/users",
        json={"email": "user@test.com", "name": "Test User"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user@test.com"
    assert data["name"] == "Test User"
    assert "user_id" in data

def test_get_user():
    create_response = client.post(
        "/api/users",
        json={"email": "user@test.com", "name": "Test User"}
    )
    user_id = create_response.json()["user_id"]

    response = client.get(f"/api/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id

def test_get_user_not_found():
    response = client.get("/api/users/invalid-id")
    assert response.status_code == 404

def test_create_item():
    response = client.post(
        "/api/items",
        json={"name": "Aspirin", "description": "Pain reliever", "price": 5.99}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Aspirin"
    assert float(data["price"]) == 5.99
    # new fields (image is stored separately)
    assert "has_image" in data
    assert data["has_image"] is False

def test_list_items():
    client.post("/api/items", json={"name": "Item 1", "price": 10.0})
    client.post("/api/items", json={"name": "Item 2", "price": 20.0})

    response = client.get("/api/items")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 2
    assert all("has_image" in it for it in items)

def test_get_item():
    create_response = client.post(
        "/api/items",
        json={"name": "Paracetamol", "description": "Fever reducer", "price": 3.50}
    )
    item_id = create_response.json()["item_id"]

    response = client.get(f"/api/items/{item_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == item_id
    assert "has_image" in data
    assert data["has_image"] is False

def test_update_item():
    create_response = client.post(
        "/api/items",
        json={"name": "Old Name", "price": 10.0}
    )
    item_id = create_response.json()["item_id"]

    response = client.put(
        f"/api/items/{item_id}",
        json={"name": "New Name", "price": 15.0}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"

def test_delete_item():
    create_response = client.post(
        "/api/items",
        json={"name": "To Delete", "price": 5.0}
    )
    item_id = create_response.json()["item_id"]

    response = client.delete(f"/api/items/{item_id}")
    assert response.status_code == 204

def test_upload_and_get_item_image():
    # Create item
    create_response = client.post(
        "/api/items",
        json={"name": "With Image", "price": 9.99}
    )
    assert create_response.status_code == 201
    item_id = create_response.json()["item_id"]

    # Upload image (minimal valid PNG bytes)
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20
    files = {"file": ("test.png", io.BytesIO(fake_png), "image/png")}

    upload_response = client.post(f"/api/items/{item_id}/image", files=files)
    assert upload_response.status_code == 200
    up = upload_response.json()
    assert up["status"] == "ok"
    assert up["item_id"] == item_id
    assert up["mime"] == "image/png"
    assert up["bytes"] == len(fake_png)

    # Item should now report has_image = true
    item_response = client.get(f"/api/items/{item_id}")
    assert item_response.status_code == 200
    assert item_response.json()["has_image"] is True

    # Get image bytes
    img_response = client.get(f"/api/items/{item_id}/image")
    assert img_response.status_code == 200
    assert img_response.headers["content-type"].startswith("image/png")
    assert img_response.content == fake_png

def test_upload_image_item_not_found():
    fake_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 20
    files = {"file": ("test.png", io.BytesIO(fake_png), "image/png")}

    response = client.post("/api/items/invalid-id/image", files=files)
    assert response.status_code == 404

def test_get_image_not_found():
    # Create item without image
    create_response = client.post(
        "/api/items",
        json={"name": "No Image", "price": 1.0}
    )
    item_id = create_response.json()["item_id"]

    response = client.get(f"/api/items/{item_id}/image")
    assert response.status_code == 404

def test_create_order():
    user_response = client.post(
        "/api/users",
        json={"email": "order@test.com", "name": "Order User"}
    )
    user_id = user_response.json()["user_id"]

    item_response = client.post(
        "/api/items",
        json={"name": "Medicine", "price": 12.0}
    )
    item_id = item_response.json()["item_id"]

    response = client.post(
        "/api/orders",
        json={
            "user_id": user_id,
            "items": [{"item_id": item_id, "quantity": 2}]
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id
    assert data["status"] == "pending"

def test_get_order():
    user_response = client.post(
        "/api/users",
        json={"email": "order2@test.com", "name": "Order User 2"}
    )
    user_id = user_response.json()["user_id"]

    item_response = client.post(
        "/api/items",
        json={"name": "Medicine 2", "price": 8.0}
    )
    item_id = item_response.json()["item_id"]

    order_response = client.post(
        "/api/orders",
        json={
            "user_id": user_id,
            "items": [{"item_id": item_id, "quantity": 1}]
        }
    )
    order_id = order_response.json()["order_id"]

    response = client.get(f"/api/orders/{order_id}")
    assert response.status_code == 200
    assert response.json()["order_id"] == order_id
