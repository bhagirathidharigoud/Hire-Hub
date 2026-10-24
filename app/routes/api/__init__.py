from app.routes.api.admin_api import admin_api
from app.routes.api.application_api import application_api
from app.routes.api.auth_api import auth_api
from app.routes.api.candidate_api import candidate_api
from app.routes.api.interview_api import interview_api
from app.routes.api.job_api import job_api
from app.routes.api.notification_api import notification_api
from app.routes.api.recruiter_api import recruiter_api


def register_api_routes(app):
    app.register_blueprint(auth_api)
    app.register_blueprint(job_api)
    app.register_blueprint(notification_api)
    app.register_blueprint(application_api)
    app.register_blueprint(interview_api)
    app.register_blueprint(candidate_api)
    app.register_blueprint(recruiter_api)
    app.register_blueprint(admin_api)
