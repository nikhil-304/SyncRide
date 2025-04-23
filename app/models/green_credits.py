from app import db
from datetime import datetime

class GreenCredit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(256))
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='green_credits')
    ride = db.relationship('Ride', backref='green_credits')
    
    def __repr__(self):
        return f'<GreenCredit {self.id}>'

class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(256))
    icon = db.Column(db.String(64))
    requirement = db.Column(db.Integer, default=0)
    achievement_type = db.Column(db.String(32), nullable=False)
    
    def __repr__(self):
        return f'<Achievement {self.name}>'

class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='achievements_earned')
    achievement = db.relationship('Achievement', backref='users_earned')
    
    def __repr__(self):
        return f'<UserAchievement {self.id}>'

class CreditRedemption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    reward_type = db.Column(db.String(32), nullable=False)
    reward_details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='credit_redemptions')
    
    def __repr__(self):
        return f'<CreditRedemption {self.id}>'