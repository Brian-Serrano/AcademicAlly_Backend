import atexit
import os
import re
from datetime import datetime, timedelta
from itertools import groupby

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, jsonify, request, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

api = Flask(__name__)
api.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///academic_ally.db'
api.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(api)

scheduler = BackgroundScheduler()


def list_to_string(lst):
    return ','.join([*map(lambda x: str(x), lst)])


def string_to_list(string):
    return string.split('|')


def string_to_double_list(string):
    return [*map(lambda x: float(x), string.split(','))]


def compute_achievement_progress(data, achievements_goal, achievements_index, achievement_progress):
    return [
        min(100 * (data / achievements_goal[achievements_index.index(idx)]), 100.0)
        if idx in achievements_index else progress
        for idx, progress in enumerate(achievement_progress)
    ]


def check_completed_achievements(current_progress, computed_progress, role):
    return [
        *map(
            lambda x: Achievement.query.filter_by(id=x[0] + 1, role=role).first().title,
            filter(
                lambda x: x[1] != computed_progress[x[0]] and computed_progress[x[0]] >= 100.0,
                enumerate(current_progress)
            )
        )
    ]


def update_assessment_achievement(eligibility, score, user_id):
    user = User.query.filter_by(id=user_id).first()
    if eligibility:
        user.assessments_taken_as_tutor = user.assessments_taken_as_tutor + 1
        user.tutor_assessment_points = user.tutor_assessment_points + (score * 0.1)
        user.tutor_points = user.tutor_points + (score * 0.1)
        current_progress_tutor = string_to_double_list(user.badge_progress_as_tutor)
        computed_progress_tutor = compute_achievement_progress(
            user.tutor_points,
            [10, 25, 50, 100, 200],
            [7, 8, 9, 10, 11],
            compute_achievement_progress(
                float(len(CourseSkill.query.filter_by(user_id=user_id, role="TUTOR").all())),
                [1, 3, 5, 10],
                [15, 16, 17, 18],
                current_progress_tutor
            )
        )
        user.badge_progress_as_tutor = list_to_string(computed_progress_tutor)

        db.session.commit()
        return check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")
    else:
        user.assessments_taken_as_student = user.assessments_taken_as_student + 1
        user.student_assessment_points = user.student_assessment_points + (score * 0.1)
        user.student_points = user.student_points + (score * 0.1)
        current_progress_student = string_to_double_list(user.badge_progress_as_student)
        computed_progress_student = compute_achievement_progress(
            user.student_points,
            [10, 25, 50, 100, 200],
            [7, 8, 9, 10, 11],
            compute_achievement_progress(
                float(len(CourseSkill.query.filter_by(user_id=user_id, role="STUDENT").all())),
                [1, 3, 5, 10],
                [15, 16, 17, 18],
                current_progress_student
            )
        )
        user.badge_progress_as_student = list_to_string(computed_progress_student)

        db.session.commit()
        return check_completed_achievements(current_progress_student, computed_progress_student, "STUDENT")


def get_course_rating(course_skill):
    course = Course.query.filter_by(course_id=course_skill.course_id).first()
    return [course.course_name, course.course_description, course_skill.assessment_taken, course_skill.assessment_rating]


def get_courses_only(course_skill):
    course = Course.query.filter_by(course_id=course_skill.course_id).first()
    return [course.course_name, course.course_description]


def get_course_module(course_skill):
    course = Course.query.filter_by(course_id=course_skill.course_id).first()
    return [course.course_name, string_to_list(course.modules)]


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def match_date(date_time, search_query):
    return re.search(search_query, str(date_time.year), re.IGNORECASE) or re.search(search_query, str(date_time.month), re.IGNORECASE) or re.search(search_query, str(date_time.day), re.IGNORECASE)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False, default="Test")
    role = db.Column(db.String, nullable=False, default="STUDENT")
    email = db.Column(db.String, nullable=False, default="test@gmail.com")
    password = db.Column(db.String, nullable=False, default="test123")

    image_path = db.Column(db.String, nullable=False, default="images/user.png")
    degree = db.Column(db.String, nullable=False, default="NA")
    age = db.Column(db.Integer, nullable=False, default=0)
    address = db.Column(db.String, nullable=False, default="NA")
    contact_number = db.Column(db.String, nullable=False, default="NA")
    summary = db.Column(db.String, nullable=False, default="This user has no summary provided")
    educational_background = db.Column(db.String, nullable=False, default="This user has no educational background provided")

    student_points = db.Column(db.Double, nullable=False, default=0.0)
    student_assessment_points = db.Column(db.Double, nullable=False, default=0.0)
    student_request_points = db.Column(db.Double, nullable=False, default=0.0)
    student_session_points = db.Column(db.Double, nullable=False, default=0.0)
    student_assignment_points = db.Column(db.Double, nullable=False, default=0.0)
    sessions_completed_as_student = db.Column(db.Integer, nullable=False, default=0)
    requests_sent = db.Column(db.Integer, nullable=False, default=0)
    denied_requests = db.Column(db.Integer, nullable=False, default=0)
    accepted_requests = db.Column(db.Integer, nullable=False, default=0)
    assignments_taken = db.Column(db.Integer, nullable=False, default=0)
    assessments_taken_as_student = db.Column(db.Integer, nullable=False, default=0)
    badge_progress_as_student = db.Column(db.String, nullable=False, default=list_to_string([0.0] * 28))
    number_of_rates_as_student = db.Column(db.Integer, nullable=False, default=0)
    total_rating_as_student = db.Column(db.Double, nullable=False, default=0.0)
    tutors_rated = db.Column(db.Integer, nullable=False, default=0)

    tutor_points = db.Column(db.Double, nullable=False, default=0.0)
    tutor_assessment_points = db.Column(db.Double, nullable=False, default=0.0)
    tutor_request_points = db.Column(db.Double, nullable=False, default=0.0)
    tutor_session_points = db.Column(db.Double, nullable=False, default=0.0)
    tutor_assignment_points = db.Column(db.Double, nullable=False, default=0.0)
    sessions_completed_as_tutor = db.Column(db.Integer, nullable=False, default=0)
    requests_accepted = db.Column(db.Integer, nullable=False, default=0)
    requests_denied = db.Column(db.Integer, nullable=False, default=0)
    requests_received = db.Column(db.Integer, nullable=False, default=0)
    assignments_created = db.Column(db.Integer, nullable=False, default=0)
    assessments_taken_as_tutor = db.Column(db.Integer, nullable=False, default=0)
    badge_progress_as_tutor = db.Column(db.String, nullable=False, default=list_to_string([0.0] * 28))
    number_of_rates_as_tutor = db.Column(db.Integer, nullable=False, default=0)
    total_rating_as_tutor = db.Column(db.Double, nullable=False, default=0.0)
    students_rated = db.Column(db.Integer, nullable=False, default=0)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Message(db.Model):
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column(db.Integer, nullable=False, default=0)
    module_id = db.Column(db.Integer, nullable=False, default=0)
    student_id = db.Column(db.Integer, nullable=False, default=0)
    tutor_id = db.Column(db.Integer, nullable=False, default=0)
    student_message = db.Column(db.String, nullable=False, default="NA")
    expire_date = db.Column(db.DateTime, nullable=False, default=datetime.now() + timedelta(days=7))
    status = db.Column(db.String, nullable=False, default="WAITING")
    tutor_viewed = db.Column(db.Boolean, nullable=False, default=False)


class Session(db.Model):
    session_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column(db.Integer, nullable=False, default=0)
    tutor_id = db.Column(db.Integer, nullable=False, default=0)
    student_id = db.Column(db.Integer, nullable=False, default=0)
    module_id = db.Column(db.Integer, nullable=False, default=0)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.now())
    end_time = db.Column(db.DateTime, nullable=False, default=datetime.now())
    location = db.Column(db.String, nullable=False, default="NA")
    expire_date = db.Column(db.DateTime, nullable=False, default=datetime.now() + timedelta(days=7))
    status = db.Column(db.String, nullable=False, default="UPCOMING")
    student_rate = db.Column(db.Boolean, nullable=False, default=False)
    tutor_rate = db.Column(db.Boolean, nullable=False, default=False)
    student_viewed = db.Column(db.Boolean, nullable=False, default=False)


class CourseSkill(db.Model):
    course_skill_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column(db.Integer, nullable=False, default=0)
    user_id = db.Column(db.Integer, nullable=False, default=0)
    role = db.Column(db.String, nullable=False, default="STUDENT")
    assessment_taken = db.Column(db.Integer, nullable=False, default=0)
    assessment_rating = db.Column(db.Double, nullable=False, default=0.0)


class Assignment(db.Model):
    assignment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, nullable=False, default=0)
    tutor_id = db.Column(db.Integer, nullable=False, default=0)
    course_id = db.Column(db.Integer, nullable=False, default=0)
    module_id = db.Column(db.Integer, nullable=False, default=0)
    data = db.Column(db.String, nullable=False, default="")
    type = db.Column(db.String, nullable=False, default="Multiple Choice")
    dead_line = db.Column(db.DateTime, nullable=False, default=datetime.now())
    student_score = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String, nullable=False, default="UNCOMPLETED")
    student_viewed = db.Column(db.Boolean, nullable=False, default=False)


class Course(db.Model):
    course_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_name = db.Column(db.String, nullable=False)
    course_description = db.Column(db.String, nullable=False)
    modules = db.Column(db.String, nullable=False)


class Achievement(db.Model):
    achievement_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String, nullable=False)
    description = db.Column(db.String, nullable=False)
    role = db.Column(db.String, nullable=False)


class MultipleChoiceAssessment(db.Model):
    assessment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column(db.Integer, nullable=False)
    module = db.Column(db.String, nullable=False)
    question = db.Column(db.String, nullable=False)
    letter_a = db.Column(db.String, nullable=False)
    letter_b = db.Column(db.String, nullable=False)
    letter_c = db.Column(db.String, nullable=False)
    letter_d = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)
    creator = db.Column(db.String, nullable=False)


class IdentificationAssessment(db.Model):
    assessment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column(db.Integer, nullable=False)
    module = db.Column(db.String, nullable=False)
    question = db.Column(db.String, nullable=False)
    answer = db.Column(db.String, nullable=False)
    creator = db.Column(db.String, nullable=False)


class TrueOrFalseAssessment(db.Model):
    assessment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    course_id = db.Column(db.Integer, nullable=False)
    module = db.Column(db.String, nullable=False)
    question = db.Column(db.String, nullable=False)
    answer = db.Column(db.Boolean, nullable=False)
    creator = db.Column(db.String, nullable=False)


# Most *
@api.route("/upload_image", methods=["POST"])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"})
    if file and allowed_file(file.filename):
        try:
            user = User.query.filter_by(id=request.form['user_id']).first()
            filename = secure_filename(datetime.now().strftime("%d_%m_%Y_%H_%M_%S") + '.' + file.filename.rsplit('.', 1)[1])
            file.save(os.path.join(api.config['UPLOAD_FOLDER'], filename))
            user.image_path = UPLOAD_FOLDER + "/" + filename
            db.session.commit()
            return jsonify({"message": "Success"})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": f"Unhandled exception: {e}"}), 500

    return jsonify({"error": "Error"})


# About Session *
@api.route("/get_session/<session_id>/<role>", methods=["GET"])
def get_session(session_id, role):
    try:
        session = Session.query.filter_by(session_id=session_id).first()

        if role == "STUDENT":
            session.student_viewed = True
            db.session.commit()

        course = Course.query.filter_by(course_id=session.course_id).first()
        response = {
            "session_id": session.session_id,
            "course_name": course.course_name,
            "tutor_name": User.query.filter_by(id=session.tutor_id).first().name,
            "student_name": User.query.filter_by(id=session.student_id).first().name,
            "module_name": string_to_list(course.modules)[session.module_id],
            "start_time": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
            "end_time": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
            "location": session.location
        }
        return jsonify(response), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Assignment Option, Create Assignment *
@api.route("/get_session_for_assignment/<session_id>", methods=["GET"])
def get_session_for_assignment(session_id):
    try:
        session = Session.query.filter_by(session_id=session_id).first()
        course = Course.query.filter_by(course_id=session.course_id).first()
        response = {
            "session_id": session.session_id,
            "course_name": course.course_name,
            "module_name": string_to_list(course.modules)[session.module_id],
            "start_time": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
            "end_time": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
            "location": session.location
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# About Student *
@api.route("/get_student/<message_id>/<role>", methods=["GET"])
def get_student(message_id, role):
    try:
        message = Message.query.filter_by(message_id=message_id).first()

        if role == "TUTOR":
            message.tutor_viewed = True
            db.session.commit()

        course = Course.query.filter_by(course_id=message.course_id).first()
        user = User.query.filter_by(id=message.tutor_id if (role == "STUDENT") else message.student_id).first()
        response = {
            "message_id": message.message_id,
            "course_name": course.course_name,
            "module_name": string_to_list(course.modules)[message.module_id],
            "student_message": message.student_message,
            "user_id": user.id,
            "name": user.name,
            "degree": user.degree,
            "age": user.age,
            "address": user.address,
            "contact_number": user.contact_number,
            "summary": user.summary,
            "educational_background": user.educational_background
        }
        return jsonify(response), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# About Student Reject *
@api.route("/reject_student", methods=["POST"])
def reject_student():
    try:
        data = request.get_json()
        message = Message.query.filter_by(message_id=data["message_id"]).first()
        student = User.query.filter_by(id=data["student_id"]).first()
        tutor = User.query.filter_by(id=data["tutor_id"]).first()
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
        return jsonify(check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# About Tutor *
@api.route("/get_tutor/<tutor_id>", methods=["GET"])
def get_tutor(tutor_id):
    try:
        tutor = User.query.filter_by(id=tutor_id).first()
        tutor_courses = CourseSkill.query.filter_by(user_id=tutor_id, role="TUTOR").all()
        tutor_courses_with_names = [*map(get_course_rating, tutor_courses)]
        response = {
            "performance_rating": tutor.total_rating_as_tutor,
            "number_of_rates": tutor.number_of_rates_as_tutor,
            "tutor_courses": tutor_courses_with_names,
            "user_id": tutor.id,
            "name": tutor.name,
            "degree": tutor.degree,
            "age": tutor.age,
            "address": tutor.address,
            "contact_number": tutor.contact_number,
            "summary": tutor.summary,
            "educational_background": tutor.educational_background
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Account *
@api.route("/get_info/<user_id>", methods=["GET"])
def get_info(user_id):
    try:
        user = User.query.filter_by(id=user_id).first()
        response = {
            "id": user.id,
            "name": user.name,
            "role": user.role,
            "email": user.email,
            "password": user.password,
            "degree": user.degree,
            "age": user.age,
            "address": user.address,
            "contact_number": user.contact_number,
            "summary": user.summary,
            "educational_background": user.educational_background
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Account Image *
@api.route("/get_image/<user_id>", methods=["GET"])
def get_image(user_id):
    try:
        user = User.query.filter_by(id=user_id).first()
        return send_file(user.image_path, mimetype="image/jpeg"), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Account Update Info *
@api.route("/update_info", methods=["POST"])
def update_info():
    try:
        data = request.get_json()
        user = User.query.filter_by(id=data["id"]).first()
        user.name = data["name"]
        user.age = data["age"]
        user.degree = data["degree"]
        user.address = data["address"]
        user.contact_number = data["contact_number"]
        user.summary = data["summary"]
        user.educational_background = data["educational_background"]
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Account Update Password *
@api.route("/update_password", methods=["POST"])
def update_password():
    try:
        data = request.get_json()
        user = User.query.filter_by(id=data["id"]).first()
        user.password = data["password"]
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Account Switch Role *
@api.route("/switch_role", methods=["POST"])
def switch_role():
    try:
        data = request.get_json()
        user = User.query.filter_by(id=data["id"]).first()
        user.role = "TUTOR" if (data["role"] == "STUDENT") else "STUDENT"
        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Achievements *
@api.route("/get_achievements/<user_id>/<role>", methods=["GET"])
def get_achievements(user_id, role):
    try:
        user = User.query.filter_by(id=user_id).first()
        progress = string_to_double_list(user.badge_progress_as_student if (role == "STUDENT") else user.badge_progress_as_tutor)
        achievements = [*map(lambda x: [x[1].title, x[1].description, progress[x[0]]], enumerate(Achievement.query.filter_by(role=role).all()))]
        return jsonify({"achievements": achievements}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Analytics *
@api.route("/get_analytics/<user_id>/<role>", methods=["GET"])
def get_analytics(user_id, role):
    try:
        user = User.query.filter_by(id=user_id).first()
        user_courses = CourseSkill.query.filter_by(user_id=user_id, role=role).all()
        user_courses_with_names = [*map(get_course_rating, user_courses)]
        response = {
            "points": user.student_points if (role == "STUDENT") else user.tutor_points,
            "assessment_points": user.student_assessment_points if (role == "STUDENT") else user.tutor_assessment_points,
            "request_points": user.student_request_points if (role == "STUDENT") else user.tutor_request_points,
            "session_points": user.student_session_points if (role == "STUDENT") else user.tutor_session_points,
            "assignment_points": user.student_assignment_points if (role == "STUDENT") else user.tutor_assignment_points,
            "sessions_completed": user.sessions_completed_as_student if (role == "STUDENT") else user.sessions_completed_as_tutor,
            "requests_sent_received": user.requests_sent if (role == "STUDENT") else user.requests_received,
            "requests_accepted": user.accepted_requests if (role == "STUDENT") else user.requests_accepted,
            "requests_denied": user.denied_requests if (role == "STUDENT") else user.requests_denied,
            "assignments": user.assignments_taken if (role == "STUDENT") else user.assignments_created,
            "assessments": user.assessments_taken_as_student if (role == "STUDENT") else user.assessments_taken_as_tutor,
            "rate_number": user.number_of_rates_as_student if (role == "STUDENT") else user.number_of_rates_as_tutor,
            "rated_users": user.tutors_rated if (role == "STUDENT") else user.students_rated,
            "badges_completed": sum(1 for x in string_to_double_list(user.badge_progress_as_student if (role == "STUDENT") else user.badge_progress_as_tutor) if x >= 100.0),
            "courses": user_courses_with_names
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Assessment Option *
@api.route("/get_course_name_and_desc/<course_id>", methods=["GET"])
def get_course_name_and_desc(course_id):
    try:
        course = Course.query.filter_by(course_id=course_id).first()
        response = {
            "name": course.course_name,
            "description": course.course_description
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Assessment *
@api.route("/get_assessment/<course_id>/<items>/<category>", methods=["GET"])
def get_assessment(course_id, items, category):
    try:
        if category == "Multiple Choice":
            assessment_obj = MultipleChoiceAssessment.query.filter_by(course_id=course_id).order_by(func.random()).limit(items).all()
            assessment = [*map(lambda x: [x.module, x.question, x.letter_a, x.letter_b, x.letter_c, x.letter_d, x.answer, x.creator], assessment_obj)]
        elif category == "Identification":
            assessment_obj = IdentificationAssessment.query.filter_by(course_id=course_id).order_by(func.random()).limit(items).all()
            assessment = [*map(lambda x: [x.module, x.question, x.answer, x.creator], assessment_obj)]
        else:
            assessment_obj = TrueOrFalseAssessment.query.filter_by(course_id=course_id).order_by(func.random()).limit(items).all()
            assessment = [*map(lambda x: [x.module, x.question, x.answer, x.creator], assessment_obj)]

        course = Course.query.filter_by(course_id=course_id).first()
        response = {
            "name": course.course_name,
            "description": course.course_description,
            "assessment_data": assessment
        }

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Assessment Complete, Login *
@api.route("/update_course_eligibility", methods=["POST"])
def update_course_eligibility():
    try:
        data = request.get_json()
        course_skill = CourseSkill.query.filter_by(course_id=data["course_id"], user_id=data["user_id"]).first()

        if course_skill:
            new_rating = course_skill.assessment_rating + data["rating"]
            new_taken = course_skill.assessment_taken + 1
            new_role = "TUTOR" if (new_rating / new_taken >= 0.5) else "STUDENT"
            course_skill.role = new_role
            course_skill.assessment_rating = new_rating
            course_skill.assessment_taken = new_taken
        else:
            new_course_skill = CourseSkill(
                course_id=data["course_id"],
                user_id=data["user_id"],
                role="TUTOR" if (data["rating"] >= 0.5) else "STUDENT",
                assessment_taken=1,
                assessment_rating=data["rating"]
            )
            db.session.add(new_course_skill)
        return jsonify(update_assessment_achievement(data["rating"] >= 0.5, data["score"], data["user_id"])), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Assignment *
@api.route("/get_assignment/<assignment_id>/<role>", methods=["GET"])
def get_assignment(assignment_id, role):
    try:
        assignment = Assignment.query.filter_by(assignment_id=assignment_id).first()

        if role == "STUDENT":
            assignment.student_viewed = True
            db.session.commit()

        course = Course.query.filter_by(course_id=assignment.course_id).first()
        response = {
            "name": course.course_name,
            "description": course.course_description,
            "type": assignment.type,
            "data": assignment.data
        }
        return jsonify(response), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Assignment Complete *
@api.route("/complete_assignment", methods=["POST"])
def complete_assignment():
    try:
        data = request.get_json()
        assignment = Assignment.query.filter_by(assignment_id=data["assignment_id"]).first()
        student = User.query.filter_by(id=data["user_id"]).first()
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
        return jsonify(check_completed_achievements(current_progress_student, computed_progress_student, "STUDENT")), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Choose Assessment *
@api.route("/get_courses", methods=["GET"])
def get_courses():
    try:
        courses = [*map(lambda x: [x.course_id, x.course_name, x.course_description], Course.query.all())]
        return jsonify({"courses": courses}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Courses Menu *
@api.route("/get_course_eligibility/<user_id>/<role>", methods=["GET"])
def get_course_eligibility(user_id, role):
    try:
        course_skills = [*map(get_course_rating, CourseSkill.query.filter_by(user_id=user_id, role=role).all())]
        return jsonify({"courses": course_skills}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Create Assignment Complete *
@api.route("/complete_session_and_create_assignment", methods=["POST"])
def complete_session_and_create_assignment():
    try:
        data = request.get_json()
        session = Session.query.filter_by(session_id=data["session_id"]).first()
        student = User.query.filter_by(id=data["student_id"]).first()
        tutor = User.query.filter_by(id=data["tutor_id"]).first()
        assignment = Assignment(
            student_id=data["student_id"],
            tutor_id=data["tutor_id"],
            course_id=data["course_id"],
            module_id=data["module_id"],
            data=data["data"],
            type=data["type"],
            dead_line=datetime.strptime(data["dead_line"], "%d/%m/%Y %I:%M %p")
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
        return jsonify(check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Create Session *
@api.route("/get_message/<message_id>", methods=["GET"])
def get_message(message_id):
    try:
        message = Message.query.filter_by(message_id=message_id).first()
        response = {
            "message_id": message.message_id,
            "course_id": message.course_id,
            "module_id": message.module_id,
            "student_id": message.student_id,
            "tutor_id": message.tutor_id,
            "student_message": message.student_message
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Create Session Add *
@api.route("/create_session", methods=["POST"])
def create_session():
    try:
        data = request.get_json()
        start_time = datetime.strptime(data["start_time"], "%d/%m/%Y %I:%M %p")
        end_time = datetime.strptime(data["end_time"], "%d/%m/%Y %I:%M %p")
        message = Message.query.filter_by(message_id=data["message_id"]).first()
        student = User.query.filter_by(id=data["student_id"]).first()
        tutor = User.query.filter_by(id=data["tutor_id"]).first()
        session = Session(
            course_id=data["course_id"],
            tutor_id=data["tutor_id"],
            student_id=data["student_id"],
            module_id=data["module_id"],
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
        return jsonify(check_completed_achievements(current_progress_tutor, computed_progress_tutor, "TUTOR")), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Dashboard *
@api.route("/get_dashboard_data/<user_id>/<role>", methods=["GET"])
def get_dashboard_data(user_id, role):
    try:
        user_courses = [*map(get_course_rating, CourseSkill.query.filter_by(user_id=user_id, role=role).all())]
        user = User.query.filter_by(id=user_id).first()
        response = {
            "rate number": user.number_of_rates_as_student if (role == "STUDENT") else user.number_of_rates_as_tutor,
            "rating": user.total_rating_as_student if (role == "STUDENT") else user.total_rating_as_tutor,
            "courses": user_courses
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Edit Session *
@api.route("/get_session_settings/<session_id>", methods=["GET"])
def get_session_settings(session_id):
    try:
        session = Session.query.filter_by(session_id=session_id).first()
        response = {
            "start_time": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
            "end_time": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
            "location": session.location
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Edit Session Update *
@api.route("/update_session", methods=["POST"])
def update_session():
    try:
        data = request.get_json()
        session = Session.query.filter_by(session_id=data["session_id"]).first()
        session.start_time = datetime.strptime(data["start_time"], "%d/%m/%Y %I:%M %p")
        session.end_time = datetime.strptime(data["end_time"], "%d/%m/%Y %I:%M %p")
        session.location = data["location"]
        session.expire_date = datetime.strptime(data["end_time"], "%d/%m/%Y %I:%M %p") + timedelta(days=7)
        session.student_viewed = False

        db.session.commit()
        return jsonify({"message": "Success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Leaderboard *
@api.route("/get_leaderboard/<role>", methods=["GET"])
def get_leaderboard(role):
    try:
        if role == "STUDENT":
            leaderboard = User.query.order_by((User.total_rating_as_student / User.number_of_rates_as_student).desc()).limit(20).all()
            response = {
                "leaderboard": [*map(lambda x: [x.id, x.name, x.total_rating_as_student, x.number_of_rates_as_student], leaderboard)]
            }
        else:
            leaderboard = User.query.order_by((User.total_rating_as_tutor / User.number_of_rates_as_tutor).desc()).limit(20).all()
            response = {
                "leaderboard": [*map(lambda x: [x.id, x.name, x.total_rating_as_tutor, x.number_of_rates_as_tutor], leaderboard)]
            }

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Message Tutor *
@api.route("/get_tutor_eligible_courses/<tutor_id>", methods=["GET"])
def get_tutor_eligible_courses(tutor_id):
    try:
        tutor_course_skills = CourseSkill.query.filter_by(user_id=tutor_id, role="TUTOR").all()
        tutor_courses = [*map(get_course_module, tutor_course_skills)]
        response = {
            "tutor_name": User.query.filter_by(id=tutor_id).first().name,
            "tutor_courses": tutor_courses
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Message Tutor Send *
@api.route("/send_tutor_request", methods=["POST"])
def send_tutor_request():
    try:
        data = request.get_json()
        message = Message.query.filter_by(student_id=data["student_id"], tutor_id=data["tutor_id"], status="WAITING").all()

        if not message:
            new_message = Message(
                course_id=data["course_id"],
                module_id=data["module_id"],
                student_id=data["student_id"],
                tutor_id=data["tutor_id"],
                student_message=data["student_message"]
            )
            db.session.add(new_message)
            student = User.query.filter_by(id=data["student_id"]).first()
            tutor = User.query.filter_by(id=data["tutor_id"]).first()
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
            return jsonify(check_completed_achievements(current_progress_student, computed_progress_student, "STUDENT")), 200
        else:
            return jsonify({"error": "Tutor can only be message once."}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Notifications Message *
@api.route("/get_message_notifications/<user_id>/<role>", methods=["GET"])
def get_message_notifications(user_id, role):
    try:
        if role == "STUDENT":
            messages = Message.query.filter_by(student_id=user_id, status="WAITING").all()
        else:
            messages = Message.query.filter_by(tutor_id=user_id, status="WAITING").all()
        return jsonify({"messages": [*map(lambda x: map_messages(x, role), messages)]}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Notifications Session *
@api.route("/get_session_notifications/<user_id>/<role>", methods=["GET"])
def get_session_notifications(user_id, role):
    try:
        if role == "STUDENT":
            sessions = Session.query.filter_by(student_id=user_id, status="UPCOMING").all()
        else:
            sessions = Session.query.filter_by(tutor_id=user_id, status="UPCOMING").all()
        return jsonify({"sessions": [*map(map_sessions, sessions)]}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Notifications Assignment *
@api.route("/get_assignment_notifications/<user_id>/<role>", methods=["GET"])
def get_assignment_notifications(user_id, role):
    try:
        if role == "STUDENT":
            assignments = Assignment.query.filter_by(student_id=user_id, status="UNCOMPLETED").all()
        else:
            assignments = Assignment.query.filter_by(tutor_id=user_id, status="UNCOMPLETED").all()
        return jsonify({"assignments": [*map(map_assignments, assignments)]}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


def map_messages(message, role):
    return {
        "message_id": message.message_id,
        "name": User.query.filter_by(id=message.tutor_id if (role == "STUDENT") else message.student_id).first().name,
        "course_name": Course.query.filter_by(course_id=message.course_id).first().course_name,
        "status": message.status,
        "tutor_viewed": message.tutor_viewed
    }


def map_sessions(session):
    return {
        "session_id": session.session_id,
        "course_name": Course.query.filter_by(course_id=session.course_id).first().course_name,
        "start_time": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
        "end_time": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
        "status": session.status,
        "student_viewed": session.student_viewed
    }


def map_assignments(assignment):
    course = Course.query.filter_by(course_id=assignment.course_id).first()
    return {
        "assignment_id": assignment.assignment_id,
        "course_name": course.course_name,
        "module_name": string_to_list(course.modules)[assignment.module_id],
        "type": assignment.type,
        "dead_line": assignment.dead_line.strftime("%d/%m/%Y %I:%M %p"),
        "status": assignment.status,
        "student_viewed": assignment.student_viewed
    }


# Profile *
@api.route("/get_profile/<other_id>", methods=["GET"])
def get_profile(other_id):
    try:
        user = User.query.filter_by(id=other_id).first().as_dict()
        user["badge_progress_as_student"] = sum(1 for x in string_to_double_list(user["badge_progress_as_student"]) if x >= 100.0)
        user["badge_progress_as_tutor"] = sum(1 for x in string_to_double_list(user["badge_progress_as_tutor"]) if x >= 100.0)
        as_student_courses = CourseSkill.query.filter_by(user_id=other_id, role="STUDENT").all()
        as_tutor_courses = CourseSkill.query.filter_by(user_id=other_id, role="TUTOR").all()
        response = {
            "user": user,
            "as_student_courses": [*map(get_courses_only, as_student_courses)],
            "as_tutor_courses": [*map(get_courses_only, as_tutor_courses)]
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Signup *
@api.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        user = User(
            name=data["name"],
            role=data["role"],
            email=data["email"],
            password=data["password"]
        )
        db.session.add(user)
        user_id = User.query.filter_by(email=data["email"], password=data["password"], role=data["role"]).first().id

        if data["eligibility"]:
            course_skill = CourseSkill(
                course_id=data["course_id"],
                user_id=user_id,
                role=data["eligibility"],
                assessment_taken=1,
                assessment_rating=data["rating"]
            )
            db.session.add(course_skill)
            return jsonify(update_assessment_achievement(data["score"] / data["items"] >= data["evaluator"], data["score"], user_id)), 200
        else:
            db.session.commit()
            return jsonify({"message": "Success"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Drawer *
@api.route("/get_drawer_data/<user_id>", methods=["GET"])
def get_drawer_data(user_id):
    try:
        user = User.query.filter_by(id=user_id).first()
        response = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "password": user.password
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Find Tutor *
@api.route("/get_tutors/<user_id>", methods=["GET"])
def get_tutors(user_id):
    try:
        course_skills = CourseSkill.query.filter_by(user_id=user_id, role="STUDENT").all()
        course_skill_ids = [*map(lambda x: x.course_id, course_skills)]
        courses = Course.query.all()
        response = {
            "student_course_ids": course_skill_ids,
            "courses": [*map(lambda x: x.course_name, courses)],
            "tutors": get_tutor_datas(course_skill_ids, "", user_id)
        }
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Find Tutor Search *
@api.route("/search_tutor/<course_filter>/<search_query>/<user_id>", methods=["GET"])
def search_tutor(course_filter, search_query, user_id):
    try:
        return jsonify({"tutors": get_tutor_datas([int(x) for x in course_filter.split(',')], search_query, user_id)}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Archive Messages
@api.route("/get_message_archives/<role>/<user_id>/<status>", methods=["GET"])
def get_message_archives(role, user_id, status):
    try:
        return jsonify({"messages": map_archive_messages(role, user_id, status)}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Archive Sessions
@api.route("/get_session_archives/<role>/<user_id>/<status>", methods=["GET"])
def get_session_archives(role, user_id, status):
    try:
        return jsonify({"sessions": get_archive_sessions(role, user_id, status)}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Archive Assignments
@api.route("/get_assignment_archives/<role>/<user_id>/<status>", methods=["GET"])
def get_assignment_archives(role, user_id, status):
    try:
        return jsonify({"assignments": map_archive_assignments(role, user_id, status)}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Archive Messages Search
@api.route("/search_message_archives/<role>/<user_id>/<status>/<search_query>", methods=["GET"])
def search_message_archives(role, user_id, status, search_query):
    try:
        messages = map_archive_messages(role, user_id, status)
        if search_query:
            return jsonify({"messages": [*filter(lambda x: re.search(search_query, x["name"], re.IGNORECASE) or re.search(search_query, x["course_name"], re.IGNORECASE), messages)]})
        else:
            return jsonify({"messages": messages}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Archive Sessions Search
@api.route("/search_session_archives/<role>/<user_id>/<status>/<search_query>", methods=["GET"])
def search_session_archives(role, user_id, status, search_query):
    try:
        sessions = get_archive_sessions(role, user_id, status)
        if search_query:
            return jsonify({"sessions": [*filter(lambda x: re.search(search_query, x["name"], re.IGNORECASE) or re.search(search_query, x["course_name"], re.IGNORECASE) or re.search(search_query, x["location"], re.IGNORECASE) or match_date(datetime.strptime(x["start_time"], "%d/%m/%Y %I:%M %p"), search_query) or match_date(datetime.strptime(x["end_time"], "%d/%m/%Y %I:%M %p"), search_query), sessions)]})
        else:
            return jsonify({"sessions": sessions}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


# Archive Assignments Search
@api.route("/search_assignment_archives/<role>/<user_id>/<status>/<search_query>", methods=["GET"])
def search_assignment_archives(role, user_id, status, search_query):
    try:
        assignments = map_archive_assignments(role, user_id, status)
        if search_query:
            return jsonify({"assignments": [*filter(lambda x: re.search(search_query, x["course_name"], re.IGNORECASE) or re.search(search_query, x["module_name"], re.IGNORECASE) or re.search(search_query, x["type"], re.IGNORECASE) or match_date(datetime.strptime(x["dead_line"], "%d/%m/%Y %I:%M %p"), search_query), assignments)]})
        else:
            return jsonify({"assignments": assignments}), 200
    except Exception as e:
        return jsonify({"error": f"Unhandled exception: {e}"}), 500


def map_archive_messages(role, user_id, status):
    if role == "STUDENT":
        messages = Message.query.filter_by(student_id=user_id, status=status).all()
    else:
        messages = Message.query.filter_by(tutor_id=user_id, status=status).all()
    return [*map(lambda x: map_messages(x, role), messages)]


def get_archive_sessions(role, user_id, status):
    if role == "STUDENT":
        sessions = Session.query.filter_by(student_id=user_id, status=status).all()
    else:
        sessions = Session.query.filter_by(tutor_id=user_id, status=status).all()
    return [*map(lambda x: map_archive_sessions(role, x), sessions)]


def map_archive_assignments(role, user_id, status):
    if role == "STUDENT":
        assignments = Assignment.query.filter_by(student_id=user_id, status=status).all()
    else:
        assignments = Assignment.query.filter_by(tutor_id=user_id, status=status).all()
    return [*map(map_assignments, assignments)]


def map_archive_sessions(role, session):
    return {
        "session_id": session.session_id,
        "course_name": Course.query.filter_by(course_id=session.course_id).first().course_name,
        "name": User.query.filter_by(id=session.tutor_id if role == "STUDENT" else session.student_id).first().name,
        "start_time": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
        "end_time": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
        "location": session.location,
        "status": session.status,
        "student_viewed": session.student_viewed,
        "student_rate": session.student_rate,
        "tutor_rate": session.tutor_rate
    }


def get_tutor_datas(course_filter, search_query, user_id):
    course_skills = [*map(lambda x: CourseSkill.query.filter_by(course_id=x, role="TUTOR").all(), course_filter)]
    flatten_course_skills = sorted([x for cs in course_skills for x in cs], key=lambda x: x.user_id)
    grouped_course_skills = [map_tutors(k, g) for k, g in groupby(flatten_course_skills, lambda x: x.user_id)]
    return search_tutors([*filter(lambda x: user_id != x["tutor_id"], grouped_course_skills)], search_query)


def search_tutors(tutors, search_query):
    if search_query:
        return [*filter(lambda x: re.search(search_query, x["tutor_name"], re.IGNORECASE) or any(re.search(search_query, y, re.IGNORECASE) for y in x["courses"]), tutors)]
    else:
        return tutors


def map_tutors(user_id, course_skills):
    user = User.query.filter_by(id=user_id).first()
    response = {
        "tutor_id": user_id,
        "tutor_name": user.name,
        "courses_and_ratings": [[Course.query.filter_by(course_id=x.course_id).first().course_name, (x.assessment_rating / x.assessment_taken) * 5] for x in course_skills],
        "performance": [user.total_rating_as_tutor, user.number_of_rates_as_tutor]
    }
    return response


def check_expires():
    with api.app_context():
        messages = Message.query.all()
        sessions = Session.query.all()
        assignments = Assignment.query.all()

        for message in messages:
            if message.expire_date < datetime.now() and message.status == "WAITING":
                message.status = "REJECT"
                db.session.commit()

        for session in sessions:
            if session.expire_date < datetime.now() and session.status == "UPCOMING":
                session.status = "CANCELLED"
                db.session.commit()

        for assignment in assignments:
            if assignment.dead_line < datetime.now() and assignment.status == "UNCOMPLETED":
                assignment.status = "DEADLINED"
                db.session.commit()


scheduler.add_job(
    func=check_expires,
    trigger=IntervalTrigger(minutes=15),
    id="check expires job",
    name="check expires",
    replace_existing=True
)


atexit.register(lambda: scheduler.shutdown())


if __name__ == '__main__':

    with api.app_context():

        db.create_all()

    scheduler.start()

    api.run(debug=True)

