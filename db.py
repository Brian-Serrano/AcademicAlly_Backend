from datetime import datetime, timedelta

from config import db


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
    badge_progress_as_student = db.Column(db.String, nullable=False, default=','.join([*map(lambda x: str(x), [0.0] * 28)]))
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
    badge_progress_as_tutor = db.Column(db.String, nullable=False, default=','.join([*map(lambda x: str(x), [0.0] * 28)]))
    number_of_rates_as_tutor = db.Column(db.Integer, nullable=False, default=0)
    total_rating_as_tutor = db.Column(db.Double, nullable=False, default=0.0)
    students_rated = db.Column(db.Integer, nullable=False, default=0)

    primary_learning_pattern = db.Column(db.String, nullable=False, server_default="NA")
    secondary_learning_pattern = db.Column(db.String, nullable=False, server_default="NA")


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


class LearningPatternAssessment(db.Model):
    assessment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question = db.Column(db.String, nullable=False)
    letter_a = db.Column(db.String, nullable=False)
    letter_b = db.Column(db.String, nullable=False)
    letter_c = db.Column(db.String, nullable=False)
    letter_d = db.Column(db.String, nullable=False)
