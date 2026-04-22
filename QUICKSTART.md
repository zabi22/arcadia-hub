# Arcadia Hub - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Option 1: Local Development (Recommended for Testing)

#### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

#### Step 1: Clone & Setup
```bash
# Navigate to project directory
cd PythonProject15

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate
```

#### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

#### Step 3: Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings (optional for local dev)
# The default SQLite configuration works out of the box
```

#### Step 4: Initialize Database
```bash
python migrate.py
```

#### Step 5: Run Application
```bash
python app.py
```

**Access the app:** http://localhost:5000

---

### Option 2: Production Deployment (Render)

#### Step 1: Create PostgreSQL Database
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **PostgreSQL**
3. Choose plan (Free tier available)
4. Copy the **Internal Database URL**

#### Step 2: Configure Environment Variables
In Render dashboard, add these variables:

```bash
FLASK_ENV=production
SECRET_KEY=<generate-secure-key>
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Optional - for Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-app.onrender.com/auth/google/callback

# Optional - for custom domain
DOMAIN=www.arcadia-hub.online
BASE_URL=https://www.arcadia-hub.online
```

**Generate a secure SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### Step 3: Deploy
1. Connect your GitHub repository to Render
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `gunicorn --worker-class eventlet -w 1 app:app --bind 0.0.0.0:$PORT --timeout 120`
4. Deploy!

The database will be initialized automatically on first run.

---

## 🧪 Testing Your Setup

### 1. Health Check
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### 2. Create Test Account
1. Visit http://localhost:5000
2. Click "Register"
3. Create an account
4. Login

### 3. Test Game Score Submission
1. Play any game
2. Score should save automatically
3. Check dashboard for updated stats

---

## 🔧 Troubleshooting

### Database Connection Error
**Problem:** `DATABASE_URL must be set in production`

**Solution:** Set the DATABASE_URL environment variable in Render dashboard

### Port Already in Use
**Problem:** `Address already in use`

**Solution:**
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port
PORT=5001 python app.py
```

### Module Not Found Error
**Problem:** `ModuleNotFoundError: No module named 'flask'`

**Solution:**
```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Google OAuth Not Working
**Problem:** Redirect URI mismatch

**Solution:**
1. Ensure GOOGLE_REDIRECT_URI matches exactly in:
   - Google Cloud Console
   - Your .env file
   - Render environment variables
2. Must use HTTPS in production

---

## 📊 Verify Installation

Run through this checklist:

- [ ] Application starts without errors
- [ ] Health check returns "healthy"
- [ ] Can register new account
- [ ] Can login with credentials
- [ ] Dashboard loads with stats
- [ ] Games page shows all 18 games
- [ ] Can play a game
- [ ] Score saves after game
- [ ] Coins increase after playing
- [ ] Shop page loads
- [ ] Can purchase item (if enough coins)
- [ ] Inventory shows purchased items
- [ ] Leaderboard displays rankings
- [ ] Can send friend request
- [ ] Daily challenges visible

---

## 🎯 Next Steps

1. **Customize branding** - Update colors, logos in base.html
2. **Add more games** - Create new game HTML files in templates/games/
3. **Configure Google OAuth** - Set up Google Cloud Console
4. **Set up custom domain** - Configure in Render dashboard
5. **Monitor logs** - Check logs/arcadia_hub.log for issues

---

## 📚 Documentation

- **Architecture Guide:** ARCHITECTURE.md
- **Deployment Guide:** DEPLOYMENT.md
- **API Documentation:** See ARCHITECTURE.md → API Endpoints

---

## 🆘 Need Help?

1. Check logs: `logs/arcadia_hub.log`
2. Review ARCHITECTURE.md
3. Check Render logs (if deployed)
4. Verify environment variables
5. Test with health check endpoint

---

<div align="center">

**Happy Gaming! 🎮**

</div>
