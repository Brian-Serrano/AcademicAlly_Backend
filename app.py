from config import api, db
from routes import auth_bp, template_bp, admin_bp, user_bp, assessment_bp, request_bp, session_bp, assignment_bp, \
    support_bp, admin_auth_bp, admin_assessment_bp
from scheduler import init_scheduler

api.register_blueprint(auth_bp, url_prefix="/auth_routes")
api.register_blueprint(user_bp, url_prefix="/user_routes")
api.register_blueprint(assessment_bp, url_prefix="/assessment_routes")
api.register_blueprint(request_bp, url_prefix="/request_routes")
api.register_blueprint(session_bp, url_prefix="/session_routes")
api.register_blueprint(assignment_bp, url_prefix="/assignment_routes")
api.register_blueprint(support_bp, url_prefix="/support_routes")
api.register_blueprint(template_bp, url_prefix="/template_routes")
api.register_blueprint(admin_bp, url_prefix="/admin_routes")
api.register_blueprint(admin_auth_bp, url_prefix="/admin_auth_routes")
api.register_blueprint(admin_assessment_bp, url_prefix="/admin_assessment_routes")

# Should be removed in deployment and its corresponding imports
if __name__ == '__main__':

    with api.app_context():
        db.create_all()

    init_scheduler()

    api.run()

