import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime, timedelta
import json
import random
import re
import traceback
import time
import math
import threading
from typing import Dict, List, Optional, Tuple, Any, Callable

# Security imports
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    import hashlib
    import warnings
    warnings.warn("bcrypt not found. Using SHA-256 fallback. Install bcrypt for production.")

# Configuration and Constants
DB_NAME = 'gaming_app.db'
APP_NAME = "Arcadia Hub"
APP_VERSION = "2.0"

# Modern Color Palette
THEME_COLORS = {
    "dark": {
        "bg": "#0f0f1a",
        "bg_secondary": "#1a1a2e",
        "bg_card": "#16213e",
        "fg": "#eaeaea",
        "fg_secondary": "#a0a0a0",
        "accent": "#00d4ff",
        "accent_secondary": "#7b2cbf",
        "success": "#00ff88",
        "warning": "#ffd700",
        "danger": "#ff4757",
        "info": "#3498db",
        "border": "#2d3561",
        "gradient_start": "#667eea",
        "gradient_end": "#764ba2"
    },
    "light": {
        "bg": "#f8f9fa",
        "bg_secondary": "#e9ecef",
        "bg_card": "#ffffff",
        "fg": "#212529",
        "fg_secondary": "#6c757d",
        "accent": "#0066cc",
        "accent_secondary": "#6f42c1",
        "success": "#28a745",
        "warning": "#ffc107",
        "danger": "#dc3545",
        "info": "#17a2b8",
        "border": "#dee2e6",
        "gradient_start": "#4facfe",
        "gradient_end": "#00f2fe"
    }
}

# Game configurations
GAME_CONFIGS = {
    "snake": {"name": "Snake Arcade", "icon": "🐍", "color": "#00ff88", "difficulty": "Easy"},
    "tictactoe": {"name": "Tic Tac Toe", "icon": "⭕", "color": "#00d4ff", "difficulty": "Easy"},
    "memory": {"name": "Memory Match", "icon": "🧠", "color": "#ff6b6b", "difficulty": "Medium"},
    "reaction": {"name": "Reaction Time", "icon": "⚡", "color": "#ffd700", "difficulty": "Medium"},
    "wordle": {"name": "Word Guess", "icon": "🔤", "color": "#9b59b6", "difficulty": "Hard"},
    "pong": {"name": "Pong Classic", "icon": "🏓", "color": "#e74c3c", "difficulty": "Hard"}
}


class DatabaseManager:
    """Robust database manager with migrations and relationship handling."""
    
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
        """Initialize schema version tracking."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        
    def _get_schema_version(self) -> int:
        """Get current schema version."""
        try:
            self.cursor.execute("SELECT MAX(version) as v FROM schema_version")
            result = self.cursor.fetchone()
            return result['v'] or 0
        except:
            return 0
            
    def _set_schema_version(self, version: int):
        """Set schema version."""
        self.cursor.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
            (version,)
        )
        self.conn.commit()
        
    def _run_migrations(self):
        """Run database migrations safely."""
        current_version = self._get_schema_version()
        
        migrations = [
            (1, self._migration_v1),
            (2, self._migration_v2),
            (3, self._migration_v3),
        ]
        
        for version, migration_func in migrations:
            if current_version < version:
                try:
                    migration_func()
                    self._set_schema_version(version)
                    print(f"Applied migration v{version}")
                except Exception as e:
                    print(f"Migration v{version} failed: {e}")
                    traceback.print_exc()
                    
    def _migration_v1(self):
        """Initial schema setup."""
        pass
        
    def _migration_v2(self):
        """Add sessions table and user stats."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                ip_address TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        
    def _migration_v3(self):
        """Add achievements and notifications."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                achievement_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                achievement_type TEXT,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                message TEXT,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        self.conn.commit()
        
    def _init_tables(self):
        """Initialize all database tables with migration support."""
        # Create tables one by one with error handling
        table_creations = [
            ('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login DATE,
                streak INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 100,
                total_games_played INTEGER DEFAULT 0,
                total_score INTEGER DEFAULT 0,
                avatar_config TEXT,
                settings_config TEXT DEFAULT '{"theme": "dark", "sound": true, "notifications": true}'
            )''', "users"),
            ('''CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_key TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                difficulty TEXT,
                play_count INTEGER DEFAULT 0,
                icon TEXT,
                color TEXT
            )''', "games"),
            ('''CREATE TABLE IF NOT EXISTS scores (
                score_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game_key TEXT NOT NULL,
                score INTEGER NOT NULL,
                play_time INTEGER DEFAULT 0,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(game_key) REFERENCES games(game_key) ON DELETE CASCADE
            )''', "scores"),
            ('''CREATE TABLE IF NOT EXISTS friends (
                friendship_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id_1 INTEGER NOT NULL,
                user_id_2 INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id_1, user_id_2),
                FOREIGN KEY(user_id_1) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(user_id_2) REFERENCES users(user_id) ON DELETE CASCADE
            )''', "friends"),
            ('''CREATE TABLE IF NOT EXISTS messages (
                msg_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(sender_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(receiver_id) REFERENCES users(user_id) ON DELETE CASCADE
            )''', "messages"),
        ]
        
        for table_sql, table_name in table_creations:
            try:
                self.cursor.execute(table_sql)
            except sqlite3.OperationalError as e:
                if "already exists" in str(e):
                    pass
                else:
                    print(f"Warning: Could not create {table_name}: {e}")
        
        # Create indexes
        indexes = [
            '''CREATE INDEX IF NOT EXISTS idx_scores_user ON scores(user_id)''',
            '''CREATE INDEX IF NOT EXISTS idx_scores_game ON scores(game_key)''',
            '''CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id)''',
            '''CREATE INDEX IF NOT EXISTS idx_messages_receiver ON messages(receiver_id)''',
        ]
        
        for idx_sql in indexes:
            try:
                self.cursor.execute(idx_sql)
            except sqlite3.OperationalError:
                pass
        
        self.conn.commit()
        
        # Migrate old schema if needed
        self._migrate_old_schema()
        
    def _migrate_old_schema(self):
        """Migrate from old schema to new schema."""
        try:
            # Check if games table has old schema (name column instead of game_key)
            self.cursor.execute("PRAGMA table_info(games)")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            # If old schema detected (has 'name' but not 'game_key')
            if columns and 'name' in columns and 'game_key' not in columns:
                print("Migrating old games table schema...")
                # Rename old table
                self.cursor.execute("ALTER TABLE games RENAME TO games_old")
                # Create new table
                self.cursor.execute('''
                    CREATE TABLE games (
                        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_key TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        category TEXT,
                        difficulty TEXT,
                        play_count INTEGER DEFAULT 0,
                        icon TEXT,
                        color TEXT
                    )
                ''')
                self.conn.commit()
                
            # Check if scores table uses game_name instead of game_key
            self.cursor.execute("PRAGMA table_info(scores)")
            columns = [col[1] for col in self.cursor.fetchall()]
            
            if columns and 'game_name' in columns and 'game_key' not in columns:
                print("Migrating old scores table schema...")
                self.cursor.execute("ALTER TABLE scores RENAME TO scores_old")
                self.cursor.execute('''
                    CREATE TABLE scores (
                        score_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        game_key TEXT NOT NULL,
                        score INTEGER NOT NULL,
                        play_time INTEGER DEFAULT 0,
                        achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                        FOREIGN KEY(game_key) REFERENCES games(game_key) ON DELETE CASCADE
                    )
                ''')
                self.conn.commit()
                
        except Exception as e:
            print(f"Schema migration warning: {e}")
            
    def _seed_games(self):
        """Seed initial game data."""
        for key, config in GAME_CONFIGS.items():
            self.cursor.execute('''
                INSERT OR IGNORE INTO games (game_key, name, category, difficulty, icon, color)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (key, config['name'], 'Arcade', config['difficulty'], config['icon'], config['color']))
        self.conn.commit()
        
    def get_connection(self):
        return self.conn
        
    def execute(self, query: str, params: tuple = ()):
        """Execute query with error handling."""
        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            return self.cursor
        except sqlite3.Error as e:
            self.conn.rollback()
            raise e
            
    def fetch_one(self, query: str, params: tuple = ()):
        """Fetch single row."""
        self.cursor.execute(query, params)
        return self.cursor.fetchone()
        
    def fetch_all(self, query: str, params: tuple = ()):
        """Fetch all rows."""
        self.cursor.execute(query, params)
        return self.cursor.fetchall()


class AuthSystem:
    """Enhanced authentication with security features."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.current_user: Optional[Dict] = None
        self.session_token: Optional[str] = None
        self.daily_reward_msg: str = ""
        
    def validate_username(self, username: str) -> Tuple[bool, str]:
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
        
    def validate_email(self, email: str) -> Tuple[bool, str]:
        """Validate email format."""
        if not email:
            return False, "Email is required."
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format."
        return True, ""
        
    def validate_password(self, password: str) -> Tuple[bool, str]:
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
            return hashlib.sha256(password.encode()).hexdigest().encode()
            
    def verify_password(self, password: str, stored_hash: bytes) -> bool:
        """Verify password against stored hash."""
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')
            
        if HAS_BCRYPT:
            try:
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
            except ValueError:
                return hashlib.sha256(password.encode()).hexdigest().encode() == stored_hash
        else:
            return hashlib.sha256(password.encode()).hexdigest().encode() == stored_hash
            
    def register(self, username: str, email: str, password: str) -> Tuple[bool, str]:
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
        except sqlite3.IntegrityError as e:
            if "username" in str(e).lower():
                return False, "Username already exists."
            return False, "Email already registered."
        except Exception as e:
            traceback.print_exc()
            return False, f"Registration failed: {str(e)}"
            
    def login(self, username: str, password: str) -> Tuple[bool, str]:
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
            self._create_session()
            return True, "Login successful!"
            
        except Exception as e:
            traceback.print_exc()
            return False, f"Login error: {str(e)}"
            
    def _create_session(self):
        """Create user session."""
        import secrets
        self.session_token = secrets.token_urlsafe(32)
        expires = datetime.now() + timedelta(days=7)
        
        self.db.execute(
            """INSERT INTO user_sessions (session_id, user_id, expires_at) 
               VALUES (?, ?, ?)""",
            (self.session_token, self.current_user['user_id'], expires)
        )
        
    def _process_login_rewards(self):
        """Calculate and award daily login rewards."""
        user_id = self.current_user['user_id']
        today = datetime.now().date()
        last_login_str = self.current_user['last_login']
        
        new_streak = 1
        reward = 0
        messages = []
        
        if last_login_str:
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
        if self.session_token:
            self.db.execute(
                "DELETE FROM user_sessions WHERE session_id = ?",
                (self.session_token,)
            )
        self.current_user = None
        self.session_token = None
        
    def update_settings(self, key: str, value: Any):
        """Update user settings."""
        if not self.current_user:
            return
            
        settings = json.loads(self.current_user['settings_config'] or '{}')
        settings[key] = value
        
        self.db.execute(
            "UPDATE users SET settings_config = ? WHERE user_id = ?",
            (json.dumps(settings), self.current_user['user_id'])
        )
        self.current_user['settings_config'] = json.dumps(settings)
        
    def get_settings(self) -> Dict:
        """Get user settings."""
        if not self.current_user:
            return {}
        return json.loads(self.current_user['settings_config'] or '{}')
        
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


class ModernFrame(tk.Frame):
    """Modern styled frame with rounded corners effect."""
    
    def __init__(self, master, colors: Dict, **kwargs):
        self.colors = colors
        bg = kwargs.pop('bg', colors['bg_card'])
        super().__init__(master, bg=bg, **kwargs)
        
        
class ModernButton(tk.Canvas):
    """Modern animated button with hover effects."""
    
    def __init__(self, master, text: str, command: Callable = None, 
                 colors: Dict = None, width: int = 150, height: int = 40,
                 font_size: int = 11, **kwargs):
        self.colors = colors or THEME_COLORS['dark']
        self.bg_color = kwargs.pop('bg', self.colors['accent'])
        self.fg_color = kwargs.pop('fg', 'white')
        self.command = command
        self.text = text
        self.is_hovered = False
        
        super().__init__(master, width=width, height=height, 
                        bg=self.colors['bg'], highlightthickness=0, **kwargs)
        
        self.font = ("Segoe UI", font_size, "bold")
        self.draw_button()
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        
    def draw_button(self):
        """Draw the button with rounded rectangle."""
        self.delete("all")
        
        # Create rounded rectangle
        radius = 8
        w, h = int(self['width']), int(self['height'])
        
        # Darken color on hover
        color = self._adjust_brightness(self.bg_color, 1.2 if self.is_hovered else 1.0)
        
        # Draw rounded rectangle
        self.create_rounded_rect(2, 2, w-2, h-2, radius, fill=color, outline="")
        
        # Draw text
        self.create_text(w//2, h//2, text=self.text, fill=self.fg_color, 
                        font=self.font)
                        
    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        """Create rounded rectangle."""
        points = [
            x1+radius, y1,
            x2-radius, y1,
            x2, y1,
            x2, y1+radius,
            x2, y2-radius,
            x2, y2,
            x2-radius, y2,
            x1+radius, y2,
            x1, y2,
            x1, y2-radius,
            x1, y1+radius,
            x1, y1
        ]
        return self.create_polygon(points, smooth=True, **kwargs)
        
    def _adjust_brightness(self, hex_color: str, factor: float) -> str:
        """Adjust color brightness."""
        hex_color = hex_color.lstrip('#')
        r = min(255, int(int(hex_color[0:2], 16) * factor))
        g = min(255, int(int(hex_color[2:4], 16) * factor))
        b = min(255, int(int(hex_color[4:6], 16) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
        
    def on_enter(self, event):
        self.is_hovered = True
        self.draw_button()
        self.config(cursor="hand2")
        
    def on_leave(self, event):
        self.is_hovered = False
        self.draw_button()
        
    def on_click(self, event):
        if self.command:
            self.command()


class ModernEntry(tk.Frame):
    """Modern styled entry with icon and validation."""
    
    def __init__(self, master, placeholder: str = "", show: str = "",
                 icon: str = "", colors: Dict = None, width: int = 30, **kwargs):
        self.colors = colors or THEME_COLORS['dark']
        super().__init__(master, bg=self.colors['bg_secondary'], **kwargs)
        
        # Icon label
        if icon:
            self.icon_label = tk.Label(self, text=icon, font=("Segoe UI", 14),
                                      bg=self.colors['bg_secondary'], 
                                      fg=self.colors['fg_secondary'])
            self.icon_label.pack(side="left", padx=(10, 5))
            
        # Entry field
        self.entry = tk.Entry(self, font=("Segoe UI", 11), show=show,
                             bg=self.colors['bg_secondary'], 
                             fg=self.colors['fg'],
                             insertbackground=self.colors['fg'],
                             relief="flat", width=width)
        self.entry.pack(side="left", fill="x", expand=True, padx=5, pady=8)
        
        self.placeholder = placeholder
        self.placeholder_shown = True
        
        if placeholder:
            self.show_placeholder()
            self.entry.bind("<FocusIn>", self.on_focus_in)
            self.entry.bind("<FocusOut>", self.on_focus_out)
            
    def show_placeholder(self):
        self.entry.config(fg=self.colors['fg_secondary'])
        self.entry.insert(0, self.placeholder)
        self.placeholder_shown = True
        
    def on_focus_in(self, event):
        if self.placeholder_shown:
            self.entry.delete(0, "end")
            self.entry.config(fg=self.colors['fg'])
            self.placeholder_shown = False
            
    def on_focus_out(self, event):
        if not self.entry.get():
            self.show_placeholder()
            
    def get(self) -> str:
        if self.placeholder_shown:
            return ""
        return self.entry.get()
        
    def set(self, value: str):
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
        self.entry.config(fg=self.colors['fg'])
        self.placeholder_shown = False


class GameEngine:
    """Base class for all games."""
    
    def __init__(self, root: tk.Tk, user_id: int, db: DatabaseManager, 
                 on_close: Callable, colors: Dict):
        self.root = root
        self.user_id = user_id
        self.db = db
        self.on_close = on_close
        self.colors = colors
        self.score = 0
        self.game_name = "Unknown"
        self.game_key = "unknown"
        self.play_time = 0
        self.start_time = time.time()
        
        # Create game window
        self.window = tk.Toplevel(root)
        self.window.configure(bg=colors['bg'])
        self.window.protocol("WM_DELETE_WINDOW", self.close_game)
        
    def save_score(self):
        """Save score to database and award coins."""
        self.play_time = int(time.time() - self.start_time)
        coins_earned = max(1, int(self.score / 10))
        
        self.db.execute(
            """INSERT INTO scores (user_id, game_key, score, play_time) 
               VALUES (?, ?, ?, ?)""",
            (self.user_id, self.game_key, self.score, self.play_time)
        )
        
        self.db.execute(
            """UPDATE users SET coins = coins + ?, total_games_played = total_games_played + 1,
               total_score = total_score + ? WHERE user_id = ?""",
            (coins_earned, self.score, self.user_id)
        )
        
        self.db.execute(
            "UPDATE games SET play_count = play_count + 1 WHERE game_key = ?",
            (self.game_key,)
        )
        
        messagebox.showinfo("Game Over", 
                           f"Score: {self.score}\nCoins earned: {coins_earned}")
        
    def close_game(self):
        """Close game window and callback."""
        self.window.destroy()
        if self.on_close:
            self.on_close()


class SnakeGame(GameEngine):
    """Enhanced Snake game with modern graphics."""
    
    def __init__(self, root, user_id, db, on_close, colors):
        super().__init__(root, user_id, db, on_close, colors)
        self.game_name = "Snake Arcade"
        self.game_key = "snake"
        
        self.window.title("Snake Arcade")
        self.window.geometry("800x600")
        
        self.cell_size = 20
        self.grid_width = 30
        self.grid_height = 20
        self.canvas_width = self.grid_width * self.cell_size
        self.canvas_height = self.grid_height * self.cell_size
        
        self.setup_ui()
        self.reset_game()
        
    def setup_ui(self):
        """Setup game UI."""
        # Header
        header = tk.Frame(self.window, bg=self.colors['bg_secondary'], height=60)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        self.score_label = tk.Label(header, text="Score: 0", 
                                   font=("Segoe UI", 16, "bold"),
                                   bg=self.colors['bg_secondary'],
                                   fg=self.colors['success'])
        self.score_label.pack(side="left", padx=20, pady=10)
        
        self.high_score_label = tk.Label(header, text="High: 0", 
                                        font=("Segoe UI", 12),
                                        bg=self.colors['bg_secondary'],
                                        fg=self.colors['fg_secondary'])
        self.high_score_label.pack(side="right", padx=20, pady=10)
        
        # Game canvas
        self.canvas = tk.Canvas(self.window, width=self.canvas_width, 
                               height=self.canvas_height,
                               bg=self.colors['bg'], highlightthickness=2,
                               highlightbackground=self.colors['border'])
        self.canvas.pack(padx=10, pady=10)
        
        # Controls info
        controls = tk.Label(self.window, 
                           text="Use Arrow Keys to Move | P to Pause",
                           font=("Segoe UI", 10),
                           bg=self.colors['bg'],
                           fg=self.colors['fg_secondary'])
        controls.pack(pady=5)
        
        # Bind controls
        self.window.bind("<Key>", self.on_key_press)
        self.window.focus_set()
        
    def reset_game(self):
        """Reset game state."""
        self.snake = [(5, 10), (4, 10), (3, 10)]
        self.direction = "Right"
        self.next_direction = "Right"
        self.food = self.spawn_food()
        self.score = 0
        self.running = True
        self.paused = False
        self.speed = 150
        
        self.update_score()
        self.game_loop()
        
    def spawn_food(self) -> Tuple[int, int]:
        """Spawn food at random location."""
        while True:
            x = random.randint(0, self.grid_width - 1)
            y = random.randint(0, self.grid_height - 1)
            if (x, y) not in self.snake:
                return (x, y)
                
    def on_key_press(self, event):
        """Handle key presses."""
        key = event.keysym
        
        if key == "p" or key == "P":
            self.paused = not self.paused
            return
            
        if key in ["Left", "Right", "Up", "Down"]:
            opposites = {"Left": "Right", "Right": "Left", 
                        "Up": "Down", "Down": "Up"}
            if opposites.get(key) != self.direction:
                self.next_direction = key
                
    def game_loop(self):
        """Main game loop."""
        if not self.running:
            self.save_score()
            self.show_game_over()
            return
            
        if not self.paused:
            self.direction = self.next_direction
            self.move_snake()
            self.draw()
            
        self.window.after(self.speed, self.game_loop)
        
    def move_snake(self):
        """Move snake and check collisions."""
        head_x, head_y = self.snake[0]
        
        if self.direction == "Left":
            head_x -= 1
        elif self.direction == "Right":
            head_x += 1
        elif self.direction == "Up":
            head_y -= 1
        elif self.direction == "Down":
            head_y += 1
            
        new_head = (head_x, head_y)
        
        # Check wall collision
        if head_x < 0 or head_x >= self.grid_width or \
           head_y < 0 or head_y >= self.grid_height:
            self.running = False
            return
            
        # Check self collision
        if new_head in self.snake:
            self.running = False
            return
            
        self.snake.insert(0, new_head)
        
        # Check food collision
        if new_head == self.food:
            self.score += 10
            self.food = self.spawn_food()
            # Increase speed slightly
            self.speed = max(50, self.speed - 2)
            self.update_score()
        else:
            self.snake.pop()
            
    def draw(self):
        """Draw game state."""
        self.canvas.delete("all")
        
        # Draw grid (subtle)
        for i in range(self.grid_width):
            for j in range(self.grid_height):
                x1 = i * self.cell_size
                y1 = j * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size
                if (i + j) % 2 == 0:
                    self.canvas.create_rectangle(x1, y1, x2, y2, 
                                                fill=self.colors['bg'], outline="")
                else:
                    self.canvas.create_rectangle(x1, y1, x2, y2,
                                                fill=self.colors['bg_secondary'], 
                                                outline="")
        
        # Draw food with glow effect
        fx, fy = self.food
        cx = fx * self.cell_size + self.cell_size // 2
        cy = fy * self.cell_size + self.cell_size // 2
        r = self.cell_size // 2 - 2
        
        self.canvas.create_oval(cx-r-2, cy-r-2, cx+r+2, cy+r+2,
                               fill=self.colors['danger'], outline="")
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                               fill=self.colors['warning'], outline="")
        
        # Draw snake
        for i, (x, y) in enumerate(self.snake):
            x1 = x * self.cell_size + 1
            y1 = y * self.cell_size + 1
            x2 = x1 + self.cell_size - 2
            y2 = y1 + self.cell_size - 2
            
            if i == 0:  # Head
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                           fill=self.colors['success'], outline="")
                # Eyes
                eye_size = 3
                if self.direction in ["Left", "Right"]:
                    self.canvas.create_oval(x1+3, y1+4, x1+3+eye_size, y1+4+eye_size,
                                          fill="white", outline="")
                    self.canvas.create_oval(x1+3, y2-4-eye_size, x1+3+eye_size, y2-4,
                                          fill="white", outline="")
                else:
                    self.canvas.create_oval(x1+4, y1+3, x1+4+eye_size, y1+3+eye_size,
                                          fill="white", outline="")
                    self.canvas.create_oval(x2-4-eye_size, y1+3, x2-4, y1+3+eye_size,
                                          fill="white", outline="")
            else:  # Body
                color_intensity = max(0.5, 1 - (i / len(self.snake)) * 0.5)
                body_color = self._adjust_color(self.colors['success'], color_intensity)
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                           fill=body_color, outline="")
                                           
        # Draw pause overlay
        if self.paused:
            self.canvas.create_text(self.canvas_width//2, self.canvas_height//2,
                                   text="PAUSED", font=("Segoe UI", 30, "bold"),
                                   fill=self.colors['fg'])
                                   
    def _adjust_color(self, hex_color: str, factor: float) -> str:
        """Adjust color brightness."""
        hex_color = hex_color.lstrip('#')
        r = min(255, int(int(hex_color[0:2], 16) * factor))
        g = min(255, int(int(hex_color[2:4], 16) * factor))
        b = min(255, int(int(hex_color[4:6], 16) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
        
    def update_score(self):
        """Update score display."""
        self.score_label.config(text=f"Score: {self.score}")
        
    def show_game_over(self):
        """Show game over screen."""
        overlay = tk.Frame(self.window, bg=self.colors['bg'])
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        tk.Label(overlay, text="GAME OVER", font=("Segoe UI", 36, "bold"),
                bg=self.colors['bg'], fg=self.colors['danger']).pack(pady=50)
        
        tk.Label(overlay, text=f"Final Score: {self.score}",
                font=("Segoe UI", 20), bg=self.colors['bg'],
                fg=self.colors['fg']).pack(pady=20)
        
        btn_frame = tk.Frame(overlay, bg=self.colors['bg'])
        btn_frame.pack(pady=30)
        
        ModernButton(btn_frame, text="Play Again", 
                    command=lambda: [overlay.destroy(), self.reset_game()],
                    colors=self.colors, bg=self.colors['success']).pack(side="left", padx=10)
        
        ModernButton(btn_frame, text="Exit",
                    command=self.close_game,
                    colors=self.colors, bg=self.colors['danger']).pack(side="left", padx=10)


class TicTacToe(GameEngine):
    """Enhanced Tic Tac Toe with smart AI."""
    
    def __init__(self, root, user_id, db, on_close, colors):
        super().__init__(root, user_id, db, on_close, colors)
        self.game_name = "Tic Tac Toe"
        self.game_key = "tictactoe"
        
        self.window.title("Tic Tac Toe")
        self.window.geometry("500x600")
        
        self.board = [""] * 9
        self.current_player = "X"
        self.game_over = False
        self.player_wins = 0
        self.computer_wins = 0
        self.draws = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup game UI."""
        # Header
        header = tk.Frame(self.window, bg=self.colors['bg_secondary'], height=80)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        self.status_label = tk.Label(header, text="Your Turn (X)",
                                    font=("Segoe UI", 18, "bold"),
                                    bg=self.colors['bg_secondary'],
                                    fg=self.colors['accent'])
        self.status_label.pack(pady=20)
        
        # Stats
        stats_frame = tk.Frame(self.window, bg=self.colors['bg'])
        stats_frame.pack(pady=10)
        
        self.stats_label = tk.Label(stats_frame,
                                   text=f"You: {self.player_wins} | Computer: {self.computer_wins} | Draws: {self.draws}",
                                   font=("Segoe UI", 12),
                                   bg=self.colors['bg'],
                                   fg=self.colors['fg_secondary'])
        self.stats_label.pack()
        
        # Game board
        board_frame = tk.Frame(self.window, bg=self.colors['bg'])
        board_frame.pack(pady=20)
        
        self.buttons = []
        for i in range(9):
            btn = tk.Button(board_frame, text="", font=("Segoe UI", 32, "bold"),
                          width=3, height=1,
                          bg=self.colors['bg_card'],
                          fg=self.colors['fg'],
                          relief="flat",
                          activebackground=self.colors['bg_secondary'],
                          command=lambda idx=i: self.player_move(idx))
            btn.grid(row=i//3, column=i%3, padx=5, pady=5)
            self.buttons.append(btn)
            
        # Control buttons
        controls = tk.Frame(self.window, bg=self.colors['bg'])
        controls.pack(pady=20)
        
        ModernButton(controls, text="New Game",
                    command=self.reset_game,
                    colors=self.colors, bg=self.colors['accent']).pack(side="left", padx=10)
        
        ModernButton(controls, text="Exit",
                    command=self.close_game,
                    colors=self.colors, bg=self.colors['danger']).pack(side="left", padx=10)
        
    def player_move(self, index):
        """Handle player move."""
        if self.board[index] == "" and not self.game_over and self.current_player == "X":
            self.make_move(index, "X")
            if not self.game_over:
                self.window.after(500, self.computer_move)
                
    def computer_move(self):
        """Smart computer AI move."""
        if self.game_over:
            return
            
        # Try to win
        move = self.find_winning_move("O")
        if move is not None:
            self.make_move(move, "O")
            return
            
        # Block player win
        move = self.find_winning_move("X")
        if move is not None:
            self.make_move(move, "O")
            return
            
        # Take center
        if self.board[4] == "":
            self.make_move(4, "O")
            return
            
        # Take corner
        corners = [0, 2, 6, 8]
        random.shuffle(corners)
        for corner in corners:
            if self.board[corner] == "":
                self.make_move(corner, "O")
                return
                
        # Take any available
        available = [i for i, x in enumerate(self.board) if x == ""]
        if available:
            self.make_move(random.choice(available), "O")
            
    def find_winning_move(self, player: str) -> Optional[int]:
        """Find a winning move for player."""
        wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        for a, b, c in wins:
            line = [self.board[a], self.board[b], self.board[c]]
            if line.count(player) == 2 and line.count("") == 1:
                return [a, b, c][line.index("")]
        return None
        
    def make_move(self, index: int, player: str):
        """Make a move on the board."""
        self.board[index] = player
        color = self.colors['accent'] if player == "X" else self.colors['danger']
        self.buttons[index].config(text=player, fg=color,
                                  state="disabled", disabledforeground=color)
        
        if self.check_winner(player):
            self.game_over = True
            if player == "X":
                self.score = 100
                self.player_wins += 1
                self.status_label.config(text="You Win!", fg=self.colors['success'])
            else:
                self.computer_wins += 1
                self.status_label.config(text="Computer Wins!", fg=self.colors['danger'])
            self.save_score()
            self.update_stats()
        elif "" not in self.board:
            self.game_over = True
            self.draws += 1
            self.score = 25
            self.status_label.config(text="Draw!", fg=self.colors['warning'])
            self.save_score()
            self.update_stats()
        else:
            self.current_player = "O" if player == "X" else "X"
            status = "Your Turn (X)" if self.current_player == "X" else "Computer Thinking..."
            self.status_label.config(text=status)
            
    def check_winner(self, player: str) -> bool:
        """Check if player has won."""
        wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        return any(self.board[a] == self.board[b] == self.board[c] == player 
                  for a, b, c in wins)
                  
    def update_stats(self):
        """Update stats display."""
        self.stats_label.config(
            text=f"You: {self.player_wins} | Computer: {self.computer_wins} | Draws: {self.draws}"
        )
        
    def reset_game(self):
        """Reset the game."""
        self.board = [""] * 9
        self.current_player = "X"
        self.game_over = False
        self.score = 0
        
        self.status_label.config(text="Your Turn (X)", fg=self.colors['accent'])
        
        for btn in self.buttons:
            btn.config(text="", state="normal", fg=self.colors['fg'])


class MemoryMatch(GameEngine):
    """Memory card matching game."""
    
    def __init__(self, root, user_id, db, on_close, colors):
        super().__init__(root, user_id, db, on_close, colors)
        self.game_name = "Memory Match"
        self.game_key = "memory"
        
        self.window.title("Memory Match")
        self.window.geometry("600x700")
        
        self.cards = ['🎮', '🎯', '🎲', '🎸', '🎨', '🎭', '🎪', '🎬'] * 2
        random.shuffle(self.cards)
        self.buttons = []
        self.flipped = []
        self.matched = []
        self.moves = 0
        self.pairs_found = 0
        self.can_flip = True
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup game UI."""
        # Header
        header = tk.Frame(self.window, bg=self.colors['bg_secondary'], height=80)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        self.status_label = tk.Label(header, text="Find all matching pairs!",
                                    font=("Segoe UI", 16, "bold"),
                                    bg=self.colors['bg_secondary'],
                                    fg=self.colors['accent'])
        self.status_label.pack(pady=10)
        
        self.moves_label = tk.Label(header, text="Moves: 0",
                                   font=("Segoe UI", 12),
                                   bg=self.colors['bg_secondary'],
                                   fg=self.colors['fg_secondary'])
        self.moves_label.pack()
        
        # Game grid
        grid_frame = tk.Frame(self.window, bg=self.colors['bg'])
        grid_frame.pack(pady=20)
        
        for i in range(16):
            btn = tk.Button(grid_frame, text="", font=("Segoe UI", 28),
                          width=4, height=2,
                          bg=self.colors['bg_card'],
                          fg=self.colors['fg'],
                          relief="flat",
                          activebackground=self.colors['accent'],
                          command=lambda idx=i: self.flip_card(idx))
            btn.grid(row=i//4, column=i%4, padx=5, pady=5)
            self.buttons.append(btn)
            
        # Control buttons
        controls = tk.Frame(self.window, bg=self.colors['bg'])
        controls.pack(pady=20)
        
        ModernButton(controls, text="New Game",
                    command=self.reset_game,
                    colors=self.colors, bg=self.colors['accent']).pack(side="left", padx=10)
        
        ModernButton(controls, text="Exit",
                    command=self.close_game,
                    colors=self.colors, bg=self.colors['danger']).pack(side="left", padx=10)
                    
    def flip_card(self, index):
        """Flip a card."""
        if not self.can_flip or index in self.flipped or index in self.matched:
            return
            
        btn = self.buttons[index]
        btn.config(text=self.cards[index], bg=self.colors['accent'])
        self.flipped.append(index)
        
        if len(self.flipped) == 2:
            self.moves += 1
            self.moves_label.config(text=f"Moves: {self.moves}")
            self.can_flip = False
            self.window.after(800, self.check_match)
            
    def check_match(self):
        """Check if flipped cards match."""
        idx1, idx2 = self.flipped
        
        if self.cards[idx1] == self.cards[idx2]:
            self.matched.extend(self.flipped)
            self.buttons[idx1].config(bg=self.colors['success'], state="disabled")
            self.buttons[idx2].config(bg=self.colors['success'], state="disabled")
            self.pairs_found += 1
            self.score = self.pairs_found * 50 - self.moves * 2
            
            if len(self.matched) == 16:
                self.game_over()
        else:
            self.buttons[idx1].config(text="", bg=self.colors['bg_card'])
            self.buttons[idx2].config(text="", bg=self.colors['bg_card'])
            
        self.flipped = []
        self.can_flip = True
        
    def game_over(self):
        """Handle game completion."""
        final_score = max(0, 400 - self.moves * 5)
        self.score = final_score
        self.status_label.config(text="You Won!", fg=self.colors['success'])
        messagebox.showinfo("Congratulations!", f"You found all pairs in {self.moves} moves!")
        self.save_score()
        
    def reset_game(self):
        """Reset the game."""
        random.shuffle(self.cards)
        self.flipped = []
        self.matched = []
        self.moves = 0
        self.pairs_found = 0
        self.can_flip = True
        self.score = 0
        
        self.status_label.config(text="Find all matching pairs!", fg=self.colors['accent'])
        self.moves_label.config(text="Moves: 0")
        
        for btn in self.buttons:
            btn.config(text="", bg=self.colors['bg_card'], state="normal")


class ReactionTime(GameEngine):
    """Test your reaction time game."""
    
    def __init__(self, root, user_id, db, on_close, colors):
        super().__init__(root, user_id, db, on_close, colors)
        self.game_name = "Reaction Time"
        self.game_key = "reaction"
        
        self.window.title("Reaction Time Test")
        self.window.geometry("600x500")
        
        self.state = "waiting"  # waiting, ready, clicked
        self.reaction_time = 0
        self.start_time = 0
        self.best_time = None
        self.attempts = []
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup game UI."""
        # Header
        header = tk.Frame(self.window, bg=self.colors['bg_secondary'], height=80)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="Reaction Time Test",
                font=("Segoe UI", 20, "bold"),
                bg=self.colors['bg_secondary'],
                fg=self.colors['accent']).pack(pady=10)
        
        # Best time display
        self.best_label = tk.Label(header, text="Best: -- ms",
                                  font=("Segoe UI", 12),
                                  bg=self.colors['bg_secondary'],
                                  fg=self.colors['fg_secondary'])
        self.best_label.pack()
        
        # Main click area
        self.click_area = tk.Frame(self.window, bg=self.colors['danger'])
        self.click_area.place(relx=0.5, rely=0.5, anchor="center",
                             width=400, height=250)
        
        self.click_label = tk.Label(self.click_area, text="CLICK TO START",
                                   font=("Segoe UI", 24, "bold"),
                                   bg=self.colors['danger'],
                                   fg="white")
        self.click_label.place(relx=0.5, rely=0.5, anchor="center")
        
        self.click_area.bind("<Button-1>", lambda e: self.on_click())
        self.click_label.bind("<Button-1>", lambda e: self.on_click())
        
        # Instructions
        self.instruction_label = tk.Label(self.window,
                                         text="Click the box when it turns GREEN",
                                         font=("Segoe UI", 12),
                                         bg=self.colors['bg'],
                                         fg=self.colors['fg_secondary'])
        self.instruction_label.pack(side="bottom", pady=20)
        
        # Results
        self.result_label = tk.Label(self.window, text="",
                                    font=("Segoe UI", 18, "bold"),
                                    bg=self.colors['bg'],
                                    fg=self.colors['fg'])
        self.result_label.pack(side="bottom", pady=10)
        
        # Control buttons
        controls = tk.Frame(self.window, bg=self.colors['bg'])
        controls.pack(side="bottom", pady=20)
        
        ModernButton(controls, text="Exit",
                    command=self.close_game,
                    colors=self.colors, bg=self.colors['danger']).pack()
                    
    def on_click(self):
        """Handle click on the reaction area."""
        if self.state == "waiting":
            self.start_round()
        elif self.state == "ready":
            self.too_early()
        elif self.state == "go":
            self.record_time()
            
    def start_round(self):
        """Start a new reaction round."""
        self.state = "ready"
        self.click_area.config(bg=self.colors['warning'])
        self.click_label.config(text="WAIT...", bg=self.colors['warning'])
        self.result_label.config(text="")
        
        # Random delay between 1-4 seconds
        delay = random.randint(1000, 4000)
        self.window.after(delay, self.show_go)
        
    def show_go(self):
        """Show the GO signal."""
        if self.state == "ready":
            self.state = "go"
            self.start_time = time.time()
            self.click_area.config(bg=self.colors['success'])
            self.click_label.config(text="CLICK NOW!", bg=self.colors['success'])
            
    def too_early(self):
        """Handle early click."""
        self.state = "waiting"
        self.click_area.config(bg=self.colors['danger'])
        self.click_label.config(text="TOO EARLY!", bg=self.colors['danger'])
        self.result_label.config(text="Wait for green!", fg=self.colors['danger'])
        self.window.after(1500, self.reset_round)
        
    def record_time(self):
        """Record reaction time."""
        self.reaction_time = int((time.time() - self.start_time) * 1000)
        self.attempts.append(self.reaction_time)
        
        if self.best_time is None or self.reaction_time < self.best_time:
            self.best_time = self.reaction_time
            self.best_label.config(text=f"Best: {self.best_time} ms")
            
        self.score = max(0, 500 - self.reaction_time)
        
        self.click_area.config(bg=self.colors['accent'])
        self.click_label.config(text=f"{self.reaction_time} ms", bg=self.colors['accent'])
        self.result_label.config(text=f"Reaction time: {self.reaction_time} ms", 
                                fg=self.colors['success'])
        
        self.state = "waiting"
        
        if len(self.attempts) >= 5:
            self.game_over()
        else:
            self.window.after(1500, self.reset_round)
            
    def reset_round(self):
        """Reset for next round."""
        self.click_area.config(bg=self.colors['danger'])
        self.click_label.config(text="CLICK TO START", bg=self.colors['danger'])
        
    def game_over(self):
        """End the game."""
        avg_time = sum(self.attempts) // len(self.attempts)
        self.score = max(0, 1000 - avg_time * 2)
        
        messagebox.showinfo("Game Over", 
                           f"Average reaction time: {avg_time} ms\nBest time: {self.best_time} ms")
        self.save_score()
        self.attempts = []
        self.best_time = None
        self.best_label.config(text="Best: -- ms")
        self.reset_round()


class WordGuess(GameEngine):
    """Word guessing game similar to Wordle."""
    
    WORDS = [
        "APPLE", "BEACH", "CHAIR", "DANCE", "EAGLE", "FLAME", "GRAPE", "HOUSE",
        "IMAGE", "JUICE", "KNIFE", "LEMON", "MUSIC", "NIGHT", "OCEAN", "PIANO",
        "QUEEN", "RIVER", "SNAKE", "TABLE", "UNCLE", "VIDEO", "WATER", "YOUTH",
        "BREAD", "CLOUD", "DREAM", "EARTH", "FRUIT", "GREEN", "HEART", "ISLAND",
        "JELLY", "LIGHT", "MONEY", "NURSE", "ORANGE", "PAPER", "QUIET", "ROBOT",
        "SLEEP", "TRAIN", "VOICE", "WATCH", "ZEBRA", "SMILE", "PLANT", "TIGER"
    ]
    
    def __init__(self, root, user_id, db, on_close, colors):
        super().__init__(root, user_id, db, on_close, colors)
        self.game_name = "Word Guess"
        self.game_key = "wordle"
        
        self.window.title("Word Guess")
        self.window.geometry("500x700")
        
        self.target_word = random.choice(self.WORDS)
        self.current_row = 0
        self.current_col = 0
        self.guesses = [["" for _ in range(5)] for _ in range(6)]
        self.labels = []
        self.game_over_flag = False
        
        self.setup_ui()
        self.window.bind("<Key>", self.on_key)
        self.window.bind("<BackSpace>", self.on_backspace)
        self.window.bind("<Return>", self.on_enter)
        
    def setup_ui(self):
        """Setup game UI."""
        # Header
        header = tk.Frame(self.window, bg=self.colors['bg_secondary'], height=80)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="Word Guess",
                font=("Segoe UI", 20, "bold"),
                bg=self.colors['bg_secondary'],
                fg=self.colors['accent']).pack(pady=10)
        
        tk.Label(header, text="Guess the 5-letter word",
                font=("Segoe UI", 11),
                bg=self.colors['bg_secondary'],
                fg=self.colors['fg_secondary']).pack()
        
        # Game grid
        grid_frame = tk.Frame(self.window, bg=self.colors['bg'])
        grid_frame.pack(pady=30)
        
        for row in range(6):
            row_labels = []
            for col in range(5):
                lbl = tk.Label(grid_frame, text="", font=("Segoe UI", 24, "bold"),
                             width=3, height=1,
                             bg=self.colors['bg_card'],
                             fg=self.colors['fg'],
                             relief="solid", borderwidth=2)
                lbl.grid(row=row, column=col, padx=5, pady=5)
                row_labels.append(lbl)
            self.labels.append(row_labels)
            
        # Keyboard
        keyboard_frame = tk.Frame(self.window, bg=self.colors['bg'])
        keyboard_frame.pack(pady=20)
        
        keys = [
            "QWERTYUIOP",
            "ASDFGHJKL",
            "ZXCVBNM"
        ]
        
        for row_keys in keys:
            row_frame = tk.Frame(keyboard_frame, bg=self.colors['bg'])
            row_frame.pack(pady=2)
            for key in row_keys:
                btn = tk.Button(row_frame, text=key, font=("Segoe UI", 12, "bold"),
                              width=3, bg=self.colors['bg_card'], fg=self.colors['fg'],
                              relief="flat", command=lambda k=key: self.on_key_char(k))
                btn.pack(side="left", padx=2)
                
        # Control buttons
        controls = tk.Frame(self.window, bg=self.colors['bg'])
        controls.pack(pady=20)
        
        ModernButton(controls, text="New Word",
                    command=self.reset_game,
                    colors=self.colors, bg=self.colors['accent']).pack(side="left", padx=10)
        
        ModernButton(controls, text="Exit",
                    command=self.close_game,
                    colors=self.colors, bg=self.colors['danger']).pack(side="left", padx=10)
                    
    def on_key(self, event):
        """Handle keyboard input."""
        if self.game_over_flag:
            return
        char = event.char.upper()
        if char.isalpha() and len(char) == 1:
            self.on_key_char(char)
            
    def on_key_char(self, char):
        """Handle character input."""
        if self.game_over_flag or self.current_col >= 5:
            return
        self.guesses[self.current_row][self.current_col] = char
        self.labels[self.current_row][self.current_col].config(text=char)
        self.current_col += 1
        
    def on_backspace(self, event):
        """Handle backspace."""
        if self.game_over_flag or self.current_col <= 0:
            return
        self.current_col -= 1
        self.guesses[self.current_row][self.current_col] = ""
        self.labels[self.current_row][self.current_col].config(text="")
        
    def on_enter(self, event):
        """Handle enter key."""
        self.submit_guess()
        
    def submit_guess(self):
        """Submit current guess."""
        if self.game_over_flag or self.current_col < 5:
            return
            
        guess = "".join(self.guesses[self.current_row])
        
        # Check each letter
        target_list = list(self.target_word)
        guess_list = list(guess)
        
        # First pass: mark correct positions
        for i in range(5):
            if guess_list[i] == target_list[i]:
                self.labels[self.current_row][i].config(
                    bg=self.colors['success'], fg="white")
                target_list[i] = None
                guess_list[i] = None
                
        # Second pass: mark present but wrong position
        for i in range(5):
            if guess_list[i] is not None:
                if guess_list[i] in target_list:
                    self.labels[self.current_row][i].config(
                        bg=self.colors['warning'], fg="white")
                    target_list[target_list.index(guess_list[i])] = None
                else:
                    self.labels[self.current_row][i].config(
                        bg=self.colors['fg_secondary'], fg="white")
                        
        if guess == self.target_word:
            self.game_won()
        elif self.current_row >= 5:
            self.game_lost()
        else:
            self.current_row += 1
            self.current_col = 0
            
    def game_won(self):
        """Handle win."""
        self.game_over_flag = True
        attempts = self.current_row + 1
        self.score = max(0, 600 - attempts * 50)
        messagebox.showinfo("Congratulations!", 
                           f"You guessed the word in {attempts} tries!")
        self.save_score()
        
    def game_lost(self):
        """Handle loss."""
        self.game_over_flag = True
        self.score = 0
        messagebox.showinfo("Game Over", 
                           f"The word was: {self.target_word}")
        self.save_score()
        
    def reset_game(self):
        """Reset the game."""
        self.target_word = random.choice(self.WORDS)
        self.current_row = 0
        self.current_col = 0
        self.guesses = [["" for _ in range(5)] for _ in range(6)]
        self.game_over_flag = False
        self.score = 0
        
        for row in self.labels:
            for lbl in row:
                lbl.config(text="", bg=self.colors['bg_card'], fg=self.colors['fg'])


class PongGame(GameEngine):
    """Classic Pong game."""
    
    def __init__(self, root, user_id, db, on_close, colors):
        super().__init__(root, user_id, db, on_close, colors)
        self.game_name = "Pong Classic"
        self.game_key = "pong"
        
        self.window.title("Pong Classic")
        self.window.geometry("800x600")
        
        self.canvas_width = 800
        self.canvas_height = 500
        self.paddle_width = 15
        self.paddle_height = 80
        self.ball_size = 15
        
        self.player_score = 0
        self.computer_score = 0
        self.max_score = 5
        
        self.setup_ui()
        self.reset_ball()
        self.game_loop()
        
    def setup_ui(self):
        """Setup game UI."""
        # Header
        header = tk.Frame(self.window, bg=self.colors['bg_secondary'], height=80)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        score_frame = tk.Frame(header, bg=self.colors['bg_secondary'])
        score_frame.pack(expand=True)
        
        self.player_label = tk.Label(score_frame, text="You: 0",
                                    font=("Segoe UI", 18, "bold"),
                                    bg=self.colors['bg_secondary'],
                                    fg=self.colors['accent'])
        self.player_label.pack(side="left", padx=30)
        
        self.computer_label = tk.Label(score_frame, text="Computer: 0",
                                      font=("Segoe UI", 18, "bold"),
                                      bg=self.colors['bg_secondary'],
                                      fg=self.colors['danger'])
        self.computer_label.pack(side="left", padx=30)
        
        # Game canvas
        self.canvas = tk.Canvas(self.window, width=self.canvas_width,
                               height=self.canvas_height,
                               bg=self.colors['bg'], highlightthickness=2,
                               highlightbackground=self.colors['border'])
        self.canvas.pack(padx=10, pady=10)
        
        # Create paddles and ball
        self.player_paddle = self.canvas.create_rectangle(
            20, self.canvas_height//2 - self.paddle_height//2,
            20 + self.paddle_width, self.canvas_height//2 + self.paddle_height//2,
            fill=self.colors['accent'], outline="")
            
        self.computer_paddle = self.canvas.create_rectangle(
            self.canvas_width - 20 - self.paddle_width,
            self.canvas_height//2 - self.paddle_height//2,
            self.canvas_width - 20, self.canvas_height//2 + self.paddle_height//2,
            fill=self.colors['danger'], outline="")
            
        self.ball = self.canvas.create_oval(
            self.canvas_width//2 - self.ball_size//2,
            self.canvas_height//2 - self.ball_size//2,
            self.canvas_width//2 + self.ball_size//2,
            self.canvas_height//2 + self.ball_size//2,
            fill=self.colors['warning'], outline="")
            
        # Center line
        self.canvas.create_line(
            self.canvas_width//2, 0, self.canvas_width//2, self.canvas_height,
            fill=self.colors['border'], dash=(10, 10))
            
        # Controls
        self.window.bind("<KeyPress-w>", lambda e: self.move_paddle(-20))
        self.window.bind("<KeyPress-s>", lambda e: self.move_paddle(20))
        self.window.bind("<KeyPress-Up>", lambda e: self.move_paddle(-20))
        self.window.bind("<KeyPress-Down>", lambda e: self.move_paddle(20))
        
        # Instructions
        tk.Label(self.window, text="Use W/S or Arrow Keys to move",
                font=("Segoe UI", 11),
                bg=self.colors['bg'],
                fg=self.colors['fg_secondary']).pack()
                
    def move_paddle(self, dy):
        """Move player paddle."""
        coords = self.canvas.coords(self.player_paddle)
        new_y1 = coords[1] + dy
        new_y2 = coords[3] + dy
        
        if new_y1 >= 0 and new_y2 <= self.canvas_height:
            self.canvas.move(self.player_paddle, 0, dy)
            
    def reset_ball(self):
        """Reset ball to center."""
        self.ball_x = self.canvas_width // 2
        self.ball_y = self.canvas_height // 2
        self.ball_dx = random.choice([-4, 4])
        self.ball_dy = random.choice([-3, -2, 2, 3])
        
    def update_computer(self):
        """Update computer paddle position."""
        paddle_coords = self.canvas.coords(self.computer_paddle)
        paddle_center = (paddle_coords[1] + paddle_coords[3]) // 2
        
        if paddle_center < self.ball_y - 10:
            self.canvas.move(self.computer_paddle, 0, 4)
        elif paddle_center > self.ball_y + 10:
            self.canvas.move(self.computer_paddle, 0, -4)
            
    def game_loop(self):
        """Main game loop."""
        if self.player_score >= self.max_score or self.computer_score >= self.max_score:
            self.game_over()
            return
            
        # Move ball
        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy
        
        # Ball collision with top/bottom
        if self.ball_y <= 0 or self.ball_y >= self.canvas_height - self.ball_size:
            self.ball_dy = -self.ball_dy
            
        # Ball collision with paddles
        ball_coords = self.canvas.coords(self.ball)
        player_coords = self.canvas.coords(self.player_paddle)
        computer_coords = self.canvas.coords(self.computer_paddle)
        
        # Check player paddle collision
        if (ball_coords[0] <= player_coords[2] and 
            ball_coords[2] >= player_coords[0] and
            ball_coords[3] >= player_coords[1] and 
            ball_coords[1] <= player_coords[3]):
            self.ball_dx = abs(self.ball_dx) * 1.05
            self.ball_dy += random.choice([-1, 0, 1])
            
        # Check computer paddle collision
        if (ball_coords[2] >= computer_coords[0] and 
            ball_coords[0] <= computer_coords[2] and
            ball_coords[3] >= computer_coords[1] and 
            ball_coords[1] <= computer_coords[3]):
            self.ball_dx = -abs(self.ball_dx) * 1.05
            self.ball_dy += random.choice([-1, 0, 1])
            
        # Score
        if self.ball_x < 0:
            self.computer_score += 1
            self.computer_label.config(text=f"Computer: {self.computer_score}")
            self.reset_ball()
        elif self.ball_x > self.canvas_width:
            self.player_score += 1
            self.player_label.config(text=f"You: {self.player_score}")
            self.reset_ball()
            
        # Update ball position
        self.canvas.coords(self.ball,
                          self.ball_x - self.ball_size//2,
                          self.ball_y - self.ball_size//2,
                          self.ball_x + self.ball_size//2,
                          self.ball_y + self.ball_size//2)
                          
        # Update computer paddle
        self.update_computer()
        
        self.window.after(16, self.game_loop)  # ~60 FPS
        
    def game_over(self):
        """Handle game over."""
        if self.player_score > self.computer_score:
            self.score = self.player_score * 100
            messagebox.showinfo("Victory!", f"You won {self.player_score}-{self.computer_score}!")
        else:
            self.score = self.player_score * 50
            messagebox.showinfo("Defeat", f"You lost {self.player_score}-{self.computer_score}")
            
        self.save_score()
        self.close_game()


class ArcadiaHubApp:
    """Main application class."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Initialize database
        self.db = DatabaseManager()
        self.auth = AuthSystem(self.db)
        
        # Theme setup
        self.current_theme = "dark"
        self.colors = THEME_COLORS[self.current_theme]
        
        self.root.configure(bg=self.colors['bg'])
        
        # Main container
        self.main_container = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_container.pack(fill="both", expand=True)
        
        # Content area reference
        self.content_area = None
        
        # Show login screen
        self.show_login()
        
    def apply_theme(self):
        """Apply current theme to all widgets."""
        self.colors = THEME_COLORS[self.current_theme]
        self.root.configure(bg=self.colors['bg'])
        
    def clear_screen(self):
        """Clear main container."""
        for widget in self.main_container.winfo_children():
            widget.destroy()
            
    def show_login(self):
        """Show enhanced login screen."""
        self.clear_screen()
        self.apply_theme()
        
        # Create gradient background effect
        bg_frame = tk.Frame(self.main_container, bg=self.colors['bg'])
        bg_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Left panel with branding
        left_panel = tk.Frame(bg_frame, bg=self.colors['bg_secondary'])
        left_panel.place(relx=0, rely=0, relwidth=0.5, relheight=1)
        
        # Logo and branding
        logo_frame = tk.Frame(left_panel, bg=self.colors['bg_secondary'])
        logo_frame.place(relx=0.5, rely=0.4, anchor="center")
        
        tk.Label(logo_frame, text="🎮", font=("Segoe UI", 100),
                bg=self.colors['bg_secondary'], 
                fg=self.colors['accent']).pack()
        
        tk.Label(logo_frame, text=APP_NAME, font=("Segoe UI", 36, "bold"),
                bg=self.colors['bg_secondary'],
                fg=self.colors['fg']).pack(pady=10)
        
        tk.Label(logo_frame, text="Your Ultimate Gaming Destination",
                font=("Segoe UI", 14),
                bg=self.colors['bg_secondary'],
                fg=self.colors['fg_secondary']).pack()
        
        # Features list
        features_frame = tk.Frame(left_panel, bg=self.colors['bg_secondary'])
        features_frame.place(relx=0.5, rely=0.7, anchor="center")
        
        features = ["🎯 Multiple Games", "🏆 Global Leaderboards", 
                   "💬 Friend Chat", "🎨 Customizable Themes"]
        for feat in features:
            tk.Label(features_frame, text=feat, font=("Segoe UI", 12),
                    bg=self.colors['bg_secondary'],
                    fg=self.colors['fg_secondary']).pack(pady=5)
        
        # Right panel with login form
        right_panel = tk.Frame(bg_frame, bg=self.colors['bg'])
        right_panel.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)
        
        # Login form container
        form_frame = ModernFrame(right_panel, self.colors, padx=50, pady=50)
        form_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        tk.Label(form_frame, text="Welcome Back", font=("Segoe UI", 28, "bold"),
                bg=self.colors['bg_card'], fg=self.colors['fg']).pack(pady=(0, 10))
        
        tk.Label(form_frame, text="Sign in to continue your journey",
                font=("Segoe UI", 12),
                bg=self.colors['bg_card'], fg=self.colors['fg_secondary']).pack(pady=(0, 30))
        
        # Username entry
        tk.Label(form_frame, text="Username or Email", font=("Segoe UI", 11),
                bg=self.colors['bg_card'], fg=self.colors['fg'],
                anchor="w").pack(fill="x", pady=(10, 5))
        
        self.login_user = ModernEntry(form_frame, placeholder="Enter username",
                                     icon="👤", colors=self.colors, width=35)
        self.login_user.pack(fill="x", pady=5)
        
        # Password entry
        tk.Label(form_frame, text="Password", font=("Segoe UI", 11),
                bg=self.colors['bg_card'], fg=self.colors['fg'],
                anchor="w").pack(fill="x", pady=(15, 5))
        
        self.login_pass = ModernEntry(form_frame, placeholder="Enter password",
                                     icon="🔒", show="•",
                                     colors=self.colors, width=35)
        self.login_pass.pack(fill="x", pady=5)
        
        # Error message label
        self.login_error = tk.Label(form_frame, text="", font=("Segoe UI", 10),
                                   bg=self.colors['bg_card'], fg=self.colors['danger'])
        self.login_error.pack(pady=10)
        
        # Login button
        ModernButton(form_frame, text="Sign In", command=self.attempt_login,
                    colors=self.colors, bg=self.colors['accent'],
                    width=300, height=45, font_size=13).pack(pady=20)
        
        # Register link
        register_frame = tk.Frame(form_frame, bg=self.colors['bg_card'])
        register_frame.pack(pady=10)
        
        tk.Label(register_frame, text="Don't have an account? ",
                font=("Segoe UI", 11),
                bg=self.colors['bg_card'], fg=self.colors['fg_secondary']).pack(side="left")
        
        register_link = tk.Label(register_frame, text="Create one",
                                font=("Segoe UI", 11, "bold"),
                                bg=self.colors['bg_card'], fg=self.colors['accent'],
                                cursor="hand2")
        register_link.pack(side="left")
        register_link.bind("<Button-1>", lambda e: self.show_register())
        
    def attempt_login(self):
        """Handle login attempt."""
        username = self.login_user.get()
        password = self.login_pass.get()
        
        success, msg = self.auth.login(username, password)
        
        if success:
            if self.auth.daily_reward_msg:
                messagebox.showinfo("Daily Reward", self.auth.daily_reward_msg)
            
            # Load user theme
            settings = self.auth.get_settings()
            self.current_theme = settings.get('theme', 'dark')
            self.apply_theme()
            self.show_dashboard()
        else:
            self.login_error.config(text=msg)
            
    def show_register(self):
        """Show enhanced registration screen."""
        self.clear_screen()
        self.apply_theme()
        
        bg_frame = tk.Frame(self.main_container, bg=self.colors['bg'])
        bg_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Form container
        form_frame = ModernFrame(bg_frame, self.colors, padx=60, pady=50)
        form_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Title
        tk.Label(form_frame, text="Create Account", font=("Segoe UI", 28, "bold"),
                bg=self.colors['bg_card'], fg=self.colors['fg']).pack(pady=(0, 10))
        
        tk.Label(form_frame, text="Join the Arcadia community today",
                font=("Segoe UI", 12),
                bg=self.colors['bg_card'], fg=self.colors['fg_secondary']).pack(pady=(0, 30))
        
        # Username
        tk.Label(form_frame, text="Username", font=("Segoe UI", 11),
                bg=self.colors['bg_card'], fg=self.colors['fg'],
                anchor="w").pack(fill="x", pady=(10, 5))
        
        self.reg_user = ModernEntry(form_frame, placeholder="Choose a username",
                                   icon="👤", colors=self.colors, width=35)
        self.reg_user.pack(fill="x", pady=5)
        
        tk.Label(form_frame, text="3-20 characters, letters, numbers, underscores only",
                font=("Segoe UI", 9),
                bg=self.colors['bg_card'], fg=self.colors['fg_secondary']).pack(anchor="w")
        
        # Email
        tk.Label(form_frame, text="Email", font=("Segoe UI", 11),
                bg=self.colors['bg_card'], fg=self.colors['fg'],
                anchor="w").pack(fill="x", pady=(15, 5))
        
        self.reg_email = ModernEntry(form_frame, placeholder="your@email.com",
                                    icon="📧", colors=self.colors, width=35)
        self.reg_email.pack(fill="x", pady=5)
        
        # Password
        tk.Label(form_frame, text="Password", font=("Segoe UI", 11),
                bg=self.colors['bg_card'], fg=self.colors['fg'],
                anchor="w").pack(fill="x", pady=(15, 5))
        
        self.reg_pass = ModernEntry(form_frame, placeholder="Create a password",
                                   icon="🔒", show="•",
                                   colors=self.colors, width=35)
        self.reg_pass.pack(fill="x", pady=5)
        
        tk.Label(form_frame, text="Min 8 chars, 1 uppercase, 1 lowercase, 1 number",
                font=("Segoe UI", 9),
                bg=self.colors['bg_card'], fg=self.colors['fg_secondary']).pack(anchor="w")
        
        # Error label
        self.reg_error = tk.Label(form_frame, text="", font=("Segoe UI", 10),
                                 bg=self.colors['bg_card'], fg=self.colors['danger'])
        self.reg_error.pack(pady=10)
        
        # Register button
        ModernButton(form_frame, text="Create Account", command=self.attempt_register,
                    colors=self.colors, bg=self.colors['success'],
                    width=300, height=45, font_size=13).pack(pady=20)
        
        # Login link
        login_frame = tk.Frame(form_frame, bg=self.colors['bg_card'])
        login_frame.pack(pady=10)
        
        tk.Label(login_frame, text="Already have an account? ",
                font=("Segoe UI", 11),
                bg=self.colors['bg_card'], fg=self.colors['fg_secondary']).pack(side="left")
        
        login_link = tk.Label(login_frame, text="Sign in",
                             font=("Segoe UI", 11, "bold"),
                             bg=self.colors['bg_card'], fg=self.colors['accent'],
                             cursor="hand2")
        login_link.pack(side="left")
        login_link.bind("<Button-1>", lambda e: self.show_login())
        
    def attempt_register(self):
        """Handle registration attempt."""
        username = self.reg_user.get()
        email = self.reg_email.get()
        password = self.reg_pass.get()
        
        success, msg = self.auth.register(username, email, password)
        
        if success:
            messagebox.showinfo("Success", msg)
            self.show_login()
        else:
            self.reg_error.config(text=msg)
            
    def show_dashboard(self):
        """Show main dashboard."""
        self.clear_screen()
        self.apply_theme()
        
        user = self.auth.current_user
        
        # Main layout with sidebar
        sidebar = tk.Frame(self.main_container, bg=self.colors['bg_secondary'],
                          width=280)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        # Profile section
        profile_frame = tk.Frame(sidebar, bg=self.colors['bg_secondary'], height=200)
        profile_frame.pack(fill="x", pady=20)
        profile_frame.pack_propagate(False)
        
        # Avatar
        avatar_canvas = tk.Canvas(profile_frame, width=80, height=80,
                                 bg=self.colors['bg_secondary'],
                                 highlightthickness=0)
        avatar_canvas.pack(pady=15)
        
        # Draw circular avatar
        avatar_canvas.create_oval(5, 5, 75, 75, fill=self.colors['accent'],
                                 outline="")
        avatar_canvas.create_text(40, 40, text=user['username'][0].upper(),
                                 font=("Segoe UI", 32, "bold"),
                                 fill="white")
        
        # Username
        tk.Label(profile_frame, text=user['username'],
                font=("Segoe UI", 16, "bold"),
                bg=self.colors['bg_secondary'],
                fg=self.colors['fg']).pack()
        
        # Stats row
        stats_frame = tk.Frame(profile_frame, bg=self.colors['bg_secondary'])
        stats_frame.pack(pady=10)
        
        # Coins
        coin_frame = tk.Frame(stats_frame, bg=self.colors['bg_card'],
                             padx=15, pady=5)
        coin_frame.pack(side="left", padx=5)
        
        tk.Label(coin_frame, text="🪙", font=("Segoe UI", 14),
                bg=self.colors['bg_card']).pack(side="left")
        tk.Label(coin_frame, text=str(user['coins']),
                font=("Segoe UI", 12, "bold"),
                bg=self.colors['bg_card'],
                fg=self.colors['warning']).pack(side="left", padx=5)
        
        # Streak
        streak_frame = tk.Frame(stats_frame, bg=self.colors['bg_card'],
                               padx=15, pady=5)
        streak_frame.pack(side="left", padx=5)
        
        tk.Label(streak_frame, text="🔥", font=("Segoe UI", 14),
                bg=self.colors['bg_card']).pack(side="left")
        tk.Label(streak_frame, text=str(user['streak']),
                font=("Segoe UI", 12, "bold"),
                bg=self.colors['bg_card'],
                fg=self.colors['danger']).pack(side="left", padx=5)
        
        # Navigation
        nav_frame = tk.Frame(sidebar, bg=self.colors['bg_secondary'])
        nav_frame.pack(fill="x", pady=20)
        
        nav_items = [
            ("🎮", "Games", self.show_games_tab),
            ("💬", "Chat", self.show_chat_tab),
            ("🏆", "Leaderboard", self.show_leaderboard_tab),
            ("⚙️", "Settings", self.show_settings_tab),
        ]
        
        self.nav_buttons = []
        for icon, text, cmd in nav_items:
            btn = tk.Button(nav_frame, text=f"{icon}  {text}",
                          font=("Segoe UI", 12),
                          bg=self.colors['bg_secondary'],
                          fg=self.colors['fg_secondary'],
                          activebackground=self.colors['bg_card'],
                          activeforeground=self.colors['accent'],
                          relief="flat", anchor="w", padx=30, pady=12,
                          command=cmd)
            btn.pack(fill="x")
            self.nav_buttons.append((btn, cmd))
            
        # Logout button at bottom
        logout_btn = tk.Button(sidebar, text="🚪  Logout",
                              font=("Segoe UI", 12),
                              bg=self.colors['danger'],
                              fg="white",
                              relief="flat", padx=30, pady=12,
                              command=self.logout)
        logout_btn.pack(side="bottom", fill="x", padx=20, pady=20)
        
        # Content area
        self.content_area = tk.Frame(self.main_container, bg=self.colors['bg'])
        self.content_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        # Show games tab by default
        self.show_games_tab()
        
    def logout(self):
        """Logout user."""
        self.auth.logout()
        self.show_login()
        
    def show_games_tab(self):
        """Show games library."""
        self.clear_content()
        self.highlight_nav(0)
        
        # Header
        header = tk.Frame(self.content_area, bg=self.colors['bg'])
        header.pack(fill="x", pady=(0, 20))
        
        tk.Label(header, text="Game Library",
                font=("Segoe UI", 28, "bold"),
                bg=self.colors['bg'],
                fg=self.colors['fg']).pack(side="left")
        
        # Games grid
        games_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        games_frame.pack(fill="both", expand=True)
        
        # Configure grid
        for i in range(3):
            games_frame.columnconfigure(i, weight=1)
        for i in range(2):
            games_frame.rowconfigure(i, weight=1)
            
        games = ["snake", "tictactoe", "memory", "reaction", "wordle", "pong"]
        
        for idx, game_key in enumerate(games):
            config = GAME_CONFIGS[game_key]
            row, col = idx // 3, idx % 3
            
            # Game card
            card = tk.Frame(games_frame, bg=self.colors['bg_card'],
                          padx=20, pady=20)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            
            # Icon
            icon_label = tk.Label(card, text=config['icon'],
                                 font=("Segoe UI", 48),
                                 bg=self.colors['bg_card'],
                                 fg=config['color'])
            icon_label.pack()
            
            # Name
            tk.Label(card, text=config['name'],
                    font=("Segoe UI", 16, "bold"),
                    bg=self.colors['bg_card'],
                    fg=self.colors['fg']).pack(pady=5)
            
            # Difficulty badge
            diff_colors = {
                "Easy": self.colors['success'],
                "Medium": self.colors['warning'],
                "Hard": self.colors['danger']
            }
            diff_label = tk.Label(card, text=config['difficulty'],
                                 font=("Segoe UI", 10),
                                 bg=self.colors['bg_secondary'],
                                 fg=diff_colors.get(config['difficulty'], 
                                                     self.colors['fg_secondary']),
                                 padx=10, pady=2)
            diff_label.pack()
            
            # Play button
            ModernButton(card, text="PLAY NOW", 
                        command=lambda g=game_key: self.launch_game(g),
                        colors=self.colors, bg=config['color'],
                        width=180, height=35).pack(pady=15)
                        
    def launch_game(self, game_key: str):
        """Launch a game."""
        user_id = self.auth.current_user['user_id']
        if game_key == "snake":
            SnakeGame(self.root, user_id, self.db, self.refresh_dashboard, self.colors)
        elif game_key == "tictactoe":
            TicTacToe(self.root, user_id, self.db, self.refresh_dashboard, self.colors)
        elif game_key == "memory":
            MemoryMatch(self.root, user_id, self.db, self.refresh_dashboard, self.colors)
        elif game_key == "reaction":
            ReactionTime(self.root, user_id, self.db, self.refresh_dashboard, self.colors)
        elif game_key == "wordle":
            WordGuess(self.root, user_id, self.db, self.refresh_dashboard, self.colors)
        elif game_key == "pong":
            PongGame(self.root, user_id, self.db, self.refresh_dashboard, self.colors)
                          
    def show_chat_tab(self):
        """Show chat interface."""
        self.clear_content()
        self.highlight_nav(1)
        
        # Header
        header = tk.Frame(self.content_area, bg=self.colors['bg'])
        header.pack(fill="x", pady=(0, 20))
        
        tk.Label(header, text="Friends & Chat",
                font=("Segoe UI", 28, "bold"),
                bg=self.colors['bg'],
                fg=self.colors['fg']).pack(side="left")
        
        ModernButton(header, text="+ Add Friend",
                    command=self.add_friend,
                    colors=self.colors, bg=self.colors['success'],
                    width=120, height=35).pack(side="right")
        
        # Chat layout
        chat_paned = tk.PanedWindow(self.content_area, orient="horizontal",
                                   bg=self.colors['bg'])
        chat_paned.pack(fill="both", expand=True)
        
        # Friends list
        friends_frame = tk.Frame(chat_paned, bg=self.colors['bg_secondary'],
                                width=250)
        chat_paned.add(friends_frame)
        
        tk.Label(friends_frame, text="Friends",
                font=("Segoe UI", 14, "bold"),
                bg=self.colors['bg_secondary'],
                fg=self.colors['fg']).pack(pady=15)
        
        # Friends list container
        friends_list = tk.Frame(friends_frame, bg=self.colors['bg_secondary'])
        friends_list.pack(fill="both", expand=True, padx=10)
        
        # Load friends
        friends = self.db.fetch_all("""
            SELECT u.user_id, u.username, u.last_login,
                   (SELECT COUNT(*) FROM messages 
                    WHERE sender_id = u.user_id AND receiver_id = ? 
                    AND is_read = 0) as unread
            FROM users u
            JOIN friends f ON (u.user_id = f.user_id_1 OR u.user_id = f.user_id_2)
            WHERE (f.user_id_1 = ? OR f.user_id_2 = ?)
            AND u.user_id != ?
            AND f.status = 'accepted'
        """, (self.auth.current_user['user_id'],) * 4)
        
        self.selected_friend = None
        
        if not friends:
            tk.Label(friends_list, text="No friends yet",
                    font=("Segoe UI", 11),
                    bg=self.colors['bg_secondary'],
                    fg=self.colors['fg_secondary']).pack(pady=20)
        else:
            for friend in friends:
                self.create_friend_button(friends_list, friend)
                
        # Chat area
        self.chat_frame = tk.Frame(chat_paned, bg=self.colors['bg'])
        chat_paned.add(self.chat_frame)
        
        # Default chat view
        self.show_empty_chat()
        
    def create_friend_button(self, parent, friend):
        """Create a friend button."""
        btn = tk.Frame(parent, bg=self.colors['bg_card'], padx=10, pady=10)
        btn.pack(fill="x", pady=5)
        btn.bind("<Button-1>", lambda e, f=friend: self.select_friend(f))
        
        # Status indicator
        status_color = self.colors['success'] if friend['last_login'] else self.colors['fg_secondary']
        status = tk.Canvas(btn, width=10, height=10, bg=self.colors['bg_card'],
                          highlightthickness=0)
        status.pack(side="left")
        status.create_oval(2, 2, 8, 8, fill=status_color, outline="")
        
        # Username
        name = tk.Label(btn, text=friend['username'],
                       font=("Segoe UI", 12),
                       bg=self.colors['bg_card'],
                       fg=self.colors['fg'])
        name.pack(side="left", padx=10)
        
        # Unread badge
        if friend['unread'] > 0:
            badge = tk.Label(btn, text=str(friend['unread']),
                           font=("Segoe UI", 9, "bold"),
                           bg=self.colors['danger'],
                           fg="white", padx=6, pady=1)
            badge.pack(side="right")
            
        # Make clickable
        for widget in [name]:
            widget.bind("<Button-1>", lambda e, f=friend: self.select_friend(f))
            
    def select_friend(self, friend):
        """Select a friend to chat with."""
        self.selected_friend = friend
        self.show_chat_with_friend(friend)
        
    def show_empty_chat(self):
        """Show empty chat state."""
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
            
        empty = tk.Frame(self.chat_frame, bg=self.colors['bg'])
        empty.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(empty, text="💬", font=("Segoe UI", 72),
                bg=self.colors['bg'],
                fg=self.colors['fg_secondary']).pack()
        
        tk.Label(empty, text="Select a friend to start chatting",
                font=("Segoe UI", 14),
                bg=self.colors['bg'],
                fg=self.colors['fg_secondary']).pack(pady=10)
                
    def show_chat_with_friend(self, friend):
        """Show chat interface with selected friend."""
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
            
        # Chat header
        header = tk.Frame(self.chat_frame, bg=self.colors['bg_secondary'],
                         height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        tk.Label(header, text=friend['username'],
                font=("Segoe UI", 14, "bold"),
                bg=self.colors['bg_secondary'],
                fg=self.colors['fg']).pack(side="left", padx=20, pady=15)
        
        # Messages area
        self.msg_canvas = tk.Canvas(self.chat_frame, bg=self.colors['bg'],
                                   highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.chat_frame, orient="vertical",
                                 command=self.msg_canvas.yview)
        
        self.msg_container = tk.Frame(self.msg_canvas, bg=self.colors['bg'])
        self.msg_canvas.create_window((0, 0), window=self.msg_container,
                                     anchor="nw", width=580)
        
        self.msg_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.msg_canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y")
        
        self.msg_container.bind("<Configure>",
                               lambda e: self.msg_canvas.configure(
                                   scrollregion=self.msg_canvas.bbox("all")))
        
        # Load messages
        self.load_messages(friend['user_id'])
        
        # Mark as read
        self.db.execute("""
            UPDATE messages SET is_read = 1 
            WHERE sender_id = ? AND receiver_id = ?
        """, (friend['user_id'], self.auth.current_user['user_id']))
        
        # Input area
        input_frame = tk.Frame(self.chat_frame, bg=self.colors['bg_secondary'],
                              height=60)
        input_frame.pack(fill="x", side="bottom")
        input_frame.pack_propagate(False)
        
        self.msg_entry = tk.Entry(input_frame, font=("Segoe UI", 12),
                                 bg=self.colors['bg_card'],
                                 fg=self.colors['fg'],
                                 relief="flat")
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.msg_entry.bind("<Return>", lambda e: self.send_message())
        
        ModernButton(input_frame, text="Send", command=self.send_message,
                    colors=self.colors, bg=self.colors['accent'],
                    width=80, height=35).pack(side="right", padx=10, pady=10)
        
        self.current_chat_friend = friend
        
    def load_messages(self, friend_id):
        """Load messages for current chat."""
        messages = self.db.fetch_all("""
            SELECT sender_id, content, sent_at
            FROM messages
            WHERE (sender_id = ? AND receiver_id = ?)
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY sent_at ASC
        """, (self.auth.current_user['user_id'], friend_id,
              friend_id, self.auth.current_user['user_id']))
        
        for msg in messages:
            self.add_message_bubble(msg)
            
    def add_message_bubble(self, msg):
        """Add a message bubble to chat."""
        is_me = msg['sender_id'] == self.auth.current_user['user_id']
        
        bubble_frame = tk.Frame(self.msg_container, bg=self.colors['bg'])
        bubble_frame.pack(fill="x", pady=5, padx=10)
        
        if is_me:
            bubble_frame.pack_configure(anchor="e")
            bg_color = self.colors['accent']
            fg_color = "white"
        else:
            bubble_frame.pack_configure(anchor="w")
            bg_color = self.colors['bg_card']
            fg_color = self.colors['fg']
            
        bubble = tk.Label(bubble_frame, text=msg['content'],
                         font=("Segoe UI", 11),
                         bg=bg_color, fg=fg_color,
                         wraplength=400, padx=15, pady=10,
                         justify="left")
        bubble.pack(side="right" if is_me else "left")
        
    def send_message(self):
        """Send a message."""
        content = self.msg_entry.get().strip()
        if not content or not self.selected_friend:
            return
            
        self.db.execute("""
            INSERT INTO messages (sender_id, receiver_id, content)
            VALUES (?, ?, ?)
        """, (self.auth.current_user['user_id'],
              self.selected_friend['user_id'], content))
              
        self.msg_entry.delete(0, "end")
        
        # Add to UI
        msg = {
            'sender_id': self.auth.current_user['user_id'],
            'content': content,
            'sent_at': datetime.now()
        }
        self.add_message_bubble(msg)
        
        # Scroll to bottom
        self.msg_canvas.update_idletasks()
        self.msg_canvas.yview_moveto(1.0)
        
    def add_friend(self):
        """Add a new friend."""
        username = simpledialog.askstring("Add Friend",
                                         "Enter username:",
                                         parent=self.root)
        if not username:
            return
            
        # Find user
        user = self.db.fetch_one("SELECT user_id FROM users WHERE username = ?",
                                (username.lower(),))
                                
        if not user:
            messagebox.showerror("Error", "User not found")
            return
            
        if user['user_id'] == self.auth.current_user['user_id']:
            messagebox.showerror("Error", "Cannot add yourself")
            return
            
        # Check if already friends
        existing = self.db.fetch_one("""
            SELECT * FROM friends 
            WHERE (user_id_1 = ? AND user_id_2 = ?)
               OR (user_id_1 = ? AND user_id_2 = ?)
        """, (self.auth.current_user['user_id'], user['user_id'],
              user['user_id'], self.auth.current_user['user_id']))
              
        if existing:
            messagebox.showinfo("Info", "Already friends or request pending")
            return
            
        # Add friend
        self.db.execute("""
            INSERT INTO friends (user_id_1, user_id_2, status)
            VALUES (?, ?, 'accepted')
        """, (self.auth.current_user['user_id'], user['user_id']))
        
        messagebox.showinfo("Success", f"Added {username} as friend!")
        self.show_chat_tab()
        
    def show_leaderboard_tab(self):
        """Show leaderboard."""
        self.clear_content()
        self.highlight_nav(2)
        
        # Header
        header = tk.Frame(self.content_area, bg=self.colors['bg'])
        header.pack(fill="x", pady=(0, 20))
        
        tk.Label(header, text="Global Leaderboard",
                font=("Segoe UI", 28, "bold"),
                bg=self.colors['bg'],
                fg=self.colors['fg']).pack(side="left")
        
        # Filter buttons
        filter_frame = tk.Frame(header, bg=self.colors['bg'])
        filter_frame.pack(side="right")
        
        filters = [("All", ""), ("Snake", "snake"), ("Tic Tac Toe", "tictactoe")]
        self.leaderboard_filter = ""
        
        for text, game_key in filters:
            btn = tk.Button(filter_frame, text=text,
                          font=("Segoe UI", 10),
                          bg=self.colors['accent'] if game_key == "" else self.colors['bg_card'],
                          fg="white" if game_key == "" else self.colors['fg'],
                          relief="flat", padx=15, pady=5,
                          command=lambda g=game_key: self.filter_leaderboard(g))
            btn.pack(side="left", padx=5)
            
        # Leaderboard table
        self.leaderboard_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        self.leaderboard_frame.pack(fill="both", expand=True)
        
        self.load_leaderboard()
        
    def filter_leaderboard(self, game_key):
        """Filter leaderboard by game."""
        self.leaderboard_filter = game_key
        self.load_leaderboard()
        
    def load_leaderboard(self):
        """Load leaderboard data."""
        for widget in self.leaderboard_frame.winfo_children():
            widget.destroy()
            
        # Headers
        headers = tk.Frame(self.leaderboard_frame, bg=self.colors['bg_secondary'],
                          height=50)
        headers.pack(fill="x")
        headers.pack_propagate(False)
        
        cols = [("Rank", 100), ("Player", 200), ("Game", 150), ("Score", 150)]
        for text, width in cols:
            tk.Label(headers, text=text, font=("Segoe UI", 12, "bold"),
                    bg=self.colors['bg_secondary'],
                    fg=self.colors['fg'], width=12).pack(side="left", padx=10, pady=10)
                    
        # Data
        if self.leaderboard_filter:
            scores = self.db.fetch_all("""
                SELECT u.username, g.name as game_name, s.score
                FROM scores s
                JOIN users u ON s.user_id = u.user_id
                JOIN games g ON s.game_key = g.game_key
                WHERE s.game_key = ?
                ORDER BY s.score DESC
                LIMIT 20
            """, (self.leaderboard_filter,))
        else:
            scores = self.db.fetch_all("""
                SELECT u.username, g.name as game_name, s.score
                FROM scores s
                JOIN users u ON s.user_id = u.user_id
                JOIN games g ON s.game_key = g.game_key
                ORDER BY s.score DESC
                LIMIT 20
            """)
            
        if not scores:
            tk.Label(self.leaderboard_frame, text="No scores yet",
                    font=("Segoe UI", 14),
                    bg=self.colors['bg'],
                    fg=self.colors['fg_secondary']).pack(pady=50)
            return
            
        for i, score in enumerate(scores, 1):
            row = tk.Frame(self.leaderboard_frame, bg=self.colors['bg_card'],
                          height=50)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)
            
            # Rank with medal
            rank_text = f"#{i}"
            if i == 1:
                rank_text = "🥇"
            elif i == 2:
                rank_text = "🥈"
            elif i == 3:
                rank_text = "🥉"
                
            tk.Label(row, text=rank_text, font=("Segoe UI", 14, "bold"),
                    bg=self.colors['bg_card'],
                    fg=self.colors['warning'] if i <= 3 else self.colors['fg'],
                    width=8).pack(side="left", padx=10, pady=10)
                    
            tk.Label(row, text=score['username'], font=("Segoe UI", 12),
                    bg=self.colors['bg_card'],
                    fg=self.colors['fg'], width=15).pack(side="left", padx=10, pady=10)
                    
            tk.Label(row, text=score['game_name'], font=("Segoe UI", 12),
                    bg=self.colors['bg_card'],
                    fg=self.colors['fg_secondary'], width=12).pack(side="left", padx=10, pady=10)
                    
            tk.Label(row, text=str(score['score']), font=("Segoe UI", 12, "bold"),
                    bg=self.colors['bg_card'],
                    fg=self.colors['accent'], width=10).pack(side="left", padx=10, pady=10)
                    
    def show_settings_tab(self):
        """Show settings panel."""
        self.clear_content()
        self.highlight_nav(3)
        
        # Header
        header = tk.Frame(self.content_area, bg=self.colors['bg'])
        header.pack(fill="x", pady=(0, 20))
        
        tk.Label(header, text="Settings",
                font=("Segoe UI", 28, "bold"),
                bg=self.colors['bg'],
                fg=self.colors['fg']).pack(side="left")
        
        # Settings container
        settings_frame = tk.Frame(self.content_area, bg=self.colors['bg'])
        settings_frame.pack(fill="both", expand=True)
        
        # About Me Section
        about_card = tk.Frame(settings_frame, bg=self.colors['bg_card'],
                             padx=30, pady=30)
        about_card.pack(fill="x", pady=10)
        
        tk.Label(about_card, text="👤 About Me",
                font=("Segoe UI", 18, "bold"),
                bg=self.colors['bg_card'],
                fg=self.colors['fg']).pack(anchor="w")
        
        about_text = """I am 15 years old, very interested in coding, programming, 
ethical hacking, computers, AI, and technology. I built this gaming platform 
to learn and practice software development skills."""
        
        tk.Label(about_card, text=about_text,
                font=("Segoe UI", 12),
                bg=self.colors['bg_card'],
                fg=self.colors['fg_secondary'],
                justify="left", wraplength=700).pack(anchor="w", pady=10)
        
        # Appearance settings
        appearance_card = tk.Frame(settings_frame, bg=self.colors['bg_card'],
                                  padx=30, pady=30)
        appearance_card.pack(fill="x", pady=10)
        
        tk.Label(appearance_card, text="🎨 Appearance",
                font=("Segoe UI", 18, "bold"),
                bg=self.colors['bg_card'],
                fg=self.colors['fg']).pack(anchor="w")
        
        # Theme toggle
        theme_frame = tk.Frame(appearance_card, bg=self.colors['bg_card'])
        theme_frame.pack(fill="x", pady=15)
        
        tk.Label(theme_frame, text="Theme",
                font=("Segoe UI", 12),
                bg=self.colors['bg_card'],
                fg=self.colors['fg']).pack(side="left")
        
        theme_var = tk.StringVar(value=self.current_theme)
        
        theme_switch = tk.Frame(theme_frame, bg=self.colors['bg_secondary'],
                               padx=5, pady=5)
        theme_switch.pack(side="right")
        
        dark_btn = tk.Button(theme_switch, text="🌙 Dark",
                            font=("Segoe UI", 10),
                            bg=self.colors['accent'] if self.current_theme == "dark" else self.colors['bg_card'],
                            fg="white" if self.current_theme == "dark" else self.colors['fg'],
                            relief="flat", padx=15, pady=5,
                            command=lambda: self.toggle_theme("dark"))
        dark_btn.pack(side="left", padx=2)
        
        light_btn = tk.Button(theme_switch, text="☀️ Light",
                             font=("Segoe UI", 10),
                             bg=self.colors['accent'] if self.current_theme == "light" else self.colors['bg_card'],
                             fg="white" if self.current_theme == "light" else self.colors['fg'],
                             relief="flat", padx=15, pady=5,
                             command=lambda: self.toggle_theme("light"))
        light_btn.pack(side="left", padx=2)
        
        # Audio settings
        audio_card = tk.Frame(settings_frame, bg=self.colors['bg_card'],
                             padx=30, pady=30)
        audio_card.pack(fill="x", pady=10)
        
        tk.Label(audio_card, text="🔊 Audio",
                font=("Segoe UI", 18, "bold"),
                bg=self.colors['bg_card'],
                fg=self.colors['fg']).pack(anchor="w")
        
        settings = self.auth.get_settings()
        
        # Sound toggle
        sound_frame = tk.Frame(audio_card, bg=self.colors['bg_card'])
        sound_frame.pack(fill="x", pady=15)
        
        tk.Label(sound_frame, text="Sound Effects",
                font=("Segoe UI", 12),
                bg=self.colors['bg_card'],
                fg=self.colors['fg']).pack(side="left")
        
        sound_var = tk.BooleanVar(value=settings.get('sound', True))
        sound_toggle = tk.Checkbutton(sound_frame, variable=sound_var,
                                     bg=self.colors['bg_card'],
                                     activebackground=self.colors['bg_card'],
                                     command=lambda: self.auth.update_settings('sound', sound_var.get()))
        sound_toggle.pack(side="right")
        
        # Notifications
        notif_frame = tk.Frame(audio_card, bg=self.colors['bg_card'])
        notif_frame.pack(fill="x", pady=15)
        
        tk.Label(notif_frame, text="Notifications",
                font=("Segoe UI", 12),
                bg=self.colors['bg_card'],
                fg=self.colors['fg']).pack(side="left")
        
        notif_var = tk.BooleanVar(value=settings.get('notifications', True))
        notif_toggle = tk.Checkbutton(notif_frame, variable=notif_var,
                                     bg=self.colors['bg_card'],
                                     activebackground=self.colors['bg_card'],
                                     command=lambda: self.auth.update_settings('notifications', notif_var.get()))
        notif_toggle.pack(side="right")
        
        # Account info
        account_card = tk.Frame(settings_frame, bg=self.colors['bg_card'],
                               padx=30, pady=30)
        account_card.pack(fill="x", pady=10)
        
        tk.Label(account_card, text="🔐 Account",
                font=("Segoe UI", 18, "bold"),
                bg=self.colors['bg_card'],
                fg=self.colors['fg']).pack(anchor="w")
        
        user = self.auth.current_user
        info_items = [
            ("Username", user['username']),
            ("Email", user['email']),
            ("Member Since", user['created_at'][:10]),
            ("Total Games", str(user['total_games_played'])),
            ("Total Score", str(user['total_score']))
        ]
        
        for label, value in info_items:
            row = tk.Frame(account_card, bg=self.colors['bg_card'])
            row.pack(fill="x", pady=5)
            
            tk.Label(row, text=label + ":",
                    font=("Segoe UI", 11),
                    bg=self.colors['bg_card'],
                    fg=self.colors['fg_secondary']).pack(side="left")
            
            tk.Label(row, text=value,
                    font=("Segoe UI", 11, "bold"),
                    bg=self.colors['bg_card'],
                    fg=self.colors['fg']).pack(side="right")
                    
    def toggle_theme(self, theme):
        """Toggle between light and dark theme."""
        self.current_theme = theme
        self.auth.update_settings('theme', theme)
        self.apply_theme()
        self.show_settings_tab()
        
    def highlight_nav(self, index):
        """Highlight active navigation button."""
        for i, (btn, _) in enumerate(self.nav_buttons):
            if i == index:
                btn.config(bg=self.colors['bg_card'],
                          fg=self.colors['accent'])
            else:
                btn.config(bg=self.colors['bg_secondary'],
                          fg=self.colors['fg_secondary'])
                          
    def clear_content(self):
        """Clear content area."""
        if self.content_area:
            for widget in self.content_area.winfo_children():
                widget.destroy()
                
    def refresh_dashboard(self):
        """Refresh dashboard after game."""
        self.auth.refresh_user_data()
        self.show_dashboard()


def main():
    """Main entry point."""
    root = tk.Tk()
    app = ArcadiaHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()