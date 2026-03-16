# PDF to JSON Processing API

A production-ready REST API for extracting text and structured data from PDF files using FastAPI and pdfplumber.

## 📚 Documentation

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get the API up and running in 5 minutes
- **[Project Summary](docs/PROJECT_SUMMARY.md)** - Complete overview of features and architecture
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment checklist and setup
- **[API Examples](docs/CURL_EXAMPLES.md)** - cURL commands for testing all endpoints

## Features

- **PDF Upload**: Secure file upload with validation (max 10MB)
- **Full Text Extraction**: Extract complete text content from PDFs
- **Structured Data Extraction**: Extract predefined fields using regex patterns
- **Health Monitoring**: Health check endpoint for service monitoring
- **Error Handling**: Comprehensive error handling with detailed messages
- **Logging**: Request/response logging for debugging and monitoring
- **API Documentation**: Auto-generated OpenAPI (Swagger) documentation

## Tech Stack

- **Framework**: FastAPI 0.115.0
- **Server**: Uvicorn
- **PDF Processing**: pdfplumber 0.11.4
- **Data Validation**: Pydantic 2.9.0
- **Python**: 3.10+

## Project Structure

```
PDF to JSON/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # API route handlers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pdf_reader.py       # PDF text extraction service
│   │   └── extractor.py        # Structured data extraction service
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   └── utils/
│       ├── __init__.py
│       ├── logger.py           # Logging configuration
│       └── exceptions.py       # Custom exceptions
├── temp_pdfs/                  # Temporary PDF storage
├── .env                        # Environment variables
├── .gitignore
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd "PDF to JSON"
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables (optional)

Edit `.env` file to customize settings:

```env
HOST=0.0.0.0
PORT=8000
MAX_FILE_SIZE_MB=10
LOG_LEVEL=INFO
```

## Running the API

### Development Mode (with auto-reload)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or run directly:

```bash
python -m app.main
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 1. Health Check

Check if the service is running.

```bash
curl -X GET "http://localhost:8000/health"
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2026-01-21T10:30:45.123456"
}
```

### 2. Upload PDF

Upload a PDF file for processing.

```bash
curl -X POST "http://localhost:8000/api/v1/upload-pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@path/to/your/file.pdf"
```

**Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "PDF uploaded successfully"
}
```

### 3. Extract Full Text

Get complete text from the uploaded PDF.

```bash
curl -X GET "http://localhost:8000/api/v1/pdf/{request_id}/fulltext"
```

**Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "full_text": "Complete text content from all pages..."
}
```

### 4. Extract Structured Data

Extract predefined fields from the PDF.

```bash
curl -X GET "http://localhost:8000/api/v1/pdf/{request_id}/extract"
```

**Response:**
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "Project": "GGC_S_0038 - Ranabima Royal College",
    "System power": 50.4,
    "Longitude": 80.123,
    "Latitude": 6.456,
    "pv_module_manufacturer": "Canadian Solar",
    "pv_module_model": "CS3W-420P",
    "inverter_manufacturer": "Huawei",
    "inverter_model": "SUN2000-50KTL-M3",
    "Nb. of modules": 120,
    "soiling_loss_pct": "2.5",
    "dc_wiring_loss_pct": "1.5"
  }
}
```

## Example Usage with Python

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000/api/v1"

# 1. Upload PDF
with open("sample.pdf", "rb") as f:
    files = {"file": ("sample.pdf", f, "application/pdf")}
    response = requests.post(f"{BASE_URL}/upload-pdf", files=files)
    data = response.json()
    request_id = data["request_id"]
    print(f"Uploaded PDF with ID: {request_id}")

# 2. Get full text
response = requests.get(f"{BASE_URL}/pdf/{request_id}/fulltext")
full_text = response.json()["full_text"]
print(f"Extracted {len(full_text)} characters")

# 3. Get structured data
response = requests.get(f"{BASE_URL}/pdf/{request_id}/extract")
extracted_data = response.json()["data"]
print(f"Extracted fields: {list(extracted_data.keys())}")
```

## Error Handling

The API returns consistent error responses:

```json
{
  "error": true,
  "message": "Invalid file type. Only PDF files are allowed.",
  "code": 400
}
```

### Common Error Codes

- **400**: Bad Request (invalid file type, file too large, missing file)
- **404**: Not Found (invalid request_id)
- **422**: Unprocessable Entity (corrupted PDF, parsing failure)
- **500**: Internal Server Error (unexpected errors)

## Validation Rules

### File Upload

- **File Type**: Must be `.pdf`
- **File Size**: Maximum 10MB
- **Required**: File must be provided

### Request ID

- Must be a valid UUID from a previous upload
- PDF must still exist in temp storage

## Extracted Fields

The structured extraction can extract the following fields (when available):

### Project Information
- Project name
- System power
- Longitude/Latitude
- Altitude
- Albedo

### Module Information
- Number of modules
- PV module manufacturer
- PV module model
- Unit PV power
- Module area

### Inverter Information
- Inverter units
- Inverter manufacturer
- Inverter model
- Inverter power
- Pnom ratio

### Array Information
- Number of arrays
- Array tilt/azimuth
- Modules per array

### Losses
- Soiling loss
- LID (Light Induced Degradation)
- Module quality loss
- Module mismatch loss
- DC wiring loss
- AC wiring loss

### IAM (Incidence Angle Modifier)
- IAM angles
- IAM values

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

The project follows PEP 8 guidelines. Use:

```bash
# Format code
black app/

# Check linting
flake8 app/
```

### Adding New Extraction Fields

To add new fields to the extraction logic:

1. Edit `app/services/extractor.py`
2. Add extraction logic in appropriate method
3. Update `app/models/schemas.py` if needed
4. Test with sample PDFs

## Logging

Logs are output to console with the following format:

```
2026-01-21 10:30:45 - pdf_api - INFO - [request_id] Message
```

Configure log level in `.env`:
```env
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## Production Deployment

### Using Docker (Recommended)

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t pdf-api .
docker run -p 8000:8000 pdf-api
```

### Using Systemd (Linux)

Create `/etc/systemd/system/pdf-api.service`:

```ini
[Unit]
Description=PDF to JSON API
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/PDF to JSON
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable pdf-api
sudo systemctl start pdf-api
```

## Security Considerations

### For Production:

1. **CORS**: Update `ALLOWED_ORIGINS` in `.env` with specific domains
2. **File Storage**: Implement file cleanup (delete old PDFs)
3. **Rate Limiting**: Add rate limiting middleware
4. **Authentication**: Add API key or OAuth2 authentication
5. **HTTPS**: Deploy behind reverse proxy (Nginx/Apache) with SSL
6. **Input Validation**: Already implemented, but review for your use case
7. **File Scanning**: Consider adding virus/malware scanning

## Troubleshooting

### PDF Parsing Fails

- Ensure PDF is not password-protected
- Check if PDF contains actual text (not scanned images)
- Try with a different PDF

### Memory Issues

- Reduce `MAX_FILE_SIZE_MB` in `.env`
- Implement file cleanup for temp PDFs
- Use streaming for large files

### Port Already in Use

```bash
# Change port in .env or use different port
uvicorn app.main:app --port 8001
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - See LICENSE file for details

## Support

For issues and questions:
- Open an issue on GitHub
- Check API documentation at `/docs`
- Review logs for error details

## Changelog

### Version 1.0.0 (2026-01-21)
- Initial release
- PDF upload endpoint
- Full text extraction
- Structured data extraction
- Health check endpoint
- Comprehensive error handling
- API documentation
