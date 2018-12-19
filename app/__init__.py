from config import Config
from elasticsearch import Elasticsearch
from flask import Flask, request, current_app
from flask_babel import Babel, lazy_gettext as _l
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from redis import Redis
import rq

# Create an instance of Flask named app
# Pass Flask __name__ which is the name of this module
# Flask uses __name__ as a starting point for associated resources such as
# template files
# Don't do this way with blueprints
# app = Flask(__name__)

# Don't do this with with blueprints
# Get configuration settings from config.py:
# app.config.from_object(Config)

# With blueprints, don't pass in app:
# db = SQLAlchemy(app)
db = SQLAlchemy()
# migrate = Migrate(app, db)
migrate = Migrate()
# login = LoginManager(app)
login = LoginManager()
# Where should flask_login send users who try to view protected URLs when
# they're not authenticated:
# login.login_view= 'login'
login.login_view = 'auth.login'
login.login_message = _l('Please log in to access this page.')
# mail = Mail(app)
mail = Mail()
# Provides access to bootstrap base templates
# bootstrap = Bootstrap(app)
bootstrap = Bootstrap()
# moment = Moment(app)
moment = Moment()
# babel = Babel(app)
babel = Babel()


# Encapsulate in factory function
def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)
    babel.init_app(app)
    # No elasticsearch Flask extension so have to do differently
    # Add as attribute to app so accessible anywhere current_app is
    # If environment variable isn't set then search will be disabled
    app.elasticsearch = (Elasticsearch([app.config['ELASTICSEARCH_URL']])
                         if app.config['ELASTICSEARCH_URL'] else None)
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('myblog-tasks', connection=app.redis)

    # Put import here to avoid circular dependencies
    # Also need to delay import until this point so we have app instance
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    # With url_prefix, all routes in this blueprint get this prefix
    # So the login URL will be /auth/login
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    # Make sure we're not in debug or testing mode - if we are then ignore
    if not app.debug and not app.testing:
        # Make sure a mail server is configured
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'], subject='Myblog Failure',
                credentials=auth, secure=secure)
            # Log errors and above
            mail_handler.setLevel(logging.ERROR)
            # Add mail server setup as target for logging (e.g., when stack traces
            # occur)
            app.logger.addHandler(mail_handler)

        # If this variable is set, we need to log to stdout instead of a log
        # file
        if app.config['LOG_TO_STDOUT']:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            app.logger.addHandler(stream_handler)
        # Otherwise, log to a log file
        else:
            # Also log stack traces to a file
            # Create logs directory if doesn't exist
            if not os.path.exists('logs'):
                os.mkdir('logs')
            # Log up to 10k/file then rotate, keep 10
            file_handler = RotatingFileHandler('logs/myblog.log', maxBytes=10240, backupCount=10)
            # What to output to file
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
            # Log at level info and above
            file_handler.setLevel(logging.INFO)
            # Add file as target for logging
            app.logger.addHandler(file_handler)

        # Change app logging level to info
        app.logger.setLevel(logging.INFO)
        # Use application logger to log app start
        app.logger.info('Myblog startup')

    return app


# Choose best language to respond with based on user request
@babel.localeselector
def get_locale():
    # return request.accept_languages.best_match(app.config['LANGUAGES'])
    # For blueprints, use current_app
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])
    # Hard code language setting for testing:
    # return 'es'


# From the app package, import the routes and models modules
# Imported at the end as it depends on app defined above, so this avoids a
# circular dependency
from app import models

