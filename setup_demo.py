"""
AI-3016 Demo Setup Guide
=======================

This guide helps you set up the Azure resources and environment 
needed for the fine-tuning and RAG pattern demos.
"""

import os
import subprocess
import sys
from pathlib import Path

def install_requirements():
    """Install required Python packages"""
    print("📦 Installing Python requirements...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("✅ Requirements installed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False
    return True

def create_env_template():
    """Create environment variables template"""
    print("📝 Creating environment template...")
    
    env_template = """# Microsoft Foundry Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_AI_PROJECT_NAME=your-ai-project-name

# Azure OpenAI Configuration (for your deployed models)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key

# Azure Search Configuration (for RAG demo)
AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net
AZURE_SEARCH_KEY=your-search-admin-key

# Optional: For local development
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
"""
    
    with open(".env.template", "w") as f:
        f.write(env_template)
    
    print("✅ Created .env.template file")
    print("📝 Please copy this to .env and fill in your Azure details")

def check_azure_resources():
    """Guide for setting up Azure resources"""
    print("\n🔧 Azure Resources Setup Guide")
    print("=" * 50)
    
    resources = [
        {
            "name": "Microsoft Foundry Project",
            "description": "Create an AI Foundry project in Azure portal",
            "steps": [
                "1. Go to https://ai.azure.com/",
                "2. Create a new project or use existing one",
                "3. Note the project name, resource group, and subscription ID",
                "4. Deploy GPT-4o model for chat completion",
                "5. Deploy text-embedding-ada-002 for embeddings"
            ]
        },
        {
            "name": "Azure AI Search Service", 
            "description": "Create search service for RAG demo",
            "steps": [
                "1. Go to Azure portal",
                "2. Create new Azure AI Search service",
                "3. Choose appropriate pricing tier (Basic or higher for vector search)",
                "4. Note the endpoint URL and admin key"
            ]
        },
        {
            "name": "Authentication Setup",
            "description": "Configure authentication",
            "steps": [
                "1. Use Azure CLI: az login",
                "2. Or create service principal for app authentication",
                "3. Or use managed identity if running on Azure"
            ]
        }
    ]
    
    for resource in resources:
        print(f"\n📋 {resource['name']}")
        print(f"   {resource['description']}")
        for step in resource['steps']:
            print(f"   {step}")

def verify_setup():
    """Verify that setup is complete"""
    print("\n🔍 Verifying setup...")
    
    # Check if .env file exists
    if not os.path.exists(".env"):
        print("❌ .env file not found. Please create it from .env.template")
        return False
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  python-dotenv not installed, skipping .env file loading")
    
    # Check required environment variables
    required_vars = [
        "AZURE_SUBSCRIPTION_ID",
        "AZURE_RESOURCE_GROUP", 
        "AZURE_AI_PROJECT_NAME",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        return False
    
    print("✅ Environment variables configured!")
    
    # Test Azure connectivity
    print("🔗 Testing Azure connectivity...")
    try:
        from azure.identity import DefaultAzureCredential
        credential = DefaultAzureCredential()
        # This will raise an exception if auth is not configured
        print("✅ Azure authentication configured!")
    except Exception as e:
        print(f"⚠️  Azure authentication issue: {e}")
        print("   Please run 'az login' or configure service principal")
    
    return True

def main():
    """Run the complete setup process"""
    print("🎬 AI-3016 Demo Setup")
    print("=" * 30)
    
    # Step 1: Install requirements
    if not install_requirements():
        return
    
    # Step 2: Create environment template
    create_env_template()
    
    # Step 3: Show Azure resources guide
    check_azure_resources()
    
    # Step 4: Verify setup
    print("\n" + "=" * 50)
    print("⏳ Please complete the Azure setup steps above,")
    print("   then run this script again to verify configuration.")
    print("=" * 50)
    
    if verify_setup():
        print("\n🎉 Setup complete! You can now run the demos:")
        print("   • python 1_fine_tuning_demo.py")
        print("   • python 2_rag_pattern_demo.py")
    else:
        print("\n⚠️  Setup incomplete. Please check the requirements above.")

if __name__ == "__main__":
    main()