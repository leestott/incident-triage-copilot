# Security

## Reporting Security Issues

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them to the Microsoft Security Response Center (MSRC) at [https://msrc.microsoft.com/create-report](https://msrc.microsoft.com/create-report).

If you prefer to submit without logging in, send email to [secure@microsoft.com](mailto:secure@microsoft.com). If possible, encrypt your message with our PGP key; please download it from the [Microsoft Security Response Center PGP Key page](https://aka.ms/security.md/msrc/pgp).

You should receive a response within 24 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

## Security Practices in This Sample

This sample follows security best practices:

- **Managed Identity**: No API keys, passwords, or connection strings for Azure services. Authentication flows through User-Assigned Managed Identity with RBAC roles.
- **Non-root container**: The Dockerfile creates and switches to a non-privileged `appuser`.
- **ACR admin disabled**: Container images are pulled via managed identity (AcrPull role), not admin credentials.
- **HTTPS enforced**: Container App ingress disallows insecure HTTP connections.
- **No secrets in code**: All configuration is injected via environment variables, set by `azd` during deployment.
- **Least-privilege RBAC**: The managed identity is granted only `Cognitive Services OpenAI User` and `AcrPull` roles.
- **Input validation**: Pydantic models validate all incoming requests with type checking and field constraints.
- **Dependency pinning**: `requirements.txt` specifies minimum versions for all packages.

## Data Handling

When deployed as a Foundry Hosted Agent:
- User incident queries are sent to Azure OpenAI (GPT-4o) for processing.
- Log snippets included in requests are processed by the model and may be stored in Application Insights.
- Bing Grounding tool sends search queries to Bing's API.
- Code Interpreter runs in a sandboxed Azure environment.

Review your organisation's AI governance policies before deploying with production data.
