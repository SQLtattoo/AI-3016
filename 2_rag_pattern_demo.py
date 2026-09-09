"""
AI-3016 Demo 2: RAG Pattern with Azure AI Search and Microsoft Foundry
================================================================

This demo shows how to:
1. Create an Azure AI Search index
2. Load and chunk banking knowledge base documents
3. Generate embeddings and store in search index
4. Implement RAG pattern with chat completion
5. Compare RAG vs non-RAG responses

Prerequisites:
- Azure AI Search service
- Microsoft Foundry project with deployed model
- Azure OpenAI embeddings model (text-embedding-ada-002)
"""

import os
import json
import time
import argparse
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField
)
from azure.core.credentials import AzureKeyCredential
from azure_openai_auth import create_azure_openai_client

load_dotenv()

class RAGDemo:
    def __init__(self):
        # Azure AI Search configuration
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY") or os.getenv("AZURE_SEARCH_KEY")
        self.index_name = "al-zahra-bank-knowledge"
        
        # Azure OpenAI model configuration
        self.ai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.chat_model = os.getenv("DEPLOYMENT_NAME", "gpt-4o")
        self.embedding_model = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME", "text-embedding-ada-002")
        
        # Initialize clients
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=AzureKeyCredential(self.search_key)
        )
        
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=AzureKeyCredential(self.search_key)
        )
        
        self.openai_client = create_azure_openai_client(api_version="2024-05-01-preview")
        
    def create_banking_knowledge_base(self):
        """Create a comprehensive banking knowledge base"""
        return [
            {
                "id": "1",
                "title": "Investment Portfolio Services",
                "content": """BankOne Private Bank offers exclusive portfolio management services for high-net-worth individuals. 
                Our minimum investment requirement is USD 5 million. We provide bespoke investment strategies tailored to each client's 
                financial goals, risk tolerance, and time horizon. Our portfolio managers have decades of experience in global markets 
                and access to exclusive investment opportunities including private equity, hedge funds, and alternative investments. 
                All portfolios are customized with regular rebalancing and performance reporting.""",
                "category": "investments",
                "tags": ["portfolio", "minimum investment", "high-net-worth", "bespoke strategies"]
            },
            {
                "id": "2", 
                "title": "Sharia-Compliant Investment Options",
                "content": """BankOne Private Bank is proud to offer comprehensive Sharia-compliant investment solutions that adhere 
                to Islamic finance principles. Our Islamic banking division provides halal investment portfolios that exclude 
                interest-based instruments, gambling, alcohol, and other prohibited sectors. We offer sukuk bonds, Islamic equity funds, 
                commodity investments, and real estate investment trusts (REITs) that comply with Sharia law. All investments are 
                certified by our Sharia Advisory Board comprising renowned Islamic scholars.""",
                "category": "islamic-banking",
                "tags": ["sharia-compliant", "islamic finance", "halal investments", "sukuk"]
            },
            {
                "id": "3",
                "title": "Luxury Property Financing",
                "content": """Our luxury property loan division specializes in financing high-end residential and commercial properties 
                worldwide. We offer competitive rates starting from 2.5% APR for qualified clients. The application process begins 
                with submitting your financial profile, property valuation, and investment objectives. Our relationship managers work 
                closely with clients to design flexible loan packages with terms up to 30 years. We finance properties in prime 
                locations including Dubai Marina, Palm Jumeirah, London, New York, and other prestigious addresses.""",
                "category": "loans",
                "tags": ["luxury property", "real estate financing", "competitive rates", "global properties"]
            },
            {
                "id": "4",
                "title": "Asset-Backed Lending Solutions", 
                "content": """BankOne Private Bank provides sophisticated asset-backed lending using valuable collateral including 
                fine art, luxury yachts, private jets, rare collectibles, and precious metals. Our art financing division works 
                with certified appraisers and authentication experts to ensure proper valuation. Loan-to-value ratios typically 
                range from 50-70% depending on the asset class and market liquidity. We offer flexible repayment terms and 
                specialized storage solutions for high-value collateral items.""",
                "category": "loans",
                "tags": ["asset-backed lending", "fine art", "yacht financing", "collectibles", "luxury assets"]
            },
            {
                "id": "5",
                "title": "Wealth Management and Family Office Services",
                "content": """Our family office division serves ultra-high-net-worth families with comprehensive wealth management, 
                estate planning, and generational wealth transfer strategies. Services include tax optimization, succession planning, 
                philanthropy advisory, and family governance structures. We coordinate with legal and tax advisors globally to 
                ensure seamless wealth preservation across jurisdictions. Our family office minimum is USD 25 million in 
                investable assets with dedicated relationship teams for each family.""",
                "category": "wealth-management", 
                "tags": ["family office", "estate planning", "wealth transfer", "tax optimization", "ultra-high-net-worth"]
            },
            {
                "id": "6",
                "title": "Privacy and Confidentiality Protocols",
                "content": """BankOne Private Bank maintains the highest standards of client confidentiality through bank-grade 
                encryption, secure communication channels, and strict privacy protocols. All client information is protected 
                under UAE banking secrecy laws and international privacy regulations. We use end-to-end encrypted communications, 
                biometric authentication, and secure document portals. Our staff undergoes regular confidentiality training and 
                signs comprehensive non-disclosure agreements. Client meetings can be conducted in private banking suites with 
                enhanced security measures.""",
                "category": "security",
                "tags": ["confidentiality", "privacy", "encryption", "banking secrecy", "secure communications"]
            },
            {
                "id": "7",
                "title": "International Diversification Strategies",
                "content": """Our global investment platform provides access to international markets through diversified portfolios 
                spanning developed and emerging markets. We offer exposure to US, European, Asian, and Middle Eastern markets through 
                direct equity investments, bonds, currencies, and alternative assets. Our currency hedging solutions protect against 
                foreign exchange volatility. Investment vehicles include mutual funds, ETFs, structured products, and direct investments 
                in foreign securities. Regional allocation is customized based on client risk profile and market outlook.""",
                "category": "investments",
                "tags": ["international diversification", "global markets", "currency hedging", "emerging markets"]
            },
            {
                "id": "8",
                "title": "Sustainable and ESG Investment Options",
                "content": """BankOne Private Bank offers comprehensive Environmental, Social, and Governance (ESG) investment portfolios 
                focused on sustainable and socially responsible investing. Our ESG funds target companies with strong sustainability 
                practices, renewable energy projects, clean technology, and positive social impact initiatives. We provide impact 
                investing opportunities in healthcare, education, and environmental conservation projects across the Middle East and 
                globally. ESG portfolios undergo rigorous screening to ensure alignment with sustainability goals while maintaining 
                competitive returns.""",
                "category": "investments",
                "tags": ["ESG investing", "sustainable investments", "impact investing", "renewable energy", "social responsibility"]
            }
        ]
        
    def chunk_documents(self, documents: List[Dict], chunk_size: int = 500) -> List[Dict]:
        """Split documents into smaller chunks for better retrieval"""
        chunks = []
        
        for doc in documents:
            content = doc["content"]
            words = content.split()
            
            # Create chunks of specified size with overlap
            for i in range(0, len(words), chunk_size - 50):  # 50 word overlap
                chunk_words = words[i:i + chunk_size]
                chunk_content = " ".join(chunk_words)
                
                chunk = {
                    "id": f"{doc['id']}_chunk_{i // (chunk_size - 50)}",
                    "parent_id": doc["id"],
                    "title": doc["title"],
                    "content": chunk_content,
                    "category": doc["category"],
                    "tags": doc["tags"]
                }
                chunks.append(chunk)
                
        return chunks
        
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for text chunks"""
        print(f"🔄 Generating embeddings for {len(texts)} texts...")
        
        embeddings = []
        batch_size = 10  # Process in batches to avoid rate limits
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            response = self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=batch
            )
            
            batch_embeddings = [item.embedding for item in response.data]
            embeddings.extend(batch_embeddings)
            
            time.sleep(0.1)  # Rate limiting
            
        print(f"✅ Generated {len(embeddings)} embeddings")
        return embeddings
        
    def create_search_index(self):
        """Create Azure AI Search index with vector search capabilities"""
        print("🏗️  Creating search index...")
        
        # Define index schema
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SimpleField(name="parent_id", type=SearchFieldDataType.String),
            SearchableField(name="title", type=SearchFieldDataType.String),
            SearchableField(name="content", type=SearchFieldDataType.String),
            SearchableField(name="category", type=SearchFieldDataType.String, facetable=True),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=1536,  # text-embedding-ada-002 dimensions
                vector_search_profile_name="myHnswProfile"
            ),
            SearchField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String), searchable=True)
        ]
        
        # Configure vector search
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="myHnsw"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(name="myHnsw")
            ]
        )
        
        # Configure semantic search
        semantic_config = SemanticConfiguration(
            name="my-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="title"),
                content_fields=[SemanticField(field_name="content")]
            )
        )
        
        semantic_search = SemanticSearch(configurations=[semantic_config])
        
        # Create the index
        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )
        
        try:
            result = self.index_client.create_index(index)
            print(f"✅ Index created: {result.name}")
        except Exception as e:
            if "already exists" in str(e):
                print(f"⚠️  Index {self.index_name} already exists, deleting and recreating...")
                self.index_client.delete_index(self.index_name)
                result = self.index_client.create_index(index)
                print(f"✅ Index recreated: {result.name}")
            else:
                raise e
                
    def load_documents_to_index(self):
        """Load documents into the search index"""
        print("📚 Loading documents to search index...")
        
        # Create knowledge base
        documents = self.create_banking_knowledge_base()
        
        # Chunk documents
        chunks = self.chunk_documents(documents)
        print(f"📄 Created {len(chunks)} chunks from {len(documents)} documents")
        
        # Generate embeddings
        texts = [chunk["content"] for chunk in chunks]
        embeddings = self.generate_embeddings(texts)
        
        # Prepare documents for indexing
        search_documents = []
        for chunk, embedding in zip(chunks, embeddings):
            search_doc = {
                "id": chunk["id"],
                "parent_id": chunk["parent_id"],
                "title": chunk["title"],
                "content": chunk["content"],
                "category": chunk["category"],
                "content_vector": embedding,
                "tags": chunk["tags"]
            }
            search_documents.append(search_doc)
            
        # Upload to search index
        result = self.search_client.upload_documents(search_documents)
        print(f"✅ Uploaded {len(result)} documents to index")
        
    def search_knowledge_base(self, query: str, top_k: int = 3) -> List[Dict]:
        """Search the knowledge base using hybrid search"""
        print(f"🔍 Searching for: '{query}'")
        
        # Generate query embedding
        query_embedding = self.generate_embeddings([query])[0]
        
        # Create vector query
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_k,
            fields="content_vector"
        )
        
        # Perform hybrid search (vector + text)
        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            select=["id", "title", "content", "category"],
            top=top_k
        )
        
        search_results = []
        for result in results:
            search_results.append({
                "content": result["content"],
                "title": result["title"],
                "category": result["category"],
                "score": result["@search.score"]
            })
            
        print(f"✅ Found {len(search_results)} relevant results")
        return search_results
        
    def generate_rag_response(self, query: str, context_docs: List[Dict]) -> str:
        """Generate response using RAG pattern"""
        # Create context from retrieved documents
        context = "\n\n".join([
            f"Document: {doc['title']}\nContent: {doc['content']}"
            for doc in context_docs
        ])
        
        # Create RAG prompt
        system_prompt = f"""You are an AI assistant for BankOne Private Bank in Abu Dhabi. 
        You provide professional, discreet advice on investments and loans for high-net-worth clients.
        
        Use the following context to answer the user's question. If the context doesn't contain 
        relevant information, politely indicate that you don't have specific information about that topic.
        
        Context:
        {context}"""
        
        # Generate response
        response = self.openai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            model=self.chat_model,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    def generate_non_rag_response(self, query: str) -> str:
        """Generate response without RAG for comparison"""
        system_prompt = """You are an AI assistant for BankOne Private Bank in Abu Dhabi. 
        Provide professional, discreet advice on investments and loans for high-net-worth clients."""
        
        response = self.openai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            model=self.chat_model,
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
        
    def demo_rag_comparison(self):
        """Demonstrate RAG vs non-RAG responses"""
        print("🎯 RAG vs Non-RAG Comparison Demo")
        print("=" * 60)
        
        test_queries = [
            "What is the minimum investment for your portfolio services?",
            "Do you offer Sharia-compliant investments?", 
            "Can I get a loan using my art collection as collateral?",
            "What ESG investment options do you have?",
            "How do you ensure client confidentiality?"
        ]
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n🔸 Test Query {i}: {query}")
            print("-" * 50)
            
            # Get RAG response
            context_docs = self.search_knowledge_base(query)
            rag_response = self.generate_rag_response(query, context_docs)
            
            # Get non-RAG response
            non_rag_response = self.generate_non_rag_response(query)
            
            print(f"📚 RAG Response (with context):")
            print(f"{rag_response}\n")
            
            print(f"🤖 Non-RAG Response (without context):")
            print(f"{non_rag_response}\n")
            
            print(f"📊 Retrieved Context Sources:")
            for doc in context_docs:
                print(f"   • {doc['title']} (Score: {doc['score']:.3f})")
            print("-" * 60)
            
    def run_demo(self):
        """Run the complete RAG demo"""
        print("🎬 Starting RAG Pattern Demo for AI-3016")
        print("=" * 60)
        
        try:
            # Step 1: Create search index
            self.create_search_index()
            
            # Step 2: Load documents
            self.load_documents_to_index()
            
            # Wait for indexing to complete
            print("⏳ Waiting for indexing to complete...")
            time.sleep(10)
            
            # Step 3: Demonstrate RAG vs non-RAG
            self.demo_rag_comparison()
            
            print("🎉 RAG demo completed successfully!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    # Set up environment variables
    parser = argparse.ArgumentParser(description="AI-3016 RAG pattern demo")
    parser.add_argument("--smoke-test", action="store_true", help="Run the normal flow non-interactively for validation")
    parser.parse_args()

    required_env_vars = [
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_ADMIN_KEY",
        "AZURE_OPENAI_ENDPOINT"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n📝 Please set these environment variables before running the demo.")
        exit(1)
    
    # Run the demo
    demo = RAGDemo()
    demo.run_demo()