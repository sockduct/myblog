from config import Config
from flask import Flask, request
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

# Create an instance of Flask named app
# Pass Flask __name__ which is the name of this module
# Flask uses __name__ as a starting point for associated resources such as
# template files
app = Flask(__name__)

# Get configuration settings from config.py:
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login = LoginManager(app)
# Where should flask_login send users who try to view protected URLs when
# they're not authenticated:
login.login_view=('login')
login.login_message = _l('Please log in to access this page.')
mail = Mail(app)
# Provides access to bootstrap base templates
bootstrap = Bootstrap(app)
moment = Moment(app)
babel = Babel(app)

# Make sure we're not in debug mode - if we are then ignore
if not app.debug:
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


# Choose best language to respond with based on user request
@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(app.config['LANGUAGES'])
    # Hard code language setting for testing:
    # return 'es'


# From the app package, import the routes and models modules
# Imported at the end as it depends on app defined above, so this avoids a
# circular dependency
from app import routes, models, errors

