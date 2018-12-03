from app import app, db
from app.forms import (LoginForm, RegistrationForm, EditProfileForm, PostForm,
                       ResetPasswordRequestForm, ResetPasswordForm)
from app.translate import translate
from app.models import User, Post
from app.email import send_password_reset_email
from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, jsonify
from flask_babel import _, get_locale
from flask_login import current_user, login_user, logout_user, login_required
from guess_language import guess_language
from werkzeug.urls import url_parse


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        # Don't have to do db.session.add because current_user loads the
        # current user into the current database session
        db.session.commit()
    # Record user's locale
    # g provided by flask - per request storage, can use in any view function
    # or in templates, this lets us pass locale to JS moment library
    g.locale = str(get_locale())


# Decorating a function with app.route routes URLs to a view function
# Note that the app.route decorators should be first
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
# Prevent non-authenticated users from viewing:
@login_required
# This is a view function
def index():
    form = PostForm()
    if form.validate_on_submit():
        # Attempt to identify language used in post
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:
	    # Don't understand language, store as blank - no translation
	    # will be offered
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        # Redirect instead of render template because after post should always
        # redirect to prevent accidental form re-submission
        return redirect(url_for('index'))
    # Temporarily create fake/mock user
    # user = {'username': 'james'}
    # Create fack/mock blog posts
    '''
    posts = [
                {'author': {'username': 'John'},
                 'body': 'Beautiful day in Paris!'},
                {'author': {'username': 'Sara'},
                 'body': 'The dance competition was fantastic!'}
            ]
    '''
    # Check query parameter for which page to start at
    page = request.args.get('page', 1, type=int)

    # Replace with database posts
    # Unpaginated version:
    # posts = current_user.followed_posts().all()
    # With pagination - page to render, how many posts/page, should we return 404
    # if go past the end? (False = return empty list)
    posts = current_user.followed_posts().paginate(page, app.config['POSTS_PER_PAGE'], False)
    # Passing a keyword parameter to url_for causes it to use it as a query
    # parameter for the generated URL if it's not consumed (e.g., used for
    # dynamic parameter)
    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None
    # Test without title to see Jinja2/template conditional:
    # return render_template('index.html', user=user)
    # return render_template('index.html', title='Home', user=user, posts=posts)
    # When eliminate fake user, no longer need to pass to template
    # When add pagination, posts is now a pagination object - to get lists of
    # posts, need to add .items
    # return render_template('index.html', title='Home', form=form, posts=posts)
    return render_template('index.html', title=_('Home'), form=form, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)

    # Add pagination
    # posts = Post.query.order_by(Post.timestamp.desc()).all()
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page,
            app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) if posts.has_prev else None
    # return render_template('index.html', title='Explore', posts=posts)
    return render_template('index.html', title=_('Explore'), posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Make sure user not already authenticated:
    if current_user.is_authenticated:
        return redirect(url_for('index'))

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
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        # Retrieve next query parameter (where user was trying to go before
        # they got redirected to authenticate)
        next_page = request.args.get('next')
        # Validate if next_page exists that its a relative URL:
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        # Want to render index.html page, but rather than repeat the code,
        # redirect the user to the correct route:
        # Rather than using explicit URL, use the view function - makes it
        # easier to maintain:
        return redirect(next_page)
    return render_template('login.html', title=_('Sign In'), form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    # Make sure user not already authenticated:
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are not a registered user!'))
        return redirect(url_for('login'))
    return render_template('register.html', title=_('Register'), form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash(_('Check your email for the instructions to reset your password'))
        return redirect(url_for('login'))
    return render_template('reset_password_request.html', title=_('Reset Password'), form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reset.'))
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


# <username> is a dynamic URL path component passed to the function
@app.route('/user/<username>')
@login_required
def user(username):
    # If user not found, raise a 404 error
    user = User.query.filter_by(username=username).first_or_404()
    # If made it here, user exists
    # Create some temporary fake/mock posts
    '''
    posts = [
                {'author': user, 'body': 'Test post #1'},
                {'author': user, 'body': 'Test post #2'}
            ]
    '''
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(page,
            app.config['POSTS_PER_PAGE'], False)
    next_url = (url_for('explore', username=user.username, page=posts.next_num)
                if posts.has_next else None)
    prev_url = (url_for('explore', username=user.username, page=posts.prev_num)
                if posts.has_prev else None)
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    # Pass in original username to validate renames
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been save.'))
        return redirect(url_for('edit_profile'))
    # Pre-populate form with current values:
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'), form=form)


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        # Flask-babel requires this:
        # flash(_('User %(username)s not found.', username=username))
        # It doesn't support the newer format method
        # Old - if use this, then when run pybabel extract it fails:
        # flash(_(f'User {username} not found.'))
        # New:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('index'))
    if user == current_user:
        flash(_('You cannot follow yourself!'))
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(_('You are now following %(username)s!', username=username))
    return redirect(url_for('user', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('index'))
    if user == current_user:
        flash(_('You cannot unfollow yourself!'))
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(_('You are no longer following %(username)s.', username=username))
    return redirect(url_for('user', username=username))


@app.route('/translate', methods=['POST'])
@login_required
def translate_text():
    # First, call translate module passing form data using flask.request
    # Take returned data and put it in a dictionary as a value of the key
    # "text"
    # Return this as JSON using flask's jsonify
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})

