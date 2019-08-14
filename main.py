"""Flask app for spam prediction API.

Usage:
    python app.py
"""
import os
import random
from datetime import datetime, timedelta

from flask import (
    render_template, flash, redirect, url_for, request, abort)
from flask_socketio import SocketIO, emit
from flask_security import (
    Security, login_required, current_user, logout_user,
    user_registered)
from flask_restful import Api
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
    create_tickeruser, delete_tickeruser,
    get_ticker, get_ticker_name, validate_ticker,
    get_ticker_latest_recommendation, get_popular_tickers,
    get_ticker_auth_users)
from app.models import User, ListUser, Chat
from app.user_referral import create_referral_code, get_referral_code
from apis.tickers import (
    TickerEmails, UpdateTicker, DeleteTicker, GetAllTickers,
    AddTickerRecommendations, PlotTickerRecommendations,
    GetAllUsersTickers, GetTickersForUser, GetTickerDetails,
    stocks_recommendations_for_user)
from post_init import user_datastore


security = Security(
    app, user_datastore,
    register_form=ExtendedRegisterForm,
    confirm_register_form=ExtendedRegisterForm,
    login_form=ExtendedLoginForm)
socketio = SocketIO(app)
api = Api(app)
api.add_resource(TickerEmails, '/ticker_emails')
api.add_resource(UpdateTicker, '/update_ticker')
api.add_resource(DeleteTicker, '/delete_ticker')
api.add_resource(GetAllTickers, '/all_tickers')
api.add_resource(AddTickerRecommendations, '/create_ticker_recommendations')
api.add_resource(PlotTickerRecommendations, '/plot_ticker_recommendations')
api.add_resource(GetAllUsersTickers, '/all_users_tickers')
api.add_resource(GetTickersForUser, '/ticker_recommendation_for_user')
api.add_resource(GetTickerDetails, '/get_ticker_details')


@user_registered.connect_via(app)
def user_registered_sighandler(app, user, confirm_token):
    if not confirm_token:
        return
    return create_referral_code(user.id, user.username)


@app.route('/')
@app.route('/index', strict_slashes=False)
def index():
    if current_user.is_anonymous:
        return render_template("index.html")
    else:
        return redirect(url_for('stocks_page'))


@app.route('/explore')
def explore_other_apps():
    return render_template("apps.html")


@app.route('/about', strict_slashes=False)
def about():
    return render_template("about.html")


@app.route('/my_profile', strict_slashes=False)
@login_required
def my_profile():
    referral_code = get_referral_code(current_user.id)
    return render_template("my_profile.html", referral_code=referral_code)


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
@login_required
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
    tickers, ticker_recommendations = stocks_recommendations_for_user(
        current_user.id)

    for ticker_id in ticker_recommendations:
        if ticker_recommendations[ticker_id]["is_strong"]:
            ticker_recommendations[ticker_id]["recommendation"] = (
                "Strong " + ticker_recommendations[ticker_id]["recommendation"]
            )

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
                ticker_created_for_user, message = create_tickeruser(
                    db, ticker_validated, current_user.id)
                if not ticker_created_for_user:
                    flash(message)

            return redirect(url_for('stocks_page'))

    popular_tickers, _ = zip(*get_popular_tickers(3))

    return render_template(
        "stocks.html",
        form=form,
        tickers=tickers,
        ticker_recommendations=ticker_recommendations,
        popular_tickers=popular_tickers)


def no_cache_headers():
    headers = {}
    headers["Cache-Control"] = (
        "no-cache, no-store, must-revalidate, public, max-age=0")
    headers["Expires"] = 0
    headers["Pragma"] = "no-cache"
    return headers


@app.route('/stocks/<int:ticker_id>',
           methods=['GET', 'POST'], strict_slashes=False)
@login_required
def stock_details_page(ticker_id):
    auth_user_ids = get_ticker_auth_users(ticker_id)
    auth_user_ids = [user[0] for user in auth_user_ids]
    if current_user.id not in auth_user_ids:
        return abort(401)

    ticker = get_ticker(ticker_id)
    plot_exists = False
    plots = os.listdir("app/static/ticker_plots")
    if ticker.name.lower().replace(".", "") + ".png" in plots:
        plot_exists = True

    latest_recommend = get_ticker_latest_recommendation(ticker_id)
    if latest_recommend is None:
        return render_template(
            "stock_details.html",
            ticker=ticker,
            plot_exists=plot_exists,
            latest_recommendation=None
        ), 200, no_cache_headers()

    _, latest_recommend_date, buy_or_sell, is_strong = latest_recommend
    latest_recommend_date = datetime.strptime(
        latest_recommend_date, "%Y-%m-%d")

    today_recommend = {
        "date": ticker.latest_trading_day,
        "buy_or_sell": "-",
    }
    ticker_latest_trading_date = datetime.strptime(
        ticker.latest_trading_day, "%Y-%m-%d")
    timedelta_diff = latest_recommend_date - ticker_latest_trading_date

    if timedelta_diff >= timedelta(days=0):
        today_recommend["buy_or_sell"] = buy_or_sell.title()
        if is_strong:
            today_recommend["buy_or_sell"] = (
                "Strong " + today_recommend["buy_or_sell"])

    return render_template(
        "stock_details.html",
        ticker=ticker,
        plot_exists=plot_exists,
        latest_recommendation=today_recommend
    ), 200, no_cache_headers()


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
