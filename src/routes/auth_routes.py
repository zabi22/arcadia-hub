from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from authlib.integrations.flask_client import OAuth
from src.services.user_service import create_user, authenticate_user
from src.utils.helpers import check_daily_streak, award_coins, update_user_activity
from src.utils.logger import get_logger
from datetime import datetime

logger = get_logger()

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# OAuth setup will be initialized in app factory
oauth = None

def init_oauth(app):
    global oauth
    oauth = OAuth(app)
    if app.config.get('GOOGLE_CLIENT_ID'):
        oauth.register(
            name='google',
            client_id=app.config.get('GOOGLE_CLIENT_ID'),
            client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
            redirect_uri=app.config.get('GOOGLE_REDIRECT_URI')
        )


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter username and password', 'warning')
            return render_template('login.html')
        
        user, error = authenticate_user(username, password)
        
        if user:
            session['user_id'] = user.user_id
            session['username'] = user.username
            session.permanent = True
            
            # Update activity and check streak
            update_user_activity(user)
            streak = check_daily_streak(user)
            
            # Award streak bonus
            if streak > 1:
                bonus = min(streak * 10, 100)
                award_coins(user, bonus, 'streak_bonus')
                flash(f'Daily streak: {streak} days! Bonus: +{bonus} coins', 'success')
            else:
                flash('Welcome back!', 'success')
            
            logger.info(f"User logged in: {username}")
            return redirect(url_for('main.dashboard'))
        
        flash(error, 'danger')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        user, error = create_user(username, email, password)
        
        if user:
            flash('Registration successful! Please login.', 'success')
            logger.info(f"User registered: {username}")
            return redirect(url_for('auth.login'))
        
        flash(error, 'danger')
    
    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    """Handle user logout"""
    user_id = session.get('user_id')
    
    if user_id:
        try:
            from src.models.models import db, User
            user = db.session.get(User, user_id)
            if user:
                user.is_online = False
                user.last_seen = datetime.utcnow()
                db.session.commit()
        except Exception as e:
            logger.error(f"Error updating logout status: {e}")
    
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/google')
def google_login():
    """Initiate Google OAuth login"""
    if not oauth or not current_app.config.get('GOOGLE_CLIENT_ID'):
        flash('Google login not configured', 'warning')
        return redirect(url_for('auth.login'))
    
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        if not oauth:
            flash('Google login not configured', 'danger')
            return redirect(url_for('auth.login'))
        
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('Failed to get user info from Google', 'danger')
            return redirect(url_for('auth.login'))
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        
        from src.models.models import db, User
        
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if not user:
            # Create new user
            username = name.lower().replace(' ', '_')
            user, error = create_user(username, email, '', is_oauth=True)
            
            if not user:
                flash(error, 'danger')
                return redirect(url_for('auth.login'))
        
        # Login user
        session['user_id'] = user.user_id
        session['username'] = user.username
        session.permanent = True
        
        update_user_activity(user)
        check_daily_streak(user)
        
        flash('Welcome!', 'success')
        logger.info(f"Google login: {user.username}")
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        flash('Login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))
