from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    profile_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    streak = db.Column(db.Integer, default=0)
    coins = db.Column(db.Integer, default=100)
    xp = db.Column(db.Integer, default=0)
    player_level = db.Column(db.Integer, default=1)
    total_games_played = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    avatar_config = db.Column(db.Text, nullable=True)
    settings_config = db.Column(db.Text, default='{"theme": "dark", "sound": true}')
    notification_preferences = db.Column(db.Text, default='{"friend_requests": true, "achievements": true, "mentions": true}')
    bio = db.Column(db.String(500), nullable=True)
    is_online = db.Column(db.Boolean, default=False)
    elo_rating = db.Column(db.Integer, default=1000) # For Ranked System
    rank_tier = db.Column(db.String(20), default='Bronze') # Bronze, Silver, Gold, Platinum, Diamond, Legend
    
    # Relationships
    scores = db.relationship('Score', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    achievements = db.relationship('Achievement', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    inventory = db.relationship('Inventory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic', cascade='all, delete-orphan')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic', cascade='all, delete-orphan')
    friend_requests_sent = db.relationship('FriendRequest', foreign_keys='FriendRequest.sender_id', backref='sender', lazy='dynamic', cascade='all, delete-orphan')
    friend_requests_received = db.relationship('FriendRequest', foreign_keys='FriendRequest.recipient_id', backref='recipient', lazy='dynamic', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'coins': self.coins,
            'xp': self.xp,
            'player_level': self.player_level,
            'total_games_played': self.total_games_played,
            'total_score': self.total_score,
            'streak': self.streak,
            'is_online': self.is_online,
            'avatar_config': self.avatar_config,
            'settings_config': self.settings_config,
            'notification_preferences': self.notification_preferences,
            'bio': self.bio,
            'elo_rating': self.elo_rating,
            'rank_tier': self.rank_tier,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Game(db.Model):
    __tablename__ = 'games'
    
    game_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50))
    difficulty = db.Column(db.String(20))
    play_count = db.Column(db.Integer, default=0)
    icon = db.Column(db.String(10))
    color = db.Column(db.String(20))
    is_multiplayer = db.Column(db.Boolean, default=False)
    
    # Relationships
    scores = db.relationship('Score', backref='game', lazy='dynamic', cascade='all, delete-orphan')


class Score(db.Model):
    __tablename__ = 'scores'
    
    score_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    game_key = db.Column(db.String(50), db.ForeignKey('games.game_key', ondelete='CASCADE'), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)
    play_time = db.Column(db.Integer, default=0)
    achieved_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    verified = db.Column(db.Boolean, default=True, nullable=False) # For anti-cheat verification
    
    __table_args__ = (
        db.Index('idx_user_game_score', 'user_id', 'game_key', 'score'),
    )


class Achievement(db.Model):
    __tablename__ = 'achievements'
    
    achievement_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    achievement_key = db.Column(db.String(100), nullable=False)
    achievement_name = db.Column(db.String(200), nullable=False)
    achieved_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'achievement_key', name='uq_user_achievement'),
    )


class Inventory(db.Model):
    __tablename__ = 'user_inventory'
    
    inventory_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.String(100), nullable=False)
    item_type = db.Column(db.String(50))
    is_equipped = db.Column(db.Boolean, default=False)
    acquired_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'item_id', name='uq_user_item'),
    )


class DailyChallenge(db.Model):
    __tablename__ = 'daily_challenges'
    
    challenge_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    challenge_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    target_value = db.Column(db.Integer, nullable=False)
    reward_coins = db.Column(db.Integer, nullable=False)
    reward_xp = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    __table_args__ = (
        db.UniqueConstraint('date', 'challenge_type', name='uq_date_challenge'),
    )


class ChallengeProgress(db.Model):
    __tablename__ = 'challenge_progress'
    
    progress_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('daily_challenges.challenge_id', ondelete='CASCADE'), nullable=False)
    current_value = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'challenge_id', name='uq_user_challenge_progress'),
    )


class Message(db.Model):
    __tablename__ = 'messages'
    
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=True, index=True)
    content = db.Column(db.Text, nullable=False)
    is_global = db.Column(db.Boolean, default=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    read_receipt_acknowledged = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        db.Index('idx_global_messages', 'is_global', 'timestamp'),
        db.Index('idx_private_messages', 'sender_id', 'recipient_id', 'timestamp'),
        db.Index('idx_message_dedup', 'sender_id', 'content', 'timestamp'),
    )


class FriendRequest(db.Model):
    __tablename__ = 'friend_requests'
    
    request_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('sender_id', 'recipient_id', name='uq_friend_request'),
    )


class Friendship(db.Model):
    __tablename__ = 'friendships'
    
    friendship_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    friend_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'friend_id', name='uq_friendship'),
    )


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    notification_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False) # friend_request, achievement, mention, challenge, system
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class GameRoom(db.Model):
    __tablename__ = 'game_rooms'
    
    room_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room_code = db.Column(db.String(10), unique=True, nullable=False, index=True)
    game_key = db.Column(db.String(50), db.ForeignKey('games.game_key', ondelete='CASCADE'), nullable=False)
    host_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='waiting') # waiting, active, ended
    max_players = db.Column(db.Integer, default=4)
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    players = db.relationship('RoomPlayer', backref='room', lazy='dynamic', cascade='all, delete-orphan')


class RoomPlayer(db.Model):
    __tablename__ = 'room_players'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    room_id = db.Column(db.Integer, db.ForeignKey('game_rooms.room_id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False)
    is_ready = db.Column(db.Boolean, default=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('room_id', 'user_id', name='uq_room_player'),
    )


# PREVIOUSLY ADDED MODELS

class PurchaseTransaction(db.Model):
    """Audit trail for all purchases"""
    __tablename__ = 'purchase_transactions'
    
    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.String(100), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    price_paid = db.Column(db.Integer, nullable=False)
    transaction_status = db.Column(db.String(20), default='success')  # success, failed, refunded
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.Index('idx_user_transactions', 'user_id', 'created_at'),
    )


class AntiCheatLog(db.Model):
    """Track suspicious scores for review"""
    __tablename__ = 'anticheat_logs'
    
    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    game_key = db.Column(db.String(50), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)
    play_time = db.Column(db.Integer, nullable=False)
    flags = db.Column(db.String(500))  # Comma-separated: score_too_high, play_time_too_short, avg_anomaly
    verified = db.Column(db.Boolean, default=False)
    admin_notes = db.Column(db.Text, nullable=True)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.Index('idx_unreviewed_scores', 'verified', 'created_at'),
    )


class DailyStats(db.Model):
    """Track daily earnings to enforce caps"""
    __tablename__ = 'daily_stats'
    
    stat_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    coins_earned = db.Column(db.Integer, default=0)
    xp_earned = db.Column(db.Integer, default=0)
    games_played = db.Column(db.Integer, default=0)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='uq_user_daily_stats'),
    )
