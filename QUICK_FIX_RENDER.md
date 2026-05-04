# 🔧 Quick Fix: Database Connection Error on Render

**Error:** `connection to server at "localhost" (::1), port 5432 failed`

**Cause:** `DATABASE_URL` environment variable not set on Render cloud

---

## ✅ Quick Fix (3 Steps)

### Step 1️⃣ Create Neon Database
1. Go to **https://console.neon.tech/**
2. Create account (free)
3. Click "Create a project"
4. Copy the **Connection String** (use "Pooling" mode)
5. Format: `postgresql://user:password@ep-xxx.neon.tech:5432/phishguard?sslmode=require`

### Step 2️⃣ Add Environment Variable on Render
1. Go to **Render Dashboard** → Your Backend Service
2. Click **Environment** tab
3. Add new variable:
   ```
   Key:   DATABASE_URL
   Value: postgresql://user:password@ep-xxx.neon.tech:5432/phishguard?sslmode=require
   ```
4. Click **Save**

### Step 3️⃣ Redeploy Backend
1. Go to **Deploys** tab
2. Click **Redeploy latest commit**
3. Wait 2-3 minutes for build
4. Check **Logs** for: `✅ Database initialized`

---

## 🧪 Verify It Works

After deployment:

```bash
# Test health endpoint
curl https://your-backend.onrender.com/health

# Should return:
# {"status": "ok", "database": "connected"}
```

Or test full scan:
```bash
curl -X POST https://your-backend.onrender.com/scan \
  -H "Content-Type: application/json" \
  -d '{"input": "https://example.com", "input_type": "url"}'
```

---

## 🔍 Troubleshooting

| Issue | Fix |
|-------|-----|
| `connection to localhost:5432` | Neon URL not set - follow Step 1-2 |
| `SCRAM authentication failed` | Password is wrong in connection string |
| `database does not exist` | Create database in Neon console |
| Still getting error after redeploy | Check logs in Render dashboard |

**📝 More details:** See [RENDER_DEPLOYMENT.md](./RENDER_DEPLOYMENT.md)

**🔍 Diagnose issues:** Run `python diagnose.py` locally
