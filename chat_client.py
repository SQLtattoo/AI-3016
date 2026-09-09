"""
Module 2b — Lightweight Foundry SDK chat client.

Connects to a model deployed in your Microsoft Foundry project and runs an
interactive chat loop in the terminal. Uses keyless auth by default.

Run:
    python demos/02-generative-ai-and-agents/b-foundry-sdk-chat/chat_client.py
"""
import os
import sys

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential

load_dotenv()

PROJECT_ENDPOINT = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
CHAT_DEPLOYMENT = os.getenv("CHAT_DEPLOYMENT", "gpt-5.1")

SYSTEM_PROMPT = (
    'You are "Aria", a concise concierge for Contoso Private Bank '
    "(Private Banking and Wealth & Investment). Answer in 3 sentences or fewer. "
    "Give general information only — no personalized investment, tax, or legal advice; "
    "refer clients to a licensed Contoso advisor for decisions. "
    "Never invent products, rates, or figures, and never ask for account numbers or passwords."
)


def get_client():
    """Return an OpenAI client bound to the Foundry project.

    In azure-ai-projects 2.x the project exposes an OpenAI-compatible client,
    so the same deployment name from the portal works here with no keys in code.
    """
    if not PROJECT_ENDPOINT:
        sys.exit(
            "FOUNDRY_PROJECT_ENDPOINT is not set. Copy .env.example to .env and fill it in, "
            "then run `az login`."
        )

    from azure.ai.projects import AIProjectClient

    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    # Returns an authenticated openai.OpenAI client (keyless, bearer token).
    return project.get_openai_client()


def main():
    client = get_client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("Aria — Contoso Private Bank concierge. Type 'exit' to quit.\n")
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
        reply = response.choices[0].message.content
        print(f"aria > {reply}\n")
        # Keep the assistant turn so the model remembers context.
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
