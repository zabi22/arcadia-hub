# Deploying Arcadia Hub to Render

## Quick Deployment Guide

### Option 1: One-Click Deploy (Recommended)

1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit - Arcadia Hub web version"
   git branch -M main
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Deploy to Render:**
   
   **Method A - Using render.yaml (Automatic):**
   - Go to https://render.com
   - Sign up/Login to your account
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Select the `render.yaml` file
   - Click "Apply"
   - Render will automatically configure and deploy your app!

   **Method B - Manual Setup:**
   - Go to https://render.com/dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Configure:
     - **Name:** arcadia-hub
     - **Environment:** Python 3
     - **Build Command:** `pip install -r requirements.txt`
     - **Start Command:** `gunicorn app:app`
   - Add Environment Variables:
     - `SECRET_KEY`: (leave auto-generated)
     - `FLASK_ENV`: `production`
   - Click "Create Web Service"

3. **Wait for deployment:**
   - Build takes ~2-3 minutes
   - Once deployed, you'll get a URL like: `https://arcadia-hub-xxxx.onrender.com`

4. **Access your app:**
   - Open the provided URL in your browser
   - Register a new account
   - Start playing games!

### Option 2: Test Locally First

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Or with gunicorn (production-like)
gunicorn app:app --bind 0.0.0.0:5000
```

Visit: http://localhost:5000

## What's Included

✅ User Registration & Login
✅ Dashboard with stats
✅ 6 Games (Snake fully implemented as example)
✅ Leaderboards
✅ Friends system
✅ Settings & Profile
✅ Daily login rewards
✅ Coin system

## Adding More Games

To add more web-based games:

1. Create HTML template in `templates/games/`
2. Follow the Snake game pattern
3. Use the `/api/score` endpoint to save scores
4. Game will automatically appear in the games list

## Database

The app uses SQLite by default. For production on Render, consider upgrading to PostgreSQL:

1. Add PostgreSQL database in Render dashboard
2. Update `database.py` to use PostgreSQL connection string
3. Set `DATABASE_URL` environment variable

## Troubleshooting

**App won't start:**
- Check logs in Render dashboard
- Verify all dependencies in requirements.txt
- Ensure `app.py` is in the root directory

**Database errors:**
- Make sure `.db` files are in `.gitignore`
- Database will be created automatically on first run

**Static files not loading:**
- All templates use CDN for Bootstrap/Icons
- Internet connection required for styling

## Support

For issues or questions about deploying to Render, check:
- Render Docs: https://render.com/docs
- Flask Docs: https://flask.palletsprojects.com/
