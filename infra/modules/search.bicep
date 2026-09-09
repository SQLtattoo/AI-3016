@description('Name of the Azure AI Search service')
param name string

@description('Location for the Search service')
param location string = resourceGroup().location

@description('Tags for the Search service')
param tags object = {}

@description('SKU for the Search service')
@allowed([
  'free'
  'basic'
  'standard'
])
param sku string = 'basic'

resource searchService 'Microsoft.Search/searchServices@2024-03-01-preview' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    networkRuleSet: {
      ipRules: []
    }
    // Allow both API key and AAD/RBAC authentication.
    // API key auth is needed for the postprovision hook and code demos.
    // AAD auth is needed for the portal RAG wizard using managed identity.
    disableLocalAuth: false
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

output id string = searchService.id
output name string = searchService.name
output endpoint string = 'https://${searchService.name}.search.windows.net'
output principalId string = searchService.identity.principalId
