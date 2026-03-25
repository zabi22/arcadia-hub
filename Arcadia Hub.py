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

# --- SECURITY CHECK ---
try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    print("⚠️ WARNING: 'bcrypt' module not found. Falling back to SHA-256. Run 'pip install bcrypt' for production security.")
    import hashlib

# --- CONFIGURATION & CONSTANTS ---
DB_NAME = 'gaming_app.db'
THEME_COLORS = {
    "dark": {
        "bg": "#1a1a1a", "fg": "#ecf0f1", "accent": "#3498db", "secondary": "#2c3e50",
        "success": "#2ecc71", "warning": "#f1c40f", "danger": "#e74c3c", "text": "white"
    },
    "light": {
        "bg": "#f5f6fa", "fg": "#2c3e50", "accent": "#2980b9", "secondary": "#dfe6e9",
        "success": "#27ae60", "warning": "#f39c12", "danger": "#c0392b", "text": "black"
    }
}

# --- DATABASE MANAGER ---
class DatabaseManager:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.conn.row_factory = sqlite3.Row  # Access columns by name
        self.cursor = self.conn.cursor()
        self._init_db()
        self._run_migrations()

    def _init_db(self):
        """Initialize database tables with modern schema."""
        tables = [
            '''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login DATE,
                streak INTEGER DEFAULT 0,
                coins INTEGER DEFAULT 0,
                avatar_config TEXT,
                settings_config TEXT
            )''',
            '''CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                category TEXT,
                play_count INTEGER DEFAULT 0
            )''',
            '''CREATE TABLE IF NOT EXISTS scores (
                score_id INTEGER PRIMARY KEY,
                user_id INTEGER,
                game_name TEXT,
                score INTEGER,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )''',
            '''CREATE TABLE IF NOT EXISTS friends (
                friendship_id INTEGER PRIMARY KEY,
                user_id_1 INTEGER,
                user_id_2 INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''',
            '''CREATE TABLE IF NOT EXISTS messages (
                msg_id INTEGER PRIMARY KEY,
                sender_id INTEGER,
                receiver_id INTEGER,
                content TEXT,
                is_read INTEGER DEFAULT 0,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )'''
        ]
        try:
            for table in tables:
                self.cursor.execute(table)
            self.conn.commit()
            print("✓ Database tables verified")
        except Exception as e:
            print(f"✗ Database Init Error: {e}")

    def _run_migrations(self):
        """Handle schema updates safely."""
        try:
            # Check if columns exist, if not add them
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [info[1] for info in self.cursor.fetchall()]
            
            # --- CRITICAL FIX FOR PASSWORD_HASH MISSING ---
            # If the old table exists without password_hash (likely named 'password'), we need to migrate or rename
            if 'password' in columns and 'password_hash' not in columns:
                 print("⚠️ Migrating 'password' column to 'password_hash'...")
                 self.cursor.execute("ALTER TABLE users RENAME COLUMN password TO password_hash")

            # Check again after potential rename
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [info[1] for info in self.cursor.fetchall()]

            if 'coins' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN coins INTEGER DEFAULT 0")
            if 'streak' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN streak INTEGER DEFAULT 0")
            if 'last_login' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN last_login DATE")
            if 'settings_config' not in columns:
                self.cursor.execute("ALTER TABLE users ADD COLUMN settings_config TEXT")
            
            # If for some reason password_hash still doesn't exist (e.g. fresh partial table), add it
            if 'password_hash' not in columns:
                 # This might fail if rows exist without default, but for SQLite add column it's usually fine if NULL allowed or default provided.
                 # However, password_hash is NOT NULL in create table. 
                 # Since we can't easily add NOT NULL column to populated table without default, we'll try adding it as nullable first for safety if needed,
                 # but for now let's assume if it's missing entirely on a 'users' table, we might need to recreate or alter carefully.
                 # A safe bet for a dev env is to just add it.
                 try:
                    self.cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")
                 except Exception as ex:
                     print(f"Error adding password_hash: {ex}")

            self.conn.commit()
        except Exception as e:
            print(f"⚠️ Migration warning: {e}")

    def get_connection(self):
        return self.conn

# --- AUTHENTICATION SYSTEM ---
class AuthSystem:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.current_user = None

    def register(self, username, email, password):
        if not all([username, email, password]):
            return False, "All fields are required."
        
        if len(password) < 6:
            return False, "Password must be at least 6 characters."
        
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return False, "Invalid email format."

        try:
            if HAS_BCRYPT:
                salt = bcrypt.gensalt()
                hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            else:
                hashed = hashlib.sha256(password.encode()).hexdigest().encode()

            cursor = self.db.get_connection().cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, coins, settings_config) VALUES (?, ?, ?, ?, ?)",
                (username, email, hashed, 100, json.dumps({'theme': 'dark', 'sound': True}))
            )
            self.db.get_connection().commit()
            return True, "Registration successful!"
        except sqlite3.IntegrityError:
            return False, "Username or Email already exists."
        except Exception as e:
            traceback.print_exc() # Print full error to console for debugging
            return False, f"Error: {str(e)}"

    def login(self, username, password):
        cursor = self.db.get_connection().cursor()
        
        # We need to handle cases where the DB might have 'password' instead of 'password_hash' if migration failed silently
        # But our migration script handles rename.
        try:
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
        except sqlite3.OperationalError:
             return False, "Database Schema Error. Please restart the app to run migrations."

        if user:
            # Handle potential schema mismatch if migration added column but data is in old column (unlikely with rename)
            # or if we are reading from a row that has the old 'password' key in the row factory if not refreshed
            
            # Check if password_hash exists in the row keys
            if 'password_hash' in user.keys():
                stored_hash = user['password_hash']
            elif 'password' in user.keys():
                stored_hash = user['password']
            else:
                return False, "Critical: Password column missing."

            if isinstance(stored_hash, str):
                stored_hash = stored_hash.encode('utf-8')
            
            valid = False
            if HAS_BCRYPT:
                try:
                    # If stored hash is not a valid bcrypt hash (e.g. old SHA256), this raises error
                    valid = bcrypt.checkpw(password.encode('utf-8'), stored_hash)
                except ValueError:
                    # Fallback for old SHA256 passwords during migration
                     valid = hashlib.sha256(password.encode()).hexdigest().encode() == stored_hash
            else:
                valid = hashlib.sha256(password.encode()).hexdigest().encode() == stored_hash

            if valid:
                self.current_user = dict(user)
                self._process_login_rewards()
                return True, "Login successful!"
        
        return False, "Invalid credentials."

    def _process_login_rewards(self):
        """Handle daily streaks and rewards."""
        user_id = self.current_user['user_id']
        today = datetime.now().date()
        last_login_str = self.current_user['last_login']
        
        conn = self.db.get_connection()
        cursor = conn.cursor()

        new_streak = 1
        reward = 0
        message = ""

        if last_login_str:
            last_login = datetime.strptime(last_login_str, "%Y-%m-%d").date()
            diff = (today - last_login).days
            
            if diff == 0:
                # Already logged in today
                return
            elif diff == 1:
                # Consecutive day
                new_streak = self.current_user['streak'] + 1
                reward = min(10 + (new_streak * 5), 100)
                message = f"🔥 Streak maintained! {new_streak} days. +{reward} coins!"
            else:
                # Streak broken
                new_streak = 1
                reward = 10
                message = f"Streak reset. +{reward} coins."
        else:
            reward = 50
            message = "Welcome! +50 coins bonus."

        # Update DB
        cursor.execute(
            "UPDATE users SET last_login = ?, streak = ?, coins = coins + ? WHERE user_id = ?",
            (today.strftime("%Y-%m-%d"), new_streak, reward, user_id)
        )
        conn.commit()
        
        # Update local session
        self.current_user['streak'] = new_streak
        self.current_user['coins'] += reward
        self.daily_reward_msg = message

    def update_settings(self, key, value):
        if not self.current_user: return
        settings = json.loads(self.current_user['settings_config'] or '{}')
        settings[key] = value
        
        conn = self.db.get_connection()
        conn.execute("UPDATE users SET settings_config = ? WHERE user_id = ?", 
                     (json.dumps(settings), self.current_user['user_id']))
        conn.commit()
        self.current_user['settings_config'] = json.dumps(settings)

# --- GAME LOGIC ---
class GameEngine:
    """Base class for all games to ensure scalability."""
    def __init__(self, root, user_id, db, on_close):
        self.root = tk.Toplevel(root)
        self.user_id = user_id
        self.db = db
        self.on_close = on_close
        self.score = 0
        self.game_name = "Unknown"
        self.root.protocol("WM_DELETE_WINDOW", self.close_game)
        
        # Determine theme
        cursor = db.get_connection().cursor()
        cursor.execute("SELECT settings_config FROM users WHERE user_id = ?", (user_id,))
        res = cursor.fetchone()
        settings = json.loads(res['settings_config']) if res and res['settings_config'] else {}
        self.is_dark = settings.get('theme', 'dark') == 'dark'
        self.colors = THEME_COLORS['dark'] if self.is_dark else THEME_COLORS['light']
        
        self.root.configure(bg=self.colors['bg'])

    def save_score(self):
        conn = self.db.get_connection()
        conn.execute("INSERT INTO scores (user_id, game_name, score) VALUES (?, ?, ?)",
                     (self.user_id, self.game_name, self.score))
        conn.execute("UPDATE users SET coins = coins + ? WHERE user_id = ?", 
                     (int(self.score / 10), self.user_id)) # 1 coin per 10 points
        conn.commit()
        messagebox.showinfo("Game Over", f"Score saved: {self.score}\nCoins earned: {int(self.score/10)}")

    def close_game(self):
        self.root.destroy()
        if self.on_close:
            self.on_close()

# Specific Games
class SnakeGame(GameEngine):
    def __init__(self, root, user_id, db, on_close):
        super().__init__(root, user_id, db, on_close)
        self.game_name = "Snake"
        self.root.title("🐍 Snake Arcade")
        self.width = 600
        self.height = 400
        self.cell_size = 20
        
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, bg=self.colors['bg'], highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)
        
        self.snake = [(100, 100), (80, 100), (60, 100)]
        self.direction = "Right"
        self.food = self.spawn_food()
        self.running = True
        
        self.root.bind("<Key>", self.change_direction)
        self.game_loop()

    def spawn_food(self):
        x = random.randint(0, (self.width - self.cell_size) // self.cell_size) * self.cell_size
        y = random.randint(0, (self.height - self.cell_size) // self.cell_size) * self.cell_size
        return (x, y)

    def change_direction(self, event):
        new_dir = event.keysym
        all_dirs = {"Left", "Right", "Up", "Down"}
        opposites = ({"Left", "Right"}, {"Up", "Down"})
        
        if new_dir in all_dirs:
            if {new_dir, self.direction} not in opposites:
                self.direction = new_dir

    def game_loop(self):
        if not self.running: return

        head_x, head_y = self.snake[0]
        if self.direction == "Left": head_x -= self.cell_size
        elif self.direction == "Right": head_x += self.cell_size
        elif self.direction == "Up": head_y -= self.cell_size
        elif self.direction == "Down": head_y += self.cell_size

        new_head = (head_x, head_y)

        # Collision Check
        if (head_x < 0 or head_x >= self.width or head_y < 0 or head_y >= self.height or new_head in self.snake):
            self.running = False
            self.save_score()
            return

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 10
            self.food = self.spawn_food()
        else:
            self.snake.pop()

        self.draw()
        self.root.after(100, self.game_loop)

    def draw(self):
        self.canvas.delete("all")
        self.canvas.create_rectangle(self.food[0], self.food[1], self.food[0]+self.cell_size, self.food[1]+self.cell_size, fill=self.colors['danger'])
        
        for x, y in self.snake:
            self.canvas.create_rectangle(x, y, x+self.cell_size, y+self.cell_size, fill=self.colors['success'])
            
        self.canvas.create_text(50, 20, text=f"Score: {self.score}", fill=self.colors['text'], font=("Arial", 14))

class TicTacToe(GameEngine):
    def __init__(self, root, user_id, db, on_close):
        super().__init__(root, user_id, db, on_close)
        self.game_name = "Tic Tac Toe"
        self.root.title("Tic Tac Toe")
        self.turn = 'X'
        self.board = [""] * 9
        self.buttons = []
        
        frame = tk.Frame(self.root, bg=self.colors['bg'])
        frame.pack(padx=20, pady=20)
        
        for i in range(9):
            btn = tk.Button(frame, text="", font=("Arial", 24), width=5, height=2,
                            bg=self.colors['secondary'], fg=self.colors['text'],
                            command=lambda i=i: self.click(i))
            btn.grid(row=i//3, column=i%3, padx=5, pady=5)
            self.buttons.append(btn)

    def click(self, index):
        if self.board[index] == "" and self.turn == 'X':
            self.board[index] = 'X'
            self.buttons[index].config(text='X', fg=self.colors['accent'])
            if not self.check_win():
                self.root.after(500, self.computer_move)

    def computer_move(self):
        available = [i for i, x in enumerate(self.board) if x == ""]
        if available:
            move = random.choice(available)
            self.board[move] = 'O'
            self.buttons[move].config(text='O', fg=self.colors['danger'])
            self.check_win()

    def check_win(self):
        wins = [(0,1,2), (3,4,5), (6,7,8), (0,3,6), (1,4,7), (2,5,8), (0,4,8), (2,4,6)]
        for a, b, c in wins:
            if self.board[a] == self.board[b] == self.board[c] and self.board[a] != "":
                winner = self.board[a]
                if winner == 'X':
                    self.score = 50
                    messagebox.showinfo("Result", "You Won!")
                else:
                    messagebox.showinfo("Result", "Computer Won!")
                self.save_score()
                self.close_game()
                return True
        if "" not in self.board:
            messagebox.showinfo("Result", "Draw!")
            self.close_game()
            return True
        return False

# --- UI COMPONENTS ---
class ModernButton(tk.Button):
    def __init__(self, master, **kw):
        bg_color = kw.pop('bg', '#3498db')
        fg_color = kw.pop('fg', 'white')
        super().__init__(master, **kw)
        self.config(bg=bg_color, fg=fg_color, font=("Segoe UI", 11, "bold"), 
                   relief="flat", activebackground=bg_color, activeforeground=fg_color,
                   padx=20, pady=10, cursor="hand2")
        self.bind("<Enter>", lambda e: self.config(bg=self.adjust_color(bg_color, -20)))
        self.bind("<Leave>", lambda e: self.config(bg=bg_color))

    def adjust_color(self, color, amount):
        # Simple placeholder for color darkening
        return color 

class ArcadiaHubApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Arcadia Hub | Professional Gaming Platform")
        self.root.geometry("1000x700")
        
        self.db_manager = DatabaseManager()
        self.auth = AuthSystem(self.db_manager)
        
        self.current_theme = "dark"
        self.colors = THEME_COLORS[self.current_theme]
        
        self.root.configure(bg=self.colors['bg'])
        self.main_container = tk.Frame(self.root, bg=self.colors['bg'])
        self.main_container.pack(fill="both", expand=True)
        
        self.show_login()

    def apply_theme(self):
        self.colors = THEME_COLORS[self.current_theme]
        self.root.configure(bg=self.colors['bg'])
        # Recursively update widgets would go here in a full framework
        
    def clear_screen(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_screen()
        frame = tk.Frame(self.main_container, bg=self.colors['secondary'], padx=40, pady=40)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="ARCADIA HUB", font=("Arial", 28, "bold"), 
                 bg=self.colors['secondary'], fg=self.colors['accent']).pack(pady=10)
        
        tk.Label(frame, text="Username", bg=self.colors['secondary'], fg=self.colors['text']).pack(anchor="w")
        user_entry = tk.Entry(frame, width=30, font=("Arial", 12))
        user_entry.pack(pady=5)

        tk.Label(frame, text="Password", bg=self.colors['secondary'], fg=self.colors['text']).pack(anchor="w")
        pass_entry = tk.Entry(frame, width=30, show="•", font=("Arial", 12))
        pass_entry.pack(pady=5)

        def attempt_login():
            success, msg = self.auth.login(user_entry.get(), pass_entry.get())
            if success:
                if hasattr(self.auth, 'daily_reward_msg'):
                    messagebox.showinfo("Daily Reward", self.auth.daily_reward_msg)
                
                # Load user theme preference
                settings = json.loads(self.auth.current_user['settings_config'] or '{}')
                self.current_theme = settings.get('theme', 'dark')
                self.apply_theme()
                self.show_dashboard()
            else:
                messagebox.showerror("Login Failed", msg)

        ModernButton(frame, text="LOGIN", command=attempt_login, bg=self.colors['accent']).pack(pady=20, fill='x')
        tk.Button(frame, text="Create Account", command=self.show_register, 
                  bg=self.colors['secondary'], fg=self.colors['text'], relief="flat").pack()

    def show_register(self):
        self.clear_screen()
        frame = tk.Frame(self.main_container, bg=self.colors['secondary'], padx=40, pady=40)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="CREATE ACCOUNT", font=("Arial", 24, "bold"), 
                 bg=self.colors['secondary'], fg=self.colors['success']).pack(pady=10)

        entries = {}
        for field in ["Username", "Email", "Password"]:
            tk.Label(frame, text=field, bg=self.colors['secondary'], fg=self.colors['text']).pack(anchor="w")
            e = tk.Entry(frame, width=30, font=("Arial", 12), show="•" if field == "Password" else "")
            e.pack(pady=5)
            entries[field] = e

        def attempt_register():
            success, msg = self.auth.register(
                entries["Username"].get(), 
                entries["Email"].get(), 
                entries["Password"].get()
            )
            if success:
                messagebox.showinfo("Success", msg)
                self.show_login()
            else:
                messagebox.showerror("Error", msg)

        ModernButton(frame, text="REGISTER", command=attempt_register, bg=self.colors['success']).pack(pady=20, fill='x')
        tk.Button(frame, text="Back to Login", command=self.show_login, 
                  bg=self.colors['secondary'], fg=self.colors['text'], relief="flat").pack()

    def show_dashboard(self):
        self.clear_screen()
        user = self.auth.current_user
        
        # --- Sidebar ---
        sidebar = tk.Frame(self.main_container, bg=self.colors['secondary'], width=250)
        sidebar.pack(side="left", fill="y")
        
        # Profile Section
        tk.Label(sidebar, text="👤", font=("Arial", 40), bg=self.colors['secondary'], fg=self.colors['text']).pack(pady=20)
        tk.Label(sidebar, text=user['username'], font=("Arial", 16, "bold"), 
                 bg=self.colors['secondary'], fg=self.colors['text']).pack()
        tk.Label(sidebar, text=f"💰 {user['coins']} Coins", font=("Arial", 12), 
                 bg=self.colors['secondary'], fg=self.colors['warning']).pack(pady=5)
        
        # Navigation
        nav_items = [
            ("🎮 Games", self.show_games_tab),
            ("💬 Chat", self.show_chat_tab),
            ("🏆 Leaderboard", self.show_leaderboard_tab),
            ("⚙️ Settings", self.show_settings_tab),
            ("🚪 Logout", self.show_login)
        ]
        
        for text, cmd in nav_items:
            btn = tk.Button(sidebar, text=text, command=cmd, 
                            bg=self.colors['secondary'], fg=self.colors['text'],
                            font=("Arial", 12), relief="flat", anchor="w", padx=20)
            btn.pack(fill="x", pady=2)

        # --- Content Area ---
        self.content_area = tk.Frame(self.main_container, bg=self.colors['bg'])
        self.content_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        
        self.show_games_tab()

    def show_games_tab(self):
        for w in self.content_area.winfo_children(): w.destroy()
        
        tk.Label(self.content_area, text="GAME LIBRARY", font=("Arial", 24, "bold"), 
                 bg=self.colors['bg'], fg=self.colors['text']).pack(anchor="w", pady=10)

        games_grid = tk.Frame(self.content_area, bg=self.colors['bg'])
        games_grid.pack(fill="both", expand=True)

        games = [
            ("Snake Arcade", "🐍", "#2ecc71", lambda: SnakeGame(self.root, self.auth.current_user['user_id'], self.db_manager, self.refresh_stats)),
            ("Tic Tac Toe", "❌⭕", "#3498db", lambda: TicTacToe(self.root, self.auth.current_user['user_id'], self.db_manager, self.refresh_stats)),
            ("2048 (Soon)", "🔢", "#f1c40f", lambda: messagebox.showinfo("Info", "Coming soon in update 1.1")),
            ("Trivia (Soon)", "❓", "#9b59b6", lambda: messagebox.showinfo("Info", "Coming soon in update 1.1"))
        ]

        for i, (name, icon, color, cmd) in enumerate(games):
            card = tk.Frame(games_grid, bg=self.colors['secondary'], width=200, height=150)
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
            card.pack_propagate(False)
            
            tk.Label(card, text=icon, font=("Arial", 30), bg=self.colors['secondary'], fg=color).pack(pady=20)
            tk.Label(card, text=name, font=("Arial", 14, "bold"), bg=self.colors['secondary'], fg=self.colors['text']).pack()
            tk.Button(card, text="PLAY NOW", command=cmd, bg=color, fg="white", relief="flat").pack(pady=10)

    def show_chat_tab(self):
        for w in self.content_area.winfo_children(): w.destroy()
        
        tk.Label(self.content_area, text="FRIENDS & CHAT", font=("Arial", 24, "bold"), 
                 bg=self.colors['bg'], fg=self.colors['text']).pack(anchor="w", pady=10)
        
        # Basic implementation of friend list + chat area
        paned = tk.PanedWindow(self.content_area, orient="horizontal", bg=self.colors['bg'])
        paned.pack(fill="both", expand=True)
        
        friends_frame = tk.Frame(paned, bg=self.colors['secondary'], width=200)
        chat_frame = tk.Frame(paned, bg=self.colors['bg'])
        
        paned.add(friends_frame)
        paned.add(chat_frame)
        
        # Add friend
        def add_friend():
            target = simpledialog.askstring("Add Friend", "Enter username:")
            if target:
                cursor = self.db_manager.get_connection().cursor()
                cursor.execute("SELECT user_id FROM users WHERE username = ?", (target,))
                res = cursor.fetchone()
                if res:
                    try:
                        cursor.execute("INSERT INTO friends (user_id_1, user_id_2, status) VALUES (?, ?, 'accepted')", 
                                     (self.auth.current_user['user_id'], res['user_id']))
                        self.db_manager.get_connection().commit()
                        self.show_chat_tab()
                    except:
                        messagebox.showinfo("Info", "Already friends or error.")
                else:
                    messagebox.showerror("Error", "User not found")

        tk.Button(friends_frame, text="+ Add Friend", command=add_friend, bg=self.colors['success'], fg="white").pack(fill="x")
        
        # Load friends
        cursor = self.db_manager.get_connection().cursor()
        cursor.execute("""
            SELECT u.username, u.user_id FROM users u 
            JOIN friends f ON u.user_id = f.user_id_2 
            WHERE f.user_id_1 = ?
        """, (self.auth.current_user['user_id'],))
        friends = cursor.fetchall()
        
        self.selected_friend_id = None
        
        def select_friend(fid, name):
            self.selected_friend_id = fid
            chat_label.config(text=f"Chat with {name}")
            load_messages(fid)

        for f in friends:
            tk.Button(friends_frame, text=f['username'], 
                      command=lambda id=f['user_id'], n=f['username']: select_friend(id, n),
                      bg=self.colors['secondary'], fg=self.colors['text'], relief="flat", anchor="w").pack(fill="x", padx=5, pady=2)

        # Chat Area
        chat_label = tk.Label(chat_frame, text="Select a friend", font=("Arial", 14), bg=self.colors['bg'], fg=self.colors['text'])
        chat_label.pack(pady=10)
        
        msg_area = tk.Text(chat_frame, bg="white", height=15, state="disabled")
        msg_area.pack(fill="both", expand=True, padx=10)
        
        input_frame = tk.Frame(chat_frame, bg=self.colors['bg'])
        input_frame.pack(fill="x", padx=10, pady=10)
        
        msg_entry = tk.Entry(input_frame)
        msg_entry.pack(side="left", fill="x", expand=True)
        
        def send_msg():
            if self.selected_friend_id and msg_entry.get():
                conn = self.db_manager.get_connection()
                conn.execute("INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?)",
                             (self.auth.current_user['user_id'], self.selected_friend_id, msg_entry.get()))
                conn.commit()
                msg_entry.delete(0, "end")
                load_messages(self.selected_friend_id)

        tk.Button(input_frame, text="Send", command=send_msg, bg=self.colors['accent'], fg="white").pack(side="right")

        def load_messages(fid):
            msg_area.config(state="normal")
            msg_area.delete(1.0, "end")
            
            cursor = self.db_manager.get_connection().cursor()
            cursor.execute("""
                SELECT sender_id, content FROM messages 
                WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
                ORDER BY sent_at ASC
            """, (self.auth.current_user['user_id'], fid, fid, self.auth.current_user['user_id']))
            
            msgs = cursor.fetchall()
            for m in msgs:
                prefix = "You: " if m['sender_id'] == self.auth.current_user['user_id'] else "Friend: "
                msg_area.insert("end", prefix + m['content'] + "\n")
            
            msg_area.config(state="disabled")
            msg_area.see("end")

    def show_leaderboard_tab(self):
        for w in self.content_area.winfo_children(): w.destroy()
        tk.Label(self.content_area, text="GLOBAL LEADERBOARD", font=("Arial", 24, "bold"), 
                 bg=self.colors['bg'], fg=self.colors['text']).pack(pady=10)
        
        tree = ttk.Treeview(self.content_area, columns=("Rank", "User", "Game", "Score"), show="headings")
        tree.heading("Rank", text="Rank")
        tree.heading("User", text="User")
        tree.heading("Game", text="Game")
        tree.heading("Score", text="Score")
        tree.pack(fill="both", expand=True)
        
        cursor = self.db_manager.get_connection().cursor()
        cursor.execute("""
            SELECT u.username, s.game_name, s.score 
            FROM scores s JOIN users u ON s.user_id = u.user_id 
            ORDER BY s.score DESC LIMIT 20
        """)
        for i, row in enumerate(cursor.fetchall(), 1):
            tree.insert("", "end", values=(i, row['username'], row['game_name'], row['score']))

    def show_settings_tab(self):
        for w in self.content_area.winfo_children(): w.destroy()
        tk.Label(self.content_area, text="SETTINGS", font=("Arial", 24, "bold"), 
                 bg=self.colors['bg'], fg=self.colors['text']).pack(pady=10)
        
        # Theme Toggle
        def toggle_theme():
            new_theme = "light" if self.current_theme == "dark" else "dark"
            self.auth.update_settings("theme", new_theme)
            self.current_theme = new_theme
            self.apply_theme()
            messagebox.showinfo("Theme", "Theme updated. Please restart app to fully apply visual changes.")
            self.show_dashboard() # Refresh UI

        tk.Button(self.content_area, text=f"Toggle Theme (Current: {self.current_theme})", 
                  command=toggle_theme, font=("Arial", 12)).pack(pady=10)
        
        tk.Label(self.content_area, text="Control Bindings (Coming Soon)", bg=self.colors['bg'], fg=self.colors['text']).pack(pady=20)

    def refresh_stats(self):
        # Callback when a game closes to refresh coin count etc
        cursor = self.db_manager.get_connection().cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (self.auth.current_user['user_id'],))
        self.auth.current_user = dict(cursor.fetchone())
        self.show_dashboard()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArcadiaHubApp(root)
    root.mainloop()
