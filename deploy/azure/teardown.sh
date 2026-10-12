#!/usr/bin/env bash
# Deletes everything setup.sh and deploy.sh created, to stop all charges. This can't be undone:
# the production database and its data are deleted too (the pipeline can reload the data).
#
#   deploy/azure/teardown.sh

set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

read -r -p "Delete resource group $RESOURCE_GROUP and everything in it? Type its name: " answer
[ "$answer" = "$RESOURCE_GROUP" ] || { echo "Cancelled."; exit 1; }

# Everything lives in one resource group, so deleting it deletes everything
az group delete --name "$RESOURCE_GROUP" --yes

# Key Vaults are "soft-deleted" for 90 days; purge it so its name can be reused
az keyvault purge --name "$KEY_VAULT" 2>/dev/null || true

# The GitHub deploy login lives in your directory, not the resource group
CLIENT_ID="$(az ad app list --display-name "$GITHUB_APP" --query '[0].appId' -o tsv)"
[ -z "$CLIENT_ID" ] || az ad app delete --id "$CLIENT_ID"

echo "Deleted. Remove the AZURE_* secrets from GitHub, or the deploy job will fail."
