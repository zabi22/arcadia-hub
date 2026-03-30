import sqlite3
from datetime import datetime, timedelta
import json
import traceback
from typing import Dict, List, Optional

DB_NAME = 'gaming_app.db'

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
    """Database manager for web application."""
    
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
