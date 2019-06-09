from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, PasswordField, BooleanField, SubmitField,
    SelectField)
from wtforms.validators import (
    ValidationError, DataRequired, Email, EqualTo, URL, Length, Optional)
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data.lower()).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class ContactForm(FlaskForm):
    name = StringField('Name', validators=[Optional()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    choices = [
        ('feedback', 'Feedback'),
        ('new feature', 'Request new feature'),
        ('partnership', 'Partnership'),
        ('thanks', 'Say thanks!'),
        ('others', 'Others')]
    message_type = SelectField(
        'Purpose',
        choices=choices,
        default="feedback",
        validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send Message')


class NewListForm(FlaskForm):
    length_message = "{} cannot be more than {} characters."

    list_name_fieldname = "List name"
    list_name_limit = 24
    list_name = StringField(
        list_name_fieldname,
        render_kw={'maxlength': list_name_limit},
        validators=[DataRequired(), Length(
            max=list_name_limit,
            message=length_message.format(
                list_name_fieldname, list_name_limit))])
    submit = SubmitField('Create List')


class EditListForm(FlaskForm):
    length_message = "{} cannot be more than {} characters."

    list_name_fieldname = "List name"
    list_name_limit = 24
    list_name = StringField(
        list_name_fieldname,
        render_kw={'maxlength': list_name_limit},
        validators=[Optional(), Length(
            max=list_name_limit,
            message=length_message.format(
                list_name_fieldname, list_name_limit))])

    invite_username = StringField(
        'Share list with User', validators=[Optional()])

    submit = SubmitField('Confirm')


class NewListItemForm(FlaskForm):
    length_message = "{} cannot be more than {} characters."

    item_name_fieldname = "Item name"
    item_name_limit = 24
    item_name = StringField(
        item_name_fieldname,
        render_kw={'maxlength': item_name_limit},
        validators=[DataRequired(), Length(
            max=item_name_limit,
            message=length_message.format(
                item_name_fieldname, item_name_limit))])

    item_desc_fieldname = "Item description"
    item_desc_limit = 1028
    item_desc = StringField(
        '{} (optional)'.format(item_desc_fieldname),
        render_kw={'maxlength': item_desc_limit},
        validators=[Optional(), Length(
            max=item_desc_limit,
            message=length_message.format(
                item_desc_fieldname, item_desc_limit))])

    item_url_fieldname = "Item URL"
    item_url_limit = 2083
    item_url = StringField(
        '{} (optional)'.format(item_url_fieldname),
        render_kw={'maxlength': item_url_limit},
        validators=[Optional(), URL(), Length(
            max=item_url_limit,
            message=length_message.format(
                item_url_fieldname, item_url_limit))])

    submit = SubmitField('Add Item')


class NewChatForm(FlaskForm):
    chat_with_username = StringField('Username', validators=[DataRequired()])
    # chat_name = StringField('Chat name', validators=[Optional()])
    submit = SubmitField('Create Chat')


class NewTickerForm(FlaskForm):
    length_message = "{} cannot be more than {} characters."

    ticker_name_fieldname = "Ticker"
    ticker_name_limit = 10
    ticker_name = StringField(
        ticker_name_fieldname,
        render_kw={'maxlength': ticker_name_limit},
        validators=[DataRequired(), Length(
            max=ticker_name_limit,
            message=length_message.format(
                ticker_name_fieldname, ticker_name_limit))])
    submit = SubmitField('Add Ticker')
