#!/usr/bin/env python3
"""
Setup Azure AI Search Index for RAG Demo
Creates the rag-bank-documents index and populates it with documents from blob storage.
"""

import os
from dotenv import load_dotenv
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    SimpleField, SearchableField, VectorSearch,
    VectorSearchProfile, HnswAlgorithmConfiguration
)
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from azure_openai_auth import create_azure_openai_client

load_dotenv()

def create_search_index():
    """Create the Azure AI Search index with vector search capabilities."""
    print("📊 Creating Azure AI Search index...")
    
    search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    search_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
    index_name = os.getenv("AZURE_SEARCH_INDEX", "rag-bank-documents")
    
    if not search_endpoint or not search_key:
        print("❌ Missing Azure Search credentials in .env")
        return None, None
    
    credential = AzureKeyCredential(search_key)
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    
    # Define index schema
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="keywords", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,  # text-embedding-ada-002
            vector_search_profile_name="rag-vector-profile"
        )
    ]
    
    # Configure vector search
    vector_search = VectorSearch(
        profiles=[
            VectorSearchProfile(
                name="rag-vector-profile",
                algorithm_configuration_name="rag-algorithm-config"
            )
        ],
        algorithms=[
            HnswAlgorithmConfiguration(name="rag-algorithm-config")
        ]
    )
    
    # Create the index
    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    
    try:
        result = index_client.create_or_update_index(index)
        print(f"✅ Index created: {result.name}")
        
        # Return search client for document upload
        search_client = SearchClient(endpoint=search_endpoint, index_name=index_name, credential=credential)
        return search_client, index_client
    except Exception as e:
        print(f"❌ Failed to create index: {str(e)}")
        return None, None

def get_documents_from_storage():
    """Read documents from Azure Storage blob container."""
    print("📥 Reading documents from Azure Storage...")
    
    storage_account = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "rag-sources")
    storage_endpoint = os.getenv("AZURE_STORAGE_ENDPOINT")
    
    if not storage_account or not storage_endpoint:
        print("❌ Missing storage configuration in .env")
        return []
    
    try:
        # Use AzureCliCredential for authentication (simpler, uses 'az login')
        from azure.identity import AzureCliCredential
        credential = AzureCliCredential()
        
        blob_service_client = BlobServiceClient(
            account_url=storage_endpoint,
            credential=credential
        )
        
        container_client = blob_service_client.get_container_client(container_name)
        
        documents = []
        blob_list = container_client.list_blobs()
        
        for blob in blob_list:
            if blob.name.endswith('.txt'):
                blob_client = container_client.get_blob_client(blob.name)
                content = blob_client.download_blob().readall().decode('utf-8')
                
                # Create document structure
                doc_id = blob.name.replace('.txt', '').replace('_', '-')
                doc = {
                    'id': doc_id,
                    'title': blob.name.replace('_', ' ').replace('.txt', '').title(),
                    'content': content,
                    'category': 'banking',
                    'keywords': []
                }
                documents.append(doc)
                print(f"   ✅ Read: {blob.name}")
        
        print(f"✅ Found {len(documents)} documents in storage")
        return documents
        
    except Exception as e:
        print(f"❌ Failed to read from storage: {str(e)}")
        return []

def get_documents_from_local_sources():
    """Read documents from the local RAG-sources folder."""
    print("📥 Reading documents from local RAG-sources folder...")

    sources_path = os.path.join(os.path.dirname(__file__), "RAG-sources")
    if not os.path.isdir(sources_path):
        print(f"❌ Local RAG-sources folder not found: {sources_path}")
        return []

    documents = []
    for filename in sorted(os.listdir(sources_path)):
        if not filename.endswith(".txt"):
            continue

        file_path = os.path.join(sources_path, filename)
        with open(file_path, "r", encoding="utf-8") as source_file:
            content = source_file.read()

        documents.append({
            "id": filename.replace(".txt", "").replace("_", "-"),
            "title": filename.replace("_", " ").replace(".txt", "").title(),
            "content": content,
            "category": "banking",
            "keywords": []
        })
        print(f"   ✅ Read: {filename}")

    print(f"✅ Found {len(documents)} local documents")
    return documents

def generate_embeddings(text, openai_client, deployment_name):
    """Generate vector embeddings for text."""
    try:
        response = openai_client.embeddings.create(
            model=deployment_name,
            input=text[:8000]  # Limit to avoid token limits
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"⚠️  Failed to generate embedding: {str(e)}")
        return None

def upload_documents(search_client, documents):
    """Upload documents with embeddings to search index."""
    print("📤 Uploading documents to search index...")
    
    # Initialize OpenAI client for embeddings - supports API key or Microsoft Entra ID
    embeddings_deployment = os.getenv("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME", "text-embedding-ada-002")

    print(f"   Using embeddings deployment: {embeddings_deployment}")
    
    try:
        openai_client = create_azure_openai_client(api_version="2024-05-01-preview")
        
        documents_to_upload = []
        
        for doc in documents:
            print(f"   Processing: {doc['title']}")
            
            # Generate embedding
            embedding = generate_embeddings(doc['content'], openai_client, embeddings_deployment)
            
            if embedding:
                search_doc = {
                    "id": doc["id"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "category": doc["category"],
                    "content_vector": embedding
                }
                documents_to_upload.append(search_doc)
                print(f"      ✅ Embedding generated ({len(embedding)} dims)")
            else:
                print(f"      ⚠️  Skipping (no embedding)")
        
        if documents_to_upload:
            result = search_client.upload_documents(documents_to_upload)
            success_count = sum(1 for r in result if r.succeeded)
            print(f"✅ Uploaded {success_count}/{len(documents_to_upload)} documents to index")
            return True
        else:
            print("❌ No documents to upload")
            return False
            
    except Exception as e:
        print(f"❌ Failed to upload documents: {str(e)}")
        return False

def main():
    """Main setup function."""
    print("🚀 Azure AI Search Index Setup for RAG Demo")
    print("=" * 50)
    
    # Step 1: Create search index
    search_client, index_client = create_search_index()
    if not search_client:
        print("\n❌ Setup failed at index creation")
        return
    
    # Step 2: Get documents from storage
    documents = get_documents_from_storage()
    if not documents:
        print("\n⚠️  No documents found in storage; falling back to local RAG-sources")
        documents = get_documents_from_local_sources()
        if not documents:
            print("\n❌ No documents found for indexing")
            return
    
    # Step 3: Upload documents with embeddings
    if upload_documents(search_client, documents):
        print("\n🎉 Search index setup complete!")
        print(f"\nYour index '{os.getenv('AZURE_SEARCH_INDEX', 'rag-bank-documents')}' is ready.")
        print("\nNext steps:")
        print("  1. Run: python 2c_rag_api_demo.py")
        print("  2. Run: python 3_chat_client_demo.py")
    else:
        print("\n❌ Setup failed at document upload")

if __name__ == "__main__":
    main()
