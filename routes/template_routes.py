from flask import Blueprint, render_template

template_bp = Blueprint("template_routes", __name__)


@template_bp.route("/forgot_password_page/<email_token>", methods=["GET"])
def forgot_password_page(email_token):
    return render_template("forgot_password.html", email=email_token)
