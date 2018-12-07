from flask import Blueprint

# Use local templates directory:
# bp = Blueprint('errors', __name__, template_folder='templates')
bp = Blueprint('errors', __name__)

# Put import at bottom to avoid circular dependencies
# Import error handlers to register them with this blueprint
from app.errors import handlers

