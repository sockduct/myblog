# Define views for errors - 404, 500
from flask import render_template
from app import app, db


@app.errorhandler(404)
# error receives the exception object
def not_found_error(error):
    # Return 404 status code (2nd argument) instead of the default 200
    # Note - can also do this in view functions, but unusual
    return render_template('404.html'), 404


@app.errorhandler(500)
def not_found_error(error):
    # When an unexpected exception happens, there may be data left in the
    # current db session - flush it out:
    db.session.rollback()
    return render_template('500.html'), 500

