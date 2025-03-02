from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    phone_number = db.Column(db.String(20))
    role = db.Column(db.String(20), default='traveler')  # 'rider' or 'traveler'
    is_verified = db.Column(db.Boolean, default=True)  # Changed to True by default
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_image = db.Column(db.String(120), default='default.jpg')
    
    # Relationships
    rides_offered = db.relationship('Ride', backref='rider', lazy='dynamic',
                                  foreign_keys='Ride.rider_id')
    rides_taken = db.relationship('RideRequest', backref='traveler', lazy='dynamic',
                                foreign_keys='RideRequest.traveler_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'
