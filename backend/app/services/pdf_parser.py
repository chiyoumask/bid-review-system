"""
PDF 解析服务 - 从 PDF 文件中提取文本内容
"""
import pdfplumber
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class PDFParser:
    """Extract text from PDF files using pdfplumber."""

    @staticmethod
    def extract_text(file_path: str) -> dict:
        """
        Extract text from a PDF file.

        Returns:
            {
                "text": str,        # full extracted text
                "pages": list,      # per-page text
                "page_count": int,
                "tables": list      # extracted tables
            }
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        full_text = []
        pages = []
        tables = []

        try:
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    # Extract text
                    page_text = page.extract_text() or ""
                    pages.append({"page": i + 1, "text": page_text})
                    full_text.append(page_text)

                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            tables.append({"page": i + 1, "data": table})

                return {
                    "text": "\n\n".join(full_text),
                    "pages": pages,
                    "page_count": len(pdf.pages),
                    "tables": tables,
                }
        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise

    @staticmethod
    def get_page_count(file_path: str) -> int:
        """Get the number of pages in a PDF."""
        with pdfplumber.open(file_path) as pdf:
            return len(pdf.pages)
