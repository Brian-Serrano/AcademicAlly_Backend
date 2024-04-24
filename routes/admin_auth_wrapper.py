from functools import wraps

import jwt
from flask import request, jsonify

from config import api
from db import Admin


def admin_auth_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = request.headers["Authorization"]

        if not token:
            return jsonify({"error": "A valid token is missing!", "type": "error"}), 401

        try:
            data = jwt.decode(token, api.config['SECRET_KEY'], algorithms=['HS256'])
            admin = Admin.query.filter_by(admin_id=data["admin_id"]).first()
            current_admin = {
                "id": admin.admin_id,
                "name": admin.name,
                "email": admin.email
            }
        except Exception as e:
            return jsonify({"error": f"Invalid token! {e}", "type": "error"}), 401

        return f(current_admin, *args, **kwargs)

    return decorator
