from flask import Blueprint

bp = Blueprint('rides', __name__)

from app.rides import routes
