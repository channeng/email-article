"""Flask app for spam prediction API.

Usage:
    python app.py
"""
import base64
from email.mime.text import MIMEText

from flask import (
    Flask, jsonify, render_template, make_response, request, abort)
from flask_basicauth import BasicAuth
from googleapiclient import errors
from newspaper import Article

from connect.google_api import get_gmail_service
from config import USERNAME, PASSWORD


app = Flask(__name__, template_folder="template")
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['BASIC_AUTH_USERNAME'] = USERNAME
app.config['BASIC_AUTH_PASSWORD'] = PASSWORD
app.config['BASIC_AUTH_FORCE'] = True
basic_auth = BasicAuth(app)


def _get_article(url):
    article = Article(url)
    article.download()
    article.parse()

    return {
        "title": article.title,
        "text": article.text,
        "authors": article.authors,
        "url": article.url
    }


def _send_message(service, user_id, message):
    """Send an email message.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
        message: Message to be sent.

    Returns:
        Sent Message.
    """
    try:
        message = (
            service
            .users()
            .messages()
            .send(userId=user_id, body=message)
            .execute()
        )
        print 'Message Id: %s' % message['id']
        return message
    except errors.HttpError, error:
        print 'An error occurred: %s' % error


def _create_message(sender, to, subject, message_text):
    """Create a message for an email.

    Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.

    Returns:
        An object containing a base64url encoded email object.
    """
    message = MIMEText(message_text)
    message['to'] = ", ".join(to)
    message['from'] = sender
    message['subject'] = subject
    return {
        'raw': base64.urlsafe_b64encode(message.as_string())
    }


def _send_email(
        send_to, article_title, article_text, url="", authors=None):
    service = get_gmail_service()
    sender = "me"
    user_id = sender
    to = [send_to]
    subject = "Article: {}".format(article_title).decode("utf-8")

    article_authors = ""
    if authors:
        article_authors = "By: {}\n\n".format(", ".join(authors))

    link_to_article = ""
    if url:
        link_to_article = "\n\nLink to article: {}\n".format(url)

    sign_off = (
        "\nGenerated by Article-to-email app: http://54.169.72.80:5000/\n"
        "\n\xc2\xa9 Shannon Chan 2017\n")
    article_text = article_authors + article_text + link_to_article + sign_off

    message = _create_message(sender, to, subject, article_text)

    _send_message(service, user_id, message)


def create_task(form_params):
    if (
        not form_params or
        "email" not in form_params or
        "article_url" not in form_params or
        not form_params["email"] or
        not form_params["article_url"]
    ):
        abort(400)
    try:
        article = _get_article(form_params["article_url"])
        title = article["title"].encode("utf-8")
        text = article["text"].encode("utf-8")
        _send_email(
            form_params["email"], title, text,
            url=article.get("url", ""),
            authors=article.get("authors", ""))
        return "Success: Article '{}' sent to {}".format(
            title, form_params["email"])
    except IOError:
        return "Error generating message for {}".format(form_params["email"])


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.route("/")
def index():
    return render_template("webpage.html")


@app.route("/", methods=["POST"])
def get_listings():
    form_params = request.form.to_dict(flat=True)
    result = create_task(form_params)
    print(result)
    return render_template("webpage.html")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
