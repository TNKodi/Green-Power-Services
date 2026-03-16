"""
Logging configuration for the PDF processing API
"""
import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(name: str = "pdf_api", log_level: str = "INFO") -> logging.Logger:
    """
    Configure and return a logger instance
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    # Console handler with formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    # Format: timestamp - level - message
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


# Create default logger instance
logger = setup_logger()


def log_request(request_id: str, endpoint: str, method: str = "GET"):
    """Log incoming API request"""
    logger.info(f"[{request_id}] {method} {endpoint}")


def log_response(request_id: str, status_code: int, duration_ms: float = None):
    """Log API response"""
    duration_str = f" - {duration_ms:.2f}ms" if duration_ms else ""
    logger.info(f"[{request_id}] Response: {status_code}{duration_str}")


def log_error(request_id: str, error: Exception):
    """Log error with request context"""
    logger.error(f"[{request_id}] Error: {type(error).__name__} - {str(error)}")


def log_pdf_upload(request_id: str, filename: str, file_size: int):
    """Log PDF upload details"""
    size_mb = file_size / (1024 * 1024)
    logger.info(f"[{request_id}] Uploaded PDF: {filename} ({size_mb:.2f} MB)")


def log_extraction_start(request_id: str):
    """Log start of extraction process"""
    logger.info(f"[{request_id}] Starting data extraction...")


def log_extraction_complete(request_id: str, fields_extracted: int):
    """Log successful extraction"""
    logger.info(f"[{request_id}] Extraction complete - {fields_extracted} fields extracted")
