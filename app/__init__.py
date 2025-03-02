from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
from config import Config

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
bcrypt = Bcrypt()
socketio = SocketIO()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    socketio.init_app(app)

    # Set up login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.rides import bp as rides_bp
    app.register_blueprint(rides_bp, url_prefix='/rides')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app
