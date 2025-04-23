from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required
from app.main import bp
from app.models.ride import Ride
from app.models.user import User
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from app import db

@bp.route('/')
def index():
    # Get some statistics for the landing page
    total_users = User.query.count()
    total_rides = Ride.query.count()
    
    # Count only active rides that haven't expired yet
    current_time = datetime.utcnow()
    active_rides = Ride.query.filter(
        Ride.status == 'active',
        Ride.departure_time > current_time
    ).count()
    
    # Get top users for the leaderboard
    users = User.query.all()
    users = sorted(users, key=lambda u: u.get_total_credits(), reverse=True)[:5]  # Top 5 users
    
    return render_template('main/index.html', 
                          title='Welcome',
                          total_users=total_users,
                          total_rides=total_rides,
                          active_rides=active_rides,
                          users=users)  # Pass users to the template

@bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html', title='Profile')

@bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    username = request.form.get('username')
    phone_number = request.form.get('phone_number')
    
    # Check if username already exists
    if username != current_user.username:
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already taken. Please choose another one.', 'danger')
            return redirect(url_for('main.profile'))
    
    current_user.username = username
    current_user.phone_number = phone_number
    
    try:
        db.session.commit()
        flash('Profile updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error updating profile. Please try again.', 'danger')
    
    return redirect(url_for('main.profile'))

@bp.route('/update_profile_picture', methods=['POST'])
@login_required
def update_profile_picture():
    if 'profile_picture' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('main.profile'))
    
    file = request.files['profile_picture']
    
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('main.profile'))
    
    if file:
        filename = secure_filename(file.filename)
        # Create a unique filename
        unique_filename = f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{filename}"
        
        # Ensure upload folder exists
        from flask import current_app
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        
        # Update user profile image
        current_user.profile_image = unique_filename
        db.session.commit()
        
        flash('Profile picture updated successfully!', 'success')
    
    return redirect(url_for('main.profile'))

@bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate current password
    if not current_user.check_password(current_password):
        flash('Current password is incorrect.', 'danger')
        return redirect(url_for('main.profile'))
    
    # Validate new password
    if new_password != confirm_password:
        flash('New passwords do not match.', 'danger')
        return redirect

@bp.route('/about')
def about():
    return render_template('main/about.html', title='About Us')

@bp.route('/contact')
def contact():
    return render_template('main/contact.html', title='Contact Us')

@bp.route('/privacy')
def privacy():
    return render_template('main/privacy.html', title='Privacy Policy')
