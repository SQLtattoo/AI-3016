#!/usr/bin/env python3
"""
AI-3016 Demo 2D: RAG with Azure Key Vault for Secret Management

This demo shows how to use Azure Key Vault to securely retrieve API keys
instead of storing them in .env files.

Demonstrates:
- Azure Key Vault integration with AzureCliCredential for local demos
- Runtime retrieval of the Azure AI Search key instead of reading it from .env
- The same Azure OpenAI RAG request as 2c_rag_api_demo.py

Prerequisites:
- Microsoft Foundry with GPT-4o deployment
- Azure AI Search with rag-bank-documents index
- Azure Key Vault with stored secrets
- Azure CLI login (az login) for authentication

Usage:
    python 2d_rag_keyvault_demo.py
"""

import os
from dotenv import load_dotenv
from rag_grounding import answer_with_search
from azure.identity import AzureCliCredential
from azure.core.exceptions import HttpResponseError
from azure.keyvault.secrets import SecretClient
from azure_openai_auth import create_azure_openai_client

load_dotenv()

def get_secrets_from_keyvault():
    """Retrieve secrets from Azure Key Vault using the current Azure CLI login."""
    
    keyvault_uri = os.getenv("AZURE_KEY_VAULT_URI")
    
    if not keyvault_uri:
        print("❌ AZURE_KEY_VAULT_URI not found in .env")
        print("Fallback: Using API keys from .env file")
        return None
    
    print(f"🔐 Connecting to Key Vault: {keyvault_uri}")
    
    try:
        # Use the same Azure CLI login as azd/az for local classroom demos.
        credential = AzureCliCredential()
        client = SecretClient(vault_url=keyvault_uri, credential=credential)
        
        # Retrieve secrets
        secrets = {
            "search_admin_key": client.get_secret("AZURE-SEARCH-ADMIN-KEY").value,
            "endpoint_url": client.get_secret("ENDPOINT-URL").value,
            "openai_endpoint": client.get_secret("AZURE-OPENAI-ENDPOINT").value,
            "search_endpoint": client.get_secret("AZURE-SEARCH-ENDPOINT").value,
        }
        
        print("✅ Secrets retrieved from Key Vault")
        return secrets
        
    except HttpResponseError as e:
        print(f"⚠️  Key Vault access blocked: {e.error.code if e.error else e.status_code}")
        if e.message:
            print(f"   {e.message.splitlines()[0]}")
        print("Fallback: Using .env values and Microsoft Entra ID")
        return None
    except Exception as e:
        print(f"⚠️  Failed to retrieve secrets from Key Vault: {type(e).__name__}: {e}")
        print("Fallback: Using API keys from .env file")
        return None

def demonstrate_rag_with_keyvault():
    """Demonstrate Azure OpenAI RAG using Search settings from Key Vault."""
    
    print("🚀 Azure OpenAI RAG API Demo (with Key Vault)")
    print("=" * 50)
    
    # Try to get secrets from Key Vault
    secrets = get_secrets_from_keyvault()
    
    # The RAG request uses the Search endpoint and key from Key Vault when available.
    # The shared Azure OpenAI client still uses its environment configuration or Entra ID.
    if secrets:
        endpoint_url = secrets["endpoint_url"]
        search_endpoint = secrets["search_endpoint"]
        search_key = secrets["search_admin_key"]
        security_mode = "Key Vault secrets + Microsoft Entra ID"
    else:
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip('"')
        search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY", "").strip('"')
        security_mode = ".env fallback + Microsoft Entra ID"
    
    search_index = os.getenv("AZURE_SEARCH_INDEX", "rag-bank-documents")
    
    # Initialize client
    try:
        client = create_azure_openai_client(api_version="2024-05-01-preview")
        print("✅ Connected to the Azure OpenAI endpoint")
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Test questions
    questions = [
        "What is the refund policy for credit cards?"
    ]
    
    print("\n🔍 Testing RAG with banking questions...")
    print(f"🔐 Security mode: {security_mode}")
    
    for question in questions:
        print(f"\n❓ {question}")
        
        answer, sources = answer_with_search(
            client, question,
            search_endpoint=search_endpoint,
            search_key=search_key,
            index_name=search_index,
        )
        print(f"🤖 {answer}")
        print(f"📚 Retrieved sources: {', '.join(sources)}")
        
        print("-" * 60)

def show_summary():
    """Show demo summary."""
    print("\n🎯 RAG with Key Vault Demo Summary")
    print("=" * 40)
    print("✅ Demonstrates Key Vault retrieval when network/RBAC policy allows it")
    print("✅ Demonstrates safe fallback when Key Vault public access is blocked")
    print("✅ Azure OpenAI can use Microsoft Entra ID when local keys are disabled")
    print("✅ Uses AzureCliCredential (az login) for local classroom runs")
    print("✅ Automatic fallback to .env if Key Vault unavailable")
    print("\n🔐 Security Benefits:")
    print("   • Centralized handling for secrets used by the demo")
    print("   • Centralized secret management")
    print("   • Audit logs of secret access")
    print("   • RBAC controls who can access secrets")
    print("   • Supports centralized rotation without changing application code")
    print("\n📝 Compare with:")
    print("   • 2c_rag_api_demo.py - Uses .env file (dev only)")
    print("   • 2d_rag_keyvault_demo.py - Demonstrates runtime Key Vault retrieval")

def main():
    """Main demo execution."""
    print("🎓 AI-3016 RAG with Key Vault Demo")
    
    # Check required environment variables
    required_vars = ["DEPLOYMENT_NAME", "AZURE_SEARCH_INDEX"]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"❌ Missing variables in .env: {', '.join(missing)}")
        return
    
    print("✅ Configuration verified")
    
    # Run demo
    demonstrate_rag_with_keyvault()
    show_summary()

if __name__ == "__main__":
    main()
