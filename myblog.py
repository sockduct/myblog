# This defines the Flask application instance:
# From the app package, import the app variable instance (defined in
# __init__.py)
from app import create_app, db, cli
from app.models import User, Post, Message, Notification

app = create_app()
cli.register(app)

# Define symbols to include in flask Python REPL session:
# flask shell
@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post, 'Message': Message,
            'Notification': Notification}

