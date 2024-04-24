from flask import Blueprint, request, jsonify

from config import db
from db import PendingMultipleChoiceAssessment, MultipleChoiceAssessment, PendingIdentificationAssessment, \
    IdentificationAssessment, PendingTrueOrFalseAssessment, TrueOrFalseAssessment, Course
from routes.admin_auth_wrapper import admin_auth_required
from utils import map_assessments

admin_assessment_bp = Blueprint("admin_assessment_routes", __name__)


@admin_assessment_bp.route("/approve_multiple_choice_question", methods=["POST"])
@admin_auth_required
def approve_multiple_choice_question(current_admin):
    try:
        data = request.get_json()
        pending_assessment = PendingMultipleChoiceAssessment.query.filter_by(assessment_id=data["assessmentId"]).first()
        pending_assessment.status = "APPROVED"
        multiple_choice = MultipleChoiceAssessment(
            course_id=data["courseId"],
            module=data["module"],
            question=data["question"],
            letter_a=data["letterA"],
            letter_b=data["letterB"],
            letter_c=data["letterC"],
            letter_d=data["letterD"],
            answer=data["answer"],
            creator=data["creator"]
        )
        db.session.add(multiple_choice)
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/approve_identification_question", methods=["POST"])
@admin_auth_required
def approve_identification_question(current_admin):
    try:
        data = request.get_json()
        pending_assessment = PendingIdentificationAssessment.query.filter_by(assessment_id=data["assessmentId"]).first()
        pending_assessment.status = "APPROVED"
        identification = IdentificationAssessment(
            course_id=data["courseId"],
            module=data["module"],
            question=data["question"],
            answer=data["answer"],
            creator=data["creator"]
        )
        db.session.add(identification)
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/approve_true_or_false_question", methods=["POST"])
@admin_auth_required
def approve_true_or_false_question(current_admin):
    try:
        data = request.get_json()
        pending_assessment = PendingTrueOrFalseAssessment.query.filter_by(assessment_id=data["assessmentId"]).first()
        pending_assessment.status = "APPROVED"
        true_or_false = TrueOrFalseAssessment(
            course_id=data["courseId"],
            module=data["module"],
            question=data["question"],
            answer=data["answer"],
            creator=data["creator"]
        )
        db.session.add(true_or_false)
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/disapprove_pending_multiple_choice_assessment", methods=["POST"])
@admin_auth_required
def disapprove_pending_multiple_choice_assessment(current_admin):
    try:
        data = request.get_json()
        pending_assessment = PendingMultipleChoiceAssessment.query.filter_by(assessment_id=data["assessmentId"]).first()
        pending_assessment.status = "UNAPPROVED"
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/disapprove_pending_identification_assessment", methods=["POST"])
@admin_auth_required
def disapprove_pending_identification_assessment(current_admin):
    try:
        data = request.get_json()
        pending_assessment = PendingIdentificationAssessment.query.filter_by(assessment_id=data["assessmentId"]).first()
        pending_assessment.status = "UNAPPROVED"
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/disapprove_pending_true_or_false_assessment", methods=["POST"])
@admin_auth_required
def disapprove_pending_true_or_false_assessment(current_admin):
    try:
        data = request.get_json()
        pending_assessment = PendingTrueOrFalseAssessment.query.filter_by(assessment_id=data["assessmentId"]).first()
        pending_assessment.status = "UNAPPROVED"
        db.session.commit()
        return jsonify({"data": {"message": "Success"}, "type": "success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/get_pending_multiple_choice_questions", methods=["GET"])
@admin_auth_required
def get_pending_multiple_choice_questions(current_admin):
    try:
        pending_assessments = PendingMultipleChoiceAssessment.query.filter_by(status="PENDING").all()
        response = [*map(map_assessments, pending_assessments)]
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/get_pending_identification_questions", methods=["GET"])
@admin_auth_required
def get_pending_identification_questions(current_admin):
    try:
        pending_assessments = PendingIdentificationAssessment.query.filter_by(status="PENDING").all()
        response = [*map(map_assessments, pending_assessments)]
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/get_pending_true_or_false_questions", methods=["GET"])
@admin_auth_required
def get_pending_true_or_false_questions(current_admin):
    try:
        pending_assessments = PendingTrueOrFalseAssessment.query.filter_by(status="PENDING").all()
        response = [*map(map_assessments, pending_assessments)]
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/get_pending_multiple_choice_question", methods=["GET"])
@admin_auth_required
def get_pending_multiple_choice_question(current_admin):
    try:
        pending_assessment = PendingMultipleChoiceAssessment.query.filter_by(assessment_id=request.args.get("assessment_id")).first()
        course = Course.query.filter_by(course_id=pending_assessment.course_id).first()
        response = {
            "assessmentId": pending_assessment.assessment_id,
            "courseId": pending_assessment.course_id,
            "courseName": course.course_name,
            "module": pending_assessment.module,
            "question": pending_assessment.question,
            "letterA": pending_assessment.letter_a,
            "letterB": pending_assessment.letter_b,
            "letterC": pending_assessment.letter_c,
            "letterD": pending_assessment.letter_d,
            "answer": pending_assessment.answer,
            "creator": pending_assessment.creator
        }
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/get_pending_identification_question", methods=["GET"])
@admin_auth_required
def get_pending_identification_question(current_admin):
    try:
        pending_assessment = PendingIdentificationAssessment.query.filter_by(assessment_id=request.args.get("assessment_id")).first()
        course = Course.query.filter_by(course_id=pending_assessment.course_id).first()
        response = {
            "assessmentId": pending_assessment.assessment_id,
            "courseId": pending_assessment.course_id,
            "courseName": course.course_name,
            "module": pending_assessment.module,
            "question": pending_assessment.question,
            "answer": pending_assessment.answer,
            "creator": pending_assessment.creator
        }
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500


@admin_assessment_bp.route("/get_pending_true_or_false_question", methods=["GET"])
@admin_auth_required
def get_pending_true_or_false_question(current_admin):
    try:
        pending_assessment = PendingTrueOrFalseAssessment.query.filter_by(assessment_id=request.args.get("assessment_id")).first()
        course = Course.query.filter_by(course_id=pending_assessment.course_id).first()
        response = {
            "assessmentId": pending_assessment.assessment_id,
            "courseId": pending_assessment.course_id,
            "courseName": course.course_name,
            "module": pending_assessment.module,
            "question": pending_assessment.question,
            "answer": pending_assessment.answer,
            "creator": pending_assessment.creator
        }
        return jsonify({"data": response, "type": "success"}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}", "type": "error"}), 500
