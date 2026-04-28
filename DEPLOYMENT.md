# 🚀 Backend Deployment Guide

Hướng dẫn chi tiết deploy Backend lên các cloud platform.

## 📋 Nội dung

- [Render](#-render-deployment)
- [AWS AppRunner](#-aws-apprunner-deployment)
- [Local Development](#-local-development)

---

## 🔄 Render Deployment

### **Bước 1: Chuẩn bị GitHub**

```bash
cd Backend
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### **Bước 2: Tạo Service trên Render Dashboard**

1. Vào https://dashboard.render.com
2. **New+** → **Web Service**
3. **Connect GitHub** → Chọn repo `DACN3-Backend`
4. **Configure**:
   - **Name**: `phishguard-backend`
   - **Runtime**: `Docker`
   - **Branch**: `main`
   - **Dockerfile Path**: `Backend/Dockerfile`

### **Bước 3: Set Environment Variables**

Nhấn **Add Environment Variable** và thêm từng cái:

| Key | Value | Notes |
|-----|-------|-------|
| `DATABASE_URL` | `postgresql://neondb_owner:npg_...@ep-spring-dew...` | Từ Neon console |
| `SECRET_KEY` | `<generate-strong-key>` | 32+ ký tự random |
| `ENVIRONMENT` | `production` | |
| `VIRUSTOTAL_API_KEY` | `667e32d0...` | API key |
| `GSB_API_KEY` | `your-key` | Google Safe Browsing |
| `ABUSEIPDB_API_KEY` | `your-key` | AbuseIPDB |
| `BACKEND_HOST` | `0.0.0.0` | |
| `BACKEND_PORT` | `8000` | |
| `FRONTEND_URL` | `https://phishguard-frontend.onrender.com` | Frontend URL |
| `LOG_LEVEL` | `INFO` | |

### **Bước 4: Deploy**

1. Nhấn **Deploy**
2. Render sẽ:
   - Pull code từ GitHub
   - Build Docker image
   - Run Dockerfile CMD
   - Load environment variables
3. Chờ 3-5 phút

### **Bước 5: Verify**

```bash
# Test health endpoint
curl https://phishguard-backend-xxx.onrender.com/health

# Response:
{
  "status": "ok",
  "timestamp": "2026-04-28T10:30:00Z"
}
```

---

## 🌐 AWS AppRunner Deployment

### **Bước 1: Prepare Code**

```bash
cd Backend
git add .
git commit -m "Ready for AWS AppRunner"
git push origin main
```

### **Bước 2: Create AWS AppRunner Service**

**Via AWS Console:**

1. Vào **AWS AppRunner**
2. **Create Service**
3. **Source**:
   - Repository type: `GitHub`
   - Branch: `main`
   - Deployment trigger: `On push to branch`

### **Bước 3: Configure Service**

```
Port: 8000
Build command: (leave empty - use Dockerfile)
Start command: (leave empty - use Dockerfile CMD)
```

### **Bước 4: Set Environment Variables**

Add to AppRunner configuration:

```
DATABASE_URL=postgresql://...
SECRET_KEY=<strong-key>
VIRUSTOTAL_API_KEY=...
GSB_API_KEY=...
ABUSEIPDB_API_KEY=...
ENVIRONMENT=production
FRONTEND_URL=https://phishguard-frontend-xxx.us-east-1.cs.amazonapprunner.com
```

### **Bước 5: Deploy**

1. Nhấn **Create & Deploy**
2. Chờ 5-10 phút
3. Test health endpoint

---

## 💻 Local Development

### **Setup Environment**

```bash
# 1. Install dependencies
pip install -r Backend/requirements.txt

# 2. Create .env from example
cp Backend/.env.example Backend/.env

# 3. Edit .env with your local settings
# DATABASE_URL=postgresql://...
# SECRET_KEY=your-local-secret
```

### **Run Server**

```bash
# Development mode (auto-reload)
cd Backend
uvicorn backend.api:app --reload --port 8000

# Production mode (testing)
uvicorn backend.api:app --host 0.0.0.0 --port 8000
```

### **Run Tests**

```bash
cd Backend
python test_backend.py

# Or with pytest
pytest test_backend.py -v
```

### **Run with Docker Locally**

```bash
# Build image
docker build -t phishguard-backend Backend/

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e SECRET_KEY="your-key" \
  phishguard-backend
```

---

## 🔑 Generate Strong SECRET_KEY

### **Python**

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### **PowerShell**

```powershell
[System.Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((1..32 | ForEach-Object {[char][Random]::new().Next(33, 126)} | Join-String)))
```

---

## 🐛 Troubleshooting

### **Error: DATABASE_URL not set**

**Solution**: Add DATABASE_URL to platform environment variables

### **Error: SECRET_KEY required in production**

**Solution**: Generate & set SECRET_KEY environment variable

### **Error: Connection refused to database**

**Solution**: 
- Check DATABASE_URL is correct
- Verify Neon/RDS security groups allow connection
- Check connection string has correct SSL mode

### **Health check failing**

**Solution**:
- Check /health endpoint returns HTTP 200
- Verify port 8000 is open
- Check logs in platform dashboard

---

## 📊 Monitoring

### **Render Logs**

```
Dashboard → phishguard-backend → Logs
```

### **Health Check**

```bash
# Should return 200 OK
curl https://your-backend-url/health
```

### **API Docs**

```
https://your-backend-url/docs (Swagger UI)
https://your-backend-url/redoc (ReDoc)
```

---

## 🔐 Security Checklist

- [x] .env file not committed (check .gitignore)
- [x] API keys stored in platform env vars (not Dockerfile)
- [x] DATABASE_URL uses SSL (sslmode=require)
- [x] CORS properly configured for frontend domain
- [x] SECRET_KEY is strong (32+ chars)
- [x] Health check endpoint available
- [x] Logging configured (LOG_LEVEL=INFO)

---

## 📝 Quick Reference

### **Render Deployment Command**

```bash
git push origin main  # Render auto-detects & deploys
```

### **AWS AppRunner URL Pattern**

```
https://service-name-xxxx.region.cs.amazonapprunner.com
```

### **Environment Variable Priority**

```
1. Platform env vars (Render/AWS) - Highest
2. Dockerfile ENV - Medium
3. .env file - Lowest (local only)
```

---

## 📞 Support

- Render docs: https://render.com/docs
- AWS AppRunner: https://docs.aws.amazon.com/apprunner/
- FastAPI docs: https://fastapi.tiangolo.com/
