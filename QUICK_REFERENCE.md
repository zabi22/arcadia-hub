# Arcadia Hub - Quick Reference

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python migrate.py

# Run application
python app.py

# Access: http://localhost:5000
```

---

## 📁 Project Structure

```
Arcadia-Hub/
├── app.py                    # Application entry point
├── migrate.py                # Database migration script
├── requirements.txt          # Python dependencies
│
├── routes/                   # Route handlers
│   ├── auth_routes.py        # Authentication
│   └── main_routes.py        # Core routes
│
├── services/                 # Business logic
│   ├── user_service.py       # User management
│   ├── game_service.py       # Game scoring
│   ├── shop_service.py       # Shop & inventory
│   ├── friend_service.py     # Friend system
│   └── challenge_service.py  # Daily challenges
│
├── models/                   # Database models
│   └── models.py             # SQLAlchemy ORM
│
├── utils/                    # Utilities
│   ├── config.py             # Configuration
│   ├── helpers.py            # Helper functions
│   └── logger.py             # Logging
│
└── templates/                # HTML templates
    ├── base.html             # Base template
    ├── dashboard.html        # Dashboard
    ├── shop.html             # Shop
    ├── inventory.html        # Inventory
    ├── profile.html          # Profile
    ├── leaderboard.html      # Leaderboard
    ├── friends.html          # Friends
    └── settings.html         # Settings
```

---

## 🔑 Key Endpoints

### Authentication
- `GET/POST /auth/login` - Login
- `GET/POST /auth/register` - Register
- `GET /auth/logout` - Logout
- `GET /auth/google` - Google OAuth

### Main Features
- `GET /dashboard` - User dashboard
- `GET /games` - Games list
- `GET /play/<game>` - Play game
- `POST /api/score` - Submit score
- `GET /leaderboard` - Rankings
- `GET /profile` - User profile

### Shop & Inventory
- `GET /shop` - Browse shop
- `POST /shop/purchase` - Buy item
- `GET /inventory` - View inventory
- `POST /inventory/equip` - Equip item

### Friends
- `GET /friends` - Friends list
- `POST /friends/add` - Add friend
- `POST /friends/accept` - Accept request
- `POST /friends/reject` - Reject request
- `GET /friends/search?q=<query>` - Search users

### System
- `GET /api/health` - Health check
- `GET /settings` - Settings page

---

## ⚙️ Environment Variables

```bash
# Required
FLASK_ENV=production
SECRET_KEY=<secure-key>
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Optional
GOOGLE_CLIENT_ID=<oauth-id>
GOOGLE_CLIENT_SECRET=<oauth-secret>
GOOGLE_REDIRECT_URI=https://domain/auth/google/callback
```

---

## 📚 Documentation

- **QUICKSTART.md** - Getting started guide
- **ARCHITECTURE.md** - System architecture
- **DEPLOYMENT_CHECKLIST.md** - Deployment steps
- **FINAL_REPORT.md** - Complete transformation report
- **TRANSFORMATION_SUMMARY.md** - Summary of changes

---

## 🛠️ Common Commands

```bash
# Run migrations
python migrate.py

# Start development server
python app.py

# Start production server
gunicorn --worker-class eventlet -w 1 app:app --bind 0.0.0.0:5000

# Check health
curl http://localhost:5000/api/health

# View logs
tail -f logs/arcadia_hub.log
```

---

## 🐛 Troubleshooting

**Database error?**
```bash
python migrate.py
```

**Port in use?**
```bash
lsof -ti:5000 | xargs kill -9
```

**Module not found?**
```bash
pip install -r requirements.txt
```

---

## 📞 Support

1. Check logs: `logs/arcadia_hub.log`
2. Review documentation in `/docs`
3. Test health: `/api/health`
4. Verify environment variables

---

<div align="center">

**Built with ❤️ for gamers worldwide**

[Full Documentation](FINAL_REPORT.md) • [Quick Start](QUICKSTART.md) • [Deploy](DEPLOYMENT_CHECKLIST.md)

</div>
