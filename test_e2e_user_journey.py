#!/usr/bin/env python
"""
End-to-End Test: Complete User Journey
Tests the entire flow:
1. User creates account
2. User browses games
3. User filters games
4. User visits shop
5. User purchases powerups
6. User plays game with loaded inventory
7. User submits score
"""

import sys
sys.path.insert(0, '/Users/zabihullahahmadzai/PycharmProjects/PythonProject15')

from app import create_app, db
from src.models.models import User, Score
import json

def print_test(title):
    print(f"\n{'='*60}")
    print(f"🧪 {title}")
    print('='*60)

def test_complete_user_journey():
    """Test complete user experience"""
    app = create_app()
    
    with app.app_context():
        print_test("COMPLETE USER JOURNEY TEST")
        
        # 1. Create test user
        print("\n[1/7] Creating user account...")
        test_user = User(
            username='journey_test_user',
            email='journey@test.local',
            password_hash='hashed',
            coins=1000,
            xp=0
        )
        db.session.add(test_user)
        db.session.commit()
        print(f"✓ User created: {test_user.username} (ID: {test_user.user_id})")
        print(f"  Starting coins: {test_user.coins}")
        
        # 2. Create test client for routes
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.user_id
            sess['username'] = test_user.username
        
        # 3. Test games page
        print("\n[2/7] Testing games page...")
        response = client.get('/games')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'game-card' in html
        assert 'filterGames' in html
        games_count = html.count('game-card')
        print(f"✓ Games page loaded with {games_count} games")
        
        # 4. Test game filtering HTML
        print("\n[3/7] Testing game filter UI...")
        assert 'filterGames(\'single\'' in html
        assert 'filterGames(\'multi\'' in html
        assert 'filterGames(\'all\'' in html
        print(f"✓ Game filter buttons properly configured")
        
        # 5. Test shop page
        print("\n[4/7] Testing shop page...")
        response = client.get('/shop')
        assert response.status_code == 200
        shop_html = response.get_data(as_text=True)
        assert 'purchase-btn' in shop_html
        item_count = shop_html.count('purchase-btn')
        print(f"✓ Shop page loaded with {item_count} items for sale")
        
        # 6. Test shop purchase
        print("\n[5/7] Testing shop purchase system...")
        purchase_response = client.post('/shop/purchase', 
            json={'item_id': 'item_shield'},
            content_type='application/json'
        )
        assert purchase_response.status_code == 200
        purchase_data = purchase_response.get_json()
        assert purchase_data.get('success')
        db.session.refresh(test_user)
        print(f"✓ Purchase successful: {purchase_data.get('message')}")
        print(f"  Coins after purchase: {test_user.coins}")
        
        # 7. Test inventory API
        print("\n[6/7] Testing inventory API...")
        inventory_response = client.get('/api/inventory')
        assert inventory_response.status_code == 200
        inventory_data = inventory_response.get_json()
        assert inventory_data.get('success')
        inventory = inventory_data.get('inventory', {})
        assert 'item_shield' in inventory
        
        shield_item = inventory['item_shield']
        assert shield_item.get('game_effect') == True
        assert shield_item.get('quantity') == 1
        assert shield_item.get('name') == 'Shield Power-up'
        print(f"✓ Inventory API working")
        print(f"  Item: {shield_item['name']}")
        print(f"  Game Effect: {shield_item['game_effect']}")
        print(f"  Quantity: {shield_item['quantity']}")
        
        # 8. Test score submission
        print("\n[7/7] Testing game score submission...")
        score_response = client.post('/api/score',
            json={
                'game_key': 'snake',
                'score': 500,
                'play_time': 120
            },
            content_type='application/json'
        )
        assert score_response.status_code == 200
        score_data = score_response.get_json()
        assert score_data.get('success')
        
        # Verify score in database
        score_record = Score.query.filter_by(
            user_id=test_user.user_id,
            game_key='snake'
        ).first()
        assert score_record is not None
        assert score_record.score == 500
        print(f"✓ Score submitted and recorded")
        print(f"  Score: {score_record.score}")
        print(f"  XP Earned: {score_data.get('xp_earned', 0)}")
        print(f"  Coins Earned: {score_data.get('coins_earned', 0)}")
        
        # Final status
        print("\n" + "="*60)
        print("✅ COMPLETE USER JOURNEY TEST PASSED!")
        print("="*60)
        print("\nSummary:")
        print("  ✓ User account creation")
        print("  ✓ Games page loading")
        print("  ✓ Game filtering UI")
        print("  ✓ Shop page loading")
        print("  ✓ Item purchase")
        print("  ✓ Inventory API")
        print("  ✓ Score submission")
        print("\n🎮 All functionality working correctly!")
        
        return True

if __name__ == '__main__':
    try:
        test_complete_user_journey()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

