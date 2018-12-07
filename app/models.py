# Database models (provided by SQLAlchemy)
# These models represent data (rows) in database via classes

from app import db, login
from app.search import add_to_index, remove_from_index, query_index
from datetime import datetime
from flask import current_app
from flask_login import UserMixin
from hashlib import md5
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

