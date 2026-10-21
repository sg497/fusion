from fastapi.testclient import TestClient
import main

def test_health_never_executes_orders():
    client = TestClient(main.app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["trading_execution"] is False

def test_strategy_info_disables_execution():
    client = TestClient(main.app)
    data = client.get("/api/strategy-info").json()
    assert data["execution"] == "disabled"
