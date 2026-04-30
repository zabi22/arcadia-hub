from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from src.models.models import db, User, Score, Game
from src.services.game_service import submit_score, get_user_scores, get_leaderboard, get_all_games, get_game_config, seed_games
from src.services.shop_service import purchase_item, get_user_inventory, equip_item, unequip_item, get_shop_items
from src.services.friend_service import send_friend_request, accept_friend_request, reject_friend_request, get_friend_requests, get_friends, remove_friendship, search_users
from src.utils.helpers import get_current_user, login_required, calculate_level, update_user_activity
from src.utils.logger import get_logger
from src.services.notification_service import get_user_notifications, mark_notification_as_read, mark_all_notifications_as_read

logger = get_logger()

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Redirect to login or dashboard"""
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    user = get_current_user()
    if not user:
        flash('Session expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))
    
    try:
        # Calculate level
        level, xp_current, xp_needed = calculate_level(user.xp)
        xp_percent = int((xp_current / xp_needed) * 100) if xp_needed > 0 else 0
        
        # Get recent scores
        recent_scores = get_user_scores(user.user_id, limit=5)
        
        # Get games - show all on dashboard
        games = get_all_games()
        
        # Get leaderboard
        leaderboard = get_leaderboard(limit=5)
        
        # Get achievements
        from src.services.game_service import get_user_achievements
        achievements = get_user_achievements(user.user_id)[:5]
        
        # Get daily challenges
        from datetime import date
        from src.services.challenge_service import get_daily_challenges
        challenges = get_daily_challenges(user.user_id)
        
        return render_template('dashboard.html',
                             user=user,
                             current_level=level,
                             xp_current=xp_current,
                             xp_needed=xp_needed,
                             xp_percent=xp_percent,
                             recent_scores=recent_scores,
                             games=games,
                             leaderboard=leaderboard,
                             achievements=achievements,
                             challenges=challenges)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        flash('An error occurred loading your dashboard.', 'danger')
        return render_template('error.html', error='Dashboard loading failed'), 500


@main_bp.route('/games')
@login_required
def games():
    """Games listing page"""
    try:
        all_games = get_all_games()
        logger.info(f"Loading games page with {len(all_games)} games")
        return render_template('games.html', games=all_games)
    except Exception as e:
        logger.error(f"Games page error: {e}", exc_info=True)
        flash(f'Error loading games: {str(e)}', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/play/<game_key>')
@login_required
def play_game(game_key):
    """Play a specific game"""
    game_config = get_game_config(game_key)
    
    if not game_config:
        flash('Game not found', 'danger')
        return redirect(url_for('main.games'))
    
    # Update user activity
    user = get_current_user()
    if user:
        update_user_activity(user)
    
    return render_template(f'games/{game_key}.html', game=game_config)


@main_bp.route('/api/score', methods=['POST'])
@login_required
def submit_score_api():
    """API endpoint to submit game score"""
    try:
        data = request.get_json()
        game_key = data.get('game_key')
        score = data.get('score', 0)
        play_time = data.get('play_time', 0)
        
        if not game_key:
            return jsonify({'success': False, 'message': 'Game key required'}), 400
        
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 401
        
        success, result = submit_score(user, game_key, score, play_time)
        
        if success:
            return jsonify({
                'success': True,
                'coins_earned': result['coins_earned'],
                'xp_earned': result['xp_earned'],
                'is_high_score': result['is_high_score']
            })
        else:
            return jsonify({'success': False, 'message': result}), 400
            
    except Exception as e:
        logger.error(f"Score submission error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/leaderboard')
@login_required
def leaderboard():
    """Leaderboard page"""
    try:
        game_key = request.args.get('game')
        leaderboard_data = get_leaderboard(game_key=game_key, limit=50)
        games = get_all_games()
        
        return render_template('leaderboard.html',
                             leaderboard=leaderboard_data,
                             games=games,
                             current_game=game_key)
    except Exception as e:
        logger.error(f"Leaderboard error: {e}")
        flash('Error loading leaderboard', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    try:
        user = get_current_user()
        level, xp_current, xp_needed = calculate_level(user.xp)
        xp_percent = int((xp_current / xp_needed) * 100) if xp_needed > 0 else 0
        
        scores = get_user_scores(user.user_id, limit=10)
        
        from src.services.game_service import get_user_achievements
        achievements = get_user_achievements(user.user_id)
        
        return render_template('profile.html',
                             user=user,
                             level=level,
                             xp_current=xp_current,
                             xp_needed=xp_needed,
                             xp_percent=xp_percent,
                             scores=scores,
                             achievements=achievements)
    except Exception as e:
        logger.error(f"Profile error: {e}")
        flash('Error loading profile', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/shop')
@login_required
def shop():
    """Shop page"""
    try:
        category = request.args.get('category')
        shop_items = get_shop_items(category=category)
        user = get_current_user()
        
        return render_template('shop.html',
                             shop_items=shop_items,
                             user=user,
                             current_category=category)
    except Exception as e:
        logger.error(f"Shop error: {e}")
        flash('Error loading shop', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/shop/purchase', methods=['POST'])
@login_required
def purchase():
    """Purchase item from shop"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        
        if not item_id:
            return jsonify({'success': False, 'message': 'Item ID required'}), 400
        
        user = get_current_user()
        success, result = purchase_item(user, item_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Purchased {result['name']}",
                'coins': user.coins
            })
        else:
            return jsonify({'success': False, 'message': result}), 400
            
    except Exception as e:
        logger.error(f"Purchase error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/inventory')
@login_required
def inventory():
    """User inventory page"""
    try:
        user = get_current_user()
        inventory_items = get_user_inventory(user.user_id)
        
        return render_template('inventory.html',
                             inventory=inventory_items,
                             user=user)
    except Exception as e:
        logger.error(f"Inventory error: {e}")
        flash('Error loading inventory', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/inventory/equip', methods=['POST'])
@login_required
def equip():
    """Equip item"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        
        user = get_current_user()
        success, error = equip_item(user, item_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Item equipped'})
        else:
            return jsonify({'success': False, 'message': error}), 400
            
    except Exception as e:
        logger.error(f"Equip error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/inventory/unequip', methods=['POST'])
@login_required
def unequip():
    """Unequip item"""
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        
        user = get_current_user()
        success, error = unequip_item(user, item_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Item unequipped'})
        else:
            return jsonify({'success': False, 'message': error}), 400
            
    except Exception as e:
        logger.error(f"Unequip error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/friends')
@login_required
def friends():
    """Friends page"""
    try:
        user = get_current_user()
        friends_list = get_friends(user.user_id)
        friend_requests = get_friend_requests(user.user_id)
        
        return render_template('friends.html',
                             friends=friends_list,
                             friend_requests=friend_requests,
                             user=user)
    except Exception as e:
        logger.error(f"Friends error: {e}")
        flash('Error loading friends', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/friends/add', methods=['POST'])
@login_required
def add_friend():
    """Add friend"""
    try:
        data = request.get_json()
        recipient_id = data.get('user_id')
        
        if not recipient_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        user = get_current_user()
        success, error = send_friend_request(user.user_id, recipient_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Friend request sent'})
        else:
            return jsonify({'success': False, 'message': error}), 400
            
    except Exception as e:
        logger.error(f"Add friend error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/friends/accept', methods=['POST'])
@login_required
def accept_friend():
    """Accept friend request"""
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        
        user = get_current_user()
        success, error = accept_friend_request(request_id, user.user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Friend request accepted'})
        else:
            return jsonify({'success': False, 'message': error}), 400
            
    except Exception as e:
        logger.error(f"Accept friend error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/friends/reject', methods=['POST'])
@login_required
def reject_friend():
    """Reject friend request"""
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        
        user = get_current_user()
        success, error = reject_friend_request(request_id, user.user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Friend request rejected'})
        else:
            return jsonify({'success': False, 'message': error}), 400
            
    except Exception as e:
        logger.error(f"Reject friend error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/friends/remove', methods=['POST'])
@login_required
def remove_friend():
    """Remove friend"""
    try:
        data = request.get_json()
        friend_id = data.get('user_id')
        
        user = get_current_user()
        success, error = remove_friendship(user.user_id, friend_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Friend removed'})
        else:
            return jsonify({'success': False, 'message': error}), 400
            
    except Exception as e:
        logger.error(f"Remove friend error: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/friends/search')
@login_required
def search_friends():
    """Search for users to add as friends"""
    try:
        query = request.args.get('q', '')
        
        if len(query) < 2:
            return jsonify({'users': []})
        
        user = get_current_user()
        users = search_users(query, exclude_id=user.user_id)
        
        return jsonify({'users': users})
    except Exception as e:
        logger.error(f"Search friends error: {e}")
        return jsonify({'users': []}), 500


@main_bp.route('/settings')
@login_required
def settings():
    """Settings page"""
    try:
        user = get_current_user()
        return render_template('settings.html', user=user)
    except Exception as e:
        logger.error(f"Settings error: {e}")
        flash('Error loading settings', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/chat')
@login_required
def chat():
    """Chat page"""
    try:
        return render_template('chat.html')
    except Exception as e:
        logger.error(f"Chat error: {e}")
        flash('Error loading chat', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': db.func.now().cast(db.String).scalar()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@main_bp.route('/api/profile', methods=['GET'])
@login_required
def get_profile_api():
    """Get current user's profile"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 401
        
        level, xp_current, xp_needed = calculate_level(user.xp)
        
        return jsonify({
            'success': True,
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'avatar_config': user.avatar_config,
                'bio': user.bio,
                'coins': user.coins,
                'xp': user.xp,
                'player_level': level,
                'xp_percent': int((xp_current / xp_needed) * 100) if xp_needed > 0 else 0,
                'total_games_played': user.total_games_played,
                'total_score': user.total_score,
                'streak': user.streak,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'profile_updated_at': user.profile_updated_at.isoformat() if hasattr(user, 'profile_updated_at') and user.profile_updated_at else None
            }
        })
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/api/profile', methods=['PUT'])
@login_required
def update_profile_api():
    """Update user profile"""
    try:
        data = request.get_json()
        user = get_current_user()
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 401
        
        from src.services.user_service import update_user_profile
        
        success, message = update_user_profile(user, **data)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500


@main_bp.route('/api/chat/messages')
@login_required
def get_chat_messages():
    """Get recent chat messages (optimized with raw SQL)"""
    try:
        from sqlalchemy import text
        
        # Use raw SQL for better performance
        query = text("""
            SELECT m.message_id, m.sender_id, m.content, m.timestamp, u.username
            FROM messages m
            LEFT JOIN users u ON m.sender_id = u.user_id
            WHERE m.is_global IS TRUE
            ORDER BY m.timestamp DESC
            LIMIT 20
        """)
        
        result = db.session.execute(query).fetchall()
        
        # Build response
        messages_data = []
        for row in reversed(result):
            messages_data.append({
                'message_id': row[0],
                'sender_id': row[1],
                'username': row[4] if row[4] else 'Unknown',
                'content': row[2],
                'timestamp': row[3].isoformat() if row[3] else ''
            })
        
        return jsonify({'messages': messages_data})
    except Exception as e:
        logger.error(f"Error fetching chat messages: {e}")
        return jsonify({'messages': []}), 500

@main_bp.route('/api/notifications', methods=['GET'])
@login_required
def get_notifications_api():
    """API endpoint to get user notifications"""
    try:
        user = get_current_user()
        notifications = get_user_notifications(user.user_id)
        return jsonify({'success': True, 'notifications': notifications})
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@main_bp.route('/api/notifications/read', methods=['POST'])
@login_required
def mark_read_api():
    """API endpoint to mark notification as read"""
    try:
        data = request.get_json()
        notification_id = data.get('notification_id')
        user = get_current_user()
        
        if notification_id:
            success = mark_notification_as_read(notification_id, user.user_id)
        else:
            success = mark_all_notifications_as_read(user.user_id)
            
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error marking notification read: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@main_bp.route('/multiplayer')
@login_required
def multiplayer_lobby():
    """Multiplayer lobby page"""
    return render_template('multiplayer_lobby.html')

@main_bp.route('/ranked')
@login_required
def ranked_page():
    """Ranked progression page"""
    user = get_current_user()
    return render_template('ranked.html', user=user)

@main_bp.route('/challenge')
@login_required
def challenge():
    """Daily challenges page"""
    user = get_current_user()
    from src.services.challenge_service import get_daily_challenges
    challenges = get_daily_challenges(user.user_id)
    return render_template('challenge.html', user=user, challenges=challenges)
