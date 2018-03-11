from flask import Flask
from flask_login import LoginManager
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


app = Flask(__name__, template_folder="template")
app.secret_key = "hello"
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask-Login needs to know what is the view function that handles logins
login = LoginManager(app)
login.login_view = 'login'
# from app import routes, models	# Noqa
