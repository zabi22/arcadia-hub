from src.models.models import db, User, FriendRequest, Friendship
from src.utils.logger import get_logger

logger = get_logger()


def send_friend_request(sender_id, recipient_id):
    """Send a friend request"""
    try:
        if sender_id == recipient_id:
            return False, "Cannot send request to yourself"
        
        # Check if already friends
        existing_friendship = Friendship.query.filter(
            ((Friendship.user_id == sender_id) & (Friendship.friend_id == recipient_id)) |
            ((Friendship.user_id == recipient_id) & (Friendship.friend_id == sender_id))
        ).first()
        
        if existing_friendship:
            return False, "Already friends"
        
        # Check if request already exists
        existing_request = FriendRequest.query.filter(
            ((FriendRequest.sender_id == sender_id) & (FriendRequest.recipient_id == recipient_id)) |
            ((FriendRequest.sender_id == recipient_id) & (FriendRequest.recipient_id == sender_id))
        ).first()
        
        if existing_request:
            return False, "Friend request already exists"
        
        # Create friend request
        friend_request = FriendRequest(
            sender_id=sender_id,
            recipient_id=recipient_id,
            status='pending'
        )
        
        db.session.add(friend_request)
        db.session.commit()
        
        logger.info(f"Friend request sent: {sender_id} -> {recipient_id}")
        return True, None
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error sending friend request: {e}")
        return False, "Error sending friend request"


def accept_friend_request(request_id, user_id):
    """Accept a friend request"""
    try:
        friend_request = db.session.get(FriendRequest, request_id)
        
        if not friend_request:
            return False, "Friend request not found"
        
        if friend_request.recipient_id != user_id:
            return False, "Unauthorized"
        
        if friend_request.status != 'pending':
            return False, "Request already processed"
        
        # Update request status
        friend_request.status = 'accepted'
        
        # Create friendship (both directions)
        friendship1 = Friendship(
            user_id=friend_request.sender_id,
            friend_id=friend_request.recipient_id
        )
        
        friendship2 = Friendship(
            user_id=friend_request.recipient_id,
            friend_id=friend_request.sender_id
        )
        
        db.session.add(friendship1)
        db.session.add(friendship2)
        db.session.commit()
        
        logger.info(f"Friend request accepted: {friend_request.sender_id} <-> {friend_request.recipient_id}")
        return True, None
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error accepting friend request: {e}")
        return False, "Error accepting friend request"


def reject_friend_request(request_id, user_id):
    """Reject a friend request"""
    try:
        friend_request = db.session.get(FriendRequest, request_id)
        
        if not friend_request:
            return False, "Friend request not found"
        
        if friend_request.recipient_id != user_id:
            return False, "Unauthorized"
        
        if friend_request.status != 'pending':
            return False, "Request already processed"
        
        friend_request.status = 'rejected'
        db.session.commit()
        
        logger.info(f"Friend request rejected: {request_id}")
        return True, None
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error rejecting friend request: {e}")
        return False, "Error rejecting friend request"


def get_friend_requests(user_id):
    """Get pending friend requests for user"""
    try:
        requests = FriendRequest.query.filter_by(
            recipient_id=user_id,
            status='pending'
        ).all()
        
        requests_with_details = []
        for req in requests:
            sender = db.session.get(User, req.sender_id)
            requests_with_details.append({
                'request_id': req.request_id,
                'sender_id': req.sender_id,
                'sender_username': sender.username if sender else 'Unknown',
                'created_at': req.created_at
            })
        
        return requests_with_details
    except Exception as e:
        logger.error(f"Error fetching friend requests: {e}")
        return []


def get_friends(user_id):
    """Get user's friends list"""
    try:
        friendships = Friendship.query.filter_by(user_id=user_id).all()
        
        friends = []
        for friendship in friendships:
            friend = db.session.get(User, friendship.friend_id)
            if friend:
                friends.append({
                    'user_id': friend.user_id,
                    'username': friend.username,
                    'is_online': friend.is_online,
                    'last_seen': friend.last_seen
                })
        
        return friends
    except Exception as e:
        logger.error(f"Error fetching friends: {e}")
        return []


def remove_friendship(user_id, friend_id):
    """Remove a friendship"""
    try:
        # Delete both directions
        Friendship.query.filter(
            ((Friendship.user_id == user_id) & (Friendship.friend_id == friend_id)) |
            ((Friendship.user_id == friend_id) & (Friendship.friend_id == user_id))
        ).delete()
        
        db.session.commit()
        
        logger.info(f"Friendship removed: {user_id} <-> {friend_id}")
        return True, None
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing friendship: {e}")
        return False, "Error removing friendship"


def search_users(query, exclude_id=None):
    """Search users by username"""
    try:
        users = User.query.filter(
            User.username.like(f'%{query}%')
        ).limit(10).all()
        
        if exclude_id:
            users = [u for u in users if u.user_id != exclude_id]
        
        return [{'user_id': u.user_id, 'username': u.username} for u in users]
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        return []
