# app/modules/document_processing/ocr.py
from typing import Dict, Optional
import os
import tempfile
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import cv2
import numpy as np
import structlog
from app.config import settings

logger = structlog.get_logger()

class OCRProcessor:
    """Advanced OCR processing with image preprocessing"""
    
    def __init__(self):
        self.language = settings.OCR_LANGUAGE
        self.config = '--oem 3 --psm 6'  # OCR Engine Mode 3, Page Segmentation Mode 6
    
    async def extract_text(self, image_path: str) -> str:
        """Extract text from image using OCR with preprocessing"""
        try:
            logger.info("Starting OCR processing", image_path=image_path)
            
            # Load and preprocess image
            processed_image = self._preprocess_image(image_path)
            
            # Perform OCR
            text = pytesseract.image_to_string(
                processed_image,
                lang=self.language,
                config=self.config
            )
            
            # Clean extracted text
            cleaned_text = self._clean_ocr_text(text)
            
            logger.info("OCR processing completed", 
                       text_length=len(cleaned_text),
                       confidence=self._estimate_confidence(cleaned_text))
            
            return cleaned_text
            
        except Exception as e:
            logger.error("OCR processing failed", error=str(e))
            raise
    
    def _preprocess_image(self, image_path: str) -> Image.Image:
        """Preprocess image for better OCR results"""
        try:
            # Load image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert to OpenCV format for advanced preprocessing
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Apply preprocessing steps
            cv_image = self._denoise_image(cv_image)
            cv_image = self._correct_skew(cv_image)
            cv_image = self._enhance_contrast(cv_image)
            cv_image = self._binarize_image(cv_image)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB))
            
            return processed_image
            
        except Exception as e:
            logger.warning("Image preprocessing failed, using original", error=str(e))
            return Image.open(image_path)
    
    def _denoise_image(self, image: np.ndarray) -> np.ndarray:
        """Remove noise from image"""
        return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    
    def _correct_skew(self, image: np.ndarray) -> np.ndarray:
        """Correct skew in scanned documents"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to get binary image
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Find the largest contour (assumed to be the document)
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Get minimum area rectangle
                rect = cv2.minAreaRect(largest_contour)
                angle = rect[2]
                
                # Correct angle
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                
                # Rotate image if skew is significant
                if abs(angle) > 0.5:
                    (h, w) = image.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            return image
            
        except Exception as e:
            logger.warning("Skew correction failed", error=str(e))
            return image
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast"""
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        
        # Convert back to BGR
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    def _binarize_image(self, image: np.ndarray) -> np.ndarray:
        """Convert image to binary (black and white)"""
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive threshold
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        # Convert back to 3-channel for consistency
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    
    def _clean_ocr_text(self, text: str) -> str:
        """Clean and normalize OCR extracted text"""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors
        replacements = {
            r'\b0\b': 'O',  # Zero to O
            r'\bl\b': 'I',  # lowercase l to I
            r'rn': 'm',     # rn to m
            r'vv': 'w',     # vv to w
            r'\|': 'l',     # pipe to l
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        # Remove lines with mostly special characters (likely OCR artifacts)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line and len(re.sub(r'[^a-zA-Z0-9\s]', '', line)) > len(line) * 0.3:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _estimate_confidence(self, text: str) -> float:
        """Estimate OCR confidence based on text characteristics"""
        if not text:
            return 0.0
        
        # Count valid words vs total words
        words = text.split()
        if not words:
            return 0.0
        
        valid_words = 0
        for word in words:
            # Consider a word valid if it has reasonable character distribution
            if len(word) >= 2 and word.isalnum():
                valid_words += 1
        
        confidence = (valid_words / len(words)) * 100
        return min(100.0, confidence)
    
    async def extract_text_with_confidence(self, image_path: str) -> Dict:
        """Extract text with confidence scores"""
        try:
            # Get detailed OCR data
            processed_image = self._preprocess_image(image_path)
            
            # Extract text with confidence data
            data = pytesseract.image_to_data(
                processed_image,
                lang=self.language,
                config=self.config,
                output_type=pytesseract.Output.DICT
            )
            
            # Process results
            text_blocks = []
            confidences = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # Only include confident detections
                    text_blocks.append(data['text'][i])
                    confidences.append(int(data['conf'][i]))
            
            full_text = ' '.join(text_blocks)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                'text': self._clean_ocr_text(full_text),
                'confidence': avg_confidence,
                'word_count': len(text_blocks),
                'low_confidence_words': len([c for c in confidences if c < 60])
            }
            
        except Exception as e:
            logger.error("OCR with confidence failed", error=str(e))
            # Fallback to basic OCR
            text = await self.extract_text(image_path)
            return {
                'text': text,
                'confidence': self._estimate_confidence(text),
                'word_count': len(text.split()),
                'low_confidence_words': 0
            }