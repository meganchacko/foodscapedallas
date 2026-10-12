# Deploying to Azure

| Piece | Azure service | Cost (rough) |
| --- | --- | --- |
| API (FastAPI) + Redis sidecar | Container Apps, scales to zero | Free monthly allowance |
| Database | PostgreSQL Flexible Server B1ms + PostGIS | Free 12 months (new accounts), then ~$13/month + storage |
| Migrations | Container Apps job, run on every deploy | Pennies |
| Weekly data pipeline | Container Apps job, Mondays 08:00 UTC | Pennies |
| Frontend | Static Web Apps (free tier) | Free |
| Secrets | Key Vault, read by a managed identity | Fractions of a cent |
| Images | GitHub Container Registry (ghcr.io) | Free for public images |

Check current prices before creating anything: https://azure.microsoft.com/pricing. Set a budget alert in the Azure portal (Cost Management > Budgets).

## First time

1. Install the Azure CLI (`brew install azure-cli`) and sign in: `az login`.
2. Create the infrastructure:
   ```bash
   CENSUS_API_KEY=... deploy/azure/setup.sh
   ```
   It prints the values to add as GitHub secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_STATIC_WEB_APPS_API_TOKEN`, plus `CARTO_API_KEY`.
3. In GitHub, add those secrets, and a repository **variable** `AZURE_DEPLOY_ENABLED` = `true`.
4. Push to `main`. After CI passes, the deploy job builds and pushes the images, runs `deploy/azure/deploy.sh` (migrations, then the API and the weekly pipeline job), and publishes the frontend.
5. Load the data once (after that it runs weekly):
   ```bash
   az containerapp job start --name foodscape-pipeline --resource-group foodscape-rg
   ```

## Every deploy after that

Push to `main`. Migrations run first; if they fail, the old version keeps running.

## How it's put together

- **Secrets** (database password, Census key) live in Key Vault. The apps read them through a managed identity, so no password is stored in code, images, or GitHub.
- **GitHub signs in to Azure with OIDC:** each workflow run gets a short-lived token for pushes to `main` of this repo only, so there's no long-lived Azure password stored in GitHub. It can only change resources in `foodscape-rg`.
- **The database** accepts connections only from Azure services, and only encrypted (`sslmode=require`).
- **Redis** runs as a sidecar container inside the API app, since it only holds disposable data (caches and rate-limit counts). The API is capped at one replica so rate limits stay exact. The weekly pipeline can't reach the sidecar to clear the map cache, so new data appears within 24 hours (the cache's expiry).
- **Scale to zero:** when nobody uses the site, the API stops and costs nothing; the first request afterwards takes a few seconds while it starts.

## Removing everything

```bash
deploy/azure/teardown.sh
```

Deletes the resource group (every resource and the database), purges the Key Vault, and removes the GitHub deploy login.
