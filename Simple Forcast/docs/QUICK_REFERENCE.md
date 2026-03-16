# 📋 Quick Reference - ThingsBoard Power Forecast API

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.template .env
# Edit .env with your credentials

# 3. Start API
python start_api.py
```

## 🌐 API Endpoints

### Health Check
```http
GET /health
```
Returns service status instantly.

### Start Forecast Job
```http
POST /forecast/start
Content-Type: application/json

{
  "main_asset_id": "YOUR_ASSET_ID"
}
```
Returns `job_id` immediately, job runs in background.

### Check Job Status
```http
GET /forecast/status/{job_id}
```
Returns job progress and status.

### Process New Asset
```http
POST /forecast/new-asset
Content-Type: application/json

{
  "asset_id": "YOUR_ASSET_ID"
}
```
Processes single asset synchronously.

## 🔧 Configuration (.env)

```env
TB_HOST=http://your-thingsboard:8080
TB_USERNAME=your_email@example.com
TB_PASSWORD=your_password
TARGET_LEVEL=3
TZ_LOCAL=Asia/Colombo
LOG_LEVEL=INFO
```

## 📝 Job Status Values

| Status | Description |
|--------|-------------|
| `pending` | Job created, not started |
| `running` | Currently executing |
| `completed` | Finished successfully |
| `failed` | Error occurred |

## 🛠️ Common Commands

### Start API
```bash
# Development (auto-reload)
python start_api.py

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Test Configuration
```bash
python test_setup.py
```

### View Logs
```bash
# Real-time (Windows PowerShell)
Get-Content logs\api_20260121.log -Tail 50 -Wait

# Real-time (Linux/Mac)
tail -f logs/api_20260121.log
```

## 🐛 Troubleshooting

### API won't start
- Check `.env` file exists
- Verify credentials are correct
- Ensure port 8000 is available

### Job fails
- Check ThingsBoard connection
- Verify asset ID is valid
- Review logs in `logs/` directory

### No telemetry written
- Confirm asset has required attributes
- Check user permissions in ThingsBoard
- Verify forecast model runs successfully

## 📚 URLs

| Resource | URL |
|----------|-----|
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |
| OpenAPI Schema | http://localhost:8000/openapi.json |

## 🔒 Security Checklist

- [ ] `.env` in `.gitignore`
- [ ] Strong passwords
- [ ] CORS configured
- [ ] HTTPS in production
- [ ] Secrets properly managed

## 📞 Support Files

- `README_API.md` - Full API documentation
- `SETUP_GUIDE.md` - Detailed setup instructions
- `example_usage.py` - Code examples
- `test_setup.py` - Setup verification

## 💡 Pro Tips

1. **Development**: Use `DEBUG=True` for detailed logs
2. **Testing**: Test single asset first with `/forecast/new-asset`
3. **Monitoring**: Set up `/health` endpoint monitoring
4. **Performance**: Adjust `TARGET_LEVEL` based on your hierarchy

---

**Need help?** Check logs, review documentation, verify configuration.
