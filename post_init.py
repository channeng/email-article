from flask_security import SQLAlchemyUserDatastore
from flask_security.signals import user_registered
from flask_security.utils import encrypt_password

from app import app, db
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


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)


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

    # Retro-actively apply user role to old users (Backfilling)
    # for user in user_datastore.user_model.query.all():
    #     if user.email != app.config["ADMIN_EMAIL"]:
    #         user_datastore.add_role_to_user(user.email, 'user')

    db.session.commit()
