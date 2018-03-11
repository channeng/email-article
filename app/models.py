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
        return '<User {}>'.format(self.username)

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

    def __repr__(self):
        return '<List {}>'.format(self.name)


class ListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(140))
    body = db.Column(db.String(140))
    url = db.Column(db.String(140))
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    list_id = db.Column(db.Integer, db.ForeignKey('list.id'))

    def __repr__(self):
        return '<ListItem {}>'.format(self.name)


class EmailArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(140))
    url = db.Column(db.String(512))
    timestamp = db.Column(
        db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<EmailArticle {email} - {url}>'.format(
            email=self.email, url=self.url)
