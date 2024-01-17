import re
from datetime import datetime

from flask import request, jsonify, Blueprint
from sqlalchemy import func

from config import db
from db import Session, Course, User, Message, CourseSkill, MultipleChoiceAssessment, IdentificationAssessment, \
    TrueOrFalseAssessment, Assignment, Achievement, LearningPatternAssessment
from routes.auth_wrapper import auth_required, auth_optional
from utils import string_to_list, get_course_rating, info_response, string_to_double_list, get_course_module, \
    map_messages, map_sessions, map_assignments, get_courses_only, get_tutor_datas, get_archive_sessions, \
    map_archive_messages, map_archive_assignments, map_pattern_assessment, match_date, get_response_image, badge_paths

get_bp = Blueprint("get_routes", __name__)


@get_bp.route("/get_session", methods=["GET"])
@auth_required
def get_session(current_user):
    try:
        session = Session.query.filter_by(session_id=request.args.get("session_id")).first()

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
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_session_for_assignment", methods=["GET"])
@auth_required
def get_session_for_assignment(current_user):
    try:
        session = Session.query.filter_by(session_id=request.args.get("session_id")).first()
        course = Course.query.filter_by(course_id=session.course_id).first()
        response = {
            "sessionId": session.session_id,
            "courseName": course.course_name,
            "moduleName": string_to_list(course.modules)[session.module_id],
            "startTime": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
            "endTime": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
            "location": session.location,
            "studentId": session.student_id,
            "tutorId": session.tutor_id,
            "courseId": session.course_id,
            "moduleId": session.module_id
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_student", methods=["GET"])
@auth_required
def get_student(current_user):
    try:
        message = Message.query.filter_by(message_id=request.args.get("message_id")).first()

        if current_user["role"] == "TUTOR":
            message.tutor_viewed = True
            db.session.commit()

        course = Course.query.filter_by(course_id=message.course_id).first()
        user = User.query.filter_by(id=message.tutor_id if (current_user["role"] == "STUDENT") else message.student_id).first()
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
            "image": get_response_image(user.image_path)
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_tutor", methods=["GET"])
@auth_required
def get_tutor(current_user):
    try:
        tutor_id = request.args.get("tutor_id")
        tutor = User.query.filter_by(id=tutor_id).first()
        tutor_courses = CourseSkill.query.filter_by(user_id=tutor_id, role="TUTOR").all()
        tutor_courses_with_names = [*map(get_course_rating, tutor_courses)]
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
            "image": get_response_image(tutor.image_path)
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_info", methods=["GET"])
@auth_required
def get_info(current_user):
    try:
        user = User.query.filter_by(id=current_user["id"]).first()
        return jsonify({"data": info_response(user), "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_achievements", methods=["GET"])
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


@get_bp.route("/get_analytics", methods=["GET"])
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


@get_bp.route("/get_course_name_and_desc", methods=["GET"])
@auth_optional
def get_course_name_and_desc(current_user):
    try:
        course = Course.query.filter_by(course_id=request.args.get("course_id")).first()
        response = {
            "name": course.course_name,
            "description": course.course_description
        }
        if current_user:
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
        else:
            return jsonify({"data": response, "type": "unauthorized"}), 250
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_assessment", methods=["GET"])
@auth_optional
def get_assessment(current_user):
    try:
        course_id = request.args.get("course_id")
        items = request.args.get("items")
        category = request.args.get("category")
        if category == "Multiple Choice":
            assessment_obj = MultipleChoiceAssessment.query.filter_by(course_id=course_id).order_by(func.random()).limit(items).all()
            assessment = [*map(lambda x: [x.module, x.question, x.letter_a, x.letter_b, x.letter_c, x.letter_d, x.answer, x.creator], assessment_obj)]
        elif category == "Identification":
            assessment_obj = IdentificationAssessment.query.filter_by(course_id=course_id).order_by(func.random()).limit(items).all()
            assessment = [*map(lambda x: [x.module, x.question, x.answer, x.creator], assessment_obj)]
        else:
            assessment_obj = TrueOrFalseAssessment.query.filter_by(course_id=course_id).order_by(func.random()).limit(items).all()
            assessment = [*map(lambda x: [x.module, x.question, str(x.answer), x.creator], assessment_obj)]

        course = Course.query.filter_by(course_id=course_id).first()
        response = {
            "name": course.course_name,
            "description": course.course_description,
            "assessmentData": assessment
        }
        if current_user:
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
        else:
            return jsonify({"data": response, "type": "unauthorized"}), 250
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_assignment", methods=["GET"])
@auth_required
def get_assignment(current_user):
    try:
        assignment = Assignment.query.filter_by(assignment_id=request.args.get("assignment_id")).first()

        if current_user["role"] == "STUDENT":
            assignment.student_viewed = True
            db.session.commit()

        course = Course.query.filter_by(course_id=assignment.course_id).first()
        response = {
            "name": course.course_name,
            "description": course.course_description,
            "type": assignment.type,
            "data": assignment.data
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_courses", methods=["GET"])
@auth_optional
def get_courses(current_user):
    try:
        courses = [*map(lambda x: {"id": x.course_id, "name": x.course_name, "description": x.course_description}, Course.query.all())]
        if current_user:
            return jsonify({"data": courses, "currentUser": current_user, "type": "success"}), 200
        else:
            return jsonify({"data": courses, "type": "unauthorized"}), 250
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_course_eligibility", methods=["GET"])
@auth_required
def get_course_eligibility(current_user):
    try:
        course_skills = [*map(get_course_rating, CourseSkill.query.filter_by(user_id=current_user["id"], role=current_user["role"]).all())]
        return jsonify({"data": course_skills, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_message", methods=["GET"])
@auth_required
def get_message(current_user):
    try:
        message = Message.query.filter_by(message_id=request.args.get("message_id")).first()
        response = {
            "messageId": message.message_id,
            "courseId": message.course_id,
            "moduleId": message.module_id,
            "studentId": message.student_id,
            "tutorId": message.tutor_id,
            "studentMessage": message.student_message
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_dashboard_data", methods=["GET"])
@auth_required
def get_dashboard_data(current_user):
    try:
        user_id = current_user["id"]
        role = current_user["role"]
        user_courses = [*map(get_course_rating, CourseSkill.query.filter_by(user_id=user_id, role=role).all())]
        user = User.query.filter_by(id=user_id).first()
        response = {
            "rateNumber": user.number_of_rates_as_student if (role == "STUDENT") else user.number_of_rates_as_tutor,
            "rating": user.total_rating_as_student if (role == "STUDENT") else user.total_rating_as_tutor,
            "courses": user_courses,
            "primaryLearning": user.primary_learning_pattern,
            "secondaryLearning": user.secondary_learning_pattern,
            "image": get_response_image(user.image_path)
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_session_settings", methods=["GET"])
@auth_required
def get_session_settings(current_user):
    try:
        session = Session.query.filter_by(session_id=request.args.get("session_id")).first()
        response = {
            "startTime": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
            "endTime": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
            "location": session.location
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_leaderboard", methods=["GET"])
@auth_required
def get_leaderboard(current_user):
    try:
        if current_user["role"] == "STUDENT":
            leaderboard = User.query.order_by((User.total_rating_as_student / User.number_of_rates_as_student).desc()).limit(20).all()
            response = [*map(lambda x: {"id": x.id, "name": x.name, "rating": x.total_rating_as_student, "rateNumber": x.number_of_rates_as_student, "image": get_response_image(x.image_path)}, leaderboard)]
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
        else:
            leaderboard = User.query.order_by((User.total_rating_as_tutor / User.number_of_rates_as_tutor).desc()).limit(20).all()
            response = [*map(lambda x: {"id": x.id, "name": x.name, "rating": x.total_rating_as_tutor, "rateNumber": x.number_of_rates_as_tutor, "image": get_response_image(x.image_path)}, leaderboard)]
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_tutor_eligible_courses", methods=["GET"])
@auth_required
def get_tutor_eligible_courses(current_user):
    try:
        tutor_id = request.args.get("tutor_id")
        tutor_course_skills = CourseSkill.query.filter_by(user_id=tutor_id, role="TUTOR").all()
        tutor_courses = [*map(get_course_module, tutor_course_skills)]
        response = {
            "tutorName": User.query.filter_by(id=tutor_id).first().name,
            "tutorCourses": tutor_courses
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_message_notifications", methods=["GET"])
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


@get_bp.route("/get_session_notifications", methods=["GET"])
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


@get_bp.route("/get_assignment_notifications", methods=["GET"])
@auth_required
def get_assignment_notifications(current_user):
    try:
        user_id = current_user["id"]
        role = current_user["role"]
        if role == "STUDENT":
            assignments = Assignment.query.filter_by(student_id=user_id, status="UNCOMPLETED").all()
        else:
            assignments = Assignment.query.filter_by(tutor_id=user_id, status="UNCOMPLETED").all()

        response = [*map(map_assignments, assignments)]
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_profile", methods=["GET"])
@auth_required
def get_profile(current_user):
    try:
        other_id = request.args.get("other_id")
        user = User.query.filter_by(id=other_id).first()
        as_student_courses = CourseSkill.query.filter_by(user_id=other_id, role="STUDENT").all()
        as_tutor_courses = CourseSkill.query.filter_by(user_id=other_id, role="TUTOR").all()
        response = {
            "user": info_response(user),
            "courses": [[*map(get_courses_only, as_student_courses)], [*map(get_courses_only, as_tutor_courses)]],
            "rating": [
                {"rating": user.total_rating_as_student, "rateNumber": user.number_of_rates_as_student},
                {"rating": user.total_rating_as_tutor, "rateNumber": user.number_of_rates_as_tutor}
            ]
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_tutors", methods=["GET"])
@auth_required
def get_tutors(current_user):
    try:
        user_id = current_user["id"]
        user = User.query.filter_by(id=user_id).first()
        course_skills = CourseSkill.query.filter_by(user_id=user_id, role="STUDENT").all()
        course_skill_ids = [*map(lambda x: x.course_id, course_skills)]
        courses = Course.query.all()
        response = {
            "primaryPattern": user.primary_learning_pattern,
            "secondaryPattern": user.secondary_learning_pattern,
            "studentCourseIds": course_skill_ids,
            "courses": [*map(lambda x: {"id": x.course_id, "name": x.course_name}, courses)],
            "tutors": get_tutor_datas(course_skill_ids, "", user_id)
        }
        return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/search_tutor", methods=["GET"])
@auth_required
def search_tutor(current_user):
    try:
        response = get_tutor_datas([int(x) for x in request.args.get("course_filter").split(',')], request.args.get("search_query"), current_user["id"])
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/search_message_archives", methods=["GET"])
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


@get_bp.route("/search_session_archives", methods=["GET"])
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


@get_bp.route("/search_assignment_archives", methods=["GET"])
@auth_required
def search_assignment_archives(current_user):
    try:
        search_query = request.args.get("search_query")
        assignments = map_archive_assignments(current_user["role"], current_user["id"], request.args.get("status"))
        if search_query:
            response = [*filter(lambda x: re.search(search_query, x["course_name"], re.IGNORECASE) or re.search(search_query, x["module_name"], re.IGNORECASE) or re.search(search_query, x["type"], re.IGNORECASE) or match_date(datetime.strptime(x["dead_line"], "%d/%m/%Y %I:%M %p"), search_query), assignments)]
            return jsonify({"data": response, "type": "success"}), 200
        else:
            return jsonify({"data": assignments, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_learning_pattern_assessment", methods=["GET"])
@auth_required
def get_learning_pattern_assessment(current_user):
    try:
        assessment = LearningPatternAssessment.query.order_by(func.random()).all()
        return jsonify({"data": [map_pattern_assessment(x) for x in assessment], "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@get_bp.route("/get_current_user", methods=["GET"])
@auth_required
def get_current_user(current_user):
    try:
        return jsonify({"data": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500
