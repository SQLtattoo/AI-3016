#!/usr/bin/env python3
"""Verify the deployed services and actual demo paths; exit nonzero on failure."""

import argparse
import asyncio
import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.search.documents import SearchClient
from dotenv import load_dotenv
from openai import OpenAIError

from azure_openai_auth import clean_env_value, create_azure_openai_client
from rag_grounding import answer_with_search
from setup_search_index import get_documents_from_local_sources, verify_search_index


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def require(condition: Any, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def check_search() -> None:
    with SearchClient(
        endpoint=clean_env_value("AZURE_SEARCH_ENDPOINT"),
        index_name=clean_env_value("AZURE_SEARCH_INDEX", "rag-bank-documents"),
        credential=AzureKeyCredential(clean_env_value("AZURE_SEARCH_ADMIN_KEY")),
    ) as client:
        documents = get_documents_from_local_sources()
        verify_search_index(client, documents)
        require(client.get_document_count() == len(documents), "The index contains missing or unexpected documents.")
    print("PASS: Search has exactly the repository documents, valid embeddings, and working vector retrieval.")


def check_chat_and_rag() -> None:
    model = clean_env_value("DEPLOYMENT_NAME", "gpt-4o")
    with create_azure_openai_client() as client:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with a short greeting."}],
            max_tokens=50,
        )
        require(response.choices[0].message.content, "Chat Completions returned no answer.")
        answer, sources = answer_with_search(
            client, "According to the bank policy, how long do credit-card refunds take?",
        )
        require(
            "business days" in answer.lower() and any("Bank Policies" in title for title in sources),
            "Application-managed RAG did not return the refund policy and its source.",
        )
    print("PASS: Chat Completions and application-managed Search RAG with source provenance.")


def check_project_and_responses() -> None:
    with DefaultAzureCredential(
        exclude_environment_credential=True, exclude_managed_identity_credential=True
    ) as credential, AIProjectClient(
        endpoint=clean_env_value("AZURE_AI_PROJECT_ENDPOINT"), credential=credential
    ) as project, project.get_openai_client() as client:
        model = clean_env_value("DEPLOYMENT_NAME", "gpt-4o")
        chat = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "Reply with a short greeting."}],
        )
        require(chat.choices[0].message.content, "The Foundry project chat client returned no answer.")
        first = client.responses.create(
            model=model, input="Remember the demo code 4729 for my next question. Reply OK.",
        )
        require(first.status == "completed" and first.output_text, "The first Responses turn did not complete.")
        second = client.responses.create(
            model=model, previous_response_id=first.id,
            input="What is the demo code? Reply with only the four digits.",
        )
        require(
            second.status == "completed" and second.output_text.strip() == "4729",
            "The Responses API did not retain the previous turn's demo code.",
        )
    print("PASS: Foundry project chat and Responses API conversation state.")


def check_tools_and_quality() -> None:
    agent_module = importlib.import_module("5_agentic_rag_tool_demo")
    agent = agent_module.AgenticRagDemo()
    try:
        require(
            agent.run("When should I expect an approved credit-card refund, and how can I escalate it?"),
            "The application-orchestrated RAG workflow returned no answer.",
        )
    finally:
        agent.openai_client.close()
        agent.search_client.close()
    evaluation_module = importlib.import_module("6_rag_quality_eval_demo")
    evaluation = evaluation_module.RagQualityEvalDemo()
    try:
        results = [evaluation.score_case(case) for case in evaluation_module.EVAL_CASES]
        average = sum(result["score"] for result in results) / len(results)
        require(all(result["source_hit"] and result["answer"] for result in results), "RAG evaluation missed a required source or answer.")
        require(average >= 0.75, f"RAG quality score {average:.2f} is below the demo threshold 0.75.")
    finally:
        evaluation.openai_client.close()
        evaluation.search_client.close()
    print(f"PASS: Application RAG tools and golden-set evaluation (average {average:.2f}).")
    tools_module = importlib.import_module("8_foundry_tool_calling_demo")
    tools_module.FoundryToolCallingDemo().run("all")
    print("PASS: Hosted Code Interpreter, web search, file search, and a locally executed function.")


def check_key_vault() -> None:
    with DefaultAzureCredential(
        exclude_environment_credential=True, exclude_managed_identity_credential=True
    ) as credential, SecretClient(
        vault_url=clean_env_value("AZURE_KEY_VAULT_URI"), credential=credential
    ) as client:
        key = client.get_secret("AZURE-SEARCH-ADMIN-KEY").value
        require(key == clean_env_value("AZURE_SEARCH_ADMIN_KEY"), "Key Vault's Search key does not match the deployed environment.")
        endpoint = client.get_secret("AZURE-OPENAI-ENDPOINT").value
        require(endpoint == clean_env_value("AZURE_OPENAI_ENDPOINT"), "Key Vault points at a different Foundry account.")
    print("PASS: Key Vault configuration is readable and matches this environment.")


async def check_voice_session(module: Any) -> None:
    from azure.ai.voicelive.models import ServerEventType

    async with module.configured_voice_connection() as connection:
        async for event in connection:
            if event.type == ServerEventType.ERROR:
                raise RuntimeError(f"Voice Live rejected the demo session: {event.error.message}")
            if event.type == ServerEventType.SESSION_UPDATED:
                names = {getattr(tool, "name", None) for tool in event.session.tools or []}
                require(
                    {"redact_customer_text", "search_bank_knowledge"} <= names,
                    "Voice Live did not accept the demo's privacy and retrieval tools.",
                )
                print("PASS: Voice Live accepted the actual demo session, voice, audio formats, and tools.")
                return
    raise RuntimeError("Voice Live closed before acknowledging the demo session.")


async def check_language_voice() -> None:
    module = importlib.import_module("7_foundry_rag_language_voice_demo")
    async with module.language_mcp_session() as session:
        runtime = module.BankingToolRuntime(session)
        try:
            customer_text = "My email is jane.doe@example.com. How long do credit-card refunds take?"
            protected = await runtime.redact_customer_text(customer_text)
            require(protected["entity_count"] > 0, "Azure Language did not detect the test email address.")
            require(
                "jane.doe@example.com" not in protected["redacted_text"].lower(),
                "Azure Language did not redact the test email address.",
            )
            evidence = runtime.search_bank_knowledge()
            require(evidence["documents"], "The Language MCP workflow retrieved no bank policies.")
            answer = await runtime.answer_typed(customer_text)
            require(
                answer and answer != "No response was generated."
                and "jane.doe@example.com" not in answer.lower(),
                "The typed Language/RAG demo returned an empty or unredacted answer.",
            )
        finally:
            runtime.openai_client.close()
            runtime.search_client.close()
    print("PASS: Local Language MCP server, Azure PII redaction, and the typed RAG workflow.")
    await asyncio.wait_for(check_voice_session(module), timeout=60)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-language-voice", action="store_true",
        default=os.getenv("AZURE_DEMO_INCLUDE_LANGUAGE_VOICE", "false").lower() == "true",
    )
    args = parser.parse_args()
    try:
        from infra.hooks.provision import (
            enabled_setting, policy_protected_services, verify_private_setup_execution,
        )

        protected = policy_protected_services(dict(os.environ))
        private_verified = enabled_setting(dict(os.environ), "AZURE_DEMO_PRIVATE_SETUP")
        if private_verified:
            verify_private_setup_execution(dict(os.environ))
        check_search()
        check_chat_and_rag()
        check_project_and_responses()
        if "keyvault" not in protected:
            check_key_vault()
        check_tools_and_quality()
        if args.include_language_voice:
            asyncio.run(check_language_voice())
        subprocess.run(
            [sys.executable, str(ROOT / "1b_fine_tuning_code_first.py"), "--dry-run", "--initials", "demo"],
            cwd=ROOT, check=True,
            env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        )
        if protected:
            limitation = (
                "Storage/Key Vault verified from the private Azure job; laptop access still uses fallback."
                if private_verified else "Storage/Key Vault private access remains unverified."
            )
            print(f"READY: Class demos passed using the approved local/.env fallback. {limitation}")
        else:
            print("READY: All selected service checks passed. No fine-tuning job was started.")
        if args.include_language_voice:
            print("Microphone/speaker interaction still requires a manual --voice run.")
        return 0
    except (AzureError, OpenAIError, OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Demo readiness FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
