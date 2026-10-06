# Terraform

This configuration defines Artifact Registry, PostgreSQL 16 Cloud SQL, Cloud Storage, Secret Manager, two Cloud Run services, least-privilege service accounts, GitHub OIDC Workload Identity Federation, and a budget resource.

Before applying, supply `project_id` and configure billing. Cloud Run image tags must exist in Artifact Registry. No service-account JSON keys are used.

Teardown: `terraform destroy -var='project_id=YOUR_PROJECT_ID'` after removing any resources you want to retain.
