import io
import random
import re
from base64 import encodebytes
from itertools import groupby

import bcrypt
from PIL import Image
from itsdangerous import URLSafeTimedSerializer

from config import ALLOWED_EXTENSIONS, EMAIL_REGEX, PASSWORD_REGEX, api, SALT
from db import Achievement, User, CourseSkill, db, Course, Assignment, Session, Message, \
    PendingMultipleChoiceAssessment, PendingIdentificationAssessment, PendingTrueOrFalseAssessment, Admin


def list_to_string(lst):
    return ','.join([*map(lambda x: str(x), lst)])


def string_to_list(string):
    return string.split('|')


def string_to_double_list(string):
    return [*map(lambda x: float(x), string.split(','))]


def string_to_int_list(string):
    return [*map(lambda x: int(x), string.split(','))]


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
    return {
        "courseName": course.course_name,
        "courseDescription": course.course_description,
        "assessmentTaken": course_skill.assessment_taken,
        "assessmentRating": course_skill.assessment_rating
    }


def get_courses_only(course_skill):
    course = Course.query.filter_by(course_id=course_skill.course_id).first()
    return {
        "name": course.course_name,
        "description": course.course_description
    }


def get_course_module(course_skill):
    course = Course.query.filter_by(course_id=course_skill.course_id).first()
    return {
        "courseId": course.course_id,
        "courseName": course.course_name,
        "modules": string_to_list(course.modules)
    }


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def match_date(date_time, search_query):
    return re.search(search_query, str(date_time.year), re.IGNORECASE) or re.search(search_query, str(date_time.month), re.IGNORECASE) or re.search(search_query, str(date_time.day), re.IGNORECASE)


def info_response(user):
    return {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "email": user.email,
        "degree": user.degree,
        "age": user.age,
        "address": user.address,
        "contactNumber": user.contact_number,
        "summary": user.summary,
        "educationalBackground": user.educational_background,
        "image": get_response_image(user.image_path),
        "freeTutoringTime": user.free_tutoring_time
    }


def validate_info(data, current_name):
    if not data["age"] or not data["name"] or not data["address"] or not data["degree"] or not data["contactNumber"] or not data["summary"] or not data["educationalBackground"]:
        return {"isValid": False, "message": "Please fill up empty fields."}
    if not 15 <= len(data["address"]) <= 40:
        return {"isValid": False, "message": "Address should be 15-40 characters length."}
    if not 5 <= len(data["name"]) <= 20:
        return {"isValid": False, "message": "Name should be 5-20 characters length."}
    if not 10 <= len(data["contactNumber"]) <= 100:
        return {"isValid": False, "message": "Contact Number should be 10-100 characters length."}
    if not 30 <= len(data["summary"]) <= 200:
        return {"isValid": False, "message": "Summary should be 30-200 characters length."}
    if not 30 <= len(data["educationalBackground"]) <= 200:
        return {"isValid": False, "message": "Educational Background should be 30-200 characters length."}
    if not 15 <= len(data["freeTutoringTime"]) <= 100:
        return {"isValid": False, "message": "Free tutoring time should be 15-100 characters length."}
    if not 15 <= int(data["age"]) <= 50:
        return {"isValid": False, "message": "Age should range from 15 to 50"}
    if not re.search("BSCS|HRS|STEM|IT|ACT|HRM|ABM", data["degree"]):
        return {"isValid": False, "message": "Please enter valid degree."}
    if any(x.name == data["name"] for x in User.query.all()) and data["name"] != current_name:
        return {"isValid": False, "message": "Username already exists."}

    return {"isValid": True, "message": "User Information Successfully Saved."}


def validate_password(current_password, new_password, confirm_password, current_password_2):
    if not current_password or not new_password or not confirm_password:
        return {"isValid": False, "message": "Please fill up empty fields."}
    if not bcrypt.checkpw(current_password.encode(), current_password_2.encode()):
        return {"isValid": False, "message": "Current password do not match."}
    if not re.search(PASSWORD_REGEX, new_password):
        return {"isValid": False, "message": "Invalid New Password."}
    if new_password != confirm_password:
        return {"isValid": False, "message": "New password do not match."}

    return {"isValid": True, "message": "Password Successfully Saved."}


def update_course_eligibility(course_id, user_id, rating, score):
    course_skill = CourseSkill.query.filter_by(course_id=course_id, user_id=user_id).first()

    if course_skill:
        new_rating = course_skill.assessment_rating + rating
        new_taken = course_skill.assessment_taken + 1
        new_role = "TUTOR" if (new_rating / new_taken >= 0.5) else "STUDENT"
        course_skill.role = new_role
        course_skill.assessment_rating = new_rating
        course_skill.assessment_taken = new_taken
    else:
        new_course_skill = CourseSkill(
            course_id=course_id,
            user_id=user_id,
            role="TUTOR" if (rating >= 0.5) else "STUDENT",
            assessment_taken=1,
            assessment_rating=rating
        )
        db.session.add(new_course_skill)
    return update_assessment_achievement(rating >= 0.5, score, user_id)


def validate_login(user, email, password, is_admin):
    if not email or not password:
        return {"isValid": False, "message": "Fill up all empty fields"}
    if not 15 <= len(email) <= 40 or not 8 <= len(password) <= 20:
        return {"isValid": False, "message": "Fill up fields with specified length"}
    if not user:
        return {"isValid": False, "message": "User not found"}
    if not bcrypt.checkpw(password.encode(), user.password.encode()):
        return {"isValid": False, "message": "Wrong password"}
    if not is_admin and user.is_banned:
        return {"isValid": False, "message": "User is banned"}

    return {"isValid": True, "message": "User Logged In"}


def map_messages(message, role):
    user = User.query.filter_by(id=message.tutor_id if (role == "STUDENT") else message.student_id).first()
    return {
        "messageId": message.message_id,
        "name": user.name,
        "courseName": Course.query.filter_by(course_id=message.course_id).first().course_name,
        "status": message.status,
        "tutorViewed": message.tutor_viewed,
        "image": get_response_image(user.image_path)
    }


def map_sessions(session):
    return {
        "sessionId": session.session_id,
        "courseName": Course.query.filter_by(course_id=session.course_id).first().course_name,
        "startTime": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
        "endTime": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
        "status": session.status,
        "studentViewed": session.student_viewed
    }


def map_assignments(assignment):
    course = Course.query.filter_by(course_id=assignment.course_id).first()
    return {
        "assignmentId": assignment.assignment_id,
        "courseName": course.course_name,
        "moduleName": string_to_list(course.modules)[assignment.module_id],
        "type": assignment.type,
        "deadLine": assignment.dead_line.strftime("%d/%m/%Y %I:%M %p"),
        "status": assignment.status,
        "studentScore": assignment.student_score,
        "studentViewed": assignment.student_viewed
    }


def validate_signup(name, email, password, confirm_password, is_admin):
    users = Admin.query.all() if is_admin else User.query.all()

    if not name or not email or not password or not confirm_password:
        return {"isValid": False, "message": "Fill up all empty fields"}
    if not 5 <= len(name) <= 20 or not 15 <= len(email) <= 40 or not 8 <= len(password) <= 20:
        return {"isValid": False, "message": "Fill up fields with specified length"}
    if password != confirm_password:
        return {"isValid": False, "message": "Passwords do not match"}
    if not re.search(EMAIL_REGEX, email):
        return {"isValid": False, "message": "Invalid Email"}
    if not re.search(PASSWORD_REGEX, password):
        return {"isValid": False, "message": "Invalid Password"}
    if any(x.name == name for x in users):
        return {"isValid": False, "message": "Username already exist"}
    if any(x.email == email for x in users):
        return {"isValid": False, "message": "Email already exist"}

    return {"isValid": True, "message": "Success"}


def map_pattern_assessment(pa):
    lst = [pa.letter_a, pa.letter_b, pa.letter_c, pa.letter_d]
    random.shuffle(lst)
    return {
        "question": pa.question,
        "choices": [split_choices(x) for x in lst]
    }


def split_choices(choice):
    x = choice.split(":")
    return {"choice": x[0], "type": x[1]}


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
        "sessionId": session.session_id,
        "studentId": session.student_id,
        "tutorId": session.tutor_id,
        "courseName": Course.query.filter_by(course_id=session.course_id).first().course_name,
        "name": User.query.filter_by(id=session.tutor_id if role == "STUDENT" else session.student_id).first().name,
        "startTime": session.start_time.strftime("%d/%m/%Y %I:%M %p"),
        "endTime": session.end_time.strftime("%d/%m/%Y %I:%M %p"),
        "location": session.location,
        "status": session.status,
        "studentViewed": session.student_viewed,
        "studentRate": session.student_rate,
        "tutorRate": session.tutor_rate
    }


def get_tutor_datas(course_filter, search_query, user_id, primary_learning, secondary_learning):
    course_skills = [*map(lambda x: CourseSkill.query.filter_by(course_id=x, role="TUTOR").all(), course_filter)]
    flatten_course_skills = sorted([x for cs in course_skills for x in cs], key=lambda x: x.user_id)
    grouped_course_skills = [map_tutors(k, g) for k, g in groupby(flatten_course_skills, lambda x: x.user_id)]
    return search_tutors([*filter(lambda x: user_id != x["tutorId"] and not x["isBanned"] and (primary_learning == x["primaryPattern"] or secondary_learning == x["secondaryPattern"]), grouped_course_skills)], search_query)


def search_tutors(tutors, search_query):
    if search_query:
        return [*filter(lambda x: re.search(search_query, x["tutorName"], re.IGNORECASE) or any(re.search(search_query, y["courseName"], re.IGNORECASE) for y in x["coursesAndRatings"]), tutors)]
    else:
        return tutors


def map_tutors(user_id, course_skills):
    user = User.query.filter_by(id=user_id).first()
    response = {
        "tutorId": user_id,
        "tutorName": user.name,
        "coursesAndRatings": [{"courseName": Course.query.filter_by(course_id=x.course_id).first().course_name, "courseRating": (x.assessment_rating / x.assessment_taken) * 5} for x in course_skills],
        "performance": {"rating": user.total_rating_as_tutor, "rateNumber": user.number_of_rates_as_tutor},
        "primaryPattern": user.primary_learning_pattern,
        "secondaryPattern": user.secondary_learning_pattern,
        "image": get_response_image(user.image_path),
        "isBanned": user.is_banned
    }
    return response


def get_response_image(image_path):
    pil_img = Image.open(image_path, mode='r')
    byte_arr = io.BytesIO()
    pil_img.save(byte_arr, format='PNG')
    encoded_img = encodebytes(byte_arr.getvalue()).decode('ascii')
    return encoded_img


def badge_paths(role):
    if role == "STUDENT":
        return [
            "badges/badge.png",
            "badges/interview.png",
            "badges/communication.png",
            "badges/interview_1.png",
            "badges/personal.png",
            "badges/accept.png",
            "badges/acceptance.png",
            "badges/accept_1.png",
            "badges/reward.png",
            "badges/loyal_customer.png",
            "badges/hand_gesture.png",
            "badges/stars.png",
            "badges/falling_star.png",
            "badges/education.png",
            "badges/management.png",
            "badges/open.png",
            "badges/criteria.png",
            "badges/candidate.png",
            "badges/skills.png",
            "badges/abilities.png",
            "badges/assignment.png",
            "badges/assignment_1.png",
            "badges/distribution.png",
            "badges/rating.png",
            "badges/review.png",
            "badges/rating_1.png",
            "badges/rating_2.png",
            "badges/star_rating.png",
            "badges/customer_review.png"
        ]
    else:
        return [
            "badges/badge.png",
            "badges/yes.png",
            "badges/agreement.png",
            "badges/approved.png",
            "badges/interactions.png",
            "badges/rejected.png",
            "badges/rejected_1.png",
            "badges/reject.png",
            "badges/reward.png",
            "badges/loyal_customer.png",
            "badges/hand_gesture.png",
            "badges/stars.png",
            "badges/falling_star.png",
            "badges/education.png",
            "badges/management.png",
            "badges/open.png",
            "badges/criteria.png",
            "badges/candidate.png",
            "badges/skills.png",
            "badges/abilities.png",
            "badges/assignment.png",
            "badges/assignment_1.png",
            "badges/distribution.png",
            "badges/rating.png",
            "badges/review.png",
            "badges/rating_1.png",
            "badges/rating_2.png",
            "badges/star_rating.png",
            "badges/customer_review.png"
        ]


def generate_token(email):
    serializer = URLSafeTimedSerializer(api.config['SECRET_KEY'])
    return serializer.dumps(email, salt=SALT)


def validate_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(api.config['SECRET_KEY'])
    try:
        email = serializer.loads(token, salt=SALT, max_age=expiration)
        return email
    except Exception as e:
        print(f"Token validation error: {e}")
        return None


def map_assessments(pending_assessment):
    course = Course.query.filter_by(course_id=pending_assessment.course_id).first()
    return {
        "assessmentId": pending_assessment.assessment_id,
        "courseId": pending_assessment.course_id,
        "courseName": course.course_name,
        "module": pending_assessment.module,
        "creator": pending_assessment.creator
    }


def save_pending_multiple_choice_assessment(data, course_id):
    multiple_choice = PendingMultipleChoiceAssessment(
        course_id=course_id,
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
    return PendingMultipleChoiceAssessment.query.filter_by(question=data["question"], letter_a=data["letterA"], letter_b=data["letterB"], letter_c=data["letterC"], letter_d=data["letterD"], answer=data["answer"]).first().assessment_id


def save_pending_identification_assessment(data, course_id):
    identification = PendingIdentificationAssessment(
        course_id=course_id,
        module=data["module"],
        question=data["question"],
        answer=data["answer"],
        creator=data["creator"]
    )
    db.session.add(identification)
    return PendingIdentificationAssessment.query.filter_by(question=data["question"], answer=data["answer"]).first().assessment_id


def save_pending_true_or_false_assessment(data, course_id):
    true_or_false = PendingTrueOrFalseAssessment(
        course_id=course_id,
        module=data["module"],
        question=data["question"],
        answer=data["answer"] == "TRUE",
        creator=data["creator"]
    )
    db.session.add(true_or_false)
    return PendingTrueOrFalseAssessment.query.filter_by(question=data["question"], answer=data["answer"] == "TRUE").first().assessment_id


def map_multiple_choice_assignment(assessment_id):
    assignment = PendingMultipleChoiceAssessment.query.filter_by(assessment_id=assessment_id).first()
    return {
        "module": assignment.module,
        "question": assignment.question,
        "letterA": assignment.letter_a,
        "letterB": assignment.letter_b,
        "letterC": assignment.letter_c,
        "letterD": assignment.letter_d,
        "answer": assignment.answer,
        "creator": assignment.creator
    }


def map_identification_assignment(assessment_id):
    assignment = PendingIdentificationAssessment.query.filter_by(assessment_id=assessment_id).first()
    return {
        "module": assignment.module,
        "question": assignment.question,
        "answer": assignment.answer,
        "creator": assignment.creator
    }


def map_true_or_false_assignment(assessment_id):
    assignment = PendingTrueOrFalseAssessment.query.filter_by(assessment_id=assessment_id).first()
    return {
        "module": assignment.module,
        "question": assignment.question,
        "answer": "TRUE" if assignment.answer else "FALSE",
        "creator": assignment.creator
    }


def map_search_user_admin(user):
    return {
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "email": user.email,
        "degree": user.degree,
        "age": user.age,
        "address": user.address,
        "contactNumber": user.contact_number,
        "summary": user.summary,
        "educationalBackground": user.educational_background,
        "image": get_response_image(user.image_path),
        "freeTutoringTime": user.free_tutoring_time,
        "isBanned": user.is_banned
    }


def map_chats(key, group):
    user = User.query.filter_by(id=key).first()
    return {
        "messages": [{"message": x.message, "sentDate": x.date.strftime("%d/%m/%Y %I:%M %p"), "isSender": x.to_id == 0} for x in group],
        "userId": key,
        "userName": user.name,
        "userRole": user.role,
        "userEmail": user.email,
        "userImage": get_response_image(user.image_path)
    }


def support_key(x):
    return x.from_id if x.to_id == 0 else x.to_id
