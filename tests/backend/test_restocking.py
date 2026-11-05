"""
Tests for restocking order endpoints.
"""
import pytest

import main


@pytest.fixture(autouse=True)
def clear_restocking_orders():
    """Restocking orders live in module-level state, so isolate each test."""
    main.restocking_orders.clear()
    yield
    main.restocking_orders.clear()


class TestRestockingOrders:
    """Test suite for restocking order endpoints."""

    def test_get_restocking_orders_empty(self, client):
        """Test that no orders exist before any are submitted."""
        response = client.get("/api/restocking-orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_restocking_order(self, client):
        """Test submitting an order computes totals and lead time on the server."""
        payload = {
            "budget": 10000,
            "lines": [
                {"sku": "WDG-001", "quantity": 100},  # Widgets, 7 days
                {"sku": "MTR-304", "quantity": 2},    # Actuators, 21 days
            ],
        }
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["status"] == "Submitted"
        assert order["order_number"].startswith("RST-")
        assert len(order["lines"]) == 2
        assert order["total_cost"] == pytest.approx(sum(l["line_total"] for l in order["lines"]))
        # Order arrives when its slowest line does
        assert order["lead_time_days"] == max(l["lead_time_days"] for l in order["lines"])
        assert order["lead_time_days"] == 21
        assert "expected_delivery" in order

    def test_created_order_is_listed(self, client):
        """Test that a submitted order appears in the list."""
        payload = {"budget": 5000, "lines": [{"sku": "GSK-203", "quantity": 10}]}
        created = client.post("/api/restocking-orders", json=payload).json()

        listed = client.get("/api/restocking-orders").json()
        assert [o["id"] for o in listed] == [created["id"]]

    def test_orders_listed_newest_first(self, client):
        """Test ordering of the list."""
        first = client.post("/api/restocking-orders",
                            json={"budget": 5000, "lines": [{"sku": "GSK-203", "quantity": 1}]}).json()
        second = client.post("/api/restocking-orders",
                             json={"budget": 5000, "lines": [{"sku": "GSK-203", "quantity": 2}]}).json()

        listed = client.get("/api/restocking-orders").json()
        assert [o["id"] for o in listed] == [second["id"], first["id"]]

    def test_order_over_budget_rejected(self, client):
        """Test that an order exceeding the budget is rejected."""
        payload = {"budget": 10, "lines": [{"sku": "MTR-304", "quantity": 5}]}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 400
        assert client.get("/api/restocking-orders").json() == []

    def test_empty_order_rejected(self, client):
        """Test that an order with no lines is rejected."""
        response = client.post("/api/restocking-orders", json={"budget": 1000, "lines": []})
        assert response.status_code == 400

    def test_unknown_sku_rejected(self, client):
        """Test that an unknown SKU returns 404."""
        payload = {"budget": 1000, "lines": [{"sku": "NOPE-000", "quantity": 1}]}
        response = client.post("/api/restocking-orders", json=payload)
        assert response.status_code == 404

    def test_non_positive_quantity_rejected(self, client):
        """Test that zero or negative quantities fail validation."""
        for quantity in (0, -5):
            payload = {"budget": 1000, "lines": [{"sku": "WDG-001", "quantity": quantity}]}
            response = client.post("/api/restocking-orders", json=payload)
            assert response.status_code == 422
