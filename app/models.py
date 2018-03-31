from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import (
    generate_password_hash, check_password_hash)

from app import db
from app import login


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    lists = db.relationship(
        'List', backref='author', lazy='dynamic')

    def __repr__(self):
        return '<User {}: {}>'.format(self.id, self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class List(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140))
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    items = db.relationship(
        'ListItem', backref='list', lazy='dynamic')
    is_deleted = db.Column(db.Boolean(), default=False)

    def __repr__(self):
        return '<List {}: {}>'.format(self.id, self.name)


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
