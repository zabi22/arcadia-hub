from src.models.models import db, Inventory
from src.utils.logger import get_logger

logger = get_logger()

SHOP_ITEMS = {
    'item_shield': {'name': 'Shield Power-up', 'description': 'Survive one collision per run', 'price': 100, 'icon': '🛡️', 'type': 'powerup', 'category': 'power', 'is_available': True, 'game_effect': True, 'quantity': 1},
    'item_speed': {'name': 'Speed Boost', 'description': 'Start with 20% faster speed for bonus points', 'price': 150, 'icon': '⚡', 'type': 'powerup', 'category': 'power', 'is_available': True, 'game_effect': True, 'quantity': 1},
    'item_multiplier': {'name': 'Score Multiplier', 'description': '1.5x coin earnings for one run', 'price': 200, 'icon': '📈', 'type': 'powerup', 'category': 'power', 'is_available': True, 'game_effect': True, 'quantity': 1},
    'item_magnet': {'name': 'Food Magnet', 'description': 'Attract food within 5 cells', 'price': 175, 'icon': '🧲', 'type': 'powerup', 'category': 'power', 'is_available': True, 'game_effect': True, 'quantity': 1},
    'avatar_dark': {'name': 'Dark Knight Avatar', 'description': 'Cool dark avatar', 'price': 50, 'icon': '🦇', 'type': 'avatar_skin', 'category': 'avatar', 'is_available': True, 'game_effect': False, 'quantity': 1},
    'avatar_fire': {'name': 'Fire Phoenix Avatar', 'description': 'Fiery avatar', 'price': 75, 'icon': '🔥', 'type': 'avatar_skin', 'category': 'avatar', 'is_available': True, 'game_effect': False, 'quantity': 1},
    'avatar_space': {'name': 'Space Astronaut Avatar', 'description': 'Galactic avatar', 'price': 75, 'icon': '👨‍🚀', 'type': 'avatar_skin', 'category': 'avatar', 'is_available': True, 'game_effect': False, 'quantity': 1},
    'avatar_legend': {'name': 'Legendary Avatar', 'description': 'Ultra rare avatar', 'price': 300, 'icon': '👑', 'type': 'avatar_skin', 'category': 'avatar', 'is_available': True, 'game_effect': False, 'quantity': 1},
    'badge_elite': {'name': 'Elite Player Badge', 'description': 'Elite badge', 'price': 100, 'icon': '⭐', 'type': 'badge', 'category': 'badge', 'is_available': True, 'game_effect': False, 'quantity': 1},
    'badge_pro': {'name': 'Pro Gamer Badge', 'description': 'Pro badge', 'price': 150, 'icon': '🏆', 'type': 'badge', 'category': 'badge', 'is_available': True, 'game_effect': False, 'quantity': 1}
}


def purchase_item(user, item_id):
    """Purchase an item from the shop with transaction safety"""
    from src.models.models import PurchaseTransaction
    
    try:
        # Validate item exists
        if item_id not in SHOP_ITEMS:
            return False, "Item not found"
        
        item = SHOP_ITEMS[item_id]
        item_price = item['price']

        # Validate item availability
        if not item.get('is_available', True):
            return False, "Item is currently not available for purchase"
        
        # Validate item not already owned
        existing = Inventory.query.filter_by(
            user_id=user.user_id,
            item_id=item_id
        ).first()
        
        if existing:
            return False, "Item already owned"
        
        # Check if user has enough coins
        if user.coins < item_price:
            return False, "Not enough coins"
        
        # Deduct coins from user
        user.coins -= item_price
        db.session.flush()  # Flush to ensure user update is queued
        
        # Create inventory item
        inventory_item = Inventory(
            user_id=user.user_id,
            item_id=item_id,
            item_type=item['type'],
            quantity=1  # Add quantity field
        )
        db.session.add(inventory_item)
        db.session.flush()
        
        # Log transaction for audit trail
        transaction = PurchaseTransaction(
            user_id=user.user_id,
            item_id=item_id,
            item_name=item['name'],
            price_paid=item_price,
            transaction_status='success'
        )
        db.session.add(transaction)
        
        # Commit all changes in one transaction
        db.session.commit()
        
        logger.info(f"Item purchased: {user.username} - {item_id} - {item_price} coins")
        return True, item
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error purchasing item: {e}", exc_info=True)
        
        # Log failed transaction
        try:
            transaction = PurchaseTransaction(
                user_id=user.user_id,
                item_id=item_id,
                item_name=SHOP_ITEMS.get(item_id, {}).get('name', 'Unknown'),
                price_paid=SHOP_ITEMS.get(item_id, {}).get('price', 0),
                transaction_status='failed'
            )
            db.session.add(transaction)
            db.session.commit()
        except Exception as inner_e:
            logger.error(f"Error logging failed transaction: {inner_e}")
            db.session.rollback()
        
        return False, "Error purchasing item"


def get_user_inventory(user_id):
    """Get user's inventory"""
    try:
        inventory = Inventory.query.filter_by(user_id=user_id).all()
        
        # Enrich with item details
        inventory_with_details = []
        for item in inventory:
            item_config = SHOP_ITEMS.get(item.item_id, {})
            inventory_with_details.append({
                'inventory_id': item.inventory_id,
                'item_id': item.item_id,
                'name': item_config.get('name', 'Unknown Item'),
                'description': item_config.get('description', ''),
                'icon': item_config.get('icon', '📦'),
                'type': item.item_type,
                'category': item_config.get('category', 'other'),
                'is_equipped': item.is_equipped,
                'quantity': item.quantity if hasattr(item, 'quantity') else 1,
                'game_effect': item_config.get('game_effect', False),
                'acquired_at': item.acquired_at
            })
        
        return inventory_with_details
    except Exception as e:
        logger.error(f"Error fetching inventory: {e}")
        return []


def equip_item(user, item_id):
    """Equip an item"""
    try:
        inventory_item = Inventory.query.filter_by(
            user_id=user.user_id,
            item_id=item_id
        ).first()
        
        if not inventory_item:
            return False, "Item not found in inventory"
        
        # Unequip all items of same type
        Inventory.query.filter_by(
            user_id=user.user_id,
            item_type=inventory_item.item_type,
            is_equipped=True
        ).update({'is_equipped': False})
        
        # Equip this item
        inventory_item.is_equipped = True
        
        db.session.commit()
        
        logger.info(f"Item equipped: {user.username} - {item_id}")
        return True, None
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error equipping item: {e}")
        return False, "Error equipping item"


def unequip_item(user, item_id):
    """Unequip an item"""
    try:
        inventory_item = Inventory.query.filter_by(
            user_id=user.user_id,
            item_id=item_id
        ).first()
        
        if not inventory_item:
            return False, "Item not found in inventory"
        
        inventory_item.is_equipped = False
        
        db.session.commit()
        
        logger.info(f"Item unequipped: {user.username} - {item_id}")
        return True, None
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unequipping item: {e}")
        return False, "Error unequipping item"


def get_shop_items(category=None):
    """Get shop items, optionally filtered by category"""
    try:
        if category:
            return {k: v for k, v in SHOP_ITEMS.items() if v.get('category') == category and v.get('is_available', True)}
        return {k: v for k, v in SHOP_ITEMS.items() if v.get('is_available', True)}
    except Exception as e:
        logger.error(f"Error fetching shop items: {e}")
        return {}