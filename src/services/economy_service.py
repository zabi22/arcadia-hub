from datetime import date, datetime
from src.models.models import db, DailyStats, User, AntiCheatLog
from src.utils.logger import get_logger

logger = get_logger()

# Game-specific score limits to detect cheating
GAME_LIMITS = {
    "snake": {"max_score": 10000, "max_time": 600},
    "tictactoe": {"max_score": 1000, "max_time": 300},
    "memory": {"max_score": 5000, "max_time": 600},
    "reaction": {"max_score": 1000, "max_time": 120},
    "wordle": {"max_score": 5000, "max_time": 300},
    "pong": {"max_score": 50000, "max_time": 900},
    "game2048": {"max_score": 100000, "max_time": 1200},
    "flappy": {"max_score": 50000, "max_time": 600},
    "runner": {"max_score": 100000, "max_time": 600},
    "breakout": {"max_score": 50000, "max_time": 600},
    "jumper": {"max_score": 50000, "max_time": 600},
    "dodge": {"max_score": 100000, "max_time": 600},
    "aimtrainer": {"max_score": 10000, "max_time": 300},
    "rhythm": {"max_score": 50000, "max_time": 600},
    "maze": {"max_score": 10000, "max_time": 600},
    "shooting": {"max_score": 50000, "max_time": 600},
    "towerstack": {"max_score": 5000, "max_time": 600},
    "colorswitch": {"max_score": 100000, "max_time": 600},
}

# Daily earning caps
DAILY_COIN_CAP = 500
DAILY_XP_CAP = 1000


def get_or_create_daily_stats(user_id):
    """Get or create daily stats for user"""
    try:
        today = date.today()
        stats = DailyStats.query.filter_by(user_id=user_id, date=today).first()

        if not stats:
            stats = DailyStats(user_id=user_id, date=today, coins_earned=0, xp_earned=0, games_played=0)
            db.session.add(stats)
            db.session.commit()

        return stats
    except Exception as e:
        logger.error(f"Error getting daily stats: {e}")
        return None


def validate_score(user_id, game_key, score, play_time):
    """
    Validate score against anti-cheat rules
    Returns: (is_valid, flags_list)
    """
    flags = []

    try:
        # Check game-specific limits
        if game_key in GAME_LIMITS:
            limits = GAME_LIMITS[game_key]

            if score > limits['max_score']:
                flags.append('score_too_high')

            if play_time < 5:  # Minimum 5 seconds
                flags.append('play_time_too_short')

            if play_time > limits['max_time']:
                flags.append('play_time_too_long')

        # Check if score is anomalous compared to user's average
        if play_time >= 10:  # Only check if play time is reasonable
            from src.models.models import Score
            # Only consider verified scores for average calculation
            user_scores = Score.query.filter_by(user_id=user_id, game_key=game_key, verified=True).all()

            if len(user_scores) >= 5:  # Need at least 5 scores to calculate average
                avg_score = sum(s.score for s in user_scores) / len(user_scores)

                # If score is more than 5x the average, flag it
                if score > (avg_score * 5):
                    flags.append('avg_anomaly')

        is_valid = len(flags) == 0
        return is_valid, flags

    except Exception as e:
        logger.error(f"Error validating score: {e}")
        return True, []  # Allow if validation fails


def log_suspicious_score(user_id, game_key, score, play_time, flags):
    """Log a suspicious score for admin review"""
    try:
        log_entry = AntiCheatLog(
            user_id=user_id,
            game_key=game_key,
            score=score,
            play_time=play_time,
            flags=','.join(flags),
            verified=False
        )
        db.session.add(log_entry)
        db.session.commit()
        logger.warning(f"Suspicious score logged: user={user_id}, game={game_key}, score={score}, flags={flags}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error logging suspicious score: {e}")


def calculate_balanced_rewards(user, game_key, score, play_time):
    """
    Calculate balanced coin and XP rewards

    Base formula:
    - coins = max(1, score // 10) with diminishing returns
    - xp = max(5, score // 5) with diminishing returns

    Diminishing returns:
    - After 3 plays of same game today: 30% reward
    - Based on daily total earnings cap
    """
    try:
        today = date.today()
        stats = get_or_create_daily_stats(user.user_id)

        if not stats: # Should not happen if get_or_create_daily_stats works, but for safety
            return 1, 5, False

        # Base rewards
        base_coins = max(1, score // 10)
        base_xp = max(5, score // 5)

        # Check if high score (bonus) - only consider verified scores for high score
        from src.models.models import Score
        high_score = Score.query.filter_by(
            user_id=user.user_id,
            game_key=game_key,
            verified=True
        ).order_by(Score.score.desc()).first()

        is_high_score = high_score is None or score > high_score.score
        if is_high_score:
            base_coins += 25
            base_xp += 50

        # Diminishing returns based on total games played today (from DailyStats)
        # This is a simplification; a more granular approach would track plays per game per day.
        # For now, we use total games played today as a proxy for diminishing returns.
        games_played_today = stats.games_played

        diminish_factor = 1.0
        if games_played_today >= 5: # More aggressive diminishing returns for overall play
            diminish_factor = 0.2
        elif games_played_today >= 3:
            diminish_factor = 0.5
        elif games_played_today >= 1:
            diminish_factor = 0.8

        # Apply diminishing returns
        coins = int(base_coins * diminish_factor)
        xp = int(base_xp * diminish_factor)

        # Apply daily caps
        coins_available = max(0, DAILY_COIN_CAP - stats.coins_earned)
        xp_available = max(0, DAILY_XP_CAP - stats.xp_earned)

        coins = min(coins, coins_available)
        xp = min(xp, xp_available)

        return coins, xp, is_high_score

    except Exception as e:
        logger.error(f"Error calculating rewards: {e}")
        return 1, 5, False


def update_daily_stats(user_id, coins_earned, xp_earned):
    """Update daily stats for user"""
    try:
        stats = get_or_create_daily_stats(user_id)
        if stats:
            stats.coins_earned += coins_earned
            stats.xp_earned += xp_earned
            stats.games_played += 1 # Increment games played
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating daily stats: {e}")


def is_daily_coin_cap_reached(user_id):
    """Check if user has reached daily coin cap"""
    try:
        stats = get_or_create_daily_stats(user_id)
        return stats and stats.coins_earned >= DAILY_COIN_CAP
    except Exception as e:
        logger.error(f"Error checking daily coin cap: {e}")
        return False


def is_daily_xp_cap_reached(user_id):
    """Check if user has reached daily XP cap"""
    try:
        stats = get_or_create_daily_stats(user_id)
        return stats and stats.xp_earned >= DAILY_XP_CAP
    except Exception as e:
        logger.error(f"Error checking daily XP cap: {e}")
        return False
