from datetime import datetime
from src.models.models import db, PlayerProgression, User, RankHistory
from src.utils.logger import get_logger

logger = get_logger()

# ============================================
# XP CURVE FORMULA & PROGRESSION CONSTANTS
# ============================================

# XP formula: 100 * (N² + 2N + 50)
# Level 1: 153 | Level 10: 10,530 | Level 50: 507,150 | Level 100: 2,030,150
# Prestige every 100 levels

def calculate_xp_for_level(level):
    """
    Calculate total XP required to reach a specific level.
    Formula: XP_for_level(N) = 100 * (N² + 2N + 50)
    """
    if level < 1:
        return 0
    # Simplified cumulative formula for testing
    total = 0
    for i in range(1, level):
        total += 100 * (i**2 + 2*i + 50)
    return total


def calculate_xp_for_next_level(level):
    """Calculate XP needed to go from current level to next level"""
    return 100 * (level**2 + 2*level + 50)


def get_or_create_progression(user_id):
    """Get or create progression record for user"""
    try:
        progression = PlayerProgression.query.filter_by(user_id=user_id).first()
        
        if not progression:
            progression = PlayerProgression(
                user_id=user_id,
                current_level=1,
                total_xp=0,
                xp_for_next_level=calculate_xp_for_next_level(1),
                prestige_count=0
            )
            db.session.add(progression)
            db.session.flush()
        
        return progression
    except Exception as e:
        logger.error(f"Error getting/creating progression: {e}")
        return None


def add_xp(user, xp_amount, source='game'):
    """
    Add XP to user and handle level-ups.
    
    Args:
        user: User object
        xp_amount: Amount of XP to add
        source: Source of XP (game, mission, achievement, etc.)
    
    Returns:
        Tuple: (level_up_occurred, new_level, rewards_earned)
    """
    try:
        if xp_amount <= 0:
            return False, user.player_level, {}
        
        progression = get_or_create_progression(user.user_id)
        if not progression:
            return False, user.player_level, {}
        
        progression.total_xp += xp_amount
        level_up_occurred = False
        rewards_earned = {}
        old_level = progression.current_level
        
        # Check for level ups (can level up multiple times)
        total_xp_for_current = calculate_xp_for_level(progression.current_level)
        
        while progression.total_xp >= total_xp_for_current + calculate_xp_for_next_level(progression.current_level):
            progression.current_level += 1
            level_up_occurred = True
            progression.last_levelup_at = datetime.utcnow()
            
            # Calculate level-up rewards (coins + bonus items)
            levelup_coins = 100 + (progression.current_level * 10)
            user.coins += levelup_coins
            rewards_earned['coins'] = levelup_coins
            rewards_earned['new_level'] = progression.current_level
            
            logger.info(f"Level up: {user.username} - Level {progression.current_level} (XP: {progression.total_xp})")
            
            # Check for prestige (every 100 levels)
            if progression.current_level % 100 == 0:
                handle_prestige(user, progression)
                rewards_earned['prestige'] = progression.prestige_count
        
        # Sync user's player_level to UserProgression
        user.player_level = progression.current_level
        
        # Update XP for next level
        progression.xp_for_next_level = calculate_xp_for_next_level(progression.current_level)
        
        db.session.flush()
        
        return level_up_occurred, progression.current_level, rewards_earned
        
    except Exception as e:
        logger.error(f"Error adding XP: {e}", exc_info=True)
        db.session.rollback()
        return False, user.player_level, {}


def handle_prestige(user, progression):
    """
    Handle prestige milestone (every 100 levels).
    Awards bonus coins, XP boost for next 10 levels.
    """
    try:
        progression.prestige_count += 1
        prestige_bonus_coins = 500 * progression.prestige_count
        user.coins += prestige_bonus_coins
        
        logger.info(f"Prestige reached: {user.username} - Prestige #{progression.prestige_count} (Coins: {prestige_bonus_coins})")
        
    except Exception as e:
        logger.error(f"Error handling prestige: {e}")


def get_progression_info(user_id):
    """Get detailed progression information for user"""
    try:
        progression = PlayerProgression.query.filter_by(user_id=user_id).first()
        user = User.query.get(user_id)
        
        if not progression or not user:
            return None
        
        # Calculate XP for current and next level
        xp_for_current_level = calculate_xp_for_level(progression.current_level)
        xp_for_next_level_total = xp_for_current_level + calculate_xp_for_next_level(progression.current_level)
        xp_progress_in_level = progression.total_xp - xp_for_current_level
        xp_needed_for_next = xp_for_next_level_total - progression.total_xp
        xp_level_percentage = (xp_progress_in_level / calculate_xp_for_next_level(progression.current_level)) * 100 if calculate_xp_for_next_level(progression.current_level) > 0 else 0
        
        return {
            'user_id': user_id,
            'current_level': progression.current_level,
            'total_xp': progression.total_xp,
            'xp_for_current_level': xp_for_current_level,
            'xp_for_next_level': xp_for_next_level_total,
            'xp_in_current_level': xp_progress_in_level,
            'xp_needed_for_next': xp_needed_for_next,
            'xp_level_percentage': round(xp_level_percentage, 1),
            'prestige_count': progression.prestige_count,
            'last_levelup_at': progression.last_levelup_at.isoformat() if progression.last_levelup_at else None,
            'coins': user.coins
        }
    except Exception as e:
        logger.error(f"Error getting progression info: {e}")
        return None


def claim_level_reward(user_id, level):
    """
    Claim rewards for reaching a specific level.
    Prevents double-claiming through inventory system.
    """
    try:
        progression = PlayerProgression.query.filter_by(user_id=user_id).first()
        
        if not progression or progression.current_level < level:
            return False, "Level not reached yet"
        
        # Check if already claimed (using achievement system)
        from src.services.game_service import unlock_achievement
        from src.models.models import Achievement
        
        user = User.query.get(user_id)
        achievement_key = f"level_reward_{level}"
        
        existing = Achievement.query.filter_by(
            user_id=user_id,
            achievement_key=achievement_key
        ).first()
        
        if existing:
            return False, "Reward already claimed"
        
        # Award reward based on level
        reward_coins = 100 + (level * 10)
        reward_xp = 50 + (level * 5)
        
        user.coins += reward_coins
        
        unlock_achievement(user, achievement_key, f"Level {level} Reward")
        db.session.commit()
        
        logger.info(f"Level reward claimed: {user.username} - Level {level} (Coins: {reward_coins})")
        
        return True, {
            'coins': reward_coins,
            'xp': reward_xp,
            'level': level
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error claiming level reward: {e}")
        return False, "Error claiming reward"


def get_xp_leaderboard(limit=100, prestige_filter=None):
    """
    Get XP/Level leaderboard.
    
    Args:
        limit: Number of top players to return
        prestige_filter: Filter by prestige level (optional)
    
    Returns:
        List of leaderboard entries
    """
    try:
        query = PlayerProgression.query.order_by(PlayerProgression.current_level.desc(), PlayerProgression.total_xp.desc())
        
        if prestige_filter is not None:
            query = query.filter_by(prestige_count=prestige_filter)
        
        progressions = query.limit(limit).all()
        
        leaderboard = []
        for i, prog in enumerate(progressions, 1):
            user = User.query.get(prog.user_id)
            if user:
                leaderboard.append({
                    'rank': i,
                    'user_id': user.user_id,
                    'username': user.username,
                    'level': prog.current_level,
                    'total_xp': prog.total_xp,
                    'prestige': prog.prestige_count
                })
        
        return leaderboard
        
    except Exception as e:
        logger.error(f"Error fetching XP leaderboard: {e}")
        return []


def get_next_milestone(user_id):
    """Get information about player's next level milestone"""
    try:
        progression = get_or_create_progression(user_id)
        if not progression:
            return None
        
        xp_for_current = calculate_xp_for_level(progression.current_level)
        xp_for_next = xp_for_current + calculate_xp_for_next_level(progression.current_level)
        xp_progress = progression.total_xp - xp_for_current
        xp_needed = xp_for_next - progression.total_xp
        
        # Estimate time to next level (assuming average 100 XP per game, 5 min per game)
        avg_xp_per_game = 100
        estimated_games = xp_needed / avg_xp_per_game
        estimated_minutes = estimated_games * 5
        
        return {
            'current_level': progression.current_level,
            'next_level': progression.current_level + 1,
            'xp_progress': xp_progress,
            'xp_needed': xp_needed,
            'xp_total_for_level': calculate_xp_for_next_level(progression.current_level),
            'percentage': round((xp_progress / calculate_xp_for_next_level(progression.current_level)) * 100, 1) if calculate_xp_for_next_level(progression.current_level) > 0 else 0,
            'estimated_games_to_level': int(estimated_games),
            'estimated_minutes_to_level': int(estimated_minutes)
        }
        
    except Exception as e:
        logger.error(f"Error getting next milestone: {e}")
        return None

