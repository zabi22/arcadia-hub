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

    @socketio.on('submit_reaction')
    def handle_reaction(data):
        """Handle reaction time submission for reaction arena"""
        user = get_current_user()
        room_code = data.get('room_code')
        reaction_time = data.get('reaction_time', 9999)  # Default high time for no reaction

        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            room = GameRoom.query.filter_by(room_code=room_code).first()

            if not room or game_state.get('game_key') != 'reaction_multi':
                return

            # Initialize round data if not exists
            if 'current_round' not in game_state:
                game_state['current_round'] = 1
                game_state['total_rounds'] = 5
                game_state['round_reactions'] = {}
                game_state['round_start_time'] = datetime.utcnow()

            # Store reaction time for this round
            game_state['round_reactions'][user.user_id] = reaction_time

            # Check if all players have reacted or time is up
            total_players = len(game_state['players'])
            reacted_players = len(game_state['round_reactions'])

            if reacted_players >= total_players:
                # All players reacted, end round
                end_reaction_round(room_code)

    def end_reaction_round(room_code):
        """End current round and determine winner"""
        if room_code not in ACTIVE_GAMES:
            return

        game_state = ACTIVE_GAMES[room_code]
        round_reactions = game_state.get('round_reactions', {})

        if not round_reactions:
            return

        # Find fastest reaction (lowest time)
        fastest_user = min(round_reactions, key=round_reactions.get)
        fastest_time = round_reactions[fastest_user]

        # Award points (faster = more points)
        for user_id, reaction_time in round_reactions.items():
            if reaction_time < 1000:  # Only award for reasonable reactions
                points = max(1, 100 - (reaction_time // 10))  # 100 points for instant, decreasing
                if user_id == fastest_user:
                    points += 50  # Bonus for winning round

                game_state['scores'][user_id] = game_state['scores'].get(user_id, 0) + points

        # Send round results
        emit('round_result', {
            'winner_id': fastest_user,
            'reaction_time': fastest_time,
            'scores': game_state['scores']
        }, room=room_code)

        # Check if match is over
        current_round = game_state.get('current_round', 1)
        if current_round >= game_state.get('total_rounds', 5):
            # Match complete
            end_multiplayer_game(room_code)
        else:
            # Start next round
            game_state['current_round'] = current_round + 1
            game_state['round_reactions'] = {}

            # Start next round after delay
            emit('round_start', {}, room=room_code)

    @socketio.on('start_round')
    def handle_start_round(data):
        """Start a new round for stack battle"""
        room_code = data.get('room_code')
        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            if game_state.get('game_key') == 'towerstack_multi':
                emit('round_start', {}, room=room_code)

    @socketio.on('place_block')
    def handle_place_block(data):
        """Handle block placement for stack battle"""
        user = get_current_user()
        room_code = data.get('room_code')
        position = data.get('position', 0)

        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            room = GameRoom.query.filter_by(room_code=room_code).first()

            if not room or game_state.get('game_key') != 'towerstack_multi':
                return

            # Initialize towers if not exists
            if 'towers' not in game_state:
                game_state['towers'] = {uid: [] for uid in game_state['players']}

            towers = game_state['towers']

            # Calculate block placement success
            # Block falls if position is too far from center
            success = abs(position) <= 100  # Within reasonable range

            if success:
                # Add block to player's tower
                block_width = max(20, 100 - abs(position) * 0.5)  # Narrower if placed poorly
                block_offset = position * 0.3  # Slight offset based on placement

                towers[user.user_id].append({
                    'width': block_width,
                    'offset': block_offset
                })

            # Send round result
            emit('round_result', {
                'towers': towers,
                'success': success
            }, room=room_code)

    @socketio.on('end_stack_game')
    def handle_end_stack_game(data):
        """End stack battle game"""
        room_code = data.get('room_code')
        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            if game_state.get('game_key') == 'towerstack_multi':
                # Determine winner by tower height
                towers = game_state.get('towers', {})
                winner_id = max(towers, key=lambda uid: len(towers[uid])) if towers else None

                # Calculate final scores
                for user_id, tower in towers.items():
                    game_state['scores'][user_id] = len(tower) * 10  # 10 points per block

                end_multiplayer_game(room_code)

    @socketio.on('player_hit')
    def handle_player_hit(data):
        """Handle player getting hit in survival dodge"""
        user = get_current_user()
        room_code = data.get('room_code')

        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            room = GameRoom.query.filter_by(room_code=room_code).first()

            if not room or game_state.get('game_key') != 'survival_dodge_multi':
                return

            # Mark player as eliminated
            if 'eliminated' not in game_state:
                game_state['eliminated'] = set()
            game_state['eliminated'].add(user.user_id)

            # Check if only one player left
            active_players = [uid for uid in game_state['players'] if uid not in game_state['eliminated']]
            if len(active_players) == 1:
                winner_id = active_players[0]
                game_state['scores'][winner_id] = 100  # Winner gets 100 points
                end_multiplayer_game(room_code)
            else:
                # Notify others that player was eliminated
                emit('player_eliminated', {
                    'user_id': user.user_id,
                    'remaining_players': len(active_players)
                }, room=room_code)

    @socketio.on('pong_ball_update')
    def handle_pong_ball_update(data):
        """Handle ball position updates in pong party"""
        room_code = data.get('room_code')
        ball_x = data.get('ball_x', 0)
        ball_y = data.get('ball_y', 0)
        ball_dx = data.get('ball_dx', 1)
        ball_dy = data.get('ball_dy', 1)

        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            if game_state.get('game_key') == 'pong_party_multi':
                # Update ball position in game state
                game_state['ball'] = {
                    'x': ball_x,
                    'y': ball_y,
                    'dx': ball_dx,
                    'dy': ball_dy
                }
                # Sync to all players
                emit('ball_sync', game_state['ball'], room=room_code, include_self=False)

    @socketio.on('pong_paddle_move')
    def handle_pong_paddle_move(data):
        """Handle paddle movement in pong party"""
        user = get_current_user()
        room_code = data.get('room_code')
        paddle_y = data.get('paddle_y', 0)

        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            if game_state.get('game_key') == 'pong_party_multi':
                # Update paddle position
                if 'paddles' not in game_state:
                    game_state['paddles'] = {}
                game_state['paddles'][user.user_id] = paddle_y
                # Sync to all players
                emit('paddle_sync', {
                    'user_id': user.user_id,
                    'paddle_y': paddle_y
                }, room=room_code, include_self=False)

    @socketio.on('pong_score')
    def handle_pong_score(data):
        """Handle scoring in pong party"""
        room_code = data.get('room_code')
        scorer_id = data.get('scorer_id')

        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            if game_state.get('game_key') == 'pong_party_multi':
                # Award point to scorer
                game_state['scores'][scorer_id] = game_state['scores'].get(scorer_id, 0) + 1

                # Check for winner (first to 5 points)
                if game_state['scores'][scorer_id] >= 5:
                    end_multiplayer_game(room_code)
                else:
                    # Reset ball
                    emit('reset_ball', {}, room=room_code)

    @socketio.on('target_click')
    def handle_target_click(data):
        """Handle target clicks in Target Rush"""
        user = get_current_user()
        room_code = data.get('room_code')
        target_id = data.get('target_id')

        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            room = GameRoom.query.filter_by(room_code=room_code).first()

            if not room or game_state.get('game_key') != 'target_rush_multi':
                return

            # Check if target exists and hasn't been clicked
            if 'targets' not in game_state:
                game_state['targets'] = {}

            if target_id in game_state['targets'] and not game_state['targets'][target_id]['clicked']:
                target = game_state['targets'][target_id]
                points = target['points']
                game_state['scores'][user.user_id] = game_state['scores'].get(user.user_id, 0) + points
                game_state['targets'][target_id]['clicked'] = True
                game_state['targets'][target_id]['clicked_by'] = user.user_id

                # Notify all players
                emit('target_clicked', {
                    'target_id': target_id,
                    'clicked_by': user.user_id,
                    'points': points,
                    'scores': game_state['scores']
                }, room=room_code)

                # Spawn new target
                spawn_target(room_code)

    @socketio.on('color_expand')
    def handle_color_expand(data):
        """Handle color territory expansion in Color Clash"""
        user = get_current_user()
        room_code = data.get('room_code')
        position = data.get('position', {})

        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            room = GameRoom.query.filter_by(room_code=room_code).first()

            if not room or game_state.get('game_key') != 'color_clash_multi':
                return

            # Initialize territories if not exists
            if 'territories' not in game_state:
                game_state['territories'] = {}
                for uid in game_state['players']:
                    game_state['territories'][uid] = []

            # Add new territory point
            game_state['territories'][user.user_id].append(position)

            # Check for territory overlaps (simplified collision)
            for other_uid, territory in game_state['territories'].items():
                if other_uid != user.user_id:
                    for point in territory:
                        if abs(point.x - position.x) < 20 and abs(point.y - position.y) < 20:
                            # Collision! Remove some territory from other player
                            if len(territory) > 0:
                                territory.pop()
                                game_state['scores'][other_uid] = max(0, game_state['scores'].get(other_uid, 0) - 5)

            # Award points for expansion
            game_state['scores'][user.user_id] = game_state['scores'].get(user.user_id, 0) + 1

            # Sync territories
            emit('territory_update', {
                'territories': game_state['territories'],
                'scores': game_state['scores']
            }, room=room_code)

    def spawn_target(room_code):
        """Spawn a new target in Target Rush"""
        if room_code in ACTIVE_GAMES:
            game_state = ACTIVE_GAMES[room_code]
            if game_state.get('game_key') == 'target_rush_multi':
                target_id = f"target_{len(game_state.get('targets', {}))}"
                target = {
                    'id': target_id,
                    'x': Math.random() * 550 + 25,
                    'y': Math.random() * 350 + 25,
                    'points': -10 if random.random() > 0.8 else 10,  # 20% chance of penalty target
                    'clicked': False
                }
                game_state['targets'][target_id] = target

                emit('new_target', target, room=room_code)

                # Auto-spawn next target after delay
                socketio.sleep(2)
                spawn_target(room_code)

