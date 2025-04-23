from flask import Blueprint

bp = Blueprint('green', __name__)

from app.green import routes