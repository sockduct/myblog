from flask import Blueprint

bp = Blueprint('auth', __name__)

# Import here to avoid circular dependencies
from app.auth import routes

