from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
import os
from database import DatabaseManager
from auth import AuthSystem

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize database and auth
db = DatabaseManager()
auth = AuthSystem(db)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        
        success, message = auth.register(username, email, password)
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        success, message = auth.login(username, password)
        if success:
            session['user_id'] = auth.current_user['user_id']
            session['username'] = auth.current_user['username']
            flash(message, 'success')
            
            # Add daily reward message if any
            if auth.daily_reward_msg:
                flash(auth.daily_reward_msg, 'info')
            
            return redirect(url_for('dashboard'))
        else:
            flash(message, 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    auth.logout()
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    
    # Get user stats
    user = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    
    # Get recent scores
    recent_scores = db.fetch_all("""
        SELECT s.*, g.name as game_name 
        FROM scores s 
        JOIN games g ON s.game_key = g.game_key 
        WHERE s.user_id = ? 
        ORDER BY s.achieved_at DESC 
        LIMIT 10
    """, (user_id,))
    
    # Get leaderboard
    leaderboard = db.fetch_all("""
        SELECT u.username, SUM(s.score) as total_score, COUNT(s.score_id) as games_played
        FROM scores s
        JOIN users u ON s.user_id = u.user_id
        GROUP BY s.user_id
        ORDER BY total_score DESC
        LIMIT 10
    """)
    
    # Get available games
    games = db.fetch_all("SELECT * FROM games ORDER BY name")
    
    return render_template('dashboard.html', 
                         user=user, 
                         recent_scores=recent_scores,
                         leaderboard=leaderboard,
                         games=games)

@app.route('/profile')
@login_required
def profile():
    user_id = session['user_id']
    user = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id))
    
    # Get user's high scores
    high_scores = db.fetch_all("""
        SELECT s.*, g.name as game_name
        FROM scores s
        JOIN games g ON s.game_key = g.game_key
        WHERE s.user_id = ?
        AND s.score = (
            SELECT MAX(score) FROM scores 
            WHERE user_id = ? AND game_key = s.game_key
        )
        ORDER BY s.score DESC
    """, (user_id, user_id))
    
    return render_template('profile.html', user=user, high_scores=high_scores)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user_id = session['user_id']
    
    if request.method == 'POST':
        theme = request.form.get('theme', 'dark')
        sound = 'sound' in request.form
        notifications = 'notifications' in request.form
        
        auth.update_settings('theme', theme)
        auth.update_settings('sound', sound)
        auth.update_settings('notifications', notifications)
        
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))
    
    user = db.fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_settings = auth.get_settings()
    
    return render_template('settings.html', user=user, settings=user_settings)

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
        flash('Game not found.', 'danger')
        return redirect(url_for('games'))
    
    return render_template(f'games/{game_key}.html', game=game)

@app.route('/api/score', methods=['POST'])
@login_required
def submit_score():
    data = request.get_json()
    game_key = data.get('game_key')
    score = data.get('score')
    play_time = data.get('play_time', 0)
    
    if not game_key or score is None:
        return jsonify({'error': 'Invalid score data'}), 400
    
    user_id = session['user_id']
    
    try:
        # Save score
        db.execute(
            """INSERT INTO scores (user_id, game_key, score, play_time) 
               VALUES (?, ?, ?, ?)""",
            (user_id, game_key, score, play_time)
        )
        
        # Award coins
        coins_earned = max(1, int(score / 10))
        db.execute(
            """UPDATE users SET coins = coins + ?, total_games_played = total_games_played + 1,
               total_score = total_score + ? WHERE user_id = ?""",
            (coins_earned, score, user_id)
        )
        
        # Update game play count
        db.execute(
            "UPDATE games SET play_count = play_count + 1 WHERE game_key = ?",
            (game_key,)
        )
        
        return jsonify({
            'success': True,
            'coins_earned': coins_earned,
            'message': f'Score saved! You earned {coins_earned} coins.'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/leaderboard')
@login_required
def leaderboard():
    # Overall leaderboard
    overall = db.fetch_all("""
        SELECT u.username, SUM(s.score) as total_score, 
               COUNT(s.score_id) as games_played,
               u.coins
        FROM scores s
        JOIN users u ON s.user_id = u.user_id
        GROUP BY s.user_id
        ORDER BY total_score DESC
        LIMIT 50
    """)
    
    # Per-game leaderboards
    games = db.fetch_all("SELECT game_key, name FROM games")
    game_leaderboards = {}
    
    for game in games:
        game_leaderboards[game['game_key']] = db.fetch_all("""
            SELECT u.username, MAX(s.score) as high_score, 
                   COUNT(s.score_id) as times_played
            FROM scores s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.game_key = ?
            GROUP BY s.user_id
            ORDER BY high_score DESC
            LIMIT 20
        """, (game['game_key'],))
    
    return render_template('leaderboard.html', 
                         overall=overall, 
                         game_leaderboards=game_leaderboards,
                         games=games)

@app.route('/friends')
@login_required
def friends():
    user_id = session['user_id']
    
    # Get friends
    friends = db.fetch_all("""
        SELECT u.*, f.status
        FROM users u
        JOIN friends f ON (
            (f.user_id_1 = ? AND f.user_id_2 = u.user_id) OR
            (f.user_id_2 = ? AND f.user_id_1 = u.user_id)
        )
        WHERE f.status = 'accepted'
    """, (user_id, user_id))
    
    # Get pending friend requests
    pending = db.fetch_all("""
        SELECT u.*
        FROM users u
        JOIN friends f ON f.user_id_1 = u.user_id
        WHERE f.user_id_2 = ? AND f.status = 'pending'
    """, (user_id,))
    
    return render_template('friends.html', friends=friends, pending=pending)

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
        db.execute(
            """INSERT INTO friends (user_id_1, user_id_2, status) 
               VALUES (?, ?, 'pending')""",
            (user_id, friend['user_id'])
        )
        return jsonify({'success': True, 'message': 'Friend request sent!'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Friend request already sent'}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
