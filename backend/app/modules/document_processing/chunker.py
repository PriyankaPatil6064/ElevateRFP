# app/modules/document_processing/chunker.py
from typing import List, Dict, Any, Optional, Tuple
import re
from dataclasses import dataclass
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter
)
from langchain_core.documents import Document
import spacy
import structlog
from app.config import settings

logger = structlog.get_logger()

@dataclass
class ChunkMetadata:
    """Metadata for document chunks"""
    chunk_id: str
    chunk_index: int
    chunk_type: str  # paragraph, section, table, list, etc.
    source_section: Optional[str] = None
    page_number: Optional[int] = None
    confidence_score: float = 1.0
    word_count: int = 0
    sentence_count: int = 0
    has_technical_terms: bool = False
    has_requirements: bool = False
    has_compliance_terms: bool = False
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = None

class SemanticChunker:
    """Semantic-aware document chunking"""
    
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("Spacy model not found, using basic chunking")
            self.nlp = None
        
        self.technical_terms = {
            'software', 'hardware', 'system', 'platform', 'application', 'database',
            'security', 'compliance', 'gdpr', 'iso', 'soc2', 'api', 'integration',
            'requirement', 'specification', 'mandatory', 'optional', 'must', 'shall',
            'should', 'may', 'will', 'budget', 'timeline', 'deadline', 'deliverable'
        }
        
        self.compliance_terms = {
            'gdpr', 'iso27001', 'soc2', 'hipaa', 'pci', 'compliance', 'audit',
            'certification', 'standard', 'regulation', 'policy', 'procedure',
            'control', 'framework', 'assessment', 'validation', 'verification'
        }
        
        self.requirement_indicators = {
            'must', 'shall', 'should', 'required', 'mandatory', 'essential',
            'necessary', 'needed', 'expected', 'desired', 'preferred',
            'requirement', 'specification', 'criteria', 'condition'
        }
    
    def chunk_document(self, 
                      text: str, 
                      metadata: Dict = None, 
                      strategy: str = "hybrid") -> List[Document]:
        """Chunk document using specified strategy"""
        
        strategies = {
            "semantic": self._semantic_chunking,
            "recursive": self._recursive_chunking,
            "sentence": self._sentence_chunking,
            "section": self._section_chunking,
            "hybrid": self._hybrid_chunking
        }
        
        if strategy not in strategies:
            logger.warning(f"Unknown chunking strategy: {strategy}, using hybrid")
            strategy = "hybrid"
        
        logger.info("Starting document chunking", 
                   strategy=strategy, 
                   text_length=len(text))
        
        chunks = strategies[strategy](text, metadata or {})
        
        logger.info("Document chunking completed", 
                   strategy=strategy, 
                   chunks_created=len(chunks))
        
        return chunks
    
    def _hybrid_chunking(self, text: str, metadata: Dict) -> List[Document]:
        """Hybrid chunking combining multiple strategies"""
        chunks = []
        
        # First, try to identify document structure
        sections = self._identify_sections(text)
        
        if len(sections) > 1:
            # Document has clear sections, chunk by section first
            for section_title, section_text in sections:
                section_chunks = self._chunk_section(section_text, section_title, metadata)
                chunks.extend(section_chunks)
        else:
            # No clear sections, use semantic + recursive chunking
            semantic_chunks = self._semantic_chunking(text, metadata)
            
            # Further split large semantic chunks
            final_chunks = []
            for chunk in semantic_chunks:
                if len(chunk.page_content) > 1500:
                    sub_chunks = self._recursive_chunking(chunk.page_content, chunk.metadata)
                    final_chunks.extend(sub_chunks)
                else:
                    final_chunks.append(chunk)
            
            chunks = final_chunks
        
        # Add hierarchical relationships
        chunks = self._add_chunk_relationships(chunks)
        
        return chunks
    
    def _semantic_chunking(self, text: str, metadata: Dict) -> List[Document]:
        """Semantic chunking using NLP"""
        if not self.nlp:
            return self._recursive_chunking(text, metadata)
        
        doc = self.nlp(text)
        chunks = []
        current_chunk = []
        current_sentences = []
        
        for sent in doc.sents:
            sentence_text = sent.text.strip()
            if not sentence_text:
                continue
            
            current_sentences.append(sentence_text)
            current_chunk.append(sentence_text)
            
            # Check if we should end the chunk
            chunk_text = " ".join(current_chunk)
            
            if (len(chunk_text) > 800 and self._is_good_break_point(sent)) or len(chunk_text) > 1200:
                # Create chunk
                chunk_metadata = self._analyze_chunk_content(chunk_text, metadata)
                chunk_doc = Document(
                    page_content=chunk_text,
                    metadata=chunk_metadata
                )
                chunks.append(chunk_doc)
                
                # Reset for next chunk
                current_chunk = []
                current_sentences = []
        
        # Handle remaining content
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_metadata = self._analyze_chunk_content(chunk_text, metadata)
            chunk_doc = Document(
                page_content=chunk_text,
                metadata=chunk_metadata
            )
            chunks.append(chunk_doc)
        
        return chunks
    
    def _recursive_chunking(self, text: str, metadata: Dict) -> List[Document]:
        """Recursive character-based chunking"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = splitter.split_text(text)
        documents = []
        
        for i, chunk in enumerate(chunks):
            chunk_metadata = self._analyze_chunk_content(chunk, metadata)
            chunk_metadata.update({
                "chunk_index": i,
                "chunk_type": "recursive",
                "chunking_strategy": "recursive"
            })
            
            doc = Document(
                page_content=chunk,
                metadata=chunk_metadata
            )
            documents.append(doc)
        
        return documents
    
    def _sentence_chunking(self, text: str, metadata: Dict) -> List[Document]:
        """Sentence-based chunking"""
        if not self.nlp:
            # Fallback to simple sentence splitting
            sentences = re.split(r'[.!?]+', text)
        else:
            doc = self.nlp(text)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        chunks = []
        current_chunk = []
        
        for sentence in sentences:
            current_chunk.append(sentence)
            chunk_text = " ".join(current_chunk)
            
            if len(chunk_text) > 800:
                chunk_metadata = self._analyze_chunk_content(chunk_text, metadata)
                chunk_metadata.update({
                    "chunk_type": "sentence",
                    "sentence_count": len(current_chunk)
                })
                
                doc = Document(
                    page_content=chunk_text,
                    metadata=chunk_metadata
                )
                chunks.append(doc)
                current_chunk = []
        
        # Handle remaining sentences
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk_metadata = self._analyze_chunk_content(chunk_text, metadata)
            doc = Document(
                page_content=chunk_text,
                metadata=chunk_metadata
            )
            chunks.append(doc)
        
        return chunks
    
    def _section_chunking(self, text: str, metadata: Dict) -> List[Document]:
        """Section-based chunking"""
        sections = self._identify_sections(text)
        chunks = []
        
        for section_title, section_text in sections:
            if len(section_text.strip()) < 50:
                continue
            
            chunk_metadata = self._analyze_chunk_content(section_text, metadata)
            chunk_metadata.update({
                "chunk_type": "section",
                "source_section": section_title,
                "section_title": section_title
            })
            
            doc = Document(
                page_content=section_text,
                metadata=chunk_metadata
            )
            chunks.append(doc)
        
        return chunks
    
    def _identify_sections(self, text: str) -> List[Tuple[str, str]]:
        """Identify document sections"""
        # Look for common section patterns
        section_patterns = [
            r'^(\d+\.?\s+[A-Z][^.\n]*)\n',  # Numbered sections
            r'^([A-Z][A-Z\s]{2,})\n',       # ALL CAPS headers
            r'^([A-Z][^.\n]*:)\n',          # Colon-ended headers
            r'^\*\*([^*]+)\*\*\n',          # Bold headers
            r'^#{1,6}\s+([^\n]+)\n'         # Markdown headers
        ]
        
        sections = []
        current_section = "Introduction"
        current_text = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                current_text.append('')
                continue
            
            # Check if line is a section header
            is_header = False
            for pattern in section_patterns:
                match = re.match(pattern, line)
                if match:
                    # Save previous section
                    if current_text:
                        section_content = '\n'.join(current_text).strip()
                        if section_content:
                            sections.append((current_section, section_content))
                    
                    # Start new section
                    current_section = match.group(1).strip()
                    current_text = []
                    is_header = True
                    break
            
            if not is_header:
                current_text.append(line)
        
        # Add final section
        if current_text:
            section_content = '\n'.join(current_text).strip()
            if section_content:
                sections.append((current_section, section_content))
        
        # If no sections found, return entire text
        if not sections:
            sections = [("Document", text)]
        
        return sections
    
    def _chunk_section(self, section_text: str, section_title: str, metadata: Dict) -> List[Document]:
        """Chunk a document section"""
        if len(section_text) <= 1000:
            # Section is small enough, keep as single chunk
            chunk_metadata = self._analyze_chunk_content(section_text, metadata)
            chunk_metadata.update({
                "chunk_type": "section",
                "source_section": section_title
            })
            
            return [Document(page_content=section_text, metadata=chunk_metadata)]
        else:
            # Section is large, split further
            sub_chunks = self._recursive_chunking(section_text, metadata)
            
            # Update metadata to include section info
            for chunk in sub_chunks:
                chunk.metadata.update({
                    "source_section": section_title,
                    "parent_section": section_title
                })
            
            return sub_chunks
    
    def _is_good_break_point(self, sentence) -> bool:
        """Determine if sentence is a good place to break chunk"""
        if not self.nlp:
            return True
        
        # Check for transition words/phrases
        transition_words = {
            'however', 'therefore', 'furthermore', 'moreover', 'additionally',
            'consequently', 'meanwhile', 'subsequently', 'nevertheless'
        }
        
        sentence_text = sentence.text.lower()
        
        # Good break points
        if any(word in sentence_text for word in transition_words):
            return True
        
        # Check if sentence ends a paragraph (followed by newline)
        if sentence.text.endswith('\n'):
            return True
        
        # Check sentence length (longer sentences are better break points)
        if len(sentence.text.split()) > 15:
            return True
        
        return False
    
    def _analyze_chunk_content(self, chunk_text: str, base_metadata: Dict) -> Dict:
        """Analyze chunk content and extract metadata"""
        chunk_text_lower = chunk_text.lower()
        words = chunk_text.split()
        
        metadata = base_metadata.copy()
        metadata.update({
            "word_count": len(words),
            "sentence_count": len(re.findall(r'[.!?]+', chunk_text)),
            "character_count": len(chunk_text),
            "has_technical_terms": any(term in chunk_text_lower for term in self.technical_terms),
            "has_requirements": any(term in chunk_text_lower for term in self.requirement_indicators),
            "has_compliance_terms": any(term in chunk_text_lower for term in self.compliance_terms),
            "chunk_id": f"chunk_{hash(chunk_text) % 1000000}",
            "chunking_strategy": "semantic"
        })
        
        # Analyze content type
        if any(word in chunk_text_lower for word in ['table', 'column', 'row']):
            metadata["content_type"] = "table"
        elif any(word in chunk_text_lower for word in ['list', 'item', 'bullet']):
            metadata["content_type"] = "list"
        elif any(word in chunk_text_lower for word in ['figure', 'image', 'diagram']):
            metadata["content_type"] = "figure"
        else:
            metadata["content_type"] = "text"
        
        # Calculate importance score
        importance_score = 0
        if metadata["has_requirements"]:
            importance_score += 3
        if metadata["has_compliance_terms"]:
            importance_score += 2
        if metadata["has_technical_terms"]:
            importance_score += 1
        
        metadata["importance_score"] = importance_score
        
        return metadata
    
    def _add_chunk_relationships(self, chunks: List[Document]) -> List[Document]:
        """Add hierarchical relationships between chunks"""
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
            
            # Add previous/next chunk references
            if i > 0:
                chunk.metadata["previous_chunk_id"] = chunks[i-1].metadata.get("chunk_id")
            if i < len(chunks) - 1:
                chunk.metadata["next_chunk_id"] = chunks[i+1].metadata.get("chunk_id")
        
        return chunks

class AdaptiveChunker:
    """Adaptive chunking based on document type and content"""
    
    def __init__(self):
        self.semantic_chunker = SemanticChunker()
        
        # Document type patterns
        self.doc_type_patterns = {
            "rfp": ["request for proposal", "rfp", "solicitation", "procurement"],
            "technical_spec": ["specification", "requirements", "technical", "architecture"],
            "contract": ["contract", "agreement", "terms", "conditions"],
            "proposal": ["proposal", "response", "solution", "approach"],
            "manual": ["manual", "guide", "instructions", "procedures"]
        }
    
    def chunk_document(self, text: str, metadata: Dict = None) -> List[Document]:
        """Adaptively chunk document based on detected type"""
        metadata = metadata or {}
        
        # Detect document type
        doc_type = self._detect_document_type(text)
        metadata["detected_document_type"] = doc_type
        
        # Choose chunking strategy based on document type
        if doc_type == "rfp":
            strategy = "section"  # RFPs usually have clear sections
        elif doc_type == "technical_spec":
            strategy = "hybrid"   # Technical specs need semantic understanding
        elif doc_type == "contract":
            strategy = "sentence" # Contracts need precise chunking
        else:
            strategy = "hybrid"   # Default to hybrid approach
        
        logger.info("Adaptive chunking", 
                   document_type=doc_type, 
                   strategy=strategy)
        
        return self.semantic_chunker.chunk_document(text, metadata, strategy)
    
    def _detect_document_type(self, text: str) -> str:
        """Detect document type based on content"""
        text_lower = text.lower()
        
        type_scores = {}
        for doc_type, keywords in self.doc_type_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            type_scores[doc_type] = score
        
        # Return type with highest score, or "unknown" if no matches
        if type_scores and max(type_scores.values()) > 0:
            return max(type_scores, key=type_scores.get)
        
        return "unknown"

# Global chunker instance
adaptive_chunker = AdaptiveChunker()