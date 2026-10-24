def test_jobs_endpoint(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True


def test_create_job(client):
    client.post(
        "/api/auth/register",
        json={
            "name": "Recruiter",
            "email": "recruiter-jobs@example.com",
            "phone": "1234567890",
            "password": "secret123",
            "role": "RECRUITER",
        },
    )
    response = client.post(
        "/api/jobs",
        json={
            "title": "Python Developer",
            "description": "Build Flask apps",
            "company_id": "company_1",
            "recruiter_id": "recruiter_1",
            "location": "Bengaluru",
            "skills": ["Python", "Flask"],
            "work_mode": "HYBRID",
        },
    )
    assert response.status_code == 201
    assert response.get_json()["success"] is True
