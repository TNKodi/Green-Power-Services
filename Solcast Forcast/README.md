# ThingsBoard Power Forecast API

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.128.0-green)
![License](https://img.shields.io/badge/license-MIT-blue)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen)

**Production-ready REST API for solar power forecasting with ThingsBoard integration**

[Features](#features) • [Quick Start](#quick-start) • [API Documentation](#api-endpoints) • [Configuration](#configuration) • [Development](#development)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [API Endpoints](#api-endpoints)
- [Error Handling](#error-handling)
- [Usage Examples](#usage-examples)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

---

## 🌟 Overview

The **ThingsBoard Power Forecast API** is a production-ready backend service designed to automate solar power forecasting for IoT assets managed in ThingsBoard. It retrieves asset configurations, runs sophisticated power prediction models using pvlib, and writes telemetry data back to ThingsBoard.

### What It Does

1. **Retrieves** solar panel configurations from ThingsBoard assets
2. **Calculates** power forecasts using industry-standard pvlib library
3. **Writes** telemetry predictions back to ThingsBoard for visualization
4. **Tracks** job progress with detailed error handling
5. **Supports** both batch processing and individual asset updates

### Use Cases

- **Automated Forecasting**: Schedule daily power predictions for all solar installations
- **New Installation Setup**: Process newly added solar assets
- **Monitoring & Analytics**: Track forecast accuracy and system performance
- **Energy Management**: Integrate predictions into energy management systems

---

## ✨ Features

### Core Functionality

- ✅ **Asynchronous Processing**: Non-blocking forecast jobs using FastAPI background tasks
- ✅ **Job Tracking**: Real-time status updates with progress monitoring
- ✅ **Error Resilience**: Comprehensive error handling with partial failure support
- ✅ **ThingsBoard Integration**: Seamless JWT authentication and API interaction
- ✅ **Solar Power Modeling**: Industry-standard pvlib for accurate predictions
- ✅ **Batch Processing**: Handle multiple assets efficiently
- ✅ **RESTful API**: Clean, well-documented HTTP endpoints

### Error Handling

- ✅ **Request Validation**: Asset ID, format, and business logic validation
- ✅ **Structured Errors**: Consistent JSON error responses with error codes
- ✅ **Partial Failures**: Jobs continue even when individual assets fail
- ✅ **Detailed Tracking**: Success/fail/skip counts with error details
- ✅ **Service Stability**: No crashes on invalid input

### Developer Experience

- ✅ **Auto-Generated Docs**: Interactive Swagger UI at `/docs`
- ✅ **Type Safety**: Pydantic models for request/response validation
- ✅ **Comprehensive Logging**: Structured logs with appropriate levels
- ✅ **Easy Setup**: One-command installation and startup
- ✅ **Test Suite**: Automated tests for all error scenarios

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Client App    │
│  (Dashboard,    │
│   Scheduler)    │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────────────────────────────┐
│      FastAPI Application                │
│  ┌───────────────────────────────────┐  │
│  │  API Endpoints                    │  │
│  │  • POST /forecast/start           │  │
│  │  • GET  /forecast/status/{id}     │  │
│  │  • POST /forecast/new-asset       │  │
│  │  • GET  /health                   │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  Business Logic Layer             │  │
│  │  • ForecastService                │  │
│  │  • JobManager                     │  │
│  │  • ThingsBoardClient              │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     ThingsBoard Cloud/Server            │
│  • Asset Management                     │
│  • Attribute Storage                    │
│  • Telemetry Ingestion                  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     Power Prediction Engine             │
│  • pvlib Solar Modeling                 │
│  • Weather Data Integration             │
│  • Daily Energy Calculations            │
└─────────────────────────────────────────┘
```

### Component Breakdown

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Layer** | FastAPI | HTTP endpoints, request validation |
| **Service Layer** | Python | Business logic, orchestration |
| **ThingsBoard Client** | HTTPX | Async API communication, JWT auth |
| **Job Manager** | In-Memory | Job tracking and status management |
| **Power Engine** | pvlib | Solar power calculations |
| **Validation** | Pydantic | Request/response schemas |
| **Logging** | Python logging | Structured logging system |

---

## 📦 Prerequisites

- **Python**: 3.9 or higher
- **ThingsBoard**: Cloud instance or self-hosted server
- **Credentials**: ThingsBoard username and password
- **Network**: Access to ThingsBoard API endpoint

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/TNKodi/Green-Power---Power-Calculations.git
cd "Power Predicition All devices"
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy template
copy .env.template .env

# Edit .env with your credentials
notepad .env
```

Required environment variables:

```env
TB_HOST=https://cloud.thingsnode.cc
TB_USERNAME=your-username@example.com
TB_PASSWORD=your-password
DEFAULT_TARGET_LEVEL=1
TZ_LOCAL=Asia/Colombo
DEBUG=false
```

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TB_HOST` | ✅ Yes | - | ThingsBoard server URL |
| `TB_USERNAME` | ✅ Yes | - | ThingsBoard login username |
| `TB_PASSWORD` | ✅ Yes | - | ThingsBoard login password |
| `DEFAULT_TARGET_LEVEL` | No | 1 | Asset hierarchy level to query |
| `TZ_LOCAL` | No | UTC | Timezone for calculations |
| `DEBUG` | No | false | Enable debug logging |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Asset Configuration

Assets in ThingsBoard must have these attributes:

| Attribute | Type | Example | Description |
|-----------|------|---------|-------------|
| `latitude` | float | 6.9271 | Location latitude |
| `longitude` | float | 79.8612 | Location longitude |
| `capacity_kw` | float | 10.5 | System capacity in kW |
| `tilt` | float | 10.0 | Panel tilt angle (degrees) |
| `azimuth` | float | 180.0 | Panel orientation (degrees) |
| `surface_type` | string | "urban" | Surface type for reflection |
| `losses` | float | 0.14 | System losses (0-1) |

---

## 🎯 Quick Start

### Start the API Server

```bash
# Using Python script
python start_api.py

# Or directly with uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server will start at: **http://localhost:8000**

### Access Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Make Your First Request

```bash
# Check API health
curl http://localhost:8000/health

# Start a forecast job
curl -X POST http://localhost:8000/forecast/start \
  -H "Content-Type: application/json" \
  -d '{"main_asset_id": "78fda490-e08b-11f0-b68f-8f33a9d74e0c"}'

# Check job status
curl http://localhost:8000/forecast/status/{job_id}
```

---

## 📚 Documentation

- [Setup Guide](docs/SETUP_GUIDE.md)
- [API Overview](docs/README_API.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Quick Reference](docs/QUICK_REFERENCE.md)
- [Index](docs/INDEX.md)
- [Project Complete Summary](docs/PROJECT_COMPLETE.md)
- [Error Handling Guide](docs/ERROR_HANDLING.md)
- [Error Handling Summary](docs/ERROR_HANDLING_SUMMARY.md)

---

## 📡 API Endpoints

### 1. Health Check

Check if the API is running.

```http
GET /health
```

**Response (200 OK):**
```json
{
  "status": "ok",
  "service": "thingsboard-power-forecast-api",
  "timestamp": "2026-01-21T10:30:00.000000"
}
```

---

### 2. Start Forecast Job

Start a background forecast job for a main asset and all related child assets.

```http
POST /forecast/start
```

**Request Body:**
```json
{
  "main_asset_id": "78fda490-e08b-11f0-b68f-8f33a9d74e0c"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "started",
  "message": "Forecast job started successfully",
  "main_asset_id": "78fda490-e08b-11f0-b68f-8f33a9d74e0c"
}
```

**Error Responses:**

- **400 Bad Request**: Missing or empty `main_asset_id`
  ```json
  {
    "detail": {
      "error": "ASSET_ID_REQUIRED",
      "message": "main_asset_id must be provided in the request body"
    }
  }
  ```

- **404 Not Found**: Asset doesn't exist in ThingsBoard
  ```json
  {
    "detail": {
      "error": "ASSET_NOT_FOUND",
      "message": "The provided asset_id does not exist in ThingsBoard",
      "asset_id": "78fda490-e08b-11f0-b68f-8f33a9d74e0c"
    }
  }
  ```

---

### 3. Check Job Status

Get the current status of a forecast job.

```http
GET /forecast/status/{job_id}
```

**Response (200 OK):**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "total_assets": 150,
  "assets_processed": 100,
  "successful_assets": 85,
  "failed_assets": 10,
  "skipped_assets": 5,
  "current_step": "processing_assets",
  "progress_message": "Processed 100/150 (success: 85, failed: 10, skipped: 5)",
  "errors": [
    {
      "asset_id": "ASSET_123",
      "error": "missing_required_attributes",
      "details": "Missing: latitude, longitude"
    }
  ],
  "started_at": "2026-01-21T10:30:00.000000",
  "completed_at": null
}
```

**Status Values:**
- `pending`: Job created, not started yet
- `running`: Job is currently processing
- `completed`: Job finished successfully
- `failed`: Job failed with errors

**Error Response:**

- **404 Not Found**: Invalid job ID
  ```json
  {
    "detail": "Job {job_id} not found"
  }
  ```

---

### 4. Process New Asset

Process a single newly added asset synchronously.

```http
POST /forecast/new-asset
```

**Request Body:**
```json
{
  "asset_id": "b4ee7360-f4fb-11f0-bef0-af3b94c8901e"
}
```

**Response (200 OK):**
```json
{
  "status": "telemetry_written",
  "asset_id": "b4ee7360-f4fb-11f0-bef0-af3b94c8901e",
  "message": "Successfully processed new asset"
}
```

**Error Responses:**

- **400 Bad Request**: Missing or empty `asset_id`
  ```json
  {
    "detail": {
      "error": "ASSET_ID_REQUIRED",
      "message": "asset_id must be provided in the request body"
    }
  }
  ```

- **404 Not Found**: Asset doesn't exist
  ```json
  {
    "detail": {
      "error": "ASSET_NOT_FOUND",
      "message": "The provided asset_id does not exist in ThingsBoard",
      "asset_id": "b4ee7360-f4fb-11f0-bef0-af3b94c8901e"
    }
  }
  ```

- **422 Unprocessable Entity**: Missing required attributes
  ```json
  {
    "detail": {
      "error": "ASSET_MISSING_ATTRIBUTES",
      "message": "Asset exists but required attributes are missing",
      "asset_id": "b4ee7360-f4fb-11f0-bef0-af3b94c8901e",
      "missing_attributes": ["latitude", "longitude", "capacity_kw"]
    }
  }
  ```

---

## 🚨 Error Handling

### HTTP Status Codes

| Code | Description | When Used |
|------|-------------|-----------|
| **200** | OK | Successful operation |
| **202** | Accepted | Job started successfully |
| **400** | Bad Request | Invalid input (missing/empty fields) |
| **404** | Not Found | Resource doesn't exist (asset/job) |
| **422** | Unprocessable Entity | Validation failed (missing attributes) |
| **500** | Internal Server Error | Server-side errors |

### Error Response Format

All errors return consistent JSON:

```json
{
  "detail": {
    "error": "ERROR_CODE",
    "message": "Human-readable description",
    "asset_id": "context_value",
    "missing_attributes": ["attr1", "attr2"]
  }
}
```

### Error Codes

| Error Code | HTTP | Description | Solution |
|------------|------|-------------|----------|
| `ASSET_ID_REQUIRED` | 400 | Missing/empty asset_id | Provide valid asset_id |
| `ASSET_NOT_FOUND` | 404 | Asset doesn't exist | Verify asset_id in ThingsBoard |
| `ASSET_MISSING_ATTRIBUTES` | 422 | Missing required attributes | Add attributes to asset |
| `Job not found` | 404 | Invalid job_id | Use job_id from start response |

### Partial Failure Handling

Jobs continue processing even when individual assets fail:

```json
{
  "status": "completed",
  "total_assets": 100,
  "successful_assets": 90,
  "failed_assets": 8,
  "skipped_assets": 2,
  "errors": [
    {"asset_id": "ASSET_1", "error": "missing_required_attributes"},
    {"asset_id": "ASSET_2", "error": "forecast_calculation_error"}
  ]
}
```

For detailed error handling documentation, see [docs/ERROR_HANDLING.md](docs/ERROR_HANDLING.md).

---

## 💡 Usage Examples

### Python Client

```python
import httpx
import asyncio

async def forecast_workflow():
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        # 1. Start forecast job
        response = await client.post(
            f"{base_url}/forecast/start",
            json={"main_asset_id": "78fda490-e08b-11f0-b68f-8f33a9d74e0c"}
        )
        
        if response.status_code == 202:
            job_id = response.json()["job_id"]
            print(f"Job started: {job_id}")
            
            # 2. Poll job status
            while True:
                status_response = await client.get(
                    f"{base_url}/forecast/status/{job_id}"
                )
                
                status = status_response.json()
                print(f"Progress: {status['assets_processed']}/{status['total_assets']}")
                
                if status["status"] in ["completed", "failed"]:
                    print(f"Job {status['status']}")
                    print(f"Success: {status['successful_assets']}")
                    print(f"Failed: {status['failed_assets']}")
                    break
                
                await asyncio.sleep(5)  # Wait 5 seconds
        else:
            print(f"Error: {response.json()}")

# Run the workflow
asyncio.run(forecast_workflow())
```

### JavaScript/Node.js

```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';

async function startForecast(assetId) {
  try {
    const response = await axios.post(`${BASE_URL}/forecast/start`, {
      main_asset_id: assetId
    });
    
    console.log('Job started:', response.data.job_id);
    return response.data.job_id;
    
  } catch (error) {
    if (error.response) {
      console.error('Error:', error.response.data.detail);
    } else {
      console.error('Request failed:', error.message);
    }
  }
}

async function checkJobStatus(jobId) {
  const response = await axios.get(`${BASE_URL}/forecast/status/${jobId}`);
  return response.data;
}

// Usage
(async () => {
  const jobId = await startForecast('78fda490-e08b-11f0-b68f-8f33a9d74e0c');
  
  if (jobId) {
    const status = await checkJobStatus(jobId);
    console.log('Job status:', status);
  }
})();
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Start forecast
curl -X POST http://localhost:8000/forecast/start \
  -H "Content-Type: application/json" \
  -d '{"main_asset_id": "78fda490-e08b-11f0-b68f-8f33a9d74e0c"}'

# Check status
curl http://localhost:8000/forecast/status/{job_id}

# Process new asset
curl -X POST http://localhost:8000/forecast/new-asset \
  -H "Content-Type: application/json" \
  -d '{"asset_id": "b4ee7360-f4fb-11f0-bef0-af3b94c8901e"}'
```

---

## 🔧 Development

### Project Structure

```
Power Predicition All devices/
│
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry
│   │
│   ├── api/                      # API endpoint definitions
│   │   ├── __init__.py
│   │   ├── health.py             # Health check endpoint
│   │   └── forecast.py           # Forecast endpoints
│   │
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── thingsboard_client.py # ThingsBoard API client
│   │   ├── forecast_service.py   # Forecast orchestration
│   │   └── job_manager.py        # Job tracking
│   │
│   ├── models/                   # Pydantic models
│   │   ├── __init__.py
│   │   ├── request_models.py     # Request schemas
│   │   └── response_models.py    # Response schemas
│   │
│   └── utils/                    # Utilities
│       ├── __init__.py
│       ├── config.py             # Configuration management
│       └── logger.py             # Logging setup
│
├── Scripts/                      # Original power prediction code
│   └── power_predicition/
│       ├── power.py              # Power calculation engine
│       ├── get_asset.py          # Asset retrieval
│       └── atribute_read.py      # Attribute processing
│
├── tests/                        # Test files
│   └── test_error_handling.py    # Error handling tests
│
├── docs/                         # Documentation bundle
│   ├── ARCHITECTURE.md           # Architecture deep dive
│   ├── ERROR_HANDLING.md         # Error handling guide
│   ├── ERROR_HANDLING_SUMMARY.md # Error handling summary
│   ├── INDEX.md                  # Documentation index
│   ├── PROJECT_COMPLETE.md       # Project completion summary
│   ├── QUICK_REFERENCE.md        # Quick command/API reference
│   ├── README_API.md             # API quickstart overview
│   └── SETUP_GUIDE.md            # Setup and installation guide
├── .env                          # Environment variables (not in git)
├── .env.template                 # Environment template
├── .gitignore                    # Git ignore rules
├── requirements.txt              # Python dependencies
├── start_api.py                  # API startup script
├── README.md                     # This file
```

### Setting Up Development Environment

```bash
# Install development dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install

# Run in development mode
uvicorn app.main:app --reload --log-level debug
```

### Code Style

- **Formatting**: Follow PEP 8
- **Type Hints**: Use type annotations
- **Docstrings**: Google style docstrings
- **Async/Await**: Use async for I/O operations
- **Error Handling**: Always catch and log exceptions

### Adding New Endpoints

1. Create endpoint in `app/api/`
2. Add request/response models in `app/models/`
3. Implement business logic in `app/services/`
4. Register router in `app/main.py`
5. Add tests
6. Update documentation

---

## 🧪 Testing

### Automated Tests

Run the error handling test suite:

```bash
# Make sure API is running first
python start_api.py

# In another terminal
python test_error_handling.py
```

### Manual Testing

Use the interactive Swagger UI:

1. Open http://localhost:8000/docs
2. Click "Try it out" on any endpoint
3. Enter parameters and execute
4. View responses and examples

### Test Coverage

Current test coverage:

- ✅ Health check endpoint
- ✅ Missing asset_id validation
- ✅ Non-existent asset detection
- ✅ Missing attributes validation
- ✅ Job status tracking
- ✅ Invalid job_id handling
- ✅ Error response formats
- ✅ Partial failure scenarios

---

## 🚢 Deployment

### Production Checklist

- [ ] Set `DEBUG=false` in `.env`
- [ ] Use strong passwords
- [ ] Configure CORS appropriately
- [ ] Set up HTTPS/TLS
- [ ] Configure rate limiting
- [ ] Set up monitoring/logging
- [ ] Configure backup strategy
- [ ] Test error scenarios
- [ ] Document runbooks

### Deployment Options

#### Option 1: Systemd Service (Linux)

```bash
# Create service file
sudo nano /etc/systemd/system/forecast-api.service
```

```ini
[Unit]
Description=ThingsBoard Forecast API
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/project
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable forecast-api
sudo systemctl start forecast-api
```

#### Option 2: Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
# Build and run
docker build -t forecast-api .
docker run -d -p 8000:8000 --env-file .env forecast-api
```

#### Option 3: Cloud Platforms

- **Heroku**: `Procfile` with `web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **AWS Lambda**: Use Mangum adapter for serverless
- **Google Cloud Run**: Deploy as containerized service
- **Azure App Service**: Deploy as Python web app

### Monitoring

Set up monitoring for:

- API uptime and response times
- Error rates and types
- Job success/failure rates
- ThingsBoard API connectivity
- System resource usage

---

## 🔍 Troubleshooting

### Common Issues

#### API Won't Start

**Problem**: `ModuleNotFoundError` or import errors

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Verify Python version
python --version  # Should be 3.9+
```

#### Authentication Failures

**Problem**: "Invalid credentials" or 401 errors

**Solution**:
```bash
# Check .env file
cat .env

# Verify credentials in ThingsBoard
# Update TB_USERNAME and TB_PASSWORD
```

#### No Assets Found

**Problem**: Job returns 0 assets

**Solution**:
- Verify `DEFAULT_TARGET_LEVEL` matches your asset hierarchy
- Check assets exist in ThingsBoard
- Verify asset relationships are correct

#### Missing Attributes

**Problem**: Assets skipped due to missing attributes

**Solution**:
```bash
# Add required attributes to assets in ThingsBoard:
# - latitude, longitude
# - capacity_kw
# - tilt, azimuth
# - surface_type
# - losses
```

#### Job Stuck in "Running"

**Problem**: Job doesn't complete

**Solution**:
- Check API logs for errors
- Verify ThingsBoard connectivity
- Restart API server
- Check job status for error details

### Debug Mode

Enable detailed logging:

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

Then restart the API and check logs.

### Getting Help

1. Check logs in terminal where API is running
2. Review [docs/ERROR_HANDLING.md](docs/ERROR_HANDLING.md)
3. Test with `/health` endpoint
4. Verify `.env` configuration
5. Run test suite: `python test_error_handling.py`

---

## 📊 Performance

### Benchmarks

- **Health Check**: < 10ms
- **Job Start**: < 500ms (immediate return)
- **Asset Processing**: ~2-5s per asset
- **Status Check**: < 50ms

### Optimization Tips

- Use batch processing for multiple assets
- Configure appropriate `DEFAULT_TARGET_LEVEL`
- Monitor ThingsBoard API response times
- Consider caching for frequently accessed data

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Commit with clear messages (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for public APIs
- Include tests for new features
- Update documentation

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 📞 Support

- **Issues**: https://github.com/TNKodi/Green-Power---Power-Calculations/issues
- **Discussions**: https://github.com/TNKodi/Green-Power---Power-Calculations/discussions
- **Documentation**: Check `/docs` endpoint when API is running

---

## 🙏 Acknowledgments

- **FastAPI**: Modern, fast web framework
- **pvlib**: Solar power modeling library
- **ThingsBoard**: IoT platform for asset management
- **Pydantic**: Data validation and settings management

---

## 📈 Roadmap

### Planned Features

- [ ] Rate limiting for API endpoints
- [ ] Webhook notifications for job completion
- [ ] Historical forecast accuracy tracking
- [ ] Multi-tenant support
- [ ] Database persistence for job history
- [ ] Grafana dashboard integration
- [ ] Automated testing CI/CD
- [ ] Docker Compose setup

---

<div align="center">

**Built with ❤️ for sustainable energy**

[⬆ Back to Top](#thingsboard-power-forecast-api)

</div>