import bcrypt
from datetime import datetime
from src.models.models import db, User
from src.utils.logger import get_logger

logger = get_logger()

def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(password_hash, password):
    """Check password against hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password check error: {e}")
        return False


def create_user(username, email, password, is_oauth=False):
    """Create a new user with validation"""
    try:
        # Validate input
        if not username or len(username) < 3:
            return None, "Username must be at least 3 characters"
        
        if not email or '@' not in email:
            return None, "Invalid email address"
        
        if not is_oauth and (not password or len(password) < 6):
            return None, "Password must be at least 6 characters"
        
        # Check if user exists
        existing_user = User.query.filter(
            (User.username == username.lower()) | (User.email == email.lower())
        ).first()
        
        if existing_user:
            return None, "Username or email already exists"
        
        # Create user
        password_hash = hash_password(password) if not is_oauth else 'google_oauth'
        
        user = User(
            username=username.lower(),
            email=email.lower(),
            password_hash=password_hash
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"User created: {username}")
        return user, None
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {e}")
        return None, "An error occurred during registration"


def authenticate_user(username, password):
    """Authenticate user with username and password"""
    try:
        user = User.query.filter_by(username=username.lower()).first()
        
        if not user:
            return None, "Invalid username or password"
        
        if user.password_hash == 'google_oauth':
            return None, "Please use Google login for this account"
        
        if not check_password(user.password_hash, password):
            return None, "Invalid username or password"
        
        return user, None
        
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None, "An error occurred during login"


def get_user_by_id(user_id):
    """Get user by ID safely"""
    try:
        return db.session.get(User, user_id)
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return None


def get_user_by_email(email):
    """Get user by email"""
    try:
        return User.query.filter_by(email=email.lower()).first()
    except Exception as e:
        logger.error(f"Error fetching user by email: {e}")
        return None


def update_user_profile(user, **kwargs):
    """
    Update user profile fields with validation
    Allowed fields: username, email, avatar_config, settings_config, bio, notification_preferences
    """
    try:
        allowed_fields = ['username', 'email', 'avatar_config', 'settings_config', 'bio', 'notification_preferences']
        updated_fields = {}
        
        for key, value in kwargs.items():
            if key not in allowed_fields:
                continue
            
            # Validate username
            if key == 'username':
                if not value or len(value) < 3:
                    return False, "Username must be at least 3 characters"
                
                value = value.lower()
                
                # Check if username already exists (and it's not the current user)
                existing = User.query.filter(
                    (User.username == value) & (User.user_id != user.user_id)
                ).first()
                
                if existing:
                    return False, "Username already taken"
            
            # Validate email
            if key == 'email':
                if not value or '@' not in value:
                    return False, "Invalid email address"
                
                value = value.lower()
                
                # Check if email already exists (and it's not the current user)
                existing = User.query.filter(
                    (User.email == value) & (User.user_id != user.user_id)
                ).first()
                
                if existing:
                    return False, "Email already in use"
            
            # Validate bio
            if key == 'bio':
                if value and len(value) > 500:
                    return False, "Bio must be 500 characters or less"
            
            updated_fields[key] = value
        
        # Update user fields
        for key, value in updated_fields.items():
            setattr(user, key, value)
        
        # Add profile_updated_at timestamp
        user.profile_updated_at = datetime.utcnow()
        
        db.session.commit()
        logger.info(f"User profile updated: {user.username} - fields: {list(updated_fields.keys())}")
        return True, "Profile updated successfully"
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile: {e}", exc_info=True)
        return False, "Error updating profile"


def delete_user(user_id):
    """Delete user and all associated data"""
    try:
        user = db.session.get(User, user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
            logger.info(f"User deleted: {user_id}")
            return True
        return False
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {e}")
        return False
