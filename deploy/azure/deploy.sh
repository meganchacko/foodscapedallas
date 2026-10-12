#!/usr/bin/env bash
# Deploys one version of FoodScape Dallas to the infrastructure setup.sh created. The GitHub
# Actions deploy job runs this after pushing the images; it also works by hand after `az login`:
#
#   deploy/azure/deploy.sh <image-tag>        e.g. the commit SHA the images were tagged with
#
# Order matters: migrations run first, so the new code never starts against an old schema.
# Prints the API's URL as the last line (and to $GITHUB_OUTPUT when run in GitHub Actions).

set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

TAG="${1:?Usage: deploy.sh <image-tag>}"
BACKEND_IMAGE_REF="${BACKEND_IMAGE}:${TAG}"
PIPELINE_IMAGE_REF="${PIPELINE_IMAGE}:${TAG}"

step() { printf '\n==> %s\n' "$1"; }

# Look up what setup.sh created
IDENTITY_ID="$(az identity show --name "$IDENTITY" --resource-group "$RESOURCE_GROUP" \
  --query id -o tsv)"
ENVIRONMENT_ID="$(az containerapp env show --name "$ENVIRONMENT" \
  --resource-group "$RESOURCE_GROUP" --query id -o tsv)"
DB_HOST="$(az postgres flexible-server show --name "$DB_SERVER" \
  --resource-group "$RESOURCE_GROUP" --query fullyQualifiedDomainName -o tsv)"
FRONTEND_URL="https://$(az staticwebapp show --name "$STATIC_WEB_APP" \
  --resource-group "$RESOURCE_GROUP" --query defaultHostname -o tsv)"
KEY_VAULT_URI="https://${KEY_VAULT}.vault.azure.net/secrets"

# Settings the migrate and pipeline jobs share with the API
JOB_ENV=(
  "POSTGRES_HOST=$DB_HOST" "POSTGRES_DB=$DB_NAME" "POSTGRES_USER=$DB_ADMIN"
  "POSTGRES_SSLMODE=require" "POSTGRES_PASSWORD=secretref:postgres-password"
)
DB_SECRET="postgres-password=keyvaultref:${KEY_VAULT_URI}/postgres-password,identityref:${IDENTITY_ID}"
CENSUS_SECRET="census-api-key=keyvaultref:${KEY_VAULT_URI}/census-api-key,identityref:${IDENTITY_ID}"

job_exists() {
  az containerapp job show --name "$1" --resource-group "$RESOURCE_GROUP" --output none 2>/dev/null
}

step "Migrations ($MIGRATE_JOB)"
if job_exists "$MIGRATE_JOB"; then
  az containerapp job update --name "$MIGRATE_JOB" --resource-group "$RESOURCE_GROUP" \
    --image "$BACKEND_IMAGE_REF" --output none
else
  az containerapp job create --name "$MIGRATE_JOB" --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT" --trigger-type Manual --replica-timeout 600 \
    --replica-retry-limit 0 --image "$BACKEND_IMAGE_REF" --cpu 0.5 --memory 1Gi \
    --mi-user-assigned "$IDENTITY_ID" --secrets "$DB_SECRET" --env-vars "${JOB_ENV[@]}" \
    --command alembic --args upgrade head --output none
fi
EXECUTION="$(az containerapp job start --name "$MIGRATE_JOB" \
  --resource-group "$RESOURCE_GROUP" --query name -o tsv)"
# Wait for it to finish (up to 10 minutes)
for _ in $(seq 1 60); do
  STATUS="$(az containerapp job execution show --name "$MIGRATE_JOB" \
    --resource-group "$RESOURCE_GROUP" --job-execution-name "$EXECUTION" \
    --query properties.status -o tsv)"
  [ "$STATUS" = "Running" ] || [ "$STATUS" = "Processing" ] || break
  sleep 10
done
echo "Migrations: $STATUS"
[ "$STATUS" = "Succeeded" ] || { echo "Migrations failed; not deploying."; exit 1; }

step "API ($API_APP)"
export LOCATION IDENTITY_ID ENVIRONMENT_ID KEY_VAULT_URI BACKEND_IMAGE_REF DB_HOST DB_NAME \
  DB_ADMIN FRONTEND_URL
# Fill in the ${...} placeholders in api.yaml from the variables above
python3 -c 'import os, sys; sys.stdout.write(os.path.expandvars(sys.stdin.read()))' \
  < api.yaml > /tmp/foodscape-api.yaml
if az containerapp show --name "$API_APP" --resource-group "$RESOURCE_GROUP" \
    --output none 2>/dev/null; then
  az containerapp update --name "$API_APP" --resource-group "$RESOURCE_GROUP" \
    --yaml /tmp/foodscape-api.yaml --output none
else
  az containerapp create --name "$API_APP" --resource-group "$RESOURCE_GROUP" \
    --yaml /tmp/foodscape-api.yaml --output none
fi
rm /tmp/foodscape-api.yaml

step "Weekly data pipeline ($PIPELINE_JOB)"
if job_exists "$PIPELINE_JOB"; then
  az containerapp job update --name "$PIPELINE_JOB" --resource-group "$RESOURCE_GROUP" \
    --image "$PIPELINE_IMAGE_REF" --output none
else
  # Every Monday at 08:00 UTC (3 a.m. in Dallas). The pipeline is idempotent, so a retry is safe.
  # It can't reach the API's Redis sidecar to clear the map cache, so new data appears when the
  # cache expires (within 24 hours).
  az containerapp job create --name "$PIPELINE_JOB" --resource-group "$RESOURCE_GROUP" \
    --environment "$ENVIRONMENT" --trigger-type Schedule --cron-expression "0 8 * * 1" \
    --replica-timeout 1800 --replica-retry-limit 1 --image "$PIPELINE_IMAGE_REF" \
    --cpu 1 --memory 2Gi --mi-user-assigned "$IDENTITY_ID" \
    --secrets "$DB_SECRET" "$CENSUS_SECRET" \
    --env-vars "${JOB_ENV[@]}" "CENSUS_API_KEY=secretref:census-api-key" --output none
fi

API_URL="https://$(az containerapp show --name "$API_APP" --resource-group "$RESOURCE_GROUP" \
  --query properties.configuration.ingress.fqdn -o tsv)"
if [ -n "${GITHUB_OUTPUT:-}" ]; then
  echo "api_url=$API_URL" >> "$GITHUB_OUTPUT"
fi
echo "$API_URL"
