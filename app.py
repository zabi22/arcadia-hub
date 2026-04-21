from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
import sqlite3
from datetime import datetime, timedelta
import json
import traceback
import hashlib
import re
import os
import logging
from authlib.integrations.flask_client import OAuth

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# Database configuration - support both SQLite and PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')
DB_TYPE = 'postgresql' if DATABASE_URL and DATABASE_URL.startswith('postgresql') else 'sqlite'
DB_NAME = 'gaming_app.db'

logger.info(f"Database type: {DB_TYPE}")
logger.info(f"DATABASE_URL set: {'Yes' if DATABASE_URL else 'No'}")

# Google OAuth configuration
oauth = OAuth(app)
if os.environ.get('GOOGLE_CLIENT_ID'):
    oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
        redirect_uri=os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    )

GAME_CONFIGS = {
    "snake": {"name": "Snake Arcade", "icon": "🐍", "color": "#00ff88", "difficulty": "Easy"},
    "tictactoe": {"name": "Tic Tac Toe", "icon": "⭕", "color": "#00d4ff", "difficulty": "Easy"},
    "memory": {"name": "Memory Match", "icon": "🧠", "color": "#ff6b6b", "difficulty": "Medium"},
    "reaction": {"name": "Reaction Time", "icon": "⚡", "color": "#ffd700", "difficulty": "Medium"},
    "wordle": {"name": "Word Guess", "icon": "🔤", "color": "#9b59b6", "difficulty": "Hard"},
    "pong": {"name": "Pong Classic", "icon": "🏓", "color": "#e74c3c", "difficulty": "Hard"},
    "game2048": {"name": "2048", "icon": "🔢", "color": "#edc22e", "difficulty": "Medium"},
    "flappy": {"name": "Flappy Bird", "icon": "🐦", "color": "#70c5ce", "difficulty": "Hard"},
    "runner": {"name": "Endless Runner", "icon": "🏃", "color": "#ff6b35", "difficulty": "Medium"},
    "breakout": {"name": "Breakout", "icon": "🧱", "color": "#e74c3c", "difficulty": "Medium"},
    "jumper": {"name": "Platform Jumper", "icon": "🦘", "color": "#2ecc71", "difficulty": "Hard"},
    "dodge": {"name": "Dodge Survival", "icon": "💥", "color": "#f39c12", "difficulty": "Hard"},
    "aimtrainer": {"name": "Aim Trainer", "icon": "🎯", "color": "#e74c3c", "difficulty": "Easy"},
    "rhythm": {"name": "Rhythm Tap", "icon": "🎵", "color": "#9b59b6", "difficulty": "Medium"},
    "maze": {"name": "Maze Escape", "icon": "🌀", "color": "#3498db", "difficulty": "Hard"},
    "shooting": {"name": "Shooting Gallery", "icon": "🔫", "color": "#c0392b", "difficulty": "Medium"},
    "towerstack": {"name": "Tower Stack", "icon": "🏗️", "color": "#f1c40f", "difficulty": "Easy"},
    "colorswitch": {"name": "Color Switch", "icon": "🎨", "color": "#e91e63", "difficulty": "Hard"}
}

SHOP_ITEMS = {
    'item_shield': {'name': 'Shield Power-up', 'description': 'Survive one collision per run', 'price': 100, 'icon': '🛡️', 'type': 'powerup', 'category': 'power', 'game_effect': 'shield'},
    'item_speed': {'name': 'Speed Boost', 'description': 'Start with 20% faster speed for bonus points', 'price': 150, 'icon': '⚡', 'type': 'powerup', 'category': 'power', 'game_effect': 'speed_boost'},
    'item_multiplier': {'name': 'Score Multiplier', 'description': '1.5x coin earnings for one run', 'price': 200, 'icon': '📈', 'type': 'powerup', 'category': 'power', 'game_effect': 'score_multiplier'},
    'item_magnet': {'name': 'Food Magnet', 'description': 'Attract food within 5 cells', 'price': 175, 'icon': '🧲', 'type': 'powerup', 'category': 'power', 'game_effect': 'magnet'},
    'avatar_dark': {'name': 'Dark Knight Avatar', 'description': 'Cool dark avatar', 'price': 50, 'icon': '🦇', 'type': 'avatar_skin', 'category': 'avatar'},
    'avatar_fire': {'name': 'Fire Phoenix Avatar', 'description': 'Fiery avatar', 'price': 75, 'icon': '🔥', 'type': 'avatar_skin', 'category': 'avatar'},
    'avatar_space': {'name': 'Space Astronaut Avatar', 'description': 'Galactic avatar', 'price': 75, 'icon': '👨‍🚀', 'type': 'avatar_skin', 'category': 'avatar'},
    'avatar_legend': {'name': 'Legendary Avatar', 'description': 'Ultra rare avatar', 'price': 300, 'icon': '👑', 'type': 'avatar_skin', 'category': 'avatar'},
    'badge_elite': {'name': 'Elite Player Badge', 'description': 'Elite badge', 'price': 100, 'icon': '⭐', 'type': 'badge', 'category': 'badge'},
    'badge_pro': {'name': 'Pro Gamer Badge', 'description': 'Pro badge', 'price': 150, 'icon': '🏆', 'type': 'badge', 'category': 'badge'}
}

GAME_RECORDS = {}

class DatabaseManager:
    CURRENT_SCHEMA_VERSION = 8
    
    def __init__(self):
        self.conn = None
        self._connect()
        self._init_version_table()
        self._run_migrations()
        self._init_tables()
        self._seed_games()
    
    def _connect(self):
        """Connect to database with proper settings for reliability"""
        try:
            if DB_TYPE == 'postgresql':
                try:
                    import psycopg2
                    from psycopg2.extras import RealDictCursor
                    
                    logger.info(f"Connecting to PostgreSQL...")
                    self.conn = psycopg2.connect(
                        DATABASE_URL,
                        sslmode='require'
                    )
                    self.conn.autocommit = False
                    self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
                    logger.info("Successfully connected to PostgreSQL database")
                except ImportError as e:
                    logger.error(f"psycopg2 not installed: {e}")
                    logger.error("Falling back to SQLite. For production, install psycopg2-binary")
                    raise
            else:
                # SQLite with WAL mode for better reliability
                logger.info(f"Connecting to SQLite database: {DB_NAME}")
                self.conn = sqlite3.connect(DB_NAME, check_same_thread=False, timeout=30)
                self.conn.row_factory = sqlite3.Row
                self.cursor = self.conn.cursor()
                
                # Enable WAL mode for better concurrent access and reliability
                self.cursor.execute('PRAGMA journal_mode=WAL')
                self.cursor.execute('PRAGMA synchronous=NORMAL')
                self.cursor.execute('PRAGMA cache_size=-2000')  # 2MB cache
                self.cursor.execute('PRAGMA foreign_keys=ON')
                logger.info(f"Successfully connected to SQLite database with WAL mode")
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            logger.error(f"DB_TYPE: {DB_TYPE}, DATABASE_URL set: {'Yes' if DATABASE_URL else 'No'}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _init_version_table(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        self.conn.commit()
    
    def _get_schema_version(self):
        try:
            self.cursor.execute("SELECT MAX(version) as v FROM schema_version")
            result = self.cursor.fetchone()
            return result['v'] or 0
        except:
            return 0
    
    def _set_schema_version(self, version):
        self.cursor.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (?)", (version,))
        self.conn.commit()
    
    def _run_migrations(self):
        current_version = self._get_schema_version()
        migrations = [(1, self._migration_v1), (2, self._migration_v2), (3, self._migration_v3), (4, self._migration_v4), (5, self._migration_v5), (6, self._migration_v6), (7, self._migration_v7)]
        for version, migration_func in migrations:
            if current_version < version:
                try:
                    migration_func()
                    self._set_schema_version(version)
                except Exception as e:
                    print(f"Migration v{version} failed: {e}")
    
    def _migration_v1(self):
        pass
    
    def _migration_v2(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS user_sessions (session_id TEXT PRIMARY KEY, user_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP, ip_address TEXT, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
    
    def _migration_v3(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS achievements (achievement_id INTEGER PRIMARY KEY, user_id INTEGER, achievement_type TEXT, unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS notifications (notification_id INTEGER PRIMARY KEY, user_id INTEGER, message TEXT, is_read INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS user_inventory (inventory_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, item_id TEXT NOT NULL, acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        self.conn.commit()
    
    def _migration_v4(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS game_records (record_id INTEGER PRIMARY KEY AUTOINCREMENT, game_key TEXT NOT NULL, user_id INTEGER NOT NULL, record_score INTEGER NOT NULL, badge_name TEXT, badge_icon TEXT, set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(game_key), FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY(game_key) REFERENCES games(game_key) ON DELETE CASCADE)')
        self.conn.commit()
    
    def _migration_v5(self):
        self.cursor.execute('CREATE TABLE IF NOT EXISTS snake_stats (stat_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, games_played INTEGER DEFAULT 0, total_food_eaten INTEGER DEFAULT 0, longest_run INTEGER DEFAULT 0, best_streak INTEGER DEFAULT 0, total_playtime INTEGER DEFAULT 0, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS powerup_usage (usage_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, item_id TEXT NOT NULL, game_key TEXT NOT NULL, score_achieved INTEGER DEFAULT 0, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        self.conn.commit()
    
    def _migration_v6(self):
        self.cursor.execute('ALTER TABLE users ADD COLUMN xp INTEGER DEFAULT 0')
        self.cursor.execute('ALTER TABLE users ADD COLUMN player_level INTEGER DEFAULT 1')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS daily_challenges (challenge_id INTEGER PRIMARY KEY AUTOINCREMENT, challenge_type TEXT NOT NULL, description TEXT NOT NULL, target_value INTEGER NOT NULL, reward_coins INTEGER NOT NULL, reward_xp INTEGER NOT NULL, date DATE NOT NULL, UNIQUE(date, challenge_type))')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS challenge_progress (progress_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, challenge_id INTEGER NOT NULL, current_value INTEGER DEFAULT 0, completed INTEGER DEFAULT 0, completed_at TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY(challenge_id) REFERENCES daily_challenges(challenge_id) ON DELETE CASCADE)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS achievements_new (achievement_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, achievement_key TEXT NOT NULL, achievement_name TEXT NOT NULL, achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE)')
        self.cursor.execute('INSERT OR IGNORE INTO achievements_new (achievement_id, user_id, achievement_key, achievement_name, achieved_at) SELECT achievement_id, user_id, achievement_type, achievement_type, CURRENT_TIMESTAMP FROM achievements')
        self.cursor.execute('DROP TABLE IF EXISTS achievements')
        self.cursor.execute('ALTER TABLE achievements_new RENAME TO achievements')
        self.conn.commit()
    
    def _migration_v7(self):
        try:
            self.cursor.execute('ALTER TABLE achievements ADD COLUMN achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except:
            pass
        self.conn.commit()
    
    def _init_tables(self):
        tables = [
            ('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, email TEXT UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login DATE, streak INTEGER DEFAULT 0, coins INTEGER DEFAULT 100, total_games_played INTEGER DEFAULT 0, total_score INTEGER DEFAULT 0, avatar_config TEXT, settings_config TEXT DEFAULT \'{"theme": "dark", "sound": true, "notifications": true}\')', "users"),
            ('CREATE TABLE IF NOT EXISTS games (game_id INTEGER PRIMARY KEY AUTOINCREMENT, game_key TEXT UNIQUE NOT NULL, name TEXT NOT NULL, category TEXT, difficulty TEXT, play_count INTEGER DEFAULT 0, icon TEXT, color TEXT)', "games"),
            ('CREATE TABLE IF NOT EXISTS scores (score_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, game_key TEXT NOT NULL, score INTEGER NOT NULL, play_time INTEGER DEFAULT 0, achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY(game_key) REFERENCES games(game_key) ON DELETE CASCADE)', "scores"),
            ('CREATE TABLE IF NOT EXISTS friends (friendship_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id_1 INTEGER NOT NULL, user_id_2 INTEGER NOT NULL, status TEXT DEFAULT \'pending\', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id_1, user_id_2), FOREIGN KEY(user_id_1) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY(user_id_2) REFERENCES users(user_id) ON DELETE CASCADE)', "friends"),
            ('CREATE TABLE IF NOT EXISTS messages (msg_id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id INTEGER NOT NULL, receiver_id INTEGER NOT NULL, content TEXT NOT NULL, is_read INTEGER DEFAULT 0, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(sender_id) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY(receiver_id) REFERENCES users(user_id) ON DELETE CASCADE)', "messages"),
        ]
        for sql, name in tables:
            try:
                self.cursor.execute(sql)
            except sqlite3.OperationalError:
                pass
        self.conn.commit()
    
    def _seed_games(self):
        for key, config in GAME_CONFIGS.items():
            self.cursor.execute('INSERT OR IGNORE INTO games (game_key, name, category, difficulty, icon, color) VALUES (?, ?, ?, ?, ?, ?)', (key, config['name'], 'Arcade', config['difficulty'], config['icon'], config['color']))
        self.conn.commit()
    
    def execute(self, query, params=()):
        """Execute a query with proper error handling and commit"""
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Database execute error: {e}\nQuery: {query}\nParams: {params}")
            raise
    
    def fetch_one(self, query, params=()):
        """Fetch a single row with error handling"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Database fetch_one error: {e}\nQuery: {query}")
            raise
    
    def fetch_all(self, query, params=()):
        """Fetch all rows with error handling"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Database fetch_all error: {e}\nQuery: {query}")
            raise
    
    def health_check(self):
        """Check if database connection is alive"""
        try:
            self.cursor.execute('SELECT 1')
            return True
        except:
            return False

class AuthSystem:
    def __init__(self, db):
        self.db = db
        self.current_user = None
        self.daily_reward_msg = ""
    
    def validate_username(self, username):
        if not username or len(username) < 3 or len(username) > 20:
            return False, "Username must be 3-20 characters"
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return False, "Username can only contain letters, numbers, and underscores"
        return True, ""
    
    def validate_email(self, email):
        if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False, "Invalid email format"
        return True, ""
    
    def validate_password(self, password):
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters"
        if not re.search(r'[A-Z]', password) or not re.search(r'[a-z]', password) or not re.search(r'\d', password):
            return False, "Password must contain uppercase, lowercase, and numbers"
        return True, ""
    
    def hash_password(self, password):
        if HAS_BCRYPT:
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
        return hashlib.sha256(password.encode('utf-8')).hexdigest().encode()
    
    def verify_password(self, password, stored_hash):
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')
        if HAS_BCRYPT:
            try:
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
            except:
                return hashlib.sha256(password.encode('utf-8')).hexdigest().encode() == stored_hash
        return hashlib.sha256(password.encode('utf-8')).hexdigest().encode() == stored_hash
    
    def register(self, username, email, password):
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
            default_settings = json.dumps({'theme': 'dark', 'sound': True, 'notifications': True, 'language': 'en'})
            self.db.execute("INSERT INTO users (username, email, password_hash, coins, settings_config) VALUES (?, ?, ?, ?, ?)", (username.lower(), email.lower(), hashed, 100, default_settings))
            return True, "Registration successful!"
        except:
            return False, "Username or email already exists"
    
    def login(self, username, password):
        if not username or not password:
            return False, "Enter username and password"
        try:
            user = self.db.fetch_one("SELECT * FROM users WHERE username = ? OR email = ?", (username.lower(), username.lower()))
            if not user or not self.verify_password(password, user['password_hash']):
                return False, "Invalid credentials"
            self.current_user = dict(user)
            self._process_login_rewards()
            return True, "Login successful!"
        except Exception as e:
            return False, f"Login error: {str(e)}"
    
    def _process_login_rewards(self):
        user_id = self.current_user['user_id']
        today = datetime.now().date()
        last_login_str = self.current_user.get('last_login')
        new_streak, reward, messages = 1, 0, []
        
        if last_login_str:
            try:
                last_login = datetime.strptime(last_login_str, "%Y-%m-%d").date()
                diff = (today - last_login).days
                if diff == 1:
                    new_streak = self.current_user['streak'] + 1
                    reward = min(50 + (new_streak * 10), 200)
                    messages.append(f"Day {new_streak} streak! +{reward} coins")
                    if new_streak % 7 == 0:
                        reward += 100
                        messages.append(f"Weekly bonus! +100 coins")
                elif diff > 1:
                    reward = 50
                    messages.append("Streak reset. Welcome back! +50 coins")
            except:
                reward = 100
                messages.append("First login bonus! +100 coins")
        else:
            reward = 100
            messages.append("First login bonus! +100 coins")
        
        self.db.execute("UPDATE users SET last_login = ?, streak = ?, coins = coins + ? WHERE user_id = ?", (today.strftime("%Y-%m-%d"), new_streak, reward, user_id))
        self.current_user['coins'] += reward
        self.daily_reward_msg = " ".join(messages)
    
    def update_settings(self, key, value):
        if not self.current_user:
            return
        settings = json.loads(self.current_user.get('settings_config') or '{}')
        settings[key] = value
        self.db.execute("UPDATE users SET settings_config = ? WHERE user_id = ?", (json.dumps(settings), self.current_user['user_id']))
        self.current_user['settings_config'] = json.dumps(settings)
    
    def get_settings(self):
        if not self.current_user:
            return {}
        return json.loads(self.current_user.get('settings_config') or '{}')

db = DatabaseManager()
auth = AuthSystem(db)

def calculate_level(xp):
    level = 1
    xp_required = 100
    total_xp = 0
    
    while total_xp + xp_required <= xp:
        total_xp += xp_required
        level += 1
        xp_required = int(xp_required * 1.5)
    
    return level, total_xp, xp_required

def award_xp(user_id, xp_amount):
    user = db.fetch_one("SELECT xp, player_level FROM users WHERE user_id = ?", (user_id,))
    if not user:
        return
    
    new_xp = user['xp'] + xp_amount
    new_level, _, _ = calculate_level(new_xp)
    
    level_up = new_level > user['player_level']
    
    db.execute("UPDATE users SET xp = ?, player_level = ? WHERE user_id = ?", (new_xp, new_level, user_id))
    
    return {'new_xp': new_xp, 'new_level': new_level, 'level_up': level_up}

def generate_daily_challenges():
    today = datetime.now().date()
    existing = db.fetch_one("SELECT COUNT(*) as count FROM daily_challenges WHERE date = ?", (today.strftime('%Y-%m-%d'),))
    
    if existing and existing['count'] > 0:
        return
    
    challenges = [
        ('play_games', 'Play 5 games today', 5, 50, 100),
        ('score_500', 'Score 500+ points in any game', 500, 75, 150),
        ('win_streak', 'Win 3 games in a row', 3, 100, 200),
        ('try_new_game', 'Play 3 different games', 3, 60, 120),
        ('reach_1000', 'Reach 1000 total score', 1000, 150, 300)
    ]
    
    for challenge in challenges:
        db.execute("INSERT OR IGNORE INTO daily_challenges (challenge_type, description, target_value, reward_coins, reward_xp, date) VALUES (?, ?, ?, ?, ?, ?)",
                  (*challenge, today.strftime('%Y-%m-%d')))

def check_achievements(user_id, game_key, score, stats=None):
    achievements_unlocked = []
    
    achievement_checks = [
        ('first_game', 'First Steps', lambda: db.fetch_one("SELECT COUNT(*) as count FROM scores WHERE user_id = ?", (user_id,))['count'] == 1),
        ('snake_500', 'Snake Master', lambda: game_key == 'snake' and score >= 500),
        ('snake_1000', 'Snake Legend', lambda: game_key == 'snake' and score >= 1000),
        ('score_1000', 'Millennial', lambda: db.fetch_one("SELECT SUM(score) as total FROM scores WHERE user_id = ?", (user_id,))['total'] >= 1000),
        ('score_5000', 'Half Way Hero', lambda: db.fetch_one("SELECT SUM(score) as total FROM scores WHERE user_id = ?", (user_id,))['total'] >= 5000),
        ('play_10', 'Dedicated Player', lambda: db.fetch_one("SELECT COUNT(*) as count FROM scores WHERE user_id = ?", (user_id,))['count'] >= 10),
        ('play_50', 'Gaming Enthusiast', lambda: db.fetch_one("SELECT COUNT(*) as count FROM scores WHERE user_id = ?", (user_id,))['count'] >= 50),
    ]
    
    for key, name, check_fn in achievement_checks:
        existing = db.fetch_one("SELECT * FROM achievements WHERE user_id = ? AND achievement_key = ?", (user_id, key))
        if not existing and check_fn():
            db.execute("INSERT INTO achievements (user_id, achievement_key, achievement_name) VALUES (?, ?, ?)", (user_id, key, name))
            achievements_unlocked.append(name)
    
    return achievements_unlocked

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        session.permanent = True
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def load_user():
    if 'user_id' in session:
        user = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (session['user_id'],))
        if user:
            session.permanent = True

@app.route('/')
def index():
    return redirect(url_for('dashboard')) if 'user_id' in session else redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        success, message = auth.register(request.form.get('username', ''), request.form.get('email', ''), request.form.get('password', ''))
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        flash(message, 'danger')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        success, message = auth.login(request.form.get('username', ''), request.form.get('password', ''))
        if success:
            session['user_id'] = auth.current_user['user_id']
            session['username'] = auth.current_user['username']
            session.permanent = True
            flash(message, 'success')
            if auth.daily_reward_msg:
                flash(auth.daily_reward_msg, 'info')
            return redirect(url_for('dashboard'))
        flash(message, 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (session['user_id'],))
    recent_scores = db.fetch_all("SELECT s.*, g.name as game_name FROM scores s JOIN games g ON s.game_key = g.game_key WHERE s.user_id = ? ORDER BY s.achieved_at DESC LIMIT 10", (session['user_id'],))
    leaderboard = db.fetch_all("SELECT u.username, SUM(s.score) as total_score, COUNT(s.score_id) as games_played FROM scores s JOIN users u ON s.user_id = u.user_id GROUP BY s.user_id ORDER BY total_score DESC LIMIT 10")
    games = db.fetch_all("SELECT * FROM games ORDER BY name")
    
    generate_daily_challenges()
    today = datetime.now().date()
    challenges = db.fetch_all("SELECT dc.*, COALESCE(cp.current_value, 0) as current_value, cp.completed FROM daily_challenges dc LEFT JOIN challenge_progress cp ON dc.challenge_id = cp.challenge_id AND cp.user_id = ? WHERE dc.date = ?", (session['user_id'], today.strftime('%Y-%m-%d')))
    
    current_level, xp_current, xp_needed = calculate_level(user['xp'])
    xp_progress = ((user['xp'] - xp_current) / xp_needed * 100) if xp_needed > 0 else 0
    
    achievements = db.fetch_all("SELECT * FROM achievements WHERE user_id = ? ORDER BY achieved_at DESC LIMIT 5", (session['user_id'],))
    
    return render_template('dashboard.html', 
                          user=user, 
                          recent_scores=recent_scores, 
                          leaderboard=leaderboard, 
                          games=games,
                          challenges=challenges,
                          current_level=current_level,
                          xp_progress=xp_progress,
                          xp_current=user['xp'] - xp_current,
                          xp_needed=xp_needed,
                          achievements=achievements)

@app.route('/profile')
@login_required
def profile():
    user = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (session['user_id'],))
    high_scores = db.fetch_all("SELECT s.*, g.name as game_name FROM scores s JOIN games g ON s.game_key = g.game_key WHERE s.user_id = ? AND s.score = (SELECT MAX(score) FROM scores WHERE user_id = ? AND game_key = s.game_key) ORDER BY s.score DESC", (session['user_id'], session['user_id']))
    return render_template('profile.html', user=user, high_scores=high_scores)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        auth.update_settings('theme', request.form.get('theme', 'dark'))
        auth.update_settings('sound', 'sound' in request.form)
        auth.update_settings('notifications', 'notifications' in request.form)
        flash('Settings updated', 'success')
        return redirect(url_for('settings'))
    user = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (session['user_id'],))
    return render_template('settings.html', user=user, settings=auth.get_settings())

@app.route('/games')
@login_required
def games():
    games_list = db.fetch_all("SELECT * FROM games ORDER BY play_count DESC")
    return render_template('games.html', games=games_list)

@app.route('/game/<game_key>')
@login_required
def play_game(game_key):
    game = db.fetch_one("SELECT * FROM games WHERE game_key = ?", (game_key,))
    if not game:
        flash('Game not found', 'danger')
        return redirect(url_for('games'))
    return render_template(f'games/{game_key}.html', game=game)

@app.route('/api/score', methods=['POST'])
@login_required
def submit_score():
    data = request.get_json()
    game_key, score = data.get('game_key'), data.get('score')
    if not game_key or score is None:
        return jsonify({'error': 'Invalid data'}), 400
    
    user_id = session['user_id']
    
    score = int(score)
    play_time = data.get('play_time', 0)
    food_eaten = data.get('food_eaten', 0)
    game_mode = data.get('game_mode', 'classic')
    active_powerups = data.get('active_powerups', [])
    
    if score < 0 or play_time < 0 or food_eaten < 0:
        return jsonify({'error': 'Invalid score data'}), 400
    
    if score > 0 and play_time > 0:
        max_reasonable_score = play_time * 50
        if score > max_reasonable_score:
            return jsonify({'error': 'Score validation failed'}), 400
    
    base_coins = max(1, int(score / 10))
    
    multiplier = 1.0
    if 'item_multiplier' in active_powerups:
        multiplier *= 1.5
    if 'item_speed' in active_powerups:
        multiplier *= 1.3
    
    streak_bonus = 0
    user = db.fetch_one("SELECT streak FROM users WHERE user_id = ?", (user_id,))
    if user and user['streak'] > 0:
        streak_bonus = int(base_coins * (user['streak'] * 0.05))
    
    mode_bonus = 1.0
    if game_mode == 'speed':
        mode_bonus = 1.5
    elif game_mode == 'survival':
        mode_bonus = 2.0
    
    coins_earned = max(1, int((base_coins + streak_bonus) * multiplier * mode_bonus))
    
    db.execute("INSERT INTO scores (user_id, game_key, score, play_time) VALUES (?, ?, ?, ?)", 
               (user_id, game_key, score, play_time))
    db.execute("UPDATE users SET coins = coins + ?, total_games_played = total_games_played + 1, total_score = total_score + ? WHERE user_id = ?", 
               (coins_earned, score, user_id))
    db.execute("UPDATE games SET play_count = play_count + 1 WHERE game_key = ?", (game_key,))
    
    if game_key == 'snake' and food_eaten > 0:
        stats = db.fetch_one("SELECT * FROM snake_stats WHERE user_id = ?", (user_id,))
        if stats:
            db.execute("UPDATE snake_stats SET games_played = games_played + 1, total_food_eaten = total_food_eaten + ?, longest_run = MAX(longest_run, ?), total_playtime = total_playtime + ? WHERE user_id = ?",
                      (food_eaten, score, play_time, user_id))
        else:
            db.execute("INSERT INTO snake_stats (user_id, games_played, total_food_eaten, longest_run, total_playtime) VALUES (?, 1, ?, ?, ?)",
                      (user_id, food_eaten, score, play_time))
    
    for powerup in active_powerups:
        db.execute("INSERT INTO powerup_usage (user_id, item_id, game_key, score_achieved) VALUES (?, ?, ?, ?)",
                  (user_id, powerup, game_key, score))
        db.execute("DELETE FROM user_inventory WHERE user_id = ? AND item_id = ? LIMIT 1",
                  (user_id, powerup))
    
    xp_earned = max(10, int(score / 5))
    xp_result = award_xp(user_id, xp_earned)
    
    today = datetime.now().date()
    challenges = db.fetch_all("SELECT dc.*, COALESCE(cp.current_value, 0) as current_value, cp.completed, cp.progress_id FROM daily_challenges dc LEFT JOIN challenge_progress cp ON dc.challenge_id = cp.challenge_id AND cp.user_id = ? WHERE dc.date = ?", (user_id, today.strftime('%Y-%m-%d')))
    
    challenges_completed = []
    for challenge in challenges:
        if challenge['completed']:
            continue
        
        new_value = challenge['current_value']
        if challenge['challenge_type'] == 'play_games':
            new_value += 1
        elif challenge['challenge_type'] == 'score_500' and score >= 500:
            new_value = max(new_value, 1)
        elif challenge['challenge_type'] == 'reach_1000':
            user_total = db.fetch_one("SELECT SUM(score) as total FROM scores WHERE user_id = ?", (user_id,))
            new_value = user_total['total'] or 0
        
        if not challenge['progress_id']:
            db.execute("INSERT INTO challenge_progress (user_id, challenge_id, current_value) VALUES (?, ?, ?)", (user_id, challenge['challenge_id'], new_value))
        else:
            db.execute("UPDATE challenge_progress SET current_value = ? WHERE progress_id = ?", (new_value, challenge['progress_id']))
        
        if new_value >= challenge['target_value'] and not challenge['completed']:
            db.execute("UPDATE challenge_progress SET completed = 1, completed_at = datetime('now') WHERE progress_id = ?", (challenge['progress_id'],))
            db.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", (challenge['reward_coins'], user_id))
            coins_earned += challenge['reward_coins']
            challenges_completed.append(challenge['description'])
    
    achievements_unlocked = check_achievements(user_id, game_key, score)
    
    record = db.fetch_one("SELECT * FROM game_records WHERE game_key = ?", (game_key,))
    is_record = False
    if record and score > record['record_score']:
        db.execute("UPDATE game_records SET user_id = ?, record_score = ?, set_at = datetime('now') WHERE game_key = ?", (user_id, score, game_key))
        is_record = True
    elif not record:
        db.execute("INSERT INTO game_records (game_key, user_id, record_score, badge_name, badge_icon) VALUES (?, ?, ?, ?, ?)", (game_key, user_id, score, f"Record Holder", "🏅"))
        is_record = True
    
    milestone = ''
    if score >= 1000 and not is_record:
        milestone = ' - Score Master! 🌟'
    elif score >= 500:
        milestone = ' - Great Run! 🔥'
    elif score >= 200:
        milestone = ' - Nice Work! ✨'
    
    return jsonify({
        'success': True, 
        'coins_earned': coins_earned, 
        'is_record': is_record, 
        'message': f'Score saved! +{coins_earned} coins' + (" - NEW RECORD! 🏅" if is_record else milestone),
        'base_coins': base_coins,
        'streak_bonus': streak_bonus,
        'multiplier': multiplier,
        'mode_bonus': mode_bonus,
        'xp_earned': xp_earned,
        'new_level': xp_result['new_level'] if xp_result else None,
        'level_up': xp_result['level_up'] if xp_result else False,
        'challenges_completed': challenges_completed,
        'achievements_unlocked': achievements_unlocked
    })

@app.route('/leaderboard')
@login_required
def leaderboard():
    overall = db.fetch_all("SELECT u.username, SUM(s.score) as total_score, COUNT(s.score_id) as games_played, u.coins FROM scores s JOIN users u ON s.user_id = u.user_id GROUP BY s.user_id ORDER BY total_score DESC LIMIT 50")
    games_list = db.fetch_all("SELECT game_key, name FROM games")
    game_leaderboards = {}
    for game in games_list:
        game_leaderboards[game['game_key']] = db.fetch_all("SELECT u.username, MAX(s.score) as high_score, COUNT(s.score_id) as times_played FROM scores s JOIN users u ON s.user_id = u.user_id WHERE s.game_key = ? GROUP BY s.user_id ORDER BY high_score DESC LIMIT 20", (game['game_key'],))
    
    records = db.fetch_all("SELECT gr.*, g.name as game_name, u.username FROM game_records gr JOIN games g ON gr.game_key = g.game_key JOIN users u ON gr.user_id = u.user_id ORDER BY gr.set_at DESC")
    
    recent_best = db.fetch_all("""
        SELECT s.*, u.username, g.name as game_name
        FROM scores s
        JOIN users u ON s.user_id = u.user_id
        JOIN games g ON s.game_key = g.game_key
        WHERE s.achieved_at >= datetime('now', '-7 days')
        ORDER BY s.score DESC
        LIMIT 20
    """)
    
    def get_rank_tier(score):
        if score >= 5000:
            return {'name': 'Legend', 'icon': '👑', 'color': '#ffd700'}
        elif score >= 2000:
            return {'name': 'Master', 'icon': '💎', 'color': '#9b59b6'}
        elif score >= 1000:
            return {'name': 'Diamond', 'icon': '🔷', 'color': '#3498db'}
        elif score >= 500:
            return {'name': 'Platinum', 'icon': '🥈', 'color': '#95a5a6'}
        elif score >= 200:
            return {'name': 'Gold', 'icon': '🥇', 'color': '#f39c12'}
        elif score >= 100:
            return {'name': 'Silver', 'icon': '🥈', 'color': '#bdc3c7'}
        else:
            return {'name': 'Bronze', 'icon': '🥉', 'color': '#cd7f32'}
    
    return render_template('leaderboard.html', 
                          overall=overall, 
                          game_leaderboards=game_leaderboards, 
                          games=games_list, 
                          records=records,
                          recent_best=recent_best,
                          get_rank_tier=get_rank_tier)

@app.route('/friends')
@login_required
def friends():
    user_id = session['user_id']
    friends_list = db.fetch_all("SELECT u.*, f.status FROM users u JOIN friends f ON ((f.user_id_1 = ? AND f.user_id_2 = u.user_id) OR (f.user_id_2 = ? AND f.user_id_1 = u.user_id)) WHERE f.status = 'accepted'", (user_id, user_id))
    pending = db.fetch_all("SELECT u.* FROM users u JOIN friends f ON f.user_id_1 = u.user_id WHERE f.user_id_2 = ? AND f.status = 'pending'", (user_id,))
    return render_template('friends.html', friends=friends_list, pending=pending)

@app.route('/api/friend/request', methods=['POST'])
@login_required
def send_friend_request():
    data = request.get_json()
    friend_username = data.get('username')
    if not friend_username:
        return jsonify({'error': 'Username required'}), 400
    
    user_id = session['user_id']
    friend = db.fetch_one("SELECT user_id FROM users WHERE username = ?", (friend_username,))
    if not friend:
        return jsonify({'error': 'User not found'}), 404
    if friend['user_id'] == user_id:
        return jsonify({'error': 'Cannot add yourself'}), 400
    
    try:
        db.execute("INSERT INTO friends (user_id_1, user_id_2, status) VALUES (?, ?, 'pending')", (user_id, friend['user_id']))
        return jsonify({'success': True, 'message': 'Friend request sent!'})
    except:
        return jsonify({'error': 'Request already sent'}), 400

@app.route('/shop')
@login_required
def shop():
    user = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (session['user_id'],))
    items_by_category = {}
    for item_id, item in SHOP_ITEMS.items():
        category = item['category']
        if category not in items_by_category:
            items_by_category[category] = []
        item['id'] = item_id
        items_by_category[category].append(item)
    return render_template('shop.html', user=user, items_by_category=items_by_category)

@app.route('/api/shop/purchase', methods=['POST'])
@login_required
def purchase_item():
    user_id = session['user_id']
    data = request.get_json()
    item_id = data.get('item_id')
    if not item_id or item_id not in SHOP_ITEMS:
        return jsonify({'error': 'Invalid item'}), 400
    
    user = db.fetch_one("SELECT coins FROM users WHERE user_id = ?", (user_id,))
    item = SHOP_ITEMS[item_id]
    
    if user['coins'] < item['price']:
        return jsonify({'error': f'Need {item["price"]} coins, you have {user["coins"]}'}), 400
    
    new_coins = user['coins'] - item['price']
    db.execute("UPDATE users SET coins = ? WHERE user_id = ?", (new_coins, user_id))
    db.execute("INSERT INTO user_inventory (user_id, item_id, acquired_at) VALUES (?, ?, datetime('now'))", (user_id, item_id))
    
    return jsonify({'success': True, 'message': f'Purchased {item["name"]}!', 'new_coins': new_coins})

@app.route('/inventory')
@login_required
def inventory():
    user = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (session['user_id'],))
    inventory_items = db.fetch_all("SELECT * FROM user_inventory WHERE user_id = ? ORDER BY acquired_at DESC", (session['user_id'],))
    
    inventory_details = []
    for inv_item in inventory_items:
        if inv_item['item_id'] in SHOP_ITEMS:
            item = SHOP_ITEMS[inv_item['item_id']].copy()
            item['acquired_at'] = inv_item['acquired_at']
            inventory_details.append(item)
    
    return render_template('inventory.html', user=user, items=inventory_details)

@app.route('/api/inventory', methods=['GET'])
@login_required
def get_inventory():
    user_id = session['user_id']
    inventory_items = db.fetch_all("SELECT item_id, COUNT(*) as quantity FROM user_inventory WHERE user_id = ? GROUP BY item_id", (user_id,))
    
    inventory = {}
    for item in inventory_items:
        if item['item_id'] in SHOP_ITEMS:
            inventory[item['item_id']] = {
                'id': item['item_id'],
                'name': SHOP_ITEMS[item['item_id']]['name'],
                'icon': SHOP_ITEMS[item['item_id']]['icon'],
                'game_effect': SHOP_ITEMS[item['item_id']].get('game_effect'),
                'quantity': item['quantity']
            }
    
    return jsonify({'success': True, 'inventory': inventory})

@app.route('/api/snake/stats', methods=['GET'])
@login_required
def get_snake_stats():
    user_id = session['user_id']
    stats = db.fetch_one("SELECT * FROM snake_stats WHERE user_id = ?", (user_id,))
    
    if not stats:
        return jsonify({
            'success': True,
            'stats': {
                'games_played': 0,
                'total_food_eaten': 0,
                'longest_run': 0,
                'best_streak': 0,
                'total_playtime': 0
            }
        })
    
    return jsonify({
        'success': True,
        'stats': {
            'games_played': stats['games_played'],
            'total_food_eaten': stats['total_food_eaten'],
            'longest_run': stats['longest_run'],
            'best_streak': stats['best_streak'],
            'total_playtime': stats['total_playtime']
        }
    })

# Google OAuth routes
@app.route('/auth/google')
def google_login():
    google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
    logger.info(f"Google login attempted - CLIENT_ID set: {'Yes' if google_client_id else 'No'}")
    logger.info(f"CLIENT_ID value: {google_client_id[:20] + '...' if google_client_id else 'None'}")
    
    if not google_client_id:
        logger.error("Google OAuth is NOT configured!")
        flash('Google login is not configured', 'warning')
        return redirect(url_for('login'))
    
    redirect_uri = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/google/callback')
    logger.info(f"Redirect URI: {redirect_uri}")
    return oauth.google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_auth_callback():
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info:
            flash('Failed to get user info from Google', 'danger')
            return redirect(url_for('login'))
        
        email = user_info.get('email')
        name = user_info.get('name', email.split('@')[0])
        
        # Check if user exists
        user = db.fetch_one("SELECT * FROM users WHERE email = ?", (email,))
        
        if not user:
            # Create new user
            default_settings = json.dumps({'theme': 'dark', 'sound': True, 'notifications': True, 'language': 'en'})
            db.execute(
                "INSERT INTO users (username, email, password_hash, coins, settings_config) VALUES (?, ?, ?, ?, ?)",
                (name.lower().replace(' ', '_'), email, 'google_oauth', 100, default_settings)
            )
            user = db.fetch_one("SELECT * FROM users WHERE email = ?", (email,))
            logger.info(f"New user created via Google OAuth: {email}")
        else:
            logger.info(f"User logged in via Google OAuth: {email}")
        
        # Set session
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session.permanent = True
        
        flash('Logged in successfully with Google!', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        logger.error(f"Google OAuth error: {e}")
        flash('Google login failed. Please try again.', 'danger')
        return redirect(url_for('login'))

# Database health check endpoint
@app.route('/api/health')
def health_check():
    try:
        db_healthy = db.health_check()
        return jsonify({
            'status': 'healthy' if db_healthy else 'unhealthy',
            'database': DB_TYPE,
            'timestamp': datetime.now().isoformat()
        }), 200 if db_healthy else 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Arcadia Hub on port {port}")
    logger.info(f"Using {DB_TYPE} database")
    app.run(debug=False, host='0.0.0.0', port=port)
