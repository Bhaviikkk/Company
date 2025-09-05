import hashlib
import io
from typing import Tuple, Optional
from pdfminer.high_level import extract_text
from pypdf import PdfReader
import logging

logger = logging.getLogger(__name__)

class DocumentParser:
    """PDF document parser using pdfminer.six and pypdf"""
    
    def extract_text_from_pdf(self, pdf_content: bytes) -> Tuple[str, str]:
        """
        Extract text from PDF content.
        Returns: (extracted_text, content_hash)
        """
        try:
            # Try pdfminer.six first (better for complex PDFs)
            text = extract_text(io.BytesIO(pdf_content))
            
            if not text.strip():
                # Fallback to pypdf
                logger.info("pdfminer failed, trying pypdf")
                reader = PdfReader(io.BytesIO(pdf_content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            
            # Normalize text
            normalized_text = self._normalize_text(text)
            
            # Generate content hash
            content_hash = hashlib.sha256(normalized_text.encode()).hexdigest()
            
            return normalized_text, content_hash
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistency"""
        # Remove extra whitespaces, normalize line breaks
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)

# Global parser instance
document_parser = DocumentParser()