from flask_socketio import emit, join_room, leave_room
from flask import session
from src.models.models import db, Message, User
from src.utils.helpers import get_current_user
from src.utils.logger import get_logger
from datetime import datetime, timedelta
import time

logger = get_logger()

# In-memory cache for deduplication check (message_id -> timestamp)
MESSAGE_DEDUP_CACHE = {}
MAX_DEDUP_CACHE_SIZE = 10000


def register_socket_events(socketio):
    """Register all SocketIO event handlers"""
    
    # Track connected users
    connected_users = {}

    @socketio.on('connect')
    def handle_connect():
        """User connected"""
        user = get_current_user()
        if user:
            try:
                user.last_seen = datetime.utcnow()
                user.is_online = True
                db.session.commit()
                
                connected_users[user.user_id] = session.sid
                
                emit('connection_established', {
                    'user_id': user.user_id,
                    'username': user.username,
                    'message': 'Connected to Arcadia Hub'
                })
                join_room('global_chat')
                
                # Broadcast user online status
                emit('user_status', {
                    'user_id': user.user_id,
                    'username': user.username,
                    'status': 'online',
                    'timestamp': datetime.utcnow().isoformat()
                }, broadcast=True)
                
                logger.info(f"User connected: {user.username}")
            except Exception as e:
                logger.error(f"Error on connect: {e}")
                db.session.rollback()
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """User disconnected"""
        user = get_current_user()
        if user:
            try:
                user.is_online = False
                user.last_seen = datetime.utcnow()
                db.session.commit()
                
                if user.user_id in connected_users:
                    del connected_users[user.user_id]
                
                emit('user_status', {
                    'user_id': user.user_id,
                    'status': 'offline',
                    'timestamp': datetime.utcnow().isoformat()
                }, broadcast=True)
                
                logger.info(f"User disconnected: {user.username}")
            except Exception as e:
                logger.error(f"Error on disconnect: {e}")
                db.session.rollback()
    
    @socketio.on('join_global_chat')
    def handle_join_global():
        """Join global chat room"""
        join_room('global_chat')
        user = get_current_user()
        if user:
            try:
                emit('system_message', {
                    'content': f'{user.username} joined the chat',
                    'timestamp': datetime.utcnow().isoformat()
                }, room='global_chat')
                logger.info(f"User joined global chat: {user.username}")
            except Exception as e:
                logger.error(f"Error joining global chat: {e}")
    
    @socketio.on('leave_global_chat')
    def handle_leave_global():
        """Leave global chat room"""
        leave_room('global_chat')
        user = get_current_user()
        if user:
            try:
                emit('system_message', {
                    'content': f'{user.username} left the chat',
                    'timestamp': datetime.utcnow().isoformat()
                }, room='global_chat')
                logger.info(f"User left global chat: {user.username}")
            except Exception as e:
                logger.error(f"Error leaving global chat: {e}")
    
    @socketio.on('send_message')
    def handle_message(data, retry_count=0):
        """Handle chat message with deduplication and retry logic"""
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
            
            # Rate limit: max 10 messages per minute
            from datetime import datetime, timedelta
            recent_messages = Message.query.filter_by(
                sender_id=user.user_id,
                is_global=True
            ).filter(
                Message.timestamp >= datetime.utcnow() - timedelta(minutes=1)
            ).count()
            
            if recent_messages >= 10:
                emit('error', {'message': 'Rate limit: Maximum 10 messages per minute'})
                return
            
            # DEDUPLICATION: Check if this message was already created
            dedup_key = f"{user.user_id}_{content}_{int(time.time())}"
            if dedup_key in MESSAGE_DEDUP_CACHE:
                # Message already processed
                emit('error', {'message': 'Duplicate message detected'})
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
            
            # Add to dedup cache
            MESSAGE_DEDUP_CACHE[dedup_key] = time.time()
            
            # Clean old dedup cache entries
            if len(MESSAGE_DEDUP_CACHE) > MAX_DEDUP_CACHE_SIZE:
                oldest_key = min(MESSAGE_DEDUP_CACHE.keys(), key=lambda k: MESSAGE_DEDUP_CACHE[k])
                del MESSAGE_DEDUP_CACHE[oldest_key]
            
            # Broadcast to all users in global chat
            emit('new_message', {
                'message_id': message.message_id,
                'sender_id': user.user_id,
                'username': user.username,
                'content': content,
                'timestamp': message.timestamp.isoformat(),
                'is_read': False
            }, room='global_chat', include_self=True)
            
            logger.info(f"Message sent: {user.username} - {content[:50]}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sending message: {e}", exc_info=True)
            
            # RETRY LOGIC: Attempt retry with exponential backoff
            if retry_count < 3:
                wait_time = 0.1 * (2 ** retry_count)  # 100ms, 200ms, 400ms
                socketio.emit('message_retry', {
                    'retry_count': retry_count + 1,
                    'wait_time': wait_time
                })
            else:
                emit('error', {'message': 'Failed to send message. Please try again.'})
    
    @socketio.on('send_private_message')
    def handle_private_message(data):
        """Handle private message with read receipts"""
        try:
            user = get_current_user()
            if not user:
                emit('error', {'message': 'You must be logged in'})
                return
            
            recipient_id = data.get('recipient_id')
            content = data.get('content', '').strip()
            
            if not recipient_id or not content:
                return
            
            if len(content) > 1000:
                emit('error', {'message': 'Message too long (max 1000 characters)'})
                return
            
            # Validate recipient exists
            recipient = db.session.get(User, recipient_id)
            if not recipient:
                emit('error', {'message': 'Recipient not found'})
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
            
            # Send to recipient's room
            emit('private_message', {
                'message_id': message.message_id,
                'sender_id': user.user_id,
                'sender_username': user.username,
                'content': content,
                'timestamp': message.timestamp.isoformat(),
                'is_read': False
            }, room=f'user_{recipient_id}')
            
            # Confirmation to sender
            emit('message_sent', {
                'message_id': message.message_id,
                'recipient_id': recipient_id,
                'timestamp': message.timestamp.isoformat()
            })
            
            logger.info(f"Private message: {user.username} -> {recipient.username}")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sending private message: {e}", exc_info=True)
            emit('error', {'message': 'Failed to send private message'})
    
    @socketio.on('join_private_room')
    def handle_join_private(data):
        """Join private room with another user"""
        user = get_current_user()
        if user:
            try:
                other_user_id = data.get('user_id')
                other_user = db.session.get(User, other_user_id)
                
                if not other_user:
                    emit('error', {'message': 'User not found'})
                    return
                
                # Create bidirectional room name
                room_name = f'private_{min(user.user_id, other_user_id)}_{max(user.user_id, other_user_id)}'
                join_room(room_name)
                
                emit('private_room_joined', {
                    'room': room_name,
                    'other_user': {
                        'user_id': other_user.user_id,
                        'username': other_user.username,
                        'is_online': other_user.is_online
                    },
                    'timestamp': datetime.utcnow().isoformat()
                })
                
                logger.info(f"Private room joined: {user.username} <-> {other_user.username}")
            except Exception as e:
                logger.error(f"Error joining private room: {e}")
    
    @socketio.on('typing')
    def handle_typing(data):
        """User is typing indicator"""
        user = get_current_user()
        if user:
            chat_type = data.get('type', 'global')  # 'global' or 'private'
            
            if chat_type == 'global':
                emit('user_typing', {
                    'user_id': user.user_id,
                    'username': user.username
                }, room='global_chat')
            else:
                recipient_id = data.get('recipient_id')
                room_name = f'private_{min(user.user_id, recipient_id)}_{max(user.user_id, recipient_id)}'
                emit('user_typing', {
                    'user_id': user.user_id,
                    'username': user.username
                }, room=room_name)
    
    @socketio.on('stop_typing')
    def handle_stop_typing(data=None):
        """User stopped typing"""
        user = get_current_user()
        if user:
            chat_type = data.get('type', 'global') if data else 'global'
            
            if chat_type == 'global':
                emit('user_stopped_typing', {
                    'user_id': user.user_id
                }, room='global_chat')
            else:
                recipient_id = data.get('recipient_id')
                room_name = f'private_{min(user.user_id, recipient_id)}_{max(user.user_id, recipient_id)}'
                emit('user_stopped_typing', {
                    'user_id': user.user_id
                }, room=room_name)
    
    @socketio.on('mark_message_read')
    def handle_mark_read(data):
        """Mark message as read"""
        try:
            user = get_current_user()
            if not user:
                return
            
            message_id = data.get('message_id')
            message = db.session.get(Message, message_id)
            
            if message and message.recipient_id == user.user_id:
                message.is_read = True
                message.read_at = datetime.utcnow()
                db.session.commit()
                
                # Notify sender that message was read
                emit('message_read', {
                    'message_id': message_id,
                    'read_at': message.read_at.isoformat()
                }, room=f'user_{message.sender_id}')
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking message as read: {e}")
