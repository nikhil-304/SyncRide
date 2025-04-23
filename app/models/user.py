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
    
    # Add these methods to the User class
    
    def get_total_credits(self):
        """Get total green credits for user"""
        from app.models.green_credits import GreenCredit, CreditRedemption
        
        # Sum all earned credits
        earned = GreenCredit.query.filter_by(user_id=self.id).with_entities(
            db.func.sum(GreenCredit.amount)).scalar() or 0
        
        # Sum all redeemed credits
        redeemed = CreditRedemption.query.filter_by(user_id=self.id).with_entities(
            db.func.sum(CreditRedemption.amount)).scalar() or 0
        
        # Return available credits
        return earned - redeemed
    
    def get_carbon_saved(self):
        """Get total carbon saved in kg CO2"""
        from app.models.green_credits import GreenCredit
        from app.models.ride import Ride, RideRequest
        
        total_saved = 0
        
        # Calculate based on completed rides
        if self.role == 'rider':
            # For drivers, calculate based on rides offered
            rides = Ride.query.filter_by(rider_id=self.id, status='completed').all()
            for ride in rides:
                # Calculate carbon savings for each ride
                from app.green.routes import calculate_carbon_savings
                total_saved += calculate_carbon_savings(ride)
        else:
            # For passengers, calculate based on rides taken
            ride_requests = RideRequest.query.filter_by(traveler_id=self.id, status='completed').all()
            for request in ride_requests:
                # Each passenger saves approximately 0.12 kg CO2 per km
                from app.utils.distance import calculate_distance
                ride = request.ride
                distance = calculate_distance(
                    ride.start_latitude, ride.start_longitude,
                    ride.end_latitude, ride.end_longitude
                )
                total_saved += distance * 0.12
        
        return round(total_saved, 2)
    
    # Add this method to the User class
    
    def get_leaderboard_position(self):
        """Get the user's position on the leaderboard"""
        # Get all users sorted by credits
        users = User.query.all()
        sorted_users = sorted(users, key=lambda u: u.get_total_credits(), reverse=True)
        
        # Find the position of the current user
        for i, user in enumerate(sorted_users):
            if user.id == self.id:
                return i + 1  # +1 because positions start at 1, not 0
        
        return len(sorted_users)  # Fallback if user not found
