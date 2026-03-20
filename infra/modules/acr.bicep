// ---------------------------------------------------------------------------
// acr.bicep — Azure Container Registry
// ---------------------------------------------------------------------------
// Stores the agent container image. Managed identity gets AcrPull access.
// ---------------------------------------------------------------------------

@description('Name of the container registry (must be globally unique, alphanumeric)')
param name string

@description('Location for the resource')
param location string

@description('Tags to apply')
param tags object = {}

@description('Principal ID of the managed identity for AcrPull')
param identityPrincipalId string

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: false  // Secure default — use managed identity, not admin keys
  }
}

// AcrPull role for the managed identity
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, identityPrincipalId, 'AcrPull')
  scope: acr
  properties: {
    principalId: identityPrincipalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '7f951dda-4ed3-4680-a7ca-43fe172d538d' // AcrPull
    )
    principalType: 'ServicePrincipal'
  }
}

output name string = acr.name
output loginServer string = acr.properties.loginServer
