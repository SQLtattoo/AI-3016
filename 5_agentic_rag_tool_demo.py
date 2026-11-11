#!/usr/bin/env python3
"""
AI-3016 Demo 5: Application-Orchestrated RAG Tool Workflow

This demo shows tool implementations that can support an agentic workflow. For
deterministic classroom output, the application calls a fixed sequence of tools
and asks the model to compose a grounded final answer from their results.
"""

import argparse
import json
import os
from datetime import date, timedelta
from typing import Any, Dict, List

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv

from azure_openai_auth import create_azure_openai_client, clean_env_value


load_dotenv()


def add_business_days(start: date, business_days: int) -> date:
    current = start
    remaining = business_days
    while remaining > 0:
        current += timedelta(days=1)
        if current.weekday() < 5:
            remaining -= 1
    return current


def get_search_client() -> SearchClient:
    return SearchClient(
        endpoint=clean_env_value("AZURE_SEARCH_ENDPOINT"),
        index_name=clean_env_value("AZURE_SEARCH_INDEX", "rag-bank-documents"),
        credential=AzureKeyCredential(clean_env_value("AZURE_SEARCH_ADMIN_KEY")),
    )


class AgenticRagDemo:
    def __init__(self) -> None:
        self.openai_client = create_azure_openai_client(api_version="2024-05-01-preview")
        self.search_client = get_search_client()
        self.chat_model = clean_env_value("DEPLOYMENT_NAME", "gpt-4o")
        self.embedding_model = clean_env_value("AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME", "text-embedding-ada-002")

    def get_embedding(self, text: str) -> List[float]:
        response = self.openai_client.embeddings.create(model=self.embedding_model, input=text)
        return response.data[0].embedding

    def search_bank_knowledge(self, query: str) -> Dict[str, Any]:
        vector = self.get_embedding(query)
        results = self.search_client.search(
            search_text=query,
            vector_queries=[VectorizedQuery(vector=vector, k_nearest_neighbors=3, fields="content_vector")],
            select=["title", "content"],
            top=3,
        )

        documents = []
        for result in results:
            documents.append({
                "title": result["title"],
                "snippet": result["content"][:900],
                "score": result.get("@search.score"),
            })
        return {"documents": documents}

    def calculate_refund_timeline(self, merchant_approved: bool = True, days_since_approval: int = 0) -> Dict[str, Any]:
        start = date.today() - timedelta(days=max(days_since_approval, 0))
        if not merchant_approved:
            return {
                "status": "waiting_on_merchant",
                "message": "The refund clock starts after merchant approval.",
            }

        standard_start = add_business_days(start, 5)
        standard_end = add_business_days(start, 7)
        holiday_end = add_business_days(start, 14)
        return {
            "status": "approved",
            "standard_window": f"{standard_start.isoformat()} to {standard_end.isoformat()}",
            "holiday_or_peak_window_end": holiday_end.isoformat(),
        }

    def build_escalation_plan(self, issue: str, urgency: str = "normal") -> Dict[str, Any]:
        channel = "customer service"
        if urgency.lower() in {"urgent", "fraud", "stolen_card"}:
            channel = "24/7 emergency card services"

        return {
            "issue": issue,
            "recommended_channel": channel,
            "steps": [
                "Confirm customer identity.",
                "Summarize the policy-grounded answer.",
                "Open a case with the retrieved source documents attached.",
                "Set follow-up expectations before ending the conversation.",
            ],
        }

    def tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_bank_knowledge",
                    "description": "Search official bank policy and product documents.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_refund_timeline",
                    "description": "Calculate the likely credit-card refund window.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "merchant_approved": {"type": "boolean"},
                            "days_since_approval": {"type": "integer", "minimum": 0},
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "build_escalation_plan",
                    "description": "Create an operations escalation plan for a banking issue.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "urgency": {"type": "string"},
                        },
                        "required": ["issue"],
                    },
                },
            },
        ]

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_map = {
            "search_bank_knowledge": self.search_bank_knowledge,
            "calculate_refund_timeline": self.calculate_refund_timeline,
            "build_escalation_plan": self.build_escalation_plan,
        }
        return tool_map[name](**arguments)

    def run(self, question: str) -> str:
        print("AI-3016 Demo 5: Application-Orchestrated RAG Tool Workflow")
        print("=" * 60)
        print(f"Customer: {question}\n")

        tool_results = [
            ("search_bank_knowledge", {"query": "credit card refund policy and escalation customer service"}),
            ("calculate_refund_timeline", {"merchant_approved": True, "days_since_approval": 3}),
            ("build_escalation_plan", {"issue": "Credit-card refund not received after merchant approval", "urgency": "normal"}),
        ]

        grounded_context = []
        for tool_name, args in tool_results:
            print(f"Tool call: {tool_name}({json.dumps(args)})")
            result = self.execute_tool(tool_name, args)
            print(f"Tool result: {json.dumps(result)[:500]}\n")
            grounded_context.append({"tool": tool_name, "arguments": args, "result": result})

        messages: List[Dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are an agentic banking operations assistant. Answer only from the "
                    "provided tool results. Preserve exact policy time windows and cite the "
                    "source document titles or tool names used."
                ),
            },
            {
                "role": "user",
                "content": f"Customer question: {question}\n\nTool results:\n{json.dumps(grounded_context, indent=2)}",
            },
        ]

        response = self.openai_client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=0.2,
            max_tokens=700,
        )
        answer = response.choices[0].message.content
        if not answer:
            raise RuntimeError("The RAG tool workflow returned an empty answer.")
        print("Assistant final answer:")
        print(answer)
        return answer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an application-orchestrated RAG tool workflow")
    parser.add_argument(
        "--question",
        default=(
            "A customer says their merchant approved a credit-card refund three days ago, "
            "but they also want to know how to escalate if it does not arrive."
        ),
    )
    args = parser.parse_args()
    AgenticRagDemo().run(args.question)


if __name__ == "__main__":
    main()