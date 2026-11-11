@description('Name of the Foundry Project')
param name string

@description('Parent Foundry account name')
param foundryAccountName string

@description('Location for the project')
param location string = resourceGroup().location

@description('Tags for the project')
param tags object = {}

resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource foundryProject 'Microsoft.CognitiveServices/accounts/projects@2025-07-01-preview' = {
  parent: foundryAccount
  name: name
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: 'AI-3016 Demo Project'
    description: 'Foundry project for AI-3016 course demos'
  }
}

output id string = foundryProject.id
output name string = foundryProject.name
output endpoint string = 'https://${foundryAccountName}.services.ai.azure.com/api/projects/${foundryProject.name}'
output principalId string = foundryProject.identity.principalId
