"""Flask app for spam prediction API.

Usage:
    python app.py
"""
from flask import render_template, flash, redirect, url_for, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse
import validators

from app import app
from app.forms import (
    LoginForm, RegistrationForm, NewListForm, NewListItemForm)
from app.models import User, List, ListItem
from app.email_article import create_task
from app.lists import (
    get_lists, create_list, delete_list, get_list_name_items,
    create_listitems, delete_listitems)

from flask import jsonify, make_response

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


@app.route('/about')
def about():
    return render_template("about.html")


@app.route('/email_article')
@login_required
def email_article_page():
    return render_template("email_article.html")


@app.route("/email_article", methods=["POST"])
@login_required
def send_email_article():
    form_params = request.form.to_dict(flat=True)
    if not (
            validators.email(form_params["email"]) and
            validators.url(form_params["article_url"])):
        flash('Invalid url or email. Please try again.')
        return redirect(url_for('send_email_article'))
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
        user = User.query.filter_by(
            username=form.username.data.lower()).first()
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
        user = User(
            username=form.username.data.lower(),
            email=form.email.data.lower())
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(
            'Congratulations, you are now a registered user!\n'
            'Please sign in.')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/lists', methods=['GET', 'POST'])
@login_required
def lists_page():
    form_params = request.form.to_dict(flat=True)
    list_id_in_request = "list_id" in form_params.keys()
    if list_id_in_request:
        delete_list(db, int(form_params["list_id"]))

    lists = get_lists(current_user.id)
    form = NewListForm()
    if not list_id_in_request:
        if form.validate_on_submit():
            create_list(db, form.list_name.data.title(), current_user.id)
            lists = get_lists(current_user.id)
    return render_template("lists.html", form=form, lists=lists)


@app.route('/lists/<int:list_id>', methods=['GET', 'POST'])
@login_required
def list_items_page(list_id):
    form_params = request.form.to_dict(flat=True)
    item_id_in_request = "item_id" in form_params.keys()
    if item_id_in_request:
        delete_listitems(db, int(form_params["item_id"]))
    list_name, items = get_list_name_items(list_id)
    new_item_form = NewListItemForm()
    if not item_id_in_request:
        if new_item_form.validate_on_submit() and new_item_form.item_name.data:
            print("New item form {}".format(new_item_form.item_name.data))
            create_listitems(db, new_item_form.item_name.data.title(), list_id)
            list_name, items = get_list_name_items(list_id)
    return render_template(
        "list_items.html",
        list_name=list_name, list_id=list_id,
        items=items,
        new_item_form=new_item_form,
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
