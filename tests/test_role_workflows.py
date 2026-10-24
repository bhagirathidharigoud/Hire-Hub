from io import BytesIO

from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService


def _register(client, email, role):
    response = client.post(
        "/api/auth/register",
        json={
            "name": role.title(),
            "email": email,
            "phone": "1234567890",
            "password": "secret123",
            "role": role,
        },
    )
    assert response.status_code == 201
    assert "password_hash" not in response.get_json()["data"]
    return response.get_json()["data"]


def test_candidate_can_manage_profile_resume_and_apply(app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    candidate_client = app.test_client()
    candidate = _register(candidate_client, "candidate-flow@example.com", "CANDIDATE")

    recruiter_client = app.test_client()
    _register(recruiter_client, "recruiter-flow@example.com", "RECRUITER")
    job_response = recruiter_client.post(
        "/api/jobs",
        json={"title": "Workflow Engineer", "description": "Build things", "location": "Remote"},
    )
    assert job_response.status_code == 201
    job_id = job_response.get_json()["data"]["_id"]

    profile_response = candidate_client.post(
        "/candidate/profile",
        data={"name": "Candidate Updated", "phone": "5551234567", "location": "Remote", "skills": "Python, Flask"},
    )
    assert profile_response.status_code == 302

    resume_response = candidate_client.post(
        "/candidate/resume",
        data={"resume": (BytesIO(b"sample resume"), "candidate.pdf")},
        content_type="multipart/form-data",
    )
    assert resume_response.status_code == 302

    apply_response = candidate_client.post(f"/jobs/{job_id}/apply")
    assert apply_response.status_code == 302

    with app.app_context():
        saved_candidate = UserRepository().find_one({"_id": candidate["_id"]})
        applications = ApplicationRepository().find_all({"candidate_id": candidate["_id"]})
        assert saved_candidate["name"] == "Candidate Updated"
        assert saved_candidate["skills"] == ["Python", "Flask"]
        assert saved_candidate["resume"]["original_name"] == "candidate.pdf"
        assert len(applications) == 1
        assert applications[0]["job_id"] == job_id


def test_recruiter_can_review_applications_and_schedule_interview(app):
    recruiter_client = app.test_client()
    recruiter = _register(recruiter_client, "recruiter-review@example.com", "RECRUITER")
    candidate_client = app.test_client()
    candidate = _register(candidate_client, "candidate-review@example.com", "CANDIDATE")

    with app.app_context():
        job_id = JobRepository().insert_one(
            {"title": "Review Engineer", "recruiter_id": recruiter["_id"], "status": "OPEN"}
        )
        application_id = ApplicationRepository().insert_one(
            {"candidate_id": candidate["_id"], "job_id": job_id, "status": "APPLIED"}
        )

    response = recruiter_client.post(
        f"/recruiter/applications/{application_id}/status",
        data={"status": "SHORTLISTED"},
    )
    assert response.status_code == 302

    response = recruiter_client.post(
        f"/recruiter/applications/{application_id}/interview",
        data={"date": "2026-11-01", "time": "10:30", "type": "ONLINE"},
    )
    assert response.status_code == 302

    with app.app_context():
        updated = ApplicationRepository().find_one({"_id": application_id})
        assert updated["status"] == "INTERVIEW_SCHEDULED"

    assert candidate_client.get("/candidate/dashboard").status_code == 200


def test_public_registration_cannot_create_admin(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Not Admin",
            "email": "not-admin@example.com",
            "phone": "1234567890",
            "password": "secret123",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 400


def test_admin_can_update_user_without_replacing_document(app):
    admin_client = app.test_client()
    admin = _register(admin_client, "admin-management@example.com", "CANDIDATE")
    with app.app_context():
        user_repo = UserRepository()
        user_repo.update_one({"_id": admin["_id"]}, {"role": "ADMIN"})
        managed = user_repo.insert_one(
            {"name": "Managed User", "email": "managed@example.com", "role": "CANDIDATE", "is_active": True}
        )
    with admin_client.session_transaction() as session:
        session["user_id"] = admin["_id"]
        session["role"] = "ADMIN"

    response = admin_client.post(
        "/admin/users",
        data={"user_id": managed, "role": "RECRUITER", "is_active": "on"},
    )
    assert response.status_code == 200
    with app.app_context():
        updated = UserRepository().find_one({"_id": managed})
        assert updated["name"] == "Managed User"
        assert updated["role"] == "RECRUITER"


def test_api_enforces_roles_and_candidate_updates_are_limited(app):
    candidate_client = app.test_client()
    candidate = _register(candidate_client, "candidate-api@example.com", "CANDIDATE")
    response = candidate_client.put(
        f"/api/candidates/{candidate['_id']}",
        json={"name": "Updated Candidate", "role": "ADMIN", "is_active": False},
    )
    assert response.status_code == 200
    with app.app_context():
        saved = UserRepository().find_one({"_id": candidate["_id"]})
        assert saved["name"] == "Updated Candidate"
        assert saved["role"] == "CANDIDATE"
        assert saved["is_active"] is True

    assert candidate_client.get("/api/admin/users").status_code == 403
    assert app.test_client().get("/api/admin/users").status_code == 401
    assert candidate_client.post("/api/jobs", json={"title": "Not allowed"}).status_code == 403
    assert candidate_client.get("/dashboard").headers["Location"].endswith("/candidate/dashboard")


def test_recommendations_job_filters_notifications_reports_and_session(app):
    client = app.test_client()
    candidate = _register(client, "candidate-modules@example.com", "CANDIDATE")
    client.put(
        f"/api/candidates/{candidate['_id']}",
        json={"skills": ["Python", "Flask"], "location": "Bengaluru"},
    )
    recommendations = client.get("/api/candidates/me/recommendations")
    assert recommendations.status_code == 200
    recommended = recommendations.get_json()["data"]
    assert recommended
    assert recommended[0]["match"]["score"] >= 70

    filtered = client.get("/api/jobs?keyword=Python&location=bengaluru&work_mode=HYBRID&skills=Python")
    assert filtered.status_code == 200
    assert [job["title"] for job in filtered.get_json()["data"]] == ["Python Developer"]

    with app.app_context():
        notification = NotificationService().create(candidate["_id"], "Application updated")
    marked = client.post(f"/api/notifications/{notification['_id']}/read")
    assert marked.status_code == 200
    notifications = client.get("/api/notifications").get_json()["data"]
    assert next(item for item in notifications if item["_id"] == notification["_id"])["is_read"] is True

    with app.app_context():
        admin = UserRepository().find_one({"email": "admin@example.com"})
    with client.session_transaction() as session:
        session["user_id"] = admin["_id"]
        session["role"] = "ADMIN"
    report = client.get("/admin/reports/export.csv")
    assert report.status_code == 200
    assert report.mimetype == "text/csv"
    assert "total_users" in report.get_data(as_text=True)

    logout = client.post("/api/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/auth/me").get_json()["data"] is None


def test_inactive_user_session_is_invalidated(app):
    client = app.test_client()
    user = _register(client, "candidate-disabled@example.com", "CANDIDATE")
    with app.app_context():
        UserRepository().update_one({"_id": user["_id"]}, {"is_active": False})
    response = client.get("/candidate/dashboard")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login?next=/candidate/dashboard")


def test_authenticated_profile_and_logout_cookie_session(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Profile Recruiter",
            "email": "profile-recruiter@example.com",
            "phone": "1234567890",
            "password": "secret123",
            "role": "RECRUITER",
        },
    )
    assert response.status_code == 201
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie
    assert client.get("/profile").status_code == 200
    updated = client.post("/profile", data={"name": "Recruiter Updated", "phone": "5551234567"})
    assert updated.status_code == 302
    with client.session_transaction() as session:
        session["user_id"] = response.get_json()["data"]["_id"]
        session["role"] = "RECRUITER"
        session.permanent = True
    assert client.post("/logout").status_code == 302
    assert client.get("/api/auth/me").get_json()["data"] is None


def test_legacy_get_logout_clears_session(client):
    response = client.post(
        "/api/auth/register",
        json={
            "name": "Legacy Logout",
            "email": "legacy-logout@example.com",
            "phone": "1234567890",
            "password": "secret123",
            "role": "CANDIDATE",
        },
    )
    assert response.status_code == 201
    logout = client.get("/logout")
    assert logout.status_code == 302
    assert logout.headers["Location"].endswith("/login")
    assert client.get("/api/auth/me").get_json()["data"] is None


def test_job_creation_validates_fields_and_admin_rest_management(app):
    recruiter_client = app.test_client()
    _register(recruiter_client, "job-validation@example.com", "RECRUITER")
    invalid_job = recruiter_client.post("/api/jobs", json={"title": "", "description": ""})
    assert invalid_job.status_code == 400

    valid_job = recruiter_client.post(
        "/api/jobs",
        json={"title": "Managed API Job", "description": "Job description"},
    )
    assert valid_job.status_code == 201
    job_id = valid_job.get_json()["data"]["_id"]

    with app.app_context():
        admin = UserRepository().find_one({"email": "admin@example.com"})
    admin_client = app.test_client()
    with admin_client.session_transaction() as session:
        session["user_id"] = admin["_id"]
        session["role"] = "ADMIN"
    changed = admin_client.patch(f"/api/admin/jobs/{job_id}", json={"status": "CLOSED"})
    assert changed.status_code == 200
    report = admin_client.get("/api/admin/reports")
    assert report.status_code == 200
    assert "application_statuses" in report.get_json()["data"]

    candidate_client = app.test_client()
    candidate = _register(candidate_client, "job-api-candidate@example.com", "CANDIDATE")
    protected_update = candidate_client.patch(f"/api/admin/jobs/{job_id}", json={"status": "OPEN"})
    assert protected_update.status_code == 403
    profile = candidate_client.post("/profile", data={"name": "Candidate Profile", "phone": "1234567890"})
    assert profile.status_code == 302
    assert candidate["_id"]


def test_redesigned_role_screens_render_and_saved_jobs_work(app):
    candidate_client = app.test_client()
    candidate = _register(candidate_client, "candidate-ui@example.com", "CANDIDATE")
    recruiter_client = app.test_client()
    recruiter = _register(recruiter_client, "recruiter-ui@example.com", "RECRUITER")
    with app.app_context():
        job_id = JobRepository().insert_one({
            "title": "UI Test Role",
            "description": "A test job for the redesigned screens",
            "recruiter_id": recruiter["_id"],
            "company_id": recruiter["_id"],
            "company_name": "HireHub Example",
            "location": "Remote",
            "work_mode": "REMOTE",
            "employment_type": "FULL_TIME",
            "skills": ["Python"],
            "status": "OPEN",
            "salary_min": 50000,
            "salary_max": 70000,
        })
    assert candidate_client.get("/candidate/dashboard").status_code == 200
    assert candidate_client.get("/candidate/profile").status_code == 200
    assert candidate_client.get("/candidate/interviews").status_code == 200
    assert candidate_client.get("/candidate/saved-jobs").status_code == 200
    assert candidate_client.get("/jobs?keyword=Python&location=Remote&work_mode=REMOTE").status_code == 200
    save = candidate_client.post(f"/candidate/jobs/{job_id}/save", data={"next": "/candidate/saved-jobs"})
    assert save.status_code == 302
    assert "saved-jobs" in save.headers["Location"]
    assert "UI Test Role" in candidate_client.get("/candidate/saved-jobs").get_data(as_text=True)

    assert recruiter_client.get("/recruiter/dashboard").status_code == 200
    assert recruiter_client.get("/recruiter/jobs").status_code == 200
    assert recruiter_client.get("/recruiter/job/new").status_code == 200
    assert recruiter_client.get("/recruiter/company").status_code == 200

    with app.app_context():
        admin = UserRepository().find_one({"email": "admin@example.com"})
    admin_client = app.test_client()
    with admin_client.session_transaction() as session:
        session["user_id"] = admin["_id"]
        session["role"] = "ADMIN"
    for path in ("/admin/dashboard", "/admin/companies", "/admin/jobs", "/admin/reports", "/admin/audit-logs"):
        assert admin_client.get(path).status_code == 200
