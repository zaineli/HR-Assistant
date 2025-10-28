"""
Image preprocessing utilities for improved OCR accuracy.
"""
import cv2
import numpy as np
from PIL import Image


def preprocess_image_for_ocr(image_path):
    """
    Apply comprehensive preprocessing to an image for better OCR results.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        PIL.Image: Preprocessed image ready for OCR
    """
    # Read image with OpenCV
    img = cv2.imread(image_path)
    
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply denoising
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
    
    # Deskew the image
    deskewed = deskew_image(denoised)
    
    # Apply adaptive thresholding for better text contrast
    # This works better than simple binary threshold for varied lighting
    thresh = cv2.adaptiveThreshold(
        deskewed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    
    # Optional: Apply morphological operations to clean up
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    # Convert back to PIL Image for pytesseract
    pil_image = Image.fromarray(processed)
    
    return pil_image


def deskew_image(image):
    """
    Detect and correct skew in an image.
    
    Args:
        image: Grayscale numpy array
        
    Returns:
        numpy.ndarray: Deskewed image
    """
    # Calculate skew angle
    coords = np.column_stack(np.where(image > 0))
    if len(coords) < 5:  # Not enough points to calculate angle
        return image
    
    angle = cv2.minAreaRect(coords)[-1]
    
    # Correct the angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Rotate image to deskew
    if abs(angle) > 0.5:  # Only rotate if angle is significant
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return rotated
    
    return image


def enhance_contrast(image):
    """
    Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image: Grayscale numpy array
        
    Returns:
        numpy.ndarray: Contrast-enhanced image
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(image)
    return enhanced


def remove_borders(image, border_size=10):
    """
    Remove borders from an image (useful for scanned documents).
    
    Args:
        image: Grayscale numpy array
        border_size: Number of pixels to remove from each edge
        
    Returns:
        numpy.ndarray: Image with borders removed
    """
    h, w = image.shape[:2]
    return image[border_size:h-border_size, border_size:w-border_size]
