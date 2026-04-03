SHOP_ITEMS = {
    'item_shield': {
        'name': 'Shield Power-up',
        'description': 'Gives you an extra life in games',
        'price': 100,
        'icon': '🛡️',
        'type': 'powerup',
        'category': 'power'
    },
    'item_speed': {
        'name': 'Speed Boost',
        'description': '2x speed in snake and flappy bird',
        'price': 150,
        'icon': '⚡',
        'type': 'powerup',
        'category': 'boost'
    },
    'item_multiplier': {
        'name': 'Score Multiplier',
        'description': 'Earn 1.5x coins from games',
        'price': 200,
        'icon': '📈',
        'type': 'powerup',
        'category': 'score'
    },
    'avatar_dark': {
        'name': 'Dark Knight Avatar',
        'description': 'Cool dark avatar for your profile',
        'price': 50,
        'icon': '🦇',
        'type': 'avatar_skin',
        'category': 'avatar'
    },
    'avatar_fire': {
        'name': 'Fire Phoenix Avatar',
        'description': 'Fiery avatar skin',
        'price': 75,
        'icon': '🔥',
        'type': 'avatar_skin',
        'category': 'avatar'
    },
    'avatar_space': {
        'name': 'Space Astronaut Avatar',
        'description': 'Galactic avatar',
        'price': 75,
        'icon': '👨‍🚀',
        'type': 'avatar_skin',
        'category': 'avatar'
    },
    'avatar_legend': {
        'name': 'Legendary Avatar',
        'description': 'Ultra rare avatar skin',
        'price': 300,
        'icon': '👑',
        'type': 'avatar_skin',
        'category': 'avatar'
    },
    'badge_elite': {
        'name': 'Elite Player Badge',
        'description': 'Show you are elite on leaderboard',
        'price': 100,
        'icon': '⭐',
        'type': 'badge',
        'category': 'badge'
    },
    'badge_pro': {
        'name': 'Pro Gamer Badge',
        'description': 'Professional player badge',
        'price': 150,
        'icon': '🏆',
        'type': 'badge',
        'category': 'badge'
    }
}

def get_shop_categories():
    return {
        'power': 'Power-ups',
        'avatar': 'Avatar Skins',
        'badge': 'Badges'
    }

def validate_purchase(item_id, user_coins):
    if item_id not in SHOP_ITEMS:
        return False, 'Item not found'
    
    item = SHOP_ITEMS[item_id]
    if user_coins < item['price']:
        return False, f'Need {item["price"]} coins, you have {user_coins}'
    
    return True, 'Success'
