import importlib
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from dotenv import dotenv_values

import check_demo_readiness as readiness
import setup_search_index as search_setup
import rag_grounding
from infra.hooks import provision
from infra.hooks import private_setup
from azure_openai_auth import normalize_project_endpoint


def source_documents():
    return [
        search_setup.source_document(name, f"Policy content from {name}")
        for name in sorted(search_setup.REQUIRED_SOURCES)
    ]


class SearchSetupTests(unittest.TestCase):
    def setUp(self):
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_missing_search_key_is_a_failure(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            search_setup.create_search_index()

    def test_all_three_repository_sources_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "bank_policies.txt").write_text("Policy", encoding="utf-8")
            with patch.object(search_setup, "SOURCE_DIRECTORY", path), self.assertRaises(ValueError):
                search_setup.get_documents_from_local_sources()

    def test_keywords_match_the_scalar_search_field(self):
        self.assertIsInstance(search_setup.source_document("bank_policies.txt", "Policy")["keywords"], str)

    def test_serialized_schema_keeps_vectors_retrievable(self):
        indexes = Mock()
        with (
            patch.dict(os.environ, {"AZURE_SEARCH_ENDPOINT": "https://test.search.windows.net", "AZURE_SEARCH_ADMIN_KEY": "unit-test"}),
            patch.object(search_setup, "has_usable_secret", return_value=True),
            patch.object(search_setup, "SearchIndexClient", return_value=indexes),
            patch.object(search_setup, "SearchClient"),
        ):
            search_setup.create_search_index()
        fields = {
            field.name: field.as_dict()
            for field in indexes.create_or_update_index.call_args.args[0].fields
        }
        self.assertEqual(fields["keywords"]["type"], "Edm.String")
        self.assertTrue(fields["content_vector"]["retrievable"])
        self.assertEqual(fields["content_vector"]["dimensions"], 1536)

    def test_invalid_embedding_dimensions_values_and_zero_vector_fail(self):
        vectors = [[], [1.0], [0.0] * 1536, [float("nan")] * 1536, [float("inf")] * 1536, [True] * 1536]
        for vector in vectors:
            with self.subTest(first=vector[:1]), self.assertRaises(ValueError):
                search_setup.validate_embedding(vector)
        search_setup.validate_embedding([0.1] * 1536)

    def embedding_client(self):
        client = MagicMock()
        client.__enter__.return_value = client
        client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1] * 1536)]
        )
        return client

    def test_partial_upload_does_not_report_success(self):
        documents = source_documents()
        search = Mock()
        search.upload_documents.return_value = [
            SimpleNamespace(key=doc["id"], succeeded=index != 1, error_message="Rejected" if index == 1 else None)
            for index, doc in enumerate(documents)
        ]
        with patch.object(search_setup, "create_azure_openai_client", return_value=self.embedding_client()):
            with self.assertRaisesRegex(RuntimeError, "Incomplete Search upload"):
                search_setup.upload_documents(search, documents)

    def test_missing_upload_result_does_not_report_success(self):
        documents = source_documents()
        search = Mock()
        search.upload_documents.return_value = [
            SimpleNamespace(key=documents[0]["id"], succeeded=True, error_message=None)
        ]
        with patch.object(search_setup, "create_azure_openai_client", return_value=self.embedding_client()):
            with self.assertRaises(RuntimeError):
                search_setup.upload_documents(search, documents)

    def test_embedding_failure_prevents_partial_upload(self):
        client = self.embedding_client()
        client.embeddings.create.side_effect = ValueError("Invalid embedding")
        search = Mock()
        with patch.object(search_setup, "create_azure_openai_client", return_value=client):
            with self.assertRaises(ValueError):
                search_setup.upload_documents(search, source_documents())
        search.upload_documents.assert_not_called()

    def test_each_document_and_vector_retrieval_are_verified(self):
        documents = source_documents()
        search = Mock()
        search.get_document.side_effect = [
            {**doc, "content_vector": [0.1] * 1536} for doc in documents
        ]
        search.search.side_effect = [[{"id": doc["id"]}] for doc in documents]
        search_setup.verify_search_index(search, documents, attempts=1, delay=0)
        self.assertEqual(search.get_document.call_count, 3)
        self.assertEqual(search.search.call_count, 3)

    def test_missing_vector_or_wrong_retrieval_fails_readiness(self):
        documents = source_documents()
        search = Mock()
        search.get_document.return_value = documents[0]
        with self.assertRaises(RuntimeError):
            search_setup.verify_search_index(search, documents, attempts=1, delay=0)
        search.get_document.return_value = {**documents[0], "content_vector": [0.1] * 1536}
        search.search.return_value = [{"id": "wrong-document"}]
        with self.assertRaises(RuntimeError):
            search_setup.verify_search_index(search, documents, attempts=1, delay=0)

    def test_visibility_retry_is_bounded(self):
        search = Mock()
        search.get_document.side_effect = ResourceNotFoundError("Not visible")
        with patch.object(search_setup.time, "sleep") as sleep, self.assertRaises(RuntimeError):
            search_setup.verify_search_index(search, source_documents(), attempts=2, delay=1)
        self.assertEqual(search.get_document.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_setup_failure_returns_nonzero(self):
        with (
            patch.object(search_setup, "get_documents_from_local_sources", return_value=source_documents()),
            patch.object(search_setup, "get_documents_from_storage", return_value=[]),
            patch.object(search_setup, "create_search_index", side_effect=RuntimeError("Index failure")),
            redirect_stderr(io.StringIO()) as errors,
        ):
            self.assertEqual(search_setup.main(), 1)
            self.assertIn("FAILED", errors.getvalue())

    def test_extra_index_documents_fail_readiness(self):
        search = MagicMock()
        search.__enter__.return_value = search
        search.get_document_count.return_value = 4
        with (
            patch.object(readiness, "SearchClient", return_value=search),
            patch.object(readiness, "verify_search_index"),
            self.assertRaisesRegex(RuntimeError, "unexpected documents"),
        ):
            readiness.check_search()


def environment_values():
    return {
        "AZURE_ENV_NAME": "test-new",
        "AZURE_SUBSCRIPTION_ID": "subscription-new",
        "AZURE_TENANT_ID": "tenant-new",
        "AZURE_LOCATION": "swedencentral",
        "AZURE_RESOURCE_GROUP": "rg-test-new",
        "AZURE_PRINCIPAL_ID": "test-principal",
        "AZURE_FOUNDRY_SERVICE_NAME": "foundry-new",
        "AZURE_OPENAI_ENDPOINT": "https://foundry-new.cognitiveservices.azure.com/",
        "AZURE_OPENAI_DEPLOYMENT_NAME": "gpt-4o",
        "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME": "text-embedding-ada-002",
        "AZURE_AI_PROJECT_NAME": "ai3016-project",
        "AZURE_AI_PROJECT_ENDPOINT": "https://foundry-new.services.ai.azure.com/api/projects/ai3016-project",
        "AZURE_STORAGE_ACCOUNT_NAME": "storage-new",
        "AZURE_STORAGE_CONTAINER_NAME": "rag-sources",
        "AZURE_STORAGE_ENDPOINT": "https://storage-new.blob.core.windows.net/",
        "AZURE_SEARCH_ENDPOINT": "https://search-new.search.windows.net",
        "AZURE_KEY_VAULT_NAME": "kv-new",
        "AZURE_KEY_VAULT_URI": "https://kv-new.vault.azure.net/",
    }


def model_catalog():
    result = []
    for name, version in (("gpt-4o", "2024-11-20"), ("text-embedding-ada-002", "2")):
        result.append({
            "kind": "AIServices",
            "model": {
                "name": name, "version": version,
                "skus": [{
                    "name": "GlobalStandard",
                    "usageName": f"OpenAI.GlobalStandard.{name}",
                    "capacity": {"minimum": 1, "maximum": 1000, "step": 1},
                }],
            },
        })
    return result


def model_usages(current=0, limit=20):
    return [
        {"name": {"value": f"OpenAI.GlobalStandard.{name}"}, "currentValue": current, "limit": limit}
        for name in ("gpt-4o", "text-embedding-ada-002")
    ]


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_parameters_use_the_same_defaults_and_overrides_as_bicep(self):
        values = environment_values()
        parameters = provision.resolve_parameters(values)
        self.assertEqual(parameters["modelVersion"], "2024-11-20")
        self.assertEqual(parameters["embeddingsDeploymentCapacity"], "10")
        values["AZURE_OPENAI_MODEL_NAME"] = "custom-chat"
        values["AZURE_OPENAI_MODEL_VERSION"] = "custom-version"
        parameters = provision.resolve_parameters(values)
        self.assertEqual(parameters["modelName"], "custom-chat")
        self.assertEqual(parameters["modelVersion"], "custom-version")

    def test_private_services_require_explicit_fallback_opt_in(self):
        values = environment_values()
        with patch.object(provision, "cli_json", return_value="Disabled"):
            with self.assertRaisesRegex(ValueError, "AZURE_DEMO_ALLOW_POLICY_FALLBACK"):
                provision.policy_protected_services(values)
            values["AZURE_DEMO_ALLOW_POLICY_FALLBACK"] = "true"
            self.assertEqual(provision.policy_protected_services(values), {"storage", "keyvault"})

    def test_quota_failure_is_explicit(self):
        parameters = provision.resolve_parameters(environment_values())
        with self.assertRaisesRegex(ValueError, "Insufficient quota"):
            provision.validate_models(parameters, model_catalog(), model_usages(current=11), [])

    def test_existing_capacity_is_not_counted_twice_on_reprovision(self):
        parameters = provision.resolve_parameters(environment_values())
        deployments = [
            {"name": name, "properties": {"model": {"name": name}},
             "sku": {"name": "GlobalStandard", "capacity": 10}}
            for name in ("gpt-4o", "text-embedding-ada-002")
        ]
        provision.validate_models(parameters, model_catalog(), model_usages(current=20), deployments)

    def test_unknown_versions_skus_or_quota_do_not_pass_preflight(self):
        parameters = provision.resolve_parameters(environment_values())
        with self.assertRaisesRegex(ValueError, "unavailable"):
            provision.validate_models(parameters, [], model_usages(), [])
        parameters["modelDeploymentSku"] = "Unsupported"
        with self.assertRaisesRegex(ValueError, "does not support SKU"):
            provision.validate_models(parameters, model_catalog(), model_usages(), [])
        parameters["modelDeploymentSku"] = "GlobalStandard"
        with self.assertRaisesRegex(ValueError, "No quota information"):
            provision.validate_models(parameters, model_catalog(), [], [])

    def test_retired_models_are_rejected(self):
        catalog = model_catalog()
        catalog[0]["model"]["deprecation"] = {"inference": "2000-01-01T00:00:00Z"}
        with self.assertRaisesRegex(ValueError, "retired"):
            provision.validate_models(
                provision.resolve_parameters(environment_values()), catalog, model_usages(), []
            )

    def test_different_cli_tenant_is_rejected(self):
        account = {"tenantId": "wrong-tenant", "id": "subscription-new"}
        with patch.object(provision, "cli_json", return_value=account), self.assertRaises(ValueError):
            provision.validate_context(environment_values())

    def test_optional_settings_survive_same_environment_reprovision(self):
        values = environment_values()
        with tempfile.TemporaryDirectory() as directory, patch.object(provision, "ROOT", Path(directory)):
            path = Path(directory) / ".env"
            path.write_text(
                f'AZURE_SUBSCRIPTION_ID={values["AZURE_SUBSCRIPTION_ID"]}\n'
                f'AZURE_OPENAI_ENDPOINT={values["AZURE_OPENAI_ENDPOINT"]}\n'
                'FINE_TUNED_DEPLOYMENT_NAME=ft-example\n'
                'AZURE_VOICELIVE_MODEL=custom-voice\n'
                'CUSTOM_OPTION="keep me"\n'
                'AZURE_OPENAI_API_KEY=old-example-key\n',
                encoding="utf-8",
            )
            provision.write_runtime_environment(values, "example-search-key")
            settings = dotenv_values(path)
            self.assertEqual(settings["FINE_TUNED_DEPLOYMENT_NAME"], "ft-example")
            self.assertEqual(settings["AZURE_VOICELIVE_MODEL"], "custom-voice")
            self.assertEqual(settings["CUSTOM_OPTION"], "keep me")
            self.assertEqual(settings["AZURE_OPENAI_API_KEY"], "")

    def test_new_target_archives_old_configuration_without_reusing_it(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(provision, "ROOT", Path(directory)):
            path = Path(directory) / ".env"
            original = (
                "AZURE_SUBSCRIPTION_ID=subscription-old\n"
                "AZURE_OPENAI_ENDPOINT=https://old.example/\n"
                "AZURE_LANGUAGE_KEY=example-old-key\n"
                "FINE_TUNED_DEPLOYMENT_NAME=ft-old\n"
            )
            path.write_text(original, encoding="utf-8")
            provision.write_runtime_environment(environment_values(), "example-new-search-key")
            settings = dotenv_values(path)
            self.assertEqual(settings["AZURE_SUBSCRIPTION_ID"], "subscription-new")
            self.assertEqual(settings["AZURE_LANGUAGE_KEY"], "")
            self.assertEqual(settings["FINE_TUNED_DEPLOYMENT_NAME"], "")
            backups = list((Path(directory) / ".azure" / "backups").glob(".env.*.bak"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(encoding="utf-8"), original)

    def test_cached_environment_restores_its_own_optional_settings(self):
        first = environment_values()
        second = {**first, "AZURE_ENV_NAME": "another", "AZURE_OPENAI_ENDPOINT": "https://another.example/"}
        with tempfile.TemporaryDirectory() as directory, patch.object(provision, "ROOT", Path(directory)):
            provision.write_runtime_environment(first, "example-first-key")
            path = Path(directory) / ".env"
            with path.open("a", encoding="utf-8") as file:
                file.write("FINE_TUNED_DEPLOYMENT_NAME=ft-first\n")
            provision.write_runtime_environment(first, "example-first-key")
            provision.write_runtime_environment(second, "example-second-key")
            self.assertEqual(dotenv_values(path)["FINE_TUNED_DEPLOYMENT_NAME"], "")
            provision.write_runtime_environment(first, "example-first-key")
            self.assertEqual(dotenv_values(path)["FINE_TUNED_DEPLOYMENT_NAME"], "ft-first")

    def test_azd_override_wins_over_preserved_optional_setting(self):
        values = {**environment_values(), "AZURE_VOICELIVE_MODEL": "explicit-override"}
        settings = provision.runtime_settings(values, "example-key", {"AZURE_VOICELIVE_MODEL": "old-choice"})
        self.assertEqual(settings["AZURE_VOICELIVE_MODEL"], "explicit-override")

    def test_rbac_retry_is_limited_to_forbidden_errors(self):
        error = HttpResponseError("Role not propagated")
        error.status_code = 403
        operation = Mock(side_effect=[error, "success"])
        with patch.object(provision.time, "sleep"):
            self.assertEqual(provision.retry_rbac("Test", operation, attempts=2), "success")
        error.status_code = 400
        with patch.object(provision.time, "sleep") as sleep, self.assertRaises(HttpResponseError):
            provision.retry_rbac("Test", Mock(side_effect=error), attempts=2)
        sleep.assert_not_called()


class HostedToolTests(unittest.TestCase):
    def setUp(self):
        module = importlib.import_module("8_foundry_tool_calling_demo")
        self.demo = module.FoundryToolCallingDemo.__new__(module.FoundryToolCallingDemo)
        self.demo.model = "example-deployment"
        self.demo.client = Mock()
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_failed_response_is_not_a_successful_tool_demo(self):
        self.demo.client.responses.create.return_value = SimpleNamespace(status="failed", error="Tool unavailable")
        with self.assertRaisesRegex(RuntimeError, "Response failed"):
            self.demo._create_response("Question", [])

    def test_project_endpoint_normalization_is_idempotent(self):
        canonical = "https://example.services.ai.azure.com/api/projects/demo"
        legacy = "https://example.cognitiveservices.azure.com/projects/demo"
        self.assertEqual(normalize_project_endpoint(legacy), canonical)
        self.assertEqual(normalize_project_endpoint(canonical), canonical)
        self.assertEqual(normalize_project_endpoint(normalize_project_endpoint(legacy)), canonical)

    def test_tools_must_actually_execute(self):
        response = SimpleNamespace(output=[], output_text="An answer without a tool")
        self.demo._create_response = Mock(return_value=response)
        self.demo._prepare_file_search = Mock(return_value="example-vector-store")
        for method in (
            self.demo.run_code_interpreter, self.demo.run_web_search,
            self.demo.run_file_search, self.demo.run_function,
        ):
            with self.subTest(method=method.__name__), self.assertRaises(RuntimeError):
                method()

    def test_function_demo_requires_and_returns_a_local_tool_result(self):
        call = SimpleNamespace(
            type="function_call", name="get_customer_service_channel",
            arguments='{"issue_type":"stolen_card","urgency":"urgent"}', call_id="example-call",
        )
        first = SimpleNamespace(id="example-response", output=[call])
        final = SimpleNamespace(output=[], output_text="Use 24/7 emergency card services.")
        self.demo._create_response = Mock(side_effect=[first, final])
        self.demo.run_function()
        arguments = self.demo._create_response.call_args.kwargs
        self.assertEqual(arguments["previous_response_id"], "example-response")
        self.assertEqual(arguments["input_items"][0]["call_id"], "example-call")
        self.assertIn("24/7 emergency card services", arguments["input_items"][0]["output"])


class PrivateSetupTests(unittest.TestCase):
    def test_recorded_execution_must_belong_to_this_job_and_succeed(self):
        job_id = "/subscriptions/test/resourceGroups/test/providers/Microsoft.App/jobs/test"
        values = {
            "AZURE_DEMO_PRIVATE_SETUP_JOB_ID": job_id,
            "AZURE_DEMO_PRIVATE_SETUP_EXECUTION_ID": f"{job_id}/executions/test-run",
        }
        with patch.object(provision, "cli_json", return_value={"properties": {"status": "Failed"}}):
            with self.assertRaises(RuntimeError):
                provision.verify_private_setup_execution(values)
        values["AZURE_DEMO_PRIVATE_SETUP_EXECUTION_ID"] = "/another/job/executions/test-run"
        with patch.object(provision, "cli_json") as cli, self.assertRaises(ValueError):
            provision.verify_private_setup_execution(values)
        cli.assert_not_called()

    def test_failed_or_timed_out_execution_does_not_report_private_readiness(self):
        job_id = "/subscriptions/test/resourceGroups/test/providers/Microsoft.App/jobs/test"
        started = {"id": f"{job_id}/executions/test-run", "name": "test-run"}
        values = {"AZURE_DEMO_PRIVATE_SETUP_JOB_ID": job_id}
        for state in ("Failed", "Running"):
            with (
                self.subTest(state=state),
                patch.object(provision, "cli_json", side_effect=[started, {"properties": {"status": state}}]),
                redirect_stdout(io.StringIO()),
                self.assertRaises(RuntimeError),
            ):
                provision.run_private_setup(values, attempts=1, delay=0)

    def test_private_dns_rejects_public_or_mixed_answers(self):
        for addresses in (["20.1.2.3"], ["10.46.1.4", "20.1.2.3"]):
            records = [(None, None, None, None, (address, 443)) for address in addresses]
            with (
                self.subTest(addresses=addresses),
                patch.object(private_setup.socket, "getaddrinfo", return_value=records),
                patch.object(private_setup.time, "sleep"),
                self.assertRaises(RuntimeError),
            ):
                private_setup.verify_private_dns("https://test.blob.core.windows.net")

    def test_private_dns_accepts_private_addresses(self):
        records = [(None, None, None, None, ("10.46.1.4", 443))]
        with (
            patch.object(private_setup.socket, "getaddrinfo", return_value=records),
            redirect_stdout(io.StringIO()) as output,
        ):
            private_setup.verify_private_dns("https://test.vault.azure.net")
        self.assertIn("resolves privately", output.getvalue())


class GroundedRagTests(unittest.TestCase):
    def test_current_rag_uses_retrieved_evidence_not_retired_data_sources(self):
        client = Mock()
        client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1] * 1536)]
        )
        client.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Refunds take 5-7 business days. Source: Bank Policies."))]
        )
        search = MagicMock()
        search.__enter__.return_value = search
        search.search.return_value = [{"title": "Bank Policies", "content": "Refunds take 5-7 business days."}]
        with patch.object(rag_grounding, "SearchClient", return_value=search):
            answer, sources = rag_grounding.answer_with_search(
                client, "How long do refunds take?",
                search_endpoint="https://test.search.windows.net", search_key="unit-test",
            )
        self.assertIn("5-7", answer)
        self.assertEqual(sources, ["Bank Policies"])
        request = client.chat.completions.create.call_args.kwargs
        self.assertNotIn("extra_body", request)
        self.assertIn("Refunds take 5-7 business days.", request["messages"][1]["content"])

    def test_missing_evidence_does_not_generate_an_ungrounded_answer(self):
        client = Mock()
        client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1] * 1536)]
        )
        search = MagicMock()
        search.__enter__.return_value = search
        search.search.return_value = []
        with patch.object(rag_grounding, "SearchClient", return_value=search), self.assertRaises(RuntimeError):
            rag_grounding.answer_with_search(
                client, "Question", search_endpoint="https://test.search.windows.net", search_key="unit-test",
            )
        client.chat.completions.create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
