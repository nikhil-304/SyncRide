from flask import request
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
from app import socketio, db
from app.models.message import Message
from app.models.ride import RideRequest

@socketio.on('join')
def on_join(data):
    if not current_user.is_authenticated:
        return
    
    room = data['room']
    join_room(room)
    emit('status', {'msg': f'{current_user.username} has joined the chat'}, room=room)

@socketio.on('leave')
def on_leave(data):
    if not current_user.is_authenticated:
        return
    
    room = data['room']
    leave_room(room)
    emit('status', {'msg': f'{current_user.username} has left the chat'}, room=room)

@socketio.on('message')
def handle_message(data):
    if not current_user.is_authenticated:
        return
    
    request_id = data['request_id']
    content = data['message']
    
    # Validate the request
    ride_request = RideRequest.query.get(request_id)
    if not ride_request:
        return
    
    # Check if user is authorized
    if current_user.id != ride_request.ride.rider_id and current_user.id != ride_request.traveler_id:
        return
    
    # Check if the request is accepted
    if ride_request.status != 'accepted':
        return
    
    # Create and save the message
    message = Message(
        ride_request_id=request_id,
        sender_id=current_user.id,
        content=content
    )
    db.session.add(message)
    db.session.commit()
    
    # Broadcast the message to the room
    room = f'chat_{request_id}'
    emit('message', {
        'id': message.id,
        'sender_id': message.sender_id,
        'sender_name': current_user.username,
        'content': message.content,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'is_read': False,
        'is_mine': True
    }, room=room, include_self=False)
    
    # Send confirmation to sender
    emit('message_sent', {
        'id': message.id,
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
    })