import pytest
from fastapi.testclient import TestClient
from main import app, Base, engine, SessionLocal
from sqlalchemy import text

# Create test database tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_db():
    """Clean database before each test"""
    yield
    # Clean up after test
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM order_items;"))
        connection.execute(text("DELETE FROM orders;"))
        connection.execute(text("DELETE FROM items;"))
        connection.execute(text("DELETE FROM users;"))

def test_hello():
    """Test hello endpoint"""
    response = client.get("/hello")
    assert response.status_code == 200
    assert response.json()["message"] == "Hello World! Backend is running"

def test_health():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_create_user():
    """Test creating a user"""
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
    """Test getting a user"""
    create_response = client.post(
        "/api/users",
        json={"email": "user@test.com", "name": "Test User"}
    )
    user_id = create_response.json()["user_id"]
    
    response = client.get(f"/api/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id

def test_get_user_not_found():
    """Test getting non-existent user"""
    response = client.get("/api/users/invalid-id")
    assert response.status_code == 404

def test_create_item():
    """Test creating an item"""
    response = client.post(
        "/api/items",
        json={"name": "Aspirin", "description": "Pain reliever", "price": 5.99}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Aspirin"
    assert float(data["price"]) == 5.99

def test_list_items():
    """Test listing items"""
    client.post("/api/items", json={"name": "Item 1", "price": 10.0})
    client.post("/api/items", json={"name": "Item 2", "price": 20.0})
    
    response = client.get("/api/items")
    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_get_item():
    """Test getting an item"""
    create_response = client.post(
        "/api/items",
        json={"name": "Paracetamol", "description": "Fever reducer", "price": 3.50}
    )
    item_id = create_response.json()["item_id"]
    
    response = client.get(f"/api/items/{item_id}")
    assert response.status_code == 200
    assert response.json()["item_id"] == item_id

def test_update_item():
    """Test updating an item"""
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
    """Test deleting an item"""
    create_response = client.post(
        "/api/items",
        json={"name": "To Delete", "price": 5.0}
    )
    item_id = create_response.json()["item_id"]
    
    response = client.delete(f"/api/items/{item_id}")
    assert response.status_code == 204

def test_create_order():
    """Test creating an order"""
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
    """Test getting an order"""
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
