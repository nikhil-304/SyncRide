from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from app.chat import bp
from app.models.ride import RideRequest, Ride
from app.models.message import Message
from app import db, socketio
from datetime import datetime

# Update any references to ride_request.messages to use ride_request.chat_messages instead

@bp.route('/chat/<int:request_id>')
@login_required
def chat(request_id):
    ride_request = RideRequest.query.get_or_404(request_id)
    ride = ride_request.ride
    
    # Check if user is authorized (either the rider or the traveler)
    if current_user.id != ride.rider_id and current_user.id != ride_request.traveler_id:
        flash('You are not authorized to access this chat.', 'danger')
        return redirect(url_for('rides.my_rides'))
    
    # Check if the request is accepted
    if ride_request.status != 'accepted':
        flash('Chat is only available for accepted ride requests.', 'warning')
        return redirect(url_for('rides.my_rides'))
    
    # Get the other user (the one who is not the current user)
    other_user = ride.rider if current_user.id == ride_request.traveler_id else ride_request.traveler
    
    # Get all messages for this ride request
    messages = Message.query.filter_by(ride_request_id=request_id).order_by(Message.created_at).all()
    
    # Mark unread messages as read
    unread_messages = Message.query.filter_by(
        ride_request_id=request_id,
        is_read=False
    ).filter(Message.sender_id != current_user.id).all()
    
    for message in unread_messages:
        message.is_read = True
    
    db.session.commit()
    
    return render_template('chat/chat.html', 
                          title='Chat',
                          ride_request=ride_request,
                          ride=ride,
                          other_user=other_user,
                          messages=messages)

@bp.route('/api/messages/<int:request_id>', methods=['GET'])
@login_required
def get_messages(request_id):
    ride_request = RideRequest.query.get_or_404(request_id)
    
    # Check if user is authorized
    if current_user.id != ride_request.ride.rider_id and current_user.id != ride_request.traveler_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    messages = Message.query.filter_by(ride_request_id=request_id).order_by(Message.created_at).all()
    
    return jsonify([{
        'id': message.id,
        'sender_id': message.sender_id,
        'sender_name': message.sender.username,
        'content': message.content,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'is_read': message.is_read,
        'is_mine': message.sender_id == current_user.id
    } for message in messages])

@bp.route('/api/messages/<int:request_id>/unread', methods=['GET'])
@login_required
def get_unread_count(request_id):
    ride_request = RideRequest.query.get_or_404(request_id)
    
    # Check if user is authorized
    if current_user.id != ride_request.ride.rider_id and current_user.id != ride_request.traveler_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    unread_count = Message.query.filter_by(
        ride_request_id=request_id,
        is_read=False
    ).filter(Message.sender_id != current_user.id).count()
    
    return jsonify({'unread_count': unread_count})