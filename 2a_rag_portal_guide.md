# AI-3016 Demo 2A: RAG with Foundry IQ Knowledge

**Demo duration:** 20 minutes

**Audience:** Mixed skill levels

**Focus:** Connect an Azure AI Search index to a Microsoft Foundry agent through Foundry IQ Knowledge

---

## Demo Overview

This demo uses the current Microsoft Foundry experience. The three banking documents are already indexed in Azure AI Search. In Microsoft Foundry, you create a reusable Knowledge object from that index and attach it to an agent in the Agent Playground.

```text
Banking documents
        |
        v
Azure AI Search index
        |
        v
Foundry IQ Knowledge (knowledge base over MCP)
        |
        v
Foundry Agent -> grounded answer with citations
```

This replaces the retired model-playground data-source attachment workflow.

### Learning Objectives

- Explain the difference between an index, a Foundry IQ Knowledge object, and an agent.
- Connect an existing Azure AI Search index to Foundry IQ.
- Give an agent access to the Knowledge object.
- Test grounded answers and citations in the Agent Playground.
- Explain why the Foundry **project managed identity** needs data-plane access to Search.

---

## Validated Demo Resources

| Resource | Value |
|---|---|
| Resource group | Value of `AZURE_RESOURCE_GROUP` from `azd env get-values` |
| Foundry account | Value of `AZURE_FOUNDRY_SERVICE_NAME` from `azd env get-values` |
| Foundry project | `ai3016-project` |
| Azure AI Search | Value of `AZURE_SEARCH_SERVICE_NAME` from `azd env get-values` |
| Search index | `rag-bank-documents` |
| Indexed documents | 3 |
| Chat deployment | `gpt-4o` |

The index contains:

- `RAG-sources/bank_policies.txt`
- `RAG-sources/investment_products.txt`
- `RAG-sources/customer_service.txt`

Its important fields are:

| Field | Purpose |
|---|---|
| `id` | Document key |
| `title` | Display title |
| `content` | Searchable banking content |
| `category` | Filterable category |
| `keywords` | Searchable keywords |
| `content_vector` | 1,536-dimension embedding vector |

---

## Pre-Demo Check

### 1. Activate the Environment

```powershell
.\activate_env.ps1
```

### 2. Confirm Azure Sign-In

```powershell
az account show --output table
```

If the session expired, run `az login`.

### 3. Confirm the Search Index

Run this only if the index is missing or needs to be rebuilt:

```powershell
python .\setup_search_index.py
```

Expected result: `rag-bank-documents` is ready and contains all three documents. The script can use local `RAG-sources` when Blob Storage data-plane access is blocked by policy.

### 4. Confirm the Critical RBAC Assignment

The Foundry project has its own system-assigned managed identity. It is different from the parent Foundry account identity.

On the deployed Azure AI Search service, the managed identity for `ai3016-project` must have:

- **Search Index Data Reader**

Find the project identity's object ID on the project's **Identity** page in the portal. Object IDs are unique to each deployment and should not be copied from another environment.

Do not rely on a role assigned only to the parent Foundry account. The Agent Service connection uses the **project managed identity**.

If the Knowledge object uses an LLM for query planning or synthesis, the Search service managed identity should also have **Cognitive Services User** on the parent Foundry account.

---

## 20-Minute Timeline

| Time | Activity | Teaching point |
|---|---|---|
| 0-3 min | Show the Search index | RAG starts with retrievable enterprise content |
| 3-8 min | Create or inspect Knowledge | Foundry IQ turns Search into reusable agent knowledge |
| 8-13 min | Attach Knowledge to an agent | The agent accesses Knowledge through an MCP tool |
| 13-18 min | Test banking questions | Answers should be grounded and cited |
| 18-20 min | Explain architecture and RBAC | Identity and data-plane permissions matter |

---

## Phase 1: Inspect the Existing Search Index

1. Open the Azure portal.
2. Open the Azure AI Search service named by `AZURE_SEARCH_SERVICE_NAME`.
3. Select **Search management** > **Indexes**.
4. Open `rag-bank-documents`.
5. Use **Search explorer** to run:

```json
{
  "search": "overdraft protection fees",
  "select": "title,content,category",
  "top": 3
}
```

Expected result: the account policies document includes the `$5` transfer fee and `$50` minimum savings balance.

Teaching point: the Search index is the retrieval layer. It is not yet the conversational agent.

---

## Phase 2: Create or Inspect Foundry IQ Knowledge

The labels can change slightly while Foundry IQ is in preview, but the resource relationship remains the same.

1. Open [Microsoft Foundry](https://ai.azure.com/).
2. Select project `ai3016-project`.
3. Under **Build**, select **Knowledge**.
4. If the banking Knowledge object already exists, open it and review its configuration.
5. Otherwise, select **Create knowledge** or **New knowledge base**.
6. Choose **Azure AI Search** as the source.
7. Select the Search service named by `AZURE_SEARCH_SERVICE_NAME`.
8. Select index `rag-bank-documents`.
9. Map the fields:

| Knowledge role | Search field |
|---|---|
| Content | `content` |
| Title | `title` |
| Vector | `content_vector` |

10. Select the available `gpt-4o` deployment when prompted for a knowledge-base model.
11. Create the Knowledge object and wait until it is ready.

Teaching points:

- Foundry IQ Knowledge is reusable across agents.
- It plans retrieval, queries Search, synthesizes results, and returns source references.
- Agent integration uses the Knowledge object's MCP endpoint.

---

## Phase 3: Attach Knowledge to an Agent

1. Under **Build**, select **Agents**.
2. Create a prompt agent or open the prepared class agent.
3. Select the `gpt-4o` deployment.
4. Enter these instructions:

```text
You are a helpful First National Bank assistant.
Use the attached knowledge base for every banking policy, product, or service question.
Do not invent rates, limits, fees, hours, or procedures.
If the knowledge base does not contain the answer, say that you do not know.
Include citations to the retrieved sources.
```

5. In **Knowledge**, select **Add**.
6. Select the banking Knowledge object backed by `rag-bank-documents`.
7. Save or publish the agent version if requested.
8. Confirm the Knowledge object appears in the agent's Knowledge list.

Behind the scenes, the agent calls the Azure AI Search knowledge-base MCP endpoint using a project connection authenticated as `ProjectManagedIdentity`.

---

## Phase 4: Test in the Agent Playground

Start a new conversation after changing Knowledge, tools, or RBAC.

### Test 1: Overdraft Protection

```text
What are the overdraft fees and how does protection work?
```

Expected facts: automatic transfer from savings, `$5` per occurrence, and a `$50` minimum savings balance.

### Test 2: Certificates of Deposit

```text
What CD rates do you offer and what is the minimum deposit?
```

Expected facts: `3.5%` to `4.2%` APY, `$1,000` minimum, and terms from 3 through 36 months.

### Test 3: Multi-Turn Retrieval

```text
What is the mobile deposit limit for a personal account?
```

Then ask:

```text
What if I am a business customer?
```

Expected facts: `$5,000` per day for personal accounts and `$10,000` per day for business accounts.

### Test 4: Missing Knowledge

```text
What is First National Bank's current mortgage rate?
```

Expected behavior: the agent says it does not know because the documents do not provide mortgage rates.

For each grounded answer, open the citation or tool-call details and identify the source document.

---

## Architecture Explanation

```text
User question
    |
    v
Foundry Agent
    |
    | knowledge_base_retrieve via MCP
    v
Foundry IQ Knowledge
    |
    | keyword/vector/hybrid retrieval
    v
Azure AI Search: rag-bank-documents
    |
    v
Grounded response with source references
```

- **Search index:** stores searchable text, metadata, and vectors.
- **Foundry IQ Knowledge:** orchestrates retrieval over one or more knowledge sources.
- **Agent:** decides when to use Knowledge and presents the final response.

---

## Troubleshooting

### `403 Access denied` while enumerating MCP tools

This was encountered and fixed in the deployed class environment.

Cause: Search roles were assigned to the parent Foundry account identity, but the MCP project connection used the separate Foundry **project managed identity**.

Fix:

1. Open the Azure AI Search service named by `AZURE_SEARCH_SERVICE_NAME`.
2. Select **Access control (IAM)**.
3. Add **Search Index Data Reader**.
4. Assign it to the managed identity for `ai3016-project`.
5. Allow several minutes for RBAC propagation.
6. Start a new Agent Playground conversation and retry.

`Search Service Contributor` alone is insufficient. It manages Search objects but cannot query documents or retrieve from a knowledge base.

### Knowledge retrieval reaches Search but model planning fails

If the Knowledge object uses an LLM, assign **Cognitive Services User** on the parent Foundry account to the Search service's system-assigned managed identity.

### Agent answers from general knowledge

- Confirm Knowledge is attached to the current agent version.
- Explicitly require Knowledge use in the agent instructions.
- Start a new conversation after changing the agent.
- Confirm `knowledge_base_retrieve` appears in the tool-call details.

### No relevant results

- Query `rag-bank-documents` directly in Search explorer.
- Confirm all three documents are present.
- Check the `content`, `title`, and `content_vector` mappings.
- Re-run `python .\setup_search_index.py` only if the index is missing or stale.

### Network-related errors

For the validated deployment, public network access is enabled on both Foundry and Search, and Search has no IP firewall rules. A generic `403` is therefore more likely to be RBAC than networking.

If policy later disables public access, use an end-to-end private network design with private endpoints, private DNS, and a supported route from hosted Foundry Agent Service to Search. Changing only one service to private access breaks the MCP call.

---

## Production Discussion

- Use least privilege: retrieval-only agents need **Search Index Data Reader**.
- Use separate project identities and assignments to isolate environments.
- Evaluate retrieval quality with representative questions.
- Plan document refresh separately from agent deployment.
- Use private endpoints and DNS as an end-to-end design.
- Treat Foundry IQ capabilities marked preview as preview services without an SLA.

---

## Student Takeaways

- RAG separates retrieval from response generation.
- Azure AI Search provides the searchable index.
- Foundry IQ Knowledge provides reusable retrieval orchestration.
- A Foundry agent consumes Knowledge through an MCP tool.
- Managed identity and data-plane RBAC are part of the architecture.
- Grounded answers should contain verifiable facts and citations.

---

## Current References

- [Connect agents to Foundry IQ knowledge bases](https://learn.microsoft.com/azure/foundry/agents/how-to/foundry-iq-connect)
- [Foundry IQ overview](https://learn.microsoft.com/azure/foundry/agents/concepts/what-is-foundry-iq)
- [Azure AI Search role-based access control](https://learn.microsoft.com/azure/search/search-security-rbac)
- [Azure AI Search agentic retrieval](https://learn.microsoft.com/azure/search/search-agentic-retrieval-concept)

---

**Validated class path:** existing Search index -> Foundry IQ Knowledge -> Agent Knowledge attachment -> Agent Playground grounded response.