from flask import Blueprint, render_template, jsonify

from utils import validate_token

template_bp = Blueprint("template_routes", __name__)


@template_bp.route("/forgot_password_page/<email_token>", methods=["GET"])
def forgot_password_page(email_token):
    email = validate_token(email_token)
    if email:
        return render_template("forgot_password.html", email=email)
    else:
        return jsonify({"error": "Invalid email token"}), 500
