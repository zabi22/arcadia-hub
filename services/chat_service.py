from flask_socketio import emit, join_room, leave_room
from flask import session
from models.models import db, Message, User
from utils.helpers import get_current_user
from utils.logger import get_logger
from datetime import datetime

logger = get_logger()


def register_socket_events(socketio):
    """Register all SocketIO event handlers"""
    
    @socketio.on('connect')
    def handle_connect():
        """User connected"""
        user = get_current_user()
        if user:
            user.last_seen = datetime.utcnow()
            db.session.commit()
            emit('connection_established', {'user_id': user.user_id, 'username': user.username})
            join_room('global_chat')
            emit('user_status', {'user_id': user.user_id, 'status': 'online'}, broadcast=True)
            logger.info(f"User connected: {user.username}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """User disconnected"""
        user = get_current_user()
        if user:
            emit('user_status', {'user_id': user.user_id, 'status': 'offline'}, broadcast=True)
            logger.info(f"User disconnected: {user.username}")
    
    @socketio.on('join_global_chat')
    def handle_join_global():
        """Join global chat room"""
        join_room('global_chat')
        user = get_current_user()
        if user:
            emit('system_message', {
                'content': f'{user.username} joined the chat',
                'timestamp': datetime.utcnow().isoformat()
            }, room='global_chat')
    
    @socketio.on('leave_global_chat')
    def handle_leave_global():
        """Leave global chat room"""
        leave_room('global_chat')
        user = get_current_user()
        if user:
            emit('system_message', {
                'content': f'{user.username} left the chat',
                'timestamp': datetime.utcnow().isoformat()
            }, room='global_chat')
    
    @socketio.on('send_message')
    def handle_message(data):
        """Handle chat message"""
        try:
            user = get_current_user()
            if not user:
                emit('error', {'message': 'You must be logged in'})
                return
            
            content = data.get('content', '').strip()
            if not content:
                return
            
            # Limit message length
            if len(content) > 500:
                emit('error', {'message': 'Message too long (max 500 characters)'})
                return
            
            # Save to database
            message = Message(
                sender_id=user.user_id,
                content=content,
                is_global=True,
                timestamp=datetime.utcnow()
            )
            db.session.add(message)
            db.session.commit()
            
            # Broadcast to all users in global chat
            emit('new_message', {
                'message_id': message.message_id,
                'sender_id': user.user_id,
                'username': user.username,
                'content': content,
                'timestamp': message.timestamp.isoformat()
            }, room='global_chat')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sending message: {e}")
            emit('error', {'message': 'Failed to send message'})
    
    @socketio.on('send_private_message')
    def handle_private_message(data):
        """Handle private message"""
        try:
            user = get_current_user()
            if not user:
                emit('error', {'message': 'You must be logged in'})
                return
            
            recipient_id = data.get('recipient_id')
            content = data.get('content', '').strip()
            
            if not recipient_id or not content:
                return
            
            # Save to database
            message = Message(
                sender_id=user.user_id,
                recipient_id=recipient_id,
                content=content,
                is_global=False,
                timestamp=datetime.utcnow()
            )
            db.session.add(message)
            db.session.commit()
            
            # Send to recipient
            emit('private_message', {
                'message_id': message.message_id,
                'sender_id': user.user_id,
                'username': user.username,
                'content': content,
                'timestamp': message.timestamp.isoformat()
            }, room=f'user_{recipient_id}')
            
            # Confirmation to sender
            emit('message_sent', {
                'message_id': message.message_id,
                'recipient_id': recipient_id
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sending private message: {e}")
            emit('error', {'message': 'Failed to send private message'})
    
    @socketio.on('join_private_room')
    def handle_join_private(data):
        """Join private room with another user"""
        user = get_current_user()
        if user:
            other_user_id = data.get('user_id')
            room_name = f'private_{min(user.user_id, other_user_id)}_{max(user.user_id, other_user_id)}'
            join_room(room_name)
            emit('private_room_joined', {'room': room_name})
    
    @socketio.on('typing')
    def handle_typing(data):
        """User is typing"""
        user = get_current_user()
        if user:
            emit('user_typing', {
                'user_id': user.user_id,
                'username': user.username
            }, room='global_chat')
    
    @socketio.on('stop_typing')
    def handle_stop_typing():
        """User stopped typing"""
        user = get_current_user()
        if user:
            emit('user_stopped_typing', {
                'user_id': user.user_id
            }, room='global_chat')
