from flask import request
from flask_login import current_user
from flask_socketio import emit
from app import socketio, db
from app.models import ChatMessage, User
from datetime import datetime

# Track connected users
connected_users = {}

@socketio.on('connect')
def handle_connect():
    """Handle user connection to the chat."""
    if not current_user.is_authenticated:
        return False
    
    # Update user's online status
    current_user.update_user_online_status(True)
    
    # Add user to connected users
    connected_users[current_user.id] = current_user
    
    # Fetch recent messages (last 100)
    messages = ChatMessage.query.order_by(ChatMessage.timestamp.desc()).limit(100).all()
    messages.reverse()
    
    # Get online users
    online_users = [{'id': user.id, 'username': user.username} 
                    for user in connected_users.values()]
    
    # Send initial data to the connected user
    emit('chat_history', {
        'messages': [msg.to_dict() for msg in messages],
        'online_users': online_users
    })
    
    # Notify others that a new user connected
    emit('user_connected', {
        'user': {
            'id': current_user.id,
            'username': current_user.username
        }
    }, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle user disconnection from the chat."""
    if current_user.is_authenticated:
        # Update user's online status
        current_user.update_user_online_status(False)
        
        # Remove from connected users
        if current_user.id in connected_users:
            del connected_users[current_user.id]
        
        # Notify others that a user disconnected
        emit('user_disconnected', {
            'user': {
                'id': current_user.id,
                'username': current_user.username
            }
        }, broadcast=True, include_self=False)

@socketio.on('new_message')
def handle_new_message(data):
    """Handle new chat message."""
    if not current_user.is_authenticated:
        return False
    
    # Create and save new chat message
    new_message = ChatMessage(
        content=data['content'],
        user_id=current_user.id
    )
    
    try:
        db.session.add(new_message)
        db.session.commit()
        
        # Broadcast the new message to all connected clients
        emit('new_message', new_message.to_dict(), broadcast=True)
    except Exception as e:
        db.session.rollback()
        print(f"Error saving message: {e}")
        return False
