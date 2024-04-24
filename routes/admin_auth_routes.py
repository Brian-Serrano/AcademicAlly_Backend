from datetime import datetime, timedelta

import bcrypt
import jwt
from flask import Blueprint, request, jsonify

from config import api, SALT, db
from db import Admin
from utils import validate_login, validate_signup

admin_auth_bp = Blueprint("admin_auth_routes", __name__)


@admin_auth_bp.route("/admin_login", methods=["POST"])
def admin_login():
    try:
        data = request.get_json()
        admin = Admin.query.filter_by(email=data["email"]).first()
        validation = validate_login(admin, data["email"], data["password"], True)
        if validation["isValid"]:
            token = jwt.encode({"admin_id": admin.admin_id, "exp": datetime.now() + timedelta(days=7)}, api.config['SECRET_KEY'], algorithm='HS256')
            response = {
                "token": token,
                "id": admin.admin_id,
                "name": admin.name,
                "email": admin.email,
                "password": data["password"]
            }
            return jsonify({"data": response, "type": "success"}), 201
        else:
            return jsonify({"type": "validation_error", "message": validation["message"]}), 400
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_auth_bp.route("/admin_signup", methods=["POST"])
def admin_signup():
    try:
        data = request.get_json()
        validation = validate_signup(data["name"], data["email"], data["password"], data["confirmPassword"], True)

        if validation["isValid"]:
            admin = Admin(
                name=data["name"],
                email=data["email"],
                password=bcrypt.hashpw(data["password"].encode(), SALT).decode()
            )
            db.session.add(admin)
            admin = Admin.query.filter_by(name=data["name"], email=data["email"]).first()

            token = jwt.encode({"admin_id": admin.admin_id, "exp": datetime.now() + timedelta(days=7)}, api.config['SECRET_KEY'], algorithm='HS256')

            db.session.commit()
            response = {
                "token": token,
                "id": admin.admin_id,
                "name": admin.name,
                "email": admin.email,
                "password": data["password"]
            }
            return jsonify({"data": response, "type": "success"}), 201
        else:
            return jsonify({"type": "validation_error", "message": validation["message"]}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500
