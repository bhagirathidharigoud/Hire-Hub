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


def test_job_api_hides_closed_jobs_from_public_search_and_detail(app):
    recruiter = app.test_client()
    recruiter.post(
        "/api/auth/register",
        json={
            "name": "Job Owner",
            "email": "job-owner@example.com",
            "password": "secret123",
            "role": "RECRUITER",
        },
    )
    created = recruiter.post(
        "/api/jobs",
        json={"title": "Private Listing", "description": "A role"},
    )
    job_id = created.get_json()["data"]["_id"]
    assert recruiter.patch(
        f"/api/jobs/{job_id}/status",
        json={"status": "CLOSED"},
    ).status_code == 200

    public = app.test_client()
    public_jobs = public.get("/api/jobs?status=CLOSED").get_json()["data"]
    assert all(job["_id"] != job_id for job in public_jobs)
    assert public.get(f"/api/jobs/{job_id}").status_code == 404
    assert recruiter.get(f"/api/jobs/{job_id}").status_code == 200


def test_recruiter_cannot_change_another_recruiters_job(app):
    owner = app.test_client()
    owner.post(
        "/api/auth/register",
        json={
            "name": "Owner",
            "email": "owner@example.com",
            "password": "secret123",
            "role": "RECRUITER",
        },
    )
    job = owner.post(
        "/api/jobs",
        json={"title": "Owned Listing", "description": "A role"},
    ).get_json()["data"]

    other = app.test_client()
    other.post(
        "/api/auth/register",
        json={
            "name": "Other",
            "email": "other@example.com",
            "password": "secret123",
            "role": "RECRUITER",
        },
    )
    response = other.patch(
        f"/api/jobs/{job['_id']}/status",
        json={"status": "CLOSED"},
    )
    assert response.status_code == 403


def test_job_service_rejects_unknown_search_filters(client):
    response = client.get("/api/jobs?password_hash=anything")
    assert response.status_code == 400
    assert "Unsupported job filter" in response.get_json()["message"]
