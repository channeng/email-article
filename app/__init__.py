from flask import Flask, session, render_template
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Flask-Security
from flask_mail import Mail


app = Flask(__name__, template_folder="template")
app.config.from_object(Config)

# Flask-Security fix for HTTP
# from werkzeug.middleware.proxy_fix import ProxyFix
# app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=1)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)

# Import database models with app context
# https://stackoverflow.com/questions/33905706/flask-migrate-seemed-to-delete-all-my-database-data
with app.app_context():
    from app.models import *  # noqa


@app.before_request
def extend_session():
    # Update session to extend timeout
    session.permanent = True
    session.modified = True


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
