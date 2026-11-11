@description('Principal ID to assign roles to (user/SP)')
param principalId string

@allowed(['User', 'Group', 'ServicePrincipal'])
param principalType string = 'User'

@description('Name of the Storage Account')
param storageAccountName string

@description('Name of the Search Service')
param searchServiceName string

@description('Name of the Key Vault')
param keyVaultName string

@description('Name of the Foundry Service (AIServices)')
param foundryServiceName string

@description('Name of the OpenAI Service for embeddings')
param openAiEmbeddingsServiceName string

@description('System-assigned principal ID of the AI Search service (for Storage access)')
param searchPrincipalId string = ''

@description('System-assigned principal ID of the Foundry / AIServices resource (for Search access)')
param foundryPrincipalId string = ''

@description('Foundry project managed identity for project tools and model access')
param projectPrincipalId string = ''

var foundryUserRoleId = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
var cognitiveServicesUserRoleId = 'a97b65f3-24c7-4388-baec-2e87135dc908'

// Cognitive Services OpenAI User
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

// Storage Blob Data Contributor
var storageBlobDataContributorRoleId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

// Search Index Data Contributor
var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'

// Search Service Contributor
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

// Key Vault Secrets Officer
var keyVaultSecretsOfficerRoleId = 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' existing = {
  name: searchServiceName
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource foundryService 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' existing = {
  name: foundryServiceName
}

resource openAiEmbeddingsService 'Microsoft.CognitiveServices/accounts@2024-04-01-preview' existing = {
  name: openAiEmbeddingsServiceName
}

// ── User / Service Principal role assignments (conditional on principalId) ──

// Assign Cognitive Services OpenAI User role on Foundry
resource foundryUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(foundryService.id, principalId, cognitiveServicesOpenAIUserRoleId)
  scope: foundryService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: principalId
    principalType: principalType
  }
}

// Assign Cognitive Services OpenAI User role on embeddings OpenAI
resource openAiEmbeddingsUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId) && openAiEmbeddingsServiceName != foundryServiceName) {
  name: guid(openAiEmbeddingsService.id, principalId, cognitiveServicesOpenAIUserRoleId)
  scope: openAiEmbeddingsService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: principalId
    principalType: principalType
  }
}

// Assign Storage Blob Data Contributor role
resource storageBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(storageAccount.id, principalId, storageBlobDataContributorRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleId)
    principalId: principalId
    principalType: principalType
  }
}

// Assign Search Index Data Contributor role
resource searchIndexRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(searchService.id, principalId, searchIndexDataContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalId: principalId
    principalType: principalType
  }
}

// Assign Search Service Contributor role
resource searchServiceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(searchService.id, principalId, searchServiceContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalId: principalId
    principalType: principalType
  }
}

// Assign Key Vault Secrets Officer role so postprovision can set secrets and local demos can read them.
resource keyVaultSecretsRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(keyVault.id, principalId, keyVaultSecretsOfficerRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsOfficerRoleId)
    principalId: principalId
    principalType: principalType
  }
}

resource foundryDeveloperRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(foundryService.id, principalId, foundryUserRoleId)
  scope: foundryService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
    principalId: principalId
    principalType: principalType
  }
}

resource languageVoiceUserRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(principalId)) {
  name: guid(foundryService.id, principalId, cognitiveServicesUserRoleId)
  scope: foundryService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleId)
    principalId: principalId
    principalType: principalType
  }
}

resource projectRuntimeRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(projectPrincipalId)) {
  name: guid(foundryService.id, projectPrincipalId, foundryUserRoleId)
  scope: foundryService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', foundryUserRoleId)
    principalId: projectPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// ── Managed Identity assignments (service-to-service, no user principal needed) ──

// AI Search system MI → Storage Blob Data Reader
// Needed so the Search indexer can read documents from blob storage via managed identity
var storageBlobDataReaderRoleId = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'

resource searchToStorageRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(searchPrincipalId)) {
  name: guid(storageAccount.id, searchPrincipalId, storageBlobDataReaderRoleId)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataReaderRoleId)
    principalId: searchPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Foundry system MI → Search Index Data Contributor
// Needed so the AI Foundry/OpenAI service can read/write the search index for RAG vectorization
resource foundryToSearchIndexRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(foundryPrincipalId)) {
  name: guid(searchService.id, foundryPrincipalId, searchIndexDataContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalId: foundryPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Foundry system MI → Search Service Contributor
// Needed so the Foundry service can manage the search service (create/update indexers)
resource foundryToSearchServiceRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(foundryPrincipalId)) {
  name: guid(searchService.id, foundryPrincipalId, searchServiceContributorRoleId)
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalId: foundryPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output roleAssignmentsCompleted bool = true
