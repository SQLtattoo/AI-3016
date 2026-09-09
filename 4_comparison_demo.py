"""
AI-3016 Demo 4: Base LLM vs RAG vs Fine-tuning Comparison
==========================================================

This demo compares three AI application approaches:
1. Base GPT-4o - Generic responses
2. RAG-enhanced - Grounded in your documents
3. Fine-tuned - Learned response behavior, tone, and format

Prerequisites:
- Microsoft Foundry with GPT-4o deployed
- Azure AI Search with rag-bank-documents index
- Fine-tuned model (optional - will skip if not available)
"""

import os
import argparse
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure_openai_auth import create_azure_openai_client

# Load environment variables
load_dotenv()

class ComparisonDemo:
    def __init__(self):
        # Provisioned chat model deployment
        self.foundry_endpoint = os.getenv("ENDPOINT_URL")
        self.deployment_name = os.getenv("DEPLOYMENT_NAME")
        
        # Azure OpenAI (for embeddings)
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.embeddings_deployment = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME")
        
        # Azure AI Search (for RAG)
        self.search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
        self.search_index = os.getenv("AZURE_SEARCH_INDEX")
        
        self.chat_client = create_azure_openai_client(api_version="2024-05-01-preview")
        self.embeddings_client = create_azure_openai_client(api_version="2024-05-01-preview")
        
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.search_index,
            credential=AzureKeyCredential(self.search_key)
        )
        
    def print_section(self, title, emoji="📌"):
        """Print formatted section header"""
        print(f"\n{emoji} {title}")
        print("=" * 70)
        
    def print_response(self, label, response, sources=None):
        """Print formatted response"""
        print(f"\n💬 {label}")
        print("-" * 70)
        print(response)
        if sources:
            print(f"\n📚 Sources: {', '.join(sources)}")
        print("-" * 70)
        
    def get_embedding(self, text):
        """Generate embedding for text"""
        response = self.embeddings_client.embeddings.create(
            input=text,
            model=self.embeddings_deployment
        )
        return response.data[0].embedding
        
    def search_documents(self, query, top_k=3):
        """Search for relevant documents using vector search"""
        query_vector = self.get_embedding(query)
        
        vector_query = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top_k,
            fields="content_vector"
        )
        
        results = self.search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            select=["content", "title"]
        )
        
        docs = []
        sources = []
        for result in results:
            docs.append(result["content"])
            sources.append(result["title"])
            
        return docs, sources
        
    def test_base_model(self, query):
        """Test base GPT-4o without any enhancements"""
        self.print_section("Approach 1: Base GPT-4o Model", "🤖")
        print(f"Query: {query}\n")
        
        response = self.chat_client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        answer = response.choices[0].message.content
        self.print_response("Base Model Response", answer)
        
        print("\n⚠️  Limitations:")
        print("   - Generic knowledge only")
        print("   - No access to your specific documents")
        print("   - May provide outdated or incorrect information")
        print("   - No authoritative sources were supplied to cite")
        
        return answer
        
    def test_rag_model(self, query):
        """Test RAG-enhanced model with document retrieval"""
        self.print_section("Approach 2: RAG (Retrieval-Augmented Generation)", "🔍")
        print(f"Query: {query}\n")
        
        # Step 1: Search for relevant documents
        print("🔎 Searching knowledge base...")
        docs, sources = self.search_documents(query, top_k=3)
        
        if not docs:
            print("❌ No relevant documents found")
            return None
            
        print(f"✅ Found {len(docs)} relevant documents")
        for i, source in enumerate(sources, 1):
            print(f"   {i}. {source}")
        
        # Step 2: Build context from retrieved documents
        context = "\n\n".join([f"Document {i+1}:\n{doc}" for i, doc in enumerate(docs)])
        
        # Step 3: Generate response with context
        print("\n🤖 Generating answer with context...")
        system_prompt = f"""You are an AI assistant for a bank. Answer questions based ONLY on the provided documents.
If the answer is not in the documents, say you don't have that information.
Always cite which document you used.

Documents:
{context}"""
        
        response = self.chat_client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        answer = response.choices[0].message.content
        self.print_response("RAG-Enhanced Response", answer, sources)
        
        print("\n✅ Advantages:")
        print("   - Grounded in your specific documents")
        print("   - Can cite the retrieved sources")
        print("   - Reflects source updates after the search index is refreshed")
        print("   - No model training required; documents must be ingested and indexed")
        
        return answer
        
    def test_fine_tuned_model(self, query):
        """Test fine-tuned model (if available)"""
        self.print_section("Approach 3: Fine-tuned Model", "🎯")
        print(f"Query: {query}\n")
        
        # Check if fine-tuned model deployment exists
        fine_tuned_deployment = os.getenv("FINE_TUNED_DEPLOYMENT_NAME")
        
        if not fine_tuned_deployment:
            print("⚠️  Fine-tuned model not available yet")
            print("\nTo create a fine-tuned model:")
            print("   1. Run: python 1b_fine_tuning_code_first.py")
            print("   2. Wait 10-30 minutes for training to complete")
            print("   3. Add FINE_TUNED_DEPLOYMENT_NAME to .env file")
            print("   4. Run this demo again")
            
            print("\n📝 What Fine-tuning Would Provide:")
            print("   - Specialized banking terminology and tone")
            print("   - Consistent response style")
            print("   - Learned behavior for patterns represented in training data")
            print("   - More consistent output structure")
            print("   - Direct inference without a retrieval step")
            
            return None
            
        # Test fine-tuned model
        try:
            response = self.chat_client.chat.completions.create(
                model=fine_tuned_deployment,
                messages=[
                    {"role": "system", "content": "You are an AI assistant for BankOne Private Bank in Abu Dhabi."},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            answer = response.choices[0].message.content
            self.print_response("Fine-tuned Model Response", answer)
            
            print("\n✅ Advantages:")
            print("   - Learned behavior for represented tasks")
            print("   - Consistent tone and style")
            print("   - No retrieval step for learned behavior")
            print("   - More consistent output format")
            
            print("\n⚠️  Considerations:")
            print("   - Requires training data preparation")
            print("   - Training takes time (10-30 minutes)")
            print("   - Costs more to train")
            print("   - Use RAG, not fine-tuning, for changing authoritative facts")
            
            return answer
            
        except Exception as e:
            print(f"❌ Error testing fine-tuned model: {e}")
            return None
            
    def run_comparison(self, query):
        """Run all three approaches for comparison"""
        print("\n" + "=" * 70)
        print("🎬 AI-3016 Comparison Demo: Base vs RAG vs Fine-tuning")
        print("=" * 70)
        print(f"\n🔍 Test Query: {query}")
        
        # Test 1: Base model
        base_answer = self.test_base_model(query)
        
        # Test 2: RAG-enhanced
        rag_answer = self.test_rag_model(query)
        
        # Test 3: Fine-tuned (if available)
        fine_tuned_answer = self.test_fine_tuned_model(query)
        
        # Summary
        self.print_section("Summary: When to Use Each Approach", "🎓")
        
        print("\n🤖 Base Model:")
        print("   ✅ Use for: General knowledge questions")
        print("   ❌ Avoid for: Company-specific or current information")
        
        print("\n🔍 RAG (Retrieval-Augmented Generation):")
        print("   ✅ Use for: Company policies, documentation, current data")
        print("   ✅ Best for: Frequently changing information")
        print("   ✅ Can provide: Source citations and transparency")
        print("   ⚡ Requires: Document ingestion, indexing, and retrieval")
        
        print("\n🎯 Fine-tuning:")
        print("   ✅ Use for: Specialized tone, style, or behavior")
        print("   ✅ Best for: Consistent behavior on represented tasks")
        print("   ⚠️  Time investment: Requires data prep and training")
        print("   ⚠️  Not a knowledge lookup mechanism; use RAG for changing facts")
        
        print("\n🚀 Hybrid Approach (RAG + Fine-tuning):")
        print("   ✅ Combine both: Fine-tune for tone/style + RAG for current facts")
        print("   ✅ Best of both worlds!")
        
        print("\n" + "=" * 70)
        print("✅ Comparison complete!")
        print("=" * 70 + "\n")

def main():
    """Run the comparison demo"""
    parser = argparse.ArgumentParser(description="Compare base, RAG, and fine-tuned approaches")
    parser.add_argument("--once", help="Run one comparison query and exit")
    args = parser.parse_args()
    
    # Test queries - use the same query across all three approaches
    test_queries = [
        "What is the refund policy for credit cards?",
        "What are the requirements to open a high-yield savings account?",
        "How do I escalate a complaint?"
    ]
    
    print("\n🎯 This demo compares three AI approaches:")
    print("   1. Base GPT-4o (generic AI)")
    print("   2. RAG-enhanced (grounded in your documents)")
    print("   3. Fine-tuned (specialized expertise)")
    print("\n" + "=" * 70)
    
    demo = ComparisonDemo()
    if args.once:
        demo.run_comparison(args.once)
        return
    
    # Run comparison for first query
    demo.run_comparison(test_queries[0])
    
    # Offer to test more queries
    print("\n📝 Want to test another query?")
    print("Available test queries:")
    for i, q in enumerate(test_queries[1:], 2):
        print(f"   {i}. {q}")
    print("   Or type your own question")
    print("   Type 'exit' to quit\n")
    
    while True:
        user_input = input("Your choice (number or question): ").strip()
        
        if user_input.lower() == 'exit':
            print("\n👋 Thanks for exploring AI approaches!")
            break
            
        # Check if it's a number
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(test_queries):
                query = test_queries[idx]
            else:
                print("❌ Invalid choice. Try again.")
                continue
        else:
            query = user_input
            
        demo.run_comparison(query)
        print("\n" + "=" * 70)
        print("Type another question, a number, or 'exit' to quit")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Demo interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
