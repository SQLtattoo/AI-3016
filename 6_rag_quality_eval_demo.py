#!/usr/bin/env python3
"""
AI-3016 Demo 6: Lightweight RAG Quality Evaluation

This demo turns RAG into an engineering loop: run a small golden set, retrieve
evidence, generate answers, and score simple source and required-term checks.
These deterministic checks are useful signals, not a full groundedness evaluation.
"""

import json
from typing import Any, Dict, List

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv

from azure_openai_auth import create_azure_openai_client, clean_env_value


load_dotenv()


EVAL_CASES = [
    {
        "question": "How long do credit card refunds take after merchant approval?",
        "expected_source": "Bank Policies",
        "must_include": ["5-7", "business days"],
    },
    {
        "question": "What is the minimum deposit for a high-yield savings account?",
        "expected_source": "Investment Products",
        "must_include": ["$1,000", "3.2%"],
    },
    {
        "question": "Who should I call for emergency card services?",
        "expected_source": "Customer Service",
        "must_include": ["1-800-CARD-911", "24/7"],
    },
]


class RagQualityEvalDemo:
    def __init__(self) -> None:
        self.openai_client = create_azure_openai_client(api_version="2024-05-01-preview")
        self.search_client = SearchClient(
            endpoint=clean_env_value("AZURE_SEARCH_ENDPOINT"),
            index_name=clean_env_value("AZURE_SEARCH_INDEX", "rag-bank-documents"),
            credential=AzureKeyCredential(clean_env_value("AZURE_SEARCH_ADMIN_KEY")),
        )
        self.chat_model = clean_env_value("DEPLOYMENT_NAME", "gpt-4o")
        self.embedding_model = clean_env_value("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME", "text-embedding-ada-002")

    def get_embedding(self, text: str) -> List[float]:
        response = self.openai_client.embeddings.create(model=self.embedding_model, input=text)
        return response.data[0].embedding

    def retrieve(self, question: str) -> List[Dict[str, Any]]:
        vector = self.get_embedding(question)
        results = self.search_client.search(
            search_text=question,
            vector_queries=[VectorizedQuery(vector=vector, k_nearest_neighbors=3, fields="content_vector")],
            select=["title", "content"],
            top=3,
        )
        return [{"title": result["title"], "content": result["content"]} for result in results]

    def answer(self, question: str, docs: List[Dict[str, Any]]) -> str:
        context = "\n\n".join(f"Source: {doc['title']}\n{doc['content']}" for doc in docs)
        response = self.openai_client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Answer using only the supplied context. Include the source title "
                        "that supports the answer. Preserve exact numbers, phone numbers, "
                        "rates, and time windows from the source. If the context is insufficient, say so."
                    ),
                },
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
            ],
            temperature=0.1,
            max_tokens=350,
        )
        return response.choices[0].message.content or ""

    def score_case(self, case: Dict[str, Any]) -> Dict[str, Any]:
        docs = self.retrieve(case["question"])
        answer = self.answer(case["question"], docs)
        source_titles = [doc["title"] for doc in docs]
        source_hit = any(case["expected_source"].lower() in title.lower() for title in source_titles)
        answer_lower = answer.lower()
        required_hits = [term for term in case["must_include"] if term.lower() in answer_lower]
        grounded_score = int(source_hit) + len(required_hits)
        possible_score = 1 + len(case["must_include"])
        return {
            "question": case["question"],
            "top_sources": source_titles,
            "source_hit": source_hit,
            "required_hits": required_hits,
            "score": grounded_score / possible_score,
            "answer": answer,
        }

    def run(self) -> None:
        print("AI-3016 Demo 6: Lightweight RAG Quality Evaluation")
        print("=" * 60)
        results = [self.score_case(case) for case in EVAL_CASES]

        for index, result in enumerate(results, 1):
            print(f"\nCase {index}: {result['question']}")
            print(f"Sources: {', '.join(result['top_sources'])}")
            print(f"Source hit: {result['source_hit']}")
            print(f"Required terms found: {', '.join(result['required_hits']) or 'none'}")
            print(f"Score: {result['score']:.2f}")
            print(f"Answer: {result['answer'][:450]}")

        average = sum(result["score"] for result in results) / len(results)
        print("\nEvaluation summary")
        print(json.dumps({"cases": len(results), "average_score": round(average, 2)}, indent=2))
        if average < 0.75:
            raise SystemExit("Average RAG quality score below class-demo threshold")


if __name__ == "__main__":
    RagQualityEvalDemo().run()