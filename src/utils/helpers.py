from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash
from src.models.models import db, User
from src.utils.logger import get_logger

logger = get_logger()

def calculate_level(xp):
    """Calculate user level based on XP with exponential scaling"""
    if xp is None or xp < 0:
        xp = 0
    
    level = 1
    xp_required = 100
    total_xp_for_prev_levels = 0
    
    current_req = xp_required
    while xp >= total_xp_for_prev_levels + current_req:
        total_xp_for_prev_levels += current_req
        level += 1
        current_req = int(current_req * 1.5)
    
    xp_in_level = xp - total_xp_for_prev_levels
    return level, xp_in_level, current_req


def get_current_user():
    """Safely get current user from session and database"""
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    try:
        user = db.session.get(User, user_id)
        if not user:
            session.clear()
            return None
        return user
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return None


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def update_user_activity(user):
    """Update user's last seen timestamp and online status"""
    try:
        user.last_seen = datetime.utcnow()
        user.is_online = True
        db.session.commit()
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")
        db.session.rollback()


def award_coins(user, amount, reason='game_reward'):
    """Award coins to user with validation"""
    try:
        if amount <= 0:
            return False
        
        user.coins += amount
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error awarding coins: {e}")
        db.session.rollback()
        return False


def award_xp(user, amount):
    """Award XP to user and calculate level up"""
    try:
        if amount <= 0:
            return False, None
        
        user.xp += amount
        old_level = user.player_level
        new_level, _, _ = calculate_level(user.xp)
        
        leveled_up = new_level > old_level
        if leveled_up:
            user.player_level = new_level
        
        db.session.commit()
        return True, new_level if leveled_up else None
    except Exception as e:
        logger.error(f"Error awarding XP: {e}")
        db.session.rollback()
        return False, None


def check_daily_streak(user):
    """Check and update user's daily login streak"""
    try:
        today = datetime.utcnow().date()
        last_login = user.last_login.date() if user.last_login else None
        
        if last_login is None:
            # First login
            user.streak = 1
        elif last_login == today:
            # Already logged in today
            pass
        elif last_login == today - timedelta(days=1):
            # Consecutive day
            user.streak += 1
        else:
            # Streak broken
            user.streak = 1
        
        user.last_login = datetime.utcnow()
        db.session.commit()
        return user.streak
    except Exception as e:
        logger.error(f"Error checking streak: {e}")
        db.session.rollback()
        return user.streak
