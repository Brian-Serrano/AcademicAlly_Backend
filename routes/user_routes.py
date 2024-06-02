import os
from datetime import datetime

import bcrypt
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from config import api, UPLOAD_FOLDER, db, SALT
from db import User, CourseSkill, Achievement
from routes.auth_wrapper import auth_required
from utils import info_response, string_to_double_list, get_response_image, badge_paths, get_course_rating, \
    get_courses_only, allowed_file, validate_info, validate_password

user_bp = Blueprint("user_routes", __name__)


@user_bp.route("/get_info", methods=["GET"])
@auth_required
def get_info(current_user):
    try:
        user = User.query.filter_by(id=current_user["id"]).first()
        return jsonify({"data": info_response(user), "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/get_achievements", methods=["GET"])
@auth_required
def get_achievements(current_user):
    try:
        role = current_user["role"]
        user = User.query.filter_by(id=current_user["id"]).first()
        progress = string_to_double_list(user.badge_progress_as_student if (role == "STUDENT") else user.badge_progress_as_tutor)
        badges = [get_response_image(x) for x in badge_paths(current_user["role"])]
        icons = badges[1:]
        achievements = [*map(lambda x: {"title": x[1].title, "description": x[1].description, "progress": progress[x[0]], "icons": icons[x[0]]}, enumerate(Achievement.query.filter_by(role=role).all()))]
        return jsonify({"data": {"achievements": achievements, "badge": badges[0]}, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/get_analytics", methods=["GET"])
@auth_required
def get_analytics(current_user):
    try:
        user_id = current_user["id"]
        role = current_user["role"]
        user = User.query.filter_by(id=user_id).first()
        user_courses = CourseSkill.query.filter_by(user_id=user_id, role=role).all()
        user_courses_with_names = [*map(get_course_rating, user_courses)]
        response = {
            "points": user.student_points if (role == "STUDENT") else user.tutor_points,
            "assessmentPoints": user.student_assessment_points if (role == "STUDENT") else user.tutor_assessment_points,
            "requestPoints": user.student_request_points if (role == "STUDENT") else user.tutor_request_points,
            "sessionPoints": user.student_session_points if (role == "STUDENT") else user.tutor_session_points,
            "assignmentPoints": user.student_assignment_points if (role == "STUDENT") else user.tutor_assignment_points,
            "sessionsCompleted": user.sessions_completed_as_student if (role == "STUDENT") else user.sessions_completed_as_tutor,
            "requestsSentReceived": user.requests_sent if (role == "STUDENT") else user.requests_received,
            "requestsAccepted": user.accepted_requests if (role == "STUDENT") else user.requests_accepted,
            "requestsDenied": user.denied_requests if (role == "STUDENT") else user.requests_denied,
            "assignments": user.assignments_taken if (role == "STUDENT") else user.assignments_created,
            "assessments": user.assessments_taken_as_student if (role == "STUDENT") else user.assessments_taken_as_tutor,
            "rateNumber": user.number_of_rates_as_student if (role == "STUDENT") else user.number_of_rates_as_tutor,
            "ratedUsers": user.tutors_rated if (role == "STUDENT") else user.students_rated,
            "badgesCompleted": sum(1 for x in string_to_double_list(user.badge_progress_as_student if (role == "STUDENT") else user.badge_progress_as_tutor) if x >= 100.0),
            "rating": user.total_rating_as_student if (role == "STUDENT") else user.total_rating_as_tutor,
            "courses": user_courses_with_names
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/get_course_eligibility", methods=["GET"])
@auth_required
def get_course_eligibility(current_user):
    try:
        course_skills = [*map(get_course_rating, CourseSkill.query.filter_by(user_id=current_user["id"], role=current_user["role"]).all())]
        return jsonify({"data": course_skills, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/get_dashboard_data", methods=["GET"])
@auth_required
def get_dashboard_data(current_user):
    try:
        user_id = current_user["id"]
        role = current_user["role"]
        user_courses = [*map(get_course_rating, CourseSkill.query.filter_by(user_id=user_id, role=role).limit(3).all())]
        user = User.query.filter_by(id=user_id).first()
        response = {
            "rateNumber": user.number_of_rates_as_student if (role == "STUDENT") else user.number_of_rates_as_tutor,
            "rating": user.total_rating_as_student if (role == "STUDENT") else user.total_rating_as_tutor,
            "courses": user_courses,
            "image": get_response_image(user.image_path)
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/get_leaderboard", methods=["GET"])
@auth_required
def get_leaderboard(current_user):
    try:
        if current_user["role"] == "STUDENT":
            leaderboard = User.query.filter_by(is_banned=False).order_by((User.total_rating_as_student / User.number_of_rates_as_student).desc()).limit(20).all()
            response = [*map(lambda x: {"id": x.id, "name": x.name, "rating": x.total_rating_as_student, "rateNumber": x.number_of_rates_as_student, "image": get_response_image(x.image_path)}, leaderboard)]
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
        else:
            leaderboard = User.query.filter_by(is_banned=False).order_by((User.total_rating_as_tutor / User.number_of_rates_as_tutor).desc()).limit(20).all()
            response = [*map(lambda x: {"id": x.id, "name": x.name, "rating": x.total_rating_as_tutor, "rateNumber": x.number_of_rates_as_tutor, "image": get_response_image(x.image_path)}, leaderboard)]
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/get_profile", methods=["GET"])
@auth_required
def get_profile(current_user):
    try:
        other_id = request.args.get("other_id")
        user = User.query.filter_by(id=other_id).first()

        if user.is_banned:
            return jsonify({"error": "Not allowed to view banned account.", "type": "error"}), 500

        as_student_courses = CourseSkill.query.filter_by(user_id=other_id, role="STUDENT").limit(3).all()
        as_tutor_courses = CourseSkill.query.filter_by(user_id=other_id, role="TUTOR").limit(3).all()
        response = {
            "user": info_response(user),
            "courses": [[*map(get_courses_only, as_student_courses)], [*map(get_courses_only, as_tutor_courses)]],
            "rating": [
                {"rating": user.total_rating_as_student, "rateNumber": user.number_of_rates_as_student},
                {"rating": user.total_rating_as_tutor, "rateNumber": user.number_of_rates_as_tutor}
            ],
            "primaryLearning": user.primary_learning_pattern,
            "secondaryLearning": user.secondary_learning_pattern
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/get_current_user", methods=["GET"])
@auth_required
def get_current_user(current_user):
    try:
        return jsonify({"data": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/upload_image", methods=["POST"])
@auth_required
def upload_image(current_user):
    if 'file' not in request.files:
        return jsonify({"error": "No file part", "type": "error"}), 500
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file", "type": "error"}), 500
    if file and allowed_file(file.filename):
        try:
            user = User.query.filter_by(id=current_user["id"]).first()
            filename = secure_filename(datetime.now().strftime("%d_%m_%Y_%H_%M_%S") + '.' + file.filename.rsplit('.', 1)[1])
            file.save(os.path.join(api.config['UPLOAD_FOLDER'], filename))

            if os.path.exists(user.image_path) and user.image_path != "images/user.png":
                os.remove(user.image_path)

            user.image_path = UPLOAD_FOLDER + "/" + filename
            db.session.commit()
            return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500

    return jsonify({"error": "Error", "type": "error"}), 500


@user_bp.route("/update_info", methods=["POST"])
@auth_required
def update_info(current_user):
    try:
        data = request.get_json()
        validation = validate_info(data, current_user["name"])
        if validation["isValid"]:
            user = User.query.filter_by(id=current_user["id"]).first()
            user.name = data["name"]
            user.age = data["age"]
            user.degree = data["degree"]
            user.address = data["address"]
            user.contact_number = data["contactNumber"]
            user.summary = data["summary"]
            user.educational_background = data["educationalBackground"]
            user.free_tutoring_time = data["freeTutoringTime"]
            db.session.commit()
        return jsonify({"data": validation, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/update_password", methods=["POST"])
@auth_required
def update_password(current_user):
    try:
        data = request.get_json()
        user = User.query.filter_by(id=current_user["id"]).first()
        validation = validate_password(data["currentPassword"], data["newPassword"], data["confirmPassword"], user.password)
        if validation["isValid"]:
            user.password = bcrypt.hashpw(data["newPassword"].encode(), SALT).decode()
            db.session.commit()
        return jsonify({"data": validation, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/switch_role", methods=["POST"])
@auth_required
def switch_role(current_user):
    try:
        user = User.query.filter_by(id=current_user["id"]).first()
        if current_user["role"] == "STUDENT":
            if CourseSkill.query.filter_by(user_id=current_user["id"], role="TUTOR").all():
                user.role = "TUTOR"
                db.session.commit()
                return jsonify({"data": {"isValid": True, "message": "Switch role successful!"}, "type": "success"}), 201
            else:
                return jsonify({"data": {"isValid": False, "message": "You don't have courses eligible as tutor."}, "type": "success"}), 201
        else:
            if CourseSkill.query.filter_by(user_id=current_user["id"], role="STUDENT").all():
                user.role = "STUDENT"
                db.session.commit()
                return jsonify({"data": {"isValid": True, "message": "Switch role successful!"}, "type": "success"}), 201
            else:
                return jsonify({"data": {"isValid": False, "message": "You don't have courses eligible as student."}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@user_bp.route("/update_notifications_token", methods=["POST"])
@auth_required
def update_notifications_token(current_user):
    try:
        data = request.get_json()
        user = User.query.filter_by(id=current_user["id"]).first()
        user.push_notifications_token = data["notificationsToken"]
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500
