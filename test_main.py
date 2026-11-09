
import csv
import hashlib
import secrets
from io import StringIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
import models
from database import Base, get_db


def hash_password(password):
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        310000
    ).hex()

    return f"pbkdf2_sha256$310000${salt}${password_hash}"


@pytest.fixture
def client():
    # Create a separate in-memory test database.
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    retailer = models.Retailer(
        name="Test Kirana Store",
        phone="9000000001",
        credit_limit=50000
    )

    other_retailer = models.Retailer(
        name="Other Kirana Store",
        phone="9000000002",
        credit_limit=30000
    )

    db.add_all([retailer, other_retailer])
    db.flush()

    db.add_all([
        models.User(
            username="retailer_test",
            password_hash=hash_password("Test@123"),
            role="retailer",
            retailer_id=retailer.id
        ),
        models.User(
            username="staff_test",
            password_hash=hash_password("Staff@123"),
            role="staff",
            retailer_id=None
        )
    ])

    db.add_all([
        models.Product(
            sku_code="TEST-BISCUIT",
            name="Test Biscuit",
            dealer_price=10.00,
            stock_cases=20,
            scheme_type="buy_x_get_y",
            scheme_value=10
        ),
        models.Product(
            sku_code="TEST-DETERGENT",
            name="Test Detergent",
            dealer_price=100.00,
            stock_cases=20,
            scheme_type="discount",
            scheme_value=3
        ),
        models.Product(
            sku_code="TEST-TEA",
            name="Test Tea",
            dealer_price=50.00,
            stock_cases=0,
            scheme_type="none",
            scheme_value=0
        )
    ])

    db.commit()
    db.close()

    def override_get_db():
        test_db = TestingSessionLocal()
        try:
            yield test_db
        finally:
            test_db.close()

    main.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main.app) as test_client:
        yield test_client

    main.app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def retailer_headers():
    token = main.create_access_token("retailer_test")
    return {"Authorization": f"Bearer {token}"}


def staff_headers():
    token = main.create_access_token("staff_test")
    return {"Authorization": f"Bearer {token}"}


def test_home_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_valid_retailer_login(client):
    response = client.post(
        "/auth/login",
        json={
            "username": "retailer_test",
            "password": "Test@123"
        }
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_invalid_login(client):
    response = client.post(
        "/auth/login",
        json={
            "username": "retailer_test",
            "password": "WrongPassword"
        }
    )

    assert response.status_code == 401


def test_products_require_login(client):
    response = client.get("/products")

    assert response.status_code == 401


def test_authenticated_user_can_view_products(client):
    response = client.get(
        "/products",
        headers=retailer_headers()
    )

    assert response.status_code == 200
    assert len(response.json()) == 3


def test_retailer_can_only_view_own_store(client):
    response = client.get(
        "/retailers",
        headers=retailer_headers()
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Test Kirana Store"


def test_retailer_cannot_export_tally_csv(client):
    response = client.get(
        "/orders/export/tally",
        headers=retailer_headers()
    )

    assert response.status_code == 403


def test_staff_can_export_tally_csv(client):
    response = client.get(
        "/orders/export/tally",
        headers=staff_headers()
    )

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "Order ID" in response.text


def test_order_applies_free_product_scheme(client):
    response = client.post(
        "/orders",
        headers=retailer_headers(),
        json={
            "retailer_id": 999,
            "items": [
                {"product_id": 1, "quantity": 10}
            ]
        }
    )

    assert response.status_code == 200

    result = response.json()

    assert result["message"] == "Order placed successfully"
    assert result["items"][0]["quantity"] == 10
    assert result["items"][0]["free_quantity"] == 1
    assert result["total_amount"] == 100.00


def test_order_applies_discount_scheme(client):
    response = client.post(
        "/orders",
        headers=retailer_headers(),
        json={
            "retailer_id": 999,
            "items": [
                {"product_id": 2, "quantity": 5}
            ]
        }
    )

    assert response.status_code == 200
    assert response.json()["total_amount"] == 485.00


def test_order_rejects_out_of_stock_product(client):
    response = client.post(
        "/orders",
        headers=retailer_headers(),
        json={
            "retailer_id": 999,
            "items": [
                {"product_id": 3, "quantity": 1}
            ]
        }
    )

    assert response.status_code == 400
    assert "Insufficient stock" in response.json()["detail"]


def test_order_rejects_duplicate_products(client):
    response = client.post(
        "/orders",
        headers=retailer_headers(),
        json={
            "retailer_id": 999,
            "items": [
                {"product_id": 1, "quantity": 1},
                {"product_id": 1, "quantity": 2}
            ]
        }
    )

    assert response.status_code == 400
    assert "same product more than once" in response.json()["detail"]


def test_order_rejects_zero_quantity(client):
    response = client.post(
        "/orders",
        headers=retailer_headers(),
        json={
            "retailer_id": 999,
            "items": [
                {"product_id": 1, "quantity": 0}
            ]
        }
    )

    assert response.status_code == 422
