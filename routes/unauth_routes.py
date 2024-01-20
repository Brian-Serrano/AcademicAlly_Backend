import re
import smtplib
import ssl
from datetime import datetime, timedelta
from email.mime.text import MIMEText

import bcrypt
from flask import request, jsonify, Blueprint

import jwt

from config import api, db, SALT, PASSWORD_REGEX
from db import User, CourseSkill
from utils import validate_login, update_course_eligibility, validate_signup, update_assessment_achievement, \
    generate_token

unauth_bp = Blueprint("unauth_routes", __name__)


@unauth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        user = User.query.filter_by(email=data["email"], role=data["role"]).first()
        validation = validate_login(user, data["email"], data["password"])
        if validation["isValid"]:
            token = jwt.encode({"user_id": user.id, "exp": datetime.now() + timedelta(days=7)}, api.config['SECRET_KEY'], algorithm='HS256')
            if data["eligibility"]:
                response = {
                    "achievements": update_course_eligibility(data["courseId"], user.id, data["rating"], data["score"]),
                    "token": token,
                    "type": "success"
                }
                return jsonify(response), 201
            else:
                return jsonify({"token": token, "type": "noAssessment"}), 201
        else:
            validation["type"] = "validationError"
            return jsonify(validation), 250
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@unauth_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        validation = validate_signup(data["name"], data["email"], data["password"], data["confirmPassword"])
        if validation["isValid"]:
            user = User(
                name=data["name"],
                role=data["role"],
                email=data["email"],
                password=bcrypt.hashpw(data["password"].encode(), SALT).decode()
            )
            db.session.add(user)
            user_id = User.query.filter_by(name=data["name"], email=data["email"], role=data["role"]).first().id

            token = jwt.encode({"user_id": user_id, "exp": datetime.now() + timedelta(days=7)}, api.config['SECRET_KEY'], algorithm='HS256')

            if data["eligibility"]:
                course_skill = CourseSkill(
                    course_id=data["courseId"],
                    user_id=user_id,
                    role=data["eligibility"],
                    assessment_taken=1,
                    assessment_rating=data["rating"]
                )
                db.session.add(course_skill)
                response = {
                    "achievements": update_assessment_achievement(data["score"] / data["items"] >= data["evaluator"], data["score"], user_id),
                    "token": token,
                    "type": "success"
                }
                return jsonify(response), 201
            else:
                db.session.commit()
                return jsonify({"token": token, "type": "noAssessment"}), 201
        else:
            validation["type"] = "validationError"
            return jsonify(validation), 250
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@unauth_bp.route("/forgot_password", methods=["POST"])
def forgot_password():
    try:
        password = "esuh ovxk nwbx zzux"
        email_sender = "Brianserrano503@gmail.com"
        email_receiver = request.json["email"]
        msg = MIMEText(f'Please access the <a href="http://127.0.0.1:5000/template_routes/forgot_password_page/{generate_token(email_receiver)}">link</a> to change your password and recover your account.', "html")
        msg["Subject"] = "Forgot Password"
        msg["From"] = email_sender
        msg["To"] = email_receiver
        context = ssl.create_default_context()

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as smtp:
            smtp.login(email_sender, password)
            smtp.sendmail(email_sender, email_receiver, msg.as_string())
            return jsonify({"message": "A mail for recovering your account has sent.", "type": "success"}), 201
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@unauth_bp.route("/change_password", methods=["POST"])
def change_password():
    try:
        data = request.get_json()
        user = User.query.filter_by(id=data["email"]).first()
        if re.search(PASSWORD_REGEX, data["password"]):
            user.password = bcrypt.hashpw(data["password"].encode(), SALT).decode()
            db.session.commit()
            return jsonify({"data": "Password successfully saved!", "type": "success"}), 201
        else:
            return jsonify({"data": "Invalid Password", "type": "validationError"}), 250
    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500
