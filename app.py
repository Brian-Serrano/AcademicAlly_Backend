from config import api, db
from routes import get_bp, post_bp, unauth_bp, template_bp
from scheduler import init_scheduler

api.register_blueprint(get_bp, url_prefix="/get_routes")
api.register_blueprint(post_bp, url_prefix="/post_routes")
api.register_blueprint(unauth_bp, url_prefix="/unauth_routes")
api.register_blueprint(template_bp, url_prefix="/template_routes")

if __name__ == '__main__':

    with api.app_context():
        db.create_all()

    init_scheduler()

    api.run()

