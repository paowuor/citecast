from fastapi.testclient import TestClient
from app.web.main import app


def test_home_page_renders():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "CiteCast" in response.text
