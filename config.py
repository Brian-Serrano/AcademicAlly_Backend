import os
import re
import firebase_admin

from flask import Flask
from flask_apscheduler import APScheduler
from flask_sqlalchemy import SQLAlchemy
from firebase_admin import credentials
from dotenv import load_dotenv

load_dotenv()

cred = credentials.Certificate("service_account_key.json")
firebase_admin.initialize_app(cred)

UPLOAD_FOLDER = 'images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
SALT = os.getenv("SALT").encode("utf-8")
PASSWORD_REGEX = re.compile(os.getenv("PASSWORD_REGEX"))
EMAIL_REGEX = re.compile(os.getenv("EMAIL_REGEX"))
PASSWORD = os.getenv("PASSWORD")

api = Flask(__name__, template_folder="templates")
api.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URI")
api.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
api.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
db = SQLAlchemy(api)
scheduler = APScheduler()
