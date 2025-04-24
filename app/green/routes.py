from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.green import bp
from app.models.green_credits import GreenCredit, Achievement, UserAchievement, CreditRedemption
from app.models.user import User
from app.models.ride import Ride, RideRequest
from sqlalchemy import desc
from datetime import datetime
from app.utils.distance import calculate_distance  # Import the utility function

@bp.route('/dashboard')
@login_required
def dashboard():
    # Get user's green credits
    credits = GreenCredit.query.filter_by(user_id=current_user.id).order_by(desc(GreenCredit.created_at)).all()
    
    # Get user's redemptions
    redemptions = CreditRedemption.query.filter_by(user_id=current_user.id).order_by(desc(CreditRedemption.created_at)).all()
    
    # Get user's achievements
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).order_by(desc(UserAchievement.earned_at)).all()
    
    # Calculate total credits
    total_credits = current_user.get_total_credits()
    
    # Calculate carbon saved
    carbon_saved = current_user.get_carbon_saved()
    
    # Get leaderboard position
    leaderboard_position = current_user.get_leaderboard_position()
    
    return render_template('green/dashboard.html', 
                           total_credits=total_credits,
                           carbon_saved=carbon_saved,
                           leaderboard_position=leaderboard_position,
                           credits=credits,
                           redemptions=redemptions,
                           user_achievements=user_achievements)

@bp.route('/leaderboard')
def leaderboard():
    # Get all users sorted by total credits
    users = User.query.all()
    users = sorted(users, key=lambda u: u.get_total_credits(), reverse=True)
    
    # Get current user's position if logged in
    user_position = None
    if current_user.is_authenticated:
        user_position = current_user.get_leaderboard_position()
    
    return render_template('green/leaderboard.html', 
                           users=users,
                           user_position=user_position)

@bp.route('/achievements')
@login_required
def achievements():
    # Get all achievements
    all_achievements = Achievement.query.all()
    
    # Group achievements by type
    achievement_groups = {}
    for achievement in all_achievements:
        if achievement.achievement_type not in achievement_groups:
            achievement_groups[achievement.achievement_type] = []
        achievement_groups[achievement.achievement_type].append(achievement)
    
    # Get user's earned achievements
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    earned_achievement_ids = [ua.achievement_id for ua in user_achievements]
    
    return render_template('green/achievements.html',
                           all_achievements=all_achievements,
                           achievement_groups=achievement_groups,
                           earned_achievement_ids=earned_achievement_ids)

@bp.route('/redeem', methods=['GET', 'POST'])
@login_required
def redeem_credits():
    # Get user's total credits
    total_credits = current_user.get_total_credits()
    
    if request.method == 'POST':
        reward_type = request.form.get('reward_type')
        amount = int(request.form.get('amount'))
        details = request.form.get('details', '')
        
        # Validate reward type
        valid_types = ['discount', 'donation', 'priority']
        if reward_type not in valid_types:
            flash('Invalid reward type selected.', 'danger')
            return redirect(url_for('green.redeem_credits'))
        
        # Validate amount based on type
        expected_amount = 0
        if reward_type == 'discount':
            expected_amount = 50
        elif reward_type == 'donation':
            expected_amount = 100
        elif reward_type == 'priority':
            expected_amount = 75
        
        if amount != expected_amount:
            flash('Invalid credit amount.', 'danger')
            return redirect(url_for('green.redeem_credits'))
        
        # Check if user has enough credits
        if total_credits < amount:
            flash('You do not have enough credits for this reward.', 'danger')
            return redirect(url_for('green.redeem_credits'))
        
        # Create redemption record
        redemption = CreditRedemption(
            user_id=current_user.id,
            amount=amount,
            reward_type=reward_type,
            reward_details=details
        )
        db.session.add(redemption)
        
        # Process reward
        reward_message = ''
        if reward_type == 'discount':
            reward_message = 'You have redeemed a 20% discount on your next ride!'
        elif reward_type == 'donation':
            reward_message = 'Thank you for your donation to environmental causes!'
        elif reward_type == 'priority':
            reward_message = 'You now have priority matching for the next 14 days!'
        
        try:
            db.session.commit()
            flash(f'Credits redeemed successfully! {reward_message}', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error redeeming credits. Please try again.', 'danger')
        
        return redirect(url_for('green.dashboard'))
    
    return render_template('green/redeem.html', total_credits=total_credits)

def award_ride_credits(ride_request):
    """Award green credits for completed ride"""
    if ride_request.status != 'completed':
        return
    
    ride = ride_request.ride
    traveler = User.query.get(ride_request.traveler_id)
    rider = User.query.get(ride.rider_id)
    
    # Calculate base credits (10 credits per ride)
    base_credits = 10
    
    # Award credits to traveler
    traveler_credit = GreenCredit(
        user_id=traveler.id,
        amount=base_credits,
        reason="Completed ride as traveler",
        ride_id=ride.id
    )
    db.session.add(traveler_credit)
    
    # Award credits to rider
    rider_credit = GreenCredit(
        user_id=rider.id,
        amount=base_credits,
        reason=f"Completed ride with {traveler.username}",
        ride_id=ride.id
    )
    db.session.add(rider_credit)
    
    # Check for achievements
    check_achievements(traveler)
    check_achievements(rider)
    
    db.session.commit()

def check_achievements(user):
    """Check and award achievements for a user"""
    # Get all achievements
    achievements = Achievement.query.all()
    
    # Get user's earned achievements
    earned_achievements = UserAchievement.query.filter_by(user_id=user.id).all()
    earned_achievement_ids = [ua.achievement_id for ua in earned_achievements]
    
    for achievement in achievements:
        # Skip if already earned
        if achievement.id in earned_achievement_ids:  # This line has the error - using earned_ids instead of earned_achievement_ids
            continue
        
        # Check if achievement should be awarded
        should_award = False
        
        if achievement.achievement_type == 'rides_completed':
            # Count completed rides based on user role
            if user.role == 'rider':
                completed_rides = user.rides_offered.filter_by(status='completed').count()
            else:
                completed_rides = user.rides_taken.filter_by(status='completed').count()
            
            should_award = completed_rides >= achievement.requirement
            
        elif achievement.achievement_type == 'carbon_saved':
            carbon_saved = user.get_carbon_saved()
            should_award = carbon_saved >= achievement.requirement
            
        elif achievement.achievement_type == 'credits_earned':
            total_credits = user.get_total_credits()
            should_award = total_credits >= achievement.requirement
        
        # Award achievement if criteria met
        if should_award:
            new_achievement = UserAchievement(
                user_id=user.id,
                achievement_id=achievement.id,
                earned_date=datetime.utcnow()
            )
            db.session.add(new_achievement)
            
            # Add notification
            notification = Notification(
                user_id=user.id,
                message=f"You've earned the '{achievement.name}' achievement!",
                icon=achievement.icon,
                link=url_for('green.achievements')
            )
            db.session.add(notification)
            
            # Award bonus credits for achievement
            bonus_credits = GreenCredit(
                user_id=user.id,
                amount=20,  # Bonus credits for achievement
                reason=f"Achievement bonus: {achievement.name}",
                ride_id=None
            )
            db.session.add(bonus_credits)
            
            # Commit changes
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error awarding achievement: {str(e)}")

# Carbon saved achievements
            carbon_achievements = Achievement.query.filter_by(achievement_type='carbon_saved').all()
            for achievement in carbon_achievements:
                if achievement.id not in earned_ids and carbon_saved >= achievement.requirement:
                    new_achievement = UserAchievement(
                        user_id=user.id,
                        achievement_id=achievement.id
                    )
                    db.session.add(new_achievement)
                    
                    # Bonus credits for earning achievement
                    bonus_credit = GreenCredit(
                        user_id=user.id,
                        amount=25,
                        reason=f"Earned achievement: {achievement.name}"
                    )
                    db.session.add(bonus_credit)
    
    # Credits earned achievements
    credit_achievements = Achievement.query.filter_by(achievement_type='credits_earned').all()
    for achievement in credit_achievements:
        if achievement.id not in earned_ids and total_credits >= achievement.requirement:
            new_achievement = UserAchievement(
                user_id=user.id,
                achievement_id=achievement.id
            )
            db.session.add(new_achievement)
            
            # Bonus credits for earning achievement
            bonus_credit = GreenCredit(
                user_id=user.id,
                amount=25,
                reason=f"Earned achievement: {achievement.name}"
            )
            db.session.add(bonus_credit)

# Function to initialize default achievements
def init_achievements():
    """Initialize default achievements if they don't exist"""
    if Achievement.query.count() == 0:
        achievements = [
            # Ride achievements
            Achievement(
                name="First Ride",
                description="Complete your first ride",
                icon="fas fa-car",
                requirement=1,
                achievement_type="rides_completed"
            ),
            Achievement(
                name="Regular Rider",
                description="Complete 5 rides",
                icon="fas fa-car",
                requirement=5,
                achievement_type="rides_completed"
            ),
            Achievement(
                name="Ride Master",
                description="Complete 25 rides",
                icon="fas fa-car-side",
                requirement=25,
                achievement_type="rides_completed"
            ),
            Achievement(
                name="Ride Legend",
                description="Complete 100 rides",
                icon="fas fa-car-alt",
                requirement=100,
                achievement_type="rides_completed"
            ),
            
            # Carbon saved achievements
            Achievement(
                name="Green Starter",
                description="Save 5kg of CO₂",
                icon="fas fa-leaf",
                requirement=5,
                achievement_type="carbon_saved"
            ),
            Achievement(
                name="Eco Warrior",
                description="Save 25kg of CO₂",
                icon="fas fa-seedling",
                requirement=25,
                achievement_type="carbon_saved"
            ),
            Achievement(
                name="Climate Champion",
                description="Save 100kg of CO₂",
                icon="fas fa-tree",
                requirement=100,
                achievement_type="carbon_saved"
            ),
            Achievement(
                name="Earth Savior",
                description="Save 500kg of CO₂",
                icon="fas fa-globe-americas",
                requirement=500,
                achievement_type="carbon_saved"
            ),
            
            # Credits earned achievements
            Achievement(
                name="Credit Collector",
                description="Earn 50 green credits",
                icon="fas fa-coins",
                requirement=50,
                achievement_type="credits_earned"
            ),
            Achievement(
                name="Credit Enthusiast",
                description="Earn 200 green credits",
                icon="fas fa-money-bill-wave",
                requirement=200,
                achievement_type="credits_earned"
            ),
            Achievement(
                name="Credit Tycoon",
                description="Earn 500 green credits",
                icon="fas fa-gem",
                requirement=500,
                achievement_type="credits_earned"
            ),
            Achievement(
                name="Credit Millionaire",
                description="Earn 1000 green credits",
                icon="fas fa-crown",
                requirement=1000,
                achievement_type="credits_earned"
            )
        ]
        
        for achievement in achievements:
            db.session.add(achievement)
        
        db.session.commit()
        print("Default achievements initialized")

# Function to calculate carbon savings for a ride
def calculate_carbon_savings(ride):
    """Calculate carbon savings for a ride in kg CO2"""
    # Calculate distance in km
    distance = calculate_distance(
        ride.start_latitude, ride.start_longitude,
        ride.end_latitude, ride.end_longitude
    )
    
    # Average car emissions: ~120g CO2 per km per person
    # Shared ride with 2 people saves ~120g per km
    # If more people, savings increase
    passengers = ride.requests.filter_by(status='completed').count()
    
    if passengers == 0:
        return 0
    
    # Calculate savings: distance * emissions * passengers
    carbon_saved = distance * 0.12 * passengers  # in kg
    
    return round(carbon_saved, 2)

# Register the init_achievements function to be called when the app starts
def register_init_app(app):
    @app.before_first_request
    def initialize_app():
        init_achievements()