#!/usr/bin/env python3
"""Create, populate, and verify the Azure AI Search index used by the demos."""

import math
import os
import sys
import time
from pathlib import Path
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError, HttpResponseError, ResourceNotFoundError
from azure.identity import AzureCliCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import VectorizedQuery
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from openai import OpenAIError, PermissionDeniedError

from azure_openai_auth import clean_env_value, create_azure_openai_client, has_usable_secret


ROOT = Path(__file__).resolve().parent
SOURCE_DIRECTORY = ROOT / "RAG-sources"
REQUIRED_SOURCES = {"bank_policies.txt", "customer_service.txt", "investment_products.txt"}
EMBEDDING_DIMENSIONS = 1536
load_dotenv(ROOT / ".env")


def create_search_index() -> tuple[SearchClient, SearchIndexClient]:
    endpoint = clean_env_value("AZURE_SEARCH_ENDPOINT")
    key = clean_env_value("AZURE_SEARCH_ADMIN_KEY")
    if not endpoint or not has_usable_secret(key):
        raise ValueError("Set AZURE_SEARCH_ENDPOINT and a valid AZURE_SEARCH_ADMIN_KEY.")

    name = clean_env_value("AZURE_SEARCH_INDEX", "rag-bank-documents")
    credential = AzureKeyCredential(key)
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.microsoft"),
        SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchableField(name="keywords", type=SearchFieldDataType.String),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            retrievable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="rag-vector-profile",
        ),
    ]
    vector_search = VectorSearch(
        profiles=[VectorSearchProfile(name="rag-vector-profile", algorithm_configuration_name="rag-algorithm-config")],
        algorithms=[HnswAlgorithmConfiguration(name="rag-algorithm-config")],
    )
    index_client.create_or_update_index(
        SearchIndex(name=name, fields=fields, vector_search=vector_search)
    )
    print(f"Search index created or updated: {name}")
    return SearchClient(endpoint=endpoint, index_name=name, credential=credential), index_client


def source_document(filename: str, content: str) -> dict[str, Any]:
    if not content.strip():
        raise ValueError(f"RAG source is empty: {filename}")
    return {
        "id": filename.removesuffix(".txt").replace("_", "-"),
        "title": filename.removesuffix(".txt").replace("_", " ").title(),
        "content": content,
        "category": "banking",
        "keywords": "",
    }


def get_documents_from_local_sources() -> list[dict[str, Any]]:
    files = sorted(SOURCE_DIRECTORY.glob("*.txt"))
    missing = REQUIRED_SOURCES - {path.name for path in files}
    if missing:
        raise ValueError(f"Missing required RAG sources: {', '.join(sorted(missing))}")
    return [source_document(path.name, path.read_text(encoding="utf-8")) for path in files]


def get_documents_from_storage() -> list[dict[str, Any]]:
    endpoint = clean_env_value("AZURE_STORAGE_ENDPOINT")
    if not endpoint:
        print("Storage endpoint is not configured; using local RAG-sources.")
        return []
    try:
        with AzureCliCredential() as credential, BlobServiceClient(
            account_url=endpoint, credential=credential
        ) as service:
            container = service.get_container_client(
                clean_env_value("AZURE_STORAGE_CONTAINER_NAME", "rag-sources")
            )
            return [
                source_document(blob.name, container.download_blob(blob.name).readall().decode("utf-8"))
                for blob in container.list_blobs()
                if blob.name.endswith(".txt")
            ]
    except HttpResponseError as exc:
        if exc.status_code not in (403, 404):
            raise
        print(
            f"WARNING: Storage read returned HTTP {exc.status_code}; using local "
            "RAG-sources. Local blob access is not verified by this fallback."
        )
        return []


def validate_embedding(embedding: list[float]) -> None:
    if (
        len(embedding) != EMBEDDING_DIMENSIONS
        or not all(
            isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
            for value in embedding
        )
        or not any(embedding)
    ):
        raise ValueError(
            f"Expected a finite, nonzero {EMBEDDING_DIMENSIONS}-dimension embedding. "
            "Choose a compatible embedding model; do not reuse an incompatible index."
        )


def generate_embeddings(text: str, openai_client: Any, deployment_name: str) -> list[float]:
    for attempt in range(12):
        try:
            embedding = openai_client.embeddings.create(
                model=deployment_name, input=text[:8000]
            ).data[0].embedding
            break
        except PermissionDeniedError:
            if attempt == 11:
                raise
            print(f"Embeddings returned HTTP 403; waiting for new RBAC assignments ({attempt + 1}/12).")
            time.sleep(10)
    validate_embedding(embedding)
    return embedding


def upload_documents(search_client: SearchClient, documents: list[dict[str, Any]]) -> bool:
    if not documents:
        raise ValueError("No RAG documents were supplied for indexing.")
    deployment = clean_env_value(
        "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME", "text-embedding-ada-002"
    )
    with create_azure_openai_client() as client:
        indexed = [
            {**doc, "content_vector": generate_embeddings(doc["content"], client, deployment)}
            for doc in documents
        ]
    results = search_client.upload_documents(indexed)
    failures = [f"{result.key}: {result.error_message}" for result in results if not result.succeeded]
    if failures or {result.key for result in results} != {doc["id"] for doc in documents}:
        raise RuntimeError(f"Incomplete Search upload: {'; '.join(failures) or 'missing document results'}")
    print(f"Uploaded all {len(indexed)} documents with {EMBEDDING_DIMENSIONS}-dimension embeddings.")
    return True


def verify_search_index(
    search_client: SearchClient,
    documents: list[dict[str, Any]],
    attempts: int = 12,
    delay: float = 5,
) -> None:
    if not documents or attempts < 1:
        raise ValueError("Verification needs source documents and at least one attempt.")
    problem = ""
    for attempt in range(attempts):
        try:
            for expected in documents:
                stored = search_client.get_document(expected["id"])
                if stored.get("content") != expected["content"] or stored.get("title") != expected["title"]:
                    raise RuntimeError(f"Missing or stale indexed content: {expected['id']}")
                embedding = stored.get("content_vector", [])
                validate_embedding(embedding)
                hits = list(search_client.search(
                    vector_queries=[VectorizedQuery(
                        vector=embedding, k_nearest_neighbors=1, fields="content_vector"
                    )],
                    select=["id"],
                    top=1,
                ))
                if not hits or hits[0]["id"] != expected["id"]:
                    raise RuntimeError(f"Vector retrieval did not find {expected['id']}")
            print(f"Verified content, embeddings, and vector retrieval for all {len(documents)} source documents.")
            return
        except (ResourceNotFoundError, RuntimeError, ValueError) as exc:
            problem = str(exc)
            if attempt + 1 < attempts:
                print(f"Waiting for Search index visibility ({attempt + 1}/{attempts}): {problem}")
                time.sleep(delay)
    raise RuntimeError(f"Search index is not ready after {attempts} checks: {problem}")


def main() -> int:
    try:
        local_documents = get_documents_from_local_sources()
        stored_documents = get_documents_from_storage()
        local_content = {doc["id"]: doc["content"] for doc in local_documents}
        stored_content = {doc["id"]: doc["content"] for doc in stored_documents}
        if stored_content != local_content:
            print("Storage sources are absent or differ from the repository; indexing local RAG-sources.")
        documents = stored_documents if stored_content == local_content else local_documents
        search_client, index_client = create_search_index()
        with search_client, index_client:
            upload_documents(search_client, documents)
            verify_search_index(search_client, documents)
        print("RAG index setup complete.")
        return 0
    except (AzureError, OpenAIError, OSError, RuntimeError, ValueError) as exc:
        print(f"RAG index setup FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
