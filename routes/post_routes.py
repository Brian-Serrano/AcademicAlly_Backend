import os
from datetime import datetime, timedelta

import bcrypt
from flask import request, jsonify, Blueprint
from werkzeug.utils import secure_filename

from config import api, UPLOAD_FOLDER, db, SALT
from db import User, Message, Assignment, Session
from routes.auth_wrapper import auth_required
from utils import allowed_file, string_to_double_list, compute_achievement_progress, list_to_string, \
    check_completed_achievements, validate_info, validate_password, update_course_eligibility


post_bp = Blueprint("post_routes", __name__)


@post_bp.route("/upload_image", methods=["POST"])
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
            user.image_path = UPLOAD_FOLDER + "/" + filename
            db.session.commit()
            return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500

    return jsonify({"error": "Error", "type": "error"}), 500


@post_bp.route("/reject_student", methods=["POST"])
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

            db.session.commit()
            response = check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")
            return jsonify({"data": response, "type": "success"}), 201
        else:
            return jsonify({"error": "Message may be accepted or rejected", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@post_bp.route("/update_info", methods=["POST"])
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


@post_bp.route("/update_password", methods=["POST"])
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


@post_bp.route("/switch_role", methods=["POST"])
@auth_required
def switch_role(current_user):
    try:
        user = User.query.filter_by(id=current_user["id"]).first()
        user.role = "TUTOR" if (current_user["role"] == "STUDENT") else "STUDENT"
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@post_bp.route("/complete_assessment", methods=["POST"])
@auth_required
def complete_assessment(current_user):
    try:
        data = request.get_json()
        response = update_course_eligibility(data["courseId"], current_user["id"], data["rating"], data["score"])
        return jsonify({"data": response, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@post_bp.route("/complete_assignment", methods=["POST"])
@auth_required
def complete_assignment(current_user):
    try:
        data = request.get_json()
        assignment = Assignment.query.filter_by(assignment_id=data["assignmentId"]).first()

        if assignment.status == "UNCOMPLETED":
            student = User.query.filter_by(id=current_user["id"]).first()
            assignment.student_score = data["score"]
            assignment.status = "COMPLETED"
            student.assignments_taken = student.assignments_taken + 1
            student.student_assignment_points = student.student_assignment_points + (data["score"] * 0.1)
            student.student_points = student.student_points + (data["score"] * 0.1)

            # Update achievement
            current_progress_student = string_to_double_list(student.badge_progress_as_student)
            computed_progress_student = compute_achievement_progress(
                student.student_points,
                [10, 25, 50, 100, 200],
                [7, 8, 9, 10, 11],
                compute_achievement_progress(
                    float(student.assignments_taken),
                    [1, 5, 10],
                    [19, 20, 21],
                    current_progress_student
                )
            )
            student.badge_progress_as_student = list_to_string(computed_progress_student)

            db.session.commit()
            response = check_completed_achievements(current_progress_student, computed_progress_student, "STUDENT")
            return jsonify({"data": response, "type": "success"}), 201
        else:
            return jsonify({"error": "Assignment may be completed or deadlined", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@post_bp.route("/complete_session_and_create_assignment", methods=["POST"])
@auth_required
def complete_session_and_create_assignment(current_user):
    try:
        data = request.get_json()
        session = Session.query.filter_by(session_id=data["sessionId"]).first()

        if session.status == "UPCOMING":
            student = User.query.filter_by(id=data["studentId"]).first()
            tutor = User.query.filter_by(id=data["tutorId"]).first()
            assignment = Assignment(
                student_id=data["studentId"],
                tutor_id=data["tutorId"],
                course_id=data["courseId"],
                module_id=data["moduleId"],
                data=data["data"],
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

            db.session.commit()
            response = check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")
            return jsonify({"data": response, "type": "success"}), 201
        else:
            return jsonify({"error": "Session may be completed or cancelled", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@post_bp.route("/create_session", methods=["POST"])
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

            db.session.commit()
            response = check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")
            return jsonify({"data": response, "type": "success"}), 201
        else:
            return jsonify({"error": "Message may be accepted or rejected", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@post_bp.route("/update_session", methods=["POST"])
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


@post_bp.route("/send_tutor_request", methods=["POST"])
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

            db.session.commit()
            return jsonify({"achievements": check_completed_achievements(current_progress_student, computed_progress_student, "STUDENT"), "type": "success"}), 201
        else:
            return jsonify({"message": "Tutor can only be message once.", "type": "duplicate"}), 401
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@post_bp.route("/rate_user", methods=["POST"])
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
            tutor.total_rating_as_tutor = tutor.total_rating_as_tutor + 1
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
            return jsonify(check_completed_achievements(current_progress_student, computed_progress_student, "STUDENT")), 200
        else:
            session.tutor_rate = True
            tutor = User.query.filter_by(id=current_user["id"]).first()
            student = User.query.filter_by(id=data["otherId"]).first()
            tutor.students_rated = tutor.students_rated + 1
            student.total_rating_as_student = student.total_rating_as_student + 1
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


@post_bp.route("/complete_learning_pattern_assessment", methods=["POST"])
@auth_required
def complete_learning_pattern_assessment(current_user):
    try:
        data = request.get_json()
        user = User.query.filter_by(id=current_user["id"]).first()
        learning_style = sorted(data, key=data.get, reverse=True)[:2]
        user.primary_learning_pattern = learning_style[0].title()
        user.secondary_learning_pattern = learning_style[1].title()
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500
