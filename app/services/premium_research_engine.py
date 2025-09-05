from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime
from app.agents.agent_orchestrator import AgentOrchestrator
from app.scrapers.supreme_court_scraper import SupremeCourtScraper
from app.scrapers.nclt_nclat_scraper import NCLTNCLATScraper
from app.services.parser import document_parser
from app.services.storage import storage_service
from app.db.base import SessionLocal
from app.db.models import Document, Summary
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class PremiumResearchEngine:
    """
    Ultimate legal research engine combining multi-agent AI analysis 
    with comprehensive data ingestion and quality assurance.
    """
    
    def __init__(self):
        self.agent_orchestrator = AgentOrchestrator()
        self.sc_scraper = SupremeCourtScraper()
        self.nclt_scraper = NCLTNCLATScraper()
        
        # Research engine configurations
        self.research_modes = {
            "comprehensive": {
                "agents": ["legal_analyst", "cs_expert", "quality_reviewer"],
                "depth": "maximum",
                "quality_threshold": 0.95
            },
            "cs_focused": {
                "agents": ["cs_expert", "legal_analyst", "quality_reviewer"], 
                "depth": "high",
                "quality_threshold": 0.90
            },
            "legal_precedent": {
                "agents": ["legal_analyst", "quality_reviewer"],
                "depth": "high",
                "quality_threshold": 0.90
            },
            "compliance_advisory": {
                "agents": ["cs_expert", "quality_reviewer"],
                "depth": "practical",
                "quality_threshold": 0.85
            }
        }
    
    async def process_research_request(
        self,
        user_query: str,
        research_mode: str = "comprehensive",
        include_recent_updates: bool = True,
        max_documents: int = 10
    ) -> Dict[str, Any]:
        """
        Process a premium research request from CS professionals.
        Returns comprehensive, multi-perspective analysis.
        """
        
        logger.info(f"Processing premium research request: {user_query}")
        
        research_session = {
            "session_id": self._generate_session_id(),
            "query": user_query,
            "mode": research_mode,
            "timestamp": datetime.now().isoformat(),
            "status": "processing"
        }
        
        try:
            # Step 1: Intelligent document discovery and retrieval
            relevant_documents = await self._discover_relevant_documents(
                user_query, max_documents, include_recent_updates
            )
            
            research_session["documents_found"] = len(relevant_documents)
            
            # Step 2: Multi-agent analysis of each document
            document_analyses = []
            
            for doc in relevant_documents[:max_documents]:
                try:
                    # Get document text
                    document_text = await self._get_document_text(doc)
                    
                    if document_text:
                        # Multi-agent analysis
                        analysis = await self.agent_orchestrator.analyze_document(
                            document_text=document_text,
                            user_query=user_query,
                            workflow_type=research_mode,
                            context={"document_metadata": doc}
                        )
                        
                        analysis["source_document"] = {
                            "title": doc.get("title", "Unknown"),
                            "court": doc.get("court", "Unknown"),
                            "url": doc.get("url"),
                            "relevance_score": doc.get("relevance_score", 0)
                        }
                        
                        document_analyses.append(analysis)
                    
                except Exception as e:
                    logger.error(f"Error analyzing document {doc.get('url')}: {e}")
                    continue
            
            # Step 3: Cross-document synthesis and insights
            synthesized_insights = await self._synthesize_cross_document_insights(
                document_analyses, user_query
            )
            
            # Step 4: Generate premium research output
            premium_output = await self._generate_premium_output(
                user_query=user_query,
                document_analyses=document_analyses,
                synthesized_insights=synthesized_insights,
                research_mode=research_mode
            )
            
            research_session.update({
                "status": "completed",
                "documents_analyzed": len(document_analyses),
                "quality_score": premium_output.get("overall_quality_score", 0),
                "completion_time": datetime.now().isoformat()
            })
            
            return {
                "research_session": research_session,
                "premium_analysis": premium_output,
                "supporting_documents": document_analyses[:5],  # Top 5 for reference
                "research_methodology": self._get_methodology_summary(research_mode)
            }
            
        except Exception as e:
            logger.error(f"Error in premium research request: {e}")
            research_session.update({
                "status": "error",
                "error": str(e)
            })
            return research_session
    
    async def _discover_relevant_documents(
        self, 
        query: str, 
        max_docs: int,
        include_recent: bool
    ) -> List[Dict]:
        """Intelligent document discovery using multiple sources"""
        
        logger.info("Discovering relevant documents")
        
        relevant_docs = []
        
        # Search existing database first
        db = SessionLocal()
        try:
            # Search in existing documents
            db_docs = await self._search_existing_documents(db, query, max_docs // 2)
            relevant_docs.extend(db_docs)
        finally:
            db.close()
        
        # If we need more documents or recent updates, scrape fresh content
        if len(relevant_docs) < max_docs or include_recent:
            remaining_needed = max_docs - len(relevant_docs)
            
            try:
                # Scrape Supreme Court
                async with self.sc_scraper as scraper:
                    sc_docs = await scraper.scrape_recent_judgments(days_back=30)
                    # Filter for query relevance
                    relevant_sc = await self._filter_by_query_relevance(sc_docs, query)
                    relevant_docs.extend(relevant_sc[:remaining_needed // 2])
                
                # Scrape NCLT/NCLAT
                async with self.nclt_scraper as scraper:
                    tribunal_docs = await scraper.scrape_recent_orders(days_back=15)
                    relevant_tribunal = await self._filter_by_query_relevance(tribunal_docs, query)
                    relevant_docs.extend(relevant_tribunal[:remaining_needed // 2])
                    
            except Exception as e:
                logger.error(f"Error in document discovery: {e}")
        
        # Rank and return top documents
        ranked_docs = await self._rank_documents_by_relevance(relevant_docs, query)
        
        logger.info(f"Found {len(ranked_docs)} relevant documents")
        return ranked_docs[:max_docs]
    
    async def _search_existing_documents(
        self, 
        db: Session, 
        query: str, 
        limit: int
    ) -> List[Dict]:
        """Search existing documents in database"""
        
        # Simple text search in database
        documents = db.query(Document).filter(
            Document.raw_text.ilike(f"%{query}%")
        ).limit(limit).all()
        
        return [
            {
                "document_id": str(doc.document_id),
                "title": doc.title,
                "court": doc.court,
                "url": doc.url,
                "decision_date": doc.decision_date.isoformat() if doc.decision_date else None,
                "source": "database",
                "raw_text": doc.raw_text
            }
            for doc in documents
        ]
    
    async def _filter_by_query_relevance(
        self, 
        documents: List[Dict], 
        query: str
    ) -> List[Dict]:
        """Filter documents by relevance to user query"""
        
        query_words = set(query.lower().split())
        relevant_docs = []
        
        for doc in documents:
            # Calculate relevance score
            title_text = doc.get("title", "").lower()
            context_text = doc.get("context", "").lower()
            combined_text = f"{title_text} {context_text}"
            
            # Count matching words
            doc_words = set(combined_text.split())
            matching_words = query_words.intersection(doc_words)
            relevance_score = len(matching_words) / len(query_words) if query_words else 0
            
            # Boost score for exact phrase matches
            if query.lower() in combined_text:
                relevance_score += 0.5
            
            # Include if relevance is above threshold
            if relevance_score > 0.2:  # 20% word match minimum
                doc["query_relevance_score"] = relevance_score
                relevant_docs.append(doc)
        
        return relevant_docs
    
    async def _rank_documents_by_relevance(
        self, 
        documents: List[Dict], 
        query: str
    ) -> List[Dict]:
        """Rank documents by combined relevance and quality scores"""
        
        def calculate_combined_score(doc):
            relevance = doc.get("query_relevance_score", doc.get("relevance_score", 0))
            priority = doc.get("priority_score", 0) / 100  # Normalize to 0-1
            recency = self._calculate_recency_score(doc)
            
            # Weighted combination
            return (relevance * 0.5) + (priority * 0.3) + (recency * 0.2)
        
        # Sort by combined score
        ranked = sorted(documents, key=calculate_combined_score, reverse=True)
        
        return ranked
    
    def _calculate_recency_score(self, doc: Dict) -> float:
        """Calculate recency score (0-1) based on document date"""
        
        try:
            if "decision_date" in doc and doc["decision_date"]:
                doc_date = datetime.fromisoformat(doc["decision_date"])
                days_old = (datetime.now() - doc_date).days
                
                # Score decreases with age
                if days_old <= 30:
                    return 1.0
                elif days_old <= 90:
                    return 0.8
                elif days_old <= 365:
                    return 0.5
                elif days_old <= 1095:  # 3 years
                    return 0.3
                else:
                    return 0.1
            else:
                return 0.1  # Default for documents without dates
                
        except Exception:
            return 0.1
    
    async def _get_document_text(self, doc: Dict) -> Optional[str]:
        """Get full text content of a document"""
        
        # If it's from database, text is already available
        if doc.get("source") == "database" and "raw_text" in doc:
            return doc["raw_text"]
        
        # If it's a scraped document, need to fetch and parse
        if "url" in doc and doc["url"]:
            try:
                # Try to fetch PDF content
                if "pdf" in doc["url"].lower():
                    # Use appropriate scraper to fetch
                    if "supremecourt" in doc["url"].lower():
                        async with self.sc_scraper as scraper:
                            result = await scraper.fetch_with_retry(doc["url"])
                            if result:
                                _, content = result
                                text, _ = document_parser.extract_text_from_pdf(content)
                                return text
                    
                    elif "nclt" in doc["url"].lower() or "nclat" in doc["url"].lower():
                        async with self.nclt_scraper as scraper:
                            result = await scraper.fetch_with_retry(doc["url"])
                            if result:
                                _, content = result
                                text, _ = document_parser.extract_text_from_pdf(content)
                                return text
                
            except Exception as e:
                logger.error(f"Error fetching document text: {e}")
        
        # Fallback to any existing text in the document
        return doc.get("context", doc.get("title", ""))
    
    async def _synthesize_cross_document_insights(
        self, 
        document_analyses: List[Dict], 
        user_query: str
    ) -> Dict[str, Any]:
        """Synthesize insights across multiple document analyses"""
        
        synthesis = {
            "common_themes": [],
            "contradictions": [],
            "emerging_trends": [],
            "consensus_principles": [],
            "jurisdictional_variations": []
        }
        
        if not document_analyses:
            return synthesis
        
        # Extract insights from all analyses
        all_legal_issues = []
        all_compliance_requirements = []
        all_court_reasonings = []
        
        for analysis in document_analyses:
            if "agent_analyses" in analysis:
                # Legal analyst insights
                if "legal_analyst" in analysis["agent_analyses"]:
                    legal_data = analysis["agent_analyses"]["legal_analyst"]
                    if "legal_issues" in legal_data:
                        all_legal_issues.extend(legal_data["legal_issues"])
                    if "court_reasoning" in legal_data:
                        all_court_reasonings.append(legal_data["court_reasoning"])
                
                # CS expert insights
                if "cs_expert" in analysis["agent_analyses"]:
                    cs_data = analysis["agent_analyses"]["cs_expert"]
                    if "compliance_implications" in cs_data:
                        compliance = cs_data["compliance_implications"]
                        if isinstance(compliance, dict):
                            for req_list in compliance.values():
                                if isinstance(req_list, list):
                                    all_compliance_requirements.extend(req_list)
        
        # Find common themes
        from collections import Counter
        
        # Count frequency of similar legal issues
        issue_counter = Counter(all_legal_issues)
        synthesis["common_themes"] = [
            {"theme": issue, "frequency": count}
            for issue, count in issue_counter.most_common(5)
            if count > 1
        ]
        
        # Count compliance requirements
        compliance_counter = Counter(all_compliance_requirements)
        synthesis["consensus_principles"] = [
            {"principle": req, "frequency": count}
            for req, count in compliance_counter.most_common(5)
            if count > 1
        ]
        
        return synthesis
    
    async def _generate_premium_output(
        self,
        user_query: str,
        document_analyses: List[Dict],
        synthesized_insights: Dict,
        research_mode: str
    ) -> Dict[str, Any]:
        """Generate the final premium research output"""
        
        output = {
            "executive_summary": "",
            "key_findings": [],
            "legal_analysis": {},
            "compliance_guidance": {},
            "practical_recommendations": [],
            "supporting_evidence": [],
            "quality_indicators": {},
            "research_confidence": 0.0,
            "overall_quality_score": 0.0
        }
        
        if not document_analyses:
            return output
        
        # Build executive summary
        exec_summary_parts = []
        if synthesized_insights["common_themes"]:
            themes = [t["theme"] for t in synthesized_insights["common_themes"][:3]]
            exec_summary_parts.append(f"Key legal themes: {'; '.join(themes)}")
        
        output["executive_summary"] = " | ".join(exec_summary_parts) or "Comprehensive analysis completed."
        
        # Aggregate key findings from all analyses
        for analysis in document_analyses:
            if "consolidated_insights" in analysis:
                insights = analysis["consolidated_insights"]
                if "key_legal_issues" in insights:
                    output["key_findings"].extend(insights["key_legal_issues"])
        
        # Remove duplicates and limit
        output["key_findings"] = list(set(output["key_findings"]))[:10]
        
        # Calculate quality scores
        quality_scores = []
        for analysis in document_analyses:
            if "quality_assessment" in analysis:
                if "overall_quality_score" in analysis["quality_assessment"]:
                    quality_scores.append(analysis["quality_assessment"]["overall_quality_score"])
        
        if quality_scores:
            output["overall_quality_score"] = sum(quality_scores) / len(quality_scores)
            output["research_confidence"] = min(quality_scores)  # Conservative confidence
        
        # Add quality indicators
        output["quality_indicators"] = {
            "documents_analyzed": len(document_analyses),
            "avg_quality_score": output["overall_quality_score"],
            "research_depth": research_mode,
            "cross_document_synthesis": bool(synthesized_insights["common_themes"])
        }
        
        return output
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID for research requests"""
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _get_methodology_summary(self, research_mode: str) -> Dict[str, Any]:
        """Get summary of research methodology used"""
        
        mode_config = self.research_modes.get(research_mode, {})
        
        return {
            "research_mode": research_mode,
            "agents_used": mode_config.get("agents", []),
            "analysis_depth": mode_config.get("depth", "standard"),
            "quality_threshold": mode_config.get("quality_threshold", 0.85),
            "methodology": "Multi-agent AI analysis with cross-document synthesis and quality assurance"
        }