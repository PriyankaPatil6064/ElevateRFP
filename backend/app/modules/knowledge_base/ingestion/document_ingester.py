# app/modules/knowledge_base/ingestion/document_ingester.py
from typing import Dict, List, Any, Optional, Union, BinaryIO
import os
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime
import structlog
import aiofiles
import json
import csv
from dataclasses import dataclass

from app.modules.document_processing.parser import DocumentProcessor
from app.modules.knowledge_base.ingestion.content_validator import ContentValidator
from app.modules.knowledge_base.ingestion.metadata_extractor import MetadataExtractor
from app.modules.knowledge_base.types import DocumentType
from app.config import settings

logger = structlog.get_logger()

@dataclass
class IngestionResult:
    """Result of document ingestion process"""
    success: bool
    document_id: str
    text: str
    metadata: Dict[str, Any]
    validation_score: float
    processing_time: float
    error: Optional[str] = None
    warnings: List[str] = None

class DocumentIngester:
    """Enterprise document ingestion pipeline"""
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.content_validator = ContentValidator()
        self.metadata_extractor = MetadataExtractor()
        
        # Supported file types and their processors
        self.supported_formats = {
            '.pdf': self._process_pdf,
            '.docx': self._process_docx,
            '.doc': self._process_docx,
            '.txt': self._process_text,
            '.json': self._process_json,
            '.csv': self._process_csv,
            '.xlsx': self._process_excel,
            '.md': self._process_markdown
        }
        
        logger.info("Document Ingester initialized", 
                   supported_formats=list(self.supported_formats.keys()))
    
    async def process_file(self, 
                          file_path: str, 
                          document_type: DocumentType,
                          metadata: Dict[str, Any] = None) -> IngestionResult:
        """Process a single file for ingestion"""
        start_time = datetime.now()
        
        try:
            logger.info("Starting file processing", 
                       file_path=file_path,
                       document_type=document_type.value)
            
            # Validate file exists and is readable
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Get file extension
            file_extension = Path(file_path).suffix.lower()
            
            if file_extension not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {file_extension}")
            
            # Process file based on type
            processor = self.supported_formats[file_extension]
            processing_result = await processor(file_path, document_type, metadata or {})
            
            # Validate content quality
            validation_result = await self.content_validator.validate_content(
                processing_result["text"], 
                document_type
            )
            
            # Extract additional metadata
            extracted_metadata = await self.metadata_extractor.extract_metadata(
                processing_result["text"],
                document_type,
                file_path
            )
            
            # Combine all metadata
            final_metadata = {
                **processing_result.get("metadata", {}),
                **extracted_metadata,
                **metadata,
                "file_path": file_path,
                "file_extension": file_extension,
                "document_type": document_type.value,
                "processed_at": datetime.now().isoformat(),
                "validation_score": validation_result.score,
                "validation_issues": validation_result.issues
            }
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = IngestionResult(
                success=True,
                document_id=self._generate_document_id(file_path),
                text=processing_result["text"],
                metadata=final_metadata,
                validation_score=validation_result.score,
                processing_time=processing_time,
                warnings=validation_result.warnings
            )
            
            logger.info("File processing completed", 
                       file_path=file_path,
                       text_length=len(result.text),
                       validation_score=result.validation_score,
                       processing_time=processing_time)
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.error("File processing failed", 
                        file_path=file_path,
                        error=str(e),
                        processing_time=processing_time)
            
            return IngestionResult(
                success=False,
                document_id=self._generate_document_id(file_path),
                text="",
                metadata=metadata or {},
                validation_score=0.0,
                processing_time=processing_time,
                error=str(e)
            )
    
    async def process_upload(self, 
                           file_content: BinaryIO, 
                           filename: str,
                           document_type: DocumentType,
                           metadata: Dict[str, Any] = None) -> IngestionResult:
        """Process uploaded file content"""
        try:
            # Save uploaded content to temporary file
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix,
                delete=False
            ) as temp_file:
                # Read and write file content
                content = await self._read_upload_content(file_content)
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Process the temporary file
                result = await self.process_file(temp_file_path, document_type, metadata)
                
                # Update metadata with original filename
                result.metadata["original_filename"] = filename
                result.metadata["file_size"] = len(content)
                
                return result
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error("Upload processing failed", 
                        filename=filename,
                        error=str(e))
            raise
    
    async def process_batch(self, 
                          file_paths: List[str],
                          document_type: DocumentType,
                          batch_size: int = 5) -> List[IngestionResult]:
        """Process multiple files in batches"""
        try:
            logger.info("Starting batch processing", 
                       total_files=len(file_paths),
                       batch_size=batch_size)
            
            results = []
            
            # Process in batches to avoid overwhelming the system
            for i in range(0, len(file_paths), batch_size):
                batch = file_paths[i:i + batch_size]
                
                # Process batch concurrently
                batch_tasks = [
                    self.process_file(file_path, document_type)
                    for file_path in batch
                ]
                
                batch_results = await asyncio.gather(
                    *batch_tasks,
                    return_exceptions=True
                )
                
                # Collect results
                for file_path, result in zip(batch, batch_results):
                    if isinstance(result, Exception):
                        error_result = IngestionResult(
                            success=False,
                            document_id=self._generate_document_id(file_path),
                            text="",
                            metadata={},
                            validation_score=0.0,
                            processing_time=0.0,
                            error=str(result)
                        )
                        results.append(error_result)
                    else:
                        results.append(result)
                
                logger.info("Batch processed", 
                           batch_number=i // batch_size + 1,
                           successful=len([r for r in batch_results if not isinstance(r, Exception)]))
            
            return results
            
        except Exception as e:
            logger.error("Batch processing failed", error=str(e))
            raise
    
    async def _process_pdf(self, 
                          file_path: str, 
                          document_type: DocumentType,
                          metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process PDF document"""
        result = await self.document_processor.process_document(file_path, Path(file_path).name)
        return {
            "text": result["processed_text"],
            "metadata": {
                **result["metadata"],
                **metadata,
                "pages": result["metadata"].get("pages", 0),
                "ocr_used": result["metadata"].get("ocr_used", False)
            }
        }
    
    async def _process_docx(self, 
                           file_path: str, 
                           document_type: DocumentType,
                           metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process DOCX/DOC document"""
        result = await self.document_processor.process_document(file_path, Path(file_path).name)
        return {
            "text": result["processed_text"],
            "metadata": {
                **result["metadata"],
                **metadata,
                "paragraphs": result["metadata"].get("paragraphs", 0),
                "tables": result["metadata"].get("tables", 0)
            }
        }
    
    async def _process_text(self, 
                           file_path: str, 
                           document_type: DocumentType,
                           metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process plain text document"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        return {
            "text": content,
            "metadata": {
                **metadata,
                "lines": len(content.split('\n')),
                "word_count": len(content.split())
            }
        }
    
    async def _process_json(self, 
                           file_path: str, 
                           document_type: DocumentType,
                           metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process JSON document"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        try:
            data = json.loads(content)
            
            # Convert JSON to readable text
            if document_type == DocumentType.PRODUCT_CATALOG:
                text = self._json_to_product_text(data)
            elif document_type == DocumentType.PRICING_SHEET:
                text = self._json_to_pricing_text(data)
            else:
                text = self._json_to_text(data)
            
            return {
                "text": text,
                "metadata": {
                    **metadata,
                    "json_structure": self._analyze_json_structure(data),
                    "record_count": len(data) if isinstance(data, list) else 1
                }
            }
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
    
    async def _process_csv(self, 
                          file_path: str, 
                          document_type: DocumentType,
                          metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process CSV document"""
        rows = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            for row in reader:
                rows.append(row)
        
        # Convert CSV to readable text
        if document_type == DocumentType.PRODUCT_CATALOG:
            text = self._csv_to_product_text(rows, headers)
        elif document_type == DocumentType.PRICING_SHEET:
            text = self._csv_to_pricing_text(rows, headers)
        else:
            text = self._csv_to_text(rows, headers)
        
        return {
            "text": text,
            "metadata": {
                **metadata,
                "columns": headers,
                "row_count": len(rows),
                "column_count": len(headers) if headers else 0
            }
        }
    
    async def _process_excel(self, 
                            file_path: str, 
                            document_type: DocumentType,
                            metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process Excel document"""
        try:
            import pandas as pd
            
            # Read Excel file
            df = pd.read_excel(file_path)
            
            # Convert to text format
            text_lines = []
            
            # Add column headers
            text_lines.append("Columns: " + ", ".join(df.columns.tolist()))
            text_lines.append("")
            
            # Add data rows
            for _, row in df.iterrows():
                row_text = []
                for col, value in row.items():
                    if pd.notna(value):
                        row_text.append(f"{col}: {value}")
                
                if row_text:
                    text_lines.append(" | ".join(row_text))
            
            return {
                "text": "\n".join(text_lines),
                "metadata": {
                    **metadata,
                    "columns": df.columns.tolist(),
                    "row_count": len(df),
                    "column_count": len(df.columns)
                }
            }
            
        except ImportError:
            raise ValueError("pandas required for Excel processing")
        except Exception as e:
            raise ValueError(f"Excel processing failed: {str(e)}")
    
    async def _process_markdown(self, 
                               file_path: str, 
                               document_type: DocumentType,
                               metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Process Markdown document"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        # Remove markdown formatting for plain text
        import re
        
        # Remove headers
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
        
        # Remove bold/italic
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)
        content = re.sub(r'\*(.*?)\*', r'\1', content)
        
        # Remove links
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)
        
        # Remove code blocks
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
        content = re.sub(r'`([^`]+)`', r'\1', content)
        
        return {
            "text": content,
            "metadata": {
                **metadata,
                "lines": len(content.split('\n')),
                "word_count": len(content.split())
            }
        }
    
    def _json_to_product_text(self, data: Union[Dict, List]) -> str:
        """Convert JSON product data to readable text"""
        if isinstance(data, list):
            products = data
        elif isinstance(data, dict) and 'products' in data:
            products = data['products']
        else:
            products = [data]
        
        text_lines = []
        
        for product in products:
            if isinstance(product, dict):
                lines = [f"Product: {product.get('name', 'Unknown')}"]
                
                if 'description' in product:
                    lines.append(f"Description: {product['description']}")
                
                if 'specifications' in product:
                    lines.append("Specifications:")
                    specs = product['specifications']
                    if isinstance(specs, dict):
                        for key, value in specs.items():
                            lines.append(f"  {key}: {value}")
                
                if 'features' in product:
                    lines.append("Features:")
                    features = product['features']
                    if isinstance(features, list):
                        for feature in features:
                            lines.append(f"  - {feature}")
                
                text_lines.extend(lines)
                text_lines.append("")  # Empty line between products
        
        return "\n".join(text_lines)
    
    def _json_to_pricing_text(self, data: Union[Dict, List]) -> str:
        """Convert JSON pricing data to readable text"""
        text_lines = ["Pricing Information:"]
        
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    name = item.get('name', item.get('product', 'Item'))
                    price = item.get('price', item.get('cost', 'N/A'))
                    text_lines.append(f"{name}: {price}")
        elif isinstance(data, dict):
            for key, value in data.items():
                text_lines.append(f"{key}: {value}")
        
        return "\n".join(text_lines)
    
    def _json_to_text(self, data: Any) -> str:
        """Convert generic JSON to readable text"""
        def flatten_json(obj, prefix=""):
            lines = []
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    new_key = f"{prefix}.{key}" if prefix else key
                    
                    if isinstance(value, (dict, list)):
                        lines.extend(flatten_json(value, new_key))
                    else:
                        lines.append(f"{new_key}: {value}")
            
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    new_key = f"{prefix}[{i}]" if prefix else f"item_{i}"
                    
                    if isinstance(item, (dict, list)):
                        lines.extend(flatten_json(item, new_key))
                    else:
                        lines.append(f"{new_key}: {item}")
            
            return lines
        
        return "\n".join(flatten_json(data))
    
    def _csv_to_product_text(self, rows: List[Dict], headers: List[str]) -> str:
        """Convert CSV product data to readable text"""
        text_lines = []
        
        for row in rows:
            product_lines = []
            
            # Try to identify product name
            name_fields = ['name', 'product_name', 'title', 'product']
            product_name = None
            
            for field in name_fields:
                if field in row and row[field]:
                    product_name = row[field]
                    break
            
            if product_name:
                product_lines.append(f"Product: {product_name}")
            
            # Add other fields
            for header in headers:
                if header.lower() not in name_fields and row.get(header):
                    product_lines.append(f"{header}: {row[header]}")
            
            text_lines.extend(product_lines)
            text_lines.append("")  # Empty line between products
        
        return "\n".join(text_lines)
    
    def _csv_to_pricing_text(self, rows: List[Dict], headers: List[str]) -> str:
        """Convert CSV pricing data to readable text"""
        text_lines = ["Pricing Information:"]
        
        for row in rows:
            # Try to identify item and price
            item_fields = ['item', 'product', 'name', 'service']
            price_fields = ['price', 'cost', 'amount', 'rate']
            
            item_name = None
            price_value = None
            
            for field in item_fields:
                if field in row and row[field]:
                    item_name = row[field]
                    break
            
            for field in price_fields:
                if field in row and row[field]:
                    price_value = row[field]
                    break
            
            if item_name and price_value:
                text_lines.append(f"{item_name}: {price_value}")
            elif item_name:
                text_lines.append(f"{item_name}: Price not specified")
        
        return "\n".join(text_lines)
    
    def _csv_to_text(self, rows: List[Dict], headers: List[str]) -> str:
        """Convert generic CSV to readable text"""
        text_lines = []
        
        # Add headers
        text_lines.append("Data columns: " + ", ".join(headers))
        text_lines.append("")
        
        # Add rows
        for i, row in enumerate(rows):
            row_lines = [f"Record {i + 1}:"]
            
            for header in headers:
                if row.get(header):
                    row_lines.append(f"  {header}: {row[header]}")
            
            text_lines.extend(row_lines)
            text_lines.append("")
        
        return "\n".join(text_lines)
    
    def _analyze_json_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze JSON structure for metadata"""
        def analyze_object(obj):
            if isinstance(obj, dict):
                return {
                    "type": "object",
                    "keys": list(obj.keys()),
                    "key_count": len(obj)
                }
            elif isinstance(obj, list):
                return {
                    "type": "array",
                    "length": len(obj),
                    "item_types": list(set(type(item).__name__ for item in obj[:10]))
                }
            else:
                return {
                    "type": type(obj).__name__,
                    "value": str(obj)[:100]
                }
        
        return analyze_object(data)
    
    def _generate_document_id(self, file_path: str) -> str:
        """Generate unique document ID"""
        import hashlib
        
        # Use file path and current timestamp for uniqueness
        content = f"{file_path}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _read_upload_content(self, file_content: BinaryIO) -> bytes:
        """Read uploaded file content"""
        if hasattr(file_content, 'read'):
            return file_content.read()
        else:
            return file_content