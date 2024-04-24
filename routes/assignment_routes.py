import re
from datetime import datetime

from flask import Blueprint, request, jsonify

from config import db
from db import Session, Course, Assignment, User
from routes.auth_wrapper import auth_required
from utils import string_to_list, map_multiple_choice_assignment, map_identification_assignment, \
    map_true_or_false_assignment, string_to_int_list, map_assignments, map_archive_assignments, string_to_double_list, \
    compute_achievement_progress, match_date, list_to_string, check_completed_achievements

assignment_bp = Blueprint("assignment_routes", __name__)


@assignment_bp.route("/get_session_for_assignment", methods=["GET"])
@auth_required
def get_session_for_assignment(current_user):
    try:
        session = Session.query.filter_by(session_id=request.args.get("session_id")).first()

        if session.status == "UPCOMING":
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
        else:
            return jsonify({"error": "Session may be completed or cancelled", "type": "error"}), 500
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@assignment_bp.route("/get_assignment", methods=["GET"])
@auth_required
def get_assignment(current_user):
    try:
        assignment = Assignment.query.filter_by(assignment_id=request.args.get("assignment_id")).first()

        if assignment.status == "UNCOMPLETED":

            if current_user["role"] == "STUDENT":
                assignment.student_viewed = True
                db.session.commit()

            course = Course.query.filter_by(course_id=assignment.course_id).first()

            if assignment.type == "Multiple Choice":
                assessment = [*map(map_multiple_choice_assignment, string_to_int_list(assignment.data))]
            elif assignment.type == "Identification":
                assessment = [*map(map_identification_assignment, string_to_int_list(assignment.data))]
            else:
                assessment = [*map(map_true_or_false_assignment, string_to_int_list(assignment.data))]

            response = {
                "name": course.course_name,
                "description": course.course_description,
                "type": assignment.type,
                "data": assessment
            }
            return jsonify({"data": response, "currentUser": current_user, "type": "success"}), 200
        else:
            return jsonify({"error": "Assignment may be completed or deadlined", "type": "error"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@assignment_bp.route("/get_assignment_notifications", methods=["GET"])
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


@assignment_bp.route("/search_assignment_archives", methods=["GET"])
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


@assignment_bp.route("/complete_assignment", methods=["POST"])
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