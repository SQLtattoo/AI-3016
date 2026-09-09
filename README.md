# AI-3016 Microsoft Foundry Demo Suite

Educational demonstrations of Microsoft Foundry, Azure OpenAI, fine-tuning, Retrieval-Augmented Generation (RAG), tool calling, and lightweight RAG evaluation.

> [!IMPORTANT]
> This repository is for educational and demonstration purposes. It is not production-ready guidance. Running `azd up`, model inference, fine-tuning, Azure AI Search, Storage, and related Azure services can incur real charges in your subscription. Review the generated resources and current Azure pricing, then run `azd down --force --purge` when the environment is no longer needed.

## 🎯 Available Demos

### **Core Demos**
- `0_concept_demo.py` - Local fine-tuning and RAG concept walkthrough; no Azure required
- `2c_rag_api_demo.py` - Azure OpenAI On Your Data pattern with Azure AI Search
- `3b_chat_client.py` - Keyless Microsoft Foundry SDK chat client
- `3c_chat_api_comparison.py` - Chat Completions versus Responses API state handling
- `4_comparison_demo.py` - Base model, RAG, and fine-tuned-model comparison
- `5_agentic_rag_tool_demo.py` - Application-orchestrated RAG with tool calling
- `6_rag_quality_eval_demo.py` - Lightweight golden-set RAG quality checks

### **Fine-tuning Demos**
- `1a_fine_tuning_portal_guide.md` - Portal-based fine-tuning walkthrough
- `1b_fine_tuning_code_first.py` - Programmatic fine-tuning implementation
- `1_fine_tuning_demo.py` - Legacy fine-tuning workflow example

### **Alternative RAG Approaches**
- `2a_rag_portal_guide.md` - Portal RAG wizard (UI-based)
- `2b_rag_code_first.py` - Manual RAG pipeline (full control)
- `2d_rag_keyvault_demo.py` - Key Vault-backed RAG configuration with `.env` fallback
- `2_rag_pattern_demo.py` - Legacy end-to-end RAG pattern example

---

## 🚀 Quick Start

### **Prerequisites**

- **Azure Subscription** with permissions to create resources
- **Azure Developer CLI (`azd`)** - [Install here](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- **Azure CLI** - [Install here](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **Python 3.10+**

### **One-Command Deployment**

```powershell
# 1. Login to Azure
az login

# 2. Deploy everything (8-12 minutes)
azd up

# 3. Create and activate the Python environment
python setup_venv.py
.\activate_env.ps1

# 4. Run the search setup and smoke tests
python setup_search_index.py
python 0_concept_demo.py
python 2c_rag_api_demo.py
python 3_chat_client_demo.py --once "What is Microsoft Foundry?"
python 4_comparison_demo.py --once "What is the refund policy for credit cards?"
```

For manual configuration without `azd`, copy `.env.example` to `.env`, replace the placeholders, and run `az login` when using Microsoft Entra authentication. Never commit `.env`.

### **What Gets Deployed**

`azd up` creates:
- **Microsoft Foundry** (`AIServices`) with GPT-4o and `text-embedding-ada-002` deployments
- **Microsoft Foundry Project** connected to the Foundry resource
- **Azure AI Search** (Basic tier) with a vector index
- **Storage Account** with the RAG source documents
- **Azure Key Vault** and required role assignments
- An auto-generated local `.env` file; OpenAI clients use Microsoft Entra ID when a usable API key is unavailable

The default location is `swedencentral`; supported locations are defined in `infra/main.bicep`. Availability, quota, and pricing vary by subscription and region.

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
python 3c_chat_api_comparison.py

# 5. Compare base, RAG, and fine-tuned approaches
python 4_comparison_demo.py --once "What is the refund policy for credit cards?"

# 6. Demonstrate tool calling and evaluation
python 5_agentic_rag_tool_demo.py
python 6_rag_quality_eval_demo.py

# 7. Validate the fine-tuning workflow without starting a paid job
python 1b_fine_tuning_code_first.py --dry-run --initials demo
```

`2c_rag_api_demo.py` runs two fixed banking questions. Use `5_agentic_rag_tool_demo.py --question "..."` or `4_comparison_demo.py --once "..."` for custom one-shot questions.

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
├── 2c_rag_api_demo.py            # Azure OpenAI data_sources RAG
├── 2d_rag_keyvault_demo.py       # Key Vault configuration example
├── 3_chat_client_demo.py         # Interactive OpenAI SDK chat
├── 3b_chat_client.py             # Microsoft Foundry SDK chat
├── 3c_chat_api_comparison.py     # Chat Completions vs Responses
├── 4_comparison_demo.py          # Base vs RAG vs fine-tuning
├── 5_agentic_rag_tool_demo.py    # Tool-calling RAG workflow
├── 6_rag_quality_eval_demo.py    # RAG evaluation harness
├── 1a_fine_tuning_portal_guide.md
├── 2a_rag_portal_guide.md
├── bank-dataset-generator.py      # Generates training data
├── setup_search_index.py          # Builds and populates the search index
├── azure_openai_auth.py           # Shared key/Entra client helper
├── azure.yaml                    # Azure Developer CLI config
├── .env.example                  # Placeholder-only configuration reference
├── infra/                        # Infrastructure as Code
│   ├── main.bicep               # Main Bicep template
│   ├── main.parameters.json     # Deployment parameters
│   ├── modules/                 # Resource modules
│   └── hooks/                   # Post-deployment scripts
├── RAG-sources/                  # Banking documents
│   ├── bank_policies.txt
│   ├── customer_service.txt
│   └── investment_products.txt
├── activate_env.ps1/.sh/.bat     # Environment activation
├── requirements.txt              # Python dependencies
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
- Hybrid search (keyword + semantic)
- Source attribution and citations
- Production-oriented patterns presented as educational samples

### **Microsoft Foundry SDK**
- Keyless authentication with `DefaultAzureCredential`
- Chat Completions with application-managed history
- Responses API with `previous_response_id`
- Streaming and standard response modes in the OpenAI SDK client

---

## 💡 Infrastructure Management

### **Deployment Commands**

```powershell
# Full deployment
azd up

# View current environment
azd env get-values

# Check deployment status
azd monitor

# Complete teardown
azd down --force --purge
```

### **What `azd up` Does**

1. **Provisions Azure resources** using Bicep templates
2. **Deploys GPT-4o model** to Microsoft Foundry
3. **Deploys text-embedding-ada-002** to the same Foundry resource
4. **Uploads RAG documents** to storage
5. **Creates search index** with vector embeddings
6. **Generates an ignored `.env` file** with endpoints and available local credentials
7. **Assigns RBAC permissions** for seamless access

### **Cost Optimization**

- **Deploy only when needed:** `azd up` before class
- **Delete after class:** `azd down --force --purge`
- **Monitor costs:** Use Azure Cost Management
- **Estimate before deploying:** Prices, quotas, and free grants change; use the Azure pricing calculator and your subscription's Cost Management view

---

## 🛠️ Troubleshooting

### **Common Issues**

| Issue | Solution |
|-------|----------|
| **Module not found** | Run `.\activate_env.ps1` and `pip install -r requirements.txt` |
| **Azure credentials** | Run `az login` |
| **.env missing** | Re-run `azd up` or `.\infra\hooks\postprovision.ps1` |
| **Search index missing** | Run `python setup_search_index.py` |
| **Quota exceeded** | Check model availability and quota in another supported region |
| **RAG not working** | Verify search index exists in Azure Portal |

### **Getting Help**

1. View deployment logs: `azd provision --debug`
2. Verify environment: `azd env get-values`
3. Rebuild the search index: `python setup_search_index.py`

---

## 📚 Additional Resources

### **Documentation**
- [Microsoft Foundry](https://learn.microsoft.com/azure/ai-studio/)
- [Azure OpenAI Service](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure AI Search](https://learn.microsoft.com/azure/search/)
- [Azure Developer CLI](https://learn.microsoft.com/azure/developer/azure-developer-cli/)

### **Course Materials**
- `1a_fine_tuning_portal_guide.md` - Portal fine-tuning walkthrough
- `2a_rag_portal_guide.md` - Portal RAG walkthrough
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
- [ ] Ran `python setup_search_index.py`
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
