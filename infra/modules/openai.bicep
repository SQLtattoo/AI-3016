@description('Name of the Azure OpenAI service')
param name string

@description('Location for the Azure OpenAI service')
param location string = resourceGroup().location

@description('Tags for the service')
param tags object = {}

@description('SKU for the service')
param sku string = 'S0'

@description('Kind of Cognitive Services account')
@allowed([
  'OpenAI'
  'AIServices'
])
param kind string = 'OpenAI'

@description('Model deployments to create')
param deployments array = []

@description('Allow project management (required for Foundry projects)')
param allowProjectManagement bool = false

resource cognitiveService 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  sku: {
    name: sku
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
    allowProjectManagement: allowProjectManagement
    disableLocalAuth: true
  }
}

@batchSize(1)
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = [for deployment in deployments: {
  parent: cognitiveService
  name: deployment.name
  sku: deployment.sku
  properties: {
    model: deployment.model
    raiPolicyName: deployment.?raiPolicyName ?? 'Microsoft.Default'
  }
}]

output id string = cognitiveService.id
output name string = cognitiveService.name
output endpoint string = cognitiveService.properties.endpoint
output principalId string = cognitiveService.identity.principalId
