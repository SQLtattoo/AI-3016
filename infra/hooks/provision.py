#!/usr/bin/env python3
"""Shared azd setup for Windows and POSIX; never reads an old root .env as input."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import venv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar


ROOT = Path(__file__).resolve().parents[2]
VENV = ROOT / "ai3016-env"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
T = TypeVar("T")


def cli(*args: str) -> str:
    executable = shutil.which(args[0])
    if not executable:
        raise RuntimeError(f"Required command is not installed: {args[0]}")
    result = subprocess.run(
        [executable, *args[1:]], cwd=ROOT, capture_output=True,
        text=True, encoding="utf-8", timeout=300, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def cli_json(*args: str) -> Any:
    return json.loads(cli(*args, "--output", "json"))


def load_environment(environment: str | None) -> dict[str, str]:
    args = ["azd", "env", "get-values"]
    if environment:
        args.extend(["--environment", environment])
    values = cli_json(*args)
    if not isinstance(values, dict):
        raise ValueError("azd did not return an environment object.")
    return {name: str(value) for name, value in values.items()}


def require(values: dict[str, str], name: str) -> str:
    value = values.get(name, "").strip().strip('"')
    if not value:
        raise ValueError(f"{name} is missing. Set it with azd env set in the target environment.")
    return value


def enabled_setting(values: dict[str, str], name: str) -> bool:
    value = values.get(name, "false").lower()
    if value not in ("true", "false"):
        raise ValueError(f"{name} must be true or false.")
    return value == "true"


def include_language_voice(values: dict[str, str]) -> bool:
    return enabled_setting(values, "AZURE_DEMO_INCLUDE_LANGUAGE_VOICE")


def policy_protected_services(values: dict[str, str]) -> set[str]:
    subscription = require(values, "AZURE_SUBSCRIPTION_ID")
    group = require(values, "AZURE_RESOURCE_GROUP")
    services = {
        "storage": (
            "az", "storage", "account", "show",
            "--name", require(values, "AZURE_STORAGE_ACCOUNT_NAME"),
            "--query", "publicNetworkAccess",
        ),
        "keyvault": (
            "az", "keyvault", "show",
            "--name", require(values, "AZURE_KEY_VAULT_NAME"),
            "--query", "properties.publicNetworkAccess",
        ),
    }
    protected = {
        name for name, command in services.items()
        if cli_json(*command, "--resource-group", group, "--subscription", subscription) == "Disabled"
    }
    if protected and not enabled_setting(values, "AZURE_DEMO_ALLOW_POLICY_FALLBACK"):
        raise ValueError(
            f"Public access is disabled for {', '.join(sorted(protected))}. "
            "Use a permitted private network, or explicitly set "
            "AZURE_DEMO_ALLOW_POLICY_FALLBACK=true for local-source/.env class demos. "
            "Their private data-plane access will remain unverified."
        )
    for name in sorted(protected):
        print(f"WARNING: {name} public access is disabled; approved local/.env fallback is active. Local private access is NOT verified.")
    return protected


def validate_context(values: dict[str, str]) -> dict[str, Any]:
    environment = require(values, "AZURE_ENV_NAME")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,63}", environment):
        raise ValueError("Use an azd environment name with only letters, digits, and hyphens.")
    subscription = require(values, "AZURE_SUBSCRIPTION_ID")
    tenant = require(values, "AZURE_TENANT_ID")
    require(values, "AZURE_LOCATION")
    account = cli_json("az", "account", "show", "--subscription", subscription)
    current = cli_json("az", "account", "show")
    if account["tenantId"] != tenant or current["id"] != subscription:
        raise ValueError(
            "Azure CLI and azd target different subscriptions or tenants. "
            f"Run az login --tenant {tenant} and az account set --subscription {subscription}."
        )
    return account


def resolve_parameters(values: dict[str, str]) -> dict[str, str]:
    template = json.loads((ROOT / "infra" / "main.parameters.json").read_text(encoding="utf-8"))
    parameters = {}
    for name, entry in template["parameters"].items():
        value = entry["value"]
        match = re.fullmatch(r"\$\{([A-Z0-9_]+)(?:=([^}]*))?\}", str(value))
        if match:
            variable, default = match.groups()
            value = values.get(variable, default)
        if value is None or value == "":
            raise ValueError(f"Missing deployment parameter: {name}")
        parameters[name] = str(value)
    return parameters


def validate_models(
    parameters: dict[str, str],
    models: list[dict[str, Any]],
    usages: list[dict[str, Any]],
    deployments: list[dict[str, Any]],
) -> None:
    usage_by_name = {item["name"]["value"]: item for item in usages}
    existing = {item["name"]: item for item in deployments}
    allocated: dict[str, int] = {}
    for prefix in ("model", "embeddings"):
        name_key = "modelName" if prefix == "model" else "embeddingsModelName"
        version_key = "modelVersion" if prefix == "model" else "embeddingsModelVersion"
        deployment_key = f"{prefix}DeploymentName"
        sku_name = parameters[f"{prefix}DeploymentSku"]
        capacity = int(parameters[f"{prefix}DeploymentCapacity"])
        if capacity < 1:
            raise ValueError("Model deployment capacities must be positive.")
        name, version = parameters[name_key], parameters[version_key]
        matching = [
            item["model"] for item in models
            if item.get("kind") == "AIServices"
            and item["model"]["name"] == name and item["model"]["version"] == version
        ]
        if not matching:
            raise ValueError(f"Model {name} version {version} is unavailable in the selected region.")
        model = matching[0]
        retirement = (model.get("deprecation") or {}).get("inference")
        if retirement and datetime.fromisoformat(retirement.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
            raise ValueError(f"Model {name} version {version} retired on {retirement}.")
        sku = next((item for item in model.get("skus", []) if item["name"] == sku_name), None)
        if not sku:
            raise ValueError(f"{name} version {version} does not support SKU {sku_name}.")
        limits = sku.get("capacity") or {}
        minimum, maximum, step = limits.get("minimum") or 1, limits.get("maximum"), limits.get("step") or 1
        allowed = limits.get("allowedValues")
        if (
            capacity < minimum or (maximum is not None and capacity > maximum)
            or (capacity - minimum) % step or (allowed and capacity not in allowed)
        ):
            raise ValueError(f"Capacity {capacity} is invalid for {name}/{sku_name}: {limits}")
        usage_name = sku["usageName"]
        if usage_name not in usage_by_name:
            raise ValueError(f"No quota information returned for {usage_name}; capacity is not verified.")
        previous = existing.get(parameters[deployment_key], {})
        previous_model = previous.get("properties", {}).get("model", {})
        previous_sku = previous.get("sku", {})
        reusable = (
            previous_model.get("name") == name
            and previous_sku.get("name") == sku_name
        )
        additional = max(0, capacity - int(previous_sku.get("capacity", 0))) if reusable else capacity
        allocated[usage_name] = allocated.get(usage_name, 0) + additional
        usage = usage_by_name[usage_name]
        if usage["currentValue"] + allocated[usage_name] > usage["limit"]:
            raise ValueError(
                f"Insufficient quota for {usage_name}: used {usage['currentValue']}, "
                f"additional {allocated[usage_name]}, limit {usage['limit']}."
            )
        print(f"Preflight OK: {name}/{version}, {sku_name}, capacity {capacity}.")
        if retirement:
            print(f"  Model retirement reported by Azure: {retirement}")


def preprovision(values: dict[str, str]) -> None:
    account = validate_context(values)
    environment = values["AZURE_ENV_NAME"]
    values.setdefault("AZURE_RESOURCE_GROUP", f"rg-{environment}")
    if not values.get("AZURE_PRINCIPAL_ID"):
        user = account["user"]
        if user["type"] == "user":
            values["AZURE_PRINCIPAL_ID"] = cli_json("az", "ad", "signed-in-user", "show", "--query", "id")
            values["AZURE_PRINCIPAL_TYPE"] = "User"
        elif user["type"] == "servicePrincipal":
            values["AZURE_PRINCIPAL_ID"] = cli_json("az", "ad", "sp", "show", "--id", user["name"], "--query", "id")
            values["AZURE_PRINCIPAL_TYPE"] = "ServicePrincipal"
        else:
            raise ValueError("Set AZURE_PRINCIPAL_ID and AZURE_PRINCIPAL_TYPE explicitly for this identity.")
    values.setdefault(
        "AZURE_PRINCIPAL_TYPE",
        "ServicePrincipal" if account["user"]["type"] == "servicePrincipal" else "User",
    )
    for name in ("AZURE_RESOURCE_GROUP", "AZURE_PRINCIPAL_ID", "AZURE_PRINCIPAL_TYPE"):
        cli("azd", "env", "set", name, require(values, name), "--environment", environment)
    subscription = values["AZURE_SUBSCRIPTION_ID"]
    providers = ["Microsoft.CognitiveServices", "Microsoft.Search", "Microsoft.Storage", "Microsoft.KeyVault"]
    if enabled_setting(values, "AZURE_DEMO_PRIVATE_SETUP"):
        providers.extend(["Microsoft.App", "Microsoft.Network", "Microsoft.ManagedIdentity"])
    for provider in providers:
        state = cli_json(
            "az", "provider", "show", "--namespace", provider,
            "--subscription", subscription, "--query", "registrationState",
        )
        if state != "Registered":
            print(f"Registering {provider} in the selected subscription...")
            cli("az", "provider", "register", "--namespace", provider, "--subscription", subscription, "--wait")
    parameters = resolve_parameters(values)
    models = cli_json("az", "cognitiveservices", "model", "list",
                      "--location", values["AZURE_LOCATION"], "--subscription", subscription)
    usages = cli_json("az", "cognitiveservices", "usage", "list",
                      "--location", values["AZURE_LOCATION"], "--subscription", subscription)
    deployments = []
    if values.get("AZURE_FOUNDRY_SERVICE_NAME"):
        deployments = cli_json(
            "az", "cognitiveservices", "account", "deployment", "list",
            "--name", values["AZURE_FOUNDRY_SERVICE_NAME"],
            "--resource-group", values["AZURE_RESOURCE_GROUP"], "--subscription", subscription,
        )
    validate_models(parameters, models, usages, deployments)
    print(f"Azure preflight complete for {environment} in {values['AZURE_LOCATION']}.")


def same_target(previous: dict[str, str], current: dict[str, str]) -> bool:
    return bool(
        previous.get("AZURE_SUBSCRIPTION_ID") == current["AZURE_SUBSCRIPTION_ID"]
        and previous.get("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        == current["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        and previous.get("AZURE_ENV_NAME", current["AZURE_ENV_NAME"]) == current["AZURE_ENV_NAME"]
    )


def runtime_settings(values: dict[str, str], search_key: str, previous: dict[str, str]) -> dict[str, str]:
    endpoint = require(values, "AZURE_OPENAI_ENDPOINT")
    settings = {**previous}
    for name in (
        "AZURE_ENV_NAME", "AZURE_SUBSCRIPTION_ID", "AZURE_TENANT_ID", "AZURE_LOCATION",
        "AZURE_RESOURCE_GROUP", "AZURE_AI_PROJECT_NAME", "AZURE_AI_PROJECT_ENDPOINT",
        "AZURE_STORAGE_ACCOUNT_NAME", "AZURE_STORAGE_CONTAINER_NAME", "AZURE_STORAGE_ENDPOINT",
        "AZURE_KEY_VAULT_NAME", "AZURE_KEY_VAULT_URI", "AZURE_SEARCH_ENDPOINT",
        "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME",
    ):
        settings[name] = require(values, name)
    settings.update(
        ENDPOINT_URL=endpoint,
        DEPLOYMENT_NAME=require(values, "AZURE_OPENAI_DEPLOYMENT_NAME"),
        AZURE_OPENAI_ENDPOINT=endpoint,
        AZURE_OPENAI_API_KEY="",
        AZURE_AI_FOUNDRY_API_KEY="",
        AZURE_AI_AUTH_MODE="entra",
        AZURE_SEARCH_ADMIN_KEY=search_key,
        AZURE_SEARCH_INDEX="rag-bank-documents",
        AZURE_DEMO_INCLUDE_LANGUAGE_VOICE=str(include_language_voice(values)).lower(),
        AZURE_DEMO_ALLOW_POLICY_FALLBACK=str(
            enabled_setting(values, "AZURE_DEMO_ALLOW_POLICY_FALLBACK")
        ).lower(),
        AZURE_DEMO_PRIVATE_SETUP=str(enabled_setting(values, "AZURE_DEMO_PRIVATE_SETUP")).lower(),
        AZURE_DEMO_PRIVATE_SETUP_JOB_ID=values.get("AZURE_DEMO_PRIVATE_SETUP_JOB_ID", ""),
        AZURE_DEMO_PRIVATE_SETUP_EXECUTION_ID=values.get("AZURE_DEMO_PRIVATE_SETUP_EXECUTION_ID", ""),
    )
    defaults = {
        "AZURE_LANGUAGE_ENDPOINT": endpoint,
        "AZURE_LANGUAGE_KEY": "",
        "AZURE_VOICELIVE_ENDPOINT": f"https://{values['AZURE_FOUNDRY_SERVICE_NAME']}.services.ai.azure.com/",
        "AZURE_VOICELIVE_API_KEY": "",
        "AZURE_VOICELIVE_MODEL": "gpt-realtime",
        "AZURE_VOICELIVE_VOICE": "en-US-Ava:DragonHDLatestNeural",
        "VOICE_LIVE_NOISE_GATE_THRESHOLD": "500",
        "FINE_TUNED_DEPLOYMENT_NAME": "",
    }
    for name, default in defaults.items():
        settings[name] = values.get(name, previous.get(name, default))
    return settings


def write_runtime_environment(values: dict[str, str], search_key: str) -> dict[str, str]:
    from dotenv import dotenv_values

    path = ROOT / ".env"
    cache = ROOT / ".azure" / values["AZURE_ENV_NAME"] / "demo.env"
    current = {key: value for key, value in dotenv_values(path, interpolate=False).items() if value is not None}
    cached = {key: value for key, value in dotenv_values(cache, interpolate=False).items() if value is not None}
    target = {
        "AZURE_ENV_NAME": values["AZURE_ENV_NAME"],
        "AZURE_SUBSCRIPTION_ID": values["AZURE_SUBSCRIPTION_ID"],
        "AZURE_OPENAI_ENDPOINT": values["AZURE_OPENAI_ENDPOINT"],
    }
    previous = cached if same_target(cached, target) else {}
    if same_target(current, target):
        previous.update(current)
    elif path.exists():
        backups = ROOT / ".azure" / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backups / f".env.{time.time_ns()}.bak")
        print("Previous root .env preserved under .azure/backups; old-tenant settings will not be reused.")
    settings = runtime_settings(values, search_key, previous)
    text = "# Generated by azd; optional settings are preserved only for the same environment.\n"
    text += "".join(f"{key}={json.dumps(value, ensure_ascii=False)}\n" for key, value in settings.items())
    temporary = path.with_name(".env.provisioning")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    print("Root .env generated from the selected azd environment (credentials not displayed).")
    return settings


def retry_rbac(label: str, operation: Callable[[], T], attempts: int = 12) -> T:
    from azure.core.exceptions import HttpResponseError

    for attempt in range(attempts):
        try:
            return operation()
        except HttpResponseError as exc:
            if (
                exc.status_code != 403 or attempt + 1 == attempts
                or "ForbiddenByFirewall" in str(exc)
            ):
                raise
            print(f"{label}: HTTP 403; waiting for new RBAC assignments ({attempt + 1}/{attempts}).")
            time.sleep(10)
    raise RuntimeError(f"{label} did not complete.")


def run_private_setup(values: dict[str, str], attempts: int = 75, delay: int = 10) -> str:
    job_id = require(values, "AZURE_DEMO_PRIVATE_SETUP_JOB_ID")
    execution = cli_json(
        "az", "rest", "--method", "post",
        "--url", f"https://management.azure.com{job_id}/start?api-version=2025-01-01",
        "--body", "{}",
    )
    execution_id = execution["id"]
    if not execution_id.startswith(f"{job_id}/executions/"):
        raise ValueError("The private setup API returned an unexpected execution resource.")
    print(f"Private setup job started: {execution['name']}")
    for attempt in range(attempts):
        state = cli_json(
            "az", "rest", "--method", "get",
            "--url", f"https://management.azure.com{execution_id}?api-version=2025-01-01",
        )["properties"]["status"]
        if state == "Succeeded":
            print("PASS: Azure-side private DNS, blob upload/readback, and Key Vault write/readback.")
            return execution_id
        if state in ("Failed", "Stopped", "Degraded"):
            raise RuntimeError(f"Private setup execution {execution['name']} ended with {state}. Inspect its Container Apps job logs.")
        if attempt + 1 < attempts:
            time.sleep(delay)
    raise RuntimeError(f"Private setup execution {execution['name']} did not complete before the readiness timeout.")


def verify_private_setup_execution(values: dict[str, str]) -> None:
    job_id = require(values, "AZURE_DEMO_PRIVATE_SETUP_JOB_ID")
    execution_id = require(values, "AZURE_DEMO_PRIVATE_SETUP_EXECUTION_ID")
    if not execution_id.startswith(f"{job_id}/executions/"):
        raise ValueError("The recorded private execution belongs to a different job.")
    execution = cli_json(
        "az", "rest", "--method", "get",
        "--url", f"https://management.azure.com{execution_id}?api-version=2025-01-01",
    )
    if execution["properties"]["status"] != "Succeeded":
        raise RuntimeError("The recorded private setup execution did not succeed.")
    print("PASS: Recorded Azure-side private service verification completed successfully; laptop access still requires a private network.")


def postprovision(values: dict[str, str]) -> None:
    from azure.identity import AzureCliCredential
    from azure.keyvault.secrets import SecretClient
    from azure.storage.blob import BlobServiceClient

    validate_context(values)
    protected = policy_protected_services(values)
    for service in protected:
        variable = (
            "AZURE_STORAGE_PUBLIC_NETWORK_ACCESS" if service == "storage"
            else "AZURE_KEY_VAULT_PUBLIC_NETWORK_ACCESS"
        )
        cli("azd", "env", "set", variable, "Disabled", "--environment", values["AZURE_ENV_NAME"])
    search_key = cli_json(
        "az", "search", "admin-key", "show",
        "--service-name", require(values, "AZURE_SEARCH_SERVICE_NAME"),
        "--resource-group", require(values, "AZURE_RESOURCE_GROUP"),
        "--subscription", values["AZURE_SUBSCRIPTION_ID"], "--query", "primaryKey",
    )
    if not isinstance(search_key, str) or not search_key:
        raise ValueError("Azure AI Search did not return an admin key.")
    settings = write_runtime_environment(values, search_key)
    os.environ.update(settings)
    if enabled_setting(values, "AZURE_DEMO_PRIVATE_SETUP"):
        execution_id = run_private_setup(values)
        values["AZURE_DEMO_PRIVATE_SETUP_EXECUTION_ID"] = execution_id
        cli(
            "azd", "env", "set", "AZURE_DEMO_PRIVATE_SETUP_EXECUTION_ID", execution_id,
            "--environment", values["AZURE_ENV_NAME"],
        )
        os.environ.update(write_runtime_environment(values, search_key))
    sys.path.insert(0, str(ROOT))
    from setup_search_index import SOURCE_DIRECTORY, get_documents_from_local_sources

    get_documents_from_local_sources()
    with AzureCliCredential(tenant_id=values["AZURE_TENANT_ID"]) as credential:
        if "storage" not in protected:
            with BlobServiceClient(
                account_url=settings["AZURE_STORAGE_ENDPOINT"], credential=credential
            ) as service:
                container = service.get_container_client(settings["AZURE_STORAGE_CONTAINER_NAME"])
                for path in sorted(SOURCE_DIRECTORY.glob("*.txt")):
                    def upload(path: Path = path) -> None:
                        with path.open("rb") as source:
                            container.upload_blob(path.name, source, overwrite=True)
                    retry_rbac(f"Upload {path.name}", upload)
                    print(f"Blob uploaded: {path.name}")
        if "keyvault" not in protected:
            with SecretClient(vault_url=settings["AZURE_KEY_VAULT_URI"], credential=credential) as vault:
                for name in (
                    "ENDPOINT_URL", "DEPLOYMENT_NAME", "AZURE_OPENAI_ENDPOINT",
                    "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_ADMIN_KEY", "AZURE_SEARCH_INDEX",
                ):
                    retry_rbac(
                        f"Store {name} in Key Vault",
                        lambda name=name: vault.set_secret(name.replace("_", "-"), settings[name]),
                    )
                print("Key Vault demo configuration stored.")
    subprocess.run([sys.executable, str(ROOT / "setup_search_index.py")], cwd=ROOT, check=True)
    command = [sys.executable, str(ROOT / "check_demo_readiness.py")]
    if include_language_voice(values):
        command.append("--include-language-voice")
    subprocess.run(command, cwd=ROOT, check=True)
    print("Post-provision setup and live demo readiness checks completed.")


def main() -> int:
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["preprovision", "postprovision"])
    parser.add_argument("--environment", default=os.environ.get("AZURE_ENV_NAME"))
    parser.add_argument("--prepared", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        values = load_environment(args.environment)
        if not args.prepared:
            if not PYTHON.exists():
                print("Creating ai3016-env...")
                venv.EnvBuilder(with_pip=True).create(VENV)
            manifests = [ROOT / "requirements.txt"]
            if include_language_voice(values):
                manifests.append(ROOT / "requirements-optional.txt")
            for manifest in manifests:
                subprocess.run(
                    [str(PYTHON), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", str(manifest)],
                    cwd=ROOT, check=True,
                )
            return subprocess.run(
                [str(PYTHON), str(Path(__file__).resolve()), args.phase,
                 "--environment", values["AZURE_ENV_NAME"], "--prepared"],
                cwd=ROOT, check=False,
            ).returncode
        os.environ.update(values)
        if args.phase == "preprovision":
            preprovision(values)
        else:
            postprovision(values)
        return 0
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"{args.phase} FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
