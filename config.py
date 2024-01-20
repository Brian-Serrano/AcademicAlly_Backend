import os
import re

from flask import Flask
from flask_apscheduler import APScheduler
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

UPLOAD_FOLDER = 'images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
SALT = os.environ.get("SALT").encode("utf-8")
PASSWORD_REGEX = re.compile(os.environ.get("PASSWORD_REGEX"))
EMAIL_REGEX = re.compile(os.environ.get("EMAIL_REGEX"))
PASSWORD = os.environ.get("PASSWORD")

api = Flask(__name__, template_folder="templates")
api.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI")
api.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
api.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
db = SQLAlchemy(api)
migrate = Migrate(api, db)
scheduler = APScheduler()
