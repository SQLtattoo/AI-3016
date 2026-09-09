"""Shared Azure OpenAI client helpers for the AI-3016 demos."""

import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI


COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


def clean_env_value(name: str, default: str = "") -> str:
    """Return a cleaned environment variable value."""
    return os.getenv(name, default).strip().strip('"')


def has_usable_secret(value: str) -> bool:
    """Return True when an environment value looks like a real local-auth secret."""
    if not value:
        return False

    placeholders = ("REPLACE_WITH", "your-", "<", ">")
    return not any(marker in value for marker in placeholders)


def create_azure_openai_client(
    endpoint_env: str = "AZURE_OPENAI_ENDPOINT",
    key_env: str = "AZURE_OPENAI_API_KEY",
    api_version: str = "2024-05-01-preview",
    timeout: float = 60.0,
) -> AzureOpenAI:
    """Create an Azure OpenAI client using API-key auth or Microsoft Entra ID."""
    endpoint = clean_env_value(endpoint_env)
    if not endpoint:
        raise ValueError(f"Missing required environment variable: {endpoint_env}")

    api_key = clean_env_value(key_env)
    if has_usable_secret(api_key):
        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
            timeout=timeout,
            max_retries=1,
        )

    credential = DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )
    token_provider = get_bearer_token_provider(credential, COGNITIVE_SERVICES_SCOPE)
    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version=api_version,
        timeout=timeout,
        max_retries=1,
    )