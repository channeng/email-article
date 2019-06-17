from flask import Flask, session, render_template
from flask_login import LoginManager
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


app = Flask(__name__, template_folder="template")
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask-Login needs to know what is the view function that handles logins
login = LoginManager(app)
login.login_view = 'login'
login.refresh_view = 'login'
login.needs_refresh_message = (u"Session timed out, please re-login")
login.needs_refresh_message_category = "info"


@app.before_first_request
def before_first_request():
    # Update session to extend timeout
    session.modified = True

# Import database models with app context
# https://stackoverflow.com/questions/33905706/flask-migrate-seemed-to-delete-all-my-database-data
with app.app_context():
    from app.models import *  # noqa


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


@app.errorhandler(405)
def method_not_allowed(error):
    return render_template(
        "error.html",
        error_message="Method Not Allowed.",
        error_number=405)
