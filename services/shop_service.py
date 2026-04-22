from models.models import db, Inventory
from utils.logger import get_logger

logger = get_logger()

SHOP_ITEMS = {
    'item_shield': {'name': 'Shield Power-up', 'description': 'Survive one collision per run', 'price': 100, 'icon': '🛡️', 'type': 'powerup', 'category': 'power'},
    'item_speed': {'name': 'Speed Boost', 'description': 'Start with 20% faster speed for bonus points', 'price': 150, 'icon': '⚡', 'type': 'powerup', 'category': 'power'},
    'item_multiplier': {'name': 'Score Multiplier', 'description': '1.5x coin earnings for one run', 'price': 200, 'icon': '📈', 'type': 'powerup', 'category': 'power'},
    'item_magnet': {'name': 'Food Magnet', 'description': 'Attract food within 5 cells', 'price': 175, 'icon': '🧲', 'type': 'powerup', 'category': 'power'},
    'avatar_dark': {'name': 'Dark Knight Avatar', 'description': 'Cool dark avatar', 'price': 50, 'icon': '🦇', 'type': 'avatar_skin', 'category': 'avatar'},
    'avatar_fire': {'name': 'Fire Phoenix Avatar', 'description': 'Fiery avatar', 'price': 75, 'icon': '🔥', 'type': 'avatar_skin', 'category': 'avatar'},
    'avatar_space': {'name': 'Space Astronaut Avatar', 'description': 'Galactic avatar', 'price': 75, 'icon': '👨‍🚀', 'type': 'avatar_skin', 'category': 'avatar'},
    'avatar_legend': {'name': 'Legendary Avatar', 'description': 'Ultra rare avatar', 'price': 300, 'icon': '👑', 'type': 'avatar_skin', 'category': 'avatar'},
    'badge_elite': {'name': 'Elite Player Badge', 'description': 'Elite badge', 'price': 100, 'icon': '⭐', 'type': 'badge', 'category': 'badge'},
    'badge_pro': {'name': 'Pro Gamer Badge', 'description': 'Pro badge', 'price': 150, 'icon': '🏆', 'type': 'badge', 'category': 'badge'}
}


def purchase_item(user, item_id):
    """Purchase an item from the shop"""
    try:
        # Check if item exists
        if item_id not in SHOP_ITEMS:
            return False, "Item not found"
        
        item = SHOP_ITEMS[item_id]
        
        # Check if user has enough coins
        if user.coins < item['price']:
            return False, "Not enough coins"
        
        # Check if already owned
        existing = Inventory.query.filter_by(
            user_id=user.user_id,
            item_id=item_id
        ).first()
        
        if existing:
            return False, "Item already owned"
        
        # Purchase item
        inventory_item = Inventory(
            user_id=user.user_id,
            item_id=item_id,
            item_type=item['type']
        )
        
        user.coins -= item['price']
        
        db.session.add(inventory_item)
        db.session.commit()
        
        logger.info(f"Item purchased: {user.username} - {item_id}")
        return True, item
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error purchasing item: {e}")
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
            return {k: v for k, v in SHOP_ITEMS.items() if v.get('category') == category}
        return SHOP_ITEMS
    except Exception as e:
        logger.error(f"Error fetching shop items: {e}")
        return {}
