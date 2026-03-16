"""
Custom exceptions for the PDF processing API
"""


class PDFProcessingException(Exception):
    """Base exception for PDF processing errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidFileTypeError(PDFProcessingException):
    """Raised when uploaded file is not a PDF"""
    def __init__(self, message: str = "Invalid file type. Only PDF files are allowed."):
        super().__init__(message, status_code=400)


class FileSizeExceededError(PDFProcessingException):
    """Raised when uploaded file exceeds size limit"""
    def __init__(self, message: str = "File size exceeds the maximum limit of 10MB."):
        super().__init__(message, status_code=400)


class FileNotFoundError(PDFProcessingException):
    """Raised when requested PDF is not found"""
    def __init__(self, message: str = "PDF file not found. Invalid request_id or file has been removed."):
        super().__init__(message, status_code=404)


class PDFParsingError(PDFProcessingException):
    """Raised when PDF parsing fails"""
    def __init__(self, message: str = "Failed to parse PDF file. The file may be corrupted or password-protected."):
        super().__init__(message, status_code=422)


class ExtractionError(PDFProcessingException):
    """Raised when data extraction fails"""
    def __init__(self, message: str = "Failed to extract structured data from PDF."):
        super().__init__(message, status_code=500)


class NoFileProvidedError(PDFProcessingException):
    """Raised when no file is provided in the upload request"""
    def __init__(self, message: str = "No file provided. Please upload a PDF file."):
        super().__init__(message, status_code=400)
