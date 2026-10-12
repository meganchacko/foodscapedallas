#!/usr/bin/env bash
# Creates FoodScape Dallas's Azure infrastructure. Run once, from the repo root, after
# `az login`:
#
#   CENSUS_API_KEY=... deploy/azure/setup.sh
#
# The apps themselves (API, migrate job, pipeline job) are created by deploy/azure/deploy.sh,
# which the GitHub Actions deploy job runs on every push to main, once the images are built.
#
# Each step says what it creates and whether it costs money. Steps skip resources that already
# exist, so the script can be re-run after fixing a failure. deploy/azure/teardown.sh deletes
# everything.
#
# What gets created:
#   Resource group        a folder for everything below (free)
#   Key Vault             stores the database password and Census API key (fractions of a cent)
#   Managed identity      lets the apps read Key Vault without a password (free)
#   PostgreSQL            Flexible Server B1ms + PostGIS (free for 12 months on new accounts,
#                         then roughly $13/month plus storage)
#   Container Apps env    where the API and jobs will run, with logging (free allowance)
#   Static Web App        hosts the frontend (free tier)
#   GitHub deploy login   lets GitHub Actions deploy with short-lived tokens (OIDC), no stored
#                         password (free)

set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

: "${CENSUS_API_KEY:?Set CENSUS_API_KEY (the same key as in your .env)}"

step() { printf '\n==> %s\n' "$1"; }

step "Azure CLI extension and resource providers (free)"
az extension add --name containerapp --upgrade --only-show-errors
for provider in Microsoft.App Microsoft.OperationalInsights Microsoft.DBforPostgreSQL \
    Microsoft.KeyVault Microsoft.Web Microsoft.ManagedIdentity; do
  az provider register --namespace "$provider" --wait
done

step "Resource group $RESOURCE_GROUP in $LOCATION (free)"
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none

step "Key Vault $KEY_VAULT, for secrets (fractions of a cent per month)"
if ! az keyvault show --name "$KEY_VAULT" --output none 2>/dev/null; then
  az keyvault create --name "$KEY_VAULT" --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" --enable-rbac-authorization true --output none
fi
KEY_VAULT_ID="$(az keyvault show --name "$KEY_VAULT" --query id -o tsv)"
# You (the signed-in user) need permission to write secrets
az role assignment create --assignee "$(az ad signed-in-user show --query id -o tsv)" \
  --role "Key Vault Secrets Officer" --scope "$KEY_VAULT_ID" --output none
# Role assignments can take a minute to apply
sleep 30

if ! az keyvault secret show --vault-name "$KEY_VAULT" --name postgres-password \
    --output none 2>/dev/null; then
  # A long random password; letters and digits only, so it's safe everywhere
  az keyvault secret set --vault-name "$KEY_VAULT" --name postgres-password \
    --value "$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | cut -c1-32)" --output none
fi
az keyvault secret set --vault-name "$KEY_VAULT" --name census-api-key \
  --value "$CENSUS_API_KEY" --output none
POSTGRES_PASSWORD="$(az keyvault secret show --vault-name "$KEY_VAULT" \
  --name postgres-password --query value -o tsv)"

step "Managed identity $IDENTITY: lets the apps read Key Vault (free)"
az identity create --name "$IDENTITY" --resource-group "$RESOURCE_GROUP" --output none
IDENTITY_ID="$(az identity show --name "$IDENTITY" --resource-group "$RESOURCE_GROUP" \
  --query id -o tsv)"
IDENTITY_PRINCIPAL="$(az identity show --name "$IDENTITY" --resource-group "$RESOURCE_GROUP" \
  --query principalId -o tsv)"
az role assignment create --assignee-object-id "$IDENTITY_PRINCIPAL" \
  --assignee-principal-type ServicePrincipal --role "Key Vault Secrets User" \
  --scope "$KEY_VAULT_ID" --output none

step "PostgreSQL $DB_SERVER with PostGIS (free 12 months on new accounts, then ~\$13/month)"
if ! az postgres flexible-server show --name "$DB_SERVER" --resource-group "$RESOURCE_GROUP" \
    --output none 2>/dev/null; then
  # --public-access 0.0.0.0 allows connections only from Azure services (not the internet).
  # Every connection must also be encrypted and use the password.
  az postgres flexible-server create --name "$DB_SERVER" --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" --tier Burstable --sku-name Standard_B1ms --storage-size 32 \
    --version 16 --admin-user "$DB_ADMIN" --admin-password "$POSTGRES_PASSWORD" \
    --public-access 0.0.0.0 --yes --output none
fi
# Azure only lets databases use extensions on its allowlist
az postgres flexible-server parameter set --server-name "$DB_SERVER" \
  --resource-group "$RESOURCE_GROUP" --name azure.extensions --value POSTGIS --output none
az postgres flexible-server db create --server-name "$DB_SERVER" \
  --resource-group "$RESOURCE_GROUP" --database-name "$DB_NAME" --output none

step "Container Apps environment $ENVIRONMENT (free monthly allowance)"
if ! az containerapp env show --name "$ENVIRONMENT" --resource-group "$RESOURCE_GROUP" \
    --output none 2>/dev/null; then
  az containerapp env create --name "$ENVIRONMENT" --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" --output none
fi

step "Static Web App $STATIC_WEB_APP for the frontend (free tier)"
if ! az staticwebapp show --name "$STATIC_WEB_APP" --resource-group "$RESOURCE_GROUP" \
    --output none 2>/dev/null; then
  az staticwebapp create --name "$STATIC_WEB_APP" --resource-group "$RESOURCE_GROUP" \
    --location "$STATIC_WEB_LOCATION" --sku Free --output none
fi

step "GitHub Actions deploy login (OIDC, free)"
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
CLIENT_ID="$(az ad app list --display-name "$GITHUB_APP" --query '[0].appId' -o tsv)"
if [ -z "$CLIENT_ID" ]; then
  CLIENT_ID="$(az ad app create --display-name "$GITHUB_APP" --query appId -o tsv)"
  az ad sp create --id "$CLIENT_ID" --output none
  # Trust GitHub's token for pushes to main of this repo, and nothing else
  az ad app federated-credential create --id "$CLIENT_ID" --parameters "{
    \"name\": \"github-main\",
    \"issuer\": \"https://token.actions.githubusercontent.com\",
    \"subject\": \"repo:${GITHUB_REPO}:ref:refs/heads/main\",
    \"audiences\": [\"api://AzureADTokenExchange\"]
  }" --output none
fi
# Allowed to update apps in this resource group only
az role assignment create --assignee "$CLIENT_ID" --role Contributor \
  --scope "/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}" --output none

cat <<SUMMARY

Done. Add these to GitHub (repo Settings > Secrets and variables > Actions > New secret):

  AZURE_CLIENT_ID                   $CLIENT_ID
  AZURE_TENANT_ID                   $TENANT_ID
  AZURE_SUBSCRIPTION_ID             $SUBSCRIPTION_ID
  AZURE_STATIC_WEB_APPS_API_TOKEN   the output of:
      az staticwebapp secrets list --name $STATIC_WEB_APP --query properties.apiKey -o tsv
  CARTO_API_KEY                     your CARTO key (from .env)

Then push to main. The deploy job builds the images, creates or updates the apps
(deploy/azure/deploy.sh), runs migrations, and publishes the frontend.
SUMMARY
unset POSTGRES_PASSWORD
