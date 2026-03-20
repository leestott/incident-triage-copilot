// ---------------------------------------------------------------------------
// identity.bicep — User-Assigned Managed Identity
// ---------------------------------------------------------------------------
// Used by the Container App to authenticate to Microsoft Foundry, ACR, etc.
// No secrets, no keys — managed identity is the secure default.
// ---------------------------------------------------------------------------

@description('Name of the managed identity')
param name string

@description('Location for the resource')
param location string

@description('Tags to apply')
param tags object = {}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
  tags: tags
}

output id string = identity.id
output principalId string = identity.properties.principalId
output clientId string = identity.properties.clientId
output name string = identity.name
