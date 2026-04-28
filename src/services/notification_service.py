from datetime import datetime
from src.models.models import db, Notification, User
from src.utils.logger import get_logger
from flask_socketio import emit

logger = get_logger()

def create_notification(user_id, notification_type, content):
    """
    Creates a new notification for a user.
    Optionally emits a real-time notification if the user is online.
    """
    try:
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            content=content
        )
        db.session.add(notification)
        db.session.commit()

        # Check if user is online and emit real-time notification
        user = db.session.get(User, user_id)
        if user and user.is_online:
            # Assuming a user_id specific room for notifications
            emit('new_notification', {
                'notification_id': notification.notification_id,
                'type': notification.type,
                'content': notification.content,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat()
            }, room=f'user_{user_id}', namespace='/') # Emit to the user's private room

        logger.info(f"Notification created for user {user_id}: {notification_type} - {content}")
        return notification
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating notification for user {user_id}: {e}", exc_info=True)
        return None

def get_user_notifications(user_id, limit=10, unread_only=False):
    """
    Retrieves notifications for a given user.
    """
    try:
        query = Notification.query.filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
        
        return [{
            'notification_id': n.notification_id,
            'type': n.type,
            'content': n.content,
            'is_read': n.is_read,
            'created_at': n.created_at.isoformat()
        } for n in notifications]
    except Exception as e:
        logger.error(f"Error fetching notifications for user {user_id}: {e}", exc_info=True)
        return []

def mark_notification_as_read(notification_id, user_id):
    """
    Marks a specific notification as read.
    """
    try:
        notification = Notification.query.filter_by(notification_id=notification_id, user_id=user_id).first()
        if notification:
            notification.is_read = True
            db.session.commit()
            logger.info(f"Notification {notification_id} marked as read by user {user_id}")
            return True
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking notification {notification_id} as read: {e}", exc_info=True)
        return False

def mark_all_notifications_as_read(user_id):
    """
    Marks all unread notifications for a user as read.
    """
    try:
        notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()
        for notification in notifications:
            notification.is_read = True
        db.session.commit()
        logger.info(f"All notifications marked as read for user {user_id}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking all notifications as read for user {user_id}: {e}", exc_info=True)
        return False
