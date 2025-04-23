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

# Update the create_app function to create tables before initializing achievements

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    socketio.init_app(app)
    
    # Register blueprints
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.rides import bp as rides_bp
    app.register_blueprint(rides_bp, url_prefix='/rides')
    
    # Register the chat blueprint
    from app.chat import bp as chat_bp
    app.register_blueprint(chat_bp, url_prefix='/chat')
    
    # Register the green blueprint
    from app.green import bp as green_bp
    app.register_blueprint(green_bp, url_prefix='/green')
    
    # Import and register the chat socket events
    from app.chat import events
    
    # Create database tables and initialize green achievements
    with app.app_context():
        db.create_all()  # Create all tables first
        from app.green.routes import init_achievements
        init_achievements()
    
    return app
