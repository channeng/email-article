"""Flask app for spam prediction API.

Usage:
    python app.py
"""
import random

from flask import (
    render_template, flash, redirect, url_for, request, abort, jsonify)
from flask_basicauth import BasicAuth
from flask_socketio import SocketIO, emit
from flask_restful import Resource, Api
from flask_security import (
    Security, SQLAlchemyUserDatastore,
    login_required, current_user, logout_user)
from flask_security.signals import user_registered
from flask_security.utils import encrypt_password
import validators

from app import app, db
from app.forms import (
    ExtendedRegisterForm, ExtendedLoginForm,
    NewListForm, NewListItemForm,
    NewChatForm, EditListForm, ContactForm, NewTickerForm)
from app.email_article import create_task
from app.email_contact_us import send_contact_message
from app.lists import (
    get_lists, create_list, delete_list, get_list_name, get_list_name_items,
    get_list_owner, get_list_auth_user_ids, update_list, create_listitems,
    delete_listitems, update_listitems, create_listuser)
from app.chats import (
    get_chats, create_chat, delete_chat, get_chat_auth_user_ids,
    create_chatmessage, get_chat_name_messages)
from app.tickers import (
    get_tickers, create_tickeruser, delete_tickeruser,
    get_ticker, get_ticker_name, get_ticker_emails, validate_ticker,
    update_ticker_data, get_all_tickers, create_ticker_recommendation)
from app.models import (
    User, Role, List, ListUser, ListItem, Chat, ChatMessage)


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

basic_auth = BasicAuth()

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(
    app, user_datastore,
    register_form=ExtendedRegisterForm,
    confirm_register_form=ExtendedRegisterForm,
    login_form=ExtendedLoginForm)


@user_registered.connect_via(app)
def user_registered_sighandler(app, user, confirm_token):
    default_role = user_datastore.find_role("user")
    user_datastore.add_role_to_user(user, default_role)
    db.session.commit()


# Executes before the first request is processed.
@app.before_first_request
def before_first_request():
    # Create any database tables that don't exist yet.
    db.create_all()

    # Create the Roles "admin" and "end-user" -- unless they already exist
    user_datastore.find_or_create_role(
        name='admin', description='Administrator')
    user_datastore.find_or_create_role(
        name='user', description='End user')

    # Create two Users for testing purposes -- unless they already exists.
    # Use Flask-Security utility function to encrypt the password.
    encrypted_password = encrypt_password(app.config["ADMIN_PASSWORD"])
    if not user_datastore.get_user(app.config["ADMIN_EMAIL"]):
        user_datastore.create_user(
            username="admin",
            email=app.config["ADMIN_EMAIL"],
            password=encrypted_password)

    # Commit any database changes;
    # User and Roles must exist before we can add a Role to the User
    db.session.commit()

    # Give one User has the "end-user" role, while the other has "admin" role.
    # (This will have no effect if the Users already have these Roles.)
    # Again, commit any database changes.
    user_datastore.add_role_to_user(app.config["ADMIN_EMAIL"], 'admin')

    # Retro-actively apply user role to old users
    for user in user_datastore.user_model.query.all():
        if user.email != app.config["ADMIN_EMAIL"]:
            user_datastore.add_role_to_user(user.email, 'user')

    db.session.commit()


api = Api(app)
socketio = SocketIO(app)


@app.route('/')
@app.route('/index', strict_slashes=False)
def index():
    return render_template("index.html")


@app.route('/about', strict_slashes=False)
def about():
    return render_template("about.html")


@app.route('/email_article', strict_slashes=False)
@login_required
def email_article_page():
    return render_template("email_article.html")


@app.route("/email_article", methods=["POST"], strict_slashes=False)
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


@app.route("/contact", methods=['GET', 'POST'], strict_slashes=False)
def contact_us():
    form_params = request.form.to_dict(flat=True)
    form = ContactForm()
    if form.validate_on_submit():
        result = send_contact_message(form_params)
        print(result)
        flash('Thank you, your message has been sent.')
        return redirect(url_for('contact_us'))
    return render_template("contact_us.html", form=form)


@app.route('/logout', strict_slashes=False)
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/lists/', methods=['GET', 'POST'])
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


@app.route('/lists/<int:list_id>/', methods=['GET', 'POST'])
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


@app.route('/lists/<int:list_id>/edit',
           methods=['GET', 'POST'], strict_slashes=False)
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


@app.route('/chats/', methods=['GET', 'POST'])
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


@app.route('/chats/<int:chat_id>',
           methods=['GET', 'POST'], strict_slashes=False)
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
    if event["msg"] != "~~~ping~~~":
        create_chatmessage(
            db, event["msg"], event["chat_id"],
            event["user_id"], event["username"])
    emit(event["chat_id"], event, broadcast=True)
    return event["msg_id"]


@app.route('/stocks/', methods=['GET', 'POST'])
@login_required
def stocks_page():
    tickers = get_tickers(current_user.id)
    form = NewTickerForm()

    form_params = request.form.to_dict(flat=True)
    ticker_id_in_request = "ticker_id_delete" in form_params.keys()
    if ticker_id_in_request:
        ticker_id = int(form_params["ticker_id_delete"])
        delete_tickeruser(db, ticker_id, current_user.id)
        flash("Ticker: {} deleted.".format(get_ticker_name(ticker_id)))
        return redirect(url_for('stocks_page'))

    if not ticker_id_in_request:
        if form.validate_on_submit():
            ticker_validated = validate_ticker(form.ticker_name.data)
            if ticker_validated in [t.name for t in tickers]:
                flash("Ticker: {} is already added.".format(ticker_validated))
            else:
                ticker_created_for_user = create_tickeruser(
                    db, ticker_validated, current_user.id)
                if not ticker_created_for_user:
                    flash("Ticker: {} is invalid.".format(ticker_validated))

            return redirect(url_for('stocks_page'))

    return render_template("stocks.html", form=form, tickers=tickers)


@app.route('/stocks/<int:ticker_id>',
           methods=['GET', 'POST'], strict_slashes=False)
@login_required
def stock_details_page(ticker_id):
    ticker = get_ticker(ticker_id)
    return render_template("stock_details.html", ticker=ticker)


# Ticker API
class TickerEmails(Resource):
    @basic_auth.required
    def get(self):
        ticker = request.form.get("ticker", None)
        limit = int(request.form.get("limit", 100))
        result = get_ticker_emails(db, ticker=ticker, limit=limit)
        result_dict = {}
        for row in result:
            result_dict[row[0]] = {
                "name": row[1],
                "currrency": row[2],
                "has_recommendations": row[3] == 1,
                "emails": row[4].split(",")
            }
        return jsonify(result_dict)

api.add_resource(TickerEmails, '/ticker_emails')


class UpdateTicker(Resource):
    @basic_auth.required
    def post(self):
        ticker = str(request.form.get("ticker", None))
        if ticker is None:
            return jsonify({"error": "Ticker must be provided."})
        update_details = request.form.get("update_details", "false")
        update_details = update_details.lower() == "true"
        result = update_ticker_data(
            db, ticker, update_details=update_details)
        return jsonify(dict(result))

api.add_resource(UpdateTicker, '/update_ticker')


class GetAllTickers(Resource):
    @basic_auth.required
    def get(self):
        limit = int(request.form.get("limit", 100))
        results = get_all_tickers(num_results=limit)
        tickers_list = []
        for ticker, last_updated in results:
            tickers_list.append({
                "ticker": ticker,
                "last_updated": last_updated
            })

        return jsonify(dict({
            "all_tickers": tickers_list
        }))

api.add_resource(GetAllTickers, '/all_tickers')


class AddTickerRecommendation(Resource):
    @basic_auth.required
    def post(self):
        ticker = str(request.form.get("ticker", None))
        if ticker is None:
            return jsonify({"error": "Ticker must be provided."})
        buy_or_sell = request.form.get("buy_or_sell", None)
        if buy_or_sell is None:
            return jsonify({"error": "Buy/sell not provided. No updates."})
        else:
            closing_date = request.form.get("closing_date", None)
            closing_price = request.form.get("closing_price", None)
            model_version = request.form.get("model_version", None)
            if (closing_date is None or closing_price is None or
                    model_version is None):
                return jsonify(
                    {"error": "Please provide closing date, closing, "
                              "price and model version."})

        is_strong = request.form.get("is_strong", False)
        result = create_ticker_recommendation(
            db, ticker, buy_or_sell, is_strong,
            closing_date, closing_price, model_version)

        if not result:
            return jsonify(
                {"error": "Ticker {} does not exist.".format(ticker)})

        return jsonify(dict(result))

api.add_resource(AddTickerRecommendation, '/ticker_recommendation')


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
