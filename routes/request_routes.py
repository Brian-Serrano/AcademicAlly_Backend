import re

from firebase_admin import messaging
from flask import Blueprint, request, jsonify

from config import db
from db import Message, Course, User, CourseSkill
from routes.auth_wrapper import auth_required
from utils import string_to_list, get_response_image, get_course_rating, get_course_module, map_messages, \
    get_tutor_datas, map_archive_messages, string_to_double_list, compute_achievement_progress, list_to_string, \
    check_completed_achievements

request_bp = Blueprint("request_routes", __name__)


@request_bp.route("/get_student", methods=["GET"])
@auth_required
def get_student(current_user):
    try:
        message = Message.query.filter_by(message_id=request.args.get("message_id")).first()

        if message.status == "WAITING":

            if current_user["role"] == "TUTOR":
                message.tutor_viewed = True
                db.session.commit()

            course = Course.query.filter_by(course_id=message.course_id).first()
            user = User.query.filter_by(id=message.tutor_id if (current_user["role"] == "STUDENT") else message.student_id).first()

            if user.is_banned:
                return jsonify({"error": "Not allowed to view banned account.", "type": "error"}), 500

            response = {
                "messageId": message.message_id,
                "studentId": message.student_id,
                "tutorId": message.tutor_id,
                "courseName": course.course_name,
                "moduleName": string_to_list(course.modules)[message.module_id],
                "studentMessage": message.student_message,
                "userId": user.id,
                "name": user.name,
                "degree": user.degree,
                "age": user.age,
                "address": user.address,
                "contactNumber": user.contact_number,
                "summary": user.summary,
                "educationalBackground": user.educational_background,
                "image": get_response_image(user.image_path),
                "primaryLearning": user.primary_learning_pattern,
                "secondaryLearning": user.secondary_learning_pattern
            }
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
        else:
            return jsonify({"error": "Message may be accepted or rejected", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@request_bp.route("/get_tutor", methods=["GET"])
@auth_required
def get_tutor(current_user):
    try:
        tutor_id = request.args.get("tutor_id")
        tutor = User.query.filter_by(id=tutor_id).first()
        tutor_courses = CourseSkill.query.filter_by(user_id=tutor_id, role="TUTOR").all()
        tutor_courses_with_names = [*map(get_course_rating, tutor_courses)]

        if tutor.is_banned:
            return jsonify({"error": "Not allowed to view banned account.", "type": "error"}), 500

        response = {
            "performanceRating": tutor.total_rating_as_tutor,
            "numberOfRates": tutor.number_of_rates_as_tutor,
            "tutorCourses": tutor_courses_with_names,
            "userId": tutor.id,
            "name": tutor.name,
            "degree": tutor.degree,
            "age": tutor.age,
            "address": tutor.address,
            "contactNumber": tutor.contact_number,
            "summary": tutor.summary,
            "educationalBackground": tutor.educational_background,
            "image": get_response_image(tutor.image_path),
            "freeTutoringTime": tutor.free_tutoring_time,
            "primaryLearning": tutor.primary_learning_pattern,
            "secondaryLearning": tutor.secondary_learning_pattern
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@request_bp.route("/get_message", methods=["GET"])
@auth_required
def get_message(current_user):
    try:
        message = Message.query.filter_by(message_id=request.args.get("message_id")).first()

        if message.status == "WAITING":
            response = {
                "messageId": message.message_id,
                "courseId": message.course_id,
                "moduleId": message.module_id,
                "studentId": message.student_id,
                "tutorId": message.tutor_id,
                "studentMessage": message.student_message
            }
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
        else:
            return jsonify({"error": "Message may be accepted or rejected", "type": "error"}), 500
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@request_bp.route("/get_tutor_eligible_courses", methods=["GET"])
@auth_required
def get_tutor_eligible_courses(current_user):
    try:
        tutor_id = request.args.get("tutor_id")
        tutor_course_skills = CourseSkill.query.filter_by(user_id=tutor_id, role="TUTOR").all()
        tutor_courses = [*map(get_course_module, tutor_course_skills)]
        tutor = User.query.filter_by(id=tutor_id).first()

        if tutor.is_banned:
            return jsonify({"error": "Not allowed to view banned account.", "type": "error"}), 500

        response = {
            "tutorName": tutor.name,
            "tutorCourses": tutor_courses
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@request_bp.route("/get_message_notifications", methods=["GET"])
@auth_required
def get_message_notifications(current_user):
    try:
        user_id = current_user["id"]
        role = current_user["role"]
        if role == "STUDENT":
            messages = Message.query.filter_by(student_id=user_id, status="WAITING").all()
        else:
            messages = Message.query.filter_by(tutor_id=user_id, status="WAITING").all()

        response = [*map(lambda x: map_messages(x, role), messages)]
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@request_bp.route("/get_tutors", methods=["GET"])
@auth_required
def get_tutors(current_user):
    try:
        user_id = current_user["id"]
        course_skills = CourseSkill.query.filter_by(user_id=user_id, role="STUDENT").all()
        course_skill_ids = [*map(lambda x: x.course_id, course_skills)]
        courses = Course.query.all()
        response = {
            "studentCourseIds": course_skill_ids,
            "courses": [*map(lambda x: {"id": x.course_id, "name": x.course_name}, courses)],
            "tutors": get_tutor_datas(course_skill_ids, "", user_id, current_user["primaryLearning"], current_user["secondaryLearning"])
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@request_bp.route("/search_tutor", methods=["GET"])
@auth_required
def search_tutor(current_user):
    try:
        filters = request.args.get("course_filter").split(',') if request.args.get("course_filter") else []
        response = get_tutor_datas([int(x) for x in filters], request.args.get("search_query"), current_user["id"], current_user["primaryLearning"], current_user["secondaryLearning"])
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@request_bp.route("/search_message_archives", methods=["GET"])
@auth_required
def search_message_archives(current_user):
    try:
        search_query = request.args.get("search_query")
        messages = map_archive_messages(current_user["role"], current_user["id"], request.args.get("status"))
        if search_query:
            response = [*filter(lambda x: re.search(search_query, x["name"], re.IGNORECASE) or re.search(search_query, x["course_name"], re.IGNORECASE), messages)]
            return jsonify({"data": response, "type": "success"}), 200
        else:
            return jsonify({"data": messages, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@request_bp.route("/reject_student", methods=["POST"])
@auth_required
def reject_student(current_user):
    try:
        data = request.get_json()
        message = Message.query.filter_by(message_id=data["messageId"]).first()

        if message.status == "WAITING":
            student = User.query.filter_by(id=data["studentId"]).first()
            tutor = User.query.filter_by(id=data["tutorId"]).first()
            message.status = "REJECT"
            student.denied_requests = student.denied_requests + 1
            tutor.requests_denied = tutor.requests_denied + 1

            # Update achievement
            current_progress_tutor = string_to_double_list(tutor.badge_progress_as_tutor)
            computed_progress_tutor = compute_achievement_progress(
                float(tutor.requests_denied),
                [1, 3, 10],
                [4, 5, 6],
                current_progress_tutor
            )
            tutor.badge_progress_as_tutor = list_to_string(computed_progress_tutor)

            notification = messaging.Message(
                data={
                    "title": "Request Rejected",
                    "body": f"{tutor.name} rejected your tutoring request."
                },
                android=messaging.AndroidConfig(priority="high"),
                token=student.push_notifications_token
            )

            messaging.send(notification)

            db.session.commit()
            response = check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")
            return jsonify({"data": response, "type": "success"}), 201
        else:
            return jsonify({"error": "Message may be accepted or rejected", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@request_bp.route("/send_tutor_request", methods=["POST"])
@auth_required
def send_tutor_request(current_user):
    try:
        data = request.get_json()
        message = Message.query.filter_by(student_id=data["studentId"], tutor_id=data["tutorId"], status="WAITING").all()

        if not message:
            new_message = Message(
                course_id=data["courseId"],
                module_id=data["moduleId"],
                student_id=data["studentId"],
                tutor_id=data["tutorId"],
                student_message=data["studentMessage"]
            )
            db.session.add(new_message)
            student = User.query.filter_by(id=data["studentId"]).first()
            tutor = User.query.filter_by(id=data["tutorId"]).first()
            student.requests_sent = student.requests_sent + 1
            student.student_request_points = student.student_request_points + 0.1
            student.student_points = student.student_points + 0.1
            tutor.requests_received = tutor.requests_received + 1
            tutor.tutor_request_points = tutor.tutor_request_points + 0.1
            tutor.tutor_points = tutor.tutor_points + 0.1

            # Update achievement
            current_progress_student = string_to_double_list(student.badge_progress_as_student)
            computed_progress_student = compute_achievement_progress(
                student.student_points,
                [10, 25, 50, 100, 200],
                [7, 8, 9, 10, 11],
                compute_achievement_progress(
                    float(student.requests_sent),
                    [1, 5, 10, 20],
                    [0, 1, 2, 3],
                    current_progress_student
                )
            )
            student.badge_progress_as_student = list_to_string(computed_progress_student)

            current_progress_tutor = string_to_double_list(tutor.badge_progress_as_tutor)
            computed_progress_tutor = compute_achievement_progress(
                tutor.tutor_points,
                [10, 25, 50, 100, 200],
                [7, 8, 9, 10, 11],
                current_progress_tutor
            )
            tutor.badge_progress_as_tutor = list_to_string(computed_progress_tutor)

            notification = messaging.Message(
                data={
                    "title": "Requesting Tutoring",
                    "body": f"{student.name} requests tutoring with you."
                },
                android=messaging.AndroidConfig(priority="high"),
                token=tutor.push_notifications_token
            )

            messaging.send(notification)

            db.session.commit()
            return jsonify({"achievements": check_completed_achievements(current_progress_student, computed_progress_student, "STUDENT"), "type": "success"}), 201
        else:
            return jsonify({"message": "Tutor can only be message once.", "type": "duplicate"}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500
