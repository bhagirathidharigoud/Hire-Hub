def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200


def test_register_api(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "phone": "1234567890",
            "password": "secret123",
            "role": "CANDIDATE",
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["success"] is True


def test_login_api(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Bob",
            "email": "bob@example.com",
            "phone": "1234567890",
            "password": "secret123",
            "role": "CANDIDATE",
        },
    )
    response = client.post(
        "/api/auth/login",
        json={"email": "bob@example.com", "password": "secret123"},
    )
    assert response.status_code == 200
    assert response.get_json()["success"] is True
