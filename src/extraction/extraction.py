"""
File extraction utilities (PDF, DOCX, OCR for images).
"""
import fitz
from docx import Document
from PIL import Image
import pytesseract
import cv2
import numpy as np

# Handle both relative and absolute imports
try:
    from .image_processing import preprocess_image_for_ocr
    from ..logging_utils import log_step
except ImportError:
    from src.extraction.image_processing import preprocess_image_for_ocr
    from src.logging_utils import log_step

# On macOS/Linux, tesseract is usually installed via package manager and available on PATH
# On Windows, you may need to set: pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extract_text_image(path, filename=""):
    """
    Extract text from image files (PNG, JPG, JPEG) using OCR with preprocessing.
    
    Args:
        path: Path to the image file
        filename: Optional filename for logging
        
    Returns:
        str: Extracted text
    """
    try:
        log_step(f"{filename}: Starting image preprocessing for OCR")
        
        # Preprocess image for better OCR
        processed_img = preprocess_image_for_ocr(path)
        
        log_step(f"{filename}: Image preprocessing completed, running OCR")
        
        # Configure Tesseract for better accuracy
        # PSM 3 = Fully automatic page segmentation (default)
        # PSM 6 = Assume a single uniform block of text
        custom_config = r'--oem 3 --psm 3'
        
        # Extract text with multiple languages support
        text = pytesseract.image_to_string(processed_img, lang='eng', config=custom_config)
        
        log_step(f"{filename}: OCR completed, extracted {len(text)} characters")
        
        return text
    except Exception as e:
        error_msg = f"Error extracting text from image {path}: {str(e)}"
        log_step(f"{filename}: {error_msg}")
        return f"ERROR: {error_msg}"


def extract_text_pdf(path, filename=""):
    """
    Extract text from PDF files. Uses OCR for image-based pages.
    
    Args:
        path: Path to the PDF file
        filename: Optional filename for logging
        
    Returns:
        str: Extracted text
    """
    try:
        doc = fitz.open(path)
        full_text = ""
        total_pages = len(doc)
        
        log_step(f"{filename}: Processing PDF with {total_pages} pages")
        
        for page_num, page in enumerate(doc, 1):
            t = page.get_text()
            # Ensure t is a string
            if isinstance(t, list):
                t = "\n".join(str(item) for item in t)
            
            if isinstance(t, str) and t.strip() and len(t.strip()) > 50:
                # Page has sufficient text content
                full_text += t
                log_step(f"{filename}: Page {page_num}/{total_pages} - text extracted directly")
            else:
                # Page is likely an image, use OCR
                log_step(f"{filename}: Page {page_num}/{total_pages} - applying OCR")
                pix = page.get_pixmap(dpi=300)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                
                # Convert PIL to numpy array for preprocessing
                img_array = np.array(img)
                
                # Apply preprocessing
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                denoised = cv2.fastNlMeansDenoising(gray, None, h=10)
                
                # Convert back to PIL
                processed_img = Image.fromarray(denoised)
                
                # OCR with custom config
                custom_config = r'--oem 3 --psm 3'
                ocr_text = pytesseract.image_to_string(processed_img, lang="eng", config=custom_config)
                full_text += ocr_text
                log_step(f"{filename}: Page {page_num}/{total_pages} - OCR completed")
        
        return full_text
    except Exception as e:
        error_msg = f"Error extracting text from PDF {path}: {str(e)}"
        log_step(f"{filename}: {error_msg}")
        return f"ERROR: {error_msg}"


def extract_text_docx(path, filename=""):
    """
    Extract text from DOCX files.
    
    Args:
        path: Path to the DOCX file
        filename: Optional filename for logging
        
    Returns:
        str: Extracted text
    """
    try:
        doc = Document(path)
        text = "\n".join([p.text for p in doc.paragraphs])
        log_step(f"{filename}: Extracted {len(text)} characters from DOCX")
        return text
    except Exception as e:
        error_msg = f"Error extracting text from DOCX {path}: {str(e)}"
        log_step(f"{filename}: {error_msg}")
        return f"ERROR: {error_msg}"
