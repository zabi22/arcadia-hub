import random
import string
from datetime import datetime
from flask_socketio import emit, join_room, leave_room
from src.models.models import db, GameRoom, RoomPlayer, User, Game
from src.utils.helpers import get_current_user
from src.utils.logger import get_logger

logger = get_logger()

# In-memory store for active game states
# room_code -> { game_state_data }
ACTIVE_GAMES = {}

def generate_room_code():
    """Generate a unique 6-character room code"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not GameRoom.query.filter_by(room_code=code).first():
            return code


def register_multiplayer_events(socketio):
    """Register SocketIO events for multiplayer"""

    @socketio.on('create_room')
    def handle_create_room(data):
        """Create a new game room"""
        user = get_current_user()
        if not user:
            emit('error', {'message': 'Unauthorized'})
            return

        game_key = data.get('game_key')
        max_players = data.get('max_players', 4)
        is_private = data.get('is_private', False)

        game = Game.query.filter_by(game_key=game_key).first()
        if not game:
            emit('error', {'message': 'Game not found'})
            return

        try:
            room_code = generate_room_code()
            room = GameRoom(
                room_code=room_code,
                game_key=game_key,
                host_id=user.user_id,
                max_players=max_players,
                is_private=is_private
            )
            db.session.add(room)
            db.session.flush()

            player = RoomPlayer(room_id=room.room_id, user_id=user.user_id, is_ready=True)
            db.session.add(player)
            db.session.commit()

            join_room(room_code)
            emit('room_created', {
                'room_code': room_code,
                'game_key': game_key,
                'host_id': user.user_id
            })
            logger.info(f"Room created: {room_code} by {user.username}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating room: {e}")
            emit('error', {'message': 'Failed to create room'})

    @socketio.on('join_room')
    def handle_join_room(data):
        """Join an existing game room"""
        user = get_current_user()
        if not user:
            emit('error', {'message': 'Unauthorized'})
            return

        room_code = data.get('room_code')
        room = GameRoom.query.filter_by(room_code=room_code, status='waiting').first()

        if not room:
            emit('error', {'message': 'Room not found or game already started'})
            return

        if room.players.count() >= room.max_players:
            emit('error', {'message': 'Room is full'})
            return

        try:
            # Check if already in room
            existing_player = RoomPlayer.query.filter_by(room_id=room.room_id, user_id=user.user_id).first()
            if not existing_player:
                player = RoomPlayer(room_id=room.room_id, user_id=user.user_id)
                db.session.add(player)
                db.session.commit()

            join_room(room_code)
            
            # Notify everyone in the room
            players_data = []
            for p in room.players:
                p_user = db.session.get(User, p.user_id)
                players_data.append({
                    'user_id': p_user.user_id,
                    'username': p_user.username,
                    'is_ready': p.is_ready
                })

            emit('room_joined', {
                'room_code': room_code,
                'game_key': room.game_key,
                'players': players_data
            }, room=room_code)
            
            logger.info(f"User {user.username} joined room {room_code}")

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error joining room: {e}")
            emit('error', {'message': 'Failed to join room'})

    @socketio.on('player_ready')
    def handle_player_ready(data):
        """Player ready toggle"""
        user = get_current_user()
        room_code = data.get('room_code')
        is_ready = data.get('is_ready', True)

        room = GameRoom.query.filter_by(room_code=room_code).first()
        if room:
            player = RoomPlayer.query.filter_by(room_id=room.room_id, user_id=user.user_id).first()
            if player:
                player.is_ready = is_ready
                db.session.commit()
                
                emit('player_status_update', {
                    'user_id': user.user_id,
                    'is_ready': is_ready
                }, room=room_code)

                # Auto-start if all ready and more than 1 player
                if room.players.count() >= 2 and all(p.is_ready for p in room.players):
                    start_game(room)

    def start_game(room):
        """Initialize and start the multiplayer game"""
        try:
            room.status = 'active'
            db.session.commit()

            # Initialize game state based on game_key
            game_state = {
                'room_code': room.room_code,
                'game_key': room.game_key,
                'status': 'starting',
                'players': [p.user_id for p in room.players],
                'scores': {p.user_id: 0 for p in room.players},
                'start_time': datetime.utcnow().isoformat()
            }
            ACTIVE_GAMES[room.room_code] = game_state

            emit('game_starting', game_state, room=room.room_code)
            logger.info(f"Game started in room {room.room_code}")

        except Exception as e:
            logger.error(f"Error starting game: {e}")

    @socketio.on('game_update')
    def handle_game_update(data):
        """Handle real-time game state updates from clients"""
        room_code = data.get('room_code')
        if room_code in ACTIVE_GAMES:
            # Sync state with other players (e.g., positions, events)
            emit('game_state_sync', data, room=room_code, include_self=False)

    @socketio.on('submit_multiplayer_score')
    def handle_multiplayer_score(data):
        """Handle final score submission for multiplayer match"""
        user = get_current_user()
        room_code = data.get('room_code')
        final_score = data.get('score', 0)

        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            game_state['scores'][user.user_id] = final_score
            
            # Check if all players have submitted
            if all(uid in game_state['scores'] for uid in game_state['players']):
                end_multiplayer_game(room_code)

    def end_multiplayer_game(room_code):
        """Finalize multiplayer game, award rewards, and close room"""
        if room_code not in ACTIVE_GAMES:
            return

        game_state = ACTIVE_GAMES[room_code]
        room = GameRoom.query.filter_by(room_code=room_code).first()
        
        try:
            # Determine winner
            winner_id = max(game_state['scores'], key=game_state['scores'].get)
            
            # Award rewards (multiplayer bonus)
            for user_id, score in game_state['scores'].items():
                user = db.session.get(User, user_id)
                # Use game_service to submit final score and handle rewards
                from src.services.game_service import submit_score
                submit_score(user, game_state['game_key'], score, play_time=60) # estimated time
                
                if user_id == winner_id:
                    user.coins += 50 # Winner bonus
                    user.xp += 100
            
            db.session.commit()

            emit('game_ended', {
                'scores': game_state['scores'],
                'winner_id': winner_id
            }, room=room_code)

            room.status = 'ended'
            db.session.commit()
            del ACTIVE_GAMES[room_code]
            logger.info(f"Game ended in room {room_code}")

        except Exception as e:
            logger.error(f"Error ending game: {e}")
