# Database models (provided by SQLAlchemy)
# These models represent data (rows) in database via classes

from app import db, login
from app.search import add_to_index, remove_from_index, query_index
from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from hashlib import md5
import redis
import rq
import json
import jwt
from time import time
from werkzeug.security import generate_password_hash, check_password_hash


class SearchableMixin(object):
    @classmethod
    # Wraps search.query_index and replaces list of IDs with objects
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression, page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    @classmethod
    # Save db updates (they're lost after commit)
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    @classmethod
    # After db commit, update elasticsearch indices:
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        session._changes = None

    @classmethod
    # Allows adding all entries from model to elasticsearch index
    def reindex(cls):
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


# Leverage SQLAlchemy events to keep elasticsearch index up to date
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)


# Auxiliary table to facilitate many-to-many relationship between follower
# users and followed users
# Not making this a model (class) because we won't use directly
followers = db.Table(
    # Table name
    'followers',
    # Foreign keys
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


# SQLAlchemy base class for models - db.Model
class User(UserMixin, db.Model):
    # Primary Key:
    id = db.Column(db.Integer, primary_key=True)
    # Index to allow fast searching and sorting within column:
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    # Make it easy to find posts by author name and vice versa:
    # db.relationship defined on the one side of 1:Many, allows accessing
    # all of user's posts
    # Backref allows finding author from Post (Post.author)
    # Lazy makes this a query instead of an actual list, also allows for
    # flexible querying
    # Here we use capital "Post" because it refers to model
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    # Additional user information:
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    # Dynamic list of users followed by this user
    followed = db.relationship(
        # User here is the right-side or followed users by class User
        # Secondary is pointing to auxiliary table defined above
        'User', secondary=followers,
        # Link left-side/follower side with association table
        # followers.c.follower_id = table.columns.column_name
        primaryjoin=(followers.c.follower_id == id),
        # Link right-side/followed side with association table
        secondaryjoin=(followers.c.followed_id == id),
        # Allow seeing relationship from right side (followed side),
        # make right-side dynamic (done via query)
        backref=db.backref('followers', lazy='dynamic'),
        # Also want left-side to be dynamic
        lazy='dynamic')
    messages_sent = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='author', lazy='dynamic')
    messages_received = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient', lazy='dynamic')
    last_message_read_time = db.Column(db.DateTime)
    notifications = db.relationship('Notification', backref='user',
                                    lazy='dynamic')
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        # Get list of followed user posts sorted by post timestamp
        # return Post.query.join(followers, (followers.c.followed_id == Post.user_id)).filter(
        #         followers.c.follower_id == self.id).order_by(Post.timestamp.desc())
        followed =  Post.query.join(followers, (followers.c.followed_id == Post.user_id)
                                   ).filter(followers.c.follower_id == self.id)
        # Add users own posts
        return followed.union(self.posts).order_by(Post.timestamp.desc())

    def get_reset_password_token(self, expires_in=600):
        # jwt.encode creates a bytes object so convert it to a string
        return jwt.encode(
                {'reset_password': self.id, 'exp': time() + expires_in},
                current_app.config['SECRET_KEY'], algorithm='HS256').decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                    algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(id)

    def new_messages(self):
        last_read_time = self.last_message_read_time or datetime(1900, 1, 1)
        return Message.query.filter_by(recipient=self).filter(
            Message.timestamp > last_read_time).count()

    def add_notification(self, name, data):
        # If user already has message notification count pending, delete it
        # so we can replace it
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user=self)
        db.session.add(n)
        return n

    def launch_task(self, name, description, *args, **kwargs):
        # Jobs will be launched from app.tasks module with function name passed in
        # We'll also pass the user ID as an argument along with any other passed
        # in args
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, self.id,
                                                *args, **kwargs)
        # Once job created, store it in the database
        task = Task(id=rq_job.get_id(), name=name, description=description,
                    user=self)
        # Add to db session, but don't commit
        # Prefer to leave commits to higher level functions allowing several
        # updates in a single transaction (if desired)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    def get_task_in_progress(self, name):
        # As design decision won't allow multiple tasks of same name running
        # at same time for same user so can use .first()
        return Task.query.filter_by(name=name, user=self, complete=False).first()


# flask_login keeps track of users in flask's user session via their user id
# We need a function which given the user id, returns the user object
# This decorator identifies this as the user loader function
@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(SearchableMixin, db.Model):
    # This is ignored by SQLAlchemy but we'll use to mark which fields need to
    # be included in search index (this is just a marker variable):
    __searchable__ = ['body']
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    # For default, notice passing function/method but not executing it (no
    # trailing parenthesis)!
    # Always store in UTC time, then convert to user's TZ when displaying
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    # user_id is a foreign key pointing to author's User ID
    # Here we use lower case "user" because it referes to the table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Identify and store language of the post to potentially offer translation
    language = db.Column(db.String(5))

    def __repr__(self):
        return f'<Post {self.body}>'


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Message {}>'.format(self.body)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # Use JavaScript friendly timestamp
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))


class Task(db.Model):
    # Rather than using database generated integer id, use string id
    # generated by rq for primary key
    id = db.Column(db.String(36), primary_key=True)
	# the name is the task's fully qualified name as passed to rq
    name = db.Column(db.String(128), index=True)
	# task description we can show users
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100

