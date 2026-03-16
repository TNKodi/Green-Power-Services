# API Testing with cURL

This file contains example cURL commands to test all API endpoints.

## Prerequisites

- API server running on http://localhost:8000
- A sample PDF file for testing

## 1. Health Check

Check if the API is running:

```bash
curl -X GET "http://localhost:8000/health" \
  -H "accept: application/json"
```

Expected Response:
```json
{
  "status": "ok",
  "timestamp": "2026-01-21T10:30:45.123456"
}
```

## 2. Upload PDF

Upload a PDF file for processing (replace `path/to/file.pdf` with actual path):

### Windows (PowerShell)
```powershell
curl -X POST "http://localhost:8000/api/v1/upload-pdf" `
  -H "accept: application/json" `
  -F "file=@path/to/file.pdf"
```

### Linux/Mac
```bash
curl -X POST "http://localhost:8000/api/v1/upload-pdf" \
  -H "accept: application/json" \
  -F "file=@path/to/file.pdf"
```

Expected Response:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "PDF uploaded successfully"
}
```

**Save the `request_id` for subsequent requests!**

## 3. Extract Full Text

Get complete text from the PDF (replace `{request_id}` with actual ID):

```bash
curl -X GET "http://localhost:8000/api/v1/pdf/{request_id}/fulltext" \
  -H "accept: application/json"
```

Example with actual ID:
```bash
curl -X GET "http://localhost:8000/api/v1/pdf/550e8400-e29b-41d4-a716-446655440000/fulltext" \
  -H "accept: application/json"
```

Expected Response:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "full_text": "Complete text content from all pages of the PDF..."
}
```

## 4. Extract Structured Data

Get structured data from the PDF (replace `{request_id}` with actual ID):

```bash
curl -X GET "http://localhost:8000/api/v1/pdf/{request_id}/extract" \
  -H "accept: application/json"
```

Example with actual ID:
```bash
curl -X GET "http://localhost:8000/api/v1/pdf/550e8400-e29b-41d4-a716-446655440000/extract" \
  -H "accept: application/json"
```

Expected Response:
```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "Project": "GGC_S_0038 - Ranabima Royal College",
    "System power": 50.4,
    "Longitude": 80.123,
    "Latitude": 6.456,
    "Altitude": 120.5,
    "Albedo": 0.2,
    "Nb. of modules": 120,
    "pv_module_manufacturer": "Canadian Solar",
    "pv_module_model": "CS3W-420P",
    "inverter_manufacturer": "Huawei",
    "inverter_model": "SUN2000-50KTL-M3",
    "Inverter Units": 1,
    "Inverter Power": 50.0,
    "soiling_loss_pct": "2.5",
    "lid_loss_pct": "1.0",
    "dc_wiring_loss_pct": "1.5",
    "ac_wiring_loss_pct": "0.5"
  }
}
```

## 5. List Uploaded PDFs (Admin)

View all uploaded PDFs:

```bash
curl -X GET "http://localhost:8000/api/v1/pdfs" \
  -H "accept: application/json"
```

## 6. Delete PDF (Admin)

Delete a specific PDF:

```bash
curl -X DELETE "http://localhost:8000/api/v1/pdf/{request_id}" \
  -H "accept: application/json"
```

## Complete Workflow Example

Here's a complete workflow from upload to extraction:

```bash
# 1. Upload PDF
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/upload-pdf" \
  -F "file=@sample.pdf")

# 2. Extract request_id
REQUEST_ID=$(echo $UPLOAD_RESPONSE | grep -o '"request_id":"[^"]*"' | cut -d'"' -f4)

echo "Uploaded PDF with ID: $REQUEST_ID"

# 3. Get full text
curl -X GET "http://localhost:8000/api/v1/pdf/$REQUEST_ID/fulltext" \
  -H "accept: application/json" | jq .

# 4. Get structured data
curl -X GET "http://localhost:8000/api/v1/pdf/$REQUEST_ID/extract" \
  -H "accept: application/json" | jq .
```

## Error Scenarios

### Invalid File Type
```bash
curl -X POST "http://localhost:8000/api/v1/upload-pdf" \
  -F "file=@document.txt"
```

Response:
```json
{
  "error": true,
  "message": "Invalid file type. Only PDF files are allowed.",
  "code": 400
}
```

### File Not Found (Invalid Request ID)
```bash
curl -X GET "http://localhost:8000/api/v1/pdf/invalid-id/fulltext"
```

Response:
```json
{
  "error": true,
  "message": "No PDF found for request_id: invalid-id",
  "code": 404
}
```

### No File Provided
```bash
curl -X POST "http://localhost:8000/api/v1/upload-pdf"
```

Response:
```json
{
  "error": true,
  "message": "No file provided. Please upload a PDF file.",
  "code": 400
}
```

## Pretty Print with jq

For better readability, pipe responses through `jq`:

```bash
curl -X GET "http://localhost:8000/api/v1/pdf/{request_id}/extract" | jq .
```

## Save Response to File

Save full text to a file:

```bash
curl -X GET "http://localhost:8000/api/v1/pdf/{request_id}/fulltext" \
  -o fulltext.json
```

Save structured data to a file:

```bash
curl -X GET "http://localhost:8000/api/v1/pdf/{request_id}/extract" \
  -o extracted_data.json
```

## Verbose Mode (Debugging)

Add `-v` flag to see full request/response headers:

```bash
curl -v -X GET "http://localhost:8000/health"
```

## Timing the Request

See how long requests take:

```bash
curl -w "\nTime: %{time_total}s\n" \
  -X GET "http://localhost:8000/api/v1/pdf/{request_id}/extract"
```
