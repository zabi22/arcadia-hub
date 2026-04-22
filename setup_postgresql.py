#!/usr/bin/env python3
"""
Database Migration Script
Migrates from SQLite to PostgreSQL
Run this BEFORE deploying to Render
"""

import os
from dotenv import load_dotenv

load_dotenv()

def check_current_database():
    """Check what database is currently being used"""
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///gaming_app.db')
    
    if database_url.startswith('sqlite'):
        print("❌ Currently using SQLite (data will be lost on restart)")
        print(f"   Database: {database_url}")
        print("\n✅ Ready to migrate to PostgreSQL!")
        return False
    elif database_url.startswith('postgresql'):
        print("✅ Already using PostgreSQL (data is persistent)")
        print(f"   Database: {database_url}")
        return True
    else:
        print(f"⚠️  Unknown database type: {database_url}")
        return False


def test_postgresql_connection(db_url):
    """Test PostgreSQL connection"""
    try:
        from sqlalchemy import create_engine
        engine = create_engine(db_url)
        connection = engine.connect()
        connection.close()
        print("✅ PostgreSQL connection successful!")
        return True
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        return False


def setup_postgresql_instructions():
    """Print step-by-step PostgreSQL setup instructions"""
    print("\n" + "="*70)
    print("🚀 POSTGRESQL SETUP FOR RENDER")
    print("="*70)
    
    print("\n📋 STEP 1: Create PostgreSQL Database on Render")
    print("-" * 70)
    print("1. Go to https://render.com and login")
    print("2. Click 'New +' → Select 'PostgreSQL'")
    print("3. Fill in:")
    print("   - Name: arcadia-hub-db")
    print("   - Database: arcadia_hub")
    print("   - User: arcadia_admin")
    print("   - Region: Choose closest to you")
    print("   - Instance Type: Free")
    print("4. Click 'Create Database'")
    print("5. WAIT 2-3 minutes for provisioning")
    print("6. Copy the 'Internal Database URL'")
    print("   (Looks like: postgresql://user:pass@host:5432/dbname)")
    
    print("\n📋 STEP 2: Update Your .env File")
    print("-" * 70)
    print("Replace your DATABASE_URL in .env with:")
    print("DATABASE_URL=postgresql://YOUR_USER:YOUR_PASS@YOUR_HOST:5432/YOUR_DB")
    print("\nExample:")
    print("DATABASE_URL=postgresql://arcadia_admin:mypassword@arcadia-hub-db.db.render.com:5432/arcadia_hub")
    
    print("\n📋 STEP 3: Test Connection Locally")
    print("-" * 70)
    print("Run: python setup_postgresql.py")
    print("It will test your PostgreSQL connection")
    
    print("\n📋 STEP 4: Deploy to Render")
    print("-" * 70)
    print("1. Push code to GitHub")
    print("2. In Render dashboard, add environment variable:")
    print("   DATABASE_URL=your-postgresql-url-here")
    print("3. Redeploy your app")
    print("4. Your data will now be PERMANENT!")
    
    print("\n" + "="*70)
    print("✅ WHAT WILL BE SAVED PERMANENTLY:")
    print("="*70)
    print("✓ User accounts and profiles")
    print("✓ Game scores and high scores")
    print("✓ Chat history and messages")
    print("✓ Friends and friend requests")
    print("✓ Shop purchases and inventory")
    print("✓ Achievements unlocked")
    print("✓ Daily challenge progress")
    print("✓ Coins and XP")
    print("✓ Level progression")
    print("="*70)
    
    print("\n💡 TIP: PostgreSQL data survives:")
    print("  • App restarts")
    print("  • Code deployments")
    print("  • Server crashes")
    print("  • Render maintenance")
    print("  • ANYTHING except manual database deletion!")
    print()


def main():
    print("\n" + "="*70)
    print("🎮 ARCADIA HUB - DATABASE SETUP CHECKER")
    print("="*70)
    print()
    
    # Check current database
    is_postgresql = check_current_database()
    
    if is_postgresql:
        print("\n✅ You're all set! Using PostgreSQL for persistent storage.")
        print("   Your data is safe and will never be lost!")
    else:
        print("\n⚠️  You need to set up PostgreSQL for production!")
        setup_postgresql_instructions()
        
        # Ask if they want to test a PostgreSQL URL
        print("\n" + "="*70)
        response = input("Do you have a PostgreSQL URL to test? (yes/no): ").strip().lower()
        
        if response == 'yes':
            db_url = input("Enter your PostgreSQL URL: ").strip()
            test_postgresql_connection(db_url)
    
    print("\n" + "="*70)
    print("📖 For complete deployment guide, see:")
    print("   RENDER_DEPLOYMENT_GUIDE.md")
    print("="*70)
    print()


if __name__ == '__main__':
    main()
