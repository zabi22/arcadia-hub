from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
import sqlite3
from datetime import datetime, timedelta
import json
import traceback
import hashlib
import re
import os

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

DB_NAME = 'gaming_app.db'

GAME_CONFIGS = {
    "snake": {"name": "Snake Arcade", "icon": "🐍", "color": "#00ff88", "difficulty": "Easy"},
    "tictactoe": {"name": "Tic Tac Toe", "icon": "⭕", "color": "#00d4ff", "difficulty": "Easy"},
    "memory": {"name": "Memory Match", "icon": "🧠", "color": "#ff6b6b", "difficulty": "Medium"},
    "reaction": {"name": "Reaction Time", "icon": "⚡", "color": "#ffd700", "difficulty": "Medium"},
    "wordle": {"name": "Word Guess", "icon": "🔤", "color": "#9b59b6", "difficulty": "Hard"},
    "pong": {"name": "Pong Classic", "icon": "🏓", "color": "#e74c3c", "difficulty": "Hard"},
    "game2048": {"name": "2048", "icon": "🔢", "color": "#edc22e", "difficulty": "Medium"},
    "flappy": {"name": "Flappy Bird", "icon": "🐦", "color": "#70c5ce", "difficulty": "Hard"}
}

SHOP_ITEMS = {
    'item_shield': {'name': 'Shield Power-up', 'description': 'Extra life in games', 'price': 100, 'icon': '🛡️', 'type': 'powerup', 'category': 'power'},
    'item_speed': {'name': 'Speed Boost', 'description': '2x speed boost', 'price': 150, 'icon': '⚡', 'type': 'powerup', 'category': 'boost'},
    'item_multiplier': {'name': 'Score Multiplier', 'description': '1.5x coins', 'price': 200, 'icon': '📈', 'type': 'powerup', 'category': 'score'},
    'avatar_dark': {'name': 'Dark Knight Avatar', 'description': 'Cool dark avatar', 'price': 50, 'icon': '🦇', 'type': 'avatar_skin', 'category': 'avatar'},
    'avatar_fire': {'name': 'Fire Phoenix Avatar', 'description': 'Fiery avatar', 'price': 75, 'icon': '🔥', 'type': 'avatar_skin', 'category': 'avatar'},
    'avatar_space': {'name': 'Space Astronaut Avatar', 'description': 'Galactic avatar', 'price': 75, 'icon': '👨‍🚀', 'type': 'avatar_skin', 'category': 'avatar'},
    'avatar_legend': {'name': 'Legendary Avatar', 'description': 'Ultra rare avatar', 'price': 300, 'icon': '👑', 'type': 'avatar_skin', 'category': 'avatar'},
    'badge_elite': {'name': 'Elite Player Badge', 'description': 'Elite badge', 'price': 100, 'icon': '⭐', 'type': 'badge', 'category': 'badge'},
    'badge_pro': {'name': 'Pro Gamer Badge', 'description': 'Pro badge', 'price': 150, 'icon': '🏆', 'type': 'badge', 'category': 'badge'}
}

class DatabaseManager:
    CURRENT_SCHEMA_VERSION = 3
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._init_version_table()
        self._run_migrations()
        self._init_tables()
        self._seed_games()
    
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
        migrations = [(1, self._migration_v1), (2, self._migration_v2), (3, self._migration_v3)]
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
    
    def _init_tables(self):
        tables = [
            ('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, email TEXT UNIQUE NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_login DATE, streak INTEGER DEFAULT 0, coins INTEGER DEFAULT 100, total_games_played INTEGER DEFAULT 0, total_score INTEGER DEFAULT 0, avatar_config TEXT, settings_config TEXT DEFAULT \\\'{"theme": "dark", "sound": true, "notifications": true}\\\')', "users"),
            ('CREATE TABLE IF NOT EXISTS games (game_id INTEGER PRIMARY KEY AUTOINCREMENT, game_key TEXT UNIQUE NOT NULL, name TEXT NOT NULL, category TEXT, difficulty TEXT, play_count INTEGER DEFAULT 0, icon TEXT, color TEXT)', "games"),
            ('CREATE TABLE IF NOT EXISTS scores (score_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, game_key TEXT NOT NULL, score INTEGER NOT NULL, play_time INTEGER DEFAULT 0, achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY(game_key) REFERENCES games(game_key) ON DELETE CASCADE)', "scores"),
            ('CREATE TABLE IF NOT EXISTS friends (friendship_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id_1 INTEGER NOT NULL, user_id_2 INTEGER NOT NULL, status TEXT DEFAULT \\\'pending\\\', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id_1, user_id_2), FOREIGN KEY(user_id_1) REFERENCES users(user_id) ON DELETE CASCADE, FOREIGN KEY(user_id_2) REFERENCES users(user_id) ON DELETE CASCADE)', "friends"),
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
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
    
    def fetch_one(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()
    
    def fetch_all(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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
    return render_template('dashboard.html', user=user, recent_scores=recent_scores, leaderboard=leaderboard, games=games)

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
    coins_earned = max(1, int(score / 10))
    
    db.execute("INSERT INTO scores (user_id, game_key, score, play_time) VALUES (?, ?, ?, ?)", (user_id, game_key, score, data.get('play_time', 0)))
    db.execute("UPDATE users SET coins = coins + ?, total_games_played = total_games_played + 1, total_score = total_score + ? WHERE user_id = ?", (coins_earned, score, user_id))
    db.execute("UPDATE games SET play_count = play_count + 1 WHERE game_key = ?", (game_key,))
    
    return jsonify({'success': True, 'coins_earned': coins_earned, 'message': f'Score saved! +{coins_earned} coins'})

@app.route('/leaderboard')
@login_required
def leaderboard():
    overall = db.fetch_all("SELECT u.username, SUM(s.score) as total_score, COUNT(s.score_id) as games_played, u.coins FROM scores s JOIN users u ON s.user_id = u.user_id GROUP BY s.user_id ORDER BY total_score DESC LIMIT 50")
    games_list = db.fetch_all("SELECT game_key, name FROM games")
    game_leaderboards = {}
    for game in games_list:
        game_leaderboards[game['game_key']] = db.fetch_all("SELECT u.username, MAX(s.score) as high_score, COUNT(s.score_id) as times_played FROM scores s JOIN users u ON s.user_id = u.user_id WHERE s.game_key = ? GROUP BY s.user_id ORDER BY high_score DESC LIMIT 20", (game['game_key'],))
    return render_template('leaderboard.html', overall=overall, game_leaderboards=game_leaderboards, games=games_list)

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
