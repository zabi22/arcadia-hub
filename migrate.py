#!/usr/bin/env python3
"""
Database Migration Script
Migrates from old architecture to new SQLAlchemy ORM
Run this once after deploying the new version
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.models import db
from services.game_service import seed_games
from services.challenge_service import generate_daily_challenges
from utils.logger import get_logger

logger = get_logger()

def migrate_database():
    """Initialize new database schema"""
    print("🚀 Starting database migration...")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            print("📦 Creating database tables...")
            db.create_all()
            print("✅ Tables created successfully")
            
            # Seed games
            print("🎮 Seeding game data...")
            seed_games()
            print("✅ Games seeded")
            
            # Generate daily challenges
            print("🎯 Generating daily challenges...")
            generate_daily_challenges()
            print("✅ Challenges generated")
            
            print("\n✨ Migration completed successfully!")
            print("📊 Database is ready for use")
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            logger.error(f"Migration error: {e}")
            sys.exit(1)

if __name__ == '__main__':
    migrate_database()
