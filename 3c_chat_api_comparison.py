"""Compare Chat Completions and Responses API conversation state.

Run:
    python 3c_chat_api_comparison.py
"""

import os
import sys

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


load_dotenv()

PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "").strip().strip('"')
PROJECT_ENDPOINT = PROJECT_ENDPOINT.replace(
    ".cognitiveservices.azure.com", ".services.ai.azure.com"
).replace("/projects/", "/api/projects/")
CHAT_DEPLOYMENT = os.getenv("DEPLOYMENT_NAME", "gpt-4o").strip().strip('"')

SYSTEM_PROMPT = (
    'You are "Aria", a concise concierge for First Private Bank. '
    "Give general information only and answer in two sentences or fewer."
)
PROMPTS = (
    "What is your role?",
    "Summarize your previous answer in exactly five words.",
)


def get_client():
    """Return a keyless OpenAI client bound to the Foundry project."""
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
    return project.get_openai_client()


def run_chat_completions(client):
    """Run both turns with conversation history managed by this application."""
    print("\n1. Chat Completions API")
    print("   State: the application resends the complete messages array")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn, prompt in enumerate(PROMPTS, start=1):
        messages.append({"role": "user", "content": prompt})
        print(f"\n   Turn {turn} sends {len(messages)} messages")
        print(f"   You:  {prompt}")

        completion = client.chat.completions.create(
            model=CHAT_DEPLOYMENT,
            messages=messages,
        )
        reply = completion.choices[0].message.content or ""
        print(f"   Aria: {reply}")
        if completion.usage:
            print(
                "   Tokens: "
                f"input={completion.usage.prompt_tokens}, "
                f"output={completion.usage.completion_tokens}, "
                f"total={completion.usage.total_tokens}"
            )
        messages.append({"role": "assistant", "content": reply})


def run_responses(client):
    """Run both turns with conversation state linked by a response ID."""
    print("\n2. Responses API")
    print("   State: the service links turns through previous_response_id")

    previous_response_id = None
    for turn, prompt in enumerate(PROMPTS, start=1):
        state = "none" if previous_response_id is None else "previous response ID"
        print(f"\n   Turn {turn} sends input plus: {state}")
        print(f"   You:  {prompt}")

        request = {
            "model": CHAT_DEPLOYMENT,
            "instructions": SYSTEM_PROMPT,
            "input": prompt,
        }
        if previous_response_id:
            request["previous_response_id"] = previous_response_id

        response = client.responses.create(**request)
        print(f"   Aria: {response.output_text}")
        if response.usage:
            print(
                "   Tokens: "
                f"input={response.usage.input_tokens}, "
                f"output={response.usage.output_tokens}, "
                f"total={response.usage.total_tokens}"
            )
        previous_response_id = response.id


def main():
    client = get_client()

    print("Chat Completions API vs Responses API")
    print(f"Deployment: {CHAT_DEPLOYMENT}")
    run_chat_completions(client)
    run_responses(client)

    print("\nComparison")
    print("- Chat Completions: your code stores and resends conversation messages.")
    print("- Responses: Azure stores conversation state; your code sends an ID.")
    print("- The response ID reduces payload management, not the tokens the model processes.")


if __name__ == "__main__":
    main()