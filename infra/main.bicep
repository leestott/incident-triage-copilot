// ---------------------------------------------------------------------------
// main.bicep — Entry point for azd infrastructure provisioning
// ---------------------------------------------------------------------------
// Provisions: Microsoft Foundry project, model deployment, ACR, Container App,
//             Managed Identity, and optional Application Insights.
// ---------------------------------------------------------------------------
targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment (e.g., dev, staging, prod)')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Name of the Microsoft Foundry hub (auto-generated if empty)')
param aiHubName string = ''

@description('Name of the Microsoft Foundry project (auto-generated if empty)')
param aiProjectName string = ''

@description('Name of the model deployment')
param modelDeploymentName string = 'gpt-4o'

@description('Model SKU for deployment')
param modelSku string = 'GlobalStandard'

@description('Model capacity (tokens per minute in thousands)')
param modelCapacity int = 30

@description('Enable Application Insights for monitoring')
param enableAppInsights bool = true

@description('Bing Grounding connection resource ID (leave empty to skip)')
param bingConnectionId string = ''

// Tags applied to every resource
var tags = {
  'azd-env-name': environmentName
  'project': 'incident-triage-copilot'
}

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// Resource group
resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

// Managed Identity for the agent
module identity './modules/identity.bicep' = {
  name: 'identity'
  scope: rg
  params: {
    name: '${abbrs.managedIdentity}${resourceToken}'
    location: location
    tags: tags
  }
}

// Microsoft Foundry Hub + Project
module aiFoundry './modules/ai-foundry.bicep' = {
  name: 'ai-foundry'
  scope: rg
  params: {
    hubName: !empty(aiHubName) ? aiHubName : '${abbrs.aiHub}${resourceToken}'
    projectName: !empty(aiProjectName) ? aiProjectName : '${abbrs.aiProject}${resourceToken}'
    location: location
    tags: tags
    modelDeploymentName: modelDeploymentName
    modelSku: modelSku
    modelCapacity: modelCapacity
    identityPrincipalId: identity.outputs.principalId
  }
}

// Container Registry (for hosted agent image)
module acr './modules/acr.bicep' = {
  name: 'acr'
  scope: rg
  params: {
    name: '${abbrs.acr}${resourceToken}'
    location: location
    tags: tags
    identityPrincipalId: identity.outputs.principalId
  }
}

// Container App Environment + App (agent runtime)
module containerApp './modules/container-app.bicep' = {
  name: 'container-app'
  scope: rg
  params: {
    name: '${abbrs.containerApp}${resourceToken}'
    location: location
    tags: tags
    identityId: identity.outputs.id
    identityClientId: identity.outputs.clientId
    acrLoginServer: acr.outputs.loginServer
    aiProjectEndpoint: aiFoundry.outputs.projectEndpoint
    appInsightsConnectionString: enableAppInsights ? monitoring.outputs.connectionString : ''
    bingConnectionId: bingConnectionId
  }
}

// Application Insights (optional but recommended)
module monitoring './modules/monitoring.bicep' = if (enableAppInsights) {
  name: 'monitoring'
  scope: rg
  params: {
    name: '${abbrs.appInsights}${resourceToken}'
    location: location
    tags: tags
  }
}

// ---------------------------------------------------------------------------
// Outputs — consumed by azd and agent runtime
// ---------------------------------------------------------------------------
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_AI_PROJECT_ENDPOINT string = aiFoundry.outputs.projectEndpoint
output AZURE_AI_PROJECT_NAME string = aiFoundry.outputs.projectName
output AZURE_CLIENT_ID string = identity.outputs.clientId
output ACR_NAME string = acr.outputs.name
output ACR_LOGIN_SERVER string = acr.outputs.loginServer
output AZURE_CONTAINER_APP_FQDN string = containerApp.outputs.fqdn
output APPLICATIONINSIGHTS_CONNECTION_STRING string = enableAppInsights ? monitoring.outputs.connectionString : ''
