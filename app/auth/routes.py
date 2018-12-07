from app import db
from app.auth import bp
from app.auth.email import send_password_reset_email
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.models import User
from flask import render_template, flash, redirect, url_for, request
from flask_babel import _
from flask_login import current_user, login_user, logout_user
from guess_language import guess_language
from werkzeug.urls import url_parse


@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Make sure user not already authenticated:
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    # Does request have form data and all fields are valid?
    if form.validate_on_submit():
        # flash is like a webapp print - must add support for it in underlying
        # template too - this was just for testing:
        # flash(f'Login requested for user {form.username.data}, remember_me='
        #       f'{form.remember_me.data}')
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'))
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        # Retrieve next query parameter (where user was trying to go before
        # they got redirected to authenticate)
        next_page = request.args.get('next')
        # Validate if next_page exists that its a relative URL:
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        # Want to render index.html page, but rather than repeat the code,
        # redirect the user to the correct route:
        # Rather than using explicit URL, use the view function - makes it
        # easier to maintain:
        return redirect(next_page)
    return render_template('auth/login.html', title=_('Sign In'), form=form)


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    # Make sure user not already authenticated:
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are not a registered user!'))
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title=_('Register'), form=form)


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash(_('Check your email for the instructions to reset your password'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html', title=_('Reset Password'),
                           form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reset.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)

