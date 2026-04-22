import bcrypt
from models.models import db, User
from utils.logger import get_logger

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
    """Update user profile fields"""
    try:
        allowed_fields = ['avatar_config', 'settings_config']
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                setattr(user, key, value)
        
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile: {e}")
        return False


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
