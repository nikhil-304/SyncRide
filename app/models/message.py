from datetime import datetime
from app import db

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ride_request_id = db.Column(db.Integer, db.ForeignKey('ride_request.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relationships - using back_populates to fix the overlapping relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    ride_request = db.relationship('RideRequest', back_populates='messages', overlaps="request")
    
    def __repr__(self):
        return f'<Message {self.id}>'