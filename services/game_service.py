from datetime import datetime
from models.models import db, Score, Achievement, Game, User
from utils.helpers import award_coins, award_xp
from utils.logger import get_logger

logger = get_logger()

GAME_CONFIGS = {
    "snake": {"name": "Snake Arcade", "icon": "🐍", "color": "#00ff88", "difficulty": "Easy"},
    "tictactoe": {"name": "Tic Tac Toe", "icon": "⭕", "color": "#00d4ff", "difficulty": "Easy"},
    "memory": {"name": "Memory Match", "icon": "🧠", "color": "#ff6b6b", "difficulty": "Medium"},
    "reaction": {"name": "Reaction Time", "icon": "⚡", "color": "#ffd700", "difficulty": "Medium"},
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
    "colorswitch": {"name": "Color Switch", "icon": "🎨", "color": "#e91e63", "difficulty": "Hard"}
}


def submit_score(user, game_key, score, play_time=0):
    """Submit game score and award rewards"""
    try:
        if score < 0:
            return False, "Invalid score"
        
        # Create score record
        score_record = Score(
            user_id=user.user_id,
            game_key=game_key,
            score=score,
            play_time=play_time
        )
        
        db.session.add(score_record)
        
        # Calculate rewards
        coins_earned = max(1, score // 10)
        xp_earned = max(5, score // 5)
        
        # Check if high score
        high_score = get_high_score(user.user_id, game_key)
        if high_score is None or score > high_score:
            coins_earned += 25  # Bonus for high score
            xp_earned += 50
            achievement = unlock_achievement(user, 'high_score', 'High Score Achiever!')
        
        # Update user stats
        user.total_games_played += 1
        user.total_score += score
        
        # Award coins and XP
        award_coins(user, coins_earned)
        award_xp(user, xp_earned)
        
        # Update game play count
        game = Game.query.filter_by(game_key=game_key).first()
        if game:
            game.play_count += 1
        
        db.session.commit()
        
        logger.info(f"Score submitted: {user.username} - {game_key} - {score}")
        
        return True, {
            'coins_earned': coins_earned,
            'xp_earned': xp_earned,
            'is_high_score': high_score is None or score > high_score
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting score: {e}")
        return False, "Error saving score"


def get_high_score(user_id, game_key):
    """Get user's high score for a game"""
    try:
        high_score = Score.query.filter_by(
            user_id=user_id,
            game_key=game_key
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
    """Get global leaderboard"""
    try:
        query = db.session.query(
            Score.user_id,
            User.username,
            db.func.sum(Score.score).label('total_score'),
            db.func.count(Score.score_id).label('games_played')
        ).join(User, Score.user_id == User.user_id)
        
        if game_key:
            query = query.filter(Score.game_key == game_key)
        
        leaderboard = query.group_by(Score.user_id, User.username)\
            .order_by(db.desc('total_score'))\
            .limit(limit)\
            .all()
        
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
