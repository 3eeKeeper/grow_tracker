from flask import Blueprint

bp = Blueprint('plants', __name__)

from app.plants import routes
