# 🚀 Quick Start Guide - PDF to JSON API

Get your PDF processing API up and running in 5 minutes!

## ⚡ Fast Setup (Windows)

### Option 1: Automated Setup (Recommended)

```powershell
# Run the setup script
.\setup.ps1

# Start the server
python run.py
```

### Option 2: Manual Setup

```powershell
# 1. Create virtual environment
python -m venv venv

# 2. Activate it
venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python run.py
```

## 🔥 Fast Setup (Linux/Mac)

```bash
# 1. Create virtual environment
python3 -m venv venv

# 2. Activate it
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
python run.py
```

## ✅ Verify Installation

Open your browser and visit:

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

You should see the Swagger UI and a healthy status!

## 📤 Upload Your First PDF

### Using the Web Interface (Easiest)

1. Go to http://localhost:8000/docs
2. Click on **POST /api/v1/upload-pdf**
3. Click **Try it out**
4. Click **Choose File** and select a PDF
5. Click **Execute**
6. Copy the `request_id` from the response

### Using cURL

```bash
curl -X POST "http://localhost:8000/api/v1/upload-pdf" \
  -F "file=@your-file.pdf"
```

### Using Python

```python
import requests

with open("your-file.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/api/v1/upload-pdf", files=files)
    request_id = response.json()["request_id"]
    print(f"Request ID: {request_id}")
```

## 📊 Extract Data

### Get Full Text

```bash
# Replace {request_id} with your actual ID
curl "http://localhost:8000/api/v1/pdf/{request_id}/fulltext"
```

### Get Structured Data

```bash
curl "http://localhost:8000/api/v1/pdf/{request_id}/extract"
```

## 🧪 Run Tests

Test the API with a sample PDF:

```bash
# With a PDF file
python test_api.py "path/to/your/file.pdf"

# Without a PDF (tests health check and error handling only)
python test_api.py
```

## 📖 Next Steps

- **Full Documentation**: See [README.md](README.md)
- **cURL Examples**: See [CURL_EXAMPLES.md](CURL_EXAMPLES.md)
- **API Docs**: http://localhost:8000/docs
- **Customize Extraction**: Edit `app/services/extractor.py`

## 🛠️ Common Commands

```bash
# Start server (development mode with auto-reload)
python run.py

# Start server (production mode)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run tests
python test_api.py sample.pdf

# View logs
# Logs are printed to console by default
```

## 🐛 Troubleshooting

### Port 8000 already in use

```bash
# Use a different port
uvicorn app.main:app --port 8001
```

### Module not found errors

```bash
# Make sure virtual environment is activated
# Windows
venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### PDF upload fails

- Check file size (<10MB)
- Ensure file is actually a PDF
- Check server logs for details

## 🎯 Example Workflow

```python
import requests
import json

BASE = "http://localhost:8000/api/v1"

# 1. Upload
with open("sample.pdf", "rb") as f:
    resp = requests.post(f"{BASE}/upload-pdf", files={"file": f})
    req_id = resp.json()["request_id"]

# 2. Get full text
text = requests.get(f"{BASE}/pdf/{req_id}/fulltext").json()
print(f"Extracted {len(text['full_text'])} characters")

# 3. Get structured data
data = requests.get(f"{BASE}/pdf/{req_id}/extract").json()
print(json.dumps(data["data"], indent=2))
```

## 💡 Pro Tips

1. **Use the interactive docs**: http://localhost:8000/docs is your friend!
2. **Check the health endpoint** before uploading: http://localhost:8000/health
3. **Save request IDs**: You'll need them to retrieve data later
4. **Enable debug logging**: Set `LOG_LEVEL=DEBUG` in `.env`
5. **Test with small PDFs first**: Under 1MB is ideal for testing

## 📞 Need Help?

- Check the [full README](README.md) for detailed documentation
- Review [CURL_EXAMPLES.md](CURL_EXAMPLES.md) for API usage examples
- Open an issue on GitHub if you encounter problems

---

**That's it! You're ready to process PDFs! 🎉**
