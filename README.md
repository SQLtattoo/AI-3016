# AI-3016 Microsoft Foundry Demo Suite

Educational demonstrations of Microsoft Foundry, Azure OpenAI, fine-tuning, Retrieval-Augmented Generation (RAG), tool calling, and lightweight RAG evaluation.

> [!IMPORTANT]
> This repository is for educational and demonstration purposes. It is not production-ready guidance. Running `azd up`, model inference, fine-tuning, Azure AI Search, Storage, and related Azure services can incur real charges in your subscription. Review the generated resources and current Azure pricing, then run `azd down --force --purge` when the environment is no longer needed.

## 🎯 Available Demos

### **Core Demos**
- `0_concept_demo.py` - Local fine-tuning and RAG concept walkthrough; no Azure required
- `2c_rag_api_demo.py` - Azure AI Search retrieval and grounded Azure OpenAI answers
- `3b_chat_client.py` - Keyless Microsoft Foundry SDK chat with per-call input/output tokens, input growth, and cumulative usage (resent history is counted again)
- `3c_chat_api_comparison.py` - Chat Completions versus Responses API state handling
- `4_comparison_demo.py` - Base model, RAG, and fine-tuned-model comparison
- `5_agentic_rag_tool_demo.py` - Application-orchestrated RAG with tool calling
- `6_rag_quality_eval_demo.py` - Lightweight golden-set RAG quality checks
- `7_foundry_rag_language_voice_demo.py` - RAG, Azure Language MCP, and Voice Live
- `8_foundry_tool_calling_demo.py` - Responses API hosted tools and local functions

### **Fine-tuning Demos**
- `1a_fine_tuning_portal_guide.md` - Portal-based fine-tuning walkthrough
- `1b_fine_tuning_code_first.py` - Programmatic fine-tuning implementation
- `1_fine_tuning_demo.py` - Legacy fine-tuning workflow example

### **Alternative RAG Approaches**
- `2a_rag_portal_guide.md` - Portal Foundry IQ Knowledge and Agent Playground walkthrough (manual setup)
- `2b_rag_code_first.py` - Manual RAG pipeline (full control)
- `2d_rag_keyvault_demo.py` - Key Vault-backed RAG configuration with `.env` fallback
- `2_rag_pattern_demo.py` - Legacy end-to-end RAG pattern example

---

## 🚀 Quick Start

### **Prerequisites**

- **Azure Subscription** with permission to create resources and resource-scoped role assignments
- **Azure Developer CLI (`azd`)** - [Install here](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- **Azure CLI** - [Install here](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **Python 3.10+** on `PATH` (`python` on Windows, `python3` on Linux/macOS)
- **PowerShell 7+** on Windows; a POSIX shell on Linux/macOS

### **One-Command Deployment**

```powershell
# 1. Sign both CLIs into the target tenant and select the subscription
az login --tenant "<tenant-id>"
az account set --subscription "<subscription-id>"
azd auth login --tenant-id "<tenant-id>"

# 2. Create a separate environment for a new target
azd env new ai3016-demo
azd env set AZURE_SUBSCRIPTION_ID "<subscription-id>"
azd env set AZURE_TENANT_ID "<tenant-id>"
azd env set AZURE_LOCATION swedencentral

# Include Demo 7 dependencies and live Language/Voice service checks
azd env set AZURE_DEMO_INCLUDE_LANGUAGE_VOICE true

# 3. Preview, then provision and prepare the demos
azd provision --preview --no-prompt
azd up --no-prompt

# 4. Activate the environment created automatically by the hooks
.\ai3016-env\Scripts\Activate.ps1
python check_demo_readiness.py
python 0_concept_demo.py
python 2c_rag_api_demo.py
python 3_chat_client_demo.py --once "What is Microsoft Foundry?"
python 4_comparison_demo.py --once "What is the refund policy for credit cards?"
```

For manual configuration against existing Azure resources, follow [Manual Setup](#manual-setup-existing-resources). Never commit `.env`.

The hooks create `ai3016-env`, install dependencies, validate the selected model versions/SKUs/quota, upload the sources, populate Search, and run real demo requests. A failed setup or readiness check fails `azd up`; it is not reported as a successful deployment. On Linux/macOS, activate with `source ai3016-env/bin/activate`.

Reuse an existing target with `azd env select <environment-name>` instead of creating it again. The Azure CLI subscription must match that environment. Optional settings survive reruns only for the same environment; switching targets archives the old root `.env` under ignored `.azure\backups` and restores that target's own cached settings.

### **Provisioning Configuration**

Infrastructure inputs belong in the selected azd environment (`.azure\<environment>\.env`), not the generated root `.env`. Use `azd env set NAME VALUE` before `azd up`.

| Input | Default / purpose |
|-------|-------------------|
| `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_LOCATION` | Explicit target; default region `swedencentral` |
| `AZURE_RESOURCE_GROUP` | `rg-<environment-name>` |
| `AZURE_STORAGE_PUBLIC_NETWORK_ACCESS`, `AZURE_KEY_VAULT_PUBLIC_NETWORK_ACCESS` | `Enabled`; approved policy fallback persists observed `Disabled` values so later deployments do not try to reopen them |
| `AZURE_OPENAI_DEPLOYMENT_NAME`, `AZURE_OPENAI_MODEL_NAME`, `AZURE_OPENAI_MODEL_VERSION` | `gpt-4o`, `gpt-4o`, `2024-11-20` |
| `AZURE_OPENAI_DEPLOYMENT_SKU`, `AZURE_OPENAI_DEPLOYMENT_CAPACITY` | `GlobalStandard`, `10` |
| `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME`, `AZURE_OPENAI_EMBEDDINGS_MODEL_NAME`, `AZURE_OPENAI_EMBEDDINGS_MODEL_VERSION` | `text-embedding-ada-002`, `text-embedding-ada-002`, `2` |
| `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_SKU`, `AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_CAPACITY` | `GlobalStandard`, `10` |
| `AZURE_PRINCIPAL_ID`, `AZURE_PRINCIPAL_TYPE` | Detected CLI developer identity; override together for another identity |
| `AZURE_DEMO_INCLUDE_LANGUAGE_VOICE` | `false`; set `true` for Demo 7 dependencies and service checks |
| `AZURE_DEMO_ALLOW_POLICY_FALLBACK` | `false`; explicitly allow local sources/`.env` if policy disables Storage/Key Vault public access; private access remains unverified |
| `AZURE_DEMO_PRIVATE_SETUP` | `false`; add private endpoints/DNS and a manual Consumption setup job to verify protected Storage/Key Vault inside Azure |

Keep the 1,536-dimensional embeddings model compatible with the index. Hosted tools must also pass `check_demo_readiness.py`; chat support alone is not sufficient. Azure OpenAI On Your Data is retired: demos 2C/2D now retrieve evidence with the Search SDK and generate grounded answers, rather than sending the rejected `data_sources` parameter.

### **What Gets Deployed**

`azd up` creates:
- **Microsoft Foundry** (`AIServices`) with GPT-4o and `text-embedding-ada-002` deployments
- **Microsoft Foundry Project** connected to the Foundry resource
- **Azure AI Search** (Basic tier) with a vector index
- **Storage Account** with the RAG source documents
- **Azure Key Vault** and required role assignments
- An auto-generated local `.env` file; Foundry local-key authentication is disabled and the demos use Microsoft Entra ID. Search demos still use a generated Search admin key, also stored in Key Vault.

The default location is `swedencentral`; supported locations are defined in `infra/main.bicep`. Availability, quota, and pricing vary by subscription and region.

Language and Voice Live use the same unified Foundry resource; Voice Live's predeployed `gpt-realtime` model needs no separate model deployment. Hosted tools need no local server deployment, and temporary file-search stores/files are cleaned up. A Voice Live session check does not exercise your microphone/speakers; run Demo 7 with `--voice` before presenting.

If tenant policy disables Storage or Key Vault public access, leave those protections unchanged. For a class that does not require their private data planes, explicitly run `azd env set AZURE_DEMO_ALLOW_POLICY_FALLBACK true`. Setup then uses local RAG sources and `.env`, prints the limitations, and still verifies the actual class demos. Otherwise configure an approved private network; retrying RBAC cannot fix a network-policy block.

For Azure-side private access, also set `AZURE_DEMO_PRIVATE_SETUP=true` and both `AZURE_STORAGE_PUBLIC_NETWORK_ACCESS` and `AZURE_KEY_VAULT_PUBLIC_NETWORK_ACCESS` to `Disabled`, then run `azd up`. This adds two private endpoints, private DNS zones/VNet links, and a VNet-integrated manual Azure Container Apps Consumption job with no ingress. Its resource-scoped managed identity uploads all three source blobs, stores the Search key/settings in Key Vault without logging values, verifies private DNS and reads everything back. No VM, VPN, registry, or custom container image is needed; the job uses a versioned Microsoft image and Python's standard library. Private endpoints/DNS incur ongoing charges; the job consumes compute only while running.

The post-provision hook starts and waits for that job before running the local class checks. A failed private job fails setup. The execution resource ID is recorded in ignored azd/runtime state. This does **not** give your laptop a route into the VNet: local demos keep their explicit fallback until you connect an approved VPN/ExpressRoute/private client.

**Fine-tuning is not provisioned.** The readiness check runs only the training dry-run. A real paid training job and a resulting fine-tuned deployment are separate; set `FINE_TUNED_DEPLOYMENT_NAME` afterward to enable the real third-model comparison.

**Foundry IQ Knowledge and portal agents are not provisioned or checked by readiness.** Create and test them separately using [Demo 2A](2a_rag_portal_guide.md). The Python RAG demos use application-managed Search retrieval, not that portal agent.

### **Manual Setup (Existing Resources)**

```powershell
python -m venv ai3016-env
.\ai3016-env\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Replace the placeholders in `.env` with the endpoints, deployment names, Search admin key, and target context for your existing resources. Sign in with `az login --tenant "<tenant-id>"` and select the subscription with `az account set --subscription "<subscription-id>"`. Foundry local keys remain empty when using Microsoft Entra authentication; the signed-in identity needs the appropriate resource-scoped roles.

For Demo 7, also run `python -m pip install -r requirements-optional.txt`. PyAudio may require platform-specific PortAudio prerequisites. On Linux/macOS, create the environment with `python3 -m venv ai3016-env`, activate it with `source ai3016-env/bin/activate`, and copy the example using your shell.

Run `python setup_search_index.py` to populate Search, then run your chosen demos. `python check_demo_readiness.py` is a broader live check: it requires the complete deployed environment, validates the Azure CLI context, invokes billable services, and checks all core demos, not just the one you selected.

---

## 🎓 Running the Demos

### **Recommended Demo Flow**

```powershell
# 1. Start with concepts (no Azure needed)
python 0_concept_demo.py

# 2. Create or refresh the search index
python setup_search_index.py

# 3. Show RAG in action
python 2c_rag_api_demo.py

# 4. Compare client-side and service-side conversation state
python 3b_chat_client.py
python 3c_chat_api_comparison.py

# 5. Compare base, RAG, and fine-tuned approaches
python 4_comparison_demo.py --once "What is the refund policy for credit cards?"

# 6. Demonstrate tool calling and evaluation
python 5_agentic_rag_tool_demo.py
python 6_rag_quality_eval_demo.py

# 7. Add privacy-aware typed or live voice interaction
python 7_foundry_rag_language_voice_demo.py --question "What is the refund policy?"
# Microphone mode: python 7_foundry_rag_language_voice_demo.py --voice

# 8. Compare Foundry-hosted tools with a local function
python 8_foundry_tool_calling_demo.py --tool all

# 9. Validate the fine-tuning workflow without starting a paid job
python 1b_fine_tuning_code_first.py --dry-run --initials demo
```

`2c_rag_api_demo.py` runs two fixed banking questions. Use `5_agentic_rag_tool_demo.py --question "..."` or `4_comparison_demo.py --once "..."` for custom one-shot questions.

`3b_chat_client.py` reports each call's input/output tokens, input growth since the previous call, and cumulative usage. Resent conversation history contributes input tokens again on every call. If the API omits usage, the client explicitly marks cumulative totals as incomplete rather than treating that call as free.

### **Demo 7: Language MCP and Voice Live**

Demo 7 sends each typed customer turn through a local MCP server backed by Azure AI Language PII redaction before retrieval or logging. It then searches the existing Azure AI Search index and answers from bank-policy evidence. With `--voice`, the same privacy and retrieval tools are exposed to Azure Voice Live for real-time microphone and speaker interaction.

```powershell
# One typed turn
python 7_foundry_rag_language_voice_demo.py --question "My name is Jane Doe. How long can a card refund take?"

# Interactive typed mode
python 7_foundry_rag_language_voice_demo.py

# Live microphone mode; press Ctrl+C to stop
python 7_foundry_rag_language_voice_demo.py --voice
```

Typed mode requires the Azure Language, MCP, and search settings generated in `.env`. Voice mode additionally requires a working microphone/speaker, the Voice Live settings in `.env`, and the optional `pyaudio` dependency.

Use synthetic customer examples. Typed text is sent to Azure AI Language for redaction first. Voice Live receives the original microphone audio before any text-redaction tool runs; this demo is not an end-to-end anonymization or compliance guarantee.

### **Demo 8: Responses API Tools**

Demo 8 uses the same `DEPLOYMENT_NAME` model through the Foundry project client. Code Interpreter, web search, and file search execute in Microsoft Foundry; `get_customer_service_channel` is selected by the model but executed by the local Python application.

```powershell
# Run all four tool scenarios
python 8_foundry_tool_calling_demo.py --tool all

# Run one scenario
python 8_foundry_tool_calling_demo.py --tool code_interpreter
python 8_foundry_tool_calling_demo.py --tool web_search
python 8_foundry_tool_calling_demo.py --tool file_search
python 8_foundry_tool_calling_demo.py --tool function

# List scenarios without connecting to Azure
python 8_foundry_tool_calling_demo.py --list
```

The file-search scenario uploads the files in `RAG-sources/` to a temporary vector store and deletes the vector store and uploaded files when the run ends. Use `--keep-resources` only when you intentionally want to inspect and later delete those resources yourself.

---

## 🧹 Cleanup

### **After Class - Delete Everything**

```powershell
# Delete all Azure resources (saves money!)
azd down --force --purge
```

**Important:** This removes all resources and stops billing. Re-run `azd up` before your next class.

---

## 📁 Project Structure

```
ai3016/
├── 0_concept_demo.py              # Start here - no Azure needed
├── 1b_fine_tuning_code_first.py  # Code-first fine-tuning workflow
├── 2b_rag_code_first.py          # Manual retrieval and generation
├── 2c_rag_api_demo.py            # Application-managed Search grounding
├── 2d_rag_keyvault_demo.py       # Key Vault configuration example
├── 3_chat_client_demo.py         # Interactive OpenAI SDK chat
├── 3b_chat_client.py             # Microsoft Foundry SDK chat
├── 3c_chat_api_comparison.py     # Chat Completions vs Responses
├── 4_comparison_demo.py          # Base vs RAG vs fine-tuning
├── 5_agentic_rag_tool_demo.py    # Tool-calling RAG workflow
├── 6_rag_quality_eval_demo.py    # RAG evaluation harness
├── 7_foundry_rag_language_voice_demo.py # Language MCP, RAG, and Voice Live
├── 8_foundry_tool_calling_demo.py # Responses hosted tools and local function
├── 1a_fine_tuning_portal_guide.md
├── 2a_rag_portal_guide.md
├── bank-dataset-generator.py      # Generates training data
├── setup_search_index.py          # Builds and populates the search index
├── check_demo_readiness.py        # Live, fail-fast demo verification
├── azure_openai_auth.py           # Shared key/Entra client helper
├── rag_grounding.py               # Shared current RAG retrieval/generation path
├── azure.yaml                    # Azure Developer CLI config
├── .env.example                  # Placeholder-only configuration reference
├── infra/                        # Infrastructure as Code
│   ├── main.bicep               # Main Bicep template
│   ├── main.parameters.json     # Deployment parameters
│   ├── modules/                 # Resource modules
│   └── hooks/                   # Portable bootstrap and provisioning hooks
├── RAG-sources/                  # Banking documents
│   ├── bank_policies.txt
│   ├── customer_service.txt
│   └── investment_products.txt
├── activate_env.ps1/.sh          # Environment activation
├── requirements.txt              # Python dependencies
├── requirements-optional.txt     # Notebook, Language MCP, and voice dependencies
├── tests/                        # Mocked provisioning, RAG, tools, and token-usage tests
└── .env                          # Generated locally and ignored by Git
```

---

## 🎯 Key Features

### **Fine-tuning**
- Banking domain specialization
- Multi-turn conversation training
- 50 high-quality training examples
- Cost-optimized hyperparameters

### **RAG Implementation**
- Real banking documents in `RAG-sources/`
- Hybrid search (keyword + vector)
- Source attribution and citations
- Production-oriented patterns presented as educational samples

### **Microsoft Foundry SDK**
- Keyless authentication with `DefaultAzureCredential`
- Chat Completions with application-managed history
- Responses API with `previous_response_id`
- Responses API hosted Code Interpreter, web search, and file search
- Model-selected functions executed by the application
- Streaming and standard response modes in the OpenAI SDK client

### **Language and Voice**

- Azure AI Language PII redaction exposed through a local MCP server
- Redaction before typed requests are logged, searched, or sent to the model
- Azure Voice Live with server VAD, echo cancellation, and noise suppression
- Shared privacy and retrieval tool runtime across typed and voice modes

---

## 💡 Infrastructure Management

### **Deployment Commands**

```powershell
# Full deployment
azd up

# Inspect environment names without printing credentials
azd env list

# Check deployment status
azd monitor

# Complete teardown
azd down --force --purge
```

### **What `azd up` Does**

1. **Bootstraps Python and checks the target, models, and quota** before provisioning
2. **Provisions the resource group, Foundry project/models, Search, Storage, Key Vault, and scoped RBAC**
3. **Generates an ignored root `.env`** while preserving same-environment optional settings
4. **Uploads the three repository sources** and stores the demo configuration in Key Vault
5. **Builds the Search index** and verifies every document, persisted embedding, and vector retrieval
6. **Runs real chat, Responses state, RAG, hosted-tool, function, and quality checks**
7. **Checks Language MCP and a hardware-free Voice Live session** when selected; never starts fine-tuning

### **Cost Optimization**

- **Deploy only when needed:** `azd up` before class
- **Delete after class:** `azd down --force --purge`
- **Monitor costs:** Use Azure Cost Management
- **Estimate before deploying:** Prices, quotas, and free grants change; use the Azure pricing calculator and your subscription's Cost Management view

### **Local Validation (No Azure Calls)**

After activating the Python environment and installing the core requirements:

```powershell
python -m unittest discover -s tests -v
python 8_foundry_tool_calling_demo.py --list
az bicep build --file infra/main.bicep --stdout > $null
```

The unit tests mock service and CLI calls. The Bicep command compiles the templates without deploying resources. Unlike these local checks, `check_demo_readiness.py` uses real Azure services and can incur charges.

Keep generated `.env`, `.azure/` state/backups, the virtual environment, and private course-delivery notes under `docs/` out of commits. Public setup and demo instructions live in this README and the tracked root-level guides.

---

## 🛠️ Troubleshooting

### **Common Issues**

| Issue | Solution |
|-------|----------|
| **Module not found** | Run `.\ai3016-env\Scripts\Activate.ps1` and `pip install -r requirements.txt` |
| **Azure credentials / context mismatch** | Sign into the configured tenant and use `az account set --subscription "<subscription-id>"` |
| **.env missing / post-provision failed** | Fix the reported error, then rerun `azd up` or `.\infra\hooks\postprovision.ps1` |
| **Search index missing** | Run `python setup_search_index.py` |
| **Demo 7 module missing** | Run `pip install -r requirements-optional.txt` |
| **Voice microphone unavailable** | Verify the OS input device and install a compatible `pyaudio` build |
| **Demo 8 project endpoint missing** | Verify `AZURE_AI_PROJECT_ENDPOINT` in `.env` and re-run `azd up` if needed |
| **Quota exceeded** | Check model availability and quota in another supported region |
| **RAG not working** | Verify search index exists in Azure Portal |
| **Hosted tool unavailable** | Check the selected model/region and subscription tool policies; do not treat a chat-only response as tool success |

### **Getting Help**

1. View deployment logs: `azd provision --debug`
2. Verify the selected environment: `azd env list` (do not share raw `.env` or `get-values` output)
3. Rebuild the search index: `python setup_search_index.py`, then run `python check_demo_readiness.py`

---

## 📚 Additional Resources

### **Documentation**
- [Microsoft Foundry](https://learn.microsoft.com/azure/ai-studio/)
- [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/)

### **Course Materials**
- `1a_fine_tuning_portal_guide.md` - Portal fine-tuning walkthrough
- `2a_rag_portal_guide.md` - Manual Foundry IQ Knowledge and Agent Playground walkthrough
- `TRAINING_DATA_GUIDE.md` - Fine-tuning data format reference
- `prompt_engineering.md` - Prompt-engineering examples

---

## ✅ Pre-flight Checklist

- [ ] Installed Azure Developer CLI (`azd`)
- [ ] Logged into Azure (`az login`)
- [ ] Ran `azd up` successfully
- [ ] Verified `.env` file exists with embeddings config
- [ ] Confirmed search index created (check Azure Portal)
- [ ] Activated Python environment
- [ ] Ran `python check_demo_readiness.py` successfully
- [ ] Tested microphone/speakers with Demo 7 `--voice`, if presenting Voice Live
- [ ] Separately prepared a fine-tuned deployment, if presenting a real fine-tuned-model comparison
- [ ] Tested the selected demos
- [ ] Reviewed Azure Cost Management and planned cleanup

---

## 🎉 Success Criteria

After completing the demos, you will understand:
- ✅ Fine-tuning workflow and best practices
- ✅ RAG architecture and implementation patterns  
- ✅ Azure AI services integration
- ✅ Production deployment considerations
- ✅ Modern Azure developer workflows with `azd`

---

Use these samples to learn and teach the patterns, then apply your organization's security, reliability, evaluation, and governance requirements before adapting them for production.
