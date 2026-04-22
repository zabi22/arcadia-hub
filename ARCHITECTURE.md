# Arcadia Hub - Production Architecture Guide

## 🎯 Complete System Transformation

Arcadia Hub has been completely rebuilt from the ground up as a **production-grade gaming platform** with enterprise-level architecture.

---

## 📐 New Architecture

### Modular Structure

```
Arcadia-Hub/
├── app.py                 # Application factory (Flask app creation)
├── routes/                # Route handlers (Controllers)
│   ├── auth_routes.py     # Authentication & OAuth
│   └── main_routes.py     # Core application routes
├── services/              # Business logic layer
│   ├── user_service.py    # User management & authentication
│   ├── game_service.py    # Game scoring & achievements
│   ├── shop_service.py    # Shop & inventory management
│   ├── friend_service.py  # Friend system
│   └── challenge_service.py # Daily challenges
├── models/                # Database models (ORM)
│   └── models.py          # SQLAlchemy models
├── utils/                 # Helper utilities
│   ├── config.py          # Configuration management
│   ├── helpers.py         # Common helper functions
│   └── logger.py          # Logging setup
├── templates/             # HTML templates
├── tests/                 # Test suite
└── migrations/            # Database migrations
```

---

## 🗄️ Database Architecture

### SQLAlchemy ORM Models

**Core Tables:**
- `users` - User accounts with XP, coins, levels, streaks
- `games` - Game metadata and configurations
- `scores` - Game scores with indexes for fast queries
- `achievements` - Unlocked achievements per user
- `user_inventory` - Purchased items with equip/unequip
- `daily_challenges` - Auto-generated daily challenges
- `challenge_progress` - User progress on challenges
- `messages` - Global & private chat messages
- `friend_requests` - Pending friend requests
- `friendships` - Established friendships

### Key Features:
✅ **PostgreSQL for production** (data persists across deploys)  
✅ **SQLite for development** (easy local testing)  
✅ **Foreign keys with CASCADE deletes** (data integrity)  
✅ **Indexes on frequently queried columns** (performance)  
✅ **Unique constraints** (prevent duplicates)  
✅ **Flask-Migrate** for schema migrations  

---

## 🔐 Security Improvements

### Authentication
- ✅ **bcrypt password hashing** (replaced weak SHA256)
- ✅ **Google OAuth** with proper redirect handling
- ✅ **Session management** with secure cookies
- ✅ **CSRF protection** via Flask-WTF
- ✅ **Rate limiting** (200 requests/day, 50/hour)
- ✅ **HTTPS enforcement** in production (Flask-Talisman)

### Input Validation
- ✅ All user inputs validated and sanitized
- ✅ SQL injection protection (ORM parameterized queries)
- ✅ XSS protection (Jinja2 autoescaping)

---

## 🚀 Performance Optimizations

### Backend
- ✅ **Database connection pooling** (10 connections, max 20 overflow)
- ✅ **Query optimization** with indexes
- ✅ **Lazy loading** for relationships
- ✅ **Caching** strategies for frequently accessed data
- ✅ **Async WebSocket** support (eventlet)

### Database
```python
# PostgreSQL connection pool configuration
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 1800,
}
```

---

## 🎮 Game System

### Unified Scoring System
```python
# Submit score (automatically handles rewards)
success, result = submit_score(user, game_key, score, play_time)

# Returns:
{
    'coins_earned': 50,
    'xp_earned': 25,
    'is_high_score': True
}
```

### Reward Calculation
- **Base coins**: `score // 10` (minimum 1)
- **Base XP**: `score // 5` (minimum 5)
- **High score bonus**: +25 coins, +50 XP
- **Streak bonus**: `min(streak * 10, 100)` coins

### Achievement System
Automatic achievement unlocking:
- First game played
- High score achieved
- Level milestones
- Streak achievements
- Purchase achievements

---

## 💰 Economy System

### Coins
- Earn from games (based on score)
- Daily login bonuses
- Streak rewards
- Challenge completion
- High score bonuses

### XP & Leveling
- **Exponential scaling**: Each level requires 1.5x more XP
- **Level 1**: 100 XP
- **Level 2**: 150 XP additional
- **Level 3**: 225 XP additional
- And so on...

### Shop Items
Categories:
- **Power-ups**: Shield, Speed Boost, Multiplier, Magnet
- **Avatars**: Dark Knight, Fire Phoenix, Space Astronaut, Legendary
- **Badges**: Elite Player, Pro Gamer

---

## 👥 Social Features

### Friend System
- Send/accept/reject friend requests
- View friends list with online status
- Remove friendships
- Search users by username

### Real-time Chat (SocketIO)
- Global chat room
- Private messaging (coming soon)
- Online user tracking
- Real-time notifications

---

## 🎯 Daily Challenges

Auto-generated every day:
1. **Play 5 games** → 50 coins, 100 XP
2. **Beat 2 high scores** → 75 coins, 150 XP
3. **Earn 1000 total points** → 100 coins, 200 XP

Progress tracked automatically.

---

## 📊 API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `GET /auth/logout` - User logout
- `GET /auth/google` - Google OAuth
- `GET /auth/google/callback` - OAuth callback

### Games
- `GET /games` - List all games
- `GET /play/<game_key>` - Play specific game
- `POST /api/score` - Submit game score

### Social
- `GET /friends` - View friends
- `POST /friends/add` - Send friend request
- `POST /friends/accept` - Accept request
- `POST /friends/reject` - Reject request
- `POST /friends/remove` - Remove friend
- `GET /friends/search?q=<query>` - Search users

### Shop & Inventory
- `GET /shop` - Browse shop
- `POST /shop/purchase` - Purchase item
- `GET /inventory` - View inventory
- `POST /inventory/equip` - Equip item
- `POST /inventory/unequip` - Unequip item

### Other
- `GET /dashboard` - User dashboard
- `GET /profile` - User profile
- `GET /leaderboard` - Global leaderboard
- `GET /settings` - User settings
- `GET /api/health` - Health check

---

## 🌐 Deployment

### Environment Variables

```bash
# Required
FLASK_ENV=production
SECRET_KEY=<secure-random-key>
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Optional
GOOGLE_CLIENT_ID=<google-oauth-id>
GOOGLE_CLIENT_SECRET=<google-oauth-secret>
GOOGLE_REDIRECT_URI=https://www.arcadia-hub.online/auth/google/callback
DOMAIN=www.arcadia-hub.online
BASE_URL=https://www.arcadia-hub.online
```

### Render Deployment

1. **Create PostgreSQL database** on Render
2. **Set environment variables** in Render dashboard
3. **Deploy** - Build command uses `requirements.txt`
4. **Database migrations** run automatically on first start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Run application
python app.py

# Access at http://localhost:5000
```

---

## 🧪 Testing

Run test suite:
```bash
python -m pytest tests/
```

### Manual Testing Checklist
- [ ] User registration
- [ ] User login (email/password)
- [ ] Google OAuth login
- [ ] Play game and submit score
- [ ] View dashboard with stats
- [ ] Purchase item from shop
- [ ] Equip/unequip inventory item
- [ ] Send/accept friend request
- [ ] View leaderboard
- [ ] Complete daily challenge
- [ ] Logout and login again (verify data persists)

---

## 📈 Monitoring & Logging

### Application Logs
- Location: `logs/arcadia_hub.log`
- Rotation: 10 files, 10KB each
- Includes: Timestamps, log levels, file locations

### Health Check
```bash
curl https://www.arcadia-hub.online/api/health
```

Response:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-01T00:00:00"
}
```

---

## 🔧 Configuration Files

### `utils/config.py`
- Development config (SQLite, debug mode)
- Production config (PostgreSQL, connection pooling)
- Testing config (isolated database)

### `Procfile`
```
gunicorn --worker-class eventlet -w 1 app:app --bind 0.0.0.0:$PORT --timeout 120
```

### `requirements.txt`
Production dependencies with pinned versions.

---

## 🎨 Frontend Features

### Base Template
- **Responsive design** (mobile-first)
- **Dark theme** with neon accents
- **Smooth animations** and transitions
- **Bootstrap 5** + custom CSS
- **Orbitron & Rajdhani fonts**

### UI Components
- Navigation bar with user menu
- Stat cards with gradients
- Game cards with hover effects
- Progress bars for XP/levels
- Alert system for notifications
- Dropdown menus
- Modal dialogs

---

## 🛡️ Error Handling

### Custom Error Pages
- 404: Page not found
- 500: Internal server error
- User-friendly messages
- Navigation options

### Defensive Coding
- All database operations in try/except
- Rollback on failures
- Safe defaults for missing data
- Input validation before processing
- Graceful degradation

---

## 🚦 Next Steps (Future Enhancements)

### Phase 2 (In Progress)
- [ ] Real-time chat with SocketIO
- [ ] Private messaging
- [ ] Notification system
- [ ] Three.js 3D games
- [ ] Sound effects system
- [ ] Particle effects in games

### Phase 3 (Planned)
- [ ] Mobile app (React Native)
- [ ] Tournament system
- [ ] Custom avatar creator
- [ ] Achievement sharing
- [ ] Game replay system
- [ ] Admin dashboard

---

## 📝 Migration from Old Architecture

### Database Migration
The old SQLite database cannot be directly migrated due to schema changes. However:

1. **Export old data** (if needed):
```python
import sqlite3
conn = sqlite3.connect('gaming_app.db')
# Export to CSV
```

2. **Deploy new version** - New tables created automatically

3. **Users re-register** - Fresh start with improved system

### Breaking Changes
- Password hashing changed (SHA256 → bcrypt)
- Session structure updated
- Database schema normalized
- API endpoints restructured

---

## 🤝 Contributing

1. Create feature branch
2. Make changes
3. Write tests
4. Submit pull request

---

## 📄 License

MIT License - See LICENSE file

---

## 👨‍💻 Author

**Zabihullah Ahmadzai**  
GitHub: [@zabi22](https://github.com/zabi22)  
Age: 15 | Passionate about Coding, AI, Technology

---

<div align="center">

### 🎮 Ready for Production!

**Built with ❤️ for gamers worldwide**

</div>
