import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import hashlib
import random
import re
import traceback



class Database:
    def __init__(self):
        try:
            self.conn = sqlite3.connect('gaming_app.db')
            self.cursor = self.conn.cursor()
            self.create_tables()
            print("✓ Database initialized successfully")
        except Exception as e:
            print(f"✗ Database error: {e}")
            traceback.print_exc()

    def create_tables(self):
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    created_date TEXT,
                    avatar_color TEXT DEFAULT '#3498db'
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS progress (
                    progress_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    game_name TEXT,
                    score INTEGER,
                    level INTEGER,
                    last_played TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS friends (
                    friend_id INTEGER PRIMARY KEY,
                    user_id_1 INTEGER,
                    user_id_2 INTEGER,
                    status TEXT DEFAULT 'pending',
                    requested_date TEXT,
                    FOREIGN KEY(user_id_1) REFERENCES users(user_id),
                    FOREIGN KEY(user_id_2) REFERENCES users(user_id)
                )
            ''')

            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS leaderboard (
                    leaderboard_id INTEGER PRIMARY KEY,
                    user_id INTEGER,
                    game_name TEXT,
                    score INTEGER,
                    date_achieved TEXT,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            ''')

            self.conn.commit()
            print("✓ Database tables created")
        except Exception as e:
            print(f"✗ Table creation error: {e}")
            traceback.print_exc()

    def register_user(self, username, email, password):
        try:

            if not username or not email or not password:
                return False, "All fields are required"

            username = username.strip()
            email = email.strip()

            if len(username) < 3:
                return False, "Username must be at least 3 characters"

            if len(password) < 6:
                return False, "Password must be at least 6 characters"


            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                return False, "Invalid email format"

            hashed = hashlib.sha256(password.encode()).hexdigest()
            avatar_colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
            selected_color = random.choice(avatar_colors)

            self.cursor.execute(
                'INSERT INTO users (username, email, password, created_date, avatar_color) VALUES (?, ?, ?, ?, ?)',
                (username, email, hashed, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), selected_color)
            )
            self.conn.commit()
            print(f"✓ User registered: {username}")
            return True, "Registration successful! Please login."

        except sqlite3.IntegrityError as e:
            print(f"✗ Integrity error: {e}")
            if 'username' in str(e).lower():
                return False, "Username already exists"
            elif 'email' in str(e).lower():
                return False, "Email already registered"
            else:
                return False, "User already exists"
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            traceback.print_exc()
            return False, f"Registration failed: {str(e)}"

    def login_user(self, username, password):
        try:
            if not username or not password:
                return None

            username = username.strip()
            hashed = hashlib.sha256(password.encode()).hexdigest()

            self.cursor.execute(
                'SELECT user_id, avatar_color FROM users WHERE username = ? AND password = ?',
                (username, hashed)
            )
            result = self.cursor.fetchone()

            if result:
                print(f"✓ User logged in: {username}")
            else:
                print(f"✗ Login failed for: {username}")

            return result
        except Exception as e:
            print(f"✗ Login error: {e}")
            traceback.print_exc()
            return None

    def get_user_id_by_username(self, username):
        try:
            self.cursor.execute('SELECT user_id FROM users WHERE username = ?', (username.strip(),))
            result = self.cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            print(f"✗ Error getting user ID: {e}")
            return None

    def save_progress(self, user_id, game_name, score, level):
        try:
            self.cursor.execute(
                'INSERT INTO progress (user_id, game_name, score, level, last_played) VALUES (?, ?, ?, ?, ?)',
                (user_id, game_name, score, level, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            self.conn.commit()
        except Exception as e:
            print(f"✗ Error saving progress: {e}")

    def save_leaderboard(self, user_id, game_name, score):
        try:
            self.cursor.execute(
                'INSERT INTO leaderboard (user_id, game_name, score, date_achieved) VALUES (?, ?, ?, ?)',
                (user_id, game_name, score, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            self.conn.commit()
        except Exception as e:
            print(f"✗ Error saving leaderboard: {e}")

    def get_leaderboard(self, game_name, limit=10):
        try:
            self.cursor.execute(
                'SELECT u.username, l.score, l.date_achieved FROM leaderboard l JOIN users u ON l.user_id = u.user_id WHERE l.game_name = ? ORDER BY l.score DESC LIMIT ?',
                (game_name, limit)
            )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"✗ Error getting leaderboard: {e}")
            return []

    def get_progress(self, user_id):
        try:
            self.cursor.execute(
                'SELECT game_name, score, level, last_played FROM progress WHERE user_id = ?',
                (user_id,)
            )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"✗ Error getting progress: {e}")
            return []

    def send_friend_request(self, user_id_1, user_id_2):
        try:
            self.cursor.execute(
                'INSERT INTO friends (user_id_1, user_id_2, status, requested_date) VALUES (?, ?, ?, ?)',
                (user_id_1, user_id_2, 'pending', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"✗ Error sending friend request: {e}")
            return False

    def get_pending_requests(self, user_id):
        try:
            self.cursor.execute(
                'SELECT u.username, u.user_id FROM users u JOIN friends f ON u.user_id = f.user_id_1 WHERE f.user_id_2 = ? AND f.status = "pending"',
                (user_id,)
            )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"✗ Error getting pending requests: {e}")
            return []

    def accept_friend_request(self, user_id_1, user_id_2):
        try:
            self.cursor.execute(
                'UPDATE friends SET status = "accepted" WHERE user_id_1 = ? AND user_id_2 = ?',
                (user_id_1, user_id_2)
            )
            self.conn.commit()
        except Exception as e:
            print(f"✗ Error accepting friend request: {e}")

    def reject_friend_request(self, user_id_1, user_id_2):
        try:
            self.cursor.execute(
                'DELETE FROM friends WHERE user_id_1 = ? AND user_id_2 = ?',
                (user_id_1, user_id_2)
            )
            self.conn.commit()
        except Exception as e:
            print(f"✗ Error rejecting friend request: {e}")

    def get_friends(self, user_id):
        try:
            self.cursor.execute(
                'SELECT u.username, u.user_id FROM users u JOIN friends f ON u.user_id = f.user_id_2 WHERE f.user_id_1 = ? AND f.status = "accepted"',
                (user_id,)
            )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"✗ Error getting friends: {e}")
            return []

    def get_all_users(self):
        try:
            self.cursor.execute('SELECT username, user_id FROM users')
            return self.cursor.fetchall()
        except Exception as e:
            print(f"✗ Error getting all users: {e}")
            return []


#Games
class TicTacToe:
    def __init__(self, root, user_id, db, opponent_id=None):
        self.user_id = user_id
        self.opponent_id = opponent_id
        self.db = db
        self.window = tk.Toplevel(root)
        self.window.title("Tic Tac Toe")
        self.window.configure(bg="#1a1a1a")
        self.board = [''] * 9
        self.current_player = 'X'
        self.score = 0
        self.buttons = []
        self.x_wins = 0
        self.o_wins = 0

        self.create_board()

    def create_board(self):
        title = tk.Label(self.window, text="Tic Tac Toe", font=("Arial", 20, "bold"),
                         bg="#1a1a1a", fg="#3498db")
        title.pack(pady=15)

        frame = tk.Frame(self.window, bg="#1a1a1a")
        frame.pack(padx=10, pady=10)

        for i in range(9):
            btn = tk.Button(frame, text='', width=8, height=4,
                            command=lambda idx=i: self.on_click(idx),
                            bg="#34495e", fg="white", font=("Arial", 18, "bold"),
                            activebackground="#2c3e50")
            btn.grid(row=i // 3, column=i % 3, padx=3, pady=3)
            self.buttons.append(btn)

    def on_click(self, idx):
        if self.board[idx] == '':
            self.board[idx] = self.current_player
            color = "#e74c3c" if self.current_player == 'X' else "#3498db"
            self.buttons[idx].config(text=self.current_player, fg=color)

            if self.check_winner():
                winner = self.current_player
                messagebox.showinfo("Game Over", f"Player {winner} wins!")
                self.score += 10
                self.db.save_progress(self.user_id, 'Tic Tac Toe', self.score, 1)
                self.db.save_leaderboard(self.user_id, 'Tic Tac Toe', self.score)
                self.reset_board()
            elif '' not in self.board:
                messagebox.showinfo("Game Over", "It's a draw!")
                self.reset_board()
            else:
                self.current_player = 'O' if self.current_player == 'X' else 'X'

    def check_winner(self):
        winning_combos = [
            [0, 1, 2], [3, 4, 5], [6, 7, 8],
            [0, 3, 6], [1, 4, 7], [2, 5, 8],
            [0, 4, 8], [2, 4, 6]
        ]
        for combo in winning_combos:
            if self.board[combo[0]] == self.board[combo[1]] == self.board[combo[2]] != '':
                return True
        return False

    def reset_board(self):
        self.board = [''] * 9
        self.current_player = 'X'
        for btn in self.buttons:
            btn.config(text='', fg="white")


class Game2048:
    def __init__(self, root, user_id, db):
        self.user_id = user_id
        self.db = db
        self.window = tk.Toplevel(root)
        self.window.title("2048")
        self.window.configure(bg="#bbada0")
        self.grid = [[0] * 4 for _ in range(4)]
        self.score = 0
        self.game_over = False
        self.tiles = []

        self.add_new_tile()
        self.add_new_tile()
        self.create_board()
        self.window.bind('<Key>', self.on_key_press)

    def create_board(self):
        title = tk.Label(self.window, text="2048 Game", font=("Arial", 20, "bold"),
                         bg="#bbada0", fg="#776e65")
        title.pack(pady=10)

        self.frame = tk.Frame(self.window, bg="#bbada0")
        self.frame.pack(padx=10, pady=10)

        for i in range(4):
            row = []
            for j in range(4):
                tile = tk.Label(self.frame, text='', width=8, height=4,
                                font=("Arial", 24, "bold"), bg="#cdc1b4", fg="#776e65")
                tile.grid(row=i, column=j, padx=2, pady=2)
                row.append(tile)
            self.tiles.append(row)

        score_label = tk.Label(self.window, text=f"Score: {self.score}", font=("Arial", 14),
                               bg="#2c3e50", fg="white")
        score_label.pack(pady=10)
        self.score_label = score_label
        self.update_display()

    def add_new_tile(self):
        empty = [(i, j) for i in range(4) for j in range(4) if self.grid[i][j] == 0]
        if empty:
            i, j = random.choice(empty)
            self.grid[i][j] = 2 if random.random() < 0.9 else 4

    def update_display(self):
        colors = {
            0: "#cdc1b4", 2: "#eee4da", 4: "#ede0c8", 8: "#f2b179",
            16: "#f59563", 32: "#f67c5f", 64: "#f65e3b", 128: "#edcf72",
            256: "#edcc61", 512: "#edc850", 1024: "#edc53f", 2048: "#edc22e"
        }
        for i in range(4):
            for j in range(4):
                val = self.grid[i][j]
                self.tiles[i][j].config(
                    text=str(val) if val != 0 else '',
                    bg=colors.get(val, "#3c3c2f")
                )
        self.score_label.config(text=f"Score: {self.score}")

    def move_left(self):
        moved = False
        for i in range(4):
            row = [self.grid[i][j] for j in range(4) if self.grid[i][j] != 0]
            for k in range(len(row) - 1):
                if row[k] == row[k + 1]:
                    row[k] *= 2
                    self.score += row[k]
                    row.pop(k + 1)
                    moved = True
            while len(row) < 4:
                row.append(0)
            for j in range(4):
                self.grid[i][j] = row[j]
        return moved

    def move_right(self):
        for i in range(4):
            self.grid[i].reverse()
        self.move_left()
        for i in range(4):
            self.grid[i].reverse()

    def move_up(self):
        for j in range(4):
            col = [self.grid[i][j] for i in range(4) if self.grid[i][j] != 0]
            for k in range(len(col) - 1):
                if col[k] == col[k + 1]:
                    col[k] *= 2
                    self.score += col[k]
                    col.pop(k + 1)
            while len(col) < 4:
                col.append(0)
            for i in range(4):
                self.grid[i][j] = col[i]

    def move_down(self):
        for j in range(4):
            col = [self.grid[i][j] for i in range(4) if self.grid[i][j] != 0]
            col.reverse()
            for k in range(len(col) - 1):
                if col[k] == col[k + 1]:
                    col[k] *= 2
                    self.score += col[k]
                    col.pop(k + 1)
            while len(col) < 4:
                col.append(0)
            col.reverse()
            for i in range(4):
                self.grid[i][j] = col[i]

    def on_key_press(self, event):
        if event.keysym == 'Left':
            self.move_left()
        elif event.keysym == 'Right':
            self.move_right()
        elif event.keysym == 'Up':
            self.move_up()
        elif event.keysym == 'Down':
            self.move_down()
        else:
            return

        self.add_new_tile()
        self.update_display()

        if self.is_game_over():
            messagebox.showinfo("Game Over", f"Final Score: {self.score}")
            self.db.save_progress(self.user_id, '2048', self.score, 1)
            self.db.save_leaderboard(self.user_id, '2048', self.score)
            self.window.destroy()

    def is_game_over(self):
        for i in range(4):
            for j in range(4):
                if self.grid[i][j] == 0:
                    return False
                if j < 3 and self.grid[i][j] == self.grid[i][j + 1]:
                    return False
                if i < 3 and self.grid[i][j] == self.grid[i + 1][j]:
                    return False
        return True


class Hangman:
    def __init__(self, root, user_id, db):
        self.user_id = user_id
        self.db = db
        self.window = tk.Toplevel(root)
        self.window.title("Hangman")
        self.window.configure(bg="#2c3e50")

        self.words = ['python', 'hangman', 'gaming', 'computer', 'puzzle', 'algorithm', 'database', 'programming']
        self.word = random.choice(self.words)
        self.guessed = set()
        self.wrong_guesses = 0
        self.score = 0
        self.max_wrong = 6

        self.create_ui()

    def create_ui(self):
        title = tk.Label(self.window, text="🎪 Hangman", font=("Arial", 20, "bold"),
                         bg="#2c3e50", fg="white")
        title.pack(pady=10)

        self.word_label = tk.Label(self.window, text=self.get_display_word(),
                                   font=("Arial", 18), bg="#2c3e50", fg="#3498db")
        self.word_label.pack(pady=10)

        self.status_label = tk.Label(self.window, text=f"Wrong Guesses: {self.wrong_guesses}/{self.max_wrong}",
                                     font=("Arial", 12), bg="#2c3e50", fg="#e74c3c")
        self.status_label.pack(pady=5)

        frame = tk.Frame(self.window, bg="#2c3e50")
        frame.pack(pady=10)

        self.letter_entry = tk.Entry(frame, font=("Arial", 12), width=5)
        self.letter_entry.pack(side="left", padx=5)

        guess_btn = tk.Button(frame, text="Guess", command=self.guess_letter,
                              bg="#27ae60", fg="white", font=("Arial", 12))
        guess_btn.pack(side="left", padx=5)

        self.guessed_label = tk.Label(self.window, text="Guessed Letters: ",
                                      font=("Arial", 10), bg="#2c3e50", fg="white")
        self.guessed_label.pack(pady=10)

    def get_display_word(self):
        return ' '.join([letter if letter in self.guessed else '_' for letter in self.word])

    def guess_letter(self):
        letter = self.letter_entry.get().lower()
        self.letter_entry.delete(0, tk.END)

        if not letter or len(letter) != 1:
            messagebox.showerror("Error", "Enter a single letter!")
            return

        if letter in self.guessed:
            messagebox.showwarning("Warning", "Already guessed!")
            return

        self.guessed.add(letter)

        if letter not in self.word:
            self.wrong_guesses += 1

        self.word_label.config(text=self.get_display_word())
        self.status_label.config(text=f"Wrong Guesses: {self.wrong_guesses}/{self.max_wrong}")
        self.guessed_label.config(text=f"Guessed Letters: {', '.join(sorted(self.guessed))}")

        if all(letter in self.guessed for letter in self.word):
            self.score = (self.max_wrong - self.wrong_guesses) * 10
            messagebox.showinfo("Win!", f"You won! Score: {self.score}")
            self.db.save_progress(self.user_id, 'Hangman', self.score, 1)
            self.db.save_leaderboard(self.user_id, 'Hangman', self.score)
            self.window.destroy()
        elif self.wrong_guesses >= self.max_wrong:
            messagebox.showinfo("Game Over", f"You lost! Word was: {self.word}")
            self.window.destroy()


class Trivia:
    def __init__(self, root, user_id, db):
        self.user_id = user_id
        self.db = db
        self.window = tk.Toplevel(root)
        self.window.title("Trivia Quiz")
        self.window.configure(bg="#2c3e50")

        self.questions = [
            {"q": "What is the capital of France?", "a": "Paris", "opts": ["Paris", "London", "Berlin", "Madrid"]},
            {"q": "What is 2 + 2?", "a": "4", "opts": ["3", "4", "5", "6"]},
            {"q": "Which planet is closest to the Sun?", "a": "Mercury", "opts": ["Venus", "Mercury", "Earth", "Mars"]},
            {"q": "What is the largest ocean?", "a": "Pacific Ocean",
             "opts": ["Atlantic", "Pacific Ocean", "Indian", "Arctic"]},
            {"q": "What year was Python created?", "a": "1991", "opts": ["1989", "1991", "1993", "1995"]},
        ]

        self.current_q = 0
        self.score = 0

        self.create_ui()

    def create_ui(self):
        title = tk.Label(self.window, text="❓ Trivia Quiz", font=("Arial", 20, "bold"),
                         bg="#2c3e50", fg="white")
        title.pack(pady=10)

        self.question_label = tk.Label(self.window, text="", font=("Arial", 14),
                                       bg="#2c3e50", fg="#3498db", wraplength=400)
        self.question_label.pack(pady=20)

        self.var = tk.StringVar()
        self.radio_buttons = []

        for i in range(4):
            rb = tk.Radiobutton(self.window, text="", variable=self.var, value="",
                                font=("Arial", 12), bg="#2c3e50", fg="white",
                                selectcolor="#34495e")
            rb.pack(anchor="w", padx=50)
            self.radio_buttons.append(rb)

        btn_frame = tk.Frame(self.window, bg="#2c3e50")
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="Next", command=self.next_question,
                  bg="#27ae60", fg="white", font=("Arial", 12)).pack(side="left", padx=10)

        self.score_label = tk.Label(self.window, text=f"Score: {self.score}/5",
                                    font=("Arial", 12), bg="#2c3e50", fg="#f39c12")
        self.score_label.pack()

        self.load_question()

    def load_question(self):
        if self.current_q < len(self.questions):
            q = self.questions[self.current_q]
            self.question_label.config(text=f"Q{self.current_q + 1}: {q['q']}")
            self.var.set("")

            random.shuffle(q['opts'])
            for i, rb in enumerate(self.radio_buttons):
                rb.config(text=q['opts'][i], value=q['opts'][i])
        else:
            self.end_quiz()

    def next_question(self):
        q = self.questions[self.current_q]
        if self.var.get() == q['a']:
            self.score += 1

        self.current_q += 1
        self.score_label.config(text=f"Score: {self.score}/{len(self.questions)}")
        self.load_question()

    def end_quiz(self):
        final_score = self.score * 20
        messagebox.showinfo("Quiz Over", f"Quiz Complete!\nFinal Score: {self.score}/5")
        self.db.save_progress(self.user_id, 'Trivia', final_score, 1)
        self.db.save_leaderboard(self.user_id, 'Trivia', final_score)
        self.window.destroy()


#Main App
class GamingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎮 Gaming Platform")
        self.root.geometry("800x700")
        self.root.configure(bg="#1a1a1a")
        self.db = Database()
        self.current_user_id = None
        self.current_username = None
        self.avatar_color = None

        self.setup_styles()
        self.show_login_screen()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', background="#2c3e50", foreground="white")
        style.configure('TButton', font=("Arial", 10))

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def show_login_screen(self):
        self.clear_window()
        self.root.configure(bg="#1a1a1a")

        main_frame = tk.Frame(self.root, bg="#1a1a1a")
        main_frame.pack(expand=True, fill="both")

        header = tk.Frame(main_frame, bg="#0f3460", height=100)
        header.pack(fill="x")

        title = tk.Label(header, text="🎮 GAMING PLATFORM", font=("Arial", 28, "bold"),
                         bg="#0f3460", fg="#00d4ff")
        title.pack(pady=20)

        subtitle = tk.Label(header, text="Play. Compete. Connect.", font=("Arial", 12),
                            bg="#0f3460", fg="#3498db")
        subtitle.pack()

        content = tk.Frame(main_frame, bg="#1a1a1a")
        content.pack(expand=True, padx=20, pady=30)

        notebook = ttk.Notebook(content)
        notebook.pack(fill="both", expand=True)

        # Login Tab
        login_frame = tk.Frame(notebook, bg="#2c3e50")
        notebook.add(login_frame, text="Login")

        tk.Label(login_frame, text="Username:", font=("Arial", 11, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=8)
        login_username = tk.Entry(login_frame, font=("Arial", 11), width=35, bg="#34495e", fg="white")
        login_username.pack(pady=5, ipady=8)

        tk.Label(login_frame, text="Password:", font=("Arial", 11, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=8)
        login_password = tk.Entry(login_frame, font=("Arial", 11), width=35, show="•", bg="#34495e", fg="white")
        login_password.pack(pady=5, ipady=8)

        def login():
            username = login_username.get().strip()
            password = login_password.get()

            if not username or not password:
                messagebox.showerror("Error", "Please fill all fields!")
                return

            result = self.db.login_user(username, password)
            if result:
                self.current_user_id = result[0]
                self.avatar_color = result[1]
                self.current_username = username
                messagebox.showinfo("Success", f"Welcome {username}!")
                self.show_main_menu()
            else:
                messagebox.showerror("Error", "Invalid username or password!")

        login_btn = tk.Button(login_frame, text="LOGIN", command=login,
                              bg="#00d4ff", fg="#0f3460", font=("Arial", 12, "bold"),
                              padx=30, pady=10)
        login_btn.pack(pady=20)

        #RegisterTab
        register_frame = tk.Frame(notebook, bg="#2c3e50")
        notebook.add(register_frame, text="Register")

        tk.Label(register_frame, text="Username:", font=("Arial", 11, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=8)
        reg_username = tk.Entry(register_frame, font=("Arial", 11), width=35, bg="#34495e", fg="white")
        reg_username.pack(pady=5, ipady=8)

        tk.Label(register_frame, text="Email:", font=("Arial", 11, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=8)
        reg_email = tk.Entry(register_frame, font=("Arial", 11), width=35, bg="#34495e", fg="white")
        reg_email.pack(pady=5, ipady=8)

        tk.Label(register_frame, text="Password (min 6 chars):", font=("Arial", 11, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=8)
        reg_password = tk.Entry(register_frame, font=("Arial", 11), width=35, show="•", bg="#34495e", fg="white")
        reg_password.pack(pady=5, ipady=8)

        tk.Label(register_frame, text="Confirm Password:", font=("Arial", 11, "bold"),
                 bg="#2c3e50", fg="white").pack(pady=8)
        reg_confirm = tk.Entry(register_frame, font=("Arial", 11), width=35, show="•", bg="#34495e", fg="white")
        reg_confirm.pack(pady=5, ipady=8)

        def register():
            username = reg_username.get().strip()
            email = reg_email.get().strip()
            password = reg_password.get()
            confirm = reg_confirm.get()

            if not username or not email or not password or not confirm:
                messagebox.showerror("Error", "Please fill all fields!")
                return

            if password != confirm:
                messagebox.showerror("Error", "Passwords don't match!")
                return

            success, message = self.db.register_user(username, email, password)
            if success:
                messagebox.showinfo("Success", message)
                reg_username.delete(0, tk.END)
                reg_email.delete(0, tk.END)
                reg_password.delete(0, tk.END)
                reg_confirm.delete(0, tk.END)
            else:
                messagebox.showerror("Error", message)

        register_btn = tk.Button(register_frame, text="REGISTER", command=register,
                                 bg="#00d4ff", fg="#0f3460", font=("Arial", 12, "bold"),
                                 padx=30, pady=10)
        register_btn.pack(pady=20)

        footer = tk.Label(main_frame, text="© 2026 Gaming Platform | Made with ❤️",
                          font=("Arial", 9), bg="#1a1a1a", fg="#7f8c8d")
        footer.pack(side="bottom", pady=10)

    def show_main_menu(self):
        self.clear_window()
        self.root.configure(bg="#1a1a1a")

        header = tk.Frame(self.root, bg=self.avatar_color, height=80)
        header.pack(fill="x")

        welcome_text = tk.Label(header, text=f"🎮 {self.current_username.upper()}",
                                font=("Arial", 22, "bold"), bg=self.avatar_color, fg="white")
        welcome_text.pack(pady=20)

        content = tk.Frame(self.root, bg="#1a1a1a")
        content.pack(expand=True, fill="both", padx=20, pady=20)

        games_label = tk.Label(content, text="🎮 AVAILABLE GAMES", font=("Arial", 14, "bold"),
                               bg="#1a1a1a", fg="#00d4ff")
        games_label.pack(anchor="w", pady=(0, 10))

        games_frame = tk.Frame(content, bg="#1a1a1a")
        games_frame.pack(fill="x", pady=10)

        self.create_game_button(games_frame, "🎯 Tic Tac Toe", self.play_tictactoe, "#e74c3c")
        self.create_game_button(games_frame, "2️⃣ 2048", self.play_2048, "#f39c12")
        self.create_game_button(games_frame, "🎪 Hangman", self.play_hangman, "#9b59b6")
        self.create_game_button(games_frame, "❓ Trivia", self.play_trivia, "#1abc9c")

        features_label = tk.Label(content, text="⭐ FEATURES", font=("Arial", 14, "bold"),
                                  bg="#1a1a1a", fg="#00d4ff")
        features_label.pack(anchor="w", pady=(20, 10))

        features_frame = tk.Frame(content, bg="#1a1a1a")
        features_frame.pack(fill="x", pady=10)

        self.create_feature_button(features_frame, "📊 Progress", self.show_progress, "#3498db")
        self.create_feature_button(features_frame, "🏆 Leaderboard", self.show_leaderboard, "#f1c40f")
        self.create_feature_button(features_frame, "👥 Friends", self.show_friends, "#2ecc71")
        self.create_feature_button(features_frame, "🚪 Logout", self.show_login_screen, "#95a5a6")

    def create_game_button(self, parent, text, command, color):
        btn = tk.Button(parent, text=text, command=command,
                        bg=color, fg="white", font=("Arial", 11, "bold"),
                        padx=20, pady=12, relief="flat")
        btn.pack(fill="x", pady=8)

    def create_feature_button(self, parent, text, command, color):
        btn = tk.Button(parent, text=text, command=command,
                        bg=color, fg="white" if color != "#f1c40f" else "#000",
                        font=("Arial", 11, "bold"),
                        padx=20, pady=12, relief="flat")
        btn.pack(fill="x", pady=6)

    def play_tictactoe(self):
        TicTacToe(self.root, self.current_user_id, self.db)

    def play_2048(self):
        Game2048(self.root, self.current_user_id, self.db)

    def play_hangman(self):
        Hangman(self.root, self.current_user_id, self.db)

    def play_trivia(self):
        Trivia(self.root, self.current_user_id, self.db)

    def show_progress(self):
        self.clear_window()
        self.root.configure(bg="#2c3e50")

        header = tk.Label(self.root, text="📊 YOUR PROGRESS", font=("Arial", 18, "bold"),
                          bg="#0f3460", fg="#00d4ff")
        header.pack(fill="x", pady=15)

        frame = tk.Frame(self.root, bg="#2c3e50")
        frame.pack(expand=True, fill="both", padx=20, pady=20)

        progress = self.db.get_progress(self.current_user_id)

        if progress:
            for game, score, level, last_played in progress:
                game_frame = tk.Frame(frame, bg="#34495e")
                game_frame.pack(fill="x", pady=8, padx=5)

                details = tk.Label(game_frame,
                                   text=f"🎮 {game} | Score: {score} | Level: {level} | Last Played: {last_played}",
                                   font=("Arial", 10), bg="#34495e", fg="white", padx=10, pady=8)
                details.pack(fill="x")
        else:
            no_data = tk.Label(frame, text="No games played yet! Start playing to see your progress.",
                               font=("Arial", 12), bg="#2c3e50", fg="#e74c3c")
            no_data.pack(pady=50)

        ttk.Button(frame, text="← Back", command=self.show_main_menu).pack(pady=20)

    def show_leaderboard(self):
        self.clear_window()
        self.root.configure(bg="#2c3e50")

        header = tk.Label(self.root, text="🏆 LEADERBOARDS", font=("Arial", 18, "bold"),
                          bg="#0f3460", fg="#00d4ff")
        header.pack(fill="x", pady=15)

        main_frame = tk.Frame(self.root, bg="#2c3e50")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        canvas = tk.Canvas(main_frame, bg="#2c3e50", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#2c3e50")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        games = ['Tic Tac Toe', '2048', 'Hangman', 'Trivia']
        for game in games:
            game_frame = tk.Frame(scrollable_frame, bg="#34495e")
            game_frame.pack(fill="x", pady=10)

            game_label = tk.Label(game_frame, text=f"🎮 {game}",
                                  font=("Arial", 12, "bold"), bg="#34495e", fg="#3498db")
            game_label.pack(anchor="w", padx=15, pady=(10, 5))

            leaderboard = self.db.get_leaderboard(game, limit=5)
            if leaderboard:
                for rank, (username, score, date) in enumerate(leaderboard, 1):
                    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
                    rank_label = tk.Label(game_frame,
                                          text=f"{medal} {username} - Score: {score} ({date})",
                                          font=("Arial", 10), bg="#34495e", fg="white")
                    rank_label.pack(anchor="w", padx=30)
            else:
                no_data = tk.Label(game_frame, text="No scores yet!",
                                   font=("Arial", 10), bg="#34495e", fg="#e74c3c")
                no_data.pack(anchor="w", padx=30)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ttk.Button(main_frame, text="← Back", command=self.show_main_menu).pack(pady=20)

    def show_friends(self):
        self.clear_window()
        self.root.configure(bg="#2c3e50")

        header = tk.Label(self.root, text="👥 FRIENDS", font=("Arial", 18, "bold"),
                          bg="#0f3460", fg="#00d4ff")
        header.pack(fill="x", pady=15)

        main_frame = tk.Frame(self.root, bg="#2c3e50")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        friends_label = tk.Label(main_frame, text="Your Friends:", font=("Arial", 12, "bold"),
                                 bg="#2c3e50", fg="white")
        friends_label.pack(anchor="w", pady=(0, 10))

        friends_frame = tk.Frame(main_frame, bg="#34495e")
        friends_frame.pack(fill="x", pady=10, ipady=10)

        friends = self.db.get_friends(self.current_user_id)
        if friends:
            for friend, friend_id in friends:
                friend_label = tk.Label(friends_frame, text=f"✓ {friend}",
                                        font=("Arial", 11), bg="#34495e", fg="#2ecc71")
                friend_label.pack(anchor="w", padx=15, pady=5)
        else:
            no_friends = tk.Label(friends_frame, text="No friends yet! Add some to get started.",
                                  font=("Arial", 11), bg="#34495e", fg="#e74c3c")
            no_friends.pack(anchor="w", padx=15, pady=5)

        pending = self.db.get_pending_requests(self.current_user_id)
        if pending:
            requests_label = tk.Label(main_frame, text="Friend Requests:", font=("Arial", 12, "bold"),
                                      bg="#2c3e50", fg="white")
            requests_label.pack(anchor="w", pady=(20, 10))

            for requester, requester_id in pending:
                req_frame = tk.Frame(main_frame, bg="#34495e")
                req_frame.pack(fill="x", pady=5)

                label = tk.Label(req_frame, text=f"📨 {requester}",
                                 font=("Arial", 11), bg="#34495e", fg="#f39c12")
                label.pack(side="left", padx=15, pady=8)

                def accept(rid=requester_id):
                    self.db.accept_friend_request(rid, self.current_user_id)
                    messagebox.showinfo("Success", "Friend request accepted!")
                    self.show_friends()

                def reject(rid=requester_id):
                    self.db.reject_friend_request(rid, self.current_user_id)
                    messagebox.showinfo("Success", "Friend request rejected!")
                    self.show_friends()

                tk.Button(req_frame, text="✓ Accept", command=accept, bg="#27ae60", fg="white",
                          font=("Arial", 10), padx=10, pady=5).pack(side="right", padx=5)
                tk.Button(req_frame, text="✗ Reject", command=reject, bg="#e74c3c", fg="white",
                          font=("Arial", 10), padx=10, pady=5).pack(side="right", padx=5)

        add_label = tk.Label(main_frame, text="Add Friend:", font=("Arial", 12, "bold"),
                             bg="#2c3e50", fg="white")
        add_label.pack(anchor="w", pady=(20, 10))

        all_users = self.db.get_all_users()
        user_friends = [u[0] for u in friends]
        available_users = [u[0] for u in all_users if u[1] != self.current_user_id and u[0] not in user_friends]

        friend_var = tk.StringVar()
        friend_combo = ttk.Combobox(main_frame, textvariable=friend_var, values=available_users,
                                    state="readonly", font=("Arial", 11))
        friend_combo.pack(fill="x", pady=5, ipady=8)

        def send_request():
            selected = friend_var.get()
            if not selected:
                messagebox.showerror("Error", "Please select a user!")
                return

            friend_id = self.db.get_user_id_by_username(selected)
            if self.db.send_friend_request(self.current_user_id, friend_id):
                messagebox.showinfo("Success", "Friend request sent!")
                self.show_friends()
            else:
                messagebox.showerror("Error", "Could not send request!")

        add_btn = tk.Button(main_frame, text="Send Request", command=send_request,
                            bg="#00d4ff", fg="#0f3460", font=("Arial", 11, "bold"),
                            padx=20, pady=10)
        add_btn.pack(pady=15)

        ttk.Button(main_frame, text="← Back", command=self.show_main_menu).pack(pady=20)


if __name__ == "__main__":
    print("🎮 Starting Gaming Platform...")
    root = tk.Tk()
    app = GamingApp(root)
    root.mainloop()
