from datetime import datetime
from src.models.models import db, Score, Achievement, Game, User
from src.utils.helpers import award_coins, award_xp
from src.utils.logger import get_logger

logger = get_logger()

GAME_CONFIGS = {
    "snake": {"name": "Snake Arcade", "icon": "🐍", "color": "#00ff88", "difficulty": "Easy"},
    "tictactoe": {"name": "Tic Tac Toe", "icon": "⭕", "color": "#00d4ff", "difficulty": "Easy"},
    "memory": {"name": "Memory Match", "icon": "🧠", "color": "#ff6b6b", "difficulty": "Medium"},
    "reaction": {"name": "Reaction Time", "icon": "⚡", "color": "#ffd700", "difficulty": "Medium"},
    "reaction_multi": {"name": "Reaction Arena", "icon": "⚡", "color": "#ffd700", "difficulty": "Medium", "is_multiplayer": True},
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
    "towerstack_multi": {"name": "Stack Battle", "icon": "🏗️", "color": "#f1c40f", "difficulty": "Medium", "is_multiplayer": True},
    "survival_dodge_multi": {"name": "Survival Dodge Arena", "icon": "💥", "color": "#e74c3c", "difficulty": "Hard", "is_multiplayer": True},
    "pong_party_multi": {"name": "Pong Party", "icon": "🏓", "color": "#3498db", "difficulty": "Medium", "is_multiplayer": True},
    "target_rush_multi": {"name": "Target Rush", "icon": "🎯", "color": "#e67e22", "difficulty": "Medium", "is_multiplayer": True},
    "color_clash_multi": {"name": "Color Clash", "icon": "🎨", "color": "#9b59b6", "difficulty": "Hard", "is_multiplayer": True},
}


def submit_score(user, game_key, score, play_time=0):
    """Submit game score with anti-cheat validation and balanced rewards"""
    try:
        # Validate input
        if score < 0 or not isinstance(score, int):
            return False, "Invalid score"
        
        if play_time < 0 or not isinstance(play_time, int):
            return False, "Invalid play time"
        
        # Import economy service for anti-cheat and reward calculation
        from src.services.economy_service import (
            validate_score, log_suspicious_score, calculate_balanced_rewards,
            update_daily_stats, is_daily_coin_cap_reached, is_daily_xp_cap_reached
        )
        
        # ANTI-CHEAT: Validate score
        is_valid, flags = validate_score(user.user_id, game_key, score, play_time)
        
        # Create score record
        score_record = Score(
            user_id=user.user_id,
            game_key=game_key,
            score=score,
            play_time=play_time,
            verified=is_valid # Mark score as verified or unverified based on validation
        )
        db.session.add(score_record)

        if not is_valid:
            log_suspicious_score(user.user_id, game_key, score, play_time, flags)
            logger.warning(f"Suspicious score: {user.username} - {game_key} - {score} - flags: {flags}")
        
        # Check daily caps
        if is_daily_coin_cap_reached(user.user_id) and is_daily_xp_cap_reached(user.user_id):
            db.session.commit()
            logger.info(f"Daily caps reached: {user.username}")
            return True, {
                'coins_earned': 0,
                'xp_earned': 0,
                'is_high_score': False,
                'message': 'Daily reward limits reached. Play again tomorrow!'
            }
        
        # Calculate balanced rewards (with diminishing returns and daily caps)
        # Note: We might want to only reward verified scores, or reward at a reduced rate for unverified
        coins_earned, xp_earned, is_high_score = calculate_balanced_rewards(
            user, game_key, score, play_time if is_valid else 0 # Example: penalize unverified scores in calculation
        )
        
        if not is_valid:
            # Further reduce rewards for unverified scores
            coins_earned = int(coins_earned * 0.1)
            xp_earned = int(xp_earned * 0.1)

        # Update user stats
        user.total_games_played += 1
        user.total_score += score
        user.coins += coins_earned
        user.xp += xp_earned
        
        # Update daily stats for cap tracking
        update_daily_stats(user.user_id, coins_earned, xp_earned)
        
        # Award XP-based level up using new progression system
        if xp_earned > 0:
            from src.services.progression_service import add_xp
            level_up_occurred, new_level, rewards = add_xp(user, xp_earned, source='game')
            
            if level_up_occurred:
                unlock_achievement(user, 'level_up', f'Reached Level {new_level}!')
                
                # Also sync the old player_level field for backwards compatibility
                user.player_level = new_level
        
        # Check if high score (only for verified scores)
        if is_high_score and is_valid:
            unlock_achievement(user, 'high_score', 'High Score Achiever!')
        
        # Update game play count
        game = Game.query.filter_by(game_key=game_key).first()
        if game:
            game.play_count += 1
        
        db.session.commit()
        
        logger.info(f"Score submitted: {user.username} - {game_key} - {score} (coins: {coins_earned}, xp: {xp_earned})")
        
        # Check for various achievements
        check_achievements(user, game_key, score, is_high_score, is_valid)
        
        return True, {
            'coins_earned': coins_earned,
            'xp_earned': xp_earned,
            'is_high_score': is_high_score and is_valid,
            'score_flagged': not is_valid
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting score: {e}", exc_info=True)
        return False, "Error saving score"


def get_high_score(user_id, game_key):
    """Get user's high score for a game (verified only)"""
    try:
        high_score = Score.query.filter_by(
            user_id=user_id,
            game_key=game_key,
            verified=True # Only count verified scores
        ).order_by(Score.score.desc()).first()
        
        return high_score.score if high_score else None
    except Exception as e:
        logger.error(f"Error fetching high score: {e}")
        return None


def get_user_scores(user_id, limit=10):
    """Get user's recent scores"""
    try:
        scores = Score.query.filter_by(user_id=user_id)\
            .order_by(Score.achieved_at.desc())\
            .limit(limit)\
            .all()
        return scores
    except Exception as e:
        logger.error(f"Error fetching user scores: {e}")
        return []


def get_leaderboard(game_key=None, limit=10):
    """Get global leaderboard (verified scores only)"""
    try:
        # Use raw SQL to avoid SQLAlchemy issues
        from sqlalchemy import text
        
        if game_key:
            query_str = """
                SELECT u.user_id, u.username, 
                       COALESCE(SUM(s.score), 0) as total_score,
                       COUNT(s.score_id) as games_played
                FROM users u
                LEFT JOIN scores s ON u.user_id = s.user_id AND s.verified = 1 AND s.game_key = :game_key
                GROUP BY u.user_id, u.username
                HAVING games_played > 0
                ORDER BY total_score DESC
                LIMIT :limit
            """
            result = db.session.execute(text(query_str), {'game_key': game_key, 'limit': limit})
        else:
            query_str = """
                SELECT u.user_id, u.username, 
                       COALESCE(SUM(s.score), 0) as total_score,
                       COUNT(s.score_id) as games_played
                FROM users u
                LEFT JOIN scores s ON u.user_id = s.user_id AND s.verified = 1
                GROUP BY u.user_id, u.username
                HAVING games_played > 0
                ORDER BY total_score DESC
                LIMIT :limit
            """
            result = db.session.execute(text(query_str), {'limit': limit})
        
        leaderboard = []
        for row in result:
            leaderboard.append({
                'user_id': row[0],
                'username': row[1],
                'total_score': int(row[2]) if row[2] else 0,
                'games_played': int(row[3]) if row[3] else 0
            })
        
        return leaderboard
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        return []


def unlock_achievement(user, achievement_key, achievement_name):
    """Unlock an achievement for user"""
    try:
        # Check if already unlocked
        existing = Achievement.query.filter_by(
            user_id=user.user_id,
            achievement_key=achievement_key
        ).first()
        
        if existing:
            return False
        
        achievement = Achievement(
            user_id=user.user_id,
            achievement_key=achievement_key,
            achievement_name=achievement_name
        )
        
        db.session.add(achievement)
        db.session.flush()  # Don't commit yet, let caller commit
        
        logger.info(f"Achievement unlocked: {user.username} - {achievement_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error unlocking achievement: {e}")
        return False


def get_user_achievements(user_id):
    """Get user's achievements"""
    try:
        achievements = Achievement.query.filter_by(user_id=user_id)\
            .order_by(Achievement.achieved_at.desc())\
            .all()
        return achievements
    except Exception as e:
        logger.error(f"Error fetching achievements: {e}")
        return []


def get_game_config(game_key):
    """Get game configuration"""
    return GAME_CONFIGS.get(game_key)


def get_all_games():
    """Get all games from database"""
    try:
        games = Game.query.order_by(Game.play_count.desc()).all()
        return games
    except Exception as e:
        logger.error(f"Error fetching games: {e}")
        return []


def seed_games():
    """Seed games into database"""
    try:
        for key, config in GAME_CONFIGS.items():
            game = Game.query.filter_by(game_key=key).first()
            if not game:
                game = Game(
                    game_key=key,
                    name=config['name'],
                    category='Arcade',
                    difficulty=config['difficulty'],
                    icon=config['icon'],
                    color=config['color']
                )
                db.session.add(game)
        
        db.session.commit()
        logger.info("Games seeded successfully")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error seeding games: {e}")


def check_achievements(user, game_key, score, is_high_score, is_valid):
    """Check and unlock achievements based on user progress"""
    try:
        if not is_valid:
            return  # Don't award achievements for invalid scores

        # First Game Achievement
        if user.total_games_played == 1:
            unlock_achievement(user, 'first_game', 'Welcome to Arcadia Hub!')

        # Games Played Milestones
        games_milestones = [10, 50, 100, 500, 1000]
        for milestone in games_milestones:
            if user.total_games_played == milestone:
                unlock_achievement(user, f'games_{milestone}', f'Played {milestone} Games!')

        # High Score Achievements
        if is_high_score:
            unlock_achievement(user, f'high_score_{game_key}', f'High Score in {GAME_CONFIGS.get(game_key, {}).get("name", game_key)}!')

        # Score-based achievements
        if score >= 1000:
            unlock_achievement(user, 'score_1000', 'Thousand Point Club!')
        if score >= 10000:
            unlock_achievement(user, 'score_10000', 'Ten Thousand Club!')
        if score >= 50000:
            unlock_achievement(user, 'score_50000', 'Fifty Thousand Club!')

        # Daily Streak Achievements
        if user.streak >= 7:
            unlock_achievement(user, 'streak_7', 'Week Warrior!')
        if user.streak >= 30:
            unlock_achievement(user, 'streak_30', 'Monthly Master!')

        # Coin Collector
        if user.coins >= 1000:
            unlock_achievement(user, 'coins_1000', 'Coin Collector!')
        if user.coins >= 10000:
            unlock_achievement(user, 'coins_10000', 'Coin Hoarder!')

        # Level Achievements
        if user.player_level >= 5:
            unlock_achievement(user, 'level_5', 'Rising Star!')
        if user.player_level >= 10:
            unlock_achievement(user, 'level_10', 'Arcade Veteran!')
        if user.player_level >= 25:
            unlock_achievement(user, 'level_25', 'Gaming Legend!')

        # Game-specific achievements
        if game_key == 'reaction' and score < 200:
            unlock_achievement(user, 'lightning_fast', 'Lightning Fast Reactions!')
        elif game_key == 'snake' and score >= 1000:
            unlock_achievement(user, 'snake_master', 'Snake Master!')
        elif game_key == 'tictactoe':
            unlock_achievement(user, 'tic_tac_toe_winner', 'Tic Tac Toe Champion!')

        # Perfect Game (if applicable)
        # This would need game-specific logic

        db.session.commit()  # Commit any new achievements

    except Exception as e:
        logger.error(f"Error checking achievements: {e}")
        db.session.rollback()
