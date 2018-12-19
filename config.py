from dotenv import load_dotenv
import os

# __file__ is the full pathname of this module
basedir = os.path.abspath(os.path.dirname(__file__))
# Load environment variables from this file
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    # Probably better to use something like Vault to store/generate secret key
    # This will try to get secret key from environment variable SECRET_KEY, and
    # if that doesn't exist (or is empty?) then it uses the string to the right
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-secret'
    # Note - //<no-host-because-local>/<file-path>, thus: '///'
    # flask-sqlalchemy extension uses this:
    SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL') or 'sqlite:///' + 
                               os.path.join(basedir, 'app.db'))
    # Do you want to be notified of whenever database is about to be changed
    # We don't need and must be set to avoid be prompted/nagged
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #
    # Log to stdout or log file?
    # Needed for Heroku where you can't rely on a persistent file system for
    # log files:
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
    #
    # Email config - also usable by flask-mail:
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['admin@example.com']
    #
    # Languages supported by app:
    LANGUAGES = ['en', 'es', 'pl']
    #
    # API Key for Azure Translation Service
    MS_TRANSLATOR_KEY = os.environ.get('MS_TRANSLATOR_KEY')
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
    #
    # Where to find Redis Server
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
    #
    # How many posts to display per page:
    POSTS_PER_PAGE = 5

