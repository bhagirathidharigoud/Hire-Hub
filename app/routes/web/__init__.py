from app.routes.web.admin_routes import admin_bp
from app.routes.web.auth_routes import auth_bp
from app.routes.web.candidate_routes import candidate_bp
from app.routes.web.dashboard_routes import dashboard_bp
from app.routes.web.job_routes import jobs_bp
from app.routes.web.recruiter_routes import recruiter_bp


def register_web_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(candidate_bp)
    app.register_blueprint(recruiter_bp)
    app.register_blueprint(admin_bp)
