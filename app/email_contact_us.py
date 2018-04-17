from flask import abort

from app.send_email import send_message, create_message
from connect.google_api import get_gmail_service
from config import Config


_domain = Config.DOMAIN
_copyright = Config.COPYRIGHT
_owner_email = Config.OWNER_EMAIL


def _send_email(send_to, article_title, article_text):
    service = get_gmail_service()
    sender = "me"
    user_id = sender
    to = [send_to]
    subject = article_title.decode("utf-8")
    sign_off = "\n\n\n"

    article_text = article_text + sign_off + _copyright

    message = create_message(sender, to, subject, article_text)
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
        _send_email(_owner_email, title, text)
        return "Success: Article '{}' sent to {}".format(
            title, form_params["email"])
    except IOError:
        return "Error generating message for {}".format(form_params["email"])
