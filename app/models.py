from datetime import datetime

from sqlalchemy.orm import validates
from sqlalchemy.sql import functions as func
from sqlalchemy import inspect

from app import db
from flask_security import UserMixin, RoleMixin


def get_columns(db_model):
    mapper = inspect(db_model)
    return [column.key for column in mapper.attrs]


# Define models
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(255), index=True, unique=True)

    @validates('username', 'email')
    def convert_lower(self, key, value):
        return value.lower()

    password = db.Column(db.String(255))
    time_created = db.Column(db.DateTime, default=func.now())
    active = db.Column(db.Boolean(), default=True)
    confirmed_at = db.Column(db.DateTime())

    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)

    roles = db.relationship(
        'Role',
        secondary=roles_users,
        backref=db.backref('users', lazy='dynamic'))

    lists = db.relationship(
        'List', backref='author', lazy='dynamic')

    def __repr__(self):
        return '<User {}: {}>'.format(self.id, self.username)


class List(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140))
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    items = db.relationship(
        'ListItem', backref='list', lazy='dynamic')
    invited_users = db.relationship(
        'ListUser', backref='list', lazy='dynamic')
    is_deleted = db.Column(db.Boolean(), default=False)

    def __repr__(self):
        return '<List {}: {}>'.format(self.id, self.name)


class ListUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    list_id = db.Column(db.Integer, db.ForeignKey('list.id'))

    def __repr__(self):
        return '<ListUser {}: user_id {}, list_id {}>'.format(
            self.id, self.user_id, self.list_id)


class ListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140))
    body = db.Column(db.String(1028))
    url = db.Column(db.String(2083))
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    list_id = db.Column(db.Integer, db.ForeignKey('list.id'))
    status = db.Column(db.String(16), default="Active")
    is_deleted = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<ListItem {}: {}>'.format(self.id, self.name)


class EmailArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(140))
    url = db.Column(db.String(2083))
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<EmailArticle {id}: {email} - {url}>'.format(
            id=self.id, email=self.email, url=self.url)


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140), default="")
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    invited_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    messages = db.relationship(
        'ChatMessage', backref='chat', lazy='dynamic')
    is_deleted = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Chat {}: {}>'.format(self.id, self.name)


class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    username = db.Column(db.String(64), db.ForeignKey('user.username'))
    message = db.Column(db.String(1028))
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id'))
    is_deleted = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<ChatMessage {}: {}>'.format(self.id, self.message)


class Ticker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140))

    @validates('name')
    def convert_upper(self, key, value):
        return value.upper()

    # https://stackoverflow.com/questions/13370317/sqlalchemy-default-datetime
    time_created = db.Column(
        db.DateTime,
        # best to use sql DB server time
        default=func.now())
    time_updated = db.Column(
        db.DateTime,
        onupdate=func.now())
    subscribed_users = db.relationship(
        'TickerUser', backref='list', lazy='dynamic')

    # https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords=xiaomi&apikey=demo
    full_name = db.Column(db.String(140))
    type = db.Column(db.String(50))
    region = db.Column(db.String(140))
    currency = db.Column(db.String(50))
    timezone = db.Column(db.String(50))

    # https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=MSFT&apikey=demo
    open = db.Column(db.Float)
    high = db.Column(db.Float)
    low = db.Column(db.Float)
    price = db.Column(db.Float)
    volume = db.Column(db.Integer)
    latest_trading_day = db.Column(db.String(50))
    previous_close = db.Column(db.Float)
    change = db.Column(db.Float)
    change_percent = db.Column(db.Float)

    is_deleted = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Ticker {}: {}>'.format(self.id, self.name)


class TickerUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ticker_id = db.Column(db.Integer, db.ForeignKey('ticker.id'))
    time_created = db.Column(db.DateTime, default=func.now())
    is_deleted = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<TickerUser {}: user_id {}, ticker_id {}>'.format(
            self.id, self.user_id, self.ticker_id)


class TickerRecommendation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticker_id = db.Column(db.Integer, db.ForeignKey('ticker.id'))
    time_created = db.Column(db.DateTime, default=func.now())

    recommendation = db.Column(db.String(50))  # buy/sell
    is_strong = db.Column(db.Boolean, default=False)
    closing_date = db.Column(db.String(50))
    closing_price = db.Column(db.Float)
    model_version = db.Column(db.String(140))

    def __repr__(self):
        return (
            "<TickerRecommendation {}: ticker_id {}, "
            "closing_date {}, recommendation {}>").format(
            self.id, self.ticker_id, self.closing_date, self.recommendation)
