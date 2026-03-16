# 🚀 Deployment Checklist

Use this checklist when deploying the PDF to JSON API to production.

## 📋 Pre-Deployment Checklist

### Code & Configuration
- [ ] All tests pass (`python test_api.py`)
- [ ] No hardcoded credentials or secrets
- [ ] `.env` file configured for production
- [ ] `.gitignore` properly configured
- [ ] All dependencies in `requirements.txt`
- [ ] Code reviewed and approved

### Security
- [ ] CORS origins restricted (update `.env`)
- [ ] File size limits appropriate
- [ ] Input validation tested
- [ ] Error messages don't leak sensitive info
- [ ] Add authentication mechanism (API keys/OAuth2)
- [ ] Add rate limiting
- [ ] Plan for file cleanup/TTL
- [ ] HTTPS configured (reverse proxy)

### Environment Variables
```env
# Production .env template
APP_NAME="PDF to JSON API"
DEBUG=False
HOST=0.0.0.0
PORT=8000
MAX_FILE_SIZE_MB=10
TEMP_PDF_DIR=temp_pdfs
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Infrastructure
- [ ] Server/container provisioned
- [ ] Python 3.10+ installed
- [ ] Sufficient disk space for temp PDFs
- [ ] Sufficient memory (min 512MB recommended)
- [ ] Network/firewall rules configured
- [ ] Domain/DNS configured (if applicable)
- [ ] SSL certificate installed

## 🐳 Docker Deployment

### 1. Create Dockerfile
```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY .env .env

# Create temp directory
RUN mkdir -p temp_pdfs

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Create docker-compose.yml
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - LOG_LEVEL=INFO
    volumes:
      - ./temp_pdfs:/app/temp_pdfs
    restart: unless-stopped
```

### 3. Build and Run
```bash
docker-compose up -d
```

## ☁️ Cloud Platform Deployment

### AWS Elastic Beanstalk
```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.10 pdf-api

# Create environment
eb create pdf-api-prod

# Deploy
eb deploy
```

### Heroku
```bash
# Create Procfile
echo "web: uvicorn app.main:app --host 0.0.0.0 --port \$PORT" > Procfile

# Deploy
heroku create pdf-api
git push heroku main
```

### Google Cloud Run
```bash
# Build container
gcloud builds submit --tag gcr.io/PROJECT-ID/pdf-api

# Deploy
gcloud run deploy pdf-api \
  --image gcr.io/PROJECT-ID/pdf-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Azure App Service
```bash
# Deploy
az webapp up --name pdf-api --runtime "PYTHON:3.10"
```

## 🔧 Production Server Setup (Ubuntu)

### 1. Install Dependencies
```bash
sudo apt update
sudo apt install python3.10 python3.10-venv nginx
```

### 2. Setup Application
```bash
# Create user
sudo useradd -m -s /bin/bash pdfapi

# Clone repository
cd /home/pdfapi
git clone <repo-url> app
cd app

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create Systemd Service
```bash
sudo nano /etc/systemd/system/pdfapi.service
```

```ini
[Unit]
Description=PDF to JSON API
After=network.target

[Service]
Type=notify
User=pdfapi
WorkingDirectory=/home/pdfapi/app
Environment="PATH=/home/pdfapi/app/venv/bin"
ExecStart=/home/pdfapi/app/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable pdfapi
sudo systemctl start pdfapi
```

### 4. Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/pdfapi
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for large files
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        
        # Increase body size for file uploads
        client_max_body_size 10M;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/pdfapi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 5. Setup SSL (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## 📊 Monitoring Setup

### Health Check Monitoring
```bash
# Add to cron (check every 5 minutes)
*/5 * * * * curl -f http://localhost:8000/health || echo "API Down!" | mail -s "Alert" admin@example.com
```

### Log Monitoring
```bash
# View logs
sudo journalctl -u pdfapi -f

# Or if using Docker
docker logs -f <container-id>
```

### Performance Monitoring
Consider adding:
- **Prometheus** + **Grafana** for metrics
- **Sentry** for error tracking
- **New Relic** / **DataDog** for APM

## 🔄 Post-Deployment Checklist

### Immediate Verification
- [ ] Health check endpoint works
- [ ] Can upload a test PDF
- [ ] Full text extraction works
- [ ] Structured extraction works
- [ ] Error handling works correctly
- [ ] HTTPS works (if configured)
- [ ] CORS settings correct

### Testing
```bash
# Test health
curl https://yourdomain.com/health

# Test upload
curl -X POST "https://yourdomain.com/api/v1/upload-pdf" \
  -F "file=@test.pdf"

# Check logs for errors
sudo journalctl -u pdfapi -n 50
```

### Documentation
- [ ] Update README with production URL
- [ ] Document any environment-specific settings
- [ ] Share API documentation URL with team
- [ ] Document backup/restore procedures

## 🔐 Security Hardening

### Additional Steps
```python
# In app/main.py, add rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/upload-pdf")
@limiter.limit("10/minute")
async def upload_pdf(request: Request, ...):
    ...
```

### File Cleanup Job
```python
# Create cleanup_old_pdfs.py
import os
from datetime import datetime, timedelta
from pathlib import Path

TEMP_DIR = Path("temp_pdfs")
MAX_AGE_HOURS = 24

for file in TEMP_DIR.glob("*.pdf"):
    if datetime.now() - datetime.fromtimestamp(file.stat().st_mtime) > timedelta(hours=MAX_AGE_HOURS):
        file.unlink()
        print(f"Deleted old file: {file}")
```

```bash
# Add to cron (daily cleanup)
0 2 * * * cd /home/pdfapi/app && /home/pdfapi/app/venv/bin/python cleanup_old_pdfs.py
```

## 📈 Scaling Considerations

### Horizontal Scaling
- [ ] Use load balancer (Nginx, HAProxy)
- [ ] Share temp_pdfs via NFS/S3
- [ ] Use external database for metadata
- [ ] Implement distributed caching (Redis)

### Vertical Scaling
- [ ] Increase workers: `--workers 4`
- [ ] Tune worker settings
- [ ] Monitor memory usage
- [ ] Optimize PDF processing

## 🚨 Incident Response

### If API Goes Down
1. Check service status: `sudo systemctl status pdfapi`
2. Check logs: `sudo journalctl -u pdfapi -n 100`
3. Check disk space: `df -h`
4. Check memory: `free -m`
5. Restart service: `sudo systemctl restart pdfapi`

### Common Issues
- **Out of disk space**: Clear old PDFs from temp_pdfs/
- **Out of memory**: Reduce workers or add swap
- **High CPU**: Check for runaway processes
- **Slow responses**: Check PDF sizes and processing time

## ✅ Final Checks

- [ ] Backups configured
- [ ] Monitoring alerts setup
- [ ] Documentation updated
- [ ] Team trained on deployment
- [ ] Rollback plan documented
- [ ] Support contacts updated
- [ ] Performance baseline established

---

**Ready for Production! 🎉**

Remember to:
- Monitor logs for the first 24 hours
- Start with low traffic
- Have rollback plan ready
- Keep documentation updated
