from datetime import datetime

from config import api, scheduler, db
from db import Message, Session, Assignment


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


def init_scheduler():
    scheduler.add_job(func=check_expires, trigger="interval", id="check expires job", hours=2)
    scheduler.start()
