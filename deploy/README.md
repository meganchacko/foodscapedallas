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

1. Install the Azure and GitHub CLIs (`brew install azure-cli gh`) and sign in: `az login`, `gh auth login`.
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

**Upgrading a deployment made before the API had its own database role:** re-run `deploy/azure/setup.sh` once before pushing. It skips everything that exists and only adds the new `postgres-api-password` secret to Key Vault. The next deploy's migrate job creates the role.

## How it's put together

- **Secrets** (database password, Census key) live in Key Vault. The apps read them through a managed identity, so no password is stored in code, images, or GitHub.
- **GitHub signs in to Azure with OIDC:** each workflow run gets a short-lived token for pushes to `main` of this repo only, so there's no long-lived Azure password stored in GitHub. It can only change resources in `foodscape-rg`.
- **The database** accepts only encrypted connections (`sslmode=require`) with a password. Two roles log in: the admin (migrations and the weekly pipeline, which change data) and `foodscape_api`, which the API uses and which can only read map data and add saved health checks (`backend/app/db/api_role.py`). If the API were compromised, the attacker couldn't drop or change tables.
- **Redis** runs as a sidecar container inside the API app, since it only holds disposable data (caches and rate-limit counts). The API is capped at one replica so rate limits stay exact. The weekly pipeline can't reach the sidecar to clear the map cache, so new data appears within 24 hours (the cache's expiry).
- **Scale to zero:** when nobody uses the site, the API stops and costs nothing; the first request afterwards takes a few seconds while it starts.

## Network access to the database: a deliberate trade-off

The database's firewall rule is "allow Azure services" (`--public-access 0.0.0.0`). That keeps out the open internet, but it lets in **any** Azure customer's services, not only ours. What actually protects the data:

- a 32-character random password (Key Vault), and encrypted connections only;
- the API's role can only read map data and add saved health checks, so even a compromised API can't damage the database;
- the data is mostly public (Census, USDA, CDC, OpenStreetMap). The sensitive part, opted-in health check answers, has no names, emails, or IPs.

**The stronger option** is a private network: put the Container Apps environment and the database in an Azure virtual network, so the database has no public address at all. It wasn't chosen because both resources would have to be recreated (Azure can't move them into a network afterwards), and it adds a private DNS zone (under $1/month; check current pricing). For a site at this scale, the password, encryption, and least-privilege role are a reasonable defense. A site holding identifiable health data should use the private network.

## Custom domain

The site is at https://foodscape.site (registered at Namecheap), as well as its Azure address. Namecheap's DNS has a TXT record proving ownership, an ALIAS record pointing `foodscape.site` at the Static Web App, and a CNAME for `www`. Azure provides the HTTPS certificate for free. `deploy.sh` adds every custom domain linked to the Static Web App to the API's allowed origins, so linking a new one only needs a redeploy.

## Removing everything

```bash
deploy/azure/teardown.sh
```

Deletes the resource group (every resource and the database), purges the Key Vault, and removes the GitHub deploy login.
