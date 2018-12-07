from flask import Blueprint

bp = Blueprint('main', __name__)

# Import here to avoid circular dependencies
from app.main import routes

