"""Flask app for spam prediction API.

Usage:
    python app.py
"""
from flask import render_template, flash, redirect, url_for, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse

from app import app
from app.forms import LoginForm, RegistrationForm
from app.models import User, List, ListItem

from flask import (jsonify, make_response)
from email_article import create_task
# from flask_basicauth import BasicAuth


# basic_auth = BasicAuth(app)
db = SQLAlchemy(app)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html")


@app.route('/email_article')
@login_required
def email_article_page():
    return render_template("email_article.html")


@app.route("/email_article", methods=["POST"])
@login_required
def send_email_article():
    form_params = request.form.to_dict(flat=True)
    result = create_task(form_params)
    print(result)
    return render_template("email_article.html")


# Called with `flask shell` cmd
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'List': List, 'ListItem': ListItem}


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)

    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
