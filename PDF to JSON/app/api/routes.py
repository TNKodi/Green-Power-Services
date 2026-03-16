"""
FastAPI route handlers for PDF processing endpoints
"""
import os
import uuid
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from ..models.schemas import (
    UploadResponse,
    FullTextResponse,
    ExtractResponse,
    HealthResponse,
    ErrorResponse
)
from ..services.pdf_reader import pdf_reader
from ..services.extractor import data_extractor
from ..services.thingnode_client import thingnode_client
from ..utils.exceptions import (
    InvalidFileTypeError,
    FileSizeExceededError,
    FileNotFoundError,
    PDFParsingError,
    ExtractionError,
    NoFileProvidedError
)
from ..utils.logger import (
    logger,
    log_request,
    log_pdf_upload,
    log_extraction_start,
    log_extraction_complete
)

# Create router
router = APIRouter(prefix="/api/v1", tags=["PDF Processing"])

# Configuration
TEMP_PDF_DIR = Path("temp_pdfs")
TEMP_PDF_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

# Storage for tracking uploaded files (In production, use Redis/Database)
uploaded_files = {}


async def _validate_and_save_temp_pdf(file: Optional[UploadFile], request_id: str) -> Path:
    """Validate upload and persist to temp directory"""
    if file is None:
        raise HTTPException(
            status_code=400,
            detail={"error": True, "message": "No file provided. Please upload a PDF file.", "status_code": 400}
        )

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail={"error": True, "message": "Invalid file type. Only PDF files are allowed.", "status_code": 400}
        )

    content = await file.read()
    file_size = len(content)

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail={"error": True, "message": "Empty file provided.", "status_code": 400}
        )

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail={"error": True, "message": "File size exceeds the maximum limit of 10MB.", "status_code": 400}
        )

    file_path = TEMP_PDF_DIR / f"{request_id}.pdf"
    with open(file_path, "wb") as f:
        f.write(content)

    log_pdf_upload(request_id, file.filename, file_size)
    logger.info(f"[{request_id}] PDF saved to {file_path}")

    return file_path


@router.post(
    "/upload-pdf",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF file",
    description="Upload a PDF file for processing. Returns a unique request_id for subsequent operations."
)
async def upload_pdf(file: Optional[UploadFile] = File(None)):
    """
    Upload a PDF file for processing
    
    - **file**: PDF file to upload (max 10MB)
    
    Returns a unique request_id to track this PDF
    """
    request_id = str(uuid.uuid4())
    log_request(request_id, "/api/v1/upload-pdf", "POST")
    
    try:
        # Validate file is provided
        if file is None:
            raise NoFileProvidedError()
        
        # Validate file extension
        if not file.filename.lower().endswith('.pdf'):
            raise InvalidFileTypeError()
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise FileSizeExceededError()
        
        # Generate unique filename
        safe_filename = f"{request_id}.pdf"
        file_path = TEMP_PDF_DIR / safe_filename
        
        # Save file to temp directory
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Store metadata
        uploaded_files[request_id] = {
            "filename": file.filename,
            "file_path": str(file_path),
            "upload_time": datetime.utcnow().isoformat(),
            "file_size": file_size
        }
        
        log_pdf_upload(request_id, file.filename, file_size)
        logger.info(f"[{request_id}] PDF saved to {file_path}")
        
        return UploadResponse(
            request_id=request_id,
            message="PDF uploaded successfully"
        )
    
    except (InvalidFileTypeError, FileSizeExceededError, NoFileProvidedError) as e:
        logger.error(f"[{request_id}] Upload validation failed: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": True, "message": e.message, "code": e.status_code}
        )
    
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error during upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "message": f"Upload failed: {str(e)}", "code": 500}
        )


@router.get(
    "/pdf/{request_id}/fulltext",
    response_model=FullTextResponse,
    summary="Extract full text from PDF",
    description="Extract all text content from the uploaded PDF as a single string."
)
async def get_full_text(request_id: str):
    """
    Extract complete text from uploaded PDF
    
    - **request_id**: Unique identifier from upload response
    
    Returns all text from the PDF merged into one string
    """
    log_request(request_id, f"/api/v1/pdf/{request_id}/fulltext", "GET")
    
    try:
        # Validate request_id exists
        if request_id not in uploaded_files:
            raise FileNotFoundError(f"No PDF found for request_id: {request_id}")
        
        # Get file path
        file_info = uploaded_files[request_id]
        file_path = file_info["file_path"]
        
        # Extract text
        logger.info(f"[{request_id}] Extracting full text from PDF")
        full_text = pdf_reader.extract_full_text(file_path)
        
        logger.info(f"[{request_id}] Full text extraction complete")
        
        return FullTextResponse(
            request_id=request_id,
            full_text=full_text
        )
    
    except (FileNotFoundError, PDFParsingError) as e:
        logger.error(f"[{request_id}] Error: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": True, "message": e.message, "code": e.status_code}
        )
    
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "message": f"Text extraction failed: {str(e)}", "code": 500}
        )


@router.get(
    "/pdf/{request_id}/extract",
    response_model=ExtractResponse,
    summary="Extract structured data from PDF",
    description="Extract predefined attributes and structured data from the PDF using regex patterns."
)
async def extract_data(request_id: str):
    """
    Extract structured data from uploaded PDF
    
    - **request_id**: Unique identifier from upload response
    
    Returns structured JSON with extracted fields like:
    - Project details
    - System specifications
    - Module information
    - Inverter details
    - Loss calculations
    """
    log_request(request_id, f"/api/v1/pdf/{request_id}/extract", "GET")
    
    try:
        # Validate request_id exists
        if request_id not in uploaded_files:
            raise FileNotFoundError(f"No PDF found for request_id: {request_id}")
        
        # Get file path
        file_info = uploaded_files[request_id]
        file_path = file_info["file_path"]
        
        log_extraction_start(request_id)
        
        # First extract full text
        full_text = pdf_reader.extract_full_text(file_path)
        
        # Then extract structured data
        raw_data = data_extractor.extract_structured_data(full_text)
        
        # Transform to formatted attributes
        extracted_data = data_extractor.transform_to_attributes(raw_data)
        
        log_extraction_complete(request_id, len(extracted_data))
        
        return ExtractResponse(
            request_id=request_id,
            data=extracted_data
        )
    
    except (FileNotFoundError, PDFParsingError, ExtractionError) as e:
        logger.error(f"[{request_id}] Error: {str(e)}")
        raise HTTPException(
            status_code=e.status_code,
            detail={"error": True, "message": e.message, "code": e.status_code}
        )
    
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "message": f"Data extraction failed: {str(e)}", "code": 500}
        )


@router.post(
    "/pdf/extract-direct",
    summary="Upload and extract structured data in one request",
    description="Uploads a PDF, extracts structured data immediately, and deletes the temp file. No request_id required."
)
async def extract_direct(file: Optional[UploadFile] = File(None)):
    """One-step PDF to structured JSON extraction (no request_id needed)"""
    request_id = str(uuid.uuid4())
    log_request(request_id, "/api/v1/pdf/extract-direct", "POST")

    file_path: Path | None = None

    try:
        # Validate and persist PDF temporarily
        file_path = await _validate_and_save_temp_pdf(file, request_id)

        log_extraction_start(request_id)

        # Extract full text then structured data
        full_text = pdf_reader.extract_full_text(str(file_path))
        raw_data = data_extractor.extract_structured_data(full_text)
        
        # Transform to formatted attributes
        extracted_data = data_extractor.transform_to_attributes(raw_data)

        log_extraction_complete(request_id, len(extracted_data))

        return {
            "success": True,
            "data": extracted_data
        }

    except HTTPException:
        # Already formatted for client
        raise

    except (PDFParsingError, ExtractionError) as e:
        logger.error(f"[{request_id}] Direct extract error: {str(e)}")
        raise HTTPException(
            status_code=getattr(e, "status_code", 400),
            detail={"error": True, "message": e.message, "status_code": getattr(e, "status_code", 400)}
        )

    except Exception as e:
        logger.error(f"[{request_id}] Unexpected direct extract error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "message": f"Direct extraction failed: {str(e)}", "status_code": 500}
        )

    finally:
        if file_path and file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"[{request_id}] Temp PDF deleted: {file_path}")
            except Exception:
                logger.warning(f"[{request_id}] Failed to delete temp PDF: {file_path}")


@router.post(
    "/pdf/fulltext-direct",
    summary="Upload and extract full text in one request",
    description="Uploads a PDF, extracts full text immediately, and deletes the temp file. No request_id required."
)
async def fulltext_direct(file: Optional[UploadFile] = File(None)):
    """One-step PDF to full text extraction (no request_id needed)"""
    request_id = str(uuid.uuid4())
    log_request(request_id, "/api/v1/pdf/fulltext-direct", "POST")

    file_path: Path | None = None

    try:
        # Validate and persist PDF temporarily
        file_path = await _validate_and_save_temp_pdf(file, request_id)

        # Extract full text
        full_text = pdf_reader.extract_full_text(str(file_path))

        return {
            "success": True,
            "full_text": full_text
        }

    except HTTPException:
        raise

    except PDFParsingError as e:
        logger.error(f"[{request_id}] Direct fulltext parse error: {str(e)}")
        raise HTTPException(
            status_code=getattr(e, "status_code", 400),
            detail={"error": True, "message": e.message, "status_code": getattr(e, "status_code", 400)}
        )

    except Exception as e:
        logger.error(f"[{request_id}] Unexpected direct fulltext error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "message": f"Direct full text extraction failed: {str(e)}", "status_code": 500}
        )

    finally:
        if file_path and file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"[{request_id}] Temp PDF deleted: {file_path}")
            except Exception:
                logger.warning(f"[{request_id}] Failed to delete temp PDF: {file_path}")


@router.post(
    "/pdf/extract-direct-to-asset",
    summary="Upload PDF, extract attributes, and write to ThingNode asset",
    description="Accepts PDF + asset_id, extracts attributes, writes to ThingNode asset, and deletes the temp PDF."
)
async def extract_direct_to_asset(
    file: Optional[UploadFile] = File(None),
    asset_id: str = Form(...)
):
    """One-step PDF extraction and ThingNode asset attribute write"""
    request_id = str(uuid.uuid4())
    log_request(request_id, "/api/v1/pdf/extract-direct-to-asset", "POST")

    file_path: Path | None = None

    try:
        if not asset_id.strip():
            raise HTTPException(
                status_code=400,
                detail={"error": True, "message": "asset_id is required.", "status_code": 400}
            )

        # Validate and persist PDF temporarily
        file_path = await _validate_and_save_temp_pdf(file, request_id)

        log_extraction_start(request_id)

        # Extract and transform
        full_text = pdf_reader.extract_full_text(str(file_path))
        raw_data = data_extractor.extract_structured_data(full_text)
        extracted_data = data_extractor.transform_to_attributes(raw_data)

        # Write to ThingNode asset
        write_result = await run_in_threadpool(
            thingnode_client.write_asset_attributes,
            asset_id.strip(),
            extracted_data,
        )

        log_extraction_complete(request_id, len(extracted_data))

        return {
            "success": True,
            "asset_id": asset_id.strip(),
            "thingnode_write": write_result,
            "data": extracted_data,
        }

    except HTTPException:
        raise

    except (PDFParsingError, ExtractionError) as e:
        logger.error(f"[{request_id}] Extract-to-asset error: {str(e)}")
        raise HTTPException(
            status_code=getattr(e, "status_code", 400),
            detail={"error": True, "message": e.message, "status_code": getattr(e, "status_code", 400)}
        )

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else 502
        err_body = e.response.text if e.response is not None else str(e)
        logger.error(f"[{request_id}] ThingNode HTTP error: {err_body}")
        raise HTTPException(
            status_code=status_code,
            detail={"error": True, "message": f"ThingNode write failed: {err_body}", "status_code": status_code}
        )

    except ValueError as e:
        logger.error(f"[{request_id}] ThingNode config/input error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail={"error": True, "message": str(e), "status_code": 400}
        )

    except Exception as e:
        logger.error(f"[{request_id}] Unexpected extract-to-asset error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "message": f"Extract and write failed: {str(e)}", "status_code": 500}
        )

    finally:
        if file_path and file_path.exists():
            try:
                os.remove(file_path)
                logger.info(f"[{request_id}] Temp PDF deleted: {file_path}")
            except Exception:
                logger.warning(f"[{request_id}] Failed to delete temp PDF: {file_path}")


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check endpoint",
    description="Check if the service is running and healthy."
)
async def health_check():
    """
    Health check endpoint for monitoring
    
    Returns service status and current timestamp
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.utcnow()
    )


# Additional utility endpoint to list uploaded PDFs (useful for debugging)
@router.get(
    "/pdfs",
    tags=["Admin"],
    summary="List all uploaded PDFs",
    description="Returns a list of all uploaded PDFs with metadata (for debugging)"
)
async def list_uploaded_pdfs():
    """List all uploaded PDFs with metadata"""
    return {
        "count": len(uploaded_files),
        "files": uploaded_files
    }


# Endpoint to delete a PDF
@router.delete(
    "/pdf/{request_id}",
    tags=["Admin"],
    summary="Delete uploaded PDF",
    description="Remove a PDF file and its metadata from the system"
)
async def delete_pdf(request_id: str):
    """
    Delete an uploaded PDF file
    
    - **request_id**: Unique identifier of the PDF to delete
    """
    if request_id not in uploaded_files:
        raise HTTPException(
            status_code=404,
            detail={"error": True, "message": f"No PDF found for request_id: {request_id}", "code": 404}
        )
    
    try:
        # Delete file from disk
        file_path = uploaded_files[request_id]["file_path"]
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Remove from tracking
        del uploaded_files[request_id]
        
        logger.info(f"[{request_id}] PDF deleted successfully")
        
        return {
            "message": f"PDF with request_id {request_id} deleted successfully"
        }
    
    except Exception as e:
        logger.error(f"[{request_id}] Error deleting PDF: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": True, "message": f"Failed to delete PDF: {str(e)}", "code": 500}
        )
