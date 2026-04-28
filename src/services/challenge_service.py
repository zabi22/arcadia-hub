from datetime import date, datetime, timedelta
from src.models.models import db, DailyChallenge, ChallengeProgress
from src.utils.logger import get_logger

logger = get_logger()


def generate_daily_challenges():
    """Generate daily challenges for today if they don't exist"""
    try:
        today = date.today()
        
        # Check if challenges already exist for today
        existing = DailyChallenge.query.filter_by(date=today).first()
        if existing:
            return
        
        # Define challenge templates
        challenge_templates = [
            {
                'challenge_type': 'play_games',
                'description': 'Play 5 games',
                'target_value': 5,
                'reward_coins': 50,
                'reward_xp': 100
            },
            {
                'challenge_type': 'high_score',
                'description': 'Beat 2 high scores',
                'target_value': 2,
                'reward_coins': 75,
                'reward_xp': 150
            },
            {
                'challenge_type': 'total_score',
                'description': 'Earn 1000 total points',
                'target_value': 1000,
                'reward_coins': 100,
                'reward_xp': 200
            }
        ]
        
        # Create challenges
        for template in challenge_templates:
            challenge = DailyChallenge(
                challenge_type=template['challenge_type'],
                description=template['description'],
                target_value=template['target_value'],
                reward_coins=template['reward_coins'],
                reward_xp=template['reward_xp'],
                date=today
            )
            db.session.add(challenge)
        
        db.session.commit()
        logger.info(f"Daily challenges generated for {today}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating daily challenges: {e}")


def get_daily_challenges(user_id):
    """Get daily challenges with user progress"""
    try:
        # Generate challenges if needed
        generate_daily_challenges()
        
        today = date.today()
        
        # Get challenges for today
        challenges = DailyChallenge.query.filter_by(date=today).all()
        
        challenges_with_progress = []
        for challenge in challenges:
            progress = ChallengeProgress.query.filter_by(
                user_id=user_id,
                challenge_id=challenge.challenge_id
            ).first()
            
            challenges_with_progress.append({
                'challenge_id': challenge.challenge_id,
                'challenge_type': challenge.challenge_type,
                'description': challenge.description,
                'target_value': challenge.target_value,
                'reward_coins': challenge.reward_coins,
                'reward_xp': challenge.reward_xp,
                'current_value': progress.current_value if progress else 0,
                'completed': progress.completed if progress else False,
                'completed_at': progress.completed_at if progress else None
            })
        
        return challenges_with_progress
    except Exception as e:
        logger.error(f"Error fetching daily challenges: {e}")
        return []


def update_challenge_progress(user_id, challenge_type, increment=1):
    """Update challenge progress"""
    try:
        today = date.today()
        
        # Get challenge
        challenge = DailyChallenge.query.filter_by(
            date=today,
            challenge_type=challenge_type
        ).first()
        
        if not challenge:
            return
        
        # Get or create progress
        progress = ChallengeProgress.query.filter_by(
            user_id=user_id,
            challenge_id=challenge.challenge_id
        ).first()
        
        if not progress:
            progress = ChallengeProgress(
                user_id=user_id,
                challenge_id=challenge.challenge_id,
                current_value=0,
                completed=False
            )
            db.session.add(progress)
        
        if progress.completed:
            return
        
        # Update progress
        progress.current_value += increment
        
        # Check if completed
        if progress.current_value >= challenge.target_value:
            progress.completed = True
            progress.completed_at = datetime.utcnow()
            
            # Award rewards
            from src.models.models import User
            user = db.session.get(User, user_id)
            if user:
                user.coins += challenge.reward_coins
                user.xp += challenge.reward_xp
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating challenge progress: {e}")
