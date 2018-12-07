from app.models import User
# Here we use lazy_gettext instead of _ because babel needs to translate when
# this module is parsed vs. routes.py where text is translated upon processing
# a GET request
from flask import request
from flask_babel import _, lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, ValidationError, Length


class EditProfileForm(FlaskForm):
    username = StringField(_l('Username'), validators=[DataRequired()])
    # Note - username/email/password fields would also benefit from using a
    # length validator:
    about_me = TextAreaField(_l('About me'), validators=[Length(min=0, max=140)])
    submit = SubmitField(_l('Submit'))

    # Create constructure which accepts original username as argument
    def __init__(self, original_username, *args, **kwargs):
        # Call parent constructor
        super(EditProfileForm, self).__init__(*args, **kwargs)
        # Save original username
        self.original_username = original_username

    # Can't just check existing username - if user edit's profile and doesn't
    # change username he/she will pass in same username and that's fine
    # But if he/she changes username we need to make sure the new username
    # isn't already in use
    def validate_username(self, username):
        # Did user change his/her username?
        if username.data != self.original_username:
            # If yes, make sure new username is unique/not in use
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError(_('Please use a different username.'))


class PostForm(FlaskForm):
    post = TextAreaField(_l('Say something'), validators=[DataRequired(), Length(min=1, max=140)])
    submit = SubmitField(_l('Submit'))


class SearchForm(FlaskForm):
    # Submit not needed for form with text field - browser submits when you
    # user hits enter with focus on this field
    q = StringField(_l('Search'), validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        # Where does Flask-WTF get form data?  Default is request.form, but
        # since we're using GET vs. POST, values are in query string so look
        # in request.args instead
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        # Disable CSRF to allow sharing search links
        # OK because no security implications in this case
        if 'csrf_enabled' not in kwargs:
            kwargs['csrf_enabled'] = False
        super(SearchForm, self).__init__(*args, **kwargs)

