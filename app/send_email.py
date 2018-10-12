import base64

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from googleapiclient import errors


def send_message(service, user_id, message):
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


def create_message(sender, to, subject, message_text, pdf_data={}):
    """Create a message for an email.

    Args:
        sender: Email address of the sender.
        to: Email address of the receiver.
        subject: The subject of the email message.
        message_text: The text of the email message.

    Returns:
        An object containing a base64url encoded email object.
    """
    message = MIMEMultipart()
    message_text = "<p>" + message_text.replace("\n\n", "</p><p>") + "</p>"
    message.attach(MIMEText(message_text, "html"))
    message['to'] = ", ".join(to)
    message['from'] = sender
    message['subject'] = subject
    if pdf_data:
        part = MIMEApplication(
            pdf_data["response"].content,
            Name="{}.pdf".format(pdf_data["title"]))
        part['Content-Disposition'] = (
            'attachment; filename="{}.pdf"'.format(pdf_data["title"]))
        message.attach(part)
    return {
        'raw': base64.urlsafe_b64encode(message.as_string())
    }
