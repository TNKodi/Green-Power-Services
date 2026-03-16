"""
PDF reading service using pdfplumber
Handles PDF text extraction operations
"""
import pdfplumber
from pathlib import Path
from typing import Optional

from ..utils.exceptions import PDFParsingError, FileNotFoundError as PDFFileNotFoundError
from ..utils.logger import logger


class PDFReader:
    """Service for reading and extracting text from PDF files"""
    
    def __init__(self):
        """Initialize PDF reader"""
        self.logger = logger
    
    def extract_full_text(self, pdf_path: str) -> str:
        """
        Extract complete text from all pages of a PDF file
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Complete text content as a single string
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            PDFParsingError: If PDF cannot be parsed
        """
        pdf_file = Path(pdf_path)
        
        # Validate file exists
        if not pdf_file.exists():
            self.logger.error(f"PDF file not found: {pdf_path}")
            raise PDFFileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            text_content = ""
            
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                self.logger.info(f"Processing PDF with {total_pages} pages")
                
                # Extract text from each page
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        text_content += text + "\n"
                        self.logger.debug(f"Extracted text from page {page_num}/{total_pages}")
                    else:
                        self.logger.warning(f"No text found on page {page_num}")
            
            # Verify we extracted some content
            if not text_content.strip():
                raise PDFParsingError("PDF appears to be empty or contains only images")
            
            self.logger.info(f"Successfully extracted {len(text_content)} characters from PDF")
            return text_content
            
        except pdfplumber.exceptions.PDFSyntaxError as e:
            self.logger.error(f"PDF syntax error: {str(e)}")
            raise PDFParsingError(f"Invalid PDF format: {str(e)}")
        
        except Exception as e:
            self.logger.error(f"Failed to read PDF: {str(e)}")
            raise PDFParsingError(f"Failed to parse PDF: {str(e)}")
    
    def get_page_count(self, pdf_path: str) -> int:
        """
        Get the number of pages in a PDF
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Number of pages
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                return len(pdf.pages)
        except Exception as e:
            self.logger.error(f"Failed to get page count: {str(e)}")
            raise PDFParsingError(f"Failed to read PDF metadata: {str(e)}")
    
    def extract_text_by_page(self, pdf_path: str, page_number: int) -> Optional[str]:
        """
        Extract text from a specific page
        
        Args:
            pdf_path: Path to the PDF file
            page_number: Page number (1-indexed)
            
        Returns:
            Text content from the specified page or None
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if 1 <= page_number <= len(pdf.pages):
                    page = pdf.pages[page_number - 1]  # Convert to 0-indexed
                    return page.extract_text()
                else:
                    self.logger.warning(f"Page {page_number} out of range")
                    return None
        except Exception as e:
            self.logger.error(f"Failed to extract page {page_number}: {str(e)}")
            raise PDFParsingError(f"Failed to extract page: {str(e)}")


# Create singleton instance
pdf_reader = PDFReader()
