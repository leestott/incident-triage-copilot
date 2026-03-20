// ---------------------------------------------------------------------------
// container-app.bicep — Container App Environment + Container App
// ---------------------------------------------------------------------------
// Hosts the agent as a containerized Foundry Hosted Agent.
// ---------------------------------------------------------------------------

@description('Base name for resources')
param name string

@description('Location for resources')
param location string

@description('Tags to apply')
param tags object = {}

@description('Resource ID of the user-assigned managed identity')
param identityId string

@description('Client ID of the managed identity')
param identityClientId string

@description('ACR login server')
param acrLoginServer string

@description('Microsoft Foundry project endpoint')
param aiProjectEndpoint string

@description('Application Insights connection string (empty to skip)')
param appInsightsConnectionString string = ''

@description('Bing Grounding connection resource ID (empty to skip)')
param bingConnectionId string = ''

// Container App Environment
resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${name}-env'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
    }
  }
}

// Container App
resource containerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: union(tags, { 'azd-service-name': 'agent' })
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acrLoginServer
          identity: identityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'agent'
          image: '${acrLoginServer}/incident-triage-copilot:latest'
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            { name: 'AZURE_AI_PROJECT_ENDPOINT', value: aiProjectEndpoint }
            { name: 'AZURE_CLIENT_ID', value: identityClientId }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'BING_CONNECTION_ID', value: bingConnectionId }
            { name: 'LOG_LEVEL', value: 'INFO' }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 3
      }
    }
  }
}

output fqdn string = containerApp.properties.configuration.ingress.fqdn
output name string = containerApp.name
