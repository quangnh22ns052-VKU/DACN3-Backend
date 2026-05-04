# 🚀 Render Deployment Guide - PhishGuard Backend

## ⚠️ Fix: Database Connection Error on Cloud

### Problem
```
sqlalchemy.exc.OperationalError: connection to server at "localhost" (::1), port 5432 failed
```

**Cause**: Backend tries to connect to `localhost:5432` but cloud has no local PostgreSQL.

**Solution**: Set `DATABASE_URL` environment variable pointing to Neon PostgreSQL.

---

## 📋 Step 1: Create Neon PostgreSQL Database

1. Go to https://console.neon.tech/
2. Create new project:
   - **Project name**: `phishguard`
   - **Database name**: `phishguard`
   - **Region**: Select region close to you
3. Copy connection string:
   - Click on "Connection string"
   - Select "Pooling" (recommended for serverless)
   - Copy full URL (format: `postgresql://user:password@host:5432/db?sslmode=require`)

Example:
```
postgresql://phishguard_owner:XXXpassXXX@ep-cool-pond-12345.us-west-2.neon.tech:5432/phishguard?sslmode=require
```

---

## 🎯 Step 2: Deploy Backend on Render

### 2.1 Connect GitHub Repository
1. Go to https://render.com/
2. Click "New +" → "Web Service"
3. Select your GitHub repository
4. Choose branch: `main`

### 2.2 Configure Service
- **Name**: `phishguard-backend`
- **Environment**: `Python 3.11`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn backend.api:app --host 0.0.0.0 --port 8000`

### 2.3 Set Environment Variables ⭐ IMPORTANT
In "Environment" section, add:

```
DATABASE_URL=postgresql://user:pass@neon-host:5432/db?sslmode=require
ENVIRONMENT=production
JWT_SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_urlsafe(32))">
BACKEND_PORT=8000
FRONTEND_URL=https://your-frontend-url.onrender.com
CORS_ORIGINS=https://your-frontend-url.onrender.com,https://your-backend-url.onrender.com
```

**Where to get DATABASE_URL?**
- From Neon dashboard → Connection string (Pooling mode)

### 2.4 Deploy
- Click "Deploy"
- Wait for build to complete
- Check logs for errors

---

## ✅ Step 3: Verify Backend is Running

1. Get Render URL from dashboard:
   - Example: `https://phishguard-backend-xxxx.onrender.com`

2. Test health endpoint:
   ```bash
   curl https://phishguard-backend-xxxx.onrender.com/health
   ```
   Should return: `{"status": "ok"}`

3. Test with sample URL:
   ```bash
   curl -X POST https://phishguard-backend-xxxx.onrender.com/scan \
     -H "Content-Type: application/json" \
     -d '{"text": "https://example.com"}'
   ```

---

## 🔧 Step 4: Update Frontend

If frontend is also on Render, update:

In Frontend environment variables:
```
BACKEND_URL=https://phishguard-backend-xxxx.onrender.com
```

In Frontend code (`app/config.py` or `utils.js`):
```python
# Change from:
BACKEND_URL = "http://localhost:8000"

# To:
BACKEND_URL = os.getenv("BACKEND_URL", "https://phishguard-backend-xxxx.onrender.com")
```

---

## 🐛 Troubleshooting

### Error: "connection refused"
- Check DATABASE_URL is set in Render environment variables
- Verify Neon database is running
- Check Neon region is accessible

### Error: "relation 'users' does not exist"
- Run database initialization:
  - SSH into Render service or
  - Add script to ensure schema exists:
    ```python
    # In backend/api.py startup
    @app.on_event("startup")
    async def startup():
        Base.metadata.create_all(bind=engine)
    ```

### Error: "SSL/TLS error"
- Ensure `?sslmode=require` is in DATABASE_URL
- Use Neon's pooling connection string (not direct)

### Service slow on first request
- Normal: Render spins down free tier services
- Upgrade to paid tier for always-on

---

## 📊 Monitoring

### View Logs
1. Go to Render dashboard → Select service
2. Click "Logs" tab
3. Search for errors

### Database Health
1. Go to Neon console
2. Check connection metrics
3. Verify query performance

---

## 🚀 Scale to Production

For production deployment:

1. **Upgrade Render tier**: Free → Starter ($12/month)
2. **Enable auto-deploy**: GitHub → Render auto-redeploy on push
3. **Add custom domain**: Map `backend.yourdomain.com`
4. **Enable monitoring**: Add error tracking (Sentry, etc.)
5. **Upgrade DB**: Neon → Dedicated PostgreSQL (AWS RDS, etc.)

---

## ✨ Summary

| Step | Action | Status |
|------|--------|--------|
| 1 | Create Neon database | ✅ |
| 2 | Set DATABASE_URL env var | ✅ |
| 3 | Deploy to Render | ✅ |
| 4 | Test /health endpoint | ✅ |
| 5 | Update frontend URL | ✅ |

**Result**: Backend running on cloud with cloud database! 🎉
