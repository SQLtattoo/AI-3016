#!/usr/bin/env python3
"""AI-3016 Demo 8: Microsoft Foundry Responses API tool calling.

Demonstrates three Foundry-hosted tools and one application-hosted function
using the same model deployment:

    python 8_foundry_tool_calling_demo.py --tool all
    python 8_foundry_tool_calling_demo.py --tool code_interpreter
    python 8_foundry_tool_calling_demo.py --tool web_search
    python 8_foundry_tool_calling_demo.py --tool file_search
    python 8_foundry_tool_calling_demo.py --tool function
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from azure_openai_auth import clean_env_value, normalize_project_endpoint


load_dotenv()

SOURCE_DIRECTORY = Path(__file__).resolve().parent / "RAG-sources"
SYSTEM_PROMPT = (
    "You are Aria, a concise banking education assistant. Clearly distinguish "
    "facts returned by tools from general explanation. Never request or invent "
    "customer credentials or account details."
)


class FoundryToolCallingDemo:
    """Show hosted and local tools through one Responses API model deployment."""

    def __init__(self) -> None:
        endpoint = clean_env_value("AZURE_AI_PROJECT_ENDPOINT")
        if not endpoint:
            raise RuntimeError(
                "AZURE_AI_PROJECT_ENDPOINT is not set. Run `azd up` to generate "
                ".env, then run `az login`."
            )

        endpoint = normalize_project_endpoint(endpoint)

        from azure.ai.projects import AIProjectClient

        self.project_client = AIProjectClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential(
                exclude_environment_credential=True,
                exclude_managed_identity_credential=True,
            ),
        )
        self.client = self.project_client.get_openai_client()
        self.model = clean_env_value("DEPLOYMENT_NAME", "gpt-4o")
        self.vector_store_id: Optional[str] = None
        self.uploaded_file_ids: List[str] = []

    @staticmethod
    def get_customer_service_channel(
        issue_type: str, urgency: str = "normal"
    ) -> Dict[str, Any]:
        """Return a deterministic local routing result for the function demo."""
        issue = issue_type.strip().lower().replace("-", "_").replace(" ", "_")
        urgent = urgency.strip().lower() in {"urgent", "high", "emergency"}

        if issue in {"fraud", "stolen_card", "lost_card"} or urgent:
            return {
                "channel": "24/7 emergency card services",
                "availability": "24 hours a day",
                "priority": "immediate",
            }
        if issue in {"mortgage", "loan", "investment"}:
            return {
                "channel": "specialist appointment desk",
                "availability": "business hours",
                "priority": "scheduled",
            }
        return {
            "channel": "general customer service",
            "availability": "business hours",
            "priority": "standard",
        }

    @staticmethod
    def _print_response(response: Any) -> None:
        item_types = [getattr(item, "type", type(item).__name__) for item in response.output]
        print(f"Response items: {', '.join(item_types)}")
        for item in response.output:
            if item.type == "code_interpreter_call" and item.code:
                print("Generated Python:")
                print(item.code)
            if item.type == "web_search_call":
                print(f"Web search action: {item.action.type}")
            for content in getattr(item, "content", []):
                for annotation in getattr(content, "annotations", []):
                    if annotation.type == "file_citation":
                        print(f"File citation: {annotation.filename}")
                    elif annotation.type == "url_citation":
                        print(f"Web citation: {annotation.title} - {annotation.url}")
        print("Assistant:")
        print(response.output_text or "[No text response]")

    def _create_response(
        self,
        prompt: str,
        tools: Iterable[Dict[str, Any]],
        previous_response_id: Optional[str] = None,
        input_items: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        request: Dict[str, Any] = {
            "model": self.model,
            "instructions": SYSTEM_PROMPT,
            "input": input_items if input_items is not None else prompt,
            "tools": list(tools),
        }
        if previous_response_id:
            request["previous_response_id"] = previous_response_id
        response = self.client.responses.create(**request)
        if response.status != "completed" or response.error:
            raise RuntimeError(f"Response failed: {response.error or response.status}")
        return response

    def run_code_interpreter(self) -> None:
        print("\n1. Code Interpreter")
        print("Execution: hosted by Microsoft Foundry")
        tool = {"type": "code_interpreter", "container": {"type": "auto"}}
        response = self._create_response(
            "Use Python to calculate the monthly payment and total interest for a "
            "$250,000, 30-year loan at 6.5% annual interest. Show the formula and "
            "round monetary values to two decimals.",
            [tool],
        )
        if not any(item.type == "code_interpreter_call" for item in response.output):
            raise RuntimeError("The model did not execute Code Interpreter.")
        self._print_response(response)

    def run_web_search(self) -> None:
        print("\n2. Web Search")
        print("Execution: hosted by Microsoft Foundry")
        tool = {"type": "web_search"}
        response = self._create_response(
            "Search the web for the current United States prime rate. Prefer an "
            "authoritative banking source, state the publication date, and cite it.",
            [tool],
        )
        if not any(item.type == "web_search_call" for item in response.output):
            raise RuntimeError("The model did not execute web search.")
        self._print_response(response)

    def _prepare_file_search(self) -> str:
        if self.vector_store_id:
            return self.vector_store_id

        source_files = sorted(SOURCE_DIRECTORY.glob("*.txt"))
        if not source_files:
            raise RuntimeError(f"No .txt files found in {SOURCE_DIRECTORY}")

        vector_store = self.client.vector_stores.create(name="ai3016-demo-8")
        self.vector_store_id = vector_store.id
        print(f"Created temporary vector store: {vector_store.id}")

        for source_path in source_files:
            with source_path.open("rb") as source:
                uploaded = self.client.vector_stores.files.upload_and_poll(
                    vector_store_id=vector_store.id,
                    file=source,
                )
            self.uploaded_file_ids.append(uploaded.id)
            print(f"Uploaded: {source_path.name}")

        return vector_store.id

    def run_file_search(self) -> None:
        print("\n3. File Search")
        print("Execution: hosted by Microsoft Foundry")
        vector_store_id = self._prepare_file_search()
        tool = {
            "type": "file_search",
            "vector_store_ids": [vector_store_id],
            "max_num_results": 3,
        }
        response = self._create_response(
            "According to the uploaded bank documents, how long can a credit-card "
            "refund take? Cite the source file and do not use outside knowledge.",
            [tool],
        )
        if not any(
            annotation.type == "file_citation"
            for item in response.output
            for content in getattr(item, "content", [])
            for annotation in getattr(content, "annotations", [])
        ):
            raise RuntimeError("File search returned no source-file citations.")
        self._print_response(response)

    def run_function(self) -> None:
        print("\n4. Function Calling")
        print("Execution: function selected by the model, run by this Python application")
        tool = {
            "type": "function",
            "name": "get_customer_service_channel",
            "description": "Find the right support channel for a banking issue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "issue_type": {
                        "type": "string",
                        "description": "The banking issue, such as fraud or mortgage.",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["normal", "high", "urgent"],
                    },
                },
                "required": ["issue_type", "urgency"],
                "additionalProperties": False,
            },
            "strict": True,
        }

        response = self._create_response(
            "My card was stolen and I need help immediately. Which service channel "
            "should I use? Call the provided function before answering.",
            [tool],
        )

        executed = False
        for _ in range(4):
            calls = [item for item in response.output if item.type == "function_call"]
            if not calls:
                if not executed or not response.output_text:
                    raise RuntimeError("Function demo did not execute a local function and produce an answer.")
                self._print_response(response)
                return

            outputs = []
            for call in calls:
                arguments = json.loads(call.arguments)
                print(f"Function call: {call.name}({json.dumps(arguments)})")
                if call.name != "get_customer_service_channel":
                    result = {"error": f"Unknown function: {call.name}"}
                else:
                    result = self.get_customer_service_channel(**arguments)
                    executed = True
                print(f"Local result: {json.dumps(result)}")
                outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call.call_id,
                        "output": json.dumps(result),
                    }
                )

            response = self._create_response(
                "", [tool], previous_response_id=response.id, input_items=outputs
            )

        raise RuntimeError("Function calling exceeded four response rounds.")

    def cleanup(self) -> None:
        if not self.vector_store_id:
            return

        print("\nCleaning up temporary file-search resources...")
        self.client.vector_stores.delete(self.vector_store_id)
        for file_id in self.uploaded_file_ids:
            self.client.files.delete(file_id)
        self.vector_store_id = None
        self.uploaded_file_ids.clear()

    def run(self, selected_tool: str, keep_resources: bool = False) -> None:
        runners = {
            "code_interpreter": self.run_code_interpreter,
            "web_search": self.run_web_search,
            "file_search": self.run_file_search,
            "function": self.run_function,
        }
        selected = list(runners) if selected_tool == "all" else [selected_tool]

        print("AI-3016 Demo 8: Responses API Tool Calling")
        print(f"Model deployment: {self.model}")
        try:
            for tool_name in selected:
                runners[tool_name]()
        finally:
            try:
                if not keep_resources:
                    self.cleanup()
            finally:
                self.client.close()
                self.project_client.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show Foundry-hosted tools and local function calling"
    )
    parser.add_argument(
        "--tool",
        choices=["all", "code_interpreter", "web_search", "file_search", "function"],
        default="all",
        help="Run one tool scenario or all scenarios",
    )
    parser.add_argument(
        "--keep-resources",
        action="store_true",
        help="Keep temporary file-search resources for inspection",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List scenarios without connecting to Azure",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.list:
        print("code_interpreter\nweb_search\nfile_search\nfunction")
        return

    demo: Optional[FoundryToolCallingDemo] = None
    try:
        demo = FoundryToolCallingDemo()
        demo.run(args.tool, args.keep_resources)
    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as exc:
        raise SystemExit(f"Demo failed: {exc}") from exc


if __name__ == "__main__":
    main()
