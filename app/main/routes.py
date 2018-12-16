from app import db
from app.main import bp
from app.main.forms import EditProfileForm, PostForm, SearchForm, MessageForm
from app.models import User, Post, Message, Notification
from app.translate import translate
from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, jsonify, current_app
from flask_babel import _, get_locale
from flask_login import current_user, login_required
from guess_language import guess_language


@bp.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        # Don't have to do db.session.add because current_user loads the
        # current user into the current database session
        db.session.commit()
        # Instantiate search form before request so can search from any page
        # In this block because only want authenticated users to be able to
        # search
        # Also note that templates can always "see" g even if you don't pass it
        g.search_form = SearchForm()
    # Record user's locale
    # g provided by flask - per request storage, can use in any view function
    # or in templates, this lets us pass locale to JS moment library
    g.locale = str(get_locale())


# Decorating a function with app.route routes URLs to a view function
# Note that the app.route decorators should be first
@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
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
        return redirect(url_for('main.index'))
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
    posts = current_user.followed_posts().paginate(page, current_app.config['POSTS_PER_PAGE'], False)
    # Passing a keyword parameter to url_for causes it to use it as a query
    # parameter for the generated URL if it's not consumed (e.g., used for
    # dynamic parameter)
    next_url = url_for('main.index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) if posts.has_prev else None
    # Test without title to see Jinja2/template conditional:
    # return render_template('index.html', user=user)
    # return render_template('index.html', title='Home', user=user, posts=posts)
    # When eliminate fake user, no longer need to pass to template
    # When add pagination, posts is now a pagination object - to get lists of
    # posts, need to add .items
    # return render_template('index.html', title='Home', form=form, posts=posts)
    return render_template('index.html', title=_('Home'), form=form, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)

    # Add pagination
    # posts = Post.query.order_by(Post.timestamp.desc()).all()
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(page,
            current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) if posts.has_prev else None
    # return render_template('index.html', title='Explore', posts=posts)
    return render_template('index.html', title=_('Explore'), posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


# <username> is a dynamic URL path component passed to the function
@bp.route('/user/<username>')
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
            current_app.config['POSTS_PER_PAGE'], False)
    next_url = (url_for('main.explore', username=user.username, page=posts.next_num)
                if posts.has_next else None)
    prev_url = (url_for('main.explore', username=user.username, page=posts.prev_num)
                if posts.has_prev else None)
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/user/<username>/popup')
@login_required
def user_popup(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user_popup.html', user=user)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    # Pass in original username to validate renames
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been save.'))
        return redirect(url_for('main.edit_profile'))
    # Pre-populate form with current values:
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'), form=form)


@bp.route('/follow/<username>')
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
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot follow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(_('You are now following %(username)s!', username=username))
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot unfollow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(_('You are no longer following %(username)s.', username=username))
    return redirect(url_for('main.user', username=username))


@bp.route('/translate', methods=['POST'])
@login_required
def translate_text():
    # First, call translate module passing form data using flask.request
    # Take returned data and put it in a dictionary as a value of the key
    # "text"
    # Return this as JSON using flask's jsonify
    return jsonify({'text': translate(request.form['text'],
                                      request.form['source_language'],
                                      request.form['dest_language'])})


@bp.route('/search')
@login_required
def search():
    # Can't use form.validate_on_submit() - only works for POSTs
    # This validation just makes sure there's actually a non-empty search query
    # submitted
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(g.search_form.q.data, page,
                               current_app.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * current_app.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Search'), posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count', user.new_messages())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)


@bp.route('/messages')
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    # Return in JSON format since for JavaScript
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])

