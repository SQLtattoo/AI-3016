#!/usr/bin/env python3
"""Demo 2C: Search retrieval and grounded Azure OpenAI answers."""

import sys

from azure.core.exceptions import AzureError
from dotenv import load_dotenv
from openai import OpenAIError

from azure_openai_auth import create_azure_openai_client
from rag_grounding import answer_with_search


load_dotenv()


def demonstrate_rag_api() -> None:
    print("AI-3016: Azure AI Search + Azure OpenAI RAG")
    print("Azure OpenAI On Your Data is retired; retrieval is now application-managed.")
    with create_azure_openai_client(api_version="2024-05-01-preview") as client:
        for question in (
            "What are your current CD rates and terms?",
            "Tell me about overdraft protection options",
        ):
            answer, sources = answer_with_search(client, question)
            print(f"\nQuestion: {question}\nAnswer: {answer}")
            print(f"Retrieved sources: {', '.join(sources)}")


def show_summary() -> None:
    print("\nRAG: embed the question, retrieve Search evidence, then generate a grounded answer.")
    print("Source titles come from the actual retrieved documents, not model-generated metadata.")


def main() -> int:
    try:
        demonstrate_rag_api()
        show_summary()
        return 0
    except (AzureError, OpenAIError, OSError, RuntimeError, ValueError) as exc:
        print(f"RAG demo FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
