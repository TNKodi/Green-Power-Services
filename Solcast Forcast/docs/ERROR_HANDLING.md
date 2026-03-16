# Error Handling Documentation

## Overview

The Power Forecast API implements comprehensive error handling to ensure robust, production-ready operation. This document details all error scenarios, HTTP status codes, and error response formats.

---

## Error Response Format

All errors return structured JSON responses with the following format:

```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error description",
  "asset_id": "optional_asset_identifier",
  "additional_fields": "context-specific data"
}
```

---

## HTTP Status Codes

### 200 OK
- Successful request completion
- Used for: health checks, successful job creation, valid status queries

### 400 Bad Request
- Invalid request data
- Missing required fields
- Invalid field values

**Example Scenarios:**
- Missing `asset_id` in request body
- Empty or whitespace-only `asset_id`
- Invalid request format

**Error Response:**
```json
{
  "detail": {
    "error": "ASSET_ID_REQUIRED",
    "message": "asset_id must be provided in the request body"
  }
}
```

### 404 Not Found
- Resource does not exist
- Asset not found in ThingsBoard
- Job ID not found

**Example Scenarios:**
- Asset ID doesn't exist in ThingsBoard
- Querying status of non-existent job

**Error Response (Asset Not Found):**
```json
{
  "detail": {
    "error": "ASSET_NOT_FOUND",
    "message": "The provided asset_id does not exist in ThingsBoard",
    "asset_id": "FAKE_ASSET_123"
  }
}
```

**Error Response (Job Not Found):**
```json
{
  "detail": "Job not found"
}
```

### 422 Unprocessable Entity
- Asset exists but missing required attributes
- Data validation failed

**Example Scenario:**
- Asset found in ThingsBoard but lacks required attributes for power calculation

**Error Response:**
```json
{
  "detail": {
    "error": "ASSET_MISSING_ATTRIBUTES",
    "message": "Asset exists but required attributes are missing",
    "asset_id": "GGC_S_0038",
    "missing_attributes": ["latitude", "longitude", "capacity_kw"]
  }
}
```

### 500 Internal Server Error
- Unexpected server errors
- ThingsBoard connection failures
- Calculation errors

**Example Scenarios:**
- ThingsBoard API timeout
- Power calculation crashes
- Database/storage errors

**Error Response:**
```json
{
  "detail": "Failed to process new asset: Connection timeout"
}
```

---

## Required Attributes

The following attributes must be present on an asset for successful power prediction:

| Attribute | Type | Description |
|-----------|------|-------------|
| `latitude` | float | Installation latitude (decimal degrees) |
| `longitude` | float | Installation longitude (decimal degrees) |
| `capacity_kw` | float | Solar panel capacity in kilowatts |
| `tilt` | float | Panel tilt angle (degrees from horizontal) |
| `azimuth` | float | Panel azimuth angle (degrees from north) |
| `surface_type` | string | Surface type (e.g., 'urban', 'grass') |
| `losses` | float | System losses (0-1 range, e.g., 0.14 = 14%) |

Missing any of these will result in HTTP 422 error.

---

## API Endpoint Error Handling

### 1. GET `/health`

**Possible Responses:**
- ✅ **200 OK**: Service is healthy

**Error Scenarios:** None (always returns 200)

---

### 2. POST `/api/v1/forecast/start`

**Request Body:**
```json
{
  "asset_id": "GGC_S_0038"
}
```

**Possible Responses:**

✅ **200 OK** - Job created successfully
```json
{
  "job_id": "uuid-here",
  "status": "running",
  "message": "Forecast job started successfully"
}
```

❌ **400 Bad Request** - Missing or invalid asset_id
```json
{
  "detail": {
    "error": "ASSET_ID_REQUIRED",
    "message": "asset_id must be provided in the request body"
  }
}
```

❌ **404 Not Found** - Asset doesn't exist
```json
{
  "detail": {
    "error": "ASSET_NOT_FOUND",
    "message": "The provided asset_id does not exist in ThingsBoard",
    "asset_id": "INVALID_ID"
  }
}
```

❌ **500 Internal Server Error** - Server error
```json
{
  "detail": "Failed to start forecast: <error details>"
}
```

---

### 3. GET `/api/v1/forecast/status/{job_id}`

**Path Parameter:** `job_id` (string, UUID format)

**Possible Responses:**

✅ **200 OK** - Job status retrieved
```json
{
  "job_id": "uuid-here",
  "status": "running",
  "total_assets": 10,
  "assets_processed": 5,
  "successful_assets": 3,
  "failed_assets": 1,
  "skipped_assets": 1,
  "current_step": "processing_assets",
  "message": "Processed 5/10 (success: 3, failed: 1, skipped: 1)",
  "errors": [
    {
      "asset_id": "ASSET_123",
      "error": "missing_required_attributes",
      "details": "Missing: latitude, longitude"
    }
  ],
  "created_at": "2026-01-21T11:30:00Z",
  "updated_at": "2026-01-21T11:32:15Z"
}
```

❌ **404 Not Found** - Job doesn't exist
```json
{
  "detail": "Job not found"
}
```

---

### 4. POST `/api/v1/forecast/new-asset`

**Request Body:**
```json
{
  "asset_id": "NEW_ASSET_001"
}
```

**Possible Responses:**

✅ **200 OK** - Asset processed successfully
```json
{
  "status": "telemetry_written",
  "asset_id": "NEW_ASSET_001",
  "message": "Successfully processed new asset"
}
```

❌ **400 Bad Request** - Missing or invalid asset_id
```json
{
  "detail": {
    "error": "ASSET_ID_REQUIRED",
    "message": "asset_id must be provided in the request body"
  }
}
```

❌ **404 Not Found** - Asset doesn't exist
```json
{
  "detail": {
    "error": "ASSET_NOT_FOUND",
    "message": "The provided asset_id does not exist in ThingsBoard",
    "asset_id": "NEW_ASSET_001"
  }
}
```

❌ **422 Unprocessable Entity** - Missing required attributes
```json
{
  "detail": {
    "error": "ASSET_MISSING_ATTRIBUTES",
    "message": "Asset exists but required attributes are missing",
    "asset_id": "NEW_ASSET_001",
    "missing_attributes": ["latitude", "longitude", "capacity_kw"]
  }
}
```

❌ **500 Internal Server Error** - Processing error
```json
{
  "detail": "Failed to process new asset: <error details>"
}
```

---

## Job Status Fields

### Error Tracking Fields

When querying job status via `/api/v1/forecast/status/{job_id}`, the following error tracking fields are included:

| Field | Type | Description |
|-------|------|-------------|
| `successful_assets` | int | Count of assets processed successfully |
| `failed_assets` | int | Count of assets that failed processing |
| `skipped_assets` | int | Count of assets skipped (e.g., missing attributes) |
| `current_step` | string | Current processing step |
| `errors` | array | List of error objects with asset_id, error code, and details |

**Current Step Values:**
- `initializing` - Job setup
- `fetching_assets` - Retrieving assets from ThingsBoard
- `processing_assets` - Running power predictions
- `completed` - Job finished
- `failed` - Job encountered fatal error

**Error Object Format:**
```json
{
  "asset_id": "ASSET_123",
  "error": "missing_required_attributes",
  "details": "Missing: latitude, longitude"
}
```

---

## Partial Failure Handling

The API handles partial failures gracefully:

1. **Multi-Asset Jobs**: Continue processing remaining assets even if some fail
2. **Error Logging**: Each failure is logged with details
3. **Status Tracking**: Failed/skipped counts tracked separately
4. **Final Status**: Job completes successfully even if some assets fail

**Example Scenario:**
- Start forecast with 100 assets
- 80 process successfully
- 15 fail due to calculation errors
- 5 skipped due to missing attributes
- **Result**: Job status = "completed" with detailed breakdown

---

## Testing Error Handling

Use the provided test script to verify error handling:

```bash
python test_error_handling.py
```

**Test Coverage:**
1. ✅ Health check endpoint
2. ✅ Missing asset_id validation (start endpoint)
3. ✅ Non-existent asset detection (start endpoint)
4. ✅ Missing asset_id validation (new-asset endpoint)
5. ✅ Non-existent asset detection (new-asset endpoint)
6. ✅ Missing attributes detection (new-asset endpoint)
7. ✅ Job status error tracking
8. ✅ Invalid job_id handling

---

## Logging

All errors are logged with appropriate severity levels:

### Log Levels

| Level | When Used | Example |
|-------|-----------|---------|
| `ERROR` | Critical failures, unexpected exceptions | ThingsBoard connection timeout |
| `WARNING` | Expected failures, missing data | Asset missing attributes |
| `INFO` | Normal operations, progress updates | Asset processed successfully |
| `DEBUG` | Detailed diagnostic info | API request/response details |

### Log Format

```
2026-01-21 11:45:34 - thingsboard-forecast - ERROR - Failed to process asset ASSET_123: Missing latitude
```

**Log Fields:**
- Timestamp (ISO 8601)
- Logger name (thingsboard-forecast)
- Level (ERROR/WARNING/INFO/DEBUG)
- Message with context

---

## Best Practices

### 1. Always Validate Asset IDs

Before processing, check:
- Asset ID is not empty/null
- Asset exists in ThingsBoard
- Asset has required attributes

### 2. Handle Partial Failures

In multi-asset operations:
- Continue processing on individual failures
- Track successes, failures, and skips separately
- Return detailed error breakdown

### 3. Return Structured Errors

Always return:
- Error code (machine-readable)
- Error message (human-readable)
- Context (asset_id, missing_attributes, etc.)

### 4. Log Everything

Log:
- All errors with stack traces
- All warnings with context
- Progress updates for long operations

### 5. Don't Crash the Service

Handle all exceptions:
- Catch unexpected errors
- Return HTTP 500 for server errors
- Keep service running

---

## Error Code Reference

| Error Code | HTTP Status | Description | Resolution |
|------------|-------------|-------------|------------|
| `ASSET_ID_REQUIRED` | 400 | Missing or empty asset_id | Provide valid asset_id in request |
| `ASSET_NOT_FOUND` | 404 | Asset doesn't exist in ThingsBoard | Verify asset_id is correct |
| `ASSET_MISSING_ATTRIBUTES` | 422 | Asset exists but missing required attributes | Add missing attributes to asset in ThingsBoard |
| `Job not found` | 404 | Job ID doesn't exist | Verify job_id from start_forecast response |

---

## Example Client Code

### Python (with error handling)

```python
import httpx

async def process_asset_with_error_handling(asset_id: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://localhost:8000/api/v1/forecast/new-asset",
                json={"asset_id": asset_id}
            )
            
            if response.status_code == 200:
                print(f"✅ Success: {response.json()}")
            elif response.status_code == 400:
                print(f"❌ Invalid request: {response.json()}")
            elif response.status_code == 404:
                print(f"❌ Asset not found: {response.json()}")
            elif response.status_code == 422:
                error = response.json()
                print(f"❌ Missing attributes: {error['detail']['missing_attributes']}")
            else:
                print(f"❌ Error: {response.json()}")
                
        except httpx.TimeoutException:
            print("❌ Request timeout")
        except httpx.RequestError as e:
            print(f"❌ Connection error: {e}")
```

### JavaScript/TypeScript

```typescript
async function processAsset(assetId: string) {
  try {
    const response = await fetch('http://localhost:8000/api/v1/forecast/new-asset', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ asset_id: assetId })
    });
    
    const data = await response.json();
    
    if (response.status === 200) {
      console.log('✅ Success:', data);
    } else if (response.status === 400) {
      console.error('❌ Invalid request:', data.detail);
    } else if (response.status === 404) {
      console.error('❌ Asset not found:', data.detail);
    } else if (response.status === 422) {
      console.error('❌ Missing attributes:', data.detail.missing_attributes);
    } else {
      console.error('❌ Error:', data);
    }
  } catch (error) {
    console.error('❌ Network error:', error);
  }
}
```

---

## Monitoring & Alerts

### Recommended Metrics

Track these metrics for production monitoring:

1. **Error Rate**: Failed requests / Total requests
2. **Error Types**: Count by HTTP status code (400, 404, 422, 500)
3. **Asset Failure Rate**: Failed assets / Total assets
4. **Response Times**: P50, P95, P99 latencies
5. **ThingsBoard Connection Errors**: Count of connection timeouts/failures

### Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Error Rate | > 5% | > 10% |
| 500 Errors | > 1/min | > 5/min |
| Asset Failure Rate | > 10% | > 25% |
| Response Time P95 | > 5s | > 10s |
| TB Connection Errors | > 2/hour | > 5/hour |

---

## Troubleshooting Guide

### Issue: Getting HTTP 404 for valid asset

**Possible Causes:**
1. Asset ID typo or incorrect format
2. Asset not created in ThingsBoard yet
3. Asset in different ThingsBoard instance

**Resolution:**
1. Verify asset ID spelling
2. Check asset exists: `GET https://cloud.thingsnode.cc/api/asset/{asset_id}`
3. Verify ThingsBoard instance URL in `.env`

---

### Issue: HTTP 422 - Missing attributes

**Possible Causes:**
1. Asset created without required attributes
2. Attributes have incorrect key names
3. Attributes not saved to server

**Resolution:**
1. Check required attributes list (see above)
2. Verify attribute names match exactly (case-sensitive)
3. Re-save attributes in ThingsBoard UI

---

### Issue: HTTP 500 errors

**Possible Causes:**
1. ThingsBoard connection timeout
2. Invalid credentials in `.env`
3. Power calculation crash
4. Server resource exhaustion

**Resolution:**
1. Check ThingsBoard is accessible
2. Verify `TB_USERNAME` and `TB_PASSWORD` in `.env`
3. Check logs for stack traces
4. Monitor server CPU/memory

---

## Support

For issues or questions:

1. Check this documentation first
2. Review API logs for error details
3. Run `test_error_handling.py` to verify setup
4. Check ThingsBoard connectivity
5. Verify all required attributes are present

**Log Location:** Console output when running `uvicorn` or in application logs

**API Documentation:** http://localhost:8000/docs (when running)
