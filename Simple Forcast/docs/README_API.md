# ThingsBoard Power Forecast API

A production-ready FastAPI backend service for running power forecasting models on ThingsBoard assets.

## 🎯 Overview

This API service:
- Connects to ThingsBoard using REST APIs
- Loads assets recursively from a main asset (multi-level relations)
- Runs power forecasting models
- Writes predicted power as telemetry to ThingsBoard assets
- Provides async execution with background tasks
- Tracks long-running job progress

## 📁 Project Structure

```
.
├── app/
│   ├── main.py                      # FastAPI application entry point
│   ├── api/
│   │   ├── health.py                # Health check endpoint
│   │   └── forecast.py              # Forecast endpoints
│   ├── services/
│   │   ├── thingsboard_client.py    # ThingsBoard REST API client
│   │   ├── forecast_service.py      # Forecast orchestration logic
│   │   └── job_manager.py           # Job tracking and status management
│   ├── models/
│   │   ├── request_models.py        # API request models
│   │   └── response_models.py       # API response models
│   └── utils/
│       ├── config.py                # Configuration management
│       └── logger.py                # Logging setup
├── Scripts/
│   └── power_predicition/           # Existing power prediction logic
├── .env.template                    # Environment variables template
├── requirements.txt                 # Python dependencies
└── README_API.md                    # This file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the template and fill in your ThingsBoard credentials:

```bash
cp .env.template .env
```

Edit `.env`:

```env
TB_HOST=http://your-thingsboard-host:8080
TB_USERNAME=your_username@example.com
TB_PASSWORD=your_password
TARGET_LEVEL=3
TZ_LOCAL=Asia/Colombo
LOG_LEVEL=INFO
DEBUG=False
```

### 3. Run the API

```bash
# Development mode (with auto-reload)
python -m app.main

# Or using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the API

- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### 1. Health Check

**GET** `/health`

Check if the service is running.

**Response:**
```json
{
  "status": "ok",
  "service": "thingsboard-power-forecast-api",
  "timestamp": "2026-01-21T10:30:00"
}
```

---

### 2. Start Forecast Job

**POST** `/forecast/start`

Trigger a long-running forecast job for all assets under a main asset.

**Request:**
```json
{
  "main_asset_id": "78fda490-e08b-11f0-b68f-8f33a9d74e0c"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "started"
}
```

**Behavior:**
- Returns immediately with a job ID
- Job runs in background
- Traverses asset hierarchy to configured level
- Processes each asset: reads attributes → runs forecast → writes telemetry

---

### 3. Check Job Status

**GET** `/forecast/status/{job_id}`

Check the progress of a forecast job.

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": "Processed 15/25 assets (failed: 0)",
  "started_at": "2026-01-21T10:30:00",
  "updated_at": "2026-01-21T10:35:00",
  "completed_at": null,
  "error": null,
  "assets_processed": 15,
  "total_assets": 25
}
```

**Status Values:**
- `pending` - Job created but not started
- `running` - Job is currently executing
- `completed` - Job finished successfully
- `failed` - Job encountered an error

---

### 4. Process New Asset

**POST** `/forecast/new-asset`

Process a single new asset immediately.

**Request:**
```json
{
  "asset_id": "b4ee7360-f4fb-11f0-bef0-af3b94c8901e"
}
```

**Response:**
```json
{
  "status": "telemetry_written",
  "asset_id": "b4ee7360-f4fb-11f0-bef0-af3b94c8901e",
  "message": "Successfully processed new asset"
}
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TB_HOST` | ThingsBoard server URL | `http://localhost:8080` |
| `TB_USERNAME` | ThingsBoard username | Required |
| `TB_PASSWORD` | ThingsBoard password | Required |
| `TARGET_LEVEL` | Asset hierarchy depth | `3` |
| `TZ_LOCAL` | Local timezone | `Asia/Colombo` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG` | Debug mode | `False` |

### Asset Hierarchy

The API traverses the asset hierarchy from a root asset to a target level:

```
Root Asset (Level 0)
  └── Level 1 Assets
       └── Level 2 Assets
            └── Level 3 Assets (TARGET_LEVEL=3)
```

## 🏗️ Architecture

### Async Design

- **FastAPI**: Async web framework
- **Background Tasks**: Long-running jobs don't block API responses
- **HTTPX**: Async HTTP client for ThingsBoard
- **Job Manager**: In-memory job tracking (easily replaceable with Redis)

### Authentication

- JWT tokens are automatically managed
- Tokens refresh before expiration
- No user authentication required (internal service)

### Error Handling

- Comprehensive error logging
- Failed jobs are marked with error messages
- Individual asset failures don't stop the entire job

## 📊 Monitoring

### Health Checks

Use the `/health` endpoint for:
- Kubernetes liveness probes
- Load balancer health checks
- Monitoring systems

### Logs

Logs are written to:
- Console (stdout)
- File: `logs/api_YYYYMMDD.log`

Log format:
```
2026-01-21 10:30:15 - thingsboard-forecast - INFO - Processing asset b4ee7360-f4fb-11f0-bef0-af3b94c8901e
```

## 🔐 Security Considerations

1. **Environment Variables**: Never commit `.env` file
2. **CORS**: Configure `allow_origins` in production
3. **Internal Service**: Add authentication if exposing publicly
4. **Secrets Management**: Use proper secrets management in production

## 🚀 Production Deployment

### Docker Example

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY Scripts/ Scripts/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Systemd Service

```ini
[Unit]
Description=ThingsBoard Power Forecast API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/forecast-api
Environment="PATH=/opt/forecast-api/venv/bin"
ExecStart=/opt/forecast-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### Environment Variables in Production

Use proper secrets management:
- Kubernetes Secrets
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

## 🔄 Future Enhancements

The current design makes these easy to add:

1. **Redis Integration**: Replace in-memory job manager
2. **Cron Jobs**: Schedule periodic forecasts
3. **Retry Logic**: Auto-retry failed assets
4. **Metrics**: Prometheus metrics endpoint
5. **Authentication**: Add API key or OAuth
6. **Rate Limiting**: Prevent API abuse
7. **Webhooks**: Notify when jobs complete

## 📝 Example Usage

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Start forecast job
curl -X POST http://localhost:8000/forecast/start \
  -H "Content-Type: application/json" \
  -d '{"main_asset_id": "78fda490-e08b-11f0-b68f-8f33a9d74e0c"}'

# Check job status
curl http://localhost:8000/forecast/status/550e8400-e29b-41d4-a716-446655440000

# Process new asset
curl -X POST http://localhost:8000/forecast/new-asset \
  -H "Content-Type: application/json" \
  -d '{"asset_id": "b4ee7360-f4fb-11f0-bef0-af3b94c8901e"}'
```

### Using Python

```python
import requests

BASE_URL = "http://localhost:8000"

# Start forecast
response = requests.post(
    f"{BASE_URL}/forecast/start",
    json={"main_asset_id": "78fda490-e08b-11f0-b68f-8f33a9d74e0c"}
)
job_id = response.json()["job_id"]

# Check status
status = requests.get(f"{BASE_URL}/forecast/status/{job_id}")
print(status.json())
```

## 🐛 Troubleshooting

### API won't start

Check:
1. `.env` file exists and has correct values
2. ThingsBoard credentials are valid
3. Port 8000 is not already in use

### Jobs failing

Check:
1. ThingsBoard server is accessible
2. Asset IDs are valid
3. Assets have required attributes
4. Logs in `logs/` directory

### No telemetry written

Check:
1. Asset attributes contain required fields
2. Power prediction model runs successfully
3. ThingsBoard user has write permissions

## 📞 Support

For issues or questions:
1. Check the logs in `logs/`
2. Review API documentation at `/docs`
3. Verify ThingsBoard connectivity

---

**Built with ❤️ using FastAPI**
