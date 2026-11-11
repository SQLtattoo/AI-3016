#!/usr/bin/env python3
"""Seed and verify protected demo services from the private Container Apps job."""

import base64
import ipaddress
import json
import os
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


def request(method, url, *, token=None, body=None, headers=None, attempts=18):
    request_headers = dict(headers or {})
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    for attempt in range(attempts):
        try:
            with urlopen(
                Request(url, data=body, headers=request_headers, method=method), timeout=45
            ) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code not in (403, 429, 500, 502, 503, 504) or attempt + 1 == attempts:
                raise RuntimeError(
                    f"{method} {urlsplit(url).hostname} failed with HTTP {exc.code}."
                ) from None
            print(f"Waiting for private service/RBAC readiness: HTTP {exc.code} ({attempt + 1}/{attempts}).", flush=True)
            time.sleep(10)
    raise RuntimeError("The private service did not become ready.")


def identity_token(resource):
    endpoint = os.environ["IDENTITY_ENDPOINT"]
    query = urlencode({
        "resource": resource,
        "api-version": "2019-08-01",
        "client_id": os.environ["AZURE_CLIENT_ID"],
    })
    payload = request(
        "GET", f"{endpoint}?{query}",
        headers={"X-IDENTITY-HEADER": os.environ["IDENTITY_HEADER"]},
    )
    return json.loads(payload)["access_token"]


def verify_private_dns(endpoint):
    hostname = urlsplit(endpoint).hostname
    for attempt in range(18):
        addresses = {entry[4][0] for entry in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)}
        if addresses and all(ipaddress.ip_address(address).is_private for address in addresses):
            print(f"PASS: {hostname} resolves privately to {', '.join(sorted(addresses))}.", flush=True)
            return
        if attempt + 1 < 18:
            time.sleep(10)
    raise RuntimeError(f"{hostname} did not resolve exclusively to private addresses.")


def main():
    settings = json.loads(os.environ["DEMO_SETTINGS"])
    documents = json.loads(base64.b64decode(os.environ["DEMO_SOURCES_BASE64"]))
    expected = {"bank_policies.txt", "customer_service.txt", "investment_products.txt"}
    if set(documents) != expected or not all(text.strip() for text in documents.values()):
        raise ValueError("The private setup job requires all three nonempty repository sources.")
    storage = settings["AZURE_STORAGE_ENDPOINT"].rstrip("/")
    vault = settings["AZURE_KEY_VAULT_URI"].rstrip("/")
    verify_private_dns(storage)
    verify_private_dns(vault)
    management_token = identity_token("https://management.azure.com/")
    storage_token = identity_token("https://storage.azure.com/")
    vault_token = identity_token("https://vault.azure.net")
    search_id = settings["AZURE_SEARCH_RESOURCE_ID"]
    search_keys = json.loads(request(
        "POST",
        f"https://management.azure.com{search_id}/listAdminKeys?api-version=2025-05-01",
        token=management_token, body=b"{}", headers={"Content-Type": "application/json"},
    ))
    search_key = search_keys["primaryKey"]
    if not isinstance(search_key, str) or not search_key:
        raise ValueError("Search returned no usable key.")
    container = settings["AZURE_STORAGE_CONTAINER_NAME"]
    for name, text in documents.items():
        payload = text.encode("utf-8")
        url = f"{storage}/{container}/{name}"
        request(
            "PUT", url, token=storage_token, body=payload,
            headers={
                "x-ms-version": "2023-11-03",
                "x-ms-blob-type": "BlockBlob",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )
        content = request("GET", url, token=storage_token, headers={"x-ms-version": "2023-11-03"})
        if content != payload:
            raise RuntimeError(f"Blob readback differs from the repository source: {name}")
        print(f"PASS: Private blob upload/readback: {name}.", flush=True)
    secrets = {
        key: settings[key] for key in (
            "ENDPOINT_URL", "DEPLOYMENT_NAME", "AZURE_OPENAI_ENDPOINT",
            "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_INDEX",
        )
    }
    secrets["AZURE_SEARCH_ADMIN_KEY"] = search_key
    for name, value in secrets.items():
        url = f"{vault}/secrets/{name.replace('_', '-')}?api-version=7.4"
        request(
            "PUT", url, token=vault_token,
            body=json.dumps({"value": value}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        result = json.loads(request("GET", url, token=vault_token))
        if result.get("value") != value:
            raise RuntimeError(f"Private Key Vault readback mismatch for {name}.")
        print(f"PASS: Private Key Vault write/readback: {name} (value not logged).", flush=True)
    print("READY: Private DNS, all three blobs, and all six Key Vault settings verified.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, KeyError, URLError) as exc:
        print(f"Private setup FAILED: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
