import re
from datetime import datetime, timedelta

from firebase_admin import messaging
from flask import Blueprint, request, jsonify

from config import db
from db import Session, Course, User, Assignment, Message
from routes.auth_wrapper import auth_required
from utils import string_to_list, map_sessions, get_archive_sessions, save_pending_multiple_choice_assessment, \
    save_pending_identification_assessment, save_pending_true_or_false_assessment, list_to_string, match_date, \
    string_to_double_list, compute_achievement_progress, check_completed_achievements

session_bp = Blueprint("session_routes", __name__)


@session_bp.route("/get_session", methods=["GET"])
@auth_required
def get_session(current_user):
    try:
        session = Session.query.filter_by(session_id=request.args.get("session_id")).first()

        if session.status == "UPCOMING":

            if current_user["role"] == "STUDENT":
                session.student_viewed = True
                db.session.commit()

            course = Course.query.filter_by(course_id=session.course_id).first()
            response = {
                "sessionId": session.session_id,
                "courseName": course.course_name,
                "tutorId": session.tutor_id,
                "tutorName": User.query.filter_by(id=session.tutor_id).first().name,
                "studentId": session.student_id,
                "studentName": User.query.filter_by(id=session.student_id).first().name,
                "moduleName": string_to_list(course.modules)[session.module_id],
                "startTime": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
                "endTime": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
                "location": session.location
            }
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
        else:
            return jsonify({"error": "Session may be completed or cancelled", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@session_bp.route("/get_session_settings", methods=["GET"])
@auth_required
def get_session_settings(current_user):
    try:
        session = Session.query.filter_by(session_id=request.args.get("session_id")).first()

        if session.status == "UPCOMING":
            response = {
                "startTime": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
                "endTime": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
                "location": session.location
            }
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
        else:
            return jsonify({"error": "Session may be completed or cancelled", "type": "error"}), 500
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@session_bp.route("/get_session_notifications", methods=["GET"])
@auth_required
def get_session_notifications(current_user):
    try:
        user_id = current_user["id"]
        role = current_user["role"]
        if role == "STUDENT":
            sessions = Session.query.filter_by(student_id=user_id, status="UPCOMING").all()
        else:
            sessions = Session.query.filter_by(tutor_id=user_id, status="UPCOMING").all()

        response = [*map(map_sessions, sessions)]
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@session_bp.route("/search_session_archives", methods=["GET"])
@auth_required
def search_session_archives(current_user):
    try:
        search_query = request.args.get("search_query")
        sessions = get_archive_sessions(current_user["role"], current_user["id"], request.args.get("status"))
        if search_query:
            response = [*filter(lambda x: re.search(search_query, x["name"], re.IGNORECASE) or re.search(search_query, x["course_name"], re.IGNORECASE) or re.search(search_query, x["location"], re.IGNORECASE) or match_date(datetime.strptime(x["start_time"], "%d/%m/%Y %I:%M %p"), search_query) or match_date(datetime.strptime(x["end_time"], "%d/%m/%Y %I:%M %p"), search_query), sessions)]
            return jsonify({"data": response, "type": "success"}), 200
        else:
            return jsonify({"data": sessions, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@session_bp.route("/complete_session_and_create_assignment", methods=["POST"])
@auth_required
def complete_session_and_create_assignment(current_user):
    try:
        data = request.get_json()
        session = Session.query.filter_by(session_id=data["sessionId"]).first()

        if session.status == "UPCOMING":
            student = User.query.filter_by(id=data["studentId"]).first()
            tutor = User.query.filter_by(id=data["tutorId"]).first()

            if data["type"] == "Multiple Choice":
                assignment_ids = [save_pending_multiple_choice_assessment(x, data["courseId"]) for x in data["data"]]
            elif data["type"] == "Identification":
                assignment_ids = [save_pending_identification_assessment(x, data["courseId"]) for x in data["data"]]
            else:
                assignment_ids = [save_pending_true_or_false_assessment(x, data["courseId"]) for x in data["data"]]

            assignment = Assignment(
                student_id=data["studentId"],
                tutor_id=data["tutorId"],
                course_id=data["courseId"],
                module_id=data["moduleId"],
                data=list_to_string(assignment_ids),
                type=data["type"],
                dead_line=datetime.strptime(data["deadLine"], "%d/%m/%Y %I:%M %p")
            )

            db.session.add(assignment)
            session.status = "COMPLETED"
            student.sessions_completed_as_student = student.sessions_completed_as_student + 1
            student.student_session_points = student.student_session_points + 0.5
            student.student_points = student.student_points + 0.5
            tutor.sessions_completed_as_tutor = tutor.sessions_completed_as_tutor + 1
            tutor.tutor_session_points = tutor.tutor_session_points + 0.5
            tutor.tutor_points = tutor.tutor_points + 0.5
            tutor.assignments_created = tutor.assignments_created + 1
            tutor.tutor_assignment_points = tutor.tutor_assignment_points + 0.5
            tutor.tutor_points = tutor.tutor_points + 0.5

            if data["rate"] > 0:
                session.tutor_rate = True
                tutor.students_rated = tutor.students_rated + 1
                student.total_rating_as_student = student.total_rating_as_student + (data["rate"] / 5.0)
                student.number_of_rates_as_student = student.number_of_rates_as_student + 1

            # Update achievement
            current_progress_student = string_to_double_list(student.badge_progress_as_student)
            computed_progress_student = compute_achievement_progress(
                student.student_points,
                [10, 25, 50, 100, 200],
                [7, 8, 9, 10, 11],
                compute_achievement_progress(
                    float(student.sessions_completed_as_student),
                    [1, 5, 10],
                    [12, 13, 14],
                    compute_achievement_progress(
                        float(student.number_of_rates_as_student),
                        [1, 5, 10],
                        [25, 26, 27],
                        current_progress_student
                    ) if data["rate"] > 0 else current_progress_student
                )
            )
            student.badge_progress_as_student = list_to_string(computed_progress_student)

            current_progress_tutor = string_to_double_list(tutor.badge_progress_as_tutor)
            computed_progress_tutor = compute_achievement_progress(
                tutor.tutor_points,
                [10, 25, 50, 100, 200],
                [7, 8, 9, 10, 11],
                compute_achievement_progress(
                    float(tutor.sessions_completed_as_tutor),
                    [1, 5, 10],
                    [12, 13, 14],
                    compute_achievement_progress(
                        float(tutor.assignments_created),
                        [1, 5, 10],
                        [19, 20, 21],
                        compute_achievement_progress(
                            float(tutor.students_rated),
                            [1, 5, 10],
                            [22, 23, 24],
                            current_progress_tutor
                        ) if data["rate"] > 0 else current_progress_tutor
                    )
                )
            )
            tutor.badge_progress_as_tutor = list_to_string(computed_progress_tutor)

            notification = messaging.Message(
                data={
                    "title": "Session Completed",
                    "body": f"{tutor.name} completed the session and made your task."
                },
                android=messaging.AndroidConfig(priority="high"),
                token=student.push_notifications_token
            )

            messaging.send(notification)

            db.session.commit()
            response = check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")
            return jsonify({"data": response, "type": "success"}), 201
        else:
            return jsonify({"error": "Session may be completed or cancelled", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@session_bp.route("/create_session", methods=["POST"])
@auth_required
def create_session(current_user):
    try:
        data = request.get_json()
        message = Message.query.filter_by(message_id=data["messageId"]).first()

        if message.status == "WAITING":
            start_time = datetime.strptime(data["startTime"], "%d/%m/%Y %I:%M %p")
            end_time = datetime.strptime(data["endTime"], "%d/%m/%Y %I:%M %p")
            student = User.query.filter_by(id=data["studentId"]).first()
            tutor = User.query.filter_by(id=data["tutorId"]).first()
            session = Session(
                course_id=data["courseId"],
                tutor_id=data["tutorId"],
                student_id=data["studentId"],
                module_id=data["moduleId"],
                start_time=start_time,
                end_time=end_time,
                location=data["location"],
                expire_date=end_time + timedelta(days=7)
            )
            db.session.add(session)
            message.status = "ACCEPT"
            student.accepted_requests = student.accepted_requests + 1
            student.student_request_points = student.student_request_points + 0.2
            student.student_points = student.student_points + 0.2
            tutor.requests_accepted = tutor.requests_accepted + 1
            tutor.tutor_request_points = tutor.tutor_request_points + 0.2
            tutor.tutor_points = tutor.tutor_points + 0.2

            # Update achievement
            current_progress_student = string_to_double_list(student.badge_progress_as_student)
            computed_progress_student = compute_achievement_progress(
                student.student_points,
                [10, 25, 50, 100, 200],
                [7, 8, 9, 10, 11],
                compute_achievement_progress(
                    float(student.accepted_requests),
                    [1, 3, 10],
                    [4, 5, 6],
                    current_progress_student
                )
            )
            student.badge_progress_as_student = list_to_string(computed_progress_student)

            current_progress_tutor = string_to_double_list(tutor.badge_progress_as_tutor)
            computed_progress_tutor = compute_achievement_progress(
                tutor.tutor_points,
                [10, 25, 50, 100, 200],
                [7, 8, 9, 10, 11],
                compute_achievement_progress(
                    float(tutor.requests_accepted),
                    [1, 5, 10, 20],
                    [0, 1, 2, 3],
                    current_progress_tutor
                )
            )
            tutor.badge_progress_as_tutor = list_to_string(computed_progress_tutor)

            notification = messaging.Message(
                data={
                    "title": "Request Accepted",
                    "body": f"{tutor.name} accepted your request and created session."
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


@session_bp.route("/update_session", methods=["POST"])
@auth_required
def update_session(current_user):
    try:
        data = request.get_json()
        session = Session.query.filter_by(session_id=data["sessionId"]).first()

        if session.status == "UPCOMING":
            session.start_time = datetime.strptime(data["startTime"], "%d/%m/%Y %I:%M %p")
            session.end_time = datetime.strptime(data["endTime"], "%d/%m/%Y %I:%M %p")
            session.location = data["location"]
            session.expire_date = datetime.strptime(data["endTime"], "%d/%m/%Y %I:%M %p") + timedelta(days=7)
            session.student_viewed = False

            db.session.commit()
            return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
        else:
            return jsonify({"error": "Session may be completed or cancelled", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@session_bp.route("/rate_user", methods=["POST"])
@auth_required
def rate_user(current_user):
    try:
        data = request.get_json()
        session = Session.query.filter_by(session_id=data["sessionId"]).first()
        if current_user["role"] == "STUDENT":
            session.student_rate = True
            student = User.query.filter_by(id=current_user["id"]).first()
            tutor = User.query.filter_by(id=data["otherId"]).first()
            student.tutors_rated = student.tutors_rated + 1
            tutor.total_rating_as_tutor = tutor.total_rating_as_tutor + (data["rate"] / 5.0)
            tutor.number_of_rates_as_tutor = tutor.number_of_rates_as_tutor + 1

            # Update achievement
            current_progress_student = string_to_double_list(student.badge_progress_as_student)
            computed_progress_student = compute_achievement_progress(
                student.tutors_rated,
                [1, 5, 10],
                [22, 23, 24],
                current_progress_student
            )
            student.badge_progress_as_student = list_to_string(computed_progress_student)

            current_progress_tutor = string_to_double_list(tutor.badge_progress_as_tutor)
            computed_progress_tutor = compute_achievement_progress(
                tutor.number_of_rates_as_tutor,
                [1, 5, 10],
                [25, 26, 27],
                current_progress_tutor
            )
            tutor.badge_progress_as_tutor = list_to_string(computed_progress_tutor)

            db.session.commit()
            response = check_completed_achievements(current_progress_student, computed_progress_student, "STUDENT")
            return jsonify({"data": response, "type": "success"}), 200
        else:
            session.tutor_rate = True
            tutor = User.query.filter_by(id=current_user["id"]).first()
            student = User.query.filter_by(id=data["otherId"]).first()
            tutor.students_rated = tutor.students_rated + 1
            student.total_rating_as_student = student.total_rating_as_student + (data["rate"] / 5.0)
            student.number_of_rates_as_student = student.number_of_rates_as_student + 1

            # Update achievement
            current_progress_student = string_to_double_list(student.badge_progress_as_student)
            computed_progress_student = compute_achievement_progress(
                student.number_of_rates_as_student,
                [1, 5, 10],
                [25, 26, 27],
                current_progress_student
            )
            student.badge_progress_as_student = list_to_string(computed_progress_student)

            current_progress_tutor = string_to_double_list(tutor.badge_progress_as_tutor)
            computed_progress_tutor = compute_achievement_progress(
                tutor.students_rated,
                [1, 5, 10],
                [22, 23, 24],
                current_progress_tutor
            )
            tutor.badge_progress_as_tutor = list_to_string(computed_progress_tutor)

            db.session.commit()
            response = check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")
            return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500