from datetime import datetime, timedelta  # Add timedelta import
from flask import render_template, flash, redirect, url_for, request, jsonify, session  # Add session import
from flask_login import current_user, login_required
from sqlalchemy import text
from app import db
from app.rides import bp
from app.rides.forms import OfferRideForm, RequestRideForm, RatingForm, FindRideForm
from app.models.ride import Ride, RideRequest, Rating
from app.utils.distance import calculate_distance
import math

def cleanup_expired_rides():
    """Automatically mark expired rides as completed"""
    current_time = datetime.utcnow()
    
    # Find all expired active rides
    expired_rides = Ride.query.filter(
        Ride.departure_time <= current_time,  # Rides in the past
        Ride.status == 'active'  # Only active rides
    ).all()
    
    for ride in expired_rides:
        ride.status = 'completed'
        
        # Update all requests for this ride
        ride_requests = RideRequest.query.filter_by(ride_id=ride.id).all()
        for request in ride_requests:
            if request.status == 'pending':
                request.status = 'cancelled'
            elif request.status == 'accepted':
                request.status = 'completed'
    
    if expired_rides:
        db.session.commit()
        
    return len(expired_rides)  # Return number of rides cleaned up

def fix_ride_status():
    """Fix any rides that should be marked as completed"""
    current_time = datetime.utcnow()
    
    # Find rides that should be completed
    rides_to_fix = Ride.query.filter(
        Ride.departure_time <= current_time,  # Past rides
        Ride.status == 'active'  # Still marked as active
    ).all()
    
    fixed_count = 0
    for ride in rides_to_fix:
        ride.status = 'completed'
        ride.available_seats = 0
        
        # Update all requests for this ride
        ride_requests = RideRequest.query.filter_by(ride_id=ride.id).all()
        for request in ride_requests:
            if request.status == 'pending':
                request.status = 'cancelled'
            elif request.status == 'accepted':
                request.status = 'completed'
        fixed_count += 1
    
    if fixed_count > 0:
        try:
            db.session.commit()
            print(f"Fixed {fixed_count} rides")
        except Exception as e:
            db.session.rollback()
            print(f"Error fixing rides: {str(e)}")
    
    return fixed_count

@bp.route('/offer', methods=['GET', 'POST'])
@login_required
def offer_ride():
    if current_user.role != 'rider':
        flash('You must be registered as a rider to offer rides.', 'warning')
        return redirect(url_for('main.index'))
    
    form = OfferRideForm()
    
    # Set min datetime to current time
    current_datetime = datetime.now().strftime('%Y-%m-%dT%H:%M')
    
    if form.validate_on_submit():
        # Process form submission
        ride = Ride(
            rider_id=current_user.id,
            start_location=form.start_location.data,
            end_location=form.end_location.data,
            start_latitude=form.start_latitude.data,
            start_longitude=form.start_longitude.data,
            end_latitude=form.end_latitude.data,
            end_longitude=form.end_longitude.data,
            departure_time=form.departure_time.data,
            available_seats=form.available_seats.data,
            price=form.price.data,
            vehicle_type=form.vehicle_type.data,
            vehicle_number=form.vehicle_number.data
        )
        db.session.add(ride)
        db.session.commit()
        flash('Your ride has been posted!', 'success')
        return redirect(url_for('rides.my_rides'))
    
    return render_template('rides/offer_ride.html', 
                          title='Offer a Ride', 
                          form=form, 
                          current_datetime=current_datetime)

# Update the find_ride route to store destination and time in session
@bp.route('/find', methods=['GET', 'POST'])
@login_required
def find_ride():
    form = FindRideForm()
    
    if form.validate_on_submit():
        # Store destination and time in session for smart matching
        if form.destination_latitude.data and form.destination_longitude.data:
            session['destination_lat'] = form.destination_latitude.data
            session['destination_lon'] = form.destination_longitude.data
            session['departure_time'] = form.departure_time.data.isoformat() if form.departure_time.data else None
        
        flash('Search criteria updated!', 'success')
        return redirect(url_for('rides.find_ride'))
    
    # Get current time for min datetime
    current_datetime = datetime.now().strftime('%Y-%m-%dT%H:%M')
    
    # Get active rides for initial display
    rides = Ride.query.filter(
        Ride.status == 'active',
        Ride.departure_time > datetime.utcnow()
    ).limit(10).all()
    
    return render_template('rides/find_ride.html', 
                          title='Find a Ride', 
                          form=form,
                          current_datetime=current_datetime,
                          rides=rides)  # Pass rides to the template

@bp.route('/request/<int:ride_id>', methods=['GET', 'POST'])
@login_required
def request_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    if ride.rider_id == current_user.id:
        flash('You cannot request your own ride.', 'warning')
        return redirect(url_for('rides.find_ride'))
    
    form = RequestRideForm()
    if form.validate_on_submit():
        if ride.available_seats < form.seats_requested.data:
            flash('Not enough seats available.', 'danger')
            return redirect(url_for('rides.find_ride'))
        
        request = RideRequest(
            ride_id=ride.id,
            traveler_id=current_user.id,
            pickup_location=form.pickup_location.data,
            pickup_latitude=form.pickup_latitude.data,
            pickup_longitude=form.pickup_longitude.data,
            seats_requested=form.seats_requested.data
        )
        db.session.add(request)
        db.session.commit()
        flash('Your ride request has been sent!', 'success')
        return redirect(url_for('rides.my_rides'))
    
    return render_template('rides/request_ride.html', title='Request a Ride', 
                         form=form, ride=ride)

@bp.route('/my-rides')
@login_required
def my_rides():
    # Check and update expired rides before displaying
    fix_ride_status()
    
    # Get current time for template
    now = datetime.utcnow()
    
    if current_user.role == 'rider':
        offered_rides = Ride.query.filter_by(rider_id=current_user.id).order_by(Ride.departure_time.desc()).all()
        return render_template('rides/my_rides_rider.html', title='My Rides', rides=offered_rides, now=now)
    else:
        requested_rides = RideRequest.query.filter_by(traveler_id=current_user.id).order_by(RideRequest.created_at.desc()).all()
        return render_template('rides/my_rides_traveler.html', title='My Rides', requests=requested_rides, now=now)

@bp.route('/api/rides')
def get_rides():
    current_time = datetime.utcnow()
    rides = Ride.query.filter(
        Ride.departure_time > current_time,  # Only future rides
        Ride.status == 'active'
    ).all()
    
    return jsonify([{
        'id': ride.id,
        'start_location': ride.start_location,
        'end_location': ride.end_location,
        'start_coords': [ride.start_latitude, ride.start_longitude],
        'end_coords': [ride.end_latitude, ride.end_longitude],
        'departure_time': ride.departure_time.strftime('%Y-%m-%d %H:%M'),
        'available_seats': ride.available_seats,
        'price': ride.price
    } for ride in rides])

# Add this import at the top of the file
from app.utils.ride_matching import get_ride_matches

# Update the nearby-rides route to use the smart matching algorithm
@bp.route('/nearby-rides')
@login_required
def nearby_rides():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', type=float)
    
    if not all([lat, lon, radius]):
        return jsonify([])
    
    # Get destination coordinates from session if available
    end_lat = session.get('destination_lat')
    end_lon = session.get('destination_lon')
    
    # If no destination is set, use basic proximity search
    if not end_lat or not end_lon:
        # Get rides within radius (original code)
        rides = Ride.query.filter(
            Ride.status == 'active',
            Ride.departure_time > datetime.utcnow()
        ).all()
        
        nearby_rides = []
        for ride in rides:
            distance = calculate_distance(lat, lon, ride.start_latitude, ride.start_longitude)
            if distance <= radius:
                ride_dict = {
                    'id': ride.id,
                    'start_location': ride.start_location,
                    'end_location': ride.end_location,
                    'start_latitude': float(ride.start_latitude),
                    'start_longitude': float(ride.start_longitude),
                    'end_latitude': float(ride.end_latitude),
                    'end_longitude': float(ride.end_longitude),
                    'departure_time': ride.departure_time.strftime('%Y-%m-%d %H:%M'),
                    'available_seats': ride.available_seats,
                    'price': float(ride.price),
                    'distance': round(distance, 2),
                    'match_score': None
                }
                nearby_rides.append(ride_dict)
        
        return jsonify(sorted(nearby_rides, key=lambda x: x['distance']))
    
    # Use smart matching algorithm
    preferred_time = session.get('departure_time', datetime.utcnow() + timedelta(hours=1))
    if isinstance(preferred_time, str):
        try:
            preferred_time = datetime.strptime(preferred_time, '%Y-%m-%dT%H:%M')
        except ValueError:
            preferred_time = datetime.utcnow() + timedelta(hours=1)
    
    # Get matched rides
    matched_rides = get_ride_matches(
        current_user.id, 
        lat, lon, 
        end_lat, end_lon, 
        preferred_time
    )
    
    # Format response
    result = []
    for ride, score in matched_rides:
        # Filter by radius
        distance = calculate_distance(lat, lon, ride.start_latitude, ride.start_longitude)
        if distance <= radius:
            ride_dict = {
                'id': ride.id,
                'start_location': ride.start_location,
                'end_location': ride.end_location,
                'start_latitude': float(ride.start_latitude),
                'start_longitude': float(ride.start_longitude),
                'end_latitude': float(ride.end_latitude),
                'end_longitude': float(ride.end_longitude),
                'departure_time': ride.departure_time.strftime('%Y-%m-%d %H:%M'),
                'available_seats': ride.available_seats,
                'price': float(ride.price),
                'distance': round(distance, 2),
                'match_score': round(score, 1)
            }
            result.append(ride_dict)
    
    return jsonify(result)

@bp.route('/request/<int:request_id>/<action>')
@login_required
def handle_request(request_id, action):
    ride_request = RideRequest.query.get_or_404(request_id)
    ride = ride_request.ride

    if ride.rider_id != current_user.id:
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('rides.my_rides'))

    if action == 'accept':
        if ride.available_seats < ride_request.seats_requested:
            flash('Not enough seats available.', 'danger')
            return redirect(url_for('rides.my_rides'))
        
        ride_request.status = 'accepted'
        ride.available_seats -= ride_request.seats_requested
        flash('Ride request accepted!', 'success')
    
    elif action == 'reject':
        ride_request.status = 'rejected'
        flash('Ride request rejected.', 'info')
    
    db.session.commit()
    return redirect(url_for('rides.my_rides'))

# Import the green credits functions at the top of the file
from app.green.routes import award_ride_credits

# Update the complete_ride route
@bp.route('/complete/<int:ride_id>')
@login_required
def complete_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    
    if ride.rider_id != current_user.id:
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('rides.my_rides'))
    
    # Force update the ride status and seats
    ride.status = 'completed'
    ride.available_seats = 0
    
    # Update all associated requests
    ride_requests = RideRequest.query.filter_by(ride_id=ride.id).all()
    for request in ride_requests:
        if request.status == 'pending':
            request.status = 'cancelled'
        elif request.status == 'accepted':
            request.status = 'completed'
            # Award green credits for completed ride requests
            award_ride_credits(request)
    
    try:
        # Commit the changes
        db.session.commit()
        
        # Double-check the update
        db.session.refresh(ride)
        if ride.status != 'completed':
            ride.status = 'completed'
            ride.available_seats = 0
            db.session.commit()
        
        flash('Ride marked as completed! Green credits awarded.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error completing ride. Please try again.', 'danger')
    
    return redirect(url_for('rides.my_rides'))

@bp.route('/cancel/<int:ride_id>')
@login_required
def cancel_ride(ride_id):
    ride = Ride.query.get_or_404(ride_id)
    
    if ride.rider_id != current_user.id:
        flash('You are not authorized to perform this action.', 'danger')
        return redirect(url_for('rides.my_rides'))
    
    if ride.status != 'active':
        flash('This ride cannot be cancelled.', 'warning')
        return redirect(url_for('rides.my_rides'))
    
    # Cancel the ride
    ride.status = 'cancelled'
    ride.available_seats = 0  # Ensure no seats are available
    
    # Cancel all pending requests
    pending_requests = RideRequest.query.filter_by(ride_id=ride.id).all()
    for request in pending_requests:
        request.status = 'cancelled'
    
    try:
        # Commit the changes
        db.session.commit()
        
        # Double-check the update
        db.session.refresh(ride)
        if ride.status != 'cancelled':
            ride.status = 'cancelled'
            ride.available_seats = 0
            db.session.commit()
            
        flash('Ride cancelled successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error cancelling ride. Please try again.', 'danger')
    
    return redirect(url_for('rides.my_rides'))

@bp.route('/rate/<int:request_id>', methods=['GET', 'POST'])
@login_required
def rate_ride(request_id):
    ride_request = RideRequest.query.get_or_404(request_id)
    
    # Check if user is authorized to rate (either rider or traveler of the ride)
    if current_user.id not in [ride_request.traveler_id, ride_request.ride.rider_id]:
        flash('You are not authorized to rate this ride.', 'danger')
        return redirect(url_for('rides.my_rides'))
    
    # Check if ride is completed
    if ride_request.status != 'completed':
        flash('You can only rate completed rides.', 'warning')
        return redirect(url_for('rides.my_rides'))
    
    # Check if already rated
    existing_rating = Rating.query.filter_by(
        ride_request_id=request_id,
        from_user_id=current_user.id
    ).first()
    
    if existing_rating:
        flash('You have already rated this ride.', 'warning')
        return redirect(url_for('rides.my_rides'))
    
    form = RatingForm()
    if form.validate_on_submit():
        # Determine who is being rated
        to_user_id = ride_request.traveler_id
        if current_user.id == ride_request.traveler_id:
            to_user_id = ride_request.ride.rider_id
        
        rating = Rating(
            ride_request_id=request_id,
            from_user_id=current_user.id,
            to_user_id=to_user_id,
            rating=form.rating.data,
            comment=form.comment.data
        )
        db.session.add(rating)
        db.session.commit()
        
        flash('Thank you for your rating!', 'success')
        return redirect(url_for('rides.my_rides'))
    
    return render_template('rides/rate_ride.html', title='Rate Ride', 
                         form=form, request=ride_request)

# Adding Real-time Location Tracking for Riders and Travelers

# I'll implement a feature that allows both riders and travelers to see each other's locations on a map for accepted ride requests. This will help riders find the pickup location and travelers track their ride's arrival.

# Let's create a new page for real-time location tracking that both parties can access:

## 1. First, let's create a new route in the rides blueprint
# Add this after the other route functions

@bp.route('/track/<int:request_id>')
@login_required
def track_ride(request_id):
    ride_request = RideRequest.query.get_or_404(request_id)
    ride = ride_request.ride
    
    # Check if user is authorized (either the rider or the traveler)
    if current_user.id != ride.rider_id and current_user.id != ride_request.traveler_id:
        flash('You are not authorized to access this tracking page.', 'danger')
        return redirect(url_for('rides.my_rides'))
    
    # Check if the request is accepted
    if ride_request.status != 'accepted':
        flash('Tracking is only available for accepted ride requests.', 'warning')
        return redirect(url_for('rides.my_rides'))
    
    # Get the other user (the one who is not the current user)
    other_user = ride.rider if current_user.id == ride_request.traveler_id else ride_request.traveler
    
    # Determine if current user is rider or traveler
    is_rider = current_user.id == ride.rider_id
    
    return render_template('rides/track_ride.html', 
                          title='Track Ride',
                          ride=ride,
                          ride_request=ride_request,
                          other_user=other_user,
                          is_rider=is_rider)
