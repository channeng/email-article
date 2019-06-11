from flask import Flask, render_template
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

# Import database models with app context
# https://stackoverflow.com/questions/33905706/flask-migrate-seemed-to-delete-all-my-database-data
with app.app_context():
    from app.models import *


@app.errorhandler(404)
def not_found(error):
    return render_template(
        "error.html",
        error_message="Page not found.",
        error_number=404)


@app.errorhandler(401)
def unauthorized(error):
    return render_template(
        "error.html",
        error_message="You are not authorized!",
        error_number=401)
