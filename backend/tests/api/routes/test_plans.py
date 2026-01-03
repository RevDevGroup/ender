import uuid

from fastapi.testclient import TestClient

from app.models import PlanUpgrade


def test_list_plans(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test listing available plans"""
    response = client.get(
        "/api/v1/plans/list",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "data" in response.json()


def test_get_quota(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test getting user quota information"""
    response = client.get(
        "/api/v1/plans/quota",
        headers=superuser_token_headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "data" in response.json()


def test_upgrade_plan_as_superuser(
    client: TestClient,
    superuser_token_headers: dict[str, str],
):
    """Test upgrading plan as superuser"""
    # Get available plans first
    plans_response = client.get(
        "/api/v1/plans/list",
        headers=superuser_token_headers,
    )
    plans = plans_response.json()["data"]

    if not plans:
        return  # Skip if no plans available

    # Try to upgrade to the first available plan
    plan_id = plans[0]["id"]
    upgrade_in = PlanUpgrade(plan_id=uuid.UUID(plan_id))

    response = client.put(
        "/api/v1/plans/upgrade",
        headers=superuser_token_headers,
        json=upgrade_in.model_dump(mode="json"),
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
