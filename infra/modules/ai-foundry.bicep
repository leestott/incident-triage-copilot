// ---------------------------------------------------------------------------
// ai-foundry.bicep — Microsoft Foundry Hub, Project, and Model Deployment
// ---------------------------------------------------------------------------

@description('Name of the AI Hub')
param hubName string

@description('Name of the AI Project')
param projectName string

@description('Location for resources')
param location string

@description('Tags to apply')
param tags object = {}

@description('Model deployment name')
param modelDeploymentName string

@description('Model SKU')
param modelSku string

@description('Model capacity (TPM in thousands)')
param modelCapacity int

@description('Principal ID of the managed identity for RBAC')
param identityPrincipalId string

// AI Hub
resource aiHub 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: hubName
  location: location
  tags: tags
  kind: 'Hub'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Incident Triage Copilot Hub'
    description: 'Microsoft Foundry hub for the incident triage multi-agent copilot'
  }
}

// AI Project (child of Hub)
resource aiProject 'Microsoft.MachineLearningServices/workspaces@2024-10-01' = {
  name: projectName
  location: location
  tags: tags
  kind: 'Project'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    friendlyName: 'Incident Triage Copilot'
    description: 'Microsoft Foundry project for the multi-agent incident triage copilot'
    hubResourceId: aiHub.id
  }
}

// Role assignment: Cognitive Services OpenAI User → Managed Identity
resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(aiProject.id, identityPrincipalId, 'CognitiveServicesOpenAIUser')
  scope: aiProject
  properties: {
    principalId: identityPrincipalId
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd' // Cognitive Services OpenAI User
    )
    principalType: 'ServicePrincipal'
  }
}

output projectEndpoint string = aiProject.properties.discoveryUrl
output projectName string = aiProject.name
output hubName string = aiHub.name
