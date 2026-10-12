# Shared names and settings for setup.sh, teardown.sh, and the deploy workflow.
# Names that must be unique across all of Azure get a short suffix derived from the
# subscription ID, so they're stable between runs.

LOCATION="${LOCATION:-southcentralus}"          # Texas: closest region to Dallas
STATIC_WEB_LOCATION="${STATIC_WEB_LOCATION:-centralus}"  # Static Web Apps has fewer regions
RESOURCE_GROUP="${RESOURCE_GROUP:-foodscape-rg}"
GITHUB_REPO="${GITHUB_REPO:-meganchacko/foodscapedallas}"

SUFFIX="$(az account show --query id -o tsv | shasum | cut -c1-6)"

DB_SERVER="foodscape-db-${SUFFIX}"
DB_NAME="foodscape"
DB_ADMIN="foodscape"
KEY_VAULT="foodscape-kv-${SUFFIX}"
IDENTITY="foodscape-identity"
ENVIRONMENT="foodscape-env"
API_APP="foodscape-api"
MIGRATE_JOB="foodscape-migrate"
PIPELINE_JOB="foodscape-pipeline"
STATIC_WEB_APP="foodscape-web-${SUFFIX}"
GITHUB_APP="foodscape-github-deploy"

# Images are built and pushed to GitHub's container registry by the deploy workflow
BACKEND_IMAGE="ghcr.io/${GITHUB_REPO%%/*}/foodscape-backend"
PIPELINE_IMAGE="ghcr.io/${GITHUB_REPO%%/*}/foodscape-pipeline"
# Until the first deploy pushes real images, apps start with Microsoft's sample image
PLACEHOLDER_IMAGE="mcr.microsoft.com/k8se/quickstart:latest"
