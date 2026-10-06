# Infrastructure (Terraform)

Creates everything the app needs in one GCP project. Not yet applied; see the status note in the
main README.

## What it creates

- Artifact Registry repository `skincare` for both images.
- Cloud SQL for PostgreSQL 16, Enterprise edition, `db-f1-micro`, zonal, no backups (demo sizing).
  Public IP with no authorised networks; Cloud Run reaches it through the Cloud SQL connector socket.
- A random database password, stored only inside the `skincare-database-url` Secret Manager secret.
- A private label bucket (`public_access_prevention = enforced`) with CORS for browser `PUT` uploads
  and a lifecycle rule that deletes photos after a day.
- Service accounts: `skincare-api` (bucket object admin on the label bucket only, Vertex AI user,
  Cloud SQL client, access to the one secret, Token Creator on itself for signed URLs) and
  `skincare-web` (no roles).
- Cloud Run services `skincare-api` and `skincare-web` (scale to zero, max 2 instances), and the
  Cloud Run job `skincare-migrate` that runs `alembic upgrade head` and the seed.
- A budget alert at 50% and 100% of `budget_amount`.
- Workload Identity Federation limited to `github_repository`, and a `skincare-deployer` service
  account with push access to the registry, `run.developer`, and actAs on the two runtime accounts.

Images start as Google's sample container; the deploy workflow replaces them and Terraform ignores
image changes afterwards.

## First deployment

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars   # set project_id and billing_account_id
terraform init
terraform apply
```

Then set these repository variables (Settings → Secrets and variables → Actions → Variables):

| Variable | Value |
|---|---|
| `GCP_PROJECT_ID` | your project |
| `GCP_REGION` | `asia-south1` unless you changed it |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `terraform output workload_identity_provider` |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | `terraform output deploy_service_account` |
| `API_URL` | `terraform output api_url` |

Run the **Deploy to Cloud Run** workflow. Finally set `cors_origins` in `terraform.tfvars` to the
`web_url` output and apply again, so only the web app can call the API and upload to the bucket.

## Teardown

```bash
terraform destroy
```

The bucket has `force_destroy = true` and the database has deletion protection off, so this removes
everything, including data.
