"""
MetroLens Statutory Enforcement Services Package:
- ocr_service: OpenCV image preprocessing & EasyOCR contour detection
- gemini_service: Google Gemini multimodal vision semantic declaration extraction
- rule_engine: Legal Metrology (Packaged Commodities) Rules, 2011 & FSSAI verification
- report_service: Statutory sealed PDF & editable DOCX notice generation
"""

from .ocr_service import run_package_ocr
from .gemini_service import extract_declarations_ai
from .rule_engine import evaluate_declarations
from .report_service import generate_pdf_report, generate_docx_report

__all__ = [
    "run_package_ocr",
    "extract_declarations_ai",
    "evaluate_declarations",
    "generate_pdf_report",
    "generate_docx_report",
]
