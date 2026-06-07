# app/modules/knowledge_base/retrieval/query_processor.py
from typing import List, Dict, Any, Optional, Set
import re
from dataclasses import dataclass
import structlog
from app.core.llm_provider import llm_manager

logger = structlog.get_logger()

@dataclass
class ProcessedQuery:
    """Processed query with enhancements"""
    original_query: str
    cleaned_query: str
    expanded_queries: List[str]
    extracted_entities: Dict[str, List[str]]
    query_intent: str
    query_type: str
    expanded_terms: List[str]
    synonyms: Dict[str, List[str]]
    filters_suggested: Dict[str, Any]

class QueryProcessor:
    """Intelligent query processing and enhancement"""
    
    def __init__(self):
        # Domain-specific synonyms and expansions
        self.domain_synonyms = {
            # Technical terms
            "software": ["application", "system", "platform", "solution"],
            "hardware": ["equipment", "device", "infrastructure", "machinery"],
            "security": ["cybersecurity", "protection", "safety", "compliance"],
            "integration": ["connection", "interface", "linking", "interoperability"],
            
            # Business terms
            "requirement": ["specification", "need", "criteria", "demand"],
            "proposal": ["bid", "offer", "submission", "response"],
            "budget": ["cost", "price", "funding", "investment"],
            "timeline": ["schedule", "deadline", "timeframe", "duration"],
            
            # Compliance terms
            "gdpr": ["general data protection regulation", "data protection", "privacy regulation"],
            "iso27001": ["iso 27001", "information security management", "security standard"],
            "soc2": ["soc 2", "service organization control", "audit standard"],
            
            # Product terms
            "feature": ["capability", "function", "functionality", "characteristic"],
            "specification": ["spec", "requirement", "parameter", "detail"],
            "performance": ["efficiency", "speed", "throughput", "capacity"]
        }
        
        # Query intent patterns
        self.intent_patterns = {
            "search": ["find", "search", "look for", "locate", "discover"],
            "compare": ["compare", "versus", "vs", "difference", "contrast"],
            "explain": ["explain", "describe", "what is", "how does", "define"],
            "list": ["list", "show", "enumerate", "display", "provide"],
            "recommend": ["recommend", "suggest", "advise", "propose", "best"]
        }
        
        # Query type patterns
        self.type_patterns = {
            "product_search": ["product", "solution", "tool", "software", "hardware"],
            "compliance_query": ["compliance", "regulation", "standard", "audit", "certification"],
            "technical_query": ["technical", "architecture", "implementation", "integration"],
            "pricing_query": ["price", "cost", "budget", "pricing", "rate", "fee"],
            "case_study_query": ["case study", "example", "success story", "implementation"]
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            "technology": r'\b(?:API|REST|SOAP|JSON|XML|HTTP|HTTPS|SQL|NoSQL|AI|ML|IoT|SaaS|PaaS|IaaS)\b',
            "standard": r'\b(?:ISO\s*\d+|SOC\s*\d|GDPR|HIPAA|PCI|NIST)\b',
            "number": r'\b\d+(?:\.\d+)?\s*(?:GB|TB|MB|KB|users?|months?|years?|days?|%)\b',
            "currency": r'\$\s*\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+\s*(?:USD|EUR|GBP)\b'
        }
        
        logger.info("Query Processor initialized")
    
    async def process_query(self, 
                          query: str, 
                          expand: bool = True,
                          context: Dict[str, Any] = None) -> ProcessedQuery:
        """Process and enhance a search query"""
        try:
            logger.info("Processing query", query=query[:100], expand=expand)
            
            # Step 1: Clean the query
            cleaned_query = self._clean_query(query)
            
            # Step 2: Extract entities
            entities = self._extract_entities(cleaned_query)
            
            # Step 3: Determine query intent and type
            intent = self._determine_intent(cleaned_query)
            query_type = self._determine_type(cleaned_query)
            
            # Step 4: Generate synonyms and expanded terms
            synonyms = self._generate_synonyms(cleaned_query)
            expanded_terms = self._extract_expandable_terms(cleaned_query, synonyms)
            
            # Step 5: Generate expanded queries if enabled
            expanded_queries = []
            if expand:
                expanded_queries = await self._generate_expanded_queries(
                    cleaned_query, 
                    synonyms, 
                    entities,
                    context
                )
            
            # Step 6: Suggest filters based on query content
            suggested_filters = self._suggest_filters(cleaned_query, entities, query_type)
            
            result = ProcessedQuery(
                original_query=query,
                cleaned_query=cleaned_query,
                expanded_queries=expanded_queries,
                extracted_entities=entities,
                query_intent=intent,
                query_type=query_type,
                expanded_terms=expanded_terms,
                synonyms=synonyms,
                filters_suggested=suggested_filters
            )
            
            logger.info("Query processing completed", 
                       intent=intent,
                       query_type=query_type,
                       expanded_count=len(expanded_queries),
                       entities_count=sum(len(v) for v in entities.values()))
            
            return result
            
        except Exception as e:
            logger.error("Query processing failed", query=query[:50], error=str(e))
            # Return basic processed query on failure
            return ProcessedQuery(
                original_query=query,
                cleaned_query=query.strip(),
                expanded_queries=[],
                extracted_entities={},
                query_intent="search",
                query_type="general",
                expanded_terms=[],
                synonyms={},
                filters_suggested={}
            )
    
    def _clean_query(self, query: str) -> str:
        """Clean and normalize the query"""
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', query.strip())
        
        # Remove special characters that might interfere with search
        cleaned = re.sub(r'[^\w\s\-\.\,\?\!]', ' ', cleaned)
        
        # Normalize case for certain terms
        cleaned = re.sub(r'\bAPI\b', 'API', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bREST\b', 'REST', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bSOAP\b', 'SOAP', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def _extract_entities(self, query: str) -> Dict[str, List[str]]:
        """Extract named entities from the query"""
        entities = {}
        
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                entities[entity_type] = list(set(matches))  # Remove duplicates
        
        # Extract potential product names (capitalized words/phrases)
        product_pattern = r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\b'
        products = re.findall(product_pattern, query)
        if products:
            # Filter out common words
            common_words = {'API', 'REST', 'SOAP', 'HTTP', 'HTTPS', 'SQL', 'JSON', 'XML'}
            filtered_products = [p for p in products if p not in common_words and len(p) > 2]
            if filtered_products:
                entities['product'] = filtered_products
        
        return entities
    
    def _determine_intent(self, query: str) -> str:
        """Determine the intent of the query"""
        query_lower = query.lower()
        
        for intent, keywords in self.intent_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                return intent
        
        # Default intent based on query structure
        if '?' in query:
            return "explain"
        elif any(word in query_lower for word in ["best", "top", "recommend"]):
            return "recommend"
        else:
            return "search"
    
    def _determine_type(self, query: str) -> str:
        """Determine the type/domain of the query"""
        query_lower = query.lower()
        
        # Score each type based on keyword matches
        type_scores = {}
        
        for query_type, keywords in self.type_patterns.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                type_scores[query_type] = score
        
        # Return the type with the highest score
        if type_scores:
            return max(type_scores, key=type_scores.get)
        
        return "general"
    
    def _generate_synonyms(self, query: str) -> Dict[str, List[str]]:
        """Generate synonyms for terms in the query"""
        query_lower = query.lower()
        found_synonyms = {}
        
        for term, synonyms in self.domain_synonyms.items():
            if term in query_lower:
                found_synonyms[term] = synonyms
        
        return found_synonyms
    
    def _extract_expandable_terms(self, 
                                query: str, 
                                synonyms: Dict[str, List[str]]) -> List[str]:
        """Extract terms that can be expanded with synonyms"""
        expandable_terms = []
        
        # Add original terms that have synonyms
        expandable_terms.extend(synonyms.keys())
        
        # Add all synonym terms
        for synonym_list in synonyms.values():
            expandable_terms.extend(synonym_list)
        
        return list(set(expandable_terms))
    
    async def _generate_expanded_queries(self, 
                                       query: str,
                                       synonyms: Dict[str, List[str]],
                                       entities: Dict[str, List[str]],
                                       context: Dict[str, Any] = None) -> List[str]:
        """Generate expanded versions of the query"""
        expanded_queries = []
        
        try:
            # Method 1: Synonym-based expansion
            synonym_expansions = self._create_synonym_expansions(query, synonyms)
            expanded_queries.extend(synonym_expansions)
            
            # Method 2: Entity-based expansion
            entity_expansions = self._create_entity_expansions(query, entities)
            expanded_queries.extend(entity_expansions)
            
            # Method 3: LLM-based expansion (if available)
            llm_expansions = await self._create_llm_expansions(query, context)
            expanded_queries.extend(llm_expansions)
            
            # Remove duplicates and limit number of expansions
            unique_expansions = list(set(expanded_queries))
            
            # Filter out expansions that are too similar to original
            filtered_expansions = []
            for expansion in unique_expansions:
                if self._calculate_similarity(query, expansion) < 0.9:  # Not too similar
                    filtered_expansions.append(expansion)
            
            return filtered_expansions[:5]  # Limit to top 5 expansions
            
        except Exception as e:
            logger.warning("Query expansion failed", error=str(e))
            return []
    
    def _create_synonym_expansions(self, 
                                 query: str, 
                                 synonyms: Dict[str, List[str]]) -> List[str]:
        """Create query expansions using synonyms"""
        expansions = []
        
        for original_term, synonym_list in synonyms.items():
            for synonym in synonym_list[:2]:  # Limit to 2 synonyms per term
                expanded_query = query.replace(original_term, synonym)
                if expanded_query != query:
                    expansions.append(expanded_query)
        
        return expansions
    
    def _create_entity_expansions(self, 
                                query: str, 
                                entities: Dict[str, List[str]]) -> List[str]:
        """Create query expansions based on extracted entities"""
        expansions = []
        
        # Add more specific queries based on entities
        if 'technology' in entities:
            for tech in entities['technology'][:2]:
                expansions.append(f"{query} {tech} implementation")
                expansions.append(f"{tech} integration {query}")
        
        if 'standard' in entities:
            for standard in entities['standard'][:2]:
                expansions.append(f"{query} {standard} compliance")
        
        return expansions
    
    async def _create_llm_expansions(self, 
                                   query: str, 
                                   context: Dict[str, Any] = None) -> List[str]:
        """Create query expansions using LLM"""
        try:
            # Create prompt for query expansion
            prompt = f"""
            Given the search query: "{query}"
            
            Generate 3 alternative ways to express the same search intent using different terminology.
            Focus on:
            1. Technical synonyms and industry terms
            2. Different phrasings of the same concept
            3. More specific or more general versions
            
            Return only the alternative queries, one per line.
            """
            
            response = await llm_manager.generate_with_cache(
                prompt, 
                cache_key=f"query_expansion_{hash(query)}"
            )
            
            # Parse response into individual queries
            expansions = []
            for line in response.strip().split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and len(line) > 10:
                    # Remove numbering or bullet points
                    cleaned_line = re.sub(r'^\d+\.\s*', '', line)
                    cleaned_line = re.sub(r'^[-*]\s*', '', cleaned_line)
                    expansions.append(cleaned_line.strip())
            
            return expansions[:3]  # Limit to 3 LLM expansions
            
        except Exception as e:
            logger.warning("LLM query expansion failed", error=str(e))
            return []
    
    def _suggest_filters(self, 
                       query: str, 
                       entities: Dict[str, List[str]],
                       query_type: str) -> Dict[str, Any]:
        """Suggest filters based on query content"""
        filters = {}
        
        # Document type filters based on query type
        if query_type == "product_search":
            filters["document_type"] = ["product_catalog", "technical_spec"]
        elif query_type == "compliance_query":
            filters["document_type"] = ["compliance_document", "certification"]
        elif query_type == "pricing_query":
            filters["document_type"] = ["pricing_sheet", "proposal"]
        elif query_type == "case_study_query":
            filters["document_type"] = ["case_study", "proposal"]
        
        # Importance filter for high-value queries
        important_keywords = ["critical", "important", "essential", "required", "mandatory"]
        if any(keyword in query.lower() for keyword in important_keywords):
            filters["importance_score"] = {"min": 0.7}
        
        # Recency filter for time-sensitive queries
        time_keywords = ["recent", "latest", "new", "current", "updated"]
        if any(keyword in query.lower() for keyword in time_keywords):
            filters["created_at"] = {"min": "2023-01-01"}  # Last year
        
        return filters
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple similarity between two texts"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    async def expand_query_with_context(self, 
                                      query: str,
                                      conversation_history: List[str] = None,
                                      user_preferences: Dict[str, Any] = None) -> ProcessedQuery:
        """Expand query using conversation context and user preferences"""
        try:
            context = {}
            
            # Add conversation history to context
            if conversation_history:
                context["conversation_history"] = conversation_history[-5:]  # Last 5 messages
            
            # Add user preferences
            if user_preferences:
                context["user_preferences"] = user_preferences
            
            return await self.process_query(query, expand=True, context=context)
            
        except Exception as e:
            logger.error("Context-aware query expansion failed", error=str(e))
            return await self.process_query(query, expand=False)
    
    def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """Analyze query complexity and characteristics"""
        analysis = {
            "word_count": len(query.split()),
            "character_count": len(query),
            "has_questions": "?" in query,
            "has_boolean_operators": any(op in query.upper() for op in ["AND", "OR", "NOT"]),
            "has_quotes": '"' in query,
            "has_wildcards": any(char in query for char in ["*", "?"]),
            "complexity_score": 0.0
        }
        
        # Calculate complexity score
        complexity = 0.0
        
        # Length complexity
        if analysis["word_count"] > 10:
            complexity += 0.3
        elif analysis["word_count"] > 5:
            complexity += 0.1
        
        # Structure complexity
        if analysis["has_boolean_operators"]:
            complexity += 0.3
        if analysis["has_quotes"]:
            complexity += 0.2
        if analysis["has_wildcards"]:
            complexity += 0.2
        
        # Entity complexity
        entities = self._extract_entities(query)
        if len(entities) > 2:
            complexity += 0.2
        
        analysis["complexity_score"] = min(1.0, complexity)
        
        return analysis