from datetime import datetime
from app import db

class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rider_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_location = db.Column(db.String(128), nullable=False)
    end_location = db.Column(db.String(128), nullable=False)
    start_latitude = db.Column(db.Float)
    start_longitude = db.Column(db.Float)
    end_latitude = db.Column(db.Float)
    end_longitude = db.Column(db.Float)
    departure_time = db.Column(db.DateTime, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    vehicle_type = db.Column(db.String(64))
    vehicle_number = db.Column(db.String(20))
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    requests = db.relationship('RideRequest', backref='ride', lazy='dynamic')
    
    def update_status(self):
        """Update ride status based on time"""
        if self.status == 'active' and self.departure_time <= datetime.utcnow():
            self.status = 'completed'
            self.available_seats = 0
            # Update all ride requests
            for request in self.requests:
                if request.status == 'pending':
                    request.status = 'cancelled'
                elif request.status == 'accepted':
                    request.status = 'completed'
            db.session.commit()
            return True
        return False
    
    def __repr__(self):
        return f'<Ride {self.id}>'

class RideRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=False)
    traveler_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected, completed
    pickup_location = db.Column(db.String(128))
    pickup_latitude = db.Column(db.Float)
    pickup_longitude = db.Column(db.Float)
    seats_requested = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<RideRequest {self.id}>'

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ride_request_id = db.Column(db.Integer, db.ForeignKey('ride_request.id'), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Rating {self.id}>'
