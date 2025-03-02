from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required
from app.main import bp
from app.models.ride import Ride
from app.models.user import User
from datetime import datetime

@bp.route('/')
def index():
    # Get some statistics for the landing page
    total_users = User.query.count()
    total_rides = Ride.query.count()
    active_rides = Ride.query.filter_by(status='active').count()
    
    return render_template('main/index.html',
                         total_users=total_users,
                         total_rides=total_rides,
                         active_rides=active_rides)

@bp.route('/profile')
@login_required
def profile():
    return render_template('main/profile.html', title='Profile')

@bp.route('/about')
def about():
    return render_template('main/about.html', title='About Us')

@bp.route('/contact')
def contact():
    return render_template('main/contact.html', title='Contact Us')

@bp.route('/privacy')
def privacy():
    return render_template('main/privacy.html', title='Privacy Policy')
