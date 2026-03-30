from database import DatabaseManager
import hashlib
import re
import json
import secrets
from datetime import datetime, timedelta
import traceback

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    import warnings
    warnings.warn("bcrypt not found. Using SHA-256 fallback.")


class AuthSystem:
    """Authentication system for web application."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.current_user = None
        self.session_token = None
        self.daily_reward_msg = ""
        
    def validate_username(self, username: str) -> tuple:
        """Validate username format."""
        if not username:
            return False, "Username is required."
        if len(username) < 3:
            return False, "Username must be at least 3 characters."
        if len(username) > 20:
            return False, "Username must be at most 20 characters."
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores."
        return True, ""
        
    def validate_email(self, email: str) -> tuple:
        """Validate email format."""
        if not email:
            return False, "Email is required."
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format."
        return True, ""
        
    def validate_password(self, password: str) -> tuple:
        """Validate password strength."""
        if not password:
            return False, "Password is required."
        if len(password) < 8:
            return False, "Password must be at least 8 characters."
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter."
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter."
        if not re.search(r'\d', password):
            return False, "Password must contain at least one number."
        return True, ""
        
    def hash_password(self, password: str) -> bytes:
        """Hash password securely."""
        if HAS_BCRYPT:
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
        else:
            return hashlib.sha256(password.encode('utf-8')).hexdigest().encode()
            
    def verify_password(self, password: str, stored_hash: bytes) -> bool:
        """Verify password against stored hash."""
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')
            
        if HAS_BCRYPT:
            try:
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
            except ValueError:
                return hashlib.sha256(password.encode('utf-8')).hexdigest().encode() == stored_hash
        else:
            return hashlib.sha256(password.encode('utf-8')).hexdigest().encode() == stored_hash
            
    def register(self, username: str, email: str, password: str) -> tuple:
        """Register new user with validation."""
        valid, msg = self.validate_username(username)
        if not valid:
            return False, msg
            
        valid, msg = self.validate_email(email)
        if not valid:
            return False, msg
            
        valid, msg = self.validate_password(password)
        if not valid:
            return False, msg
            
        try:
            hashed = self.hash_password(password)
            default_settings = json.dumps({
                'theme': 'dark',
                'sound': True,
                'notifications': True,
                'language': 'en'
            })
            
            self.db.execute(
                """INSERT INTO users (username, email, password_hash, coins, settings_config) 
                   VALUES (?, ?, ?, ?, ?)""",
                (username.lower(), email.lower(), hashed, 100, default_settings)
            )
            return True, "Registration successful! Welcome to Arcadia Hub."
        except Exception as e:
            if "username" in str(e).lower() or "UNIQUE constraint failed" in str(e) and "username" in str(e):
                return False, "Username already exists."
            elif "email" in str(e).lower() or "UNIQUE constraint failed" in str(e) and "email" in str(e):
                return False, "Email already registered."
            traceback.print_exc()
            return False, f"Registration failed: {str(e)}"
            
    def login(self, username: str, password: str) -> tuple:
        """Authenticate user with session management."""
        if not username or not password:
            return False, "Please enter both username and password."
            
        try:
            user = self.db.fetch_one(
                "SELECT * FROM users WHERE username = ? OR email = ?",
                (username.lower(), username.lower())
            )
            
            if not user:
                return False, "Invalid credentials."
                
            stored_hash = user['password_hash']
            if not self.verify_password(password, stored_hash):
                return False, "Invalid credentials."
                
            self.current_user = dict(user)
            self._process_login_rewards()
            return True, "Login successful!"
            
        except Exception as e:
            traceback.print_exc()
            return False, f"Login error: {str(e)}"
            
    def _process_login_rewards(self):
        """Calculate and award daily login rewards."""
        user_id = self.current_user['user_id']
        today = datetime.now().date()
        last_login_str = self.current_user.get('last_login')
        
        new_streak = 1
        reward = 0
        messages = []
        
        if last_login_str:
            try:
                last_login = datetime.strptime(last_login_str, "%Y-%m-%d").date()
                diff = (today - last_login).days
                
                if diff == 0:
                    messages.append("Welcome back!")
                    self.daily_reward_msg = "\n".join(messages)
                    return
                elif diff == 1:
                    new_streak = self.current_user['streak'] + 1
                    reward = min(50 + (new_streak * 10), 200)
                    messages.append(f"Day {new_streak} streak! +{reward} coins")
                    if new_streak % 7 == 0:
                        bonus = 100
                        reward += bonus
                        messages.append(f"Weekly bonus! +{bonus} coins")
                else:
                    new_streak = 1
                    reward = 50
                    messages.append(f"Streak reset. Welcome back! +{reward} coins")
            except:
                pass
        else:
            reward = 100
            messages.append("First login bonus! +100 coins")
            
        self.db.execute(
            """UPDATE users SET last_login = ?, streak = ?, coins = coins + ? 
               WHERE user_id = ?""",
            (today.strftime("%Y-%m-%d"), new_streak, reward, user_id)
        )
        
        self.current_user['streak'] = new_streak
        self.current_user['coins'] += reward
        self.daily_reward_msg = "\n".join(messages)
        
    def logout(self):
        """Clear session and logout."""
        self.current_user = None
        self.session_token = None
        
    def update_settings(self, key: str, value):
        """Update user settings."""
        if not self.current_user:
            return
            
        settings = json.loads(self.current_user.get('settings_config') or '{}')
        settings[key] = value
        
        self.db.execute(
            "UPDATE users SET settings_config = ? WHERE user_id = ?",
            (json.dumps(settings), self.current_user['user_id'])
        )
        self.current_user['settings_config'] = json.dumps(settings)
        
    def get_settings(self) -> dict:
        """Get user settings."""
        if not self.current_user:
            return {}
        return json.loads(self.current_user.get('settings_config') or '{}')
        
    def refresh_user_data(self):
        """Refresh current user data from database."""
        if not self.current_user:
            return
        user = self.db.fetch_one(
            "SELECT * FROM users WHERE user_id = ?",
            (self.current_user['user_id'],)
        )
        if user:
            self.current_user = dict(user)
