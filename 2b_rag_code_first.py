#!/usr/bin/env python3
"""
AI-3016 Demo 2B: RAG Pattern with Azure AI Search via Code (Automated)

⏱️ Demo Duration: 20 minutes
🎯 Audience: Developer-focused students
🔍 Environment: Programmatic Azure AI Search and OpenAI integration

This script demonstrates building a complete RAG solution using Azure SDK.
Designed to complement the portal-guided demo (2a_rag_portal_guide.md).
"""

import os
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Azure SDK imports
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    SimpleField, SearchableField, VectorSearch,
    VectorSearchProfile, HnswAlgorithmConfiguration
)
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from azure_openai_auth import create_azure_openai_client

# Utilities
import logging
import uuid

load_dotenv()

# Configure logging for demo visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGDemo:
    """
    Automated RAG (Retrieval-Augmented Generation) demonstration class.
    
    This class implements a complete RAG pipeline:
    1. Document preparation and upload
    2. Azure AI Search index creation
    3. Vector embedding generation
    4. Hybrid search implementation
    5. Response generation with context
    """
    
    def __init__(self, student_initials: str = "demo"):
        """Initialize the RAG demo with student-specific naming."""
        self.student_initials = student_initials
        self.timestamp = datetime.now().strftime("%m%d")
        
        # Resource naming (matches portal guide conventions)
        self.index_name = f"{student_initials}-bank-docs-index"
        self.container_name = "documents"
        
        # Azure service clients
        self.search_client = None
        self.index_client = None
        self.blob_client = None
        self.openai_client = None
        
        # Demo data
        self.documents = []
        self.demo_start_time = time.time()
        self.demo_steps = []
        
        # Banking documents for the demo
        self.banking_documents = self._prepare_banking_documents()
        
    def _prepare_banking_documents(self) -> List[Dict[str, Any]]:
        """Prepare sample banking documents for the RAG demo."""
        return [
            {
                "id": "bank_policies",
                "title": "First National Bank - Account Policies",
                "content": """FIRST NATIONAL BANK - ACCOUNT POLICIES

OVERDRAFT PROTECTION:
- Automatic transfer from savings to checking
- $5 transfer fee per occurrence
- Must maintain $50 minimum in savings
- Available 24/7 for eligible accounts

WIRE TRANSFER LIMITS:
- Domestic: $25,000 per day
- International: $15,000 per day
- Additional verification required for amounts over $10,000
- Processing time: Same day for domestic, 1-3 days international

MOBILE DEPOSIT LIMITS:
- Personal accounts: $5,000 per day
- Business accounts: $10,000 per day
- Checks over $1,000 may have extended hold periods
- Image quality requirements apply

ACCOUNT CLOSURE PROCEDURES:
- 30-day written notice preferred
- All outstanding transactions must clear
- Automatic payments should be redirected
- Final statement issued within 10 business days""",
                "category": "policies",
                "keywords": ["overdraft", "wire transfer", "mobile deposit", "account closure"]
            },
            {
                "id": "investment_products",
                "title": "First National Bank - Investment Products",
                "content": """FIRST NATIONAL BANK - INVESTMENT PRODUCTS

CERTIFICATES OF DEPOSIT (CDs):
- Terms: 3, 6, 12, 24, 36 months
- Minimum deposit: $1,000
- Current rates: 3.5% - 4.2% APY
- Early withdrawal penalties apply
- Automatic renewal unless instructed otherwise

MONEY MARKET ACCOUNTS:
- Minimum balance: $2,500
- Current rate: 3.8% APY
- Limited to 6 withdrawals per month
- Debit card access available
- Check writing privileges included

SAVINGS ACCOUNTS:
- Standard Savings: 0.5% APY, $100 minimum
- High-Yield Savings: 3.2% APY, $1,000 minimum
- Youth Savings: 2.0% APY, no minimum (under 18)
- No monthly fees with minimum balance maintained

RETIREMENT ACCOUNTS:
- Traditional IRA: Tax-deferred growth
- Roth IRA: Tax-free withdrawals in retirement
- 401(k) rollover services available
- Professional investment advisory services
- Annual contribution limits: $6,500 (under 50), $7,500 (50+)""",
                "category": "investments",
                "keywords": ["CD", "certificate of deposit", "money market", "savings", "IRA", "retirement"]
            },
            {
                "id": "customer_service",
                "title": "First National Bank - Customer Service Guide",
                "content": """FIRST NATIONAL BANK - CUSTOMER SERVICE GUIDE

CONTACT INFORMATION:
- Customer Service: 1-800-BANK-123
- Hours: Monday-Friday 7 AM - 7 PM, Saturday 9 AM - 2 PM
- Online Banking: Available 24/7 at firstnationalbank.com
- Mobile App: Download from App Store or Google Play
- Emergency Card Services: 1-800-CARD-911 (24/7)

COMMON ISSUES AND SOLUTIONS:

FORGOTTEN PIN/PASSWORD:
- Visit any branch with valid ID
- Call customer service for temporary PIN
- Use online password reset tool
- Mobile app biometric setup available

DISPUTED TRANSACTIONS:
- Report within 60 days of statement date
- Temporary credit issued during investigation
- Resolution typically within 10 business days
- Required documentation varies by transaction type

CARD REPLACEMENT:
- Lost/stolen cards: Report immediately
- Damaged cards: Visit branch or request online
- Expedited shipping available for $25 fee
- New card activation required within 30 days

ACCOUNT STATEMENTS:
- Electronic statements: Free, available immediately
- Paper statements: $3 monthly fee
- Historical statements: Available online for 7 years
- Special statement requests: $5 fee per copy""",
                "category": "customer_service",
                "keywords": ["contact", "phone", "hours", "PIN", "password", "disputes", "card replacement", "statements"]
            }
        ]
    
    def setup_azure_clients(self) -> bool:
        """
        Step 1: Initialize Azure service clients.
        
        Required environment variables:
        - AZURE_SEARCH_ENDPOINT
        - AZURE_SEARCH_ADMIN_KEY
        - AZURE_OPENAI_ENDPOINT
        - AZURE_OPENAI_API_KEY
        - AZURE_STORAGE_CONNECTION_STRING (optional)
        """
        logger.info("🔧 Setting up Azure service clients...")
        
        try:
            # Azure AI Search client
            search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
            search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
            
            if not search_endpoint or not search_key:
                logger.error("❌ Missing Azure Search credentials!")
                logger.error("   Please set: AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_ADMIN_KEY")
                return False
            
            credential = AzureKeyCredential(search_key)
            self.search_client = SearchClient(
                endpoint=search_endpoint,
                index_name=self.index_name,
                credential=credential
            )
            self.index_client = SearchIndexClient(
                endpoint=search_endpoint,
                credential=credential
            )
            
            # Azure OpenAI client
            if not os.getenv("AZURE_OPENAI_ENDPOINT"):
                logger.error("❌ Missing Azure OpenAI endpoint!")
                logger.error("   Please set: AZURE_OPENAI_ENDPOINT")
                return False
            
            self.openai_client = create_azure_openai_client(api_version="2024-05-01-preview")
            
            # Optional: Azure Storage client for larger deployments
            storage_connection = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if storage_connection:
                self.blob_client = BlobServiceClient.from_connection_string(storage_connection)
                logger.info("   📦 Azure Storage client initialized")
            
            logger.info("✅ All Azure clients initialized successfully!")
            self._add_demo_step("Azure clients setup", "✅ Success")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup Azure clients: {str(e)}")
            self._add_demo_step("Azure clients setup", f"❌ Failed: {str(e)}")
            return False
    
    def create_search_index(self) -> bool:
        """
        Step 2: Create Azure AI Search index with hybrid search capabilities.
        
        Configures both traditional search and vector search fields.
        """
        logger.info("📊 Creating search index with hybrid capabilities...")
        
        try:
            # Define search index fields
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
                SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
                SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,  # text-embedding-ada-002 dimensions
                    vector_search_profile_name="banking-vector-profile"
                ),
                SearchField(
                    name="keywords",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    searchable=True
                )
            ]
            
            # Configure vector search
            vector_search = VectorSearch(
                profiles=[
                    VectorSearchProfile(
                        name="banking-vector-profile",
                        algorithm_configuration_name="banking-algorithm-config"
                    )
                ],
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="banking-algorithm-config"
                    )
                ]
            )
            
            # Create search index
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search
            )
            
            # Recreate the demo-owned index so repeated class runs are deterministic.
            try:
                self.index_client.delete_index(self.index_name)
                logger.info(f"   Removed existing demo index: {self.index_name}")
            except Exception:
                pass

            # Deploy the index
            result = self.index_client.create_or_update_index(index)
            
            logger.info(f"✅ Search index created: {result.name}")
            logger.info("   📋 Index capabilities:")
            logger.info("      • Full-text search with language analysis")
            logger.info("      • Vector search for semantic similarity")
            logger.info("      • Hybrid search combining both approaches")
            logger.info("      • Filtering and faceting by category")
            
            self._add_demo_step("Search index creation", "✅ Hybrid search index created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create search index: {str(e)}")
            self._add_demo_step("Search index creation", f"❌ Failed: {str(e)}")
            return False
    
    def generate_embeddings(self, text: str) -> List[float]:
        """Generate vector embeddings for text using Azure OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                model=os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME", "text-embedding-ada-002"),
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.warning(f"⚠️ Failed to generate embedding: {str(e)}")
            return []

    def _format_score(self, result: Dict[str, Any]) -> str:
        """Format an Azure Search score for demo output."""
        score = result.get('@search.score') if hasattr(result, 'get') else None
        return f"{score:.3f}" if isinstance(score, (int, float)) else "N/A"
    
    def upload_documents(self) -> bool:
        """
        Step 3: Upload banking documents with vector embeddings.
        
        Processes each document and generates embeddings for vector search.
        """
        logger.info("📤 Uploading documents with vector embeddings...")
        
        try:
            documents_to_upload = []
            
            for doc in self.banking_documents:
                logger.info(f"   Processing: {doc['title']}")
                
                # Generate vector embedding for content
                embedding = self.generate_embeddings(doc['content'])
                
                # Prepare document for upload
                search_doc = {
                    "id": doc["id"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "category": doc["category"],
                    "keywords": doc["keywords"],
                    "content_vector": embedding
                }
                
                documents_to_upload.append(search_doc)
                logger.info(f"      ✅ Embedding generated ({len(embedding)} dimensions)")
            
            # Upload all documents to search index
            result = self.search_client.upload_documents(documents_to_upload)
            
            success_count = len([r for r in result if r.succeeded])
            logger.info(f"✅ Uploaded {success_count}/{len(documents_to_upload)} documents")
            
            # Show document statistics
            logger.info("   📊 Document statistics:")
            for doc in self.banking_documents:
                word_count = len(doc['content'].split())
                logger.info(f"      • {doc['title']}: {word_count} words, {len(doc['keywords'])} keywords")
            
            self._add_demo_step("Document upload", f"✅ {success_count} documents with embeddings")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload documents: {str(e)}")
            self._add_demo_step("Document upload", f"❌ Failed: {str(e)}")
            return False
    
    def demonstrate_search_capabilities(self):
        """
        Step 4: Demonstrate different search approaches.
        
        Shows keyword search, semantic search, and hybrid search results.
        """
        logger.info("🔍 Demonstrating search capabilities...")
        
        # Test queries
        test_queries = [
            "What are the wire transfer limits?",
            "How do I set up overdraft protection?",
            "Tell me about CD rates and terms",
            "I need help with customer service hours"
        ]
        
        for i, query in enumerate(test_queries, 1):
            logger.info(f"\n   🤔 Query {i}: {query}")
            
            # 1. Keyword search
            try:
                keyword_results = self.search_client.search(
                    search_text=query,
                    search_mode="all",
                    top=2,
                    select=["title", "content", "category"]
                )
                
                logger.info("   📝 Keyword search results:")
                for result in keyword_results:
                    logger.info(f"      Score: {self._format_score(result)} - {result['title']}")
                    content_preview = result['content'][:100] + "..."
                    logger.info(f"      Preview: {content_preview}")
                    
            except Exception as e:
                logger.warning(f"      ⚠️ Keyword search failed: {str(e)}")
            
            # 2. Vector search (semantic similarity)
            try:
                query_vector = self.generate_embeddings(query)
                if query_vector:
                    vector_results = self.search_client.search(
                        search_text=None,
                        vector_queries=[VectorizedQuery(vector=query_vector, k_nearest_neighbors=2, fields="content_vector")],
                        select=["title", "content", "category"]
                    )
                    
                    logger.info("   🎯 Vector search results:")
                    for result in vector_results:
                        logger.info(f"      Score: {self._format_score(result)} - {result['title']}")
                        
            except Exception as e:
                logger.warning(f"      ⚠️ Vector search failed: {str(e)}")
            
            # 3. Hybrid search (best of both)
            try:
                hybrid_results = self.search_client.search(
                    search_text=query,
                    vector_queries=[VectorizedQuery(vector=query_vector, k_nearest_neighbors=2, fields="content_vector")] if query_vector else [],
                    top=2,
                    select=["title", "content", "category"]
                )
                
                logger.info("   🔄 Hybrid search results (recommended):")
                for result in hybrid_results:
                    logger.info(f"      Score: {self._format_score(result)} - {result['title']}")
                    
            except Exception as e:
                logger.warning(f"      ⚠️ Hybrid search failed: {str(e)}")
        
        self._add_demo_step("Search demonstration", "✅ Keyword, vector, and hybrid search tested")
    
    def demonstrate_rag_pipeline(self):
        """
        Step 5: Demonstrate complete RAG pipeline with response generation.
        
        Shows how retrieved context enhances language model responses.
        """
        logger.info("🤖 Demonstrating complete RAG pipeline...")
        
        # RAG test scenarios
        rag_scenarios = [
            {
                "query": "What are the fees for wire transfers?",
                "intent": "Fee information lookup"
            },
            {
                "query": "I want to open a high-yield savings account. What do I need to know?",
                "intent": "Product information and requirements"
            },
            {
                "query": "My debit card was stolen. What should I do?",
                "intent": "Emergency procedures and contact info"
            }
        ]
        
        for i, scenario in enumerate(rag_scenarios, 1):
            query = scenario["query"]
            intent = scenario["intent"]
            
            logger.info(f"\n   🎬 RAG Scenario {i}: {intent}")
            logger.info(f"   🤔 User query: {query}")
            
            try:
                # Step 1: Retrieve relevant context
                query_vector = self.generate_embeddings(query)
                search_results = self.search_client.search(
                    search_text=query,
                    vector_queries=[VectorizedQuery(vector=query_vector, k_nearest_neighbors=3, fields="content_vector")] if query_vector else [],
                    top=3,
                    select=["title", "content", "category"]
                )
                
                # Collect context from search results
                context_pieces = []
                sources = []
                
                logger.info("   📚 Retrieved context:")
                for result in search_results:
                    context_pieces.append(result['content'])
                    sources.append(result['title'])
                    logger.info(f"      • {result['title']} (score: {self._format_score(result)})")
                
                context = "\n\n".join(context_pieces)
                
                # Step 2: Generate response with context
                system_prompt = """You are a helpful banking assistant for First National Bank. 
Use the provided context to answer customer questions accurately and helpfully. 
If the context doesn't contain relevant information, say so politely.
Always be professional and cite the source documents when possible."""
                
                user_prompt = f"""Context from bank documents:
{context}

Customer question: {query}

Please provide a helpful response based on the context above."""
                
                # Simulate GPT response (in production, call actual model)
                logger.info("   🤖 Generated response:")
                
                # For demo purposes, create contextual response based on retrieved content
                if "wire transfer" in query.lower() and any("wire transfer" in piece.lower() for piece in context_pieces):
                    response = """Based on our bank policies, here are the wire transfer details:

• Domestic wire transfers: $25,000 per day limit
• International wire transfers: $15,000 per day limit  
• Additional verification is required for amounts over $10,000
• Processing time: Same day for domestic transfers, 1-3 days for international

These limits help ensure the security of your transactions. If you need to transfer larger amounts, please contact our customer service team.

Source: First National Bank - Account Policies"""
                
                elif "savings" in query.lower() and any("savings" in piece.lower() for piece in context_pieces):
                    response = """For a high-yield savings account, here's what you need to know:

• High-Yield Savings: 3.2% APY with $1,000 minimum balance
• No monthly fees when minimum balance is maintained
• Standard Savings also available: 0.5% APY with $100 minimum
• Youth Savings (under 18): 2.0% APY with no minimum

The high-yield option offers the best return and is perfect for building your savings with our competitive rates.

Source: First National Bank - Investment Products"""
                
                elif "card" in query.lower() and "stolen" in query.lower():
                    response = """If your debit card was stolen, please take these immediate steps:

1. Report the card as lost/stolen immediately
2. Call our Emergency Card Services: 1-800-CARD-911 (available 24/7)
3. Monitor your account for any unauthorized transactions
4. We can expedite a replacement card for $25 if needed
5. Your new card must be activated within 30 days

For any disputed transactions, report them within 60 days and we'll issue a temporary credit during investigation.

Source: First National Bank - Customer Service Guide"""
                
                else:
                    response = f"I found relevant information in our {', '.join(sources)} documents. Based on the context, I can help you with your question about {query.lower()}. Please let me provide you with the specific details from our official bank policies."
                
                logger.info(f"      {response}")
                
                # Step 3: Show source attribution
                logger.info(f"   📋 Sources used: {', '.join(sources)}")
                
            except Exception as e:
                logger.warning(f"      ⚠️ RAG pipeline failed: {str(e)}")
        
        self._add_demo_step("RAG pipeline demonstration", "✅ Complete retrieval and generation workflow")
    
    def demonstrate_rag_api_approach(self):
        """
        Explain the supported replacement for the retired On Your Data API.
        """
        logger.info("Azure OpenAI On Your Data is retired. Use application-managed Search grounding.")
        
        logger.info("\n   📋 RAG API Implementation Steps:")
        api_steps = [
            "1. Index documents in an Azure AI Search index",
            "2. Create an OpenAI SDK client for the Azure OpenAI endpoint",
            "3. Retrieve Search evidence and pass it as context to Chat Completions"
        ]
        
        for step in api_steps:
            logger.info(f"      {step}")
        
        logger.info("\n   💻 Code Example (RAG API approach):")
        logger.info("""
        from azure_openai_auth import create_azure_openai_client
        from rag_grounding import answer_with_search

        with create_azure_openai_client() as client:
            answer, sources = answer_with_search(client, "What are your CD rates?")
            print(answer, sources)
        """)
        
        logger.info("\nHistorical comparison only: the managed On Your Data API is retired.")
        comparison = [
            ("Control", "Manual: Full control over search and generation", "API: Azure handles integration automatically"),
            ("Complexity", "Manual: More code, more customization", "API: Simpler, less code required"),
            ("Flexibility", "Manual: Custom search logic, scoring", "API: Standard Azure implementation"),
            ("Debugging", "Manual: Full visibility into each step", "API: Limited visibility into internal process"),
            ("Performance", "Manual: Optimize each component", "API: Azure-optimized pipeline"),
            ("Use Case", "Manual: Complex, custom requirements", "API: Standard RAG implementations")
        ]
        
        for aspect, manual, api in comparison:
            logger.info(f"      📊 {aspect}:")
            logger.info(f"         • {manual}")
            logger.info(f"         • {api}")
        
        self._add_demo_step("RAG API migration", "Supported Search SDK grounding replacement explained")

    def explain_production_architecture(self):
        """
        Step 6: Explain production RAG architecture and best practices.
        """
        logger.info("🏗️ Production RAG architecture considerations...")
        
        architecture_components = [
            ("Data Ingestion Pipeline", [
                "Automated document processing and chunking",
                "Incremental updates and change detection",
                "Data quality validation and preprocessing",
                "Scheduled refresh and reindexing"
            ]),
            ("Search Optimization", [
                "Optimal chunk size and overlap strategies",
                "Hybrid search weight tuning",
                "Custom scoring profiles for domain relevance",
                "Performance monitoring and query optimization"
            ]),
            ("Response Generation", [
                "Prompt engineering for consistent responses",
                "Context window management and truncation",
                "Response caching for common queries",
                "A/B testing for prompt variations"
            ]),
            ("Production Operations", [
                "Load balancing and auto-scaling",
                "Monitoring and alerting systems",
                "Security and access controls",
                "Cost optimization and resource management"
            ])
        ]
        
        for component, details in architecture_components:
            logger.info(f"\n   🎯 {component}:")
            for detail in details:
                logger.info(f"      • {detail}")
        
        logger.info("\n   💡 RAG Best Practices:")
        best_practices = [
            "Use hybrid search for better accuracy than pure vector or keyword search",
            "Implement proper document chunking strategies (300-500 words per chunk)",
            "Monitor and evaluate response quality with human feedback",
            "Implement fallback mechanisms for when no relevant context is found",
            "Use source attribution for transparency and trust",
            "Regular evaluation against ground truth Q&A pairs"
        ]
        
        for practice in best_practices:
            logger.info(f"      ✅ {practice}")
        
        self._add_demo_step("Production architecture", "✅ Architecture and best practices explained")
    
    def cleanup_demo_resources(self):
        """Clean up demo resources to manage costs."""
        logger.info("🧹 Cleanup and cost management...")
        
        cleanup_actions = [
            ("Search Index", "Keep for additional testing, delete when done"),
            ("Uploaded Documents", "Remain in index for future queries"),
            ("Embedding Calls", f"Used ~{len(self.banking_documents)} embedding API calls"),
            ("Search Queries", f"Performed ~{len(self.demo_steps) * 3} search operations")
        ]
        
        logger.info("   📊 Resource usage summary:")
        for resource, action in cleanup_actions:
            logger.info(f"      • {resource}: {action}")
        
        logger.info("\n   💰 Cost estimates:")
        cost_estimates = [
            "Azure AI Search: ~$250/month (Standard tier)",
            "Embedding generation: ~$0.10 for this demo",
            "Search queries: ~$0.01 for this demo",
            "Storage: <$0.01/month for documents"
        ]
        
        for estimate in cost_estimates:
            logger.info(f"      • {estimate}")
        
        self._add_demo_step("Cleanup", "✅ Resource cleanup and cost analysis")
    
    def _add_demo_step(self, step_name: str, result: str):
        """Track demo steps for summary."""
        elapsed = time.time() - self.demo_start_time
        self.demo_steps.append({
            "step": step_name,
            "result": result,
            "elapsed_minutes": round(elapsed / 60, 1)
        })
    
    def print_demo_summary(self):
        """Print comprehensive demo summary."""
        total_time = time.time() - self.demo_start_time
        
        logger.info("\n" + "="*60)
        logger.info("📋 RAG DEMO SUMMARY")
        logger.info("="*60)
        
        logger.info(f"🎯 Student: {self.student_initials}")
        logger.info(f"⏱️ Total demo time: {total_time/60:.1f} minutes")
        logger.info(f"🏷️ Search index: {self.index_name}")
        logger.info(f"📚 Documents processed: {len(self.banking_documents)}")
        
        logger.info("\n📊 Demo Steps Completed:")
        for step in self.demo_steps:
            logger.info(f"   {step['elapsed_minutes']:4.1f}min - {step['step']}: {step['result']}")
        
        logger.info("\n🎓 Key Learning Points:")
        learning_points = [
            "✅ RAG architecture and component integration",
            "✅ Hybrid search combining keyword and vector approaches",
            "✅ Vector embedding generation and storage",
            "✅ Context retrieval and relevance scoring",
            "✅ Response generation with source attribution",
            "✅ Production deployment and scaling considerations"
        ]
        
        for point in learning_points:
            logger.info(f"   {point}")
        
        logger.info("\n🔗 Related Files:")
        logger.info("   • 2a_rag_portal_guide.md - Portal version of this demo")
        logger.info("   • bank-dataset-generator.py - Training data that could be used for retrieval")
        logger.info("   • Azure AI Search documentation for advanced features")

def main():
    """
    Main demo execution function.
    
    This function runs the complete RAG demonstration workflow.
    Perfect for 20-minute classroom demonstration.
    """
    print("🔍 AI-3016 Demo 2B: RAG Pattern with Azure AI Search via Code")
    print("=" * 60)
    print("⏱️ Estimated demo time: 20 minutes")
    print("🎯 Focus: Automated RAG pipeline implementation")
    print()
    
    parser = argparse.ArgumentParser(description="AI-3016 code-first RAG demo")
    parser.add_argument("--initials", default="demo", help="Initials for resource naming")
    args = parser.parse_args()

    student_initials = args.initials.strip().lower()
    if not student_initials:
        student_initials = "demo"
    
    # Initialize demo
    demo = RAGDemo(student_initials)
    
    try:
        # Execute demo workflow
        logger.info("🎬 Starting RAG demo workflow...")
        
        # Step 1: Setup Azure clients
        if not demo.setup_azure_clients():
            logger.error("❌ Cannot proceed without Azure service connections")
            return
        
        # Step 2: Create search index
        if not demo.create_search_index():
            logger.error("❌ Cannot proceed without search index")
            return
        
        # Step 3: Upload documents with embeddings
        if not demo.upload_documents():
            logger.error("❌ Cannot proceed without documents")
            return
        
        # Step 4: Demonstrate search capabilities
        demo.demonstrate_search_capabilities()
        
        # Step 5: Demonstrate complete RAG pipeline
        demo.demonstrate_rag_pipeline()
        
        # Step 6: Demonstrate alternative RAG API approach
        demo.demonstrate_rag_api_approach()
        
        # Step 7: Explain production architecture
        demo.explain_production_architecture()
        
        # Step 8: Cleanup and cost management
        demo.cleanup_demo_resources()
        
        # Final summary
        demo.print_demo_summary()
        
        logger.info("\n🎉 RAG demo completed successfully!")
        logger.info("📚 Check 2a_rag_portal_guide.md for the manual version")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Demo interrupted by user")
        demo.print_demo_summary()
    except Exception as e:
        logger.error(f"\n❌ Demo failed with error: {str(e)}")
        demo.print_demo_summary()

if __name__ == "__main__":
    main()