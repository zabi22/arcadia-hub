# Deployment Guide - Arcadia Hub Gaming Platform

## 🚨 CRITICAL: Database Persistence Issue

### The Problem
If you're deploying on **Render**, **Heroku**, or similar platforms, **SQLite will NOT persist data** because:
- These platforms use **ephemeral filesystems**
- Every deploy wipes the database file
- All user data, scores, and progress gets lost

### The Solution: PostgreSQL

This platform now supports **PostgreSQL** for production deployments!

---

## 📦 Deploying to Render with PostgreSQL

### Step 1: Create PostgreSQL Database on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **New +** → **PostgreSQL**
3. Choose your plan (Free tier available)
4. Note the **Internal Database URL** (looks like: `postgresql://user:pass@host:5432/dbname`)

### Step 2: Configure Render to Use requirements-render.txt

**Important:** Render should use `requirements-render.txt` (which includes psycopg2-binary), not `requirements.txt`.

In your Render dashboard:
- **Build Command:** `pip install -r requirements-render.txt`
- **Start Command:** `gunicorn app:app`

### Step 3: Set Environment Variables

In your Render dashboard, add these environment variables:

```bash
DATABASE_URL=postgresql://user:password@host:5432/dbname
SECRET_KEY=your-super-secret-key-change-this
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-app.onrender.com/auth/google/callback
```

### Step 4: Deploy Your App

1. Connect your GitHub repository to Render
2. Deploy!

---

## 💻 Local Development

For local development, just use `requirements.txt` (SQLite, no PostgreSQL needed):

```bash
pip install -r requirements.txt
python app.py
```

The app will automatically use SQLite for local development.

---

## 🔐 Setting Up Google Login

### Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google+ API**
4. Go to **Credentials** → **Create Credentials** → **OAuth client ID**
5. Application type: **Web application**
6. Add authorized redirect URIs:
   - Development: `http://localhost:5000/auth/google/callback`
   - Production: `https://your-app.onrender.com/auth/google/callback`

### Step 2: Add to Environment Variables

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=https://your-app.onrender.com/auth/google/callback
```

---

## 🗄️ Database Migration (SQLite → PostgreSQL)

### Automatic Migration

The app automatically detects the database type:
- If `DATABASE_URL` is set → Uses PostgreSQL
- If not set → Uses SQLite (for local development)

### Manual Data Migration (Optional)

If you have existing SQLite data you want to keep:

```bash
# Install sqlite3-to-postgres tool
pip install pgloader

# Migrate data
pgloader sqlite:///gaming_app.db postgresql:///your_new_db
```

---

## ✅ Verification

After deployment, verify everything works:

1. **Check database health**: Visit `/api/health`
   - Should show: `{"status": "healthy", "database": "postgresql"}`

2. **Test user registration**: Create a new account

3. **Test Google login**: Click "Login with Google"

4. **Play a game and submit score**: Verify it saves

5. **Logout and login again**: Verify data persists

---

## 🔧 Troubleshooting

### Data Still Not Saving?

1. Check logs: `render logs` or dashboard logs
2. Verify `DATABASE_URL` is set correctly
3. Check database health: `/api/health`
4. Ensure PostgreSQL database is running

### Google Login Not Working?

1. Verify redirect URI matches exactly
2. Check Google Cloud Console for errors
3. Ensure environment variables are set
4. Check app logs for OAuth errors

### Local Development

For local development, just run:
```bash
python app.py
```

The app will automatically use SQLite for local development.

---

## 📊 Database Schema

The platform uses these main tables:
- `users` - User accounts and settings
- `scores` - Game scores and play history
- `games` - Game metadata
- `user_inventory` - Purchased items
- `achievements` - Unlocked achievements
- `game_records` - High scores per game
- `daily_challenges` - Daily challenge definitions
- `challenge_progress` - User challenge progress

All tables have proper foreign keys and constraints.

---

## 🎯 Best Practices

1. **Always use PostgreSQL in production**
2. **Never commit `.env` files or secrets**
3. **Regular database backups** (Render does this automatically)
4. **Monitor database health** via `/api/health`
5. **Use strong SECRET_KEY** (generate with: `python -c "import secrets; print(secrets.token_hex(32))"`)

---

## 📞 Support

If you encounter issues:
1. Check application logs
2. Verify all environment variables
3. Test database connection
4. Review this guide

Your data will now persist permanently across sessions and deployments! 🎉
