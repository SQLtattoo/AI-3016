"""
Module 3B — Lightweight Microsoft Foundry SDK chat client.

Connects to a model deployed in your Microsoft Foundry project and runs an
interactive chat loop in the terminal. Uses keyless auth by default and shows
per-call and cumulative token usage reported by the API.

Run:
    python 3b_chat_client.py
"""
import os
import sys

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure_openai_auth import normalize_project_endpoint

load_dotenv()

PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "").strip().strip('"')
PROJECT_ENDPOINT = normalize_project_endpoint(PROJECT_ENDPOINT)
CHAT_DEPLOYMENT = os.getenv("DEPLOYMENT_NAME", "gpt-4o")

SYSTEM_PROMPT = (
    'You are "Aria", a concise concierge for First Private Bank '
    "(Private Banking and Wealth & Investment). Answer in 3 sentences or fewer. "
    "Give general information only — no personalized investment, tax, or legal advice; "
    "refer clients to a licensed advisor for decisions. "
    "Never invent products, rates, or figures, and never ask for account numbers or passwords."
)


def get_client():
    """Return an OpenAI client bound to the Foundry project.

    In azure-ai-projects 2.x the project exposes an OpenAI-compatible client,
    so the same deployment name from the portal works here with no keys in code.
    """
    if not PROJECT_ENDPOINT:
        sys.exit(
            "AZURE_AI_PROJECT_ENDPOINT is not set. Run `azd up` to generate .env, "
            "then run `az login`."
        )

    from azure.ai.projects import AIProjectClient

    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        ),
    )
    # Returns an authenticated openai.OpenAI client (keyless, bearer token).
    return project.get_openai_client()


def main():
    client = get_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    turn = 0
    total_input_tokens = 0
    total_output_tokens = 0
    previous_input_tokens = None
    usage_incomplete = False

    print("Aria — First Private Bank concierge. Type 'exit' to quit.\n")
    print(
        "Input tokens include the system prompt, all prior turns, and your new message.\n"
        "History is resent on every call, so cumulative usage counts it again.\n"
    )
    while True:
        try:
            user = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if user.lower() in {"exit", "quit"}:
            break
        if not user:
            continue

        messages.append({"role": "user", "content": user})
        response = client.chat.completions.create(model=CHAT_DEPLOYMENT, messages=messages)
        turn += 1
        reply = response.choices[0].message.content
        print(f"aria > {reply}")
        # Keep the assistant turn so the model remembers context.
        messages.append({"role": "assistant", "content": reply})

        usage = response.usage
        if usage is None:
            usage_incomplete = True
            previous_input_tokens = None
            print(f"  Call {turn} tokens: unavailable (API did not return usage).")
            print("  Cumulative usage is incomplete; this call is not included.\n")
            continue

        total_input_tokens += usage.prompt_tokens
        total_output_tokens += usage.completion_tokens
        print(
            f"  Call {turn} tokens: input {usage.prompt_tokens} "
            f"+ output {usage.completion_tokens} = {usage.total_tokens}"
        )
        if previous_input_tokens is not None:
            print(
                f"  Input change since previous call: "
                f"{usage.prompt_tokens - previous_input_tokens:+d} tokens "
                "(previous reply + new user message + message overhead)."
            )
        previous_input_tokens = usage.prompt_tokens
        qualifier = " (reported calls only)" if usage_incomplete else ""
        print(
            f"  Cumulative tokens{qualifier}: input {total_input_tokens} "
            f"+ output {total_output_tokens} = {total_input_tokens + total_output_tokens}\n"
        )


if __name__ == "__main__":
    main()
