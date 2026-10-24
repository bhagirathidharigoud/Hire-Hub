# Hire-Hub

A modular Flask recruitment portal with candidate, recruiter, and admin flows.

## Local setup

1. Create a virtual environment and install dependencies:
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
2. Copy `.env.example` to `.env` and adjust values as needed.
3. Run the app:
   python run.py

The app uses signed Flask session cookies. Set a strong `SECRET_KEY`; production startup requires it and enables secure cookies by default. Sessions expire after 12 hours by default (`SESSION_LIFETIME_HOURS`) and can be explicitly logged out.

## Features included

- Candidate, recruiter, and admin role-based access
- Registration, login, logout, and session-based dashboard routing
- Public job listings and detail pages, with candidate-only job applications
- Candidate profile editing, resume upload/download, application tracking/withdrawal, interviews, and notifications
- Profile management for candidate, recruiter, and admin accounts
- Recruiter job posting and status management, applicant review, and interview scheduling
- Admin user/job/application management, analytics, reports, and audit logs
- Personalized candidate job recommendations using skills and location
- Job search and filtering by keyword, location, skill, work mode, and employment type
- Role-scoped REST API endpoints for auth, jobs, applications, candidates, interviews, notifications, recommendations, and admin data
- MongoDB persistence using `MONGO_URI` and `MONGO_DATABASE` from `.env`, with in-memory fallback when MongoDB is unavailable
- Isolated in-memory storage for automated tests

## Notes

Resume uploads accept PDF, DOC, and DOCX files; the default maximum request size is 5 MB and can be changed with `MAX_CONTENT_LENGTH`. The MongoDB repository is used whenever the configured server is reachable; development can fall back to in-memory storage with a warning. Set `MONGO_REQUIRED=true` to fail startup rather than run without MongoDB. Production sets this requirement by default. Resume binary files are stored in the configured protected upload folder, with their metadata stored in MongoDB.

Demo accounts and sample jobs are created only in non-production configurations. Provision production admin users through a trusted deployment process; public registration cannot create admin accounts.
