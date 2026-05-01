#!/usr/bin/env python
"""
Comprehensive test script for Arcadia Hub critical issues
Tests:
1. Game filtering works
2. API inventory endpoint
3. Shop purchase system 
4. Game score submission
5. Item equip/unequip
"""

import sys
import os
sys.path.insert(0, '/Users/zabihullahahmadzai/PycharmProjects/PythonProject15')

from app import create_app, socketio, db
from src.models.models import User, Game, Inventory, Score
from src.services.shop_service import purchase_item, get_user_inventory, equip_item
from flask import json

def init_test_user():
    """Create a test user with initial coins"""
    user = User(
        username='testuser_dev',
        email='test_dev@arcadia.local',
        password_hash='hashed_password',
        coins=1000,
        xp=0
    )
    db.session.add(user)
    db.session.commit()
    return user

def test_api_inventory(client, user_token):
    """Test the /api/inventory endpoint"""
    print("\n🧪 Test 1: API Inventory Endpoint")
    print("-" * 50)
    
    # First purchase an item so we have inventory
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username='testuser_dev').first()
        if user:
            success, result = purchase_item(user, 'item_shield')
            if success:
                print(f"  ✓ Purchased item: {result['name']}")
            else:
                print(f"  ✗ Purchase failed: {result}")
        
        # Test endpoint
    response = client.get('/api/inventory')
    if response.status_code == 200:
        data = response.get_json()
        if data.get('success'):
            inventory = data.get('inventory', {})
            print(f"  ✓ Inventory API works")
            print(f"  ✓ Returned {len(inventory)} items")
            
            for item_id, item_data in inventory.items():
                if 'game_effect' in item_data and 'quantity' in item_data:
                    print(f"    - {item_data['name']}: quantity={item_data['quantity']}, game_effect={item_data['game_effect']}")
                else:
                    print(f"    ✗ Missing fields in {item_id}")
                    
            return True
        else:
            print(f"  ✗ API returned error: {data.get('message')}")
    else:
        print(f"  ✗ API endpoint failed: {response.status_code}")
    return False

def test_shop_purchase(client):
    """Test the shop purchase system"""
    print("\n🧪 Test 2: Shop Purchase System")
    print("-" * 50)
    
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username='testuser_dev').first()
        initial_coins = user.coins
        
        print(f"  Initial coins: {initial_coins}")
        
        # Try to purchase another item
        success, result = purchase_item(user, 'item_magnet')
        
        if success:
            print(f"  ✓ Purchase successful: {result['name']}")
            print(f"  ✓ Coins after purchase: {user.coins}")
            
            # Verify inventory
            inventory = get_user_inventory(user.user_id)
            shield = next((i for i in inventory if i['item_id'] == 'item_shield'), None)
            magnet = next((i for i in inventory if i['item_id'] == 'item_magnet'), None)
            
            if shield and magnet:
                print(f"  ✓ Both items in inventory")
                return True
            else:
                print(f"  ✗ Items not in inventory")
        else:
            print(f"  ✗ Purchase failed: {result}")
    
    return False

def test_equip_unequip(client):
    """Test equipping and unequipping items"""
    print("\n🧪 Test 3: Equip/Unequip System")
    print("-" * 50)
    
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username='testuser_dev').first()
        
        # Equip shield
        success, error = equip_item(user, 'item_shield')
        if success:
            print(f"  ✓ Shield equipped")
            # Verify it's equipped
            inventory = get_user_inventory(user.user_id)
            shield = next((i for i in inventory if i['item_id'] == 'item_shield'), None)
            if shield and shield['is_equipped']:
                print(f"  ✓ Verified equipped status")
                return True
            else:
                print(f"  ✗ Equipped status not verified")
        else:
            print(f"  ✗ Equip failed: {error}")
    
    return False

def test_game_endpoints(client):
    """Test game-related endpoints"""
    print("\n🧪 Test 4: Game Endpoints")
    print("-" * 50)
    
    # Test games page loads
    response = client.get('/games')
    if response.status_code == 200:
        print(f"  ✓ Games page loads (200)")
        
        # Check for game filtering content
        html = response.get_data(as_text=True)
        if 'filterGames' in html and 'game-card' in html:
            print(f"  ✓ Game filtering elements present")
            return True
        else:
            print(f"  ✗ Game filtering elements missing")
    else:
        print(f"  ✗ Games page failed: {response.status_code}")
    
    return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("🎮 ARCADIA HUB - CRITICAL ISSUES TEST SUITE")
    print("=" * 60)
    
    app = create_app()
    
    # Setup testing context
    with app.app_context():
        # Clear existing test user
        test_user = User.query.filter_by(username='testuser_dev').first()
        if test_user:
            db.session.delete(test_user)
            db.session.commit()
        
        # Create fresh test user
        test_user = init_test_user()
        print(f"\n✓ Test user created: {test_user.username} (ID: {test_user.user_id})")
        
    # Create test client
    app.config['TESTING'] = True
    client = app.test_client()
    
    # Login test user
    with app.test_request_context():
        from flask import session
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
            sess['username'] = test_user.username
    
    # Run tests
    results = []
    
    try:
        results.append(("API Inventory", test_api_inventory(client, None)))
        results.append(("Shop Purchase", test_shop_purchase(client)))
        results.append(("Equip/Unequip", test_equip_unequip(client)))
        results.append(("Game Endpoints", test_game_endpoints(client)))
    except Exception as e:
        print(f"\n✗ Test error: {e}")
        import traceback
        traceback.print_exc()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL CRITICAL ISSUES FIXED!")
    else:
        print(f"\n⚠️  {total - passed} tests still failing")
        sys.exit(1)

if __name__ == '__main__':
    main()

