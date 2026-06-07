# app/modules/knowledge_base/ingestion/content_validator.py
from typing import Dict, List, Any, Optional
import re
from dataclasses import dataclass
from enum import Enum
import structlog
from app.modules.knowledge_base.types import DocumentType

logger = structlog.get_logger()

class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class ValidationIssue:
    """Validation issue details"""
    severity: ValidationSeverity
    category: str
    message: str
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    """Content validation result"""
    score: float  # 0.0 to 1.0
    is_valid: bool
    issues: List[ValidationIssue]
    warnings: List[str]
    quality_metrics: Dict[str, float]

class ContentValidator:
    """Enterprise content validation and quality assessment"""
    
    def __init__(self):
        # Quality thresholds
        self.min_word_count = 50
        self.min_sentence_count = 3
        self.max_repetition_ratio = 0.3
        self.min_readability_score = 0.3
        
        # Document type specific validators
        self.type_validators = {
            DocumentType.PRODUCT_CATALOG: self._validate_product_catalog,
            DocumentType.PROPOSAL: self._validate_proposal,
            DocumentType.CASE_STUDY: self._validate_case_study,
            DocumentType.COMPLIANCE_DOC: self._validate_compliance_doc,
            DocumentType.CERTIFICATION: self._validate_certification,
            DocumentType.PRICING_SHEET: self._validate_pricing_sheet,
            DocumentType.TECHNICAL_SPEC: self._validate_technical_spec
        }
        
        # Domain-specific keywords
        self.domain_keywords = {
            "rfp": ["request", "proposal", "requirement", "specification", "bid", "tender"],
            "technical": ["system", "architecture", "implementation", "technology", "solution"],
            "compliance": ["gdpr", "iso", "soc2", "hipaa", "compliance", "audit", "certification"],
            "pricing": ["price", "cost", "budget", "rate", "fee", "pricing", "quote"],
            "product": ["product", "feature", "capability", "specification", "model"]
        }
        
        logger.info("Content Validator initialized")
    
    async def validate_content(self, 
                             text: str, 
                             document_type: DocumentType,
                             metadata: Dict[str, Any] = None) -> ValidationResult:
        """Validate document content quality and relevance"""
        try:
            logger.info("Starting content validation", 
                       document_type=document_type.value,
                       text_length=len(text))
            
            issues = []
            warnings = []
            quality_metrics = {}
            
            # Basic content validation
            basic_issues, basic_metrics = self._validate_basic_content(text)
            issues.extend(basic_issues)
            quality_metrics.update(basic_metrics)
            
            # Language and readability validation
            lang_issues, lang_metrics = self._validate_language_quality(text)
            issues.extend(lang_issues)
            quality_metrics.update(lang_metrics)
            
            # Structure validation
            struct_issues, struct_metrics = self._validate_structure(text)
            issues.extend(struct_issues)
            quality_metrics.update(struct_metrics)
            
            # Domain relevance validation
            domain_issues, domain_metrics = self._validate_domain_relevance(text, document_type)
            issues.extend(domain_issues)
            quality_metrics.update(domain_metrics)
            
            # Document type specific validation
            if document_type in self.type_validators:
                type_issues, type_metrics = await self.type_validators[document_type](text)
                issues.extend(type_issues)
                quality_metrics.update(type_metrics)
            
            # Calculate overall score
            score = self._calculate_overall_score(quality_metrics, issues)
            
            # Determine if content is valid
            is_valid = score >= 0.5 and not any(issue.severity == ValidationSeverity.CRITICAL for issue in issues)
            
            # Generate warnings
            warnings = [issue.message for issue in issues if issue.severity == ValidationSeverity.WARNING]
            
            result = ValidationResult(
                score=score,
                is_valid=is_valid,
                issues=issues,
                warnings=warnings,
                quality_metrics=quality_metrics
            )
            
            logger.info("Content validation completed", 
                       score=score,
                       is_valid=is_valid,
                       issues_count=len(issues))
            
            return result
            
        except Exception as e:
            logger.error("Content validation failed", error=str(e))
            raise
    
    def _validate_basic_content(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate basic content requirements"""
        issues = []
        metrics = {}
        
        # Word count validation
        words = text.split()
        word_count = len(words)
        metrics["word_count"] = word_count
        
        if word_count < self.min_word_count:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="content_length",
                message=f"Document too short: {word_count} words (minimum: {self.min_word_count})",
                suggestion="Ensure document contains sufficient content for meaningful analysis"
            ))
        
        # Sentence count validation
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])
        metrics["sentence_count"] = sentence_count
        
        if sentence_count < self.min_sentence_count:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="content_structure",
                message=f"Very few sentences: {sentence_count} (minimum recommended: {self.min_sentence_count})",
                suggestion="Check if document content is properly formatted"
            ))
        
        # Character count and density
        char_count = len(text)
        metrics["character_count"] = char_count
        metrics["avg_word_length"] = char_count / max(word_count, 1)
        
        # Check for excessive whitespace
        whitespace_ratio = (char_count - len(text.replace(' ', '').replace('\n', '').replace('\t', ''))) / max(char_count, 1)
        metrics["whitespace_ratio"] = whitespace_ratio
        
        if whitespace_ratio > 0.5:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="formatting",
                message="Document contains excessive whitespace",
                suggestion="Review document formatting and remove unnecessary spaces"
            ))
        
        return issues, metrics
    
    def _validate_language_quality(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate language quality and readability"""
        issues = []
        metrics = {}
        
        # Check for repetitive content
        words = text.lower().split()
        if words:
            unique_words = set(words)
            repetition_ratio = 1 - (len(unique_words) / len(words))
            metrics["repetition_ratio"] = repetition_ratio
            
            if repetition_ratio > self.max_repetition_ratio:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="content_quality",
                    message=f"High repetition ratio: {repetition_ratio:.2f}",
                    suggestion="Review content for unnecessary repetition"
                ))
        
        # Basic readability assessment
        sentences = re.split(r'[.!?]+', text)
        valid_sentences = [s.strip() for s in sentences if s.strip()]
        
        if valid_sentences:
            avg_sentence_length = len(words) / len(valid_sentences)
            metrics["avg_sentence_length"] = avg_sentence_length
            
            # Simple readability score (based on sentence length)
            if avg_sentence_length > 30:
                readability_penalty = min(0.3, (avg_sentence_length - 30) / 100)
                metrics["readability_score"] = 1.0 - readability_penalty
                
                if avg_sentence_length > 50:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category="readability",
                        message=f"Long average sentence length: {avg_sentence_length:.1f} words",
                        suggestion="Consider breaking down complex sentences for better readability"
                    ))
            else:
                metrics["readability_score"] = 1.0
        
        # Check for common OCR errors
        ocr_error_patterns = [
            r'\b[Il1]\b',  # Single characters that might be OCR errors
            r'\b[0O]\b',   # Zero/O confusion
            r'[^\w\s.,!?;:()-]',  # Unusual characters
        ]
        
        ocr_error_count = 0
        for pattern in ocr_error_patterns:
            ocr_error_count += len(re.findall(pattern, text))
        
        ocr_error_ratio = ocr_error_count / max(len(words), 1)
        metrics["ocr_error_ratio"] = ocr_error_ratio
        
        if ocr_error_ratio > 0.05:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="text_quality",
                message=f"Possible OCR errors detected: {ocr_error_ratio:.2%}",
                suggestion="Review document for text recognition errors"
            ))
        
        return issues, metrics
    
    def _validate_structure(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate document structure"""
        issues = []
        metrics = {}
        
        # Check for headers/sections
        header_patterns = [
            r'^[A-Z][A-Z\s]{2,}$',  # ALL CAPS headers
            r'^\d+\.?\s+[A-Z]',     # Numbered sections
            r'^[A-Z][^.]*:$',       # Colon-ended headers
        ]
        
        lines = text.split('\n')
        header_count = 0
        
        for line in lines:
            line = line.strip()
            for pattern in header_patterns:
                if re.match(pattern, line):
                    header_count += 1
                    break
        
        metrics["header_count"] = header_count
        metrics["structure_score"] = min(1.0, header_count / 5)  # Normalize to 0-1
        
        if header_count == 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="structure",
                message="No clear document structure detected",
                suggestion="Consider adding headers or sections for better organization"
            ))
        
        # Check for lists
        list_patterns = [
            r'^\s*[-*•]\s+',  # Bullet points
            r'^\s*\d+\.\s+',  # Numbered lists
            r'^\s*[a-z]\)\s+', # Lettered lists
        ]
        
        list_item_count = 0
        for line in lines:
            for pattern in list_patterns:
                if re.match(pattern, line):
                    list_item_count += 1
                    break
        
        metrics["list_item_count"] = list_item_count
        
        # Check for tables (simple detection)
        table_indicators = ['|', '\t', '  ']  # Common table separators
        potential_table_lines = 0
        
        for line in lines:
            if any(indicator in line for indicator in table_indicators):
                # Check if line has multiple separators (likely a table row)
                separator_count = sum(line.count(sep) for sep in table_indicators)
                if separator_count >= 2:
                    potential_table_lines += 1
        
        metrics["table_lines"] = potential_table_lines
        
        return issues, metrics
    
    def _validate_domain_relevance(self, text: str, document_type: DocumentType) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate domain relevance and terminology"""
        issues = []
        metrics = {}
        
        text_lower = text.lower()
        
        # Check for domain-specific keywords
        domain_scores = {}
        
        for domain, keywords in self.domain_keywords.items():
            keyword_count = sum(1 for keyword in keywords if keyword in text_lower)
            domain_scores[domain] = keyword_count / len(keywords)
        
        metrics["domain_scores"] = domain_scores
        
        # Determine expected domain based on document type
        expected_domains = {
            DocumentType.PRODUCT_CATALOG: ["product", "technical"],
            DocumentType.PROPOSAL: ["rfp", "technical"],
            DocumentType.CASE_STUDY: ["technical", "product"],
            DocumentType.COMPLIANCE_DOC: ["compliance"],
            DocumentType.PRICING_SHEET: ["pricing", "product"],
            DocumentType.TECHNICAL_SPEC: ["technical", "product"]
        }
        
        if document_type in expected_domains:
            relevant_domains = expected_domains[document_type]
            relevance_score = max(domain_scores.get(domain, 0) for domain in relevant_domains)
            metrics["relevance_score"] = relevance_score
            
            if relevance_score < 0.1:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    category="domain_relevance",
                    message=f"Low domain relevance for {document_type.value}: {relevance_score:.2f}",
                    suggestion=f"Ensure document contains relevant {'/'.join(relevant_domains)} terminology"
                ))
        
        return issues, metrics
    
    async def _validate_product_catalog(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate product catalog specific content"""
        issues = []
        metrics = {}
        
        # Check for product-related terms
        product_terms = ["product", "model", "specification", "feature", "price", "description"]
        found_terms = sum(1 for term in product_terms if term.lower() in text.lower())
        
        metrics["product_terms_coverage"] = found_terms / len(product_terms)
        
        if found_terms < 3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="product_content",
                message="Limited product-related terminology found",
                suggestion="Ensure document contains product names, specifications, and descriptions"
            ))
        
        # Check for structured product information
        product_patterns = [
            r'product\s*:\s*\w+',
            r'model\s*:\s*\w+',
            r'price\s*:\s*[\$€£]?\d+',
            r'specification\s*:',
        ]
        
        structured_info_count = 0
        for pattern in product_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                structured_info_count += 1
        
        metrics["structured_info_score"] = structured_info_count / len(product_patterns)
        
        return issues, metrics
    
    async def _validate_proposal(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate proposal specific content"""
        issues = []
        metrics = {}
        
        # Check for proposal sections
        proposal_sections = [
            "executive summary", "introduction", "approach", "methodology",
            "timeline", "budget", "team", "experience", "conclusion"
        ]
        
        found_sections = sum(1 for section in proposal_sections if section.lower() in text.lower())
        metrics["proposal_sections_coverage"] = found_sections / len(proposal_sections)
        
        if found_sections < 3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="proposal_structure",
                message="Few standard proposal sections found",
                suggestion="Consider including standard proposal sections like executive summary, approach, timeline"
            ))
        
        return issues, metrics
    
    async def _validate_case_study(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate case study specific content"""
        issues = []
        metrics = {}
        
        # Check for case study elements
        case_study_elements = [
            "challenge", "solution", "result", "outcome", "client", "project",
            "implementation", "benefit", "success", "improvement"
        ]
        
        found_elements = sum(1 for element in case_study_elements if element.lower() in text.lower())
        metrics["case_study_elements_coverage"] = found_elements / len(case_study_elements)
        
        if found_elements < 4:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="case_study_content",
                message="Limited case study elements found",
                suggestion="Include challenge, solution, implementation, and results information"
            ))
        
        return issues, metrics
    
    async def _validate_compliance_doc(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate compliance document specific content"""
        issues = []
        metrics = {}
        
        # Check for compliance frameworks
        compliance_frameworks = ["gdpr", "iso27001", "soc2", "hipaa", "pci", "nist"]
        found_frameworks = sum(1 for fw in compliance_frameworks if fw.lower() in text.lower())
        
        metrics["compliance_frameworks_coverage"] = found_frameworks / len(compliance_frameworks)
        
        # Check for compliance terms
        compliance_terms = ["control", "requirement", "audit", "assessment", "policy", "procedure"]
        found_terms = sum(1 for term in compliance_terms if term.lower() in text.lower())
        
        metrics["compliance_terms_coverage"] = found_terms / len(compliance_terms)
        
        if found_frameworks == 0 and found_terms < 2:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="compliance_content",
                message="Limited compliance-related content found",
                suggestion="Ensure document contains compliance frameworks, controls, or requirements"
            ))
        
        return issues, metrics
    
    async def _validate_certification(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate certification document specific content"""
        issues = []
        metrics = {}
        
        # Check for certification terms
        cert_terms = ["certificate", "certification", "certified", "accredited", "standard", "compliance"]
        found_terms = sum(1 for term in cert_terms if term.lower() in text.lower())
        
        metrics["certification_terms_coverage"] = found_terms / len(cert_terms)
        
        if found_terms < 2:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="certification_content",
                message="Limited certification-related terminology",
                suggestion="Ensure document contains certification details and standards"
            ))
        
        return issues, metrics
    
    async def _validate_pricing_sheet(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate pricing sheet specific content"""
        issues = []
        metrics = {}
        
        # Check for pricing information
        price_patterns = [
            r'[\$€£]\s*\d+',  # Currency symbols with numbers
            r'\d+\s*(?:usd|eur|gbp)',  # Numbers with currency codes
            r'price\s*:\s*\d+',  # Price: format
            r'cost\s*:\s*\d+',   # Cost: format
        ]
        
        price_matches = 0
        for pattern in price_patterns:
            price_matches += len(re.findall(pattern, text, re.IGNORECASE))
        
        metrics["price_information_count"] = price_matches
        
        if price_matches == 0:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="pricing_content",
                message="No pricing information found in pricing sheet",
                suggestion="Ensure document contains actual prices, costs, or rates"
            ))
        
        return issues, metrics
    
    async def _validate_technical_spec(self, text: str) -> tuple[List[ValidationIssue], Dict[str, float]]:
        """Validate technical specification specific content"""
        issues = []
        metrics = {}
        
        # Check for technical terms
        tech_terms = [
            "system", "architecture", "component", "interface", "protocol",
            "specification", "requirement", "implementation", "configuration"
        ]
        
        found_terms = sum(1 for term in tech_terms if term.lower() in text.lower())
        metrics["technical_terms_coverage"] = found_terms / len(tech_terms)
        
        if found_terms < 4:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                category="technical_content",
                message="Limited technical terminology found",
                suggestion="Ensure document contains technical specifications and requirements"
            ))
        
        return issues, metrics
    
    def _calculate_overall_score(self, metrics: Dict[str, float], issues: List[ValidationIssue]) -> float:
        """Calculate overall content quality score"""
        # Base score from metrics
        base_score = 0.5
        
        # Add positive contributions
        if "word_count" in metrics:
            word_score = min(1.0, metrics["word_count"] / 500)  # Normalize to 500 words
            base_score += word_score * 0.2
        
        if "readability_score" in metrics:
            base_score += metrics["readability_score"] * 0.1
        
        if "structure_score" in metrics:
            base_score += metrics["structure_score"] * 0.1
        
        if "relevance_score" in metrics:
            base_score += metrics["relevance_score"] * 0.2
        
        # Subtract penalties for issues
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                base_score -= 0.3
            elif issue.severity == ValidationSeverity.ERROR:
                base_score -= 0.2
            elif issue.severity == ValidationSeverity.WARNING:
                base_score -= 0.1
        
        return max(0.0, min(1.0, base_score))