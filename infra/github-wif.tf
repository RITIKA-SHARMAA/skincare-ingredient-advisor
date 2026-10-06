resource "google_iam_workload_identity_pool" "github" {workload_identity_pool_id="github-actions" display_name="GitHub Actions"}
resource "google_iam_workload_identity_pool_provider" "github" {workload_identity_pool_id=google_iam_workload_identity_pool.github.workload_identity_pool_id workload_identity_pool_provider_id="github" display_name="GitHub" attribute_mapping={"google.subject"="assertion.sub","attribute.repository"="assertion.repository"} attribute_condition="assertion.repository == '${var.github_repository}'" oidc={issuer_uri="https://token.actions.githubusercontent.com"}}
resource "google_service_account" "github" {account_id="skincare-github"}
resource "google_service_account_iam_member" "github_wif" {service_account_id=google_service_account.github.name role="roles/iam.workloadIdentityUser" member="principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"}
resource "google_project_iam_member" "github_artifact" {project=var.project_id role="roles/artifactregistry.writer" member="serviceAccount:${google_service_account.github.email}"}
resource "google_project_iam_member" "github_run" {project=var.project_id role="roles/run.admin" member="serviceAccount:${google_service_account.github.email}"}
resource "google_service_account_iam_member" "github_deploy_api" {service_account_id=google_service_account.api.name role="roles/iam.serviceAccountUser" member="serviceAccount:${google_service_account.github.email}"}
resource "google_service_account_iam_member" "github_deploy_web" {service_account_id=google_service_account.web.name role="roles/iam.serviceAccountUser" member="serviceAccount:${google_service_account.github.email}"}
output "github_workload_provider" {value=google_iam_workload_identity_pool_provider.github.name}
output "github_service_account" {value=google_service_account.github.email}
