"""Flask app for spam prediction API.

Usage:
    python app.py
"""
import random

from flask import render_template, flash, redirect, url_for, request, abort
from flask.ext.sqlalchemy import SQLAlchemy
from flask_login import current_user, login_user, logout_user, login_required
from flask_socketio import SocketIO, emit
from werkzeug.urls import url_parse
import validators

from app import app
from app.forms import (
    LoginForm, RegistrationForm, NewListForm, NewListItemForm,
    NewChatForm, EditListForm)
from app.email_article import create_task
from app.lists import (
    get_lists, create_list, delete_list, get_list_name, get_list_name_items,
    get_list_owner, get_list_auth_user_ids, update_list, create_listitems,
    delete_listitems, update_listitems, create_listuser)
from app.chats import (
    get_chats, create_chat, delete_chat, get_chat_auth_user_ids,
    create_chatmessage, get_chat_name_messages)

from app.models import User, List, ListUser, ListItem, Chat, ChatMessage


# Called with `flask shell` cmd
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'List': List,
        'ListUser': ListUser,
        'ListItem': ListItem,
        'Chat': Chat,
        'ChatMessage': ChatMessage,
    }


db = SQLAlchemy(app)
socketio = SocketIO(app)


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
    lists = get_lists(current_user.id)
    form = NewListForm()

    rand_list = request.args.get("rand", None)
    if rand_list is not None:
        list_name, items = get_list_name_items(rand_list, is_active_only=True)
        if items:
            rand_item = random.choice(items)
            return render_template(
                "lists.html",
                form=form, lists=lists, rand_item=rand_item)

    form_params = request.form.to_dict(flat=True)
    list_id_in_request = "list_id" in form_params.keys()
    if list_id_in_request:
        delete_list(db, int(form_params["list_id"]))
        return redirect(url_for('lists_page'))

    if not list_id_in_request:
        if form.validate_on_submit():
            create_list(db, form.list_name.data, current_user.id)
            return redirect(url_for('lists_page'))

    return render_template("lists.html", form=form, lists=lists)


def _list_items_delete(form_params):
    delete_in_request = "item_id_delete" in form_params.keys()
    if delete_in_request:
        for item_id in form_params["item_id_delete"]:
            delete_listitems(db, int(item_id))
    return delete_in_request


def _list_items_checked_unchecked(form_params):
    check_in_request = "item_id_checked" in form_params.keys()
    uncheck_in_request = "item_id_unchecked" in form_params.keys()
    if check_in_request or uncheck_in_request:
        if check_in_request:
            item_ids_checked = form_params["item_id_checked"]
            update_listitems(db, item_ids_checked, status="Done")
        if uncheck_in_request:
            item_ids_unchecked = form_params["item_id_unchecked"]
            if check_in_request:
                item_ids_unchecked = list(
                    set(item_ids_unchecked) - set(item_ids_checked))
            update_listitems(db, item_ids_unchecked, status="Active")
    checked_unchecked_in_request = (check_in_request or uncheck_in_request)
    return checked_unchecked_in_request


@app.route('/lists/<int:list_id>', methods=['GET', 'POST'])
@login_required
def list_items_page(list_id, auth_user_ids=[], owner_username=None):
    # Check if user has permission to access list
    if not auth_user_ids or owner_username is None:
        owner, auth_user_ids = get_list_auth_user_ids(list_id)
        owner_username = db.session.query(User.username).filter_by(
            id=owner).scalar()
    if current_user.id not in auth_user_ids:
        return abort(401)

    form_params = request.form.to_dict(flat=False)
    delete_in_request = _list_items_delete(form_params)
    checked_unchecked_in_request = _list_items_checked_unchecked(form_params)
    list_name, items = get_list_name_items(list_id)
    new_item_form = NewListItemForm()
    if not (delete_in_request or checked_unchecked_in_request):
        if new_item_form.validate_on_submit() and new_item_form.item_name.data:
            create_listitems(
                db,
                new_item_form.item_name.data,
                new_item_form.item_desc.data,
                new_item_form.item_url.data,
                list_id)
            return redirect(url_for(
                'list_items_page',
                list_id=list_id,
                auth_user_ids=auth_user_ids,
                owner_username=owner_username))

    return render_template(
        "list_items.html",
        list_name=list_name, list_id=list_id,
        items=items, new_item_form=new_item_form,
        owner_username=owner_username
    )


def _user_was_invited(list_id, invited_user_id):
    user_id = db.session.query(ListUser.user_id).filter_by(
        user_id=invited_user_id,
        list_id=list_id).scalar()
    return user_id is not None


@app.route('/lists/<int:list_id>/edit', methods=['GET', 'POST'])
@login_required
def list_edit_page(list_id, user_ids=[]):
    # Check if user has permission to access list
    if not user_ids:
        auth_user_ids = get_list_owner(list_id)
    if current_user.id not in auth_user_ids:
        return abort(401)

    list_name = get_list_name(list_id)
    edit_list_form = EditListForm()
    if edit_list_form.validate_on_submit():
        if edit_list_form.invite_username.data:
            username = edit_list_form.invite_username.data.lower()
            invited_user_id = db.session.query(User.id).filter_by(
                username=username).scalar()
            same_user = invited_user_id == current_user.id
            if invited_user_id is not None and not same_user:
                if _user_was_invited(list_id, invited_user_id):
                    flash('List already shared with user {}.'.format(username))
                    return redirect(url_for('list_edit_page', list_id=list_id))

                else:
                    create_listuser(db, list_id, invited_user_id)
                    flash('List is shared with user {}!'.format(username))

            elif same_user:
                flash("You already have access to the list.")
                return redirect(url_for('list_edit_page', list_id=list_id))

            else:
                flash("User {} does not exist. Please try again.".format(
                    username))
                return redirect(url_for('list_edit_page', list_id=list_id))

        if edit_list_form.list_name.data:
            update_list(
                db,
                list_id,
                edit_list_form.list_name.data)
        if not (
                edit_list_form.list_name.data or
                edit_list_form.invite_username.data):
            flash("No changes were made.")

        return redirect(url_for(
            'list_items_page',
            list_id=list_id))

    return render_template(
        "list_edit.html",
        list_name=list_name, list_id=list_id,
        edit_list_form=edit_list_form
    )


def _get_chat_names(chats):
    """Set chat names relative to other party's username."""

    chats_invited_user_ids = [chat.invited_user_id for chat in chats]
    chats_invited_users = User.query.filter(
        User.id.in_(chats_invited_user_ids)).all()

    chats_started_user_ids = [chat.user_id for chat in chats]
    chats_started_users = User.query.filter(
        User.id.in_(chats_started_user_ids)).all()

    userid_to_username = {}
    for user in chats_invited_users:
        userid_to_username[user.id] = user.username
    for user in chats_started_users:
        userid_to_username[user.id] = user.username

    chat_names = []
    for chat in chats:
        if chat.name == "":
            started_username = userid_to_username.get(
                chat.user_id, "???")
            invited_username = userid_to_username.get(
                chat.invited_user_id, "???")
            if current_user.username == started_username:
                chat_names.append(invited_username)
            elif current_user.username == invited_username:
                chat_names.append(started_username)
        else:
            chat_names.append(chat.name)

    return chat_names


def _has_chat_with_user(user_id, invited_user_id):
    chat_id = db.session.query(Chat.id).filter_by(
        user_id=user_id,
        invited_user_id=invited_user_id,
        is_deleted=False).scalar()
    chat_id_inverse = db.session.query(Chat.id).filter_by(
        user_id=invited_user_id,
        invited_user_id=user_id,
        is_deleted=False).scalar()
    return chat_id is not None or chat_id_inverse is not None


@app.route('/chats', methods=['GET', 'POST'])
@login_required
def chats_page():
    chats = get_chats(current_user.id)
    chat_names = _get_chat_names(chats)
    form = NewChatForm()

    form_params = request.form.to_dict(flat=True)
    chat_id_in_request = "chat_id" in form_params.keys()
    if chat_id_in_request:
        delete_chat(db, int(form_params["chat_id"]))
        return redirect(url_for('chats_page'))

    if not chat_id_in_request:
        if form.validate_on_submit():
            username = form.chat_with_username.data.lower()
            invited_user_id = db.session.query(User.id).filter_by(
                username=username).scalar()
            same_user = invited_user_id == current_user.id
            if invited_user_id is not None and not same_user:
                if _has_chat_with_user(current_user.id, invited_user_id):
                    flash('Chat already exists with user {}.'.format(username))
                else:
                    create_chat(db, current_user.id, invited_user_id)
            elif same_user:
                flash(
                    "You can't create a chat with yourself.")
            else:
                flash("User {} does not exist. Please try again.".format(
                    username))
            return redirect(url_for('chats_page'))

    return render_template(
        "chats.html", form=form, chats=chats, chat_names=chat_names)


@app.route('/chats/<int:chat_id>', methods=['GET', 'POST'])
@login_required
def chat_room_page(chat_id, user_ids=[]):
    # Check if user has permission to access chat
    if not user_ids:
        _, auth_user_ids = get_chat_auth_user_ids(chat_id)
    if current_user.id not in auth_user_ids:
        return abort(401)

    chat_name = request.args.get('chat_name', "???")
    chat_message = request.args.get('msg', "")
    _, messages = get_chat_name_messages(chat_id)
    return render_template(
        "chatroom.html", messages=messages,
        chat_id=chat_id, chat_name=chat_name,
        chat_message=chat_message)


@socketio.on('message')
@login_required
# message_event = u'{"msg":"hi","chat_id":"1","user_id":"2","username":"chan"}'
def broadcast_chat_message(event):
    # event["msg"] = event["msg"].encode("latin1").decode("utf-8")
    if event["msg"] != "~~~ping~~~":
        create_chatmessage(
            db, event["msg"], event["chat_id"],
            event["user_id"], event["username"])
    emit(event["chat_id"], event, broadcast=True)
    return event["msg_id"]


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
