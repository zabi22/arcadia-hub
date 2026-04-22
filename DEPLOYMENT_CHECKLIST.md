# Arcadia Hub - Deployment Checklist

## ✅ Pre-Deployment Checklist

### 1. Environment Setup
- [ ] Create `.env` file from `.env.example`
- [ ] Generate secure SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] Set FLASK_ENV=production
- [ ] Configure DATABASE_URL (PostgreSQL for production)
- [ ] Set DOMAIN and BASE_URL to production domain

### 2. Google OAuth Configuration
- [ ] Create Google Cloud Console project
- [ ] Enable Google+ API
- [ ] Create OAuth 2.0 credentials
- [ ] Add authorized redirect URI: `https://www.arcadia-hub.online/auth/google/callback`
- [ ] Set GOOGLE_CLIENT_ID in environment
- [ ] Set GOOGLE_CLIENT_SECRET in environment
- [ ] Set GOOGLE_REDIRECT_URI in environment

### 3. Database Setup (Render PostgreSQL)
- [ ] Create PostgreSQL database on Render
- [ ] Copy Internal Database URL
- [ ] Set DATABASE_URL environment variable
- [ ] Test database connection

### 4. Dependencies
- [ ] Verify all packages in requirements.txt
- [ ] Test local installation: `pip install -r requirements.txt`
- [ ] Verify no dependency conflicts

### 5. Local Testing
```bash
# Run migration script
python migrate.py

# Start application
python app.py

# Test health endpoint
curl http://localhost:5000/api/health
```

- [ ] Application starts without errors
- [ ] Health check returns "healthy"
- [ ] Can register new account
- [ ] Can login successfully
- [ ] Dashboard loads with all stats
- [ ] Games page shows all 18 games
- [ ] Can play a game
- [ ] Score submits and saves
- [ ] Coins increase after game
- [ ] Shop page loads with items
- [ ] Can purchase item
- [ ] Inventory shows purchased items
- [ ] Can equip/unequip items
- [ ] Leaderboard displays rankings
- [ ] Friends page loads
- [ ] Can search for users
- [ ] Can send friend request
- [ ] Profile page shows stats
- [ ] Settings page loads
- [ ] Logout works correctly

### 6. Code Quality
- [ ] No hardcoded secrets in code
- [ ] All sensitive data in environment variables
- [ ] Error pages display correctly (404, 500)
- [ ] Logging configured and working
- [ ] No console.log statements in production code
- [ ] All routes have error handling

### 7. Security
- [ ] SECRET_KEY is strong and unique
- [ ] HTTPS will be enforced (Flask-Talisman)
- [ ] CSRF protection enabled
- [ ] Rate limiting configured
- [ ] Session cookies secure
- [ ] Input validation on all forms
- [ ] SQL injection protected (ORM)
- [ ] XSS protection (Jinja2 autoescape)

---

## 🚀 Render Deployment

### Step 1: Prepare Repository
- [ ] Commit all changes to Git
- [ ] Push to GitHub
- [ ] Verify .gitignore excludes sensitive files

### Step 2: Create Web Service on Render
- [ ] Go to Render Dashboard
- [ ] Click New + → Web Service
- [ ] Connect GitHub repository
- [ ] Configure:
  - **Name**: arcadia-hub
  - **Region**: Choose closest to users
  - **Branch**: main
  - **Root Directory**: (leave blank)
  - **Runtime**: Python 3
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `gunicorn --worker-class eventlet -w 1 app:app --bind 0.0.0.0:$PORT --timeout 120`

### Step 3: Create PostgreSQL Database
- [ ] Click New + → PostgreSQL
- [ ] Choose plan (Free tier)
- [ ] Note the Internal Database URL
- [ ] Wait for database to provision

### Step 4: Configure Environment Variables
In Render dashboard, add these variables:

```
FLASK_ENV=production
SECRET_KEY=<your-secure-key>
DATABASE_URL=<postgresql-url-from-step-3>
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
GOOGLE_REDIRECT_URI=https://your-app-name.onrender.com/auth/google/callback
DOMAIN=your-app-name.onrender.com
BASE_URL=https://your-app-name.onrender.com
```

### Step 5: Deploy
- [ ] Click Deploy
- [ ] Monitor build logs
- [ ] Wait for deployment to complete
- [ ] Check application logs for errors

### Step 6: Post-Deployment Verification
- [ ] Visit https://your-app.onrender.com
- [ ] Test health endpoint: `/api/health`
- [ ] Register test account
- [ ] Login and verify dashboard
- [ ] Play a game and verify score saves
- [ ] Test shop purchase
- [ ] Test friend system
- [ ] Verify data persists after page refresh
- [ ] Test Google OAuth login
- [ ] Check logs for any errors

---

## 🔧 Custom Domain Setup (Optional)

### Step 1: Configure in Render
- [ ] Go to Settings → Custom Domain
- [ ] Add domain: `www.arcadia-hub.online`
- [ ] Note the CNAME target

### Step 2: DNS Configuration
- [ ] Go to domain registrar (Namecheap, GoDaddy, etc.)
- [ ] Add CNAME record:
  - **Name**: www
  - **Value**: <render-cname-target>
- [ ] Wait for DNS propagation (up to 48 hours)

### Step 3: Update Environment Variables
- [ ] Update DOMAIN: `www.arcadia-hub.online`
- [ ] Update BASE_URL: `https://www.arcadia-hub.online`
- [ ] Update GOOGLE_REDIRECT_URI: `https://www.arcadia-hub.online/auth/google/callback`
- [ ] Redeploy application

### Step 4: SSL Certificate
- [ ] Render automatically provisions SSL
- [ ] Wait for certificate to activate
- [ ] Verify HTTPS works

---

## 📊 Monitoring & Maintenance

### Daily Checks
- [ ] Check application logs for errors
- [ ] Monitor response times
- [ ] Verify database health
- [ ] Check disk space usage

### Weekly Tasks
- [ ] Review user registration stats
- [ ] Check for failed login attempts
- [ ] Monitor database size
- [ ] Review error logs

### Monthly Tasks
- [ ] Update dependencies
- [ ] Review security settings
- [ ] Backup database (Render does this automatically)
- [ ] Performance optimization review

---

## 🐛 Troubleshooting

### Application Won't Start
**Check:**
1. Application logs in Render dashboard
2. Environment variables are set correctly
3. DATABASE_URL is accessible
4. Requirements installed successfully

**Common Errors:**
- `DATABASE_URL must be set` → Add DATABASE_URL env var
- `ModuleNotFoundError` → Check requirements.txt
- `Address already in use` → Render PORT variable issue

### Database Connection Failed
**Check:**
1. DATABASE_URL is correct
2. PostgreSQL database is running
3. Network access allowed
4. SSL mode configured

### Google OAuth Not Working
**Check:**
1. Redirect URI matches exactly in Google Console
2. GOOGLE_CLIENT_ID and SECRET are correct
3. Google+ API is enabled
4. Using HTTPS in production

### Data Not Persisting
**Check:**
1. Using PostgreSQL (not SQLite)
2. DATABASE_URL is set
3. Database is provisioned on Render
4. No errors in logs

---

## 📈 Performance Optimization

### If App is Slow
1. **Enable connection pooling** (already configured)
2. **Add Redis caching** (future enhancement)
3. **Optimize database queries** (add more indexes)
4. **Use CDN for static assets**
5. **Enable gzip compression**

### If Database is Slow
1. **Add indexes** to frequently queried columns
2. **Use query caching**
3. **Optimize slow queries**
4. **Consider read replicas** (for scale)

---

## 🎯 Go-Live Checklist

- [ ] All pre-deployment checks passed
- [ ] Test deployment successful
- [ ] Custom domain configured (optional)
- [ ] SSL certificate active
- [ ] Google OAuth working
- [ ] All features tested in production
- [ ] Monitoring setup
- [ ] Error tracking configured
- [ ] Backup strategy confirmed
- [ ] Documentation updated
- [ ] Team notified of deployment

---

## 📞 Support Contacts

- **Render Support**: https://render.com/support
- **PostgreSQL Issues**: Check Render database logs
- **Google OAuth**: Google Cloud Console documentation
- **Application Bugs**: Check logs/arcadia_hub.log

---

<div align="center">

**Deployment Complete! 🎉**

*Your production-grade gaming platform is now live!*

</div>
