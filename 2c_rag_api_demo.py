#!/usr/bin/env python3
"""
AI-3016 Demo 2C: Azure OpenAI RAG with an Azure AI Search Data Source
Demonstrates programmatic RAG using the Azure OpenAI Chat Completions API.
"""

import os
from dotenv import load_dotenv
from azure_openai_auth import create_azure_openai_client, clean_env_value

load_dotenv()

def demonstrate_rag_api():
    """Demonstrate Azure OpenAI RAG with an Azure AI Search data source."""
    
    print("🚀 Azure OpenAI RAG API Demo")
    print("=" * 40)
    
    # Initialize client
    try:
        # Uses API-key auth when available, otherwise Microsoft Entra ID.
        client = create_azure_openai_client(api_version="2024-05-01-preview")
        print("✅ Connected to Azure OpenAI")
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return
    
    # Test questions
    questions = [
        "What are your current CD rates and terms?",
        "Tell me about overdraft protection options"
    ]
    
    print("\n🔍 Testing RAG with banking questions...")
    
    for question in questions:
        print(f"\n❓ {question}")
        
        try:
            response = client.chat.completions.create(
                model=clean_env_value("DEPLOYMENT_NAME"),
                messages=[
                    {"role": "system", "content": "You are a helpful banking assistant."},
                    {"role": "user", "content": question}
                ],
                extra_body={
                    "data_sources": [{
                        "type": "azure_search",
                        "parameters": {
                            "endpoint": clean_env_value("AZURE_SEARCH_ENDPOINT"),
                            "index_name": clean_env_value("AZURE_SEARCH_INDEX"),
                            "authentication": {
                                "type": "api_key",
                                "key": clean_env_value("AZURE_SEARCH_ADMIN_KEY")
                            },
                            "top_n_documents": 1,
                            "in_scope": True,
                            "strictness": 3
                        }
                    }]
                }
            )
            
            print(f"🤖 {response.choices[0].message.content}")
            
            # Show sources if available
            if hasattr(response.choices[0].message, 'context'):
                citations = response.choices[0].message.context.get('citations', [])
                if citations:
                    print("📚 Sources:")
                    for citation in citations:
                        print(f"   • {citation.get('title', 'Document')}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("-" * 50)

def show_summary():
    """Show demo summary."""
    print("\n🎯 RAG API Demo Summary")
    print("=" * 30)
    print("✅ Programmatic RAG with Azure OpenAI and Azure AI Search")
    print("✅ Managed document retrieval with citation metadata when returned")
    print("✅ Simple integration with extra_body parameter")
    print("\nCompare with:")
    print("   • 2a_rag_portal_guide.md - Portal approach")
    print("   • 2b_rag_code_first.py - Manual pipeline")

def main():
    """Main demo execution."""
    print("🎓 AI-3016 RAG API Demo")
    
    # Check required environment variables
    required_vars = ["AZURE_OPENAI_ENDPOINT", "DEPLOYMENT_NAME",
                    "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_ADMIN_KEY", "AZURE_SEARCH_INDEX"]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Missing variables: {', '.join(missing)}")
        return
    
    print("✅ Configuration verified")
    
    # Run demo
    demonstrate_rag_api()
    show_summary()

if __name__ == "__main__":
    main()