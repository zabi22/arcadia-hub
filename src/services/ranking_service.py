from datetime import datetime
from src.models.models import db, RankTier, RankHistory, User
from src.utils.logger import get_logger

logger = get_logger()

# ============================================
# RANKING SYSTEM CONSTANTS
# ============================================

# Rank tier thresholds (Elo-based: 800-3000)
RANK_TIERS = {
    'Bronze': (800, 1200),
    'Silver': (1200, 1600),
    'Gold': (1600, 2000),
    'Platinum': (2000, 2400),
    'Diamond': (2400, 3000),
    'Legend': (3000, 99999)
}

# Divisions: I (highest), II, III, IV (lowest) for Bronze-Diamond
DIVISIONS = ['I', 'II', 'III', 'IV']

# Elo K-factor (rating volatility)
K_FACTOR_STANDARD = 32
K_FACTOR_NEW_PLAYER = 40  # First 10 games
K_FACTOR_VETERAN = 16  # 500+ games

# Matchmaking settings
MATCHMAKING_BAND = 200  # ±200 rating difference acceptable


def get_or_create_rank(user_id, season=1):
    """Get or create rank record for user"""
    try:
        rank_tier = RankTier.query.filter_by(user_id=user_id, season=season).first()
        
        if not rank_tier:
            rank_tier = RankTier(
                user_id=user_id,
                season=season,
                rank_name='Bronze',
                rank_points=1000,  # Start at 1000 Elo
                division='IV'
            )
            db.session.add(rank_tier)
            db.session.flush()
        
        return rank_tier
    except Exception as e:
        logger.error(f"Error getting/creating rank: {e}")
        return None


def calculate_elo_change(player_rating, opponent_rating, match_result, k_factor=K_FACTOR_STANDARD):
    """
    Calculate Elo rating change using standard Elo formula.
    
    Args:
        player_rating: Player's current Elo
        opponent_rating: Opponent's current Elo
        match_result: 'win', 'loss', or 'draw'
        k_factor: K-factor (volatility)
    
    Returns:
        Elo change amount (can be negative)
    """
    # Expected win probability
    expected = 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))
    
    # Result score
    if match_result == 'win':
        score = 1
    elif match_result == 'loss':
        score = 0
    else:  # draw
        score = 0.5
    
    # Elo change
    change = k_factor * (score - expected)
    
    return int(round(change))


def get_k_factor(user):
    """Determine appropriate K-factor based on user's ranked game count"""
    rank_tier = RankTier.query.filter_by(user_id=user.user_id, season=1).first()
    
    if not rank_tier:
        return K_FACTOR_NEW_PLAYER
    
    if rank_tier.games_played_ranked < 10:
        return K_FACTOR_NEW_PLAYER
    elif rank_tier.games_played_ranked >= 500:
        return K_FACTOR_VETERAN
    else:
        return K_FACTOR_STANDARD


def update_rank_tier(user_id, new_elo, game_type='ranked', match_result=None, opponent_rating=None):
    """
    Update player's rank tier based on Elo rating.
    Handles promotions, demotions, and tier changes.
    
    Args:
        user_id: User ID
        new_elo: New Elo rating
        game_type: Type of game (ranked, multiplayer, etc.)
        match_result: Result of match (win, loss, draw)
        opponent_rating: Opponent's Elo (for logging)
    
    Returns:
        Tuple: (rank_changed, old_rank, new_rank, message)
    """
    try:
        rank_tier = get_or_create_rank(user_id, season=1)
        user = User.query.get(user_id)
        
        if not rank_tier or not user:
            return False, None, None, "Unable to update rank"
        
        old_rank_name = rank_tier.rank_name
        old_rank_points = rank_tier.rank_points
        
        # Update rating
        rank_tier.rank_points = max(800, min(3000, new_elo))  # Clamp between 800-3000
        rank_tier.last_rank_update = datetime.utcnow()
        
        # Determine new tier and division
        new_rank_name = 'Bronze'
        new_division = 'IV'
        
        for tier, (min_elo, max_elo) in RANK_TIERS.items():
            if min_elo <= rank_tier.rank_points < max_elo:
                new_rank_name = tier
                break
        
        # Calculate division (only for Bronze-Diamond, not Legend)
        if new_rank_name != 'Legend':
            tier_min, tier_max = RANK_TIERS[new_rank_name]
            tier_range = tier_max - tier_min
            progress = rank_tier.rank_points - tier_min
            division_index = int((progress / tier_range) * 4)
            division_index = min(3, max(0, division_index))
            new_division = DIVISIONS[division_index]
        
        rank_tier.rank_name = new_rank_name
        rank_tier.division = new_division if new_rank_name != 'Legend' else None
        
        # Track peak rank
        if rank_tier.rank_points > rank_tier.peak_rank_points:
            rank_tier.peak_rank_name = new_rank_name
            rank_tier.peak_rank_points = rank_tier.rank_points
        
        # Update game statistics
        rank_tier.games_played_ranked += 1
        if match_result == 'win':
            rank_tier.wins_ranked += 1
        elif match_result == 'loss':
            rank_tier.losses_ranked += 1
        
        # Update user's Elo
        user.elo_rating = rank_tier.rank_points
        user.rank_tier = new_rank_name
        
        rank_changed = (old_rank_name != new_rank_name) or (rank_tier.division != DIVISIONS[int((rank_tier.rank_points - RANK_TIERS[new_rank_name][0]) / (RANK_TIERS[new_rank_name][1] - RANK_TIERS[new_rank_name][0]) * 4)])
        
        # Log rank history
        points_delta = rank_tier.rank_points - old_rank_points
        log_rank_change(
            user_id=user_id,
            game_type=game_type,
            old_rank_name=old_rank_name,
            old_rank_points=old_rank_points,
            new_rank_name=new_rank_name,
            new_rank_points=rank_tier.rank_points,
            points_delta=points_delta,
            match_result=match_result,
            reason=f"Ranked match result: {match_result.upper()}"
        )
        
        db.session.flush()
        
        message = f"Rating: {old_rank_points} → {rank_tier.rank_points} ({points_delta:+d})"
        
        return rank_changed, old_rank_name, new_rank_name, message
        
    except Exception as e:
        logger.error(f"Error updating rank tier: {e}", exc_info=True)
        db.session.rollback()
        return False, None, None, "Error updating rank"


def submit_ranked_result(player_ids, player_elos, results, game_type='ranked'):
    """
    Submit results from a ranked multiplayer game.
    
    Args:
        player_ids: List of player IDs
        player_elos: List of current Elo ratings
        results: List of placement/results (1st place, 2nd, etc.)
        game_type: Type of ranked game
    
    Returns:
        List of rank update results
    """
    try:
        rank_updates = []
        
        for i, player_id in enumerate(player_ids):
            placement = results[i] if i < len(results) else None
            current_elo = player_elos[i] if i < len(player_elos) else 1000
            
            # Determine match result based on placement
            if placement == 1:
                match_result = 'win'
                elo_change = 20  # Victory bonus
            elif placement == 2:
                match_result = 'loss'
                elo_change = -10  # Second place penalty
            else:
                match_result = 'loss'
                elo_change = -20  # Lower placement penalty
            
            new_elo = current_elo + elo_change
            
            rank_changed, old_rank, new_rank, message = update_rank_tier(
                user_id=player_id,
                new_elo=new_elo,
                game_type=game_type,
                match_result=match_result,
                opponent_rating=None
            )
            
            rank_updates.append({
                'user_id': player_id,
                'rank_changed': rank_changed,
                'old_rank': old_rank,
                'new_rank': new_rank,
                'message': message
            })
        
        db.session.commit()
        return rank_updates
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error submitting ranked results: {e}")
        return []


def get_rank_info(user_id):
    """Get current ranking information for user"""
    try:
        rank_tier = RankTier.query.filter_by(user_id=user_id, season=1).first()
        user = User.query.get(user_id)
        
        if not rank_tier or not user:
            return None
        
        # Calculate progress to next rank tier
        tier_min, tier_max = RANK_TIERS[rank_tier.rank_name]
        tier_progress = rank_tier.rank_points - tier_min
        tier_range = tier_max - tier_min
        tier_percentage = (tier_progress / tier_range) * 100 if tier_range > 0 else 0
        
        # Points to next tier
        points_to_next = tier_max - rank_tier.rank_points if tier_max <= rank_tier.rank_points else tier_max - rank_tier.rank_points
        
        # Win rate
        total_ranked_games = rank_tier.wins_ranked + rank_tier.losses_ranked
        win_rate = (rank_tier.wins_ranked / total_ranked_games * 100) if total_ranked_games > 0 else 0
        
        return {
            'user_id': user_id,
            'username': user.username,
            'rank_tier': rank_tier.rank_name,
            'division': rank_tier.division,
            'rank_points': rank_tier.rank_points,
            'tier_min': tier_min,
            'tier_max': tier_max,
            'tier_progress_percentage': round(tier_percentage, 1),
            'points_to_next_tier': max(0, tier_max - rank_tier.rank_points),
            'peak_rank_tier': rank_tier.peak_rank_name,
            'peak_rank_points': rank_tier.peak_rank_points,
            'games_played': rank_tier.games_played_ranked,
            'wins': rank_tier.wins_ranked,
            'losses': rank_tier.losses_ranked,
            'win_rate': round(win_rate, 1),
            'last_rank_update': rank_tier.last_rank_update.isoformat() if rank_tier.last_rank_update else None,
            'season': rank_tier.season
        }
        
    except Exception as e:
        logger.error(f"Error getting rank info: {e}")
        return None


def log_rank_change(user_id, game_type, old_rank_name, old_rank_points, new_rank_name, new_rank_points, points_delta, match_result, reason):
    """Log rank change to history"""
    try:
        history = RankHistory(
            user_id=user_id,
            game_type=game_type,
            old_rank_name=old_rank_name,
            old_rank_points=old_rank_points,
            new_rank_name=new_rank_name,
            new_rank_points=new_rank_points,
            points_delta=points_delta,
            match_result=match_result,
            reason=reason
        )
        db.session.add(history)
        db.session.flush()
    except Exception as e:
        logger.error(f"Error logging rank change: {e}")


def get_ranked_leaderboard(season=1, limit=100):
    """Get ranked leaderboard sorted by Elo rating"""
    try:
        rank_tiers = RankTier.query.filter_by(season=season)\
            .order_by(RankTier.rank_points.desc())\
            .limit(limit)\
            .all()
        
        leaderboard = []
        for i, rank in enumerate(rank_tiers, 1):
            user = User.query.get(rank.user_id)
            if user:
                rank_display = f"{rank.rank_name}"
                if rank.division and rank.rank_name != 'Legend':
                    rank_display += f" {rank.division}"
                
                leaderboard.append({
                    'rank': i,
                    'user_id': user.user_id,
                    'username': user.username,
                    'tier': rank.rank_name,
                    'division': rank.division,
                    'rank_display': rank_display,
                    'rating': rank.rank_points,
                    'wins': rank.wins_ranked,
                    'losses': rank.losses_ranked,
                    'win_rate': round((rank.wins_ranked / (rank.wins_ranked + rank.losses_ranked) * 100) if (rank.wins_ranked + rank.losses_ranked) > 0 else 0, 1)
                })
        
        return leaderboard
        
    except Exception as e:
        logger.error(f"Error fetching ranked leaderboard: {e}")
        return []


def get_rank_history(user_id, limit=50):
    """Get rank change history for user"""
    try:
        history = RankHistory.query.filter_by(user_id=user_id)\
            .order_by(RankHistory.created_at.desc())\
            .limit(limit)\
            .all()
        
        history_data = []
        for record in history:
            history_data.append({
                'game_type': record.game_type,
                'old_rank': record.old_rank_name,
                'new_rank': record.new_rank_name,
                'points_delta': record.points_delta,
                'match_result': record.match_result,
                'reason': record.reason,
                'timestamp': record.created_at.isoformat()
            })
        
        return history_data
        
    except Exception as e:
        logger.error(f"Error fetching rank history: {e}")
        return []


def reset_season(current_season):
    """
    Reset rankings for new season.
    Top 100 retain Legend status, others drop rating by 400 points.
    """
    try:
        # Get all rank tiers from previous season
        all_ranks = RankTier.query.filter_by(season=current_season).order_by(RankTier.rank_points.desc()).all()
        
        for i, rank in enumerate(all_ranks):
            if i < 100:  # Top 100 keep Legend
                new_season_rank = RankTier(
                    user_id=rank.user_id,
                    season=current_season + 1,
                    rank_name='Legend',
                    rank_points=max(2400, rank.rank_points - 200),  # Slight reduction
                    division=None,
                    peak_rank_name='Legend',
                    peak_rank_points=rank.peak_rank_points
                )
            else:  # Others drop 400 points or to 800 minimum
                new_rating = max(800, rank.rank_points - 400)
                determine_tier_and_division = _determine_tier_division(new_rating)
                
                new_season_rank = RankTier(
                    user_id=rank.user_id,
                    season=current_season + 1,
                    rank_name=determine_tier_and_division['tier'],
                    rank_points=new_rating,
                    division=determine_tier_and_division['division'],
                    peak_rank_name='Bronze',
                    peak_rank_points=new_rating
                )
            
            db.session.add(new_season_rank)
        
        db.session.commit()
        logger.info(f"Season {current_season + 1} reset completed")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resetting season: {e}")
        return False


def _determine_tier_division(elo):
    """Helper to determine tier and division from Elo"""
    for tier, (min_elo, max_elo) in RANK_TIERS.items():
        if min_elo <= elo < max_elo:
            if tier == 'Legend':
                return {'tier': tier, 'division': None}
            
            tier_range = max_elo - min_elo
            progress = elo - min_elo
            division_index = int((progress / tier_range) * 4)
            division_index = min(3, max(0, division_index))
            
            return {'tier': tier, 'division': DIVISIONS[division_index]}
    
    return {'tier': 'Bronze', 'division': 'IV'}

