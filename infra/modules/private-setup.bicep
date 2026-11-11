param name string
param location string = resourceGroup().location
param tags object = {}
param storageAccountName string
param keyVaultName string
param searchServiceName string
param openaiEndpoint string
param modelDeploymentName string
param containerName string = 'rag-sources'

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' existing = {
  name: storageAccountName
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: keyVaultName
}

resource search 'Microsoft.Search/searchServices@2024-03-01-preview' existing = {
  name: searchServiceName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${name}-identity'
  location: location
  tags: tags
}

var blobRole = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var vaultRole = 'b86a8fe4-44ce-4948-aee5-eccb2c155cd7'
var searchRole = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

resource blobAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, identity.id, blobRole)
  scope: storage
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobRole)
  }
}

resource vaultAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vault.id, identity.id, vaultRole)
  scope: vault
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', vaultRole)
  }
}

resource searchAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, identity.id, searchRole)
  scope: search
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchRole)
  }
}

resource network 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: '${name}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.46.0.0/16'] }
    subnets: [
      {
        name: 'jobs'
        properties: {
          addressPrefix: '10.46.0.0/27'
          delegations: [
            {
              name: 'container-apps'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
        }
      }
      {
        name: 'private-endpoints'
        properties: {
          addressPrefix: '10.46.1.0/27'
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

var privateServices = [
  { name: 'blob', zone: 'privatelink.blob.core.windows.net', target: storage.id, group: 'blob' }
  { name: 'vault', zone: 'privatelink.vaultcore.azure.net', target: vault.id, group: 'vault' }
]

resource zones 'Microsoft.Network/privateDnsZones@2024-06-01' = [for service in privateServices: {
  name: service.zone
  location: 'global'
  tags: tags
}]

resource links 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [for (service, index) in privateServices: {
  parent: zones[index]
  name: '${name}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: { id: network.id }
  }
}]

resource endpoints 'Microsoft.Network/privateEndpoints@2024-05-01' = [for service in privateServices: {
  name: '${name}-${service.name}-pe'
  location: location
  tags: tags
  properties: {
    subnet: { id: '${network.id}/subnets/private-endpoints' }
    privateLinkServiceConnections: [
      {
        name: service.name
        properties: {
          privateLinkServiceId: service.target
          groupIds: [service.group]
        }
      }
    ]
  }
}]

resource zoneGroups 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = [for (service, index) in privateServices: {
  parent: endpoints[index]
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      { name: service.name, properties: { privateDnsZoneId: zones[index].id } }
    ]
  }
}]

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: '${name}-env'
  location: location
  tags: tags
  properties: {
    vnetConfiguration: {
      infrastructureSubnetId: '${network.id}/subnets/jobs'
      internal: true
    }
    workloadProfiles: [
      { name: 'Consumption', workloadProfileType: 'Consumption' }
    ]
  }
}

var settings = {
  AZURE_STORAGE_ENDPOINT: storage.properties.primaryEndpoints.blob
  AZURE_STORAGE_CONTAINER_NAME: containerName
  AZURE_KEY_VAULT_URI: vault.properties.vaultUri
  AZURE_SEARCH_RESOURCE_ID: search.id
  AZURE_SEARCH_ENDPOINT: 'https://${searchServiceName}.search.windows.net'
  AZURE_SEARCH_INDEX: 'rag-bank-documents'
  ENDPOINT_URL: openaiEndpoint
  AZURE_OPENAI_ENDPOINT: openaiEndpoint
  DEPLOYMENT_NAME: modelDeploymentName
}
var sources = {
  'bank_policies.txt': loadTextContent('../../RAG-sources/bank_policies.txt')
  'customer_service.txt': loadTextContent('../../RAG-sources/customer_service.txt')
  'investment_products.txt': loadTextContent('../../RAG-sources/investment_products.txt')
}

resource job 'Microsoft.App/jobs@2025-01-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  properties: {
    environmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 900
      replicaRetryLimit: 0
      manualTriggerConfig: { parallelism: 1, replicaCompletionCount: 1 }
    }
    template: {
      containers: [
        {
          name: 'private-setup'
          image: 'mcr.microsoft.com/azure-cli:2.81.0'
          command: ['python3', '-u', '-c']
          args: [
            'import base64;exec(base64.b64decode("${base64(loadTextContent('../hooks/private_setup.py'))}"))'
          ]
          env: [
            { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
            { name: 'DEMO_SETTINGS', value: string(settings) }
            { name: 'DEMO_SOURCES_BASE64', value: base64(string(sources)) }
          ]
          resources: { cpu: json('0.5'), memory: '1Gi' }
        }
      ]
    }
  }
}

output jobName string = job.name
output jobResourceId string = job.id
output identityPrincipalId string = identity.properties.principalId
