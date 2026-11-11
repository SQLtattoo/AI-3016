targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment for resource naming')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
@allowed([
  'swedencentral'
  'eastus'
  'westus'
  'westeurope'
])
param location string = 'swedencentral'

@description('Resource group for this azd environment')
param resourceGroupName string = 'rg-${environmentName}'

@allowed(['Enabled', 'Disabled'])
param storagePublicNetworkAccess string = 'Enabled'

@allowed(['Enabled', 'Disabled'])
param keyVaultPublicNetworkAccess string = 'Enabled'

param includePrivateSetup bool = false

@description('Principal ID for RBAC assignments')
param principalId string = ''

@allowed(['User', 'Group', 'ServicePrincipal'])
param principalType string = 'User'

@description('Name of the chat model deployment')
param modelDeploymentName string = 'gpt-4o'

@description('Name of the chat model')
param modelName string = 'gpt-4o'

@description('Version of the chat model')
param modelVersion string = '2024-11-20'

@allowed(['Standard', 'GlobalStandard', 'DataZoneStandard'])
param modelDeploymentSku string = 'GlobalStandard'

@minValue(1)
param modelDeploymentCapacity int = 10

@description('Name of the embeddings model deployment')
param embeddingsDeploymentName string = 'text-embedding-ada-002'

@description('Name of the embeddings model')
param embeddingsModelName string = 'text-embedding-ada-002'

@description('Version of the embeddings model')
param embeddingsModelVersion string = '2'

@allowed(['Standard', 'GlobalStandard', 'DataZoneStandard'])
param embeddingsDeploymentSku string = 'GlobalStandard'

@minValue(1)
param embeddingsDeploymentCapacity int = 10

// Generate unique resource names
var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName, 'demo': 'ai3016' }

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

// Storage Account
module storage './modules/storage.bicep' = {
  name: 'storage-deployment'
  scope: resourceGroup
  params: {
    name: '${abbrs.storageStorageAccounts}${resourceToken}'
    location: location
    tags: tags
    containerName: 'rag-sources'
    publicNetworkAccess: storagePublicNetworkAccess
  }
}

// Foundry Resource (AIServices) with model deployments
module foundry './modules/openai.bicep' = {
  name: 'foundry-deployment'
  scope: resourceGroup
  params: {
    name: 'foundry-${resourceToken}'
    location: location
    tags: tags
    kind: 'AIServices'
    allowProjectManagement: true
    deployments: [
      {
        name: modelDeploymentName
        sku: { name: modelDeploymentSku, capacity: modelDeploymentCapacity }
        model: { format: 'OpenAI', name: modelName, version: modelVersion }
      }
      {
        name: embeddingsDeploymentName
        sku: { name: embeddingsDeploymentSku, capacity: embeddingsDeploymentCapacity }
        model: { format: 'OpenAI', name: embeddingsModelName, version: embeddingsModelVersion }
      }
    ]
  }
}

// Foundry Project (on top of the Foundry resource)
module foundryProject './modules/foundry-project.bicep' = {
  name: 'foundry-project-deployment'
  scope: resourceGroup
  params: {
    name: 'ai3016-project'
    foundryAccountName: foundry.outputs.name
    location: location
    tags: tags
  }
}

// AI Search
module search './modules/search.bicep' = {
  name: 'search-deployment'
  scope: resourceGroup
  params: {
    name: '${abbrs.searchSearchServices}${resourceToken}'
    location: location
    tags: tags
    sku: 'basic'
  }
}

// Key Vault for storing secrets
module keyVault './modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  scope: resourceGroup
  params: {
    name: '${abbrs.keyVaultVaults}${resourceToken}'
    location: location
    tags: tags
    sku: 'standard'
    publicNetworkAccess: keyVaultPublicNetworkAccess
  }
}

// RBAC Assignments
// User/SP roles are conditional on principalId being provided.
// Service-to-service roles (Search MI → Storage, Foundry MI → Search) are always assigned.
module rbac './modules/rbac.bicep' = {
  name: 'rbac-deployment'
  scope: resourceGroup
  params: {
    principalId: principalId
    principalType: principalType
    storageAccountName: storage.outputs.name
    searchServiceName: search.outputs.name
    keyVaultName: keyVault.outputs.name
    foundryServiceName: foundry.outputs.name
    openAiEmbeddingsServiceName: foundry.outputs.name
    // Service-to-service: AI Search managed identity reads blobs from storage
    searchPrincipalId: search.outputs.principalId
    // Service-to-service: Foundry managed identity accesses the search index
    foundryPrincipalId: foundry.outputs.principalId
    projectPrincipalId: foundryProject.outputs.principalId
  }
}

// Outputs for azd environment
module privateSetup './modules/private-setup.bicep' = if (includePrivateSetup) {
  name: 'private-setup-deployment'
  scope: resourceGroup
  params: {
    name: 'demo-private-${resourceToken}'
    location: location
    tags: tags
    storageAccountName: storage.outputs.name
    keyVaultName: keyVault.outputs.name
    searchServiceName: search.outputs.name
    openaiEndpoint: foundry.outputs.endpoint
    modelDeploymentName: modelDeploymentName
  }
}

output AZURE_DEMO_PRIVATE_SETUP_JOB_NAME string = includePrivateSetup ? privateSetup!.outputs.jobName : ''
output AZURE_DEMO_PRIVATE_SETUP_JOB_ID string = includePrivateSetup ? privateSetup!.outputs.jobResourceId : ''
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

// Foundry Project outputs
output AZURE_AI_PROJECT_NAME string = foundryProject.outputs.name
output AZURE_AI_PROJECT_ENDPOINT string = foundryProject.outputs.endpoint

// Foundry outputs (hosts both GPT-4o and embeddings)
output AZURE_FOUNDRY_ENDPOINT string = foundry.outputs.endpoint
output AZURE_FOUNDRY_SERVICE_NAME string = foundry.outputs.name
// GPT-4o deployment on Foundry
output AZURE_OPENAI_ENDPOINT string = foundry.outputs.endpoint
output AZURE_OPENAI_DEPLOYMENT_NAME string = modelDeploymentName
output AZURE_OPENAI_SERVICE_NAME string = foundry.outputs.name

// Embeddings deployment on Foundry (same resource)
output AZURE_OPENAI_EMBEDDINGS_ENDPOINT string = foundry.outputs.endpoint
output AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME string = embeddingsDeploymentName
output AZURE_OPENAI_EMBEDDINGS_SERVICE_NAME string = foundry.outputs.name

output AZURE_SEARCH_ENDPOINT string = search.outputs.endpoint
output AZURE_SEARCH_SERVICE_NAME string = search.outputs.name

output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.name
output AZURE_STORAGE_CONTAINER_NAME string = storage.outputs.containerName
output AZURE_STORAGE_ENDPOINT string = storage.outputs.endpoint

output AZURE_KEY_VAULT_NAME string = keyVault.outputs.name
output AZURE_KEY_VAULT_URI string = keyVault.outputs.uri
