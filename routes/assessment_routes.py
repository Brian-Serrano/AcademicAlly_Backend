from flask import Blueprint, request, jsonify
from sqlalchemy import func

from config import db
from db import Course, MultipleChoiceAssessment, IdentificationAssessment, TrueOrFalseAssessment, \
    LearningPatternAssessment, User
from routes.auth_wrapper import auth_optional, auth_required
from utils import map_pattern_assessment, update_course_eligibility

assessment_bp = Blueprint("assessment_routes", __name__)


@assessment_bp.route("/get_course_name_and_desc", methods=["GET"])
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


@assessment_bp.route("/get_assessment", methods=["GET"])
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


@assessment_bp.route("/get_courses", methods=["GET"])
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


@assessment_bp.route("/get_learning_pattern_assessment", methods=["GET"])
@auth_required
def get_learning_pattern_assessment(current_user):
    try:
        assessment = LearningPatternAssessment.query.order_by(func.random()).all()
        return jsonify({"data": [map_pattern_assessment(x) for x in assessment], "currentUser": current_user, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@assessment_bp.route("/complete_assessment", methods=["POST"])
@auth_required
def complete_assessment(current_user):
    try:
        data = request.get_json()
        response = update_course_eligibility(data["courseId"], current_user["id"], data["rating"], data["score"])
        return jsonify({"data": response, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@assessment_bp.route("/complete_learning_pattern_assessment", methods=["POST"])
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