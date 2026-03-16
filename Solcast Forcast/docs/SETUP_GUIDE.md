# 🚀 Setup Guide - ThingsBoard Power Forecast API

Complete step-by-step guide to get the API up and running.

## Prerequisites

- Python 3.9 or higher
- Access to a ThingsBoard server
- ThingsBoard credentials (username/password)

## Step-by-Step Setup

### 1. Verify Python Installation

```bash
python --version
# Should show Python 3.9 or higher
```

### 2. Create Virtual Environment (Recommended)

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- FastAPI and Uvicorn (API framework)
- HTTPX (async HTTP client)
- pvlib (solar power calculations)
- pandas, numpy (data processing)
- python-dotenv (environment variables)

### 4. Configure Environment Variables

**Create .env file:**

**Windows (PowerShell):**
```powershell
Copy-Item .env.template .env
```

**Linux/Mac:**
```bash
cp .env.template .env
```

**Edit .env file** with your actual credentials:

```env
# Required Settings
TB_HOST=http://your-thingsboard-server.com:8080
TB_USERNAME=your_email@example.com
TB_PASSWORD=your_password

# Optional Settings
TARGET_LEVEL=3
TZ_LOCAL=Asia/Colombo
LOG_LEVEL=INFO
DEBUG=False
```

⚠️ **IMPORTANT**: Never commit the `.env` file to version control!

### 5. Test Configuration

Quick test to verify ThingsBoard connection:

```bash
python -c "from app.utils.config import settings; settings.validate(); print('✓ Configuration valid')"
```

### 6. Start the API Server

**Option A: Using Python directly**
```bash
python start_api.py
```

**Option B: Using PowerShell script (Windows)**
```powershell
.\start_api.ps1
```

**Option C: Using uvicorn directly**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. Verify API is Running

Open your browser and visit:

- **Swagger UI**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

You should see:
```json
{
  "status": "ok",
  "service": "thingsboard-power-forecast-api",
  "timestamp": "2026-01-21T10:30:00"
}
```

## 🎯 Quick Test

### Test 1: Health Check

```bash
curl http://localhost:8000/health
```

### Test 2: Start a Forecast Job

Replace `YOUR_ASSET_ID` with an actual asset ID from your ThingsBoard:

```bash
curl -X POST http://localhost:8000/forecast/start \
  -H "Content-Type: application/json" \
  -d "{\"main_asset_id\": \"YOUR_ASSET_ID\"}"
```

You'll get a response like:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started"
}
```

### Test 3: Check Job Status

Use the `job_id` from the previous step:

```bash
curl http://localhost:8000/forecast/status/550e8400-e29b-41d4-a716-446655440000
```

## 📁 Project Structure After Setup

```
your-project/
├── app/                      # API application code
│   ├── main.py              # FastAPI app
│   ├── api/                 # API endpoints
│   ├── services/            # Business logic
│   ├── models/              # Request/response models
│   └── utils/               # Utilities
├── Scripts/                  # Existing power prediction code
│   └── power_predicition/
├── logs/                     # Log files (created automatically)
│   └── api_20260121.log
├── venv/                     # Virtual environment (if created)
├── .env                      # Your configuration (DO NOT COMMIT)
├── .env.template            # Template for .env
├── requirements.txt         # Python dependencies
├── start_api.py            # Startup script
├── start_api.ps1           # PowerShell startup script
└── README_API.md           # API documentation
```

## 🔧 Troubleshooting

### Issue: "Module not found" errors

**Solution**: Make sure you're in the virtual environment and dependencies are installed:
```bash
pip install -r requirements.txt
```

### Issue: "Configuration validation failed"

**Solution**: Check your `.env` file has all required variables:
```env
TB_HOST=http://...
TB_USERNAME=...
TB_PASSWORD=...
```

### Issue: "Port 8000 already in use"

**Solution**: Either stop the other service or use a different port:
```bash
uvicorn app.main:app --port 8001
```

### Issue: "Connection to ThingsBoard failed"

**Solution**: 
1. Verify `TB_HOST` is correct and accessible
2. Check username/password are correct
3. Ensure ThingsBoard server is running
4. Check firewall settings

### Issue: "Assets not found"

**Solution**:
1. Verify the asset ID is correct
2. Check the `TARGET_LEVEL` setting
3. Ensure asset hierarchy exists in ThingsBoard

## 📊 Checking Logs

Logs are written to:
- **Console**: Real-time output
- **File**: `logs/api_YYYYMMDD.log`

To view logs:

**Windows (PowerShell):**
```powershell
Get-Content logs\api_20260121.log -Tail 50 -Wait
```

**Linux/Mac:**
```bash
tail -f logs/api_20260121.log
```

## 🔐 Security Checklist

Before deploying to production:

- [ ] `.env` file is in `.gitignore`
- [ ] Strong passwords used for ThingsBoard
- [ ] CORS settings configured properly
- [ ] API authentication added (if exposing publicly)
- [ ] HTTPS enabled
- [ ] Secrets stored in proper secrets management system

## 🚀 Next Steps

1. **Read the API Documentation**: Visit http://localhost:8000/docs
2. **Test with Real Data**: Use your ThingsBoard asset IDs
3. **Monitor Job Progress**: Use the status endpoint
4. **Review Logs**: Check `logs/` directory
5. **Customize**: Modify settings in `.env` as needed

## 📚 Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **ThingsBoard API**: https://thingsboard.io/docs/api/
- **pvlib Documentation**: https://pvlib-python.readthedocs.io/

## 💡 Tips

1. **Development**: Use `DEBUG=True` and `LOG_LEVEL=DEBUG` for detailed logs
2. **Production**: Use `DEBUG=False` and `LOG_LEVEL=INFO`
3. **Testing**: Process a single asset first using `/forecast/new-asset`
4. **Monitoring**: Set up health check monitoring on `/health`

---

Need help? Check the troubleshooting section or review the logs!
