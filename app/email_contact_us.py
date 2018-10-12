from flask import abort

from app.send_email import send_message, create_message
from connect.google_api import get_gmail_service
from config import Config


_copyright = Config.COPYRIGHT
_owner_email = Config.OWNER_EMAIL


def _send_email(send_to, title, message, reply_to_email):
    service = get_gmail_service()
    sender = "me"
    user_id = sender
    to = [send_to]
    subject = title.decode("utf-8")
    sign_off = "\n\nReply to: {}\n".format(reply_to_email)

    message = message + sign_off + _copyright

    message = create_message(sender, to, subject, message)
    send_message(service, user_id, message)


def send_contact_message(form_params):
    if (
        not form_params or
        "message" not in form_params or
        "message_type" not in form_params or
        "email" not in form_params or
        not form_params["email"] or
        not form_params["message"] or
        not form_params["message_type"]
    ):
        abort(400)
    try:
        msg_type = form_params["message_type"].title()
        name = form_params.get("name", "")
        title = "{} from {}".format(msg_type, name).encode("utf-8")
        text = form_params["message"].encode("utf-8")
        reply_to_email = form_params["email"]
        _send_email(_owner_email, title, text, reply_to_email)
        return "Success: Article '{}' sent to {}".format(
            title, form_params["email"])
    except IOError:
        return "Error generating message for {}".format(form_params["email"])
